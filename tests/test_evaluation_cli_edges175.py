"""evaluation/cli.py 第六百七十六轮 edges 测试（Round 1340）。

补强 edges174 未触及的角度（第七百一十二批，probe 实证）。

新角度（tolerance flag 渲染 / validate-report 缺文件）：
- **--tolerance-chars 10**
  ——inspect 输出
  '_tolerance_chars'
  行渲染 10 (ok)
  （flag 到重算链
  首锁）
- **validate-report
  缺文件**——rc 2 +
  '[ERROR] 报告不
  存在: <path>'
- **rc 0**——带 flag
  照常成功
- forbidden tokens 第五百九十七批（open 1）
"""

from __future__ import annotations

import inspect
import io
import sys
from contextlib import redirect_stderr, \
    redirect_stdout

import pytest

import evaluation.cli as cli_mod
from app.pipeline import process_single
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


def _ojson(tmp_path):
    (tmp_path / "c.pdf").write_bytes(_wrap(ONEP))
    doc, errors = process_single(
        tmp_path / "c.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=32)
    assert errors == []
    return tmp_path / "o.json"


# ---------- tolerance flag 渲染 ----------

def test_tolerance_ten_line_batch538(tmp_path):
    oj = _ojson(tmp_path)
    sys.argv = ["evaluation.cli", "inspect-doc",
                str(oj), "--tolerance-chars", "10"]
    out = io.StringIO()
    with redirect_stdout(out):
        main()
    assert (f"  {'_tolerance_chars':36}"
            " 10  (ok)") in out.getvalue()


def test_tolerance_zero_line_batch538(tmp_path):
    oj = _ojson(tmp_path)
    sys.argv = ["evaluation.cli", "inspect-doc",
                str(oj), "--tolerance-chars", "0"]
    out = io.StringIO()
    with redirect_stdout(out):
        main()
    assert (f"  {'_tolerance_chars':36}"
            " 0  (ok)") in out.getvalue()


def test_tolerance_flag_rc_zero_batch538(
        tmp_path):
    oj = _ojson(tmp_path)
    sys.argv = ["evaluation.cli", "inspect-doc",
                str(oj), "--tolerance-chars", "10"]
    out = io.StringIO()
    with redirect_stdout(out):
        rc = main()
    assert rc == 0


# ---------- validate-report 缺文件 ----------

def test_validate_report_missing_rc_two_batch538(
        tmp_path):
    sys.argv = ["evaluation.cli", "validate-report",
                str(tmp_path / "nope.json")]
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main()
    assert rc == 2


def test_validate_report_missing_error_batch538(
        tmp_path):
    sys.argv = ["evaluation.cli", "validate-report",
                str(tmp_path / "nope.json")]
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        main()
    assert err.getvalue().startswith(
        "[ERROR] 报告不存在:")


# ---------- inspect 缺文件复核 ----------

def test_inspect_missing_rc_two_batch538(
        tmp_path):
    sys.argv = ["evaluation.cli", "inspect-doc",
                str(tmp_path / "nope.json")]
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main()
    assert rc == 2


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_counts_batch538():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


def test_source_error_lines_batch538():
    src = _src()
    assert "[ERROR] 报告不存在" in src


# ---------- forbidden tokens 第五百九十七批 ----------

def test_source_no_eval_batch538():
    assert "eval(" not in _src()


def test_source_no_exec_batch538():
    assert "exec(" not in _src()


def test_source_no_compile_batch538():
    assert "compile(" not in _src()


def test_source_no_globals_batch538():
    assert "globals(" not in _src()


def test_source_no_locals_batch538():
    assert "locals(" not in _src()


def test_source_no_os_system_batch538():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch538():
    assert "subprocess" not in _src()


def test_source_no_popen_batch538():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch538():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch538():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch538():
    assert "socket" not in _src()


def test_source_no_requests_batch538():
    assert "requests" not in _src()


def test_source_no_urllib_batch538():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch538():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch538():
    assert "yield" not in _src()


def test_source_no_async_await_batch538():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch538():
    assert ".call(" not in _src()


def test_source_open_count_is_1_batch538():
    assert _src().count("open(") == 1
