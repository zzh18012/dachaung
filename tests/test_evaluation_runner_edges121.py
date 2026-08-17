"""evaluation/runner.py 第四百二十九轮 edges 测试（Round 985）。

补强 edges120 未触及的角度（第三百六十一批，probe 实证）。

新角度：
- 标注端到端：annotation_file → _load_annotation →
  chunk_boundary_prf 用真实 anchors 计算 → 公开报告
  per_doc.metrics 出现 chunk_boundary_precision 1.0
- 嵌套输出目录 sub/dir/o.json 自动创建
- 落盘 JSON 格式锁定：indent=2（第 2 行两个空格起）+
  ensure_ascii=False（中文 category 原样写入非 \\u 转义）
- 报告顶层恰 6 键有序
- forbidden tokens 第四百五十五批（open 2）
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.runner as runner_mod
from evaluation.runner import run_evaluation


class _FakeDoc:
    parser_version = "pv"
    source_hash = "sh"

    def to_dict(self):
        return {"elements": [], "chunks": [
            {"text": "AB", "source_element_ids": []},
            {"text": "CD", "source_element_ids": []}]}


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    (tmp_path / "anns").mkdir()
    (tmp_path / "anns" / "ann.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "d1",
        "chunk_boundary_anchors": [
            {"marker": "AB", "position": "after"}]}),
        encoding="utf-8")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf",
             "annotation_file": "anns/ann.json",
             "categories": ["中文"]}]}), encoding="utf-8")
    from evaluation.manifest import load_manifest
    return load_manifest(mf, tmp_path)


def _run(tmp_path, out_rel):
    m = _setup(tmp_path)
    with patch.object(runner_mod, "process_single",
                      return_value=(_FakeDoc(), [])):
        rep = run_evaluation(m, tmp_path / out_rel)
    return rep


# ---------- 标注端到端 ----------

def test_annotation_flows_to_public_metrics_batch183(tmp_path):
    rep = _run(tmp_path, "o.json")
    assert rep["per_doc"][0]["metrics"][
        "chunk_boundary_precision"] == {"value": 1.0,
                                        "reason": None}
    assert rep["devset"]["categories_covered"] == ["中文"]


# ---------- 嵌套输出目录 ----------

def test_nested_output_dirs_created_batch183(tmp_path):
    rep = _run(tmp_path, "sub/dir/o.json")
    assert (tmp_path / "sub" / "dir" / "o.json").is_file()
    assert rep["report_version"] == "1.1"


# ---------- 落盘格式 ----------

def test_report_json_formatting_batch183(tmp_path):
    _run(tmp_path, "o.json")
    raw = (tmp_path / "o.json").read_text(encoding="utf-8")
    lines = raw.splitlines()
    assert lines[0] == "{"
    assert lines[1] == '  "report_version": "1.1",'
    assert "中文" in raw
    assert "\\u4e2d" not in raw


# ---------- 顶层 6 键 ----------

def test_report_top_six_keys_order_batch183(tmp_path):
    rep = _run(tmp_path, "o.json")
    assert list(rep) == ["report_version", "provenance", "devset",
                         "summary", "per_doc",
                         "expected_failures"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch183():
    src = _src()
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in src
    assert "out_p.parent.mkdir(parents=True, exist_ok=True)" in src
    assert "annotation = _load_annotation(doc.annotation_resolved)" in src
    assert '"expected_failures": expected_failure_results,' in src


# ---------- forbidden tokens 第四百五十五批 ----------

def test_source_no_eval_batch183():
    assert "eval(" not in _src()


def test_source_no_exec_batch183():
    assert "exec(" not in _src()


def test_source_no_compile_batch183():
    assert "compile(" not in _src()


def test_source_no_globals_batch183():
    assert "globals(" not in _src()


def test_source_no_locals_batch183():
    assert "locals(" not in _src()


def test_source_no_os_system_batch183():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch183():
    assert "subprocess" not in _src()


def test_source_no_popen_batch183():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch183():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch183():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch183():
    assert "socket" not in _src()


def test_source_no_requests_batch183():
    assert "requests" not in _src()


def test_source_no_urllib_batch183():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch183():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch183():
    assert "yield" not in _src()


def test_source_no_async_await_batch183():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch183():
    assert _src().count("open(") == 2
