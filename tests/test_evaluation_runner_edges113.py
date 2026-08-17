"""evaluation/runner.py 第三百七十三轮 edges 测试（Round 929）。

补强 edges112 未触及的角度（第三百零五批，probe 实证）。

新角度：
- 内部 metrics dict 末 6 键序：figure_caption 三连在前、
  chunk_boundary 三连在后（update 顺序 fig_caps → chunk_b）
- 公开 per_doc 的 metrics 与内部行同一对象（引用传递，
  非拷贝）；report["provenance"] 亦是 build_provenance
  返回值原对象
- 报告落盘 ensure_ascii=False：categories ["中文"] 在文件
  里是原生 UTF-8 非 \\u 转义；文件末字符 "}"（json.dump
  无尾换行）
- 空清单真实聚合：per_doc []、counts sum None /
  participating 0、success rate None（分母 0）、devset 全 0
- forbidden tokens 第三百九十九批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


class _FakeDoc:
    parser_version = "7.7"
    source_hash = "deadbeef"

    def __init__(self):
        self._d = {
            "elements": [{"element_id": "e1", "type": "paragraph",
                          "content": "AB"}],
            "chunks": [{"text": "AB",
                        "source_element_ids": ["e1"]}],
        }

    def to_dict(self):
        return self._d


def _mk(tmp_path, docs):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True, exist_ok=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs}), encoding="utf-8")
    return load_manifest(f, root)


# ---------- metrics 末 6 键序 + 引用传递 ----------

def test_metrics_tail_six_keys_batch127(tmp_path):
    m = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf",
                        "categories": ["中文"]}])
    sentinel_prov = {"git_commit": None}
    captured = []
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value=sentinel_prov), \
         patch.object(runner_mod, "aggregate_summary",
                      side_effect=lambda r: captured.append(
                          list(r)) or {}):
        rep = run_evaluation(m, tmp_path / "r.json")
    row = captured[0][0]
    assert list(row["metrics"])[-6:] == [
        "figure_caption_precision", "figure_caption_recall",
        "figure_caption_f1", "chunk_boundary_precision",
        "chunk_boundary_recall", "chunk_boundary_f1",
    ]
    assert rep["per_doc"][0]["metrics"] is row["metrics"]
    assert rep["provenance"] is sentinel_prov


# ---------- ensure_ascii=False ----------

def test_report_utf8_raw_no_escape_batch127(tmp_path):
    m = _mk(tmp_path, [{"doc_id": "d1", "path": "samples/a.pdf",
                        "source_type": "pdf",
                        "categories": ["中文"]}])
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])), \
         patch.object(runner_mod, "build_provenance",
                      return_value={}):
        run_evaluation(m, tmp_path / "r.json")
    raw = (tmp_path / "r.json").read_text(encoding="utf-8")
    assert "中文" in raw
    assert "\\u4e2d" not in raw
    assert raw[-1] == "}"


# ---------- 空清单真实聚合 ----------

def test_empty_manifest_real_aggregation_batch127(tmp_path):
    m = _mk(tmp_path, [])
    with patch.object(runner_mod, "build_provenance",
                      return_value={}):
        rep = run_evaluation(m, tmp_path / "r.json")
    assert rep["per_doc"] == []
    assert rep["summary"]["counts"] == {
        "element_count_total": {"sum": None,
                                "participating_docs": 0}}
    assert rep["summary"]["success_rates"] == {
        "pipeline_success": {"success_count": 0, "total": 0,
                             "rate": None}}
    assert rep["devset"] == {
        "status": "incomplete", "file_count": 0,
        "content_group_count": 0, "pdf_count": 0,
        "docx_count": 0, "categories_covered": []}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch127():
    src = _src()
    assert 'json.dump(report, f, ensure_ascii=False, indent=2)' in src
    assert 'summary = aggregate_summary(per_doc_results)' in src
    assert "public_per_doc = []" in src
    assert 'out_p.parent.mkdir(parents=True, exist_ok=True)' in src


# ---------- forbidden tokens 第三百九十九批 ----------

def test_source_no_eval_batch127():
    assert "eval(" not in _src()


def test_source_no_exec_batch127():
    assert "exec(" not in _src()


def test_source_no_compile_batch127():
    assert "compile(" not in _src()


def test_source_no_globals_batch127():
    assert "globals(" not in _src()


def test_source_no_locals_batch127():
    assert "locals(" not in _src()


def test_source_no_os_system_batch127():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch127():
    assert "subprocess" not in _src()


def test_source_no_popen_batch127():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch127():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch127():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch127():
    assert "socket" not in _src()


def test_source_no_requests_batch127():
    assert "requests" not in _src()


def test_source_no_urllib_batch127():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch127():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch127():
    assert "yield" not in _src()


def test_source_no_async_await_batch127():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch127():
    assert _src().count("open(") == 2
