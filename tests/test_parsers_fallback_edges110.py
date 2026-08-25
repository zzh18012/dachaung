r"""app/parsers_fallback PDF 边角测试 - 第一百一十轮（Round 1540）。

新角度（probe 实证）页面几何变体（R1520 锁过 per-page
MediaBox 与小页坐标翻转；本轮锁 MediaBox **取值变体**
——扫描件常见的负原点/小数、退化值与 /UserUnit——零覆
盖）：

- **负原点 [-100 -100 512 692] → 完全忽略原点**：bbox
  与 [0 0 612 792] 基线一字不差（y 翻转只用高度、x 不
  平移）
- **小数高度 [0 0 612.5 792.25]** → bbox 随高度小数精
  确偏移（82.7/94.7）
- **零尺寸 [0 0 0 0]** → 退化接受、y 深负（-709.5，翻
  转高度 0）
- **巨型 [0 0 6120 7920]** → y 达 7210.5
- **倒序 [612 792 0 0]** → 宽高为负：x 移至 -540、y
  874.5（按负宽高参与翻转）
- **/UserUnit 2 → 完全忽略**（bbox 与默认一致）
- **横向 [0 0 792 612]** → 高度 612：内容 y=700 出界
  → 负 bbox（-97.5），不裁剪不警告
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

_CONTENT = ("BT /F1 12 Tf 72 700 Td"
            " (BODY) Tj ET")


def _els(tmp_path, name, media,
         extra=""):
    objs = [
        "<< /Type /Catalog"
        " /Pages 2 0 R >>",
        "<< /Type /Pages"
        " /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page"
        f" /Parent 2 0 R"
        f" /MediaBox [{media}]"
        f" {extra}"
        f" /Resources << /Font"
        f" << /F1 5 0 R >> >>"
        f" /Contents 4 0 R >>",
        f"<< /Length"
        f" {len(_CONTENT)} >>"
        f"\nstream\n{_CONTENT}\n"
        f"endstream",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding"
        " /WinAnsiEncoding >>",
    ]
    pdf = b"%PDF-1.4\n"
    for i, o in enumerate(objs):
        pdf += (f"{i + 1} 0 obj\n{o}"
                f"\nendobj\n"
                ).encode("latin-1")
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 6 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.warnings == []
    return [(e.content,
             [round(v, 1) for v in
              e.source_locator["bbox"]])
            for e in doc.elements]


def test_negative_origin_ignored(
        tmp_path):
    assert _els(
        tmp_path, "neg.pdf",
        "-100 -100 512 692") == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]


def test_fractional_media(tmp_path):
    assert _els(
        tmp_path, "frac.pdf",
        "0 0 612.5 792.25") == [
        ("BODY", [72.0, 82.7, 106.0,
                  94.7])]


def test_zero_size(tmp_path):
    assert _els(
        tmp_path, "zero.pdf",
        "0 0 0 0") == [
        ("BODY", [72.0, -709.5,
                  106.0, -697.5])]


def test_huge_media(tmp_path):
    assert _els(
        tmp_path, "huge.pdf",
        "0 0 6120 7920") == [
        ("BODY", [72.0, 7210.5,
                  106.0, 7222.5])]


def test_swapped_corners(tmp_path):
    assert _els(
        tmp_path, "swap.pdf",
        "612 792 0 0") == [
        ("BODY", [-540.0, 874.5,
                  -506.0, 886.5])]


def test_user_unit_ignored(tmp_path):
    assert _els(
        tmp_path, "uu.pdf",
        "0 0 612 792",
        "/UserUnit 2") == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]


def test_landscape_offpage(
        tmp_path):
    assert _els(
        tmp_path, "land.pdf",
        "0 0 792 612") == [
        ("BODY", [72.0, -97.5,
                  106.0, -85.5])]
