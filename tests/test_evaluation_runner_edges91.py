"""evaluation/runner.py 第二百一十九轮 edges 测试（Round 775）。

补强 edges88-90 未触及的角度（第一百三十九批）。

新角度：
- _process_one 错误记录透传：errors[0].to_dict() 原样成为 error dict，
  parser_version None、image_dir None（document None 不推导）
- parser_version 空串跳过：doc1 pv=""（falsy）不占位，doc2 pv="1.2"
  → provenance 记 1.2（first-truthy-wins 的空串补角）
- ef-only manifest（documents 空）：EF 循环的 mkdir 仍创建 _per_doc
  目录（与 R768 双空 manifest 不创建对照）
- ef 解析无错误 → actual_error_code None → matches False
- ef 多条错误只取第一条的 code（errors[0].code，第二条忽略）
- 公共 wall_time_seconds 五键完整形态：total float +
  parse/chunk None + parse_reason/chunk_reason "not_instrumented"
- annotation 文件顶层是列表 → chunk_boundary_prf 内 annotation.get
  AttributeError 未守卫传播（json.load 合法但形状错，现状记录）
- forbidden tokens 第二百四十五批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, ExpectedFailure, Manifest
from evaluation.runner import _process_one, run_evaluation


class _FakeDoc:
    parser_version = "1.2"
    source_hash = "cafe"

    def to_dict(self):
        return {"elements": [], "chunks": []}


class _DocEmptyPv(_FakeDoc):
    parser_version = ""


class _ErrRec:
    code = "parse_failed"

    def to_dict(self):
        return {"code": "parse_failed", "message": "m"}


class _DE:
    doc_id = "d1"
    resolved_path = Path("samples") / "a.pdf"


def _env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    return tmp, root


def _de(root, did):
    return DocumentEntry(did, "s/a.pdf", root / "s/a.pdf", "pdf", None,
                         (), None, None, None, None)


def _prov(**k):
    return {"git_commit": "c", "git_dirty": False}


# ---------- _process_one 错误透传 ----------

def test_process_one_error_record_passthrough_batch54():
    tmp = Path(tempfile.mkdtemp())
    with patch.object(runner_mod, "process_single",
                      return_value=(None, [_ErrRec()])):
        doc, err, elapsed, pv, image_dir = _process_one(
            _DE(), tmp, "fallback", 800)
    assert doc is None
    assert err == {"code": "parse_failed", "message": "m"}
    assert pv is None
    assert image_dir is None


# ---------- parser_version 空串 ----------

def test_empty_parser_version_skipped_batch54():
    tmp, root = _env()
    counter = []
    pv_seen = []

    def fake_ps(*a, **k):
        counter.append(1)
        return ((_DocEmptyPv(), []) if len(counter) == 1
                else (_FakeDoc(), []))

    def bp(**k):
        pv_seen.append(k.get("parser_version"))
        return _prov()

    man = Manifest("1.0", "incomplete", (_de(root, "d1"),
                                         _de(root, "d2")), (), root)
    with patch.object(runner_mod, "process_single", fake_ps), \
            patch.object(runner_mod, "build_provenance", bp):
        run_evaluation(man, tmp / "r.json")
    assert pv_seen == ["1.2"]


# ---------- ef-only manifest ----------

def test_ef_only_creates_per_doc_dir_batch54():
    tmp, root = _env()
    ef = ExpectedFailure("f1", "s/x.pdf", root / "s/x.pdf", "boom", "pdf")
    man = Manifest("1.0", "incomplete", (), (ef,), root)
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "build_provenance", _prov):
        rep = run_evaluation(man, tmp / "r.json")
    assert (tmp / "_per_doc").is_dir()
    assert rep["expected_failures"] == [
        {"doc_id": "f1", "expected_error_code": "boom",
         "actual_error_code": None, "matches": False}]


# ---------- ef 多错误取首 ----------

def test_ef_multiple_errors_first_code_batch54():
    tmp, root = _env()
    ef = ExpectedFailure("f1", "s/x.pdf", root / "s/x.pdf", "boom", "pdf")
    man = Manifest("1.0", "incomplete", (), (ef,), root)

    class E1:
        code = "first"

    class E2:
        code = "second"

    with patch.object(runner_mod, "process_single",
                      return_value=(None, [E1(), E2()])), \
            patch.object(runner_mod, "build_provenance", _prov):
        rep = run_evaluation(man, tmp / "r.json")
    assert rep["expected_failures"][0]["actual_error_code"] == "first"
    assert rep["expected_failures"][0]["matches"] is False


# ---------- wall_time 完整形态 ----------

def test_wall_time_five_key_shape_batch54():
    tmp, root = _env()
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "build_provenance", _prov):
        rep = run_evaluation(Manifest("1.0", "incomplete",
                                      (_de(root, "d1"),), (), root),
                             tmp / "r.json")
    wt = rep["per_doc"][0]["wall_time_seconds"]
    assert isinstance(wt["total"], float) and wt["total"] >= 0
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


# ---------- annotation 顶层列表 ----------

def test_annotation_list_crashes_batch54():
    tmp, root = _env()
    ann = root / "ann.json"
    ann.write_text("[1]", encoding="utf-8")
    de = DocumentEntry("d3", "s/a.pdf", root / "s/a.pdf", "pdf", None, (),
                       None, "ann.json", ann, None)
    man = Manifest("1.0", "incomplete", (de,), (), root)
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "build_provenance", _prov), \
            pytest.raises(AttributeError, match="list"):
        run_evaluation(man, tmp / "r.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_ef_and_pv_lines_batch54():
    src = _src()
    assert "if parser_version and not parser_version_for_prov:" in src
    assert "actual_code = errors[0].code if errors else None" in src
    assert "return document.to_dict(), None, elapsed" in src


# ---------- forbidden tokens 第二百四十五批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch54():
    assert _src().count("open(") == 2
