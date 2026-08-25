r"""app/parsers/fallback_parser.py PDF 边角测试 - 第八十一轮（Round 1511）。

新角度（probe 实证）XObject /Do 家族（此前 80 轮只测
页面内容流，未碰 Form/Image XObject）：

- **Form 内文本照常提取且坐标变换**：form 空间 (10,20)
  经 cm(100,600) → 设备 bbox [110,162.5,176,174.5]；
  与页面文本按自上而下阅读序混排
- **Form 无 /Resources 时继承页面资源**：F1 从 page
  Resources 解析，文本照常提取
- **cm 缩放精确作用 bbox**：2x cm → bbox 宽高精确翻倍
  （66→132、12→24）
- **⚠ Form /BBox 不裁剪文本**：文本放 form y=150（BBox
  仅 0..100）→ 照常提取（bbox 在 BBox 外也收）
- **Image XObject 触发 image 元素**：/Im1 Do → type
  ='image'、content=None、resource_path='(unrendered)'、
  bbox 即 cm 变换矩形 [200,492,300,592]、metadata
  srcsize=[5,5]、extracted_to_disk=False
- **未定义 XObject 名静默忽略**：'/NoSuchX Do' → 无警
  告、文本正常
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _pdf_form(tmp_path, name, page, form,
              form_res=
              " << /Font << /F1 5 0 R >> >>"):
    res = f" /Resources{form_res}" \
        if form_res else ""
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R]"
        " /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R"
        " /MediaBox [0 0 612 792]"
        " /Resources << /Font"
        " << /F1 5 0 R >> /XObject"
        " << /Fm1 6 0 R >> >>"
        " /Contents 4 0 R >>",
        f"<< /Length {len(page)} >>\nstream"
        f"\n{page}\nendstream",
        "<< /Type /Font /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding /WinAnsiEncoding >>",
        f"<< /Type /XObject"
        f" /Subtype /Form /BBox"
        f" [0 0 200 100]{res}"
        f" /Length {len(form)} >>\nstream"
        f"\n{form}\nendstream",
    ]
    pdf = "%PDF-1.4\n" + "".join(
        f"{i + 1} 0 obj\n{o}\nendobj\n"
        for i, o in enumerate(objs))
    pdf += ("trailer << /Root 1 0 R"
            " /Size 7 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf.encode("latin-1"))
    return p


def _pdf_img(tmp_path, name, page):
    imgdata = b"\x80" * 25
    objs = [
        b"<< /Type /Catalog"
        b" /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R]"
        b" /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R"
        b" /MediaBox [0 0 612 792]"
        b" /Resources << /Font"
        b" << /F1 5 0 R >> /XObject"
        b" << /Im1 6 0 R >> >>"
        b" /Contents 4 0 R >>",
        f"<< /Length {len(page)} >>\nstream\n"
        .encode("latin-1") + page
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1"
        b" /BaseFont /Helvetica"
        b" /Encoding /WinAnsiEncoding >>",
        f"<< /Type /XObject /Subtype /Image"
        f" /Width 5 /Height 5"
        f" /ColorSpace /DeviceGray"
        f" /BitsPerComponent 8 /Length"
        f" {len(imgdata)} >>\nstream\n"
        .encode("latin-1") + imgdata
        + b"\nendstream",
    ]
    pdf = b"%PDF-1.4\n" + b"".join(
        f"{i + 1} 0 obj\n".encode("latin-1")
        + o + b"\nendobj\n"
        for i, o in enumerate(objs))
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 7 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def _doc(p):
    return FallbackParser().parse(
        p, compute_file_hash(p))


def test_form_xobject_text_transformed(
        tmp_path):
    p = _pdf_form(
        tmp_path, "formonly.pdf",
        "q 1 0 0 1 100 600 cm /Fm1 Do Q",
        "BT /F1 12 Tf 10 20 Td"
        " (FORMTEXT) Tj ET")
    doc = _doc(p)
    assert [(e.content,
             [round(v, 1)
              for v in
              e.source_locator["bbox"]])
            for e in doc.elements] == [
        ("FORMTEXT",
         [110.0, 162.5, 176.0, 174.5])]
    assert doc.warnings == []


def test_form_and_page_reading_order(
        tmp_path):
    p = _pdf_form(
        tmp_path, "mixed.pdf",
        "BT /F1 12 Tf 72 100 Td"
        " (PAGETEXT) Tj ET"
        " q 1 0 0 1 100 600 cm"
        " /Fm1 Do Q",
        "BT /F1 12 Tf 10 20 Td"
        " (FORMTEXT) Tj ET")
    doc = _doc(p)
    assert [e.content
            for e in doc.elements] == [
        "FORMTEXT", "PAGETEXT"]


def test_form_without_resources(
        tmp_path):
    p = _pdf_form(
        tmp_path, "nores.pdf",
        "q 1 0 0 1 100 600 cm /Fm1 Do Q",
        "BT /F1 12 Tf 10 20 Td"
        " (FORMTEXT) Tj ET",
        form_res="")
    doc = _doc(p)
    assert len(doc.elements) == 1
    assert doc.elements[0].content \
        == "FORMTEXT"


def test_scaled_form_doubles_bbox(
        tmp_path):
    p = _pdf_form(
        tmp_path, "scaled.pdf",
        "q 2 0 0 2 100 300 cm /Fm1 Do Q",
        "BT /F1 12 Tf 10 20 Td"
        " (FORMTEXT) Tj ET")
    doc = _doc(p)
    bbox = [round(v, 1) for v in
            doc.elements[0]
            .source_locator["bbox"]]
    assert bbox == [120.0, 433.0,
                    252.0, 457.0]


def test_form_bbox_does_not_clip(
        tmp_path):
    p = _pdf_form(
        tmp_path, "clipped.pdf",
        "q 1 0 0 1 100 100 cm /Fm1 Do Q",
        "BT /F1 12 Tf 10 150 Td"
        " (OUTSIDE) Tj ET")
    doc = _doc(p)
    assert [(e.content,
             [round(v, 1)
              for v in
              e.source_locator["bbox"]])
            for e in doc.elements] == [
        ("OUTSIDE",
         [110.0, 532.5, 163.3, 544.5])]


def test_image_xobject_element(
        tmp_path):
    p = _pdf_img(
        tmp_path, "imgtext.pdf",
        b"q 100 0 0 100 200 200 cm"
        b" /Im1 Do Q BT /F1 12 Tf"
        b" 72 700 Td (TEXT) Tj ET")
    doc = _doc(p)
    assert [e.type
            for e in doc.elements] == [
        "heading", "image"]
    im = doc.elements[1]
    assert im.content is None
    assert im.resource_path \
        == "(unrendered)"
    assert [round(v, 1) for v in
            im.source_locator["bbox"]] \
        == [200.0, 492.0,
            300.0, 592.0]
    assert im.metadata["srcsize"] \
        == [5, 5]
    assert im.metadata[
        "extracted_to_disk"] is False


def test_unknown_xobject_ignored(
        tmp_path):
    p = _pdf_img(
        tmp_path, "unknowndo.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" (TEXT) Tj ET /NoSuchX Do")
    doc = _doc(p)
    assert [e.content
            for e in doc.elements] == [
        "TEXT"]
    assert doc.warnings == []
