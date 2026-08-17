"""evaluation/schema.py 第四百三十九轮 edges 测试（Round 995）。

补强 edges111 未触及的角度（第三百七十一批，probe 实证）。

新角度（document.schema.json 行为面）：
- allOf 恰 6 条 if/then 分支（6 种 source_type 全覆盖）
- pdf_locator 的 bbox 竟是可选（required 只有 page）→
  只给 page 照常 VALID
- ipynb_locator 缺 cell_type → "'cell_type' is a required
  property"；cell_type "python" 不在 enum [markdown, code,
  raw]；"raw" 合法
- docx_locator 空 {} → "{} should be non-empty"
  （minProperties 1）；只给 paragraph_index 合法
- bbox 字符串项 → "'1' is not of type 'number'"；
  3 项 → "[1, 2, 3] is too short"（minItems 4）
- confidence 1.5 → "1.5 is greater than the maximum of 1"
- source_hash 大写十六进制 → pattern ^[0-9a-f]{64}$ 拒绝
- schema_version "0.2.0" → "'0.1.0' was expected"（const）
- element content 与 resource_path 双空串 → anyOf 拒绝
- forbidden tokens 第四百六十五批（open 2）
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import load_schema, validate, EvalSchemaError


def _mdoc(source_type="pdf", elem_extra=None, loc=None):
    el = {"element_id": "e1", "type": "paragraph", "content": "x",
          "parent_id": None, "confidence": 0.9, "metadata": {},
          "source_locator": {"page": 1, "bbox": [1, 2, 3, 4]}}
    if source_type == "docx":
        el["source_locator"] = {"paragraph_index": 0}
    if source_type == "ipynb":
        el["source_locator"] = {"cell_index": 0, "cell_type": "code"}
    if elem_extra:
        el.update(elem_extra)
    if loc is not None:
        el["source_locator"] = loc
    return {"schema_version": "0.1.0", "document_id": "d",
            "source_path": "a.pdf", "source_type": source_type,
            "source_hash": "a" * 64, "parser_name": "p",
            "parser_version": "1", "elements": [el], "chunks": [],
            "relations": [], "warnings": [], "errors": [],
            "metadata": {}}


def _err(doc):
    with pytest.raises(EvalSchemaError) as ei:
        validate(doc, "document.schema.json")
    return ei.value.errors


# ---------- 结构面 ----------

def test_allof_branch_count_6_batch193():
    ds = load_schema("document.schema.json")
    assert len(ds["allOf"]) == 6


# ---------- bbox 可选（quirk） ----------

def test_pdf_locator_bbox_optional_batch193():
    validate(_mdoc("pdf", loc={"page": 1}), "document.schema.json")


# ---------- ipynb_locator ----------

def test_ipynb_missing_cell_type_batch193():
    errs = _err(_mdoc("ipynb", loc={"cell_index": 0}))
    assert errs[0]["message"] == "'cell_type' is a required property"


def test_ipynb_cell_type_enum_rejects_python_batch193():
    errs = _err(_mdoc("ipynb", loc={"cell_index": 0,
                                    "cell_type": "python"}))
    assert errs[0]["message"] == \
        "'python' is not one of ['markdown', 'code', 'raw']"


def test_ipynb_cell_type_raw_valid_batch193():
    validate(_mdoc("ipynb", loc={"cell_index": 0,
                                 "cell_type": "raw"}),
             "document.schema.json")


# ---------- docx_locator ----------

def test_docx_locator_empty_rejected_batch193():
    errs = _err(_mdoc("docx", loc={}))
    assert errs[0]["message"] == "{} should be non-empty"


def test_docx_locator_paragraph_index_valid_batch193():
    validate(_mdoc("docx", loc={"paragraph_index": 5}),
             "document.schema.json")


# ---------- bbox 项类型与长度 ----------

def test_bbox_string_item_rejected_batch193():
    errs = _err(_mdoc("pdf", loc={"page": 1,
                                  "bbox": ["1", 2, 3, 4]}))
    assert errs[0]["message"] == "'1' is not of type 'number'"


def test_bbox_three_items_rejected_batch193():
    errs = _err(_mdoc("pdf", loc={"page": 1, "bbox": [1, 2, 3]}))
    assert errs[0]["message"] == "[1, 2, 3] is too short"


# ---------- confidence 上界 ----------

def test_confidence_1_5_rejected_batch193():
    errs = _err(_mdoc("pdf",
                      elem_extra={"confidence": 1.5}))
    assert errs[0]["message"] == \
        "1.5 is greater than the maximum of 1"


# ---------- source_hash pattern ----------

def test_source_hash_uppercase_rejected_batch193():
    errs = _err({**_mdoc("pdf"), "source_hash": "A" * 64})
    assert errs[0]["message"].startswith(
        "'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAA' does not match")


# ---------- schema_version const ----------

def test_schema_version_0_2_rejected_batch193():
    errs = _err({**_mdoc("pdf"), "schema_version": "0.2.0"})
    assert errs[0]["message"] == "'0.1.0' was expected"


# ---------- anyOf 双空串 ----------

def test_element_both_empty_strings_anyof_batch193():
    errs = _err(_mdoc("pdf", elem_extra={"content": "",
                                         "resource_path": ""}))
    assert len(errs) >= 1


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch193():
    src = _src()
    assert "errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))" in src
    assert "validator = Draft202012Validator(schema)" in src
    assert "head = errors[0]" in src
    assert "flat: list[dict[str, Any]] = []" in src


# ---------- forbidden tokens 第四百六十五批 ----------

def test_source_no_eval_batch193():
    assert "eval(" not in _src()


def test_source_no_exec_batch193():
    assert "exec(" not in _src()


def test_source_no_compile_batch193():
    assert "compile(" not in _src()


def test_source_no_globals_batch193():
    assert "globals(" not in _src()


def test_source_no_locals_batch193():
    assert "locals(" not in _src()


def test_source_no_os_system_batch193():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch193():
    assert "subprocess" not in _src()


def test_source_no_popen_batch193():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch193():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch193():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch193():
    assert "socket" not in _src()


def test_source_no_requests_batch193():
    assert "requests" not in _src()


def test_source_no_urllib_batch193():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch193():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch193():
    assert "yield" not in _src()


def test_source_no_async_await_batch193():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch193():
    assert _src().count("open(") == 2
