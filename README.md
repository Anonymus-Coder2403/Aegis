# Aegis Smart Home AI Assistant (V1)

Aegis is an AI-powered smart home assistant with three features: **Billing RAG**, **Weather Advisor**, and **AC Control**. Built as an internship prototype demonstrating Schema-First Modular RAG architecture.

## Features

### Billing RAG
- Parse Indian electricity bills (PVVNL and MSEDCL formats)
- Extract structured data into a canonical schema via PDF text/table extraction
- Store and index bill data in ChromaDB (3 collections: fields, charges, history)
- Answer natural language questions grounded in bill evidence
- Deterministic answers for exact fields, LLM-powered for complex queries

### Weather Advisor
- Fetch live weather data from OpenWeatherMap API (with mock fallback)
- Generate contextual advice using Gemini 2.5 Flash via LiteLLM

### AC Control
- Mock hardware server (FastAPI on port 8765): on/off/status
- Natural language intent classification via LLM with keyword fallback
- HTTP client for action execution

### Orchestrator
- Keyword-based routing to weather / AC / billing
- LLM fallback for ambiguous queries
- CLI: `uv run aegis ask "<question>"`

### Streamlit UI
- Three-tab prototype: Billing / Weather Advisor / AC Control
- Upload bill PDFs, ask questions, get weather advice, control AC

## Architecture

```
User Query
    |
    v
Orchestrator (keyword routing + LLM fallback)
    |
    +-- Billing --> PDF Extract --> Parse --> ChromaDB --> Query --> Answer
    +-- Weather --> OpenWeatherMap API --> LLM Advice
    +-- AC      --> Intent Classify --> Mock Hardware Server
```

**RAG Architecture:** Schema-First Modular RAG
- PDF extraction: pdfplumber (tables) + PyMuPDF (text) + EasyOCR (scanned fallback)
- Canonical schema: `CanonicalBill` dataclass with amounts, charges, consumption, history
- Vector store: ChromaDB with L2 distance, 1.0 threshold
- Embeddings: sentence-transformers `all-MiniLM-L6-v2`
- LLM: Gemini 2.5 Flash via LiteLLM 1.82.6

## Project Structure

```
src/aegis/
├── core/
│   ├── config.py              # AegisConfig
│   └── orchestrator.py        # Keyword routing + CLI
├── billing/
│   ├── types.py               # CanonicalBill schema
│   ├── config.py              # BillingConfig
│   ├── answerer.py            # answer_billing_question()
│   ├── query_classifier.py    # Query intent routing
│   ├── llm_formatter.py       # Grounded answer formatting
│   ├── cli.py                 # Billing CLI (inspect/ingest/query)
│   ├── parser/
│   │   ├── extractors.py      # PDF text/table extraction
│   │   ├── normalize.py       # Field normalization
│   │   ├── pvvnl_parser.py    # PVVNL bill parser
│   │   └── msedcl_parser.py   # MSEDCL bill parser
│   └── rag/
│       ├── embeddings.py      # sentence-transformers wrapper
│       ├── retriever.py       # ChromaDB retrieval + metadata filtering
│       └── store.py           # Canonical JSON + ChromaDB persistence
├── weather/
│   ├── fetcher.py             # OpenWeatherMap + mock fallback
│   └── advisor.py             # LLM weather advice
├── ac_control/
│   ├── server.py              # FastAPI mock hardware (port 8765)
│   ├── classifier.py          # LLM intent + keyword fallback
│   └── client.py              # httpx client
└── ui/
    └── streamlit_app.py       # 3-tab prototype UI
```

## Requirements

- Python 3.10+
- `uv` package manager

## Setup

```bash
uv sync --group dev
```

Create a `.env` file:
```
GEMINI_API_KEY=your_gemini_api_key
OPENWEATHERMAP_API_KEY=your_openweather_key  # optional
```

## Usage

```bash
# Orchestrator CLI
uv run aegis ask "What is my electricity bill due date?"

# Billing CLI
uv run aegis-billing query --question "Show charge breakdown" --pdf data/document_pdf.pdf

# Inspect bill (parse without ingestion)
uv run aegis-billing inspect --pdf data/document_pdf.pdf

# AC mock server
uv run aegis-ac-server

# Streamlit UI
uv run python -m streamlit run src/aegis/ui/streamlit_app.py
```

## Tests

```bash
# Full suite (172 tests)
uv run python -m pytest tests/ -v

# Unit tests only (no API key needed)
uv run python -m pytest tests/ -v -m "not integration"

# Integration tests (needs GEMINI_API_KEY)
uv run python -m pytest tests/integration/ -v -m integration
```

> **Windows note:** `uv run pytest` fails with "Failed to canonicalize script path". Always use `uv run python -m pytest` instead.

## Test Coverage (172 tests)

| Category | Tests | Description |
|---|---|---|
| Billing CLI | 11 | CLI argument parsing, inspect/ingest/query flows |
| Answerer grounding | 22 | Query routing, field resolution, evidence grounding |
| LLM formatter | 7 | Deterministic formatting, snippet handling |
| Retriever logic | 12 | ChromaDB retrieval, distance threshold, metadata filtering |
| Embeddings | 6 | Model loading, embedding dimensions, caching |
| Store persistence | 8 | Canonical JSON, ChromaDB upsert, bill loading |
| Query classifier | 24 | Intent classification across all query types |
| PVVNL parser | 14 | PVVNL bill field extraction |
| MSEDCL parser | 12 | MSEDCL bill field extraction |
| PDF extractors | 8 | Real PDF text/table extraction |
| Format detection | 12 | DISCOM format identification, unsupported bill handling |
| AC classifier | 8 | LLM + keyword intent classification |
| Integration (real API) | 14 | Full pipeline with real Gemini API calls |
| Other | 14 | Orchestrator routing, weather advisor |

## V1 Fixes Applied (v1-fixes branch)

| # | Fix | File |
|---|---|---|
| 1 | `api_base` to `base_url` in LiteLLM billing call | `billing/llm_formatter.py` |
| 2 | AC server bind `0.0.0.0` to `127.0.0.1` | `ac_control/server.py` |
| 3 | AC keyword scoring (OFF wins on ties) | `ac_control/classifier.py` |
| 4 | Add logging to silent `except: pass` in orchestrator | `core/orchestrator.py` |
| 5 | Add L2 distance threshold (1.0) to vector retrieval | `billing/rag/retriever.py` |
| 6 | Wrap embed calls in try/except in store | `billing/rag/store.py` |
| 7 | Add ingestion cache (skip re-ingest if exists) | `billing/answerer.py` |
| 8 | Add unsupported bill format detection | `billing/answerer.py` |
| 9 | Expand query classifier (more canonical fields) | `billing/query_classifier.py` |
| 10 | Add MSEDCL, PDF extraction, format detection tests | `tests/` |

## Security

- LiteLLM pinned to `1.82.6` (versions 1.82.7 and 1.82.8 are blocked)
- LLM never directly calls external APIs — Python controls all I/O
- Billing answers are grounded strictly in parsed bill evidence

## Tech Stack

- **Python 3.10+**
- **Gemini 2.5 Flash** via LiteLLM 1.82.6
- **ChromaDB** (local persistent vector store)
- **sentence-transformers** (`all-MiniLM-L6-v2`)
- **pdfplumber** + **PyMuPDF** (PDF extraction)
- **FastAPI** + **httpx** (AC control)
- **Streamlit** (prototype UI)

## License

Internship prototype. Not for production use.
