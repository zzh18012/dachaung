r"""PDF 图片文件名全局 counter 编号 + 零宽图静默跳过锁定（Round 1896，a 优先级）。

edges17 只锁过单图 p1_00 正则；**多页多图编号语义**与**退化几何跳过**
零覆盖。探针 R1896 实证（`_parse_pdf` :250 image_counter 页循环外
初始化 + :340 前缀 p{page_idx} 但 index 用全局 counter；:326
`x1 <= x0 or bottom <= top` 直接 continue）：

- **页内顺序编号**：同页两图 → _p1_00 / _p1_01（顺序无意外，作基线）
- **counter 是全局的**：第二页唯一图片文件名是 **_p2_02**——页前缀
  + 全局索引的错配组合：每页前缀暗示"每页编号"，索引却跨页延续
  （p2_02 是第 2 页唯一的图，若按页归零应为 p2_00）
- **零宽图静默丢弃**：cm 矩阵宽 0 的放置（x1 == x0）不产生元素也
  不产生告警——silent drop 无痕迹；同页正常图不受影响
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

_IMG = (b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 "
        b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Length 3 >>\n"
        b"stream\n\xff\x00\x00\nendstream")
_FONT = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"


def _pdf(contents: list[bytes]) -> bytes:
    """页 i → 对象 3+2i（页）/4+2i（内容）；image=3+2n，font=4+2n，全连续。"""
    n = len(contents)
    img_oid, font_oid = 3 + 2 * n, 4 + 2 * n
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (b"<< /Type /Pages /Kids ["
            + b" ".join(f"{3 + 2 * i} 0 R".encode() for i in range(n))
            + b"] /Count " + str(n).encode() + b" >>"),
        img_oid: _IMG,
        font_oid: _FONT,
    }
    for i, content in enumerate(contents):
        objs[3 + 2 * i] = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                           b"/Resources << /Font << /F1 " + str(font_oid).encode()
                           + b" 0 R >> /XObject << /Im1 " + str(img_oid).encode()
                           + b" 0 R >> >> /Contents " + str(4 + 2 * i).encode() + b" 0 R >>")
        objs[4 + 2 * i] = (b"<< /Length " + str(len(content)).encode()
                           + b" >>\nstream\n" + content + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref_pos = len(out)
    max_oid = max(objs)
    out += f"xref\n0 {max_oid + 1}\n".encode() + b"0000000000 65535 f \n"
    for oid in range(1, max_oid + 1):
        out += ("%010d 00000 n \n" % offsets[oid]).encode()
    out += (b"trailer\n<< /Size " + str(max_oid + 1).encode()
            + b" /Root 1 0 R >>\nstartxref\n" + str(xref_pos).encode() + b"\n%%EOF")
    return bytes(out)


_P1_TWO = ("q 100 0 0 100 450 600 cm /Im1 Do Q\n"
           "q 100 0 0 100 450 50 cm /Im1 Do Q").encode()
_P2_ONE = b"q 100 0 0 100 450 600 cm /Im1 Do Q"


def test_pdf_image_filename_sequential_within_page(tmp_path):
    """页内基线：同页两图 → _p1_00 / _p1_01，均落盘。"""
    pdf_path = tmp_path / "twoimg.pdf"
    pdf_path.write_bytes(_pdf([_P1_TWO]))
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    doc = FallbackParser(image_output_dir=str(img_dir)).parse(
        pdf_path, compute_file_hash(pdf_path))
    images = [e for e in doc.elements if e.type == "image"]
    names = [Path(e.resource_path).name for e in images]
    assert names[0].endswith("_p1_00.png")
    assert names[1].endswith("_p1_01.png")
    assert all(e.metadata["extracted_to_disk"] for e in images)
    assert sorted(p.name for p in img_dir.glob("*.png")) == sorted(names)


def test_pdf_image_counter_is_global_across_pages(tmp_path):
    """判别式：第二页唯一图片文件名是 _p2_02——全局 counter 延续第
    一页的两图（每页归零假设下应为 p2_00）。"""
    pdf_path = tmp_path / "multipage.pdf"
    pdf_path.write_bytes(_pdf([_P1_TWO, _P2_ONE]))
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    doc = FallbackParser(image_output_dir=str(img_dir)).parse(
        pdf_path, compute_file_hash(pdf_path))
    images = [e for e in doc.elements if e.type == "image"]
    assert [e.source_locator["page"] for e in images] == [1, 1, 2]
    assert Path(images[2].resource_path).name.endswith("_p2_02.png")
    assert sorted(p.name for p in img_dir.glob("*.png"))[2].endswith("_p2_02.png")


def test_pdf_zero_width_image_silently_skipped(tmp_path):
    """零宽图（cm 矩阵宽 0 → x1 == x0）不产生元素也不产生告警；
    同页正常图保留（bbox 完好）。"""
    content = ("q 0 0 0 100 450 600 cm /Im1 Do Q\n"
               "q 100 0 0 100 450 50 cm /Im1 Do Q").encode()
    pdf_path = tmp_path / "degen.pdf"
    pdf_path.write_bytes(_pdf([content]))
    doc = FallbackParser().parse(pdf_path, compute_file_hash(pdf_path))
    images = [e for e in doc.elements if e.type == "image"]
    assert len(images) == 1
    assert images[0].source_locator["bbox"] == [450.0, 642.0, 550.0, 742.0]
    assert [w.code for w in doc.warnings] == []
