"""Generate a weather recommendation via LiteLLM or deterministic fallback."""

from __future__ import annotations

import json

from aegis.core.config import AegisConfig
from aegis.weather.fetcher import WeatherData

_RAIN_THRESHOLD_MM = 0.1


def _deterministic_advice(weather: WeatherData) -> str:
    umbrella = "You should carry an umbrella." if weather.rain_3h >= _RAIN_THRESHOLD_MM else "No umbrella needed."
    return (
        f"It's {weather.temp_c:.1f}°C and {weather.description} in {weather.city}. "
        f"Humidity is {weather.humidity}%. {umbrella}"
    )


def advise_weather(weather: WeatherData, question: str, config: AegisConfig) -> str:
    """Return a conversational weather recommendation.

    Attempts LiteLLM → Gemini 2.5 Flash.  Falls back to a deterministic
    template if LiteLLM is unavailable or raises.
    """
    api_key = config.litellm_api_key
    if not api_key:
        return _deterministic_advice(weather)

    context = json.dumps(
        {
            "city": weather.city,
            "temp_c": weather.temp_c,
            "description": weather.description,
            "rain_3h_mm": weather.rain_3h,
            "humidity_pct": weather.humidity,
        }
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful weather advisor. "
                "Answer the user's question using ONLY the provided weather context. "
                "Do NOT add information not present in the context. "
                "Be concise (2-3 sentences)."
            ),
        },
        {
            "role": "user",
            "content": f"Weather context: {context}\n\nQuestion: {question}",
        },
    ]

    try:
        import litellm  # type: ignore
        litellm.suppress_debug_info = True

        response = litellm.completion(
            model=config.litellm_model,
            messages=messages,
            api_key=api_key,
            base_url=config.litellm_base_url,
            temperature=0,
            max_tokens=300,
        )
        return str(response.choices[0].message.content).strip()
    except Exception:
        return _deterministic_advice(weather)
