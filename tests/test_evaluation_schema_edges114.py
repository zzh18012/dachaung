"""evaluation/schema.py 第四百五十三轮 edges 测试（Round 1009）。

补强 edges113 未触及的角度（第三百八十五批，probe 实证）。

新角度（document.schema.json allOf 分支行为面）：
- 6 分支 if 条件 const 恰为 [pdf, docx, markdown, html,
  text, ipynb]，全部 if+then 成对
- markdown locator {"line": 5} 合法；附加键（col）也合法
  （locator 开放）
- html locator 缺 line → required 拒
- text locator line=0 → "0 is less than the minimum of 1"
  （line 有 minimum 1）
- pdf 分支给 docx 键 paragraph_index → 'page' is required
  （pdf locator 必含 page）
- **docx locator 同时带 page + paragraph_index 合法**——
  schema 不禁 page，而 metrics._docx_locator_ratio 把
  含 page 的判无效（跨模块张力）
- relation 用 from/to 键名 → 'from_id' is required
- warning 缺 reason 拒；error {code,message} 合法
- forbidden tokens 第四百七十九批（open 2）
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import load_schema, validate, EvalSchemaError


def _mdoc(source_type, loc):
    return {"schema_version": "0.1.0", "document_id": "d",
            "source_path": "a.md", "source_type": source_type,
            "source_hash": "a" * 64, "parser_name": "p",
            "parser_version": "1",
            "elements": [
                {"element_id": "e1", "type": "paragraph",
                 "content": "x", "parent_id": None,
                 "confidence": 0.9, "metadata": {},
                 "source_locator": loc}],
            "chunks": [], "relations": [], "warnings": [],
            "errors": [], "metadata": {}}


def _err(doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(doc, "document.schema.json")
    return ei.value.errors


# ---------- 分支 const 序 ----------

def test_branch_consts_order_batch207():
    ds = load_schema("document.schema.json")
    branches = ds["allOf"]
    consts = [b["if"]["properties"]["source_type"]["const"]
              for b in branches]
    assert consts == ["pdf", "docx", "markdown", "html",
                      "text", "ipynb"]
    assert all("if" in b and "then" in b for b in branches)


# ---------- markdown ----------

def test_markdown_line_valid_extra_ok_batch207():
    validate(_mdoc("markdown", {"line": 5}),
             "document.schema.json")
    validate(_mdoc("markdown", {"line": 5, "col": 1}),
             "document.schema.json")


# ---------- html ----------

def test_html_missing_line_rejected_batch207():
    errs = _err(_mdoc("html", {}))
    assert errs[0]["message"] == \
        "'line' is a required property"


# ---------- text line minimum ----------

def test_text_line_zero_minimum_batch207():
    errs = _err(_mdoc("text", {"line": 0}))
    assert errs[0]["message"] == \
        "0 is less than the minimum of 1"


# ---------- pdf 分支必含 page ----------

def test_pdf_branch_requires_page_batch207():
    errs = _err(_mdoc("pdf", {"paragraph_index": 1}))
    assert errs[0]["message"] == \
        "'page' is a required property"


# ---------- docx locator 允许 page（跨模块张力） ----------

def test_docx_locator_page_allowed_schema_batch207():
    validate(_mdoc("docx",
                   {"page": 1, "paragraph_index": 0}),
             "document.schema.json")


# ---------- relation 键名 ----------

def test_relation_from_id_required_batch207():
    doc = _mdoc("pdf", {"page": 1, "bbox": [1, 2, 3, 4]})
    doc["relations"] = [{"from_element": "a", "to_element": "b",
                         "type": "caption_of"}]
    errs = _err(doc)
    assert errs[0]["message"] == "'from_id' is a required property"


# ---------- warning/error defs ----------

def test_warning_reason_required_error_ok_batch207():
    doc = _mdoc("pdf", {"page": 1, "bbox": [1, 2, 3, 4]})
    doc["warnings"] = [{"code": "W"}]
    assert _err(doc)[0]["message"] == \
        "'reason' is a required property"

    doc2 = _mdoc("pdf", {"page": 1, "bbox": [1, 2, 3, 4]})
    doc2["errors"] = [{"code": "E", "message": "m"}]
    validate(doc2, "document.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch207():
    src = _src()
    assert "schema = load_schema(schema_name)" in src
    assert "raise EvalSchemaError(" in src
    assert "errors=flat," in src
    assert '"schema_path": list(err.absolute_schema_path),' in src


# ---------- forbidden tokens 第四百七十九批 ----------

def test_source_no_eval_batch207():
    assert "eval(" not in _src()


def test_source_no_exec_batch207():
    assert "exec(" not in _src()


def test_source_no_compile_batch207():
    assert "compile(" not in _src()


def test_source_no_globals_batch207():
    assert "globals(" not in _src()


def test_source_no_locals_batch207():
    assert "locals(" not in _src()


def test_source_no_os_system_batch207():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch207():
    assert "subprocess" not in _src()


def test_source_no_popen_batch207():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch207():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch207():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch207():
    assert "socket" not in _src()


def test_source_no_requests_batch207():
    assert "requests" not in _src()


def test_source_no_urllib_batch207():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch207():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch207():
    assert "yield" not in _src()


def test_source_no_async_await_batch207():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch207():
    assert _src().count("open(") == 2
