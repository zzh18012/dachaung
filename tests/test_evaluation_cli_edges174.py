"""evaluation/cli.py 第六百七十五轮 edges 测试（Round 1334）。

补强 edges173 未触及的角度（第七百零六批，probe 实证）。

新角度（run 子命令正路 / 缺清单错误路径）：
- **run 四行输出**——
  '[OK] 评测完成：
  <output>' +
  documents=1（成功 1，
  失败 0）+
  devset_status=
  incomplete file_
  count=1 groups=1
  pdf=1 docx=0 +
  git_commit=unknown
  git_dirty=False
  （CLI 把 None 渲染
  unknown 首锁）
- **报告落盘**——rc 0
  后 r.json 存在
- **缺清单**——rc 2 +
  '[ERROR] 清单不
  存在: <path>'
- forbidden tokens 第五百九十六批（open 1）
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


def _board(tmp_path):
    (tmp_path / "c.pdf").write_bytes(_wrap(ONEP))
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "g1", "path": "c.pdf",
             "source_type": "pdf"}]}),
        encoding="utf-8")


def _run_cli(tmp_path, *extra):
    sys.argv = (["evaluation.cli", "run",
                 "--manifest", str(tmp_path / "m.json"),
                 "--output", str(tmp_path / "r.json")]
                + list(extra))
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main()
    return rc, out.getvalue(), err.getvalue()


# ---------- run 四行输出 ----------

def test_run_ok_line_batch532(tmp_path):
    _board(tmp_path)
    rc, out, _ = _run_cli(tmp_path, "--parser",
                          "fallback", "--max-chars", "32")
    assert rc == 0
    assert out.startswith(
        "[OK] 评测完成：")
    assert str(tmp_path / "r.json") in out


def test_run_documents_line_batch532(tmp_path):
    _board(tmp_path)
    _, out, _ = _run_cli(tmp_path)
    assert "documents=1（成功 1，失败 0）" in out


def test_run_devset_line_batch532(tmp_path):
    _board(tmp_path)
    _, out, _ = _run_cli(tmp_path)
    assert ("devset_status=incomplete "
            "file_count=1 groups=1 pdf=1 "
            "docx=0") in out


def test_run_git_line_batch532(tmp_path):
    _board(tmp_path)
    _, out, _ = _run_cli(tmp_path)
    assert ("git_commit=unknown "
            "git_dirty=False") in out


# ---------- 报告落盘 ----------

def test_run_report_written_batch532(tmp_path):
    _board(tmp_path)
    _run_cli(tmp_path)
    rep = tmp_path / "r.json"
    assert rep.is_file()
    d = json.loads(rep.read_text(encoding="utf-8"))
    assert d["report_version"] == "1.1"


def test_run_rc_zero_batch532(tmp_path):
    _board(tmp_path)
    rc, _, err = _run_cli(tmp_path)
    assert rc == 0
    assert err == ""


# ---------- 缺清单 ----------

def test_missing_manifest_rc_two_batch532(
        tmp_path):
    sys.argv = ["evaluation.cli", "run",
                "--manifest",
                str(tmp_path / "nope.json"),
                "--output",
                str(tmp_path / "r.json")]
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main()
    assert rc == 2


def test_missing_manifest_error_line_batch532(
        tmp_path):
    sys.argv = ["evaluation.cli", "run",
                "--manifest",
                str(tmp_path / "nope.json"),
                "--output",
                str(tmp_path / "r.json")]
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        main()
    assert err.getvalue().startswith(
        "[ERROR] 清单不存在:")


def test_missing_manifest_no_report_batch532(
        tmp_path):
    sys.argv = ["evaluation.cli", "run",
                "--manifest",
                str(tmp_path / "nope.json"),
                "--output",
                str(tmp_path / "r.json")]
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        main()
    assert not (tmp_path / "r.json").exists()


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_counts_batch532():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


def test_source_error_lines_batch532():
    src = _src()
    assert "[ERROR] 清单不存在" in src
    assert "评测完成" in src


# ---------- forbidden tokens 第五百九十六批 ----------

def test_source_no_eval_batch532():
    assert "eval(" not in _src()


def test_source_no_exec_batch532():
    assert "exec(" not in _src()


def test_source_no_compile_batch532():
    assert "compile(" not in _src()


def test_source_no_globals_batch532():
    assert "globals(" not in _src()


def test_source_no_locals_batch532():
    assert "locals(" not in _src()


def test_source_no_os_system_batch532():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch532():
    assert "subprocess" not in _src()


def test_source_no_popen_batch532():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch532():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch532():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch532():
    assert "socket" not in _src()


def test_source_no_requests_batch532():
    assert "requests" not in _src()


def test_source_no_urllib_batch532():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch532():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch532():
    assert "yield" not in _src()


def test_source_no_async_await_batch532():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch532():
    assert ".call(" not in _src()


def test_source_open_count_is_1_batch532():
    assert _src().count("open(") == 1
