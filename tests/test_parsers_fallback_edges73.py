r"""app/parsers/fallback_parser.py PDF 边角测试 - 第七十三轮（Round 1496）。

新角度（probe 实证）文本状态机边界 + 坐标矩阵（edges1-72
未碰）：

- **BT 外文本 op 被忽略**：无 BT 的 '72 700 Td (x) Tj'
  → 无元素 + pdf_no_text_extracted（文本对象边界硬性）
- **裸 ET 前置无害**：'ET BT ...' → 'x' 照常
- **⚠ Tm 旋转 90° 文本倒序**：'0 1 -1 0 72 700 Tm'
  的 'rotated' → **'detator'**（逐字符反向，字符沿 y 排
  布后按升序 y 串起——与 R1495 页内 y 升序同规则）
- **Tm 纯缩放正常**：'2 0 0 2' 矩阵 → 'scaled' 顺序正
  常（方向不变）
- **页外坐标仍提取**：(72000,70000) 远超 MediaBox →
  'far' 照常（无裁剪）
- **字体缺失仍提取**：/F2 不在 Resources → 'ghost
  font' 照常（pdfminer 容错，仅 stderr 日志，无 doc 告
  警）
- **行内换字号**：24pt 'big' 先出（y=650 < 700，页内
  y 升序规则的又一实证）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

from tests.test_parsers_fallback_edges66 \
    import _pdf


def _pdf_no_f2(tmp_path, name, content):
    pdf = (
        "%PDF-1.4\n1 0 obj\n"
        "<< /Type /Catalog"
        " /Pages 2 0 R >>\nendobj\n"
        "2 0 obj\n<< /Type /Pages"
        " /Kids [3 0 R] /Count 1"
        " >>\nendobj\n"
        "3 0 obj\n<< /Type /Page"
        " /Parent 2 0 R"
        " /MediaBox [0 0 612 792]"
        " /Resources << /Font"
        " << /F1 5 0 R >> >>"
        " /Contents 4 0 R"
        " >>\nendobj\n"
        f"4 0 obj\n<< /Length"
        f" {len(content)} >>\nstream\n"
        f"{content}\nendstream\n"
        "endobj\n"
        "5 0 obj\n<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding /WinAnsiEncoding"
        " >>\nendobj\n"
        "trailer\n<< /Root 1 0 R"
        " /Size 6 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf.encode("latin-1"))
    return p


def _parse(p):
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- BT/ET 边界 ----------

def test_text_outside_bt_ignored(
        tmp_path):
    p = _pdf(
        tmp_path, "nobt.pdf",
        "72 700 Td (outside) Tj")
    doc = _parse(p)
    assert doc.elements == []
    assert [w.code for w in
            doc.warnings] == \
        ["pdf_no_text_extracted"]


def test_stray_et_harmless(
        tmp_path):
    p = _pdf(
        tmp_path, "et.pdf",
        "ET BT /F1 12 Tf 72 700 Td"
        " (x) Tj ET")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == [
        "x",
    ]
    assert doc.warnings == []


# ---------- Tm 矩阵 ----------

def test_tm_rotation_reverses_chars(
        tmp_path):
    p = _pdf(
        tmp_path, "rot.pdf",
        "BT /F1 12 Tf"
        " 0 1 -1 0 72 700 Tm"
        " (rotated) Tj ET")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == [
        "detator",
    ]
    assert doc.warnings == []


def test_tm_scale_normal_order(
        tmp_path):
    p = _pdf(
        tmp_path, "scl.pdf",
        "BT /F1 12 Tf"
        " 2 0 0 2 72 700 Tm"
        " (scaled) Tj ET")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == [
        "scaled",
    ]


# ---------- 坐标与资源 ----------

def test_offpage_coords_extracted(
        tmp_path):
    p = _pdf(
        tmp_path, "far.pdf",
        "BT /F1 12 Tf"
        " 72000 70000 Td"
        " (far) Tj ET")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == [
        "far",
    ]
    assert doc.warnings == []


def test_missing_font_still_extracted(
        tmp_path):
    p = _pdf_no_f2(
        tmp_path, "mf.pdf",
        "BT /F2 12 Tf 72 700 Td"
        " (ghost font) Tj ET")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == [
        "ghost font",
    ]
    assert doc.warnings == []


def test_mid_line_font_switch(
        tmp_path):
    p = _pdf(
        tmp_path, "fs.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (small) Tj /F2 24 Tf"
        " 72 650 Td (big) Tj ET")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == [
        "big", "small",
    ]
