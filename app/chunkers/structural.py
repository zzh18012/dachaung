"""基础结构分块器（标题硬边界 + 长度上限 + source_element_ids + source_spans）。

规则：
1. heading element 是硬边界：之前的 chunk 立即封口，新 chunk 从 heading 开始
2. table/image/caption element 单独成 chunk（保留完整结构）
3. paragraph / list_item：累积到当前 chunk，超 max_chars 就开新 chunk
4. 单个 paragraph 自身超 max_chars 时按句子切分；句子也太长就硬切
5. 每个 chunk 至少记录一个 source_element_id
6. 不修改文本内容，仅切段（保证"不丢不重"）
7. 每个 chunk 带 source_spans：每个被引用 element 在其 content 中的字符区间
   [start, end)（契约 docs/chunker-source-spans-contract.md）；空列表表示
   该 chunk 不带 span 信息（向后兼容旧 chunker 输出）
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

# ipynb cell 边界哨兵（契约 docs/chunker-ipynb-cell-contract.md §1/§2）：
# _NO_CELL 是起始态标记；_UNGROUPED() 每次返回全新对象，
# 使 locator 异常缺失 cell_index 的连续元素各自成组、不互相合并。
_NO_CELL = object()


def _UNGROUPED() -> object:
    return object()


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

    start / end：piece 在传入 _split_long_text 的（已 strip 的）text 中的
    字符区间 [start, end)（契约规则 5）。调用方负责加上 el_start 映射到
    element.content 坐标。
    """

    text: str
    boundary_after: str | None
    start: int = 0
    end: int = 0


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

    每个 piece 的 start/end 在输入 text 坐标系（契约规则 5）。
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
            piece_text = text[i:n].rstrip()
            pieces.append(
                _SplitPiece(
                    text=piece_text,
                    boundary_after=None,
                    start=i,
                    end=i + len(piece_text),
                )
            )
            i = n
            break

        lower = i + max_chars // 2
        upper = i + max_chars
        ws_idx = -1
        for j in range(upper, lower - 1, -1):
            if text[j].isspace():
                ws_idx = j
                break

        piece_start = i
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

        pieces.append(
            _SplitPiece(
                text=piece_text,
                boundary_after=boundary_after,
                start=piece_start,
                end=piece_start + len(piece_text),
            )
        )

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

    每个 piece 的 start/end 在输入 text（已 strip）坐标系；句子合并时
    end 扩到后句结尾（句间空白含于合并 span，契约规则 5）。
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [_SplitPiece(text=text, boundary_after=None, start=0, end=len(text))]

    raw_pieces: list[_SplitPiece] = []
    pos = 0
    for sentence in _SENTENCE_SPLIT_RE.split(text):
        if not sentence:
            continue
        # 在 text 中从 pos 起定位 sentence（句子之间是正则吃掉的空白）
        sentence_start = text.find(sentence, pos)
        if sentence_start < 0:
            sentence_start = pos  # 防御性 fallback
        if len(sentence) <= max_chars:
            raw_pieces.append(
                _SplitPiece(
                    text=sentence,
                    boundary_after=None,
                    start=sentence_start,
                    end=sentence_start + len(sentence),
                )
            )
        else:
            for sp in _hard_split_with_whitespace_fallback(sentence, max_chars):
                raw_pieces.append(
                    _SplitPiece(
                        text=sp.text,
                        boundary_after=sp.boundary_after,
                        start=sentence_start + sp.start,
                        end=sentence_start + sp.end,
                    )
                )
        pos = sentence_start + len(sentence)

    out: list[_SplitPiece] = []
    buf_text = ""
    buf_start = 0
    buf_end = 0
    buf_boundary: str | None = None
    for p in raw_pieces:
        sep = 1 if buf_text else 0
        if not buf_text:
            buf_text = p.text
            buf_start = p.start
            buf_end = p.end
            buf_boundary = p.boundary_after
        elif len(buf_text) + sep + len(p.text) <= max_chars:
            buf_text = buf_text + " " + p.text
            buf_end = p.end  # 扩到包含当前 piece（句间空白在 [buf_start, buf_end) 内）
            buf_boundary = p.boundary_after
        else:
            out.append(
                _SplitPiece(
                    text=buf_text,
                    boundary_after=buf_boundary,
                    start=buf_start,
                    end=buf_end,
                )
            )
            buf_text = p.text
            buf_start = p.start
            buf_end = p.end
            buf_boundary = p.boundary_after
    if buf_text:
        out.append(
            _SplitPiece(
                text=buf_text,
                boundary_after=buf_boundary,
                start=buf_start,
                end=buf_end,
            )
        )
    return out


# _ChunkBuffer.parts 元组的字段索引
_PART_TEXT = 0
_PART_ELEMENT_ID = 1
_PART_START = 2  # 该段文本在 element.content 中的起始位置（契约规则 3/4）
_PART_END = 3    # 结束位置（exclusive）


@dataclass
class _ChunkBuffer:
    """累积中的 chunk。flush 时生成 Chunk。"""
    document_id: str
    parts: list[tuple[str, str, int, int]] = field(default_factory=list)
    counter: int = 0  # 由 chunker 维护，确保 chunk_id 递增

    def push_text(self, text: str, element_id: str, start: int, end: int) -> None:
        self.parts.append((text, element_id, start, end))

    def length(self) -> int:
        return sum(len(p[_PART_TEXT]) for p in self.parts)

    def is_empty(self) -> bool:
        return not self.parts

    def flush(self, *, strategy: str, max_chars: int) -> Chunk | None:
        if self.is_empty():
            return None
        text = " ".join(p[_PART_TEXT] for p in self.parts).strip()
        if not text:
            return None
        # source_element_ids：保留首次出现顺序去重（既有语义不变）
        source_ids: list[str] = []
        for p in self.parts:
            eid = p[_PART_ELEMENT_ID]
            if eid not in source_ids:
                source_ids.append(eid)
        # source_spans：每个 part 一项，按 part 顺序（契约规则 6，不去重）
        spans: list[dict[str, Any]] = [
            {
                "element_id": p[_PART_ELEMENT_ID],
                "start": p[_PART_START],
                "end": p[_PART_END],
            }
            for p in self.parts
        ]
        chunk = Chunk(
            chunk_id=f"{self.document_id}::c{self.counter:04d}",
            text=text,
            source_element_ids=source_ids,
            metadata={
                "strategy": strategy,
                "max_chars": max_chars,
                "char_count": len(text),
            },
            source_spans=spans,
        )
        # 清空，等下次复用
        self.parts.clear()
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
        # ipynb cell 硬边界状态（契约 docs/chunker-ipynb-cell-contract.md §1/§2）：
        # 仅 source_type == "ipynb" 时激活；非 ipynb 路径不进入该分支，
        # 既有分块结果保持不变。
        is_ipynb = document.source_type == "ipynb"
        current_cell: Any = _NO_CELL

        def flush(strategy: str = "sequential") -> None:
            nonlocal counter
            buf.counter = counter
            c = buf.flush(strategy=strategy, max_chars=self.max_chars)
            if c is not None:
                chunks.append(c)
                counter += 1

        for el in document.elements:
            text, el_start, el_end = self._element_text_with_span(el)
            if not text:
                continue

            # 0. ipynb cell 硬边界：相邻元素 cell_index 不同 → 先封口再开新
            #    chunk；相邻短 cell 即使未达 max_chars 也不得合并（规则 1/3）。
            #    locator 异常缺失 cell_index → 该元素自成一组（不崩溃不猜测）。
            if is_ipynb:
                loc = el.source_locator if isinstance(el.source_locator, dict) else {}
                if "cell_index" in loc:
                    cell = loc["cell_index"]
                    if cell != current_cell:
                        flush()
                        current_cell = cell
                else:
                    flush()
                    current_cell = _UNGROUPED()

            # 1. table/image/caption：单独成 chunk（先 flush 当前 buf）
            if el.type in ("table", "image", "caption"):
                flush()
                # 单元素 chunk
                buf.push_text(text, el.element_id, el_start, el_end)
                flush(strategy=f"isolated_{el.type}")
                continue

            # 2. heading：硬边界（先 flush 当前 buf，heading 进入新 buf）
            if el.type == "heading":
                flush()
                buf.push_text(text, el.element_id, el_start, el_end)
                # heading 之后还会接 paragraph，继续累积
                continue

            # 3. paragraph / list_item / 其他
            # 3a. 自身就超长 → 先 flush 当前 buf，再按句子切
            #     （切分只发生在该 element 内，天然不跨 cell——规则 2）
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
                            source_spans=[
                                {
                                    "element_id": el.element_id,
                                    # piece.start/end 在 stripped 坐标系；
                                    # el_start 是 stripped 文本在 el.content
                                    # 中的偏移（契约规则 3/5）
                                    "start": el_start + piece.start,
                                    "end": el_start + piece.end,
                                }
                            ],
                        )
                    )
                    counter += 1
                continue

            # 3b. 加入当前 buf 是否超长？
            projected = buf.length() + (1 if buf.length() > 0 else 0) + len(text)
            if projected > self.max_chars and not buf.is_empty():
                flush()
            buf.push_text(text, el.element_id, el_start, el_end)

        flush()
        return chunks

    def _element_text_with_span(self, el: Element) -> tuple[str, int, int]:
        """获取 element 的可分块文本与它在 el.content 中的字符区间。

        返回 (stripped_text, start, end)（契约规则 3/4）：
        - stripped_text = (el.content or "").strip()
        - start = stripped_text 在 el.content 中的起始位置（用 lstrip 长度
          推算，不用 find——内容重复时会定位错）
        - end = start + len(stripped_text)（exclusive）

        image / 空文本 element 返回 ("", 0, 0)。
        """
        if el.type == "image":
            # 图片本身没文本，但 metadata.caption 可以作为 chunk 内容
            # 本阶段不实现图片提取，所以图片 element 不参与分块
            return "", 0, 0
        raw = el.content or ""
        if not raw:
            return "", 0, 0
        stripped = raw.strip()
        if not stripped:
            return "", 0, 0
        start = len(raw) - len(raw.lstrip())
        end = start + len(stripped)
        return stripped, start, end

    def _element_text(self, el: Element) -> str:
        """兼容旧接口：只要纯文本。"""
        return self._element_text_with_span(el)[0]


__all__ = ["StructuralChunker", "normalize_text"]
