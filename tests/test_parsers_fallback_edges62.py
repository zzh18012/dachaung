r"""app/parsers/fallback_parser.py 边角测试 - 第六十二轮（Round 1469）。

新角度（probe 实证）**q/Q 图形状态 + cm 矩阵变换**（历史
只碰过 Tm/Td 定位，cm 家族与 q 嵌套从未探过）：
- cm **纯平移**：text bbox 整体搬到 (200,482..)
- cm **等比 2 倍缩放**（带平移）：字号 12 → bbox 高 24、
  宽也翻倍
- cm **仅横向 3 倍缩放**：宽 74.016、高仍 12
- cm **旋转 90°**：文本**字符倒序** '09tor'（rot90 → 09tor），
  bbox 窄高条
- cm **垂直翻转**：'flipped' → 'f lip p e d' 且 bbox 顶出
  页面（top-origin y 为负）
- **Tz 写在 BT 外**：pdfminer 不吃（大小不变）→ 两串同位
  置**逐字交错** 'hfaulfll'
- **q/q/q 嵌套无 cm**：无效入栈 → 'deep'/'after' 同位置
  交错 'daefteepr'
- **孤儿 Q**：无 q 配对也不崩，文本照出
- **cm 不包 q**：变换**持续生效**（后续文本仍 2 倍）
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


# ---------- cm 平移 ----------

def test_cm_translate(tmp_path):
    p = _pdf(
        tmp_path, "ct.pdf",
        "q 1 0 0 1 200 300 cm BT"
        " /F1 12 Tf (moved) Tj ET Q")
    doc = _parse(p)
    assert doc.elements[
        0].content == "moved"
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox[:2] == [200.0, 482.484]
    assert round(bbox[2], 3) == 236.012
    assert bbox[3] == 494.484


# ---------- cm 缩放 ----------

def test_cm_uniform_scale2(tmp_path):
    p = _pdf(
        tmp_path, "cs.pdf",
        "q 2 0 0 2 100 100 cm BT"
        " /F1 12 Tf (big) Tj ET Q")
    doc = _parse(p)
    assert doc.elements[
        0].content == "big"
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox == [
        100.0, 672.968,
        132.016, 696.968,
    ]
    assert bbox[3] - bbox[1] == 24.0


def test_cm_scale_x_only(tmp_path):
    p = _pdf(
        tmp_path, "cx.pdf",
        "q 3 0 0 1 0 0 cm BT"
        " /F1 12 Tf (wide) Tj ET Q")
    doc = _parse(p)
    assert doc.elements[
        0].content == "wide"
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox == [
        0.0, 782.484,
        74.016, 794.484,
    ]


# ---------- cm 旋转 / 翻转 ----------

def test_cm_rotate90_reverses(
        tmp_path):
    p = _pdf(
        tmp_path, "cr.pdf",
        "q 0 1 -1 0 306 396 cm BT"
        " /F1 12 Tf (rot90) Tj ET Q")
    doc = _parse(p)
    assert doc.elements[
        0].content == "09tor"
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox == [
        296.484, 368.652,
        308.484, 396.0,
    ]


def test_cm_flip_y_negative_bbox(
        tmp_path):
    p = _pdf(
        tmp_path, "cf.pdf",
        "q 1 0 0 -1 0 792 cm BT"
        " /F1 12 Tf (flipped) Tj ET Q")
    doc = _parse(p)
    assert doc.elements[
        0].content == "f lip p e d"
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox[1] < 0
    assert bbox[3] < 12


# ---------- 状态语义 ----------

def test_tz_outside_bt_ignored(
        tmp_path):
    p = _pdf(
        tmp_path, "tz.pdf",
        "q 50 Tz BT /F1 12 Tf"
        " (half) Tj ET Q BT /F1 12 Tf"
        " (full) Tj ET")
    doc = _parse(p)
    assert len(doc.elements) == 1
    assert doc.elements[
        0].content == "hfaulfll"


def test_nested_q_without_cm_noop(
        tmp_path):
    p = _pdf(
        tmp_path, "qq.pdf",
        "q q q BT /F1 12 Tf (deep)"
        " Tj ET Q Q Q BT /F1 12 Tf"
        " (after) Tj ET")
    doc = _parse(p)
    assert doc.elements[
        0].content == "daefteepr"


def test_orphan_q_no_crash(tmp_path):
    p = _pdf(
        tmp_path, "oq.pdf",
        "Q Q BT /F1 12 Tf (orphan)"
        " Tj ET")
    doc = _parse(p)
    assert doc.elements[
        0].content == "orphan"
    assert doc.warnings == []


def test_cm_without_q_sticky(
        tmp_path):
    p = _pdf(
        tmp_path, "st.pdf",
        "2 0 0 2 50 50 cm BT"
        " /F1 12 Tf (sticky) Tj ET")
    doc = _parse(p)
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox[:2] == [50.0, 722.968]
    assert round(bbox[2], 3) == 110.0
    assert bbox[3] == 746.968
