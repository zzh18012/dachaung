"""evaluation/cli.py 第六百五十九轮 edges 测试（Round 1268）。

补强 edges162 未触及的角度（第六百四十批，probe 实证）。

新角度（--max-chars 参数化 CLI 链 / 块数行翻转）：
- **cbr 经 CLI 翻转**——同
  manifest+标注，--max-chars 200
  → 报告 cbr 0.5；98 → 1.0
  （CLI 级 mc 参数效应首锁）
- **provenance max_chars 记录**
  ——200 / 98 分别入档
- **inspect 块数行翻转**——
  "counts:      elements=3
  chunks=2"（mc 200）vs
  "elements=3 chunks=3"（mc 98）
- **stdout 双跑同形**——两次 run
  均 [OK] + documents=1
- forbidden tokens 第五百八十五批（open 1）
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


MIX_TEXTS = ["Figure 1 An overview diagram.", "A" * 80,
             "Is this a heading?"]


def _pdf() -> bytes:
    ys = [700, 660, 620]
    return _wrap("".join(
        "BT /F1 12 Tf 10 %d Td (%s) Tj ET\n" % (y, t)
        for y, t in zip(ys, MIX_TEXTS)).encode())


def _board(tmp_path):
    (tmp_path / "mix.pdf").write_bytes(_pdf())
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "mix.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "mix",
        "chunk_boundary_anchors": [
            {"marker": "Figure 1 An overview diagram.",
             "position": "after"},
            {"marker": "A" * 80, "position": "after"}]}),
        encoding="utf-8")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "mix", "path": "mix.pdf",
                       "source_type": "pdf",
                       "annotation_file": "ann/mix.json"}]}),
        encoding="utf-8")
    return mf


def _run_cli(capsys, argv):
    rc = main(argv)
    out = capsys.readouterr().out
    return rc, out


def _run_mc(capsys, tmp_path, mc):
    mf = _board(tmp_path)
    rc, out = _run_cli(capsys, [
        "run", "--manifest", str(mf),
        "--output", str(tmp_path / "r.json"),
        "--parser", "fallback", "--max-chars", str(mc)])
    assert rc == 0
    rep = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))
    return rep, out


def _doc(tmp_path, mc):
    from app.pipeline import process_single
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "mix.pdf", tmp_path / "doc.json",
        parser_name="fallback", max_chars=mc)
    assert errors == []
    return str(tmp_path / "doc.json")


# ---------- cbr 经 CLI 翻转 ----------

def test_run_mc200_cbr_half_batch466(tmp_path, capsys):
    rep, _ = _run_mc(capsys, tmp_path, 200)
    assert rep["per_doc"][0]["metrics"][
        "chunk_boundary_recall"] == {"value": 0.5, "reason": None}


def test_run_mc98_cbr_one_batch466(tmp_path, capsys):
    rep, _ = _run_mc(capsys, tmp_path, 98)
    assert rep["per_doc"][0]["metrics"][
        "chunk_boundary_recall"] == {"value": 1.0, "reason": None}


def test_run_mc200_f1_two_thirds_batch466(tmp_path, capsys):
    rep, _ = _run_mc(capsys, tmp_path, 200)
    assert rep["per_doc"][0]["metrics"]["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


def test_run_mc98_f1_one_batch466(tmp_path, capsys):
    rep, _ = _run_mc(capsys, tmp_path, 98)
    assert rep["per_doc"][0]["metrics"]["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


# ---------- provenance max_chars 记录 ----------

def test_provenance_max_chars_200_batch466(tmp_path, capsys):
    rep, _ = _run_mc(capsys, tmp_path, 200)
    assert rep["provenance"]["max_chars"] == 200


def test_provenance_max_chars_98_batch466(tmp_path, capsys):
    rep, _ = _run_mc(capsys, tmp_path, 98)
    assert rep["provenance"]["max_chars"] == 98


# ---------- stdout 双跑同形 ----------

def test_stdout_both_ok_batch466(tmp_path, capsys):
    for mc in (200, 98):
        rep, out = _run_mc(capsys, tmp_path, mc)
        assert "[OK]" in out
        assert "documents=1（成功 1，失败 0）" in out
        assert ("devset_status=incomplete file_count=1 "
                "groups=1 pdf=1 docx=0") in out


def test_validate_report_both_batch466(tmp_path, capsys):
    for mc in (200, 98):
        _run_mc(capsys, tmp_path, mc)
        rc, out = _run_cli(capsys, [
            "validate-report", str(tmp_path / "r.json")])
        assert rc == 0
        assert "[OK]" in out


# ---------- inspect 块数行翻转 ----------

def test_inspect_mc200_counts_batch466(tmp_path, capsys):
    rc, out = _run_cli(capsys, ["inspect-doc",
                                _doc(tmp_path, 200)])
    assert rc == 0
    assert "counts:      elements=3 chunks=2" in out


def test_inspect_mc98_counts_batch466(tmp_path, capsys):
    rc, out = _run_cli(capsys, ["inspect-doc",
                                _doc(tmp_path, 98)])
    assert rc == 0
    assert "counts:      elements=3 chunks=3" in out


def test_inspect_mc98_by_type_multi_batch466(tmp_path, capsys):
    rc, out = _run_cli(capsys, ["inspect-doc",
                                _doc(tmp_path, 98)])
    assert rc == 0
    assert ("element_count_by_type                caption=1,"
            " heading=1, paragraph=1  (ok)") in out


def test_inspect_mc200_hbc_one_batch466(tmp_path, capsys):
    rc, out = _run_cli(capsys, ["inspect-doc",
                                _doc(tmp_path, 200)])
    assert rc == 0
    assert ("heading_boundary_compliance          1.0000"
            "  (ok)") in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch466():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百八十五批 ----------

def test_source_no_eval_batch466():
    assert "eval(" not in _src()


def test_source_no_exec_batch466():
    assert "exec(" not in _src()


def test_source_no_compile_batch466():
    assert "compile(" not in _src()


def test_source_no_globals_batch466():
    assert "globals(" not in _src()


def test_source_no_locals_batch466():
    assert "locals(" not in _src()


def test_source_no_os_system_batch466():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch466():
    assert ".call(" not in _src()


def test_source_no_popen_batch466():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch466():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch466():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch466():
    assert "socket" not in _src()


def test_source_no_requests_batch466():
    assert "requests" not in _src()


def test_source_no_urllib_batch466():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch466():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch466():
    assert "yield" not in _src()


def test_source_no_async_await_batch466():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch466():
    assert _src().count("open(") == 1
