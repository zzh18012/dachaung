"""evaluation/metrics.py 第四百三十三轮 edges 测试（Round 989）。

补强 edges118 未触及的角度（第三百六十五批，probe 实证）。

新角度：
- schema 校验抛异常 → schema_valid False +
  reason "schema_check_exception:ValueError"（动态类型名）；
  pipeline_success 不受影响仍 True（文档在、无 error）
- error 传空 dict {}：pipeline_success False（is None 检查）
  但 error_code None（{} falsy 检查）→ 同一对象两处判定
  分歧
- resource_path 绝对路径 + image_base_dir=None → Path(rp)
  直查命中 → 1.0
- document 与 error 双 None 基线：success False +
  error_code None + 其余 null pipeline_failed
- forbidden tokens 第四百五十九批（open 0）
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import evaluation.metrics as metrics_mod
import evaluation.schema_validation as sv
from evaluation.metrics import compute_automatic_metrics


# ---------- schema_check_exception ----------

def test_schema_check_exception_reason_batch187():
    doc = {"elements": [], "chunks": []}
    with patch.object(sv, "document_passes_schema",
                      side_effect=ValueError("boom")):
        out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["schema_valid"] == {
        "value": False,
        "reason": "schema_check_exception:ValueError"}
    assert out["pipeline_success"] == {"value": True,
                                       "reason": None}


# ---------- 空 error dict 分歧 ----------

def test_empty_error_dict_divergence_batch187():
    out = compute_automatic_metrics(None, {}, "pdf", None)
    assert out["pipeline_success"] == {"value": False,
                                       "reason": None}
    assert out["error_code"] == {"value": None, "reason": None}
    assert out["schema_valid"] == {
        "value": None, "reason": "pipeline_failed"}


# ---------- 绝对 resource_path 直查 ----------

def test_absolute_resource_path_direct_batch187(tmp_path):
    f = tmp_path / "x.png"
    f.write_bytes(b"d")
    doc = {"elements": [{"type": "image",
                         "resource_path": str(f)}],
           "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["image_resource_exists_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- 双 None 基线 ----------

def test_both_none_baseline_batch187():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"] == {"value": False,
                                       "reason": None}
    assert out["error_code"] == {"value": None, "reason": None}
    assert out["element_count_total"] == {
        "value": None, "reason": "pipeline_failed"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch187():
    src = _src()
    assert 'f"schema_check_exception:{type(e).__name__}"' in src
    assert "pipeline_success = error is None and document is not None" in src
    assert '{"value": error["code"] if error else None, "reason": None}' in src
    assert "from evaluation.schema_validation import document_passes_schema" in src


# ---------- forbidden tokens 第四百五十九批 ----------

def test_source_no_eval_batch187():
    assert "eval(" not in _src()


def test_source_no_exec_batch187():
    assert "exec(" not in _src()


def test_source_no_compile_batch187():
    assert "compile(" not in _src()


def test_source_no_globals_batch187():
    assert "globals(" not in _src()


def test_source_no_locals_batch187():
    assert "locals(" not in _src()


def test_source_no_os_system_batch187():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch187():
    assert "subprocess" not in _src()


def test_source_no_popen_batch187():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch187():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch187():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch187():
    assert "socket" not in _src()


def test_source_no_requests_batch187():
    assert "requests" not in _src()


def test_source_no_urllib_batch187():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch187():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch187():
    assert "yield" not in _src()


def test_source_no_async_await_batch187():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch187():
    assert "open(" not in _src()
