import types

from aegis.billing.config import BillingConfig
from aegis.billing.llm_formatter import format_grounded_answer


def test_exact_lookup_with_missing_values_returns_not_found(tmp_path):
    result = format_grounded_answer(
        question="What is my due date?",
        query_type="exact_field_lookup",
        resolved_fields={"due_date": None},
        evidence={},
        snippets=[],
        config=BillingConfig(store_dir=tmp_path),
    )

    assert result == "I could not find that in the bill documents."


def test_litellm_exception_falls_back_to_deterministic(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def _raise_completion(**kwargs):
        raise RuntimeError("litellm failed")

    monkeypatch.setitem(
        __import__("sys").modules,
        "litellm",
        types.SimpleNamespace(completion=_raise_completion),
    )

    result = format_grounded_answer(
        question="Show electricity duty.",
        query_type="charge_breakdown_lookup",
        resolved_fields={"charges.electricity_duty": 133.93},
        evidence={"charges.electricity_duty": "Electricity Duty 133.93"},
        snippets=[],
        config=BillingConfig(store_dir=tmp_path, litellm_enabled=True),
    )

    assert "Charge breakdown from your bill" in result
    assert "charges.electricity_duty: 133.93" in result


def test_exact_lookup_bypasses_litellm_even_when_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    called = {"value": False}

    def _should_not_be_called(**kwargs):
        called["value"] = True
        return {"choices": [{"message": {"content": "llm output"}}]}

    monkeypatch.setitem(
        __import__("sys").modules,
        "litellm",
        types.SimpleNamespace(completion=_should_not_be_called),
    )

    result = format_grounded_answer(
        question="When was last payment?",
        query_type="exact_field_lookup",
        resolved_fields={
            "amounts.last_payment_date": "10-JAN-2020",
            "amounts.last_payment_amount": 2119.0,
        },
        evidence={},
        snippets=[],
        config=BillingConfig(store_dir=tmp_path, litellm_enabled=True),
    )

    assert called["value"] is False
    assert "10-JAN-2020" in result
    assert "2119.0" in result


def test_charge_lookup_reaches_litellm_when_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    called = {"value": False}

    def _fake_completion(**kwargs):
        called["value"] = True
        return {"choices": [{"message": {"content": "LLM formatted charge answer"}}]}

    monkeypatch.setitem(
        __import__("sys").modules,
        "litellm",
        types.SimpleNamespace(completion=_fake_completion),
    )

    result = format_grounded_answer(
        question="Show electricity duty.",
        query_type="charge_breakdown_lookup",
        resolved_fields={"charges.electricity_duty": 133.93},
        evidence={"charges.electricity_duty": "Electricity Duty 133.93"},
        snippets=[],
        config=BillingConfig(store_dir=tmp_path, litellm_enabled=True),
    )

    assert called["value"] is True
    assert result == "LLM formatted charge answer"


def test_charge_lookup_deterministic_snippets_appended(tmp_path):
    result = format_grounded_answer(
        question="Show electricity duty.",
        query_type="charge_breakdown_lookup",
        resolved_fields={"charges.electricity_duty": 133.93},
        evidence={},
        snippets=[
            {"document": "Electricity Duty 133.93", "metadata": {}, "distance": 0.1},
            {"document": "Fuel surcharge: 45.00", "metadata": {}, "distance": 0.2},
            {"document": "Meter rent: 20.00", "metadata": {}, "distance": 0.3},
        ],
        config=BillingConfig(store_dir=tmp_path, litellm_enabled=False),
    )

    assert "Charge breakdown from your bill" in result
    assert "charges.electricity_duty: 133.93" in result
    # First snippet overlaps resolved value (contains "133.93"), should be skipped
    assert "Fuel surcharge: 45.00" in result
    assert "Additional details" in result
