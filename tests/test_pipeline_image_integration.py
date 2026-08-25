r"""pipeline 图片元素落盘端到端集成（Round 1551）。

新角度：`images-<sha16>/` 命名约定与 `extracted_to_disk`
此前各有单测（image_output_dir_for、parser 层），但**真实
PDF 图片 → process_single → 目录/文件真正出现在输出
JSON 旁 → JSON 中 content null / resource_path 非空 →
图片不进入 chunks** 的完整链路零覆盖：

- **图片元素 + 落盘**：element.content 为 None、
  resource_path 为**绝对路径**（以 `images-<sha16>\image_<sha16>_p1_00.png`
  结尾，平台分隔符）、该文件真实存在、
  metadata srcsize=[1,1] extracted_to_disk=True
- **chunks 排除图片**：仅 ['BODY']，图片不产生文本块
- **写盘 JSON 不变量**：schema 的 anyOf（content 与
  resource_path 至少一个非 null）在磁盘产物上成立
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.hash import compute_file_hash
from app.pipeline import process_single

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")
_IMG = bytes([255, 0, 0])
_C = ("q 100 0 0 100 72 692 cm"
      " /Im1 Do Q"
      " BT /F1 12 Tf 72 650 Td"
      " (BODY) Tj ET")
_IM = (f"<< /Type /XObject"
       f" /Subtype /Image /Width 1"
       f" /Height 1 /ColorSpace"
       f" /DeviceRGB /BitsPerComponent 8"
       f" /Length {len(_IMG)} >>"
       f"\nstream\n"
       ).encode() + _IMG + b"\nendstream"


def _pdf(tmp_path: Path) -> Path:
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R] /Count 1 >>",
        3: "<< /Type /Page /Parent 2 0 R"
           " /MediaBox [0 0 612 792]"
           " /Resources << /Font"
           " << /F1 5 0 R >> /XObject"
           " << /Im1 7 0 R >> >>"
           " /Contents 4 0 R >>",
        4: f"<< /Length {len(_C)} >>"
           f"\nstream\n{_C}\nendstream",
        5: _FONT,
        7: _IM,
    }
    pdf = b"%PDF-1.4\n"
    for oid in sorted(objs):
        o = objs[oid]
        if isinstance(o, str):
            o = o.encode("latin-1")
        pdf += (f"{oid} 0 obj\n"
                ).encode() + o + b"\nendobj\n"
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 8 >>\n%%EOF")
    p = tmp_path / "img.pdf"
    p.write_bytes(pdf)
    return p


def test_image_extracted_to_disk(
        tmp_path):
    p = _pdf(tmp_path)
    out = tmp_path / "out.json"
    doc, errors = process_single(
        p, out, write_json=True)
    assert errors == []
    sha = compute_file_hash(p)[:16]
    imgs = [e for e in doc.elements
            if e.type == "image"]
    assert len(imgs) == 1
    e = imgs[0]
    assert e.content is None
    assert e.resource_path.endswith(
        f"images-{sha}"
        f"\\image_{sha}_p1_00.png")
    assert e.metadata[
        "srcsize"] == [1, 1]
    assert e.metadata[
        "extracted_to_disk"] is True
    png = (tmp_path
           / f"images-{sha}"
           / f"image_{sha}_p1_00.png")
    assert png.is_file()


def test_chunks_exclude_image(
        tmp_path):
    p = _pdf(tmp_path)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "BODY"]
    assert all(
        c.source_element_ids
        for c in doc.chunks)


def test_json_keeps_resource_path(
        tmp_path):
    p = _pdf(tmp_path)
    out = tmp_path / "out.json"
    process_single(p, out,
                   write_json=True)
    data = json.loads(
        out.read_text(encoding="utf-8"))
    imgs = [el for el
            in data["elements"]
            if el["type"] == "image"]
    assert len(imgs) == 1
    el = imgs[0]
    assert el["content"] is None
    assert re.search(
        r"images-[0-9a-f]{16}"
        r"[\\/]"
        r"image_[0-9a-f]{16}"
        r"_p1_00\.png$",
        el["resource_path"])
