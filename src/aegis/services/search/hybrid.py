from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .bm25 import BM25Result, OpenSearchBM25Client
from .vector import OpenSearchVectorClient, VectorResult


@dataclass
class HybridResult:
    chunk_id: str
    text: str
    score: float
    rank: int
    bm25_score: float | None
    vector_score: float | None
    metadata: dict[str, Any]


def rrf_fusion(
    bm25_results: list[BM25Result],
    vector_results: list[VectorResult],
    k: int = 60,
) -> dict[str, float]:
    scores = defaultdict(float)

    for rank, result in enumerate(bm25_results):
        scores[result.chunk_id] += 1 / (k + rank)

    for rank, result in enumerate(vector_results):
        scores[result.chunk_id] += 1 / (k + rank)

    return dict(scores)


def weighted_fusion(
    bm25_results: list[BM25Result],
    vector_results: list[VectorResult],
    bm25_weight: float = 0.5,
    normalize: bool = True,
) -> dict[str, float]:
    scores = defaultdict(float)

    bm25_max = max((r.score for r in bm25_results), default=1.0)
    vector_max = max((r.score for r in vector_results), default=1.0)

    for result in bm25_results:
        normalized = (
            result.score / bm25_max if normalize and bm25_max > 0 else result.score
        )
        scores[result.chunk_id] += normalized * bm25_weight

    for result in vector_results:
        normalized = (
            result.score / vector_max if normalize and vector_max > 0 else result.score
        )
        scores[result.chunk_id] += normalized * (1 - bm25_weight)

    return dict(scores)


class HybridSearch:
    def __init__(
        self,
        bm25_client: OpenSearchBM25Client | None = None,
        vector_client: OpenSearchVectorClient | None = None,
        fusion_method: str = "rrf",
        bm25_weight: float = 0.5,
        k: int = 60,
    ):
        self.bm25_client = bm25_client
        self.vector_client = vector_client
        self.fusion_method = fusion_method
        self.bm25_weight = bm25_weight
        self.k = k

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[HybridResult]:
        bm25_results = []
        vector_results = []

        if self.bm25_client:
            bm25_results = self.bm25_client.search(query, top_k * 2, filters)

        if self.vector_client:
            vector_results = self.vector_client.search(query, top_k * 2, filters)

        if self.fusion_method == "rrf":
            fused_scores = rrf_fusion(bm25_results, vector_results, self.k)
        else:
            fused_scores = weighted_fusion(
                bm25_results,
                vector_results,
                self.bm25_weight,
                normalize=True,
            )

        bm25_map = {r.chunk_id: r for r in bm25_results}
        vector_map = {r.chunk_id: r for r in vector_results}

        sorted_results = sorted(
            fused_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        results = []
        for rank, (chunk_id, score) in enumerate(sorted_results, 1):
            bm25_result = bm25_map.get(chunk_id)
            vector_result = vector_map.get(chunk_id)

            text = (
                bm25_result.text
                if bm25_result
                else vector_result.text
                if vector_result
                else ""
            )

            results.append(
                HybridResult(
                    chunk_id=chunk_id,
                    text=text,
                    score=score,
                    rank=rank,
                    bm25_score=bm25_result.score if bm25_result else None,
                    vector_score=vector_result.score if vector_result else None,
                    metadata={
                        **(bm25_result.metadata if bm25_result else {}),
                        **(vector_result.metadata if vector_result else {}),
                    },
                )
            )

        return results


class OpenSearchHybridClient:
    def __init__(self, client, index_name: str = "aegis-documents"):
        self.client = client
        self.index_name = index_name

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict | None = None,
        bm25_weight: float = 0.5,
    ) -> list[HybridResult]:
        body = {
            "size": top_k,
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "should": [
                                {
                                    "multi_match": {
                                        "query": query,
                                        "fields": ["text^2", "content", "title"],
                                        "type": "best_fields",
                                    }
                                },
                                {
                                    "knn": {
                                        "embedding": {
                                            "vector": self._get_dummy_vector(query),
                                            "k": top_k,
                                        }
                                    }
                                },
                            ]
                        }
                    },
                    "score_mode": "sum",
                    "boost_mode": "multiply",
                }
            },
        }

        if filters:
            body["query"]["function_score"]["query"]["bool"]["filter"] = [
                {"term": {field: value}} for field, value in filters.items()
            ]

        try:
            response = self.client.search(index=self.index_name, body=body)
            hits = response.get("hits", {}).get("hits", [])

            results = []
            for rank, hit in enumerate(hits, 1):
                source = hit.get("_source", {})
                results.append(
                    HybridResult(
                        chunk_id=hit.get("_id", ""),
                        text=source.get("text", ""),
                        score=hit.get("_score", 0.0),
                        rank=rank,
                        bm25_score=None,
                        vector_score=None,
                        metadata=source.get("metadata", {}),
                    )
                )

            return results

        except Exception:
            return []

    def _get_dummy_vector(self, text: str) -> list[float]:
        import numpy as np

        np.random.seed(hash(text) % (2**32))
        return np.random.randn(1024).tolist()
