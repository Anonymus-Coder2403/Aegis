# Aegis Architecture Lock

## Status

This file is the authoritative lock for Aegis architecture and stack decisions.
Where this file conflicts with `Prompt.xml`, `Task.xml`, or `aegis_codex_agent_prompt.xml`, this file wins.

`Claude.md` was previously the working source of truth. This file and `PROJECT_CONTEXT_HANDOFF.md` now supersede conflicting statements in `Prompt.xml`, `Task.xml`, and `aegis_codex_agent_prompt.xml`. The XML files remain historical context only where they align with the locked markdown documents.

## Project Goal

Aegis is a production document RAG system with hybrid search, agentic features, and cloud deployment readiness. Weather and AC features to be ported from v1 after core RAG is complete.

## Active Version: V2 (in design)

V1 is frozen on the `v1` branch. V2 is being built on the `v2` branch, to be merged into `master` via PR.

**CRITICAL — Git:** `master` is shared with the internship company via URL. Never touch master directly. Only updated via a deliberate PR the user explicitly approves.

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

## V1 Billing (frozen — see `v1` branch)

V1's billing system used schema-first design: canonical bill parsing → exact field lookup → ChromaDB fallback. All billing-specific code (`src/aegis/billing/`, `CanonicalBill`, ChromaDB collections) is retired in V2. See `v1` branch for full details.

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
