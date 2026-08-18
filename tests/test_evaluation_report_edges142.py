"""evaluation/report.py 第五百七十三轮 edges 测试（Round 1294）。

补强 edges141 未触及的角度（第六百六十六批，probe 实证）。

新角度（mc 崩变面 15 路 / 聚合劈叉差分）：
- **崩变差分**——同标注板
  mc32 vs mc10000 全树
  对比 → 恰 15 条叶路径：
  cbp value+reason / cbr
  value（reason 同 None 不
  变）/ cbf value+reason /
  wall_time / max_chars /
  时间戳 / 聚合 cbp 三键 +
  cbf 三键 + cbr 仅
  macro_average（edges141
  3 路不变面的崩变侧首锁）
- **聚合劈叉差分**——cbr
  participating 两 mc 均 1
  （macro 1.0 ↔ 0.0）而
  cbp 0↔1 翻转（劈叉在差分
  下的形态首锁）
- **计数面恒等**——counts/
  success 跨 mc 不变（单块
  化不动元素计数）
- forbidden tokens 第七百五十二批（open 0）
"""

from __future__ import annotations

import inspect
import json

import evaluation.report as report_mod
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
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "combo", "path": "c.pdf",
                       "source_type": "pdf",
                       "annotation_file": "ann/a.json"}]}),
        encoding="utf-8")
    return load_manifest((tmp_path / "m.json"),
                         project_root=tmp_path)


def _runs(tmp_path):
    mf = _board(tmp_path)
    r32 = run_evaluation(mf, tmp_path / "r32.json",
                         parser_name="fallback", max_chars=32)
    r10k = run_evaluation(mf, tmp_path / "r10k.json",
                          parser_name="fallback",
                          max_chars=10000)
    return r32, r10k


def _diff_paths(a, b):
    diffs = set()

    def walk(x, y, path):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in set(x) | set(y):
                walk(x.get(k), y.get(k), path + [k])
        elif isinstance(x, list) and isinstance(y, list):
            for i in range(max(len(x), len(y))):
                walk(x[i] if i < len(x) else None,
                     y[i] if i < len(y) else None, path + [i])
        elif x != y:
            diffs.add(tuple(path))

    walk(a, b, [])
    return diffs


BREAK_DIFF = {
    ("per_doc", 0, "metrics", "chunk_boundary_f1",
     "reason"),
    ("per_doc", 0, "metrics", "chunk_boundary_f1",
     "value"),
    ("per_doc", 0, "metrics", "chunk_boundary_precision",
     "reason"),
    ("per_doc", 0, "metrics", "chunk_boundary_precision",
     "value"),
    ("per_doc", 0, "metrics", "chunk_boundary_recall",
     "value"),
    ("per_doc", 0, "wall_time_seconds", "total"),
    ("provenance", "max_chars"),
    ("provenance", "run_timestamp_iso"),
    ("summary", "ratio_macro_averages",
     "chunk_boundary_f1", "macro_average"),
    ("summary", "ratio_macro_averages",
     "chunk_boundary_f1", "not_evaluated"),
    ("summary", "ratio_macro_averages",
     "chunk_boundary_f1", "participating_docs"),
    ("summary", "ratio_macro_averages",
     "chunk_boundary_precision", "macro_average"),
    ("summary", "ratio_macro_averages",
     "chunk_boundary_precision", "not_evaluated"),
    ("summary", "ratio_macro_averages",
     "chunk_boundary_precision",
     "participating_docs"),
    ("summary", "ratio_macro_averages",
     "chunk_boundary_recall", "macro_average")}


# ---------- 崩变面 15 路 ----------

def test_break_diff_set_exact_batch492(tmp_path):
    r32, r10k = _runs(tmp_path)
    assert _diff_paths(r32, r10k) == BREAK_DIFF


def test_break_diff_size_15_batch492(tmp_path):
    r32, r10k = _runs(tmp_path)
    assert len(_diff_paths(r32, r10k)) == 15


def test_break_diff_excludes_batch492(tmp_path):
    r32, r10k = _runs(tmp_path)
    d = _diff_paths(r32, r10k)
    assert ("per_doc", 0, "metrics",
            "chunk_boundary_recall", "reason") not in d
    assert ("per_doc", 0, "metrics",
            "element_count_total", "value") not in d
    assert ("summary", "success_rates") not in d


# ---------- 崩变两侧值 ----------

def test_mc32_hit_face_batch492(tmp_path):
    r32, _ = _runs(tmp_path)
    m = r32["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1 / 15, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}


def test_mc10k_single_chunk_face_batch492(tmp_path):
    _, r10k = _runs(tmp_path)
    m = r10k["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": None,
        "reason": "no_predicted_boundaries"}
    assert m["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": None,
        "reason": "no_predicted_boundaries"}


# ---------- 聚合劈叉差分 ----------

def test_agg_cbp_flip_batch492(tmp_path):
    r32, r10k = _runs(tmp_path)
    assert r32["summary"]["ratio_macro_averages"][
        "chunk_boundary_precision"] == {
        "macro_average": 1 / 15, "participating_docs": 1,
        "not_evaluated": 0}
    assert r10k["summary"]["ratio_macro_averages"][
        "chunk_boundary_precision"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 1}


def test_agg_cbr_participating_both_batch492(tmp_path):
    r32, r10k = _runs(tmp_path)
    a32 = r32["summary"]["ratio_macro_averages"][
        "chunk_boundary_recall"]
    a10 = r10k["summary"]["ratio_macro_averages"][
        "chunk_boundary_recall"]
    assert a32["participating_docs"] == \
        a10["participating_docs"] == 1
    assert a32["not_evaluated"] == a10["not_evaluated"] == 0
    assert a32["macro_average"] == 1.0
    assert a10["macro_average"] == 0.0


def test_agg_cbf_flip_batch492(tmp_path):
    r32, r10k = _runs(tmp_path)
    assert r10k["summary"]["ratio_macro_averages"][
        "chunk_boundary_f1"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 1}


# ---------- 计数面恒等 ----------

def test_counts_success_invariant_batch492(tmp_path):
    r32, r10k = _runs(tmp_path)
    assert r32["summary"]["counts"] == \
        r10k["summary"]["counts"]
    assert r32["summary"]["success_rates"] == \
        r10k["summary"]["success_rates"]


def test_max_chars_prov_batch492(tmp_path):
    r32, r10k = _runs(tmp_path)
    assert r32["provenance"]["max_chars"] == 32
    assert r10k["provenance"]["max_chars"] == 10000


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch492():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src


# ---------- forbidden tokens 第七百五十二批 ----------

def test_source_no_eval_batch492():
    assert "eval(" not in _src()


def test_source_no_exec_batch492():
    assert "exec(" not in _src()


def test_source_no_compile_batch492():
    assert "compile(" not in _src()


def test_source_no_globals_batch492():
    assert "globals(" not in _src()


def test_source_no_locals_batch492():
    assert "locals(" not in _src()


def test_source_no_os_system_batch492():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch492():
    assert ".call(" not in _src()


def test_source_no_popen_batch492():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch492():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch492():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch492():
    assert "socket" not in _src()


def test_source_no_requests_batch492():
    assert "requests" not in _src()


def test_source_no_urllib_batch492():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch492():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch492():
    assert "yield" not in _src()


def test_source_no_async_await_batch492():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch492():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch492():
    assert _src().count("subprocess.run") == 2
