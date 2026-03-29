# Production RAG Implementation Plan

**Date**: 2026-03-29
**Goal**: General-purpose document RAG for 10,000+ page PDFs
**Timeline**: TBD — realistic estimate after design complete
**Status**: Brainstorming in progress (paused at API surface question)

---

## Executive Summary

Production-ready general-purpose document RAG system. Any PDF, any question, pure retrieval + generation. Replaces v1's billing-specific schema-first pipeline entirely. Cloud-first (AWS), Docker Compose for local dev.

### Key Goals
1. Handle 10,000+ page PDF documents efficiently
2. Hybrid search (BM25 + kNN) via OpenSearch with RRF fusion
3. BGE-M3 embeddings — sparse+dense in one pass
4. Redis caching layer (50%+ API cost reduction)
5. S3-compatible file storage for documents
6. Celery for async PDF processing + embedding
7. Agentic features via LangGraph (query rewriting, document grading, guardrails)
8. Langfuse observability
9. AWS cloud deployment readiness

---

## Locked Architecture Decisions

### Stack (All Confirmed)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **LLM Generation** | Gemini 2.5 Flash | $0.30/$2.50 per 1M tokens, free tier (250 RPD), 1M context |
| **LLM SDK** | `google-genai` direct | LiteLLM dropped — supply chain compromise (1.82.7/1.82.8), structured output bugs with Gemini (#22391), lossy translation |
| **Hybrid Search** | OpenSearch (BM25 + kNN) | Native hybrid, RRF fusion, single engine |
| **Metadata Storage** | PostgreSQL | Relational only — documents, chunks, sessions |
| **Vector Storage** | OpenSearch kNN only | pgvector dropped — redundant with OpenSearch |
| **Embeddings** | BGE-M3 (self-hosted) | MIT, 1024 dims, 8K context, sparse+dense in one pass, MTEB 63.0 |
| **Caching** | Redis | Query cache (1h TTL), embedding cache (24h TTL), LLM cache (1h TTL) |
| **Async Tasks** | Celery + Redis | PDF ingestion, embedding generation |
| **File Storage** | S3-compatible | Local MinIO for dev, AWS S3 for prod |
| **Agentic** | LangGraph | Query rewriting → retrieve → grade → rewrite loop → generate |
| **Observability** | Langfuse | Full LLM tracing |
| **Backend** | FastAPI | Port 8000 |
| **Containerization** | Docker Compose (dev) | AWS ECS/EKS for production |

### Context Strategy
- Small targeted retrieval: 2-4K tokens per query
- Never stuff the context window — "lost in the middle" degrades quality
- Top-k = 4-8 chunks, each 512-1024 tokens

### LangGraph Agentic Flow
```
User Query → Guardrail (out-of-domain check)
           → Retrieve (OpenSearch hybrid search)
           → Grade (relevance scoring)
           → Rewrite (if low relevance, rewrite query and re-retrieve)
           → Generate (Gemini 2.5 Flash with grounded context)
```

### Cloud Deployment (AWS)
| Dev (Local Docker) | Prod (AWS) |
|---|---|
| Docker Compose | ECS / EKS |
| Local PostgreSQL | RDS PostgreSQL |
| Local Redis | ElastiCache Redis |
| Local OpenSearch | OpenSearch Service |
| MinIO (S3-compatible) | S3 |
| Celery worker container | ECS task / SQS + Lambda |

### Reference Implementation
- [production-agentic-rag-course](https://github.com/jamwithai/production-agentic-rag-course) — 7-week course, 5.3K stars
- **Key difference from reference**: Uses `google-genai` instead of Ollama; PostgreSQL as relational store only (no pgvector)

---

## Pending Design Decisions (brainstorming in progress)

| Decision | Status |
|---|---|
| API surface / endpoints | **TBD** — paused here |
| Auth strategy | TBD |
| Frontend choice | TBD |
| Docker Compose service list | TBD |
| Test strategy | TBD |
| V2 project structure | TBD |
| Weather/AC port timeline | After core RAG |

---

## What Changed from Original Plan

| Original Plan | Corrected |
|---|---|
| pgvector for vector storage | **Dropped** — OpenSearch handles all vectors |
| LiteLLM as LLM layer | **Dropped** — direct `google-genai` SDK |
| all-MiniLM-L6-v2 embeddings | **Replaced** — BGE-M3 (MTEB 63 vs 56.3, 8K vs 512 token context) |
| 7-day timeline | **Unrealistic** — reference repo is 7 weeks |
| Gradio + Streamlit + Web as clients | **TBD** — to be decided |
| JWT auth from day one | **TBD** — may be unnecessary for v1 |
| Rate limiting from day one | **TBD** |
| "LiteLLM (Gemini/Claude)" in diagram | **Gemini only** via direct SDK |

---

## Docker Compose (Draft — services confirmed, config TBD)

Services:
- `api` — FastAPI app (port 8000)
- `worker` — Celery worker
- `postgres` — PostgreSQL 16 (port 5432)
- `redis` — Redis 7 (port 6379)
- `opensearch` — OpenSearch 2.19 (port 9200)
- `minio` — S3-compatible local storage (port 9000) *(or skip for MVP)*

```yaml
# Full config TBD after API surface + auth decisions
services:
  postgres:
    image: postgres:16-alpine

  redis:
    image: redis:7-alpine

  opensearch:
    image: opensearchproject/opensearch:2.19.0
    environment:
      discovery.type: single-node
      DISABLE_SECURITY_PLUGIN: "true"  # dev only
    mem_limit: 1g  # critical on 16GB RAM dev machine

  api:
    build: .
    ports:
      - "8000:8000"

  worker:
    build: .
    command: celery -A src.aegis.workers.celery_app worker
```

**Note on dev machine RAM (16GB):** OpenSearch needs ~1-1.5GB JVM heap minimum. Set `mem_limit: 1g` and `OPENSEARCH_JAVA_OPTS: "-Xms512m -Xmx512m"` for local dev.

---

## Expected Outcomes

| Metric | Current (V1) | V2 Target |
|--------|-------------|-----------|
| Max document size | ~100 pages | 10,000+ pages |
| Search quality | ChromaDB vector only | Hybrid BM25 + kNN (OpenSearch) |
| Embedding quality | all-MiniLM-L6-v2 (MTEB 56.3) | BGE-M3 (MTEB 63.0) |
| Response time | 5-10s | <3s (with Redis cache) |
| API costs | Full price | 50%+ reduction (cache) |
| Observability | None | Full tracing (Langfuse) |
| Async processing | None | Celery tasks |
| Cloud-ready | No | Yes (AWS) |
