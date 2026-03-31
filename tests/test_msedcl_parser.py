"""Tests for MSEDCL/LTIP bill parser — mirrors test_bill_schema_mapping.py pattern."""

from aegis.billing.parser.extractors import ExtractedBillContent
from aegis.billing.parser.msedcl_parser import can_parse_msedcl, parse_msedcl_bill


def _sample_msedcl_content() -> ExtractedBillContent:
    return ExtractedBillContent(
        source_path="msedcl_bill.pdf",
        raw_text=(
            "MAHARASHTRA STATE ELECTRICITY DISTRIBUTION CO. LTD.\n"
            "MAHAVITARAN\n"
            "LTIP BILL FORMAT\n"
            "BILL OF SUPPLY FOR THE MONTH OF January 2024\n"
            "123456789012 (Opted\n"
            "BILL DATE\n"
            "I15-01-2024\n"
            "1500.00\n"
            "DUE DATE\n"
            "I31-01-2024\n"
            "IF PAID UPTO\n"
            "I31-01-2024\n"
            "1450.00\n"
            "IF PAID AFTER\n"
            "I15-02-2024\n"
            "1550.00\n"
            "Last Receipt No. Date\n"
            "I10-12-2023\n"
            "Last Month Payment\n"
            "1200.00\n"
            "TOTAL CURRENT BILL\n"
            "1500.00\n"
            "Demand Charges\n"
            "200.00\n"
            "Wheeling Charge\n"
            "5.0\n"
            "150.00\n"
            "Energy Charges_\n"
            "800.00\n"
            "Electricity Duty\n"
            "6.0%\n"
            "90.00\n"
            "KConsumption\n"
            "350.00\n"
            "ICurrent 15-01-2024\n"
            "5200.00\n"
            "Previous 15-12-2023\n"
            "4850.00\n"
            "Jan 2024\n"
            "350\n"
            "5\n"
            "1500.00\n"
            "Dec 2023\n"
            "300\n"
            "4\n"
            "1200.00\n"
        ),
        pages_text=[],
        tables=[],
    )


def test_can_parse_msedcl_detects_mahavitaran():
    content = _sample_msedcl_content()
    assert can_parse_msedcl(content.raw_text) is True


def test_can_parse_msedcl_rejects_pvvnl():
    assert can_parse_msedcl("PVVNL Bill Due Date 24-JAN-2020") is False


def test_can_parse_msedcl_detects_mahadiscom():
    assert can_parse_msedcl("mahadiscom consumer bill") is True


def test_can_parse_msedcl_detects_bill_of_supply():
    assert can_parse_msedcl("BILL OF SUPPLY FOR THE MONTH of March") is True


def test_maps_bill_month():
    bill = parse_msedcl_bill(_sample_msedcl_content())
    assert bill.bill_month == "JAN-2024"


def test_maps_account_number():
    bill = parse_msedcl_bill(_sample_msedcl_content())
    assert bill.account_no == "123456789012"


def test_maps_amounts_correctly():
    bill = parse_msedcl_bill(_sample_msedcl_content())
    assert bill.amounts.current_payable == 1500.0
    assert bill.amounts.payable_by_due_date == 1450.0
    assert bill.amounts.total_payable_rounded == 1550.0


def test_maps_last_payment():
    bill = parse_msedcl_bill(_sample_msedcl_content())
    assert bill.amounts.last_payment_amount == 1200.0


def test_maps_consumption():
    bill = parse_msedcl_bill(_sample_msedcl_content())
    assert bill.consumption.billed_units_kwh == 350.0
    assert bill.consumption.current_read == 5200.0
    assert bill.consumption.previous_read == 4850.0


def test_maps_charges():
    bill = parse_msedcl_bill(_sample_msedcl_content())
    assert bill.charges.get("demand_charges") == 200.0
    assert bill.charges.get("energy_charges") == 800.0
    assert bill.charges.get("electricity_duty") == 90.0


def test_maps_history():
    bill = parse_msedcl_bill(_sample_msedcl_content())
    assert len(bill.history) >= 2
    assert bill.history[0]["month"] == "JAN-2024"
    assert bill.history[0]["units"] == 350.0
    assert bill.history[1]["month"] == "DEC-2023"


def test_maps_evidence_for_amounts():
    bill = parse_msedcl_bill(_sample_msedcl_content())
    assert "amounts.current_payable" in bill.evidence_map
    assert "amounts.payable_by_due_date" in bill.evidence_map
    assert "amounts.total_payable_rounded" in bill.evidence_map


def test_preserves_raw_text():
    bill = parse_msedcl_bill(_sample_msedcl_content())
    assert "MAHAVITARAN" in bill.raw_text
    assert bill.source_doc_id == "msedcl_bill"


def test_bill_id_is_none_for_msedcl():
    """MSEDCL format does not have a dedicated bill_id field."""
    bill = parse_msedcl_bill(_sample_msedcl_content())
    assert bill.bill_id is None
