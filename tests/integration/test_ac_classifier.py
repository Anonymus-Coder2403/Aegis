"""Integration tests for AC intent classification (real LiteLLM API calls)."""

import os

import pytest

from aegis.ac_control.classifier import VALID_INTENTS, classify_ac_intent
from aegis.core.config import AegisConfig

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY"),
        reason="GEMINI_API_KEY not set",
    ),
]


def test_litellm_classifies_turn_on(aegis_config: AegisConfig):
    result = classify_ac_intent(
        "I'm absolutely boiling, it's unbearable in this room", aegis_config
    )
    assert result in VALID_INTENTS


def test_litellm_classifies_turn_off(aegis_config: AegisConfig):
    result = classify_ac_intent(
        "Please switch off the air conditioner, I'm freezing", aegis_config
    )
    assert result in VALID_INTENTS


def test_litellm_classifies_no_ac_intent(aegis_config: AegisConfig):
    result = classify_ac_intent("What's the capital of France?", aegis_config)
    assert result in VALID_INTENTS
