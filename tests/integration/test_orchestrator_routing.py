"""Integration tests for LiteLLM routing in orchestrator (real API calls)."""

import os

import pytest

from aegis.core.config import AegisConfig
from aegis.core.orchestrator import _route_via_litellm

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY"),
        reason="GEMINI_API_KEY not set",
    ),
]


def test_litellm_routes_ambiguous_question(aegis_config: AegisConfig):
    result = _route_via_litellm("Should I bring a jacket today?", aegis_config)
    assert result in {"weather", "ac", "billing", "none"}


def test_litellm_routes_billing_question(aegis_config: AegisConfig):
    result = _route_via_litellm("Explain my electricity charges", aegis_config)
    assert result in {"weather", "ac", "billing", "none"}


def test_litellm_routing_returns_string(aegis_config: AegisConfig):
    result = _route_via_litellm("Tell me something random", aegis_config)
    assert isinstance(result, str)
    assert len(result) > 0
