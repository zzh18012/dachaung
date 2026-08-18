"""evaluation/metrics.py 第五百六十九轮 edges 测试（Round 1278）。

补强 edges147 未触及的角度（第六百五十批，probe 实证）。

新角度（pdf_locator 分母全类型 / bbox 四类型门控）：
- **半降 0.5**——真 combo 板单
  元素 pop bbox / pop page /
  bbox 短 3 / bbox 字符串项 →
  全部恰 0.5（真板部分降级首锁，
  前史仅手造板 0.0/1.0 两端）
- **page 全类型必查**——
  header/image/footer 改型后
  pop page 仍 0.5（分母不挑型
  首锁）
- **bbox 四类型门控豁免**——
  header + bbox 字符串项 →
  1.0（非 bbox 类型免查首锁）
  vs caption + 同 bbox → 0.5
- **双元素全灭 0.0**——两元素
  pop page → 0.0
- **hbc 随型消失**——heading 改
  header → no_heading_elements
- forbidden tokens 第七百三十八批（open 0）
"""

from __future__ import annotations

import copy
import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


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
HEAD = "A" * 80


def _doc(tmp_path):
    from app.pipeline import process_single
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()
    p = tmp_path / "combo.pdf"
    p.write_bytes(_wrap(s))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=32)
    assert errors == []
    return doc.to_dict()


def _loc(base, fn):
    d = copy.deepcopy(base)
    fn(d)
    m = compute_automatic_metrics(d, None, "pdf", None)
    return m["pdf_locator_valid_ratio"]


# ---------- 基态 ----------

def test_base_ratio_one_batch476(tmp_path):
    assert _loc(_doc(tmp_path), lambda d: None) == {
        "value": 1.0, "reason": None}


def test_base_docx_null_batch476(tmp_path):
    m = compute_automatic_metrics(_doc(tmp_path), None,
                                  "pdf", None)
    assert m["docx_locator_valid_ratio"] == {
        "value": None, "reason": "not_docx_document"}


# ---------- 半降 0.5 ----------

def test_pop_bbox_half_batch476(tmp_path):
    assert _loc(_doc(tmp_path), lambda d: d["elements"][0][
        "source_locator"].pop("bbox")) == {
        "value": 0.5, "reason": None}


def test_pop_page_half_batch476(tmp_path):
    assert _loc(_doc(tmp_path), lambda d: d["elements"][0][
        "source_locator"].pop("page")) == {
        "value": 0.5, "reason": None}


def test_none_page_bbox_half_batch476(tmp_path):
    assert _loc(_doc(tmp_path), lambda d: d["elements"][0][
        "source_locator"].update(
            {"page": None, "bbox": None})) == {
        "value": 0.5, "reason": None}


def test_bbox_short3_half_batch476(tmp_path):
    assert _loc(_doc(tmp_path), lambda d: d["elements"][0][
        "source_locator"].update(
            {"bbox": [1, 2, 3]})) == {
        "value": 0.5, "reason": None}


def test_bbox_str_item_half_batch476(tmp_path):
    assert _loc(_doc(tmp_path), lambda d: d["elements"][0][
        "source_locator"].update(
            {"bbox": ["a", 1, 2, 3]})) == {
        "value": 0.5, "reason": None}


# ---------- page 全类型必查 ----------

def test_header_pop_page_half_batch476(tmp_path):
    assert _loc(_doc(tmp_path), lambda d: (
        d["elements"][0].update({"type": "header"}),
        d["elements"][0]["source_locator"].pop("page"))) == {
        "value": 0.5, "reason": None}


def test_image_pop_page_half_batch476(tmp_path):
    assert _loc(_doc(tmp_path), lambda d: (
        d["elements"][0].update({"type": "image"}),
        d["elements"][0]["source_locator"].pop("page"))) == {
        "value": 0.5, "reason": None}


def test_footer_pop_page_half_batch476(tmp_path):
    assert _loc(_doc(tmp_path), lambda d: (
        d["elements"][0].update({"type": "footer"}),
        d["elements"][0]["source_locator"].pop("page"))) == {
        "value": 0.5, "reason": None}


# ---------- bbox 四类型门控豁免 ----------

def test_header_bad_bbox_exempt_batch476(tmp_path):
    assert _loc(_doc(tmp_path), lambda d: (
        d["elements"][0].update({"type": "header"}),
        d["elements"][0]["source_locator"].update(
            {"bbox": ["a", 1, 2, 3]}))) == {
        "value": 1.0, "reason": None}


def test_caption_bad_bbox_counted_batch476(tmp_path):
    assert _loc(_doc(tmp_path), lambda d: (
        d["elements"][0].update({"type": "caption"}),
        d["elements"][0]["source_locator"].update(
            {"bbox": ["a", 1, 2, 3]}))) == {
        "value": 0.5, "reason": None}


def test_image_bad_bbox_exempt_batch476(tmp_path):
    assert _loc(_doc(tmp_path), lambda d: (
        d["elements"][0].update({"type": "image"}),
        d["elements"][0]["source_locator"].update(
            {"bbox": ["a", 1, 2, 3]}))) == {
        "value": 1.0, "reason": None}


# ---------- 双元素全灭 ----------

def test_both_pop_page_zero_batch476(tmp_path):
    assert _loc(_doc(tmp_path), lambda d: (
        d["elements"][0]["source_locator"].pop("page"),
        d["elements"][1]["source_locator"].pop("page"))) == {
        "value": 0.0, "reason": None}


# ---------- hbc 随型消失 ----------

def test_hbc_no_heading_after_retype_batch476(tmp_path):
    d = _doc(tmp_path)
    d["elements"][0]["type"] = "header"
    m = compute_automatic_metrics(d, None, "pdf", None)
    assert m["heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}


def test_hbc_one_at_base_batch476(tmp_path):
    m = compute_automatic_metrics(_doc(tmp_path), None,
                                  "pdf", None)
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch476():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", ' \
           '"paragraph", "caption", "list_item")' in src
    assert 'if e.get("type") == "heading"' in src


# ---------- forbidden tokens 第七百三十八批 ----------

def test_source_no_eval_batch476():
    assert "eval(" not in _src()


def test_source_no_exec_batch476():
    assert "exec(" not in _src()


def test_source_no_compile_batch476():
    assert "compile(" not in _src()


def test_source_no_globals_batch476():
    assert "globals(" not in _src()


def test_source_no_locals_batch476():
    assert "locals(" not in _src()


def test_source_no_os_system_batch476():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch476():
    assert "subprocess" not in _src()


def test_source_no_popen_batch476():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch476():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch476():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch476():
    assert "socket" not in _src()


def test_source_no_requests_batch476():
    assert "requests" not in _src()


def test_source_no_urllib_batch476():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch476():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch476():
    assert "yield" not in _src()


def test_source_no_async_await_batch476():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch476():
    assert "open(" not in _src()
