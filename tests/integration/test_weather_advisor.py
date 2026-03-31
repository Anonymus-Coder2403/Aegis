"""Integration tests for weather advisor (real LiteLLM API calls)."""

import os

import pytest

from aegis.core.config import AegisConfig
from aegis.weather.advisor import advise_weather
from aegis.weather.fetcher import WeatherData

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY"),
        reason="GEMINI_API_KEY not set",
    ),
]


@pytest.fixture
def mock_weather():
    return WeatherData(
        city="Delhi",
        temp_c=32.4,
        description="haze",
        rain_3h=0.0,
        humidity=58,
    )


def test_litellm_generates_weather_advice(
    aegis_config: AegisConfig, mock_weather: WeatherData
):
    result = advise_weather(mock_weather, "Should I carry an umbrella today?", aegis_config)
    assert isinstance(result, str)
    assert len(result) > 10


def test_litellm_weather_is_natural_language(
    aegis_config: AegisConfig, mock_weather: WeatherData
):
    result = advise_weather(mock_weather, "What's the weather like?", aegis_config)
    assert any(c.isalpha() for c in result)
    assert not result.strip().startswith("{")
    assert len(result) >= 20


def test_litellm_weather_references_context(
    aegis_config: AegisConfig, mock_weather: WeatherData
):
    result = advise_weather(mock_weather, "Is it humid outside?", aegis_config)
    result_lower = result.lower()
    assert any(
        term in result_lower for term in ["humid", "haze", "delhi", "32", "58"]
    ), f"Response did not reference weather context: {result}"
