r"""pipeline 超长标题豁免切分、不吸
尾段、max_chars 31 触底 ValueError
（Round 1830）。

新角度：R1829 读 chunker 源码锁真表
孤立——**heading 分支（310-315 行）
绕过超长切分：900 字标题单块 900
sequential 不劈（与表格豁免平行）；
超长标题不吸收后随短段（投影超限
flush）；max_chars=31 < 32 触底 →
chunker_failed ValueError**零覆盖：

- **900 字标题**：单块 (900, seq)
- **标题+段**：(900)+(4) 两块
- **max_chars 31**：ValueError
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, **kw):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown", **kw)


def test_oversize_heading_never_splits(tmp_path):
    doc, errors = _run(tmp_path, "# " + "H" * 900 + "\n")
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"])
            for c in doc.chunks] == [
        (900, "sequential")]


def test_oversize_heading_no_pull(tmp_path):
    doc, errors = _run(
        tmp_path, "# " + "H" * 900 + "\n\nbody\n")
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"],
             len(c.source_element_ids))
            for c in doc.chunks] == [
        (900, "sequential", 1),
        (4, "sequential", 1)]


def test_maxchars_floor_valueerror(tmp_path):
    doc, errors = _run(tmp_path, "x\n", max_chars=31)
    assert doc is None
    assert errors[0].code == "chunker_failed"
    assert errors[0].details["exception_type"] == \
        "ValueError"
