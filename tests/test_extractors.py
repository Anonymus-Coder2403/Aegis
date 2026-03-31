"""Tests for PDF extraction — extract_pdf_content with real PDFs."""

from pathlib import Path

import pytest

from aegis.billing.parser.extractors import ExtractedBillContent, extract_pdf_content

_BILL_PDF = Path(__file__).resolve().parent.parent / "data" / "document_pdf.pdf"
_WATER_PDF = Path(__file__).resolve().parent.parent / "data" / "water-bill-pdf_compress.pdf"


@pytest.fixture
def bill_content() -> ExtractedBillContent:
    if not _BILL_PDF.exists():
        pytest.skip(f"Test PDF not found: {_BILL_PDF}")
    return extract_pdf_content(_BILL_PDF)


@pytest.fixture
def water_content() -> ExtractedBillContent:
    if not _WATER_PDF.exists():
        pytest.skip(f"Test PDF not found: {_WATER_PDF}")
    return extract_pdf_content(_WATER_PDF)


def test_returns_extracted_bill_content(bill_content: ExtractedBillContent):
    assert isinstance(bill_content, ExtractedBillContent)


def test_raw_text_is_nonempty(bill_content: ExtractedBillContent):
    assert len(bill_content.raw_text.strip()) > 0


def test_pages_text_is_list(bill_content: ExtractedBillContent):
    assert isinstance(bill_content.pages_text, list)
    assert len(bill_content.pages_text) >= 1


def test_tables_is_list(bill_content: ExtractedBillContent):
    assert isinstance(bill_content.tables, list)


def test_source_path_matches(bill_content: ExtractedBillContent):
    assert "document_pdf" in bill_content.source_path


def test_used_ocr_is_bool(bill_content: ExtractedBillContent):
    assert isinstance(bill_content.used_ocr, bool)


def test_water_bill_extracts_text(water_content: ExtractedBillContent):
    assert len(water_content.raw_text.strip()) > 0


def test_nonexistent_pdf_raises():
    with pytest.raises(Exception):
        extract_pdf_content("nonexistent_file_xyz.pdf")
