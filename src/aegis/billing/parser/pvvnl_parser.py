"""Rule-based PVVNL bill parser."""

from __future__ import annotations

from pathlib import Path
import re

from aegis.billing.parser.extractors import ExtractedBillContent
from aegis.billing.parser.normalize import clean_cell, parse_amount, parse_date
from aegis.billing.types import BillAmounts, BillConsumption, CanonicalBill


def parse_pvvnl_bill(extracted: ExtractedBillContent) -> CanonicalBill:
    rows = _flatten_rows(extracted.tables)
    values = {label: clean_cell(value) for label, value in rows}
    raw_text = extracted.raw_text
    due_date_from_block, disconnection_date_from_block = _extract_due_and_disconnection_dates(raw_text)
    receipt_no_from_block, receipt_date_from_block = _extract_receipt_details(raw_text)
    current_payable_from_block = _extract_current_payable(raw_text)
    rounded_payable_from_block = _extract_total_payable(raw_text)
    arrears_total = _extract_arrears_total(raw_text)
    charges = _extract_charge_breakdown(raw_text)
    consumption = _extract_consumption(raw_text)
    history = _extract_history(raw_text)
    bill_month = _extract_bill_month(values.get("Bill Month"), raw_text)

    amounts = BillAmounts(
        current_payable=parse_amount(
            values.get("Current Payable")
            or current_payable_from_block
        ),
        total_payable_rounded=parse_amount(
            values.get("Rounded Payable")
            or rounded_payable_from_block
        ),
        payable_by_due_date=parse_amount(
            values.get("Payable by Due Date")
            or _search_pattern(raw_text, r"Total Amount Payable by due Date\(\s*`\s*\)\s+(\d[\d,]*\.?\d*)")
        ),
        last_payment_amount=parse_amount(
            values.get("Last Payment Amount")
            or _search_pattern(raw_text, r"Payment Details\s+(\d[\d,]*\.?\d*)")
        ),
        last_payment_date=parse_date(
            values.get("Last Payment Date")
            or receipt_date_from_block
        ),
        last_receipt_no=values.get("Receipt No") or receipt_no_from_block,
        arrears_total=parse_amount(arrears_total),
    )

    evidence_map = {
        "amounts.last_payment_amount": _build_evidence(
            rows,
            "Last Payment Amount",
        )
        or _search_pattern(raw_text, r"(Payment Details\s+\d[\d,]*\.?\d*)", group=1),
        "amounts.last_payment_date": _build_evidence(
            rows,
            "Last Payment Date",
        )
        or _search_pattern(raw_text, r"(Receipt Date\s+[0-9]{2}-[A-Z]{3}-[0-9]{4})", group=1)
        or _build_receipt_date_evidence(raw_text),
        "amounts.last_receipt_no": _build_evidence(
            rows,
            "Receipt No",
        )
        or _build_receipt_number_evidence(raw_text),
        "amounts.arrears_total": _build_arrears_total_evidence(raw_text),
        "amounts.current_payable": _build_evidence(
            rows,
            "Current Payable",
        )
        or _build_current_payable_evidence(raw_text),
    }
    evidence_map.update(_build_charge_evidence(raw_text))

    return CanonicalBill(
        source_doc_id=Path(extracted.source_path).stem,
        bill_id=values.get("Bill No") or _search_pattern(raw_text, r"Bill No\s*:\s*([0-9]{6,})"),
        account_no=values.get("Account No") or _search_pattern(raw_text, r"Account No\s*:\s*([0-9]{6,})"),
        bill_month=bill_month,
        bill_date=parse_date(values.get("Bill Date"))
        or values.get("Bill Date")
        or _search_pattern(raw_text, r"Bill Date\s*:\s*([0-9]{2}-[A-Z]{3}-[0-9]{2,4})"),
        due_date=parse_date(values.get("Due Date"))
        or values.get("Due Date")
        or due_date_from_block
        or _search_pattern(raw_text, r"Due Date\s+([0-9]{2}-[A-Z]{3}-[0-9]{4})"),
        disconnection_date=parse_date(values.get("Disconnection Date"))
        or values.get("Disconnection Date")
        or disconnection_date_from_block
        or _search_pattern(raw_text, r"Disconnection Date\s+([0-9]{2}-[A-Z]{3}-[0-9]{4})"),
        amounts=amounts,
        charges=charges,
        consumption=consumption,
        history=history,
        raw_text=extracted.raw_text,
        evidence_map={key: value for key, value in evidence_map.items() if value is not None},
    )


def _flatten_rows(tables: list[list[list[str | None]]]) -> list[tuple[str, str | None]]:
    rows: list[tuple[str, str | None]] = []
    for table in tables:
        for row in table:
            if len(row) < 2:
                continue
            label = clean_cell(row[0])
            if label is None:
                continue
            rows.append((label, row[1]))
    return rows


def _build_evidence(rows: list[tuple[str, str | None]], target_label: str) -> str | None:
    for label, value in rows:
        if label == target_label:
            cleaned = clean_cell(value)
            if cleaned is None:
                return label
            return f"{label} {cleaned}"
    return None


def _search_pattern(raw_text: str, pattern: str, group: int = 1) -> str | None:
    match = re.search(pattern, raw_text, flags=re.IGNORECASE)
    if match is None:
        return None
    return clean_cell(match.group(group))


def _extract_due_and_disconnection_dates(raw_text: str) -> tuple[str | None, str | None]:
    match = re.search(
        r"Bill Due Date\s+Disconnection Date\s+([0-9]{2}-[A-Z]{3}-[0-9]{4})\s+([0-9]{2}-[A-Z]{3}-[0-9]{4})",
        raw_text,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None, None
    return clean_cell(match.group(1)), clean_cell(match.group(2))


def _extract_receipt_details(raw_text: str) -> tuple[str | None, str | None]:
    match = re.search(
        r"Receipt No\s+Receipt Date\s+\d[\d,]*\.?\d*\s+([0-9]{6,})\s+([0-9]{2}-[A-Z]{3}-[0-9]{4})",
        raw_text,
        flags=re.IGNORECASE,
    )
    if match is not None:
        return clean_cell(match.group(1)), clean_cell(match.group(2))

    simple_receipt = _search_pattern(raw_text, r"Receipt No\s+([0-9]{6,})")
    simple_date = _search_pattern(raw_text, r"Receipt Date\s+([0-9]{2}-[A-Z]{3}-[0-9]{4})")
    return simple_receipt, simple_date


def _extract_current_payable(raw_text: str) -> str | None:
    match = re.search(
        r"Current Payable Amount\(`\)\s+(.+?)\s+Installment Amount",
        raw_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return _search_pattern(raw_text, r"Current Payable Amount\(`\)\s+(\d[\d,]*\.?\d*)")
    values = re.findall(r"\d[\d,]*\.?\d*", match.group(1))
    if not values:
        return _search_pattern(raw_text, r"Current Payable Amount\(`\)\s+(\d[\d,]*\.?\d*)")
    return values[-1]


def _extract_total_payable(raw_text: str) -> str | None:
    match = re.search(
        r"Total Payable\s+Amount\(`\)\s+(.+?)\s+Total Amount Payable by due Date",
        raw_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return None
    values = re.findall(r"\d[\d,]*\.?\d*", match.group(1))
    if not values:
        return None
    return clean_cell(values[0])


def _extract_arrears_total(raw_text: str) -> str | None:
    match = re.search(
        r"Arrears\s+Previous Late Pymnt Surcharge\s+Miscellaneous Arrears\s+Total\s+([-\d.,]+)\s+([-\d.,]+)\s+([-\d.,]+)\s+([-\d.,]+)",
        raw_text,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    return clean_cell(match.group(4))


def _extract_charge_breakdown(raw_text: str) -> dict[str, float | None]:
    match = re.search(
        r"Bill Details\(\s*`\s*\)\s+Bill Details\(\s*`\s*\)\s+Last Payment Status\s+(.+?)\s+Current Payable Amount\(`\)\s+(.+?)\s+Installment Amount",
        raw_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        match = re.search(
            r"Bill Details\(\s*`\s*\)\s+Last Payment Status\s+(.+?)\s+Current Payable Amount\(`\)\s+(.+?)(?:\s+Installment Amount|$)",
            raw_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
    if match is None:
        return {}

    labels_block = match.group(1)
    values_block = match.group(2)
    labels = [
        clean_cell(line)
        for line in labels_block.splitlines()
        if clean_cell(line) is not None
    ]
    values = re.findall(r"[-+]?\d[\d,]*\.?\d*", values_block)
    if not labels or not values:
        return {}

    label_to_key = {
        "Electricity Charges": "electricity_charges",
        "Fixed/Demand Charges": "fixed_demand_charges",
        "Current Bill LPSC": "current_bill_lpsc",
        "Electricity Duty": "electricity_duty",
    }

    parsed: dict[str, float | None] = {}
    for label, value in zip(labels, values, strict=False):
        key = label_to_key.get(label)
        if key is None:
            continue
        parsed[key] = parse_amount(value)
    return parsed


def _extract_consumption(raw_text: str) -> BillConsumption:
    match = re.search(
        r"([0-9]{2}-[A-Z]{3}-[0-9]{2})\s+(\d+)\s+([0-9]{2}-[A-Z]{3}-[0-9]{2})\s+(\d+)\s+(\d+)",
        raw_text,
        flags=re.IGNORECASE,
    )
    if match is None:
        return BillConsumption()
    return BillConsumption(
        previous_read=parse_amount(match.group(2)),
        current_read=parse_amount(match.group(4)),
        billed_units_kwh=parse_amount(match.group(5)),
    )


def _extract_history(raw_text: str) -> list[dict[str, str | float | None]]:
    match = re.search(
        r"Previous Consumption Pattern\s+Bill Month\s+Units \(KWH\)\s+Units\s+\(KVAH\)\s+Demand\s+Status\s+(.+?)(?:Energy Saved Is Energy Produced\.|Note: If the Bill is not paid|$)",
        raw_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return []

    lines = [clean_cell(line) for line in match.group(1).splitlines()]
    tokens = [line for line in lines if line is not None]
    history: list[dict[str, str | float | None]] = []
    index = 0
    while index + 3 < len(tokens):
        month = tokens[index]
        if not re.fullmatch(r"[A-Z]{3}-[0-9]{4}", month):
            index += 1
            continue
        units = parse_amount(tokens[index + 1])
        demand = parse_amount(tokens[index + 2])
        status = tokens[index + 3]
        history.append(
            {
                "month": month,
                "units": units,
                "demand": demand,
                "status": status,
            }
        )
        index += 4
    return history


def _build_current_payable_evidence(raw_text: str) -> str | None:
    value = _extract_current_payable(raw_text)
    if value is None:
        return None
    return f"Current Payable Amount(`) {value}"


def _extract_bill_month(table_value: str | None, raw_text: str) -> str | None:
    if table_value is not None and re.fullmatch(r"[A-Z]{3}-[0-9]{4}", table_value):
        return table_value
    return _search_pattern(raw_text, r"Bill Month\s*:\s*([A-Z]{3}-[0-9]{4})")


def _build_receipt_number_evidence(raw_text: str) -> str | None:
    receipt_no, _ = _extract_receipt_details(raw_text)
    if receipt_no is None:
        return None
    return f"Receipt No {receipt_no}"


def _build_receipt_date_evidence(raw_text: str) -> str | None:
    _, receipt_date = _extract_receipt_details(raw_text)
    if receipt_date is None:
        return None
    return f"Receipt Date {receipt_date}"


def _build_arrears_total_evidence(raw_text: str) -> str | None:
    arrears_total = _extract_arrears_total(raw_text)
    if arrears_total is None:
        return None
    return f"Total {arrears_total}"


def _build_charge_evidence(raw_text: str) -> dict[str, str]:
    match = re.search(
        r"Bill Details\(\s*`\s*\)\s+Bill Details\(\s*`\s*\)\s+Last Payment Status\s+(.+?)\s+Current Payable Amount\(`\)\s+(.+?)(?:\s+Installment Amount|$)",
        raw_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        match = re.search(
            r"Bill Details\(\s*`\s*\)\s+Last Payment Status\s+(.+?)\s+Current Payable Amount\(`\)\s+(.+?)(?:\s+Installment Amount|$)",
            raw_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
    if match is None:
        return {}

    labels = [
        clean_cell(line)
        for line in match.group(1).splitlines()
        if clean_cell(line) is not None
    ]
    values = re.findall(r"[-+]?\d[\d,]*\.?\d*", match.group(2))
    label_to_key = {
        "Electricity Charges": "charges.electricity_charges",
        "Fixed/Demand Charges": "charges.fixed_demand_charges",
        "Current Bill LPSC": "charges.current_bill_lpsc",
        "Electricity Duty": "charges.electricity_duty",
    }

    evidence: dict[str, str] = {}
    for label, value in zip(labels, values, strict=False):
        key = label_to_key.get(label)
        if key is None:
            continue
        evidence[key] = f"{label} {clean_cell(value)}"
    return evidence
