r"""app/parsers/fallback_parser.py 边角测试 - 第四十四轮（Round 1436）。

新角度（probe 实证）文本状态操作符 + 多 /Contents 流（历史
状态只碰过 Tf/Td/Tm/TL，Tw/Tc/Tz/Ts/Tr 与流数组全空白）：
- Tw 15：文本不变仅加宽空格 bbox（195.372）；真实空格
  'a b c' 也不双空格
- Tc 字距**词裂变阈值 = 3pt**：Tc1/Tc2 'Stretched' 完整
  （131.36/139.36），Tc3 → 'Str etched'（147.36，pdfminer
  词间隙启发式把 ≥3pt 字缝当空格）
- Tz 50：水平缩放半宽 bbox 98.34
- Ts 8：基线抬升——bbox 整体上移 8pt（82.484→74.484）
- Tr 3 隐形渲染模式：**照常提取**（渲染模式被无视）
- /Contents [4 0 R 6 0 R]：两流拼接，各自 BT → 两元素
  （100pt 垂直间隔）；跨流未闭合 BT → 'Stream first Stream
  cont text' 无缝单元素
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _stream(content):
    return (b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n"
            + content + b"\nendstream")


def _build(content4,
           contents=b"4 0 R",
           extra=None):
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
            b"/Contents "
            + contents + b" >>"),
        4: _stream(content4),
    }
    if extra:
        objs.update(extra)
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
        out += ("%010d 00000 n \n"
                % offsets[oid]).encode()
    out += (b"trailer\n<< /Size "
            + str(mx + 1).encode()
            + b" /Root 1 0 R >>\n"
            b"startxref\n"
            + str(xref_pos).encode()
            + b"\n%%EOF")
    return bytes(out)


def _pdf(tmp_path, name, content,
         contents=b"4 0 R",
         extra=None):
    p = tmp_path / name
    p.write_bytes(_build(content,
                         contents, extra))
    return p


# ---------- Tw 词距 ----------

def test_tw_text_unchanged(
        tmp_path):
    p = _pdf(
        tmp_path, "tw.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"15 Tw (Word spaced text)"
        b" Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "Word spaced text"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        195.372, 94.48400000000004]


def test_tw_real_spaces(
        tmp_path):
    p = _pdf(
        tmp_path, "tws.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"15 Tw (a b c) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "a b c"


# ---------- Tc 字距 ----------

def test_tc1_intact(tmp_path):
    p = _pdf(
        tmp_path, "tc1.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"1 Tc (Stretched) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Stretched"
    assert doc.elements[
        0].source_locator["bbox"][2] \
        == 131.36


def test_tc2_intact(tmp_path):
    p = _pdf(
        tmp_path, "tc2.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"2 Tc (Stretched) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Stretched"
    assert doc.elements[
        0].source_locator["bbox"][2] \
        == 139.35999999999999


def test_tc3_word_split(
        tmp_path):
    p = _pdf(
        tmp_path, "tc3.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"3 Tc (Stretched) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Str etched"
    assert doc.elements[
        0].source_locator["bbox"][2] \
        == 147.35999999999999


# ---------- Tz / Ts / Tr ----------

def test_tz_half_scale(tmp_path):
    p = _pdf(
        tmp_path, "tz.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"50 Tz (Half scale) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Half scale"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        98.33999999999999,
        94.48400000000004]


def test_ts_rises_bbox(tmp_path):
    p = _pdf(
        tmp_path, "ts.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"8 Ts (Risen) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Risen"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 74.48400000000004,
        102.672, 86.48400000000004]


def test_tr3_invisible_still(
        tmp_path):
    p = _pdf(
        tmp_path, "tr3.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"3 Tr (Invisibly) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Invisibly"]
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        114.67200000000001,
        94.48400000000004]
    assert doc.warnings == []


# ---------- 多 /Contents 流 ----------

def _mc_extra():
    c6 = (b"BT /F1 12 Tf 72 600 Td "
          b"(Stream two text) "
          b"Tj ET")
    return {6: _stream(c6)}


def test_mc_both_streams(
        tmp_path):
    p = _pdf(
        tmp_path, "mc.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"(Stream one text) Tj ET",
        b"[4 0 R 6 0 R]",
        _mc_extra())
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Stream one text",
        "Stream two text"]
    assert doc.warnings == []


def test_mc_bboxes(tmp_path):
    p = _pdf(
        tmp_path, "mcb.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"(Stream one text) Tj ET",
        b"[4 0 R 6 0 R]",
        _mc_extra())
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        1].source_locator["bbox"] == [
        72.0, 182.48400000000004,
        155.364, 194.48400000000004]


def test_mc_unclosed_bt_across(
        tmp_path):
    c6 = (b"(Stream cont text) "
          b"Tj ET")
    p = _pdf(
        tmp_path, "mc2.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"(Stream first ) Tj ",
        b"[4 0 R 6 0 R]",
        {6: _stream(c6)})
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Stream first Stream cont "
        "text"]
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        224.05200000000002,
        94.48400000000004]


# ---------- 通用 ----------

def test_mc_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _pdf(
        tmp_path, "mcs.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"(Stream one text) Tj ET",
        b"[4 0 R 6 0 R]",
        _mc_extra())
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_mc_chunks(tmp_path):
    p = _pdf(
        tmp_path, "mcc.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"(Stream one text) Tj ET",
        b"[4 0 R 6 0 R]",
        _mc_extra())
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "Stream one text",
        "Stream two text"]


def test_tc3_chunk(tmp_path):
    p = _pdf(
        tmp_path, "tc3c.pdf",
        b"BT /F1 12 Tf 72 700 Td "
        b"3 Tc (Stretched) Tj ET")
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert doc.chunks[
        0].text == "Str etched"


def test_state_no_warnings(
        tmp_path):
    for name, content in (
            ("n1.pdf",
             b"BT /F1 12 Tf 72 700 Td "
             b"1 Tc (Stretched) "
             b"Tj ET"),
            ("n2.pdf",
             b"BT /F1 12 Tf 72 700 Td "
             b"50 Tz (Half scale) "
             b"Tj ET"),
            ("n3.pdf",
             b"BT /F1 12 Tf 72 700 Td "
             b"8 Ts (Risen) Tj ET")):
        p = _pdf(tmp_path, name,
                 content)
        doc = FallbackParser().parse(
            p, compute_file_hash(p))
        assert doc.warnings == []
