r"""app/parsers/fallback_parser.py PDF 边角测试 - 第九十五轮（Round 1525）。

新角度（probe 实证）Tr 7 裁剪渲染模式与错误 /Length
（Tr 家族 0-3 已测，7 未测；流长度错误未测）：

- **Tr 7（仅裁剪、不显示）仍提取**：'CLIP' 照常（与
  Tr 3 不可见同路）
- **⚠ Tr 7 → Tr 0 后顺序倒置**：CLIP(y700 上) +
  NORMAL(y650 下) → 输出 ['NORMAL','CLIP']（CLIP 在
  上方却排第二——裁剪模式字符参与布局排序异常）
- **/Length 偏大容忍**：500（实际 33）→ 'TEXT' 照常
  （pdfminer 读到 endstream 关键字为止）
- **/Length 0 容忍**：0 → 'TEXT' 照常（长度全错也不
  截断内容）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _pdf(tmp_path, name, content,
         length_override=None):
    length = (length_override
              if length_override is not None
              else len(content))
    objs = [
        "<< /Type /Catalog"
        " /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R]"
        " /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R"
        " /MediaBox [0 0 612 792]"
        " /Resources << /Font"
        " << /F1 5 0 R >> >>"
        " /Contents 4 0 R >>",
        f"<< /Length {length} >>"
        f"\nstream\n{content}"
        f"\nendstream",
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


def _els(tmp_path, name, content,
         length_override=None):
    p = _pdf(tmp_path, name, content,
             length_override)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    return [e.content
            for e in doc.elements], \
        doc.warnings


def test_tr7_extracted(tmp_path):
    got, warns = _els(
        tmp_path, "tr7.pdf",
        "BT /F1 12 Tf 7 Tr 72 700 Td"
        " (CLIP) Tj ET")
    assert got == ["CLIP"]
    assert warns == []


def test_tr7_then_normal_order(
        tmp_path):
    got, _ = _els(
        tmp_path, "tr7b.pdf",
        "BT /F1 12 Tf 7 Tr 72 700 Td"
        " (CLIP) Tj 0 Tr 72 650 Td"
        " (NORMAL) Tj ET")
    assert got == ["NORMAL", "CLIP"]


def test_length_too_big(tmp_path):
    got, _ = _els(
        tmp_path, "lenbig.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (TEXT) Tj ET",
        length_override=500)
    assert got == ["TEXT"]


def test_length_zero(tmp_path):
    got, _ = _els(
        tmp_path, "len0.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (TEXT) Tj ET",
        length_override=0)
    assert got == ["TEXT"]
