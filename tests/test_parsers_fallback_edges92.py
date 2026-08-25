r"""app/parsers/fallback_parser.py PDF 边角测试 - 第九十二轮（Round 1522）。

新角度（probe 实证）跨页状态/空页/图形状态栈（此前轮
次未碰 q/Q 栈与缺 /Contents 页）：

- **跨页文本状态不泄漏**：第 1 页 Tf 24 + Tc 30（'B I
  G' 炸开）、第 2 页自带 Tf 12 → 'plainer' 正常（每页
  图形/文本状态独立初始化）
- **空白中页页码跳号正确**：P1/空页/P3 → locator page
  1 与 3、无警告
- **不闭合 q 双层变换仍提取**：q+cm(100,0) 再 q+cm(2x)
  无 Q → 'QQ' bbox [244,-627,281.3,-603]（字号翻倍高
  24pt、y 负——栈不配对不报错）
- **孤立 Q（无 q）容忍**：'OQ' 正常 [72,82.5,90.7,94.5]
- **⚠ BT 内 cm 仍生效**：cm 严格应在 BT 外，放 BT 内
  Td 前 → 'CM' bbox [244,-927,281.3,-903]（pdfminer
  照常并入 CTM、字号翻倍）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _pdf(tmp_path, name, pages):
    n = len(pages)
    kids = " ".join(f"{3 + i * 2} 0 R"
                    for i in range(n))
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: f"<< /Type /Pages"
           f" /Kids [{kids}]"
           f" /Count {n} >>",
        100: "<< /Type /Font"
             " /Subtype /Type1"
             " /BaseFont /Helvetica"
             " /Encoding"
             " /WinAnsiEncoding >>",
    }
    for i, content in enumerate(pages):
        oid = 3 + i * 2
        objs[oid] = (
            "<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 100 0 R >> >>"
            + (f" /Contents {oid + 1}"
               f" 0 R >>"
               if content is not None
               else " >>"))
        if content is not None:
            objs[oid + 1] = (
                f"<< /Length"
                f" {len(content)} >>"
                f"\nstream\n{content}"
                f"\nendstream")
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


def _els(tmp_path, name, pages):
    p = _pdf(tmp_path, name, pages)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    return [(e.content,
             e.source_locator["page"],
             [round(v, 1) for v in
              e.source_locator["bbox"]])
            for e in doc.elements], \
        doc.warnings


def test_cross_page_state_reset(
        tmp_path):
    got, warns = _els(
        tmp_path, "leak.pdf", [
            "BT /F1 24 Tf 30 Tc"
            " 72 700 Td (BIG) Tj ET",
            "BT /F1 12 Tf 72 700 Td"
            " (plainer) Tj ET"])
    assert got == [
        ("B I G", 1,
         [72.0, 73.0, 173.4, 97.0]),
        ("plainer", 2,
         [72.0, 82.5, 108.0, 94.5])]
    assert warns == []


def test_blank_middle_page_numbering(
        tmp_path):
    got, _ = _els(
        tmp_path, "blank.pdf", [
            "BT /F1 12 Tf 72 700 Td"
            " (P1) Tj ET",
            None,
            "BT /F1 12 Tf 72 700 Td"
            " (P3) Tj ET"])
    assert got == [
        ("P1", 1,
         [72.0, 82.5, 86.7, 94.5]),
        ("P3", 3,
         [72.0, 82.5, 86.7, 94.5])]


def test_unbalanced_q_transforms(
        tmp_path):
    got, _ = _els(
        tmp_path, "qonly.pdf", [
            "q 1 0 0 1 100 0 cm"
            " q 2 0 0 2 0 0 cm"
            " BT /F1 12 Tf 72 700"
            " Td (QQ) Tj ET"])
    assert got == [
        ("QQ", 1,
         [244.0, -627.0,
          281.3, -603.0])]


def test_orphan_q_tolerated(
        tmp_path):
    got, _ = _els(
        tmp_path, "oq.pdf", [
            "Q BT /F1 12 Tf 72 700"
            " Td (OQ) Tj ET"])
    assert got == [
        ("OQ", 1,
         [72.0, 82.5, 90.7, 94.5])]


def test_cm_inside_bt_applies(
        tmp_path):
    got, _ = _els(
        tmp_path, "cminbt.pdf", [
            "BT /F1 12 Tf"
            " 2 0 0 2 100 300 cm"
            " 72 700 Td (CM) Tj ET"])
    assert got == [
        ("CM", 1,
         [244.0, -927.0,
          281.3, -903.0])]
