import re
from typing import Any

from .base import BaseChunker, Chunk, ChunkingConfig


class SectionChunker(BaseChunker):
    def __init__(self, config: ChunkingConfig | None = None):
        super().__init__(config)
        self.heading_pattern = self._build_heading_pattern()

    def _build_heading_pattern(self) -> re.Pattern:
        patterns = [
            r"^#{1,6}\s+.+$",
            r"^(?:chapter|section|part)\s+\d+[\.:]\s*.+$",
            r"^[IVXLC]+\.\s+.+$",
            r"^\d+(?:\.\d+)*\s+.+$",
        ]
        return re.compile("|".join(patterns), re.MULTILINE | re.IGNORECASE)

    def chunk(self, text: str, **kwargs) -> list[Chunk]:
        sections = self._extract_sections(text)
        if not sections:
            return self._chunk_as_single(text)

        chunks = []
        for section in sections:
            section_text = section["text"]
            section_size = len(section_text)

            if section_size <= self.config.chunk_size:
                chunks.append(
                    self._create_chunk(
                        text=section_text,
                        start_index=section["start"],
                        end_index=section["end"],
                        metadata={
                            "section_heading": section.get("heading"),
                            "section_level": section.get("level", 1),
                        },
                    )
                )
            else:
                sub_chunks = self._chunk_large_section(
                    section_text, section["start"], section.get("heading")
                )
                chunks.extend(sub_chunks)

        return self._merge_small_chunks(chunks)

    def _extract_sections(self, text: str) -> list[dict[str, Any]]:
        matches = list(self.heading_pattern.finditer(text))
        if not matches:
            return []

        sections = []
        for i, match in enumerate(matches):
            heading = match.group().strip()
            level = self._get_heading_level(heading)
            start = match.start()

            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(text)

            section_text = text[start:end].strip()
            if section_text:
                sections.append(
                    {
                        "heading": heading,
                        "level": level,
                        "start": start,
                        "end": end,
                        "text": section_text,
                    }
                )

        return sections

    def _get_heading_level(self, heading: str) -> int:
        if heading.startswith("#"):
            return len(heading) - len(heading.lstrip("#"))
        return 1

    def _chunk_large_section(
        self, text: str, offset: int, heading: str | None
    ) -> list[Chunk]:
        words = text.split()
        chunks = []

        for i in range(
            0, len(words), self.config.chunk_size - self.config.chunk_overlap
        ):
            chunk_words = words[i : i + self.config.chunk_size]
            chunk_text = " ".join(chunk_words)

            if len(chunk_text) < self.config.min_chunk_size:
                if chunks:
                    chunks[-1] = Chunk(
                        text=chunks[-1].text + " " + chunk_text,
                        start_index=chunks[-1].start_index,
                        end_index=offset + i * 5 + len(chunk_text),
                        metadata=chunks[-1].metadata,
                    )
                continue

            start = offset + (i * 5)
            end = start + len(chunk_text)

            chunks.append(
                self._create_chunk(
                    text=chunk_text,
                    start_index=start,
                    end_index=end,
                    metadata={"section_heading": heading},
                )
            )

        return chunks

    def _chunk_as_single(self, text: str) -> list[Chunk]:
        return [self._create_chunk(text=text, start_index=0, end_index=len(text))]

    def _merge_small_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        if not chunks:
            return []

        merged = [chunks[0]]

        for chunk in chunks[1:]:
            if len(chunk.text) < self.config.min_chunk_size and merged:
                merged[-1] = Chunk(
                    text=merged[-1].text + " " + chunk.text,
                    start_index=merged[-1].start_index,
                    end_index=chunk.end_index,
                    metadata=merged[-1].metadata,
                )
            else:
                merged.append(chunk)

        return merged
