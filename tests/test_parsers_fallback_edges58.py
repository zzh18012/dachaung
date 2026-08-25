r"""app/parsers/fallback_parser.py 边角测试 - 第五十八轮（Round 1452）。

新角度（probe 实证）聚合/分类边界（自有代码 _group_words_
to_paragraphs 与 _classify_pdf_paragraph 的阈值从未直接打过）：
- 行聚类边界（y 中心差 ≤3.0 同行）：恰好 3.0 → pdfplumber
  自身容差把两段重叠文本**字符交错**成一个词 'ABlepthaa'
  bbox [72.0, 82.484, 102.684, 97.484]；3.5 → 两行分开
  'Alpha Beta' bbox 高 15.5
- 段落边界（行距 > 1.5×中位行高=18）：恰好 18.0 → 同段
  'Alpha Beta' 单元素跨两行 bbox；18.1 → **劈成两元素**
- 标题长度边界：恰好 80 字符 → heading；81 → paragraph
- 句尾标点：'Short line.'/'Ends with !' → paragraph；
  无标点短行 → heading level 0
- caption 正则：'Table 1. '/'Table 1 '/'figure 2:'/
  'Fig. 3 ' → caption；'Tab 1.' → heading；
  直连 _is_caption：'表 1、'/'图2、'/'表１、'/'图3 ' 命中，
  全角冒号 '：' 不在字符类 → '图2：' 不命中（文档化缺口），
  'Tables 1.' 不命中
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser, _is_caption
from app.pipeline import process_single


def _stream(data):
    return (b"<< /Length "
            + str(len(data)).encode()
            + b" >>\nstream\n" + data
            + b"\nendstream")


def _build(objs):
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


def _pdf(tmp_path, name, content4):
    objs = {
        5: (b"<< /Type /Font /Subtype"
            b" /Type1 /BaseFont "
            b"/Helvetica >>"),
        1: (b"<< /Type /Catalog "
            b"/Pages 2 0 R >>"),
        2: (b"<< /Type /Pages "
            b"/Kids [3 0 R] "
            b"/Count 1 >>"),
        3: (b"<< /Type /Page /Parent"
            b" 2 0 R /MediaBox "
            b"[0 0 612 792] "
            b"/Resources << /Font "
            b"<< /F1 5 0 R >> >>"
            b" /Contents 4 0 R >>"),
        4: _stream(content4),
    }
    p = tmp_path / name
    p.write_bytes(_build(objs))
    return p


def _two_line(tmp_path, name, y2):
    return _pdf(
        tmp_path, name,
        b"BT /F1 12 Tf 72 700 Td"
        b" (Alpha) Tj ET"
        b" BT /F1 12 Tf 72 "
        + str(y2).encode()
        + b" Td (Beta) Tj ET")


# ---------- 行聚类边界 ----------

def test_ycenter_3p0_interleaved(
        tmp_path):
    p = _two_line(
        tmp_path, "lc3.pdf", 697)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "ABlepthaa"]
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        102.684, 97.48400000000004]


def test_ycenter_3p5_two_lines(
        tmp_path):
    p = _two_line(
        tmp_path, "lc35.pdf", 696.5)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Alpha Beta"]
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        102.684, 97.98400000000004]


# ---------- 段落边界 ----------

def test_para_gap_18_same(
        tmp_path):
    p = _two_line(
        tmp_path, "pg18.pdf", 670)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Alpha Beta"]
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        102.684, 124.48400000000004]


def test_para_gap_18p1_split(
        tmp_path):
    p = _two_line(
        tmp_path, "pg181.pdf", 669.9)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Alpha", "Beta"]
    assert doc.elements[
        1].source_locator["bbox"] == [
        72.0, 112.58400000000006,
        96.684, 124.58400000000006]


# ---------- 标题长度边界 ----------

def test_heading_len_80(tmp_path):
    p = _pdf(
        tmp_path, "h80.pdf",
        b"BT /F1 12 Tf 72 700 Td ("
        + b"H" * 80
        + b") Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].type == "heading"
    assert doc.elements[
        0].metadata == {
        "level": 0,
        "heuristic": "short_line"}


def test_heading_len_81(tmp_path):
    p = _pdf(
        tmp_path, "h81.pdf",
        b"BT /F1 12 Tf 72 700 Td ("
        + b"H" * 81
        + b") Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].type == "paragraph"
    assert doc.elements[
        0].metadata == {}


# ---------- 句尾标点 ----------

def test_period_forces_paragraph(
        tmp_path):
    p = _pdf(
        tmp_path, "pd.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" (Short line.) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].type == "paragraph"


def test_exclamation_paragraph(
        tmp_path):
    p = _pdf(
        tmp_path, "ex.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" (Ends with !) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].type == "paragraph"


# ---------- caption 正则 ----------

def _caption_case(tmp_path, name,
                  text):
    p = _pdf(
        tmp_path, name,
        b"BT /F1 12 Tf 72 700 Td ("
        + text + b") Tj ET")
    return FallbackParser().parse(
        p, compute_file_hash(p))


def test_caption_table_dot(
        tmp_path):
    doc = _caption_case(
        tmp_path, "c1.pdf",
        b"Table 1. Data")
    assert doc.elements[
        0].type == "caption"
    assert doc.elements[
        0].metadata == {
        "heuristic": "caption_regex"}


def test_caption_space(tmp_path):
    doc = _caption_case(
        tmp_path, "c2.pdf",
        b"Table 1 Data")
    assert doc.elements[
        0].type == "caption"


def test_caption_lowercase_colon(
        tmp_path):
    doc = _caption_case(
        tmp_path, "c3.pdf",
        b"figure 2: Fig")
    assert doc.elements[
        0].type == "caption"


def test_caption_fig_dot(
        tmp_path):
    doc = _caption_case(
        tmp_path, "c4.pdf",
        b"Fig. 3 Caption")
    assert doc.elements[
        0].type == "caption"


def test_not_caption_tab(
        tmp_path):
    doc = _caption_case(
        tmp_path, "c5.pdf",
        b"Tab 1. Not")
    assert doc.elements[
        0].type == "heading"


# ---------- _is_caption 直连 ----------

def test_is_caption_chinese():
    assert _is_caption("表 1、销售数据")
    assert _is_caption("图2、架构")
    assert _is_caption("表１、全角数字")
    assert _is_caption("图3 ")


def test_is_caption_fullwidth_colon_gap():
    # 全角冒号 '：' 不在正则字符类 [\.、:\s] 内——文档化缺口
    assert not _is_caption("图2：架构")
    assert not _is_caption("表 1：销售")


def test_is_caption_negative():
    assert not _is_caption("Tables 1. plural")
    assert not _is_caption("prefix 表 1、")
    assert not _is_caption("")
    assert not _is_caption(None)


# ---------- 通用 ----------

def test_split_paragraphs_chunk(
        tmp_path):
    p = _two_line(
        tmp_path, "spc.pdf", 669.9)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "Alpha", "Beta"]


def test_split_schema(tmp_path):
    from app.schema import is_valid
    p = _two_line(
        tmp_path, "sps.pdf", 670)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())
