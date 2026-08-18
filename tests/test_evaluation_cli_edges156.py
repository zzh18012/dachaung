"""evaluation/cli.py 第六百五十二轮 edges 测试（Round 1232）。

补强 cli edges155 未触及的角度（第六百零四批，probe 实证）。

新角度（mc32 均劈板 CLI 全链 + 锚）：
- **带锚 run**——w07/w23 after 两锚
  → CLI 报告 boundary P 0.5 /
  R 1.0 / F1 2/3（多界锚 CLI 侧
  呈现，区别于直调 run_
  evaluation）
- **报告顶层键全锁**——
  [devset, expected_failures,
  per_doc, provenance,
  report_version, summary]
- **devset 块**——status/
  file_count/content_group_
  count/pdf_count/docx_count/
  categories_covered 六键
- **inspect counts**——
  "counts:      elements=1
  chunks=5"（五块反差档首锁）
- **_tolerance_chars 30 (ok)**
  与 chunk_boundary_f1 null
  (no_annotation) 行
- forbidden tokens 第五百七十八批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.cli as cli_mod
from evaluation.cli import main


def _pdf() -> bytes:
    words = " ".join("w%02d" % i for i in range(40))
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
         % words).encode()
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
    xref_pos = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


def _board(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "u5.pdf").write_bytes(_pdf())
    (tmp_path / "a").mkdir(exist_ok=True)
    (tmp_path / "a" / "a.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "u5",
        "chunk_boundary_anchors": [
            {"marker": "w07", "position": "after"},
            {"marker": "w23", "position": "after"}]}),
        encoding="utf-8")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "u5", "path": "samples/u5.pdf",
                       "source_type": "pdf",
                       "annotation_file": "a/a.json"}]}),
        encoding="utf-8")
    return mf


def _doc(tmp_path):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "u5.pdf", tmp_path / "doc.json",
        parser_name="fallback", max_chars=32)
    assert errors == []
    return tmp_path / "doc.json"


def _run_cli(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


# ---------- 带锚 run ----------

def test_cli_run_anchor_metrics_batch430(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "32"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    m = rep["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


def test_cli_run_report_top_keys_batch430(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "32"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    assert sorted(rep.keys()) == [
        "devset", "expected_failures", "per_doc",
        "provenance", "report_version", "summary"]


def test_cli_run_devset_block_batch430(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "32"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    assert rep["devset"] == {
        "status": "incomplete", "file_count": 1,
        "content_group_count": 1, "pdf_count": 1,
        "docx_count": 0, "categories_covered": []}


def test_cli_run_stdout_summary_batch430(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "32"])
    assert rc == 0
    assert "[OK]" in out
    assert "documents=1（成功 1，失败 0）" in out


def test_cli_run_stdout_devset_line_batch430(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "32"])
    assert rc == 0
    assert "devset_status=incomplete file_count=1 groups=1 pdf=1 docx=0" \
        in out


def test_cli_validate_report_batch430(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "32"])
    assert rc == 0
    rc2, out2 = _run_cli(capsys, [
        "validate-report", str(tmp_path / "r.json")])
    assert rc2 == 0
    assert "[OK]" in out2


# ---------- inspect-doc ----------

def test_cli_inspect_counts_five_batch430(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "counts:      elements=1 chunks=5" in out


def test_cli_inspect_tolerance_line_batch430(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("_tolerance_chars                     "
            "30  (ok)") in out


def test_cli_inspect_boundary_null_batch430(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("chunk_boundary_f1                    "
            "null  (no_annotation)") in out


def test_cli_inspect_multiset_batch430(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("text_char_multiset_precision         "
            "1.0000  (ok)") in out
    assert ("text_char_multiset_recall            "
            "1.0000  (ok)") in out


def test_cli_inspect_total_batch430(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("element_count_total                  "
            "1  (ok)") in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch430():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百七十八批 ----------

def test_source_no_eval_batch430():
    assert "eval(" not in _src()


def test_source_no_exec_batch430():
    assert "exec(" not in _src()


def test_source_no_compile_batch430():
    assert "compile(" not in _src()


def test_source_no_globals_batch430():
    assert "globals(" not in _src()


def test_source_no_locals_batch430():
    assert "locals(" not in _src()


def test_source_no_os_system_batch430():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch430():
    assert "subprocess" not in _src()


def test_source_no_popen_batch430():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch430():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch430():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch430():
    assert "socket" not in _src()


def test_source_no_requests_batch430():
    assert "requests" not in _src()


def test_source_no_urllib_batch430():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch430():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch430():
    assert "yield" not in _src()


def test_source_no_async_await_batch430():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch430():
    assert _src().count("open(") == 1
