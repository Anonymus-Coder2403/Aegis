"""Tests for aegis.weather.fetcher (OpenWeatherMap backend)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import httpx

from aegis.core.config import AegisConfig
from aegis.weather.fetcher import WeatherData, fetch_weather, _parse_owm, _load_mock


@pytest.fixture
def mock_json_path(tmp_path: Path) -> Path:
    data = {
        "name": "Delhi",
        "main": {"temp": 32.4, "humidity": 58},
        "weather": [{"description": "haze"}],
        "rain": {"3h": 0.5},
    }
    p = tmp_path / "weather_mock.json"
    p.write_text(json.dumps(data))
    return p


def _cfg(mock_path: Path) -> AegisConfig:
    return AegisConfig(weather_mock_path=mock_path)


# ---------------------------------------------------------------------------
# Parser unit tests
# ---------------------------------------------------------------------------

def test_parse_owm_basic(mock_json_path):
    with mock_json_path.open() as f:
        data = json.load(f)
    result = _parse_owm(data)
    assert result.city == "Delhi"
    assert result.temp_c == pytest.approx(32.4)
    assert result.rain_3h == pytest.approx(0.5)
    assert result.humidity == 58
    assert result.is_mock is False


def test_parse_owm_no_rain_key(tmp_path):
    data = {"name": "Pune", "main": {"temp": 25.0, "humidity": 60}, "weather": [{"description": "clear sky"}]}
    result = _parse_owm(data)
    assert result.rain_3h == 0.0


def test_load_mock_uses_requested_city(mock_json_path):
    result = _load_mock(mock_json_path, city="Manali")
    assert result.city == "Manali"
    assert result.is_mock is True


# ---------------------------------------------------------------------------
# Fallback behaviour
# ---------------------------------------------------------------------------

def test_fallback_when_no_api_key(monkeypatch, mock_json_path):
    monkeypatch.delenv("OPENWEATHERMAP_API_KEY", raising=False)
    config = _cfg(mock_json_path)
    result = fetch_weather("Begusarai", config)
    assert isinstance(result, WeatherData)
    assert result.city == "Begusarai"
    assert result.is_mock is True


def test_fallback_when_http_raises(monkeypatch, mock_json_path):
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "fake-key")
    config = _cfg(mock_json_path)

    def _raise(*args, **kwargs):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(httpx, "get", _raise)
    result = fetch_weather("Delhi", config)
    assert result.is_mock is True


def test_fallback_on_http_error_status(monkeypatch, mock_json_path):
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "fake-key")
    config = _cfg(mock_json_path)

    class _BadResp:
        def raise_for_status(self):
            raise httpx.HTTPStatusError("401", request=None, response=self)  # type: ignore
        def json(self):
            return {}

    monkeypatch.setattr(httpx, "get", lambda *a, **kw: _BadResp())
    result = fetch_weather("Delhi", config)
    assert result.is_mock is True


# ---------------------------------------------------------------------------
# Live API path (monkeypatched)
# ---------------------------------------------------------------------------

def test_live_api_parses_correctly(monkeypatch, mock_json_path):
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "fake-key")
    config = _cfg(mock_json_path)

    api_data = {
        "name": "Manali",
        "main": {"temp": 8.0, "humidity": 80},
        "weather": [{"description": "light snow"}],
        "rain": {"3h": 0.2},
    }

    class _FakeResp:
        def raise_for_status(self): pass
        def json(self): return api_data

    monkeypatch.setattr(httpx, "get", lambda *a, **kw: _FakeResp())

    result = fetch_weather("Manali", config)
    assert result.city == "Manali"
    assert result.temp_c == pytest.approx(8.0)
    assert result.rain_3h == pytest.approx(0.2)
    assert result.is_mock is False


def test_live_api_sends_correct_params(monkeypatch, mock_json_path):
    monkeypatch.setenv("OPENWEATHERMAP_API_KEY", "test-key-123")
    config = _cfg(mock_json_path)
    captured = {}

    class _FakeResp:
        def raise_for_status(self): pass
        def json(self): return {"name": "Begusarai", "main": {"temp": 35.0, "humidity": 70}, "weather": [{"description": "sunny"}]}

    def _fake_get(url, params, **kwargs):
        captured["url"] = url
        captured["params"] = params
        return _FakeResp()

    monkeypatch.setattr(httpx, "get", _fake_get)
    fetch_weather("Begusarai", config)

    assert "openweathermap.org" in captured["url"]
    assert captured["params"]["q"] == "Begusarai"
    assert captured["params"]["units"] == "metric"
    assert captured["params"]["appid"] == "test-key-123"
