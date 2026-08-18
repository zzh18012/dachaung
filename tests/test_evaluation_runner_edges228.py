"""evaluation/runner.py 第六百六十三轮 edges 测试（Round 1273）。

补强 edges227 未触及的角度（第六百四十五批，probe 实证）。

新角度（mc32 句包格子 / 贪心回退 / 容差越界）：
- **模 4 对齐格**——469 字长段
  15 界，Word3/7/11 句尾与界
  恰 d 0（每 4 句对齐一格首锁）
- **三锚全中**——P 3/15=0.2 /
  R 1.0 / F1 0.33333333333333337
  （≠ 1/3 浮点误差首锁）
- **四锚加 heading**——P 4/15 /
  R 1.0 / F1 0.4210526315789474
  （≠ 8/19 首锁）
- **贪心回退**——Word3 抢界 108
  (d 0) 后 Word2 (d 7) 回退到界
  80 (d 21) 仍中 → 双双命中非竞争
- **d 32 越界**——Word59 句尾距
  界 518 恰 32 > tol 30 → 全 0.0
- forbidden tokens 第七百三十三批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


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


def _board(tmp_path, anchors):
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()
    (tmp_path / "combo.pdf").write_bytes(_wrap(s))
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "combo.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "combo",
        "chunk_boundary_anchors": [
            {"marker": m, "position": p} for m, p in anchors]}),
        encoding="utf-8")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "combo", "path": "combo.pdf",
                       "source_type": "pdf",
                       "annotation_file": "ann/combo.json"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


def _run(tmp_path, anchors):
    board = _board(tmp_path, anchors)
    return run_evaluation(board, tmp_path / "r.json",
                          parser_name="fallback", max_chars=32)


def _cbf(r):
    m = r["per_doc"][0]["metrics"]
    return (m["chunk_boundary_precision"]["value"],
            m["chunk_boundary_recall"]["value"],
            m["chunk_boundary_f1"]["value"])


# ---------- 格子几何 ----------

def test_stream_550_16_chunks_batch471(tmp_path):
    from app.pipeline import process_single
    p = tmp_path / "g.pdf"
    p.write_bytes(_wrap(
        ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=32)
    assert errors == []
    dd = doc.to_dict()
    assert len(dd["chunks"]) == 16
    assert len(" ".join(c["text"] for c in dd["chunks"])) == 550


def test_mod4_alignment_d0_batch471(tmp_path):
    from app.pipeline import process_single
    p = tmp_path / "g.pdf"
    p.write_bytes(_wrap(
        ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()))
    doc, _ = process_single(p, tmp_path / "o.json",
                            parser_name="fallback", max_chars=32)
    dd = doc.to_dict()
    joined = " ".join(c["text"] for c in dd["chunks"])
    bounds = []
    run = 0
    for c in dd["chunks"][:-1]:
        run += len(c["text"]) + 1
        bounds.append(run - 1)
    for m in ("Word3.", "Word7.", "Word11."):
        end = joined.index(m) + len(m)
        assert min(abs(end - b) for b in bounds) == 0


def test_word59_end_d32_batch471(tmp_path):
    from app.pipeline import process_single
    p = tmp_path / "g.pdf"
    p.write_bytes(_wrap(
        ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()))
    doc, _ = process_single(p, tmp_path / "o.json",
                            parser_name="fallback", max_chars=32)
    dd = doc.to_dict()
    joined = " ".join(c["text"] for c in dd["chunks"])
    bounds = []
    run = 0
    for c in dd["chunks"][:-1]:
        run += len(c["text"]) + 1
        bounds.append(run - 1)
    end = joined.index("Word59.") + len("Word59.")
    assert end == 550
    assert min(abs(end - b) for b in bounds) == 32


# ---------- 单锚 ----------

def test_word3_single_batch471(tmp_path):
    assert _cbf(_run(tmp_path, [("Word3.", "after")])) == (
        1 / 15, 1.0, 0.125)


def test_word1_d14_still_hits_batch471(tmp_path):
    assert _cbf(_run(tmp_path, [("Word1.", "after")])) == (
        1 / 15, 1.0, 0.125)


def test_word59_all_zero_batch471(tmp_path):
    assert _cbf(_run(tmp_path, [("Word59.", "after")])) == (
        0.0, 0.0, 0.0)


# ---------- 多锚 ----------

THREE = ("Word3.", "Word7.", "Word11.")


def test_three_anchors_batch471(tmp_path):
    assert _cbf(_run(tmp_path,
                     [(m, "after") for m in THREE])) == (
        0.2, 1.0, 0.33333333333333337)


def test_three_f1_float_error_batch471(tmp_path):
    r = _run(tmp_path, [(m, "after") for m in THREE])
    f1 = r["per_doc"][0]["metrics"]["chunk_boundary_f1"]["value"]
    assert f1 == 0.33333333333333337
    assert f1 != 1 / 3


def test_four_with_heading_batch471(tmp_path):
    r = _run(tmp_path, [(HEAD, "after")]
             + [(m, "after") for m in THREE])
    assert _cbf(r) == (4 / 15, 1.0, 0.4210526315789474)


def test_four_f1_not_exact_frac_batch471(tmp_path):
    r = _run(tmp_path, [(HEAD, "after")]
             + [(m, "after") for m in THREE])
    f1 = r["per_doc"][0]["metrics"]["chunk_boundary_f1"]["value"]
    assert f1 == 0.4210526315789474
    assert f1 != 8 / 19


# ---------- 贪心回退 ----------

def test_greedy_fallback_both_match_batch471(tmp_path):
    assert _cbf(_run(tmp_path,
                     [("Word2.", "after"),
                      ("Word3.", "after")])) == (
        2 / 15, 1.0, 0.23529411764705882)


def test_greedy_fallback_not_competition_batch471(tmp_path):
    r = _run(tmp_path, [("Word2.", "after"), ("Word3.", "after")])
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_recall"]["value"] == 1.0
    assert m["chunk_boundary_precision"]["value"] == 2 / 15


# ---------- 报告面 ----------

def test_three_aggregates_batch471(tmp_path):
    r = _run(tmp_path, [(m, "after") for m in THREE])
    agg = r["summary"]["ratio_macro_averages"]
    assert agg["chunk_boundary_precision"] == {
        "macro_average": 0.2, "participating_docs": 1,
        "not_evaluated": 0}
    assert agg["chunk_boundary_f1"] == {
        "macro_average": 0.33333333333333337,
        "participating_docs": 1, "not_evaluated": 0}


def test_counts_only_ect_batch471(tmp_path):
    r = _run(tmp_path, [("Word3.", "after")])
    assert list(r["summary"]["counts"].keys()) == [
        "element_count_total"]
    assert r["summary"]["counts"]["element_count_total"] == {
        "sum": 2, "participating_docs": 1}


def test_doc_metrics_shape_batch471(tmp_path):
    r = _run(tmp_path, [("Word3.", "after")])
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "paragraph": 1}, "reason": None}
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}


def test_word59_report_round_trip_batch471(tmp_path):
    r = _run(tmp_path, [("Word59.", "after")])
    assert json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8")) == r


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_lines_batch471():
    src = _src()
    assert "def run_evaluation(" in src
    assert "def _process_one(" in src


# ---------- forbidden tokens 第七百三十三批 ----------

def test_source_no_eval_batch471():
    assert "eval(" not in _src()


def test_source_no_exec_batch471():
    assert "exec(" not in _src()


def test_source_no_compile_batch471():
    assert "compile(" not in _src()


def test_source_no_globals_batch471():
    assert "globals(" not in _src()


def test_source_no_locals_batch471():
    assert "locals(" not in _src()


def test_source_no_os_system_batch471():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch471():
    assert "subprocess" not in _src()


def test_source_no_popen_batch471():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch471():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch471():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch471():
    assert "socket" not in _src()


def test_source_no_requests_batch471():
    assert "requests" not in _src()


def test_source_no_urllib_batch471():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch471():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch471():
    assert "yield" not in _src()


def test_source_no_async_await_batch471():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch471():
    assert _src().count("open(") == 2
