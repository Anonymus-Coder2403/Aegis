from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Chunk:
    text: str
    start_index: int
    end_index: int
    metadata: dict[str, Any]


@dataclass
class ChunkingConfig:
    chunk_size: int = 512
    chunk_overlap: int = 50
    min_chunk_size: int = 50


class BaseChunker(ABC):
    def __init__(self, config: ChunkingConfig | None = None):
        self.config = config or ChunkingConfig()

    @abstractmethod
    def chunk(self, text: str, **kwargs) -> list[Chunk]:
        pass

    def _create_chunk(
        self,
        text: str,
        start_index: int,
        end_index: int,
        metadata: dict[str, Any] | None = None,
    ) -> Chunk:
        return Chunk(
            text=text.strip(),
            start_index=start_index,
            end_index=end_index,
            metadata=metadata or {},
        )
