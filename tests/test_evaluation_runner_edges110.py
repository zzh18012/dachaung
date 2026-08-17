"""evaluation/runner.py 第三百五十二轮 edges 测试（Round 908）。

补强 edges109 未触及的角度（第二百八十四批，probe 实证）。

新角度：
- _load_annotation 遇非 UTF-8 字节 → UnicodeDecodeError 未捕获
  （except 只接 OSError/JSONDecodeError）直接冒出
- _load_annotation 返回空 dict {}：runner 层 _annotation_present
  为 True（is not None）但 chunk_boundary 三指标 reason
  no_annotation（{} falsy 走无标注分支）——不对称现状锁定
- run_evaluation(tolerance_chars=9) 真实路径 → 内部行
  _tolerance_chars == 9（单 chunk 早退也记录）
- fake process_single 创建 image 目录 → compute_automatic_metrics
  收到非 None image_base_dir（is_dir 判定）
- forbidden tokens 第三百七十八批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import pytest

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import _load_annotation, run_evaluation


class _FakeDoc:
    parser_version = "7.7"
    source_hash = "deadbeef"

    def __init__(self, d):
        self._d = d

    def to_dict(self):
        return self._d


_DOC_DICT = {
    "elements": [{"element_id": "e1", "type": "paragraph",
                  "content": "AB"}],
    "chunks": [{"text": "AB", "source_element_ids": ["e1"]}],
}


def _mk(tmp_path, ann_content=None):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    doc = {"doc_id": "d1", "path": "samples/a.pdf",
           "source_type": "pdf"}
    if ann_content is not None:
        (root / "ann.json").write_text(ann_content, encoding="utf-8")
        doc["annotation_file"] = "ann.json"
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [doc]}), encoding="utf-8")
    return load_manifest(f, root)


# ---------- 非 UTF-8 标注 ----------

def test_load_annotation_bad_encoding_batch106(tmp_path):
    f = tmp_path / "ann.json"
    f.write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(UnicodeDecodeError):
        _load_annotation(f)


# ---------- 空 dict 标注不对称 ----------

def test_empty_dict_annotation_asymmetry_batch106(tmp_path):
    m = _mk(tmp_path, "{}")
    assert _load_annotation(m.documents[0].annotation_resolved) == {}
    captured = []
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}), \
         patch.object(runner_mod, "aggregate_summary",
                      side_effect=lambda r: captured.append(
                          list(r)) or {}):
        run_evaluation(m, tmp_path / "r.json")
    row = captured[0][0]
    assert row["_annotation_present"] is True  # {} is not None


def test_empty_dict_annotation_no_annotation_metrics_batch106(
        tmp_path):
    m = _mk(tmp_path, "{}")
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        rep = run_evaluation(m, tmp_path / "r.json")
    metrics = rep["per_doc"][0]["metrics"]
    assert metrics["chunk_boundary_precision"] == {
        "value": None, "reason": "no_annotation"}
    assert metrics["chunk_boundary_f1"] == {
        "value": None, "reason": "no_annotation"}


# ---------- tolerance 真实路径 ----------

def test_tolerance_nine_real_path_batch106(tmp_path):
    m = _mk(tmp_path)
    captured = []
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}), \
         patch.object(runner_mod, "aggregate_summary",
                      side_effect=lambda r: captured.append(
                          list(r)) or {}):
        run_evaluation(m, tmp_path / "r.json", tolerance_chars=9)
    assert captured[0][0]["_tolerance_chars"] == 9


# ---------- image_base_dir 非 None ----------

def test_image_base_dir_real_dir_batch106(tmp_path):
    m = _mk(tmp_path)
    captured = {}

    def fake_ps(path, out_path, **kwargs):
        d = runner_mod.image_output_dir_for(
            out_path, _FakeDoc.source_hash)
        d.mkdir(parents=True, exist_ok=True)
        return _FakeDoc(_DOC_DICT), []

    with patch.object(runner_mod, "process_single",
                      side_effect=fake_ps), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}), \
         patch.object(runner_mod, "compute_automatic_metrics",
                      side_effect=lambda **kw:
                      captured.update(kw) or {}):
        run_evaluation(m, tmp_path / "r.json")
    expected = runner_mod.image_output_dir_for(
        tmp_path / "_per_doc" / "d1.json", "deadbeef")
    assert captured["image_base_dir"] == expected


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch106():
    src = _src()
    assert "except (OSError, json.JSONDecodeError):" in src
    assert ("image_base_dir=image_dir if (image_dir is not None "
            "and image_dir.is_dir()) else None,") in src
    assert "public_per_doc = []" in src


# ---------- forbidden tokens 第三百七十八批 ----------

def test_source_no_eval_batch106():
    assert "eval(" not in _src()


def test_source_no_exec_batch106():
    assert "exec(" not in _src()


def test_source_no_compile_batch106():
    assert "compile(" not in _src()


def test_source_no_globals_batch106():
    assert "globals(" not in _src()


def test_source_no_locals_batch106():
    assert "locals(" not in _src()


def test_source_no_os_system_batch106():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch106():
    assert "subprocess" not in _src()


def test_source_no_popen_batch106():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch106():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch106():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch106():
    assert "socket" not in _src()


def test_source_no_requests_batch106():
    assert "requests" not in _src()


def test_source_no_urllib_batch106():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch106():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch106():
    assert "yield" not in _src()


def test_source_no_async_await_batch106():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch106():
    assert _src().count("open(") == 2
