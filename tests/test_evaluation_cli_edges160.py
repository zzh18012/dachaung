"""evaluation/cli.py 第六百五十六轮 edges 测试（Round 1252）。

补强 edges159 未触及的角度（第六百二十四批，probe 实证）。

新角度（三文档梯度板 CLI 全链）：
- **stdout 三文档行**——"documents=3
  （成功 3，失败 0）" + devset
  "file_count=3 groups=3 pdf=3
  docx=0"
- **per-doc ect [1,3,2]**——行距梯度
  在 CLI 报告并排（三值梯度首锁）
- **summary sum 6**——跨三文档求和
  / participating 3
- **inspect 反差行**——"elements=3
  chunks=1"（三元素一块）
- **inspect null 带因行**——
  "heading_boundary_compliance
  null  (no_heading_elements)" 与
  "chunk_boundary_f1  null
  (no_annotation)"（inspect 层 null
  reason 呈现首锁）
- forbidden tokens 第五百八十二批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.cli as cli_mod
from evaluation.cli import main


def _pdf3(ys) -> bytes:
    parts = []
    for y, txt in zip(ys, ["Alpha first line.", "Beta second line.",
                           "Gamma third line."]):
        parts.append("BT /F1 12 Tf 10 %d Td (%s) Tj ET" % (y, txt))
    s = ("\n".join(parts) + "\n").encode()
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: (b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"),
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


def _board(tmp_path):
    (tmp_path / "s").mkdir(exist_ok=True)
    for did, ys in (("ga", [700, 670, 640]), ("gb", [700, 669, 638]),
                    ("gc", [700, 670, 639])):
        (tmp_path / "s" / (did + ".pdf")).write_bytes(_pdf3(ys))
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": did, "path": "s/%s.pdf" % did,
             "source_type": "pdf"}
            for did in ("ga", "gb", "gc")]}), encoding="utf-8")
    return mf


def _doc(tmp_path):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "s" / "gb.pdf", tmp_path / "doc.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    return tmp_path / "doc.json"


def _run_cli(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


# ---------- run 三文档 ----------

def test_cli_run_three_docs_ect_batch450(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    assert [p["metrics"]["element_count_total"]["value"]
            for p in rep["per_doc"]] == [1, 3, 2]


def test_cli_run_summary_sum6_batch450(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    assert rep["summary"]["counts"]["element_count_total"] == {
        "sum": 6, "participating_docs": 3}


def test_cli_run_stdout_three_docs_batch450(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    assert "[OK]" in out
    assert "documents=3（成功 3，失败 0）" in out


def test_cli_run_stdout_devset3_batch450(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    assert ("devset_status=incomplete file_count=3 groups=3 "
            "pdf=3 docx=0") in out


def test_cli_validate_report_batch450(tmp_path, capsys):
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


# ---------- inspect-doc 反差行 ----------

def test_cli_inspect_counts_three_one_batch450(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "counts:      elements=3 chunks=1" in out


def test_cli_inspect_by_type_para3_batch450(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("element_count_by_type                "
            "paragraph=3  (ok)") in out


def test_cli_inspect_total_three_batch450(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("element_count_total                  "
            "3  (ok)") in out


# ---------- inspect null 带因行 ----------

def test_cli_inspect_hbc_null_reason_batch450(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("heading_boundary_compliance          "
            "null  (no_heading_elements)") in out


def test_cli_inspect_cbf1_null_reason_batch450(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("chunk_boundary_f1                    "
            "null  (no_annotation)") in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch450():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百八十二批 ----------

def test_source_no_eval_batch450():
    assert "eval(" not in _src()


def test_source_no_exec_batch450():
    assert "exec(" not in _src()


def test_source_no_compile_batch450():
    assert "compile(" not in _src()


def test_source_no_globals_batch450():
    assert "globals(" not in _src()


def test_source_no_locals_batch450():
    assert "locals(" not in _src()


def test_source_no_os_system_batch450():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch450():
    assert "subprocess" not in _src()


def test_source_no_popen_batch450():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch450():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch450():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch450():
    assert "socket" not in _src()


def test_source_no_requests_batch450():
    assert "requests" not in _src()


def test_source_no_urllib_batch450():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch450():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch450():
    assert "yield" not in _src()


def test_source_no_async_await_batch450():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch450():
    assert _src().count("open(") == 1
