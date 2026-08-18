"""evaluation/cli.py 第六百一十轮 edges 测试（Round 1166）。

补强 cli edges143 未触及的角度（第五百三十八批，probe 实证）。

新角度（五型 PDF 板的 CLI 全链）：
- **五型板 run**——caption/paragraph/heading/
  table/image 单页 PDF 经 CLI run → rc 0、报告
  by_type 五键齐（CLI 通道五型首锁）
- **inspect-doc 五型 counts 行**——"counts:
  elements=5 chunks=4"——检视通道五型计数行
- **自产自校**——同报告 validate-report rc 0
- forbidden tokens 第六百三十八批（open 1）
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


def _five_type_pdf() -> bytes:
    s = (b"1 w 0 G\n"
         b"10 180 100 50 re S\n60 180 0 50 re S\n"
         b"10 230 100 0 re S\n"
         b"q 40 0 0 40 200 300 cm /Im0 Do Q\n"
         b"BT /F1 10 Tf 15 205 Td (Ga) Tj ET\n"
         b"BT /F1 10 Tf 65 205 Td (Gb) Tj ET\n"
         b"BT /F1 12 Tf 10 390 Td "
         b"(Figure 3: pdf caption text.) Tj ET\n"
         b"BT /F1 12 Tf 10 330 Td "
         b"(Regular paragraph with a period.) Tj ET")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 400]"
            b"/Resources<</XObject<</Im0 6 0 R>>"
            b"/Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        6: (b"<</Type/XObject/Subtype/Image/Width 1/Height 1"
            b"/ColorSpace/DeviceRGB/BitsPerComponent 8"
            b"/Length 3>>stream\n" + b"\xff\x00\x00"
            + b"\nendstream "),
    }, 7)


def _board(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "t.pdf").write_bytes(
        _five_type_pdf())
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "pf", "path": "samples/t.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return mf


def _run_cli(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


# ---------- 五型板 run ----------

def test_cli_run_five_type_batch364(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    assert rep["per_doc"][0]["metrics"][
        "element_count_by_type"] == {
        "value": {"caption": 1, "paragraph": 1,
                  "heading": 1, "table": 1, "image": 1},
        "reason": None}


def test_cli_run_five_stdout_batch364(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    assert "documents=1（成功 1，失败 0）" in out
    assert "pdf=1 docx=0" in out


# ---------- inspect-doc 五型 counts 行 ----------

def test_cli_inspect_five_counts_batch364(tmp_path, capsys):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "t.pdf", tmp_path / "doc.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    rc, out = _run_cli(capsys, [
        "inspect-doc", str(tmp_path / "doc.json")])
    assert rc == 0
    assert "counts:      elements=5 chunks=4" in out


# ---------- 自产自校 ----------

def test_cli_validate_five_report_batch364(tmp_path, capsys):
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


def test_source_identifier_counts_batch364():
    src = _src()
    assert src.count("argparse") == 4
    assert src.count("add_parser") == 3
    assert src.count("schema") == 4


# ---------- forbidden tokens 第六百三十八批 ----------

def test_source_no_eval_batch364():
    assert "eval(" not in _src()


def test_source_no_exec_batch364():
    assert "exec(" not in _src()


def test_source_no_compile_batch364():
    assert "compile(" not in _src()


def test_source_no_globals_batch364():
    assert "globals(" not in _src()


def test_source_no_locals_batch364():
    assert "locals(" not in _src()


def test_source_no_os_system_batch364():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch364():
    assert "subprocess" not in _src()


def test_source_no_popen_batch364():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch364():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch364():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch364():
    assert "socket" not in _src()


def test_source_no_requests_batch364():
    assert "requests" not in _src()


def test_source_no_urllib_batch364():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch364():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch364():
    assert "yield" not in _src()


def test_source_no_async_await_batch364():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch364():
    assert _src().count("open(") == 1
