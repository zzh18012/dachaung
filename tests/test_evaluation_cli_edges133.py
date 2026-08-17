"""evaluation/cli.py 第五百一十三轮 edges 测试（Round 1069）。

补强 edges129-132 未触及的角度（第四百四十五批，probe 实证）。

新角度（自定义容差的伪指标显示 + CLI 对 chunker-ef 的静默）：
- inspect-doc --tolerance-chars 7 → 泄漏的 `_tolerance_chars`
  伪指标行渲染 **7**（R1062 的泄漏行随旗标值流动）；
  boundary 三项仍 null no_annotation——无标注时容差
  旗标只改显示、不改任何判定
- CLI run mc 31 双账本板（R1068 的 doc+ef 同文件）在
  CLI 表面：rc 0、stdout 只报 "documents=1（成功 0，
  失败 1）"，**"chunker_failed" 字样完全不出现**（CLI
  对 ef 命中保持静默——R1048 结论在新错误码下复现）；
  报告文件里 ef matches True + d1 error_code
  chunker_failed 双双在场；validate-report 对该报告 [OK]
- forbidden tokens 第五百四十批（open 1）
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json

from docx import Document

import evaluation.cli as cli_mod
from app.pipeline import process_single
from evaluation.cli import main


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("",
                                             encoding="utf-8")
    (tmp_path / "samples").mkdir()
    d = Document()
    d.add_paragraph("AAA first paragraph body.")
    d.save(str(tmp_path / "samples" / "good.docx"))


def _main(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(argv)
    return rc, buf.getvalue()


def _run_ef(tmp_path):
    _setup(tmp_path)
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1",
                       "path": "samples/good.docx",
                       "source_type": "docx"}],
        "expected_failures": [{
            "doc_id": "ef1", "path": "samples/good.docx",
            "source_type": "docx",
            "expected_error_code":
                "chunker_failed"}]}), encoding="utf-8")
    return _main(["run", "--manifest", str(mf),
                  "--output", str(tmp_path / "o.json"),
                  "--max-chars", "31"])


# ---------- 自定义容差 → 伪指标行流动 ----------

def test_inspect_doc_custom_tolerance_batch268(tmp_path):
    _setup(tmp_path)
    process_single(tmp_path / "samples" / "good.docx",
                   tmp_path / "doc.json",
                   parser_name="fallback", max_chars=200,
                   write_json=True)
    rc, out = _main(["inspect-doc",
                     str(tmp_path / "doc.json"),
                     "--tolerance-chars", "7"])
    assert rc == 0
    assert ("  _tolerance_chars"
            "                     7  (ok)") in out
    assert ("  chunk_boundary_f1"
            "                    null  (no_annotation)") in out


# ---------- CLI 对 chunker-ef 命中静默 ----------

def test_cli_run_ef_chunker_silent_batch268(tmp_path):
    rc, out = _run_ef(tmp_path)
    assert rc == 0
    assert "documents=1（成功 0，失败 1）" in out
    assert "chunker_failed" not in out
    rep = json.loads((tmp_path / "o.json").read_text(
        encoding="utf-8"))
    assert rep["expected_failures"][0]["matches"] is True
    assert rep["per_doc"][0]["metrics"]["error_code"] == {
        "value": "chunker_failed", "reason": None}


# ---------- 同报告的汇总口径 ----------

def test_cli_report_ef_run_summary_batch268(tmp_path):
    _run_ef(tmp_path)
    rep = json.loads((tmp_path / "o.json").read_text(
        encoding="utf-8"))
    assert rep["summary"]["success_rates"] == {
        "pipeline_success": {"success_count": 0,
                             "total": 1, "rate": 0.0}}


# ---------- validate-report 对该报告放行 ----------

def test_cli_validate_report_ef_run_batch268(tmp_path):
    _run_ef(tmp_path)
    rc, out = _main(["validate-report",
                     str(tmp_path / "o.json")])
    assert rc == 0
    assert "[OK]" in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch268():
    src = _src()
    assert "args.tolerance_chars" in src
    assert "inspect-doc" in src


# ---------- forbidden tokens 第五百四十批 ----------

def test_source_no_eval_batch268():
    assert "eval(" not in _src()


def test_source_no_exec_batch268():
    assert "exec(" not in _src()


def test_source_no_compile_batch268():
    assert "compile(" not in _src()


def test_source_no_globals_batch268():
    assert "globals(" not in _src()


def test_source_no_locals_batch268():
    assert "locals(" not in _src()


def test_source_no_os_system_batch268():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch268():
    assert "subprocess" not in _src()


def test_source_no_popen_batch268():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch268():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch268():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch268():
    assert "socket" not in _src()


def test_source_no_requests_batch268():
    assert "requests" not in _src()


def test_source_no_urllib_batch268():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch268():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch268():
    assert "yield" not in _src()


def test_source_no_async_await_batch268():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch268():
    assert _src().count("open(") == 1
