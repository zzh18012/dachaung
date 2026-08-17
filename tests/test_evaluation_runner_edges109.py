"""evaluation/runner.py 第三百四十五轮 edges 测试（Round 901）。

补强 edges108 未触及的角度（第二百七十七批）。

新角度：
- _process_one 直接三分支：成功（doc_dict + pv + image_dir 由
  image_output_dir_for(out_stub, source_hash) 推导）/ errors 非空
  （doc 丢弃 + pv None + image_dir None）/ doc None 无 errors
  （code "unknown" 完整 message）
- 两文档标注独立性：仅第二份带标注 → _annotation_present
  [False, True]
- run_evaluation 输出到嵌套不存在目录 → parents 自动创建
- forbidden tokens 第三百七十一批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import _process_one, run_evaluation


class _FakeDoc:
    parser_version = "7.7"
    source_hash = "deadbeef"

    def __init__(self, d):
        self._d = d

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


def _doc_entry(tmp_path, doc_id="d1"):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id, "path": "samples/a.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(f, root).documents[0]


# ---------- _process_one 成功 ----------

def test_process_one_success_batch99(tmp_path):
    doc = _doc_entry(tmp_path)
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])):
        out = _process_one(doc, tmp_path, "fallback", 800)
    doc_dict, error, elapsed, pv, image_dir = out
    assert doc_dict == _DOC_DICT
    assert error is None
    assert isinstance(elapsed, float) and elapsed >= 0
    assert pv == "7.7"
    stub = tmp_path / "_per_doc" / "d1.json"
    assert image_dir == runner_mod.image_output_dir_for(
        stub, "deadbeef")
    assert not stub.is_file()  # stub 不残留（fake 未写也检查目录）
    assert (tmp_path / "_per_doc").is_dir()


# ---------- _process_one errors 非空 ----------

def test_process_one_errors_win_batch99(tmp_path):
    doc = _doc_entry(tmp_path)
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT),
                                    [_Err("E_X")])):
        doc_dict, error, elapsed, pv, image_dir = _process_one(
            doc, tmp_path, "fallback", 800)
    assert doc_dict is None
    assert error == {"code": "E_X", "message": "m"}
    assert pv is None
    # doc 对象仍在 → image_dir 照常推导（仅 document None 时为 None）
    stub = tmp_path / "_per_doc" / "d1.json"
    assert image_dir == runner_mod.image_output_dir_for(
        stub, "deadbeef")


# ---------- _process_one doc None 无 errors ----------

def test_process_one_none_no_errors_batch99(tmp_path):
    doc = _doc_entry(tmp_path)
    with patch.object(runner_mod, "process_single",
                      return_value=(None, [])):
        doc_dict, error, elapsed, pv, image_dir = _process_one(
            doc, tmp_path, "fallback", 800)
    assert doc_dict is None
    assert error == {
        "code": "unknown",
        "message": "process_single returned None without errors",
    }
    assert pv is None
    assert image_dir is None


# ---------- 标注独立性 ----------

def test_annotation_per_doc_independent_batch99(tmp_path):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    (root / "ann2.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "d2",
        "chunk_boundary_anchors": []}), encoding="utf-8")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf"},
            {"doc_id": "d2", "path": "samples/a.pdf",
             "source_type": "pdf",
             "annotation_file": "ann2.json"}]}),
        encoding="utf-8")
    m = load_manifest(f, root)
    captured = []
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}), \
         patch.object(runner_mod, "aggregate_summary",
                      side_effect=lambda r: captured.append(
                          [x["_annotation_present"]
                           for x in r]) or {}):
        run_evaluation(m, tmp_path / "r.json")
    assert captured[0] == [False, True]


# ---------- 嵌套输出目录 ----------

def test_output_nested_dir_created_batch99(tmp_path):
    m_doc = _doc_entry(tmp_path)
    f = tmp_path / "m.json"
    root = tmp_path / "proj"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    m = load_manifest(f, root)
    out = tmp_path / "deep" / "nested" / "r.json"
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        run_evaluation(m, out)
    assert out.is_file()


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch99():
    src = _src()
    assert ("image_dir = image_output_dir_for("
            "out_stub, document.source_hash)") in src
    assert ('{"code": "unknown", "message": "process_single '
            'returned None without errors"}') in src
    assert "out_stub.parent.mkdir(parents=True, exist_ok=True)" in src
    assert 'tolerance_record = chunk_b.pop("_tolerance_chars", None)' in src


# ---------- forbidden tokens 第三百七十一批 ----------

def test_source_no_eval_batch99():
    assert "eval(" not in _src()


def test_source_no_exec_batch99():
    assert "exec(" not in _src()


def test_source_no_compile_batch99():
    assert "compile(" not in _src()


def test_source_no_globals_batch99():
    assert "globals(" not in _src()


def test_source_no_locals_batch99():
    assert "locals(" not in _src()


def test_source_no_os_system_batch99():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch99():
    assert "subprocess" not in _src()


def test_source_no_popen_batch99():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch99():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch99():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch99():
    assert "socket" not in _src()


def test_source_no_requests_batch99():
    assert "requests" not in _src()


def test_source_no_urllib_batch99():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch99():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch99():
    assert "yield" not in _src()


def test_source_no_async_await_batch99():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch99():
    assert _src().count("open(") == 2
