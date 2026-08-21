"""evaluation/cli.py 第六百七十四轮 edges 测试（Round 1328）。

补强 edges172 未触及的角度（第七百批，probe 实证）。

新角度（1P 无标注 inspect 全景 / validate-report 正路）：
- **counts 行**——
  elements=1 chunks=15
  （1P 板 15 chunks）
- **_tolerance_chars 行**
  ——'  {name:36} 30
  (ok)' 整数渲染首锁
- **cb 三 null**——
  无标注 inspect 重算
  → 三行均
  'null  (no_annotation)'
- **型互斥 null**——
  dlvr
  'null  (not_docx_
  document)'；hbc
  'null  (no_heading_
  elements)'；irer
  'null  (no_image_
  elements)'；sdc
  'null  (no_
  expectations)'
- **ecbt 行**——
  'paragraph=1  (ok)'
- **parser 行**——
  'fallback vpdfplumber
  =0.11.10,python-docx
  =1.2.0,pypdfium2=
  unknown'（pypdfium2
  unknown 首锁）
- **validate-report 正路**
  ——rc 0 +
  '[OK] <path> 通过
  evaluation-report
  Schema 校验'
- forbidden tokens 第五百九十五批（open 1）
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
from app.pipeline import process_single
from evaluation.cli import main
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


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


def _inspect(tmp_path):
    (tmp_path / "c.pdf").write_bytes(_wrap(ONEP))
    doc, errors = process_single(
        tmp_path / "c.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=32)
    assert errors == []
    sys.argv = ["evaluation.cli", "inspect-doc",
                str(tmp_path / "o.json")]
    out = io.StringIO()
    with redirect_stdout(out):
        rc = main()
    return rc, out.getvalue()


# ---------- counts / 头部 ----------

def test_counts_line_batch526(tmp_path):
    _, out = _inspect(tmp_path)
    assert "counts:      elements=1 chunks=15" in out


def test_metrics_header_batch526(tmp_path):
    _, out = _inspect(tmp_path)
    assert "\nmetrics:\n" in out


def test_source_type_line_batch526(tmp_path):
    _, out = _inspect(tmp_path)
    assert "type=pdf" in out


def test_parser_line_batch526(tmp_path):
    _, out = _inspect(tmp_path)
    assert ("parser:      fallback vpdfplumber=0.11.10,"
            "python-docx=1.2.0,"
            "pypdfium2=unknown") in out


# ---------- _tolerance_chars 行 ----------

def test_tolerance_chars_line_batch526(tmp_path):
    _, out = _inspect(tmp_path)
    assert (f"  {'_tolerance_chars':36}"
            " 30  (ok)") in out


# ---------- cb 三 null ----------

def test_cb_trio_no_annotation_batch526(tmp_path):
    _, out = _inspect(tmp_path)
    for name in ("chunk_boundary_f1",
                 "chunk_boundary_precision",
                 "chunk_boundary_recall"):
        assert (f"  {name:36}"
                " null  (no_annotation)") in out


# ---------- 型互斥 null ----------

def test_dlvr_not_docx_batch526(tmp_path):
    _, out = _inspect(tmp_path)
    assert (f"  {'docx_locator_valid_ratio':36}"
            " null  (not_docx_document)") in out


def test_hbc_no_heading_batch526(tmp_path):
    _, out = _inspect(tmp_path)
    assert (f"  {'heading_boundary_compliance':36}"
            " null  (no_heading_elements)") in out


def test_irer_no_images_batch526(tmp_path):
    _, out = _inspect(tmp_path)
    assert (f"  {'image_resource_exists_ratio':36}"
            " null  (no_image_elements)") in out


def test_sdc_no_expectations_batch526(tmp_path):
    _, out = _inspect(tmp_path)
    assert (f"  {'silent_drop_count':36}"
            " null  (no_expectations)") in out


# ---------- ecbt 行 ----------

def test_ecbt_paragraph_only_batch526(tmp_path):
    _, out = _inspect(tmp_path)
    assert (f"  {'element_count_by_type':36}"
            " paragraph=1  (ok)") in out


# ---------- 全绿行 ----------

def test_green_lines_batch526(tmp_path):
    _, out = _inspect(tmp_path)
    assert (f"  {'pipeline_success':36}"
            " true  (ok)") in out
    assert (f"  {'schema_valid':36}"
            " true  (ok)") in out
    assert (f"  {'chunk_reference_intact_ratio':36}"
            " 1.0000  (ok)") in out


def test_rc_zero_batch526(tmp_path):
    rc, _ = _inspect(tmp_path)
    assert rc == 0


# ---------- validate-report 正路 ----------

def _report(tmp_path):
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "g1", "path": "c.pdf",
             "source_type": "pdf"}]}),
        encoding="utf-8")
    mf = load_manifest(tmp_path / "m.json",
                       project_root=tmp_path)
    return run_evaluation(mf, tmp_path / "rep.json",
                          parser_name="fallback",
                          max_chars=32)


def test_validate_report_ok_batch526(tmp_path):
    (tmp_path / "c.pdf").write_bytes(_wrap(ONEP))
    rep = tmp_path / "rep.json"
    _report(tmp_path)
    sys.argv = ["evaluation.cli", "validate-report",
                str(rep)]
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main()
    assert rc == 0
    assert out.getvalue() == (
        "[OK] %s 通过 evaluation-report "
        "Schema 校验\n" % rep.resolve())


def test_validate_report_bad_batch526(tmp_path):
    (tmp_path / "c.pdf").write_bytes(_wrap(ONEP))
    _report(tmp_path)
    rep = tmp_path / "rep.json"
    d = json.loads(rep.read_text(encoding="utf-8"))
    d["report_version"] = "9.9"
    rep.write_text(json.dumps(d), encoding="utf-8")
    sys.argv = ["evaluation.cli", "validate-report",
                str(rep)]
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main()
    assert rc == 1
    assert "[FAIL]" in err.getvalue()
    assert "报告校验失败" in err.getvalue()
    assert ("'1.1' was expected "
            "@ path=['report_version']"
            in err.getvalue())


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_counts_batch526():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


def test_source_ok_line_batch526():
    assert "通过 evaluation-report " \
           "Schema 校验" in _src()


# ---------- forbidden tokens 第五百九十五批 ----------

def test_source_no_eval_batch526():
    assert "eval(" not in _src()


def test_source_no_exec_batch526():
    assert "exec(" not in _src()


def test_source_no_compile_batch526():
    assert "compile(" not in _src()


def test_source_no_globals_batch526():
    assert "globals(" not in _src()


def test_source_no_locals_batch526():
    assert "locals(" not in _src()


def test_source_no_os_system_batch526():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch526():
    assert "subprocess" not in _src()


def test_source_no_popen_batch526():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch526():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch526():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch526():
    assert "socket" not in _src()


def test_source_no_requests_batch526():
    assert "requests" not in _src()


def test_source_no_urllib_batch526():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch526():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch526():
    assert "yield" not in _src()


def test_source_no_async_await_batch526():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch526():
    assert ".call(" not in _src()


def test_source_open_count_is_1_batch526():
    assert _src().count("open(") == 1
