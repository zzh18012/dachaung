"""evaluation/cli.py 第六百四十六轮 edges 测试（Round 1202）。

补强 cli edges149 未触及的角度（第五百七十四批，probe 实证）。

新角度（max-chars 下界经 CLI / 同位双图检查）：
- **mc31 经 CLI rc 0**——--max-chars 31 触发
  chunker_failed（分块器下界 max_chars ≥
  32），单文档失败是数据不是 CLI 错：
  rc 0 + "documents=1（成功 0，失败
  1）"+ success rate 0.0
- **mc32 下界成功**——--max-chars 32 →
  成功 1 / by_type {paragraph: 2,
  image: 2}
- **失败报告可校验**——validate-report
  对 mc31 报告 [OK] rc 0
- **同位双图 inspect**——counts 行 +
  image_resource_exists_ratio 1.0000 +
  by_type image=2, paragraph=2
- forbidden tokens 第五百七十二批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.cli as cli_mod
from evaluation.cli import main


_PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
        b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
        b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')


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


def _img() -> bytes:
    return (b"<</Type/XObject/Subtype/Image/Width 1/Height 1"
            b"/ColorSpace/DeviceRGB/BitsPerComponent 8/Length "
            + str(len(_PNG)).encode()
            + b">>stream\n" + _PNG + b"\nendstream ")


def _pdf() -> bytes:
    s = (_T("Above the picture text line.", 10, 720)
         + b"q 30 0 0 30 50 650 cm /Im1 Do Q\n"
         + _T("Below the picture text line.", 10, 600)
         + b"q 30 0 0 30 50 650 cm /Im2 Do Q\n")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 7 0 R>>"
            b"/XObject<</Im1 5 0 R/Im2 6 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: _img(),
        6: _img(),
        7: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 8)


def _board(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "ip.pdf").write_bytes(_pdf())
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "ip", "path": "samples/ip.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return mf


def _doc(tmp_path):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "ip.pdf", tmp_path / "doc.json",
        parser_name="fallback", max_chars=50)
    assert errors == []
    return tmp_path / "doc.json"


def _run_cli(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


# ---------- mc31 经 CLI ----------

def test_cli_run_mc31_batch400(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r31.json"),
        "--parser", "fallback", "--max-chars", "31"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r31.json").read_text(encoding="utf-8"))
    m = rep["per_doc"][0]["metrics"]
    assert m["error_code"] == {"value": "chunker_failed",
                               "reason": None}
    assert m["pipeline_success"] == {"value": False,
                                     "reason": None}
    assert rep["summary"]["success_rates"][
        "pipeline_success"] == {"success_count": 0, "total": 1,
                                "rate": 0.0}


def test_cli_run_mc31_stdout_batch400(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r31.json"),
        "--parser", "fallback", "--max-chars", "31"])
    assert rc == 0
    assert "[OK]" in out
    assert "documents=1（成功 0，失败 1）" in out
    assert "pdf=1 docx=0" in out


def test_cli_validate_failure_report_batch400(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r31.json"),
        "--parser", "fallback", "--max-chars", "31"])
    assert rc == 0
    rc2, out2 = _run_cli(capsys, [
        "validate-report", str(tmp_path / "r31.json")])
    assert rc2 == 0
    assert "[OK]" in out2


# ---------- mc32 下界成功 ----------

def test_cli_run_mc32_batch400(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r32.json"),
        "--parser", "fallback", "--max-chars", "32"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r32.json").read_text(encoding="utf-8"))
    m = rep["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 2, "image": 2}, "reason": None}
    assert rep["summary"]["success_rates"][
        "pipeline_success"] == {"success_count": 1, "total": 1,
                                "rate": 1.0}


def test_cli_run_mc32_stdout_batch400(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r32.json"),
        "--parser", "fallback", "--max-chars", "32"])
    assert rc == 0
    assert "documents=1（成功 1，失败 0）" in out


# ---------- inspect-doc 同位双图 ----------

def test_cli_inspect_counts_batch400(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "counts:      elements=4 chunks=2" in out


def test_cli_inspect_image_lines_batch400(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "image_resource_exists_ratio          1.0000  (ok)" in out
    assert ("element_count_by_type                "
            "image=2, paragraph=2  (ok)") in out


def test_cli_inspect_bools_batch400(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "pipeline_success                     true  (ok)" in out
    assert "schema_valid                         true  (ok)" in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch400():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百七十二批 ----------

def test_source_no_eval_batch400():
    assert "eval(" not in _src()


def test_source_no_exec_batch400():
    assert "exec(" not in _src()


def test_source_no_compile_batch400():
    assert "compile(" not in _src()


def test_source_no_globals_batch400():
    assert "globals(" not in _src()


def test_source_no_locals_batch400():
    assert "locals(" not in _src()


def test_source_no_os_system_batch400():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch400():
    assert "subprocess" not in _src()


def test_source_no_popen_batch400():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch400():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch400():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch400():
    assert "socket" not in _src()


def test_source_no_requests_batch400():
    assert "requests" not in _src()


def test_source_no_urllib_batch400():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch400():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch400():
    assert "yield" not in _src()


def test_source_no_async_await_batch400():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch400():
    assert _src().count("open(") == 1
