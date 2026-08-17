"""evaluation/schema.py 第五百一十五轮 edges 测试（Round 1071）。

补强 edges119-122 未触及的角度（第四百四十七批，probe 实证）。

新角度（同一报告里的严格性倒挂：ef 闭仓 vs metrics 暗仓）：
- evaluation-report.schema.json 的 **per_doc.metrics 是
  素 object**（def 层字面 {"type": "object"}）——value
  塞字符串/塞对象、reason 塞 int、删 reason、加全然
  陌生的指标键，**全部放行**——schema 对指标内部完全
  失明；但 metrics 本身 required（pop 掉即拒）
- 同一报告的 **expected_failures 条目是闭仓**：
  additionalProperties: false（多一个键即拒）、matches
  强类型 bool（"yes" → 'is not of type boolean'）、
  actual_error_code required——ef 四键全钉死
- 一份报告两套纪律：结构键守门、度量值放任——
  def 层 + 真实 run 双重锁死
- forbidden tokens 第五百四十二批（open 2）
"""

from __future__ import annotations

import copy
import inspect
import json

from docx import Document

import evaluation.schema as schema_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from evaluation.schema import (
    EvalSchemaError, load_schema, validate)


def _run(tmp_path):
    (tmp_path / "pyproject.toml").write_text("",
                                             encoding="utf-8")
    (tmp_path / "samples").mkdir()
    d = Document()
    d.add_paragraph("AAA first paragraph body.")
    d.save(str(tmp_path / "samples" / "a.docx"))
    (tmp_path / "samples" / "bad.docx").write_bytes(
        b"nope")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1",
                       "path": "samples/a.docx",
                       "source_type": "docx"}],
        "expected_failures": [{
            "doc_id": "f1", "path": "samples/bad.docx",
            "source_type": "docx",
            "expected_error_code":
                "docx_open_failed"}]}),
        encoding="utf-8")
    return run_evaluation(load_manifest(mf, tmp_path),
                          tmp_path / "o.json",
                          max_chars=200)


def _pass(rep, label, fn):
    r = copy.deepcopy(rep)
    fn(r)
    validate(r, "evaluation-report.schema.json")


def _reject(rep, fn, path, fragment):
    r = copy.deepcopy(rep)
    fn(r)
    try:
        validate(r, "evaluation-report.schema.json")
        raised = False
    except EvalSchemaError as e:
        raised = True
        assert e.errors[0]["path"] == path
        assert fragment in e.errors[0]["message"]
    assert raised


# ---------- metrics 暗仓：五路全放行 ----------

def test_metrics_interior_blind_batch270(tmp_path):
    rep = _run(tmp_path)
    m = rep["per_doc"][0]["metrics"]
    _pass(rep, "value str", lambda r: r["per_doc"][0]
          ["metrics"]["pipeline_success"]
          .__setitem__("value", "bogus"))
    _pass(rep, "value obj", lambda r: r["per_doc"][0]
          ["metrics"]["pipeline_success"]
          .__setitem__("value", {"x": 1}))
    _pass(rep, "reason int", lambda r: r["per_doc"][0]
          ["metrics"]["pipeline_success"]
          .__setitem__("reason", 42))
    _pass(rep, "unknown key", lambda r: r["per_doc"][0]
          ["metrics"].__setitem__(
              "totally_new_metric",
              {"value": 1, "reason": None}))
    _pass(rep, "reason gone", lambda r: r["per_doc"][0]
          ["metrics"]["pipeline_success"].pop("reason"))


# ---------- 但 metrics 本身 required ----------

def test_metrics_required_batch270(tmp_path):
    rep = _run(tmp_path)
    _reject(rep,
            lambda r: r["per_doc"][0].pop("metrics"),
            ["per_doc", 0],
            "'metrics' is a required property")


# ---------- def 层：素 object 字面 ----------

def test_per_doc_def_shape_batch270():
    s = load_schema("evaluation-report.schema.json")
    pd = s["$defs"]["per_doc"]
    assert pd["required"] == ["doc_id", "source_type",
                              "metrics",
                              "wall_time_seconds"]
    assert pd["properties"]["metrics"] == {
        "type": "object"}


# ---------- ef 闭仓：matches 强类型 ----------

def test_ef_matches_typed_batch270(tmp_path):
    rep = _run(tmp_path)
    _reject(rep,
            lambda r: r["expected_failures"][0]
            .__setitem__("matches", "yes"),
            ["expected_failures", 0, "matches"],
            "is not of type 'boolean'")


# ---------- ef 闭仓：多键即拒 ----------

def test_ef_extra_key_rejected_batch270(tmp_path):
    rep = _run(tmp_path)
    _reject(rep,
            lambda r: r["expected_failures"][0]
            .__setitem__("note", "x"),
            ["expected_failures", 0],
            "Additional properties are not allowed")


# ---------- ef 闭仓：actual required ----------

def test_ef_actual_required_batch270(tmp_path):
    rep = _run(tmp_path)
    _reject(rep,
            lambda r: r["expected_failures"][0]
            .pop("actual_error_code"),
            ["expected_failures", 0],
            "'actual_error_code' is a required property")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch270():
    src = _src()
    assert "self.errors = errors or []" in src
    assert "SCHEMAS_DIR" in src


# ---------- forbidden tokens 第五百四十二批 ----------

def test_source_no_eval_batch270():
    assert "eval(" not in _src()


def test_source_no_exec_batch270():
    assert "exec(" not in _src()


def test_source_no_compile_batch270():
    assert "compile(" not in _src()


def test_source_no_globals_batch270():
    assert "globals(" not in _src()


def test_source_no_locals_batch270():
    assert "locals(" not in _src()


def test_source_no_os_system_batch270():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch270():
    assert "subprocess" not in _src()


def test_source_no_popen_batch270():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch270():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch270():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch270():
    assert "socket" not in _src()


def test_source_no_requests_batch270():
    assert "requests" not in _src()


def test_source_no_urllib_batch270():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch270():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch270():
    assert "yield" not in _src()


def test_source_no_async_await_batch270():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch270():
    assert _src().count("open(") == 2
