"""evaluation/runner.py 第二百三十三轮 edges 测试（Round 789）。

补强 edges91-92 未触及的角度（第一百五十三批）。

新角度：
- _process_one errors 优先：document 与 errors 同时非空 → 返回
  (None, errors[0].to_dict(), parser_version None)（errors 分支
  在 document None 检查之前）
- _process_one stub 清理：fake process_single 落盘 stub → 调用后
  文件被 unlink、_per_doc 目录保留
- image_base_dir 双向守卫：image_output_dir_for 返回存在目录 →
  compute_automatic_metrics 收到该 Path；不存在 → 收到 None
  （is_dir() 守卫）
- ef 循环调用约定：stub == output_root/_per_doc/f1.json、
  write_json=False、max_chars=555 透传（与文档循环同一 stub 命名）
- build_provenance 收到 manifest.project_root + max_chars +
  首个非空 parser_version（"1.2"）
- _missing_markers 流转：annotation marker "ZZ" 未命中 → 内部
  记录 ["ZZ"]；_tolerance_chars 30
- 公共 per_doc 恰 4 键（_annotation_present/_tolerance_chars/
  _missing_markers 内部键被剥离）
- forbidden tokens 第二百五十九批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, ExpectedFailure, Manifest
from evaluation.runner import _process_one, run_evaluation


class _FakeDoc:
    parser_version = "1.2"
    source_hash = "hh"

    def to_dict(self):
        return {"elements": [
            {"element_id": "e1", "type": "paragraph", "content": "A"},
            {"element_id": "e2", "type": "paragraph", "content": "B"}],
            "chunks": [
                {"text": "A", "source_element_ids": ["e1"]},
                {"text": "B", "source_element_ids": ["e2"]}]}


class _FakeErr:
    code = "x"

    def to_dict(self):
        return {"code": "x", "message": "m"}


def _env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    return tmp, root


def _de(root, did, ann=None):
    return DocumentEntry(did, "s/a.pdf", root / "s/a.pdf", "pdf",
                         None, (), None,
                         "ann.json" if ann else None, ann, None)


# ---------- _process_one errors 优先 ----------

def test_process_one_errors_priority_batch54():
    tmp, root = _env()
    with patch.object(runner_mod, "image_output_dir_for",
                      lambda s, h: tmp / "imgs"), \
            patch.object(runner_mod, "process_single",
                         return_value=(_FakeDoc(), [_FakeErr()])):
        doc, err, _el, pv, img = _process_one(_de(root, "d1"), tmp,
                                              "fallback", 800)
    assert doc is None
    assert err == {"code": "x", "message": "m"}
    assert pv is None
    assert img == tmp / "imgs"


# ---------- stub 清理 ----------

def test_process_one_stub_cleaned_batch54():
    tmp, root = _env()

    def fake_ps(path, out, **kw):
        out.write_text("{}", encoding="utf-8")
        return _FakeDoc(), []

    with patch.object(runner_mod, "image_output_dir_for",
                      lambda s, h: tmp / "imgs"), \
            patch.object(runner_mod, "process_single", fake_ps):
        _process_one(_de(root, "d1"), tmp, "fallback", 800)
    assert not (tmp / "_per_doc" / "d1.json").is_file()
    assert (tmp / "_per_doc").is_dir()


# ---------- 运行期捕获 ----------

def _run_with_caps(tmp, root, make_img_dir, ann):
    if make_img_dir:
        (tmp / "imgs").mkdir()
    got_img, ef_calls, prov_calls, agg = [], [], [], {}

    def cap_agg(results):
        agg["r"] = results
        return {"counts": {}, "success_rates": {},
                "ratio_macro_averages": {}, "silent_drop_total": None}

    def fake_ps(path, out, **kw):
        ef_calls.append((path, Path(out), kw))
        return _FakeDoc(), []

    with patch.object(runner_mod, "image_output_dir_for",
                      lambda s, h: tmp / "imgs"), \
            patch.object(runner_mod, "process_single", fake_ps), \
            patch.object(runner_mod, "build_provenance",
                         lambda **k: prov_calls.append(k) or
                         {"git_commit": None, "git_dirty": True}), \
            patch.object(runner_mod, "compute_automatic_metrics",
                         lambda **k: got_img.append(
                             k.get("image_base_dir", "MISSING")) or
                         {"pipeline_success": {"value": True,
                                               "reason": None}}), \
            patch.object(runner_mod, "aggregate_summary", cap_agg):
        m = Manifest("1.0", "incomplete", (_de(root, "d1", ann),),
                     (ExpectedFailure("f1", "s/a.pdf",
                                      root / "s/a.pdf",
                                      "open_error", "pdf"),), root)
        rep = run_evaluation(m, tmp / "r.json", max_chars=555)
    return got_img, ef_calls, prov_calls, agg, rep


def test_image_base_dir_guard_both_ways_batch54():
    tmp, root = _env()
    got, _, _, _, _ = _run_with_caps(tmp, root, True, None)
    assert got == [tmp / "imgs"]

    tmp2, root2 = _env()
    got2, _, _, _, _ = _run_with_caps(tmp2, root2, False, None)
    assert got2 == [None]


def test_ef_call_convention_batch54():
    tmp, root = _env()
    _, ef_calls, _, _, _ = _run_with_caps(tmp, root, True, None)
    ef_path, ef_out, ef_kw = ef_calls[-1]
    assert ef_out == tmp / "_per_doc" / "f1.json"
    assert ef_kw["write_json"] is False
    assert ef_kw["max_chars"] == 555


def test_provenance_receives_root_and_version_batch54():
    tmp, root = _env()
    _, _, prov_calls, _, _ = _run_with_caps(tmp, root, True, None)
    kw = prov_calls[0]
    assert kw["project_root"] == root
    assert kw["max_chars"] == 555
    assert kw["parser_version"] == "1.2"


def test_missing_markers_flows_to_internal_record_batch54():
    tmp, root = _env()
    ann = root / "ann.json"
    ann.write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "d1",
        "chunk_boundary_anchors": [{"marker": "ZZ"}]}), encoding="utf-8")
    _, _, _, agg, _ = _run_with_caps(tmp, root, True, ann)
    r0 = agg["r"][0]
    assert r0["_annotation_present"] is True
    assert r0["_missing_markers"] == ["ZZ"]
    assert r0["_tolerance_chars"] == 30


def test_public_per_doc_strips_internal_keys_batch54():
    tmp, root = _env()
    _, _, _, _, rep = _run_with_caps(tmp, root, True, None)
    assert list(rep["per_doc"][0].keys()) == [
        "doc_id", "source_type", "metrics", "wall_time_seconds"]
    assert rep["expected_failures"][0] == {
        "doc_id": "f1", "expected_error_code": "open_error",
        "actual_error_code": None, "matches": False}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_guard_lines_batch54():
    src = _src()
    assert "image_dir.is_dir()) else None" in src
    assert "if errors:" in src
    assert "out_stub.unlink()" in src
    assert 'output_root / "_per_doc" / f"{ef.doc_id}.json"' in src


# ---------- forbidden tokens 第二百五十九批 ----------

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
