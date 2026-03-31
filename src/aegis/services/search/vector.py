from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class VectorResult:
    chunk_id: str
    text: str
    score: float
    rank: int
    metadata: dict[str, Any]


class EmbeddingGenerator:
    def __init__(self, model_name: str = "BGE-M3", dimension: int = 1024):
        self.model_name = model_name
        self.dimension = dimension
        self._model = None

    def _get_model(self):
        if self._model is not None:
            return self._model

        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self.model_name, local_files_only=True)
        return self._model

    def encode(self, texts: list[str]) -> list[np.ndarray]:
        try:
            model = self._get_model()
            embeddings = model.encode(texts, normalize_embeddings=True)
            return [emb for emb in embeddings]
        except Exception:
            return [self._dummy_encode(text) for text in texts]

    def encode_single(self, text: str) -> np.ndarray:
        return self._dummy_encode(text)

    def _dummy_encode(self, text: str) -> np.ndarray:
        np.random.seed(hash(text) % (2**32))
        return np.random.randn(self.dimension).astype(np.float32)


class VectorSearch:
    def __init__(self, embedding_generator: EmbeddingGenerator | None = None):
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.documents: dict[str, tuple[str, np.ndarray]] = {}

    def index_documents(self, documents: list[dict[str, Any]]) -> None:
        self.documents.clear()

        texts = [doc.get("text", "") for doc in documents]
        embeddings = self.embedding_generator.encode(texts)

        for doc, embedding in zip(documents, embeddings):
            doc_id = doc.get("id", "")
            text = doc.get("text", "")
            self.documents[doc_id] = (text, embedding)

    def search(self, query: str, top_k: int = 10) -> list[VectorResult]:
        query_embedding = self.embedding_generator.encode_single(query)

        scores: dict[str, float] = {}

        for doc_id, (text, doc_embedding) in self.documents.items():
            score = self._cosine_similarity(query_embedding, doc_embedding)
            scores[doc_id] = score

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        results = []
        for rank, (doc_id, score) in enumerate(sorted_scores[:top_k], 1):
            text, _ = self.documents[doc_id]
            results.append(
                VectorResult(
                    chunk_id=doc_id,
                    text=text,
                    score=float(score),
                    rank=rank,
                    metadata={},
                )
            )

        return results

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))


class OpenSearchVectorClient:
    def __init__(
        self,
        client,
        index_name: str = "aegis-documents",
        vector_field: str = "embedding",
    ):
        self.client = client
        self.index_name = index_name
        self.vector_field = vector_field
        self.embedding_generator = EmbeddingGenerator()

    def search(
        self, query: str, top_k: int = 10, filters: dict | None = None
    ) -> list[VectorResult]:
        query_embedding = self.embedding_generator.encode_single(query)

        body = {
            "size": top_k,
            "query": {
                "knn": {
                    self.vector_field: {
                        "vector": query_embedding.tolist(),
                        "k": top_k,
                    }
                }
            },
        }

        if filters:
            body["query"] = {
                "bool": {
                    "must": [
                        {
                            "knn": {
                                self.vector_field: {
                                    "vector": query_embedding.tolist(),
                                    "k": top_k,
                                }
                            }
                        }
                    ],
                    "filter": [
                        {"term": {field: value}} for field, value in filters.items()
                    ],
                }
            }

        try:
            response = self.client.search(index=self.index_name, body=body)
            hits = response.get("hits", {}).get("hits", [])

            results = []
            for rank, hit in enumerate(hits, 1):
                source = hit.get("_source", {})
                results.append(
                    VectorResult(
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
