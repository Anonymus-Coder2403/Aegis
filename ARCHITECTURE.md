# Aegis Architecture

This document covers how the system is actually built — the data flows, the design decisions that shaped each feature, and where the boundaries are drawn.

---

## Overview

Aegis has three independent features: a billing RAG pipeline, a weather advisor, and an AC controller. They share a config object and a keyword router, but they have no other coupling. You can read, modify, or test any one of them without touching the others.

```
User input
    │
    ▼
Orchestrator (keyword match → LiteLLM fallback)
    │
    ├── weather  → fetch_weather() → advise_weather() → LiteLLM
    ├── ac       → classify_ac_intent() → execute_ac_command() → FastAPI mock
    └── billing  → ingest_bill() → classify_billing_query() → format_grounded_answer()
```

The LLM never calls APIs, never queries ChromaDB, never makes HTTP requests. Python handles all I/O. The LLM only receives structured data and returns text.

---

## Package layout

```
src/aegis/
├── core/
│   ├── config.py          AegisConfig — shared frozen dataclass
│   └── orchestrator.py    keyword routing + LiteLLM fallback + CLI
├── billing/
│   ├── answerer.py        main entry point: answer_billing_question()
│   ├── query_classifier.py rule-based query intent classification
│   ├── llm_formatter.py   grounded answer formatting, LiteLLM for charge/history
│   ├── config.py          BillingConfig — store paths, LiteLLM settings
│   ├── types.py           CanonicalBill, BillAmounts, BillConsumption dataclasses
│   ├── cli.py             argparse CLI: inspect / ingest / query
│   ├── parser/
│   │   ├── extractors.py  PDF → ExtractedBillContent (pdfplumber + PyMuPDF)
│   │   ├── normalize.py   amount/date normalization helpers
│   │   ├── pvvnl_parser.py PVVNL bill → CanonicalBill
│   │   └── msedcl_parser.py MSEDCL bill → CanonicalBill
│   └── rag/
│       ├── embeddings.py  sentence-transformers wrapper (lazy-loaded, cached)
│       ├── store.py       canonical JSON + ChromaDB upsert, chunking logic
│       └── retriever.py   field lookup, charge/history/document snippet retrieval
├── weather/
│   ├── fetcher.py         OpenWeatherMap API + mock fallback
│   └── advisor.py         LiteLLM → Gemini weather recommendation
├── ac_control/
│   ├── server.py          FastAPI mock hardware (port 8765)
│   ├── classifier.py      LiteLLM JSON intent + keyword fallback
│   └── client.py          httpx calls → ACActionResult
└── ui/
    └── streamlit_app.py   3-tab prototype UI
```

---

## Config

`AegisConfig` (`core/config.py`) is a frozen dataclass. It holds the LiteLLM model name, API key env var names, weather API settings, and the AC server address. It does not store secrets directly — keys are read at runtime from environment via `os.getenv()`.

`BillingConfig` (`billing/config.py`) adds billing-specific paths: where canonical JSON lives (`store_dir/canonical/`) and where ChromaDB lives (`store_dir/chroma/`). Both are derived from `store_dir`.

Neither config reads from YAML files. There are no config files in the repo. Secrets go in `.env` only.

---

## Orchestrator

`route_and_answer()` in `core/orchestrator.py` does keyword matching first:

- weather keywords: `weather`, `umbrella`, `rain`, `temperature`, etc.
- AC keywords: `ac`, `air condition`, `hot`, `cold`, `cool`, etc.
- billing keywords: `bill`, `payment`, `charge`, `due`, `electricity`, etc.

If exactly one keyword set matches, it routes there. If zero or multiple match, it calls Gemini to classify — asking for exactly one word (`weather`, `ac`, `billing`, or `none`), temperature 0, max 10 tokens.

No routing state is kept between calls. Every call is independent.

---

## Billing RAG pipeline

This is the most complex part of the system. Here is what actually happens when you call `answer_billing_question()`:

### Step 1 — PDF extraction

`extractors.extract_pdf_content()` runs two passes:
- `pdfplumber` for table extraction (structured rows)
- `PyMuPDF` for raw text fallback

The output is `ExtractedBillContent`, which holds both.

### Step 2 — Parser

The parser is chosen by inspecting the raw text. MSEDCL bills have a distinct header pattern; everything else goes to the PVVNL parser. The parser produces a `CanonicalBill` dataclass with named fields for every amount, charge, and date. It also builds an `evidence_map` — a dict of field paths to the raw text snippet that the value was extracted from.

Three amount fields that look similar but are different:
- `amounts.current_payable` — the pre-rounding calculated amount
- `amounts.total_payable_rounded` — the rounded version shown at the bottom
- `amounts.payable_by_due_date` — a discounted amount valid only before the due date

These are never merged.

### Step 3 — Store

`BillingStore.upsert_bill()` does two things:
1. Writes the canonical bill as JSON to `store_dir/canonical/{source_doc_id}.json`
2. Chunks the bill and upserts into three ChromaDB collections

The chunking in `_build_field_chunks()` produces:
- one `summary` chunk (bill ID, account, dates)
- one `amounts` chunk (all 7 amount fields)
- one `consumption` chunk (meter readings, billed units)
- one `evidence` chunk per `evidence_map` entry (typically ~9)
- multiple `raw_text` chunks (500 char segments, 50 char overlap)

Before chunking was added, the entire bill JSON was stored as a single document. `all-MiniLM-L6-v2` has a 512-token limit; a full bill JSON is around 5800 characters. Chunking fixes that and makes top-k=4 actually return different parts of the bill.

`bill_charges` and `bill_history` collections each get one document per charge line or history row.

### Step 4 — Query classification

`classify_billing_query()` is rule-based, not LLM-based. It checks for keywords:

| Pattern | Query type | Example |
|---|---|---|
| "last" + "paid" | `exact_field_lookup` | "When was my last bill paid?" |
| "due date" | `exact_field_lookup` | "What's my due date?" |
| "charge" / "duty" / "lpsc" | `charge_breakdown_lookup` | "What are my charges?" |
| "history" / "consumption" | `history_lookup` | "Show me previous months" |
| short query (<8 chars) | `insufficient_context` | "bill?" |
| no match | `document_fallback_lookup` | any other question |

The intent object carries `field_paths` — the exact schema keys the answerer should look up.

### Step 5 — Answer resolution

`answer_billing_question()` in `answerer.py` handles the routing:

- `exact_field_lookup` → `lookup_exact_fields(bill, field_paths)` — direct attribute access on the dataclass, no Chroma involved
- `charge_breakdown_lookup` / `history_lookup` → structured lookup first, then `retrieve_charge_snippets()` or `retrieve_history_snippets()` from ChromaDB, filtered by `source_doc_id`
- `document_fallback_lookup` → `retrieve_document_snippets()` from `bill_fields` collection, filtered by `source_doc_id`
- `insufficient_context` → skip all retrieval, go straight to formatting

Vector retrieval never overrides a valid structured value. If `lookup_exact_fields` finds the value, that value is the answer — not whatever similarity search might return.

### Step 6 — Answer formatting

`format_grounded_answer()` in `llm_formatter.py`:

- Builds a deterministic answer first (always)
- For `exact_field_lookup`, returns the deterministic answer — no LLM involved
- For everything else, passes `resolved_fields`, `evidence`, and `snippets` to Gemini as structured JSON and asks it to format a grounded response
- If LiteLLM fails for any reason, falls back to the deterministic answer silently

The system prompt tells Gemini: resolved_fields are authoritative, snippets are supplementary, never invent values.

---

## Weather Advisor

`fetch_weather()` calls OpenWeatherMap's current weather endpoint. If the API key is missing or the call fails, it loads `data/weather_mock.json` and sets `is_mock=True` on the result. The UI shows a warning banner when mock data is in use.

`advise_weather()` sends the structured weather data (city, temp, description, rain, humidity) to Gemini as JSON context and asks it to answer the user's specific question. If LiteLLM is unavailable, it returns a deterministic template sentence.

---

## AC Control

Two-step path, deliberately kept separate:

**Step 1 — classify intent** (`classifier.py`)

Sends the user message to Gemini with a strict JSON-only system prompt. Expects exactly `{"intent": "turn_on"}`, `{"intent": "turn_off"}`, or `{"intent": "none"}`. Any parse failure, exception, or unrecognised value falls back to keyword matching (`hot/warm/stuffy` → `turn_on`, `cold/cool/freezing` → `turn_off`).

**Step 2 — execute** (`client.py`)

Maps the intent string to the right endpoint (`POST /ac/on` or `POST /ac/off`) on the mock server (port 8765) and returns an `ACActionResult` with a confirmation string and the current state.

The mock server (`server.py`) is a FastAPI app with in-memory state. It has three routes: `POST /ac/on`, `POST /ac/off`, `GET /ac/status`.

The classifier and the HTTP client are in separate files by design. Intent classification should not know about HTTP, and the HTTP client should not know about NLP.

---

## LiteLLM usage

Every LLM call goes through LiteLLM with:
- `temperature=0` — deterministic outputs
- small `max_tokens` — 10 for routing, 50 for AC intent, 300 for weather advice, 500 for billing answers
- explicit `api_key` passed per call — not stored in global state

All three features have a deterministic fallback path that activates when LiteLLM raises, the API key is missing, or the response is malformed. The fallback is silent — the user sees an answer, not an error.

LiteLLM is pinned to `1.82.6`. Versions `1.82.7` and `1.82.8` are not used; both have known security issues identified in March 2026.

---

## What the LLM does not do

Worth being explicit:

- It does not call OpenWeatherMap. Python calls OpenWeatherMap.
- It does not query ChromaDB. Python queries ChromaDB.
- It does not hit the AC server. Python hits the AC server.
- It does not parse PDFs. Python parses PDFs.
- It does not look up bill fields. Python looks up bill fields.
- For billing exact-field answers, it is not called at all.

The LLM's role is narrow: classify intent, recommend based on structured data, format answers. All state and all I/O live in Python.

---

## Tests

88 tests across 15 files. All use pytest with `monkeypatch`, `capsys`, and `tmp_path`. No live API calls in the test suite — LiteLLM and HTTP calls are monkeypatched throughout.

```
tests/
├── conftest.py
├── test_ac_classifier.py        9 tests — keyword and LiteLLM paths, fallback behaviour
├── test_ac_client.py            5 tests — endpoint mapping, connection errors
├── test_answerer_grounding.py   6 tests — grounding contract, missing fields, no-pdf guard
├── test_bill_schema_mapping.py  11 tests — canonical field mapping, amount field separation
├── test_billing_cli_integration.py 4 tests — inspect / ingest / query end-to-end
├── test_embeddings.py           4 tests — lazy load, caching, error handling
├── test_llm_formatter.py        5 tests — LiteLLM path, deterministic fallback, exact bypass
├── test_normalize.py            4 tests — amount parsing, date normalization
├── test_orchestrator.py         8 tests — routing, keyword matching, billing-needs-pdf guard
├── test_query_classifier.py     7 tests — each query type, insufficient context
├── test_retriever_logic.py      8 tests — field lookup, chunk retrieval, multi-chunk return
├── test_streamlit_app.py        2 tests — PDF save helper
├── test_weather_advisor.py      6 tests — deterministic advice, LiteLLM path, fallback
└── test_weather_fetcher.py      8 tests — OWM parsing, mock fallback, error handling
```
