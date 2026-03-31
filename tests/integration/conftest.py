"""Shared fixtures for integration tests — loads real .env and provides configs."""

from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

from aegis.core.config import AegisConfig


@pytest.fixture(scope="session")
def aegis_config():
    return AegisConfig()


@pytest.fixture(scope="session")
def pvvnl_pdf_path():
    path = Path(__file__).resolve().parent.parent.parent / "data" / "document_pdf.pdf"
    if not path.exists():
        pytest.skip(f"Test PDF not found: {path}")
    return path
