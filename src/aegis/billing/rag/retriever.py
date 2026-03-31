"""Exact and semantic retrieval helpers for billing data."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import logging
from typing import Any

from aegis.billing.config import BillingConfig
from aegis.billing.rag.embeddings import embed_text
from aegis.billing.types import CanonicalBill

LOGGER = logging.getLogger(__name__)


def lookup_exact_fields(bill: CanonicalBill, field_paths: list[str]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for path in field_paths:
        resolved[path] = _resolve_path(bill, path)
    return resolved


def _resolve_path(value: Any, path: str) -> Any:
    current: Any = asdict(value) if is_dataclass(value) else value
    for segment in path.split("."):
        if isinstance(current, dict):
            current = current.get(segment)
        else:
            current = getattr(current, segment, None)
        if current is None:
            return None
    return current


def retrieve_charge_snippets(
    query_text: str,
    source_doc_id: str,
    config: BillingConfig,
    n_results: int = 4,
) -> list[dict[str, Any]]:
    return _query_collection(
        collection_name="bill_charges",
        query_text=query_text,
        source_doc_id=source_doc_id,
        config=config,
        n_results=n_results,
    )


def retrieve_history_snippets(
    query_text: str,
    source_doc_id: str,
    config: BillingConfig,
    n_results: int = 4,
) -> list[dict[str, Any]]:
    return _query_collection(
        collection_name="bill_history",
        query_text=query_text,
        source_doc_id=source_doc_id,
        config=config,
        n_results=n_results,
    )


def retrieve_document_snippets(
    query_text: str,
    source_doc_id: str,
    config: BillingConfig,
    n_results: int = 4,
) -> list[dict[str, Any]]:
    return _query_collection(
        collection_name="bill_fields",
        query_text=query_text,
        source_doc_id=source_doc_id,
        config=config,
        n_results=n_results,
    )


_DISTANCE_THRESHOLD = 1.0  # L2 distance; above this = semantically unrelated


def _query_collection(
    collection_name: str,
    query_text: str,
    source_doc_id: str,
    config: BillingConfig,
    n_results: int,
) -> list[dict[str, Any]]:
    try:
        import chromadb
    except ImportError as exc:
        LOGGER.warning("chromadb import failed; semantic retrieval disabled: %s", exc)
        return []

    try:
        client = chromadb.PersistentClient(path=str(config.chroma_dir))
        collection = client.get_or_create_collection(collection_name)
        query_result = collection.query(
            query_embeddings=[embed_text(query_text)],
            where={"source_doc_id": source_doc_id},
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        LOGGER.exception(
            "Semantic retrieval query failed for collection='%s' source_doc_id='%s'",
            collection_name,
            source_doc_id,
        )
        return []

    documents = (query_result.get("documents") or [[]])[0]
    metadatas = (query_result.get("metadatas") or [[]])[0]
    distances = (query_result.get("distances") or [[]])[0]

    snippets: list[dict[str, Any]] = []
    for index, document in enumerate(documents):
        distance = distances[index] if index < len(distances) else None
        if distance is not None and distance > _DISTANCE_THRESHOLD:
            LOGGER.debug(
                "Skipping chunk (distance=%.3f > threshold=%.1f) for collection='%s'",
                distance,
                _DISTANCE_THRESHOLD,
                collection_name,
            )
            continue
        metadata = metadatas[index] if index < len(metadatas) else {}
        snippets.append(
            {
                "document": document,
                "metadata": metadata or {},
                "distance": distance,
            }
        )
    return snippets
