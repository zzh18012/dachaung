r"""PDF 离页/越界图片渲染语义锁定（Round 1921，a 优先级）。

R1896 锁零宽静默跳过；edges3 用 monkeypatch 锁单图 render 失败。
本轮全部走**真实 PDF 路径**（合成 XObject 放置，零 monkeypatch），
探针 R1921 实证：

- **完全离页图**（整框越出 MediaBox 顶部，bbox top=-108..-8）：
  pdfplumber 照常报告（无页面裁剪）→ 元素保留 resource
  "(unrendered)" + warning `pdf_image_render_failed`，无 PNG 落盘
- **失败不占号**：image_counter 只在渲染成功时递增（:355）——
  离页图（失败）+ 在页图（成功）→ 在页图拿 **_p1_00**（若失败
  占号应为 _p1_01）
- **半离页/负 x 钳制渲染**：部分越出（top -50..50）或 x0=-50 →
  crop 钳制到页面范围后非退化 → 正常落盘（越出部分丢弃）

判别式：image_counter 改为无条件递增 → 失败不占号测试翻红；
crop 不做 max(0,...) 钳制 → 钳制渲染测试翻红（负坐标进 PIL.crop
抛 ValueError）。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf


def _parse(tmp_path: Path, content: str):
    p = tmp_path / "d.pdf"
    p.write_bytes(_pdf([content.encode("latin-1")]))
    img_dir = tmp_path / "imgs"
    doc = FallbackParser(image_output_dir=str(img_dir)).parse(
        p, compute_file_hash(p))
    return doc, img_dir


def test_fully_offpage_image_element_kept_with_render_failure(tmp_path):
    """整框离顶（PDF y 800 h 100 → top 坐标 -108..-8）：元素保留、
    resource "(unrendered)"、warning pdf_image_render_failed、零 PNG。"""
    doc, img_dir = _parse(tmp_path, "q 100 0 0 100 450 800 cm /Im1 Do Q")
    images = [e for e in doc.elements if e.type == "image"]
    assert len(images) == 1
    img = images[0]
    # pdfplumber 不做页面裁剪：负坐标 bbox 原样进 locator
    assert img.source_locator["bbox"] == [450.0, -108.0, 550.0, -8.0]
    assert img.resource_path == "(unrendered)"
    assert img.metadata["extracted_to_disk"] is False
    assert [w.code for w in doc.warnings] == ["pdf_image_render_failed"]
    assert list(img_dir.glob("*.png")) == []


def test_render_failure_does_not_consume_image_counter(tmp_path):
    """离页图（失败）先画 + 在页图（成功）后画 → 在页图拿 _p1_00
    ——counter 只计成功渲染；盘上恰一个 PNG。"""
    doc, img_dir = _parse(tmp_path, (
        "q 100 0 0 100 450 800 cm /Im1 Do Q\n"
        "q 100 0 0 100 450 50 cm /Im1 Do Q"))
    images = [e for e in doc.elements if e.type == "image"]
    assert len(images) == 2
    failed, ok = images
    assert failed.resource_path == "(unrendered)"
    assert failed.source_locator["bbox"][1] < 0
    # 判别式：失败若占号，ok 应是 _p1_01
    assert Path(ok.resource_path).name.endswith("_p1_00.png")
    assert ok.metadata["extracted_to_disk"] is True
    assert any(w.code == "pdf_image_render_failed" for w in doc.warnings)
    pngs = sorted(p.name for p in img_dir.glob("*.png"))
    assert pngs == [Path(ok.resource_path).name]


def test_partially_offpage_placements_clamp_and_render(tmp_path):
    """半离顶（top -50..50）与负 x（x0=-50）两放置：crop 钳制到页面
    范围后非退化 → 均正常落盘，各拿自己的编号。"""
    half_off = tmp_path / "half.pdf"
    half_off.write_bytes(_pdf(["q 100 0 0 100 450 742 cm /Im1 Do Q".encode()]))
    d1 = FallbackParser(image_output_dir=str(tmp_path / "i1")).parse(
        half_off, compute_file_hash(half_off))
    neg_x = tmp_path / "negx.pdf"
    neg_x.write_bytes(_pdf(["q 100 0 0 100 -50 600 cm /Im1 Do Q".encode()]))
    d2 = FallbackParser(image_output_dir=str(tmp_path / "i2")).parse(
        neg_x, compute_file_hash(neg_x))
    for doc, img_dir, bbox in (
        (d1, tmp_path / "i1", [450.0, -50.0, 550.0, 50.0]),
        (d2, tmp_path / "i2", [-50.0, 92.0, 50.0, 192.0]),
    ):
        images = [e for e in doc.elements if e.type == "image"]
        assert len(images) == 1
        img = images[0]
        assert img.source_locator["bbox"] == bbox
        assert img.metadata["extracted_to_disk"] is True
        assert img.resource_path != "(unrendered)"
        assert [w.code for w in doc.warnings] == []
        assert (Path(img.resource_path)).exists()
    assert [w.code for w in d1.warnings] == []
    assert [w.code for w in d2.warnings] == []
