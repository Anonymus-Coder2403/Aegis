"""Grounded answer formatting with optional LiteLLM."""

from __future__ import annotations

import json
from typing import Any

from aegis.billing.config import BillingConfig


def format_grounded_answer(
    question: str,
    query_type: str,
    resolved_fields: dict[str, Any],
    evidence: dict[str, str],
    snippets: list[dict[str, Any]],
    config: BillingConfig,
) -> str:
    deterministic = _format_deterministic(
        query_type=query_type,
        resolved_fields=resolved_fields,
        evidence=evidence,
        snippets=snippets,
    )

    # Exact field lookups always stay deterministic — schema values are authoritative.
    if query_type == "exact_field_lookup":
        return deterministic

    if not config.litellm_enabled:
        return deterministic
    if not config.litellm_api_key:
        return deterministic

    try:
        import litellm
        litellm.suppress_debug_info = True
        from litellm import completion

        system_prompt = (
            "You are a strict billing assistant. "
            "PRIORITY: resolved_fields contain authoritative schema values — always use them as-is. "
            "Snippets provide supplementary context only. "
            "Never invent values. If context is missing, say it clearly."
        )
        user_prompt = json.dumps(
            {
                "question": question,
                "query_type": query_type,
                "resolved_fields": resolved_fields,
                "evidence": evidence,
                "snippets": snippets,
            },
            ensure_ascii=False,
        )

        response = completion(
            model=config.litellm_model,
            api_key=config.litellm_api_key,
            base_url=config.litellm_base_url,
            temperature=0,
            max_tokens=500,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response["choices"][0]["message"]["content"]
        return content.strip() if content else deterministic
    except Exception:
        return deterministic


def _extract_snippet_extras(
    snippets: list[dict[str, Any]],
    resolved_fields: dict[str, Any],
) -> list[str]:
    """Return snippet documents not already covered by resolved_fields values. Cap at 3."""
    resolved_values = {str(v) for v in resolved_fields.values() if v is not None}
    extras: list[str] = []
    for snippet in snippets:
        doc = snippet.get("document", "")
        if not doc:
            continue
        if any(rv in doc for rv in resolved_values):
            continue
        extras.append(doc)
        if len(extras) >= 3:
            break
    return extras


def _format_deterministic(
    query_type: str,
    resolved_fields: dict[str, Any],
    evidence: dict[str, str],
    snippets: list[dict[str, Any]],
) -> str:
    if query_type == "insufficient_context":
        return "Please provide a more specific billing question."

    if query_type == "exact_field_lookup" and resolved_fields:
        non_null_resolved = {
            key: value for key, value in resolved_fields.items() if value is not None
        }
        if not non_null_resolved:
            return "I could not find that in the bill documents."

        if {
            "amounts.last_payment_date",
            "amounts.last_payment_amount",
        }.issubset(non_null_resolved):
            return (
                "Your last payment was made on "
                f"{non_null_resolved['amounts.last_payment_date']} "
                f"for {non_null_resolved['amounts.last_payment_amount']}."
            )
        return "; ".join(f"{key}: {value}" for key, value in non_null_resolved.items())

    if query_type == "charge_breakdown_lookup" and resolved_fields:
        parts = [f"{key}: {value}" for key, value in resolved_fields.items() if value is not None]
        if parts:
            base = "Charge breakdown from your bill: " + "; ".join(parts)
            extras = _extract_snippet_extras(snippets, resolved_fields)
            if extras:
                base += " | Additional details: " + "; ".join(extras)
            return base

    if query_type == "history_lookup" and resolved_fields:
        history = resolved_fields.get("history")
        if isinstance(history, list) and history:
            preview = history[:3]
            base = "Recent bill history: " + "; ".join(json.dumps(row) for row in preview)
            extras = _extract_snippet_extras(snippets, resolved_fields)
            if extras:
                base += " | Additional details: " + "; ".join(extras)
            return base

    if snippets:
        top = snippets[0].get("document", "")
        if top:
            return f"Based on retrieved bill evidence: {top}"

    if evidence:
        evidence_values = [value for value in evidence.values() if value]
        if evidence_values:
            return "Based on bill evidence: " + "; ".join(evidence_values)

    return "I could not find that in the bill documents."
