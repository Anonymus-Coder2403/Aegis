from pathlib import Path

from aegis.ui.streamlit_app import save_uploaded_pdf


def test_save_uploaded_pdf_persists_bytes(tmp_path: Path):
    payload = b"%PDF-1.7 fake pdf bytes"
    saved_path = save_uploaded_pdf("bill.pdf", payload, tmp_path)

    assert saved_path.exists()
    assert saved_path.read_bytes() == payload


def test_save_uploaded_pdf_enforces_pdf_suffix(tmp_path: Path):
    saved_path = save_uploaded_pdf("uploaded_bill", b"data", tmp_path)

    assert saved_path.suffix == ".pdf"
