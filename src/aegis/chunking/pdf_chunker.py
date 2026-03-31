from dataclasses import dataclass
from typing import Any, BinaryIO

from .base import BaseChunker, Chunk, ChunkingConfig
from .section_chunker import SectionChunker
from .recursive_chunker import RecursiveChunker


@dataclass
class PDFPage:
    page_number: int
    text: str
    width: float = 0
    height: float = 0


class PDFChunker(BaseChunker):
    def __init__(self, config: ChunkingConfig | None = None):
        super().__init__(config)
        self.section_chunker = SectionChunker(config)
        self.recursive_chunker = RecursiveChunker(config)

    def chunk(self, text: str, **kwargs) -> list[Chunk]:
        pages: list[PDFPage] | None = kwargs.get("pages")

        if pages:
            return self._chunk_by_pages(pages, text)

        return self._chunk_by_sections_or_recursive(text)

    def _chunk_by_pages(self, pages: list[PDFPage], full_text: str) -> list[Chunk]:
        chunks = []

        for page in pages:
            page_text = page.text.strip()
            if not page_text:
                continue

            if len(page_text) <= self.config.chunk_size:
                chunks.append(
                    self._create_chunk(
                        text=page_text,
                        start_index=0,
                        end_index=len(page_text),
                        metadata={
                            "page_number": page.page_number,
                            "source": "pdf_page",
                        },
                    )
                )
            else:
                page_chunks = self.recursive_chunker.chunk(page_text)
                for chunk in page_chunks:
                    chunks.append(
                        self._create_chunk(
                            text=chunk.text,
                            start_index=chunk.start_index,
                            end_index=chunk.end_index,
                            metadata={
                                "page_number": page.page_number,
                                "source": "pdf_page",
                                **chunk.metadata,
                            },
                        )
                    )

        return self._add_headings_to_chunks(chunks, full_text)

    def _chunk_by_sections_or_recursive(self, text: str) -> list[Chunk]:
        section_chunks = self.section_chunker.chunk(text)

        if len(section_chunks) <= len(text) // self.config.chunk_size:
            return section_chunks

        return self.recursive_chunker.chunk(text)

    def _add_headings_to_chunks(
        self, chunks: list[Chunk], full_text: str
    ) -> list[Chunk]:
        current_heading = None
        heading_pattern = self.section_chunker.heading_pattern

        for chunk in chunks:
            chunk_end = chunk.end_index
            text_before = full_text[:chunk_end]

            matches = list(heading_pattern.finditer(text_before))
            if matches:
                last_heading = matches[-1].group()
                if last_heading != current_heading:
                    current_heading = last_heading

            if current_heading:
                chunk.metadata["section_heading"] = current_heading

        return chunks


class PDFProcessor:
    def __init__(self, chunker: PDFChunker | None = None):
        self.chunker = chunker or PDFChunker()

    def process_file(self, file: BinaryIO, filename: str) -> list[Chunk]:
        try:
            import PyPDF2
        except ImportError:
            return self._fallback_process(file, filename)

        try:
            reader = PyPDF2.PdfReader(file)
            pages = []

            for i, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                pages.append(PDFPage(page_number=i, text=text))

            full_text = "\n\n".join(p.text for p in pages)
            return self.chunker.chunk(full_text, pages=pages)

        except Exception:
            file.seek(0)
            text = file.read().decode("utf-8", errors="ignore")
            return self.chunker.chunk(text)

    def _fallback_process(self, file: BinaryIO, filename: str) -> list[Chunk]:
        try:
            text = file.read().decode("utf-8", errors="ignore")
        except Exception:
            text = ""

        return self.chunker.chunk(text)
