r"""app/parsers/fallback_parser.py 边角测试 - 第四十六轮（Round 1438）。

新角度（probe 实证）PDF 表格检测 + 多页（历史 PDF 全是纯文本
流，从未画过 re 矩形、从未超过 1 页）：
- re S 矩形触发 pdfplumber lines 策略 → **table 元素诞生**：
  两格并排（格内两行字）→ 单行表 '| Name\nAge | Alice\n30
  |\n| --- | --- |'（格内 \n 连接）；PDF 表 locator 只有
  page+bbox **无 table_index**（对照 docx）
- 文本**双份**：同一批字既进 heading 元素（'Name Alice Age
  30'）又进 table——解析器不减除表格文字
- 3×3 全框格：每行一个 heading（行距 40 > 31 阈值分行），
  'r1c1 r1c2 r1c3' ×3 + 完整 markdown 表；bbox [72.0, 32.0,
  672.0, 152.0]（格网整体）
- 无矩形对照组：纯文本格阵**不产表**，只有 3 个 heading
- 空矩形（无任何文字）→ **幽灵空表** '|  |  |\n| --- | --- |'
- 多页：/Pages /Kids 三页 → page 1/2/3 locator、三 chunk
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _build(content):
    objs = {
        5: (b"<< /Type /Font /Subtype "
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
            b"<< /F1 5 0 R >> >> "
            b"/Contents 4 0 R >>"),
        4: (b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n" + content
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
    out += b"xref\n0 6\n" \
        b"0000000000 65535 f \n"
    for oid in range(1, 6):
        out += ("%010d 00000 n \n"
                % offsets[oid]).encode()
    out += (b"trailer\n<< /Size 6 "
            b"/Root 1 0 R >>\n"
            b"startxref\n"
            + str(xref_pos).encode()
            + b"\n%%EOF")
    return bytes(out)


def _build_multi(pages):
    n = len(pages)
    kids = b" ".join(b"%d 0 R" % (10 + i)
                     for i in range(n))
    objs = {
        5: (b"<< /Type /Font /Subtype "
            b"/Type1 /BaseFont "
            b"/Helvetica >>"),
        1: (b"<< /Type /Catalog "
            b"/Pages 2 0 R >>"),
        2: (b"<< /Type /Pages /Kids ["
            + kids + b"] /Count "
            + str(n).encode() + b" >>"),
    }
    for i, content in enumerate(pages):
        objs[10 + i] = (
            b"<< /Type /Page /Parent 2 0 R"
            b" /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1"
            b" 5 0 R >> >> /Contents "
            + str(20 + i).encode()
            + b" 0 R >>")
        objs[20 + i] = (
            b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n" + content
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
    mx = max(objs)
    out += (b"xref\n0 "
            + str(mx + 1).encode()
            + b"\n0000000000 65535 f \n")
    for oid in range(1, mx + 1):
        if oid in offsets:
            out += ("%010d 00000 n \n"
                    % offsets[oid]).encode()
        else:
            out += b"0000000000 65535 f \n"
    out += (b"trailer\n<< /Size "
            + str(mx + 1).encode()
            + b" /Root 1 0 R >>\n"
            b"startxref\n"
            + str(xref_pos).encode()
            + b"\n%%EOF")
    return bytes(out)


def _pdf(tmp_path, name, content):
    p = tmp_path / name
    p.write_bytes(_build(content))
    return p


def _two_cell_grid():
    return (b"72 660 200 60 re S "
            b"272 660 200 60 re S "
            + b"BT /F1 12 Tf 80 700 Td"
            b" (Name) Tj ET "
            b"BT /F1 12 Tf 80 680 Td"
            b" (Age) Tj ET "
            + b"BT /F1 12 Tf 280 700 Td"
            b" (Alice) Tj ET "
            b"BT /F1 12 Tf 280 680 Td"
            b" (30) Tj ET")


def _g33():
    rects = b"".join(
        b"%d %d 200 40 re S "
        % (x, y)
        for x in (72, 272, 472)
        for y in (640, 680, 720))
    cells = [
        (80, 730, b"r1c1"), (280, 730, b"r1c2"),
        (480, 730, b"r1c3"),
        (80, 690, b"r2c1"), (280, 690, b"r2c2"),
        (480, 690, b"r2c3"),
        (80, 650, b"r3c1"), (280, 650, b"r3c2"),
        (480, 650, b"r3c3")]
    text = b"".join(
        b"BT /F1 10 Tf %d %d Td (%s)"
        b" Tj ET " % c for c in cells)
    return rects + text


def _g33_text_only():
    cells = [
        (80, 730, b"r1c1"), (280, 730, b"r1c2"),
        (480, 730, b"r1c3"),
        (80, 690, b"r2c1"), (280, 690, b"r2c2"),
        (480, 690, b"r2c3"),
        (80, 650, b"r3c1"), (280, 650, b"r3c2"),
        (480, 650, b"r3c3")]
    return b"".join(
        b"BT /F1 10 Tf %d %d Td (%s)"
        b" Tj ET " % c for c in cells)


# ---------- 两格表 ----------

def test_rect_table_element(
        tmp_path):
    p = _pdf(tmp_path, "t2.pdf",
             _two_cell_grid())
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.type
            for e in doc.elements] == [
        "heading", "table"]
    assert doc.elements[
        1].content == \
        "| Name\nAge | Alice\n30 |" \
        "\n| --- | --- |"


def test_rect_table_text_dup(
        tmp_path):
    p = _pdf(tmp_path, "t2d.pdf",
             _two_cell_grid())
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "Name Alice Age 30"


def test_rect_table_locator(
        tmp_path):
    p = _pdf(tmp_path, "t2l.pdf",
             _two_cell_grid())
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        1].source_locator == {
        "page": 1,
        "bbox": [72.0, 72.0,
                 472.0, 132.0]}


# ---------- 3×3 全框格 ----------

def test_grid33_types(tmp_path):
    p = _pdf(tmp_path, "g33.pdf",
             _g33())
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.type
            for e in doc.elements] == [
        "heading", "heading",
        "heading", "table"]


def test_grid33_headings(
        tmp_path):
    p = _pdf(tmp_path, "g33h.pdf",
             _g33())
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements
            if e.type == "heading"] == [
        "r1c1 r1c2 r1c3",
        "r2c1 r2c2 r2c3",
        "r3c1 r3c2 r3c3"]


def test_grid33_table(tmp_path):
    p = _pdf(tmp_path, "g33t.pdf",
             _g33())
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        3].content == (
        "| r1c1 | r1c2 | r1c3 |"
        "\n| --- | --- | --- |"
        "\n| r2c1 | r2c2 | r2c3 |"
        "\n| r3c1 | r3c2 | r3c3 |")
    assert doc.elements[
        3].source_locator["bbox"] == [
        72.0, 32.0, 672.0, 152.0]


# ---------- 无矩形对照 ----------

def test_norect_no_table(
        tmp_path):
    p = _pdf(tmp_path, "nr.pdf",
             _g33_text_only())
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.type
            for e in doc.elements] == [
        "heading", "heading",
        "heading"]


# ---------- 空矩形幽灵表 ----------

def test_emptyrect_ghost_table(
        tmp_path):
    p = _pdf(
        tmp_path, "er.pdf",
        b"72 660 200 60 re S "
        b"272 660 200 60 re S")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.type
            for e in doc.elements] == [
        "table"]
    assert doc.elements[
        0].content == \
        "|  |  |\n| --- | --- |"
    assert doc.warnings == []


# ---------- 多页 ----------

def _mp(tmp_path, name):
    p = tmp_path / name
    p.write_bytes(_build_multi([
        b"BT /F1 12 Tf 72 700 Td "
        b"(Page one text) Tj ET",
        b"BT /F1 12 Tf 72 700 Td "
        b"(Page two text) Tj ET",
        b"BT /F1 12 Tf 72 700 Td "
        b"(Page three text) Tj ET"]))
    return p


def test_multipage_pages(
        tmp_path):
    p = _mp(tmp_path, "mp.pdf")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.source_locator["page"]
            for e in doc.elements] == [
        1, 2, 3]


def test_multipage_contents(
        tmp_path):
    p = _mp(tmp_path, "mp2.pdf")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Page one text",
        "Page two text",
        "Page three text"]


def test_multipage_chunks(
        tmp_path):
    doc, errors = process_single(
        _mp(tmp_path, "mp3.pdf"),
        None, parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "Page one text",
        "Page two text",
        "Page three text"]


# ---------- 通用 ----------

def test_grid33_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _pdf(tmp_path, "g33s.pdf",
             _g33())
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_grid33_chunks_dup(
        tmp_path):
    p = _pdf(tmp_path, "g33c.pdf",
             _g33())
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    texts = [c.text
             for c in doc.chunks]
    assert "r1c1 r1c2 r1c3" in texts
    assert any("r3c2" in t
               and "|" in t
               for t in texts)


def test_no_warnings(tmp_path):
    for name, content in (
            ("w1.pdf", _two_cell_grid()),
            ("w2.pdf", _g33()),
            ("w3.pdf",
             b"BT /F1 12 Tf 72 700 Td "
             b"(x) Tj ET")):
        p = _pdf(tmp_path, name,
                 content)
        doc = FallbackParser().parse(
            p, compute_file_hash(p))
        assert doc.warnings == []
