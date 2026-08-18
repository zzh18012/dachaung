"""evaluation/cli.py 第六百一十九轮 edges 测试（Round 1175）。

补强 cli edges145 未触及的角度（第五百四十七批，probe 实证）。

新角度（跨页流板的 CLI 全链）：
- **跨页流板 run**——两页四段单 PDF 经 CLI run →
  rc 0、by_type {paragraph: 4}（跨页合流经 CLI
  通道首锁）
- **inspect-doc 跨页 counts 行**——"counts:
  elements=4 chunks=1"——4 元素仅 1 块，页界
  不分块的 CLI 可观测
- **自产自校**——同报告 validate-report rc 0
- forbidden tokens 第六百四十七批（open 1）
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


def _two_page_pdf() -> bytes:
    s1 = (b"BT /F1 12 Tf 10 750 Td "
          b"(First page opening line with period.) Tj ET\n"
          b"BT /F1 12 Tf 10 700 Td "
          b"(First page closing line here.) Tj ET\n")
    s2 = (b"BT /F1 12 Tf 10 750 Td "
          b"(Second page continuation text.) Tj ET\n"
          b"BT /F1 12 Tf 10 700 Td "
          b"(Second page final line now.) Tj ET\n")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 5 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 800]"
            b"/Resources<</Font<</F1 7 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
        5: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 800]"
            b"/Resources<</Font<</F1 7 0 R>>>>/Contents 6 0 R>>"),
        6: (b"<</Length " + str(len(s2)).encode()
            + b">>stream\n" + s2 + b"\nendstream "),
        7: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 8)


def _board(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "t.pdf").write_bytes(
        _two_page_pdf())
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "xp", "path": "samples/t.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return mf


def _run_cli(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


# ---------- 跨页流板 run ----------

def test_cli_run_cross_page_batch373(tmp_path, capsys):
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
        "value": {"paragraph": 4}, "reason": None}
    assert rep["per_doc"][0]["metrics"][
        "text_preservation_equal"] == {"value": True,
                                       "reason": None}


def test_cli_run_cross_page_stdout_batch373(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    assert "documents=1（成功 1，失败 0）" in out
    assert "pdf=1 docx=0" in out


# ---------- inspect-doc 跨页 counts 行 ----------

def test_cli_inspect_cross_page_counts_batch373(tmp_path, capsys):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "t.pdf", tmp_path / "doc.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    rc, out = _run_cli(capsys, [
        "inspect-doc", str(tmp_path / "doc.json")])
    assert rc == 0
    assert "counts:      elements=4 chunks=1" in out


# ---------- 自产自校 ----------

def test_cli_validate_cross_page_report_batch373(tmp_path, capsys):
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


def test_source_identifier_counts_batch373():
    src = _src()
    assert src.count("argparse") == 4
    assert src.count("add_parser") == 3
    assert src.count("report") == 14


# ---------- forbidden tokens 第六百四十七批 ----------

def test_source_no_eval_batch373():
    assert "eval(" not in _src()


def test_source_no_exec_batch373():
    assert "exec(" not in _src()


def test_source_no_compile_batch373():
    assert "compile(" not in _src()


def test_source_no_globals_batch373():
    assert "globals(" not in _src()


def test_source_no_locals_batch373():
    assert "locals(" not in _src()


def test_source_no_os_system_batch373():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch373():
    assert "subprocess" not in _src()


def test_source_no_popen_batch373():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch373():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch373():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch373():
    assert "socket" not in _src()


def test_source_no_requests_batch373():
    assert "requests" not in _src()


def test_source_no_urllib_batch373():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch373():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch373():
    assert "yield" not in _src()


def test_source_no_async_await_batch373():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch373():
    assert _src().count("open(") == 1
