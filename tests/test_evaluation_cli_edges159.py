"""evaluation/cli.py 第六百五十五轮 edges 测试（Round 1246）。

补强 cli edges158 未触及的角度（第六百一十八批，probe 实证）。

新角度（行距阈值对双文档 CLI）：
- **双文档 run**——g30 + g31 单
  清单 → "documents=2（成功 2，
  失败 0）"、per-doc ect 1 / 2
  （阈值对在 CLI 报告并排首锁）
- **summary sum 3**——跨文档
  求和 1+2 / participating 2
- **counts 反差行**——
  "counts:      elements=2
  chunks=1"（元素多于块的
  inspect 行首锁——两行分列
  后顺序合并）
- **stdout devset 行**——
  "file_count=2 groups=2
  pdf=2 docx=0"
- forbidden tokens 第五百八十一批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.cli as cli_mod
from evaluation.cli import main


def _pdf(y2: int) -> bytes:
    s = (("BT /F1 12 Tf 10 700 Td (Top line text here.) Tj ET\n"
          "BT /F1 12 Tf 10 %d Td (Lower line text here.) Tj ET\n"
          % y2).encode())
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
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "g30.pdf").write_bytes(_pdf(670))
    (tmp_path / "samples" / "g31.pdf").write_bytes(_pdf(669))
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "g30", "path": "samples/g30.pdf",
             "source_type": "pdf"},
            {"doc_id": "g31", "path": "samples/g31.pdf",
             "source_type": "pdf"}]}), encoding="utf-8")
    return mf


def _doc(tmp_path):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "g31.pdf", tmp_path / "doc.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    return tmp_path / "doc.json"


def _run_cli(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


# ---------- 双文档 run ----------

def test_cli_run_two_docs_batch444(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    assert rep["per_doc"][0]["metrics"][
        "element_count_total"] == {"value": 1, "reason": None}
    assert rep["per_doc"][1]["metrics"][
        "element_count_total"] == {"value": 2, "reason": None}


def test_cli_run_summary_sum3_batch444(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    assert rep["summary"]["counts"]["element_count_total"] == {
        "sum": 3, "participating_docs": 2}


def test_cli_run_stdout_two_docs_batch444(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    assert "[OK]" in out
    assert "documents=2（成功 2，失败 0）" in out


def test_cli_run_stdout_devset2_batch444(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])
    assert rc == 0
    assert "devset_status=incomplete file_count=2 groups=2 pdf=2 docx=0" \
        in out


def test_cli_validate_report_batch444(tmp_path, capsys):
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

def test_cli_inspect_elements_two_chunks_one_batch444(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "counts:      elements=2 chunks=1" in out


def test_cli_inspect_by_type_para2_batch444(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("element_count_by_type                "
            "paragraph=2  (ok)") in out


def test_cli_inspect_pdf_locator_batch444(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("pdf_locator_valid_ratio              "
            "1.0000  (ok)") in out


def test_cli_inspect_total_two_batch444(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("element_count_total                  "
            "2  (ok)") in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch444():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百八十一批 ----------

def test_source_no_eval_batch444():
    assert "eval(" not in _src()


def test_source_no_exec_batch444():
    assert "exec(" not in _src()


def test_source_no_compile_batch444():
    assert "compile(" not in _src()


def test_source_no_globals_batch444():
    assert "globals(" not in _src()


def test_source_no_locals_batch444():
    assert "locals(" not in _src()


def test_source_no_os_system_batch444():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch444():
    assert "subprocess" not in _src()


def test_source_no_popen_batch444():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch444():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch444():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch444():
    assert "socket" not in _src()


def test_source_no_requests_batch444():
    assert "requests" not in _src()


def test_source_no_urllib_batch444():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch444():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch444():
    assert "yield" not in _src()


def test_source_no_async_await_batch444():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch444():
    assert _src().count("open(") == 1
