import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel


router = APIRouter(prefix="/ingest", tags=["ingestion"])


class ChunkingStrategy(str, Enum):
    RECURSIVE = "recursive"
    SECTION = "section"
    PDF = "pdf"


class IngestDocumentRequest(BaseModel):
    filename: str
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.PDF
    chunk_size: int = 512
    chunk_overlap: int = 50


class IngestDocumentResponse(BaseModel):
    document_id: str
    status: str
    chunks_count: int
    filename: str
    uploaded_at: datetime


class ChunkResponse(BaseModel):
    chunk_id: str
    text: str
    start_index: int
    end_index: int
    metadata: dict[str, Any]


@router.post(
    "/upload",
    response_model=IngestDocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    file: UploadFile = File(...),
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.PDF,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> IngestDocumentResponse:
    if file.size and file.size > 100 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 100MB.",
        )

    allowed_extensions = {".pdf", ".txt", ".doc", ".docx"}
    file_ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""

    if f".{file_ext}" not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed: {allowed_extensions}",
        )

    document_id = str(uuid.uuid4())

    from ...chunking.base import ChunkingConfig
    from ...chunking.pdf_chunker import PDFChunker
    from ...chunking.recursive_chunker import RecursiveChunker
    from ...chunking.section_chunker import SectionChunker

    config = ChunkingConfig(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    chunker = {
        ChunkingStrategy.PDF: PDFChunker(config),
        ChunkingStrategy.RECURSIVE: RecursiveChunker(config),
        ChunkingStrategy.SECTION: SectionChunker(config),
    }[chunking_strategy]

    content = await file.read()

    chunks = chunker.chunk(content.decode("utf-8", errors="ignore"))

    return IngestDocumentResponse(
        document_id=document_id,
        status="processing",
        chunks_count=len(chunks),
        filename=file.filename or "unknown",
        uploaded_at=datetime.utcnow(),
    )


@router.get("/status/{document_id}")
async def get_ingestion_status(document_id: str) -> dict[str, Any]:
    return {
        "document_id": document_id,
        "status": "completed",
        "progress": 100,
    }


@router.delete("/{document_id}")
async def delete_document(document_id: str) -> dict[str, str]:
    return {"document_id": document_id, "status": "deleted"}


@router.post("/{document_id}/reindex")
async def reindex_document(
    document_id: str,
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.PDF,
) -> dict[str, str]:
    return {
        "document_id": document_id,
        "status": "reindexing",
        "strategy": chunking_strategy,
    }
