"""evaluation/runner.py 第六百五十八轮 edges 测试（Round 1245）。

补强 edges222 未触及的角度（第六百一十七批，probe 实证）。

新角度（行距阈值 runner 可见性 / 真实 PDF hbc）：
- **阈值对的 runner 呈现**——同
  板 gap 30 vs 31 → ect 1 vs 2
  （解析层阈值在 runner 指标层
  显形首锁）
- **真实 PDF hbc 1.0**——
  "SECTION OVERVIEW"（短行无
  句号）启发式判 heading → 合并
  块首 id → hbc 1.0 + summary
  macro {1.0, 1, 0}（DOCX 真
  heading 之外的 PDF 启发式变体
  首锁）
- **wall_time 五键契约**——在
  PDF 板上复证 parse/chunk None
  + not_instrumented
- forbidden tokens 第七百一十批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


def _pdf(y2: int, top: str, low: str) -> bytes:
    s = (("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
          "BT /F1 12 Tf 10 %d Td (%s) Tj ET\n"
          % (top, y2, low)).encode())
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: (b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"),
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


def _board(tmp_path, doc_id, y2, top, low):
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "s" / (doc_id + ".pdf")).write_bytes(
        _pdf(y2, top, low))
    mf = tmp_path / (doc_id + ".json")
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id,
                       "path": "s/%s.pdf" % doc_id,
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 阈值对的 runner 呈现 ----------

def test_gap30_ect_one_batch443(tmp_path):
    r = run_evaluation(
        _board(tmp_path, "g30", 670,
               "Top line text here.", "Lower line text here."),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    assert r["per_doc"][0]["metrics"]["element_count_total"] == {
        "value": 1, "reason": None}


def test_gap31_ect_two_batch443(tmp_path):
    r = run_evaluation(
        _board(tmp_path, "g31", 669,
               "Top line text here.", "Lower line text here."),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    assert r["per_doc"][0]["metrics"]["element_count_total"] == {
        "value": 2, "reason": None}


def test_gap30_summary_sum_batch443(tmp_path):
    r = run_evaluation(
        _board(tmp_path, "g30", 670,
               "Top line text here.", "Lower line text here."),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    assert r["summary"]["counts"]["element_count_total"] == {
        "sum": 1, "participating_docs": 1}


# ---------- 真实 PDF hbc ----------

def test_heading_hbc_batch443(tmp_path):
    r = run_evaluation(
        _board(tmp_path, "hh", 660,
               "SECTION OVERVIEW", "Body sentence with a period."),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "paragraph": 1},
        "reason": None}


def test_summary_hbc_macro_batch443(tmp_path):
    r = run_evaluation(
        _board(tmp_path, "hh", 660,
               "SECTION OVERVIEW", "Body sentence with a period."),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    assert r["summary"]["ratio_macro_averages"][
        "heading_boundary_compliance"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 0}


def test_source_type_pdf_batch443(tmp_path):
    r = run_evaluation(
        _board(tmp_path, "hh", 660,
               "SECTION OVERVIEW", "Body sentence with a period."),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    assert r["per_doc"][0]["source_type"] == "pdf"
    assert r["per_doc"][0]["doc_id"] == "hh"


# ---------- wall_time 五键契约 ----------

def test_wall_time_keys_batch443(tmp_path):
    r = run_evaluation(
        _board(tmp_path, "hh", 660,
               "SECTION OVERVIEW", "Body sentence with a period."),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    wt = r["per_doc"][0]["wall_time_seconds"]
    assert sorted(wt.keys()) == [
        "chunk", "chunk_reason", "parse", "parse_reason",
        "total"]
    assert wt["parse"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk"] is None
    assert wt["chunk_reason"] == "not_instrumented"
    assert isinstance(wt["total"], float)
    assert wt["total"] >= 0


def test_hh_tpe_batch443(tmp_path):
    r = run_evaluation(
        _board(tmp_path, "hh", 660,
               "SECTION OVERVIEW", "Body sentence with a period."),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["schema_valid"] == {"value": True, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch443():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第七百一十批 ----------

def test_source_no_eval_batch443():
    assert "eval(" not in _src()


def test_source_no_exec_batch443():
    assert "exec(" not in _src()


def test_source_no_compile_batch443():
    assert "compile(" not in _src()


def test_source_no_globals_batch443():
    assert "globals(" not in _src()


def test_source_no_locals_batch443():
    assert "locals(" not in _src()


def test_source_no_os_system_batch443():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch443():
    assert "subprocess" not in _src()


def test_source_no_popen_batch443():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch443():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch443():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch443():
    assert "socket" not in _src()


def test_source_no_requests_batch443():
    assert "requests" not in _src()


def test_source_no_urllib_batch443():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch443():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch443():
    assert "yield" not in _src()


def test_source_no_async_await_batch443():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch443():
    assert _src().count("open(") == 2
