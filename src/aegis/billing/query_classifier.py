"""Rule-based query classification for billing questions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BillingQueryIntent:
    query_type: str
    field_paths: list[str]
    needs_semantic_fallback: bool
    bill_selection_hint: str | None = None


def classify_billing_query(question: str) -> BillingQueryIntent:
    normalized = question.lower().strip()

    if len(normalized) < 8:
        return BillingQueryIntent(
            query_type="insufficient_context",
            field_paths=[],
            needs_semantic_fallback=False,
        )

    if "last" in normalized and "paid" in normalized:
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=[
                "amounts.last_payment_date",
                "amounts.last_payment_amount",
            ],
            needs_semantic_fallback=False,
        )

    if "due date" in normalized:
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["due_date"],
            needs_semantic_fallback=False,
        )

    if "rounded payable" in normalized:
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["amounts.total_payable_rounded"],
            needs_semantic_fallback=False,
        )

    if "charge" in normalized or "duty" in normalized or "lpsc" in normalized:
        return BillingQueryIntent(
            query_type="charge_breakdown_lookup",
            field_paths=[
                "charges.electricity_charges",
                "charges.fixed_demand_charges",
                "charges.current_bill_lpsc",
                "charges.electricity_duty",
            ],
            needs_semantic_fallback=True,
        )

    if (
        "history" in normalized
        or "consumption" in normalized
        or "previous month" in normalized
    ):
        return BillingQueryIntent(
            query_type="history_lookup",
            field_paths=[
                "history",
                "consumption.billed_units_kwh",
                "consumption.previous_read",
                "consumption.current_read",
            ],
            needs_semantic_fallback=True,
        )

    return BillingQueryIntent(
        query_type="document_fallback_lookup",
        field_paths=[],
        needs_semantic_fallback=True,
    )
