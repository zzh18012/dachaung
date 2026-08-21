"""evaluation/schema.py 第五百八十七轮 edges 测试（Round 1341）。

补强 edges151 未触及的角度（第七百一十三批，probe 实证）。

新角度（report 深层严宽分界）：
- **per_doc 严**——
  source_type enum
  ['pdf','docx']；
  wall_time 必填
  parse/total、
  严闭 5 键
- **chunk_reason
  可缺**——缺键
  VALID（wall_time
  非全必填首锁）
- **metrics 宽**——
  额外指标键
  VALID（metrics
  自由对象首锁）
- **ratio/sr/counts
  全宽**——缺
  macro_average/
  rate/sum 均 VALID、
  额外键 VALID
  （summary 内层不
  深约束首锁）
- **ef 严闭**——额外
  键拒 + matches
  required
- forbidden tokens 第七百八十三批（open 2）
"""

from __future__ import annotations

import copy
import inspect
import json
import tempfile
from pathlib import Path

import evaluation.schema as schema_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from evaluation.schema import EvalSchemaError, \
    validate


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
ONEP = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
        % LONG).encode()


def _base():
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "c.pdf").write_bytes(_wrap(ONEP))
        (tp / "m.json").write_text(json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [
                {"doc_id": "g1", "path": "c.pdf",
                 "source_type": "pdf"}]}),
            encoding="utf-8")
        mf = load_manifest(tp / "m.json",
                           project_root=tp)
        return run_evaluation(mf, tp / "r.json",
                              parser_name="fallback",
                              max_chars=32)


def _rej(mutate, message, path):
    d = copy.deepcopy(_base())
    mutate(d)
    try:
        validate(d, "evaluation-report.schema.json")
    except EvalSchemaError as e:
        assert e.errors[0]["message"] == message
        assert list(e.errors[0]["path"]) == path
    else:
        raise AssertionError("expected rejection")


def _acc(mutate):
    d = copy.deepcopy(_base())
    mutate(d)
    validate(d, "evaluation-report.schema.json")


# ---------- per_doc 严 ----------

def test_pd_srctxt_rejected_batch539():
    _rej(lambda d: d["per_doc"][0].__setitem__(
             "source_type", "txt"),
         "'txt' is not one of ['pdf', 'docx']",
         ["per_doc", 0, "source_type"])


def test_wt_missing_parse_batch539():
    _rej(lambda d: d["per_doc"][0][
             "wall_time_seconds"].pop("parse"),
         "'parse' is a required property",
         ["per_doc", 0, "wall_time_seconds"])


def test_wt_missing_total_batch539():
    _rej(lambda d: d["per_doc"][0][
             "wall_time_seconds"].pop("total"),
         "'total' is a required property",
         ["per_doc", 0, "wall_time_seconds"])


def test_wt_extra_key_batch539():
    _rej(lambda d: d["per_doc"][0][
             "wall_time_seconds"].__setitem__("zz", 1),
         "Additional properties are not allowed "
         "('zz' was unexpected)",
         ["per_doc", 0, "wall_time_seconds"])


# ---------- chunk_reason 可缺 ----------

def test_wt_chunk_reason_optional_batch539():
    _acc(lambda d: d["per_doc"][0][
        "wall_time_seconds"].pop("chunk_reason"))


def test_wt_keys_five_batch539():
    b = _base()
    assert set(b["per_doc"][0][
        "wall_time_seconds"]) == {
        "chunk", "chunk_reason", "parse",
        "parse_reason", "total"}


# ---------- metrics 宽 ----------

def test_metrics_extra_key_valid_batch539():
    _acc(lambda d: d["per_doc"][0]["metrics"].
        __setitem__("zz_metric",
                    {"value": 1, "reason": None}))


# ---------- ratio/sr/counts 全宽 ----------

def test_ratio_missing_macro_valid_batch539():
    _acc(lambda d: d["summary"]["ratio_macro_averages"]
        ["schema_valid"].pop("macro_average"))


def test_ratio_missing_ne_valid_batch539():
    _acc(lambda d: d["summary"]["ratio_macro_averages"]
        ["schema_valid"].pop("not_evaluated"))


def test_ratio_extra_key_valid_batch539():
    _acc(lambda d: d["summary"]["ratio_macro_averages"]
        ["schema_valid"].__setitem__("zz", 1))


def test_sr_missing_rate_valid_batch539():
    _acc(lambda d: d["summary"]["success_rates"]
        ["pipeline_success"].pop("rate"))


def test_sr_extra_key_valid_batch539():
    _acc(lambda d: d["summary"]["success_rates"]
        ["pipeline_success"].__setitem__("zz", 1))


def test_counts_missing_sum_valid_batch539():
    _acc(lambda d: d["summary"]["counts"]
        ["element_count_total"].pop("sum"))


def test_counts_extra_key_valid_batch539():
    _acc(lambda d: d["summary"]["counts"]
        ["element_count_total"].__setitem__("zz", 1))


# ---------- ef 严闭 ----------

def test_ef_extra_key_rejected_batch539():
    def mut(d):
        d["expected_failures"] = [
            {"doc_id": "x",
             "expected_error_code": "e",
             "actual_error_code": "e",
             "matches": True, "zz": 1}]
    _rej(mut,
         "Additional properties are not allowed "
         "('zz' was unexpected)",
         ["expected_failures", 0])


def test_ef_missing_matches_batch539():
    def mut(d):
        d["expected_failures"] = [
            {"doc_id": "x",
             "expected_error_code": "e",
             "actual_error_code": "e"}]
    _rej(mut, "'matches' is a required property",
         ["expected_failures", 0])


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch539():
    src = _src()
    assert "class EvalSchemaError(Exception):" \
        in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第七百八十三批 ----------

def test_source_no_eval_batch539():
    assert "eval(" not in _src()


def test_source_no_exec_batch539():
    assert "exec(" not in _src()


def test_source_no_compile_batch539():
    assert "compile(" not in _src()


def test_source_no_globals_batch539():
    assert "globals(" not in _src()


def test_source_no_locals_batch539():
    assert "locals(" not in _src()


def test_source_no_os_system_batch539():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch539():
    assert "subprocess" not in _src()


def test_source_no_popen_batch539():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch539():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch539():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch539():
    assert "socket" not in _src()


def test_source_no_requests_batch539():
    assert "requests" not in _src()


def test_source_no_urllib_batch539():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch539():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch539():
    assert "yield" not in _src()


def test_source_no_async_await_batch539():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch539():
    assert _src().count("open(") == 2
