"""evaluation/runner.py 第六百七十三轮 edges 测试（Round 1333）。

补强 edges237 未触及的角度（第七百零五批，probe 实证）。

新角度（ef 命中面 / 垃圾 PDF / 报告回读）：
- **ef 命中 true**——
  expected=file_not_
  found 恰等 actual →
  matches true
  （runner 级首锁）
- **ef 错码 false**
  ——expected
  wrong_code → false
- **垃圾 PDF**——
  b'not a pdf' →
  actual
  pdfplumber_open_
  failed（错误码
  首锁）
- **ef 条目 4 键**——
  {actual_error_
  code, doc_id,
  expected_error_
  code, matches}
- **报告回读相等**
  ——output_path
  落盘 JSON ==
  返回 dict（首次
  回读锁）
- **ef 不扰主面**——
  per_doc 1 条、
  success 1/1
- forbidden tokens 第七百七十七批（open 2）
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import evaluation.runner as runner_mod
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
ONEP = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
        % LONG).encode()


def _run(tmp_path):
    (tmp_path / "c.pdf").write_bytes(_wrap(ONEP))
    (tmp_path / "bad.pdf").write_bytes(
        b"not a pdf at all")
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "g1", "path": "c.pdf",
             "source_type": "pdf"}],
        "expected_failures": [
            {"doc_id": "ef1", "path": "nope.pdf",
             "expected_error_code":
                 "file_not_found"},
            {"doc_id": "ef2", "path": "nope.pdf",
             "expected_error_code":
                 "wrong_code"},
            {"doc_id": "ef3", "path": "bad.pdf",
             "expected_error_code": "parse_error",
             "source_type": "other"}]}),
        encoding="utf-8")
    mf = load_manifest(tmp_path / "m.json",
                       project_root=tmp_path)
    return run_evaluation(mf, tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=32)


# ---------- ef 命中 true ----------

def test_ef_hit_true_batch531(tmp_path):
    r = _run(tmp_path)
    assert r["expected_failures"][0] == {
        "doc_id": "ef1",
        "expected_error_code": "file_not_found",
        "actual_error_code": "file_not_found",
        "matches": True}


# ---------- ef 错码 false ----------

def test_ef_wrong_code_false_batch531(tmp_path):
    r = _run(tmp_path)
    ef = r["expected_failures"][1]
    assert ef["expected_error_code"] \
        == "wrong_code"
    assert ef["actual_error_code"] \
        == "file_not_found"
    assert ef["matches"] is False


# ---------- 垃圾 PDF ----------

def test_garbage_pdf_error_code_batch531(tmp_path):
    r = _run(tmp_path)
    assert r["expected_failures"][2][
        "actual_error_code"] == \
        "pdfplumber_open_failed"


def test_garbage_pdf_matches_false_batch531(
        tmp_path):
    r = _run(tmp_path)
    assert r["expected_failures"][2][
        "matches"] is False


# ---------- ef 条目 4 键 ----------

def test_ef_entry_keys_batch531(tmp_path):
    r = _run(tmp_path)
    for ef in r["expected_failures"]:
        assert set(ef) == {
            "actual_error_code", "doc_id",
            "expected_error_code", "matches"}


def test_ef_count_three_batch531(tmp_path):
    assert len(_run(tmp_path)[
        "expected_failures"]) == 3


# ---------- 报告回读相等 ----------

def test_report_round_trip_batch531(tmp_path):
    r = _run(tmp_path)
    on_disk = json.loads(
        (tmp_path / "r.json").read_text(
            encoding="utf-8"))
    assert on_disk == r


def test_report_file_exists_batch531(tmp_path):
    _run(tmp_path)
    assert (tmp_path / "r.json").is_file()


# ---------- ef 不扰主面 ----------

def test_per_doc_untouched_batch531(tmp_path):
    r = _run(tmp_path)
    assert len(r["per_doc"]) == 1
    assert r["per_doc"][0]["doc_id"] == "g1"


def test_success_untouched_batch531(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["success_rates"][
        "pipeline_success"] == {
        "success_count": 1, "total": 1,
        "rate": 1.0}


def test_report_schema_batch531(tmp_path):
    validate(_run(tmp_path),
             "evaluation-report.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_counts_batch531():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("per_doc") == 12
    assert src.count("open(") == 2


# ---------- forbidden tokens 第七百七十七批 ----------

def test_source_no_eval_batch531():
    assert "eval(" not in _src()


def test_source_no_exec_batch531():
    assert "exec(" not in _src()


def test_source_no_compile_batch531():
    assert "compile(" not in _src()


def test_source_no_globals_batch531():
    assert "globals(" not in _src()


def test_source_no_locals_batch531():
    assert "locals(" not in _src()


def test_source_no_os_system_batch531():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch531():
    assert "subprocess" not in _src()


def test_source_no_popen_batch531():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch531():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch531():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch531():
    assert "socket" not in _src()


def test_source_no_requests_batch531():
    assert "requests" not in _src()


def test_source_no_urllib_batch531():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch531():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch531():
    assert "yield" not in _src()


def test_source_no_async_await_batch531():
    assert "async " not in _src()
    assert "await " not in _src()
