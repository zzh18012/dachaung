"""evaluation/cli.py 第六百四十八轮 edges 测试（Round 1212）。

补强 cli edges151 未触及的角度（第五百八十四批，probe 实证）。

新角度（空夹页板 CLI 全链 / 仓外 provenance）：
- **空夹页 run**——3 页中空板经 CLI →
  rc 0、成功 1/1、by_type {paragraph: 2}
- **双锚 macro**——"page" ×2 → macro
  P 0.6667 / R 1.0 / F1 0.8（聚合层
  锚值首锁）
- **仓外 provenance**——manifest 在
  OS temp（无 .git 上溯）→ stdout
  "git_commit=unknown git_dirty=False"
- **inspect counts**——mc60 → 4 块 →
  "counts:      elements=2 chunks=4"
- **by_type 行**——"element_count_
  by_type                paragraph=2  (ok)"
- **locator / ref_intact**——各 1.0000 (ok)
- **null 族**——hbc no_heading_elements、
  silent_drop no_expectations、cb_f1
  no_annotation（inspect-doc 层 null
  渲染首锁）
- forbidden tokens 第五百七十四批（open 1）
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


_R1 = b"BT /F1 12 Tf 10 700 Td (First page with " \
      b"\\(escaped parens\\) here.) Tj ET\n" \
      b"BT /F1 12 Tf 10 680 Td (Second line of page one text.) " \
      b"Tj ET\n"
_R3 = b"BT /F1 12 Tf 10 700 Td (Third page after empty page " \
      b"two.) Tj ET\n" \
      b"BT /F1 12 Tf 10 680 Td (More text on page three " \
      b"follows.) Tj ET\n"


def _pdf() -> bytes:
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 5 0 R 7 0 R]/Count 3>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 9 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(_R1)).encode()
            + b">>stream\n" + _R1 + b"\nendstream "),
        5: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 9 0 R>>>>/Contents 6 0 R>>"),
        6: b"<</Length 0>>stream\n\nendstream ",
        7: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 9 0 R>>>>/Contents 8 0 R>>"),
        8: (b"<</Length " + str(len(_R3)).encode()
            + b">>stream\n" + _R3 + b"\nendstream "),
        9: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 10)


def _board(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "emp.pdf").write_bytes(_pdf())
    (tmp_path / "anns").mkdir(exist_ok=True)
    (tmp_path / "anns" / "a.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "emp",
        "chunk_boundary_anchors": [
            {"marker": "page", "position": "after"},
            {"marker": "page", "position": "after"}]}),
        encoding="utf-8")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "emp", "path": "samples/emp.pdf",
                       "source_type": "pdf",
                       "annotation_file": "anns/a.json"}]}),
        encoding="utf-8")
    return mf


def _doc(tmp_path):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "emp.pdf", tmp_path / "doc.json",
        parser_name="fallback", max_chars=60)
    assert errors == []
    return tmp_path / "doc.json"


def _run_cli(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


# ---------- 空夹页 run ----------

def test_cli_run_empty_middle_batch410(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "60"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    m = rep["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 2}, "reason": None}
    assert rep["summary"]["success_rates"][
        "pipeline_success"] == {"success_count": 1, "total": 1,
                                "rate": 1.0}


def test_cli_run_anchor_macro_batch410(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "60"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    rma = rep["summary"]["ratio_macro_averages"]
    assert rma["chunk_boundary_precision"] == {
        "macro_average": 0.6666666666666666,
        "participating_docs": 1, "not_evaluated": 0}
    assert rma["chunk_boundary_recall"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 0}
    assert rma["chunk_boundary_f1"] == {
        "macro_average": 0.8, "participating_docs": 1,
        "not_evaluated": 0}


def test_cli_run_stdout_batch410(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "60"])
    assert rc == 0
    assert "[OK]" in out
    assert "documents=1（成功 1，失败 0）" in out
    assert "pdf=1 docx=0" in out


def test_cli_run_git_unknown_batch410(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "60"])
    assert rc == 0
    assert "git_commit=unknown" in out
    assert "git_dirty=False" in out


def test_cli_validate_report_batch410(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "60"])
    assert rc == 0
    rc2, out2 = _run_cli(capsys, [
        "validate-report", str(tmp_path / "r.json")])
    assert rc2 == 0
    assert "[OK]" in out2
    assert "通过" in out2


# ---------- inspect-doc ----------

def test_cli_inspect_counts_batch410(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "counts:      elements=2 chunks=4" in out


def test_cli_inspect_by_type_batch410(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("element_count_by_type                "
            "paragraph=2  (ok)") in out


def test_cli_inspect_locator_batch410(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("pdf_locator_valid_ratio              "
            "1.0000  (ok)") in out


def test_cli_inspect_ref_intact_batch410(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("chunk_reference_intact_ratio         "
            "1.0000  (ok)") in out


def test_cli_inspect_hbc_null_batch410(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("heading_boundary_compliance          "
            "null  (no_heading_elements)") in out


def test_cli_inspect_silent_null_batch410(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("silent_drop_count                    "
            "null  (no_expectations)") in out


def test_cli_inspect_cb_no_annotation_batch410(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("chunk_boundary_f1                    "
            "null  (no_annotation)") in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch410():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百七十四批 ----------

def test_source_no_eval_batch410():
    assert "eval(" not in _src()


def test_source_no_exec_batch410():
    assert "exec(" not in _src()


def test_source_no_compile_batch410():
    assert "compile(" not in _src()


def test_source_no_globals_batch410():
    assert "globals(" not in _src()


def test_source_no_locals_batch410():
    assert "locals(" not in _src()


def test_source_no_os_system_batch410():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch410():
    assert "subprocess" not in _src()


def test_source_no_popen_batch410():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch410():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch410():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch410():
    assert "socket" not in _src()


def test_source_no_requests_batch410():
    assert "requests" not in _src()


def test_source_no_urllib_batch410():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch410():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch410():
    assert "yield" not in _src()


def test_source_no_async_await_batch410():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch410():
    assert _src().count("open(") == 1
