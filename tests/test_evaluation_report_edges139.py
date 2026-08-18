"""evaluation/report.py 第五百七十轮 edges 测试（Round 1276）。

补强 edges138 未触及的角度（第六百四十八批，probe 实证）。

新角度（标注存在性差分 / 聚合参与翻转 / mc 翻转）：
- **标注差分路径集首锁**——同
  manifest 同 mc32，有无标注文件
  两跑全树对比 → 恰 17 条叶路径
  不同：cbp/cbr/cbf per-doc
  value+reason 六条 + 聚合三键
  ×三 metric 九条 + wall_time +
  timestamp（其余全同首锁）
- **聚合参与翻转**——无标注 →
  {macro None, participating 0,
  not_evaluated 1} ↔ 有标注 →
  {macro 1/15, participating 1,
  not_evaluated 0}
- **mc 翻转同标注**——Word3 锚
  mc32 → P 1/15 vs mc100 →
  P 1/5（界数 15 → 5，精度随
  分母翻首锁）
- forbidden tokens 第七百三十六批（open 0）
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


def _pdf(tmp_path):
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()
    (tmp_path / "combo.pdf").write_bytes(_wrap(s))


def _board_ann(tmp_path):
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "combo.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "combo",
        "chunk_boundary_anchors": [
            {"marker": "Word3.", "position": "after"}]}),
        encoding="utf-8")
    (tmp_path / "m_ann.json").write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "combo", "path": "combo.pdf",
                       "source_type": "pdf",
                       "annotation_file": "ann/combo.json"}]}),
        encoding="utf-8")
    return load_manifest(tmp_path / "m_ann.json",
                         project_root=tmp_path)


def _board_noann(tmp_path):
    (tmp_path / "m_noann.json").write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "combo", "path": "combo.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(tmp_path / "m_noann.json",
                         project_root=tmp_path)


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


ANN_DIFF = set()
for _m in ("chunk_boundary_precision",
           "chunk_boundary_recall", "chunk_boundary_f1"):
    ANN_DIFF.add(("per_doc", 0, "metrics", _m, "value"))
    ANN_DIFF.add(("per_doc", 0, "metrics", _m, "reason"))
    ANN_DIFF.add(("summary", "ratio_macro_averages", _m,
                  "macro_average"))
    ANN_DIFF.add(("summary", "ratio_macro_averages", _m,
                  "participating_docs"))
    ANN_DIFF.add(("summary", "ratio_macro_averages", _m,
                  "not_evaluated"))
ANN_DIFF.add(("per_doc", 0, "wall_time_seconds", "total"))
ANN_DIFF.add(("provenance", "run_timestamp_iso"))


# ---------- 标注差分路径集 ----------

def test_ann_diff_set_exact_batch474(tmp_path):
    _pdf(tmp_path)
    r_ann = run_evaluation(_board_ann(tmp_path),
                           tmp_path / "ra.json",
                           parser_name="fallback", max_chars=32)
    r_no = run_evaluation(_board_noann(tmp_path),
                          tmp_path / "rn.json",
                          parser_name="fallback", max_chars=32)
    assert _diff_paths(r_ann, r_no) == ANN_DIFF


def test_ann_diff_set_size_batch474(tmp_path):
    _pdf(tmp_path)
    r_ann = run_evaluation(_board_ann(tmp_path),
                           tmp_path / "ra.json",
                           parser_name="fallback", max_chars=32)
    r_no = run_evaluation(_board_noann(tmp_path),
                          tmp_path / "rn.json",
                          parser_name="fallback", max_chars=32)
    assert len(_diff_paths(r_ann, r_no)) == 17


def test_ann_diff_excludes_others_batch474(tmp_path):
    _pdf(tmp_path)
    r_ann = run_evaluation(_board_ann(tmp_path),
                           tmp_path / "ra.json",
                           parser_name="fallback", max_chars=32)
    r_no = run_evaluation(_board_noann(tmp_path),
                          tmp_path / "rn.json",
                          parser_name="fallback", max_chars=32)
    diffs = _diff_paths(r_ann, r_no)
    assert ("devset", "file_count") not in diffs
    assert ("per_doc", 0, "source_type") not in diffs
    assert ("per_doc", 0, "metrics", "element_count_total",
            "value") not in diffs
    assert ("per_doc", 0, "metrics",
            "heading_boundary_compliance", "value") not in diffs


# ---------- 聚合参与翻转 ----------

def test_noann_metrics_null_batch474(tmp_path):
    _pdf(tmp_path)
    r = run_evaluation(_board_noann(tmp_path),
                       tmp_path / "rn.json",
                       parser_name="fallback", max_chars=32)
    m = r["per_doc"][0]["metrics"]
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall", "chunk_boundary_f1"):
        assert m[k] == {"value": None,
                        "reason": "no_annotation"}


def test_noann_aggregate_flip_batch474(tmp_path):
    _pdf(tmp_path)
    r = run_evaluation(_board_noann(tmp_path),
                       tmp_path / "rn.json",
                       parser_name="fallback", max_chars=32)
    agg = r["summary"]["ratio_macro_averages"]
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall", "chunk_boundary_f1"):
        assert agg[k] == {"macro_average": None,
                          "participating_docs": 0,
                          "not_evaluated": 1}


def test_ann_aggregate_participating_batch474(tmp_path):
    _pdf(tmp_path)
    r = run_evaluation(_board_ann(tmp_path),
                       tmp_path / "ra.json",
                       parser_name="fallback", max_chars=32)
    agg = r["summary"]["ratio_macro_averages"]
    assert agg["chunk_boundary_precision"] == {
        "macro_average": 1 / 15, "participating_docs": 1,
        "not_evaluated": 0}
    assert agg["chunk_boundary_f1"] == {
        "macro_average": 0.125, "participating_docs": 1,
        "not_evaluated": 0}


# ---------- mc 翻转同标注 ----------

def test_mc100_cbp_one_fifth_batch474(tmp_path):
    _pdf(tmp_path)
    r = run_evaluation(_board_ann(tmp_path),
                       tmp_path / "r100.json",
                       parser_name="fallback", max_chars=100)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"]["value"] == 0.2
    assert m["chunk_boundary_recall"]["value"] == 1.0
    assert m["chunk_boundary_f1"]["value"] == \
        0.33333333333333337


def test_mc_precision_flip_ratio_batch474(tmp_path):
    _pdf(tmp_path)
    r32 = run_evaluation(_board_ann(tmp_path),
                         tmp_path / "r32.json",
                         parser_name="fallback", max_chars=32)
    r100 = run_evaluation(_board_ann(tmp_path),
                          tmp_path / "r100.json",
                          parser_name="fallback", max_chars=100)
    p32 = r32["per_doc"][0]["metrics"][
        "chunk_boundary_precision"]["value"]
    p100 = r100["per_doc"][0]["metrics"][
        "chunk_boundary_precision"]["value"]
    assert p32 == 1 / 15
    assert p100 == 1 / 5
    assert p32 * 3 == p100


def test_mc_provenance_values_batch474(tmp_path):
    _pdf(tmp_path)
    r32 = run_evaluation(_board_ann(tmp_path),
                         tmp_path / "r32.json",
                         parser_name="fallback", max_chars=32)
    r100 = run_evaluation(_board_ann(tmp_path),
                          tmp_path / "r100.json",
                          parser_name="fallback", max_chars=100)
    assert r32["provenance"]["max_chars"] == 32
    assert r100["provenance"]["max_chars"] == 100


def test_mc_counts_identical_batch474(tmp_path):
    _pdf(tmp_path)
    r32 = run_evaluation(_board_ann(tmp_path),
                         tmp_path / "r32.json",
                         parser_name="fallback", max_chars=32)
    r100 = run_evaluation(_board_ann(tmp_path),
                          tmp_path / "r100.json",
                          parser_name="fallback", max_chars=100)
    assert r32["summary"]["counts"] == \
        r100["summary"]["counts"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch474():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src


# ---------- forbidden tokens 第七百三十六批 ----------

def test_source_no_eval_batch474():
    assert "eval(" not in _src()


def test_source_no_exec_batch474():
    assert "exec(" not in _src()


def test_source_no_compile_batch474():
    assert "compile(" not in _src()


def test_source_no_globals_batch474():
    assert "globals(" not in _src()


def test_source_no_locals_batch474():
    assert "locals(" not in _src()


def test_source_no_os_system_batch474():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch474():
    assert ".call(" not in _src()


def test_source_no_popen_batch474():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch474():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch474():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch474():
    assert "socket" not in _src()


def test_source_no_requests_batch474():
    assert "requests" not in _src()


def test_source_no_urllib_batch474():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch474():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch474():
    assert "yield" not in _src()


def test_source_no_async_await_batch474():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch474():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch474():
    assert _src().count("subprocess.run") == 2
