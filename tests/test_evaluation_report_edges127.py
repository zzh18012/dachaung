"""evaluation/report.py 第五百四十六轮 edges 测试（Round 1102）。

补强 edges124-126 未触及的角度（第四百七十八批，probe 实证）。

新角度（parser_version 落穿 + 数值截断 + 写读全等）：
- **parser_version 落穿**：bad.docx（无版本）在前 +
  good.docx 在后 → provenance.parser_version 取自
  good——"首个成功文档"语义：失败文档被跳过，
  版本号向后落穿（runner 侧 for 循环行为首锁）
- **全失败板版本 None**：仅 bad.docx → 落穿到底
  无所获 → parser_version None——provenance 字段
  依赖至少一次成功
- **float max_chars 截断**：build_provenance 传
  200.9 → int(200.9)=200——入档前显式 int() 强转
- **写出即读回全等**：run_evaluation 返回 dict 与
  落盘 JSON reload 后 == 全等——序列化无损
  （float wall_time、嵌套 reason 均原样）
- forbidden tokens 第五百七十三批（report 变体：15 项
  去 subprocess + open 0 + subprocess.run 计 2）
"""

from __future__ import annotations

import inspect
import json
import pathlib

from docx import Document

import evaluation.report as report_mod
from evaluation.manifest import load_manifest
from evaluation.report import build_provenance
from evaluation.runner import run_evaluation


def _board(tmp_path, documents):
    (tmp_path / "samples").mkdir(exist_ok=True)
    d = Document()
    d.add_paragraph("AAA body text here.")
    d.save(str(tmp_path / "samples" / "good.docx"))
    (tmp_path / "samples" / "bad.docx").write_bytes(
        b"garbage")
    m = {"manifest_version": "1.0",
         "devset_status": "incomplete",
         "documents": documents}
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(m), encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- parser_version 落穿 ----------

def test_parser_version_falls_through_batch301(tmp_path):
    rep = run_evaluation(
        _board(tmp_path, [
            {"doc_id": "zbad",
             "path": "samples/bad.docx",
             "source_type": "docx"},
            {"doc_id": "agood",
             "path": "samples/good.docx",
             "source_type": "docx"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    pv = rep["provenance"]["parser_version"]
    assert pv is not None
    assert "pdfplumber" in pv
    assert "python-docx" in pv


# ---------- 全失败板版本 None ----------

def test_all_fail_parser_version_none_batch301(tmp_path):
    rep = run_evaluation(
        _board(tmp_path, [
            {"doc_id": "d1", "path": "samples/bad.docx",
             "source_type": "docx"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    assert rep["provenance"]["parser_version"] is None


# ---------- float max_chars 截断 ----------

def test_float_max_chars_truncated_batch301(tmp_path):
    prov = build_provenance(tmp_path, "fallback",
                            200.9, None)
    assert prov["max_chars"] == 200
    assert isinstance(prov["max_chars"], int)


# ---------- 写出即读回全等 ----------

def test_round_trip_equal_batch301(tmp_path):
    out = tmp_path / "r.json"
    rep = run_evaluation(
        _board(tmp_path, [
            {"doc_id": "d1", "path": "samples/good.docx",
             "source_type": "docx"}]),
        out, parser_name="fallback", max_chars=200)
    reloaded = json.loads(
        out.read_text(encoding="utf-8"))
    assert rep == reloaded


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch301():
    src = _src()
    assert 'summary["counts"] = counts' in src
    assert '"sum": sum(values),' in src


# ---------- forbidden tokens 第五百七十三批（report 变体）----------

def test_source_no_eval_batch301():
    assert "eval(" not in _src()


def test_source_no_exec_batch301():
    assert "exec(" not in _src()


def test_source_no_compile_batch301():
    assert "compile(" not in _src()


def test_source_no_globals_batch301():
    assert "globals(" not in _src()


def test_source_no_locals_batch301():
    assert "locals(" not in _src()


def test_source_no_os_system_batch301():
    assert "os.system" not in _src()


def test_source_no_popen_batch301():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch301():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch301():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch301():
    assert "socket" not in _src()


def test_source_no_requests_batch301():
    assert "requests" not in _src()


def test_source_no_urllib_batch301():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch301():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch301():
    assert "yield" not in _src()


def test_source_no_async_await_batch301():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch301():
    assert _src().count("open(") == 0


def test_source_subprocess_run_count_is_2_batch301():
    assert _src().count("subprocess.run") == 2
