"""evaluation/runner.py 第五百一十二轮 edges 测试（Round 1068）。

补强 edges129-132 未触及的角度（第四百四十四批，probe 实证）。

新角度（ef 编码 chunker_failed：matches 随 max_chars 翻转）：
- ef 条目此前只锁过 parse 族（docx_open_failed）；
  本批让 ef **期望 chunker_failed**——同一文件同一
  清单，mc 31 → actual chunker_failed、matches True；
  mc 200 → actual None、matches False——matches 纯随
  max_chars 旋钮翻转（地板 31/32 在 ef 通道同样生效）
- **一文件双账本**：mc 31 下同一 good.docx 同时以
  document 与 ef 两身份入场——document 账本 pipeline
  False、error_code {chunker_failed}、ect null
  pipeline_failed、rate 0.0；ef 账本 matches True——
  一次 run、一份文件、两套口径互不干扰
- forbidden tokens 第五百三十九批（open 2）
"""

from __future__ import annotations

import inspect
import json

from docx import Document

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("",
                                             encoding="utf-8")
    (tmp_path / "samples").mkdir()
    d = Document()
    d.add_paragraph("AAA first paragraph body.")
    d.save(str(tmp_path / "samples" / "good.docx"))


def _manifest(tmp_path, with_doc):
    docs = ([{"doc_id": "d1", "path": "samples/good.docx",
              "source_type": "docx"}] if with_doc else [])
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": docs,
        "expected_failures": [{
            "doc_id": "ef1", "path": "samples/good.docx",
            "source_type": "docx",
            "expected_error_code":
                "chunker_failed"}]}), encoding="utf-8")
    return mf


# ---------- mc 31：地板击穿 → ef 命中 ----------

def test_ef_chunker_failed_match_mc31_batch267(tmp_path):
    _setup(tmp_path)
    rep = run_evaluation(
        load_manifest(_manifest(tmp_path, False), tmp_path),
        tmp_path / "o.json", max_chars=31)
    assert rep["expected_failures"] == [{
        "doc_id": "ef1",
        "expected_error_code": "chunker_failed",
        "actual_error_code": "chunker_failed",
        "matches": True}]
    assert rep["per_doc"] == []


# ---------- mc 200：同文件照跑 → ef 落空 ----------

def test_ef_flip_mc200_mismatch_batch267(tmp_path):
    _setup(tmp_path)
    rep = run_evaluation(
        load_manifest(_manifest(tmp_path, False), tmp_path),
        tmp_path / "o.json", max_chars=200)
    assert rep["expected_failures"] == [{
        "doc_id": "ef1",
        "expected_error_code": "chunker_failed",
        "actual_error_code": None,
        "matches": False}]


# ---------- 一文件双账本 ----------

def test_same_file_both_roles_batch267(tmp_path):
    _setup(tmp_path)
    rep = run_evaluation(
        load_manifest(_manifest(tmp_path, True), tmp_path),
        tmp_path / "o.json", max_chars=31)
    m = rep["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": False,
                                     "reason": None}
    assert m["error_code"] == {"value": "chunker_failed",
                               "reason": None}
    assert rep["expected_failures"][0]["matches"] is True


# ---------- document 账本 null 化 ----------

def test_doc_role_nulls_mc31_batch267(tmp_path):
    _setup(tmp_path)
    rep = run_evaluation(
        load_manifest(_manifest(tmp_path, True), tmp_path),
        tmp_path / "o.json", max_chars=31)
    m = rep["per_doc"][0]["metrics"]
    assert m["element_count_total"] == {
        "value": None, "reason": "pipeline_failed"}
    assert rep["summary"]["success_rates"] == {
        "pipeline_success": {"success_count": 0,
                             "total": 1, "rate": 0.0}}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch267():
    src = _src()
    assert ("actual_code = errors[0].code "
            "if errors else None") in src
    assert "for ef in manifest.expected_failures:" in src


# ---------- forbidden tokens 第五百三十九批 ----------

def test_source_no_eval_batch267():
    assert "eval(" not in _src()


def test_source_no_exec_batch267():
    assert "exec(" not in _src()


def test_source_no_compile_batch267():
    assert "compile(" not in _src()


def test_source_no_globals_batch267():
    assert "globals(" not in _src()


def test_source_no_locals_batch267():
    assert "locals(" not in _src()


def test_source_no_os_system_batch267():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch267():
    assert "subprocess" not in _src()


def test_source_no_popen_batch267():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch267():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch267():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch267():
    assert "socket" not in _src()


def test_source_no_requests_batch267():
    assert "requests" not in _src()


def test_source_no_urllib_batch267():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch267():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch267():
    assert "yield" not in _src()


def test_source_no_async_await_batch267():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch267():
    assert _src().count("open(") == 2
