"""Orchestrator: keyword-routes questions to weather / AC / billing handlers."""

from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Any

from aegis.core.config import AegisConfig

LOGGER = logging.getLogger(__name__)

_WEATHER_KEYWORDS = {"weather", "umbrella", "rain", "temperature", "temp", "humid", "forecast", "sunny", "cloudy"}
_AC_KEYWORDS = {"ac", "air condition", "air conditioning", "aircon", "hot", "cold", "cool", "warm", "stuffy", "freezing"}
_BILL_KEYWORDS = {"bill", "billing", "payment", "charge", "due", "payable", "electricity", "receipt", "amount"}


def _matches_keywords(text: str, keywords: set[str]) -> bool:
    lower = text.lower()
    # Check multi-word phrases first
    for kw in keywords:
        if " " in kw and kw in lower:
            return True
    words = set(re.findall(r"\w+", lower))
    return bool(words & keywords)


def _route_via_litellm(question: str, config: AegisConfig) -> str:
    """Use LiteLLM to classify ambiguous input into weather/ac/billing/none."""
    api_key = config.litellm_api_key
    if not api_key:
        return "none"
    messages = [
        {
            "role": "system",
            "content": (
                "Classify the user question into exactly one of: weather, ac, billing, none. "
                "Respond with ONLY the category word, nothing else."
            ),
        },
        {"role": "user", "content": question},
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
            max_tokens=10,
        )
        category = str(response.choices[0].message.content).strip().lower()
        if category in {"weather", "ac", "billing"}:
            return category
    except Exception:
        LOGGER.warning("LiteLLM routing classification failed", exc_info=True)
    return "none"


def route_and_answer(
    question: str,
    config: AegisConfig,
    pdf_path: str | Path | None = None,
    city: str | None = None,
) -> str:
    """Route *question* to the correct handler and return an answer string."""

    is_weather = _matches_keywords(question, _WEATHER_KEYWORDS)
    is_ac = _matches_keywords(question, _AC_KEYWORDS)
    is_bill = _matches_keywords(question, _BILL_KEYWORDS)

    # Resolve ambiguity: if exactly one keyword set matches, use it.
    # If multiple or none match, ask LiteLLM.
    matched = sum([is_weather, is_ac, is_bill])

    if matched == 0 or matched > 1:
        route = _route_via_litellm(question, config)
    elif is_weather:
        route = "weather"
    elif is_ac:
        route = "ac"
    else:
        route = "billing"

    if route == "weather":
        from aegis.weather.fetcher import fetch_weather
        from aegis.weather.advisor import advise_weather

        target_city = city or config.weather_default_city
        weather = fetch_weather(target_city, config)
        return advise_weather(weather, question, config)

    if route == "ac":
        from aegis.ac_control.classifier import classify_ac_intent
        from aegis.ac_control.client import execute_ac_command

        intent = classify_ac_intent(question, config)
        result = execute_ac_command(intent, config)
        return result.confirmation_text

    if route == "billing":
        if pdf_path is None:
            return "Billing questions require a PDF path. Please provide --pdf."
        from aegis.billing.answerer import answer_billing_question
        from aegis.billing.config import BillingConfig

        billing_config = BillingConfig(
            store_dir=Path(".billing_store"),
            litellm_enabled=bool(config.litellm_api_key),
            litellm_model=config.litellm_model,
            litellm_api_key_env=config.litellm_api_key_env,
            litellm_base_url=config.litellm_base_url,
        )
        answer = answer_billing_question(
            question=question,
            config=billing_config,
            pdf_path=str(pdf_path),
        )
        return answer.answer_text

    return "I could not determine what you are asking about. Please ask about weather, AC, or billing."


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aegis", description="Aegis smart home assistant")
    sub = parser.add_subparsers(dest="command")

    ask_parser = sub.add_parser("ask", help="Ask a question")
    ask_parser.add_argument("question", help="Natural language question")
    ask_parser.add_argument("--pdf", dest="pdf", default=None, help="PDF path for billing questions")
    ask_parser.add_argument("--city", dest="city", default=None, help="City name for weather questions")

    args = parser.parse_args(argv)

    if args.command != "ask":
        parser.print_help()
        return 1

    config = AegisConfig()
    answer = route_and_answer(
        question=args.question,
        config=config,
        pdf_path=args.pdf,
        city=args.city,
    )
    print(answer)
    return 0


if __name__ == "__main__":
    sys.exit(main_cli())
