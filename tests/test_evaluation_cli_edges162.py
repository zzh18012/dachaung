"""evaluation/cli.py 第六百五十八轮 edges 测试（Round 1262）。

补强 edges161 未触及的角度（第六百三十四批，probe 实证）。

新角度（异类型板 CLI 全链 / 多键 ect 行）：
- **四文档 stdout 行**——
  "documents=4（成功 4，失败 0）" +
  "file_count=4 groups=4 pdf=4
  docx=0"
- **多键 ect 行首锁**——mix 文档
  "element_count_by_type
  caption=1, heading=1, paragraph=1
  (ok)"（逗号连接多类型首锁，
  前史全单键）
- **caption=1 / heading=1 单键行**
  ——分类边界行在 CLI 并排
- **三元素两块行**——"counts:
  elements=3 chunks=2"（caption
  独块在 CLI 可见）
- **hbc 值行 1.0000**——hh80/mix
  "heading_boundary_compliance
  1.0000  (ok)" 与 figcap null 行
  对照
- forbidden tokens 第五百八十四批（open 1）
"""

from __future__ import annotations

import inspect
import json

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


def _one(text: str) -> bytes:
    return _wrap(("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
                  % text).encode())


MIX_TEXTS = ["Figure 1 An overview diagram.", "A" * 80,
             "Is this a heading?"]


def _mix_pdf() -> bytes:
    ys = [700, 660, 620]
    s = "".join("BT /F1 12 Tf 10 %d Td (%s) Tj ET\n" % (y, t)
                for y, t in zip(ys, MIX_TEXTS)).encode()
    return _wrap(s)


def _board(tmp_path):
    (tmp_path / "figcap.pdf").write_bytes(
        _one("Figure 1 An overview diagram."))
    (tmp_path / "hh80.pdf").write_bytes(_one("A" * 80))
    (tmp_path / "qq.pdf").write_bytes(_one("Is this a heading?"))
    (tmp_path / "mix.pdf").write_bytes(_mix_pdf())
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": did, "path": "%s.pdf" % did,
             "source_type": "pdf"}
            for did in ("figcap", "hh80", "qq", "mix")]}),
        encoding="utf-8")
    return mf


def _run_cli(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


def _doc(tmp_path, did):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / (did + ".pdf"), tmp_path / (did + ".json"),
        parser_name="fallback", max_chars=200)
    assert errors == []
    return str(tmp_path / (did + ".json"))


def _run4(capsys, tmp_path):
    mf = _board(tmp_path)
    return _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", "200"])


# ---------- run 四文档 ----------

def test_run_rc_ok_batch460(tmp_path, capsys):
    rc, out = _run4(capsys, tmp_path)
    assert rc == 0
    assert "[OK]" in out


def test_run_stdout_documents_four_batch460(tmp_path, capsys):
    rc, out = _run4(capsys, tmp_path)
    assert rc == 0
    assert "documents=4（成功 4，失败 0）" in out


def test_run_stdout_devset_four_batch460(tmp_path, capsys):
    rc, out = _run4(capsys, tmp_path)
    assert rc == 0
    assert ("devset_status=incomplete file_count=4 groups=4 "
            "pdf=4 docx=0") in out


def test_report_ect_gradient_batch460(tmp_path, capsys):
    rc, _ = _run4(capsys, tmp_path)
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    assert [p["metrics"]["element_count_total"]["value"]
            for p in rep["per_doc"]] == [1, 1, 1, 3]


def test_report_counts_sum_six_batch460(tmp_path, capsys):
    rc, _ = _run4(capsys, tmp_path)
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    assert rep["summary"]["counts"]["element_count_total"] == {
        "sum": 6, "participating_docs": 4}


def test_report_success_four_batch460(tmp_path, capsys):
    rc, _ = _run4(capsys, tmp_path)
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    assert rep["summary"]["success_rates"] == {
        "pipeline_success": {"success_count": 4, "total": 4,
                             "rate": 1.0}}


def test_validate_report_ok_batch460(tmp_path, capsys):
    rc, _ = _run4(capsys, tmp_path)
    assert rc == 0
    rc2, out2 = _run_cli(capsys, [
        "validate-report", str(tmp_path / "r.json")])
    assert rc2 == 0
    assert "[OK]" in out2


# ---------- inspect figcap ----------

def test_inspect_figcap_counts_batch460(tmp_path, capsys):
    rc, out = _run_cli(capsys, ["inspect-doc", _doc(tmp_path,
                                                    "figcap")])
    assert rc == 0
    assert "counts:      elements=1 chunks=1" in out


def test_inspect_figcap_caption_line_batch460(tmp_path, capsys):
    rc, out = _run_cli(capsys, ["inspect-doc", _doc(tmp_path,
                                                    "figcap")])
    assert rc == 0
    assert ("element_count_by_type                caption=1"
            "  (ok)") in out


def test_inspect_figcap_hbc_null_line_batch460(tmp_path, capsys):
    rc, out = _run_cli(capsys, ["inspect-doc", _doc(tmp_path,
                                                    "figcap")])
    assert rc == 0
    assert ("heading_boundary_compliance          null"
            "  (no_heading_elements)") in out


# ---------- inspect hh80 ----------

def test_inspect_hh80_heading_line_batch460(tmp_path, capsys):
    rc, out = _run_cli(capsys, ["inspect-doc", _doc(tmp_path,
                                                    "hh80")])
    assert rc == 0
    assert ("element_count_by_type                heading=1"
            "  (ok)") in out


def test_inspect_hh80_hbc_one_line_batch460(tmp_path, capsys):
    rc, out = _run_cli(capsys, ["inspect-doc", _doc(tmp_path,
                                                    "hh80")])
    assert rc == 0
    assert ("heading_boundary_compliance          1.0000"
            "  (ok)") in out


# ---------- inspect mix ----------

def test_inspect_mix_counts_three_two_batch460(tmp_path, capsys):
    rc, out = _run_cli(capsys, ["inspect-doc", _doc(tmp_path,
                                                    "mix")])
    assert rc == 0
    assert "counts:      elements=3 chunks=2" in out


def test_inspect_mix_by_type_multi_batch460(tmp_path, capsys):
    rc, out = _run_cli(capsys, ["inspect-doc", _doc(tmp_path,
                                                    "mix")])
    assert rc == 0
    assert ("element_count_by_type                caption=1,"
            " heading=1, paragraph=1  (ok)") in out


def test_inspect_mix_hbc_one_line_batch460(tmp_path, capsys):
    rc, out = _run_cli(capsys, ["inspect-doc", _doc(tmp_path,
                                                    "mix")])
    assert rc == 0
    assert ("heading_boundary_compliance          1.0000"
            "  (ok)") in out


def test_inspect_mix_total_three_batch460(tmp_path, capsys):
    rc, out = _run_cli(capsys, ["inspect-doc", _doc(tmp_path,
                                                    "mix")])
    assert rc == 0
    assert "element_count_total                  3  (ok)" in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch460():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百八十四批 ----------

def test_source_no_eval_batch460():
    assert "eval(" not in _src()


def test_source_no_exec_batch460():
    assert "exec(" not in _src()


def test_source_no_compile_batch460():
    assert "compile(" not in _src()


def test_source_no_globals_batch460():
    assert "globals(" not in _src()


def test_source_no_locals_batch460():
    assert "locals(" not in _src()


def test_source_no_os_system_batch460():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch460():
    assert ".call(" not in _src()


def test_source_no_popen_batch460():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch460():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch460():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch460():
    assert "socket" not in _src()


def test_source_no_requests_batch460():
    assert "requests" not in _src()


def test_source_no_urllib_batch460():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch460():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch460():
    assert "yield" not in _src()


def test_source_no_async_await_batch460():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch460():
    assert _src().count("open(") == 1
