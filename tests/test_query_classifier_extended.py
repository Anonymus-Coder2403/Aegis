"""Tests for expanded query classifier — all canonical fields (Fix #9)."""

from aegis.billing.query_classifier import classify_billing_query


# --- bill_id ---

def test_classifies_bill_number_question():
    intent = classify_billing_query("What is my bill number?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["bill_id"]


def test_classifies_bill_no_question():
    intent = classify_billing_query("Tell me the bill no.")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["bill_id"]


# --- account_no ---

def test_classifies_account_number_question():
    intent = classify_billing_query("What is my account number?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["account_no"]


def test_classifies_consumer_number_question():
    intent = classify_billing_query("Tell me the consumer number on this bill.")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["account_no"]


# --- bill_month ---

def test_classifies_bill_month_question():
    intent = classify_billing_query("Which bill month is this for?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["bill_month"]


def test_classifies_billing_period_question():
    intent = classify_billing_query("What is the billing period?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["bill_month"]


# --- bill_date ---

def test_classifies_bill_date_question():
    intent = classify_billing_query("What is the bill date?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["bill_date"]


# --- disconnection_date ---

def test_classifies_disconnection_question():
    intent = classify_billing_query("When is the disconnection date?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["disconnection_date"]


def test_classifies_supply_cut_question():
    intent = classify_billing_query("When will supply cut happen?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["disconnection_date"]


# --- amounts.current_payable ---

def test_classifies_how_much_owe():
    intent = classify_billing_query("How much do I owe on my bill?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["amounts.current_payable"]


def test_classifies_total_amount():
    intent = classify_billing_query("What is the total amount on my bill?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["amounts.current_payable"]


def test_classifies_current_payable():
    intent = classify_billing_query("Show me the current payable amount.")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["amounts.current_payable"]


def test_how_much_with_last_routes_to_last_payment():
    """'how much was the last payment' should NOT route to current_payable."""
    intent = classify_billing_query("How much was the last bill paid for?")
    assert intent.query_type == "exact_field_lookup"
    assert "amounts.last_payment_amount" in intent.field_paths


# --- amounts.payable_by_due_date ---

def test_classifies_pay_by_question():
    intent = classify_billing_query("What should I pay by the due date?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["amounts.payable_by_due_date"]


def test_classifies_if_paid_question():
    intent = classify_billing_query("What is the amount if paid on time?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["amounts.payable_by_due_date"]


def test_classifies_payable_by_due_phrase():
    intent = classify_billing_query("Show the amount payable by due date.")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["amounts.payable_by_due_date"]


# --- amounts.total_payable_rounded ---

def test_classifies_total_payable_question():
    intent = classify_billing_query("What is the total payable amount?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["amounts.total_payable_rounded"]


# --- amounts.arrears_total ---

def test_classifies_arrears_question():
    intent = classify_billing_query("Do I have any arrears on my bill?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["amounts.arrears_total"]


def test_classifies_outstanding_question():
    intent = classify_billing_query("What is the outstanding amount?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["amounts.arrears_total"]


def test_classifies_overdue_question():
    intent = classify_billing_query("Is there any overdue balance?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["amounts.arrears_total"]


# --- amounts.last_receipt_no ---

def test_classifies_receipt_number_question():
    intent = classify_billing_query("What is the receipt number?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["amounts.last_receipt_no"]


def test_classifies_last_receipt_combo():
    intent = classify_billing_query("Show me the last receipt details.")
    assert intent.query_type == "exact_field_lookup"
    assert "amounts.last_receipt_no" in intent.field_paths


# --- Existing rules still work ---

def test_existing_last_paid_still_works():
    intent = classify_billing_query(
        "When was my last electricity bill paid, and what was the amount?"
    )
    assert intent.query_type == "exact_field_lookup"
    assert "amounts.last_payment_date" in intent.field_paths
    assert "amounts.last_payment_amount" in intent.field_paths


def test_existing_due_date_still_works():
    intent = classify_billing_query("What is the due date?")
    assert intent.query_type == "exact_field_lookup"
    assert intent.field_paths == ["due_date"]


def test_existing_charge_breakdown_still_works():
    intent = classify_billing_query("Show my electricity duty and charges.")
    assert intent.query_type == "charge_breakdown_lookup"


def test_existing_history_still_works():
    intent = classify_billing_query("Show previous consumption history.")
    assert intent.query_type == "history_lookup"


def test_existing_insufficient_context_still_works():
    intent = classify_billing_query("bill?")
    assert intent.query_type == "insufficient_context"


def test_unmapped_question_falls_back():
    intent = classify_billing_query("What does this bill say about service quality?")
    assert intent.query_type == "document_fallback_lookup"
