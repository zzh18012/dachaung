r"""PDF 内联图片 BI/ID/EI（非 XObject）（Round 1966，a 优先级）。

既有图片测试全走 /Resources /XObject /Im1 Do（广扫
BI/ID/EI、inline image 零匹配）；小图形/图标的真实 PDF 常
内联。探针 R1966 实证（pdfplumber page.images 收内联图，
与 XObject 同路径全平权——元素/cm 变换 bbox/盘渲染/编号/
srcsize 透传）：

- **I1 文本 + 单内联图**（q cm BI /W /H /CS /BPC ID…EI Q，
  cm 100×50 @ (200,100)）→ image 元素 bbox [200, 642,
  300, 692]（top = 792−150）、PNG 落盘 p1_00、srcsize
  [2,1] 透传、文本不受扰、零告警
- **I2 双内联图** → 顺序编号 p1_00 / p1_01、两 bbox 各准
- **I3 XObject Do + 内联图同页** → 双图都提取、**内容顺序
  保持**（XObject 在前 p1_00、内联在后 p1_01）、编号连续

判别式：若 pdfplumber/解析器不收内联图则 I1 无 image 元素
翻红；若编号按图型分池则 I3 顺序/编号翻红。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf


def _inline(w: int, h: int, cm: bytes, data: bytes) -> bytes:
    return (b"q " + cm + b" cm\nBI\n/W " + str(w).encode()
            + b"\n/H " + str(h).encode()
            + b"\n/CS /DeviceRGB\n/BPC 8\nID " + data + b"\nEI\nQ\n")


_TXT = b"BT /F1 12 Tf 72 700 Td (INLINETXT) Tj ET\n"
_D6 = b"\xff\x00\x00\x00\xff\x00"


def _parse(contents: list[bytes]):
    with tempfile.TemporaryDirectory() as td:
        outdir = Path(td) / "img"
        p = Path(td) / "i.pdf"
        p.write_bytes(_pdf(contents))
        d = FallbackParser(image_output_dir=outdir).parse(p, compute_file_hash(p))
        return d, sorted(f.name for f in outdir.iterdir())


def test_single_inline_image_element_and_render():
    """I1：单内联图 → image 元素 bbox 由 cm 定、PNG 落盘、
    srcsize [2,1]、文本照提零告警。"""
    d, files = _parse([_TXT + _inline(2, 1, b"100 0 0 50 200 100", _D6)])
    assert [e.type for e in d.elements] == ["heading", "image"]
    img = d.elements[1]
    assert img.content is None
    assert img.source_locator["page"] == 1
    assert img.source_locator["bbox"] == pytest.approx(
        [200.0, 642.0, 300.0, 692.0], abs=0.01)
    assert img.metadata["srcsize"] == [2, 1]
    assert img.metadata["extracted_to_disk"] is True
    assert len(files) == 1 and files[0].endswith("_p1_00.png")
    assert d.warnings == []


def test_two_inline_images_sequential_numbering():
    """I2：双内联图 → p1_00 / p1_01 顺序编号、bbox 各准。"""
    d, files = _parse([_TXT
                       + _inline(2, 1, b"100 0 0 50 200 100", _D6)
                       + _inline(2, 1, b"40 0 0 40 400 200", _D6)])
    imgs = [e for e in d.elements if e.type == "image"]
    assert len(imgs) == 2
    assert imgs[0].source_locator["bbox"] == pytest.approx(
        [200.0, 642.0, 300.0, 692.0], abs=0.01)
    assert imgs[1].source_locator["bbox"] == pytest.approx(
        [400.0, 552.0, 440.0, 592.0], abs=0.01)
    assert [f for f in files if f.endswith("p1_00.png")]
    assert [f for f in files if f.endswith("p1_01.png")]
    assert d.warnings == []


def test_xobject_and_inline_same_page_content_order():
    """I3：XObject Do + 内联图同页 → 都提取、内容顺序保持
    （XObject p1_00 在前、内联 p1_01 在后）、srcsize [1,1]
    vs [2,1] 可辨来源。"""
    d, files = _parse([_TXT
                       + b"q 100 0 0 30 500 600 cm /Im1 Do Q\n"
                       + _inline(2, 1, b"100 0 0 50 200 100", _D6)])
    imgs = [e for e in d.elements if e.type == "image"]
    assert len(imgs) == 2
    assert imgs[0].source_locator["bbox"] == pytest.approx(
        [500.0, 162.0, 600.0, 192.0], abs=0.01)
    assert imgs[0].metadata["srcsize"] == [1, 1]
    assert imgs[1].source_locator["bbox"] == pytest.approx(
        [200.0, 642.0, 300.0, 692.0], abs=0.01)
    assert imgs[1].metadata["srcsize"] == [2, 1]
    assert any(f.endswith("_p1_00.png") for f in files)
    assert any(f.endswith("_p1_01.png") for f in files)
    assert d.elements[0].content == "INLINETXT"
    assert d.warnings == []
