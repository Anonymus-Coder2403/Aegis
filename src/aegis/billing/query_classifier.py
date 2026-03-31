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

    # --- Multi-word phrase rules (most specific first) ---

    if "receipt number" in normalized or "receipt no" in normalized:
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["amounts.last_receipt_no"],
            needs_semantic_fallback=False,
        )

    if "bill number" in normalized or "bill no" in normalized or "bill id" in normalized:
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["bill_id"],
            needs_semantic_fallback=False,
        )

    if (
        "account number" in normalized
        or "account no" in normalized
        or "consumer number" in normalized
        or "consumer no" in normalized
    ):
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["account_no"],
            needs_semantic_fallback=False,
        )

    if "rounded payable" in normalized or "total payable" in normalized:
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["amounts.total_payable_rounded"],
            needs_semantic_fallback=False,
        )

    if (
        "payable by due" in normalized
        or "by due date" in normalized
        or "if paid" in normalized
        or "before due" in normalized
        or "pay by" in normalized
    ):
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["amounts.payable_by_due_date"],
            needs_semantic_fallback=False,
        )

    # --- Two-keyword combination rules ---

    if "last" in normalized and "paid" in normalized:
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=[
                "amounts.last_payment_date",
                "amounts.last_payment_amount",
            ],
            needs_semantic_fallback=False,
        )

    if "last" in normalized and "receipt" in normalized:
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=[
                "amounts.last_receipt_no",
                "amounts.last_payment_date",
            ],
            needs_semantic_fallback=False,
        )

    # --- Single-phrase and keyword rules ---

    if "bill month" in normalized or "billing period" in normalized or "which month" in normalized:
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["bill_month"],
            needs_semantic_fallback=False,
        )

    if "bill date" in normalized or "issued on" in normalized or "generated on" in normalized:
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["bill_date"],
            needs_semantic_fallback=False,
        )

    if "due date" in normalized:
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["due_date"],
            needs_semantic_fallback=False,
        )

    if "disconnection" in normalized or "cut off" in normalized or "supply cut" in normalized:
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["disconnection_date"],
            needs_semantic_fallback=False,
        )

    if "arrears" in normalized or "outstanding" in normalized or "overdue" in normalized:
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["amounts.arrears_total"],
            needs_semantic_fallback=False,
        )

    if "current payable" in normalized or "owe" in normalized or "total amount" in normalized:
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["amounts.current_payable"],
            needs_semantic_fallback=False,
        )

    if "how much" in normalized and "last" not in normalized:
        return BillingQueryIntent(
            query_type="exact_field_lookup",
            field_paths=["amounts.current_payable"],
            needs_semantic_fallback=False,
        )

    # --- Category rules (charge breakdown, history) ---

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
        or "units" in normalized
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
