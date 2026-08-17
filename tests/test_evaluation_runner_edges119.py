"""evaluation/runner.py 第四百一十五轮 edges 测试（Round 971）。

补强 edges118 未触及的角度（第三百四十七批，probe 实证）。

新角度：
- per_doc 保持 manifest documents 顺序（[zeta, alpha]
  不重排）
- 失败文档指标键恰 20 个 = 基础 14 + figure 3 +
  boundary 3；尾 6 键序 [figure_caption P/R/F1,
  chunk_boundary P/R/F1]
- figure 与 boundary 对 document=None 的分歧：
  figure 恒 parser_does_not_emit_relations（忽略
  document）；boundary 是 pipeline_failed（尊重
  document None）
- 汇总 rate {success_count 0, total 2, rate 0.0}
- _process_one 错误路径五元组：err = errors[0].
  to_dict() 全量透传、parser_version None、image_dir
  None（document None 时）
- forbidden tokens 第四百四十一批（open 2）
"""

from __future__ import annotations

import inspect
import json
import types
from pathlib import Path
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.runner import _process_one, run_evaluation


class _ErrRec:
    code = "E_PARSE"

    def to_dict(self):
        return {"code": "E_PARSE", "message": "boom"}


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    (tmp_path / "samples" / "b.pdf").write_bytes(b"x")


def _two_doc_manifest(tmp_path):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "zeta", "path": "samples/a.pdf",
             "source_type": "pdf"},
            {"doc_id": "alpha", "path": "samples/b.pdf",
             "source_type": "pdf"}]}), encoding="utf-8")
    from evaluation.manifest import load_manifest
    return load_manifest(f, tmp_path)


# ---------- 顺序保持 ----------

def test_per_doc_preserves_manifest_order_batch169(tmp_path):
    _setup(tmp_path)
    m = _two_doc_manifest(tmp_path)
    with patch.object(runner_mod, "process_single",
                      return_value=(None, [_ErrRec()])):
        rep = run_evaluation(m, tmp_path / "o.json")
    assert [r["doc_id"] for r in rep["per_doc"]] == [
        "zeta", "alpha"]


# ---------- 失败文档 20 键 ----------

def test_failed_doc_twenty_metric_keys_batch169(tmp_path):
    _setup(tmp_path)
    m = _two_doc_manifest(tmp_path)
    with patch.object(runner_mod, "process_single",
                      return_value=(None, [_ErrRec()])):
        rep = run_evaluation(m, tmp_path / "o.json")
    metrics = rep["per_doc"][0]["metrics"]
    assert len(metrics) == 20
    assert list(metrics)[-6:] == [
        "figure_caption_precision", "figure_caption_recall",
        "figure_caption_f1", "chunk_boundary_precision",
        "chunk_boundary_recall", "chunk_boundary_f1"]
    assert metrics["figure_caption_precision"] == {
        "value": None,
        "reason": "parser_does_not_emit_relations"}
    assert metrics["chunk_boundary_precision"] == {
        "value": None, "reason": "pipeline_failed"}
    assert metrics["pipeline_success"] == {"value": False,
                                           "reason": None}
    assert rep["summary"]["success_rates"][
        "pipeline_success"] == {"success_count": 0,
                                "total": 2, "rate": 0.0}


# ---------- _process_one 错误路径 ----------

def test_process_one_error_tuple_batch169(tmp_path):
    _setup(tmp_path)
    doc = types.SimpleNamespace(
        doc_id="d1",
        resolved_path=tmp_path / "samples" / "a.pdf")
    with patch.object(runner_mod, "process_single",
                      return_value=(None, [_ErrRec()])):
        out, err, elapsed, pv, idir = _process_one(
            doc, tmp_path, "fallback", 800)
    assert out is None
    assert err == {"code": "E_PARSE", "message": "boom"}
    assert isinstance(elapsed, float) and elapsed >= 0.0
    assert pv is None
    assert idir is None


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch169():
    src = _src()
    assert "return None, errors[0].to_dict(), elapsed, None, image_dir" in src
    assert 'metrics.update(fig_caps)' in src
    assert "metrics.update(chunk_b)" in src
    assert "document.parser_version, image_dir" in src


# ---------- forbidden tokens 第四百四十一批 ----------

def test_source_no_eval_batch169():
    assert "eval(" not in _src()


def test_source_no_exec_batch169():
    assert "exec(" not in _src()


def test_source_no_compile_batch169():
    assert "compile(" not in _src()


def test_source_no_globals_batch169():
    assert "globals(" not in _src()


def test_source_no_locals_batch169():
    assert "locals(" not in _src()


def test_source_no_os_system_batch169():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch169():
    assert "subprocess" not in _src()


def test_source_no_popen_batch169():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch169():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch169():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch169():
    assert "socket" not in _src()


def test_source_no_requests_batch169():
    assert "requests" not in _src()


def test_source_no_urllib_batch169():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch169():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch169():
    assert "yield" not in _src()


def test_source_no_async_await_batch169():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch169():
    assert _src().count("open(") == 2
