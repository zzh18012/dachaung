r"""app/parsers/fallback_parser.py 边角测试 - 第十九轮（Round 1404）。

新角度（probe 实证）两个未锁 PDF 几何事实：
- 非零 MediaBox 起点 [50 50 562 742]：bbox 的 x0 用 Td 绝对
  坐标（起点不减）、top 按 box 高 692 算（792-700 与
  692-600 同得 82.484）——起点被忽略、高度被尊重
- 段落分组按页隔离：页 1 底 + 页 2 顶的同缩进文字不跨页
  合并（两元素各自 page 1/2、各自 bbox 聚合）；但 chunk
  层仍把两页段落并进同一 chunk（空格连接、refs 2）
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _build(pages, box):
    n = len(pages)
    page_ids = [3 + i * 2
                for i in range(n)]
    content_ids = [4 + i * 2
                   for i in range(n)]
    font_id = 3 + n * 2
    objs = {
        font_id: (b"<< /Type /Font /Subtype "
                  b"/Type1 /BaseFont "
                  b"/Helvetica >>"),
        1: (b"<< /Type /Catalog "
            b"/Pages 2 0 R >>")}
    kids = " ".join(
        f"{pid} 0 R" for pid in page_ids)
    objs[2] = (f"<< /Type /Pages /Kids "
               f"[{kids}] /Count {n} >>"
               ).encode()
    for i, lines in enumerate(pages):
        pid = page_ids[i]
        cid = content_ids[i]
        objs[pid] = (
            f"<< /Type /Page /Parent "
            f"2 0 R /MediaBox {box} "
            f"/Resources << /Font << /F1 "
            f"{font_id} 0 R >> >> "
            f"/Contents {cid} 0 R >>"
        ).encode()
        stream = " ".join(
            f"BT /F1 12 Tf {x} {y} "
            f"Td ({t}) Tj ET"
            for (x, y, t) in lines
        ).encode()
        objs[cid] = (
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n" + stream
            + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += (f"{oid} 0 obj\n".encode()
                + objs[oid]
                + b"\nendobj\n")
    xref_pos = len(out)
    maxid = max(objs)
    out += (f"xref\n0 {maxid + 1}\n"
            ).encode() \
        + b"0000000000 65535 f \n"
    for oid in range(1, maxid + 1):
        out += (
            f"{offsets[oid]:010d} "
            f"00000 n \n".encode()
            if oid in offsets
            else b"0000000000 65535 f \n")
    out += (f"trailer\n<< /Size "
            f"{maxid + 1} /Root 1 0 R "
            f">>\nstartxref\n{xref_pos}"
            f"\n%%EOF").encode()
    return bytes(out)


_BOX_PAGES = [[
    (100, 600, "Boxed heading"),
    (100, 560,
     "Boxed body text here.")]]
_BOX = "[50 50 562 742]"

P1 = ("Cross page paragraph part "
      "one with some continuing "
      "words on the first page.")
P2 = ("Cross page paragraph part "
      "two picks up words on the "
      "second page here.")
_CROSS_PAGES = [
    [(72, 100,
      "Cross page paragraph part "
      "one with some"),
     (72, 86,
      "continuing words on the "
      "first page.")],
    [(72, 700,
      "Cross page paragraph part "
      "two picks up"),
     (72, 686,
      "words on the second page "
      "here.")]]


def _parse(tmp_path, pages, box,
           name):
    p = tmp_path / name
    p.write_bytes(_build(pages, box))
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- 非零 MediaBox 起点 ----------

def test_box_elements(tmp_path):
    doc = _parse(tmp_path,
                 _BOX_PAGES, _BOX,
                 "box.pdf")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "Boxed heading"),
        ("paragraph",
         "Boxed body text here.")]


def test_box_heading_bbox(tmp_path):
    doc = _parse(tmp_path,
                 _BOX_PAGES, _BOX,
                 "box.pdf")
    assert doc.elements[
        0].source_locator == {
        "page": 1,
        "bbox": [100.0,
                 82.48400000000004,
                 180.052,
                 94.48400000000004]}


def test_box_paragraph_bbox(tmp_path):
    doc = _parse(tmp_path,
                 _BOX_PAGES, _BOX,
                 "box.pdf")
    assert doc.elements[
        1].source_locator == {
        "page": 1,
        "bbox": [100.0,
                 122.48400000000004,
                 216.736,
                 134.48399999999998]}


def test_box_x_origin_ignored(tmp_path):
    doc = _parse(tmp_path,
                 _BOX_PAGES, _BOX,
                 "box.pdf")
    for e in doc.elements:
        assert e.source_locator[
            "bbox"][0] == 100.0


def test_box_top_uses_box_height(
        tmp_path):
    """box 高 692：Td y=600 的 top 与
    792 页 Td y=700 同为 82.484——
    起点不减、高度生效。"""
    doc = _parse(tmp_path,
                 _BOX_PAGES, _BOX,
                 "box.pdf")
    assert doc.elements[
        0].source_locator["bbox"][1] \
        == 82.48400000000004


def test_box_schema_valid(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path,
                 _BOX_PAGES, _BOX,
                 "box.pdf")
    assert is_valid(doc.to_dict())


def test_box_no_warnings(tmp_path):
    doc = _parse(tmp_path,
                 _BOX_PAGES, _BOX,
                 "box.pdf")
    assert doc.warnings == []


# ---------- 跨页段落 ----------

def test_cross_two_paragraph_elements(
        tmp_path):
    doc = _parse(tmp_path,
                 _CROSS_PAGES,
                 "[0 0 612 792]",
                 "cross.pdf")
    assert [e.type for e in
            doc.elements] == [
        "paragraph", "paragraph"]
    assert [e.content for e in
            doc.elements] == [P1, P2]


def test_cross_grouping_page_scoped(
        tmp_path):
    """页 1 两行合成一元素、页 2 两行
    合成另一元素——不跨页合并。"""
    doc = _parse(tmp_path,
                 _CROSS_PAGES,
                 "[0 0 612 792]",
                 "cross.pdf")
    assert len(doc.elements) == 2
    assert doc.elements[
        0].content == P1
    assert doc.elements[
        1].content == P2


def test_cross_locators(tmp_path):
    doc = _parse(tmp_path,
                 _CROSS_PAGES,
                 "[0 0 612 792]",
                 "cross.pdf")
    assert [e.source_locator["page"]
            for e in doc.elements
            ] == [1, 2]


def test_cross_bbox_aggregates(
        tmp_path):
    doc = _parse(tmp_path,
                 _CROSS_PAGES,
                 "[0 0 612 792]",
                 "cross.pdf")
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 682.484, 296.1,
        708.484]
    assert doc.elements[
        1].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        284.76,
        108.48400000000004]


def test_cross_chunk_combines_pages(
        tmp_path):
    p = tmp_path / "cross.pdf"
    p.write_bytes(_build(
        _CROSS_PAGES,
        "[0 0 612 792]"))
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert len(doc.chunks) == 1
    assert doc.chunks[0].text == \
        P1 + " " + P2
    assert len(doc.chunks[0]
               .source_element_ids) == 2


def test_cross_schema_valid(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path,
                 _CROSS_PAGES,
                 "[0 0 612 792]",
                 "cross.pdf")
    assert is_valid(doc.to_dict())


def test_cross_pdfloc_green(tmp_path):
    from evaluation.metrics import \
        compute_automatic_metrics
    p = tmp_path / "cross.pdf"
    p.write_bytes(_build(
        _CROSS_PAGES,
        "[0 0 612 792]"))
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    m = compute_automatic_metrics(
        doc.to_dict(), None, "pdf",
        None)
    assert m[
        "pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}
