# Aegis — Smart Home AI Assistant

An internship prototype for a smart home AI assistant that handles electricity bill Q&A, weather advice, and AC control via natural language.

Built with Python, Gemini 2.5 Flash (via LiteLLM), ChromaDB, and FastAPI.

---

## Features

### Billing RAG
- Upload a PDF electricity bill and ask grounded questions
- Schema-first design: structured lookup first, ChromaDB semantic search as fallback
- PDF parsed with `pdfplumber` + `PyMuPDF` into a canonical JSON schema
- Bill chunks embedded with `sentence-transformers` (`all-MiniLM-L6-v2`) into ChromaDB
- LiteLLM → Gemini 2.5 Flash formats charge/history answers; exact fields are deterministic
- Supported bills: PVVNL, MSEDCL

### Weather Advisor
- Fetches live weather from OpenWeatherMap (or falls back to mock data)
- Answers natural language weather questions with Gemini 2.5 Flash

### AC Control
- Classifies natural language commands (`turn_on` / `turn_off` / `none`)
- Executes against a FastAPI mock hardware server (port 8765)
- Returns confirmation with current AC state

---

## Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| LLM | Gemini 2.5 Flash via LiteLLM `1.82.6` |
| Vector DB | ChromaDB (local) |
| Embeddings | `sentence-transformers` `all-MiniLM-L6-v2` |
| PDF Parsing | `pdfplumber` + `PyMuPDF` |
| API Server | FastAPI + uvicorn |
| HTTP Client | httpx |
| UI | Streamlit (prototype) |

> **Security:** LiteLLM is pinned to `1.82.6`. Versions `1.82.7` and `1.82.8` are blocked.

---

## Setup

```bash
uv sync --group dev
```

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
OPENWEATHERMAP_API_KEY=your_openweathermap_key_here   # optional, falls back to mock
```

---

## Usage

### Orchestrator CLI (all features)

```bash
uv run aegis ask "Should I carry an umbrella today?"
uv run aegis ask "Turn on the AC"
uv run aegis ask "What was my last bill payment?" --pdf data/document_pdf.pdf
```

### Billing CLI

```bash
# Inspect extracted bill fields
uv run aegis-billing inspect --pdf data/document_pdf.pdf --store-dir .billing_store

# Ingest bill into ChromaDB
uv run aegis-billing ingest --pdf data/document_pdf.pdf --store-dir .billing_store

# Ask a billing question
uv run aegis-billing query --question "When was my last electricity bill paid?" --pdf data/document_pdf.pdf --store-dir .billing_store
```

### AC Mock Server

```bash
uv run aegis-ac-server   # starts on port 8765
```

### Streamlit UI

```bash
uv run aegis-ui
```

Three tabs: Billing / Weather Advisor / AC Control

---

## Tests

```bash
uv run pytest tests/ -v        # 88 tests
```

---

## Project Structure

```
src/aegis/
├── core/           config.py, orchestrator.py
├── billing/        answerer, cli, config, llm_formatter, query_classifier, types
│   ├── parser/     extractors, normalize, pvvnl_parser, msedcl_parser
│   └── rag/        embeddings, retriever, store
├── weather/        advisor, fetcher
├── ac_control/     classifier, client, server
└── ui/             streamlit_app
```

---

## Sample Bills

Two reference bills are included in `data/`:
- `document_pdf.pdf` — PVVNL electricity bill
- `water-bill-pdf_compress.pdf` — water bill sample
