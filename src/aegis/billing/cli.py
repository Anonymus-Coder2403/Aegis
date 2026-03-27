"""CLI entrypoint for the billing package."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from aegis.billing.answerer import answer_billing_question, ingest_bill, inspect_bill
from aegis.billing.config import BillingConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aegis-billing-rag")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--pdf", required=True)
    inspect_parser.add_argument("--store-dir", default=".billing_store")

    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument("--pdf", required=True)
    ingest_parser.add_argument("--store-dir", default=".billing_store")

    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("--question", required=True)
    query_parser.add_argument("--pdf", required=True)
    query_parser.add_argument("--store-dir", default=".billing_store")

    args = parser.parse_args(argv)
    config = BillingConfig(store_dir=Path(args.store_dir))

    if args.command == "inspect":
        bill = inspect_bill(args.pdf)
        print(json.dumps(asdict(bill), indent=2))
        return 0

    if args.command == "ingest":
        bill = ingest_bill(args.pdf, config)
        print(f"Ingested bill {bill.source_doc_id}")
        return 0

    if args.command == "query":
        answer = answer_billing_question(args.question, config, pdf_path=args.pdf)
        print(answer.answer_text)
        for key, value in answer.resolved_fields.items():
            print(f"{key}: {value}")
        return 0

    return 1
