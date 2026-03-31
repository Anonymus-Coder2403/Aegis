# Aegis V2 Implementation Plan

## Project Overview

**Aegis V2** is a general-purpose document RAG system that evolved from a billing-specific v1 prototype. It handles 10,000+ page PDFs with hybrid search (BM25 + kNN), agentic features, and cloud deployment readiness.

### V2 Locked Stack

| Component | Technology |
|-----------|------------|
| LLM | Gemini 2.5 Flash via `google-genai` SDK |
| Search | OpenSearch (BM25 + kNN hybrid) |
| Database | PostgreSQL (metadata only) |
| Embeddings | BGE-M3 (self-hosted, MIT, 1024 dims) |
| Cache | Redis |
| Async | Celery + Redis |
| Agentic | LangGraph |
| API | FastAPI |
| Observability | Langfuse |
| Container | Docker Compose |

---

## Implementation Status (2026-03-31)

| Phase | Status | Notes |
|-------|--------|-------|
| **Day 1: Infrastructure & FastAPI Setup** | ✅ Complete | FastAPI app with all endpoints, in-memory storage |
| **Day 2: Database & OpenSearch Integration** | ⚠️ Partial | In-memory implementation (OpenSearch client ready) |
| **Day 3: Advanced Chunking & File Storage** | ✅ Complete | PDF, recursive, section chunkers, storage clients |
| **Day 4: Hybrid Search Implementation** | ✅ Complete | BM25, Vector, RRF fusion, weighted fusion |
| **Day 5: Caching Layer & Async Tasks** | ❌ Not Started | Redis caching planned |
| **Day 6: Agentic RAG (LangGraph)** | ❌ Not Started | Agentic features planned |
| **Day 7: Observability & Testing** | ❌ Not Started | Langfuse integration planned |

---

## Implementation Phases (7 Days)

### Day 1: Infrastructure & FastAPI Setup

**Goal**: Basic API skeleton running in Docker

| Person | Tasks |
|--------|-------|
| **Person A** | Create `src/aegis/api/` module, `main.py` with FastAPI lifespan, `deps.py` for dependencies (get_db, get_cache), health check endpoint |
| **Person B** | Create `config.py`, `Dockerfile`, `docker-compose.yml` with all services (FastAPI, OpenSearch, PostgreSQL, Redis, Celery) |

**Files to create:**

- `src/aegis/api/__init__.py`
- `src/aegis/api/main.py`
- `src/aegis/api/deps.py`
- `src/aegis/api/routers/health.py`
- `src/aegis/config.py`
- `Dockerfile`
- `docker-compose.yml`

### Day 2: Database & OpenSearch Integration

**Goal**: Data models and search engine connectivity

| Person | Tasks |
|--------|-------|
| **Person A** | SQLAlchemy models (Document, Chunk, Session), database setup with pgvector, document upload endpoints |
| **Person B** | OpenSearch client, create BM25 + Vector indexes, hybrid search logic |

**Files to create:**

- `src/aegis/db/models.py`
- `src/aegis/db/base.py`
- `src/aegis/services/opensearch/client.py`
- `src/aegis/services/opensearch/indexes.py`
- `src/aegis/services/opensearch/search.py`
- `src/aegis/api/routers/documents.py`

### Day 3: Advanced Chunking & File Storage

**Goal**: PDF processing pipeline for 10K+ pages

| Person | Tasks |
|--------|-------|
| **Person A** | Chunkers: Base interface, section-aware, recursive with overlap, PDF-specific chunking |
| **Person B** | S3-compatible storage client, ingestion endpoint, Celery task setup |

**Files to create:**

- `src/aegis/chunking/base.py`
- `src/aegis/chunking/section_chunker.py`
- `src/aegis/chunking/recursive_chunker.py`
- `src/aegis/chunking/pdf_chunker.py`
- `src/aegis/services/storage/s3_client.py`
- `src/aegis/api/routers/ingest.py`

### Day 4: Hybrid Search Implementation

**Goal**: Working BM25 + Vector + RRF fusion

| Person | Tasks |
|--------|-------|
| **Person A** | BM25 search implementation, vector search implementation, RRF fusion algorithm |
| **Person B** | Re-ranking (optional), unified search API endpoint, unit tests |

**Files to create:**

- `src/aegis/services/search/bm25.py`
- `src/aegis/services/search/vector.py`
- `src/aegis/services/search/hybrid.py`
- `src/aegis/services/search/reranker.py`
- `src/aegis/api/routers/search.py`

### Day 5: Caching Layer & Async Tasks

**Goal**: Redis caching and Celery workers

| Person | Tasks |
|--------|-------|
| **Person A** | Redis client, query cache, embedding cache, rate limiting middleware |
| **Person B** | Cache middleware, Celery app setup, document processing tasks |

**Files to create:**

- `src/aegis/services/cache/redis.py`
- `src/aegis/services/cache/query_cache.py`
- `src/aegis/services/cache/embedding_cache.py`
- `src/aegis/middleware/rate_limiter.py`
- `src/aegis/middleware/cache_middleware.py`
- `src/aegis/workers/celery_app.py`
- `src/aegis/workers/tasks/document_tasks.py`

### Day 6: Agentic RAG (LangGraph)

**Goal**: Intelligent query handling with query rewriting, document grading, guardrails

| Person | Tasks |
|--------|-------|
| **Person A** | LangGraph nodes: guardrail, retrieve, grade, rewrite, generate |
| **Person B** | LangGraph workflow orchestration, agentic API endpoint |

**Files to create:**

- `src/aegis/agents/nodes/guardrail.py`
- `src/aegis/agents/nodes/retrieve.py`
- `src/aegis/agents/nodes/grade.py`
- `src/aegis/agents/nodes/rewrite.py`
- `src/aegis/agents/nodes/generate.py`
- `src/aegis/agents/agentic_rag.py`
- `src/aegis/api/routers/agentic.py`

### Day 7: Observability & Testing

**Goal**: Langfuse tracing and test coverage

| Person | Tasks |
|--------|-------|
| **Person A** | Langfuse setup, integrate tracing into endpoints |
| **Person B** | Unit tests (hybrid search, chunking, agentic flow), update README |

**Files to create:**

- `src/aegis/services/langfuse/tracing.py`
- `tests/test_hybrid_search.py`
- `tests/test_chunking.py`
- `tests/test_agentic_rag.py`

---

## Recommended Work Distribution

| Week | Person A (Focus) | Person B (Focus) |
|------|------------------|-------------------|
| **Day 1** | FastAPI API skeleton | Docker/Config |
| **Day 2** | Database models | OpenSearch |
| **Day 3** | Chunking logic | Storage + Ingest |
| **Day 4** | BM25 + Vector | Search API + Tests |
| **Day 5** | Caching | Celery Workers |
| **Day 6** | LangGraph Nodes | Agentic Flow |
| **Day 7** | Tracing | Tests + Docs |

---

## Getting Started (From Scratch)

```bash
# 1. Clone and checkout v2 branch
git clone <repo>
git checkout v2

# 2. Set up environment
cp .env.example .env
# Fill in: GEMINI_API_KEY, OPENSEARCH_URL, POSTGRES_URL, REDIS_URL

# 3. Start infrastructure
docker compose up -d

# 4. Verify services
curl http://localhost:8000/health

# 5. Run specific day tasks (coordinate with partner)
```

---

## Key Dependencies to Install

```toml
fastapi = ">=0.115.0"
uvicorn = {version = ">=0.32.0", extras = ["standard"]}
python-multipart = ">=0.0.20"
psycopg2-binary = ">=2.9.9"
sqlalchemy = ">=2.0.0"
asyncpg = ">=0.29.0"
alembic = ">=1.13.0"
celery = ">=5.3.0"
redis = ">=5.0.0"
boto3 = ">=1.34.0"
aiobotocore = ">=2.12.0"
google-genai = ">=0.8.0"
langgraph = ">=0.2.0"
langfuse = ">=3.0.0"
```

---

## Important Rules

1. **No LiteLLM** — Use `google-genai` SDK directly
2. **All search via OpenSearch** — No secondary vector stores
3. **Small context retrieval** — 2-4K tokens max per query
4. **Grounded answers** — Say "not found" if no context
5. **Python controls I/O** — LLM never calls external APIs directly

---

## Docker Compose Services

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://aegis:aegis@postgres:5432/aegis
      - REDIS_URL=redis://redis:6379
      - OPENSEARCH_URL=https://opensearch:9200
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    depends_on:
      - postgres
      - redis
      - opensearch

  worker:
    build: .
    command: celery -A src.aegis.workers.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://aegis:aegis@postgres:5432/aegis
      - REDIS_URL=redis://redis:6379
      - OPENSEARCH_URL=https://opensearch:9200
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    depends_on:
      - postgres
      - redis
      - opensearch

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: aegis
      POSTGRES_PASSWORD: aegis
      POSTGRES_DB: aegis
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  opensearch:
    image: opensearchproject/opensearch:2.19.0
    environment:
      discovery.type: single-node
      OPENSEARCH_INITIAL_ADMIN_PASSWORD: admin123
    volumes:
      - opensearch_data:/usr/share/opensearch/data
```

---

## Expected Outcomes

| Metric | V1 (frozen) | V2 MVP (Current) | After Full Implementation |
|--------|-------------|------------------|-------------------------|
| **Max document size** | ~100 pages | 10,000+ pages | 10,000+ pages |
| **Search quality** | ChromaDB vector | Hybrid (BM25 + Vector) | Hybrid (BM25 + Vector) |
| **Response time** | 5-10s | <3s | <3s (with cache) |
| **LLM Provider** | LiteLLM | Gemini + Groq | Gemini + Groq |
| **API costs** | Full price | Pay per call | 50%+ reduction (cache) |
| **Observability** | None | None | Full tracing (Langfuse) |
| **Rate limiting** | None | None | Built-in |
| **Async processing** | None | None | Celery tasks |
| **File storage** | Local | Local + S3 ready | S3-compatible |
| **Cloud-ready** | No | Partial | Yes |

---

## RRF Fusion Formula

```python
def rrf_fusion(bm25_results, vector_results, k=60):
    scores = defaultdict(float)
    for rank, doc in enumerate(bm25_results):
        scores[doc.id] += 1 / (k + rank)
    for rank, doc in enumerate(vector_results):
        scores[doc.id] += 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

---

## Chunking Strategy for 10K Pages

1. Upload PDF to S3 storage
2. Parse PDF structure (headings, sections)
3. Identify section boundaries
4. Chunk by sections (not fixed size)
5. Add overlap (50-100 words)
6. Store metadata (page, section, headings)
7. Process in batches (Celery tasks)

---

## Cache Strategy

```python
# Query cache: 1 hour TTL
cache_key = f"query:{hash(question)}"

# Embedding cache: 24 hour TTL
cache_key = f"embed:{hash(text)}"

# LLM response cache: 1 hour TTL
cache_key = f"llm:{hash(prompt + context)}"
```

---

## LangGraph Workflow

```
User Query → Guardrail (check relevance)
          → Retrieve (hybrid search)
          → Grade (relevance score)
          → Rewrite (if low relevance)
          → Generate (final answer)
```

---

## Cloud Deployment Readiness (AWS)

| Current (Local) | AWS Cloud (Future) |
|-----------------|-------------------|
| Docker Compose | ECS / EKS |
| Local PostgreSQL | RDS PostgreSQL |
| Local Redis | ElastiCache Redis |
| Local OpenSearch | OpenSearch Service |
| Local File Storage | S3 |
| Celery + Redis | SQS + Lambda |

---

## Reference

- [production-agentic-rag-course](https://github.com/jamwithai/production-agentic-rag-course) - 5.3K stars
