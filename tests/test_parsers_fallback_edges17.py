r"""app/parsers/fallback_parser.py 边角测试 - 第十七轮（Round 1394）。

新角度（probe 实证）：真 PDF 画线表格 + 内嵌 Image XObject
（历史 PDF 表格/图片测试全 monkeypatch，从未有真实线条与
XObject 字节）：
- find_tables 认出 2x2 规则表 → table 元素 markdown 渲染
  + metadata {row_count, col_count, source: pdfplumber}
- 表内文字同时以普通 word 分组元素出现（'cell A1 cell B1'
  heading）——表格文本双份不丢
- Image XObject → image 元素；无 dir 时 resource_path
  '(unrendered)'；有 dir 时 pypdfium2 渲染落盘
  image_<hash16>_p1_00.png（页基命名，非 docx 的 _paraN）
- schema / 管线（表格 isolated、图片不进 chunk）
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _build_pdf():
    table_lines = [
        "1 w 0 0 0 RG",
        "100 500 m 400 500 l S",
        "100 450 m 400 450 l S",
        "100 400 m 400 400 l S",
        "100 500 m 100 400 l S",
        "250 500 m 250 400 l S",
        "400 500 m 400 400 l S",
    ]
    img_data = b"\xff\x00\x00"
    parts = list(table_lines)
    for (x, y, t) in [(110, 475, "cell A1"),
                      (260, 475, "cell B1"),
                      (110, 425, "cell A2"),
                      (260, 425, "cell B2")]:
        parts.append(
            f"BT /F1 12 Tf {x} {y} Td "
            f"({t}) Tj ET")
    parts.append(
        "q 100 0 0 100 450 600 cm "
        "/Im1 Do Q")
    content = "\n".join(parts).encode()
    objs = {
        1: (b"<< /Type /Catalog "
            b"/Pages 2 0 R >>"),
        2: (b"<< /Type /Pages "
            b"/Kids [3 0 R] /Count 1 >>"),
        3: (b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 "
            b"6 0 R >> /XObject << /Im1 "
            b"5 0 R >> >> /Contents "
            b"4 0 R >>"),
        5: (b"<< /Type /XObject /Subtype "
            b"/Image /Width 1 /Height 1 "
            b"/ColorSpace /DeviceRGB "
            b"/BitsPerComponent 8 "
            b"/Length 3 >>\nstream\n"
            + img_data + b"\nendstream"),
        6: (b"<< /Type /Font /Subtype "
            b"/Type1 /BaseFont "
            b"/Helvetica >>"),
        4: (b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n" + content
            + b"\nendstream"),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += (f"{oid} 0 obj\n".encode()
                + objs[oid] + b"\nendobj\n")
    xref_pos = len(out)
    out += (b"xref\n0 7\n"
            b"0000000000 65535 f \n")
    for oid in range(1, 7):
        out += ("%010d 00000 n \n"
                % offsets[oid]).encode()
    out += (b"trailer\n<< /Size 7 "
            b"/Root 1 0 R >>\nstartxref\n"
            + str(xref_pos).encode()
            + b"\n%%EOF")
    return bytes(out)


def _parse(tmp_path, image_dir=None):
    p = tmp_path / "t.pdf"
    p.write_bytes(_build_pdf())
    parser = (FallbackParser(
        image_output_dir=str(image_dir))
        if image_dir else
        FallbackParser())
    return parser.parse(
        p, compute_file_hash(p))


# ---------- 表格 ----------

def test_table_element_present(tmp_path):
    doc = _parse(tmp_path)
    tables = [e for e in doc.elements
              if e.type == "table"]
    assert len(tables) == 1


def test_table_markdown(tmp_path):
    doc = _parse(tmp_path)
    table = [e for e in doc.elements
             if e.type == "table"][0]
    assert table.content == (
        "| cell A1 | cell B1 |\n"
        "| --- | --- |\n"
        "| cell A2 | cell B2 |")


def test_table_metadata(tmp_path):
    doc = _parse(tmp_path)
    table = [e for e in doc.elements
             if e.type == "table"][0]
    assert table.metadata == {
        "row_count": 2, "col_count": 2,
        "source": "pdfplumber"}


def test_table_locator(tmp_path):
    doc = _parse(tmp_path)
    table = [e for e in doc.elements
             if e.type == "table"][0]
    assert table.source_locator == {
        "page": 1,
        "bbox": [100.0, 292.0,
                 400.0, 392.0]}


# ---------- 表内文字双份 ----------

def test_cell_text_also_word_elements(
        tmp_path):
    doc = _parse(tmp_path)
    words = [e for e in doc.elements
             if e.type == "heading"]
    assert [w.content
            for w in words] == [
        "cell A1 cell B1",
        "cell A2 cell B2"]


def test_word_heading_heuristic(tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[0].metadata == {
        "level": 0,
        "heuristic": "short_line"}


def test_elements_order(tmp_path):
    doc = _parse(tmp_path)
    assert [e.type for e in doc.elements
            ] == ["heading", "heading",
                  "table", "image"]


# ---------- 图片：无 dir ----------

def test_image_unrendered_placeholder(
        tmp_path):
    doc = _parse(tmp_path)
    img = doc.elements[3]
    assert img.type == "image"
    assert img.resource_path == \
        "(unrendered)"


def test_image_metadata_unrendered(
        tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[3].metadata == {
        "tag": None, "srcsize": [1, 1],
        "extracted_to_disk": False}


def test_image_bbox(tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[
        3].source_locator["bbox"] == [
        450.0, 92.0, 550.0, 192.0]


def test_no_warnings(tmp_path):
    doc = _parse(tmp_path)
    assert doc.warnings == []


# ---------- 图片：有 dir（pypdfium2 渲染） ----------

def test_image_rendered_to_disk(tmp_path):
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    doc = _parse(tmp_path,
                 image_dir=img_dir)
    img = doc.elements[3]
    assert img.metadata[
        "extracted_to_disk"] is True
    assert Path(
        img.resource_path).is_file()


def test_image_filename_page_based(
        tmp_path):
    import re
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    doc = _parse(tmp_path,
                 image_dir=img_dir)
    name = Path(
        doc.elements[3].resource_path
    ).name
    assert re.fullmatch(
        r"image_[0-9a-f]{16}"
        r"_p1_00\.png", name)


# ---------- schema + 管线 ----------

def test_passes_schema(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path)
    assert is_valid(doc.to_dict())


def test_pipeline_table_isolated(tmp_path):
    from app.pipeline import \
        process_single
    p = tmp_path / "t.pdf"
    p.write_bytes(_build_pdf())
    doc, errors = process_single(
        p, None, parser_name="fallback",
        max_chars=800)
    assert errors == []
    table_chunks = [c for c in doc.chunks
                    if c.text.startswith(
                        "| cell A1")]
    assert len(table_chunks) == 1
    assert len(
        table_chunks[0]
        .source_element_ids) == 1


def test_pipeline_image_not_in_chunks(
        tmp_path):
    from app.pipeline import \
        process_single
    p = tmp_path / "t.pdf"
    p.write_bytes(_build_pdf())
    doc, _ = process_single(
        p, None, parser_name="fallback",
        max_chars=800)
    img_id = [e.element_id
              for e in doc.elements
              if e.type == "image"][0]
    assert all(
        img_id not in c.source_element_ids
        for c in doc.chunks)
