"""evaluation/annotation_metrics.py 第五百九十一轮 edges 测试（Round 1319）。

补强 edges159 未触及的角度（第六百九十一批，probe 实证）。

新角度（批量锚一对一部分匹配 / 头 before / 字面搜索）：
- **批量 10 锚**——
  Word0/2/…/18 after
  → 仅 6 匹配：cbp
  6/15、cbr 6/10、f1
  0.48（一对一路上
  相邻锚共享邻近 pred
  部分命中首锁）
- **头 before**——
  'Word0.' before →
  gt 81 恰首 pred →
  HIT（区别 edges159
  尾 before 的头侧补
  全）
- **reason 键容忍**——
  anchor 带 reason 字
  段（schema 合法附
  加键）运行时忽略 →
  HIT 不受扰
- **字面搜索**——
  'Word[3].' 方括号
  原样按字面找 → 不
  存在 → missing 三
  元组（str.find 非
  regex 首锁）
- forbidden tokens 第七百六十五批（open 0）
"""

from __future__ import annotations

import inspect
import json

import evaluation.annotation_metrics as amod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from evaluation.schema import validate


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
STREAM = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
          % ("A" * 80)
          + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
          % LONG).encode()


def _trio(tmp_path, anchors):
    (tmp_path / "c.pdf").write_bytes(_wrap(STREAM))
    (tmp_path / "ann").mkdir(exist_ok=True)
    (tmp_path / "ann" / "a.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": "d1",
        "chunk_boundary_anchors": anchors}),
        encoding="utf-8")
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "c.pdf",
                       "source_type": "pdf",
                       "annotation_file": "ann/a.json"}]}),
        encoding="utf-8")
    mf = load_manifest((tmp_path / "m.json"),
                       project_root=tmp_path)
    r = run_evaluation(mf, tmp_path / "r.json",
                       parser_name="fallback",
                       max_chars=32)
    m = r["per_doc"][0]["metrics"]
    return (m["chunk_boundary_precision"],
            m["chunk_boundary_recall"],
            m["chunk_boundary_f1"])


HIT = ({"value": 1 / 15, "reason": None},
       {"value": 1.0, "reason": None},
       {"value": 0.125, "reason": None})
MISSING = ({"value": 0.0, "reason": None},
           {"value": None,
            "reason": "no_ground_truth_anchors_in_stream"},
           {"value": None,
            "reason": "precision_or_recall_not_evaluated"})
BULK10 = [{"marker": "Word%d." % n, "position": "after"}
          for n in range(0, 20, 2)]


# ---------- 批量 10 锚 ----------

def test_bulk10_cbp_batch517(tmp_path):
    cbp, _, _ = _trio(tmp_path, BULK10)
    assert cbp == {"value": 6 / 15, "reason": None}


def test_bulk10_cbr_batch517(tmp_path):
    _, cbr, _ = _trio(tmp_path, BULK10)
    assert cbr == {"value": 6 / 10, "reason": None}


def test_bulk10_f1_batch517(tmp_path):
    _, _, f1 = _trio(tmp_path, BULK10)
    assert f1 == {"value": 0.48, "reason": None}


def test_bulk10_partial_not_full_batch517(tmp_path):
    _, cbr, _ = _trio(tmp_path, BULK10)
    assert cbr["value"] < 1.0
    assert cbr["value"] > 0.5


# ---------- 头 before ----------

def test_head_before_hit_batch517(tmp_path):
    assert _trio(tmp_path, [{"marker": "Word0.",
                             "position": "before"}]) \
        == HIT


def test_head_before_vs_after_same_batch517(tmp_path):
    b = _trio(tmp_path, [{"marker": "Word0.",
                          "position": "before"}])
    a = _trio(tmp_path, [{"marker": "Word0.",
                          "position": "after"}])
    assert b == a == HIT


# ---------- reason 键容忍 ----------

def test_reason_key_ignored_batch517(tmp_path):
    assert _trio(tmp_path, [
        {"marker": "Word3.", "position": "after",
         "reason": "section break"}]) == HIT


def test_reason_empty_string_batch517(tmp_path):
    assert _trio(tmp_path, [
        {"marker": "Word3.", "position": "after",
         "reason": ""}]) == HIT


# ---------- 字面搜索 ----------

def test_regex_brackets_missing_batch517(tmp_path):
    assert _trio(tmp_path, [{"marker": "Word[3].",
                             "position": "after"}]) \
        == MISSING


def test_literal_find_not_regex_batch517(tmp_path):
    _, cbr, _ = _trio(tmp_path, [{"marker": "Word[3].",
                                  "position": "after"}])
    assert cbr["reason"] == "no_ground_truth_" \
                            "anchors_in_stream"


# ---------- 报告合法性 ----------

def test_report_schema_batch517(tmp_path):
    _trio(tmp_path, BULK10)
    validate(json.loads((tmp_path / "r.json")
                        .read_text(encoding="utf-8")),
             "evaluation-report.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(amod)


def test_source_key_lines_batch517():
    src = _src()
    assert "used_pred" in src
    assert "pairs.sort(key=lambda x: x[0])" in src


# ---------- forbidden tokens 第七百六十五批 ----------

def test_source_no_eval_batch517():
    assert "eval(" not in _src()


def test_source_no_exec_batch517():
    assert "exec(" not in _src()


def test_source_no_compile_batch517():
    assert "compile(" not in _src()


def test_source_no_globals_batch517():
    assert "globals(" not in _src()


def test_source_no_locals_batch517():
    assert "locals(" not in _src()


def test_source_no_os_system_batch517():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch517():
    assert "subprocess" not in _src()


def test_source_no_popen_batch517():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch517():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch517():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch517():
    assert "socket" not in _src()


def test_source_no_requests_batch517():
    assert "requests" not in _src()


def test_source_no_urllib_batch517():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch517():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch517():
    assert "yield" not in _src()


def test_source_no_async_await_batch517():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch517():
    assert ".call(" not in _src()


def test_source_open_count_is_0_batch517():
    assert _src().count("open(") == 0
