"""evaluation/runner.py 第六百六十八轮 edges 测试（Round 1303）。

补强 edges232 未触及的角度（第六百七十五批，probe 实证）。

新角度（categories/paired_with devset 语义 / 真文件 expected_failures）：
- **categories 并集排序**——
  {beta,alpha} ∪ {alpha,
  gamma} → categories_
  covered ['alpha','beta',
  'gamma']（去重排序首锁）
- **paired_with 组折叠**——
  3 文档 1 对 → content_
  group_count 2（对内合
  一首锁）
- **真坏文件 ef 命中**——
  非 PDF 字节 → actual
  pdfplumber_open_failed；
  期望同码 → matches True
  （真文件 ef 全链首锁，
  区别 edges111 mock 版）
- **期望落空**——好文档列
  ef → actual None +
  matches False（期望失败
  而成功首锁）
- **失败文档指标面**——
  error_code 有值 +
  pipeline_success False +
  element_count_total
  null/pipeline_failed
- forbidden tokens 第七百五十二批（open 2）
"""

from __future__ import annotations

import inspect
import json

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
STREAM = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
          % ("A" * 80)
          + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
          % LONG).encode()


def _board(tmp_path, docs, ef):
    (tmp_path / "good.pdf").write_bytes(_wrap(STREAM))
    (tmp_path / "bad.pdf").write_bytes(b"not a pdf at all")
    (tmp_path / "m.json").write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": docs,
        "expected_failures": ef}), encoding="utf-8")
    return load_manifest((tmp_path / "m.json"),
                         project_root=tmp_path)


# ---------- categories / paired_with ----------

def _cat_run(tmp_path):
    mf = _board(tmp_path, [
        {"doc_id": "g1", "path": "good.pdf",
         "source_type": "pdf",
         "categories": ["beta", "alpha"]},
        {"doc_id": "g2", "path": "good.pdf",
         "source_type": "pdf",
         "categories": ["alpha", "gamma"],
         "paired_with": "g1"},
        {"doc_id": "bad1", "path": "bad.pdf",
         "source_type": "pdf"}], [])
    return run_evaluation(mf, tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=32)


def test_categories_union_sorted_batch501(tmp_path):
    r = _cat_run(tmp_path)
    assert r["devset"]["categories_covered"] == [
        "alpha", "beta", "gamma"]


def test_group_collapse_batch501(tmp_path):
    r = _cat_run(tmp_path)
    assert r["devset"]["content_group_count"] == 2


def test_file_counts_batch501(tmp_path):
    r = _cat_run(tmp_path)
    assert r["devset"]["file_count"] == 3
    assert r["devset"]["pdf_count"] == 3


def test_mixed_success_batch501(tmp_path):
    r = _cat_run(tmp_path)
    assert r["summary"]["success_rates"][
        "pipeline_success"] == {
        "success_count": 2, "total": 3,
        "rate": 2 / 3}


# ---------- 真坏文件 ef 命中 ----------

def test_ef_match_true_batch501(tmp_path):
    mf = _board(tmp_path, [
        {"doc_id": "g1", "path": "good.pdf",
         "source_type": "pdf"},
        {"doc_id": "bad1", "path": "bad.pdf",
         "source_type": "pdf"}],
        [{"doc_id": "bad1", "path": "bad.pdf",
          "expected_error_code":
          "pdfplumber_open_failed"}])
    r = run_evaluation(mf, tmp_path / "r.json",
                       parser_name="fallback",
                       max_chars=32)
    assert r["expected_failures"] == [{
        "doc_id": "bad1",
        "expected_error_code": "pdfplumber_open_failed",
        "actual_error_code": "pdfplumber_open_failed",
        "matches": True}]


def test_ef_expect_success_miss_batch501(tmp_path):
    mf = _board(tmp_path, [
        {"doc_id": "g1", "path": "good.pdf",
         "source_type": "pdf"},
        {"doc_id": "bad1", "path": "bad.pdf",
         "source_type": "pdf"}],
        [{"doc_id": "g1", "path": "good.pdf",
          "expected_error_code":
          "pdfplumber_open_failed"}])
    r = run_evaluation(mf, tmp_path / "r.json",
                       parser_name="fallback",
                       max_chars=32)
    assert r["expected_failures"] == [{
        "doc_id": "g1",
        "expected_error_code": "pdfplumber_open_failed",
        "actual_error_code": None,
        "matches": False}]


# ---------- 失败文档指标面 ----------

def _bad_run(tmp_path):
    mf = _board(tmp_path, [
        {"doc_id": "g1", "path": "good.pdf",
         "source_type": "pdf"},
        {"doc_id": "bad1", "path": "bad.pdf",
         "source_type": "pdf"}], [])
    return run_evaluation(mf, tmp_path / "r.json",
                          parser_name="fallback",
                          max_chars=32)


def test_bad_doc_error_code_batch501(tmp_path):
    r = _bad_run(tmp_path)
    assert r["per_doc"][1]["metrics"]["error_code"] == {
        "value": "pdfplumber_open_failed",
        "reason": None}


def test_bad_doc_success_false_batch501(tmp_path):
    r = _bad_run(tmp_path)
    assert r["per_doc"][1]["metrics"][
        "pipeline_success"] == {"value": False,
                                "reason": None}


def test_bad_doc_metrics_null_batch501(tmp_path):
    r = _bad_run(tmp_path)
    m = r["per_doc"][1]["metrics"]
    assert m["element_count_total"] == {
        "value": None, "reason": "pipeline_failed"}
    assert m["text_preservation_equal"] == {
        "value": None, "reason": "pipeline_failed"}


def test_good_doc_error_none_batch501(tmp_path):
    r = _bad_run(tmp_path)
    assert r["per_doc"][0]["metrics"]["error_code"] == {
        "value": None, "reason": None}


def test_report_schema_valid_batch501(tmp_path):
    r = _bad_run(tmp_path)
    validate(r, "evaluation-report.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_key_counts_batch501():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("per_doc") == 12
    assert src.count("open(") == 2


# ---------- forbidden tokens 第七百五十二批 ----------

def test_source_no_eval_batch501():
    assert "eval(" not in _src()


def test_source_no_exec_batch501():
    assert "exec(" not in _src()


def test_source_no_compile_batch501():
    assert "compile(" not in _src()


def test_source_no_globals_batch501():
    assert "globals(" not in _src()


def test_source_no_locals_batch501():
    assert "locals(" not in _src()


def test_source_no_os_system_batch501():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch501():
    assert "subprocess" not in _src()


def test_source_no_popen_batch501():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch501():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch501():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch501():
    assert "socket" not in _src()


def test_source_no_requests_batch501():
    assert "requests" not in _src()


def test_source_no_urllib_batch501():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch501():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch501():
    assert "yield" not in _src()


def test_source_no_async_await_batch501():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_call_batch501():
    assert ".call(" not in _src()
