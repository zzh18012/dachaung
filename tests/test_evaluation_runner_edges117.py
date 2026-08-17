"""evaluation/runner.py 第四百零一轮 edges 测试（Round 957）。

补强 edges116 未触及的角度（第三百三十三批，probe 实证）。

新角度：
- 内部键不泄漏：_tolerance_chars / _missing_markers 被
  pop 出 metrics；per_doc 无下划线开头键（四键固定）
- 缺失 marker 不进分母：anchors [AB 命中, ZZ 缺失] +
  chunks ["AB","CD"] → P/R/F1 全 1.0（ZZ 只进内部
  _missing_markers）
- 输出根目录派生：output 位于 sub/o.json →
  sub/_per_doc/ 目录被创建且跑完后为空（stub 已 unlink）
- 自定义 tolerance_chars=11 全程透传（计算在
  annotation_metrics，runner 只传参不落地）
- forbidden tokens 第四百二十七批（open 2）
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.runner import run_evaluation


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")


def _fake_document():
    class D:
        source_hash = "a" * 64
        parser_version = "1.0"

        def to_dict(self):
            return {"schema_version": "0.1.0",
                    "chunks": [{"text": "AB"},
                               {"text": "CD"}]}
    return D()


def _run_with_ann(tmp_path, out_rel="o.json", tol=30):
    ann = {"annotation_version": "1.0", "doc_id": "d1",
           "chunk_boundary_anchors": [
               {"marker": "AB", "position": "after"},
               {"marker": "ZZ", "position": "after"}]}
    (tmp_path / "ann.json").write_text(json.dumps(ann),
                                       encoding="utf-8")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1",
                       "path": "samples/a.pdf",
                       "source_type": "pdf",
                       "annotation_file": "ann.json"}]}),
        encoding="utf-8")
    from evaluation.manifest import load_manifest
    m = load_manifest(f, tmp_path)
    with patch.object(runner_mod, "process_single",
                      return_value=(_fake_document(), [])):
        return run_evaluation(m, tmp_path / out_rel,
                              tolerance_chars=tol)


# ---------- 内部键不泄漏 ----------

def test_no_internal_key_leak_batch155(tmp_path):
    _setup(tmp_path)
    rep = _run_with_ann(tmp_path)
    pd = rep["per_doc"][0]
    assert list(pd) == ["doc_id", "source_type", "metrics",
                        "wall_time_seconds"]
    assert not any(k.startswith("_")
                   for k in pd["metrics"])
    assert "_tolerance_chars" not in pd["metrics"]
    assert "_missing_markers" not in pd["metrics"]


# ---------- 缺失 marker 不进分母 ----------

def test_missing_marker_not_in_denominator_batch155(tmp_path):
    _setup(tmp_path)
    metrics = _run_with_ann(tmp_path)["per_doc"][0]["metrics"]
    assert metrics["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert metrics["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert metrics["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


# ---------- 输出根派生 ----------

def test_per_doc_dir_under_output_root_batch155(tmp_path):
    _setup(tmp_path)
    rep = _run_with_ann(tmp_path, out_rel="sub/o.json")
    per_doc_dir = tmp_path / "sub" / "_per_doc"
    assert per_doc_dir.is_dir()
    assert list(per_doc_dir.iterdir()) == []
    assert (tmp_path / "sub" / "o.json").is_file()


# ---------- tolerance 透传 ----------

def test_tolerance_passthrough_batch155(tmp_path):
    _setup(tmp_path)
    rep = _run_with_ann(tmp_path, tol=11)
    # 计算结果不受影响（边界精确重合），仅验证不抛错、
    # 输出结构完整
    pd = rep["per_doc"][0]
    assert pd["metrics"]["chunk_boundary_f1"]["value"] == 1.0
    assert pd["wall_time_seconds"]["parse_reason"] == \
        "not_instrumented"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch155():
    src = _src()
    assert 'tolerance_record = chunk_b.pop("_tolerance_chars", None)' in src
    assert 'missing_markers_record = chunk_b.pop("_missing_markers", None)' in src
    assert 'out_stub.parent.mkdir(parents=True, exist_ok=True)' in src
    assert "out_p.parent.mkdir(parents=True, exist_ok=True)" in src


# ---------- forbidden tokens 第四百二十七批 ----------

def test_source_no_eval_batch155():
    assert "eval(" not in _src()


def test_source_no_exec_batch155():
    assert "exec(" not in _src()


def test_source_no_compile_batch155():
    assert "compile(" not in _src()


def test_source_no_globals_batch155():
    assert "globals(" not in _src()


def test_source_no_locals_batch155():
    assert "locals(" not in _src()


def test_source_no_os_system_batch155():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch155():
    assert "subprocess" not in _src()


def test_source_no_popen_batch155():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch155():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch155():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch155():
    assert "socket" not in _src()


def test_source_no_requests_batch155():
    assert "requests" not in _src()


def test_source_no_urllib_batch155():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch155():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch155():
    assert "yield" not in _src()


def test_source_no_async_await_batch155():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch155():
    assert _src().count("open(") == 2
