"""evaluation/runner.py 第二百四十轮 edges 测试（Round 796）。

补强 edges93 未触及的角度（第一百六十批）。

新角度：
- 嵌套输出目录：output x/y/r.json → 两级父目录被递归创建
  （mkdir parents=True）
- ef 循环异常传播：process_single 抛 RuntimeError →
  run_evaluation 原样上抛（ef 循环无 try/except 包裹）
- _load_annotation 恰每文档调用一次（2 docs → 2 次，与
  annotation 是否为 None 无关）
- chunk_boundary_prf 收到 tolerance_chars=77 逐文档透传；
  figure_caption_prf 收到 (document_dict, annotation) 位置参数
  （document 恒非 None dict）
- forbidden tokens 第二百六十六批
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, ExpectedFailure, Manifest
from evaluation.runner import run_evaluation


class _FakeDoc:
    parser_version = "1.0"
    source_hash = "h"

    def to_dict(self):
        return {"elements": [], "chunks": []}


def _env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    return tmp, root


def _de(root, did):
    return DocumentEntry(did, "s/a.pdf", root / "s/a.pdf", "pdf",
                         None, (), None, None, None, None)


def _prov(**k):
    return {"git_commit": "c", "git_dirty": False}


# ---------- 嵌套输出目录 ----------

def test_nested_output_dirs_created_batch54():
    tmp, root = _env()
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "build_provenance", _prov):
        run_evaluation(Manifest("1.0", "incomplete",
                                (_de(root, "d1"),), (), root),
                       tmp / "x" / "y" / "r.json")
    assert (tmp / "x" / "y" / "r.json").is_file()


# ---------- ef 循环异常传播 ----------

def test_ef_loop_exception_propagates_batch54():
    tmp, root = _env()
    with patch.object(runner_mod, "process_single",
                      side_effect=RuntimeError("boom")), \
            patch.object(runner_mod, "build_provenance", _prov):
        with pytest.raises(RuntimeError, match="boom"):
            run_evaluation(
                Manifest("1.0", "incomplete", (),
                         (ExpectedFailure("f1", "s/a.pdf",
                                          root / "s/a.pdf", "e",
                                          "pdf"),), root),
                tmp / "r.json")


# ---------- 调用计数与约定 ----------

def test_annotation_loaded_once_per_doc_batch54():
    tmp, root = _env()
    ann_calls, cb_calls, fig_calls = [], [], []

    def fake_cb(doc, ann, tolerance_chars=30):
        cb_calls.append(tolerance_chars)
        return {"chunk_boundary_precision": {"value": None,
                                             "reason": "x"},
                "chunk_boundary_recall": {"value": None,
                                          "reason": "x"},
                "chunk_boundary_f1": {"value": None, "reason": "x"},
                "_tolerance_chars": {"value": tolerance_chars,
                                     "reason": None}}

    def fake_fig(doc, ann):
        fig_calls.append((doc, ann))
        return {"figure_caption_precision": {"value": None,
                                             "reason": "x"},
                "figure_caption_recall": {"value": None,
                                          "reason": "x"},
                "figure_caption_f1": {"value": None, "reason": "x"}}

    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "build_provenance", _prov), \
            patch.object(runner_mod, "_load_annotation",
                         lambda p: ann_calls.append(p) or None), \
            patch.object(runner_mod, "chunk_boundary_prf", fake_cb), \
            patch.object(runner_mod, "figure_caption_prf", fake_fig):
        run_evaluation(Manifest("1.0", "incomplete",
                                (_de(root, "d1"), _de(root, "d2")),
                                (), root),
                       tmp / "r.json", tolerance_chars=77)
    assert len(ann_calls) == 2
    assert cb_calls == [77, 77]
    assert all(d == {"elements": [], "chunks": []}
               for d, _ in fig_calls)
    assert all(a is None for _, a in fig_calls)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_call_lines_batch54():
    src = _src()
    assert "output_root.mkdir(parents=True, exist_ok=True)" in src
    assert "annotation = _load_annotation(doc.annotation_resolved)" in src
    assert "tolerance_chars=tolerance_chars" in src


# ---------- forbidden tokens 第二百六十六批 ----------

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
