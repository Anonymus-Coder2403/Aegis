from enum import Enum
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


router = APIRouter(prefix="/search", tags=["search"])


class SearchMode(str, Enum):
    BM25 = "bm25"
    VECTOR = "vector"
    HYBRID = "hybrid"


class FusionMethod(str, Enum):
    RRF = "rrf"
    WEIGHTED = "weighted"


class SearchRequest(BaseModel):
    query: str
    mode: SearchMode = SearchMode.HYBRID
    top_k: int = 10
    filters: dict[str, Any] | None = None
    fusion_method: FusionMethod = FusionMethod.RRF
    bm25_weight: float = 0.5
    use_reranker: bool = False


class SearchResult(BaseModel):
    chunk_id: str
    text: str
    score: float
    rank: int
    bm25_score: float | None = None
    vector_score: float | None = None
    relevance: float | None = None
    metadata: dict[str, Any] = {}


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    query: str
    mode: str


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    if not request.query or len(request.query.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="Query must be at least 2 characters",
        )

    if request.top_k < 1 or request.top_k > 100:
        raise HTTPException(
            status_code=400,
            detail="top_k must be between 1 and 100",
        )

    results = _perform_search(
        query=request.query,
        mode=request.mode,
        top_k=request.top_k,
        filters=request.filters,
        fusion_method=request.fusion_method,
        bm25_weight=request.bm25_weight,
        use_reranker=request.use_reranker,
    )

    return SearchResponse(
        results=results,
        total=len(results),
        query=request.query,
        mode=request.mode.value,
    )


@router.get("", response_model=SearchResponse)
async def search_get(
    q: str = Query(..., min_length=2),
    mode: SearchMode = SearchMode.HYBRID,
    top_k: int = Query(10, ge=1, le=100),
    fusion: FusionMethod = FusionMethod.RRF,
    rerank: bool = False,
) -> SearchResponse:
    results = _perform_search(
        query=q,
        mode=mode,
        top_k=top_k,
        filters=None,
        fusion_method=fusion,
        bm25_weight=0.5,
        use_reranker=rerank,
    )

    return SearchResponse(
        results=results,
        total=len(results),
        query=q,
        mode=mode.value,
    )


def _perform_search(
    query: str,
    mode: SearchMode,
    top_k: int,
    filters: dict[str, Any] | None,
    fusion_method: FusionMethod,
    bm25_weight: float,
    use_reranker: bool,
) -> list[SearchResult]:
    from ...services.search.bm25 import BM25Search
    from ...services.search.hybrid import HybridSearch, rrf_fusion
    from ...services.search.reranker import CrossEncoderReranker
    from ...services.search.vector import VectorSearch

    bm25_search = BM25Search()
    vector_search = VectorSearch()

    sample_docs = [
        {"id": "1", "text": f"Sample document {i} about {query}"} for i in range(20)
    ]
    bm25_search.index_documents(sample_docs)
    vector_search.index_documents(sample_docs)

    if mode == SearchMode.BM25:
        bm25_results = bm25_search.search(query, top_k)
        results = [
            SearchResult(
                chunk_id=r.chunk_id,
                text=r.text,
                score=r.score,
                rank=r.rank,
                bm25_score=r.score,
                metadata=r.metadata,
            )
            for r in bm25_results
        ]
    elif mode == SearchMode.VECTOR:
        vector_results = vector_search.search(query, top_k)
        results = [
            SearchResult(
                chunk_id=r.chunk_id,
                text=r.text,
                score=r.score,
                rank=r.rank,
                vector_score=r.score,
                metadata=r.metadata,
            )
            for r in vector_results
        ]
    else:
        hybrid_search = HybridSearch(
            bm25_client=None,
            vector_client=None,
            fusion_method=fusion_method.value,
            bm25_weight=bm25_weight,
        )

        from ...services.search.bm25 import BM25Result
        from ...services.search.vector import VectorResult

        bm25_results = bm25_search.search(query, top_k * 2)
        vector_results = vector_search.search(query, top_k * 2)

        if fusion_method == FusionMethod.RRF:
            fused = rrf_fusion(bm25_results, vector_results)
        else:
            from ...services.search.hybrid import weighted_fusion

            fused = weighted_fusion(bm25_results, vector_results, bm25_weight)

        bm25_map = {r.chunk_id: r for r in bm25_results}
        vector_map = {r.chunk_id: r for r in vector_results}

        sorted_scores = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:top_k]

        hybrid_results = []
        for rank, (chunk_id, score) in enumerate(sorted_scores, 1):
            bm25_r = bm25_map.get(chunk_id)
            vector_r = vector_map.get(chunk_id)

            text = bm25_r.text if bm25_r else (vector_r.text if vector_r else "")

            hybrid_results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    text=text,
                    score=score,
                    rank=rank,
                    bm25_score=bm25_r.score if bm25_r else None,
                    vector_score=vector_r.score if vector_r else None,
                    metadata={},
                )
            )

        results = hybrid_results

    if use_reranker and results:
        reranker = CrossEncoderReranker()

        from ...services.search.hybrid import HybridResult

        hybrid_results = [
            HybridResult(
                chunk_id=r.chunk_id,
                text=r.text,
                score=r.score,
                rank=r.rank,
                bm25_score=r.bm25_score,
                vector_score=r.vector_score,
                metadata=r.metadata,
            )
            for r in results
        ]

        reranked = reranker.rerank(query, hybrid_results, top_k)

        results = [
            SearchResult(
                chunk_id=r.chunk_id,
                text=r.text,
                score=r.reranked_score,
                rank=r.rank,
                bm25_score=r.metadata.get("bm25_score"),
                vector_score=r.metadata.get("vector_score"),
                relevance=r.relevance,
                metadata=r.metadata,
            )
            for r in reranked
        ]

    return results
