from pathlib import Path

import pytest

from aegis.billing.parser.extractors import ExtractedBillContent


@pytest.fixture
def sample_extracted_content() -> ExtractedBillContent:
    return ExtractedBillContent(
        source_path="document_pdf.pdf",
        raw_text=(
            "Bill No: 132189891047\n"
            "Account No: 1321865000\n"
            "Bill Month: JAN-2020\n"
            "Bill Date: 17-JAN-2020\n"
            "Due Date: 24-JAN-2020\n"
            "Disconnection Date: 31-JAN-2020\n"
            "Current Payable 2837.58\n"
            "Rounded Payable 2837\n"
            "Payable by Due Date 2811\n"
            "Last Payment Amount 2119.00\n"
            "Last Payment Date 10-JAN-2020\n"
            "Receipt No 132186537483\n"
        ),
        pages_text=[],
        tables=[
            [
                ["Bill No", "132189891047"],
                ["Account No", "1321865000"],
                ["Bill Month", "JAN-2020"],
                ["Bill Date", "17-JAN-2020"],
                ["Due Date", "24-JAN-2020"],
                ["Disconnection Date", "31-JAN-2020"],
                ["Current Payable", "2837.58"],
                ["Rounded Payable", "2837"],
                ["Payable by Due Date", "2811"],
                ["Last Payment Amount", "2119.00"],
                ["Last Payment Date", "10-JAN-2020"],
                ["Receipt No", "132186537483"],
            ]
        ],
    )


@pytest.fixture
def sample_pdf_path(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "document_pdf.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")
    return pdf_path
