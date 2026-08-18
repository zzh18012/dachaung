"""evaluation/cli.py 第六百四十七轮 edges 测试（Round 1206）。

补强 cli edges150 未触及的角度（第五百七十八批，probe 实证）。

新角度（并排双表板 CLI 全链）：
- **双表 run**——并排格网板经 CLI →
  rc 0、by_type {heading: 1, table: 2}
  （并排表通道经 CLI 首锁）
- **stdout 汇总**——"documents=1
  （成功 1，失败 0）" + "pdf=1 docx=0"
- **inspect counts**——"counts:
  elements=3 chunks=3"
- **by_type 行**——"element_count_
  by_type                heading=1,
  table=2  (ok)"
- **hbc 行**——"heading_boundary_
  compliance          1.0000  (ok)"
- **自产自校** rc 0
- forbidden tokens 第五百七十三批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.cli as cli_mod
from evaluation.cli import main


def _build_pdf(objects, n_obj) -> bytes:
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objects[num] + b"endobj\n")
    xref_pos = len(out)
    out += b"xref\n0 " + str(n_obj).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for num in range(1, n_obj):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size " + str(n_obj).encode()
            + b"/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


def _T(text, x, y) -> bytes:
    return ("BT /F1 12 Tf %d %d Td (%s) Tj ET\n"
            % (x, y, text)).encode()


def _pdf() -> bytes:
    s = (b"1 w 0 G\n"
         + b"10 300 100 60 re S\n" + b"60 300 0 60 re S\n"
         + b"10 330 100 0 re S\n"
         + b"200 300 100 60 re S\n" + b"250 300 0 60 re S\n"
         + b"200 330 100 0 re S\n"
         + _T("LA", 15, 340) + _T("LB", 65, 340)
         + _T("LC", 15, 310) + _T("LD", 65, 310)
         + _T("RA", 205, 340) + _T("RB", 255, 340)
         + _T("RC", 205, 310) + _T("RD", 255, 310))
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 6)


def _board(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "sb.pdf").write_bytes(_pdf())
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "sb", "path": "samples/sb.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return mf


def _doc(tmp_path):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "sb.pdf", tmp_path / "doc.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    return tmp_path / "doc.json"


def _run_cli(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


# ---------- 双表 run ----------

def test_cli_run_side_batch404(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    m = rep["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "table": 2}, "reason": None}
    assert rep["summary"]["success_rates"][
        "pipeline_success"] == {"success_count": 1, "total": 1,
                                "rate": 1.0}


def test_cli_run_side_stdout_batch404(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    assert "[OK]" in out
    assert "documents=1（成功 1，失败 0）" in out
    assert "pdf=1 docx=0" in out


def test_cli_validate_side_report_batch404(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    rc2, out2 = _run_cli(capsys, [
        "validate-report", str(tmp_path / "r.json")])
    assert rc2 == 0
    assert "[OK]" in out2
    assert "通过" in out2


# ---------- inspect-doc ----------

def test_cli_inspect_side_counts_batch404(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "counts:      elements=3 chunks=3" in out


def test_cli_inspect_side_by_type_batch404(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("element_count_by_type                "
            "heading=1, table=2  (ok)") in out


def test_cli_inspect_side_hbc_batch404(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("heading_boundary_compliance          "
            "1.0000  (ok)") in out


def test_cli_inspect_side_bools_batch404(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "pipeline_success                     true  (ok)" in out
    assert "schema_valid                         true  (ok)" in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch404():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百七十三批 ----------

def test_source_no_eval_batch404():
    assert "eval(" not in _src()


def test_source_no_exec_batch404():
    assert "exec(" not in _src()


def test_source_no_compile_batch404():
    assert "compile(" not in _src()


def test_source_no_globals_batch404():
    assert "globals(" not in _src()


def test_source_no_locals_batch404():
    assert "locals(" not in _src()


def test_source_no_os_system_batch404():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch404():
    assert "subprocess" not in _src()


def test_source_no_popen_batch404():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch404():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch404():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch404():
    assert "socket" not in _src()


def test_source_no_requests_batch404():
    assert "requests" not in _src()


def test_source_no_urllib_batch404():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch404():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch404():
    assert "yield" not in _src()


def test_source_no_async_await_batch404():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch404():
    assert _src().count("open(") == 1
