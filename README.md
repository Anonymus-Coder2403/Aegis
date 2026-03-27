# Aegis a Smart Home AI Assistant

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Tests](https://img.shields.io/badge/tests-88%20passing-brightgreen)
![LiteLLM](https://img.shields.io/badge/litellm-1.82.6-orange)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

Aegis is a smart home AI assistant that answers electricity bill questions, gives weather advice, and controls a mock AC unit — all through natural language.

Three things it does:

- **Billing Librarian** — upload a PDF bill, ask questions like "When was my last payment?", get answers grounded in the actual document. Not from the LLM's memory. From the bill.
- **Weather Advisor** — asks OpenWeatherMap, sends the structured data to Gemini, gets a conversational recommendation back.
- **AC Control** — says "It's getting hot in here", classifies the intent, hits a FastAPI mock hardware server, confirms the action.

---

## Why Gemini instead of Ollama

The aPRD spec listed Ollama as the LLM engine. I didn't use it.

The dev machine has an RTX 3050 with 4GB VRAM. Running Llama 3 8B on that during a live demo is slow enough to be latency issue 30-40s per response on quantized models. Gemini 2.5 Flash via LiteLLM gives sub-3s responses and a free API tier. Same interface, faster demo.

If you want to run it locally with Ollama anyway, [see the Ollama setup section below](#ollama-local-alternative).

---

## Stack

| Component | What we used |
|---|---|
| LLM | Gemini 2.5 Flash via LiteLLM `1.82.6` |
| Vector DB | ChromaDB (local) |
| Embeddings | `sentence-transformers` `all-MiniLM-L6-v2` |
| PDF parsing | `pdfplumber` + `PyMuPDF` |
| API server | FastAPI + uvicorn |
| HTTP client | httpx |
| UI | Streamlit (prototype) |
| Language | Python 3.10+ |

> LiteLLM is pinned to `1.82.6`. Versions `1.82.7` and `1.82.8` have known security issues and are blocked in this repo.

---

## Setup

**Requirements:** Python 3.10+, [`uv`](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/Anonymus-Coder2403/Aegis.git
cd Aegis
uv sync --group dev
```

Create a `.env` file:

```env
GEMINI_API_KEY=your_key_here
OPENWEATHERMAP_API_KEY=your_key_here   # optional — falls back to mock data
```

---

## LLM provider options

### Option 1: Google AI Studio (default)

Get a free API key at [aistudio.google.com](https://aistudio.google.com).

```env
GEMINI_API_KEY=your_key_here
```

The config already points to `gemini/gemini-2.5-flash`. No other changes needed.

### Option 2: OpenRouter

OpenRouter proxies many models including Gemini. Useful if you want to swap models without changing the key setup.

```env
OPENROUTER_API_KEY=your_key_here
```

In `src/aegis/core/config.py` and `src/aegis/billing/config.py`, update:

```python
litellm_model: str = "openrouter/google/gemini-2.5-flash"
litellm_api_key_env: str = "OPENROUTER_API_KEY"
litellm_base_url: str | None = "https://openrouter.ai/api/v1"
```

### Option 3: Ollama (local alternative) {#ollama-local-alternative}

If your machine has 8GB+ VRAM, you can run this locally.

```bash
ollama pull llama3
ollama serve
```

Update both config files:

```python
litellm_model: str = "ollama/llama3"
litellm_api_key_env: str = ""          # no key needed
litellm_base_url: str | None = "http://localhost:11434"
```

Note: response times will vary significantly depending on hardware. On machines with less than 8GB VRAM, expect 20-60s per response on Llama 3 8B.

---

## Running the app

### Start the AC mock server (required for AC control)

```bash
uv run aegis-ac-server
# runs on port 8765
```

### Orchestrator CLI

```bash
uv run aegis ask "Should I take an umbrella today?"
uv run aegis ask "It's getting hot in here"
uv run aegis ask "What was my last bill payment?" --pdf data/document_pdf.pdf
```

### Billing CLI

```bash
# Parse and inspect canonical bill fields
uv run aegis-billing inspect --pdf data/document_pdf.pdf --store-dir .billing_store

# Ingest bill into ChromaDB
uv run aegis-billing ingest --pdf data/document_pdf.pdf --store-dir .billing_store

# Ask a grounded question
uv run aegis-billing query \
  --question "When was my last electricity bill paid, and what was the amount?" \
  --pdf data/document_pdf.pdf \
  --store-dir .billing_store
```

### Streamlit UI (all three features in one place)

```bash
uv run aegis-ui
```

---

## Tests

```bash
uv run pytest tests/ -v
# 88 tests, ~12s
```

---

## How the billing RAG works

Most RAG pipelines chunk the raw PDF text and retrieve by similarity. That breaks on electricity bills — the bill has multiple similar-looking amounts on the same page (`current_payable`, `total_payable_rounded`, `payable_by_due_date`) and the labels often get separated from values during extraction.

Aegis uses a schema-first approach instead:

1. Parse the PDF into a canonical JSON schema with named fields
2. Chunk that schema into typed segments (summary, amounts, charges, history, evidence snippets) and store in ChromaDB
3. For exact questions ("what was my last payment?"), look up the field directly — no semantic search involved
4. For charge/history questions, use ChromaDB retrieval filtered by field type, then pass to Gemini for formatting
5. If nothing matches, say so — no hallucinated answers

The LLM never sees raw PDF text. It only sees structured data that Python already extracted and verified.

---

## Project structure

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

## Sample bills

Two reference bills are in `data/`:

- `document_pdf.pdf` — PVVNL electricity bill (the one the RAG is tested against)
- `water-bill-pdf_compress.pdf` — water bill sample

---

## Demo log

See [`DEMO_RUN_LOG.txt`](DEMO_RUN_LOG.txt) for a full run of all three tasks with actual output.
