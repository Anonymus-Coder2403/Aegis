from aegis.billing.parser.normalize import clean_cell, parse_amount, parse_date


def test_parse_amount_strips_currency_and_commas():
    assert parse_amount("Rs. 2,837.58") == 2837.58


def test_parse_amount_returns_none_for_invalid_values():
    assert parse_amount("not-an-amount") is None


def test_parse_date_normalizes_supported_input():
    assert parse_date("10/01/2020") == "10-JAN-2020"


def test_clean_cell_trims_whitespace_and_empty_values():
    assert clean_cell("  Total Payable  ") == "Total Payable"
    assert clean_cell("   ") is None
