"""evaluation/runner.py 第四百零八轮 edges 测试（Round 964）。

补强 edges117 未触及的角度（第三百四十批，probe 实证）。

新角度：
- BOM 头标注文件：utf-8 读入 BOM 字符 → json 解析
  失败 → _load_annotation 返回 None（静默丢弃，无告警）
- ef 路径指向存在但内容非法的文件（b"x"）→ 真实
  parser 错误码 "pdfplumber_open_failed" ≠
  "E_PARSE" → matches False
- 空 documents 清单 → 完整报告仍通过
  evaluation-report Schema（provenance+devset+空
  summary/per_doc/ef）
- wall_time_seconds.total 恒为非负 float
- forbidden tokens 第四百三十四批（open 2）
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from evaluation.manifest import load_manifest
from evaluation.runner import _load_annotation, run_evaluation
from evaluation.schema import validate_file


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")


def _manifest(tmp_path, name, data):
    f = tmp_path / name
    f.write_text(json.dumps(data), encoding="utf-8")
    return load_manifest(f, tmp_path)


# ---------- BOM 标注 ----------

def test_bom_annotation_dropped_batch162(tmp_path):
    _setup(tmp_path)
    bom = tmp_path / "bom.json"
    payload = json.dumps({"chunk_boundary_anchors": []})
    bom.write_bytes(b"\xef\xbb\xbf" + payload.encode("utf-8"))
    assert _load_annotation(bom) is None


# ---------- ef 指向坏内容文件 ----------

def test_ef_garbage_content_real_error_batch162(tmp_path):
    _setup(tmp_path)
    m = _manifest(tmp_path, "m.json", {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1",
                       "path": "samples/a.pdf",
                       "source_type": "pdf"}],
        "expected_failures": [{
            "doc_id": "ef1", "path": "samples/a.pdf",
            "expected_error_code": "E_PARSE"}]})
    rep = run_evaluation(m, tmp_path / "o.json")
    assert rep["expected_failures"][0] == {
        "doc_id": "ef1",
        "expected_error_code": "E_PARSE",
        "actual_error_code": "pdfplumber_open_failed",
        "matches": False}


# ---------- 空清单完整报告 ----------

def test_empty_manifest_report_schema_valid_batch162(tmp_path):
    _setup(tmp_path)
    m = _manifest(tmp_path, "m2.json", {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": []})
    rep = run_evaluation(m, tmp_path / "sub" / "o2.json")
    assert rep["per_doc"] == []
    assert list(rep["summary"]) == [
        "counts", "success_rates", "ratio_macro_averages",
        "silent_drop_total"]
    validate_file(tmp_path / "sub" / "o2.json",
                  "evaluation-report.schema.json")


# ---------- wall_time 非负 float ----------

def test_wall_time_nonneg_float_batch162(tmp_path):
    _setup(tmp_path)
    m = _manifest(tmp_path, "m3.json", {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf"}]})
    rep = run_evaluation(m, tmp_path / "o3.json")
    for r in rep["per_doc"]:
        t = r["wall_time_seconds"]["total"]
        assert isinstance(t, float)
        assert t >= 0.0


# ---------- 源码补强 ----------

def _src():
    import evaluation.runner as runner_mod
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch162():
    src = _src()
    assert "except (OSError, json.JSONDecodeError):" in src
    assert "t0 = time.perf_counter()" in src
    assert "elapsed = time.perf_counter() - t0" in src
    assert 'if errors[0].code if errors else None' not in src


# ---------- forbidden tokens 第四百三十四批 ----------

def test_source_no_eval_batch162():
    assert "eval(" not in _src()


def test_source_no_exec_batch162():
    assert "exec(" not in _src()


def test_source_no_compile_batch162():
    assert "compile(" not in _src()


def test_source_no_globals_batch162():
    assert "globals(" not in _src()


def test_source_no_locals_batch162():
    assert "locals(" not in _src()


def test_source_no_os_system_batch162():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch162():
    assert "subprocess" not in _src()


def test_source_no_popen_batch162():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch162():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch162():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch162():
    assert "socket" not in _src()


def test_source_no_requests_batch162():
    assert "requests" not in _src()


def test_source_no_urllib_batch162():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch162():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch162():
    assert "yield" not in _src()


def test_source_no_async_await_batch162():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch162():
    assert _src().count("open(") == 2
