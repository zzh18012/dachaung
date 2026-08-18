"""evaluation/report.py 第五百七十一轮 edges 测试（Round 1282）。

补强 edges139 未触及的角度（第六百五十四批，probe 实证）。

新角度（板型差分 13 路径 / hbc 聚合参与翻转）：
- **板型差分路径集首锁**——
  combo（heading+长段）vs fig
  （单 caption）同构单档报告
  全树对比 → 恰 13 条叶路径：
  doc_id + ecbt 三键增删 +
  element_count_total + hbc
  value/reason + 聚合 hbc 三键
  + counts sum + wall_time +
  时间戳
- **hbc 聚合参与翻转**——
  combo {1.0, 1, 0} ↔ fig
  {None, 0, 1}
- **success_rates 跨板同**——
  两板 rate 1.0 完全相同
- **ecbt 三键增删**——
  caption/heading/paragraph
  键的存在性差分（dict 键集
  差分首锁）
- forbidden tokens 第七百四十一批（open 0）
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


def _pdfs(tmp_path):
    (tmp_path / "combo.pdf").write_bytes(_wrap(
        ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()))
    (tmp_path / "fig.pdf").write_bytes(_wrap(
        b"BT /F1 12 Tf 10 700 Td "
        b"(Figure 1 An overview diagram.) Tj ET\n"))


def _board(tmp_path, doc_id, path):
    mf = tmp_path / ("m_%s.json" % doc_id)
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id, "path": path,
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


def _runs(tmp_path):
    rc = run_evaluation(_board(tmp_path, "combo", "combo.pdf"),
                        tmp_path / "rc.json",
                        parser_name="fallback", max_chars=32)
    rf = run_evaluation(_board(tmp_path, "fig", "fig.pdf"),
                        tmp_path / "rf.json",
                        parser_name="fallback", max_chars=32)
    return rc, rf


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


BOARD_DIFF = {
    ("per_doc", 0, "doc_id"),
    ("per_doc", 0, "metrics", "element_count_by_type",
     "value", "caption"),
    ("per_doc", 0, "metrics", "element_count_by_type",
     "value", "heading"),
    ("per_doc", 0, "metrics", "element_count_by_type",
     "value", "paragraph"),
    ("per_doc", 0, "metrics", "element_count_total",
     "value"),
    ("per_doc", 0, "metrics",
     "heading_boundary_compliance", "reason"),
    ("per_doc", 0, "metrics",
     "heading_boundary_compliance", "value"),
    ("per_doc", 0, "wall_time_seconds", "total"),
    ("provenance", "run_timestamp_iso"),
    ("summary", "counts", "element_count_total", "sum"),
    ("summary", "ratio_macro_averages",
     "heading_boundary_compliance", "macro_average"),
    ("summary", "ratio_macro_averages",
     "heading_boundary_compliance", "not_evaluated"),
    ("summary", "ratio_macro_averages",
     "heading_boundary_compliance",
     "participating_docs")}


# ---------- 板型差分路径集 ----------

def test_board_diff_set_exact_batch480(tmp_path):
    _pdfs(tmp_path)
    rc, rf = _runs(tmp_path)
    assert _diff_paths(rc, rf) == BOARD_DIFF


def test_board_diff_size_13_batch480(tmp_path):
    _pdfs(tmp_path)
    rc, rf = _runs(tmp_path)
    assert len(_diff_paths(rc, rf)) == 13


def test_board_diff_excludes_batch480(tmp_path):
    _pdfs(tmp_path)
    rc, rf = _runs(tmp_path)
    diffs = _diff_paths(rc, rf)
    assert ("summary", "success_rates") not in diffs
    assert ("per_doc", 0, "metrics",
            "text_preservation_equal", "value") not in diffs
    assert ("per_doc", 0, "metrics", "silent_drop_count",
            "reason") not in diffs
    assert ("devset", "file_count") not in diffs


# ---------- hbc 聚合参与翻转 ----------

def test_combo_hbc_agg_participating_batch480(tmp_path):
    _pdfs(tmp_path)
    rc, _ = _runs(tmp_path)
    assert rc["summary"]["ratio_macro_averages"][
        "heading_boundary_compliance"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 0}


def test_fig_hbc_agg_not_evaluated_batch480(tmp_path):
    _pdfs(tmp_path)
    _, rf = _runs(tmp_path)
    assert rf["summary"]["ratio_macro_averages"][
        "heading_boundary_compliance"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 1}


def test_fig_hbc_metric_null_batch480(tmp_path):
    _pdfs(tmp_path)
    _, rf = _runs(tmp_path)
    assert rf["per_doc"][0]["metrics"][
        "heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}


# ---------- ecbt 三键增删 ----------

def test_ecbt_key_sets_batch480(tmp_path):
    _pdfs(tmp_path)
    rc, rf = _runs(tmp_path)
    kc = rc["per_doc"][0]["metrics"][
        "element_count_by_type"]["value"]
    kf = rf["per_doc"][0]["metrics"][
        "element_count_by_type"]["value"]
    assert set(kc) == {"heading", "paragraph"}
    assert set(kf) == {"caption"}


def test_ecbt_values_batch480(tmp_path):
    _pdfs(tmp_path)
    rc, rf = _runs(tmp_path)
    assert rc["per_doc"][0]["metrics"][
        "element_count_by_type"]["value"] == {
        "heading": 1, "paragraph": 1}
    assert rf["per_doc"][0]["metrics"][
        "element_count_by_type"]["value"] == {
        "caption": 1}


# ---------- success_rates 跨板同 ----------

def test_success_rates_identical_batch480(tmp_path):
    _pdfs(tmp_path)
    rc, rf = _runs(tmp_path)
    assert rc["summary"]["success_rates"] == \
        rf["summary"]["success_rates"]
    assert rc["summary"]["success_rates"] == {
        "pipeline_success": {"success_count": 1,
                             "total": 1, "rate": 1.0}}


def test_counts_sum_flip_batch480(tmp_path):
    _pdfs(tmp_path)
    rc, rf = _runs(tmp_path)
    assert rc["summary"]["counts"][
        "element_count_total"]["sum"] == 2
    assert rf["summary"]["counts"][
        "element_count_total"]["sum"] == 1


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch480():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src


# ---------- forbidden tokens 第七百四十一批 ----------

def test_source_no_eval_batch480():
    assert "eval(" not in _src()


def test_source_no_exec_batch480():
    assert "exec(" not in _src()


def test_source_no_compile_batch480():
    assert "compile(" not in _src()


def test_source_no_globals_batch480():
    assert "globals(" not in _src()


def test_source_no_locals_batch480():
    assert "locals(" not in _src()


def test_source_no_os_system_batch480():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch480():
    assert ".call(" not in _src()


def test_source_no_popen_batch480():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch480():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch480():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch480():
    assert "socket" not in _src()


def test_source_no_requests_batch480():
    assert "requests" not in _src()


def test_source_no_urllib_batch480():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch480():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch480():
    assert "yield" not in _src()


def test_source_no_async_await_batch480():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch480():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch480():
    assert _src().count("subprocess.run") == 2
