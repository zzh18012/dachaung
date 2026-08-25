r"""app/parsers/fallback_parser.py PDF 边角测试 - 第八十二轮（Round 1512）。

新角度（probe 实证）页面几何属性 /Rotate /CropBox 与内联
图像 BI/ID/EI（此前轮次未碰页面级属性）：

- **/Rotate 90 坐标旋转**：TEXT bbox → [697.5,72,709.5,
  102.7]（原 [72,82.5,102.7,94.5] 绕页角旋转）
- **⚠ /Rotate 180/270 内容镜像反转**：'TEXT' → 'TXET'
  （180°翻转阅读方向后 pdfminer 按左→右重排字符）
- **⚠ /Rotate 180 词+字符双反转**：'WORD1 word2' →
  '2drow 1DROW'
- **/Rotate 90 竖排两行并栏**：TOP(y700)/BOT(y650) 两行
  → 单元素 'BOT TOP'（旋转后两行成并列、按新 x 排序）
- **/CropBox 完全被忽略**：文本放 CropBox 外（y=770 超
  出 [50 100 500 750]、x=550 超右界）→ 照常提取、bbox
  不裁剪
- **内联图像 BI/ID/EI 触发 image 元素**：bbox 退化为
  [0,791,1,792]（1×1，pdfminer 无定位信息）、EI 后文
  本照常提取
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _pdf(tmp_path, name, extra_page="",
         content="BT /F1 12 Tf 72 700 Td"
                 " (TEXT) Tj ET"):
    page = ("<< /Type /Page /Parent 2 0 R"
            " /MediaBox [0 0 612 792]"
            f" {extra_page}"
            " /Resources << /Font"
            " << /F1 5 0 R >> >>"
            " /Contents 4 0 R >>")
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R]"
        " /Count 1 >>",
        page,
        f"<< /Length {len(content)} >>"
        f"\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding /WinAnsiEncoding >>",
    ]
    pdf = "%PDF-1.4\n" + "".join(
        f"{i + 1} 0 obj\n{o}\nendobj\n"
        for i, o in enumerate(objs))
    pdf += ("trailer << /Root 1 0 R"
            " /Size 6 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf.encode("latin-1"))
    return p


def _els(tmp_path, name, **kw):
    p = _pdf(tmp_path, name, **kw)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    return [(e.content, e.type,
             [round(v, 1) for v in
              e.source_locator["bbox"]])
            for e in doc.elements]


def test_rotate_90_bbox(tmp_path):
    got = _els(tmp_path, "r90.pdf",
               extra_page="/Rotate 90")
    assert got == [
        ("TEXT", "heading",
         [697.5, 72.0, 709.5, 102.7])]


def test_rotate_180_270_reverse(
        tmp_path):
    for rot, bbox in (
        (180, [509.3, 697.5,
               540.0, 709.5]),
        (270, [82.5, 509.3,
               94.5, 540.0]),
    ):
        got = _els(
            tmp_path, f"r{rot}.pdf",
            extra_page=f"/Rotate {rot}")
        assert got == [
            ("TXET", "heading", bbox)], rot


def test_rotate_180_word_mirror(
        tmp_path):
    got = _els(
        tmp_path, "r2w.pdf",
        extra_page="/Rotate 180",
        content="BT /F1 12 Tf 72 700 Td"
                " (WORD1 word2) Tj ET")
    assert [g[0] for g in got] == [
        "2drow 1DROW"]


def test_rotate_90_two_lines_merge(
        tmp_path):
    got = _els(
        tmp_path, "r2l.pdf",
        extra_page="/Rotate 90",
        content="BT /F1 12 Tf 72 700 Td"
                " (TOP) Tj 0 -50 Td"
                " (BOT) Tj ET")
    assert got == [
        ("BOT TOP", "heading",
         [647.5, 72.0, 709.5, 96.7])]


def test_cropbox_outside_still(
        tmp_path):
    got = _els(
        tmp_path, "co.pdf",
        extra_page=
        "/CropBox [50 100 500 750]",
        content="BT /F1 12 Tf 72 770 Td"
                " (HIDDEN) Tj ET")
    assert got == [
        ("HIDDEN", "heading",
         [72.0, 12.5, 118.0, 24.5])]


def test_inline_image_element(
        tmp_path):
    content = ("BI /W 5 /H 5 /CS /G"
               " /BPC 8 ID " + "\x80" * 25
               + " EI BT /F1 12 Tf"
               " 72 700 Td (TEXT) Tj ET")
    got = _els(
        tmp_path, "inl.pdf",
        content=content)
    assert [(c, t) for c, t, _ in got] \
        == [("TEXT", "heading"),
            (None, "image")]
    assert got[1][2] == [0.0, 791.0,
                         1.0, 792.0]
