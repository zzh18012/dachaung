r"""app/parsers/fallback_parser.py 边角测试 - 第二十五轮（Round 1412）。

新角度（probe 实证）多页画线表（R1394 只锁单页）：两页各
一条 2x1 规则表——每页各产出 word-group heading + table
元素、page 1/2 各自 locator、各自独立 chunk；表格 bbox 按
页坐标换算（grid y 350-400 → top 392 / bottom 442）。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _grid(y0, y1, xs):
    g = ["1 w 0 0 0 RG"]
    g += [f"100 {y0} m 340 {y0} l S",
          f"100 {y1} m 340 {y1} l S"]
    g += [f"{x} {y0} m {x} {y1} l S"
          for x in xs]
    return g


def _t(x, y, s):
    return (f"BT /F1 12 Tf {x} {y} "
            f"Td ({s}) Tj ET")


def _build():
    pages = [
        _grid(400, 350,
              [100, 220, 340])
        + [_t(110, 365, "p1c1"),
           _t(230, 365, "p1c2")],
        _grid(500, 450,
              [100, 220, 340])
        + [_t(110, 465, "p2c1"),
           _t(230, 465, "p2c2")],
    ]
    n = len(pages)
    page_ids = [3 + i * 2
                for i in range(n)]
    content_ids = [4 + i * 2
                   for i in range(n)]
    font_id = 3 + n * 2
    objs = {
        font_id: (b"<< /Type /Font "
                  b"/Subtype /Type1 "
                  b"/BaseFont "
                  b"/Helvetica >>"),
        1: (b"<< /Type /Catalog "
            b"/Pages 2 0 R >>")}
    kids = " ".join(
        f"{pid} 0 R"
        for pid in page_ids)
    objs[2] = (f"<< /Type /Pages /Kids "
               f"[{kids}] /Count {n} >>"
               ).encode()
    for i, lines in enumerate(pages):
        pid = page_ids[i]
        cid = content_ids[i]
        objs[pid] = (
            f"<< /Type /Page /Parent "
            f"2 0 R /MediaBox "
            f"[0 0 612 792] "
            f"/Resources << /Font << "
            f"/F1 {font_id} 0 R >> >> "
            f"/Contents {cid} 0 R >>"
        ).encode()
        stream = "\n".join(
            lines).encode()
        objs[cid] = (
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n"
            + stream
            + b"\nendstream")
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
    p = tmp_path / "mt.pdf"
    p.write_bytes(_build())
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- 元素 ----------

def test_four_elements(tmp_path):
    doc = _parse(tmp_path)
    assert [e.type
            for e in doc.elements] == [
        "heading", "table",
        "heading", "table"]


def test_word_groups_per_page(
        tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[
        0].content == "p1c1 p1c2"
    assert doc.elements[
        2].content == "p2c1 p2c2"


def test_tables_per_page(tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[
        1].content == (
        "| p1c1 | p1c2 |\n"
        "| --- | --- |")
    assert doc.elements[
        3].content == (
        "| p2c1 | p2c2 |\n"
        "| --- | --- |")


def test_page_locators(tmp_path):
    doc = _parse(tmp_path)
    assert [e.source_locator["page"]
            for e in doc.elements
            ] == [1, 1, 2, 2]


def test_table_bboxes(tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[
        1].source_locator["bbox"] == [
        100.0, 392.0, 340.0, 442.0]
    assert doc.elements[
        3].source_locator["bbox"] == [
        100.0, 292.0, 340.0, 342.0]


def test_word_group_bboxes(tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[
        0].source_locator["bbox"] == [
        110.0, 417.484, 256.016,
        429.484]


# ---------- 管线 ----------

def test_schema_valid(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path)
    assert is_valid(doc.to_dict())


def test_four_isolated_chunks(tmp_path):
    p = tmp_path / "mt.pdf"
    p.write_bytes(_build())
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text for c in doc.chunks
            ] == [
        "p1c1 p1c2",
        "| p1c1 | p1c2 |\n"
        "| --- | --- |",
        "p2c1 p2c2",
        "| p2c1 | p2c2 |\n"
        "| --- | --- |"]
    assert all(len(c.source_element_ids)
               == 1
               for c in doc.chunks)


def test_no_warnings(tmp_path):
    doc = _parse(tmp_path)
    assert doc.warnings == []


def test_pdfloc_green(tmp_path):
    from evaluation.metrics import \
        compute_automatic_metrics
    p = tmp_path / "mt.pdf"
    p.write_bytes(_build())
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    m = compute_automatic_metrics(
        doc.to_dict(), None, "pdf",
        None)
    assert m[
        "pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}
