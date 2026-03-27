from aegis.billing.query_classifier import classify_billing_query


def test_classifies_last_payment_question_as_exact_field_lookup():
    intent = classify_billing_query(
        "When was my last electricity bill paid, and what was the amount?"
    )

    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == [
        "amounts.last_payment_date",
        "amounts.last_payment_amount",
    ]
    assert intent.needs_semantic_fallback is False


def test_classifies_due_date_question():
    intent = classify_billing_query("What is the due date?")

    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["due_date"]


def test_classifies_rounded_payable_question():
    intent = classify_billing_query("What is the rounded payable amount?")

    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["amounts.total_payable_rounded"]


def test_falls_back_for_unmapped_question():
    intent = classify_billing_query("What does this bill say about service quality?")

    assert intent.query_type == "document_fallback_lookup"
    assert intent.needs_semantic_fallback is True


def test_classifies_charge_breakdown_question():
    intent = classify_billing_query("Show electricity duty and fixed charges for my bill.")

    assert intent.query_type == "charge_breakdown_lookup"
    assert "charges.electricity_duty" in intent.field_paths
    assert "charges.fixed_demand_charges" in intent.field_paths
    assert intent.needs_semantic_fallback is True


def test_classifies_history_question():
    intent = classify_billing_query("Show my previous consumption history.")

    assert intent.query_type == "history_lookup"
    assert "history" in intent.field_paths
    assert intent.needs_semantic_fallback is True


def test_classifies_insufficient_context_for_short_question():
    intent = classify_billing_query("bill?")

    assert intent.query_type == "insufficient_context"
    assert intent.needs_semantic_fallback is False
