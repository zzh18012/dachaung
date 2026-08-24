r"""app/parsers/fallback_parser.py 边角测试 - 第二十六轮（Round 1413）。

新角度（probe 实证）q/cm 图形变换下的文本几何（历史 cm
只用于图片放置，从未用于文本）：
- 'q 2 0 0 2 0 0 cm' 内 Td(72,350) 12pt → 有效位置
  (144,700)、有效字号 24：bbox [144.0, 72.968, 370.752,
  96.968]（与 R1406 的 24pt 直排文本 top 完全一致）
- 同文本无变换 Td(72,350) → [72.0, 432.484, ...]；
  两份同文本不同缩放 → 两个独立 heading 元素
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _cm_pdf():
    content = (
        b"BT /F1 12 Tf 72 350 Td "
        b"(Scaled transform text) "
        b"Tj ET "
        b"q 2 0 0 2 0 0 cm "
        b"BT /F1 12 Tf 72 350 Td "
        b"(Scaled transform text) "
        b"Tj ET Q "
        b"BT /F1 12 Tf 72 200 Td "
        b"(Plain reference text "
        b"body.) Tj ET")
    objs = {
        6: (b"<< /Type /Font /Subtype "
            b"/Type1 /BaseFont "
            b"/Helvetica >>"),
        1: (b"<< /Type /Catalog "
            b"/Pages 2 0 R >>"),
        2: (b"<< /Type /Pages "
            b"/Kids [3 0 R] "
            b"/Count 1 >>"),
        3: (b"<< /Type /Page /Parent "
            b"2 0 R /MediaBox "
            b"[0 0 612 792] "
            b"/Resources << /Font "
            b"<< /F1 6 0 R >> >> "
            b"/Contents 4 0 R >>"),
        4: (b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n"
            + content
            + b"\nendstream"),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += (f"{oid} 0 obj\n"
                .encode()
                + objs[oid]
                + b"\nendobj\n")
    xref_pos = len(out)
    maxid = max(objs)
    out += (f"xref\n0 {maxid + 1}\n"
            ).encode() \
        + b"0000000000 65535 f \n"
    for oid in range(1, maxid + 1):
        out += (
            f"{offsets[oid]:010d} "
            f"00000 n \n".encode()
            if oid in offsets
            else b"0000000000 65535 f \n")
    out += (f"trailer\n<< /Size "
            f"{maxid + 1} /Root 1 0 R "
            f">>\nstartxref\n{xref_pos}"
            f"\n%%EOF").encode()
    return bytes(out)


def _parse(tmp_path):
    p = tmp_path / "cm.pdf"
    p.write_bytes(_cm_pdf())
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- 元素与几何 ----------

def test_three_elements(tmp_path):
    doc = _parse(tmp_path)
    assert [e.type
            for e in doc.elements] == [
        "heading", "heading",
        "paragraph"]


def test_scaled_bbox(tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[
        0].source_locator == {
        "page": 1,
        "bbox": [144.0,
                 72.96799999999996,
                 370.75199999999995,
                 96.96799999999996]}


def test_plain_bbox(tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[
        1].source_locator == {
        "page": 1,
        "bbox": [72.0, 432.484,
                 185.37599999999998,
                 444.484]}


def test_reference_bbox(tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[
        2].source_locator == {
        "page": 1,
        "bbox": [72.0, 582.484,
                 208.06799999999998,
                 594.484]}


def test_scale_doubles_fontsize(
        tmp_path):
    """12pt × cm 2 → 高 24.0
    （与 R1406 24pt 直排同 top）。"""
    doc = _parse(tmp_path)
    b = doc.elements[
        0].source_locator["bbox"]
    assert (b[3] - b[1]) == 24.0


def test_scaled_x_doubled(tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[
        0].source_locator["bbox"][0] \
        == 144.0


def test_identical_text_two_elements(
        tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[
        0].content == doc.elements[
        1].content == (
        "Scaled transform text")


# ---------- 管线 ----------

def test_schema_valid(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path)
    assert is_valid(doc.to_dict())


def test_no_warnings(tmp_path):
    doc = _parse(tmp_path)
    assert doc.warnings == []


def test_pipeline_chunks(tmp_path):
    p = tmp_path / "cm.pdf"
    p.write_bytes(_cm_pdf())
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text for c in doc.chunks
            ] == [
        "Scaled transform text",
        "Scaled transform text "
        "Plain reference text body."]
