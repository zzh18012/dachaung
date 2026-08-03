"""基础结构分块器（标题硬边界 + 长度上限 + source_element_ids）。

规则：
1. heading element 是硬边界：之前的 chunk 立即封口，新 chunk 从 heading 开始
2. table/image/caption element 单独成 chunk（保留完整结构）
3. paragraph / list_item：累积到当前 chunk，超 max_chars 就开新 chunk
4. 单个 paragraph 自身超 max_chars 时按句子切分；句子也太长就硬切
5. 每个 chunk 至少记录一个 source_element_id
6. 不修改文本内容，仅切段（保证"不丢不重"）
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.models import Chunk, Document, Element

# 句子分隔符：中英文句号、问号、叹号（保留分隔符在前一段末尾）
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?\.])\s+")
_HARD_BREAK_LANGS = ("。", "！", "？", ".", "!", "?")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(s: str) -> str:
    """统一的文本规范化规则（用于"不丢不重"测试）。

    规则：
    - 所有空白（含 \\r\\n\\t）压成单个空格
    - strip 两端

    为什么这样定义：分块器不修改文本内容，只切段；
    所以"原始 elements 的拼接" 和 "所有 chunk 文本的拼接" 在规范化后应当相等。
    """
    if not s:
        return ""
    return _WHITESPACE_RE.sub(" ", s).strip()


def _split_long_text(text: str, max_chars: int) -> list[str]:
    """把超长文本切成不超过 max_chars 的片段。

    优先级：
    1. 按句子边界（句号、问号、叹号后）
    2. 句子仍超长则硬切
    """
    if len(text) <= max_chars:
        return [text]

    # 1. 按句子切
    parts = []
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        if not sentence:
            continue
        parts.extend(_hard_split_if_needed(sentence, max_chars))

    # 2. 把句子累积成 ≤ max_chars 的片段
    out: list[str] = []
    buf = ""
    for s in parts:
        if not buf:
            buf = s
        elif len(buf) + 1 + len(s) <= max_chars:
            buf = buf + " " + s
        else:
            out.append(buf)
            buf = s
    if buf:
        out.append(buf)
    return out


def _hard_split_if_needed(text: str, max_chars: int) -> list[str]:
    """单个句子超过 max_chars 时硬切。"""
    if len(text) <= max_chars:
        return [text]
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


@dataclass
class _ChunkBuffer:
    """累积中的 chunk。flush 时生成 Chunk。"""
    document_id: str
    parts: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    counter: int = 0  # 由 chunker 维护，确保 chunk_id 递增

    def push_text(self, text: str, element_id: str) -> None:
        self.parts.append(text)
        if element_id not in self.source_ids:
            self.source_ids.append(element_id)

    def length(self) -> int:
        return sum(len(p) for p in self.parts)

    def is_empty(self) -> bool:
        return not self.parts

    def flush(self, *, strategy: str, max_chars: int) -> Chunk | None:
        if self.is_empty():
            return None
        text = " ".join(self.parts).strip()
        if not text:
            return None
        chunk = Chunk(
            chunk_id=f"{self.document_id}::c{self.counter:04d}",
            text=text,
            source_element_ids=list(self.source_ids),
            metadata={
                "strategy": strategy,
                "max_chars": max_chars,
                "char_count": len(text),
            },
        )
        # 清空，等下次复用
        self.parts.clear()
        self.source_ids.clear()
        return chunk


class StructuralChunker:
    """基础结构分块器。

    用法：
        chunker = StructuralChunker(max_chars=800)
        chunks = chunker.chunk(document)
        document.chunks = chunks
    """

    def __init__(self, max_chars: int = 800) -> None:
        if max_chars < 32:
            raise ValueError(f"max_chars 过小: {max_chars}")
        self.max_chars = max_chars

    def chunk(self, document: Document) -> list[Chunk]:
        chunks: list[Chunk] = []
        counter = 0
        buf = _ChunkBuffer(document_id=document.document_id, counter=0)

        def flush(strategy: str = "sequential") -> None:
            nonlocal counter
            buf.counter = counter
            c = buf.flush(strategy=strategy, max_chars=self.max_chars)
            if c is not None:
                chunks.append(c)
                counter += 1

        for el in document.elements:
            text = self._element_text(el)
            if not text:
                continue

            # 1. table/image/caption：单独成 chunk（先 flush 当前 buf）
            if el.type in ("table", "image", "caption"):
                flush()
                # 单元素 chunk
                buf.push_text(text, el.element_id)
                flush(strategy=f"isolated_{el.type}")
                continue

            # 2. heading：硬边界（先 flush 当前 buf，heading 进入新 buf）
            if el.type == "heading":
                flush()
                buf.push_text(text, el.element_id)
                # heading 之后还会接 paragraph，继续累积
                continue

            # 3. paragraph / list_item / 其他
            # 3a. 自身就超长 → 先 flush 当前 buf，再按句子切
            if len(text) > self.max_chars:
                flush()
                for piece in _split_long_text(text, self.max_chars):
                    if not piece.strip():
                        continue
                    # 每个 piece 单独成 chunk（因为整段已超长）
                    chunks.append(
                        Chunk(
                            chunk_id=f"{document.document_id}::c{counter:04d}",
                            text=piece.strip(),
                            source_element_ids=[el.element_id],
                            metadata={
                                "strategy": "long_paragraph_sentence_split",
                                "max_chars": self.max_chars,
                                "char_count": len(piece.strip()),
                            },
                        )
                    )
                    counter += 1
                continue

            # 3b. 加入当前 buf 是否超长？
            projected = buf.length() + (1 if buf.length() > 0 else 0) + len(text)
            if projected > self.max_chars and not buf.is_empty():
                flush()
            buf.push_text(text, el.element_id)

        flush()
        return chunks

    def _element_text(self, el: Element) -> str:
        """获取 element 的可分块文本。"""
        if el.type == "image":
            # 图片本身没文本，但 metadata.caption 可以作为 chunk 内容
            # 本阶段不实现图片提取，所以图片 element 不参与分块
            return ""
        return (el.content or "").strip()


__all__ = ["StructuralChunker", "normalize_text"]
