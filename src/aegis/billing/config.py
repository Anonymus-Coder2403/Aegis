"""Configuration helpers for the billing slice."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class BillingConfig:
    store_dir: Path
    litellm_enabled: bool = True
    litellm_model: str = "gemini/gemini-2.5-flash"
    litellm_api_key_env: str = "GEMINI_API_KEY"
    litellm_base_url: str | None = None

    @property
    def canonical_dir(self) -> Path:
        return self.store_dir / "canonical"

    @property
    def chroma_dir(self) -> Path:
        return self.store_dir / "chroma"

    @property
    def litellm_api_key(self) -> str | None:
        return os.getenv(self.litellm_api_key_env)
