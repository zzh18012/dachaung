r"""pipeline DOCX 图片元素家族（Round 1575）。

新角度：R1551–R1565 锁满 **PDF** 图片路径——
**DOCX 图片**在 pipeline 层零覆盖：

- 无 output → resource_path='(unsaved)' 哨兵（区别于
  PDF 的 '(unrendered)'）、extracted_to_disk=False
- 有 output → 落盘命名 `image_{docsha16}_para{段索引}
  _{全局序:02d}.png`（**段索引**作用域 + 全局递增序号，
  区别于 PDF 的 `p{页}_` 页作用域与图片内容哈希）
- 图片元素不参与 chunk（source_element_ids 不含它）
- 纯图片文档 → 仅 '(空段落)' 一个 chunk
"""

from __future__ import annotations

import io
import zlib
import struct

from pathlib import Path

import docx as docxlib

from app.hash import compute_file_hash
from app.pipeline import process_single


def _png() -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(t: bytes, d: bytes) -> bytes:
        return (struct.pack(">I", len(d))
                + t + d
                + struct.pack(
                    ">I",
                    zlib.crc32(t + d)
                    & 0xffffffff))

    ihdr = chunk(
        b"IHDR",
        struct.pack(">IIBBBBB",
                    1, 1, 8, 2, 0, 0, 0))
    return (sig + ihdr
            + chunk(b"IDAT",
                    zlib.compress(
                        b"\x00\xff\x00\x00"))
            + chunk(b"IEND", b""))


def _docx(path: Path, pics: int) -> Path:
    d = docxlib.Document()
    for _ in range(pics):
        d.add_picture(io.BytesIO(_png()))
    d.save(str(path))
    return path


def test_docx_image_unsaved(
        tmp_path):
    p = _docx(tmp_path / "i.docx", 1)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    imgs = [e for e in doc.elements
            if e.type == "image"]
    assert len(imgs) == 1
    (im,) = imgs
    assert im.content is None
    assert im.resource_path == "(unsaved)"
    assert im.metadata[
        "extracted_to_disk"] is False
    for c in doc.chunks:
        assert im.element_id \
            not in c.source_element_ids


def test_docx_image_extracted(
        tmp_path):
    p = _docx(tmp_path / "i.docx", 1)
    out = tmp_path / "o" / "i.json"
    doc, errors = process_single(
        p, output_path=out)
    assert errors == []
    sha = compute_file_hash(p)[:16]
    (im,) = [e for e in doc.elements
             if e.type == "image"]
    assert im.resource_path.endswith(
        f"images-{sha}"
        f"\\image_{sha}"
        f"_para0_00.png")
    assert im.metadata[
        "extracted_to_disk"] is True
    f = (tmp_path / "o"
         / f"images-{sha}"
         / f"image_{sha}"
           f"_para0_00.png")
    assert f.exists()


def test_two_docx_images_naming(
        tmp_path):
    p = _docx(tmp_path / "t.docx", 2)
    out = tmp_path / "t.json"
    doc, errors = process_single(
        p, output_path=out)
    assert errors == []
    sha = compute_file_hash(p)[:16]
    names = [e.resource_path[-12:]
             for e in doc.elements
             if e.type == "image"]
    assert names == ["para0_00.png",
                     "para1_01.png"]
    base = (tmp_path
            / f"images-{sha}")
    assert (base
            / f"image_{sha}"
              f"_para0_00.png").exists()
    assert (base
            / f"image_{sha}"
              f"_para1_01.png").exists()


def test_docx_image_only(
        tmp_path):
    p = _docx(tmp_path / "o.docx", 1)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert [e.type
            for e in doc.elements] == [
        "paragraph", "image"]
    (c,) = doc.chunks
    assert c.text == "(空段落)"
    assert c.source_element_ids == [
        doc.elements[0].element_id]
