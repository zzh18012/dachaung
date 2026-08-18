"""evaluation/cli.py 第六百四十三轮 edges 测试（Round 1199）。

补强 cli edges148 未触及的角度（第五百七十一批，probe 实证）。

新角度（旋转板 CLI 全链）：
- **旋转板 run**——倒序串 "eniL
  detatoR" + 隐形串 + 两页四题经
  CLI → rc 0、by_type {heading: 4}
  （旋转/隐形通道经 CLI 首锁）
- **inspect-doc counts 行**——
  "counts:      elements=4 chunks=4"
- **stdout 汇总**——"documents=1
  （成功 1，失败 0）" + "pdf=1
  docx=0"
- **自产自校** rc 0
- forbidden tokens 第五百七十一批（open 1）
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


def _pdf() -> bytes:
    s1 = (b"BT /F1 12 Tf 0 1 -1 0 100 700 Tm "
          b"(Rotated Line) Tj ET\n"
          b"BT /F1 12 Tf 3 Tr 10 650 Td "
          b"(Invisible Text Here) Tj ET\n"
          b"BT /F1 12 Tf 0 Tr 10 600 Td "
          b"(Normal Line) Tj ET\n")
    s2 = (b"BT /F1 12 Tf 10 700 Td "
          b"(Second Page Line) Tj ET\n")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 5 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 7 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
        5: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 7 0 R>>>>/Contents 6 0 R>>"),
        6: (b"<</Length " + str(len(s2)).encode()
            + b">>stream\n" + s2 + b"\nendstream "),
        7: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 8)


def _board(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "rt.pdf").write_bytes(_pdf())
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "rt", "path": "samples/rt.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return mf


def _doc(tmp_path):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "rt.pdf", tmp_path / "doc.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    return tmp_path / "doc.json"


def _run_cli(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


# ---------- 旋转板 run ----------

def test_cli_run_rotated_batch397(tmp_path, capsys):
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
        "value": {"heading": 4}, "reason": None}
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


def test_cli_run_rotated_stdout_batch397(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    assert "documents=1（成功 1，失败 0）" in out
    assert "pdf=1 docx=0" in out


# ---------- inspect-doc ----------

def test_cli_inspect_rotated_counts_batch397(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "counts:      elements=4 chunks=4" in out


def test_cli_inspect_rotated_bools_batch397(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "pipeline_success                     true  (ok)" in out
    assert "schema_valid                         true  (ok)" in out


def test_cli_inspect_rotated_nulls_batch397(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "null  (no_annotation)" in out
    assert "null  (not_docx_document)" in out
    assert "null  (no_expectations)" in out


# ---------- 自产自校 ----------

def test_cli_validate_rotated_report_batch397(tmp_path, capsys):
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


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch397():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百七十一批 ----------

def test_source_no_eval_batch397():
    assert "eval(" not in _src()


def test_source_no_exec_batch397():
    assert "exec(" not in _src()


def test_source_no_compile_batch397():
    assert "compile(" not in _src()


def test_source_no_globals_batch397():
    assert "globals(" not in _src()


def test_source_no_locals_batch397():
    assert "locals(" not in _src()


def test_source_no_os_system_batch397():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch397():
    assert "subprocess" not in _src()


def test_source_no_popen_batch397():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch397():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch397():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch397():
    assert "socket" not in _src()


def test_source_no_requests_batch397():
    assert "requests" not in _src()


def test_source_no_urllib_batch397():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch397():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch397():
    assert "yield" not in _src()


def test_source_no_async_await_batch397():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch397():
    assert _src().count("open(") == 1
