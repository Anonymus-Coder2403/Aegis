import re
from typing import Any

from .base import BaseChunker, Chunk, ChunkingConfig


class RecursiveChunker(BaseChunker):
    def __init__(self, config: ChunkingConfig | None = None):
        super().__init__(config)
        self.separators = self._build_separators()

    def _build_separators(self) -> list[str]:
        return [
            "\n\n\n",
            "\n\n",
            "\n",
            ". ",
            "! ",
            "? ",
            "; ",
            ", ",
            " ",
            "",
        ]

    def chunk(self, text: str, **kwargs) -> list[Chunk]:
        chunks = self._split_text(text, self.config.chunk_size)
        return self._create_chunks_with_metadata(chunks, text)

    def _split_text(self, text: str, chunk_size: int) -> list[str]:
        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        for separator in self.separators:
            if separator == "":
                return self._fixed_chunk(text, chunk_size)

            parts = text.split(separator)
            if len(parts) <= 1:
                continue

            chunks = []
            current_chunk = ""

            for part in parts:
                test_chunk = current_chunk + separator + part if current_chunk else part

                if len(test_chunk) <= chunk_size:
                    current_chunk = test_chunk
                else:
                    if current_chunk:
                        chunks.append(current_chunk)

                    if len(part) > chunk_size:
                        sub_chunks = self._split_text(part, chunk_size)
                        chunks.extend(sub_chunks[:-1])
                        current_chunk = sub_chunks[-1] if sub_chunks else part
                    else:
                        current_chunk = part

            if current_chunk:
                chunks.append(current_chunk)

            if len(chunks) > 1:
                return self._apply_overlap(chunks)

        return self._fixed_chunk(text, chunk_size)

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        if len(chunks) <= 1 or self.config.chunk_overlap == 0:
            return chunks

        overlapped = [chunks[0]]
        overlap_text = chunks[0]

        for i in range(1, len(chunks)):
            chunk_words = chunks[i].split()
            overlap_words = overlap_text.split()[-self.config.chunk_overlap :]

            overlapped_chunk = " ".join(overlap_words) + " " + chunks[i]
            overlapped.append(overlapped_chunk)
            overlap_text = chunks[i]

        return overlapped

    def _fixed_chunk(self, text: str, chunk_size: int) -> list[str]:
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            if end < len(text):
                last_period = chunk.rfind(". ")
                last_newline = chunk.rfind("\n")

                split_point = max(last_period, last_newline)
                if split_point > chunk_size - 100:
                    chunk = chunk[: split_point + 1]
                    end = start + split_point + 1

            chunks.append(chunk.strip())
            start = end - self.config.chunk_overlap if end < len(text) else end

        return [c for c in chunks if c.strip()]

    def _create_chunks_with_metadata(
        self, chunks: list[str], original_text: str
    ) -> list[Chunk]:
        result = []
        current_pos = 0

        for i, chunk_text in enumerate(chunks):
            pos = original_text.find(chunk_text, current_pos)
            if pos == -1:
                pos = current_pos

            result.append(
                self._create_chunk(
                    text=chunk_text,
                    start_index=pos,
                    end_index=pos + len(chunk_text),
                    metadata={"chunk_id": i, "total_chunks": len(chunks)},
                )
            )
            current_pos = pos + len(chunk_text)

        return result
