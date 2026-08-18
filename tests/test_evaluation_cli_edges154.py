"""evaluation/cli.py 第六百五十轮 edges 测试（Round 1220）。

补强 cli edges153 未触及的角度（第五百九十二批，probe 实证）。

新角度（xref 错位自愈板 CLI 全链）：
- **自愈 run**——rc 0、成功 1/1、
  by_type {paragraph: 1}（错位 xref
  经 CLI 照常成功首锁）
- **stdout 汇总**——"documents=1
  （成功 1，失败 0）" + "pdf=1
  docx=0"
- **inspect counts**——"elements=1
  chunks=1"（单元素单块最小档）
- **by_type 行**——"paragraph=1
  (ok)"
- **element_count_total 行**——
  "1  (ok)"
- **ref_intact 行**——"1.0000  (ok)"
- forbidden tokens 第五百七十六批（open 1）
"""

from __future__ import annotations

import inspect
import json

import evaluation.cli as cli_mod
from evaluation.cli import main


def _pdf() -> bytes:
    s = (b"BT /F1 12 Tf 10 700 Td "
         b"(Corrupt xref board text.) Tj ET\n")
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
        out += ("%010d 00000 n \n"
                % (offsets[num] + 7)).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos + 13).encode() + b"\n%%EOF\n")
    return bytes(out)


def _board(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "xr.pdf").write_bytes(_pdf())
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "xr", "path": "samples/xr.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return mf


def _doc(tmp_path):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "xr.pdf", tmp_path / "doc.json",
        parser_name="fallback", max_chars=60)
    assert errors == []
    return tmp_path / "doc.json"


def _run_cli(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


# ---------- 自愈 run ----------

def test_cli_run_recovered_batch418(tmp_path, capsys):
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
        "value": {"paragraph": 1}, "reason": None}
    assert rep["summary"]["success_rates"][
        "pipeline_success"] == {"success_count": 1, "total": 1,
                                "rate": 1.0}


def test_cli_run_recovered_stdout_batch418(tmp_path, capsys):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "60"])
    assert rc == 0
    assert "[OK]" in out
    assert "documents=1（成功 1，失败 0）" in out
    assert "pdf=1 docx=0" in out


def test_cli_validate_report_batch418(tmp_path, capsys):
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

def test_cli_inspect_counts_batch418(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert "counts:      elements=1 chunks=1" in out


def test_cli_inspect_by_type_batch418(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("element_count_by_type                "
            "paragraph=1  (ok)") in out


def test_cli_inspect_total_batch418(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("element_count_total                  "
            "1  (ok)") in out


def test_cli_inspect_ref_intact_batch418(tmp_path, capsys):
    docp = _doc(tmp_path)
    rc, out = _run_cli(capsys, ["inspect-doc", str(docp)])
    assert rc == 0
    assert ("chunk_reference_intact_ratio         "
            "1.0000  (ok)") in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch418():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百七十六批 ----------

def test_source_no_eval_batch418():
    assert "eval(" not in _src()


def test_source_no_exec_batch418():
    assert "exec(" not in _src()


def test_source_no_compile_batch418():
    assert "compile(" not in _src()


def test_source_no_globals_batch418():
    assert "globals(" not in _src()


def test_source_no_locals_batch418():
    assert "locals(" not in _src()


def test_source_no_os_system_batch418():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch418():
    assert "subprocess" not in _src()


def test_source_no_popen_batch418():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch418():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch418():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch418():
    assert "socket" not in _src()


def test_source_no_requests_batch418():
    assert "requests" not in _src()


def test_source_no_urllib_batch418():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch418():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch418():
    assert "yield" not in _src()


def test_source_no_async_await_batch418():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch418():
    assert _src().count("open(") == 1
