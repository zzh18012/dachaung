"""evaluation/cli.py 第六百五十一轮 edges 测试（Round 1227）。

补强 cli edges154 未触及的角度（第五百九十九批，probe 实证）。

新角度（单长行板 CLI 全链）：
- **劈块 run**——rc 0、成功 1/1、
  ect 1（单元素板）
- **stdout 汇总**——"documents=1
  （成功 1，失败 0）"
- **inspect counts**——"elements=1
  chunks=3"（一元素三块最小反差
  档首锁）
- **multiset 双 1.0 行**——
  precision/recall 各 "1.0000
  (ok)"（劈块不丢字符的 CLI 侧
  呈现）
- forbidden tokens 第五百七十七批（open 1）
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
    (tmp_path / "samples" / "ll.pdf").write_bytes(_pdf())
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "ll", "path": "samples/ll.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return mf


def _doc(tmp_path):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "ll.pdf", tmp_path / "doc.json",
        parser_name="fallback", max_chars=60)
    assert errors == []
    return tmp_path / "doc.json"


def _run_cli(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


# ---------- 劈块 run ----------

def test_cli_run_long_line_batch425(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, _ = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "60"])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    m = rep["per_doc"][0]["metrics"]
    assert m["element_count_total"] == {"value": 1,
                                        "reason": None}
    assert rep["summary"]["success_rates"][
        "pipeline_success"] == {"success_count": 1, "total": 1,
                                "rate": 1.0}


def test_cli_run_long_line_stdout_batch425(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "60"])
    assert rc == 0
    assert "[OK]" in out
    assert "documents=1（成功 1，失败 0）" in out


def test_cli_validate_report_batch425(tmp_path, capsys):
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

def test_cli_inspect_counts_batch425(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "counts:      elements=1 chunks=3" in out


def test_cli_inspect_by_type_batch425(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("element_count_by_type                "
            "paragraph=1  (ok)") in out


def test_cli_inspect_multiset_batch425(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("text_char_multiset_precision         "
            "1.0000  (ok)") in out
    assert ("text_char_multiset_recall            "
            "1.0000  (ok)") in out


def test_cli_inspect_total_batch425(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("element_count_total                  "
            "1  (ok)") in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch425():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百七十七批 ----------

def test_source_no_eval_batch425():
    assert "eval(" not in _src()


def test_source_no_exec_batch425():
    assert "exec(" not in _src()


def test_source_no_compile_batch425():
    assert "compile(" not in _src()


def test_source_no_globals_batch425():
    assert "globals(" not in _src()


def test_source_no_locals_batch425():
    assert "locals(" not in _src()


def test_source_no_os_system_batch425():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch425():
    assert "subprocess" not in _src()


def test_source_no_popen_batch425():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch425():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch425():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch425():
    assert "socket" not in _src()


def test_source_no_requests_batch425():
    assert "requests" not in _src()


def test_source_no_urllib_batch425():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch425():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch425():
    assert "yield" not in _src()


def test_source_no_async_await_batch425():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch425():
    assert _src().count("open(") == 1
