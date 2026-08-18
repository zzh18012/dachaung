"""evaluation/runner.py 第六百六十四轮 edges 测试（Round 1279）。

补强 edges228 未触及的角度（第六百五十一批，probe 实证）。

新角度（混合参与板 / 逐档 expectations / silent_drop 求和）：
- **逐档 expectations**——combo
  {heading 1, paragraph 1} →
  sdc 0（精确匹配零漏）；fig
  {caption 2} → sdc 1（欠 1 全
  额计，per-doc 差分首锁）
- **silent_drop_total 求和**——
  0 + 1 = 1（跨档求和首锁）
- **混合参与聚合**——combo 有
  标注参与 cbp 1/15、fig 无标注
  → {participating 1,
  not_evaluated 1}（边界指标
  参与混合首锁）
- **counts 跨档**——
  {sum 3, participating 2}
- forbidden tokens 第七百三十九批（open 2）
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


def _board(tmp_path):
    (tmp_path / "combo.pdf").write_bytes(_wrap(
        ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()))
    (tmp_path / "fig.pdf").write_bytes(_wrap(
        b"BT /F1 12 Tf 10 700 Td "
        b"(Figure 1 An overview diagram.) Tj ET\n"))
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "combo.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "combo",
        "chunk_boundary_anchors": [
            {"marker": "Word3.", "position": "after"}]}),
        encoding="utf-8")
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "combo", "path": "combo.pdf",
             "source_type": "pdf",
             "annotation_file": "ann/combo.json",
             "expectations": {"element_count_by_type": {
                 "heading": 1, "paragraph": 1}}},
            {"doc_id": "fig", "path": "fig.pdf",
             "source_type": "pdf",
             "expectations": {"element_count_by_type": {
                 "caption": 2}}}]}),
        encoding="utf-8")
    return load_manifest(tmp_path / "m.json", project_root=tmp_path)


def _run(tmp_path):
    return run_evaluation(_board(tmp_path), tmp_path / "r.json",
                          parser_name="fallback", max_chars=32)


def _md(r, doc_id):
    return next(d for d in r["per_doc"]
                if d["doc_id"] == doc_id)


# ---------- 逐档 expectations ----------

def test_combo_sdc_zero_batch477(tmp_path):
    r = _run(tmp_path)
    assert _md(r, "combo")["metrics"]["silent_drop_count"] == {
        "value": 0, "reason": None}


def test_fig_sdc_one_batch477(tmp_path):
    r = _run(tmp_path)
    assert _md(r, "fig")["metrics"]["silent_drop_count"] == {
        "value": 1, "reason": None}


def test_sdc_differential_batch477(tmp_path):
    r = _run(tmp_path)
    vals = {d["doc_id"]: d["metrics"]["silent_drop_count"][
        "value"] for d in r["per_doc"]}
    assert vals == {"combo": 0, "fig": 1}


# ---------- silent_drop_total 求和 ----------

def test_silent_drop_total_one_batch477(tmp_path):
    assert _run(tmp_path)["summary"]["silent_drop_total"] == 1


# ---------- 混合参与聚合 ----------

def test_agg_mixed_participation_batch477(tmp_path):
    r = _run(tmp_path)
    agg = r["summary"]["ratio_macro_averages"]
    assert agg["chunk_boundary_precision"] == {
        "macro_average": 1 / 15, "participating_docs": 1,
        "not_evaluated": 1}
    assert agg["chunk_boundary_f1"] == {
        "macro_average": 0.125, "participating_docs": 1,
        "not_evaluated": 1}


def test_fig_cbp_null_batch477(tmp_path):
    r = _run(tmp_path)
    assert _md(r, "fig")["metrics"][
        "chunk_boundary_precision"] == {
        "value": None, "reason": "no_annotation"}


def test_combo_cbp_participating_batch477(tmp_path):
    r = _run(tmp_path)
    assert _md(r, "combo")["metrics"][
        "chunk_boundary_precision"]["value"] == 1 / 15


# ---------- counts 跨档 ----------

def test_counts_sum_three_batch477(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["counts"]["element_count_total"] == {
        "sum": 3, "participating_docs": 2}


def test_doc_order_manifest_batch477(tmp_path):
    r = _run(tmp_path)
    assert [d["doc_id"] for d in r["per_doc"]] == [
        "combo", "fig"]


def test_fig_solo_caption_batch477(tmp_path):
    r = _run(tmp_path)
    m = _md(r, "fig")["metrics"]
    assert m["element_count_by_type"]["value"] == {
        "caption": 1}


# ---------- 报告面 ----------

def test_round_trip_batch477(tmp_path):
    r = _run(tmp_path)
    assert json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8")) == r


def test_expected_failures_empty_batch477(tmp_path):
    assert _run(tmp_path)["expected_failures"] == []


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_counts_batch477():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第七百三十九批 ----------

def test_source_no_eval_batch477():
    assert "eval(" not in _src()


def test_source_no_exec_batch477():
    assert "exec(" not in _src()


def test_source_no_compile_batch477():
    assert "compile(" not in _src()


def test_source_no_globals_batch477():
    assert "globals(" not in _src()


def test_source_no_locals_batch477():
    assert "locals(" not in _src()


def test_source_no_os_system_batch477():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch477():
    assert "subprocess" not in _src()


def test_source_no_popen_batch477():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch477():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch477():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch477():
    assert "socket" not in _src()


def test_source_no_requests_batch477():
    assert "requests" not in _src()


def test_source_no_urllib_batch477():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch477():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch477():
    assert "yield" not in _src()


def test_source_no_async_await_batch477():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch477():
    assert _src().count("open(") == 2
