"""evaluation/cli.py 第六百六十轮 edges 测试（Round 1274）。

补强 edges163 未触及的角度（第六百四十六批，probe 实证）。

新角度（combo 板跨 CLI 链 / inspect-doc 全表）：
- **parse → inspect-doc 链**——
  app.cli parse OK 行
  (elements=2, chunks=16,
  warnings=0) → evaluation.cli
  inspect-doc counts 行
  'elements=2 chunks=16' 跨 CLI
  计数一致首锁
- **inspect-doc 无标注全表**——
  chunk_boundary_* 三键 null
  (no_annotation) 同现
- **多键 ect 序**——
  'heading=1, paragraph=1'
  逗号连接序首锁
- **run 带标注**——Word3 锚 →
  rc 0 + documents=1（成功 1，
  失败 0）+ 报告 cbp 1/15
- **validate-report 通关**——
  combo 报告过 Schema
- forbidden tokens 第五百八十六批（open 1）
"""

from __future__ import annotations

import inspect
import json
import sys

import evaluation.cli as cli_mod
from evaluation.cli import main


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
HEAD = "A" * 80


def _pdf(tmp_path):
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()
    (tmp_path / "combo.pdf").write_bytes(_wrap(s))
    return tmp_path / "combo.pdf"


def _parse(capsys, tmp_path):
    from app.cli import main as app_main
    doc_json = str(tmp_path / "doc.json")
    sys.argv = ["app.cli", "parse", str(_pdf(tmp_path)),
                "-o", doc_json, "--parser", "fallback",
                "--max-chars", "32"]
    rc = app_main()
    out = capsys.readouterr().out
    return rc, out, doc_json


# ---------- parse 链 ----------

def test_parse_rc_ok_batch472(capsys, tmp_path):
    rc, out, _ = _parse(capsys, tmp_path)
    assert rc == 0
    assert "[OK]" in out
    assert "(elements=2, chunks=16, warnings=0)" in out


def test_parse_doc_id_prefix_batch472(capsys, tmp_path):
    _, _, doc_json = _parse(capsys, tmp_path)
    dd = json.loads(
        __import__("pathlib").Path(doc_json).read_text(
            encoding="utf-8"))
    assert dd["document_id"].startswith("doc-")


def test_parse_strategies_batch472(capsys, tmp_path):
    _, _, doc_json = _parse(capsys, tmp_path)
    dd = json.loads(
        __import__("pathlib").Path(doc_json).read_text(
            encoding="utf-8"))
    strategies = [c["metadata"]["strategy"] for c in dd["chunks"]]
    assert strategies[0] == "sequential"
    assert set(strategies[1:]) == {
        "long_paragraph_sentence_split"}


# ---------- inspect-doc 全表 ----------

def test_inspect_counts_line_batch472(capsys, tmp_path):
    _, _, doc_json = _parse(capsys, tmp_path)
    sys.argv = ["evaluation.cli", "inspect-doc", doc_json]
    assert main() == 0
    out = capsys.readouterr().out
    assert "counts:      elements=2 chunks=16" in out


def test_inspect_ecbty_line_batch472(capsys, tmp_path):
    _, _, doc_json = _parse(capsys, tmp_path)
    sys.argv = ["evaluation.cli", "inspect-doc", doc_json]
    main()
    out = capsys.readouterr().out
    assert ("  element_count_by_type"
            "                heading=1, paragraph=1  (ok)"
            in out)


def test_inspect_boundary_null_trio_batch472(capsys, tmp_path):
    _, _, doc_json = _parse(capsys, tmp_path)
    sys.argv = ["evaluation.cli", "inspect-doc", doc_json]
    main()
    out = capsys.readouterr().out
    assert ("  chunk_boundary_f1"
            "                    null  (no_annotation)"
            in out)
    assert ("  chunk_boundary_precision"
            "             null  (no_annotation)" in out)
    assert ("  chunk_boundary_recall"
            "                null  (no_annotation)"
            in out)


def test_inspect_hbc_line_batch472(capsys, tmp_path):
    _, _, doc_json = _parse(capsys, tmp_path)
    sys.argv = ["evaluation.cli", "inspect-doc", doc_json]
    main()
    out = capsys.readouterr().out
    assert ("  heading_boundary_compliance"
            "          1.0000  (ok)" in out)


def test_inspect_image_null_line_batch472(capsys, tmp_path):
    _, _, doc_json = _parse(capsys, tmp_path)
    sys.argv = ["evaluation.cli", "inspect-doc", doc_json]
    main()
    out = capsys.readouterr().out
    assert ("  image_resource_exists_ratio"
            "          null  (no_image_elements)"
            in out)


def test_inspect_tolerance_line_batch472(capsys, tmp_path):
    _, _, doc_json = _parse(capsys, tmp_path)
    sys.argv = ["evaluation.cli", "inspect-doc", doc_json]
    main()
    out = capsys.readouterr().out
    assert f"  {'_tolerance_chars':36} 30  (ok)" in out


def test_inspect_metrics_count_batch472(capsys, tmp_path):
    _, _, doc_json = _parse(capsys, tmp_path)
    sys.argv = ["evaluation.cli", "inspect-doc", doc_json]
    main()
    out = capsys.readouterr().out
    body = [ln for ln in out.splitlines()
            if ln.startswith("  ") and "(ok)" in ln
            or ln.startswith("  ") and "null  (" in ln]
    assert len(body) == 21


# ---------- run 带标注 ----------

def _board(tmp_path):
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "combo.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "combo",
        "chunk_boundary_anchors": [
            {"marker": "Word3.", "position": "after"}]}),
        encoding="utf-8")
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "combo", "path": "combo.pdf",
                       "source_type": "pdf",
                       "annotation_file": "ann/combo.json"}]}),
        encoding="utf-8")
    return str(tmp_path / "m.json")


def test_run_rc_and_summary_batch472(capsys, tmp_path):
    _pdf(tmp_path)
    rep = str(tmp_path / "rep.json")
    sys.argv = ["evaluation.cli", "run", "--manifest",
                _board(tmp_path), "--output", rep,
                "--parser", "fallback", "--max-chars", "32"]
    assert main() == 0
    out = capsys.readouterr().out
    assert "documents=1（成功 1，失败 0）" in out
    assert "devset_status=incomplete file_count=1" in out


def test_run_report_cpb_batch472(capsys, tmp_path):
    _pdf(tmp_path)
    rep = str(tmp_path / "rep.json")
    sys.argv = ["evaluation.cli", "run", "--manifest",
                _board(tmp_path), "--output", rep,
                "--parser", "fallback", "--max-chars", "32"]
    main()
    capsys.readouterr()
    r = json.loads(
        __import__("pathlib").Path(rep).read_text(encoding="utf-8"))
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"]["value"] == 1 / 15
    assert m["chunk_boundary_recall"]["value"] == 1.0
    assert m["chunk_boundary_f1"]["value"] == 0.125


def test_run_report_provenance_batch472(capsys, tmp_path):
    _pdf(tmp_path)
    rep = str(tmp_path / "rep.json")
    sys.argv = ["evaluation.cli", "run", "--manifest",
                _board(tmp_path), "--output", rep,
                "--parser", "fallback", "--max-chars", "32"]
    main()
    capsys.readouterr()
    r = json.loads(
        __import__("pathlib").Path(rep).read_text(encoding="utf-8"))
    assert r["provenance"]["max_chars"] == 32
    assert r["provenance"]["parser_name"] == "fallback"
    assert r["provenance"]["report_version"] == "1.1"


def test_validate_report_pass_batch472(capsys, tmp_path):
    _pdf(tmp_path)
    rep = str(tmp_path / "rep.json")
    sys.argv = ["evaluation.cli", "run", "--manifest",
                _board(tmp_path), "--output", rep,
                "--parser", "fallback", "--max-chars", "32"]
    main()
    capsys.readouterr()
    sys.argv = ["evaluation.cli", "validate-report", rep]
    assert main() == 0
    out = capsys.readouterr().out
    assert "通过 evaluation-report Schema 校验" in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch472():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百八十六批 ----------

def test_source_no_eval_batch472():
    assert "eval(" not in _src()


def test_source_no_exec_batch472():
    assert "exec(" not in _src()


def test_source_no_compile_batch472():
    assert "compile(" not in _src()


def test_source_no_globals_batch472():
    assert "globals(" not in _src()


def test_source_no_locals_batch472():
    assert "locals(" not in _src()


def test_source_no_os_system_batch472():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch472():
    assert "subprocess" not in _src()


def test_source_no_popen_batch472():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch472():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch472():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch472():
    assert "socket" not in _src()


def test_source_no_requests_batch472():
    assert "requests" not in _src()


def test_source_no_urllib_batch472():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch472():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch472():
    assert "yield" not in _src()


def test_source_no_async_await_batch472():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch472():
    assert ".call(" not in _src()


def test_source_open_count_is_1_batch472():
    assert _src().count("open(") == 1
