"""Tests for aegis.orchestrator routing logic."""

from __future__ import annotations

import json
import types
from pathlib import Path

import pytest

from aegis.core.config import AegisConfig
from aegis.core.orchestrator import route_and_answer, _matches_keywords, _WEATHER_KEYWORDS, _AC_KEYWORDS, _BILL_KEYWORDS


# ---------------------------------------------------------------------------
# Keyword matching helpers
# ---------------------------------------------------------------------------

def test_weather_keyword_matched():
    assert _matches_keywords("Should I carry an umbrella today?", _WEATHER_KEYWORDS)


def test_ac_keyword_matched():
    assert _matches_keywords("It's really hot, turn on the AC", _AC_KEYWORDS)


def test_billing_keyword_matched():
    assert _matches_keywords("What is my bill due date?", _BILL_KEYWORDS)


def test_unrelated_keyword_not_matched():
    assert not _matches_keywords("Tell me a joke", _WEATHER_KEYWORDS)


# ---------------------------------------------------------------------------
# Weather routing
# ---------------------------------------------------------------------------

def test_routes_to_weather(monkeypatch, tmp_path):
    mock_json = tmp_path / "mock.json"
    mock_json.write_text(json.dumps({
        "name": "Delhi",
        "main": {"temp": 30.0, "humidity": 55},
        "weather": [{"description": "sunny"}],
    }))
    config = AegisConfig(weather_mock_path=mock_json)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENWEATHERMAP_API_KEY", raising=False)

    result = route_and_answer("Should I take an umbrella today?", config, city="Delhi")
    assert isinstance(result, str)
    assert len(result) > 0
    assert "30.0°C" in result or "sunny" in result


# ---------------------------------------------------------------------------
# AC routing
# ---------------------------------------------------------------------------

def test_routes_to_ac_no_server(monkeypatch, tmp_path):
    import httpx

    mock_json = tmp_path / "mock.json"
    mock_json.write_text(json.dumps({
        "name": "Delhi",
        "main": {"temp": 35.0, "humidity": 60},
        "weather": [{"description": "hot"}],
    }))
    config = AegisConfig(weather_mock_path=mock_json)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def _refuse(url, **kwargs):
        raise httpx.ConnectError("no server")

    monkeypatch.setattr(httpx, "post", _refuse)

    result = route_and_answer("It's getting really hot in here", config)
    # Should acknowledge AC intent even if server is down
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Billing routing
# ---------------------------------------------------------------------------

def test_billing_requires_pdf_path(monkeypatch, tmp_path):
    mock_json = tmp_path / "mock.json"
    mock_json.write_text(json.dumps({
        "name": "Delhi",
        "main": {"temp": 30.0, "humidity": 55},
        "weather": [{"description": "clear"}],
    }))
    config = AegisConfig(weather_mock_path=mock_json)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = route_and_answer("What is my electricity bill amount?", config, pdf_path=None)
    assert "PDF" in result or "pdf" in result.lower()


# ---------------------------------------------------------------------------
# Ambiguous / unknown routing
# ---------------------------------------------------------------------------

def test_unknown_input_returns_helpful_message(monkeypatch, tmp_path):
    mock_json = tmp_path / "mock.json"
    mock_json.write_text(json.dumps({
        "name": "Delhi",
        "main": {"temp": 30.0, "humidity": 55},
        "weather": [{"description": "clear"}],
    }))
    config = AegisConfig(weather_mock_path=mock_json)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = route_and_answer("Tell me a funny story", config)
    assert isinstance(result, str)
    assert len(result) > 0
