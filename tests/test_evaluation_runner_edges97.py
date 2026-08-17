"""evaluation/runner.py 第二百六十一轮 edges 测试（Round 817）。

补强 edges96 未触及的角度（第一百八十五批）。

新角度：
- annotation 路径是目录：is_file() False → None →
  chunk_boundary_f1 no_annotation（与坏 JSON 同归宿）
- expected_failures matches 三态：actual==expected → True；
  错码 W vs Y → False 且 actual_error_code 记 W；无错误
  （成功）→ actual_error_code None + matches False
- output_path 裸文件名 "r.json"：parent 为 "."，写进当前目录
  （chdir 到 tmp 后文件落在 tmp）
- per_doc 顺序保持清单序（d2, d1 原样输出）
- wall_time_seconds chunk_reason 同为 not_instrumented
- forbidden tokens 第二百八十七批
"""

from __future__ import annotations

import inspect
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, ExpectedFailure, \
    Manifest
from evaluation.runner import run_evaluation


class _FakeDoc:
    parser_version = "1.0"
    source_hash = "h"

    def to_dict(self):
        return {"elements": [
            {"element_id": "e1", "type": "paragraph",
             "content": "A"}],
            "chunks": [
                {"text": "A", "source_element_ids": ["e1"]}]}


class _Err:
    def __init__(self, code):
        self.code = code

    def to_dict(self):
        return {"code": self.code, "message": "m"}


def _env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    return tmp, root


def _de(root, did, ann=None):
    return DocumentEntry(did, "samples/a.pdf",
                         root / "samples/a.pdf", "pdf",
                         None, (), None, ann, None, None)


def _ef(root, did, code):
    return ExpectedFailure(did, "samples/a.pdf",
                           root / "samples/a.pdf", code, "pdf")


def _patched():
    return patch.object(runner_mod, "process_single",
                        return_value=(_FakeDoc(), [])), \
        patch.object(runner_mod, "build_provenance",
                     lambda **k: {"git_commit": "c",
                                  "git_dirty": False})


# ---------- annotation 是目录 ----------

def test_annotation_directory_treated_missing_batch55():
    tmp, root = _env()
    d = tmp / "ann_dir"
    d.mkdir()
    with _patched()[0], _patched()[1]:
        rep = run_evaluation(
            Manifest("1.0", "incomplete", (_de(root, "d1", d),),
                     (), root), tmp / "r.json")
    assert rep["per_doc"][0]["metrics"]["chunk_boundary_f1"] == {
        "value": None, "reason": "no_annotation"}


# ---------- ef matches 三态 ----------

def test_ef_matches_three_states_batch55():
    tmp, root = _env()
    ef_rets = iter([(None, [_Err("X")]), (None, [_Err("W")]),
                    (_FakeDoc(), [])])
    doc_rets = iter([(_FakeDoc(), [])])

    def fake_ps(path, out, **kw):
        if Path(out).name.startswith("f"):
            return next(ef_rets)
        return next(doc_rets)

    with patch.object(runner_mod, "process_single", fake_ps), \
            patch.object(runner_mod, "build_provenance",
                         lambda **k: {"git_commit": "c",
                                      "git_dirty": False}):
        rep = run_evaluation(
            Manifest("1.0", "incomplete", (_de(root, "d1"),),
                     (_ef(root, "f1", "X"), _ef(root, "f2", "Y"),
                      _ef(root, "f3", "Z")), root),
            tmp / "r.json")
    assert rep["expected_failures"] == [
        {"doc_id": "f1", "expected_error_code": "X",
         "actual_error_code": "X", "matches": True},
        {"doc_id": "f2", "expected_error_code": "Y",
         "actual_error_code": "W", "matches": False},
        {"doc_id": "f3", "expected_error_code": "Z",
         "actual_error_code": None, "matches": False}]


# ---------- 裸输出文件名 ----------

def test_bare_output_filename_writes_cwd_batch55(tmp_path,
                                                 monkeypatch):
    tmp, root = _env()
    monkeypatch.chdir(tmp_path)
    with _patched()[0], _patched()[1]:
        run_evaluation(
            Manifest("1.0", "incomplete", (_de(root, "d1"),),
                     (), root), "r.json")
    assert (tmp_path / "r.json").is_file()


# ---------- 顺序保持 ----------

def test_per_doc_preserves_manifest_order_batch55():
    tmp, root = _env()
    with _patched()[0], _patched()[1]:
        rep = run_evaluation(
            Manifest("1.0", "incomplete", (_de(root, "d2"),
                                           _de(root, "d1")),
                     (), root), tmp / "r.json")
    assert [r["doc_id"] for r in rep["per_doc"]] == ["d2", "d1"]


# ---------- chunk_reason ----------

def test_wall_time_chunk_reason_batch55():
    tmp, root = _env()
    with _patched()[0], _patched()[1]:
        rep = run_evaluation(
            Manifest("1.0", "incomplete", (_de(root, "d1"),),
                     (), root), tmp / "r.json")
    wt = rep["per_doc"][0]["wall_time_seconds"]
    assert wt["chunk_reason"] == "not_instrumented"
    assert wt["parse_reason"] == "not_instrumented"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert 'if path is None or not path.is_file():' in src
    assert 'actual_code = errors[0].code if errors else None' in src
    assert '"matches": actual_code == ef.expected_error_code,' in src


# ---------- forbidden tokens 第二百八十七批 ----------

def test_source_no_eval_batch55():
    assert "eval(" not in _src()


def test_source_no_exec_batch55():
    assert "exec(" not in _src()


def test_source_no_compile_batch55():
    assert "compile(" not in _src()


def test_source_no_globals_batch55():
    assert "globals(" not in _src()


def test_source_no_locals_batch55():
    assert "locals(" not in _src()


def test_source_no_os_system_batch55():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch55():
    assert "subprocess" not in _src()


def test_source_no_popen_batch55():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch55():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch55():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch55():
    assert "socket" not in _src()


def test_source_no_requests_batch55():
    assert "requests" not in _src()


def test_source_no_urllib_batch55():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch55():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch55():
    assert "yield" not in _src()


def test_source_no_async_await_batch55():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch55():
    assert _src().count("open(") == 2
