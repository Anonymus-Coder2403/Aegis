from dataclasses import dataclass
from typing import Any

from .hybrid import HybridResult


@dataclass
class RerankedResult:
    chunk_id: str
    text: str
    original_score: float
    reranked_score: float
    rank: int
    relevance: float
    metadata: dict[str, Any]


class Reranker:
    def rerank(
        self,
        query: str,
        results: list[HybridResult],
        top_k: int = 10,
    ) -> list[RerankedResult]:
        raise NotImplementedError


class CrossEncoderReranker(Reranker):
    def __init__(self, model_name: str = "BGE-BGE-Reranker-v2-m3"):
        self.model_name = model_name

    def rerank(
        self,
        query: str,
        results: list[HybridResult],
        top_k: int = 10,
    ) -> list[RerankedResult]:
        try:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder(self.model_name)

            pairs = [(query, r.text) for r in results]
            scores = model.predict(pairs)

            for result, score in zip(results, scores):
                result.metadata["rerank_score"] = float(score)

            sorted_results = sorted(
                results,
                key=lambda r: r.metadata.get("rerank_score", 0),
                reverse=True,
            )[:top_k]

            reranked = []
            for rank, result in enumerate(sorted_results, 1):
                reranked.append(
                    RerankedResult(
                        chunk_id=result.chunk_id,
                        text=result.text,
                        original_score=result.score,
                        reranked_score=result.metadata.get("rerank_score", 0),
                        rank=rank,
                        relevance=result.metadata.get("rerank_score", 0),
                        metadata=result.metadata,
                    )
                )

            return reranked

        except ImportError:
            return self._fallback_rerank(query, results, top_k)

    def _fallback_rerank(
        self,
        query: str,
        results: list[HybridResult],
        top_k: int = 10,
    ) -> list[RerankedResult]:
        query_terms = set(query.lower().split())

        scored_results = []
        for result in results:
            text_terms = set(result.text.lower().split())
            overlap = len(query_terms & text_terms)
            relevance = overlap / max(len(query_terms), 1)

            scored_results.append((result, relevance))

        scored_results.sort(key=lambda x: x[1], reverse=True)

        reranked = []
        for rank, (result, relevance) in enumerate(scored_results[:top_k], 1):
            reranked.append(
                RerankedResult(
                    chunk_id=result.chunk_id,
                    text=result.text,
                    original_score=result.score,
                    reranked_score=relevance,
                    rank=rank,
                    relevance=relevance,
                    metadata=result.metadata,
                )
            )

        return reranked


class LLMReranker(Reranker):
    def __init__(self):
        pass

    async def rerank(
        self,
        query: str,
        results: list[HybridResult],
        top_k: int = 10,
    ) -> list[RerankedResult]:
        scored_results = []

        for result in results:
            relevance = await self._compute_relevance(query, result.text)
            scored_results.append((result, relevance))

        scored_results.sort(key=lambda x: x[1], reverse=True)

        reranked = []
        for rank, (result, relevance) in enumerate(scored_results[:top_k], 1):
            reranked.append(
                RerankedResult(
                    chunk_id=result.chunk_id,
                    text=result.text,
                    original_score=result.score,
                    reranked_score=relevance,
                    rank=rank,
                    relevance=relevance,
                    metadata=result.metadata,
                )
            )

        return reranked

    async def _compute_relevance(self, query: str, text: str) -> float:
        query_terms = set(query.lower().split())
        text_terms = set(text.lower().split())
        overlap = len(query_terms & text_terms)
        return overlap / max(len(query_terms), 1)
