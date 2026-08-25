r"""pipeline max_chars 下限 32 与 heading×list
累积（Round 1613）。

新角度：R1612 锁 flush 交互——**max_chars < 32
一律 ValueError（与内容长度无关）**零覆盖
（R1581 的 max_chars=5 失败实为此下限）：

- **下限边界**：max_chars=31 → chunker_failed
  （exception_type=ValueError）；32 → 正常
  （源码 structural.py:280 `if max_chars < 32
  raise`）
- **与内容无关**：1 字符 heading 在 max_chars=10
  也失败；2 字符段落在 2/5/8 均失败
- **heading 累积跨 list**：'# Head' + '- a\n- b'
  → 单 sequential chunk 'Head a b'（3 个 source id）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, max_chars,
         name="d.md"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False,
        parser_name="markdown",
        max_chars=max_chars)


def test_floor_boundary(tmp_path):
    doc31, errs31 = _run(
        tmp_path, "ab\n", 31, "a31.md")
    assert doc31 is None
    assert [(e.code, e.details)
            for e in errs31] == [
        ("chunker_failed",
         {"exception_type": "ValueError"})]

    doc32, errs32 = _run(
        tmp_path, "ab\n", 32, "a32.md")
    assert errs32 == []
    assert [(c.text,
             c.metadata["strategy"])
            for c in doc32.chunks] == [
        ("ab", "sequential")]


def test_floor_independent_of_content(
        tmp_path):
    d, e = _run(tmp_path, "# H\n", 10,
                "h10.md")
    assert d is None
    assert [x.code for x in e] == [
        "chunker_failed"]
    for mc in (2, 5, 8):
        d2, e2 = _run(
            tmp_path, "ab\n", mc,
            f"p{mc}.md")
        assert d2 is None
        assert [x.code for x in e2] == [
            "chunker_failed"]


def test_heading_accumulates_list(tmp_path):
    doc, errors = _run(
        tmp_path, "# Head\n\n- a\n- b\n", 800)
    assert errors == []
    (c,) = doc.chunks
    assert c.text == "Head a b"
    assert c.metadata["strategy"] == "sequential"
    assert len(c.source_element_ids) == 3
