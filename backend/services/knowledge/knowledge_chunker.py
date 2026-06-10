import re
from typing import Any

from backend.core.config import settings
from backend.services.knowledge.types import ChunkResult, ChunkStrategy


class KnowledgeChunker:
    """Multi-strategy chunking: semantic, recursive, table-aware, document-aware."""

    def __init__(
        self,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE_TOKENS
        self.overlap = overlap or settings.CHUNK_OVERLAP_TOKENS

    def chunk(
        self,
        text: str,
        strategy: ChunkStrategy = ChunkStrategy.SEMANTIC,
        tables: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[ChunkResult]:
        if strategy == ChunkStrategy.TABLE_AWARE and tables:
            return self._table_aware_chunk(text, tables, metadata or {})
        if strategy == ChunkStrategy.DOCUMENT_AWARE:
            return self._document_aware_chunk(text, metadata or {})
        if strategy == ChunkStrategy.RECURSIVE:
            return self._recursive_chunk(text, metadata or {})
        return self._semantic_chunk(text, metadata or {})

    def chunk_all(
        self,
        text: str,
        tables: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[ChunkResult]:
        chunks: list[ChunkResult] = []
        seen_content: set[str] = set()

        for strategy in [ChunkStrategy.DOCUMENT_AWARE, ChunkStrategy.SEMANTIC, ChunkStrategy.TABLE_AWARE]:
            for chunk in self.chunk(text, strategy, tables, metadata):
                key = chunk.content[:200]
                if key not in seen_content:
                    seen_content.add(key)
                    chunk.chunk_index = len(chunks)
                    chunks.append(chunk)

        return chunks

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    def _semantic_chunk(self, text: str, metadata: dict) -> list[ChunkResult]:
        paragraphs = re.split(r"\n\s*\n", text.strip())
        chunks: list[ChunkResult] = []
        current: list[str] = []
        current_tokens = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            para_tokens = self._estimate_tokens(para)

            if current_tokens + para_tokens > self.chunk_size and current:
                content = "\n\n".join(current)
                chunks.append(ChunkResult(
                    chunk_index=len(chunks),
                    content=content,
                    token_count=current_tokens,
                    chunk_type=ChunkStrategy.SEMANTIC.value,
                    page_number=metadata.get("page_number"),
                    metadata={"strategy": "semantic"},
                ))
                overlap_text = self._overlap_text(content)
                current = [overlap_text] if overlap_text else []
                current_tokens = self._estimate_tokens(overlap_text) if overlap_text else 0

            current.append(para)
            current_tokens += para_tokens

        if current:
            content = "\n\n".join(current)
            chunks.append(ChunkResult(
                chunk_index=len(chunks),
                content=content,
                token_count=self._estimate_tokens(content),
                chunk_type=ChunkStrategy.SEMANTIC.value,
                page_number=metadata.get("page_number"),
                metadata={"strategy": "semantic"},
            ))

        return chunks

    def _recursive_chunk(self, text: str, metadata: dict) -> list[ChunkResult]:
        separators = ["\n\n", "\n", ". ", " "]
        return self._split_recursive(text, separators, 0, metadata)

    def _split_recursive(
        self,
        text: str,
        separators: list[str],
        depth: int,
        metadata: dict,
    ) -> list[ChunkResult]:
        if self._estimate_tokens(text) <= self.chunk_size:
            return [ChunkResult(
                chunk_index=0,
                content=text.strip(),
                token_count=self._estimate_tokens(text),
                chunk_type=ChunkStrategy.RECURSIVE.value,
                metadata={"strategy": "recursive", "depth": depth},
            )]

        if depth >= len(separators):
            return self._hard_split(text, metadata)

        sep = separators[depth]
        parts = text.split(sep)
        chunks: list[ChunkResult] = []
        current = ""

        for part in parts:
            candidate = f"{current}{sep}{part}" if current else part
            if self._estimate_tokens(candidate) > self.chunk_size and current:
                chunks.extend(self._split_recursive(current, separators, depth + 1, metadata))
                current = part
            else:
                current = candidate

        if current:
            if self._estimate_tokens(current) > self.chunk_size:
                chunks.extend(self._split_recursive(current, separators, depth + 1, metadata))
            else:
                chunks.append(ChunkResult(
                    chunk_index=len(chunks),
                    content=current.strip(),
                    token_count=self._estimate_tokens(current),
                    chunk_type=ChunkStrategy.RECURSIVE.value,
                    metadata={"strategy": "recursive"},
                ))

        for i, c in enumerate(chunks):
            c.chunk_index = i
        return chunks

    def _hard_split(self, text: str, metadata: dict) -> list[ChunkResult]:
        words = text.split()
        chunks: list[ChunkResult] = []
        step = self.chunk_size - self.overlap

        for i in range(0, len(words), step):
            window = words[i : i + self.chunk_size]
            content = " ".join(window)
            chunks.append(ChunkResult(
                chunk_index=len(chunks),
                content=content,
                token_count=len(window),
                chunk_type=ChunkStrategy.RECURSIVE.value,
                metadata={"strategy": "hard_split"},
            ))
        return chunks

    def _table_aware_chunk(
        self,
        text: str,
        tables: list[dict[str, Any]],
        metadata: dict,
    ) -> list[ChunkResult]:
        chunks: list[ChunkResult] = []

        for idx, table in enumerate(tables):
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            table_type = table.get("table_type", "general")
            page = table.get("page", table.get("page_number"))

            header_line = " | ".join(str(h) for h in headers)
            table_text = f"Table: {table_type}\n{header_line}\n"
            for row in rows[:100]:
                table_text += " | ".join(str(c) for c in row) + "\n"

            chunks.append(ChunkResult(
                chunk_index=len(chunks),
                content=table_text.strip(),
                token_count=self._estimate_tokens(table_text),
                chunk_type=ChunkStrategy.TABLE_AWARE.value,
                page_number=page,
                metadata={"table_index": idx, "table_type": table_type, "strategy": "table_aware"},
            ))

        if not chunks:
            return self._semantic_chunk(text, metadata)
        return chunks

    def _document_aware_chunk(self, text: str, metadata: dict) -> list[ChunkResult]:
        sections = re.split(
            r"(?=(?:^|\n)(?:INVOICE|BILL|TAX|GST|TOTAL|SUBTOTAL|AMOUNT|VENDOR|CUSTOMER|DATE|HSN|CGST|SGST|IGST))",
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        chunks: list[ChunkResult] = []
        for section in sections:
            section = section.strip()
            if not section or self._estimate_tokens(section) < 10:
                continue
            if self._estimate_tokens(section) > self.chunk_size:
                chunks.extend(self._semantic_chunk(section, metadata))
            else:
                chunks.append(ChunkResult(
                    chunk_index=len(chunks),
                    content=section,
                    token_count=self._estimate_tokens(section),
                    chunk_type=ChunkStrategy.DOCUMENT_AWARE.value,
                    metadata={"strategy": "document_aware"},
                ))
        return chunks if chunks else self._semantic_chunk(text, metadata)

    def _overlap_text(self, text: str) -> str:
        words = text.split()
        if len(words) <= self.overlap:
            return text
        return " ".join(words[-self.overlap:])
