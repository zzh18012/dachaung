r"""pipeline 默认 max_chars=800 精确边界（Round 1569）。

新角度：R1549 锁非法值与 32 下界；**默认 800 的精确
边界**（800→单 chunk / 801→双 chunk）与**超大 max_chars**
零覆盖：

- **段落恰 800 字** → 单 chunk（len==800）
- **段落 801 字** → 2 chunk（词边界切分，两段均
  ≤800，第二段以完整词开头）
- **max_chars=10** **9** → 999 字段落单 chunk
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single
from tests._synthetic_docs import (
    build_minimal_pdf,
)


def _para(total: int) -> str:
    words = []
    used = 0
    i = 0
    while True:
        w = f"w{i}"
        need = len(w) if used == 0 \
            else 1 + len(w)
        if used + need > total:
            break
        words.append(w)
        used += need
        i += 1
    rest = total - used
    if rest:
        if words:
            words[-1] += "x" * rest
        else:
            words.append("x" * rest)
    return " ".join(words)


def _chunks(tmp_path, text, **kw):
    p = tmp_path / "d.pdf"
    build_minimal_pdf(p, text=f"({text})")
    doc, errors = process_single(
        p, write_json=False, **kw)
    assert errors == []
    return doc


def test_exactly_800_single(
        tmp_path):
    text = _para(798)
    doc = _chunks(tmp_path, text)
    (el,) = doc.elements
    assert el.content == f"({text})"
    assert len(el.content) == 800
    assert [len(c.text)
            for c in doc.chunks] == [800]


def test_801_two_chunks(
        tmp_path):
    text = _para(799)
    doc = _chunks(tmp_path, text)
    (el,) = doc.elements
    assert len(el.content) == 801
    lengths = [len(c.text)
               for c in doc.chunks]
    assert len(lengths) == 2
    assert all(l <= 800
               for l in lengths)
    assert doc.chunks[1].text[0] \
        != " "


def test_huge_max_chars_single(
        tmp_path):
    text = _para(997)
    doc = _chunks(
        tmp_path, text,
        max_chars=10 ** 9)
    assert [len(c.text)
            for c in doc.chunks] == [999]
