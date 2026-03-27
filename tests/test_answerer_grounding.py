from pathlib import Path

import pytest

from aegis.billing.answerer import answer_billing_question
from aegis.billing.config import BillingConfig
from aegis.billing.query_classifier import BillingQueryIntent
from aegis.billing.types import BillAmounts, BillConsumption, CanonicalBill


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
        charges={
            "electricity_charges": 2238.5,
            "fixed_demand_charges": 440.0,
            "current_bill_lpsc": 25.15,
            "electricity_duty": 133.93,
        },
        consumption=BillConsumption(
            billed_units_kwh=379.0,
            previous_read=12021.0,
            current_read=12400.0,
        ),
        history=[
            {"month": "DEC-2019", "units": 272.0, "demand": 4.0},
            {"month": "NOV-2019", "units": 202.0, "demand": 4.0},
        ],
        raw_text="raw bill text",
        evidence_map={
            "amounts.last_payment_amount": "Last Payment Amount 2119.00",
            "amounts.last_payment_date": "Receipt Date 10-JAN-2020",
            "charges.electricity_duty": "Electricity Duty 133.93",
        },
    )


def test_exact_lookup_answer_uses_structured_fields(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "aegis.billing.answerer.ingest_bill",
        lambda pdf_path, config: _sample_bill(),
    )
    monkeypatch.setattr(
        "aegis.billing.answerer.classify_billing_query",
        lambda _: BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["amounts.last_payment_date", "amounts.last_payment_amount"],
            needs_semantic_fallback=False,
        ),
    )

    result = answer_billing_question(
        question="When was my last electricity bill paid?",
        config=BillingConfig(store_dir=tmp_path),
        pdf_path="document_pdf.pdf",
    )

    assert result.used_fallback is False
    assert "10-JAN-2020" in result.answer_text
    assert "2119.0" in result.answer_text


def test_charge_lookup_uses_deterministic_fallback_if_litellm_disabled(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "aegis.billing.answerer.ingest_bill",
        lambda pdf_path, config: _sample_bill(),
    )
    monkeypatch.setattr(
        "aegis.billing.answerer.classify_billing_query",
        lambda _: BillingQueryIntent(
            query_type="charge_breakdown_lookup",
            field_paths=["charges.electricity_duty", "charges.fixed_demand_charges"],
            needs_semantic_fallback=True,
        ),
    )
    monkeypatch.setattr(
        "aegis.billing.answerer.retrieve_charge_snippets",
        lambda **_: [{"document": "electricity_duty: 133.93", "metadata": {}, "distance": 0.1}],
    )

    result = answer_billing_question(
        question="Show electricity duty and fixed charges",
        config=BillingConfig(store_dir=tmp_path, litellm_enabled=False),
        pdf_path="document_pdf.pdf",
    )

    assert result.used_fallback is True
    assert "Charge breakdown" in result.answer_text
    assert "charges.electricity_duty" in result.answer_text


def test_document_fallback_returns_not_found_when_no_snippets(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "aegis.billing.answerer.ingest_bill",
        lambda pdf_path, config: _sample_bill(),
    )
    monkeypatch.setattr(
        "aegis.billing.answerer.classify_billing_query",
        lambda _: BillingQueryIntent(
            query_type="document_fallback_lookup",
            field_paths=[],
            needs_semantic_fallback=True,
        ),
    )
    monkeypatch.setattr(
        "aegis.billing.answerer.retrieve_document_snippets",
        lambda **_: [],
    )

    result = answer_billing_question(
        question="Summarize service quality notes",
        config=BillingConfig(store_dir=tmp_path, litellm_enabled=False),
        pdf_path="document_pdf.pdf",
    )

    assert result.used_fallback is True
    assert result.answer_text == "I could not find that in the bill documents."


def test_insufficient_context_returns_clarification(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "aegis.billing.answerer.ingest_bill",
        lambda pdf_path, config: _sample_bill(),
    )
    monkeypatch.setattr(
        "aegis.billing.answerer.classify_billing_query",
        lambda _: BillingQueryIntent(
            query_type="insufficient_context",
            field_paths=[],
            needs_semantic_fallback=False,
        ),
    )

    result = answer_billing_question(
        question="bill?",
        config=BillingConfig(store_dir=tmp_path, litellm_enabled=False),
        pdf_path="document_pdf.pdf",
    )

    assert result.query_type == "insufficient_context"
    assert result.used_fallback is True
    assert "more specific" in result.answer_text


def test_exact_lookup_with_missing_field_returns_not_found(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "aegis.billing.answerer.ingest_bill",
        lambda pdf_path, config: _sample_bill(),
    )
    monkeypatch.setattr(
        "aegis.billing.answerer.classify_billing_query",
        lambda _: BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["amounts.unknown_field"],
            needs_semantic_fallback=False,
        ),
    )

    result = answer_billing_question(
        question="What is unknown field?",
        config=BillingConfig(store_dir=tmp_path),
        pdf_path="document_pdf.pdf",
    )

    assert result.used_fallback is True
    assert result.answer_text == "I could not find that in the bill documents."


def test_answer_billing_question_requires_explicit_pdf_path(tmp_path):
    with pytest.raises(ValueError, match="requires an explicit pdf_path"):
        answer_billing_question(
            question="When was my last electricity bill paid?",
            config=BillingConfig(store_dir=tmp_path),
            pdf_path=None,
        )
