r"""pipeline id 形态、section_path 转换与
source_spans 现状（Round 1744）。

新角度：R1743 锁 html 链同构——**结构字
段零覆盖：element_id 'doc-<16hex>::eNNNN'
4 位序号、section_path 首标题前缺失后跟
随、合并块 source_spans 各元素 start 恒 0
长度=元素长（非 chunk 内偏移，现状锁定）、
confidence 0.95 与 doc 元数据**：

- **'## T\\n\\nbbb\\n\\nccc'**：e0000-e0002
  顺序 id；chunk 'T bbb ccc' spans
  (0,1)/(0,3)/(0,3)
- **'intro\\n\\n## T\\n\\nbbb\\n\\n## U\\n\\nccc'**：
  首元素 locator 无 section_path 键，
  T 段 'T'、U 段 'U'
- **doc 字段**：source_type 'markdown'、
  parser_version 'stdlib/0.1.0'、
  metadata {'markdown': True}、
  relations []、confidence 0.95
"""

from __future__ import annotations

import re

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_sequential_element_ids_and_spans(tmp_path):
    doc, errors = _run(tmp_path, "## T\n\nbbb\n\nccc\n")
    assert errors == []
    pat = re.compile(r"^doc-[0-9a-f]{16}::e\d{4}$")
    assert all(pat.match(e.element_id)
               for e in doc.elements)
    assert re.match(
        r"^doc-[0-9a-f]{16}::c\d{4}$",
        doc.chunks[0].chunk_id)
    assert doc.chunks[0].text == "T bbb ccc"
    assert [(s["start"], s["end"])
            for s in doc.chunks[0].source_spans] == [
        (0, 1), (0, 3), (0, 3)]
    assert [s["element_id"] for s in
            doc.chunks[0].source_spans] == [
        e.element_id for e in doc.elements]


def test_section_path_transitions(tmp_path):
    doc, errors = _run(
        tmp_path,
        "intro\n\n## T\n\nbbb\n\n## U\n\nccc\n")
    assert errors == []
    assert [e.source_locator for e in doc.elements] == [
        {"line": 1}, {"line": 3, "section_path": "T"},
        {"line": 5, "section_path": "T"},
        {"line": 7, "section_path": "U"},
        {"line": 9, "section_path": "U"}]


def test_document_level_fields(tmp_path):
    doc, errors = _run(tmp_path, "x\n")
    assert errors == []
    assert doc.source_type == "markdown"
    assert doc.parser_name == "markdown"
    assert doc.parser_version == "stdlib/0.1.0"
    assert doc.metadata == {"markdown": True}
    assert doc.relations == []


def test_element_confidence_default(tmp_path):
    doc, errors = _run(tmp_path, "x\n")
    assert errors == []
    assert all(e.confidence == 0.95
               for e in doc.elements)
    assert all(e.parent_id is None
               for e in doc.elements)
