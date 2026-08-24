r"""app/parsers/fallback_parser.py 边角测试 - 第十一轮（Round 1384）。

全新角度：真实 PDF 字节端到端（probe 实证，历史 PDF 测试全走
monkeypatch 或 dummy 字节，从未有正确 xref 的手工 PDF 穿过
pdfplumber）——每行独立 BT/ET 块绝对定位，阅读顺序保序：
- 短行无句号 → heading（heuristic=short_line, level 0）
- 长行带句号 / 短行带句号 → paragraph（metadata 空 dict）
- Figure 1: / TABLE 1: / Fig. 3: → caption（heuristic=caption_regex）
- locator page 按真实页对象编号（中间空白页不重排：1、3）
- bbox 四元组 [x0, top, x1, bottom]，x0=72.0 精确
- 圆括号 / 反斜杠转义往返无损
- 全空白 PDF → 0 元素 + pdf_no_text_extracted
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _build_pdf(pages_lines):
    """手工构造带正确 xref 的最小合法 PDF。

    pages_lines: 每页一个列表，元素是 (y, text)。
    每行独立 BT/ET 块 → 绝对定位 → 阅读顺序。
    """
    n_pages = len(pages_lines)
    page_ids = [3 + i * 2 for i in range(n_pages)]
    content_ids = [4 + i * 2 for i in range(n_pages)]
    font_id = 3 + n_pages * 2
    objs = {font_id: b"<< /Type /Font /Subtype "
                    b"/Type1 /BaseFont "
                    b"/Helvetica >>"}
    objs[1] = b"<< /Type /Catalog " \
              b"/Pages 2 0 R >>"
    kids = " ".join(
        f"{pid} 0 R" for pid in page_ids)
    objs[2] = (f"<< /Type /Pages /Kids "
               f"[{kids}] /Count "
               f"{n_pages} >>").encode()
    for i, lines in enumerate(pages_lines):
        pid, cid = page_ids[i], content_ids[i]
        objs[pid] = (
            f"<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 "
            f"{font_id} 0 R >> >> /Contents "
            f"{cid} 0 R >>").encode()
        blocks = []
        for (y, line) in lines:
            esc = line.replace(
                "\\", r"\\").replace(
                "(", r"\(").replace(
                ")", r"\)")
            blocks.append(
                f"BT /F1 12 Tf 72 {y} Td "
                f"({esc}) Tj ET")
        stream = " ".join(blocks).encode()
        objs[cid] = (
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n" + stream
            + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += (f"{oid} 0 obj\n".encode()
                + objs[oid]
                + b"\nendobj\n")
    xref_pos = len(out)
    maxid = max(objs)
    out += f"xref\n0 {maxid + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for oid in range(1, maxid + 1):
        out += (
            f"{offsets[oid]:010d} 00000 n \n"
            .encode() if oid in offsets
            else b"0000000000 65535 f \n")
    out += (f"trailer\n<< /Size "
            f"{maxid + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF"
            ).encode()
    return bytes(out)


_LONG1 = ("This is a long body paragraph "
          "that definitely exceeds any "
          "short line threshold and ends "
          "with a period.")
_LONG2 = ("Another long body paragraph "
          "on page one which also ends "
          "with a period.")


def _board():
    return [
        [(700, "Short Title"),
         (640, _LONG1),
         (580, "Figure 1: a real caption "
               "line here"),
         (520, "TABLE 1: an english table "
               "caption"),
         (460, _LONG2)],
        [(700, "Page Two Heading"),
         (640, "Body text on the second "
               "page of the document ends "
               "here."),
         (580, "TABLE 2: table caption on "
               "page two")],
    ]


def _parse(tmp_path, pages, name="d.pdf"):
    p = tmp_path / name
    p.write_bytes(_build_pdf(pages))
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- 阅读顺序与类型 ----------

def test_reading_order_types(tmp_path):
    doc = _parse(tmp_path, _board())
    assert [e.type for e in doc.elements] == [
        "heading", "paragraph", "caption",
        "caption", "paragraph",
        "heading", "paragraph", "caption"]


def test_full_board_no_warnings(tmp_path):
    doc = _parse(tmp_path, _board())
    assert doc.warnings == []


# ---------- 分类启发式 ----------

def test_short_no_period_is_heading(tmp_path):
    doc = _parse(tmp_path, _board())
    h = doc.elements[0]
    assert h.content == "Short Title"
    assert h.metadata == {
        "level": 0,
        "heuristic": "short_line"}


def test_short_with_period_is_paragraph(
        tmp_path):
    doc = _parse(tmp_path,
                 [[(700, "Ends with period.")]])
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "Ends with period.")]
    assert doc.elements[0].metadata == {}


def test_long_with_period_paragraph_meta_empty(
        tmp_path):
    doc = _parse(tmp_path, _board())
    assert doc.elements[1].content == _LONG1
    assert doc.elements[1].metadata == {}


def test_figure_caption_heuristic(tmp_path):
    doc = _parse(tmp_path, _board())
    c = doc.elements[2]
    assert c.type == "caption"
    assert c.metadata == {
        "heuristic": "caption_regex"}


def test_table_caption_heuristic(tmp_path):
    doc = _parse(tmp_path, _board())
    assert doc.elements[3].metadata == {
        "heuristic": "caption_regex"}


def test_fig_abbrev_caption(tmp_path):
    doc = _parse(tmp_path,
                 [[(700, "Fig. 3: abbreviated "
                     "caption line")]])
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("caption",
         "Fig. 3: abbreviated caption "
         "line")]


def test_caption_overrides_short_line(
        tmp_path):
    """caption 优先于 short_line（短 caption
    不会因无句号变 heading）。"""
    doc = _parse(tmp_path,
                 [[(700, "Figure 2: tiny")]])
    assert doc.elements[0].type == "caption"
    assert doc.elements[0].metadata == {
        "heuristic": "caption_regex"}


# ---------- locator ----------

def test_page_numbers_sequential(tmp_path):
    doc = _parse(tmp_path, _board())
    assert [e.source_locator["page"]
            for e in doc.elements] == [
        1, 1, 1, 1, 1, 2, 2, 2]


def test_blank_middle_page_not_renumbered(
        tmp_path):
    doc = _parse(tmp_path, [
        [(700, "First page line one.")],
        [],
        [(700, "Third page line one.")]])
    assert [e.source_locator["page"]
            for e in doc.elements] == [1, 3]


def test_bbox_four_numbers(tmp_path):
    doc = _parse(tmp_path, _board())
    bb = doc.elements[0].source_locator["bbox"]
    assert len(bb) == 4
    assert all(isinstance(v, float)
               for v in bb)


def test_bbox_x0_is_margin(tmp_path):
    doc = _parse(tmp_path, _board())
    assert doc.elements[0].source_locator[
        "bbox"][0] == 72.0


def test_bbox_top_exact(tmp_path):
    """y=700 的 12pt 行 → top = 792-700-9.516
    = 82.484。"""
    doc = _parse(tmp_path, _board())
    assert doc.elements[0].source_locator[
        "bbox"][1] == 82.48400000000004


def test_locator_keys_exactly(tmp_path):
    doc = _parse(tmp_path, _board())
    assert set(doc.elements[0]
               .source_locator.keys()) == {
        "page", "bbox"}


# ---------- element_id ----------

def test_element_id_pattern(tmp_path):
    doc = _parse(tmp_path, [
        [(700, "First page line one.")],
        [],
        [(700, "Third page line one.")]])
    ids = [e.element_id
           for e in doc.elements]
    assert ids[0].startswith(
        "doc-") and "::e0000" in ids[0]
    assert ids[1].endswith("::e0001")


# ---------- 转义往返 ----------

def test_parens_roundtrip(tmp_path):
    doc = _parse(tmp_path,
                 [[(640, "Text with "
                     "(parentheses) inside "
                     "body.")]])
    assert doc.elements[0].content == (
        "Text with (parentheses) "
        "inside body.")


def test_backslash_roundtrip(tmp_path):
    doc = _parse(tmp_path,
                 [[(580, "Escaped \\ backslash "
                     "\"quotes\" ok.")]])
    assert doc.elements[0].content == (
        'Escaped \\ backslash "quotes" '
        'ok.')


# ---------- 全空白 PDF ----------

def test_all_blank_pdf_no_elements(tmp_path):
    doc = _parse(tmp_path, [[]])
    assert doc.elements == []


def test_all_blank_pdf_warning_code(
        tmp_path):
    doc = _parse(tmp_path, [[]])
    assert [w.code for w in doc.warnings] \
        == ["pdf_no_text_extracted"]


# ---------- schema + 管线 + 指标 ----------

def test_full_board_passes_schema(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path, _board())
    assert is_valid(doc.to_dict())


def test_full_board_through_pipeline(
        tmp_path):
    from app.pipeline import process_single
    p = tmp_path / "b.pdf"
    p.write_bytes(_build_pdf(_board()))
    doc, errors = process_single(
        p, None, parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert len(doc.chunks) == 6


def test_metrics_real_pdf(tmp_path):
    from evaluation.metrics import \
        compute_automatic_metrics
    from app.pipeline import process_single
    p = tmp_path / "m.pdf"
    p.write_bytes(_build_pdf(_board()))
    doc, _ = process_single(
        p, None, parser_name="fallback",
        max_chars=800)
    m = compute_automatic_metrics(
        doc.to_dict(), None, "pdf", None)
    assert m["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["heading_boundary_compliance"] \
        == {"value": 1.0, "reason": None}
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
