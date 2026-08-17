"""evaluation/schema.py 第三百五十五轮 edges 测试（Round 911）。

补强 edges98 未触及的角度（第二百八十七批，probe 实证）。

新角度：
- document 顶层 required 恰 13 项有序（schema_version 首位）；
  顶层 additionalProperties 未设（开放，与 chunk/element 封闭
  形成对照）
- pdf_locator：page integer minimum 1；bbox array items
  number minItems=maxItems 4；def 开放
- docx_locator props 恰 7 个结构键
- manifest 顶层封闭（addProps False）；annotation_version
  const "1.0"
- provenance 属性类型：dependencies 自由 string|null 映射、
  max_chars integer min 1、run_timestamp_iso minLength 1、
  git_commit 双类型、git_dirty boolean、parser_name minLength 1
- summary def 四属性类型化 + 开放 + 无 required
- forbidden tokens 第三百八十一批
"""

from __future__ import annotations

import inspect

import evaluation.schema as schema_mod
from evaluation.schema import load_schema


# ---------- document 顶层 ----------

def test_document_top_required_ordered_batch109():
    d = load_schema("document.schema.json")
    assert d["required"] == [
        "schema_version", "document_id", "source_path",
        "source_type", "source_hash", "parser_name",
        "parser_version", "elements", "chunks", "relations",
        "warnings", "errors", "metadata",
    ]
    assert "additionalProperties" not in d  # 顶层开放


# ---------- pdf_locator ----------

def test_pdf_locator_shape_batch109():
    pl = load_schema("document.schema.json")["$defs"]["pdf_locator"]
    assert pl["required"] == ["page"]
    page = pl["properties"]["page"]
    assert page == {"type": "integer", "minimum": 1}
    bbox = pl["properties"]["bbox"]
    assert bbox["type"] == "array"
    assert bbox["items"] == {"type": "number"}
    assert bbox["minItems"] == 4
    assert bbox["maxItems"] == 4
    assert pl["additionalProperties"] is True


# ---------- docx_locator 7 键 ----------

def test_docx_locator_seven_keys_batch109():
    dl = load_schema("document.schema.json")["$defs"][
        "docx_locator"]
    assert sorted(dl["properties"]) == [
        "col_index", "paragraph_index", "relationship_id",
        "row_index", "run_index", "section", "table_index",
    ]


# ---------- manifest / annotation 顶层 ----------

def test_manifest_top_closed_batch109():
    m = load_schema("manifest.schema.json")
    assert m["additionalProperties"] is False
    assert m["required"] == ["manifest_version", "devset_status",
                             "documents"]


def test_annotation_version_const_batch109():
    a = load_schema("annotation.schema.json")
    assert a["properties"]["annotation_version"] == {
        "type": "string", "const": "1.0"}
    assert a["additionalProperties"] is False


# ---------- provenance 属性类型 ----------

def test_provenance_prop_types_batch109():
    pv = load_schema("evaluation-report.schema.json")["$defs"][
        "provenance"]["properties"]
    assert pv["dependencies"] == {
        "type": "object",
        "additionalProperties": {"type": ["string", "null"]}}
    assert pv["max_chars"] == {"type": "integer", "minimum": 1}
    assert pv["run_timestamp_iso"] == {"type": "string",
                                       "minLength": 1}
    assert pv["git_commit"] == {"type": ["string", "null"]}
    assert pv["git_dirty"] == {"type": "boolean"}
    assert pv["parser_name"] == {"type": "string", "minLength": 1}


# ---------- summary def ----------

def test_summary_def_typed_props_batch109():
    s = load_schema("evaluation-report.schema.json")["$defs"][
        "summary"]
    assert "required" not in s
    assert s["additionalProperties"] is True
    props = s["properties"]
    assert sorted(props) == ["counts", "ratio_macro_averages",
                             "silent_drop_total", "success_rates"]
    assert props["counts"] == {"type": "object"}
    assert props["silent_drop_total"] == {"type": ["integer",
                                                   "null"]}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch109():
    src = _src()
    assert "validator = Draft202012Validator(schema)" in src
    assert "if not errors:" in src
    assert 'SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"' in src


# ---------- forbidden tokens 第三百八十一批 ----------

def test_source_no_eval_batch109():
    assert "eval(" not in _src()


def test_source_no_exec_batch109():
    assert "exec(" not in _src()


def test_source_no_compile_batch109():
    assert "compile(" not in _src()


def test_source_no_globals_batch109():
    assert "globals(" not in _src()


def test_source_no_locals_batch109():
    assert "locals(" not in _src()


def test_source_no_os_system_batch109():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch109():
    assert "subprocess" not in _src()


def test_source_no_popen_batch109():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch109():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch109():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch109():
    assert "socket" not in _src()


def test_source_no_requests_batch109():
    assert "requests" not in _src()


def test_source_no_urllib_batch109():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch109():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch109():
    assert "yield" not in _src()


def test_source_no_async_await_batch109():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch109():
    assert _src().count("open(") == 2
