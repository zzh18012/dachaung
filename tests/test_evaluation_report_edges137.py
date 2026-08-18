"""evaluation/report.py 第五百六十八轮 edges 测试（Round 1264）。

补强 edges136 未触及的角度（第六百三十六批，probe 实证）。

新角度（报告各节插入序 / 异类型板序列化）：
- **summary 插入序首锁**——
  ['counts', 'success_rates',
  'ratio_macro_averages',
  'silent_drop_total']（前史全
  set 等值，插入序列表首锁）
- **per_doc metrics 20 键插入序**
  ——pipeline_success 起始 →
  chunk_boundary_f1 收尾（磁盘
  序列化后仍保序）
- **ratio 12 键插入序**——
  schema_valid 起始 →
  chunk_boundary_f1 收尾（edges135
  锁的是 sorted 集，插入序首锁）
- **devset 六键插入序 + 精确值**
  ——status/file_count/
  content_group_count/pdf_count/
  docx_count/categories_covered
  （空 categories 首锁）
- **部分参与聚合经报告**——hbc
  {macro 1.0, participating 2,
  not_evaluated 2}（4 板中 2 排除）
- forbidden tokens 第七百二十五批（open 0）
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


def _one(text: str) -> bytes:
    return _wrap(("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
                  % text).encode())


MIX_TEXTS = ["Figure 1 An overview diagram.", "A" * 80,
             "Is this a heading?"]


def _board(tmp_path):
    (tmp_path / "figcap.pdf").write_bytes(
        _one("Figure 1 An overview diagram."))
    (tmp_path / "hh80.pdf").write_bytes(_one("A" * 80))
    (tmp_path / "qq.pdf").write_bytes(_one("Is this a heading?"))
    ys = [700, 660, 620]
    s = "".join("BT /F1 12 Tf 10 %d Td (%s) Tj ET\n" % (y, t)
                for y, t in zip(ys, MIX_TEXTS)).encode()
    (tmp_path / "mix.pdf").write_bytes(_wrap(s))
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": did, "path": "%s.pdf" % did,
             "source_type": "pdf"}
            for did in ("figcap", "hh80", "qq", "mix")]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


def _run(tmp_path):
    return run_evaluation(_board(tmp_path), tmp_path / "r.json",
                          parser_name="fallback", max_chars=200)


def _disk(tmp_path):
    return json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"))


# ---------- summary 插入序 ----------

def test_summary_key_order_batch462(tmp_path):
    assert list(_run(tmp_path)["summary"].keys()) == [
        "counts", "success_rates", "ratio_macro_averages",
        "silent_drop_total"]


def test_file_summary_key_order_batch462(tmp_path):
    _run(tmp_path)
    on_disk = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"),
        object_pairs_hook=list)
    summary = [v for k, v in on_disk if k == "summary"][0]
    assert [k for k, _ in summary] == [
        "counts", "success_rates", "ratio_macro_averages",
        "silent_drop_total"]


# ---------- per_doc metrics 20 键插入序 ----------

METRIC_ORDER = [
    "pipeline_success", "error_code", "schema_valid",
    "element_count_total", "element_count_by_type",
    "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
    "image_resource_exists_ratio", "chunk_reference_intact_ratio",
    "text_preservation_equal", "text_char_multiset_precision",
    "text_char_multiset_recall", "heading_boundary_compliance",
    "silent_drop_count", "figure_caption_precision",
    "figure_caption_recall", "figure_caption_f1",
    "chunk_boundary_precision", "chunk_boundary_recall",
    "chunk_boundary_f1"]


def test_metrics_key_order_twenty_batch462(tmp_path):
    assert list(_run(tmp_path)["per_doc"][0]["metrics"].keys()) == \
        METRIC_ORDER


def test_metrics_key_order_on_disk_batch462(tmp_path):
    _run(tmp_path)
    on_disk = json.loads(
        (tmp_path / "r.json").read_text(encoding="utf-8"),
        object_pairs_hook=list)
    per_doc = [v for k, v in on_disk if k == "per_doc"][0]
    metrics = [v for k, v in per_doc[0] if k == "metrics"][0]
    assert [k for k, _ in metrics] == METRIC_ORDER


# ---------- ratio 12 键插入序 ----------

RATIO_ORDER = [
    "schema_valid", "pdf_locator_valid_ratio",
    "docx_locator_valid_ratio", "image_resource_exists_ratio",
    "chunk_reference_intact_ratio", "text_preservation_equal",
    "text_char_multiset_precision", "text_char_multiset_recall",
    "heading_boundary_compliance", "chunk_boundary_precision",
    "chunk_boundary_recall", "chunk_boundary_f1"]


def test_ratio_key_order_twelve_batch462(tmp_path):
    assert list(_run(tmp_path)["summary"][
        "ratio_macro_averages"].keys()) == RATIO_ORDER


# ---------- devset 六键 ----------

def test_devset_exact_batch462(tmp_path):
    assert _run(tmp_path)["devset"] == {
        "status": "incomplete", "file_count": 4,
        "content_group_count": 4, "pdf_count": 4,
        "docx_count": 0, "categories_covered": []}


def test_devset_key_order_batch462(tmp_path):
    assert list(_run(tmp_path)["devset"].keys()) == [
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered"]


# ---------- expected_failures ----------

def test_expected_failures_empty_batch462(tmp_path):
    assert _run(tmp_path)["expected_failures"] == []


# ---------- 部分参与聚合经报告 ----------

def test_hbc_partial_participation_batch462(tmp_path):
    assert _run(tmp_path)["summary"]["ratio_macro_averages"][
        "heading_boundary_compliance"] == {
        "macro_average": 1.0, "participating_docs": 2,
        "not_evaluated": 2}


def test_counts_sum_six_batch462(tmp_path):
    assert _run(tmp_path)["summary"]["counts"] == {
        "element_count_total": {"sum": 6, "participating_docs": 4}}


def test_success_four_batch462(tmp_path):
    assert _run(tmp_path)["summary"]["success_rates"] == {
        "pipeline_success": {"success_count": 4, "total": 4,
                             "rate": 1.0}}


# ---------- 往返 + ect 序列化 ----------

def test_round_trip_equal_batch462(tmp_path):
    r = _run(tmp_path)
    assert _disk(tmp_path) == r


def test_ect_values_serialized_batch462(tmp_path):
    assert [p["metrics"]["element_count_by_type"]["value"]
            for p in _run(tmp_path)["per_doc"]] == [
        {"caption": 1}, {"heading": 1}, {"paragraph": 1},
        {"caption": 1, "heading": 1, "paragraph": 1}]


def test_ect_mix_key_order_batch462(tmp_path):
    ect = _run(tmp_path)["per_doc"][3]["metrics"][
        "element_count_by_type"]["value"]
    assert list(ect.keys()) == ["caption", "heading", "paragraph"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch462():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src


# ---------- forbidden tokens 第七百二十五批 ----------

def test_source_no_eval_batch462():
    assert "eval(" not in _src()


def test_source_no_exec_batch462():
    assert "exec(" not in _src()


def test_source_no_compile_batch462():
    assert "compile(" not in _src()


def test_source_no_globals_batch462():
    assert "globals(" not in _src()


def test_source_no_locals_batch462():
    assert "locals(" not in _src()


def test_source_no_os_system_batch462():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch462():
    assert ".call(" not in _src()


def test_source_no_popen_batch462():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch462():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch462():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch462():
    assert "socket" not in _src()


def test_source_no_requests_batch462():
    assert "requests" not in _src()


def test_source_no_urllib_batch462():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch462():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch462():
    assert "yield" not in _src()


def test_source_no_async_await_batch462():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch462():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch462():
    assert _src().count("subprocess.run") == 2
