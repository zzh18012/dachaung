r"""PDF 混合页尺寸 + 小页右缘越界图锁定（Round 1930，a 优先级）。

评测侧 edges150+ 已用单尺寸 400x800 页（页族度量语境）；
**同文档混合页尺寸**零覆盖。探针 R1930 实证（per-page
MediaBox：p1 612x792 / p2 300x300）：

- **M1 混合尺寸正常抽取**：两页文本各自成元素、pages=[1,2]、
  bbox 落各自坐标系（小页 y 翻转按页高 300 计算）、零告警
- **M2 小页右缘越界图**：p2（宽 300）上 x 450-550 图 → 元素
  保留、bbox 超 MediaBox 宽（pdfplumber 不裁剪）；渲染 crop
  钳制 x1=min(页宽) → 退化 → resource_path=="(unrendered)" +
  warning `pdf_image_render_failed`——R1921 顶缘（height 钳制）
  的 **width 版**
- **M3 界内图不受累**：同页 x 50-150 图渲染成功且拿到
  _p2_00（成功才计数，失败图不占号——R1921 计数规则的
  小页重放）

判别式：若渲染改为按绝对坐标（忽略页 MediaBox）或越界
bbox 被裁剪，M2/M3 断言翻红；若页尺寸参与文本抽取坐标，
M1 翻红。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

_IMG = (b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 "
        b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Length 3 >>\n"
        b"stream\n\xff\x00\x00\nendstream")
_FONT = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"


def _pdf_mixed(pages: list[tuple[bytes, str]]) -> bytes:
    """pages: (content, mediabox)；image=3+2n, font=4+2n。"""
    n = len(pages)
    img_oid, font_oid = 3 + 2 * n, 4 + 2 * n
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (b"<< /Type /Pages /Kids ["
            + b" ".join(f"{3 + 2 * i} 0 R".encode() for i in range(n))
            + b"] /Count " + str(n).encode() + b" >>"),
        img_oid: _IMG,
        font_oid: _FONT,
    }
    for i, (content, box) in enumerate(pages):
        objs[3 + 2 * i] = (b"<< /Type /Page /Parent 2 0 R /MediaBox ["
                           + box.encode()
                           + b"] /Resources << /Font << /F1 "
                           + str(font_oid).encode() + b" 0 R >> "
                           + b"/XObject << /Im1 " + str(img_oid).encode()
                           + b" 0 R >> >> /Contents "
                           + str(4 + 2 * i).encode() + b" 0 R >>")
        objs[4 + 2 * i] = (b"<< /Length " + str(len(content)).encode()
                           + b" >>\nstream\n" + content + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref_pos = len(out)
    max_oid = max(objs)
    out += f"xref\n0 {max_oid + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for oid in range(1, max_oid + 1):
        out += ("%010d 00000 n \n" % offsets[oid]).encode()
    out += (b"trailer\n<< /Size " + str(max_oid + 1).encode()
            + b" /Root 1 0 R >>\nstartxref\n" + str(xref_pos).encode()
            + b"\n%%EOF")
    return bytes(out)


_BIG_TEXT = b"BT /F1 12 Tf 72 700 Td (big page text) Tj ET"
_SMALL_TEXT = b"BT /F1 12 Tf 72 100 Td (small page text) Tj ET"
_SMALL_PAGE = "0 0 300 300"


def _parse(tmp_path: Path, pages, with_img_dir=False):
    p = tmp_path / "m.pdf"
    p.write_bytes(_pdf_mixed(pages))
    img_dir = tmp_path / "imgs"
    if with_img_dir:
        img_dir.mkdir()
    parser = FallbackParser(
        image_output_dir=str(img_dir) if with_img_dir else None)
    doc = parser.parse(p, compute_file_hash(p))
    return doc, (img_dir if with_img_dir else None)


def test_mixed_page_sizes_text_extraction(tmp_path):
    """M1：p1 612x792 + p2 300x300 文本各自成元素、pages=[1,2]、
    小页 y 坐标按页高 300 翻转（top > 150）、零告警。"""
    doc, _ = _parse(tmp_path, [
        (_BIG_TEXT, "0 0 612 792"), (_SMALL_TEXT, _SMALL_PAGE)])
    assert [(e.content, e.source_locator["page"])
            for e in doc.elements] == [
        ("big page text", 1), ("small page text", 2)]
    small = doc.elements[1]
    # 页高 300、基线 y=100 → top-from-top ≈ 188-202 带（按 792 翻转则 ~690）
    assert 150 < small.source_locator["bbox"][1] < 220
    assert doc.warnings == []


def test_small_page_right_edge_image_render_fails(tmp_path):
    """M2：小页（宽 300）上 x 450-550 图 → 元素保留、bbox 超
    MediaBox 宽；渲染 width 钳制退化 → "(unrendered)" + 告警。"""
    content = (_SMALL_TEXT + b"\nq 100 0 0 100 450 150 cm /Im1 Do Q")
    doc, _ = _parse(tmp_path, [
        (_BIG_TEXT, "0 0 612 792"), (content, _SMALL_PAGE)],
        with_img_dir=True)
    images = [e for e in doc.elements if e.type == "image"]
    assert len(images) == 1
    img = images[0]
    assert img.source_locator["bbox"] == [450.0, 50.0, 550.0, 150.0]
    assert img.resource_path == "(unrendered)"
    assert img.metadata["extracted_to_disk"] is False
    assert [w.code for w in doc.warnings] == ["pdf_image_render_failed"]


def test_small_page_inbounds_image_renders_despite_neighbor(tmp_path):
    """M3：同页界内图渲染成功且拿 _p2_00——失败图不占号（成功才
    计数）；失败与成功并存时恰一 PNG。"""
    content = (_SMALL_TEXT + b"\n"
               + b"q 100 0 0 100 450 150 cm /Im1 Do Q\n"
               + b"q 100 0 0 100 50 150 cm /Im1 Do Q")
    doc, img_dir = _parse(tmp_path, [
        (_BIG_TEXT, "0 0 612 792"), (content, _SMALL_PAGE)],
        with_img_dir=True)
    images = [e for e in doc.elements if e.type == "image"]
    assert [i.metadata["extracted_to_disk"] for i in images] == [False, True]
    ok = images[1]
    assert Path(ok.resource_path).name.endswith("_p2_00.png")
    pngs = sorted(x.name for x in img_dir.glob("*.png"))
    assert len(pngs) == 1 and pngs[0].endswith("_p2_00.png")
