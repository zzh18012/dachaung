r"""pipeline 各级标题拉段一致、链块元数据
与多行拼接（Round 1741）。

新角度：R1740 锁拉段 800 边界——**h1–h6
六级行为全同（'T bbb' 2 ids）、链块
metadata 含 strategy/max_chars/
char_count 三键、多行引用入链内部 \\n 保
留拼接用单空格**零覆盖：

- **'#'×lvl+' T\\n\\nbbb'**：六级全部
  'T bbb'（2 ids，sequential）
- **'## T\\n\\n- a'**：chunk metadata =
  {'strategy','max_chars','char_count'}
- **'> line a\\n> line b'+'bbb'**：
  'line a\\nline b bbb'（2 ids）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_all_heading_levels_pull(tmp_path):
    for lvl in range(1, 7):
        doc, errors = _run(
            tmp_path, "#" * lvl + " T\n\nbbb\n")
        assert errors == []
        assert [(c.text, len(c.source_element_ids))
                for c in doc.chunks] == [("T bbb", 2)], lvl


def test_chain_chunk_metadata_keys(tmp_path):
    doc, errors = _run(tmp_path, "## T\n\n- a\n")
    assert errors == []
    assert len(doc.chunks) == 1
    assert doc.chunks[0].metadata == {
        "strategy": "sequential", "max_chars": 800,
        "char_count": 3}


def test_multiline_element_join_single_space(tmp_path):
    doc, errors = _run(
        tmp_path, "> line a\n> line b\n\nbbb\n")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "line a\nline b"),
        ("paragraph", "bbb")]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [
        ("line a\nline b bbb", 2)]
