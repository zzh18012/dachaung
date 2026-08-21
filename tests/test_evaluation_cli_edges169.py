"""evaluation/cli.py 第六百七十轮 edges 测试（Round 1304）。

补强 edges168 未触及的角度（第六百七十六批，probe 实证）。

新角度（真坏文件 CLI 链 / 全败清单）：
- **混合成败行**——好 + 坏
  PDF + ef 命中 → rc 0 +
  'documents=2（成功 1，
  失败 1）'（成败混计输出
  首锁）
- **ef 报告过 Schema**——
  含 expected_failures 段
  报告 validate-report 通
  关
- **全败 rc 仍 0**——仅坏
  PDF 清单 → rc 0 + [OK]
  + 'documents=1（成功 0，
  失败 1）'（run 退出码反
  映清单处理而非文档成败
  首锁）
- **全败报告面**——success
  {0, 1, 0.0}；ecbt null/
  pipeline_failed；报告
  仍过 Schema
- forbidden tokens 第五百九十一批（open 1）
"""

from __future__ import annotations

import inspect
import json
import sys

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
STREAM = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
          % ("A" * 80)
          + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
          % LONG).encode()


def _files(tmp_path):
    (tmp_path / "good.pdf").write_bytes(_wrap(STREAM))
    (tmp_path / "bad.pdf").write_bytes(b"not a pdf at all")


def _run(tmp_path, capsys, manifest_name):
    rep = tmp_path / ("r_%s" % manifest_name)
    sys.argv = ["evaluation.cli", "run", "--manifest",
                str(tmp_path / manifest_name),
                "--output", str(rep), "--parser", "fallback",
                "--max-chars", "32"]
    rc = main()
    out = capsys.readouterr().out
    return rc, out, json.loads(
        rep.read_text(encoding="utf-8"))


# ---------- 混合成败行 ----------

def _mixed(tmp_path):
    _files(tmp_path)
    (tmp_path / "mmix.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "g1", "path": "good.pdf",
             "source_type": "pdf"},
            {"doc_id": "bad1", "path": "bad.pdf",
             "source_type": "pdf"}],
        "expected_failures": [{
            "doc_id": "bad1", "path": "bad.pdf",
            "expected_error_code":
            "pdfplumber_open_failed"}]}),
        encoding="utf-8")


def test_mixed_rc_zero_batch502(tmp_path, capsys):
    _mixed(tmp_path)
    rc, out, _ = _run(tmp_path, capsys, "mmix.json")
    assert rc == 0
    assert "[OK]" in out


def test_mixed_counts_line_batch502(tmp_path, capsys):
    _mixed(tmp_path)
    _, out, _ = _run(tmp_path, capsys, "mmix.json")
    assert "documents=2（成功 1，失败 1）" in out


def test_mixed_ef_report_batch502(tmp_path, capsys):
    _mixed(tmp_path)
    _, _, report = _run(tmp_path, capsys, "mmix.json")
    assert report["expected_failures"] == [{
        "doc_id": "bad1",
        "expected_error_code": "pdfplumber_open_failed",
        "actual_error_code": "pdfplumber_open_failed",
        "matches": True}]


def test_mixed_report_validates_batch502(tmp_path, capsys):
    _mixed(tmp_path)
    _run(tmp_path, capsys, "mmix.json")
    sys.argv = ["evaluation.cli", "validate-report",
                str(tmp_path / "r_mmix.json")]
    assert main() == 0
    assert "通过 evaluation-report Schema 校验" in \
        capsys.readouterr().out


# ---------- 全败清单 ----------

def _badonly(tmp_path):
    _files(tmp_path)
    (tmp_path / "mbad.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "bad1", "path": "bad.pdf",
             "source_type": "pdf"}]}), encoding="utf-8")


def test_badonly_rc_zero_batch502(tmp_path, capsys):
    _badonly(tmp_path)
    rc, out, _ = _run(tmp_path, capsys, "mbad.json")
    assert rc == 0
    assert "[OK]" in out


def test_badonly_counts_line_batch502(tmp_path, capsys):
    _badonly(tmp_path)
    _, out, _ = _run(tmp_path, capsys, "mbad.json")
    assert "documents=1（成功 0，失败 1）" in out
    assert ("devset_status=incomplete file_count=1 "
            "groups=1 pdf=1 docx=0") in out


def test_badonly_success_zero_batch502(tmp_path, capsys):
    _badonly(tmp_path)
    _, _, report = _run(tmp_path, capsys, "mbad.json")
    assert report["summary"]["success_rates"][
        "pipeline_success"] == {
        "success_count": 0, "total": 1, "rate": 0.0}


def test_badonly_ecbt_null_batch502(tmp_path, capsys):
    _badonly(tmp_path)
    _, _, report = _run(tmp_path, capsys, "mbad.json")
    assert report["per_doc"][0]["metrics"][
        "element_count_by_type"] == {
        "value": None, "reason": "pipeline_failed"}


def test_badonly_report_validates_batch502(
        tmp_path, capsys):
    _badonly(tmp_path)
    _run(tmp_path, capsys, "mbad.json")
    sys.argv = ["evaluation.cli", "validate-report",
                str(tmp_path / "r_mbad.json")]
    assert main() == 0


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch502():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百九十一批 ----------

def test_source_no_eval_batch502():
    assert "eval(" not in _src()


def test_source_no_exec_batch502():
    assert "exec(" not in _src()


def test_source_no_compile_batch502():
    assert "compile(" not in _src()


def test_source_no_globals_batch502():
    assert "globals(" not in _src()


def test_source_no_locals_batch502():
    assert "locals(" not in _src()


def test_source_no_os_system_batch502():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch502():
    assert "subprocess" not in _src()


def test_source_no_popen_batch502():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch502():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch502():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch502():
    assert "socket" not in _src()


def test_source_no_requests_batch502():
    assert "requests" not in _src()


def test_source_no_urllib_batch502():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch502():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch502():
    assert "yield" not in _src()


def test_source_no_async_await_batch502():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch502():
    assert ".call(" not in _src()


def test_source_open_count_is_1_batch502():
    assert _src().count("open(") == 1
