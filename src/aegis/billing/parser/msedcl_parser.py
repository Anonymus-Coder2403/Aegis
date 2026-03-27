"""Rule-based MSEDCL/LTIP bill parser for OCR-extracted text."""

from __future__ import annotations

import re

from aegis.billing.parser.extractors import ExtractedBillContent
from aegis.billing.parser.normalize import clean_cell, parse_amount, parse_date
from aegis.billing.types import BillAmounts, BillConsumption, CanonicalBill


def parse_msedcl_bill(extracted: ExtractedBillContent) -> CanonicalBill:
    """Parse an MSEDCL/LTIP format electricity bill."""
    raw_text = extracted.raw_text

    bill_month = _extract_bill_month(raw_text)
    bill_date = _extract_field(raw_text, r"B?BILL\s*DATE\s*\n?\s*[I|]?(\d{2}-\d{2}-\d{4})")
    due_date = _extract_field(raw_text, r"I?DUE\s*DATE\s*\n?\s*[I|]?(\d{2}-\d{2}-\d{4})")
    paid_upto_date = _extract_field(raw_text, r"IF\s*PAID\s*UPTO\s*\n?\s*[I|]?(\d{2}-\d{2}-\d{4})")
    paid_after_date = _extract_field(raw_text, r"IF\s*PAID\s*AFTER\s*\n?\s*[I|]?(\d{2}-\d{2}-\d{4})")

    # Amounts following dates on the same or next line
    bill_amount = _extract_amount_after(raw_text, r"B?BILL\s*DATE\s*\n?\s*[I|]?\d{2}-\d{2}-\d{4}\s*\n?\s*")
    paid_upto_amount = _extract_amount_after(raw_text, r"IF\s*PAID\s*UPTO\s*\n?\s*[I|]?\d{2}-\d{2}-\d{4}\s*\n?\s*")
    paid_after_amount = _extract_amount_after(raw_text, r"IF\s*PAID\s*AFTER\s*\n?\s*[I|]?\d{2}-\d{2}-\d{4}\s*\n?\s*")

    last_receipt_date = _extract_field(raw_text, r"Last\s*Receipt\s*No\.?\s*[I|]?\s*Date\s*\n?\s*[I|]?(\d{2}-\d{2}-\d{4})")
    last_month_payment = _extract_amount_after(raw_text, r"I?Last\s*Month\s*Payment\s*\n?\s*")

    total_current_bill = _extract_amount_after(raw_text, r"TOTAL\s*CURRENT\s*BILL\s*\n?\s*")

    # Consumer account number
    account_match = re.search(r"(\d{12,})\s*\(Opted", raw_text)
    account_no = account_match.group(1) if account_match else None

    # Consumption from page 2
    consumption = _extract_consumption(raw_text)
    history = _extract_billing_history(raw_text)
    charges = _extract_charges(raw_text)

    amounts = BillAmounts(
        current_payable=total_current_bill or bill_amount,
        total_payable_rounded=paid_after_amount,
        payable_by_due_date=paid_upto_amount,
        last_payment_amount=last_month_payment,
        last_payment_date=last_receipt_date,
        last_receipt_no=None,
        arrears_total=None,
    )

    evidence_map: dict[str, str] = {}
    if bill_amount is not None:
        evidence_map["amounts.current_payable"] = f"TOTAL CURRENT BILL {total_current_bill or bill_amount}"
    if paid_upto_amount is not None:
        evidence_map["amounts.payable_by_due_date"] = f"IF PAID UPTO {paid_upto_date} {paid_upto_amount}"
    if paid_after_amount is not None:
        evidence_map["amounts.total_payable_rounded"] = f"IF PAID AFTER {paid_after_date} {paid_after_amount}"
    if last_month_payment is not None:
        evidence_map["amounts.last_payment_amount"] = f"Last Month Payment {last_month_payment}"
    if last_receipt_date is not None:
        evidence_map["amounts.last_payment_date"] = f"Last Receipt Date {last_receipt_date}"

    from pathlib import Path

    return CanonicalBill(
        source_doc_id=Path(extracted.source_path).stem,
        bill_id=None,
        account_no=account_no,
        bill_month=bill_month,
        bill_date=_normalize_date(bill_date),
        due_date=_normalize_date(due_date),
        disconnection_date=None,
        amounts=amounts,
        charges=charges,
        consumption=consumption,
        history=history,
        raw_text=raw_text,
        evidence_map={k: v for k, v in evidence_map.items() if v is not None},
    )


def _extract_field(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match:
        return clean_cell(match.group(1))
    return None


def _extract_amount_after(text: str, pattern: str) -> float | None:
    match = re.search(pattern + r"[I|]?([\d,]+\.?\d*)", text, flags=re.IGNORECASE)
    if match:
        return parse_amount(match.group(1))
    return None


def _extract_bill_month(text: str) -> str | None:
    match = re.search(
        r"BILL\s*OF\s*SUPPLY\s*FOR\s*THE\s*MONTH\s*OF\s+([A-Za-z]+\s+\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        raw = match.group(1).strip()
        # Normalize "Jan 2024" -> "JAN-2024"
        parts = raw.split()
        if len(parts) == 2:
            return f"{parts[0][:3].upper()}-{parts[1]}"
        return raw.upper()
    return None


def _normalize_date(date_str: str | None) -> str | None:
    """Convert DD-MM-YYYY to DD-MMM-YYYY format."""
    if date_str is None:
        return None
    # Try DD-MM-YYYY first
    result = parse_date(date_str)
    if result:
        return result
    # Return as-is if it's already in some recognizable format
    return date_str


def _extract_billing_history(text: str) -> list[dict[str, str | float | None]]:
    """Extract billing history table entries."""
    history: list[dict[str, str | float | None]] = []
    # Pattern: month_name year \n units \n demand \n amount
    pattern = re.compile(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\s*\n\s*([\d,]+)\s*\n\s*(\d+)\s*\n\s*([\d,]+\.?\d*)",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        month = f"{match.group(1).upper()}-{match.group(2)}"
        units = parse_amount(match.group(3))
        demand = parse_amount(match.group(4))
        amount = parse_amount(match.group(5))
        history.append({
            "month": month,
            "units": units,
            "demand": demand,
            "bill_amount": amount,
        })
    return history


def _extract_consumption(text: str) -> BillConsumption:
    """Extract consumption details from MSEDCL format."""
    # Look for KWH consumption value
    kwh_match = re.search(r"KConsumption\s*\n?\s*([\d,]+\.?\d*)", text, flags=re.IGNORECASE)
    billed_units = parse_amount(kwh_match.group(1)) if kwh_match else None

    # Look for Current and Previous reading dates and values
    current_match = re.search(r"ICurrent\s+\d{2}-\d{2}-\d{4}\s*\n?\s*([\d,]+\.?\d*)", text)
    previous_match = re.search(r"Previous\s+\d{2}-\d{2}-\d{4}\s*\n?\s*([\d,]+\.?\d*)", text)

    current_read = parse_amount(current_match.group(1)) if current_match else None
    previous_read = parse_amount(previous_match.group(1)) if previous_match else None

    return BillConsumption(
        billed_units_kwh=billed_units,
        previous_read=previous_read,
        current_read=current_read,
    )


def _extract_charges(text: str) -> dict[str, float | None]:
    """Extract charge breakdown from MSEDCL billing details."""
    charges: dict[str, float | None] = {}

    patterns = {
        "demand_charges": r"Demand\s*Charges\s*\n?\s*([\d,]+\.?\d*)",
        "wheeling_charge": r"Wheeling\s*Charge\s*\n?\s*[\d.]+\s*\n?\s*([\d,]+\.?\d*)",
        "energy_charges": r"Energy\s*Charges\s*_?\s*\n?\s*([\d,]+\.?\d*)",
        "electricity_duty": r"Electricity\s*Duty\s*\n?\s*[\d.]+\s*%?\s*\n?\s*([\d,]+\.?\d*)",
        "tod_tariff_ec": r"TOD\s*Tariff\s*EC\s*\n?\s*([\d,]+\.?\d*)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            charges[key] = parse_amount(match.group(1))

    return charges


def can_parse_msedcl(raw_text: str) -> bool:
    """Check if the text looks like an MSEDCL/LTIP bill."""
    indicators = [
        "MAHAVITARAN",
        "Maharashtra State Electricity",
        "MSEDCL",
        "LTIP BILL FORMAT",
        "mahadiscom",
        "BILL OF SUPPLY FOR THE MONTH",
    ]
    text_upper = raw_text.upper()
    return any(indicator.upper() in text_upper for indicator in indicators)
