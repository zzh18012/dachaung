"""evaluation/runner.py 第二百八十二轮 edges 测试（Round 838）。

补强 edges99 未触及的角度（第二百一十二批）。

新角度：
- _process_one 直测失败路径：(None, [err]) → image_dir 恒 None
  且错误取 err.to_dict()；(None, []) → code "unknown"、
  parser_version None、elapsed 为 float
- per_doc metrics 含 figure_caption 三连 null
  （parser_does_not_emit_relations，runner 级装配验证）
- 合法标注但 anchors 空列表 → chunk_boundary_* 全
  no_ground_truth_anchors（经 runner 透传）
- image_dir 目录存在时才传 image_base_dir：
  现造 x.png → image_resource_exists_ratio 1.0
- build_provenance 收到 manifest.project_root / parser_name /
  max_chars / 首个 parser_version（kwargs 捕获）
- forbidden tokens 第三百零八批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import evaluation.runner as runner_mod
import evaluation.schema_validation as sv
from evaluation.runner import _process_one, run_evaluation


class _FakeDoc:
    def __init__(self, d, pv="9.9"):
        self._d = d
        self.parser_version = pv
        self.source_hash = "abc123"

    def to_dict(self):
        return self._d


class _Err:
    def __init__(self, code):
        self.code = code

    def to_dict(self):
        return {"code": self.code, "message": "m"}


# ---------- _process_one 失败路径 ----------

def test_process_one_error_image_dir_none_batch55(tmp_path):
    doc = SimpleNamespace(doc_id="d1",
                          resolved_path=tmp_path / "a.pdf")
    with patch.object(runner_mod, "process_single",
                      lambda *a, **k: (None, [_Err("X")])):
        document, error, elapsed, pv, image_dir = _process_one(
            doc, tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "X", "message": "m"}
    assert pv is None
    assert image_dir is None
    assert isinstance(elapsed, float)


def test_process_one_unknown_code_batch55(tmp_path):
    doc = SimpleNamespace(doc_id="d1",
                          resolved_path=tmp_path / "a.pdf")
    with patch.object(runner_mod, "process_single",
                      lambda *a, **k: (None, [])):
        document, error, elapsed, pv, image_dir = _process_one(
            doc, tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "unknown", "message": None} or \
        error["code"] == "unknown"
    assert pv is None
    assert image_dir is None


# ---------- runner 级装配 ----------

_IMG_DOC = {
    "elements": [
        {"element_id": "i1", "type": "image", "content": None,
         "resource_path": "x.png",
         "source_locator": {"page": 1}}],
    "chunks": [],
}


def _manifest(tmp_path, docs, ef=()):
    root = tmp_path / "proj"
    root.mkdir(exist_ok=True)
    (root / "samples").mkdir(exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    return SimpleNamespace(
        documents=docs, expected_failures=list(ef),
        project_root=root, devset_status="incomplete",
        file_count=len(docs), content_group_count=len(docs),
        pdf_count=len(docs), docx_count=0,
        categories_covered=[])


def _entry(root, ann_path=None):
    return SimpleNamespace(
        doc_id="d1", resolved_path=root / "samples" / "a.pdf",
        source_type="pdf", expectations=None,
        annotation_resolved=ann_path)


prov_cap: dict = {}


def _prov(**k):
    prov_cap.clear()
    prov_cap.update(k)
    return {"git_commit": None, "git_dirty": False}


def test_figure_caption_trio_in_report_batch55(tmp_path):
    m = _manifest(tmp_path, [_entry(tmp_path / "proj")])
    with patch.object(runner_mod, "process_single",
                      lambda *a, **k: (_FakeDoc(_IMG_DOC), [])), \
         patch.object(sv, "document_passes_schema",
                      lambda d: True), \
         patch.object(runner_mod, "build_provenance", _prov):
        rep = run_evaluation(m, tmp_path / "out.json")
    mt = rep["per_doc"][0]["metrics"]
    for k in ("figure_caption_precision",
              "figure_caption_recall", "figure_caption_f1"):
        assert mt[k] == {
            "value": None,
            "reason": "parser_does_not_emit_relations"}


def test_annotation_empty_anchors_reason_batch55(tmp_path):
    ann = tmp_path / "ann.json"
    ann.write_text(json.dumps({"chunk_boundary_anchors": []}),
                   encoding="utf-8")
    m = _manifest(tmp_path, [_entry(tmp_path / "proj", ann)])
    doc = {"elements": [
        {"element_id": "e1", "type": "paragraph",
         "content": "A"}],
        "chunks": [{"text": "A",
                    "source_element_ids": ["e1"]},
                   {"text": "B",
                    "source_element_ids": ["e1"]}]}
    with patch.object(runner_mod, "process_single",
                      lambda *a, **k: (_FakeDoc(doc), [])), \
         patch.object(sv, "document_passes_schema",
                      lambda d: True), \
         patch.object(runner_mod, "build_provenance", _prov):
        rep = run_evaluation(m, tmp_path / "out.json")
    mt = rep["per_doc"][0]["metrics"]
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall", "chunk_boundary_f1"):
        assert mt[k]["reason"] == "no_ground_truth_anchors"


def test_image_dir_gating_ratio_batch55(tmp_path):
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    (img_dir / "x.png").write_bytes(b"data")
    m = _manifest(tmp_path, [_entry(tmp_path / "proj")])
    with patch.object(runner_mod, "process_single",
                      lambda *a, **k: (_FakeDoc(_IMG_DOC), [])), \
         patch.object(sv, "document_passes_schema",
                      lambda d: True), \
         patch.object(runner_mod, "image_output_dir_for",
                      lambda stub, sha: img_dir), \
         patch.object(runner_mod, "build_provenance", _prov):
        rep = run_evaluation(m, tmp_path / "out.json")
    assert rep["per_doc"][0]["metrics"][
        "image_resource_exists_ratio"] == {
        "value": 1.0, "reason": None}


def test_provenance_kwargs_batch55(tmp_path):
    m = _manifest(tmp_path, [_entry(tmp_path / "proj")])
    with patch.object(runner_mod, "process_single",
                      lambda *a, **k: (_FakeDoc(_IMG_DOC), [])), \
         patch.object(sv, "document_passes_schema",
                      lambda d: True), \
         patch.object(runner_mod, "build_provenance", _prov):
        run_evaluation(m, tmp_path / "out.json",
                       parser_name="kreuzberg", max_chars=555)
    assert prov_cap["project_root"] == tmp_path / "proj"
    assert prov_cap["parser_name"] == "kreuzberg"
    assert prov_cap["max_chars"] == 555
    assert prov_cap["parser_version"] == "9.9"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "image_base_dir=image_dir if (image_dir is not None and image_dir.is_dir()) else None" in src
    assert "provenance = build_provenance(" in src
    assert "summary = aggregate_summary(per_doc_results)" in src


# ---------- forbidden tokens 第三百零八批 ----------

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
