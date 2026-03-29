# Aegis Architecture Lock

## Status

This file is the authoritative lock for Aegis architecture and stack decisions.
Where this file conflicts with `Prompt.xml`, `Task.xml`, or `aegis_codex_agent_prompt.xml`, this file wins.

`Claude.md` was previously the working source of truth. This file and `PROJECT_CONTEXT_HANDOFF.md` now supersede conflicting statements in `Prompt.xml`, `Task.xml`, and `aegis_codex_agent_prompt.xml`. The XML files remain historical context only where they align with the locked markdown documents.

## Project Goal

Aegis is a production document RAG system with hybrid search, agentic features, and cloud deployment readiness. Weather and AC features to be ported from v1 after core RAG is complete.

## Active Version: V2 (in design)

V1 is frozen on the `v1` branch. V2 is being built on the `v2` branch, to be merged into `master` via PR.

## V2 Locked Stack

- Python 3.10+
- Gemini 2.5 Flash via direct `google-genai` SDK
- OpenSearch (BM25 + kNN hybrid search)
- PostgreSQL (relational metadata only — no pgvector)
- BGE-M3 embeddings (self-hosted, MIT, 1024 dims, sparse+dense)
- Redis (caching)
- Celery + Redis (async tasks)
- LangGraph (agentic orchestration)
- FastAPI (backend API)
- Langfuse (observability)
- Docker Compose (dev), AWS (production)

## V1 Stack (frozen on `v1` branch)

- Python 3.10+
- Gemini 2.5 Flash via LiteLLM `1.82.6`
- ChromaDB local
- `sentence-transformers` with `all-MiniLM-L6-v2`
- FastAPI + httpx
- pdfplumber + PyMuPDF

## LiteLLM — DROPPED for V2

- V1 used `litellm==1.82.6` (security-pinned). Versions `1.82.7`, `1.82.8` were compromised (supply chain attack, March 2026).
- V2 uses direct `google-genai` SDK instead. Reasons: single-provider (no multi-provider benefit), structured output bugs with Gemini (GitHub #22391, #1967), lossy translation layer, supply chain risk.
- LiteLLM must NOT be reintroduced in v2.

## Non-Negotiable Design Rules (V2)

- The LLM never directly calls external APIs, FastAPI endpoints, or search indexes. Python handles all I/O.
- RAG answers must be grounded strictly in retrieved context. If the answer is not in context, the system must say so.
- Retrieval uses small, targeted context (2-4K tokens per query) — never stuff the full context window.
- OpenSearch handles all search (BM25 + kNN). PostgreSQL is relational metadata only.
- BGE-M3 generates sparse+dense vectors in one pass for OpenSearch hybrid search.
- LangGraph orchestrates agentic workflows. `google-genai` SDK makes LLM calls. These are separate concerns.

## V2 RAG Architecture

- General-purpose document RAG — any PDF, any question, pure retrieval + generation
- Hybrid search: BM25 (keyword) + kNN (vector) via OpenSearch with RRF fusion
- Agentic features via LangGraph: query rewriting, document grading, guardrails, adaptive retrieval
- No billing-specific structured parsing — v1's schema-first approach is retired

## V1 Billing RAG Architecture (frozen on `v1` branch)

- Schema-first hybrid design with direct structured lookup as primary path
- ChromaDB as fallback/evidence layer with three collections: `bill_fields`, `bill_charges`, `bill_history`

## Current Billing Status

- Billing slice lives in `src/aegis/billing/` (unified under the `aegis` package).
- Embedding, retrieval, and LLM formatting live inside `src/aegis/billing/rag/` and `src/aegis/billing/llm_formatter.py`.
- The current implementation uses:
  - rule-based query classification
  - canonical bill parsing from `pdfplumber` + `PyMuPDF` output
  - exact structured lookup as the primary working answer path
  - local canonical JSON persistence (`store_dir/canonical/`) plus Chroma upsert (`store_dir/chroma/`) via `BillingConfig`
  - CLI exposed through `uv run aegis-billing ...`
- Verified real sample-bill support currently includes:
  - `bill_id`, `account_no`, `bill_month`, `bill_date`, `due_date`, `disconnection_date`
  - `amounts.current_payable`, `amounts.total_payable_rounded`, `amounts.payable_by_due_date`
  - `amounts.last_payment_amount`, `amounts.last_payment_date`, `amounts.last_receipt_no`, `amounts.arrears_total`
  - selected `charges.*`, selected `consumption.*`, `history[]`, expanded `evidence_map`
- Verified real query currently works for:
  - "When was my last electricity bill paid, and what was the amount?"

## Query Routing Rules

- Exact-field questions go to structured lookup first.
- Charge and history questions use structured lookup first, with optional evidence retrieval.
- Unmapped or ambiguous billing questions use metadata-filtered semantic retrieval.
- Vector retrieval never overrides a valid exact structured value.

## Canonical Bill Fields

The canonical bill object must include:

- `source_doc_id`
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
- `charges.*`
- `consumption.*`
- `history[]`
- `raw_text`
- `evidence_map`

## Source of Truth Priority

1. `ARCHITECTURE_LOCK.md`
2. `PROJECT_CONTEXT_HANDOFF.md`
3. `Claude.md`
4. XML prompt and task files only where non-conflicting

## Explicit Overrides (V2)

The chosen architecture is not:

- Ollama as the primary LLM runtime
- LiteLLM as the LLM abstraction layer
- pgvector for vector storage
- Billing-specific schema-first RAG
- Large context window stuffing (1M context is a trap — "lost in the middle" problem)

The chosen architecture is:

- Gemini 2.5 Flash via direct `google-genai` SDK
- General-purpose document RAG with OpenSearch hybrid search
- BGE-M3 for embeddings (sparse+dense)
- LangGraph for agentic orchestration
- Cloud-first (AWS), Docker Compose for dev

## V1 Implementation Status (frozen)

All three features implemented and tested (88 tests passing). Single unified `aegis` package. Frozen on `v1` branch.

---

## Production RAG Phase (APPROVED - 2026-03-29)

### Production RAG Goals
- Handle 10,000+ page PDF documents efficiently
- Implement hybrid search (BM25 + Vector) with RRF fusion
- Add Redis caching layer (50%+ API cost reduction)
- Add S3-compatible file storage for documents
- Add Celery for async task processing
- Add rate limiting for production deployment
- Add agentic features (query rewriting, document grading)
- Add Langfuse observability
- Design for cloud deployment readiness (AWS-compatible)

### Production Stack Decisions (Updated 2026-03-29)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Hybrid Search** | OpenSearch | BM25 + kNN native, RRF fusion |
| **Metadata Storage** | PostgreSQL | Relational metadata only — no pgvector |
| **Embeddings** | BGE-M3 (self-hosted) | MIT, 1024 dims, sparse+dense in one pass |
| **LLM Generation** | Gemini 2.5 Flash | Cost, free tier, temp=0 |
| **LLM SDK** | `google-genai` direct | LiteLLM dropped (supply chain risk, lossy translation) |
| **Caching** | Redis | 50%+ API cost reduction |
| **Async Tasks** | Celery + Redis | PDF processing, embeddings |
| **File Storage** | S3-compatible | Cloud-ready design |
| **Docker** | Yes | Full production setup |
| **Agentic Features** | LangGraph | Query rewriting + document grading |
| **Observability** | Langfuse | Full tracing |

### Cloud Deployment Readiness (AWS)

| Current (Local) | AWS Cloud (Future) |
|-----------------|-------------------|
| Docker Compose | ECS / EKS |
| Local PostgreSQL | RDS PostgreSQL |
| Local Redis | ElastiCache Redis |
| Local OpenSearch | OpenSearch Service |
| Local File Storage | S3 |
| Celery + Redis | SQS + Lambda |

### Reference Implementation
- [production-agentic-rag-course](https://github.com/jamwithai/production-agentic-rag-course) - 5.3K stars

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

### Feature locations
- Billing RAG: `src/aegis/billing/` — complete
- Weather Advisor: `src/aegis/weather/` — OpenWeatherMap + mock fallback + LiteLLM recommendation
- AC Control: `src/aegis/ac_control/` — FastAPI mock server (port 8765) + LiteLLM intent classifier + httpx client
- Core: `src/aegis/core/config.py` (AegisConfig) + `src/aegis/core/orchestrator.py` (keyword routing + CLI)
- Streamlit: `src/aegis/ui/streamlit_app.py` — three-tab UI (prototype/testing surface only)

### Entry points
- `aegis` → orchestrator CLI (`aegis.core.orchestrator:main_cli`)
- `aegis-billing` → billing CLI (inspect/ingest/query)
- `aegis-ac-server` → AC mock hardware (port 8765)
- `aegis-ui` → Streamlit prototype UI

## Remaining Items (brainstorming in progress)

- API surface (endpoints TBD)
- Auth strategy (TBD)
- Frontend choice (TBD)
- Docker Compose service list (TBD)
- Test strategy (TBD)
- V2 project structure (TBD)
- Weather/AC port timeline (after core RAG)

## Non-Negotiable Structural Rules

- Secrets always in `.env`; never in config files
- FastAPI backend on port 8000
- All search goes through OpenSearch — no secondary vector stores
- LLM calls via `google-genai` SDK only — no LiteLLM
