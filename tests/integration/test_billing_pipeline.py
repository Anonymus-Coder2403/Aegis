"""Integration tests for the full billing pipeline (real PDF, ChromaDB, embeddings, LiteLLM)."""

import os
from pathlib import Path

import pytest

from aegis.billing.answerer import answer_billing_question, ingest_bill
from aegis.billing.config import BillingConfig
from aegis.billing.rag.retriever import retrieve_charge_snippets

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY"),
        reason="GEMINI_API_KEY not set",
    ),
]


@pytest.fixture
def billing_config(tmp_path: Path) -> BillingConfig:
    return BillingConfig(
        store_dir=tmp_path / ".billing_store",
        litellm_enabled=True,
    )


@pytest.fixture
def ingested_bill(billing_config: BillingConfig, pvvnl_pdf_path: Path):
    return ingest_bill(pvvnl_pdf_path, billing_config, force_reingest=True)


def test_ingested_bill_structure(ingested_bill):
    assert ingested_bill.source_doc_id == "document_pdf"
    assert ingested_bill.amounts.current_payable is not None
    assert ingested_bill.due_date is not None


def test_chromadb_retrieval_returns_snippets(
    ingested_bill, billing_config: BillingConfig
):
    snippets = retrieve_charge_snippets(
        query_text="electricity duty",
        source_doc_id=ingested_bill.source_doc_id,
        config=billing_config,
    )
    assert isinstance(snippets, list)
    assert len(snippets) > 0


def test_full_pipeline_charge_breakdown(
    billing_config: BillingConfig, pvvnl_pdf_path: Path
):
    result = answer_billing_question(
        "Show me the charge breakdown and electricity duty",
        billing_config,
        pdf_path=pvvnl_pdf_path,
    )
    assert result.query_type == "charge_breakdown_lookup"
    assert isinstance(result.answer_text, str)
    assert len(result.answer_text) > 0


def test_full_pipeline_history_lookup(
    billing_config: BillingConfig, pvvnl_pdf_path: Path
):
    result = answer_billing_question(
        "Show me consumption history",
        billing_config,
        pdf_path=pvvnl_pdf_path,
    )
    assert result.query_type == "history_lookup"
    assert isinstance(result.answer_text, str)
    assert len(result.answer_text) > 0


def test_exact_field_bypasses_litellm(
    billing_config: BillingConfig, pvvnl_pdf_path: Path
):
    result = answer_billing_question(
        "What is the due date?",
        billing_config,
        pdf_path=pvvnl_pdf_path,
    )
    assert result.query_type == "exact_field_lookup"
    assert result.used_fallback is False
