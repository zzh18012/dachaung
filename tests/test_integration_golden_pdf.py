r"""集成金样板测试 - PDF 孪生（Round 1401）。

R1400 金样 docx 的 PDF 孪生：富手工 PDF（heading + 长段 +
题注 + 画线表 + Image XObject + 尾行）穿全栈 parse →
chunk(mc=120) → 落盘 JSON → schema → metrics → 图片渲染
落盘：
- 9 元素（表内文字先于表格元素——word 分组在前、表格在后、
  图片最后）
- 6 chunk 精确文本
- output 推导 images-<sha16>/ → image_<sha16>_p1_00.png
  （pypdfium2 渲染 447 字节）
- irer/pdfloc/hbc/tpe 全绿
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.hash import compute_file_hash
from app.pipeline import process_single


P1 = ("Golden pdf body paragraph "
      "one with more than enough "
      "characters to overflow a "
      "small chunk budget.")
P2 = ("Golden pdf body paragraph "
      "two sits under the second "
      "heading and is long enough "
      "to split as well.")


def _build_golden_pdf():
    def text(x, y, t):
        return (f"BT /F1 12 Tf {x} {y} "
                f"Td ({t}) Tj ET")

    grid = [
        "1 w 0 0 0 RG",
        "100 400 m 340 400 l S",
        "100 350 m 340 350 l S",
        "100 400 m 100 350 l S",
        "220 400 m 220 350 l S",
        "340 400 m 340 350 l S",
    ]
    c1 = "\n".join(grid + [
        text(72, 700, "Golden Root"),
        text(72, 640, P1),
        text(72, 580,
             "Figure 1: golden pdf "
             "caption"),
        text(110, 365, "ph1"),
        text(230, 365, "ph2"),
        "q 80 0 0 80 450 600 cm "
        "/Im1 Do Q",
        text(72, 300, "Nested"),
        text(72, 240, P2),
        text(72, 180,
             "tail short")]).encode()
    img = b"\x00\xff\x00"
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
            + img + b"\nendstream"),
        6: (b"<< /Type /Font /Subtype "
            b"/Type1 /BaseFont "
            b"/Helvetica >>"),
        4: (b"<< /Length "
            + str(len(c1)).encode()
            + b" >>\nstream\n" + c1
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


def _run(tmp_path):
    p = tmp_path / "gold.pdf"
    p.write_bytes(_build_golden_pdf())
    out = tmp_path / "gold.json"
    doc, errors = process_single(
        p, out, parser_name="fallback",
        max_chars=120)
    return p, out, doc, errors


# ---------- 元素 ----------

def test_element_types(tmp_path):
    _, _, doc, errors = _run(tmp_path)
    assert errors == []
    assert [e.type for e in doc.elements
            ] == [
        "heading", "paragraph",
        "caption", "heading",
        "heading", "paragraph",
        "heading", "table",
        "image"]


def test_table_words_before_table(
        tmp_path):
    """word 分组元素（'ph1 ph2'）在表格
    元素之前。"""
    _, _, doc, _ = _run(tmp_path)
    types = [e.type
             for e in doc.elements]
    word_h = doc.elements[3]
    assert word_h.content == "ph1 ph2"
    assert types.index("table") > 3


def test_image_last(tmp_path):
    _, _, doc, _ = _run(tmp_path)
    assert doc.elements[-1].type == \
        "image"


def test_element_ids_sequential(
        tmp_path):
    _, _, doc, _ = _run(tmp_path)
    assert [e.element_id[-4:]
            for e in doc.elements] == [
        f"{i:04d}"
        for i in range(9)]


# ---------- 分块 ----------

def test_six_chunks(tmp_path):
    _, _, doc, _ = _run(tmp_path)
    assert len(doc.chunks) == 6


def test_chunk_texts(tmp_path):
    _, _, doc, _ = _run(tmp_path)
    assert [c.text for c in doc.chunks
            ] == [
        "Golden Root " + P1,
        "Figure 1: golden pdf caption",
        "ph1 ph2",
        "Nested " + P2,
        "tail short",
        "| ph1 | ph2 |\n"
        "| --- | --- |"]


def test_chunks_within_max(tmp_path):
    _, _, doc, _ = _run(tmp_path)
    assert all(len(c.text) <= 120
               for c in doc.chunks)


# ---------- 落盘 JSON ----------

def test_json_written(tmp_path):
    _, out, _, _ = _run(tmp_path)
    assert out.is_file()


def test_json_shape(tmp_path):
    _, out, _, _ = _run(tmp_path)
    data = json.loads(
        out.read_text(encoding="utf-8"))
    assert data["schema_version"] == \
        "0.1.0"
    assert len(data["elements"]) == 9
    assert len(data["chunks"]) == 6
    assert data["errors"] == []
    assert data["source_type"] == "pdf"


def test_json_schema_valid(tmp_path):
    from app.schema import is_valid
    _, out, _, _ = _run(tmp_path)
    assert is_valid(
        json.loads(
            out.read_text(
                encoding="utf-8")))


def test_source_hash_matches(tmp_path):
    p, _, doc, _ = _run(tmp_path)
    assert doc.source_hash == \
        compute_file_hash(p)


# ---------- 图片渲染落盘 ----------

def test_images_dir(tmp_path):
    _, out, doc, _ = _run(tmp_path)
    sha = doc.source_hash[:16]
    img_dir = out.parent / (
        f"images-{sha}")
    assert img_dir.is_dir()
    pngs = list(img_dir.glob("*.png"))
    assert len(pngs) == 1
    assert pngs[0].name == (
        f"image_{sha}_p1_00.png")


def test_png_rendered_bytes(tmp_path):
    _, out, _, _ = _run(tmp_path)
    png = list(
        out.parent.rglob("*.png"))[0]
    assert png.read_bytes()[:8] == \
        b"\x89PNG\r\n\x1a\n"
    assert png.stat().st_size == 447


# ---------- 指标 ----------

def test_metrics_all_green(tmp_path):
    from evaluation.metrics import \
        compute_automatic_metrics
    _, _, doc, _ = _run(tmp_path)
    m = compute_automatic_metrics(
        doc.to_dict(), None, "pdf",
        None)
    assert m[
        "image_resource_exists_ratio"] \
        == {"value": 1.0,
            "reason": None}
    assert m[
        "pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}
    assert m[
        "heading_boundary_compliance"] \
        == {"value": 1.0,
            "reason": None}
    assert m["text_preservation_equal"] \
        == {"value": True,
            "reason": None}


def test_metrics_ect(tmp_path):
    from evaluation.metrics import \
        compute_automatic_metrics
    _, _, doc, _ = _run(tmp_path)
    m = compute_automatic_metrics(
        doc.to_dict(), None, "pdf",
        None)
    assert m[
        "element_count_by_type"][
        "value"] == {
        "heading": 4, "paragraph": 2,
        "caption": 1, "table": 1,
        "image": 1}


def test_document_id_pattern(tmp_path):
    _, _, doc, _ = _run(tmp_path)
    assert re.fullmatch(
        r"doc-[0-9a-f]{16}",
        doc.document_id)
