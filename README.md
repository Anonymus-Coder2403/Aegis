# Aegis Billing RAG

This repository currently contains the billing RAG slice for Aegis Smart Home AI Assistant.

The implemented path is schema-first:
- PDF content is extracted with `pdfplumber` and `PyMuPDF`
- bill data is normalized into a canonical JSON shape
- canonical data is persisted locally
- Chroma collections are populated for bill fields, charges, and history
- embeddings are generated with `sentence-transformers` using `all-MiniLM-L6-v2`

## Security Pin

LiteLLM is security-pinned to `1.82.6` in this repo.
Blocked compromised versions are `1.82.7` and `1.82.8`.

The weather and AC-control parts described in the project handoff docs are not implemented in this README yet. This document only covers the working billing slice.

## Requirements

- Python `3.10+`
- `uv`

## Setup

Create the project environment and install runtime + dev dependencies:

```powershell
uv sync --group dev
```

This recreates the local `.venv` when needed. If `.venv` was removed during cleanup, running the command again is the expected way to restore it.

## Billing CLI

The project exposes one CLI:

```powershell
uv run --no-sync aegis-billing-rag --help
```

Available commands:
- `inspect`
- `ingest`
- `query`

All commands accept `--store-dir`. The default is `.billing_store`.

## Streamlit UI (Billing Only)

Run the Streamlit app:

```powershell
uv run --no-sync streamlit run src/aegis_billing_rag/billing/streamlit_app.py
```

In the UI:
- upload one bill PDF
- use **Inspect Bill** to preview canonical extraction
- ask questions with **Ask Question**

## Example Commands

Inspect the representative sample bill and print canonical JSON:

```powershell
uv run --no-sync aegis-billing-rag inspect --pdf document_pdf.pdf --store-dir .billing_store
```

Ingest the sample bill into local canonical storage + Chroma:

```powershell
uv run --no-sync aegis-billing-rag ingest --pdf document_pdf.pdf --store-dir .billing_store
```

Query the ingested bill:

```powershell
uv run --no-sync aegis-billing-rag query --question "When was my last electricity bill paid, and what was the amount?" --pdf document_pdf.pdf --store-dir .billing_store
```

`query` is single-bill only and always requires `--pdf`.

## Tests

Run the full billing test suite:

```powershell
uv run --group dev pytest -q
```

Run answer-routing and formatter grounding tests:

```powershell
uv run --group dev pytest tests/test_answerer_grounding.py tests/test_llm_formatter.py -q
```

Run only the embedding wrapper tests:

```powershell
uv run --group dev pytest tests/test_embeddings.py -q
```

## Current Embedding Behavior

The billing RAG embedder is implemented in [src/aegis_billing_rag/billing/rag/embeddings.py](/d:/Aegis/src/aegis_billing_rag/billing/rag/embeddings.py).

Current behavior:
- lazy-loads `sentence-transformers/all-MiniLM-L6-v2`
- caches the model instance per process
- returns embeddings as `list[float]`
- raises `RuntimeError` if model initialization fails

The first embedding call may download model files from Hugging Face if they are not already cached locally.

## Important Files

- [pyproject.toml](/d:/Aegis/pyproject.toml)
- [src/aegis_billing_rag/billing/cli.py](/d:/Aegis/src/aegis_billing_rag/billing/cli.py)
- [src/aegis_billing_rag/billing/answerer.py](/d:/Aegis/src/aegis_billing_rag/billing/answerer.py)
- [src/aegis_billing_rag/billing/rag/store.py](/d:/Aegis/src/aegis_billing_rag/billing/rag/store.py)
- [src/aegis_billing_rag/billing/rag/retriever.py](/d:/Aegis/src/aegis_billing_rag/billing/rag/retriever.py)
- [src/aegis_billing_rag/billing/rag/embeddings.py](/d:/Aegis/src/aegis_billing_rag/billing/rag/embeddings.py)
- [tests/test_billing_cli_integration.py](/d:/Aegis/tests/test_billing_cli_integration.py)
- [tests/test_embeddings.py](/d:/Aegis/tests/test_embeddings.py)

## Notes

- `.billing_store/`, `.venv/`, `.pytest_cache/`, and `__pycache__/` are local artifacts and are ignored.
- The representative sample bill is [document_pdf.pdf](/d:/Aegis/document_pdf.pdf).
- The locked architecture and project handoff context are documented in [ARCHITECTURE_LOCK.md](/d:/Aegis/ARCHITECTURE_LOCK.md) and [PROJECT_CONTEXT_HANDOFF.md](/d:/Aegis/PROJECT_CONTEXT_HANDOFF.md).
