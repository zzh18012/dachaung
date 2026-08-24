r"""app/parsers/fallback_parser.py 边角测试 - 第十二轮（Round 1385）。

真实 PDF 字节的段落 grouping 行为（承接 Round 1384 的
真实字节端到端，本轮聚焦 group_words_to_paragraphs 穿过
真实 pdfplumber word 框）：
- 同 y 两词流序 ≠ x 序 → 按 x0 排序（'left word right word'）
- 14pt 紧邻三行合并成单元素（空格连接）
- 合并后 bbox 跨行聚合：top=首行 top、bottom=末行 bottom、
  x1=各行 x1 最大值
- 50pt 间隔三行 → 三个独立元素
- 12pt Helvetica 实测 gap 阈值：≤30 合并、≥32 切分
- 混合板：紧邻对合并 + 远距行独立
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _build_pdf(pages_lines):
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


def _parse(tmp_path, pages, name="d.pdf"):
    p = tmp_path / name
    p.write_bytes(_build_pdf(pages))
    return FallbackParser().parse(
        p, compute_file_hash(p))


_TIGHT = [
    (700, "line one of merged para"),
    (686, "line two of merged para"),
    (672, "line three ends here.")]

_MIXED = [
    (700, "alpha first line here."),
    (686, "alpha second line here."),
    (636, "beta para starts anew.")]


# ---------- 同 y 流序 ≠ x 序 ----------

def _same_y_pdf(tmp_path):
    """x=300 的词在流里先出现，x=72 后出现。"""
    stream = " ".join([
        "BT /F1 12 Tf 300 700 Td "
        "(right word) Tj ET",
        "BT /F1 12 Tf 72 700 Td "
        "(left word) Tj ET"]).encode()
    objs = {
        1: b"<< /Type /Catalog "
           b"/Pages 2 0 R >>",
        2: (b"<< /Type /Pages "
            b"/Kids [3 0 R] /Count 1 >>"),
        3: (b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 "
            b"5 0 R >> >> /Contents "
            b"4 0 R >>"),
        5: (b"<< /Type /Font /Subtype "
            b"/Type1 /BaseFont "
            b"/Helvetica >>"),
        4: (b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n" + stream
            + b"\nendstream")}
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += (f"{oid} 0 obj\n".encode()
                + objs[oid] + b"\nendobj\n")
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
    p = tmp_path / "same.pdf"
    p.write_bytes(bytes(out))
    return p


def test_same_y_sorted_by_x(tmp_path):
    p = _same_y_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[0].content == \
        "left word right word"


def test_same_y_single_element(tmp_path):
    p = _same_y_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert len(doc.elements) == 1


def test_same_y_short_no_period_heading(
        tmp_path):
    p = _same_y_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[0].type == "heading"
    assert doc.elements[0].metadata == {
        "level": 0, "heuristic": "short_line"}


# ---------- 紧邻合并 ----------

def test_tight_lines_merge_one(tmp_path):
    doc = _parse(tmp_path, [_TIGHT])
    assert len(doc.elements) == 1


def test_tight_merged_space_joined(
        tmp_path):
    doc = _parse(tmp_path, [_TIGHT])
    assert doc.elements[0].content == (
        "line one of merged para "
        "line two of merged para "
        "line three ends here.")


def test_tight_merged_is_paragraph(
        tmp_path):
    doc = _parse(tmp_path, [_TIGHT])
    assert doc.elements[0].type == \
        "paragraph"
    assert doc.elements[0].metadata == {}


def test_merged_bbox_aggregates(tmp_path):
    """top=首行(y=700) 82.484，bottom=末行
    (y=672) 122.484。"""
    doc = _parse(tmp_path, [_TIGHT])
    bb = doc.elements[0].source_locator[
        "bbox"]
    assert bb == [72.0, 82.48400000000004,
                  198.73199999999994,
                  122.48400000000004]


def test_merged_bbox_x1_max_across(tmp_path):
    """x1 是三行各自 x1 的最大值（第三行
    最长）。"""
    doc = _parse(tmp_path, [_TIGHT])
    assert doc.elements[0].source_locator[
        "bbox"][2] == 198.73199999999994


# ---------- 远距切分 ----------

def test_far_lines_three_elements(tmp_path):
    doc = _parse(tmp_path, [[
        (700, "para one ends here."),
        (650, "para two ends here."),
        (600, "para three ends here.")]])
    assert len(doc.elements) == 3
    assert [e.content for e in doc.elements
            ] == ["para one ends here.",
                  "para two ends here.",
                  "para three ends here."]


# ---------- gap 阈值 ----------

def test_gap30_merges(tmp_path):
    doc = _parse(tmp_path, [[
        (700, "alpha line here."),
        (670, "beta line here.")]])
    assert len(doc.elements) == 1
    assert doc.elements[0].content == (
        "alpha line here. beta line here.")


def test_gap32_splits(tmp_path):
    doc = _parse(tmp_path, [[
        (700, "alpha line here."),
        (668, "beta line here.")]])
    assert len(doc.elements) == 2


# ---------- 混合板 ----------

def test_mixed_pair_plus_solo(tmp_path):
    doc = _parse(tmp_path, [_MIXED])
    assert len(doc.elements) == 2


def test_mixed_first_is_merged_pair(
        tmp_path):
    doc = _parse(tmp_path, [_MIXED])
    assert doc.elements[0].content == (
        "alpha first line here. "
        "alpha second line here.")


def test_mixed_second_solo(tmp_path):
    doc = _parse(tmp_path, [_MIXED])
    assert doc.elements[1].content == \
        "beta para starts anew."


def test_mixed_bboxes(tmp_path):
    doc = _parse(tmp_path, [_MIXED])
    bbs = [e.source_locator["bbox"]
           for e in doc.elements]
    assert bbs[0][1] < bbs[1][1]
    assert bbs[1] == [72.0, 146.48400000000004,
                      190.728, 158.48400000000004]


# ---------- schema + 管线 ----------

def test_mixed_passes_schema(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path, [_MIXED])
    assert is_valid(doc.to_dict())


def test_tight_passes_schema(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path, [_TIGHT])
    assert is_valid(doc.to_dict())


def test_mixed_single_chunk(tmp_path):
    from app.pipeline import process_single
    p = tmp_path / "m.pdf"
    p.write_bytes(_build_pdf([_MIXED]))
    doc, errors = process_single(
        p, None, parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert len(doc.chunks) == 1
