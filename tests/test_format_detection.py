"""Tests for bill format detection — can_parse_pvvnl, can_parse_msedcl, _parse_bill (Fix #8)."""

import pytest

from aegis.billing.answerer import _parse_bill
from aegis.billing.parser.extractors import ExtractedBillContent
from aegis.billing.parser.msedcl_parser import can_parse_msedcl
from aegis.billing.parser.pvvnl_parser import can_parse_pvvnl


# --- can_parse_pvvnl ---

def test_pvvnl_detects_pvvnl_keyword():
    assert can_parse_pvvnl("PVVNL Consumer Bill") is True


def test_pvvnl_detects_paschimanchal():
    assert can_parse_pvvnl("Paschimanchal Vidyut Vitran Nigam") is True


def test_pvvnl_detects_puvvnl():
    assert can_parse_pvvnl("PUVVNL electricity statement") is True


def test_pvvnl_detects_dvvnl():
    assert can_parse_pvvnl("DVVNL Bill Due Date 15-JAN-2024") is True


def test_pvvnl_detects_mvvnl():
    assert can_parse_pvvnl("MVVNL Madhyanchal Vidyut Vitran") is True


def test_pvvnl_detects_bill_due_date_phrase():
    assert can_parse_pvvnl("Bill Due Date 20-FEB-2024") is True


def test_pvvnl_detects_current_payable_amount():
    assert can_parse_pvvnl("Current Payable Amount(`) 1234.00") is True


def test_pvvnl_detects_rounded_payable():
    assert can_parse_pvvnl("Rounded Payable 1234") is True


def test_pvvnl_case_insensitive():
    assert can_parse_pvvnl("pvvnl bill") is True


def test_pvvnl_rejects_msedcl():
    assert can_parse_pvvnl("MAHAVITARAN LTIP BILL") is False


def test_pvvnl_rejects_random_text():
    assert can_parse_pvvnl("Hello world this is a random document") is False


# --- can_parse_msedcl ---

def test_msedcl_detects_mahavitaran():
    assert can_parse_msedcl("MAHAVITARAN LTIP bill") is True


def test_msedcl_detects_mahadiscom():
    assert can_parse_msedcl("mahadiscom consumer bill") is True


def test_msedcl_detects_bill_of_supply():
    assert can_parse_msedcl("BILL OF SUPPLY FOR THE MONTH of March") is True


def test_msedcl_rejects_pvvnl():
    assert can_parse_msedcl("PVVNL Bill Due Date 24-JAN-2020") is False


def test_msedcl_rejects_random_text():
    assert can_parse_msedcl("Some random document text") is False


# --- _parse_bill raises ValueError for unsupported formats ---

def test_parse_bill_raises_for_unsupported_format():
    content = ExtractedBillContent(
        source_path="water_bill.pdf",
        raw_text="Municipal Water Supply Board - Water Bill - Amount Due: 500",
        pages_text=[],
        tables=[],
    )
    with pytest.raises(ValueError, match="Unsupported bill format"):
        _parse_bill(content)


def test_parse_bill_raises_for_empty_text():
    content = ExtractedBillContent(
        source_path="blank.pdf",
        raw_text="",
        pages_text=[],
        tables=[],
    )
    with pytest.raises(ValueError, match="Unsupported bill format"):
        _parse_bill(content)


def test_parse_bill_accepts_pvvnl():
    """Smoke test: PVVNL content doesn't raise (may not parse perfectly with minimal text)."""
    content = ExtractedBillContent(
        source_path="pvvnl_test.pdf",
        raw_text="PVVNL Bill Due Date 15-JAN-2024 Current Payable Amount(`) 1000",
        pages_text=[],
        tables=[],
    )
    bill = _parse_bill(content)
    assert bill.source_doc_id == "pvvnl_test"


def test_parse_bill_accepts_msedcl():
    """Smoke test: MSEDCL content doesn't raise."""
    content = ExtractedBillContent(
        source_path="msedcl_test.pdf",
        raw_text="MAHAVITARAN BILL OF SUPPLY FOR THE MONTH OF January 2024",
        pages_text=[],
        tables=[],
    )
    bill = _parse_bill(content)
    assert bill.source_doc_id == "msedcl_test"
