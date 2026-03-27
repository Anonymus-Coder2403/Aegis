"""Fetch current weather data from OpenWeatherMap or fall back to mock."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import httpx

from aegis.core.config import AegisConfig

_OWM_URL = "https://api.openweathermap.org/data/2.5/weather"


@dataclass(frozen=True)
class WeatherData:
    city: str
    temp_c: float
    description: str
    rain_3h: float  # mm in last 3 hours; 0.0 if no rain
    humidity: int
    is_mock: bool = False  # True when live API was unavailable


def _parse_owm(data: dict, requested_city: str | None = None) -> WeatherData:
    city = data.get("name") or requested_city or "Unknown"
    temp_c = float(data["main"]["temp"])
    description = data["weather"][0]["description"] if data.get("weather") else "unknown"
    rain_3h = float(data.get("rain", {}).get("3h", 0.0))
    humidity = int(data["main"].get("humidity", 0))
    return WeatherData(city=city, temp_c=temp_c, description=description, rain_3h=rain_3h, humidity=humidity)


def _load_mock(mock_path: Path, city: str | None = None) -> WeatherData:
    with mock_path.open() as f:
        data = json.load(f)
    w = _parse_owm(data, requested_city=city)
    return WeatherData(
        city=city or w.city,
        temp_c=w.temp_c,
        description=w.description,
        rain_3h=w.rain_3h,
        humidity=w.humidity,
        is_mock=True,
    )


def fetch_weather(city: str, config: AegisConfig) -> WeatherData:
    """Return WeatherData for *city*.

    Uses OpenWeatherMap current-weather API if ``OPENWEATHERMAP_API_KEY`` is
    set.  Falls back to ``config.weather_mock_path`` if the key is absent or
    the call fails.
    """
    api_key = config.weather_api_key
    if not api_key:
        return _load_mock(config.weather_mock_path, city)

    try:
        resp = httpx.get(
            _OWM_URL,
            params={"q": city, "appid": api_key, "units": "metric"},
            timeout=10.0,
        )
        resp.raise_for_status()
        return _parse_owm(resp.json())
    except Exception:
        return _load_mock(config.weather_mock_path, city)
