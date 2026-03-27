import types

from aegis.billing.config import BillingConfig
from aegis.billing.rag import retriever
from aegis.billing.rag.retriever import lookup_exact_fields
from aegis.billing.rag.store import _build_field_chunks
from aegis.billing.types import (
    BillAmounts,
    BillConsumption,
    CanonicalBill,
)


def _sample_bill() -> CanonicalBill:
    return CanonicalBill(
        source_doc_id="bill_jan_2020",
        bill_id="132189891047",
        account_no="1321865000",
        bill_month="JAN-2020",
        bill_date="17-JAN-2020",
        due_date="24-JAN-2020",
        disconnection_date="31-JAN-2020",
        amounts=BillAmounts(
            current_payable=2837.58,
            total_payable_rounded=2837.0,
            payable_by_due_date=2811.0,
            last_payment_amount=2119.0,
            last_payment_date="10-JAN-2020",
            last_receipt_no="132186537483",
            arrears_total=-0.21,
        ),
        charges={},
        consumption=BillConsumption(
            billed_units_kwh=379.0,
            previous_read=12021.0,
            current_read=12400.0,
        ),
        history=[],
        raw_text="raw text",
        evidence_map={"amounts.last_payment_amount": "Last Payment Amount 2119.00"},
    )


def test_lookup_exact_fields_returns_requested_paths():
    resolved = lookup_exact_fields(
        _sample_bill(),
        [
            "amounts.last_payment_date",
            "amounts.last_payment_amount",
            "due_date",
        ],
    )

    assert resolved == {
        "amounts.last_payment_date": "10-JAN-2020",
        "amounts.last_payment_amount": 2119.0,
        "due_date": "24-JAN-2020",
    }


def test_lookup_exact_fields_returns_none_for_missing_paths():
    resolved = lookup_exact_fields(_sample_bill(), ["amounts.unknown_value"])

    assert resolved == {"amounts.unknown_value": None}


def test_retrieve_charge_snippets_applies_source_doc_filter(monkeypatch, tmp_path):
    observed = {}

    class FakeCollection:
        def query(self, **kwargs):
            observed.update(kwargs)
            return {
                "documents": [["electricity_duty: 133.93"]],
                "metadatas": [[{"source_doc_id": "bill_jan_2020", "charge_type": "electricity_duty"}]],
                "distances": [[0.12]],
            }

    class FakeClient:
        def __init__(self, path):
            observed["path"] = path

        def get_or_create_collection(self, name):
            observed["collection"] = name
            return FakeCollection()

    fake_chromadb = types.SimpleNamespace(PersistentClient=FakeClient)
    monkeypatch.setattr(retriever, "chromadb", fake_chromadb, raising=False)
    monkeypatch.setitem(__import__("sys").modules, "chromadb", fake_chromadb)

    config = BillingConfig(store_dir=tmp_path)
    snippets = retriever.retrieve_charge_snippets(
        query_text="electricity duty",
        source_doc_id="bill_jan_2020",
        config=config,
        n_results=4,
    )

    assert observed["collection"] == "bill_charges"
    assert observed["where"] == {"source_doc_id": "bill_jan_2020"}
    assert snippets[0]["document"] == "electricity_duty: 133.93"


def test_retrieve_document_snippets_returns_empty_on_query_error(monkeypatch, tmp_path):
    class FakeCollection:
        def query(self, **kwargs):
            raise RuntimeError("query failed")

    class FakeClient:
        def __init__(self, path):
            pass

        def get_or_create_collection(self, name):
            return FakeCollection()

    fake_chromadb = types.SimpleNamespace(PersistentClient=FakeClient)
    monkeypatch.setattr(retriever, "chromadb", fake_chromadb, raising=False)
    monkeypatch.setitem(__import__("sys").modules, "chromadb", fake_chromadb)

    config = BillingConfig(store_dir=tmp_path)
    snippets = retriever.retrieve_document_snippets(
        query_text="service quality",
        source_doc_id="bill_jan_2020",
        config=config,
    )

    assert snippets == []


def test_retrieve_document_snippets_logs_query_error(monkeypatch, tmp_path, caplog):
    class FakeCollection:
        def query(self, **kwargs):
            raise RuntimeError("query failed")

    class FakeClient:
        def __init__(self, path):
            pass

        def get_or_create_collection(self, name):
            return FakeCollection()

    fake_chromadb = types.SimpleNamespace(PersistentClient=FakeClient)
    monkeypatch.setattr(retriever, "chromadb", fake_chromadb, raising=False)
    monkeypatch.setitem(__import__("sys").modules, "chromadb", fake_chromadb)

    config = BillingConfig(store_dir=tmp_path)
    with caplog.at_level("ERROR"):
        snippets = retriever.retrieve_document_snippets(
            query_text="service quality",
            source_doc_id="bill_jan_2020",
            config=config,
        )

    assert snippets == []
    assert "Semantic retrieval query failed" in caplog.text


def test_retrieve_document_snippets_returns_multiple_chunks(monkeypatch, tmp_path):
    """With chunked storage, bill_fields returns multiple docs per query."""

    class FakeCollection:
        def query(self, **kwargs):
            return {
                "documents": [["Bill summary: bill_id: 123", "Bill amounts: current_payable: 2837.58", "raw text chunk 0", "evidence: due_date: 24-JAN"]],
                "metadatas": [[
                    {"source_doc_id": "bill_jan_2020", "chunk_type": "summary"},
                    {"source_doc_id": "bill_jan_2020", "chunk_type": "amounts"},
                    {"source_doc_id": "bill_jan_2020", "chunk_type": "raw_text"},
                    {"source_doc_id": "bill_jan_2020", "chunk_type": "evidence"},
                ]],
                "distances": [[0.1, 0.2, 0.3, 0.4]],
            }

    class FakeClient:
        def __init__(self, path):
            pass

        def get_or_create_collection(self, name):
            return FakeCollection()

    fake_chromadb = types.SimpleNamespace(PersistentClient=FakeClient)
    monkeypatch.setattr(retriever, "chromadb", fake_chromadb, raising=False)
    monkeypatch.setitem(__import__("sys").modules, "chromadb", fake_chromadb)
    monkeypatch.setattr(retriever, "embed_text", lambda text: [0.1, 0.2, 0.3], raising=False)

    config = BillingConfig(store_dir=tmp_path)
    snippets = retriever.retrieve_document_snippets(
        query_text="what is my bill amount",
        source_doc_id="bill_jan_2020",
        config=config,
        n_results=4,
    )

    assert len(snippets) == 4
    assert snippets[0]["metadata"]["chunk_type"] == "summary"
    assert snippets[1]["metadata"]["chunk_type"] == "amounts"


def test_retrieve_document_snippets_uses_local_query_embeddings(monkeypatch, tmp_path):
    observed = {}

    class FakeCollection:
        def query(self, **kwargs):
            observed.update(kwargs)
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    class FakeClient:
        def __init__(self, path):
            pass

        def get_or_create_collection(self, name):
            return FakeCollection()

    fake_chromadb = types.SimpleNamespace(PersistentClient=FakeClient)
    monkeypatch.setattr(retriever, "chromadb", fake_chromadb, raising=False)
    monkeypatch.setitem(__import__("sys").modules, "chromadb", fake_chromadb)
    monkeypatch.setattr(retriever, "embed_text", lambda text: [0.1, 0.2, 0.3], raising=False)

    config = BillingConfig(store_dir=tmp_path)
    retriever.retrieve_document_snippets(
        query_text="service quality",
        source_doc_id="bill_jan_2020",
        config=config,
    )

    assert observed["query_embeddings"] == [[0.1, 0.2, 0.3]]
    assert "query_texts" not in observed


def test_build_field_chunks_produces_expected_chunk_types():
    bill = _sample_bill()
    chunks = _build_field_chunks(bill)

    chunk_types = {c["metadata"]["chunk_type"] for c in chunks}
    assert "summary" in chunk_types
    assert "amounts" in chunk_types
    assert "consumption" in chunk_types
    assert "evidence" in chunk_types
    assert "raw_text" in chunk_types

    # Summary chunk should contain bill_id
    summary = [c for c in chunks if c["metadata"]["chunk_type"] == "summary"][0]
    assert "132189891047" in summary["text"]

    # Amounts chunk should contain all 7 fields
    amounts = [c for c in chunks if c["metadata"]["chunk_type"] == "amounts"][0]
    assert "amounts.current_payable: 2837.58" in amounts["text"]

    # Evidence chunk — one per evidence_map entry
    evidence_chunks = [c for c in chunks if c["metadata"]["chunk_type"] == "evidence"]
    assert len(evidence_chunks) == len(bill.evidence_map)

    # All chunks have source_doc_id
    for chunk in chunks:
        assert chunk["metadata"]["source_doc_id"] == "bill_jan_2020"

    # Total chunk count >= 5 (summary + amounts + consumption + evidence + raw_text)
    assert len(chunks) >= 5
