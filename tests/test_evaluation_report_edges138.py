"""evaluation/report.py 第五百六十九轮 edges 测试（Round 1270）。

补强 edges137 未触及的角度（第六百四十二批，probe 实证）。

新角度（mc98/mc200 报告差分 / 精确差异路径集）：
- **差分路径集首锁**——同
  manifest+标注跑 mc98 vs
  mc200，全树逐一对比 → 恰 7
  条叶路径不同：cbr/cbf per-doc
  值、两处聚合 macro、
  provenance.max_chars、
  run_timestamp_iso、
  wall_time.total（其余全同首锁）
- **metrics 除界全同**——
  per_doc metrics 弹出
  chunk_boundary_recall/f1 后
  两跑 dict 相等
- **wall_time_seconds 形**——
  parse/chunk null +
  *_reason "not_instrumented" +
  total float（未插桩五键首锁）
- forbidden tokens 第七百三十批（open 0）
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


MIX_TEXTS = ["Figure 1 An overview diagram.", "A" * 80,
             "Is this a heading?"]


def _board(tmp_path):
    ys = [700, 660, 620]
    s = "".join("BT /F1 12 Tf 10 %d Td (%s) Tj ET\n" % (y, t)
                for y, t in zip(ys, MIX_TEXTS)).encode()
    (tmp_path / "mix.pdf").write_bytes(_wrap(s))
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
    return load_manifest(mf, project_root=tmp_path)


def _runs(tmp_path):
    board = _board(tmp_path)
    r98 = run_evaluation(board, tmp_path / "r98.json",
                         parser_name="fallback", max_chars=98)
    r200 = run_evaluation(board, tmp_path / "r200.json",
                          parser_name="fallback", max_chars=200)
    return r98, r200


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


DIFF_SET = {
    ("per_doc", 0, "metrics", "chunk_boundary_f1", "value"),
    ("per_doc", 0, "metrics", "chunk_boundary_recall", "value"),
    ("per_doc", 0, "wall_time_seconds", "total"),
    ("provenance", "max_chars"),
    ("provenance", "run_timestamp_iso"),
    ("summary", "ratio_macro_averages", "chunk_boundary_f1",
     "macro_average"),
    ("summary", "ratio_macro_averages", "chunk_boundary_recall",
     "macro_average")}


# ---------- 差分路径集 ----------

def test_diff_set_exact_batch468(tmp_path):
    r98, r200 = _runs(tmp_path)
    assert _diff_paths(r98, r200) == DIFF_SET


def test_diff_deterministic_paths_batch468(tmp_path):
    r98, r200 = _runs(tmp_path)
    diffs = _diff_paths(r98, r200)
    assert ("per_doc", 0, "metrics", "chunk_boundary_recall",
            "value") in diffs
    assert ("provenance", "max_chars") in diffs
    assert ("summary", "ratio_macro_averages",
            "chunk_boundary_recall", "macro_average") in diffs
    assert ("per_doc", 0, "source_type") not in diffs
    assert ("devset", "file_count") not in diffs


def test_metrics_equal_except_boundary_batch468(tmp_path):
    r98, r200 = _runs(tmp_path)
    m98 = dict(r98["per_doc"][0]["metrics"])
    m200 = dict(r200["per_doc"][0]["metrics"])
    for k in ("chunk_boundary_recall", "chunk_boundary_f1"):
        m98.pop(k)
        m200.pop(k)
    assert m98 == m200


def test_provenance_max_chars_differs_batch468(tmp_path):
    r98, r200 = _runs(tmp_path)
    assert r98["provenance"]["max_chars"] == 98
    assert r200["provenance"]["max_chars"] == 200


def test_devset_identical_batch468(tmp_path):
    r98, r200 = _runs(tmp_path)
    assert r98["devset"] == r200["devset"]


def test_counts_identical_batch468(tmp_path):
    r98, r200 = _runs(tmp_path)
    assert r98["summary"]["counts"] == r200["summary"]["counts"]


# ---------- 值 ----------

def test_r98_cbr_one_batch468(tmp_path):
    r98, _ = _runs(tmp_path)
    assert r98["per_doc"][0]["metrics"][
        "chunk_boundary_recall"] == {"value": 1.0, "reason": None}


def test_r200_cbr_half_batch468(tmp_path):
    _, r200 = _runs(tmp_path)
    assert r200["per_doc"][0]["metrics"][
        "chunk_boundary_recall"] == {"value": 0.5, "reason": None}


def test_r98_agg_all_one_batch468(tmp_path):
    r98, _ = _runs(tmp_path)
    agg = r98["summary"]["ratio_macro_averages"]
    assert agg["chunk_boundary_recall"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 0}
    assert agg["chunk_boundary_f1"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 0}


def test_r200_agg_half_batch468(tmp_path):
    _, r200 = _runs(tmp_path)
    agg = r200["summary"]["ratio_macro_averages"]
    assert agg["chunk_boundary_recall"] == {
        "macro_average": 0.5, "participating_docs": 1,
        "not_evaluated": 0}
    assert agg["chunk_boundary_f1"] == {
        "macro_average": 0.6666666666666666,
        "participating_docs": 1, "not_evaluated": 0}


# ---------- 形 ----------

def test_wall_time_shape_batch468(tmp_path):
    r98, r200 = _runs(tmp_path)
    for r in (r98, r200):
        wt = r["per_doc"][0]["wall_time_seconds"]
        assert wt["parse"] is None
        assert wt["chunk"] is None
        assert wt["parse_reason"] == "not_instrumented"
        assert wt["chunk_reason"] == "not_instrumented"
        assert isinstance(wt["total"], float)
        assert wt["total"] > 0


def test_report_version_both_batch468(tmp_path):
    r98, r200 = _runs(tmp_path)
    assert r98["report_version"] == "1.1"
    assert r200["report_version"] == "1.1"
    assert r98["provenance"]["report_version"] == "1.1"
    assert r200["provenance"]["report_version"] == "1.1"


def test_expected_failures_both_batch468(tmp_path):
    r98, r200 = _runs(tmp_path)
    assert r98["expected_failures"] == []
    assert r200["expected_failures"] == []


def test_tolerance_absent_both_batch468(tmp_path):
    r98, r200 = _runs(tmp_path)
    assert "tolerance_chars" not in json.dumps(r98)
    assert "tolerance_chars" not in json.dumps(r200)


def test_round_trip_both_batch468(tmp_path):
    board = _board(tmp_path)
    r98 = run_evaluation(board, tmp_path / "r98.json",
                         parser_name="fallback", max_chars=98)
    assert json.loads(
        (tmp_path / "r98.json").read_text(encoding="utf-8")) \
        == r98


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch468():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src


# ---------- forbidden tokens 第七百三十批 ----------

def test_source_no_eval_batch468():
    assert "eval(" not in _src()


def test_source_no_exec_batch468():
    assert "exec(" not in _src()


def test_source_no_compile_batch468():
    assert "compile(" not in _src()


def test_source_no_globals_batch468():
    assert "globals(" not in _src()


def test_source_no_locals_batch468():
    assert "locals(" not in _src()


def test_source_no_os_system_batch468():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch468():
    assert ".call(" not in _src()


def test_source_no_popen_batch468():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch468():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch468():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch468():
    assert "socket" not in _src()


def test_source_no_requests_batch468():
    assert "requests" not in _src()


def test_source_no_urllib_batch468():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch468():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch468():
    assert "yield" not in _src()


def test_source_no_async_await_batch468():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch468():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch468():
    assert _src().count("subprocess.run") == 2
