"""Classify user intent for AC control via LiteLLM or keyword fallback."""

from __future__ import annotations

import json
import re

from aegis.core.config import AegisConfig

_TURN_ON_KEYWORDS = {"hot", "warm", "stuffy", "humid", "sweating", "heat"}
_TURN_OFF_KEYWORDS = {"cold", "cool", "freezing", "chilly", "off", "stop", "turn off"}

VALID_INTENTS = {"turn_on", "turn_off", "none"}

_SYSTEM_PROMPT = (
    "You are an AC intent classifier. "
    "Given a user message, respond with ONLY valid JSON in this exact format: "
    '{"intent": "turn_on"} or {"intent": "turn_off"} or {"intent": "none"}. '
    "turn_on: user wants AC on (hot, warm, uncomfortable). "
    "turn_off: user wants AC off (cold, cool, done). "
    "none: no clear AC intent. No other text."
)


def _keyword_fallback(text: str) -> str:
    lower = text.lower()
    words = set(re.findall(r"\w+", lower))
    on_score = len(words & _TURN_ON_KEYWORDS)
    off_score = len(words & _TURN_OFF_KEYWORDS)
    # Explicit off/stop signals win on ties — ambient conditions (hot/warm)
    # should not override direct commands (off/stop/turn off).
    if off_score >= on_score and off_score > 0:
        return "turn_off"
    if on_score > 0:
        return "turn_on"
    return "none"


def classify_ac_intent(text: str, config: AegisConfig) -> str:
    """Return ``'turn_on'``, ``'turn_off'``, or ``'none'``.

    Tries LiteLLM → Gemini 2.5 Flash first; falls back to keyword matching if
    LiteLLM is unavailable, raises, or returns malformed JSON.
    """
    api_key = config.litellm_api_key
    if not api_key:
        return _keyword_fallback(text)

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": text},
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
            max_tokens=50,
        )
        raw = str(response.choices[0].message.content).strip()
        parsed = json.loads(raw)
        intent = parsed.get("intent", "none")
        if intent not in VALID_INTENTS:
            return _keyword_fallback(text)
        return intent
    except Exception:
        return _keyword_fallback(text)
