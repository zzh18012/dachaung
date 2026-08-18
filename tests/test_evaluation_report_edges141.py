"""evaluation/report.py 第五百七十二轮 edges 测试（Round 1288）。

补强 edges140 未触及的角度（第六百六十批，probe 实证）。

新角度（期望板差分 15 路 / mc 不变面）：
- **期望板差分**——combo
  expectations 精确 vs fig
  expectations {caption: 2}
  → 恰 15 条叶路径 = edges140
  13 路 BOARD_DIFF ⊕
  sdc value + summary.
  silent_drop_total（期望增面
  首锁）
- **sdt 直挂 summary**——
  silent_drop_total 是 summary
  直属键而非 counts 子键
  （键位首锁）；值 0 vs 1
- **mc 不变面**——同板 mc32
  vs mc100 → 全报告差分恰
  3 路：wall_time total +
  provenance.max_chars +
  时间戳；per_doc metrics
  整 dict 相等、success/
  counts/devset 全等
  （16→5 块计数无关首锁）
- forbidden tokens 第七百四十七批（open 0）
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


def _board(tmp_path, name, docs):
    mf = tmp_path / (name + ".json")
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": docs}), encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


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


def _exp_runs(tmp_path):
    rc = run_evaluation(_board(tmp_path, "ma", [
        {"doc_id": "combo", "path": "combo.pdf",
         "source_type": "pdf",
         "expectations": {"element_count_by_type": {
             "heading": 1, "paragraph": 1}}}]),
        tmp_path / "rc.json",
        parser_name="fallback", max_chars=32)
    rf = run_evaluation(_board(tmp_path, "mb", [
        {"doc_id": "fig", "path": "fig.pdf",
         "source_type": "pdf",
         "expectations": {"element_count_by_type": {
             "caption": 2}}}]),
        tmp_path / "rf.json",
        parser_name="fallback", max_chars=32)
    return rc, rf


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

EXP_NEW = {
    ("per_doc", 0, "metrics",
     "silent_drop_count", "value"),
    ("summary", "silent_drop_total")}


# ---------- 期望板差分 15 路 ----------

def test_exp_diff_set_exact_batch486(tmp_path):
    _pdfs(tmp_path)
    rc, rf = _exp_runs(tmp_path)
    assert _diff_paths(rc, rf) == BOARD_DIFF | EXP_NEW


def test_exp_diff_size_15_batch486(tmp_path):
    _pdfs(tmp_path)
    rc, rf = _exp_runs(tmp_path)
    assert len(_diff_paths(rc, rf)) == 15


def test_exp_diff_superset_board_diff_batch486(tmp_path):
    _pdfs(tmp_path)
    rc, rf = _exp_runs(tmp_path)
    assert BOARD_DIFF < _diff_paths(rc, rf)


def test_exp_new_paths_present_batch486(tmp_path):
    _pdfs(tmp_path)
    rc, rf = _exp_runs(tmp_path)
    assert EXP_NEW < _diff_paths(rc, rf)


# ---------- sdc / sdt 值 ----------

def test_sdc_values_batch486(tmp_path):
    _pdfs(tmp_path)
    rc, rf = _exp_runs(tmp_path)
    assert rc["per_doc"][0]["metrics"][
        "silent_drop_count"] == {"value": 0, "reason": None}
    assert rf["per_doc"][0]["metrics"][
        "silent_drop_count"] == {"value": 1, "reason": None}


def test_sdt_values_batch486(tmp_path):
    _pdfs(tmp_path)
    rc, rf = _exp_runs(tmp_path)
    assert rc["summary"]["silent_drop_total"] == 0
    assert rf["summary"]["silent_drop_total"] == 1


def test_sdt_not_in_counts_batch486(tmp_path):
    _pdfs(tmp_path)
    rc, _ = _exp_runs(tmp_path)
    assert "silent_drop_total" in rc["summary"]
    assert "silent_drop_total" not in rc["summary"][
        "counts"]


# ---------- mc 不变面 ----------

def _mc_runs(tmp_path):
    doc = {"doc_id": "combo", "path": "combo.pdf",
           "source_type": "pdf"}
    r32 = run_evaluation(
        _board(tmp_path, "a", [doc]), tmp_path / "r32.json",
        parser_name="fallback", max_chars=32)
    r100 = run_evaluation(
        _board(tmp_path, "b", [doc]), tmp_path / "r100.json",
        parser_name="fallback", max_chars=100)
    return r32, r100


MC_DIFF = {
    ("per_doc", 0, "wall_time_seconds", "total"),
    ("provenance", "max_chars"),
    ("provenance", "run_timestamp_iso")}


def test_mc_diff_exact_batch486(tmp_path):
    _pdfs(tmp_path)
    r32, r100 = _mc_runs(tmp_path)
    assert _diff_paths(r32, r100) == MC_DIFF


def test_mc_max_chars_prov_batch486(tmp_path):
    _pdfs(tmp_path)
    r32, r100 = _mc_runs(tmp_path)
    assert r32["provenance"]["max_chars"] == 32
    assert r100["provenance"]["max_chars"] == 100


def test_mc_metrics_dict_equal_batch486(tmp_path):
    _pdfs(tmp_path)
    r32, r100 = _mc_runs(tmp_path)
    assert r32["per_doc"][0]["metrics"] == \
        r100["per_doc"][0]["metrics"]


def test_mc_success_counts_devset_equal_batch486(
        tmp_path):
    _pdfs(tmp_path)
    r32, r100 = _mc_runs(tmp_path)
    assert r32["summary"]["success_rates"] == \
        r100["summary"]["success_rates"]
    assert r32["summary"]["counts"] == \
        r100["summary"]["counts"]
    assert r32["devset"] == r100["devset"]


def test_mc_per_doc_minus_wall_equal_batch486(
        tmp_path):
    _pdfs(tmp_path)
    r32, r100 = _mc_runs(tmp_path)
    p32 = dict(r32["per_doc"][0])
    p100 = dict(r100["per_doc"][0])
    p32.pop("wall_time_seconds")
    p100.pop("wall_time_seconds")
    assert p32 == p100


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch486():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src


# ---------- forbidden tokens 第七百四十七批 ----------

def test_source_no_eval_batch486():
    assert "eval(" not in _src()


def test_source_no_exec_batch486():
    assert "exec(" not in _src()


def test_source_no_compile_batch486():
    assert "compile(" not in _src()


def test_source_no_globals_batch486():
    assert "globals(" not in _src()


def test_source_no_locals_batch486():
    assert "locals(" not in _src()


def test_source_no_os_system_batch486():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch486():
    assert ".call(" not in _src()


def test_source_no_popen_batch486():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch486():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch486():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch486():
    assert "socket" not in _src()


def test_source_no_requests_batch486():
    assert "requests" not in _src()


def test_source_no_urllib_batch486():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch486():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch486():
    assert "yield" not in _src()


def test_source_no_async_await_batch486():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch486():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch486():
    assert _src().count("subprocess.run") == 2
