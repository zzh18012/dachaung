"""evaluation/metrics.py 第五百六十五轮 edges 测试（Round 1254）。

补强 edges143 未触及的角度（第六百二十六批，probe 实证）。

新角度（双页 PDF 基板——前史全单页）：
- **页号分元素**——同 y 两行分属 page
  1 / page 2（page 是唯一区分位）
- **bbox 同 y**——两元素 bbox y 起
  点相同（跨页坐标不复用判据）
- **跨页块合并**——两页各一行 →
  单 chunk "Page one body text.
  Page two body text." 2 源（块层
  不设页界首锁）
- **metadata 无页键**——页数不入
  metadata
- forbidden tokens 第七百一十七批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _two_page_pdf() -> bytes:
    s1 = b"BT /F1 12 Tf 10 700 Td (Page one body text.) Tj ET\n"
    s2 = b"BT /F1 12 Tf 10 700 Td (Page two body text.) Tj ET\n"
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 6 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        6: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 7 0 R>>"),
        7: (b"<</Length " + str(len(s2)).encode()
            + b">>stream\n" + s2 + b"\nendstream "),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xp = len(out)
    out += b"xref\n0 8\n0000000000 65535 f \n"
    for num in range(1, 8):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 8/Root 1 0 R>>\nstartxref\n"
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


def _doc(tmp_path):
    from app.pipeline import process_single
    p = tmp_path / "two.pdf"
    p.write_bytes(_two_page_pdf())
    d, errors = process_single(p, tmp_path / "o.json",
                               parser_name="fallback",
                               max_chars=200)
    assert errors == []
    return d.to_dict()


# ---------- 页号分元素 ----------

def test_two_page_elements_batch452(tmp_path):
    dd = _doc(tmp_path)
    assert [e["content"] for e in dd["elements"]] == [
        "Page one body text.", "Page two body text."]


def test_pages_one_two_batch452(tmp_path):
    dd = _doc(tmp_path)
    assert [e["source_locator"]["page"] for e in dd["elements"]] == [
        1, 2]


def test_same_bbox_y_batch452(tmp_path):
    dd = _doc(tmp_path)
    b0 = dd["elements"][0]["source_locator"]["bbox"]
    b1 = dd["elements"][1]["source_locator"]["bbox"]
    assert b0[1] == b1[1]


def test_types_para_batch452(tmp_path):
    dd = _doc(tmp_path)
    assert [e["type"] for e in dd["elements"]] == [
        "paragraph", "paragraph"]


def test_element_ids_distinct_batch452(tmp_path):
    dd = _doc(tmp_path)
    assert [e["element_id"].split("::")[-1]
            for e in dd["elements"]] == ["e0000", "e0001"]


# ---------- 跨页块合并 ----------

def test_cross_page_chunk_merge_batch452(tmp_path):
    dd = _doc(tmp_path)
    assert len(dd["chunks"]) == 1
    assert dd["chunks"][0]["text"] == (
        "Page one body text. Page two body text.")
    assert len(dd["chunks"][0]["source_element_ids"]) == 2


# ---------- 指标层 ----------

def test_ect_two_batch452(tmp_path):
    m = compute_automatic_metrics(_doc(tmp_path), None, "pdf", None)
    assert m["element_count_total"] == {"value": 2, "reason": None}


def test_ecbt_two_para_batch452(tmp_path):
    m = compute_automatic_metrics(_doc(tmp_path), None, "pdf", None)
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 2}, "reason": None}


def test_pdf_locator_one_batch452(tmp_path):
    m = compute_automatic_metrics(_doc(tmp_path), None, "pdf", None)
    assert m["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}


def test_tpe_true_batch452(tmp_path):
    m = compute_automatic_metrics(_doc(tmp_path), None, "pdf", None)
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}


def test_intact_one_batch452(tmp_path):
    m = compute_automatic_metrics(_doc(tmp_path), None, "pdf", None)
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- metadata 无页键 ----------

def test_metadata_no_page_keys_batch452(tmp_path):
    dd = _doc(tmp_path)
    assert all("page" not in str(k) for k in dd["metadata"])


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch452():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", ' \
           '"paragraph", "caption", "list_item")' in src
    assert 'if e.get("type") == "heading"' in src


# ---------- forbidden tokens 第七百一十七批 ----------

def test_source_no_eval_batch452():
    assert "eval(" not in _src()


def test_source_no_exec_batch452():
    assert "exec(" not in _src()


def test_source_no_compile_batch452():
    assert "compile(" not in _src()


def test_source_no_globals_batch452():
    assert "globals(" not in _src()


def test_source_no_locals_batch452():
    assert "locals(" not in _src()


def test_source_no_os_system_batch452():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch452():
    assert "subprocess" not in _src()


def test_source_no_popen_batch452():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch452():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch452():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch452():
    assert "socket" not in _src()


def test_source_no_requests_batch452():
    assert "requests" not in _src()


def test_source_no_urllib_batch452():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch452():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch452():
    assert "yield" not in _src()


def test_source_no_async_await_batch452():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch452():
    assert "open(" not in _src()
