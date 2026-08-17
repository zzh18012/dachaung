"""evaluation/schema.py 第五百二十九轮 edges 测试（Round 1085）。

补强 edges122-124 未触及的角度（第四百六十一批，probe 实证）。

新角度（document.schema 的严格性梯度：顶层开、def 层闭）：
- **真实文档顶层加 "note" 键照过**——document.schema
  顶层 additionalProperties 未设（开仓）；同一文档
  elements[i] 或 chunks[i] 加 "note" 即拒——element /
  chunk 两个 def 均 additionalProperties: false
- 至此三张 schema 的梯度合拢：manifest 处处闭
  （edges124）、report metrics 暗仓（edges123）、
  document 顶层开而 def 层闭
- 顶层 required 13 键全名册：[schema_version,
  document_id, source_path, source_type, source_hash,
  parser_name, parser_version, elements, chunks,
  relations, warnings, errors, metadata]
- element def required 6 键名册 [element_id, type,
  parent_id, source_locator, confidence, metadata] +
  闭仓
- **load_schema 无缓存**：两次调用不同对象、改动其一
  不泄漏到后续调用
- forbidden tokens 第五百五十六批（open 2）
"""

from __future__ import annotations

import copy
import inspect
import tempfile
import pathlib

from docx import Document

import evaluation.schema as schema_mod
from app.pipeline import process_single
from evaluation.schema import (
    EvalSchemaError, load_schema, validate)


def _real_doc(tmp_path):
    p = tmp_path / "a.docx"
    d = Document()
    d.add_paragraph("AAA first paragraph body.")
    d.save(str(p))
    doc, errors = process_single(
        p, tmp_path / "s.json", parser_name="fallback",
        max_chars=200, write_json=False)
    assert errors == []
    return doc.to_dict()


# ---------- 顶层开仓 ----------

def test_top_level_open_batch284(tmp_path):
    r = copy.deepcopy(_real_doc(tmp_path))
    r["note"] = "extra top-level key"
    validate(r, "document.schema.json")


# ---------- element def 闭仓 ----------

def test_element_def_closed_batch284(tmp_path):
    r = copy.deepcopy(_real_doc(tmp_path))
    r["elements"][0]["note"] = "x"
    try:
        validate(r, "document.schema.json")
        raised = False
    except EvalSchemaError as e:
        raised = True
        assert "Additional properties" in str(e)
    assert raised


# ---------- chunk def 闭仓 ----------

def test_chunk_def_closed_batch284(tmp_path):
    r = copy.deepcopy(_real_doc(tmp_path))
    r["chunks"][0]["note"] = "x"
    try:
        validate(r, "document.schema.json")
        raised = False
    except EvalSchemaError as e:
        raised = True
        assert "Additional properties" in str(e)
    assert raised


# ---------- 顶层 required 13 键名册 ----------

def test_top_required_roster_batch284():
    s = load_schema("document.schema.json")
    assert s["required"] == [
        "schema_version", "document_id", "source_path",
        "source_type", "source_hash", "parser_name",
        "parser_version", "elements", "chunks",
        "relations", "warnings", "errors", "metadata"]


# ---------- element def 名册 ----------

def test_element_def_roster_batch284():
    s = load_schema("document.schema.json")
    d = s["$defs"]["element"]
    assert d["required"] == [
        "element_id", "type", "parent_id",
        "source_locator", "confidence", "metadata"]
    assert d["additionalProperties"] is False


# ---------- load_schema 无缓存 ----------

def test_load_schema_no_caching_batch284():
    s1 = load_schema("document.schema.json")
    s2 = load_schema("document.schema.json")
    assert s1 is not s2
    s1["_probe_mutation"] = True
    s3 = load_schema("document.schema.json")
    assert "_probe_mutation" not in s3


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch284():
    src = _src()
    assert "sorted(" in src
    assert "absolute_path" in src


# ---------- forbidden tokens 第五百五十六批 ----------

def test_source_no_eval_batch284():
    assert "eval(" not in _src()


def test_source_no_exec_batch284():
    assert "exec(" not in _src()


def test_source_no_compile_batch284():
    assert "compile(" not in _src()


def test_source_no_globals_batch284():
    assert "globals(" not in _src()


def test_source_no_locals_batch284():
    assert "locals(" not in _src()


def test_source_no_os_system_batch284():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch284():
    assert "subprocess" not in _src()


def test_source_no_popen_batch284():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch284():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch284():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch284():
    assert "socket" not in _src()


def test_source_no_requests_batch284():
    assert "requests" not in _src()


def test_source_no_urllib_batch284():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch284():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch284():
    assert "yield" not in _src()


def test_source_no_async_await_batch284():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch284():
    assert _src().count("open(") == 2
