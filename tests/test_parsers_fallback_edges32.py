r"""app/parsers/fallback_parser.py 边角测试 - 第三十二轮（Round 1422）。

新角度（probe 实证）页级 /Rotate 属性 + 内联图像（历史未
碰过二者）：
- /Rotate 90：文本保留但 bbox 旋成竖条 [697.516, 72.0,
  709.516, 166.728]（宽 12 高 94.7）
- /Rotate 180：字符序**倒序**（'txet egap detatoR'）、bbox
  镜像到 [445.272, 697.516, 540.0, 709.516]（540=612-72）
- BI/ID/EI 内联图像：不崩——产出 image 元素（content
  None、bbox 退化成原点单位框 [0,791,1,792]），照常落盘
  image_<sha>_p1_00.png；chunk 层图片不参与
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _build(page_extra, content):
    page = (b"<< /Type /Page /Parent "
            b"2 0 R /MediaBox "
            b"[0 0 612 792] "
            + page_extra
            + b"/Resources << /Font "
            b"<< /F1 5 0 R >> >> "
            b"/Contents 4 0 R >>")
    objs = {
        5: (b"<< /Type /Font /Subtype "
            b"/Type1 /BaseFont "
            b"/Helvetica >>"),
        1: (b"<< /Type /Catalog "
            b"/Pages 2 0 R >>"),
        2: (b"<< /Type /Pages "
            b"/Kids [3 0 R] "
            b"/Count 1 >>"),
        3: page,
        4: (b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n" + content
            + b"\nendstream"),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += (f"{oid} 0 obj\n"
                .encode()
                + objs[oid]
                + b"\nendobj\n")
    xref_pos = len(out)
    out += b"xref\n0 6\n" \
        b"0000000000 65535 f \n"
    for oid in range(1, 6):
        out += ("%010d 00000 n \n"
                % offsets[oid]).encode()
    out += (b"trailer\n<< /Size 6 "
            b"/Root 1 0 R >>\n"
            b"startxref\n"
            + str(xref_pos).encode()
            + b"\n%%EOF")
    return bytes(out)


def _rot_pdf(tmp_path, degrees):
    p = tmp_path / f"rot{degrees}.pdf"
    p.write_bytes(_build(
        f"/Rotate {degrees} ".encode(),
        b"BT /F1 12 Tf 72 700 Td "
        b"(Rotated page text) "
        b"Tj ET"))
    return p


def _inl_pdf(tmp_path):
    c = (b"BT /F1 12 Tf 72 700 Td "
         b"(Inline image page) Tj ET "
         b"BI /W 2 /H 2 /CS /G "
         b"/BPC 8 ID \x00\x40\x80\xff EI "
         b"BT /F1 12 Tf 72 300 Td "
         b"(After inline) Tj ET")
    p = tmp_path / "inl.pdf"
    p.write_bytes(_build(b"", c))
    return p


# ---------- /Rotate 90 ----------

def test_rot90_content_kept(
        tmp_path):
    p = _rot_pdf(tmp_path, 90)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "Rotated page text"


def test_rot90_vertical_bbox(
        tmp_path):
    p = _rot_pdf(tmp_path, 90)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].source_locator == {
        "page": 1,
        "bbox": [697.516, 72.0,
                 709.516, 166.728]}


# ---------- /Rotate 180 ----------

def test_rot180_reversed(
        tmp_path):
    p = _rot_pdf(tmp_path, 180)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "txet egap detatoR"


def test_rot180_mirror_bbox(
        tmp_path):
    p = _rot_pdf(tmp_path, 180)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].source_locator == {
        "page": 1,
        "bbox": [445.272, 697.516,
                 540.0, 709.516]}


def test_rot_mirror_x_sum(
        tmp_path):
    """镜像：x0+x1 == (612-原x0)
    + (612-原x1) = (612-72)
    + (612-166.728)。"""
    doc90 = FallbackParser().parse(
        _rot_pdf(tmp_path, 90),
        compute_file_hash(
            _rot_pdf(tmp_path, 90)))
    doc = FallbackParser().parse(
        _rot_pdf(tmp_path, 180),
        compute_file_hash(
            _rot_pdf(tmp_path, 180)))
    b180 = doc.elements[
        0].source_locator["bbox"]
    assert b180[0] + b180[2] == \
        (612 - 72) + (612 - 166.728)
    assert doc90.warnings == []
    assert doc.warnings == []


# ---------- 内联图像 ----------

def test_inline_elements_order(
        tmp_path):
    p = _inl_pdf(tmp_path)
    doc = FallbackParser(
        image_output_dir=(
            tmp_path / "imgs")
    ).parse(p, compute_file_hash(p))
    assert [e.type
            for e in doc.elements] == [
        "heading", "heading",
        "image"]


def test_inline_image_none_content(
        tmp_path):
    p = _inl_pdf(tmp_path)
    doc = FallbackParser(
        image_output_dir=(
            tmp_path / "imgs")
    ).parse(p, compute_file_hash(p))
    img = doc.elements[2]
    assert img.content is None
    assert img.resource_path \
        is not None


def test_inline_image_bbox(
        tmp_path):
    p = _inl_pdf(tmp_path)
    doc = FallbackParser(
        image_output_dir=(
            tmp_path / "imgs")
    ).parse(p, compute_file_hash(p))
    assert doc.elements[
        2].source_locator == {
        "page": 1,
        "bbox": [0.0, 791.0,
                 1.0, 792.0]}


def test_inline_image_file(
        tmp_path):
    p = _inl_pdf(tmp_path)
    FallbackParser(
        image_output_dir=(
            tmp_path / "imgs")
    ).parse(p, compute_file_hash(p))
    names = [f.name for f in
             (tmp_path / "imgs")
             .glob("*.png")]
    assert len(names) == 1
    assert re.fullmatch(
        r"image_[0-9a-f]{16}"
        r"_p1_00.png",
        names[0])
    f = (tmp_path / "imgs"
         / names[0])
    assert f.read_bytes()[:8] == \
        b"\x89PNG\r\n\x1a\n"


def test_inline_texts_intact(
        tmp_path):
    p = _inl_pdf(tmp_path)
    doc = FallbackParser(
        image_output_dir=(
            tmp_path / "imgs")
    ).parse(p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "Inline image page"
    assert doc.elements[
        1].content == \
        "After inline"


def test_inline_no_warnings(
        tmp_path):
    p = _inl_pdf(tmp_path)
    doc = FallbackParser(
        image_output_dir=(
            tmp_path / "imgs")
    ).parse(p, compute_file_hash(p))
    assert doc.warnings == []


def test_inline_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _inl_pdf(tmp_path)
    doc = FallbackParser(
        image_output_dir=(
            tmp_path / "imgs")
    ).parse(p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_inline_chunks_skip_image(
        tmp_path):
    p = _inl_pdf(tmp_path)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "Inline image page",
        "After inline"]
    assert [len(c.source_element_ids)
            for c in doc.chunks] == [
        1, 1]


def test_rot_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _rot_pdf(tmp_path, 90)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())
    p2 = _rot_pdf(tmp_path, 180)
    doc2 = FallbackParser().parse(
        p2, compute_file_hash(p2))
    assert is_valid(doc2.to_dict())
