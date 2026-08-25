r"""app/parsers/fallback_parser.py 边角测试 - 第六十三轮（Round 1472）。

新角度（probe 实证）marked-content + 未知资源 + 嵌套 BT
（edges1-62 未碰过；图片 /Im Do 与 re S 画线表格已由
edges17/27/46 锁定，避开）：
- **BDC/BMC/EMC 标记内容完全透明**：文本照常提取、bbox
  正常（MCID 属性被 pdfminer 忽略）；**未闭合 BDC**（无
  EMC）也容忍
- **未知 XObject Do 静默忽略**：/Missing Do 不产告警、
  后续文本存活
- **裁剪路径 W n 不裁剪提取**：bbox 不受 re+W n 影响
  （pdfplumber 不模拟 clipping）
- **缺失 gs 资源**：/GState1 gs 被忽略无告警
- **sh 轴渐变**忽略
- **BT 嵌套 BT**（无中间 ET）：两串文本都提取，top-origin
  y 排序内层（Td 72 700）在前
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


# ---------- marked-content ----------

def test_bdc_emc_transparent(tmp_path):
    p = _pdf(
        tmp_path, "bdc.pdf",
        "/P <</MCID 0>> BDC BT"
        " /F1 12 Tf (marked text) Tj"
        " ET EMC")
    doc = _parse(p)
    assert doc.elements[
        0].content == "marked text"
    assert doc.elements[
        0].source_locator["bbox"] == [
        0.0, 782.484,
        62.68799999999999, 794.484,
    ]
    assert doc.warnings == []


def test_bmc_emc_transparent(tmp_path):
    p = _pdf(
        tmp_path, "bmc.pdf",
        "BMC BT /F1 12 Tf"
        " (bmc text) Tj ET EMC")
    doc = _parse(p)
    assert doc.elements[
        0].content == "bmc text"


def test_unbalanced_bdc_tolerated(
        tmp_path):
    p = _pdf(
        tmp_path, "ubdc.pdf",
        "/P <</MCID 1>> BDC BT"
        " /F1 12 Tf (in bdc) Tj ET")
    doc = _parse(p)
    assert doc.elements[
        0].content == "in bdc"
    assert doc.warnings == []


# ---------- 未知资源 ----------

def test_unknown_do_silent(tmp_path):
    p = _pdf(
        tmp_path, "udo.pdf",
        "/Missing Do BT /F1 12 Tf"
        " (after missing) Tj ET")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == \
        ["after missing"]
    assert doc.warnings == []


def test_missing_gs_ignored(tmp_path):
    p = _pdf(
        tmp_path, "gs.pdf",
        "/GState1 gs BT /F1 12 Tf"
        " (gs text) Tj ET")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == \
        ["gs text"]
    assert doc.warnings == []


def test_sh_operator_ignored(
        tmp_path):
    p = _pdf(
        tmp_path, "sh.pdf",
        "0 0 200 200 re W n /Sh1 sh"
        " BT /F1 12 Tf (after sh) Tj"
        " ET")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == \
        ["after sh"]


# ---------- 裁剪 ----------

def test_clip_not_applied(tmp_path):
    p = _pdf(
        tmp_path, "clip.pdf",
        "0 0 50 50 re W n BT"
        " /F1 12 Tf (clipped region)"
        " Tj ET")
    doc = _parse(p)
    e = doc.elements[0]
    assert e.content == "clipped region"
    bbox = e.source_locator["bbox"]
    assert bbox[2] == 74.7
    assert bbox[3] == 794.484


# ---------- 嵌套 BT ----------

def test_nested_bt_both_extracted(
        tmp_path):
    p = _pdf(
        tmp_path, "nbt.pdf",
        "BT /F1 12 Tf (outer) Tj"
        " BT /F1 12 Tf 72 700 Td"
        " (inner) Tj ET ET")
    doc = _parse(p)
    assert [(e.content,
             e.source_locator["bbox"][0])
            for e in doc.elements] == [
        ("inner", 72.0),
        ("outer", 0.0),
    ]
