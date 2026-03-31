"""Local persistence for canonical bills and optional vector data."""

from __future__ import annotations

from dataclasses import asdict
import json
import logging
from typing import Any

from aegis.billing.config import BillingConfig
from aegis.billing.rag.embeddings import embed_text
from aegis.billing.types import BillAmounts, BillConsumption, CanonicalBill

LOGGER = logging.getLogger(__name__)

_RAW_TEXT_CHUNK_SIZE = 500
_RAW_TEXT_OVERLAP = 50


def _build_field_chunks(bill: CanonicalBill) -> list[dict[str, Any]]:
    sid = bill.source_doc_id
    chunks: list[dict[str, Any]] = []

    # Summary chunk
    summary_lines = []
    for field_name in ("bill_id", "account_no", "bill_month", "bill_date", "due_date", "disconnection_date"):
        value = getattr(bill, field_name, None)
        if value is not None:
            summary_lines.append(f"{field_name}: {value}")
    if summary_lines:
        chunks.append({
            "id": f"{sid}:summary",
            "text": "Bill summary: " + "; ".join(summary_lines),
            "metadata": {
                "source_doc_id": sid,
                "chunk_type": "summary",
                "field_paths": json.dumps([f for f in ("bill_id", "account_no", "bill_month", "bill_date", "due_date", "disconnection_date") if getattr(bill, f, None) is not None]),
            },
        })

    # Amounts chunk
    amounts_dict = asdict(bill.amounts)
    amount_lines = [f"amounts.{k}: {v}" for k, v in amounts_dict.items() if v is not None]
    if amount_lines:
        chunks.append({
            "id": f"{sid}:amounts",
            "text": "Bill amounts: " + "; ".join(amount_lines),
            "metadata": {
                "source_doc_id": sid,
                "chunk_type": "amounts",
                "field_paths": json.dumps([f"amounts.{k}" for k, v in amounts_dict.items() if v is not None]),
            },
        })

    # Consumption chunk
    consumption_dict = asdict(bill.consumption)
    consumption_lines = [f"consumption.{k}: {v}" for k, v in consumption_dict.items() if v is not None]
    if consumption_lines:
        chunks.append({
            "id": f"{sid}:consumption",
            "text": "Bill consumption: " + "; ".join(consumption_lines),
            "metadata": {
                "source_doc_id": sid,
                "chunk_type": "consumption",
                "field_paths": json.dumps([f"consumption.{k}" for k, v in consumption_dict.items() if v is not None]),
            },
        })

    # Evidence chunks — one per evidence_map entry
    for field_path, evidence_text in bill.evidence_map.items():
        if evidence_text:
            chunks.append({
                "id": f"{sid}:evidence:{field_path}",
                "text": f"{field_path}: {evidence_text}",
                "metadata": {
                    "source_doc_id": sid,
                    "chunk_type": "evidence",
                    "field_paths": json.dumps([field_path]),
                },
            })

    # Raw text chunks — ~500 char segments with 50 char overlap
    raw = bill.raw_text or ""
    if raw:
        start = 0
        idx = 0
        while start < len(raw):
            end = start + _RAW_TEXT_CHUNK_SIZE
            chunks.append({
                "id": f"{sid}:raw:{idx}",
                "text": raw[start:end],
                "metadata": {
                    "source_doc_id": sid,
                    "chunk_type": "raw_text",
                    "field_paths": "[]",
                },
            })
            start = end - _RAW_TEXT_OVERLAP
            idx += 1

    return chunks


class BillingStore:
    def __init__(self, config: BillingConfig) -> None:
        self.config = config
        self.config.canonical_dir.mkdir(parents=True, exist_ok=True)
        self.config.chroma_dir.mkdir(parents=True, exist_ok=True)

    def upsert_bill(self, bill: CanonicalBill) -> None:
        canonical_path = self.config.canonical_dir / f"{bill.source_doc_id}.json"
        canonical_path.write_text(
            json.dumps(asdict(bill), indent=2),
            encoding="utf-8",
        )

        try:
            import chromadb
        except ImportError:
            return

        client = chromadb.PersistentClient(path=str(self.config.chroma_dir))
        fields = client.get_or_create_collection("bill_fields")
        charges = client.get_or_create_collection("bill_charges")
        history = client.get_or_create_collection("bill_history")

        chunks = _build_field_chunks(bill)
        if chunks:
            try:
                fields.upsert(
                    ids=[c["id"] for c in chunks],
                    documents=[c["text"] for c in chunks],
                    metadatas=[c["metadata"] for c in chunks],
                    embeddings=[embed_text(c["text"]) for c in chunks],
                )
            except Exception:
                LOGGER.warning(
                    "bill_fields upsert failed for source_doc_id='%s'; "
                    "canonical JSON is saved but vector index may be incomplete.",
                    bill.source_doc_id,
                    exc_info=True,
                )

        for key, value in bill.charges.items():
            if value is None:
                continue
            try:
                charges.upsert(
                    ids=[f"{bill.source_doc_id}:{key}"],
                    documents=[f"{key}: {value}"],
                    metadatas=[{"source_doc_id": bill.source_doc_id, "charge_type": key}],
                    embeddings=[embed_text(f"{key}: {value}")],
                )
            except Exception:
                LOGGER.warning(
                    "bill_charges upsert failed for key='%s' source_doc_id='%s'.",
                    key,
                    bill.source_doc_id,
                    exc_info=True,
                )

        for index, row in enumerate(bill.history):
            row_text = json.dumps(row, ensure_ascii=False)
            try:
                history.upsert(
                    ids=[f"{bill.source_doc_id}:history:{index}"],
                    documents=[row_text],
                    metadatas=[{"source_doc_id": bill.source_doc_id}],
                    embeddings=[embed_text(row_text)],
                )
            except Exception:
                LOGGER.warning(
                    "bill_history upsert failed for index=%d source_doc_id='%s'.",
                    index,
                    bill.source_doc_id,
                    exc_info=True,
                )

    def load_bill(self, source_doc_id: str) -> CanonicalBill | None:
        """Return a previously ingested bill by source_doc_id, or None if not found."""
        canonical_path = self.config.canonical_dir / f"{source_doc_id}.json"
        if not canonical_path.exists():
            return None
        payload = json.loads(canonical_path.read_text(encoding="utf-8"))
        return _canonical_bill_from_dict(payload)

    def load_latest_bill(self) -> CanonicalBill | None:
        files = sorted(self.config.canonical_dir.glob("*.json"))
        if not files:
            return None
        payload = json.loads(files[-1].read_text(encoding="utf-8"))
        return _canonical_bill_from_dict(payload)


def _canonical_bill_from_dict(payload: dict[str, Any]) -> CanonicalBill:
    return CanonicalBill(
        source_doc_id=payload["source_doc_id"],
        bill_id=payload.get("bill_id"),
        account_no=payload.get("account_no"),
        bill_month=payload.get("bill_month"),
        bill_date=payload.get("bill_date"),
        due_date=payload.get("due_date"),
        disconnection_date=payload.get("disconnection_date"),
        amounts=BillAmounts(**payload.get("amounts", {})),
        charges=payload.get("charges", {}),
        consumption=BillConsumption(**payload.get("consumption", {})),
        history=payload.get("history", []),
        raw_text=payload.get("raw_text", ""),
        evidence_map=payload.get("evidence_map", {}),
    )
