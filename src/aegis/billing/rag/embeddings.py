"""Embedding helpers for local billing storage."""

from __future__ import annotations

from typing import Any

from sentence_transformers import SentenceTransformer


EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
_MODEL: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _MODEL

    if _MODEL is None:
        try:
            _MODEL = SentenceTransformer(EMBEDDING_MODEL_NAME)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load sentence-transformers model "
                f"'{EMBEDDING_MODEL_NAME}': {exc}"
            ) from exc

    return _MODEL


def _normalize_embedding(vector: Any) -> list[float]:
    if hasattr(vector, "tolist"):
        vector = vector.tolist()
    elif not isinstance(vector, list):
        vector = list(vector)

    return [float(value) for value in vector]


def embed_text(text: str) -> list[float]:
    """Return a sentence-transformers embedding for one text input."""
    return _normalize_embedding(_get_model().encode(text))
