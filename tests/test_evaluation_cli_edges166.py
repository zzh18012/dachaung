"""evaluation/cli.py 第六百六十七轮 edges 测试（Round 1286）。

补强 edges165 未触及的角度（第六百五十八批，probe 实证）。

新角度（三态 null 谱系 CLI 全链 / 公共报告面剥除）：
- **空锚 CLI**——ann 空 [] 经
  run → rc 0 + trio 全
  no_ground_truth_anchors
  （CLI 端到端首锁，区别于
  no_annotation）
- **缺标注文件 CLI 静默**——
  ann/gone.json → rc 0 +
  [OK] 仍打印 + trio 全
  no_annotation；与无键同因
- **absent 标记第三态**——
  NotInDoc. → cbp {0.0, None}
  + cbr _in_stream + cbf
  not_evaluated；三态共 4 种
  reason 字符串
- **公共面剥除**——per_doc 条目
  恰 4 键；_annotation_present/
  _tolerance_chars/_missing_
  markers 全部不出现在公共
  报告 JSON；"tolerance" 子串
  全报告缺席
- **tol 7 对 null 无效**——
  --tolerance-chars 7 改变
  不了空锚三态
- forbidden tokens 第五百八十八批（open 1）
"""

from __future__ import annotations

import inspect
import json
import sys

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


def _board(tmp_path, annotation_file):
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()
    (tmp_path / "combo.pdf").write_bytes(_wrap(s))
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "empty.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "combo",
        "chunk_boundary_anchors": []}), encoding="utf-8")
    (tmp_path / "ann" / "absent.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "combo",
        "chunk_boundary_anchors": [
            {"marker": "NotInDoc.", "position": "after"}]}),
        encoding="utf-8")
    doc = {"doc_id": "combo", "path": "combo.pdf",
           "source_type": "pdf"}
    if annotation_file is not None:
        doc["annotation_file"] = annotation_file
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [doc]}), encoding="utf-8")
    return str(tmp_path / "m.json")


def _run(tmp_path, capsys, annotation_file, extra=()):
    rep = tmp_path / ("r_%s.json" %
                      str(annotation_file).replace("/", "_"))
    sys.argv = ["evaluation.cli", "run", "--manifest",
                _board(tmp_path, annotation_file),
                "--output", str(rep), "--parser", "fallback",
                "--max-chars", "32"] + list(extra)
    rc = main()
    out = capsys.readouterr().out
    return rc, out, json.loads(
        rep.read_text(encoding="utf-8"))


def _trio(report):
    m = report["per_doc"][0]["metrics"]
    return tuple(m[k] for k in (
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1"))


NGT = {"value": None, "reason": "no_ground_truth_anchors"}
NOANN = {"value": None, "reason": "no_annotation"}


# ---------- 空锚 CLI 全链 ----------

def test_empty_anchors_trio_batch484(tmp_path, capsys):
    rc, _, report = _run(tmp_path, capsys, "ann/empty.json")
    assert rc == 0
    assert _trio(report) == (NGT, NGT, NGT)


def test_empty_anchors_aggregate_batch484(tmp_path, capsys):
    _, _, report = _run(tmp_path, capsys, "ann/empty.json")
    agg = report["summary"]["ratio_macro_averages"]
    assert agg["chunk_boundary_f1"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 1}


def test_success_full_despite_nulls_batch484(tmp_path, capsys):
    _, _, report = _run(tmp_path, capsys, "ann/empty.json")
    assert report["summary"]["success_rates"] == {
        "pipeline_success": {"success_count": 1,
                             "total": 1, "rate": 1.0}}


# ---------- 缺标注文件 CLI 静默 ----------

def test_missing_ann_trio_batch484(tmp_path, capsys):
    rc, _, report = _run(tmp_path, capsys, "ann/gone.json")
    assert rc == 0
    assert _trio(report) == (NOANN, NOANN, NOANN)


def test_missing_ann_ok_printed_batch484(tmp_path, capsys):
    rc, out, _ = _run(tmp_path, capsys, "ann/gone.json")
    assert "[OK] 评测完成" in out
    assert "documents=1（成功 1，失败 0）" in out


def test_nokey_same_as_missing_batch484(tmp_path, capsys):
    _, _, r_miss = _run(tmp_path, capsys, "ann/gone.json")
    _, _, r_none = _run(tmp_path, capsys, None)
    assert _trio(r_miss) == _trio(r_none)


# ---------- absent 标记第三态 ----------

def test_absent_marker_state_batch484(tmp_path, capsys):
    _, _, report = _run(tmp_path, capsys, "ann/absent.json")
    cbp, cbr, cbf = _trio(report)
    assert cbp == {"value": 0.0, "reason": None}
    assert cbr == {"value": None,
                   "reason": "no_ground_truth_anchors_in_stream"}
    assert cbf == {
        "value": None,
        "reason": "precision_or_recall_not_evaluated"}


def test_three_states_reasons_set_batch484(tmp_path, capsys):
    reasons = set()
    for af in ("ann/empty.json", "ann/gone.json",
               "ann/absent.json"):
        for metric in _trio(
                _run(tmp_path, capsys, af)[2]):
            if metric["reason"] is not None:
                reasons.add(metric["reason"])
    assert reasons == {"no_ground_truth_anchors",
                       "no_annotation",
                       "no_ground_truth_anchors_in_stream",
                       "precision_or_recall_not_evaluated"}


# ---------- 公共报告面剥除 ----------

def test_public_per_doc_keys_batch484(tmp_path, capsys):
    _, _, report = _run(tmp_path, capsys, "ann/empty.json")
    assert set(report["per_doc"][0]) == {
        "doc_id", "source_type", "metrics",
        "wall_time_seconds"}


def test_no_underscore_internals_batch484(tmp_path, capsys):
    _, _, report = _run(tmp_path, capsys, "ann/absent.json")
    s = json.dumps(report)
    assert "_annotation_present" not in s
    assert "_tolerance_chars" not in s
    assert "_missing_markers" not in s


def test_no_tolerance_substring_batch484(tmp_path, capsys):
    _, _, report = _run(tmp_path, capsys, "ann/empty.json")
    assert "tolerance" not in json.dumps(report)


# ---------- tol 7 对 null 无效 ----------

def test_tol7_moot_batch484(tmp_path, capsys):
    rc, _, report = _run(tmp_path, capsys, "ann/empty.json",
                         extra=("--tolerance-chars", "7"))
    assert rc == 0
    assert _trio(report) == (NGT, NGT, NGT)


# ---------- validate-report 往返 ----------

def test_validate_roundtrip_batch484(tmp_path, capsys):
    _run(tmp_path, capsys, "ann/empty.json")
    rep_path = tmp_path / "r_ann_empty.json.json"
    sys.argv = ["evaluation.cli", "validate-report", str(rep_path)]
    rc = main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "通过 evaluation-report Schema 校验" in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_identifier_counts_batch484():
    src = _src()
    assert src.count("validate") == 7
    assert src.count("inspect") == 9
    assert src.count("report") == 14


# ---------- forbidden tokens 第五百八十八批 ----------

def test_source_no_eval_batch484():
    assert "eval(" not in _src()


def test_source_no_exec_batch484():
    assert "exec(" not in _src()


def test_source_no_compile_batch484():
    assert "compile(" not in _src()


def test_source_no_globals_batch484():
    assert "globals(" not in _src()


def test_source_no_locals_batch484():
    assert "locals(" not in _src()


def test_source_no_os_system_batch484():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch484():
    assert "subprocess" not in _src()


def test_source_no_popen_batch484():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch484():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch484():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch484():
    assert "socket" not in _src()


def test_source_no_requests_batch484():
    assert "requests" not in _src()


def test_source_no_urllib_batch484():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch484():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch484():
    assert "yield" not in _src()


def test_source_no_async_await_batch484():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch484():
    assert ".call(" not in _src()


def test_source_open_count_is_1_batch484():
    assert _src().count("open(") == 1
