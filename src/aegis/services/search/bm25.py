from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class BM25Result:
    chunk_id: str
    text: str
    score: float
    rank: int
    metadata: dict[str, Any]


class BM25Search:
    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        avg_doc_length: float = 1000.0,
    ):
        self.k1 = k1
        self.b = b
        self.avg_doc_length = avg_doc_length
        self.documents: dict[str, tuple[str, int]] = {}
        self.doc_freqs: dict[str, int] = {}
        self.doc_lengths: dict[str, int] = {}
        self.N = 0

    def index_documents(self, documents: list[dict[str, Any]]) -> None:
        self.documents.clear()
        self.doc_freqs.clear()
        self.doc_lengths.clear()
        self.N = 0

        term_doc_freqs: dict[str, set[str]] = {}

        for doc in documents:
            doc_id = doc.get("id", str(self.N))
            text = doc.get("text", "")
            self.documents[doc_id] = (text, len(text))
            self.doc_lengths[doc_id] = len(text)

            tokens = self._tokenize(text)
            unique_tokens = set(tokens)

            for token in unique_tokens:
                if token not in term_doc_freqs:
                    term_doc_freqs[token] = set()
                term_doc_freqs[token].add(doc_id)

        for term, doc_ids in term_doc_freqs.items():
            self.doc_freqs[term] = len(doc_ids)

        self.N = len(documents)

    def search(self, query: str, top_k: int = 10) -> list[BM25Result]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores: dict[str, float] = {}

        for doc_id, (text, doc_length) in self.documents.items():
            doc_tokens = self._tokenize(text)
            doc_tf = self._compute_tf(doc_tokens)

            score = 0.0
            for token in query_tokens:
                if token in doc_tf:
                    tf = doc_tf[token]
                    idf = self._compute_idf(token)
                    doc_len_norm = (
                        1 - self.b + self.b * (doc_length / self.avg_doc_length)
                    )
                    score += idf * (tf * (self.k1 + 1)) / (tf + self.k1 * doc_len_norm)

            if score > 0:
                scores[doc_id] = score

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        results = []
        for rank, (doc_id, score) in enumerate(sorted_scores[:top_k], 1):
            text, _ = self.documents[doc_id]
            results.append(
                BM25Result(
                    chunk_id=doc_id,
                    text=text,
                    score=score,
                    rank=rank,
                    metadata={},
                )
            )

        return results

    def _tokenize(self, text: str) -> list[str]:
        import re

        text = text.lower()
        tokens = re.findall(r"\b\w+\b", text)
        return [t for t in tokens if len(t) > 1]

    def _compute_tf(self, tokens: list[str]) -> dict[str, float]:
        tf: dict[str, int] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1

        max_tf = max(tf.values()) if tf else 1
        return {t: count / max_tf for t, count in tf.items()}

    def _compute_idf(self, term: str) -> float:
        df = self.doc_freqs.get(term, 0)
        if df == 0:
            return 0.0
        return np.log((self.N - df + 0.5) / (df + 0.5) + 1)


class OpenSearchBM25Client:
    def __init__(self, client, index_name: str = "aegis-documents"):
        self.client = client
        self.index_name = index_name

    def search(
        self, query: str, top_k: int = 10, filters: dict | None = None
    ) -> list[BM25Result]:
        body = {
            "size": top_k,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["text^2", "content", "title"],
                                "type": "best_fields",
                            }
                        }
                    ]
                }
            },
        }

        if filters:
            filter_clauses = []
            for field, value in filters.items():
                filter_clauses.append({"term": {field: value}})
            body["query"]["bool"]["filter"] = filter_clauses

        try:
            response = self.client.search(index=self.index_name, body=body)
            hits = response.get("hits", {}).get("hits", [])

            results = []
            for rank, hit in enumerate(hits, 1):
                source = hit.get("_source", {})
                results.append(
                    BM25Result(
                        chunk_id=hit.get("_id", ""),
                        text=source.get("text", ""),
                        score=hit.get("_score", 0.0),
                        rank=rank,
                        metadata=source.get("metadata", {}),
                    )
                )

            return results

        except Exception:
            return []
