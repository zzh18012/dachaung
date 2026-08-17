"""evaluation/runner.py 第三百二十四轮 edges 测试（Round 880）。

补强 edges105 未触及的角度（第二百五十五批）。

新角度：
- _load_annotation 收目录 → is_file False → None
- _process_one 收到 (document, errors) 双非空：errors 优先，
  document 被丢弃（返回 None + errors[0]）
- 标注文件为垃圾 JSON → _load_annotation None →
  chunk_boundary no_annotation
- process_single 抛异常：runner 不设防，直接向上传播
  （现状锁定）
- 落盘 JSON 与返回 report 深相等
- forbidden tokens 第三百五十批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import pytest

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


class _FakeDoc:
    def __init__(self, d):
        self._d = d
        self.parser_version = "7.7"
        self.source_hash = "deadbeef"

    def to_dict(self):
        return self._d


class _Err:
    def __init__(self, code):
        self.code = code

    def to_dict(self):
        return {"code": self.code, "message": "m"}


_DOC_DICT = {
    "elements": [{"element_id": "e1", "type": "paragraph",
                  "content": "AB"}],
    "chunks": [{"text": "AB", "source_element_ids": ["e1"]}],
}


def _mk(tmp_path, docs, efs=(), ann=None):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    if ann is not None:
        (root / "ann.json").write_text(ann, encoding="utf-8")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs, "expected_failures": list(efs)}),
        encoding="utf-8")
    return load_manifest(f, root)


# ---------- 目录标注 ----------

def test_load_annotation_directory_none_batch78(tmp_path):
    d = tmp_path / "adir"
    d.mkdir()
    assert runner_mod._load_annotation(d) is None


# ---------- errors 优先于 document ----------

def test_process_one_errors_win_over_document_batch78(tmp_path):
    m = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf"}])
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT),
                                    [_Err("E_X")])):
        doc, err, secs, pv, image_dir = \
            runner_mod._process_one(m.documents[0],
                                    tmp_path, "fallback", 800)
    assert doc is None
    assert err == {"code": "E_X", "message": "m"}
    assert pv is None


# ---------- 垃圾标注 ----------

def test_garbage_annotation_treated_missing_batch78(tmp_path):
    m = _mk(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf", "annotation_file": "ann.json"}],
        ann="{broken")
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        report = run_evaluation(m, tmp_path / "r.json")
    cb = report["per_doc"][0]["metrics"][
        "chunk_boundary_precision"]
    assert cb == {"value": None, "reason": "no_annotation"}


# ---------- process_single 异常传播 ----------

def test_process_single_exception_propagates_batch78(tmp_path):
    m = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf"}])
    with patch.object(runner_mod, "process_single",
                      side_effect=RuntimeError("boom")), \
         pytest.raises(RuntimeError) as ei:
        run_evaluation(m, tmp_path / "r.json")
    assert "boom" in str(ei.value)


# ---------- 落盘与返回深相等 ----------

def test_disk_json_equals_returned_report_batch78(tmp_path):
    m = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf"}])
    out = tmp_path / "r.json"
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={"pv": 1}):
        report = run_evaluation(m, out)
    assert json.loads(out.read_text(encoding="utf-8")) == \
        report


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch78():
    src = _src()
    assert "if path is None or not path.is_file():" in src
    assert "if errors:" in src
    assert "return None, errors[0].to_dict(), elapsed, None, image_dir" in src


# ---------- forbidden tokens 第三百五十批 ----------

def test_source_no_eval_batch78():
    assert "eval(" not in _src()


def test_source_no_exec_batch78():
    assert "exec(" not in _src()


def test_source_no_compile_batch78():
    assert "compile(" not in _src()


def test_source_no_globals_batch78():
    assert "globals(" not in _src()


def test_source_no_locals_batch78():
    assert "locals(" not in _src()


def test_source_no_os_system_batch78():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch78():
    assert "subprocess" not in _src()


def test_source_no_popen_batch78():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch78():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch78():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch78():
    assert "socket" not in _src()


def test_source_no_requests_batch78():
    assert "requests" not in _src()


def test_source_no_urllib_batch78():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch78():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch78():
    assert "yield" not in _src()


def test_source_no_async_await_batch78():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch78():
    assert _src().count("open(") == 2
