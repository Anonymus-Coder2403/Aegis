"""Tests for aegis.ac_control.classifier."""

from __future__ import annotations

import json
import types

import pytest

from aegis.ac_control.classifier import classify_ac_intent, _keyword_fallback
from aegis.core.config import AegisConfig


def test_keyword_turn_on():
    assert _keyword_fallback("It's really hot in here") == "turn_on"


def test_keyword_turn_off():
    assert _keyword_fallback("It's too cold, please turn off") == "turn_off"


def test_keyword_none():
    assert _keyword_fallback("What time is it?") == "none"


def test_fallback_when_no_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    config = AegisConfig()
    result = classify_ac_intent("I'm sweating like crazy", config)
    assert result == "turn_on"


def test_litellm_returns_turn_on(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = AegisConfig()

    class _FakeChoice:
        class message:
            content = '{"intent": "turn_on"}'

    class _FakeResponse:
        choices = [_FakeChoice()]

    def _fake_completion(**kwargs):
        return _FakeResponse()

    monkeypatch.setitem(
        __import__("sys").modules,
        "litellm",
        types.SimpleNamespace(completion=_fake_completion),
    )

    result = classify_ac_intent("It's boiling hot", config)
    assert result == "turn_on"


def test_litellm_returns_turn_off(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = AegisConfig()

    class _FakeChoice:
        class message:
            content = '{"intent": "turn_off"}'

    class _FakeResponse:
        choices = [_FakeChoice()]

    monkeypatch.setitem(
        __import__("sys").modules,
        "litellm",
        types.SimpleNamespace(completion=lambda **kw: _FakeResponse()),
    )

    result = classify_ac_intent("Please stop the AC", config)
    assert result == "turn_off"


def test_malformed_json_falls_back_to_keyword(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = AegisConfig()

    class _FakeChoice:
        class message:
            content = "not valid json at all"

    class _FakeResponse:
        choices = [_FakeChoice()]

    monkeypatch.setitem(
        __import__("sys").modules,
        "litellm",
        types.SimpleNamespace(completion=lambda **kw: _FakeResponse()),
    )

    result = classify_ac_intent("I'm feeling warm", config)
    # keyword fallback: "warm" → turn_on
    assert result == "turn_on"


def test_invalid_intent_value_falls_back(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = AegisConfig()

    class _FakeChoice:
        class message:
            content = '{"intent": "explode"}'

    class _FakeResponse:
        choices = [_FakeChoice()]

    monkeypatch.setitem(
        __import__("sys").modules,
        "litellm",
        types.SimpleNamespace(completion=lambda **kw: _FakeResponse()),
    )

    result = classify_ac_intent("some random text", config)
    assert result in {"turn_on", "turn_off", "none"}


def test_litellm_exception_falls_back_to_keyword(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    config = AegisConfig()

    def _raise(**kwargs):
        raise RuntimeError("API error")

    monkeypatch.setitem(
        __import__("sys").modules,
        "litellm",
        types.SimpleNamespace(completion=_raise),
    )

    result = classify_ac_intent("It's very cold", config)
    assert result == "turn_off"
