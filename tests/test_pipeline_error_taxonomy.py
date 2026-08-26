r"""pipeline 失败分类学：坏 JSON、旧
nbformat、缺文件与解析器崩溃（Round 1753）。

新角度：R1752 锁空输入契约——**四类失败
统一 (None, [ErrorRecord])：ipynb 坏
JSON→ipynb_invalid_json（details 含
exception_type）；nbformat 3→
ipynb_unsupported_version；缺文件→
file_not_found（'hash 目标不是文件'）；
'##   ' 崩溃→unexpected_parser_error
（details 含 parser_name）**零覆盖：

- **'{not json'**：code+exception_type
  JSONDecodeError+message 含 json 报错
- **nbformat=3**：code+message 无 details
- **不存在文件**：code+details path
- **'##   '**：message 以 'ValueError:'
  开头、details parser_name 'markdown'
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_invalid_json_error(tmp_path):
    p = tmp_path / "bad.ipynb"
    p.write_text("{not json", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert doc is None
    assert len(errors) == 1
    e = errors[0]
    assert e.code == "ipynb_invalid_json"
    assert e.message.startswith(".ipynb 不是合法 JSON:")
    assert "Expecting property name" in e.message
    assert e.details["exception_type"] == "JSONDecodeError"
    assert e.details["path"] == str(p)


def test_nbformat3_error(tmp_path):
    p = tmp_path / "old.ipynb"
    p.write_text(json.dumps(
        {"cells": [], "metadata": {}, "nbformat": 3}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert doc is None
    assert [(e.code, e.message) for e in errors] == [
        ("ipynb_unsupported_version",
         "仅支持 nbformat ≥ 4，得到 nbformat=3")]


def test_missing_file_error(tmp_path):
    p = tmp_path / "nope.md"
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert doc is None
    e = errors[0]
    assert e.code == "file_not_found"
    assert e.message == f"hash 目标不是文件: {p}"
    assert e.details == {"path": str(p)}


def test_ws_heading_crash_error(tmp_path):
    p = tmp_path / "crash.md"
    p.write_text("##   \n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert doc is None
    e = errors[0]
    assert e.code == "unexpected_parser_error"
    assert e.message.startswith("ValueError: element doc-")
    assert "必须至少有" in e.message
    assert e.details == {
        "path": str(p), "parser_name": "markdown"}
