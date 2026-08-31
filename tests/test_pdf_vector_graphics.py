"""PDF 矢量图形聚类检测测试（Stage 7 批次 15，Option A 裁决）。

背景：pdfplumber page.images 只含栅格 XObject（/Subtype /Image），
矢量图形（Form XObject 或直接 path 绘制）完全不可见 → 003-PDF 插图、
002-PDF 封面/封底艺术、004-P2 矢量折线图全部漏计。
修复：_vector_figure_clusters 把 rects/lines/curves 按 bbox 空间聚类
（gap 15pt），簇含 ≥1 curve 且 bbox ≥100×100pt 计 1 个矢量图。

测试用合成 PDF（手写最小 PDF 字节，无新增依赖）：
- 多段路径（m … c S）→ pdfplumber curve 对象
- 单段线（m … l S）→ line；re 操作符 → rect
- 栅格用 /Subtype /Image XObject 内嵌（zlib 压缩原始 RGB）
"""

from __future__ import annotations

import zlib
from pathlib import Path

import pytest

from app.schema import validate as validate_udm

pdfplumber = pytest.importorskip("pdfplumber", reason="pdfplumber 未安装")

from app.parsers.fallback_parser import FallbackParser  # noqa: E402


def _make_pdf(path: Path, content_stream: str, extra_objs: dict[int, bytes] | None = None,
              resources: str = "<< >>") -> None:
    """写最小单页 PDF（MediaBox 595×842）。"""
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources {resources} /Contents 4 0 R >>").encode(),
    }
    content = content_stream.encode("latin-1")
    objs[4] = (b"<< /Length " + str(len(content)).encode()
               + b" >>\nstream\n" + content + b"\nendstream")
    if extra_objs:
        objs.update(extra_objs)
    out = b"%PDF-1.4\n"
    offsets: dict[int, int] = {}
    for i in sorted(objs):
        offsets[i] = len(out)
        out += f"{i} 0 obj\n".encode() + objs[i] + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n0000000000 65535 f \n"
    for i in sorted(objs):
        out += f"{offsets[i]:010d} 00000 n \n".encode()
    out += (b"trailer\n<< /Size " + str(len(objs) + 1).encode()
            + b" /Root 1 0 R >>\nstartxref\n" + str(xref_pos).encode() + b"\n%%EOF")
    path.write_bytes(out)


def _parse(tmp_path: Path, content_stream: str, **kw) -> dict:
    p = tmp_path / "synthetic.pdf"
    _make_pdf(p, content_stream, **kw)
    doc = FallbackParser().parse(p, source_hash="a" * 64)
    return doc.to_dict()


def _images(d: dict) -> list[dict]:
    return [e for e in d["elements"] if e["type"] == "image"]


# 大曲线：pdfplumber curve bbox 取锚点（起点→终点）hull，此处 150×150
CURVE_BIG = "0 0 0 RG 2 w\n100 700 m 180 690 220 600 250 550 c S\n"
# 小曲线：50×10（公式根号形态）
CURVE_SMALL = "0 0 0 RG 1 w\n100 400 m 150 415 120 395 150 390 c S\n"


# ---------- 1. 单条大曲线 → 1 个矢量图 ----------

def test_vector_graphic_single_curve(tmp_path: Path):
    d = _parse(tmp_path, CURVE_BIG)
    imgs = _images(d)
    assert len(imgs) == 1
    assert imgs[0]["metadata"]["kind"] == "vector_cluster"
    assert imgs[0]["confidence"] == 0.5
    assert imgs[0]["resource_path"] == "(unrendered)"
    assert imgs[0]["source_locator"]["page"] == 1
    bb = imgs[0]["source_locator"]["bbox"]
    assert bb[0] == pytest.approx(100) and bb[2] == pytest.approx(250)
    validate_udm(d)


# ---------- 2. 曲线 + 矩形混合簇（gap 10pt）→ 1 个矢量图 ----------

def test_vector_graphic_curve_rect_cluster(tmp_path: Path):
    # 曲线锚点 y[550,700]；矩形 y[440,540]（间距 10pt）→ 聚为一簇
    stream = CURVE_BIG + "0 0 0 RG 0.7 w\n110 440 130 100 re S\n"
    d = _parse(tmp_path, stream)
    imgs = _images(d)
    assert len(imgs) == 1
    assert imgs[0]["metadata"]["kind"] == "vector_cluster"
    bb = imgs[0]["source_locator"]["bbox"]
    assert bb[3] - bb[1] >= 100 and bb[2] - bb[0] >= 100  # 簇整体 ≥100×100


# ---------- 3. 小曲线簇（<100×100）排除 ----------

def test_small_curve_excluded(tmp_path: Path):
    d = _parse(tmp_path, CURVE_SMALL)
    assert _images(d) == []


# ---------- 4. 纯 rects+lines 表格不误报 ----------

def test_table_rects_not_detected(tmp_path: Path):
    # 表格网格：单段线 + re 矩形（真实 corpus 表格均为单段线，零 curves）
    rows = "".join(
        f"\n100 {700 - i * 60} m 480 {700 - i * 60} l S" for i in range(6)
    )
    cols = "".join(
        f"\n{100 + j * 95} 400 m {100 + j * 95} 700 l S" for j in range(5)
    )
    stream = "0 0 0 RG 0.5 w" + rows + cols + "\n100 400 380 300 re S\n"
    d = _parse(tmp_path, stream)
    assert _images(d) == []


# ---------- 5. 栅格图与矢量图共存，各自计数 ----------

def test_raster_and_vector_coexist(tmp_path: Path):
    raw = bytes([(i * 7) % 256 for i in range(8 * 8 * 3)])
    img_obj = (
        b"5 0 obj << /Type /XObject /Subtype /Image /Width 8 /Height 8 "
        b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Length "
        + str(len(raw)).encode()
        + b" >>\nstream\n" + raw + b"\nendstream\nendobj"
    )
    resources = "<< /XObject << /Im1 5 0 R >> >>"
    stream = "q 300 300 120 120 cm /Im1 Do Q\n" + CURVE_BIG
    p = tmp_path / "synthetic.pdf"
    _make_pdf(p, stream, extra_objs={5: img_obj}, resources=resources)
    d = FallbackParser().parse(p, source_hash="a" * 64).to_dict()
    imgs = _images(d)
    assert len(imgs) == 2
    rasters = [e for e in imgs if e["metadata"].get("kind") != "vector_cluster"]
    vectors = [e for e in imgs if e["metadata"].get("kind") == "vector_cluster"]
    assert len(rasters) == 1 and len(vectors) == 1
    validate_udm(d)


# ---------- 6. gap=15pt：近距合并 / 远距分开 ----------

def test_clustering_gap_15pt(tmp_path: Path):
    # 两条曲线锚点 hull y[660,780] 与 y[540,650]，间距 10pt ≤ 15 → 1 簇
    near = (
        "0 0 0 RG 2 w\n100 780 m 160 770 180 690 200 660 c S\n"
        "100 650 m 160 640 180 570 200 540 c S\n"
    )
    d = _parse(tmp_path, near)
    assert len(_images(d)) == 1

    # 第二条下移，间距 50pt > 15 → 2 簇（各 100×120）
    far = (
        "0 0 0 RG 2 w\n100 780 m 160 770 180 690 200 660 c S\n"
        "100 610 m 160 600 180 530 200 500 c S\n"
    )
    d = _parse(tmp_path, far)
    imgs = _images(d)
    assert len(imgs) == 2
    assert all(e["metadata"]["kind"] == "vector_cluster" for e in imgs)


# ---------- 7. bbox 重叠的图形聚为 1 簇 ----------

def test_overlapping_graphics_clustered(tmp_path: Path):
    stream = (
        "0 0 0 RG 2 w\n100 700 m 180 690 220 600 250 550 c S\n"
        "150 690 m 240 680 270 600 300 560 c S\n"
    )
    d = _parse(tmp_path, stream)
    imgs = _images(d)
    assert len(imgs) == 1
    bb = imgs[0]["source_locator"]["bbox"]
    assert bb[0] == pytest.approx(100) and bb[2] == pytest.approx(300)


# ---------- 8. 边界：簇 bbox 恰好 100×100 → 包含 ----------

def test_boundary_100x100pt(tmp_path: Path):
    # 锚点 (100,600)→(200,500)：锚点 hull 恰好 100×100
    stream = "0 0 0 RG 2 w\n100 600 m 180 590 160 530 200 500 c S\n"
    d = _parse(tmp_path, stream)
    imgs = _images(d)
    assert len(imgs) == 1
    bb = imgs[0]["source_locator"]["bbox"]
    assert (bb[2] - bb[0]) == pytest.approx(100.0)
    assert (bb[3] - bb[1]) == pytest.approx(100.0)
