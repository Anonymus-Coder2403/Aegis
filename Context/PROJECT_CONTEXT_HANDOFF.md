# Aegis Project Context Handoff

## Quick Start for New Sessions

Read this file first. Then read `ARCHITECTURE_LOCK.md`. Then inspect the current repo state before making changes. Do not reopen locked architecture decisions unless the user explicitly asks to revisit them.

`Claude.md` was previously the working source of truth. This file and `ARCHITECTURE_LOCK.md` now supersede conflicting statements in `Prompt.xml`, `Task.xml`, and `aegis_codex_agent_prompt.xml`. The XML files remain historical context only unless they align with the locked markdown docs.

## Project Identity

- Project: Aegis — Production Document RAG System
- Purpose: production app (evolved from internship prototype)
- Language: Python 3.10+
- Developer hardware: HP Victus 15 (fb0052ax), Ryzen 7 5600H, RTX 3050 4GB VRAM, 16GB RAM
- Deployment: Cloud-first (AWS), Docker Compose for dev only
- Active version: V2 (on `v2` branch, merges to `master` via PR)
- V1: frozen on `v1` branch

## Current Repo Reality

All three features (Billing RAG, Weather Advisor, AC Control) implemented under a single unified `aegis` package. 88 tests passing.

### V1 Package Structure

```
src/aegis/
├── core/              config.py, orchestrator.py
├── billing/           answerer, cli, config, llm_formatter, query_classifier, types
│   ├── parser/        extractors, normalize, pvvnl_parser, msedcl_parser
│   └── rag/           embeddings, retriever, store
├── weather/           advisor, fetcher
├── ac_control/        classifier, client, server
└── ui/                streamlit_app
```

### Entry points

- `aegis` → `aegis.core.orchestrator:main_cli`
- `aegis-billing` → `aegis.billing.cli:main`
- `aegis-ac-server` → `aegis.ac_control.server:run_server`
- `aegis-ui` → `aegis.ui.streamlit_app:main`

## V2 Production RAG Phase (APPROVED - 2026-03-29, brainstorming in progress)

### System Type
General-purpose document RAG — any PDF, any question, pure retrieval + generation. Replaces v1's billing-specific schema-first approach entirely.

### V2 Tech Stack (Locked)
| Component | Choice | Rationale |
|-----------|--------|-----------|
| LLM Generation | Gemini 2.5 Flash | Cost, free tier, temp=0 grounding |
| LLM SDK | `google-genai` direct | LiteLLM dropped — supply chain risk, lossy structured output |
| Hybrid Search | OpenSearch | BM25 + kNN native, RRF fusion |
| Metadata Storage | PostgreSQL | Relational only — no pgvector |
| Embeddings | BGE-M3 (self-hosted) | MIT, 1024 dims, sparse+dense in one pass |
| Caching | Redis | 50%+ API cost reduction |
| Async Tasks | Celery + Redis | PDF processing, embeddings |
| File Storage | S3-compatible | Cloud-ready design |
| Agentic | LangGraph | Query rewriting, document grading, guardrails |
| Observability | Langfuse | Full tracing |
| Docker | Yes | Full production setup |

### Cloud Deployment Readiness (AWS)
| Current (Local) | AWS Cloud (Future) |
|-----------------|-------------------|
| Docker Compose | ECS / EKS |
| Local PostgreSQL | RDS PostgreSQL |
| Local Redis | ElastiCache Redis |
| Local OpenSearch | OpenSearch Service |
| Local File Storage | S3 |
| Celery + Redis | SQS + Lambda |

### Reference
- [production-agentic-rag-course](https://github.com/jamwithai/production-agentic-rag-course) — 5.3K stars, 7-week course

### Remaining Design Decisions (brainstorming paused)
- API surface / endpoints
- Auth strategy
- Frontend choice
- Docker Compose services
- Test strategy
- V2 project structure
- Weather/AC port timeline

## V2 Key Technical Decisions

### Why LiteLLM was dropped for V2
- Single provider (Gemini) — multi-provider abstraction adds risk without benefit
- Structured output bugs with Gemini (GitHub #22391, #1967) — silent field drops
- System prompt handling bugs (PR #13243)
- Supply chain compromise on 1.82.7/1.82.8 (March 2026)
- Direct `google-genai` SDK gives full access to Gemini features without translation layer

### Why pgvector was dropped
- OpenSearch handles all search (BM25 + kNN) natively — redundant second vector store
- Reference repo uses PostgreSQL for relational data only, no pgvector

### Why BGE-M3 over all-MiniLM-L6-v2
- all-MiniLM-L6-v2 is obsolete: MTEB 56.3, 512-token context limit
- BGE-M3: MTEB 63.0, 8K context, 1024 dims, MIT license, sparse+dense in one pass

### Context strategy
- Small targeted retrieval (2-4K tokens per query), NOT large context stuffing

## V1 Technical Decisions (frozen, historical)

- LiteLLM `1.82.6` was the orchestration layer (security-pinned, versions 1.82.7/1.82.8 compromised)
- ChromaDB local for vector storage
- `sentence-transformers` with `all-MiniLM-L6-v2` for embeddings
- Schema-first billing QA: structured lookup first, Chroma fallback second
- pdfplumber + PyMuPDF for PDF extraction

### Why schema-first billing QA was chosen

- The target bill format contains multiple visually similar amounts.
- Layout and table extraction are likely to separate labels from values.
- A structured parse is more reliable than treating the PDF as plain text chunks.
- Chroma remains useful, but as support for evidence retrieval and long-tail queries.

## Architecture Overview

### Weather Advisor

- Python fetches weather data from OpenWeatherMap or falls back to `data/weather_mock.json`.
- Python extracts the relevant precipitation fields.
- LiteLLM sends only structured weather facts to Gemini 2.5 Flash.
- The model returns conversational advice rather than raw numbers.

### AC Control

- The user asks in natural language.
- LiteLLM classifies the intent as `turn_on`, `turn_off`, or `none`.
- Python maps the intent to the correct AC action.
- The action is executed through an HTTP call to a separate FastAPI mock hardware server.
- The final response confirms the action taken and the observable state.

### Billing Librarian

- PDFs are parsed into canonical structured bill objects.
- Structured fields become the primary source for exact billing answers.
- Chroma collections hold searchable bill-level, charge-level, and history-level material.
- Metadata filtering narrows scope before semantic retrieval.
- Gemini 2.5 Flash formats only the selected structured answer and evidence.

### Current implementation status

- The billing CLI is working through:
  - `uv run aegis-billing inspect --pdf document_pdf.pdf --store-dir .billing_store`
  - `uv run aegis-billing ingest --pdf document_pdf.pdf --store-dir .billing_store`
  - `uv run aegis-billing query --question "When was my last electricity bill paid, and what was the amount?" --pdf document_pdf.pdf --store-dir .billing_store`
- The real sample bill currently parses these verified fields correctly:
  - `bill_id`
  - `account_no`
  - `bill_month`
  - `bill_date`
  - `due_date`
  - `disconnection_date`
  - `amounts.current_payable`
  - `amounts.total_payable_rounded`
  - `amounts.payable_by_due_date`
  - `amounts.last_payment_amount`
  - `amounts.last_payment_date`
  - `amounts.last_receipt_no`
  - `amounts.arrears_total`
  - selected `charges.*`
  - selected `consumption.*`
  - `history[]`
  - selected `evidence_map` entries
- The verified real sample query currently returns:
  - last payment date: `10-JAN-2020`
  - last payment amount: `2119.0`

## Billing System Deep Context

The representative PVVNL bill format is not a good fit for naive chunked RAG. The bill contains multiple amount fields with similar numeric values and different meanings. It also has layout and table characteristics that make plain token chunking unreliable.

Naive RAG fails because:

- labels and values can be split apart
- last payment amount can be confused with current payable amount
- multiple payable figures appear on the same page
- the document is semi-structured rather than narrative

Structured parsing is primary because:

- most user questions map to stable fields
- exact answers are safer when fetched directly from canonical JSON
- failure states can be handled explicitly instead of guessed

Chroma still exists because:

- the assignment expects retrieval infrastructure
- charge and history lookups benefit from searchable records
- evidence snippets improve answer transparency
- fallback retrieval is useful for less predictable queries

## Canonical Bill Schema

```json
{
  "source_doc_id": "bill_2020_01_pvvnl_001",
  "bill_id": "132189891047",
  "account_no": "1321865000",
  "bill_month": "JAN-2020",
  "bill_date": "17-JAN-2020",
  "due_date": "24-JAN-2020",
  "disconnection_date": "31-JAN-2020",
  "amounts": {
    "current_payable": 2837.58,
    "total_payable_rounded": 2837,
    "payable_by_due_date": 2811,
    "last_payment_amount": 2119.0,
    "last_payment_date": "10-JAN-2020",
    "last_receipt_no": "132186537483",
    "arrears_total": -0.21
  },
  "charges": {
    "electricity_charges": 2238.5,
    "fixed_demand_charges": 440.0,
    "current_bill_lpsc": 25.15,
    "electricity_duty": 133.93
  },
  "consumption": {
    "billed_units_kwh": 379,
    "previous_read": 12021,
    "current_read": 12400
  },
  "history": [
    {
      "month": "DEC-2019",
      "units": 272,
      "demand": 4
    },
    {
      "month": "NOV-2019",
      "units": 202,
      "demand": 4
    }
  ],
  "raw_text": "...full page fallback text...",
  "evidence_map": {
    "amounts.last_payment_amount": "evidence snippet",
    "amounts.last_payment_date": "evidence snippet"
  }
}
```

## Planned Folder Structure

```text
aegis/
├── main.py
├── requirements.txt
├── README.md
├── config/
│   └── settings.py
├── agent/
│   └── orchestrator.py
├── tasks/
│   ├── weather_advisor.py
│   ├── ac_control.py
│   └── billing_librarian.py
├── rag/
│   ├── ingest.py
│   ├── parser.py
│   ├── retriever.py
│   └── embeddings.py
├── mcp_server/
│   └── server.py
├── data/
│   ├── bills/
│   └── weather_mock.json
└── logs/
    └── session.log
```

## Planned Module Responsibilities

- `main.py`
  - application entry point and top-level agent loop
- `config/settings.py`
  - configuration for API keys, ports, model name, and local paths
- `agent/orchestrator.py`
  - route user requests to weather, AC control, or billing flows
- `tasks/weather_advisor.py`
  - weather fetch, fallback loading, and structured advice input assembly
- `tasks/ac_control.py`
  - AC intent handling and HTTP interaction with FastAPI mock hardware
- `tasks/billing_librarian.py`
  - billing query classification, structured lookup orchestration, and final grounded response generation
- `rag/ingest.py`
  - PDF extraction orchestration and Chroma upsert
- `rag/parser.py`
  - canonical bill parsing and normalization
- `rag/retriever.py`
  - bill resolution, metadata filtering, structured lookup, and semantic fallback retrieval
- `rag/embeddings.py`
  - sentence-transformer wrapper for local embeddings
- `mcp_server/server.py`
  - FastAPI mock hardware server exposing AC control endpoints

## Data Contracts and Interfaces

### Billing query classifier output

The billing query classifier should emit one of:

- `exact_field_lookup`
- `charge_breakdown_lookup`
- `history_lookup`
- `document_fallback_lookup`
- `insufficient_context`

### Canonical bill object

The canonical bill type is `CanonicalBill` and must preserve:

- top-level identifiers and dates
- all amount fields without merging semantically distinct values
- `charges`
- `consumption`
- `history`
- `raw_text`
- `source_doc_id`
- `evidence_map`

### Chroma collection responsibilities

- `bill_fields`
  - one document per bill with flattened canonical JSON and selected evidence text
- `bill_charges`
  - one document per charge line with bill metadata
- `bill_history`
  - one document per history row with bill metadata

### Current implementation caveat

- Chroma upsert is implemented with real `sentence-transformers` embeddings (`all-MiniLM-L6-v2`) via `rag/embeddings.py`.

## Build Order

1. Build the FastAPI mock hardware server.
2. Build the Weather Advisor.
3. Build the AC Control path on top of LiteLLM + FastAPI.
4. Build the RAG ingest pipeline.
5. Build the Billing Librarian query path.

## Acceptance Criteria

### Weather Advisor

- accepts a natural-language umbrella question
- fetches weather data or uses the mock file
- returns recommendation-quality advice, not just a percentage

### AC Control

- supports direct and indirect requests
- correctly classifies on/off intent
- calls the FastAPI hardware endpoint
- confirms the action taken and exposes observable state

### Billing Librarian

- answers billing questions strictly from parsed bill data or retrieved evidence
- does not hallucinate missing dates or amounts
- distinguishes the three payable amount fields correctly
- can answer the last payment date and amount from the representative bill format
- uses structured lookup first and Chroma fallback or evidence retrieval second

## Known Risks and Mitigations

- Parser brittleness
  - Use field-specific rules, normalization, and explicit missing-field handling.
- Amount confusion
  - Keep separate canonical keys and attach evidence where possible.
- Ambiguous bill targeting
  - Require explicit bill PDF context for each billing query.
- Retrieval noise
  - Apply metadata filters before semantic retrieval and keep top-k small.
- Partial extraction failures
  - Return grounded failure instead of guessing when key fields are missing.

## Operational Defaults

- Billing query flow is single-bill only and requires explicit PDF context.
- If a required answer field is missing, the system should say it could not find that in the bill documents.
- Vector retrieval never overrides a valid exact structured value.
- The sample bill PDF currently in the repo is treated as representative of the target PVVNL bill set unless the user later says otherwise.

## Future Agent Instructions

For substantial new tasks, start by clarifying the work in this format:

- Goal
- Context
- Action
- Output

Then ask the minimum useful follow-up questions needed to remove ambiguity. Do not casually agree with weak technical choices. Challenge assumptions when the design or implementation path is weak or underspecified.

## Open Items

- Multi-bill ranking/selection remains intentionally out of scope for this phase.
- Variance across the full 5+ PVVNL bill set still needs confirmation.
- The billing implementation has strong regression coverage for the current parser/query path and currently passes the full local billing test suite.

## Current Phase: V1 Complete (88 tests passing)

All three features implemented under single unified `aegis` package. V1 restructure complete.

### V1 Project layout

```
src/aegis/
├── core/              config.py (AegisConfig), orchestrator.py (keyword routing + CLI)
├── billing/           answerer, cli, config, llm_formatter, query_classifier, types
│   ├── parser/        extractors, normalize, pvvnl_parser, msedcl_parser
│   └── rag/           embeddings, retriever, store
├── weather/           advisor, fetcher
├── ac_control/        classifier, client, server
└── ui/                streamlit_app
```

### V1 Entry points
```bash
uv run aegis ask "<question>"                      # orchestrator CLI
uv run aegis-billing query --question "..." --pdf   # billing CLI
uv run aegis-ac-server                              # mock hardware on port 8765
uv run aegis-ui                                     # Streamlit prototype UI
uv run pytest tests/ -v                             # 88 tests passing
```

### Completed migration

| Before | After |
|---|---|
| `src/aegis_billing_rag/billing/*` | `src/aegis/billing/*` |
| `src/aegis/config.py` | `src/aegis/core/config.py` |
| `src/aegis/orchestrator.py` | `src/aegis/core/orchestrator.py` |
| `billing/streamlit_app.py` | `src/aegis/ui/streamlit_app.py` |
| Two packages (`aegis` + `aegis_billing_rag`) | Single unified `aegis` package |

### Hard constraints
- Weather, AC, Billing remain fully independent — no cross-feature coupling
- Secrets always in `.env`; never in config files
- AC mock server on port 8765

---

## Remaining Production Items (require explicit user approval)

### LiteLLM mandatory (enabled by default)
- `BillingConfig.litellm_enabled` default → `True`
- Startup validation: raise clear error if LLM API key env var is missing
- Deterministic fallbacks remain as silent safety nets only

### Proper frontend (after Streamlit validation)
- Streamlit is prototype/testing surface only — NOT the production frontend
- After sign-off, build a proper frontend that talks to the FastAPI backend only
- No direct Python module imports from the frontend
