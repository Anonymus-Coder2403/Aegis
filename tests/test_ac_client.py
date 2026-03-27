"""Tests for aegis.ac_control.client."""

from __future__ import annotations

import pytest
import httpx

from aegis.ac_control.client import execute_ac_command, ACActionResult
from aegis.core.config import AegisConfig


class _FakeResponse:
    def __init__(self, data: dict, status_code: int = 200):
        self._data = data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)  # type: ignore

    def json(self):
        return self._data


def test_intent_none_returns_no_action():
    config = AegisConfig()
    result = execute_ac_command("none", config)
    assert result.intent == "none"
    assert result.ac_on is None
    assert "No AC action" in result.confirmation_text


def test_turn_on_calls_correct_endpoint(monkeypatch):
    config = AegisConfig()
    captured = {}

    def _fake_post(url, **kwargs):
        captured["url"] = url
        return _FakeResponse({"ac_on": True})

    monkeypatch.setattr(httpx, "post", _fake_post)

    result = execute_ac_command("turn_on", config)
    assert "ac/on" in captured["url"]
    assert result.ac_on is True
    assert "on" in result.confirmation_text.lower()


def test_turn_off_calls_correct_endpoint(monkeypatch):
    config = AegisConfig()
    captured = {}

    def _fake_post(url, **kwargs):
        captured["url"] = url
        return _FakeResponse({"ac_on": False})

    monkeypatch.setattr(httpx, "post", _fake_post)

    result = execute_ac_command("turn_off", config)
    assert "ac/off" in captured["url"]
    assert result.ac_on is False
    assert "off" in result.confirmation_text.lower()


def test_server_connection_error_returns_graceful_message(monkeypatch):
    config = AegisConfig()

    def _raise(url, **kwargs):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "post", _raise)

    result = execute_ac_command("turn_on", config)
    assert result.ac_on is None
    assert "Could not reach" in result.confirmation_text


def test_result_is_frozen_dataclass():
    config = AegisConfig()
    result = execute_ac_command("none", config)
    with pytest.raises((AttributeError, TypeError)):
        result.intent = "turn_on"  # type: ignore
