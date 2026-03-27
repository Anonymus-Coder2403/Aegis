"""Tests for aegis.weather.advisor."""

from __future__ import annotations

import types

import pytest

from aegis.core.config import AegisConfig
from aegis.weather.advisor import advise_weather, _deterministic_advice
from aegis.weather.fetcher import WeatherData


@pytest.fixture
def delhi_weather() -> WeatherData:
    return WeatherData(city="Delhi", temp_c=32.4, description="haze", rain_3h=0.0, humidity=58)


@pytest.fixture
def rainy_weather() -> WeatherData:
    return WeatherData(city="Mumbai", temp_c=27.0, description="light rain", rain_3h=0.5, humidity=85)


def test_deterministic_no_rain(delhi_weather):
    advice = _deterministic_advice(delhi_weather)
    assert "32.4°C" in advice
    assert "haze" in advice
    assert "No umbrella needed" in advice


def test_deterministic_with_rain(rainy_weather):
    advice = _deterministic_advice(rainy_weather)
    assert "carry an umbrella" in advice.lower()


def test_fallback_when_no_api_key(delhi_weather, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    config = AegisConfig()
    result = advise_weather(delhi_weather, "Should I carry an umbrella?", config)
    assert "32.4°C" in result
    assert "haze" in result


def test_litellm_called_with_api_key(delhi_weather, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = AegisConfig()

    class _FakeChoice:
        class message:
            content = "It's warm and hazy. No umbrella needed today."

    class _FakeResponse:
        choices = [_FakeChoice()]

    def _fake_completion(**kwargs):
        return _FakeResponse()

    monkeypatch.setitem(
        __import__("sys").modules,
        "litellm",
        types.SimpleNamespace(completion=_fake_completion),
    )

    result = advise_weather(delhi_weather, "Weather today?", config)
    assert "warm" in result.lower() or "hazy" in result.lower()


def test_litellm_failure_falls_back_to_deterministic(delhi_weather, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = AegisConfig()

    def _raise(**kwargs):
        raise RuntimeError("litellm down")

    monkeypatch.setitem(
        __import__("sys").modules,
        "litellm",
        types.SimpleNamespace(completion=_raise),
    )

    result = advise_weather(delhi_weather, "Is it safe to go out?", config)
    assert "32.4°C" in result


def test_recommendation_does_not_expose_raw_numbers_alone(delhi_weather, monkeypatch):
    """Returned string must be a sentence, not a bare number."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    config = AegisConfig()
    result = advise_weather(delhi_weather, "What's the weather like?", config)
    # Must contain at least one alphabetic word beyond the number
    assert any(c.isalpha() for c in result)
    assert len(result) > 10
