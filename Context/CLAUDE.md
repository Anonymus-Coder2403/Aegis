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

## V2 Current Implementation (2026-03-31)

### Implemented Components

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI Backend | ✅ Complete | Port 8000, all CRUD endpoints |
| InMemoryRAG Engine | ✅ Complete | Hybrid search in-memory |
| BM25 Search | ✅ Complete | Custom implementation in bm25.py |
| Vector Search | ✅ Complete | EmbeddingGenerator with BGE-M3 (falls back to dummy on failure) |
| RRF Fusion | ✅ Complete | hybrid.py - rrf_fusion and weighted_fusion |
| LLM Providers | ✅ Complete | Gemini (google-genai) + **Groq (openai/gpt-oss-120b)** |
| Chunking | ✅ Complete | PDF, recursive, section chunkers |
| Storage | ✅ Complete | LocalStorageClient + S3Client |
| Context7 MCP | ⚠️ Stub | MCP server stub exists |
| Redis Caching | ❌ Not Started | Planned for future |
| Celery Tasks | ❌ Not Started | Planned for future |
| LangGraph Agentic | ❌ Not Started | Planned for future |
| Langfuse Observability | ❌ Not Started | Planned for future |

### Current Architecture: In-Memory MVP

The system currently runs with **no external dependencies** for rapid development:

- **No PostgreSQL required** - Documents stored in `InMemoryRAG.documents` (Dict)
- **No Redis required** - In-memory indexes rebuilt on document add
- **No OpenSearch required** - Custom BM25 + Vector implementation (OpenSearch client ready for future)
- **Works offline** - Requires only LLM API key (Groq or Gemini) or runs in mock mode

### LLM Provider Configuration

```env
# Default: Groq with openai/gpt-oss-120b
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_key
GROQ_MODEL=openai/gpt-oss-120b

# Alternative: Gemini
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.0-flash
```

### API Endpoints (All Implemented)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root info |
| `/health` | GET | Health check with LLM provider info |
| `/upload` | POST | Upload document with chunking |
| `/test-documents` | GET | List test documents |
| `/test-documents/{filename}/upload` | POST | Upload test document |
| `/documents` | GET | List all documents |
| `/documents/{doc_id}` | GET | Get specific document |
| `/documents/{doc_id}` | DELETE | Delete document |
| `/query` | POST | Full RAG query (search + LLM) |
| `/search` | GET | Search only (no LLM) |
| `/docs` | GET | Swagger UI |

### Code Structure

```
src/aegis/
├── config.py              ✅ Settings (LLM, storage, search, chunking)
├── api/
│   ├── main.py           ✅ FastAPI app, InMemoryRAG, all endpoints
│   └── routers/
│       ├── ingest.py     ✅ ChunkingStrategy enum
│       └── search.py     ⚠️ Skeleton
├── services/
│   ├── llm/
│   │   ├── __init__.py   ✅ Exports
│   │   ├── types.py     ✅ LLMResponse, MockLLM (shared)
│   │   ├── gemini.py    ✅ GeminiLLM (google-genai SDK)
│   │   └── groq.py      ✅ GroqLLM (Groq API)
│   ├── search/
│   │   ├── bm25.py      ✅ BM25Search
│   │   ├── vector.py    ✅ VectorSearch, EmbeddingGenerator
│   │   ├── hybrid.py    ✅ rrf_fusion, weighted_fusion
│   │   └── reranker.py  ⚠️ Skeleton
│   ├── storage/
│   │   ├── __init__.py  ✅ Exports
│   │   └── s3_client.py ✅ LocalStorageClient, S3Client
│   └── mcp_server/
│       └── __init__.py  ✅ Context7MCPServer stub
├── chunking/
│   ├── base.py          ✅ Chunk, ChunkingConfig, BaseChunker
│   ├── pdf_chunker.py   ✅ PDFChunker, PDFProcessor
│   ├── recursive_chunker.py ✅ RecursiveChunker
│   └── section_chunker.py   ✅ SectionChunker
└── __init__.py
```

### Running the System

```bash
# Start server
python -m uvicorn src.aegis.api.main:app --host 0.0.0.0 --port 8000 --reload

# Test health
curl http://localhost:8000/health

# Upload document
curl -X POST http://localhost:8000/test-documents/persistent-annual-report-2024.pdf/upload

# Query with LLM
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize this document", "top_k": 5, "use_llm": true}'
```

## V2 Key Architecture Decisions

- General-purpose RAG: any PDF, any question, pure retrieval + generation
- OpenSearch for all search (BM25 + kNN + RRF fusion) — no pgvector
- BGE-M3 embeddings (sparse+dense in one pass)
- Gemini 2.5 Flash via `google-genai` SDK (LiteLLM dropped)
- **Groq API supported** via `openai/gpt-oss-120b` model for faster inference
- LangGraph for agentic workflows
- Cloud-first (AWS), Docker Compose for dev
- Small targeted retrieval (2-4K tokens) — never stuff the context window
- Weather/AC ported from v1 later, not removed

## V2 Non-Negotiable Rules

- LLM never directly calls external APIs, FastAPI endpoints, or search indexes
- Python controls all I/O and retrieval decisions
- RAG answers must be grounded in retrieved context — say so if not found
- All search through OpenSearch — no secondary vector stores
- LLM calls via `google-genai` SDK or `groq` SDK — no LiteLLM

## V1 (frozen on `v1` branch)

V1 had 88 tests, three features (Billing RAG, Weather, AC Control), LiteLLM + ChromaDB + sentence-transformers. See `v1` branch for full code and docs.

## Git Branching

- `v1` branch — frozen v1 permanently
- `v2` branch — active development, merges to `master` via PR
- `master` — currently v1 code, will be v2 after PR merge

## Notes for Future Sessions

- Do not reopen decided v2 architecture choices unless explicitly requested
- Resume brainstorming from API surface question
- Prefer updating `ARCHITECTURE_LOCK.md` and `PROJECT_CONTEXT_HANDOFF.md` first, then mirror concise changes here
- Keep this file practical and implementation-aligned, not speculative
