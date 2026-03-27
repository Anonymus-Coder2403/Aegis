"""Extraction models and helpers for bill parsing."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExtractedBillContent:
    source_path: str
    raw_text: str
    pages_text: list[str]
    tables: list[list[list[str | None]]]
    used_ocr: bool = False


def extract_pdf_content(pdf_path: str | Path) -> ExtractedBillContent:
    path = Path(pdf_path)

    import fitz
    import pdfplumber

    pages_text: list[str] = []
    with fitz.open(path) as document:
        for page in document:
            pages_text.append(page.get_text("text"))

    tables: list[list[list[str | None]]] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                tables.append(table)

    has_text = any(page.strip() for page in pages_text)

    if not has_text:
        pages_text, used_ocr = _ocr_extract(path)
    else:
        used_ocr = False

    return ExtractedBillContent(
        source_path=str(path),
        raw_text="\n".join(pages_text),
        pages_text=pages_text,
        tables=tables,
        used_ocr=used_ocr,
    )


def _ocr_extract(path: Path) -> tuple[list[str], bool]:
    """Fall back to EasyOCR for scanned/image-based PDFs."""
    try:
        import fitz
        import easyocr

        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        pages_text: list[str] = []

        with fitz.open(path) as document:
            for page in document:
                pix = page.get_pixmap(dpi=300)
                img_bytes = pix.tobytes("png")
                results = reader.readtext(img_bytes)
                text = "\n".join(r[1] for r in results)
                pages_text.append(text)

        return pages_text, True
    except ImportError:
        return [], False
    except Exception:
        return [], False
