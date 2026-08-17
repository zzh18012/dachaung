"""evaluation/runner.py 第三百三十八轮 edges 测试（Round 894）。

补强 edges107 未触及的角度（第二百七十批，probe 实证）。

新角度：
- 标注文件内容为 JSON 字符串 '"x"' → chunk_boundary_prf 处
  AttributeError 未防护直接冒出
- 标注文件内容为 null → _annotation_present False，但单 chunk 文档
  _tolerance_chars 仍记录 30、_missing_markers []
- 报告顶层键序恰 6 项；落盘 indent=2
- 失败文档 wall_time 6 键完整（total 浮点 + 双 not_instrumented）
- tolerance_chars=7 透传到 chunk_boundary_prf kwargs
- figure_caption_prf 收到 (document_dict, annotation) 位置参数
- 公开 per_doc 键序恰 4 项（内部三键已剥）
- forbidden tokens 第三百六十四批
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


# ---------- 字符串标注未防护 ----------

def test_string_annotation_crashes_batch92(tmp_path):
    m = _mk(tmp_path, '"x"')
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        with pytest.raises(AttributeError):
            run_evaluation(m, tmp_path / "r.json")


# ---------- null 标注 ----------

def test_null_annotation_internal_row_batch92(tmp_path):
    m = _mk(tmp_path, "null")
    captured = []
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}), \
         patch.object(runner_mod, "aggregate_summary",
                      side_effect=lambda r: captured.append(list(r))
                      or {}):
        run_evaluation(m, tmp_path / "r.json")
    row = captured[0][0]
    assert row["_annotation_present"] is False
    assert row["_tolerance_chars"] == 30
    assert row["_missing_markers"] == []


# ---------- 报告结构 ----------

def test_report_key_order_batch92(tmp_path):
    m = _mk(tmp_path)
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        rep = run_evaluation(m, tmp_path / "r.json")
    assert list(rep) == ["report_version", "provenance", "devset",
                         "summary", "per_doc", "expected_failures"]


def test_report_written_indent2_batch92(tmp_path):
    m = _mk(tmp_path)
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        run_evaluation(m, tmp_path / "r.json")
    raw = (tmp_path / "r.json").read_text(encoding="utf-8")
    assert '\n  "provenance"' in raw


def test_public_per_doc_key_order_batch92(tmp_path):
    m = _mk(tmp_path)
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        rep = run_evaluation(m, tmp_path / "r.json")
    assert list(rep["per_doc"][0]) == ["doc_id", "source_type",
                                       "metrics", "wall_time_seconds"]


# ---------- 失败文档 wall_time ----------

def test_failed_doc_wall_time_shape_batch92(tmp_path):
    m = _mk(tmp_path)
    with patch.object(runner_mod, "process_single",
                      return_value=(None, [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        rep = run_evaluation(m, tmp_path / "r.json")
    wt = rep["per_doc"][0]["wall_time_seconds"]
    assert list(wt) == ["total", "parse", "chunk",
                        "parse_reason", "chunk_reason"]
    assert isinstance(wt["total"], float)
    assert wt["total"] >= 0
    assert wt["parse"] is None and wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


# ---------- 透传捕获 ----------

def test_tolerance_passthrough_kwarg_batch92(tmp_path):
    m = _mk(tmp_path)
    captured = {}

    def fake_cbp(doc, ann, **kwargs):
        captured.update(kwargs)
        return {}

    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}), \
         patch.object(runner_mod, "chunk_boundary_prf",
                      side_effect=fake_cbp):
        run_evaluation(m, tmp_path / "r.json", tolerance_chars=7)
    assert captured == {"tolerance_chars": 7}


def test_figure_caption_positional_args_batch92(tmp_path):
    m = _mk(tmp_path)
    captured = []

    def fake_fcp(doc, ann):
        captured.append((doc, ann))
        return {}

    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(_DOC_DICT), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}), \
         patch.object(runner_mod, "figure_caption_prf",
                      side_effect=fake_fcp):
        run_evaluation(m, tmp_path / "r.json")
    doc, ann = captured[0]
    assert doc == _DOC_DICT
    assert ann is None


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch92():
    src = _src()
    assert "metrics.update(fig_caps)" in src
    assert '"_annotation_present": annotation is not None,' in src
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in src
    assert "actual_code = errors[0].code if errors else None" in src


# ---------- forbidden tokens 第三百六十四批 ----------

def test_source_no_eval_batch92():
    assert "eval(" not in _src()


def test_source_no_exec_batch92():
    assert "exec(" not in _src()


def test_source_no_compile_batch92():
    assert "compile(" not in _src()


def test_source_no_globals_batch92():
    assert "globals(" not in _src()


def test_source_no_locals_batch92():
    assert "locals(" not in _src()


def test_source_no_os_system_batch92():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch92():
    assert "subprocess" not in _src()


def test_source_no_popen_batch92():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch92():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch92():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch92():
    assert "socket" not in _src()


def test_source_no_requests_batch92():
    assert "requests" not in _src()


def test_source_no_urllib_batch92():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch92():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch92():
    assert "yield" not in _src()


def test_source_no_async_await_batch92():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch92():
    assert _src().count("open(") == 2
