r"""markdown CRLF 全面归一化（Round 1857）。

新角度（probe 实证，grep 核实零覆盖——'\r' 相关测试只在
text/kreuzberg/fallback/chunker/evaluation 侧，markdown 结构
性 CRLF 全库零覆盖；Windows 记事本风格 .md 是真实输入形态）：
- **结构全清**：heading/list/fence/bq/table 的 '\r' 全部剥离，
  行定位按行正确（body line 3、第二 list_item line 2）
- **EOF 裸 CR**：'# H\r'（无 \n 收尾）→ heading 'H'；
  '---\r\n' 仍判 thematic break（零元素）
- **setext 不受影响**：'H\r\n===\r\n' → paragraph 'H\n==='
  （setext 本就不支持，与 LF 的合并行为逐字一致）；
  'H\r\n---\r\n' → paragraph 'H'（'---' 行 thematic 掉）
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.markdown_parser import MarkdownParser


def _parse(raw: bytes):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "a.md"
        p.write_bytes(raw)
        return MarkdownParser().parse(p, compute_file_hash(p))


def test_md_crlf_structures_normalized():
    doc = _parse(b"# H\r\n\r\nbody\r\n")
    assert [(e.type, e.content, e.metadata) for e in doc.elements] == [
        ("heading", "H", {"level": 1}), ("paragraph", "body", {})]
    assert doc.elements[0].source_locator == {"line": 1, "section_path": "H"}
    assert doc.elements[1].type == "paragraph"
    assert doc.elements[1].content == "body"
    assert doc.elements[1].source_locator["line"] == 3

    doc = _parse(b"- a\r\n- b\r\n")
    assert [(e.type, e.content) for e in doc.elements] == [
        ("list_item", "a"), ("list_item", "b")]
    assert doc.elements[1].source_locator["line"] == 2

    doc = _parse(b"```py\r\nx=1\r\n```\r\n")
    assert [(e.type, e.content, e.metadata) for e in doc.elements] == [
        ("paragraph", "x=1", {"kind": "code_block", "language": "py"})]


def test_md_crlf_eof_cr_and_thematic():
    doc = _parse(b"# H\r")
    assert [(e.type, e.content) for e in doc.elements] == [("heading", "H")]

    assert _parse(b"---\r\n").elements == []

    doc = _parse(b"H\r\n---\r\n")
    assert [(e.type, e.content) for e in doc.elements] == [("paragraph", "H")]


def test_md_crlf_table_setext_normalized():
    doc = _parse(b"| a | b |\r\n| --- | --- |\r\n| c | d |\r\n")
    assert [(e.type, e.content, e.metadata) for e in doc.elements] == [
        ("table", "| a | b |\n| --- | --- |\n| c | d |",
         {"row_count": 2, "col_count": 2, "source": "markdown_pipe_table"})]

    doc = _parse(b"H\r\n===\r\n")
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "H\n===")]
