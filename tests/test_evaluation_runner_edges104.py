"""evaluation/runner.py 第三百一十轮 edges 测试（Round 866）。

补强 edges103 未触及的角度（第二百四十一批）。

新角度：
- _load_annotation 直调：JSON 数组文件 → 返回 []（falsy 非 None）
- 两文档共用同一源文件 → process_single 恰被调 2 次
- wall_time parse/chunk None + reason "not_instrumented"
  + total 非负
- compute_automatic_metrics 收到失败文档的完整 kwargs
  （document None / error dict / expectations 透传 /
  image_base_dir None）
- build_provenance 哨兵透传进 report["provenance"]；
  真实 devset file_count 进 report
- forbidden tokens 第三百三十六批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

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


def _mk(tmp_path, docs, efs=()):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs, "expected_failures": list(efs)}),
        encoding="utf-8")
    return load_manifest(f, root)


# ---------- _load_annotation 直调 ----------

def test_load_annotation_array_file_returns_list_batch64(tmp_path):
    arr = tmp_path / "arr.json"
    arr.write_text("[1, 2]", encoding="utf-8")
    out = runner_mod._load_annotation(arr)
    assert out == [1, 2]
    assert out is not None


def test_load_annotation_dict_passthrough_batch64(tmp_path):
    d = tmp_path / "d.json"
    d.write_text('{"k": 1}', encoding="utf-8")
    assert runner_mod._load_annotation(d) == {"k": 1}


# ---------- 同一源文件两文档 ----------

def test_two_docs_same_file_two_calls_batch64(tmp_path):
    m = _mk(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf"},
        {"doc_id": "d2", "path": "samples/a.pdf",
         "source_type": "pdf"}])
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), []),
                      ) as ps, \
         patch.object(runner_mod, "build_provenance",
                      return_value={"prov": 1}):
        report = run_evaluation(m, tmp_path / "r.json")
    assert ps.call_count == 2
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"
    assert isinstance(wt["total"], float)
    assert wt["total"] >= 0
    assert report["provenance"] == {"prov": 1}
    assert report["devset"]["file_count"] == 2


# ---------- compute_automatic_metrics 失败文档 kwargs ----------

def test_cam_kwargs_on_failed_doc_batch64(tmp_path):
    m = _mk(tmp_path, [
        {"doc_id": "d1", "path": "samples/a.pdf",
         "source_type": "pdf",
         "expectations": {"element_count_by_type":
                          {"paragraph": 2}}}])
    captured = {}

    def fake_cam(**kwargs):
        captured.update(kwargs)
        return {}

    err_dict = {"code": "E_X", "message": "m"}

    def fake_ps(*a, **k):
        return None, [_Err("E_X")]

    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps), \
         patch.object(runner_mod,
                      "compute_automatic_metrics",
                      side_effect=fake_cam), \
         patch.object(runner_mod, "figure_caption_prf",
                      return_value={}), \
         patch.object(runner_mod, "chunk_boundary_prf",
                      return_value={}), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        report = run_evaluation(m, tmp_path / "r.json")

    assert captured["document"] is None
    assert captured["error"] == err_dict
    assert captured["source_type"] == "pdf"
    assert captured["expectations"] == {
        "element_count_by_type": {"paragraph": 2}}
    assert captured["image_base_dir"] is None
    assert report["per_doc"][0]["metrics"] == {}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch64():
    src = _src()
    assert "annotation = _load_annotation(doc.annotation_resolved)" in src
    assert 'out_stub = output_root / "_per_doc" / f"{doc.doc_id}.json"' in src
    assert "if parser_version and not parser_version_for_prov:" in src


# ---------- forbidden tokens 第三百三十六批 ----------

def test_source_no_eval_batch64():
    assert "eval(" not in _src()


def test_source_no_exec_batch64():
    assert "exec(" not in _src()


def test_source_no_compile_batch64():
    assert "compile(" not in _src()


def test_source_no_globals_batch64():
    assert "globals(" not in _src()


def test_source_no_locals_batch64():
    assert "locals(" not in _src()


def test_source_no_os_system_batch64():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch64():
    assert "subprocess" not in _src()


def test_source_no_popen_batch64():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch64():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch64():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch64():
    assert "socket" not in _src()


def test_source_no_requests_batch64():
    assert "requests" not in _src()


def test_source_no_urllib_batch64():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch64():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch64():
    assert "yield" not in _src()


def test_source_no_async_await_batch64():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch64():
    assert _src().count("open(") == 2
