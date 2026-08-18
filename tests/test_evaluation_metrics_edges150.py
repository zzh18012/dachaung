"""evaluation/metrics.py 第五百七十一轮 edges 测试（Round 1290）。

补强 edges149 未触及的角度（第六百六十二批，probe 实证）。

新角度（真实图片板 metrics 全貌）：
- **三型元素序**——图片先画
  （Do 在文本前）但元素序
  [heading, paragraph, image]
  ——文本按 y 序在前，图片
  追加末尾（元素序首锁）
- **图片元素体**——content
  None + resource_path 非
  空 + metadata {tag None,
  srcsize [2,2],
  extracted_to_disk True}
- **locator 几何**——cm 变换
  10 500 → bbox [10.0,
  250.0, 110.0, 300.0]
  （top-down 换算首锁）
- **图片不产块**——chunks 仍
  16；ecbt 三键 {heading 1,
  paragraph 1, image 1} /
  ect 3
- **irer 真渲染**——1.0；断
  resource_path → 0.0（磁盘
  存在性实检）
- **文本面无扰**——tpe/crir/
  msp/msr 全 1.0、hbc 1.0、
  plvr 三元素 1.0
- forbidden tokens 第七百四十九批（open 0）
"""

from __future__ import annotations

import copy
import inspect

import evaluation.metrics as metrics_mod
from app.pipeline import process_single
from evaluation.metrics import compute_automatic_metrics


def _image_pdf(content: bytes) -> bytes:
    img = bytes([255, 0, 0, 0, 255, 0,
                 0, 0, 255, 255, 255, 0])
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>"
            b"/XObject<</Im0 6 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(content)).encode()
            + b">>stream\n" + content + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        6: (b"<</Type/XObject/Subtype/Image/Width 2/Height 2"
            b"/ColorSpace/DeviceRGB/BitsPerComponent 8/Length "
            + str(len(img)).encode()
            + b">>stream\n" + img + b"\nendstream "),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xp = len(out)
    out += b"xref\n0 7\n0000000000 65535 f \n"
    for num in range(1, 7):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 7/Root 1 0 R>>\nstartxref\n"
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


LONG = " ".join("Word%d." % i for i in range(60))
HEAD = "A" * 80


def _doc(tmp_path):
    content = (b"q 100 0 0 50 10 500 cm /Im0 Do Q\n"
               + ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
                  % HEAD).encode()
               + ("BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
                  % LONG).encode())
    p = tmp_path / "imgcombo.pdf"
    p.write_bytes(_image_pdf(content))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=32)
    assert errors == []
    return doc.to_dict()


def _img(dd):
    for e in dd["elements"]:
        if e["type"] == "image":
            return e
    raise AssertionError("no image element")


def _m(dd):
    return compute_automatic_metrics(dd, None, "pdf", None)


# ---------- 元素序 ----------

def test_elements_three_types_order_batch488(tmp_path):
    dd = _doc(tmp_path)
    assert [e["type"] for e in dd["elements"]] == [
        "heading", "paragraph", "image"]


# ---------- 图片元素体 ----------

def test_image_content_none_batch488(tmp_path):
    dd = _doc(tmp_path)
    e = _img(dd)
    assert e["content"] is None
    assert e["resource_path"]


def test_image_metadata_batch488(tmp_path):
    e = _img(_doc(tmp_path))
    assert e["metadata"] == {
        "tag": None, "srcsize": [2, 2],
        "extracted_to_disk": True}


def test_image_locator_batch488(tmp_path):
    e = _img(_doc(tmp_path))
    assert e["source_locator"] == {
        "page": 1, "bbox": [10.0, 250.0, 110.0, 300.0]}


# ---------- 图片不产块 ----------

def test_image_no_chunk_batch488(tmp_path):
    assert len(_doc(tmp_path)["chunks"]) == 16


def test_ecbt_three_keys_batch488(tmp_path):
    m = _m(_doc(tmp_path))
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "paragraph": 1, "image": 1},
        "reason": None}


def test_ect_three_batch488(tmp_path):
    assert _m(_doc(tmp_path))[
        "element_count_total"] == {"value": 3, "reason": None}


# ---------- irer 真渲染 ----------

def test_irer_one_batch488(tmp_path):
    assert _m(_doc(tmp_path))[
        "image_resource_exists_ratio"] == {
        "value": 1.0, "reason": None}


def test_irer_broken_zero_batch488(tmp_path):
    dd = copy.deepcopy(_doc(tmp_path))
    _img(dd)["resource_path"] = "gone_dir/nope.png"
    assert _m(dd)["image_resource_exists_ratio"] == {
        "value": 0.0, "reason": None}


def test_resource_file_exists_batch488(tmp_path):
    from pathlib import Path
    e = _img(_doc(tmp_path))
    assert Path(e["resource_path"]).is_file()


# ---------- 文本面无扰 ----------

def test_text_face_untouched_batch488(tmp_path):
    m = _m(_doc(tmp_path))
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_precision"] == {
        "value": 1.0, "reason": None}
    assert m["text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}


def test_hbc_plvr_one_batch488(tmp_path):
    m = _m(_doc(tmp_path))
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}
    assert m["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}


def test_sdc_no_expectations_batch488(tmp_path):
    assert _m(_doc(tmp_path))["silent_drop_count"] == {
        "value": None, "reason": "no_expectations"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch488():
    src = _src()
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", ' \
           '"paragraph", "caption", "list_item")' in src
    assert 'if e.get("type") == "heading"' in src


# ---------- forbidden tokens 第七百四十九批 ----------

def test_source_no_eval_batch488():
    assert "eval(" not in _src()


def test_source_no_exec_batch488():
    assert "exec(" not in _src()


def test_source_no_compile_batch488():
    assert "compile(" not in _src()


def test_source_no_globals_batch488():
    assert "globals(" not in _src()


def test_source_no_locals_batch488():
    assert "locals(" not in _src()


def test_source_no_os_system_batch488():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch488():
    assert "subprocess" not in _src()


def test_source_no_popen_batch488():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch488():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch488():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch488():
    assert "socket" not in _src()


def test_source_no_requests_batch488():
    assert "requests" not in _src()


def test_source_no_urllib_batch488():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch488():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch488():
    assert "yield" not in _src()


def test_source_no_async_await_batch488():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch488():
    assert "open(" not in _src()
