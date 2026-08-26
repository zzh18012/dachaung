r"""pipeline 未知 parser、目录输入与
kreuzberg 扩展名限制（Round 1755）。

新角度：R1754 锁 fallback 分派——**
未知 parser 名 → unexpected_parser_error
（message 枚举全部 6 个支持名）；目录作
输入 → file_not_found；kreuzberg 同样仅
认 .pdf/.docx（.md → unsupported_type）**
零覆盖：

- **parser_name='nonexistent'**：
  message 'ValueError: 未知 parser: …
  （支持： fallback, kreuzberg, markdown,
  html, text, ipynb）'
- **目录**：'hash 目标不是文件' 同缺文件
- **kreuzberg+.md**：与 fallback 同
  unsupported_type
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _mk(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("x\n", encoding="utf-8")
    return p


def test_unknown_parser_error(tmp_path):
    p = _mk(tmp_path)
    doc, errors = process_single(
        p, write_json=False, parser_name="nonexistent")
    assert doc is None
    e = errors[0]
    assert e.code == "unexpected_parser_error"
    assert e.message == (
        "ValueError: 未知 parser: nonexistent"
        "（支持: fallback, kreuzberg, markdown, "
        "html, text, ipynb）")
    assert e.details == {
        "path": str(p), "parser_name": "nonexistent"}


def test_directory_input(tmp_path):
    sub = tmp_path / "adir"
    sub.mkdir()
    doc, errors = process_single(
        sub, write_json=False, parser_name="markdown")
    assert doc is None
    e = errors[0]
    assert e.code == "file_not_found"
    assert e.message == f"hash 目标不是文件: {sub}"


def test_kreuzberg_same_extension_limit(tmp_path):
    p = _mk(tmp_path)
    doc, errors = process_single(
        p, write_json=False, parser_name="kreuzberg")
    assert doc is None
    e = errors[0]
    assert e.code == "unsupported_type"
    assert e.message == (
        "不支持的文件扩展名: .md，仅支持 .pdf / .docx")
    assert e.details["suffix"] == ".md"
