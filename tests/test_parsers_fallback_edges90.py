r"""app/parsers/fallback_parser.py PDF 边角测试 - 第九十轮（Round 1520）。

新角度（probe 实证）OCG 隐藏图层与逐页 MediaBox 差异
（此前轮次多页全部同尺寸 letter）：

- **⚠ OCG OFF 图层文本照常提取**：catalog /OCProperties
  OFF [隐藏层]、内容 /OC /mc0 BDC (HIDDENL) Tj EMC →
  'HIDDENL' 仍提取并与可见层文本同行合并
  'HIDDENLVISIBLE'（pdfplumber 无图层可见性概念）
- **⚠ 小页框上方文本负 y**：第 2 页 MediaBox [0 0 842
  595]（A4 横）、文本 y=700 > 595 → bbox y=-114.5
  （超框仍提取、按该页自身高度翻转）
- **大页框按自身高度翻转**：MediaBox [0 0 612 1000]、
  y=700 → bbox y=290.5（非 letter 的 82.5——坐标归一
  化逐页独立）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _pdf(tmp_path, name, pages,
         ocg=False):
    n = len(pages)
    kids = " ".join(f"{3 + i * 2} 0 R"
                    for i in range(n))
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R"
           + (" /OCProperties"
              " << /OCGs [90 0 R]"
              " /D << /ON [91 0 R]"
              " /OFF [90 0 R]"
              " /AS [] >> >>"
              if ocg else "") + " >>",
        2: f"<< /Type /Pages"
           f" /Kids [{kids}]"
           f" /Count {n} >>",
        100: "<< /Type /Font"
             " /Subtype /Type1"
             " /BaseFont /Helvetica"
             " /Encoding"
             " /WinAnsiEncoding >>",
    }
    for i, (mb, content) in enumerate(
            pages):
        oid = 3 + i * 2
        objs[oid] = (
            f"<< /Type /Page"
            f" /Parent 2 0 R"
            f" /MediaBox {mb}"
            f" /Resources << /Font"
            f" << /F1 100 0 R >> >>"
            f" /Contents {oid + 1}"
            f" 0 R >>")
        objs[oid + 1] = (
            f"<< /Length"
            f" {len(content)} >>"
            f"\nstream\n{content}"
            f"\nendstream")
    if ocg:
        objs[90] = ("<< /Type /OCG"
                    " /Name (Hidden"
                    " Layer) >>")
        objs[91] = ("<< /Type /OCG"
                    " /Name (Visible"
                    " Layer) >>")
    pdf = "%PDF-1.4\n"
    for oid in sorted(objs):
        pdf += (f"{oid} 0 obj\n"
                f"{objs[oid]}\n"
                f"endobj\n")
    pdf += ("trailer << /Root 1 0 R"
            f" /Size {max(objs) + 1} >>"
            "\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf.encode("latin-1"))
    return p


def _els(tmp_path, name, **kw):
    p = _pdf(tmp_path, name, **kw)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    return doc


_P1 = ("BT /F1 12 Tf 72 700 Td"
       " (PAGE1) Tj ET")


def test_ocg_off_layer_extracted(
        tmp_path):
    doc = _els(
        tmp_path, "ocg.pdf",
        pages=[("[0 0 612 792]",
                "BT /F1 12 Tf 72 700 Td"
                " /OC /mc0 BDC"
                " (HIDDENL) Tj EMC"
                " /OC /mc1 BDC"
                " (VISIBLE) Tj EMC ET")],
        ocg=True)
    assert [(e.content,
             [round(v, 1) for v in
              e.source_locator["bbox"]])
            for e in doc.elements] == [
        ("HIDDENLVISIBLE",
         [72.0, 82.5, 170.0, 94.5])]
    assert doc.warnings == []


def test_small_page_above_box_negative(
        tmp_path):
    doc = _els(
        tmp_path, "mixed.pdf",
        pages=[("[0 0 612 792]", _P1),
               ("[0 0 842 595]", _P1)])
    assert [(e.content,
             e.source_locator["page"],
             [round(v, 1) for v in
              e.source_locator["bbox"]])
            for e in doc.elements] == [
        ("PAGE1", 1,
         [72.0, 82.5, 112.0, 94.5]),
        ("PAGE1", 2,
         [72.0, -114.5,
          112.0, -102.5])]


def test_tall_page_own_height(
        tmp_path):
    doc = _els(
        tmp_path, "tall.pdf",
        pages=[("[0 0 612 1000]",
                _P1)])
    assert [round(v, 1) for v in
            doc.elements[0]
            .source_locator["bbox"]] \
        == [72.0, 290.5,
            112.0, 302.5]
