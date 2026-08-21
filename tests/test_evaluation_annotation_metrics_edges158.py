"""evaluation/annotation_metrics.py 第五百八十九轮 edges 测试（Round 1307）。

补强 edges157 未触及的角度（第六百七十九批，probe 实证）。

新角度（marker 定位严苛面 / position 默认分支）：
- **大小写敏感**——marker
  'word3.'（小写 w）→ 全
  missing 三元组 {0.0,
  None} / {None,
  no_ground_truth_
  anchors_in_stream} /
  {None, precision_or_
  recall_not_evaluated}
  （str.find 原样大小写
  匹配首锁）
- **空 marker**——'' falsy
  守卫 → find 跳过（-1）
  → 同 missing 三元组
  （不误定位于 0 首锁）
- **position 非枚举值**——
  'middle' 落 else 分支
  → 与 after 全等（HIT
  三元组）
- **position 键缺失**——
  a.get("position",
  "after") 默认 → after
  全等
- **position 'AFTER' 大写**
  ——比较大小写敏感 →
  非 'before' → after
  分支全等
- **混板不毒化**——好
  'Word3.' + 坏小写同板
  → 坏 anchor 静默丢、
  好 anchor 仍 HIT
- forbidden tokens 第七百五十五批（open 0）
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


MISSING = ({"value": 0.0, "reason": None},
           {"value": None,
            "reason": "no_ground_truth_anchors_in_stream"},
           {"value": None,
            "reason": "precision_or_recall_not_evaluated"})
HIT = ({"value": 1 / 15, "reason": None},
       {"value": 1.0, "reason": None},
       {"value": 0.125, "reason": None})


# ---------- 大小写敏感 ----------

def test_lowercase_marker_missing_batch505(tmp_path):
    assert _trio(tmp_path, [{"marker": "word3.",
                             "position": "after"}]) \
        == MISSING


def test_case_sensitive_no_zero_div_batch505(tmp_path):
    cbp, _, _ = _trio(tmp_path, [{"marker": "word3.",
                                  "position": "after"}])
    assert cbp == {"value": 0.0, "reason": None}


# ---------- 空 marker ----------

def test_empty_marker_missing_batch505(tmp_path):
    assert _trio(tmp_path, [{"marker": "",
                             "position": "after"}]) \
        == MISSING


def test_empty_marker_no_pos0_batch505(tmp_path):
    _, cbr, _ = _trio(tmp_path, [{"marker": "",
                                  "position": "after"}])
    assert cbr["reason"] == "no_ground_truth_anchors_" \
                            "in_stream"


# ---------- position 非枚举值 ----------

def test_position_middle_as_after_batch505(tmp_path):
    assert _trio(tmp_path, [{"marker": "Word3.",
                             "position": "middle"}]) \
        == HIT


def test_position_during_as_after_batch505(tmp_path):
    assert _trio(tmp_path, [{"marker": "Word3.",
                             "position": "during"}]) \
        == HIT


# ---------- position 键缺失 ----------

def test_position_absent_defaults_after_batch505(
        tmp_path):
    assert _trio(tmp_path, [{"marker": "Word3."}]) == HIT


# ---------- position 大写 ----------

def test_position_uppercase_as_after_batch505(tmp_path):
    assert _trio(tmp_path, [{"marker": "Word3.",
                             "position": "AFTER"}]) == HIT


# ---------- 混板不毒化 ----------

def test_mixed_good_and_lowercase_batch505(tmp_path):
    assert _trio(tmp_path, [
        {"marker": "Word3.", "position": "after"},
        {"marker": "word3.", "position": "after"}]) \
        == HIT


def test_mixed_good_and_empty_batch505(tmp_path):
    assert _trio(tmp_path, [
        {"marker": "Word3.", "position": "after"},
        {"marker": "", "position": "after"}]) == HIT


def test_mixed_good_and_badpos_batch505(tmp_path):
    assert _trio(tmp_path, [
        {"marker": "Word3.", "position": "after"},
        {"marker": "Word5.", "position": "zzz"}]) \
        == ({"value": 2 / 15, "reason": None},
            {"value": 1.0, "reason": None},
            {"value": 4 / 17, "reason": None})


# ---------- 报告合法性 ----------

def test_report_schema_batch505(tmp_path):
    _trio(tmp_path, [{"marker": "Word3.",
                      "position": "after"}])
    validate(json.loads((tmp_path / "r.json")
                        .read_text(encoding="utf-8")),
             "evaluation-report.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(amod)


def test_source_key_lines_batch505():
    src = _src()
    assert 'position = a.get("position", "after")' in src
    assert ("stream.find(marker, search_from) "
            "if marker else -1") in src
    assert 'if position == "before":' in src


# ---------- forbidden tokens 第七百五十五批 ----------

def test_source_no_eval_batch505():
    assert "eval(" not in _src()


def test_source_no_exec_batch505():
    assert "exec(" not in _src()


def test_source_no_compile_batch505():
    assert "compile(" not in _src()


def test_source_no_globals_batch505():
    assert "globals(" not in _src()


def test_source_no_locals_batch505():
    assert "locals(" not in _src()


def test_source_no_os_system_batch505():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch505():
    assert "subprocess" not in _src()


def test_source_no_popen_batch505():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch505():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch505():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch505():
    assert "socket" not in _src()


def test_source_no_requests_batch505():
    assert "requests" not in _src()


def test_source_no_urllib_batch505():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch505():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch505():
    assert "yield" not in _src()


def test_source_no_async_await_batch505():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch505():
    assert ".call(" not in _src()


def test_source_open_count_is_0_batch505():
    assert _src().count("open(") == 0
