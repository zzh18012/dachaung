"""evaluation/annotation_metrics.py 第五百九十轮 edges 测试（Round 1313）。

补强 edges158 未触及的角度（第六百八十五批，probe 实证）。

新角度（1P 板锚定几何 / 尾锚不对称 / 同 marker 双锚）：
- **1P 分母 14**——无
  标题板 15 块 14 边
  界 → cbp 1/14 +
  f1 2/15（区别组合
  板 1/15 分母首锁）
- **头锚 Word0.**——
  after → gt 87 邻首
  pred → HIT
- **尾锚 after 全零**
  ——'Word59.' after →
  gt 恰 stream 末端
  469，无 pred 在容差
  内 → {0.0, 0.0,
  0.0}（marker 已找到
  而零匹配——区别
  missing null 三元组
  首锁）
- **尾锚 before 命中**
  ——'Word59.' before
  → gt 463 邻末前 pred
  → HIT（尾锚 before/
  after 不对称首锁）
- **同 marker 双锚**——
  [after, before] 与
  [before, after] 均单
  gt HIT（search_from
  前进后第二锚必 missing
  首锁）
- forbidden tokens 第七百六十批（open 0）
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


HIT14 = ({"value": 1 / 14, "reason": None},
         {"value": 1.0, "reason": None},
         {"value": 2 / 15, "reason": None})
ZERO = ({"value": 0.0, "reason": None},
        {"value": 0.0, "reason": None},
        {"value": 0.0, "reason": None})


# ---------- 1P 分母 14 ----------

def test_w3_denominator_14_batch511(tmp_path):
    assert _trio(tmp_path, [{"marker": "Word3.",
                             "position": "after"}]) \
        == HIT14


def test_w3_cbp_exact_batch511(tmp_path):
    cbp, _, _ = _trio(tmp_path, [{"marker": "Word3.",
                                  "position": "after"}])
    assert cbp["value"] == 1 / 14


def test_w3_f1_exact_batch511(tmp_path):
    _, _, f1 = _trio(tmp_path, [{"marker": "Word3.",
                                 "position": "after"}])
    assert f1["value"] == 2 / 15


# ---------- 头锚 ----------

def test_w0_head_hit_batch511(tmp_path):
    assert _trio(tmp_path, [{"marker": "Word0.",
                             "position": "after"}]) \
        == HIT14


# ---------- 尾锚 after 全零 ----------

def test_w59_after_zero_trio_batch511(tmp_path):
    assert _trio(tmp_path, [{"marker": "Word59.",
                             "position": "after"}]) \
        == ZERO


def test_w59_after_no_null_reason_batch511(tmp_path):
    _, cbr, _ = _trio(tmp_path, [{"marker": "Word59.",
                                  "position": "after"}])
    assert cbr["reason"] is None
    assert cbr["value"] == 0.0


# ---------- 尾锚 before 命中 ----------

def test_w59_before_hit_batch511(tmp_path):
    assert _trio(tmp_path, [{"marker": "Word59.",
                             "position": "before"}]) \
        == HIT14


def test_tail_asymmetry_batch511(tmp_path):
    after = _trio(tmp_path, [{"marker": "Word59.",
                              "position": "after"}])
    before = _trio(tmp_path, [{"marker": "Word59.",
                               "position": "before"}])
    assert after == ZERO
    assert before == HIT14


# ---------- 同 marker 双锚 ----------

def test_dup_after_before_single_gt_batch511(
        tmp_path):
    assert _trio(tmp_path, [
        {"marker": "Word3.", "position": "after"},
        {"marker": "Word3.", "position": "before"}]) \
        == HIT14


def test_dup_before_after_single_gt_batch511(
        tmp_path):
    assert _trio(tmp_path, [
        {"marker": "Word3.", "position": "before"},
        {"marker": "Word3.", "position": "after"}]) \
        == HIT14


def test_dup_recall_one_batch511(tmp_path):
    _, cbr, _ = _trio(tmp_path, [
        {"marker": "Word3.", "position": "after"},
        {"marker": "Word3.", "position": "before"}])
    assert cbr == {"value": 1.0, "reason": None}


# ---------- 报告合法性 ----------

def test_report_schema_batch511(tmp_path):
    _trio(tmp_path, [{"marker": "Word3.",
                      "position": "after"}])
    validate(json.loads((tmp_path / "r.json")
                        .read_text(encoding="utf-8")),
             "evaluation-report.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(amod)


def test_source_key_lines_batch511():
    src = _src()
    assert "search_from = find_pos + len(marker)" \
        in src
    assert "missing_markers" in src


# ---------- forbidden tokens 第七百六十批 ----------

def test_source_no_eval_batch511():
    assert "eval(" not in _src()


def test_source_no_exec_batch511():
    assert "exec(" not in _src()


def test_source_no_compile_batch511():
    assert "compile(" not in _src()


def test_source_no_globals_batch511():
    assert "globals(" not in _src()


def test_source_no_locals_batch511():
    assert "locals(" not in _src()


def test_source_no_os_system_batch511():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch511():
    assert "subprocess" not in _src()


def test_source_no_popen_batch511():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch511():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch511():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch511():
    assert "socket" not in _src()


def test_source_no_requests_batch511():
    assert "requests" not in _src()


def test_source_no_urllib_batch511():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch511():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch511():
    assert "yield" not in _src()


def test_source_no_async_await_batch511():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch511():
    assert ".call(" not in _src()


def test_source_open_count_is_0_batch511():
    assert _src().count("open(") == 0
