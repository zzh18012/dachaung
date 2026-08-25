r"""app/parsers/fallback_parser.py 边角测试 - 第六十六轮（Round 1483）。

新角度（probe 实证）字号退化 + 奇长度十六进制 + 同位叠印
+ 空白位移（edges1-65 未碰过；edges55 已锁 Tf 0 点 bbox
与 Tf 负镜像、edges56 已锁偶长度 hex 串与 \( \) 转义、
edges30 已锁八进制与 () 空串、edges35 已锁常规 hex，避开）：
- **奇长度十六进制串**：'<414>' → 'A(cid:4)'——尾巴半字节
  解成不可映射 CID 占位符（edges56 的 (cid:) 由 \\t 触发，
  此处由奇 hex 触发，不同入口）
- **Tf 1 微字号**：bbox 高度精确 1.0（791.207-792.207）
- **Tf 12.5 小数字号**：bbox 高度 12.5（782.0875-794.5875）
- **同行混字号**：12pt 'big' + 24pt 'SMALL24' 同 y → 单
  元素 'SMALL24 big'、bbox 跨两行高（772.968-796.968）
- **同位叠印**：'dup' 两次画在同位置 → 'dduupp'（重叠
  字符 x 排序交织）
- **纯空格 Tj**：'(   ) Tj' → 无元素 + pdf_no_text_extracted
- **空格位移**：'(   ) Tj (real) Tj' → 空格推进 x0 至
  10.008、内容只剩 'real'
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _pdf(tmp_path, name, content):
    pdf = (f"%PDF-1.4\n"
           f"1 0 obj\n<< /Type /Catalog"
           f" /Pages 2 0 R >>\nendobj\n"
           f"2 0 obj\n<< /Type /Pages"
           f" /Kids [3 0 R] /Count 1"
           f" >>\nendobj\n"
           f"3 0 obj\n<< /Type /Page"
           f" /Parent 2 0 R"
           f" /MediaBox [0 0 612 792]"
           f" /Resources << /Font"
           f" << /F1 5 0 R >> >>"
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
           f" >>\nendobj\n"
           f"trailer\n<< /Root 1 0 R"
           f" /Size 6 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf.encode("latin-1"))
    return p


def _parse(p):
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- 奇长度十六进制 ----------

def test_hex_odd_nibble_cid(tmp_path):
    p = _pdf(
        tmp_path, "hexodd.pdf",
        "BT /F1 12 Tf <414> Tj ET")
    doc = _parse(p)
    e = doc.elements[0]
    assert e.content == "A(cid:4)"
    assert doc.warnings == []


# ---------- 字号退化 ----------

def test_tiny_font_bbox_height_one(tmp_path):
    p = _pdf(
        tmp_path, "tiny.pdf",
        "BT /F1 1 Tf (tiny) Tj ET")
    doc = _parse(p)
    e = doc.elements[0]
    assert e.content == "tiny"
    bbox = e.source_locator["bbox"]
    assert bbox[3] - bbox[1] == 1.0


def test_fractional_font_size(tmp_path):
    p = _pdf(
        tmp_path, "frac.pdf",
        "BT /F1 12.5 Tf (half) Tj ET")
    doc = _parse(p)
    e = doc.elements[0]
    assert e.content == "half"
    bbox = e.source_locator["bbox"]
    assert round(
        bbox[3] - bbox[1], 4) == 12.5


def test_mixed_sizes_same_line(tmp_path):
    p = _pdf(
        tmp_path, "mix.pdf",
        "BT /F1 12 Tf (big) Tj"
        " /F1 24 Tf (SMALL24) Tj ET")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == [
        "SMALL24 big",
    ]
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert round(bbox[1], 3) == 772.968
    assert round(bbox[3], 3) == 796.968


# ---------- 同位叠印 ----------

def test_overprint_interleaves(tmp_path):
    p = _pdf(
        tmp_path, "ovp.pdf",
        "BT /F1 12 Tf (dup) Tj"
        " 0 0 Td (dup) Tj ET")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == [
        "dduupp",
    ]
    assert doc.warnings == []


# ---------- 空格行为 ----------

def test_space_only_tj_no_text(tmp_path):
    p = _pdf(
        tmp_path, "sp.pdf",
        "BT /F1 12 Tf (   ) Tj ET")
    doc = _parse(p)
    assert doc.elements == []
    assert [w.code for w in doc.warnings] \
        == ["pdf_no_text_extracted"]


def test_leading_spaces_shift_x(tmp_path):
    p = _pdf(
        tmp_path, "sh.pdf",
        "BT /F1 12 Tf (   ) Tj"
        " (real) Tj ET")
    doc = _parse(p)
    e = doc.elements[0]
    assert e.content == "real"
    bbox = e.source_locator["bbox"]
    assert round(bbox[0], 3) == 10.008
    assert round(bbox[2], 3) == 30.012
