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
from typing import Any

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


@dataclass(frozen=True)
class _SplitPiece:
    """_hard_split_with_whitespace_fallback 与 _split_long_text 的产物。

    boundary_after 取值：
    - "whitespace"：piece 结尾是闭区间内最右空白处切开（whitespace 回退）。
    - "forced_char"：piece 结尾是 upper 处固定字符兜底（窗口内无空白）。
    - None：piece 是输入文本的自然结尾（remaining ≤ max_chars）或
      自然句子累积到容量上限而 flush。
    """

    text: str
    boundary_after: str | None


def _hard_split_with_whitespace_fallback(
    text: str, max_chars: int
) -> list[_SplitPiece]:
    """把单个句子（已确认 len > max_chars）切成 ≤ max_chars 的 piece 列表。

    每轮：
    1. 跳过所有前导空白（不产生纯空白 piece）。
    2. remaining ≤ max_chars 时输出 rstrip 后的自然尾段，boundary_after=None。
    3. remaining > max_chars 时在闭区间 [i + max_chars//2, i + max_chars]
       从右向左找 isspace() 字符：
       - 找到 → piece = text[i:ws_idx].rstrip()；游标跳过 ws_idx 及其后连续空白；
         若仍有非空白文本 boundary_after="whitespace"，否则 None。
       - 未找到 → piece = text[i:upper]，boundary_after="forced_char"。
    """
    n = len(text)
    pieces: list[_SplitPiece] = []
    i = 0
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break

        remaining = n - i
        if remaining <= max_chars:
            pieces.append(_SplitPiece(text=text[i:n].rstrip(), boundary_after=None))
            i = n
            break

        lower = i + max_chars // 2
        upper = i + max_chars
        ws_idx = -1
        for j in range(upper, lower - 1, -1):
            if text[j].isspace():
                ws_idx = j
                break

        if ws_idx != -1:
            piece_text = text[i:ws_idx].rstrip()
            next_i = ws_idx + 1
            while next_i < n and text[next_i].isspace():
                next_i += 1
            has_more = next_i < n
            boundary_after = "whitespace" if has_more else None
            i = next_i
        else:
            piece_text = text[i:upper]
            boundary_after = "forced_char"
            i = upper

        pieces.append(_SplitPiece(text=piece_text, boundary_after=boundary_after))

    return pieces


def _split_long_text(text: str, max_chars: int) -> list[_SplitPiece]:
    """把超长 element 文本切成不超过 max_chars 的 piece 列表。

    入口统一 strip；空串或纯空白返回 []。
    len(text) ≤ max_chars 时返回单个 boundary_after=None 的 piece。
    否则按 _SENTENCE_SPLIT_RE 句子切，每句超长则调
    _hard_split_with_whitespace_fallback，最后累积成 ≤ max_chars 的 piece。

    累积规则：
    - 多 piece 合并用单空格 joiner。
    - chunk 的 boundary_after 取最后一个输入 piece 的值。
    - 自然句子累积到容量上限而 flush → boundary_after 保持 None
      （不写 metadata.split_boundary_after）。
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [_SplitPiece(text=text, boundary_after=None)]

    raw_pieces: list[_SplitPiece] = []
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        if not sentence:
            continue
        if len(sentence) <= max_chars:
            raw_pieces.append(_SplitPiece(text=sentence, boundary_after=None))
        else:
            raw_pieces.extend(
                _hard_split_with_whitespace_fallback(sentence, max_chars)
            )

    out: list[_SplitPiece] = []
    buf_text = ""
    buf_boundary: str | None = None
    for p in raw_pieces:
        sep = 1 if buf_text else 0
        if not buf_text:
            buf_text = p.text
            buf_boundary = p.boundary_after
        elif len(buf_text) + sep + len(p.text) <= max_chars:
            buf_text = buf_text + " " + p.text
            buf_boundary = p.boundary_after
        else:
            out.append(_SplitPiece(text=buf_text, boundary_after=buf_boundary))
            buf_text = p.text
            buf_boundary = p.boundary_after
    if buf_text:
        out.append(_SplitPiece(text=buf_text, boundary_after=buf_boundary))
    return out


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
                    if not piece.text:
                        continue
                    meta: dict[str, Any] = {
                        "strategy": "long_paragraph_sentence_split",
                        "max_chars": self.max_chars,
                        "char_count": len(piece.text),
                    }
                    if piece.boundary_after is not None:
                        meta["split_boundary_after"] = piece.boundary_after
                    chunks.append(
                        Chunk(
                            chunk_id=f"{document.document_id}::c{counter:04d}",
                            text=piece.text,
                            source_element_ids=[el.element_id],
                            metadata=meta,
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
