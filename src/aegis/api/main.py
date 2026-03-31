import io
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .routers.ingest import ChunkingStrategy
from ..chunking.base import ChunkingConfig
from ..chunking.pdf_chunker import PDFChunker
from ..chunking.pdf_chunker import PDFProcessor
from ..chunking.recursive_chunker import RecursiveChunker
from ..chunking.section_chunker import SectionChunker
from ..config import settings
from ..services.llm.gemini import get_llm
from ..services.search.bm25 import BM25Search
from ..services.search.hybrid import rrf_fusion, weighted_fusion
from ..services.search.vector import VectorSearch
from ..services.storage.s3_client import LocalStorageClient, S3Client


STORAGE_PATH = Path("./storage")
STORAGE_PATH.mkdir(exist_ok=True)
TEST_DOCUMENTS_PATH = Path("./test_document")
TEST_DOCUMENTS_PATH.mkdir(exist_ok=True)


class InMemoryRAG:
    def __init__(self):
        self.documents: dict[str, dict[str, Any]] = {}
        self.chunks: list[dict[str, Any]] = []
        self.bm25 = BM25Search()
        self.vector = VectorSearch()
        self.llm = get_llm(use_mock=not settings.gemini_api_key)

    def add_document(self, doc_id: str, filename: str, chunks: list[str]) -> None:
        self.documents[doc_id] = {
            "id": doc_id,
            "filename": filename,
            "created_at": datetime.utcnow().isoformat(),
            "chunks_count": len(chunks),
        }

        for i, text in enumerate(chunks):
            chunk_id = f"{doc_id}_{i}"
            self.chunks.append(
                {
                    "id": chunk_id,
                    "document_id": doc_id,
                    "text": text,
                }
            )

        self._reindex()

    def _reindex(self) -> None:
        self.bm25 = BM25Search()
        self.vector = VectorSearch()

        docs = [{"id": c["id"], "text": c["text"]} for c in self.chunks]
        if docs:
            self.bm25.index_documents(docs)
            self.vector.index_documents(docs)

    def search(
        self, query: str, top_k: int = 5, fusion: str = "rrf"
    ) -> list[dict[str, Any]]:
        if not self.chunks:
            return []

        bm25_results = self.bm25.search(query, top_k * 2)
        vector_results = self.vector.search(query, top_k * 2)

        if fusion == "rrf":
            fused = rrf_fusion(bm25_results, vector_results, k=settings.rrf_k)
        else:
            fused = weighted_fusion(bm25_results, vector_results, settings.bm25_weight)

        bm25_map = {r.chunk_id: r for r in bm25_results}
        vector_map = {r.chunk_id: r for r in vector_results}

        sorted_results = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for rank, (chunk_id, score) in enumerate(sorted_results, 1):
            chunk = next((c for c in self.chunks if c["id"] == chunk_id), None)
            if chunk:
                results.append(
                    {
                        "chunk_id": chunk_id,
                        "text": chunk["text"],
                        "score": score,
                        "rank": rank,
                        "document_id": chunk["document_id"],
                    }
                )

        return results

    def generate_answer(self, query: str, context_results: list[dict[str, Any]]) -> str:
        if not context_results:
            return "No relevant documents found to answer your question."

        context = "\n\n".join(
            [f"[{r['rank']}] {r['text'][:500]}" for r in context_results]
        )

        system_prompt = """You are a helpful AI assistant that answers questions based on the provided context.
If the answer is not in the context, say "I don't have enough information to answer that question."
Always be accurate and cite relevant parts from the context when possible."""

        prompt = f"""Based on the following context, answer the question.

Context:
{context}

Question: {query}

Answer:"""

        try:
            response = self.llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
            )
            return response.text
        except Exception as e:
            return f"Error generating answer: {str(e)}"


rag = InMemoryRAG()


def _build_chunker(chunking_strategy: str):
    chunking_map = {
        "pdf": PDFChunker,
        "recursive": RecursiveChunker,
        "section": SectionChunker,
    }

    chunker_class = chunking_map.get(chunking_strategy, PDFChunker)
    return chunker_class(
        ChunkingConfig(
            chunk_size=settings.default_chunk_size,
            chunk_overlap=settings.default_chunk_overlap,
        )
    )


def _extract_chunks(
    content: bytes, filename: str, chunking_strategy: str
) -> list[str]:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf" or chunking_strategy == "pdf":
        processor = PDFProcessor(_build_chunker("pdf"))
        chunks = processor.process_file(io.BytesIO(content), filename)
    else:
        text = content.decode("utf-8", errors="ignore")
        chunks = _build_chunker(chunking_strategy).chunk(text)

    return [c.text for c in chunks if c.text.strip()]


def _ingest_document_bytes(
    content: bytes,
    filename: str,
    chunking_strategy: str = "pdf",
) -> dict[str, Any]:
    chunk_texts = _extract_chunks(content, filename, chunking_strategy)
    doc_id = str(uuid.uuid4())

    storage = LocalStorageClient(str(STORAGE_PATH / "documents"))
    storage.upload_file(
        io.BytesIO(content),
        filename or "document.txt",
        folder=doc_id,
    )

    rag.add_document(doc_id, filename or "unknown", chunk_texts)

    return {
        "document_id": doc_id,
        "filename": filename,
        "status": "uploaded",
        "chunks_count": len(chunk_texts),
        "message": f"Document uploaded and indexed with {len(chunk_texts)} chunks",
    }


def _resolve_test_document(filename: str) -> Path:
    candidate = (TEST_DOCUMENTS_PATH / filename).resolve()
    base = TEST_DOCUMENTS_PATH.resolve()

    if base not in candidate.parents and candidate != base:
        raise HTTPException(status_code=400, detail="Invalid test document path")

    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Test document not found")

    return candidate


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Aegis RAG API starting...")
    print(f"Storage mode: {settings.storage_mode}")
    print(
        f"LLM: {'Mock (no API key)' if not settings.gemini_api_key else settings.llm_model}"
    )
    yield
    print("Aegis RAG API shutting down...")


app = FastAPI(
    title="Aegis RAG API",
    description="Production Document RAG System with Gemini + Hybrid Search",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    fusion: str = "rrf"
    use_llm: bool = True


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    query: str


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "documents": len(rag.documents),
        "chunks": len(rag.chunks),
        "llm": "mock" if not settings.gemini_api_key else settings.llm_model,
    }


@app.get("/")
async def root():
    return {
        "message": "Aegis RAG API - Upload documents and query them",
        "docs": "/docs",
        "endpoints": {
            "upload": "POST /upload",
            "query": "POST /query",
            "documents": "GET /documents",
            "health": "GET /health",
        },
    }


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    chunking_strategy: str = "pdf",
):
    if file.size and file.size > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 100MB)")

    content = await file.read()
    return _ingest_document_bytes(
        content=content,
        filename=file.filename or "document.txt",
        chunking_strategy=chunking_strategy,
    )


@app.get("/test-documents")
async def list_test_documents():
    allowed_extensions = {".pdf", ".txt", ".doc", ".docx"}
    files = [
        {
            "filename": path.name,
            "size": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
        }
        for path in sorted(TEST_DOCUMENTS_PATH.iterdir())
        if path.is_file() and path.suffix.lower() in allowed_extensions
    ]

    return {
        "folder": str(TEST_DOCUMENTS_PATH.resolve()),
        "documents": files,
        "total": len(files),
    }


@app.post("/test-documents/{filename}/upload")
async def upload_test_document(
    filename: str,
    chunking_strategy: str = "pdf",
):
    test_file = _resolve_test_document(filename)
    content = test_file.read_bytes()

    return _ingest_document_bytes(
        content=content,
        filename=test_file.name,
        chunking_strategy=chunking_strategy,
    )


@app.get("/documents")
async def list_documents():
    return {
        "documents": list(rag.documents.values()),
        "total": len(rag.documents),
    }


@app.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    doc = rag.documents.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    if doc_id not in rag.documents:
        raise HTTPException(status_code=404, detail="Document not found")

    rag.chunks = [c for c in rag.chunks if c["document_id"] != doc_id]
    del rag.documents[doc_id]
    rag._reindex()

    return {"status": "deleted", "document_id": doc_id}


@app.post("/query", response_model=QueryResponse)
async def query_document(request: QueryRequest):
    if not request.query or len(request.query.strip()) < 2:
        raise HTTPException(
            status_code=400, detail="Query must be at least 2 characters"
        )

    results = rag.search(request.query, request.top_k, request.fusion)

    if not results:
        return QueryResponse(
            answer="No relevant documents found. Try uploading a document first.",
            sources=[],
            query=request.query,
        )

    if request.use_llm and settings.gemini_api_key:
        answer = rag.generate_answer(request.query, results)
    else:
        best_chunk = results[0]["text"] if results else ""
        answer = f"Best match: {best_chunk[:500]}..."

    return QueryResponse(
        answer=answer,
        sources=results,
        query=request.query,
    )


@app.get("/search")
async def search_get(q: str, top_k: int = 5, fusion: str = "rrf"):
    results = rag.search(q, top_k, fusion)
    return {"results": results, "query": q, "total": len(results)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
