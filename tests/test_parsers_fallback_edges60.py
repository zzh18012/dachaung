r"""app/parsers/fallback_parser.py 边角测试 - 第六十轮（Round 1463）。

新角度（probe 实证）Tw/TL 缺省/负 Tz/双 BT 排序/同源 Form
（edges54-59 与 Tz/Tf/行进算子各轮未碰过）：
- **Tw 词间距**：10 Tw → 'a b c' 正常提取，bbox x1 拉宽到
  46.016（每个空格 +10pt）；对照无 Tw 同文本 x1 < 40
- **TL 缺省 0 时 ' 算子不换行**：两串落同 y → pdfplumber
  按 x 排字符**逐字交错** 'snteaxrtt line'（edges56 的 '
  用 TL 14 才并段）
- **Tz 负值**：-50 → 文本反向 + 词内散开 'tz g e n'，
  bbox x0 为**负**（往左伸出原点）
- **Tz 小数**：33.3 → 宽度按 0.333 缩放（x1 ≈ 11.77）
- **双 BT 块按 top-origin y 排序**：Td 72 700 的 'B'
  （y≈82）排在原点 'A'（y≈782）**前面**
- **同源 Form XObject**：/X9 Do 的表单文本与页面文本同
  坐标 → 逐字交错 'ianf txeorbject'（edges55 只测过带
  平移的嵌套 Form）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _pdf(tmp_path, name, content,
         xobjects=None):
    xref = ""
    for num in xobjects or {}:
        xref += f"/X{num} {num} 0 R "
    res = f"/Font << /F1 5 0 R >>"
    if xref:
        res += f" /XObject << {xref}>>"
    pdf = (f"%PDF-1.4\n"
           f"1 0 obj\n<< /Type /Catalog"
           f" /Pages 2 0 R >>\nendobj\n"
           f"2 0 obj\n<< /Type /Pages"
           f" /Kids [3 0 R] /Count 1"
           f" >>\nendobj\n"
           f"3 0 obj\n<< /Type /Page"
           f" /Parent 2 0 R"
           f" /MediaBox [0 0 612 792]"
           f" /Resources << {res} >>"
           f" /Contents 4 0 R"
           f" >>\nendobj\n"
           f"4 0 obj\n<< /Length "
           f"{len(content)} >>\nstream\n"
           f"{content}\nendstream"
           f"\nendobj\n"
           f"5 0 obj\n<< /Type /Font"
           f" /Subtype /Type1"
           f" /BaseFont /Helvetica"
           f" /Encoding /WinAnsiEncoding"
           f" >>\nendobj\n")
    for num, body in (xobjects or
                      {}).items():
        pdf += (f"{num} 0 obj\n"
                f"{body}\nendobj\n")
    pdf += ("trailer\n"
            "<< /Root 1 0 R"
            " /Size 10 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf.encode("latin-1"))
    return p


def _parse(p):
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- Tw 词间距 ----------

def test_tw_word_spacing_widens(
        tmp_path):
    p = _pdf(
        tmp_path, "tw.pdf",
        "BT /F1 12 Tf 10 Tw"
        " (a b c) Tj ET")
    doc = _parse(p)
    assert doc.elements[
        0].content == "a b c"
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox == [
        0.0, 782.484,
        46.016000000000005, 794.484,
    ]


def test_no_tw_narrower(
        tmp_path):
    p = _pdf(
        tmp_path, "notw.pdf",
        "BT /F1 12 Tf (a b c) Tj ET")
    doc = _parse(p)
    assert doc.elements[
        0].content == "a b c"
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox[2] < 40.0


# ---------- TL 缺省 0 ----------

def test_quote_no_tl_interleaves(
        tmp_path):
    p = _pdf(
        tmp_path, "q0.pdf",
        "BT /F1 12 Tf (start) Tj"
        " (next line)' ET")
    doc = _parse(p)
    assert len(doc.elements) == 1
    assert doc.elements[
        0].content == "snteaxrtt line"
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox == [
        0.0, 782.484, 44.688, 794.484,
    ]


# ---------- Tz 变体 ----------

def test_tz_negative_reversed(
        tmp_path):
    p = _pdf(
        tmp_path, "tzn.pdf",
        "BT /F1 12 Tf -50 Tz"
        " (neg tz) Tj ET")
    doc = _parse(p)
    assert doc.elements[
        0].content == "tz g e n"
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox[0] == -16.344
    assert bbox[2] == 0.0


def test_tz_float_scaled(
        tmp_path):
    p = _pdf(
        tmp_path, "tzf.pdf",
        "BT /F1 12 Tf 33.3 Tz"
        " (float tz) Tj ET")
    doc = _parse(p)
    assert doc.elements[
        0].content == "float tz"
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox == [
        0.0, 782.484,
        11.772215999999998, 794.484,
    ]


# ---------- 双 BT 排序 ----------

def test_two_bt_y_sort_order(
        tmp_path):
    p = _pdf(
        tmp_path, "btx2.pdf",
        "BT /F1 12 Tf (A) Tj ET"
        " BT /F1 12 Tf 72 700 Td"
        " (B) Tj ET")
    doc = _parse(p)
    assert [(e.content,
             e.source_locator["bbox"])
            for e in doc.elements] == [
        ("B", [72.0,
               82.48400000000004,
               80.004,
               94.48400000000004]),
        ("A", [0.0, 782.484,
               8.004000000000001,
               794.484]),
    ]


# ---------- 同源 Form XObject ----------

def test_form_same_origin_interleave(
        tmp_path):
    p = _pdf(
        tmp_path, "fx.pdf",
        "/X9 Do BT /F1 12 Tf"
        " (after) Tj ET",
        xobjects={9: (
            "<< /Type /XObject"
            " /Subtype /Form"
            " /BBox [0 0 100 100]"
            " /Length 0 >>"
            "\nstream\n"
            "BT /F1 12 Tf"
            " (in xobject) Tj ET"
            "\nendstream")})
    doc = _parse(p)
    assert len(doc.elements) == 1
    assert doc.elements[
        0].content == "ianf txeorbject"
