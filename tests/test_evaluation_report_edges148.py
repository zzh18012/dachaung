"""evaluation/report.py 第五百七十九轮 edges 测试（Round 1330）。

补强 edges147 未触及的角度（第七百零二批，probe 实证）。

新角度（provenance 值面 / 非 git project_root）：
- **git_commit None**——
  project_root 为
  tmp（非 git）→
  {None, False} 组合
  首锁（不伪造哈希）
- **双版本 '1.1'**——
  evaluator_version
  / report_version
  值级首锁
- **max_chars 回显**
  ——int 32 直传
  （型锁）
- **时间戳可解析**——
  run_timestamp_iso
  过 datetime.
  fromisoformat（含
  时区偏移）
- **版本不对称**——
  dependencies.
  pypdfium2='5.12.1'
  但 parser_version
  串 'pypdfium2=
  unknown'（两个来源
  不对称首锁）
- **parser_version
  精确串**——
  'pdfplumber=0.11.10,
  python-docx=1.2.0,
  pypdfium2=unknown'
- forbidden tokens 第七百七十四批（open 0）
"""

from __future__ import annotations

import inspect
import json
import tempfile
from datetime import datetime
from pathlib import Path

import evaluation.report as report_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from evaluation.schema import validate


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


def _run(tmp_path):
    (tmp_path / "c.pdf").write_bytes(_wrap(ONEP))
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "g1", "path": "c.pdf",
             "source_type": "pdf"}]}),
        encoding="utf-8")
    mf = load_manifest(tmp_path / "m.json",
                       project_root=tmp_path)
    return run_evaluation(mf, tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=32)


def _prov(tmp_path):
    return _run(tmp_path)["provenance"]


# ---------- 非 git project_root ----------

def test_git_commit_none_batch528(tmp_path):
    assert _prov(tmp_path)["git_commit"] is None


def test_git_dirty_false_batch528(tmp_path):
    assert _prov(tmp_path)["git_dirty"] is False


def test_git_dirty_is_bool_batch528(tmp_path):
    assert isinstance(
        _prov(tmp_path)["git_dirty"], bool)


# ---------- 双版本 ----------

def test_evaluator_version_batch528(tmp_path):
    assert _prov(tmp_path)[
        "evaluator_version"] == "1.1"


def test_report_version_batch528(tmp_path):
    assert _prov(tmp_path)[
        "report_version"] == "1.1"


# ---------- max_chars 回显 ----------

def test_max_chars_echo_batch528(tmp_path):
    assert _prov(tmp_path)["max_chars"] == 32


def test_max_chars_is_int_batch528(tmp_path):
    assert isinstance(
        _prov(tmp_path)["max_chars"], int)


def test_parser_name_batch528(tmp_path):
    assert _prov(tmp_path)["parser_name"] \
        == "fallback"


# ---------- 时间戳 ----------

def test_timestamp_parseable_batch528(tmp_path):
    ts = _prov(tmp_path)["run_timestamp_iso"]
    datetime.fromisoformat(ts)


def test_timestamp_shape_batch528(tmp_path):
    ts = _prov(tmp_path)["run_timestamp_iso"]
    assert ts.startswith("20")
    assert "T" in ts


# ---------- 版本不对称 ----------

def test_parser_version_string_batch528(tmp_path):
    assert _prov(tmp_path)["parser_version"] == (
        "pdfplumber=0.11.10,python-docx=1.2.0,"
        "pypdfium2=unknown")


def test_dependencies_pypdfium2_known_batch528(
        tmp_path):
    assert _prov(tmp_path)["dependencies"][
        "pypdfium2"] == "5.12.1"


def test_version_asymmetry_batch528(tmp_path):
    p = _prov(tmp_path)
    assert "pypdfium2=unknown" \
        in p["parser_version"]
    assert p["dependencies"][
        "pypdfium2"] != "unknown"


def test_dependencies_dict_batch528(tmp_path):
    assert _prov(tmp_path)["dependencies"] == {
        "pdfplumber": "0.11.10",
        "python-docx": "1.2.0",
        "pypdfium2": "5.12.1"}


# ---------- 报告合法性 ----------

def test_report_schema_batch528(tmp_path):
    validate(_run(tmp_path),
             "evaluation-report.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch528():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src
    assert "def build_provenance(" in src
    assert "def get_git_provenance(" in src


# ---------- forbidden tokens 第七百七十四批 ----------

def test_source_no_eval_batch528():
    assert "eval(" not in _src()


def test_source_no_exec_batch528():
    assert "exec(" not in _src()


def test_source_no_compile_batch528():
    assert "compile(" not in _src()


def test_source_no_globals_batch528():
    assert "globals(" not in _src()


def test_source_no_locals_batch528():
    assert "locals(" not in _src()


def test_source_no_os_system_batch528():
    assert "os.system" not in _src()


def test_source_subprocess_run_two_batch528():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch528():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch528():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch528():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch528():
    assert "socket" not in _src()


def test_source_no_requests_batch528():
    assert "requests" not in _src()


def test_source_no_urllib_batch528():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch528():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch528():
    assert "yield" not in _src()


def test_source_no_async_await_batch528():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch528():
    assert ".call(" not in _src()


def test_source_open_count_is_0_batch528():
    assert _src().count("open(") == 0
