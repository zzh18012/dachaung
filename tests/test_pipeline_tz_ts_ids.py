r"""pipeline Tz/Ts 缩放与跨 max_chars 的 id 稳定性（Round 1581）。

新角度：R1579 锁字号——**Tz 水平缩放、Ts 基线抬升、
max_chars 越界与跨参数 id 不变性**零覆盖：

- **Tz 50/200** → bbox 宽度精确减半/加倍（两元素
  50pt 行距不合并）
- **Ts 30** → bbox 整体上移 30
- **max_chars=5 < 32** → chunker_failed（不静默钳制）
- **同一文件不同 max_chars** → document_id 与全部
  element_id 完全一致；chunk 数量随参数变化
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.pipeline import process_single

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")


def _pdf(tmp_path: Path, name: str,
         c: str) -> Path:
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R]"
           " /Count 1 >>",
        3: ("<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox"
            " [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 5 0 R >> >>"
            " /Contents 4 0 R >>"),
        4: f"<< /Length {len(c)} >>"
           f"\nstream\n{c}\nendstream",
        5: _FONT,
    }
    pdf = b"%PDF-1.4\n"
    for oid in sorted(objs):
        o = objs[oid]
        if isinstance(o, str):
            o = o.encode("latin-1")
        pdf += (f"{oid} 0 obj\n"
                ).encode() + o \
            + b"\nendobj\n"
    pdf += (b"trailer"
            b" << /Root 1 0 R"
            b" /Size 6 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def test_tz_scaling_bbox_width(
        tmp_path):
    c = ("BT /F1 12 Tf 50 Tz"
         " 72 700 Td"
         " (CONDENSED) Tj ET"
         " BT /F1 12 Tf 200 Tz"
         " 72 650 Td"
         " (STRETCHED) Tj ET")
    p = _pdf(tmp_path, "tz.pdf", c)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert [e.content
            for e in doc.elements] == [
        "CONDENSED", "STRETCHED"]
    b0 = doc.elements[0]\
        .source_locator["bbox"]
    b1 = doc.elements[1]\
        .source_locator["bbox"]
    assert b0 == pytest.approx(
        [72.0, 82.48, 110.33, 94.48],
        abs=0.01)
    assert b1 == pytest.approx(
        [72.0, 132.48, 218.66,
         144.48], abs=0.01)


def test_ts_rise_shifts_bbox(
        tmp_path):
    p = _pdf(
        tmp_path, "ts.pdf",
        "BT /F1 12 Tf 30 Ts"
        " 72 700 Td"
        " (RISED) Tj ET")
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (el,) = doc.elements
    assert el.content == "RISED"
    assert el.source_locator["bbox"] \
        == pytest.approx(
            [72.0, 52.48, 108.67,
             64.48], abs=0.01)


def test_max_chars_below_minimum(
        tmp_path):
    p = _pdf(
        tmp_path, "m.pdf",
        "BT /F1 12 Tf 72 700"
        " Td (X) Tj ET")
    doc, errors = process_single(
        p, write_json=False,
        max_chars=5)
    assert doc is None
    assert [e.code
            for e in errors] == [
        "chunker_failed"]


def test_ids_stable_across_max_chars(
        tmp_path):
    words = " ".join(f"w{i:03d}"
                     for i in range(20))
    p = _pdf(
        tmp_path, "id.pdf",
        f"BT /F1 12 Tf 72 700"
        f" Td ({words}) Tj ET")
    small, e1 = process_single(
        p, write_json=False,
        max_chars=40)
    big, e2 = process_single(
        p, write_json=False,
        max_chars=800)
    assert e1 == [] and e2 == []
    assert small.document_id \
        == big.document_id
    assert [e.element_id
            for e in small.elements] \
        == [e.element_id
            for e in big.elements]
    (c,) = big.chunks
    assert c.text == words
    assert len(small.chunks) > 1
    assert all(
        len(ch.text) <= 40
        for ch in small.chunks)
