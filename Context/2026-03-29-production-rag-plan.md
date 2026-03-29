# Production RAG Implementation Plan

**Date**: 2026-03-29  
**Goal**: Advanced RAG architecture for 10,000+ page documents  
**Timeline**: 7 days  
**Status**: Approved - Ready for Implementation

---

## Executive Summary

This plan outlines the implementation of a production-ready advanced RAG architecture to handle large documents (10,000+ pages). Based on the production-agentic-rag-course (5.3K stars) and industry best practices, aligned with the AWS cloud architecture screenshot.

### Key Goals
1. Handle 10,000+ page PDF documents efficiently
2. Implement hybrid search (BM25 + Vector) with RRF fusion
3. Add Redis caching layer (50%+ API cost reduction)
4. Add S3-compatible file storage for documents
5. Add Celery for async task processing
6. Add rate limiting for production deployment
7. Add agentic features (query rewriting, document grading)
8. Add Langfuse observability
9. Design for cloud deployment readiness (AWS-compatible)

---

## Architecture Diagram (Updated)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTS                                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   │
│  │  Streamlit  │   │   Swagger   │   │  Gradio    │   │  Web/Mobile │   │
│  │  (current)  │   │   (new)     │   │  (new)     │   │   (future)  │   │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   │
└─────────┼──────────────────┼──────────────────┼──────────────────┼───────────┘
          │                  │                  │                  │
          ▼                  ▼                  ▼                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI BACKEND (Port 8000)                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  API ROUTES                                                            ││
│  │  GET  /health              - Health check                              ││
│  │  POST /api/v1/search       - Hybrid search (BM25 + Vector)            ││
│  │  POST /api/v1/ask          - RAG query                                 ││
│  │  POST /api/v1/stream       - Streaming RAG                             ││
│  │  POST /api/v1/documents    - Upload/document management               ││
│  │  POST /api/v1/ingest       - Async document ingestion                 ││
│  │  GET  /docs                - Swagger UI                                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  MIDDLEWARE                                                            ││
│  │  • Rate Limiting (slowapi)    • CORS                    • Auth (JWT) ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
     ┌────────────────────────────┼────────────────────────────┐
     │                            │                            │
     ▼                            ▼                            ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐
│   HYBRID        │    │    CACHING      │    │      AGENTIC            │
│   SEARCH        │    │    (Redis)      │    │      (LangGraph)        │
│   ─────────     │    │  ─────────      │    │  ─────────────         │
│   OpenSearch    │    │  • Query cache │    │  • Query Rewriting     │
│   • BM25        │    │  • Embed cache │    │  • Document Grading    │
│   • Vector      │    │  • LLM cache   │    │  • Guardrails          │
│   • RRF fusion  │    │                 │    │  • Adaptive Retrieval  │
└────────┬────────┘    └────────┬────────┘    └────────────┬────────────┘
         │                       │                         │
         ▼                       ▼                         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐
│   OPENSEARCH    │    │     REDIS       │    │       LITELLM           │
│   (Port 9200)   │    │    (Port 6379) │    │     (Gemini/Claude)     │
│                 │    │                 │    │                         │
│ • BM25 Index   │    │  Cache layer    │    │  LLM Generation        │
│ • Vector Index │    │  Session store  │    │                         │
└────────┬────────┘    └────────┬────────┘    └────────────┬────────────┘
         │                       │                         │
         ▼                       ▼                         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐
│   POSTGRESQL    │    │   CELERY        │    │      S3/STORAGE         │
│   (Port 5432)   │    │  (Async Tasks)  │    │  (File Storage)        │
│                 │    │                 │    │                         │
│  • pgvector    │    │  • PDF ingest   │    │  • Document uploads    │
│  • Documents   │    │  • Embeddings   │    │  • Chunked files      │
│  • Sessions    │    │  • Re-ranking   │    │  • Cloud-ready        │
└────────┬────────┘    └────────┬────────┘    └────────┬────────────┘
         │                       │                         │
         └───────────────────────┼─────────────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │    LANGFUSE     │
                        │  (Observability) │
                        └─────────────────┘
```

---

## Decision Summary

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Hybrid Search** | OpenSearch | BM25 + Vector built-in, RRF fusion |
| **Metadata Storage** | PostgreSQL | Production standard |
| **Vector Storage** | pgvector | Inside PostgreSQL, cost-effective |
| **Caching** | Redis | 50%+ API cost reduction |
| **Async Tasks** | Celery + Redis | PDF processing, embeddings |
| **File Storage** | S3-compatible (local for MVP) | Cloud-ready design |
| **Docker** | Yes | Full production setup |
| **Agentic Features** | Yes | Query rewriting + document grading |
| **Observability** | Langfuse | Full tracing |

---

## Cloud Deployment Readiness

The architecture is designed to be AWS-compatible for future deployment:

| Current (Local) | AWS Cloud (Future) |
|-----------------|-------------------|
| Docker Compose | ECS / EKS |
| Local PostgreSQL | RDS PostgreSQL |
| Local Redis | ElastiCache Redis |
| Local OpenSearch | OpenSearch Service |
| Local File Storage | S3 |
| Celery + Redis | SQS + Lambda |
| FastAPI | API Gateway + Lambda |

---

## Day-by-Day Implementation Plan

### Day 1: Infrastructure & FastAPI Setup

| Task | Files | Description |
|------|-------|-------------|
| 1.1 | `src/aegis/api/__init__.py` | Create API module |
| 1.2 | `src/aegis/api/main.py` | FastAPI app with lifespan |
| 1.3 | `src/aegis/api/deps.py` | Dependencies (get_db, get_cache) |
| 1.4 | `src/aegis/api/routers/health.py` | Health check endpoint |
| 1.5 | `src/aegis/config.py` | Add API config |
| 1.6 | `Dockerfile` | Create FastAPI Dockerfile |
| 1.7 | `docker-compose.yml` | Full stack (FastAPI + OpenSearch + Postgres + Redis + Celery) |

**New Dependencies:**
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
boto3 = ">=1.34.0"  # S3-compatible
aiobotocore = ">=2.12.0"  # Async S3
```

---

### Day 2: Database & OpenSearch Integration

| Task | Files | Description |
|------|-------|-------------|
| 2.1 | `src/aegis/db/models.py` | SQLAlchemy models (Document, Chunk, Session) |
| 2.2 | `src/aegis/db/base.py` | Database setup + pgvector |
| 2.3 | `src/aegis/services/opensearch/client.py` | OpenSearch client |
| 2.4 | `src/aegis/services/opensearch/indexes.py` | Create BM25 + Vector indexes |
| 2.5 | `src/aegis/services/opensearch/search.py` | Hybrid search logic |
| 2.6 | `src/aegis/api/routers/documents.py` | Document upload endpoints |

---

### Day 3: Advanced Chunking & File Storage

| Task | Files | Description |
|------|-------|-------------|
| 3.1 | `src/aegis/chunking/base.py` | Base chunker interface |
| 3.2 | `src/aegis/chunking/section_chunker.py` | Section-aware chunking |
| 3.3 | `src/aegis/chunking/recursive_chunker.py` | Recursive chunking with overlap |
| 3.4 | `src/aegis/chunking/pdf_chunker.py` | PDF-specific chunking (10K pages) |
| 3.5 | `src/aegis/services/storage/s3_client.py` | S3-compatible storage client |
| 3.6 | `src/aegis/api/routers/ingest.py` | Document ingestion endpoint |

**Chunking Strategy for 10K Pages:**
1. Upload PDF to S3 storage
2. Parse PDF structure (headings, sections)
3. Identify section boundaries
4. Chunk by sections (not fixed size)
5. Add overlap (50-100 words)
6. Store metadata (page, section, headings)
7. Process in batches (Celery tasks)

---

### Day 4: Hybrid Search Implementation

| Task | Files | Description |
|------|-------|-------------|
| 4.1 | `src/aegis/services/search/bm25.py` | BM25 search implementation |
| 4.2 | `src/aegis/services/search/vector.py` | Vector search implementation |
| 4.3 | `src/aegis/services/search/hybrid.py` | RRF fusion algorithm |
| 4.4 | `src/aegis/services/search/reranker.py` | Re-ranking (optional) |
| 4.5 | `src/aegis/api/routers/search.py` | Unified search API |
| 4.6 | Tests | Unit tests for search module |

**RRF Fusion Formula:**
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

### Day 5: Caching Layer & Async Tasks

| Task | Files | Description |
|------|-------|-------------|
| 5.1 | `src/aegis/services/cache/redis.py` | Redis client setup |
| 5.2 | `src/aegis/services/cache/query_cache.py` | Query result caching |
| 5.3 | `src/aegis/services/cache/embedding_cache.py` | Embedding caching |
| 5.4 | `src/aegis/middleware/rate_limiter.py` | Rate limiting |
| 5.5 | `src/aegis/middleware/cache_middleware.py` | Cache middleware |
| 5.6 | `src/aegis/workers/celery_app.py` | Celery app setup |
| 5.7 | `src/aegis/workers/tasks/document_tasks.py` | Document processing tasks |

**Celery Tasks:**
- `process_pdf` - Upload, parse, chunk PDF
- `generate_embeddings` - Generate embeddings for chunks
- `rerank_results` - Re-rank search results

**Cache Strategy:**
```python
# Query cache: 1 hour TTL
cache_key = f"query:{hash(question)}"
# Embedding cache: 24 hour TTL  
cache_key = f"embed:{hash(text)}"
# LLM response cache: 1 hour TTL
cache_key = f"llm:{hash(prompt + context)}"
```

---

### Day 6: Agentic RAG (LangGraph)

| Task | Files | Description |
|------|-------|-------------|
| 6.1 | `src/aegis/agents/nodes/guardrail.py` | Out-of-domain detection |
| 6.2 | `src/aegis/agents/nodes/retrieve.py` | Retrieval node |
| 6.3 | `src/aegis/agents/nodes/grade.py` | Document grading |
| 6.4 | `src/aegis/agents/nodes/rewrite.py` | Query rewriting |
| 6.5 | `src/aegis/agents/nodes/generate.py` | Generate answer |
| 6.6 | `src/aegis/agents/agentic_rag.py` | LangGraph workflow |
| 6.7 | `src/aegis/api/routers/agentic.py` | Agentic endpoint |

**LangGraph Workflow:**
```
User Query → Guardrail (check relevance)
           → Retrieve (hybrid search)
           → Grade (relevance score)
           → Rewrite (if low relevance)
           → Generate (final answer)
```

---

### Day 7: Observability & Testing

| Task | Files | Description |
|------|-------|-------------|
| 7.1 | `src/aegis/services/langfuse/tracing.py` | Langfuse setup |
| 7.2 | `src/aegis/api/main.py` | Add tracing to endpoints |
| 7.3 | `tests/test_hybrid_search.py` | Search tests |
| 7.4 | `tests/test_chunking.py` | Chunking tests |
| 7.5 | `tests/test_agentic_rag.py` | Agentic flow tests |
| 7.6 | Documentation | Update README + API docs |

---

## Docker Compose Configuration (Updated)

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

| Metric | Current | After Implementation |
|--------|---------|---------------------|
| **Max document size** | ~100 pages | 10,000+ pages |
| **Search quality** | Basic vector | Hybrid (BM25 + Vector) |
| **Response time** | 5-10s | <3s (with cache) |
| **API costs** | Full price | 50%+ reduction (cache) |
| **Observability** | None | Full tracing (Langfuse) |
| **Rate limiting** | None | Built-in |
| **Async processing** | None | Celery tasks |
| **File storage** | Local | S3-compatible |
| **Cloud-ready** | No | Yes |

---

## References

- [production-agentic-rag-course](https://github.com/jamwithai/production-agentic-rag-course) - 5.3K stars
- AWS Architecture screenshot (provided by user)
- OpenSearch for hybrid search (BM25 + Vector)
- pgvector for vector storage inside PostgreSQL
- Redis for caching
- Celery for async tasks
- S3 for file storage
- LangGraph for agentic RAG
- Langfuse for observability
