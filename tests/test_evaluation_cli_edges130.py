"""evaluation/cli.py 第四百九十二轮 edges 测试（Round 1048）。

补强 edges129 未触及的角度（第四百二十四批，probe 实证）。

新角度（ef 结果对 CLI 表面全静默）：
- 真实好 docx + 真实损坏 docx（ef，期望码错误
  E_PARSE_FAIL）与期望码正确（docx_open_failed）
  两次 run 的 CLI 表面完全相同：rc 0、stderr 空、
  documents=1（成功 1，失败 0）、stdout 无 "matches"
  无 "f1"——ef 匹配与否只在报告 JSON 里可见
  （matches False vs True），CLI 不给任何信号
- documents 计数行只数 documents 条目：两个文件
  实际参与（好 doc + 损坏 ef），表面恒 documents=1
- 注意 stdout 里 "False" 子串来自 git_dirty=False，
  与 ef 无关——断言避开该子串
- forbidden tokens 第五百一十九批（open 1）
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json

from docx import Document

import evaluation.cli as cli_mod
from evaluation.cli import main


def _setup(tmp_path):
    (tmp_path / "pyproject.toml").write_text("",
                                             encoding="utf-8")
    (tmp_path / "samples").mkdir()
    d = Document()
    d.add_paragraph("Hello world paragraph one.")
    d.save(str(tmp_path / "samples" / "good.docx"))
    (tmp_path / "samples" / "bad.docx").write_bytes(
        b"not a docx")


def _run(tmp_path, code):
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1",
                       "path": "samples/good.docx",
                       "source_type": "docx"}],
        "expected_failures": [{
            "doc_id": "f1", "path": "samples/bad.docx",
            "expected_error_code": code}]}),
        encoding="utf-8")
    out, err = io.StringIO(), io.StringIO()
    rp = tmp_path / "o.json"
    with contextlib.redirect_stdout(out), \
            contextlib.redirect_stderr(err):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(rp)])
    rep = json.loads(rp.read_text(encoding="utf-8"))
    return rc, out.getvalue(), err.getvalue(), rep


# ---------- 期望码错误：表面无信号 ----------

def test_mismatch_silent_at_cli_batch246(tmp_path):
    _setup(tmp_path)
    rc, out, err, rep = _run(tmp_path, "E_PARSE_FAIL")
    assert rc == 0
    assert err == ""
    assert "matches" not in out
    assert "f1" not in out
    assert "documents=1（成功 1，失败 0）" in out
    assert rep["expected_failures"][0]["matches"] is False
    assert rep["expected_failures"][0][
        "actual_error_code"] == "docx_open_failed"


# ---------- 期望码正确：同一表面 ----------

def test_match_same_surface_batch246(tmp_path):
    _setup(tmp_path)
    rc, out, err, rep = _run(tmp_path, "docx_open_failed")
    assert rc == 0
    assert err == ""
    assert "matches" not in out
    assert "documents=1（成功 1，失败 0）" in out
    assert report_ef(rep) == {
        "doc_id": "f1",
        "expected_error_code": "docx_open_failed",
        "actual_error_code": "docx_open_failed",
        "matches": True}


def report_ef(rep):
    return rep["expected_failures"][0]


# ---------- ef 不进计数行 ----------

def test_ef_absent_from_counts_batch246(tmp_path):
    _setup(tmp_path)
    for code in ("E_PARSE_FAIL", "docx_open_failed"):
        rc, out, _, rep = _run(tmp_path, code)
        assert rc == 0
        assert "documents=1（成功 1，失败 0）" in out
        assert len(rep["per_doc"]) == 1


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch246():
    src = _src()
    assert "documents={n_docs}（成功 {n_ok}，失败 {n_fail}）" \
        in src
    assert "n_fail = n_docs - n_ok" in src


# ---------- forbidden tokens 第五百一十九批 ----------

def test_source_no_eval_batch246():
    assert "eval(" not in _src()


def test_source_no_exec_batch246():
    assert "exec(" not in _src()


def test_source_no_compile_batch246():
    assert "compile(" not in _src()


def test_source_no_globals_batch246():
    assert "globals(" not in _src()


def test_source_no_locals_batch246():
    assert "locals(" not in _src()


def test_source_no_os_system_batch246():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch246():
    assert "subprocess" not in _src()


def test_source_no_popen_batch246():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch246():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch246():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch246():
    assert "socket" not in _src()


def test_source_no_requests_batch246():
    assert "requests" not in _src()


def test_source_no_urllib_batch246():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch246():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch246():
    assert "yield" not in _src()


def test_source_no_async_await_batch246():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch246():
    assert _src().count("open(") == 1
