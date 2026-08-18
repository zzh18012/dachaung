"""evaluation/cli.py 第六百六十八轮 edges 测试（Round 1292）。

补强 edges166 未触及的角度（第六百六十四批，probe 实证）。

新角度（mc10000 单块板 CLI 全链）：
- **极宽 mc 合一块**——heading +
  469 字段 → mc 10000 →
  1 块 550 字（跨型合流首锁）
- **单块 + 锚混合三态**——cbp
  {None, no_predicted_
  boundaries} + cbr
  {0.0, None} + cbf {None,
  no_predicted_boundaries}
  （有锚但无预测界 → R 计 0
  而非 null 首锁）
- **聚合劈叉参与**——cbp
  {None, 0, 1} vs cbr
  {0.0, 1, 0} 同报告并存
- **no_annotation 优先**——无
  锚时三态全 no_annotation
  （标注缺席压过块数不足）
- **tol 0 无效**——单块分支
  不读容差
- forbidden tokens 第五百八十九批（open 1）
"""

from __future__ import annotations

import inspect
import json
import sys

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main


@pytest.fixture(autouse=True)
def _restore_argv():
    saved = sys.argv
    yield
    sys.argv = saved


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


def _board(tmp_path, with_ann):
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()
    (tmp_path / "c.pdf").write_bytes(_wrap(s))
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "a.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "combo",
        "chunk_boundary_anchors": [
            {"marker": "Word3.", "position": "after"}]}),
        encoding="utf-8")
    doc = {"doc_id": "combo", "path": "c.pdf",
           "source_type": "pdf"}
    if with_ann:
        doc["annotation_file"] = "ann/a.json"
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [doc]}), encoding="utf-8")
    return str(tmp_path / "m.json")


def _run(tmp_path, capsys, with_ann, extra=()):
    rep = tmp_path / ("r_%s.json" % with_ann)
    sys.argv = ["evaluation.cli", "run", "--manifest",
                _board(tmp_path, with_ann),
                "--output", str(rep), "--parser", "fallback",
                "--max-chars", "10000"] + list(extra)
    rc = main()
    out = capsys.readouterr().out
    return rc, out, json.loads(
        rep.read_text(encoding="utf-8"))


def _trio(report):
    m = report["per_doc"][0]["metrics"]
    return tuple(m[k] for k in (
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1"))


NPB = {"value": None, "reason": "no_predicted_boundaries"}


# ---------- 极宽 mc 合一块 ----------

def test_run_success_one_chunk_batch490(tmp_path, capsys):
    rc, out, _ = _run(tmp_path, capsys, False)
    assert rc == 0
    assert "documents=1（成功 1，失败 0）" in out


def test_parse_single_chunk_550_batch490(tmp_path):
    from pathlib import Path
    from app.cli import main as app_main
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()
    (tmp_path / "c2.pdf").write_bytes(_wrap(s))
    doc_json = str(tmp_path / "d.json")
    sys.argv = ["app.cli", "parse", str(tmp_path / "c2.pdf"),
                "-o", doc_json, "--parser", "fallback",
                "--max-chars", "10000"]
    assert app_main() == 0
    doc = json.loads(
        Path(doc_json).read_text(encoding="utf-8"))
    assert len(doc["chunks"]) == 1
    assert len(doc["chunks"][0]["text"]) == 550


# ---------- 单块 + 锚混合三态 ----------

def test_withann_mixed_trio_batch490(tmp_path, capsys):
    _, _, report = _run(tmp_path, capsys, True)
    assert _trio(report) == (
        NPB, {"value": 0.0, "reason": None}, NPB)


def test_withann_aggregate_split_batch490(tmp_path, capsys):
    _, _, report = _run(tmp_path, capsys, True)
    agg = report["summary"]["ratio_macro_averages"]
    assert agg["chunk_boundary_precision"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 1}
    assert agg["chunk_boundary_recall"] == {
        "macro_average": 0.0, "participating_docs": 1,
        "not_evaluated": 0}


# ---------- no_annotation 优先 ----------

def test_noann_all_no_annotation_batch490(tmp_path, capsys):
    _, _, report = _run(tmp_path, capsys, False)
    noann = {"value": None, "reason": "no_annotation"}
    assert _trio(report) == (noann, noann, noann)


def test_noann_aggregate_both_out_batch490(tmp_path, capsys):
    _, _, report = _run(tmp_path, capsys, False)
    agg = report["summary"]["ratio_macro_averages"]
    assert agg["chunk_boundary_recall"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 1}


# ---------- tol 0 无效 ----------

def test_tol0_same_trio_batch490(tmp_path, capsys):
    _, _, report = _run(tmp_path, capsys, True,
                        extra=("--tolerance-chars", "0"))
    assert _trio(report) == (
        NPB, {"value": 0.0, "reason": None}, NPB)


# ---------- validate-report 往返 ----------

def test_validate_single_chunk_report_batch490(
        tmp_path, capsys):
    _run(tmp_path, capsys, True)
    rep = str(tmp_path / "r_True.json")
    sys.argv = ["evaluation.cli", "validate-report", rep]
    assert main() == 0
    assert "通过 evaluation-report Schema 校验" in \
        capsys.readouterr().out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch490():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百八十九批 ----------

def test_source_no_eval_batch490():
    assert "eval(" not in _src()


def test_source_no_exec_batch490():
    assert "exec(" not in _src()


def test_source_no_compile_batch490():
    assert "compile(" not in _src()


def test_source_no_globals_batch490():
    assert "globals(" not in _src()


def test_source_no_locals_batch490():
    assert "locals(" not in _src()


def test_source_no_os_system_batch490():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch490():
    assert "subprocess" not in _src()


def test_source_no_popen_batch490():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch490():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch490():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch490():
    assert "socket" not in _src()


def test_source_no_requests_batch490():
    assert "requests" not in _src()


def test_source_no_urllib_batch490():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch490():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch490():
    assert "yield" not in _src()


def test_source_no_async_await_batch490():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch490():
    assert ".call(" not in _src()


def test_source_open_count_is_1_batch490():
    assert _src().count("open(") == 1
