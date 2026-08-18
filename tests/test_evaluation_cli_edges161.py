"""evaluation/cli.py 第六百五十七轮 edges 测试（Round 1256）。

补强 edges160 未触及的角度（第六百二十八批，probe 实证）。

新角度（双页板 CLI 全链）：
- **stdout 两文档行**——"documents=2
  （成功 2，失败 0）" + devset
  "file_count=2 groups=2 pdf=2
  docx=0"
- **per-doc ect [2, 4]**——页内合
  并 vs 分列在 CLI 报告并排
- **inspect 四元素反差行**——
  "counts:      elements=4
  chunks=1"（四元素一块首锁）
- **by_type paragraph=4 行**——
  "element_count_by_type
  paragraph=4  (ok)"
- forbidden tokens 第五百八十三批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.cli as cli_mod
from evaluation.cli import main


def _two_page(y2: int) -> bytes:
    s1 = (("BT /F1 12 Tf 10 700 Td (Top line text here.) Tj ET\n"
           "BT /F1 12 Tf 10 %d Td (Lower line text here.) Tj ET\n"
           % y2).encode())
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 6 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        6: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 7 0 R>>"),
        7: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xp = len(out)
    out += b"xref\n0 8\n0000000000 65535 f \n"
    for num in range(1, 8):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 8/Root 1 0 R>>\nstartxref\n"
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


def _board(tmp_path):
    for did, y2 in (("wg30", 670), ("wg31", 669)):
        (tmp_path / (did + ".pdf")).write_bytes(_two_page(y2))
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": did, "path": "%s.pdf" % did,
             "source_type": "pdf"}
            for did in ("wg30", "wg31")]}), encoding="utf-8")
    return mf


def _doc(tmp_path):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "wg31.pdf", tmp_path / "doc.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    return tmp_path / "doc.json"


def _run_cli(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


# ---------- run 两文档 ----------

def test_cli_run_ect_two_four_batch454(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    assert [p["metrics"]["element_count_total"]["value"]
            for p in rep["per_doc"]] == [2, 4]


def test_cli_run_summary_sum6_batch454(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    assert rep["summary"]["counts"]["element_count_total"] == {
        "sum": 6, "participating_docs": 2}


def test_cli_run_stdout_two_docs_batch454(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    assert "[OK]" in out
    assert "documents=2（成功 2，失败 0）" in out


def test_cli_run_stdout_devset_batch454(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    assert ("devset_status=incomplete file_count=2 groups=2 "
            "pdf=2 docx=0") in out


def test_cli_validate_report_batch454(tmp_path, capsys):
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


# ---------- inspect 四元素反差行 ----------

def test_cli_inspect_counts_four_one_batch454(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "counts:      elements=4 chunks=1" in out


def test_cli_inspect_by_type_para4_batch454(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("element_count_by_type                "
            "paragraph=4  (ok)") in out


def test_cli_inspect_total_four_batch454(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("element_count_total                  "
            "4  (ok)") in out


def test_cli_inspect_pdf_locator_batch454(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("pdf_locator_valid_ratio              "
            "1.0000  (ok)") in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch454():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百八十三批 ----------

def test_source_no_eval_batch454():
    assert "eval(" not in _src()


def test_source_no_exec_batch454():
    assert "exec(" not in _src()


def test_source_no_compile_batch454():
    assert "compile(" not in _src()


def test_source_no_globals_batch454():
    assert "globals(" not in _src()


def test_source_no_locals_batch454():
    assert "locals(" not in _src()


def test_source_no_os_system_batch454():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch454():
    assert "subprocess" not in _src()


def test_source_no_popen_batch454():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch454():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch454():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch454():
    assert "socket" not in _src()


def test_source_no_requests_batch454():
    assert "requests" not in _src()


def test_source_no_urllib_batch454():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch454():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch454():
    assert "yield" not in _src()


def test_source_no_async_await_batch454():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch454():
    assert _src().count("open(") == 1
