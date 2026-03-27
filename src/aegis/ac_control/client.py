"""httpx client that executes AC commands against the mock hardware server."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from aegis.core.config import AegisConfig


@dataclass(frozen=True)
class ACActionResult:
    intent: str
    ac_on: bool | None  # None when intent == "none"
    confirmation_text: str


def execute_ac_command(intent: str, config: AegisConfig) -> ACActionResult:
    """Send an AC on/off command and return an :class:`ACActionResult`.

    If *intent* is ``'none'``, no HTTP call is made.
    """
    if intent == "none":
        return ACActionResult(
            intent="none",
            ac_on=None,
            confirmation_text="No AC action needed.",
        )

    endpoint = "on" if intent == "turn_on" else "off"
    url = f"{config.ac_server_base_url}/ac/{endpoint}"

    try:
        resp = httpx.post(url, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        ac_on: bool = bool(data.get("ac_on", intent == "turn_on"))
        state_word = "on" if ac_on else "off"
        return ACActionResult(
            intent=intent,
            ac_on=ac_on,
            confirmation_text=f"AC is now {state_word}.",
        )
    except Exception as exc:
        return ACActionResult(
            intent=intent,
            ac_on=None,
            confirmation_text=f"Could not reach AC server: {exc}",
        )
