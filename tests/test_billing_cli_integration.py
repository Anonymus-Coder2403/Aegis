from pathlib import Path

import pytest

from aegis.billing import cli


def test_inspect_command_prints_canonical_bill_json(
    monkeypatch, capsys, tmp_path: Path, sample_extracted_content, sample_pdf_path: Path
):
    monkeypatch.setattr(
        "aegis.billing.parser.extractors.extract_pdf_content",
        lambda _: sample_extracted_content,
    )

    exit_code = cli.main(
        ["inspect", "--pdf", str(sample_pdf_path), "--store-dir", str(tmp_path / "store")]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"bill_id": "132189891047"' in captured.out
    assert '"last_payment_amount": 2119.0' in captured.out


def test_ingest_command_persists_canonical_bill_artifact(
    monkeypatch, capsys, tmp_path: Path, sample_extracted_content, sample_pdf_path: Path
):
    monkeypatch.setattr(
        "aegis.billing.parser.extractors.extract_pdf_content",
        lambda _: sample_extracted_content,
    )
    monkeypatch.setattr(
        "aegis.billing.rag.store.embed_text",
        lambda _: [0.1, 0.2, 0.3],
    )

    store_dir = tmp_path / "store"
    exit_code = cli.main(["ingest", "--pdf", str(sample_pdf_path), "--store-dir", str(store_dir)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert (store_dir / "canonical" / "document_pdf.json").exists()
    assert "Ingested bill document_pdf" in captured.out


def test_query_command_returns_grounded_last_payment_answer(
    monkeypatch, capsys, tmp_path: Path, sample_extracted_content, sample_pdf_path: Path
):
    monkeypatch.setattr(
        "aegis.billing.parser.extractors.extract_pdf_content",
        lambda _: sample_extracted_content,
    )
    monkeypatch.setattr(
        "aegis.billing.rag.store.embed_text",
        lambda _: [0.1, 0.2, 0.3],
    )

    exit_code = cli.main(
        [
            "query",
            "--question",
            "When was my last electricity bill paid, and what was the amount?",
            "--pdf",
            str(sample_pdf_path),
            "--store-dir",
            str(tmp_path / "store"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "10-JAN-2020" in captured.out
    assert "2119.0" in captured.out
    assert "amounts.last_payment_amount" in captured.out


def test_query_command_requires_pdf_argument(tmp_path: Path):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(
            [
                "query",
                "--question",
                "When was my last electricity bill paid, and what was the amount?",
                "--store-dir",
                str(tmp_path / "store"),
            ]
        )

    assert exc_info.value.code == 2
