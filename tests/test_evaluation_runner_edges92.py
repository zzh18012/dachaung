"""evaluation/runner.py 第二百二十六轮 edges 测试（Round 782）。

补强 edges88-91 未触及的角度（第一百四十二批补）。

新角度：
- image_output_dir_for 恰以 (out_stub, document.source_hash) 调用：
  stub 是 output_root/_per_doc/<doc_id>.json、hash 原样（复用
  pipeline 命名约定，不硬编码目录名）
- per_doc 顺序与 manifest.documents 严格一致（d3,d1,d2 保持乱序）
- 标注端到端：annotation 文件带匹配 anchor → 报告 metrics 里
  chunk_boundary_precision 1.0 非 null（annotation 真实流入
  指标，同时 figure_caption 仍 parser_does_not_emit_relations）
- 输出文件 indent=2 布局（'\n  "report_version"' 在原文中）
- forbidden tokens 第二百五十二批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.manifest import DocumentEntry, Manifest
from evaluation.runner import run_evaluation


class _FakeDoc:
    parser_version = "1.0"
    source_hash = "abcd1234"

    def to_dict(self):
        return {
            "elements": [
                {"element_id": "e1", "type": "paragraph",
                 "content": "AB"},
                {"element_id": "e2", "type": "paragraph",
                 "content": "CD"},
            ],
            "chunks": [
                {"text": "AB", "source_element_ids": ["e1"]},
                {"text": "CD", "source_element_ids": ["e2"]},
            ],
        }


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


# ---------- image_output_dir_for 调用约定 ----------

def test_image_dir_for_call_convention_batch54():
    tmp, root = _env()
    (tmp / "imgs").mkdir()
    calls = []
    with patch.object(runner_mod, "image_output_dir_for",
                      lambda stub, sha:
                      calls.append((stub, sha)) or tmp / "imgs"), \
            patch.object(runner_mod, "process_single",
                         return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "build_provenance", _prov):
        run_evaluation(Manifest("1.0", "incomplete",
                                (_de(root, "d1"),), (), root),
                       tmp / "r.json")
    assert len(calls) == 1
    stub, sha = calls[0]
    assert stub == tmp / "_per_doc" / "d1.json"
    assert sha == "abcd1234"


# ---------- per_doc 顺序 ----------

def test_per_doc_order_matches_manifest_batch54():
    tmp, root = _env()
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "build_provenance", _prov):
        rep = run_evaluation(
            Manifest("1.0", "incomplete",
                     (_de(root, "d3"), _de(root, "d1"),
                      _de(root, "d2")), (), root),
            tmp / "r.json")
    assert [r["doc_id"] for r in rep["per_doc"]] == ["d3", "d1", "d2"]


# ---------- 标注端到端 ----------

def test_annotation_flows_to_boundary_metric_batch54():
    tmp, root = _env()
    ann = root / "ann.json"
    ann.write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "d1",
        "chunk_boundary_anchors": [{"marker": "AB"}]}),
        encoding="utf-8")
    de = DocumentEntry("d1", "s/a.pdf", root / "s/a.pdf", "pdf", None,
                       (), None, "ann.json", ann, None)
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "build_provenance", _prov):
        rep = run_evaluation(Manifest("1.0", "incomplete", (de,),
                                      (), root), tmp / "r.json")
    mets = rep["per_doc"][0]["metrics"]
    assert mets["chunk_boundary_precision"] == {"value": 1.0,
                                                "reason": None}
    assert mets["chunk_boundary_recall"] == {"value": 1.0,
                                             "reason": None}
    assert mets["figure_caption_precision"]["reason"] == \
        "parser_does_not_emit_relations"


# ---------- 输出布局 ----------

def test_output_json_indent_two_batch54():
    tmp, root = _env()
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
            patch.object(runner_mod, "build_provenance", _prov):
        run_evaluation(Manifest("1.0", "incomplete",
                                (_de(root, "d1"),), (), root),
                       tmp / "r.json")
    raw = (tmp / "r.json").read_text(encoding="utf-8")
    assert '\n  "report_version"' in raw


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_convention_lines_batch54():
    src = _src()
    assert "image_output_dir_for(out_stub, document.source_hash)" in src
    assert 'json.dump(report, f, ensure_ascii=False, indent=2)' in src


# ---------- forbidden tokens 第二百五十二批 ----------

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
