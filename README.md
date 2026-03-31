# Aegis - Production Document RAG System

A high-performance document RAG (Retrieval-Augmented Generation) system with hybrid search capabilities, multiple LLM provider support, and production-ready architecture.

## Version

**V2 (In Development)** - See `Context/ARCHITECTURE_LOCK.md` for locked architecture decisions.

---

## Features

| Feature | Status | Description |
|---------|--------|-------------|
| Hybrid Search | DONE | BM25 + Vector search with RRF fusion |
| Multi-LLM Support | DONE | Gemini (google-genai) + Groq (openai/gpt-oss-120b) |
| PDF Chunking | DONE | PDF, recursive, and section-based chunking |
| Local Storage | DONE | LocalStorageClient + S3-compatible storage |
| MCP Server | PARTIAL | Context7 MCP server stub |
| Redis Caching | TODO | Planned for production |
| Celery Tasks | TODO | Planned for async processing |
| LangGraph Agentic | TODO | Planned for agentic features |
| Langfuse Observability | TODO | Planned for tracing |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.10+ |
| **API Framework** | FastAPI |
| **LLM Providers** | Gemini 2.5 Flash (google-genai), Groq (openai/gpt-oss-120b) |
| **Search** | In-memory BM25 + Vector (OpenSearch-ready) |
| **Embeddings** | BGE-M3 (with graceful fallback) |
| **Storage** | Local + S3-compatible |
| **Configuration** | Pydantic Settings |

---

## Project Structure

```
src/aegis/
├── config.py                    # Application settings
├── api/
│   ├── main.py                  # FastAPI app, InMemoryRAG, endpoints
│   └── routers/
│       ├── ingest.py            # ChunkingStrategy enum
│       └── search.py            # Search router (skeleton)
├── services/
│   ├── llm/
│   │   ├── __init__.py          # Exports
│   │   ├── types.py             # LLMResponse, MockLLM
│   │   ├── gemini.py            # GeminiLLM
│   │   └── groq.py              # GroqLLM
│   ├── search/
│   │   ├── bm25.py              # BM25Search
│   │   ├── vector.py            # VectorSearch, EmbeddingGenerator
│   │   ├── hybrid.py            # rrf_fusion, weighted_fusion
│   │   └── reranker.py          # Reranker (skeleton)
│   ├── storage/
│   │   ├── __init__.py          # Exports
│   │   └── s3_client.py         # LocalStorageClient, S3Client
│   └── mcp_server/
│       └── __init__.py          # Context7MCPServer
├── chunking/
│   ├── base.py                  # Chunk, ChunkingConfig, BaseChunker
│   ├── pdf_chunker.py           # PDFChunker, PDFProcessor
│   ├── recursive_chunker.py    # RecursiveChunker
│   └── section_chunker.py       # SectionChunker
└── __init__.py
```

---

## Installation

### 1. Clone and Setup

```bash
# Clone repository
git clone <repo>
cd Aegis

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create `.env` file:

```env
# LLM Configuration (choose one or both)

# Groq (default - faster inference)
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b

# Or Gemini
GEMINI_API_KEY=your_gemini_api_key
LLM_MODEL=gemini-2.0-flash

# Storage Configuration
STORAGE_MODE=local

# Search Configuration
DEFAULT_CHUNK_SIZE=512
DEFAULT_CHUNK_OVERLAP=50
RRF_K=60
BM25_WEIGHT=0.5

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

---

## Running the Server

### Development

```bash
python -m uvicorn src.aegis.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production

```bash
python -m uvicorn src.aegis.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root information |
| `/health` | GET | Health check with LLM provider info |
| `/docs` | GET | Swagger UI |
| `/upload` | POST | Upload document with chunking |
| `/test-documents` | GET | List test documents |
| `/test-documents/{filename}/upload` | POST | Upload test document |
| `/documents` | GET | List all documents |
| `/documents/{doc_id}` | GET | Get specific document |
| `/documents/{doc_id}` | DELETE | Delete document |
| `/query` | POST | Full RAG query (search + LLM) |
| `/search` | GET | Search only (no LLM) |

---

## Usage Examples

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "documents": 0,
  "chunks": 0,
  "llm_provider": "groq",
  "llm_model": "openai/gpt-oss-120b"
}
```

### Upload Document

```bash
curl -X POST "http://localhost:8000/test-documents/persistent-annual-report-2024.pdf/upload"
```

Response:
```json
{
  "document_id": "uuid-string",
  "filename": "persistent-annual-report-2024.pdf",
  "status": "uploaded",
  "chunks_count": 42,
  "message": "Document uploaded and indexed with 42 chunks"
}
```

### Search Only

```bash
curl "http://localhost:8000/search?q=revenue&top_k=5"
```

### Full RAG Query with LLM

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the total revenue?",
    "top_k": 5,
    "use_llm": true,
    "fusion": "rrf"
  }'
```

Response:
```json
{
  "answer": "Based on the context, the total revenue was...",
  "sources": [
    {
      "chunk_id": "doc_123_0",
      "text": "Revenue section text...",
      "score": 0.85,
      "rank": 1,
      "document_id": "doc_123"
    }
  ],
  "query": "What is the total revenue?"
}
```

---

## Technical Implementation

### InMemoryRAG Architecture

The core `InMemoryRAG` class manages the entire RAG pipeline:

```
Document Upload
      |
      v
+-----------------+
|  Chunking      |  PDFChunker -> RecursiveChunker -> SectionChunker
|  (PDF/Text)    |
+--------+--------+
         |
         v
+-----------------+
|  Storage       |  LocalStorageClient / S3Client
|  (File Save)   |
+--------+--------+
         |
         v
+-----------------+
|  Indexing      |  BM25Search.index_documents()
|  (Reindex)     |  VectorSearch.index_documents()
+--------+--------+
         |
         v
+-----------------+
|  Query         |
|  Pipeline      |
+--------+--------+
         |
         v
+------------------------------------------+
|  Hybrid Search                           |
|  +-------------+    +-------------+     |
|  | BM25 Search | +  |Vector Search|     |
|  | (keyword)   |    | (semantic)  |     |
|  +------+------+    +------+------+     |
|         +-------------+                   |
|                  v                        |
|         +----------------+               |
|         | RRF Fusion     |               |
|         | (rank fusion)  |               |
|         +--------+-------+               |
+------------------+-----------------------+
                   |
                   v
+------------------------------------------+
|  LLM Generation (Optional)               |
|  +-------------+    +-------------+      |
|  |   Gemini    | or |   Groq      |      |
|  +-------------+    +-------------+      |
+------------------------------------------+
                   |
                   v
              Final Response
```

### Hybrid Search Implementation

**RRF (Reciprocal Rank Fusion)**:

```python
def rrf_fusion(bm25_results, vector_results, k=60):
    scores = defaultdict(float)
    for rank, result in enumerate(bm25_results):
        scores[result.chunk_id] += 1 / (k + rank)
    for rank, result in enumerate(vector_results):
        scores[result.chunk_id] += 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**Weighted Fusion**:

```python
def weighted_fusion(bm25_results, vector_results, bm25_weight=0.5):
    # Normalize scores and apply weights
    normalized_bm25 = [r.score / max_bm25 for r in bm25_results]
    normalized_vector = [r.score / max_vector for r in vector_results]
    # Combine with weights
    ...
```

### Chunking Strategies

1. **PDF Chunking**: Page-based + recursive for large pages
   - Uses PyPDF2 to extract page text
   - Splits large pages recursively
   - Preserves page metadata

2. **Recursive Chunking**: Fixed size with overlap
   - Splits text into chunks of `chunk_size`
   - Adds `chunk_overlap` for context continuity

3. **Section Chunking**: Heading-aware splitting
   - Detects headings (#, numbers, roman numerals)
   - Splits on section boundaries
   - Merges small chunks

### LLM Provider Integration

```python
from aegis.services.llm import get_llm_provider

# Automatically selects based on settings.llm_provider
llm = get_llm_provider()

# Gemini (synchronous)
response = llm.generate(prompt="...", system_prompt="...")

# Groq (asynchronous)
response = await llm.generate_async(prompt="...", system_prompt="...")
```

### Configuration Flow

```python
# config.py
class Settings(BaseSettings):
    llm_provider: str = "gemini"  # or "groq"
    groq_model: str = "openai/gpt-oss-120b"
    gemini_api_key: str = ""
    groq_api_key: str = ""

# selection in get_llm_provider()
if settings.llm_provider == "groq":
    return GroqLLM()
return GeminiLLM()
```

---

## Configuration Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `LLM_PROVIDER` | `gemini` | LLM provider: `gemini` or `groq` |
| `GEMINI_API_KEY` | (empty) | Google Gemini API key |
| `GROQ_API_KEY` | (empty) | Groq API key |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq model name |
| `LLM_MODEL` | `gemini-2.0-flash` | Gemini model name |
| `STORAGE_MODE` | `local` | Storage mode: `local` or `s3` |
| `DEFAULT_CHUNK_SIZE` | `512` | Default chunk size in characters |
| `DEFAULT_CHUNK_OVERLAP` | `50` | Chunk overlap |
| `RRF_K` | `60` | RRF k parameter |
| `BM25_WEIGHT` | `0.5` | BM25 weight in weighted fusion |
| `DEFAULT_TOP_K` | `5` | Default number of results |

---

## Future Enhancements

- [ ] Redis caching for API cost reduction
- [ ] Celery async task processing
- [ ] LangGraph agentic workflows
- [ ] Langfuse observability
- [ ] OpenSearch integration for production
- [ ] PostgreSQL metadata storage
- [ ] Docker Compose deployment
- [ ] AWS cloud deployment

---

## Context Files

See `Context/` directory for detailed architecture and implementation plans:

- `ARCHITECTURE_LOCK.md` - Locked architecture decisions
- `IMPLEMENTATION_PLAN.md` - Implementation phases
- `2026-03-29-production-rag-plan.md` - Production RAG plan
- `CLAUDE.md` - Current implementation status
- `PROJECT_CONTEXT_HANDOFF.md` - Project handoff details

---

## License

MIT

---

## Reference

- [production-agentic-rag-course](https://github.com/jamwithai/production-agentic-rag-course)
- [Google GenAI SDK](https://github.com/google/generative-ai-python)
- [Groq API](https://console.groq.com/docs)