# Aegis - Working Context (Updated)

This file tracks the current practical state of the project. If this file conflicts with `ARCHITECTURE_LOCK.md` or `PROJECT_CONTEXT_HANDOFF.md`, those two files win.

## Source of Truth Order

1. `ARCHITECTURE_LOCK.md`
2. `PROJECT_CONTEXT_HANDOFF.md`
3. `Claude.md`
4. Prompt XML files only where non-conflicting

## Project Identity

- Project: Aegis — Production Document RAG System
- Purpose: production app (evolved from internship prototype)
- Language: Python 3.10+
- Active version: V2 (on `v2` branch, merges to `master` via PR)
- V1: frozen on `v1` branch
- Runtime direction: cloud LLM generation via `google-genai` SDK, OpenSearch hybrid retrieval

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

## LiteLLM — DROPPED for V2

- V1 used `litellm==1.82.6`. V2 uses `google-genai` SDK directly.
- Do NOT reintroduce LiteLLM in v2.

## V2 Status (brainstorming in progress — paused 2026-03-29)

V2 is a clean build. General-purpose document RAG replacing v1's billing-specific pipeline. Design not yet finalized — remaining questions: API surface, auth, frontend, Docker services, tests, observability, project structure.

See `ARCHITECTURE_LOCK.md` for full locked decisions.

## V2 Key Architecture Decisions

- General-purpose RAG: any PDF, any question, pure retrieval + generation
- OpenSearch for all search (BM25 + kNN + RRF fusion) — no pgvector
- BGE-M3 embeddings (sparse+dense in one pass)
- Gemini 2.5 Flash via `google-genai` SDK (LiteLLM dropped)
- LangGraph for agentic workflows
- Cloud-first (AWS), Docker Compose for dev
- Small targeted retrieval (2-4K tokens) — never stuff the context window
- Weather/AC ported from v1 later, not removed

## V2 Non-Negotiable Rules

- LLM never directly calls external APIs, FastAPI endpoints, or search indexes
- Python controls all I/O and retrieval decisions
- RAG answers must be grounded in retrieved context — say so if not found
- All search through OpenSearch — no secondary vector stores
- LLM calls via `google-genai` SDK only — no LiteLLM

## V1 (frozen on `v1` branch)

V1 had 88 tests, three features (Billing RAG, Weather, AC Control), LiteLLM + ChromaDB + sentence-transformers. See `v1` branch for full code and docs.

## Git Branching — CRITICAL

- `v1` branch — frozen v1 permanently
- `v2` branch — ALL active development happens here
- `master` — v1 code, shared with internship company via URL. NEVER touch directly. Only updated via deliberate PR the user explicitly approves.
- If any command would affect master, warn and stop immediately.

## Notes for Future Sessions

- Do not reopen decided v2 architecture choices unless explicitly requested
- Resume brainstorming from API surface question
- Prefer updating `ARCHITECTURE_LOCK.md` and `PROJECT_CONTEXT_HANDOFF.md` first, then mirror concise changes here
- Keep this file practical and implementation-aligned, not speculative
