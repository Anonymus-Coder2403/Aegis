from aegis.billing.parser.extractors import ExtractedBillContent
from aegis.billing.parser.pvvnl_parser import parse_pvvnl_bill


def _sample_extracted_content() -> ExtractedBillContent:
    return ExtractedBillContent(
        source_path="document_pdf.pdf",
        raw_text=(
            "Bill No: 132189891047\n"
            "Account No: 1321865000\n"
            "Bill Month: JAN-2020\n"
            "Bill Date: 17-JAN-2020\n"
            "Due Date: 24-JAN-2020\n"
            "Disconnection Date: 31-JAN-2020\n"
            "Current Payable 2837.58\n"
            "Rounded Payable 2837\n"
            "Payable by Due Date 2811\n"
            "Last Payment Amount 2119.00\n"
            "Last Payment Date 10-JAN-2020\n"
            "Receipt No 132186537483\n"
        ),
        pages_text=[],
        tables=[
            [
                ["Bill No", "132189891047"],
                ["Account No", "1321865000"],
                ["Bill Month", "JAN-2020"],
                ["Bill Date", "17-JAN-2020"],
                ["Due Date", "24-JAN-2020"],
                ["Disconnection Date", "31-JAN-2020"],
                ["Current Payable", "2837.58"],
                ["Rounded Payable", "2837"],
                ["Payable by Due Date", "2811"],
                ["Last Payment Amount", "2119.00"],
                ["Last Payment Date", "10-JAN-2020"],
                ["Receipt No", "132186537483"],
            ]
        ],
    )


def test_maps_key_bill_fields_from_extracted_content():
    bill = parse_pvvnl_bill(_sample_extracted_content())

    assert bill.bill_id == "132189891047"
    assert bill.account_no == "1321865000"
    assert bill.bill_month == "JAN-2020"
    assert bill.bill_date == "17-JAN-2020"
    assert bill.due_date == "24-JAN-2020"
    assert bill.disconnection_date == "31-JAN-2020"


def test_keeps_distinct_payable_fields_separate():
    bill = parse_pvvnl_bill(_sample_extracted_content())

    assert bill.amounts.current_payable == 2837.58
    assert bill.amounts.total_payable_rounded == 2837.0
    assert bill.amounts.payable_by_due_date == 2811.0


def test_maps_last_payment_fields_without_confusing_them_with_payable_fields():
    bill = parse_pvvnl_bill(_sample_extracted_content())

    assert bill.amounts.last_payment_amount == 2119.0
    assert bill.amounts.last_payment_date == "10-JAN-2020"
    assert bill.amounts.last_receipt_no == "132186537483"


def test_preserves_raw_text_and_evidence_map():
    bill = parse_pvvnl_bill(_sample_extracted_content())

    assert "Current Payable 2837.58" in bill.raw_text
    assert bill.evidence_map["amounts.last_payment_amount"] == "Last Payment Amount 2119.00"


def test_falls_back_to_raw_text_when_table_rows_are_not_structured():
    extracted = ExtractedBillContent(
        source_path="document_pdf.pdf",
        raw_text=(
            "Bill No : 132189891047\n"
            "Account No : 1321865000\n"
            "Bill Date : 17-JAN-2020\n"
            "Bill Month : JAN-2020\n"
            "Due Date 24-JAN-2020\n"
            "Disconnection Date 31-JAN-2020\n"
            "Current Payable Amount(`)\n2837.58\n"
            "Receipt No\n132186537483\n"
            "Receipt Date\n10-JAN-2020\n"
            "Payment Details\n2119.00\n"
            "Total Payable Amount(`)\n2837\n"
            "Total Amount Payable by due Date( ` )\n2811\n"
        ),
        pages_text=[],
        tables=[],
    )

    bill = parse_pvvnl_bill(extracted)

    assert bill.bill_id == "132189891047"
    assert bill.account_no == "1321865000"
    assert bill.amounts.current_payable == 2837.58
    assert bill.amounts.total_payable_rounded == 2837.0
    assert bill.amounts.payable_by_due_date == 2811.0
    assert bill.amounts.last_payment_amount == 2119.0
    assert bill.amounts.last_payment_date == "10-JAN-2020"
    assert bill.amounts.last_receipt_no == "132186537483"


def test_handles_multiline_realistic_payment_and_payable_sections():
    extracted = ExtractedBillContent(
        source_path="document_pdf.pdf",
        raw_text=(
            "Bill Due Date \n"
            "Disconnection Date\n"
            "24-JAN-2020\n"
            "31-JAN-2020\n"
            "Bill Month : JAN-2020\n"
            "Current Payable Amount(`)\n"
            "2238.50\n"
            "440.00\n"
            "0.00\n"
            "2837.58\n"
            "Installment Amount\n"
            "Receipt No\n"
            "Receipt Date\n"
            "2119.00\n"
            "132186537483\n"
            "10-JAN-2020\n"
            "Payment Details\n"
            "2119.00\n"
            "Total Payable \n"
            "Amount(`)\n"
            "2837\n"
            "Total Amount Payable by due Date( ` )\n"
            "2811\n"
        ),
        pages_text=[],
        tables=[],
    )

    bill = parse_pvvnl_bill(extracted)

    assert bill.bill_month == "JAN-2020"
    assert bill.disconnection_date == "31-JAN-2020"
    assert bill.amounts.current_payable == 2837.58
    assert bill.amounts.total_payable_rounded == 2837.0
    assert bill.amounts.last_receipt_no == "132186537483"
    assert bill.amounts.last_payment_date == "10-JAN-2020"


def test_parses_realistic_bill_month_and_arrears_details():
    extracted = ExtractedBillContent(
        source_path="document_pdf.pdf",
        raw_text=(
            "Bill Date : 17-JAN-2020\n"
            "Bill Month : JAN-2020\n"
            "Previous Consumption Pattern\n"
            "Bill Month   \n"
            "Units (KWH)\n"
            "Arrears\n"
            "Previous Late Pymnt Surcharge\n"
            "Miscellaneous Arrears\n"
            "Total\n"
            "0.00\n"
            "-0.21\n"
            "0.00\n"
            "-0.21\n"
        ),
        pages_text=[],
        tables=[],
    )

    bill = parse_pvvnl_bill(extracted)

    assert bill.bill_month == "JAN-2020"
    assert bill.amounts.arrears_total == -0.21


def test_parses_charge_breakdown_from_bill_details_section():
    extracted = ExtractedBillContent(
        source_path="document_pdf.pdf",
        raw_text=(
            "Bill Details( ` )\n"
            "Last Payment Status\n"
            "Electricity Charges\n"
            "Fixed/Demand Charges\n"
            "Rural/Dept Rebate\n"
            "Load Factor Rebate\n"
            "Power Loom Rebate\n"
            "Amount for Min Charges\n"
            "Dishonor  Cheque\n"
            "Solar Heater Rebate\n"
            "Fuel Surcharge\n"
            "LT Metering surcharge\n"
            "Surcharge exceeding Demand\n"
            "Capacitor Surcharge\n"
            "Current Bill LPSC\n"
            "Electricity Duty\n"
            "Regulatory Surcharge1\n"
            "Regulatory Surcharge2\n"
            "Maintenance Charges\n"
            "Provisional Adjustment\n"
            "Tariff Adjustments\n"
            "Debit\n"
            "Credit\n"
            "Current Payable Amount(`)\n"
            "2238.50\n"
            "440.00\n"
            "0.00\n"
            "0.00\n"
            "0.00\n"
            "0.00\n"
            "0.00\n"
            "0.00\n"
            "0.00\n"
            "0.00\n"
            "0.00\n"
            "0.00\n"
            "25.15\n"
            "133.93\n"
            "0.00\n"
            "0.00\n"
            "0.00\n"
            "0.00\n"
            "0.00\n"
            "0.00\n"
            "0.00\n"
            "2837.58\n"
        ),
        pages_text=[],
        tables=[],
    )

    bill = parse_pvvnl_bill(extracted)

    assert bill.charges["electricity_charges"] == 2238.50
    assert bill.charges["fixed_demand_charges"] == 440.00
    assert bill.charges["current_bill_lpsc"] == 25.15
    assert bill.charges["electricity_duty"] == 133.93


def test_parses_consumption_and_history_sections():
    extracted = ExtractedBillContent(
        source_path="document_pdf.pdf",
        raw_text=(
            "Previous\n"
            "Current\n"
            "Billed\n"
            "Units\n"
            "17-DEC-19\n"
            "12021\n"
            "17-JAN-20\n"
            "12400\n"
            "379\n"
            "Previous Consumption Pattern\n"
            "Bill Month   \n"
            "Units (KWH)\n"
            "Units \n"
            "(KVAH)\n"
            "Demand\n"
            "Status\n"
            "DEC-2019\n"
            "272\n"
            "4\n"
            "OK\n"
            "NOV-2019\n"
            "202\n"
            "4\n"
            "OK\n"
        ),
        pages_text=[],
        tables=[],
    )

    bill = parse_pvvnl_bill(extracted)

    assert bill.consumption.previous_read == 12021.0
    assert bill.consumption.current_read == 12400.0
    assert bill.consumption.billed_units_kwh == 379.0
    assert bill.history[0]["month"] == "DEC-2019"
    assert bill.history[0]["units"] == 272.0
    assert bill.history[0]["demand"] == 4.0
    assert bill.history[1]["month"] == "NOV-2019"


def test_current_payable_evidence_uses_final_payable_value_not_first_charge():
    extracted = ExtractedBillContent(
        source_path="document_pdf.pdf",
        raw_text=(
            "Current Payable Amount(`)\n"
            "2238.50\n"
            "440.00\n"
            "0.00\n"
            "2837.58\n"
            "Installment Amount\n"
        ),
        pages_text=[],
        tables=[],
    )

    bill = parse_pvvnl_bill(extracted)

    assert bill.evidence_map["amounts.current_payable"] == "Current Payable Amount(`) 2837.58"


def test_maps_evidence_for_receipt_and_arrears_fields():
    extracted = ExtractedBillContent(
        source_path="document_pdf.pdf",
        raw_text=(
            "Arrears\n"
            "Previous Late Pymnt Surcharge\n"
            "Miscellaneous Arrears\n"
            "Total\n"
            "0.00\n"
            "-0.21\n"
            "0.00\n"
            "-0.21\n"
            "Receipt No\n"
            "Receipt Date\n"
            "2119.00\n"
            "132186537483\n"
            "10-JAN-2020\n"
        ),
        pages_text=[],
        tables=[],
    )

    bill = parse_pvvnl_bill(extracted)

    assert bill.evidence_map["amounts.last_receipt_no"] == "Receipt No 132186537483"
    assert bill.evidence_map["amounts.last_payment_date"] == "Receipt Date 10-JAN-2020"
    assert bill.evidence_map["amounts.arrears_total"] == "Total -0.21"


def test_maps_evidence_for_selected_charge_fields():
    extracted = ExtractedBillContent(
        source_path="document_pdf.pdf",
        raw_text=(
            "Bill Details( ` )\n"
            "Last Payment Status\n"
            "Electricity Charges\n"
            "Fixed/Demand Charges\n"
            "Current Bill LPSC\n"
            "Electricity Duty\n"
            "Current Payable Amount(`)\n"
            "2238.50\n"
            "440.00\n"
            "25.15\n"
            "133.93\n"
            "2837.58\n"
        ),
        pages_text=[],
        tables=[],
    )

    bill = parse_pvvnl_bill(extracted)

    assert bill.evidence_map["charges.electricity_charges"] == "Electricity Charges 2238.50"
    assert bill.evidence_map["charges.fixed_demand_charges"] == "Fixed/Demand Charges 440.00"
    assert bill.evidence_map["charges.current_bill_lpsc"] == "Current Bill LPSC 25.15"
    assert bill.evidence_map["charges.electricity_duty"] == "Electricity Duty 133.93"
