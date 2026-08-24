r"""app/pipeline.py 边角测试 - 第十五轮（Round 1379）。

parser 结构化错误经 process_single 透传（probe 实证，历史
pipeline 错误板只用 fallback/pdf/docx 路径，ipynb 三个专属错误
码在 pipeline 层零覆盖）：
- cells 非数组（字符串 / JSON 数组 / JSON null 三种输入）→
  ipynb_bad_structure
- nbformat=3 → ipynb_unsupported_version
- 非 JSON 文本 → ipynb_invalid_json
- ErrorRecord.details 含 path；to_dict 三键完整
- 空文件（html/md/txt）→ no_extracted_elements（各 parser 专属
  而非统一空文件码）
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, fn, content):
    (tmp_path / fn).write_text(content, encoding="utf-8")
    return process_single(
        tmp_path / fn, None,
        parser_name="ipynb", max_chars=200)


# ---------- ipynb_bad_structure 三种入口 ----------

def test_cells_string_bad_structure(tmp_path):
    doc, errors = _run(tmp_path, "a.ipynb", json.dumps(
        {"cells": "nope", "metadata": {},
         "nbformat": 4}))
    assert doc is None
    assert errors[0].code == "ipynb_bad_structure"


def test_json_array_bad_structure(tmp_path):
    doc, errors = _run(tmp_path, "b.ipynb", "[1, 2, 3]")
    assert doc is None
    assert errors[0].code == "ipynb_bad_structure"


def test_json_null_bad_structure(tmp_path):
    doc, errors = _run(tmp_path, "c.ipynb", "null")
    assert doc is None
    assert errors[0].code == "ipynb_bad_structure"


# ---------- 版本 / JSON 错误 ----------

def test_nbformat3_unsupported_version(tmp_path):
    doc, errors = _run(tmp_path, "d.ipynb", json.dumps(
        {"cells": [], "metadata": {},
         "nbformat": 3}))
    assert doc is None
    assert errors[0].code == \
        "ipynb_unsupported_version"


def test_not_json_invalid_json(tmp_path):
    doc, errors = _run(tmp_path, "e.ipynb",
                       "not json at all")
    assert doc is None
    assert errors[0].code == "ipynb_invalid_json"


# ---------- ErrorRecord 结构 ----------

def test_error_details_has_path(tmp_path):
    _, errors = _run(tmp_path, "f.ipynb", json.dumps(
        {"cells": "nope", "metadata": {},
         "nbformat": 4}))
    assert list(errors[0].details.keys()) == \
        ["path"]


def test_error_details_path_is_source(tmp_path):
    src = tmp_path / "g.ipynb"
    src.write_text(json.dumps(
        {"cells": "nope", "metadata": {},
         "nbformat": 4}), encoding="utf-8")
    _, errors = process_single(
        src, None, parser_name="ipynb",
        max_chars=200)
    assert errors[0].details["path"] == \
        str(src)


def test_error_to_dict_shape(tmp_path):
    _, errors = _run(tmp_path, "h.ipynb", json.dumps(
        {"cells": "nope", "metadata": {},
         "nbformat": 4}))
    d = errors[0].to_dict()
    assert set(d.keys()) == {
        "code", "message", "details"}
    assert d["code"] == "ipynb_bad_structure"
    assert d["message"] == \
        ".ipynb 的 cells 字段不是数组"


def test_single_error_only(tmp_path):
    _, errors = _run(tmp_path, "i.ipynb",
                     "[1, 2, 3]")
    assert len(errors) == 1


# ---------- 空文件 × 三 parser ----------

def test_empty_html_no_elements(tmp_path):
    (tmp_path / "e.html").write_text(
        "", encoding="utf-8")
    doc, errors = process_single(
        tmp_path / "e.html", None,
        parser_name="html", max_chars=200)
    assert doc is None
    assert errors[0].code == \
        "no_extracted_elements"


def test_empty_md_no_elements(tmp_path):
    (tmp_path / "e.md").write_text(
        "", encoding="utf-8")
    doc, errors = process_single(
        tmp_path / "e.md", None,
        parser_name="markdown", max_chars=200)
    assert doc is None
    assert errors[0].code == \
        "no_extracted_elements"


def test_empty_txt_no_elements(tmp_path):
    (tmp_path / "e.txt").write_text(
        "", encoding="utf-8")
    doc, errors = process_single(
        tmp_path / "e.txt", None,
        parser_name="text", max_chars=200)
    assert doc is None
    assert errors[0].code == \
        "no_extracted_elements"


def test_empty_md_details_source_type(tmp_path):
    (tmp_path / "e.md").write_text(
        "", encoding="utf-8")
    _, errors = process_single(
        tmp_path / "e.md", None,
        parser_name="markdown", max_chars=200)
    assert errors[0].details[
        "source_type"] == "markdown"


def test_empty_html_details_source_type(tmp_path):
    (tmp_path / "e.html").write_text(
        "", encoding="utf-8")
    _, errors = process_single(
        tmp_path / "e.html", None,
        parser_name="html", max_chars=200)
    assert errors[0].details[
        "source_type"] == "html"


# ---------- 失败不落盘 ----------

def test_ipynb_error_no_output(tmp_path):
    out = tmp_path / "o.json"
    src = tmp_path / "j.ipynb"
    src.write_text("not json", encoding="utf-8")
    process_single(src, out,
                   parser_name="ipynb",
                   max_chars=200)
    assert not out.exists()
