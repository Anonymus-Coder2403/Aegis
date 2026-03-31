"""Answer orchestration for billing questions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aegis.billing.config import BillingConfig
from aegis.billing.llm_formatter import format_grounded_answer
from aegis.billing.parser import extractors
from aegis.billing.parser.msedcl_parser import can_parse_msedcl, parse_msedcl_bill
from aegis.billing.parser.pvvnl_parser import can_parse_pvvnl, parse_pvvnl_bill
from aegis.billing.query_classifier import classify_billing_query
from aegis.billing.rag.retriever import (
    lookup_exact_fields,
    retrieve_charge_snippets,
    retrieve_document_snippets,
    retrieve_history_snippets,
)
from aegis.billing.rag.store import BillingStore
from aegis.billing.types import CanonicalBill


@dataclass
class BillingAnswer:
    answer_text: str
    resolved_fields: dict[str, object | None]
    evidence: dict[str, str]
    query_type: str
    used_fallback: bool
    source_doc_id: str


def _parse_bill(extracted: extractors.ExtractedBillContent) -> CanonicalBill:
    """Auto-detect bill format and parse with the appropriate parser."""
    if can_parse_msedcl(extracted.raw_text):
        return parse_msedcl_bill(extracted)
    if can_parse_pvvnl(extracted.raw_text):
        return parse_pvvnl_bill(extracted)
    raise ValueError(
        "Unsupported bill format: the PDF does not appear to be a PVVNL or MSEDCL "
        "electricity bill. Only PVVNL (UP-DISCOM) and MSEDCL formats are supported."
    )


def ingest_bill(
    pdf_path: str | Path,
    config: BillingConfig,
    force_reingest: bool = False,
) -> CanonicalBill:
    source_doc_id = Path(pdf_path).stem
    store = BillingStore(config)
    if not force_reingest:
        cached = store.load_bill(source_doc_id)
        if cached is not None:
            return cached
    extracted = extractors.extract_pdf_content(pdf_path)
    bill = _parse_bill(extracted)
    store.upsert_bill(bill)
    return bill


def inspect_bill(pdf_path: str | Path) -> CanonicalBill:
    extracted = extractors.extract_pdf_content(pdf_path)
    return _parse_bill(extracted)


def answer_billing_question(
    question: str,
    config: BillingConfig,
    pdf_path: str | Path | None = None,
) -> BillingAnswer:
    if pdf_path is None:
        raise ValueError("Single-bill query flow requires an explicit pdf_path.")

    bill = ingest_bill(pdf_path, config)

    intent = classify_billing_query(question)
    resolved_fields: dict[str, object | None] = {}
    evidence: dict[str, str] = {}
    snippets: list[dict[str, object]] = []
    used_fallback = False

    if intent.query_type == "insufficient_context":
        answer_text = format_grounded_answer(
            question=question,
            query_type=intent.query_type,
            resolved_fields=resolved_fields,
            evidence=evidence,
            snippets=snippets,
            config=config,
        )
        return BillingAnswer(
            answer_text=answer_text,
            resolved_fields=resolved_fields,
            evidence=evidence,
            query_type=intent.query_type,
            used_fallback=True,
            source_doc_id=bill.source_doc_id,
        )

    if intent.query_type == "exact_field_lookup":
        resolved_fields = lookup_exact_fields(bill, intent.field_paths)
        evidence = {key: bill.evidence_map.get(key, "") for key in resolved_fields}
    elif intent.query_type == "charge_breakdown_lookup":
        resolved_fields = lookup_exact_fields(bill, intent.field_paths)
        evidence = {key: bill.evidence_map.get(key, "") for key in resolved_fields}
        snippets = retrieve_charge_snippets(
            query_text=question,
            source_doc_id=bill.source_doc_id,
            config=config,
        )
        used_fallback = True
    elif intent.query_type == "history_lookup":
        resolved_fields = lookup_exact_fields(bill, intent.field_paths)
        evidence = {key: bill.evidence_map.get(key, "") for key in resolved_fields}
        snippets = retrieve_history_snippets(
            query_text=question,
            source_doc_id=bill.source_doc_id,
            config=config,
        )
        used_fallback = True
    else:
        snippets = retrieve_document_snippets(
            query_text=question,
            source_doc_id=bill.source_doc_id,
            config=config,
        )
        used_fallback = True

    answer_text = format_grounded_answer(
        question=question,
        query_type=intent.query_type,
        resolved_fields=resolved_fields,
        evidence=evidence,
        snippets=snippets,
        config=config,
    )

    if intent.query_type == "exact_field_lookup":
        used_fallback = not any(value is not None for value in resolved_fields.values())

    return BillingAnswer(
        answer_text=answer_text,
        resolved_fields=resolved_fields,
        evidence=evidence,
        query_type=intent.query_type,
        used_fallback=used_fallback,
        source_doc_id=bill.source_doc_id,
    )
