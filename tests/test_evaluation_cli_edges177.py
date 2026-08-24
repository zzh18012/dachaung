"""evaluation/cli.py 第六百七十八轮 edges 测试（Round 1351）。

补强 edges176 未触及的角度（第七百二十三批，probe 实证）。

新角度（composite manifest 走 CLI run / run 无 tolerance 行）：
- **run 收 --tolerance-chars**
  ——flag 被 run
  子命令接受
  （edges175 仅
  inspect-doc）
- **报告 composite**
  ——CLI 生成报告
  sdt 2 + cbp 1/14
  （容差 40 端到端
  进报告）
- **run 输出恰四行**
  ——成功输出无
  tolerance 行
  （负锁首验）
- **max_chars 回显**
  ——provenance
  max_chars 32
- forbidden tokens 第五百九十九批（open 1）
"""

from __future__ import annotations

import inspect
import io
import json
import sys
from contextlib import redirect_stderr, \
    redirect_stdout

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main


@pytest.fixture(autouse=True)
def _restore_argv():
    saved = sys.argv
    yield
    sys.argv = saved


def _wrap(s: bytes) -> bytes:
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xp = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


LONG = " ".join("Word%d." % i for i in range(60))
ONEP = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
        % LONG).encode()


def _setup(tmp_path):
    (tmp_path / "c.pdf").write_bytes(_wrap(ONEP))
    (tmp_path / "ann").mkdir()
    (tmp_path / "ann" / "a.json").write_text(
        json.dumps({
            "annotation_version": "1.0",
            "doc_id": "g1",
            "chunk_boundary_anchors": [
                {"marker": "Word1.",
                 "position": "after"}]}),
        encoding="utf-8")
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "g1", "path": "c.pdf",
             "source_type": "pdf",
             "annotation_file": "ann/a.json",
             "expectations": {
                 "element_count_by_type": {
                     "paragraph": 3}}}]}),
        encoding="utf-8")


def _run(tmp_path):
    _setup(tmp_path)
    sys.argv = ["evaluation.cli", "run",
                "--manifest",
                str(tmp_path / "m.json"),
                "--output",
                str(tmp_path / "r.json"),
                "--parser", "fallback",
                "--max-chars", "32",
                "--tolerance-chars", "40"]
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main()
    return rc, out.getvalue(), err.getvalue()


# ---------- run 收 --tolerance-chars ----------

def test_run_accepts_tolerance_flag_batch549(
        tmp_path):
    rc, _, err = _run(tmp_path)
    assert rc == 0
    assert err == ""


# ---------- run 输出恰四行 ----------

def test_run_output_four_lines_batch549(
        tmp_path):
    _, out, _ = _run(tmp_path)
    assert len(out.splitlines()) == 4


def test_run_stdout_no_tolword_batch549(
        tmp_path):
    _, out, _ = _run(tmp_path)
    assert "tolerance" not in out


def test_run_first_line_ok_batch549(tmp_path):
    _, out, _ = _run(tmp_path)
    assert out.splitlines()[0].startswith(
        "[OK] 评测完成：")


def test_run_documents_line_batch549(tmp_path):
    _, out, _ = _run(tmp_path)
    assert ("documents=1（成功 1，失败 0）"
            in out.splitlines()[1])


def test_run_devset_line_batch549(tmp_path):
    _, out, _ = _run(tmp_path)
    assert ("devset_status=incomplete "
            "file_count=1 groups=1 pdf=1 docx=0"
            in out.splitlines()[2])


def test_run_git_line_batch549(tmp_path):
    _, out, _ = _run(tmp_path)
    assert ("git_commit=unknown git_dirty=False"
            in out.splitlines()[3])


# ---------- 报告 composite ----------

def test_report_sdt_two_batch549(tmp_path):
    _run(tmp_path)
    rep = json.loads(
        (tmp_path / "r.json").read_text(
            encoding="utf-8"))
    assert rep["summary"]["silent_drop_total"] == 2


def test_report_cbp_hit_batch549(tmp_path):
    _run(tmp_path)
    rep = json.loads(
        (tmp_path / "r.json").read_text(
            encoding="utf-8"))
    assert rep["per_doc"][0]["metrics"][
        "chunk_boundary_precision"] == {
        "value": 1 / 14, "reason": None}


def test_report_sdc_per_doc_two_batch549(
        tmp_path):
    _run(tmp_path)
    rep = json.loads(
        (tmp_path / "r.json").read_text(
            encoding="utf-8"))
    assert rep["per_doc"][0]["metrics"][
        "silent_drop_count"] == {
        "value": 2, "reason": None}


def test_report_tolerance_absent_batch549(
        tmp_path):
    _run(tmp_path)
    blob = (tmp_path / "r.json").read_text(
        encoding="utf-8")
    assert "tolerance" not in blob


# ---------- max_chars 回显 ----------

def test_provenance_max_chars_batch549(
        tmp_path):
    _run(tmp_path)
    rep = json.loads(
        (tmp_path / "r.json").read_text(
            encoding="utf-8"))
    assert rep["provenance"]["max_chars"] == 32


def test_provenance_parser_fallback_batch549(
        tmp_path):
    _run(tmp_path)
    rep = json.loads(
        (tmp_path / "r.json").read_text(
            encoding="utf-8"))
    assert rep["provenance"]["parser_name"] == \
        "fallback"


# ---------- validate-report 闭环 ----------

def test_validate_report_on_composite_batch549(
        tmp_path):
    _run(tmp_path)
    sys.argv = ["evaluation.cli",
                "validate-report",
                str(tmp_path / "r.json")]
    out = io.StringIO()
    with redirect_stdout(out):
        rc = main()
    assert rc == 0
    assert out.getvalue().startswith("[OK]")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_counts_batch549():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


def test_source_tolerance_flag_batch549():
    assert "--tolerance-chars" in _src()


# ---------- forbidden tokens 第五百九十九批 ----------

def test_source_no_eval_batch549():
    assert "eval(" not in _src()


def test_source_no_exec_batch549():
    assert "exec(" not in _src()


def test_source_no_compile_batch549():
    assert "compile(" not in _src()


def test_source_no_globals_batch549():
    assert "globals(" not in _src()


def test_source_no_locals_batch549():
    assert "locals(" not in _src()


def test_source_no_os_system_batch549():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch549():
    assert "subprocess" not in _src()


def test_source_no_popen_batch549():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch549():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch549():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch549():
    assert "socket" not in _src()


def test_source_no_requests_batch549():
    assert "requests" not in _src()


def test_source_no_urllib_batch549():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch549():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch549():
    assert "yield" not in _src()


def test_source_no_async_await_batch549():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch549():
    assert ".call(" not in _src()


def test_source_open_count_is_1_batch549():
    assert _src().count("open(") == 1
