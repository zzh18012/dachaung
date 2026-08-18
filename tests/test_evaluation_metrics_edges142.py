"""evaluation/metrics.py 第五百六十三轮 edges 测试（Round 1244）。

补强 edges141 未触及的角度（第六百一十六批，probe 实证）。

新角度（行距 30/31 阈值 / 真实 PDF 启发式标题喂 hbc）：
- **行距 30 合并**——两 Tj 行
  gap 30 → 单元素 "Top line text
  here. Lower line text here."
  （fallback 行分组阈值下沿
  首锁）
- **行距 31 分列**——gap 31 →
  恰 2 元素（阈值精确翻转，
  probe 31-39 全 2）
- **真实 PDF hbc 因果链**——
  "SECTION OVERVIEW"（短行无
  句号）被启发式判 heading →
  hbc 分母收它 → 合并块首 id
  是它 → hbc 1.0（分类喂指标
  首锁；edges128 是 DOCX 真
  heading，此为 PDF 启发式变体）
- forbidden tokens 第七百零九批（open 0）
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _pdf(y2: int, top_text: str = "Top line text here.",
         lower_text: str = "Lower line text here.") -> bytes:
    s = (("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
          "BT /F1 12 Tf 10 %d Td (%s) Tj ET\n"
          % (top_text, y2, lower_text)).encode())
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


def _doc(tmp_path, y2):
    from app.pipeline import process_single
    p = tmp_path / "g.pdf"
    p.write_bytes(_pdf(y2))
    d, errors = process_single(p, tmp_path / "o.json",
                               parser_name="fallback",
                               max_chars=200)
    assert errors == []
    return d.to_dict()


def _heading_doc(tmp_path):
    from app.pipeline import process_single
    p = tmp_path / "h.pdf"
    p.write_bytes(_pdf(660, "SECTION OVERVIEW",
                       "Body sentence with a period."))
    d, errors = process_single(p, tmp_path / "oh.json",
                               parser_name="fallback",
                               max_chars=200)
    assert errors == []
    return d.to_dict()


# ---------- 行距 30 合并 ----------

def test_line_merge_gap30_batch442(tmp_path):
    dd = _doc(tmp_path, 670)
    assert len(dd["elements"]) == 1
    assert dd["elements"][0]["content"] == \
        "Top line text here. Lower line text here."


# ---------- 行距 31 分列 ----------

def test_line_split_gap31_batch442(tmp_path):
    dd = _doc(tmp_path, 669)
    assert len(dd["elements"]) == 2
    assert [e["content"] for e in dd["elements"]] == [
        "Top line text here.", "Lower line text here."]


def test_split_lines_merge_into_one_chunk_batch442(tmp_path):
    dd = _doc(tmp_path, 669)
    assert len(dd["chunks"]) == 1
    assert dd["chunks"][0]["text"] == \
        "Top line text here. Lower line text here."
    assert len(dd["chunks"][0]["source_element_ids"]) == 2


# ---------- 真实 PDF 启发式标题喂 hbc ----------

def test_heading_type_heuristic_batch442(tmp_path):
    dd = _heading_doc(tmp_path)
    assert [e["type"] for e in dd["elements"]] == [
        "heading", "paragraph"]


def test_heading_chunk_first_batch442(tmp_path):
    dd = _heading_doc(tmp_path)
    assert len(dd["chunks"]) == 1
    assert dd["chunks"][0]["source_element_ids"][0] == \
        dd["elements"][0]["element_id"]


def test_real_pdf_hbc_batch442(tmp_path):
    m = compute_automatic_metrics(
        _heading_doc(tmp_path), None, "pdf", None)
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


def test_real_pdf_pdf_locator_batch442(tmp_path):
    m = compute_automatic_metrics(
        _heading_doc(tmp_path), None, "pdf", None)
    assert m["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["docx_locator_valid_ratio"] == {
        "value": None, "reason": "not_docx_document"}


def test_real_pdf_ecbt_batch442(tmp_path):
    m = compute_automatic_metrics(
        _heading_doc(tmp_path), None, "pdf", None)
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "paragraph": 1},
        "reason": None}
    assert m["element_count_total"] == {"value": 2,
                                        "reason": None}


def test_real_pdf_preservation_batch442(tmp_path):
    m = compute_automatic_metrics(
        _heading_doc(tmp_path), None, "pdf", None)
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch442():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", ' \
           '"paragraph", "caption", "list_item")' in src
    assert 'if e.get("type") == "heading"' in src


# ---------- forbidden tokens 第七百零九批 ----------

def test_source_no_eval_batch442():
    assert "eval(" not in _src()


def test_source_no_exec_batch442():
    assert "exec(" not in _src()


def test_source_no_compile_batch442():
    assert "compile(" not in _src()


def test_source_no_globals_batch442():
    assert "globals(" not in _src()


def test_source_no_locals_batch442():
    assert "locals(" not in _src()


def test_source_no_os_system_batch442():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch442():
    assert "subprocess" not in _src()


def test_source_no_popen_batch442():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch442():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch442():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch442():
    assert "socket" not in _src()


def test_source_no_requests_batch442():
    assert "requests" not in _src()


def test_source_no_urllib_batch442():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch442():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch442():
    assert "yield" not in _src()


def test_source_no_async_await_batch442():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch442():
    assert "open(" not in _src()
