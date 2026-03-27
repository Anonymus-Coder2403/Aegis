"""Core billing domain types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BillAmounts:
    current_payable: float | None = None
    total_payable_rounded: float | None = None
    payable_by_due_date: float | None = None
    last_payment_amount: float | None = None
    last_payment_date: str | None = None
    last_receipt_no: str | None = None
    arrears_total: float | None = None


@dataclass
class BillConsumption:
    billed_units_kwh: float | None = None
    previous_read: float | None = None
    current_read: float | None = None


@dataclass
class CanonicalBill:
    source_doc_id: str
    bill_id: str | None = None
    account_no: str | None = None
    bill_month: str | None = None
    bill_date: str | None = None
    due_date: str | None = None
    disconnection_date: str | None = None
    amounts: BillAmounts = field(default_factory=BillAmounts)
    charges: dict[str, float | None] = field(default_factory=dict)
    consumption: BillConsumption = field(default_factory=BillConsumption)
    history: list[dict[str, str | float | None]] = field(default_factory=list)
    raw_text: str = ""
    evidence_map: dict[str, str] = field(default_factory=dict)
