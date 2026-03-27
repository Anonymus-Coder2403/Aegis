"""AegisConfig: top-level frozen config for all Aegis sub-systems."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class AegisConfig:
    litellm_model: str = "gemini/gemini-2.5-flash"
    litellm_api_key_env: str = "GEMINI_API_KEY"
    litellm_base_url: str | None = None
    weather_api_key_env: str = "OPENWEATHERMAP_API_KEY"
    weather_mock_path: Path = Path("data/weather_mock.json")
    weather_default_city: str = "Delhi"
    ac_server_host: str = "localhost"
    ac_server_port: int = 8765

    @property
    def litellm_api_key(self) -> str | None:
        return os.getenv(self.litellm_api_key_env)

    @property
    def weather_api_key(self) -> str | None:
        return os.getenv(self.weather_api_key_env)

    @property
    def ac_server_base_url(self) -> str:
        return f"http://{self.ac_server_host}:{self.ac_server_port}"
