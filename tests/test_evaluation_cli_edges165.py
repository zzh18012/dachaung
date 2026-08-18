"""evaluation/cli.py 第六百六十一轮 edges 测试（Round 1280）。

补强 edges164 未触及的角度（第六百五十二批，probe 实证）。

新角度（fig 单 caption 板 / inspect 两段式排序迁移）：
- **inspect 两段式排序首锁**——
  ok 值段在前 null 段在后；
  heading_boundary_compliance
  在 combo 板（1.0）居 ok 段、
  在 fig 板（null）迁至 null 段
  figure_caption_* 之后（跨板
  位置迁移首锁）
- **fig 单元素链**——parse
  (elements=1, chunks=1) →
  inspect 'caption=1' 单键行 +
  hbc null (no_heading_elements)
- **--tolerance-chars 0 变体**——
  inspect _tolerance_chars 0 行
- **混合板 run CLI**——
  documents=2（成功 2，失败 0）+
  报告 silent_drop_total 1 +
  validate-report 通关
- forbidden tokens 第五百八十七批（open 1）
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

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


def _fig_pdf(tmp_path):
    p = tmp_path / "fig.pdf"
    p.write_bytes(_wrap(
        b"BT /F1 12 Tf 10 700 Td "
        b"(Figure 1 An overview diagram.) Tj ET\n"))
    return p


def _parse_fig(capsys, tmp_path):
    from app.cli import main as app_main
    doc_json = str(tmp_path / "figdoc.json")
    sys.argv = ["app.cli", "parse", str(_fig_pdf(tmp_path)),
                "-o", doc_json, "--parser", "fallback",
                "--max-chars", "32"]
    rc = app_main()
    return rc, capsys.readouterr().out, doc_json


def _parse_combo(capsys, tmp_path):
    from app.cli import main as app_main
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()
    p = tmp_path / "combo.pdf"
    p.write_bytes(_wrap(s))
    doc_json = str(tmp_path / "combodoc.json")
    sys.argv = ["app.cli", "parse", str(p), "-o", doc_json,
                "--parser", "fallback", "--max-chars", "32"]
    rc = app_main()
    return rc, capsys.readouterr().out, doc_json


def _inspect(capsys, doc_json, *extra):
    sys.argv = ["evaluation.cli", "inspect-doc", doc_json,
                *extra]
    rc = main()
    return rc, capsys.readouterr().out


def _line_index(out, key):
    lines = out.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip().startswith(key):
            return i
    raise AssertionError(key)


# ---------- fig 单元素链 ----------

def test_fig_parse_ok_batch478(capsys, tmp_path):
    rc, out, _ = _parse_fig(capsys, tmp_path)
    assert rc == 0
    assert "(elements=1, chunks=1, warnings=0)" in out


def test_fig_inspect_counts_batch478(capsys, tmp_path):
    _, _, doc_json = _parse_fig(capsys, tmp_path)
    rc, out = _inspect(capsys, doc_json)
    assert rc == 0
    assert "counts:      elements=1 chunks=1" in out


def test_fig_inspect_caption_line_batch478(capsys, tmp_path):
    _, _, doc_json = _parse_fig(capsys, tmp_path)
    _, out = _inspect(capsys, doc_json)
    assert ("  element_count_by_type"
            "                caption=1  (ok)" in out)


def test_fig_inspect_hbc_null_batch478(capsys, tmp_path):
    _, _, doc_json = _parse_fig(capsys, tmp_path)
    _, out = _inspect(capsys, doc_json)
    assert ("  heading_boundary_compliance"
            "          null  (no_heading_elements)"
            in out)


def test_fig_solo_caption_strategy_batch478(capsys, tmp_path):
    _, _, doc_json = _parse_fig(capsys, tmp_path)
    dd = json.loads(Path(doc_json).read_text(encoding="utf-8"))
    assert dd["chunks"][0]["metadata"]["strategy"] == \
        "isolated_caption"
    assert len(dd["elements"][0]["content"]) == 29


# ---------- 两段式排序迁移 ----------

def test_hbc_null_segment_position_batch478(
        capsys, tmp_path):
    _, _, doc_json = _parse_fig(capsys, tmp_path)
    _, out = _inspect(capsys, doc_json)
    assert _line_index(out, "heading_boundary_compliance") \
        > _line_index(out, "figure_caption_f1")


def test_hbc_ok_segment_position_batch478(
        capsys, tmp_path):
    _, _, doc_json = _parse_combo(capsys, tmp_path)
    _, out = _inspect(capsys, doc_json)
    assert _line_index(out, "heading_boundary_compliance") \
        < _line_index(out, "pdf_locator_valid_ratio")


def test_two_segment_null_last_batch478(capsys, tmp_path):
    _, _, doc_json = _parse_fig(capsys, tmp_path)
    _, out = _inspect(capsys, doc_json)
    lines = [ln for ln in out.splitlines()
             if ln.startswith("  ") and ("(ok)" in ln
             or "null  (" in ln)]
    oks = [i for i, ln in enumerate(lines)
           if "(ok)" in ln]
    nulls = [i for i, ln in enumerate(lines)
             if "null  (" in ln]
    assert max(oks) < min(nulls)


# ---------- tolerance 变体 ----------

def test_tolerance_zero_line_batch478(capsys, tmp_path):
    _, _, doc_json = _parse_fig(capsys, tmp_path)
    _, out = _inspect(capsys, doc_json,
                      "--tolerance-chars", "0")
    assert f"  {'_tolerance_chars':36} 0  (ok)" in out


def test_tolerance_default_line_batch478(capsys, tmp_path):
    _, _, doc_json = _parse_fig(capsys, tmp_path)
    _, out = _inspect(capsys, doc_json)
    assert f"  {'_tolerance_chars':36} 30  (ok)" in out


# ---------- 混合板 run CLI ----------

def _mixed_board(tmp_path):
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()
    (tmp_path / "combo.pdf").write_bytes(_wrap(s))
    (tmp_path / "fig2.pdf").write_bytes(_wrap(
        b"BT /F1 12 Tf 10 700 Td "
        b"(Figure 1 An overview diagram.) Tj ET\n"))
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "combo.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "combo",
        "chunk_boundary_anchors": [
            {"marker": "Word3.", "position": "after"}]}),
        encoding="utf-8")
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "combo", "path": "combo.pdf",
             "source_type": "pdf",
             "annotation_file": "ann/combo.json",
             "expectations": {"element_count_by_type": {
                 "heading": 1, "paragraph": 1}}},
            {"doc_id": "fig2", "path": "fig2.pdf",
             "source_type": "pdf",
             "expectations": {"element_count_by_type": {
                 "caption": 2}}}]}),
        encoding="utf-8")
    return str(tmp_path / "m.json")


def test_mixed_run_stdout_batch478(capsys, tmp_path):
    _mixed_board(tmp_path)
    rep = str(tmp_path / "rep.json")
    sys.argv = ["evaluation.cli", "run", "--manifest",
                _mixed_board(tmp_path), "--output", rep,
                "--parser", "fallback", "--max-chars", "32"]
    assert main() == 0
    out = capsys.readouterr().out
    assert "documents=2（成功 2，失败 0）" in out
    assert "file_count=2" in out


def test_mixed_report_sdc_total_batch478(
        capsys, tmp_path):
    _mixed_board(tmp_path)
    rep = str(tmp_path / "rep.json")
    sys.argv = ["evaluation.cli", "run", "--manifest",
                _mixed_board(tmp_path), "--output", rep,
                "--parser", "fallback", "--max-chars", "32"]
    main()
    capsys.readouterr()
    r = json.loads(Path(rep).read_text(encoding="utf-8"))
    assert r["summary"]["silent_drop_total"] == 1


def test_mixed_validate_report_batch478(
        capsys, tmp_path):
    _mixed_board(tmp_path)
    rep = str(tmp_path / "rep.json")
    sys.argv = ["evaluation.cli", "run", "--manifest",
                _mixed_board(tmp_path), "--output", rep,
                "--parser", "fallback", "--max-chars", "32"]
    main()
    capsys.readouterr()
    sys.argv = ["evaluation.cli", "validate-report", rep]
    assert main() == 0


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch478():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百八十七批 ----------

def test_source_no_eval_batch478():
    assert "eval(" not in _src()


def test_source_no_exec_batch478():
    assert "exec(" not in _src()


def test_source_no_compile_batch478():
    assert "compile(" not in _src()


def test_source_no_globals_batch478():
    assert "globals(" not in _src()


def test_source_no_locals_batch478():
    assert "locals(" not in _src()


def test_source_no_os_system_batch478():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch478():
    assert "subprocess" not in _src()


def test_source_no_popen_batch478():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch478():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch478():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch478():
    assert "socket" not in _src()


def test_source_no_requests_batch478():
    assert "requests" not in _src()


def test_source_no_urllib_batch478():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch478():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch478():
    assert "yield" not in _src()


def test_source_no_async_await_batch478():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch478():
    assert ".call(" not in _src()


def test_source_open_count_is_1_batch478():
    assert _src().count("open(") == 1
