"""evaluation/schema.py 第五百八十四轮 edges 测试（Round 1323）。

补强 edges148 未触及的角度（第六百九十五批，probe 实证）。

新角度（evaluation-report.schema.json 真报告变异面）：
- **版本 const**——
  report_version '1.0'
  → "'1.1' was
  expected"（版本锁
  1.1 首锁）
- **根必填严闭**——
  provenance /
  per_doc / summary
  缺键均 required @
  []；顶层额外键拒
- **per_doc 面**——
  数组型 + 条目必填
  [doc_id, metrics] +
  条目严闭 + metrics
  对象型
- **devset / ef 型**——
  devset 对象、
  expected_failures
  数组；ef 可选（缺键
  VALID）
- **provenance 严闭**
  ——额外键拒
- **键集锁**——
  per_doc[0] 恰 4 键；
  provenance 9 键
  （evaluator_version
  / git_commit /
  max_chars 等）
- forbidden tokens 第七百六十八批（open 2）
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
from evaluation.schema import EvalSchemaError, validate


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


def _base():
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "c.pdf").write_bytes(_wrap(STREAM))
        (tp / "m.json").write_text(json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [{"doc_id": "d1", "path": "c.pdf",
                           "source_type": "pdf"}]}),
            encoding="utf-8")
        mf = load_manifest(tp / "m.json",
                           project_root=tp)
        return run_evaluation(mf, tp / "r.json",
                              parser_name="fallback",
                              max_chars=32)


def _rej(base, mutate, message, path):
    d = copy.deepcopy(base)
    mutate(d)
    try:
        validate(d, "evaluation-report.schema.json")
    except EvalSchemaError as e:
        assert e.errors[0]["message"] == message
        assert list(e.errors[0]["path"]) == path
    else:
        raise AssertionError("expected rejection")


def _acc(base, mutate):
    d = copy.deepcopy(base)
    mutate(d)
    validate(d, "evaluation-report.schema.json")


# ---------- 版本 const ----------

def test_version_const_batch521():
    b = _base()
    _rej(b, lambda d: d.__setitem__("report_version",
                                    "1.0"),
         "'1.1' was expected", ["report_version"])


def test_version_baseline_batch521():
    assert _base()["report_version"] == "1.1"


# ---------- 根必填严闭 ----------

def test_missing_provenance_batch521():
    b = _base()
    _rej(b, lambda d: d.pop("provenance"),
         "'provenance' is a required property", [])


def test_missing_per_doc_batch521():
    b = _base()
    _rej(b, lambda d: d.pop("per_doc"),
         "'per_doc' is a required property", [])


def test_missing_summary_batch521():
    b = _base()
    _rej(b, lambda d: d.pop("summary"),
         "'summary' is a required property", [])


def test_root_extra_key_batch521():
    b = _base()
    _rej(b, lambda d: d.__setitem__("zz", 1),
         "Additional properties are not allowed "
         "('zz' was unexpected)", [])


# ---------- per_doc 面 ----------

def test_per_doc_string_rejected_batch521():
    b = _base()
    _rej(b, lambda d: d.__setitem__("per_doc", "x"),
         "'x' is not of type 'array'", ["per_doc"])


def test_per_doc_entry_missing_doc_id_batch521():
    b = _base()
    _rej(b, lambda d: d["per_doc"][0].pop("doc_id"),
         "'doc_id' is a required property",
         ["per_doc", 0])


def test_per_doc_entry_missing_metrics_batch521():
    b = _base()
    _rej(b, lambda d: d["per_doc"][0].pop("metrics"),
         "'metrics' is a required property",
         ["per_doc", 0])


def test_per_doc_entry_extra_key_batch521():
    b = _base()
    _rej(b, lambda d: d["per_doc"][0].__setitem__(
             "zz", 1),
         "Additional properties are not allowed "
         "('zz' was unexpected)", ["per_doc", 0])


def test_metrics_string_rejected_batch521():
    b = _base()
    _rej(b, lambda d: d["per_doc"][0].__setitem__(
             "metrics", "x"),
         "'x' is not of type 'object'",
         ["per_doc", 0, "metrics"])


# ---------- devset / ef 型 ----------

def test_devset_string_rejected_batch521():
    b = _base()
    _rej(b, lambda d: d.__setitem__("devset", "x"),
         "'x' is not of type 'object'", ["devset"])


def test_ef_string_rejected_batch521():
    b = _base()
    _rej(b, lambda d: d.__setitem__(
             "expected_failures", "x"),
         "'x' is not of type 'array'",
         ["expected_failures"])


def test_ef_missing_valid_batch521():
    b = _base()
    _acc(b, lambda d: d.pop("expected_failures"))


# ---------- provenance 严闭 ----------

def test_provenance_extra_key_batch521():
    b = _base()
    _rej(b, lambda d: d["provenance"].__setitem__(
             "zz", 1),
         "Additional properties are not allowed "
         "('zz' was unexpected)", ["provenance"])


def test_summary_string_rejected_batch521():
    b = _base()
    _rej(b, lambda d: d.__setitem__("summary", "x"),
         "'x' is not of type 'object'", ["summary"])


# ---------- 键集锁 ----------

def test_per_doc_entry_keys_batch521():
    b = _base()
    assert set(b["per_doc"][0]) == {
        "doc_id", "metrics", "source_type",
        "wall_time_seconds"}


def test_provenance_keys_batch521():
    b = _base()
    assert set(b["provenance"]) == {
        "dependencies", "evaluator_version",
        "git_commit", "git_dirty", "max_chars",
        "parser_name", "parser_version",
        "report_version", "run_timestamp_iso"}


def test_summary_keys_batch521():
    b = _base()
    assert set(b["summary"]) == {
        "counts", "ratio_macro_averages",
        "silent_drop_total", "success_rates"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch521():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第七百六十八批 ----------

def test_source_no_eval_batch521():
    assert "eval(" not in _src()


def test_source_no_exec_batch521():
    assert "exec(" not in _src()


def test_source_no_compile_batch521():
    assert "compile(" not in _src()


def test_source_no_globals_batch521():
    assert "globals(" not in _src()


def test_source_no_locals_batch521():
    assert "locals(" not in _src()


def test_source_no_os_system_batch521():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch521():
    assert "subprocess" not in _src()


def test_source_no_popen_batch521():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch521():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch521():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch521():
    assert "socket" not in _src()


def test_source_no_requests_batch521():
    assert "requests" not in _src()


def test_source_no_urllib_batch521():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch521():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch521():
    assert "yield" not in _src()


def test_source_no_async_await_batch521():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch521():
    assert _src().count("open(") == 2
