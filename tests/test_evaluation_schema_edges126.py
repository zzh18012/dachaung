"""evaluation/schema.py 第五百三十六轮 edges 测试（Round 1092）。

补强 edges123-125 未触及的角度（第四百六十八批，probe 实证）。

新角度（chunk 不变量 schema 执法 + 报告 def 梯度收口）：
- **chunk source_element_ids 空列表即拒**："[] should
  be non-empty"——CLAUDE.md"每 chunk 必须非空
  source_element_ids"不变量由 schema minItems 执法
  （真实文档变异路径首锁；edges112 的 non-empty 是
  locator 的 minProperties）
- **confidence 下界**：-0.1 → "-0.1 is less than the
  minimum of 0"——edges112 只锁了上界 1.5，下界补齐
- **metadata 字段可空**：真实文档 title 置 None 照过
  ——metadata 是 nullable 容器
- **evaluation-report 三 def 梯度**：devset 闭仓 +
  required 6；provenance 闭仓 + required 9；**summary
  既无 required 也 additionalProperties True——全开
  暗仓**——报告 schema 的第四种纪律形态（ef 闭、
  metrics 素 object、summary 全开）
- forbidden tokens 第五百六十三批（open 2）
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


def _reject(tmp_path, mut, frag):
    r = copy.deepcopy(_real_doc(tmp_path))
    mut(r)
    try:
        validate(r, "document.schema.json")
        raised = False
    except EvalSchemaError as e:
        raised = True
        assert frag in str(e)
    assert raised


# ---------- chunk source_element_ids 非空执法 ----------

def test_chunk_source_ids_nonempty_batch291(tmp_path):
    _reject(
        tmp_path,
        lambda r: r["chunks"][0].__setitem__(
            "source_element_ids", []),
        "[] should be non-empty")


# ---------- confidence 下界 ----------

def test_confidence_minimum_batch291(tmp_path):
    _reject(
        tmp_path,
        lambda r: r["elements"][0].__setitem__(
            "confidence", -0.1),
        "-0.1 is less than the minimum of 0")


# ---------- metadata 可空 ----------

def test_metadata_nullable_batch291(tmp_path):
    r = copy.deepcopy(_real_doc(tmp_path))
    r["metadata"]["title"] = None
    validate(r, "document.schema.json")


# ---------- 报告 def 梯度 ----------

def test_report_defs_gradient_batch291():
    s = load_schema("evaluation-report.schema.json")
    dev = s["$defs"]["devset"]
    assert dev["required"] == [
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered"]
    assert dev["additionalProperties"] is False
    prov = s["$defs"]["provenance"]
    assert prov["required"] == [
        "git_commit", "git_dirty", "evaluator_version",
        "report_version", "parser_name", "parser_version",
        "dependencies", "max_chars", "run_timestamp_iso"]
    assert prov["additionalProperties"] is False
    summ = s["$defs"]["summary"]
    assert "required" not in summ
    assert summ["additionalProperties"] is True


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch291():
    src = _src()
    assert "def validate(" in src
    assert "def load_schema(" in src


# ---------- forbidden tokens 第五百六十三批 ----------

def test_source_no_eval_batch291():
    assert "eval(" not in _src()


def test_source_no_exec_batch291():
    assert "exec(" not in _src()


def test_source_no_compile_batch291():
    assert "compile(" not in _src()


def test_source_no_globals_batch291():
    assert "globals(" not in _src()


def test_source_no_locals_batch291():
    assert "locals(" not in _src()


def test_source_no_os_system_batch291():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch291():
    assert "subprocess" not in _src()


def test_source_no_popen_batch291():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch291():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch291():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch291():
    assert "socket" not in _src()


def test_source_no_requests_batch291():
    assert "requests" not in _src()


def test_source_no_urllib_batch291():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch291():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch291():
    assert "yield" not in _src()


def test_source_no_async_await_batch291():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch291():
    assert _src().count("open(") == 2
