"""evaluation/runner.py 第四百九十一轮 edges 测试（Round 1047）。

补强 edges129 未触及的角度（第四百二十三批，probe 实证）。

新角度（同一损坏 docx 的双角色镜像）：
- 同一真实损坏 docx（伪字节）按 manifest 角色分流：
  作 document → per_doc 1 条（error_code
  docx_open_failed、pipeline False、
  element_count_total/schema_valid 双 null
  pipeline_failed、rate 0.0）+ ef 空；作
  expected_failure → per_doc 空 + ef matches True
  ——同一文件、同一底层 process_single 结果、
  两条互为镜像的记账通道
- 真实解析失败不写任何东西：_per_doc 目录两种角色
  下都空（无 doc stub、无 images 目录——与 R1034
  成功路径留下 images-<hash16> 正交）
- 失败路径 wall_time 仍五键（total float +
  parse/chunk null not_instrumented）——计时与
  成败正交
- forbidden tokens 第五百一十八批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


def _run(tmp_path, as_doc):
    (tmp_path / "pyproject.toml").write_text("",
                                             encoding="utf-8")
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "bad.docx").write_bytes(
        b"not a docx")
    docs = ([{"doc_id": "d1", "path": "samples/bad.docx",
              "source_type": "docx"}] if as_doc else [])
    efs = ([] if as_doc else
           [{"doc_id": "f1", "path": "samples/bad.docx",
             "expected_error_code": "docx_open_failed"}])
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": docs,
        "expected_failures": efs}), encoding="utf-8")
    rep = run_evaluation(load_manifest(mf, tmp_path),
                         tmp_path / "o.json")
    per = tmp_path / "_per_doc"
    leftovers = (sorted(p.name for p in per.iterdir())
                 if per.is_dir() else None)
    return rep, leftovers


# ---------- 作 document：per_doc 记账 ----------

def test_corrupt_as_doc_metrics_batch245(tmp_path):
    rep, _ = _run(tmp_path, as_doc=True)
    m = rep["per_doc"][0]["metrics"]
    assert m["error_code"] == {"value": "docx_open_failed",
                               "reason": None}
    assert m["pipeline_success"] == {"value": False,
                                     "reason": None}
    assert m["element_count_total"] == {
        "value": None, "reason": "pipeline_failed"}
    assert m["schema_valid"] == {
        "value": None, "reason": "pipeline_failed"}
    assert rep["summary"]["success_rates"][
        "pipeline_success"] == {"success_count": 0,
                                "total": 1, "rate": 0.0}
    assert rep["expected_failures"] == []


def test_corrupt_as_doc_wall_time_batch245(tmp_path):
    rep, _ = _run(tmp_path, as_doc=True)
    wt = rep["per_doc"][0]["wall_time_seconds"]
    assert isinstance(wt["total"], float)
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


# ---------- 作 expected_failure：ef 记账 ----------

def test_corrupt_as_ef_mirror_batch245(tmp_path):
    rep, _ = _run(tmp_path, as_doc=False)
    assert rep["per_doc"] == []
    assert rep["expected_failures"] == [{
        "doc_id": "f1",
        "expected_error_code": "docx_open_failed",
        "actual_error_code": "docx_open_failed",
        "matches": True}]


# ---------- 失败路径不落盘 ----------

def test_per_doc_empty_both_roles_batch245(tmp_path):
    _, as_doc = _run(tmp_path, as_doc=True)
    _, as_ef = _run(tmp_path, as_doc=False)
    assert as_doc == []
    assert as_ef == []


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch245():
    src = _src()
    assert "out_stub.unlink()" in src
    assert "image_output_dir_for(" in src
    assert "per_doc_results" in src


# ---------- forbidden tokens 第五百一十八批 ----------

def test_source_no_eval_batch245():
    assert "eval(" not in _src()


def test_source_no_exec_batch245():
    assert "exec(" not in _src()


def test_source_no_compile_batch245():
    assert "compile(" not in _src()


def test_source_no_globals_batch245():
    assert "globals(" not in _src()


def test_source_no_locals_batch245():
    assert "locals(" not in _src()


def test_source_no_os_system_batch245():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch245():
    assert "subprocess" not in _src()


def test_source_no_popen_batch245():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch245():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch245():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch245():
    assert "socket" not in _src()


def test_source_no_requests_batch245():
    assert "requests" not in _src()


def test_source_no_urllib_batch245():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch245():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch245():
    assert "yield" not in _src()


def test_source_no_async_await_batch245():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch245():
    assert _src().count("open(") == 2
