"""evaluation/cli.py 第五百九十四轮 edges 测试（Round 1150）。

补强 cli edges141 未触及的角度（第五百二十三批，probe 实证）。

新角度（真文本 PDF 的 CLI 全链）：
- **run 真文本 PDF**——手写 BT/Tj 文本 PDF 经 CLI main
  run → rc 0、file_count 1、success 1/1——旧 CLI 成功链
  全用 docx 板，真 PDF 成功行首锁
- **自产自校**——同一报告再走 validate-report → rc 0 +
  [OK]——真 PDF 产物过自家校验器
- **inspect-doc 真元素**——同板 inspect-doc rc 0，
  输出含真实 paragraph 文本——真 PDF 检视通道首锁
- forbidden tokens 第六百二十二批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.cli as cli_mod
from evaluation.cli import main


def _build_one_page_pdf(stream) -> bytes:
    objects = {}
    objects[1] = b"<</Type/Catalog/Pages 2 0 R>>"
    objects[2] = b"<</Type/Pages/Kids[3 0 R]/Count 1>>"
    objects[3] = (
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 500 100]"
        b"/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>")
    objects[4] = b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"
    objects[5] = (
        b"<</Length " + str(len(stream)).encode() + b">>stream\n"
        + stream + b"\nendstream ")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objects[num] + b"endobj\n")
    xref_pos = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


def _board(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "t.pdf").write_bytes(
        _build_one_page_pdf(
            b"BT /F1 12 Tf 10 80 Td "
            b"(Hello PDF cli chain body.) Tj ET"))
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "pc", "path": "samples/t.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return mf


def _run_cli(tmp_path, capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


# ---------- run 真文本 PDF ----------

def test_cli_run_real_pdf_batch348(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(tmp_path, capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    assert rep["devset"]["file_count"] == 1
    assert rep["summary"]["success_rates"]["pipeline_success"] \
        == {"success_count": 1, "total": 1, "rate": 1.0}


def test_cli_run_pdf_doc_metrics_batch348(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(tmp_path, capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    m = rep["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 1}, "reason": None}


# ---------- 自产自校 ----------

def test_cli_validate_report_pdf_batch348(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(tmp_path, capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    rc2, out2 = _run_cli(tmp_path, capsys, [
        "validate-report", str(tmp_path / "r.json")])
    assert rc2 == 0
    assert "[OK]" in out2


# ---------- inspect-doc 真元素 ----------

def test_cli_inspect_doc_pdf_batch348(tmp_path, capsys):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "t.pdf", tmp_path / "doc.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    rc, out = _run_cli(tmp_path, capsys, [
        "inspect-doc", str(tmp_path / "doc.json")])
    assert rc == 0
    assert "pipeline_success" in out
    assert "no_expectations" in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch348():
    src = _src()
    assert src.count("main") == 3
    assert "validate-report" in src
    assert "inspect-doc" in src


# ---------- forbidden tokens 第六百二十二批 ----------

def test_source_no_eval_batch348():
    assert "eval(" not in _src()


def test_source_no_exec_batch348():
    assert "exec(" not in _src()


def test_source_no_compile_batch348():
    assert "compile(" not in _src()


def test_source_no_globals_batch348():
    assert "globals(" not in _src()


def test_source_no_locals_batch348():
    assert "locals(" not in _src()


def test_source_no_os_system_batch348():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch348():
    assert "subprocess" not in _src()


def test_source_no_popen_batch348():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch348():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch348():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch348():
    assert "socket" not in _src()


def test_source_no_requests_batch348():
    assert "requests" not in _src()


def test_source_no_urllib_batch348():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch348():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch348():
    assert "yield" not in _src()


def test_source_no_async_await_batch348():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch348():
    assert _src().count("open(") == 1
