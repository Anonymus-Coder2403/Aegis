"""Normalization helpers for billing extraction."""

from __future__ import annotations

from datetime import datetime
import re


_AMOUNT_PATTERN = re.compile(r"[-+]?\d[\d,]*\.?\d*")
_DATE_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%d-%B-%Y")


def clean_cell(value: str | None) -> str | None:
    """Trim a table cell and collapse empty values to None."""
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def parse_amount(value: str | None) -> float | None:
    """Parse currency-like strings into floats."""
    cleaned = clean_cell(value)
    if cleaned is None:
        return None

    sanitized = cleaned.replace("Rs.", "").replace("₹", "").replace("INR", "")
    match = _AMOUNT_PATTERN.search(sanitized)
    if match is None:
        return None

    numeric = match.group(0).replace(",", "")
    try:
        return float(numeric)
    except ValueError:
        return None


def parse_date(value: str | None) -> str | None:
    """Normalize supported date formats into DD-MMM-YYYY."""
    cleaned = clean_cell(value)
    if cleaned is None:
        return None

    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, date_format).strftime("%d-%b-%Y").upper()
        except ValueError:
            continue
    return None
