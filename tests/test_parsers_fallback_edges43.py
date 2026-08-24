r"""app/parsers/fallback_parser.py 边角测试 - 第四十三轮（Round 1435）。

新角度（probe 实证）文本定位/微调操作符（历史只碰过 Td/Tm，
TL/T*/TD/'/" 与 TJ 数组全空白）：
- TJ 数组 [（Ker) -120 (ned) 60 (text)]：文本无空格直连
  'Kernedtext'，净调整 -60 → bbox 比裸 Tj 宽 0.72pt
  （130.752 vs 130.032，= 60/1000×12）
- TL+T* 纵向聚类阈值精确定位：dy≤30 同列两词合并单元素
  （空格连接），dy≥31 分裂两元素；leading 200 时第二行
  bbox [282.484, 294.484] 无浮点尘埃
- TD（设 leading + 移动）：同 T* 效果 'Alpha Beta' 合并
- ' 撇号 = T*+Tj：TL=0 时同基线字符级交错
  'ANpeoxtstrophe'；TL=24 时正常空格合并
- " 双引号：**不做换行**——TL=40 仍单行直连
  'Quote oneQuote two'（当前 Tj 位置续排）
- [()] TJ（仅空串）：零元素 + pdf_no_text_extracted 告警
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


def _pdf(tmp_path, name, content):
    p = tmp_path / name
    p.write_bytes(_build(content))
    return p


# ---------- TJ 数组 ----------

def test_tj_adjustments_concat(
        tmp_path):
    p = _pdf(
        tmp_path, "tj.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"[(Ker) -120 (ned) 60 "
        b"(text)] TJ ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Kernedtext"]
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        130.752, 94.48400000000004]


def test_tj_wider_than_plain(
        tmp_path):
    p_tj = _pdf(
        tmp_path, "tj2.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"[(Ker) -120 (ned) 60 "
        b"(text)] TJ ET")
    p_plain = _pdf(
        tmp_path, "plain.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"(Kernedtext) Tj ET")
    d1 = FallbackParser().parse(
        p_tj, compute_file_hash(p_tj))
    d2 = FallbackParser().parse(
        p_plain,
        compute_file_hash(p_plain))
    w_tj = (d1.elements[0]
            .source_locator
            ["bbox"][2])
    w_plain = (d2.elements[0]
               .source_locator
               ["bbox"][2])
    assert w_plain == 130.032
    assert round(
        w_tj - w_plain, 6) == 0.72


def test_tj_empty_array_no_ghost(
        tmp_path):
    p = _pdf(
        tmp_path, "tje.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"(Before) Tj [] TJ "
        b"(After) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "BeforeAfter"]
    assert len(doc.elements) == 1


def test_tj_only_empty_string(
        tmp_path):
    p = _pdf(
        tmp_path, "tjoe.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"[()] TJ ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements == []
    assert [w.code
            for w in doc.warnings] == [
        "pdf_no_text_extracted"]


def test_tj_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _pdf(
        tmp_path, "tj3.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"[(Ker) -120 (ned) 60 "
        b"(text)] TJ ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


# ---------- TL + T* ----------

def test_tl24_three_lines_merge(
        tmp_path):
    p = _pdf(
        tmp_path, "tl.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"24 TL (First line) Tj "
        b"T* (Second line) Tj "
        b"T* (Third line) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "First line Second line "
        "Third line"]
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        134.70000000000002,
        142.48400000000004]


def test_dy30_merge(tmp_path):
    p = _pdf(
        tmp_path, "dy30.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"30 TL (Top word) Tj "
        b"T* (Bot word) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert len(doc.elements) == 1
    assert doc.elements[
        0].content == \
        "Top word Bot word"


def test_dy31_split(tmp_path):
    p = _pdf(
        tmp_path, "dy31.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"31 TL (Top word) Tj "
        b"T* (Bot word) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Top word", "Bot word"]
    assert doc.elements[
        1].source_locator["bbox"] == [
        72.0, 113.48400000000004,
        119.352, 125.48400000000004]


def test_lead200_split(tmp_path):
    p = _pdf(
        tmp_path, "l200.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"200 TL (Twohun A) Tj "
        b"T* (Twohun B) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Twohun A", "Twohun B"]
    assert doc.elements[
        1].source_locator["bbox"] == [
        72.0, 282.484, 126.024,
        294.484]


def test_lead200_chunks(tmp_path):
    p = _pdf(
        tmp_path, "l200c.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"200 TL (Twohun A) Tj "
        b"T* (Twohun B) Tj ET")
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "Twohun A", "Twohun B"]


# ---------- TD ----------

def test_td_merge(tmp_path):
    p = _pdf(
        tmp_path, "td.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"(Alpha) Tj 0 -24 TD "
        b"(Beta) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Alpha Beta"]
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        102.684, 118.48400000000004]


# ---------- 撇号 / 双引号 ----------

def test_apo_tl0_interleave(
        tmp_path):
    p = _pdf(
        tmp_path, "apo0.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"24 TL (Apostrophe) Tj "
        b"0 TL (Next) ' ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "ANpeoxtstrophe"


def test_apo_tl24_merge(
        tmp_path):
    p = _pdf(
        tmp_path, "apo24.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"24 TL (First apo) Tj "
        b"(Second apo) ' ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "First apo Second apo"]


def test_dq_no_line_move(
        tmp_path):
    p = _pdf(
        tmp_path, "dq40.pdf",
        b'BT /F1 12 Tf 72 700 Td '
        b'40 TL (Quote one) Tj '
        b'0 0 (Quote two) " ET')
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Quote oneQuote two"]
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        182.73599999999996,
        94.48400000000004]


def test_dq_concat_no_space(
        tmp_path):
    p = _pdf(
        tmp_path, "dq.pdf",
        b'BT /F1 12 Tf 72 700 Td '
        b'24 TL (DQ line) Tj '
        b'0 0 (DQ next) " ET')
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "DQ lineDQ next"


# ---------- 通用 ----------

def test_no_warnings(tmp_path):
    for name, content in (
            ("w1.pdf",
             b"BT /F1 12 Tf 72 700 Td "
             b"[(Ker) -120 (ned) 60 "
             b"(text)] TJ ET"),
            ("w2.pdf",
             b'BT /F1 12 Tf 72 700 Td '
             b'40 TL (Quote one) Tj '
             b'0 0 (Quote two) " ET'),
            ("w3.pdf",
             b"BT /F1 12 Tf 72 700 Td "
             b"31 TL (Top word) Tj "
             b"T* (Bot word) Tj ET")):
        p = _pdf(tmp_path, name,
                 content)
        doc = FallbackParser().parse(
            p, compute_file_hash(p))
        assert doc.warnings == []


def test_dy31_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _pdf(
        tmp_path, "d31s.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"31 TL (Top word) Tj "
        b"T* (Bot word) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_tj_chunk(tmp_path):
    p = _pdf(
        tmp_path, "tjc.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"[(Ker) -120 (ned) 60 "
        b"(text)] TJ ET")
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert doc.chunks[
        0].text == "Kernedtext"
