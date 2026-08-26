r"""pipeline 超限标题：永不切分、不拉段
与 799 合并边界（Round 1771）。

新角度：R1770 锁 JSON 警告——**标题自
身超 800 也原样单 chunk 不切（850）；
恰好合并不超时才拉段：795+' bbb'=799
合并（2 ids）、798+' bbb'=802 分开两
块**零覆盖：

- **'## '+H×850+'bbb'**：850（1 id，
  不拆）+ 'bbb'（1 id）
- **'## '+H×798+'bbb'**：798 + 3 两块
- **'## '+H×795+'bbb'**：单 chunk 799
  （2 ids）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, n):
    p = tmp_path / "d.md"
    p.write_text(
        "## " + "H" * n + "\n\nbbb\n", encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_oversized_heading_never_split(tmp_path):
    doc, errors = _run(tmp_path, 850)
    assert errors == []
    assert [(len(c.text), len(c.source_element_ids),
             c.text[:2]) for c in doc.chunks] == [
        (850, 1, "HH"), (3, 1, "bb")]


def test_heading_798_no_pull(tmp_path):
    doc, errors = _run(tmp_path, 798)
    assert errors == []
    assert [(len(c.text), len(c.source_element_ids))
            for c in doc.chunks] == [
        (798, 1), (3, 1)]


def test_heading_795_pulls_to_799(tmp_path):
    doc, errors = _run(tmp_path, 795)
    assert errors == []
    assert [(len(c.text), len(c.source_element_ids))
            for c in doc.chunks] == [(799, 2)]
    assert doc.chunks[0].text.endswith("bbb")
