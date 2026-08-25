r"""app/parsers/fallback_parser.py 边角测试 - 第五十六轮（Round 1450）。

新角度（probe 实证）文本显示算子变体（历史全部用朴素
`(text) Tj`，转义/十六进制/TJ 数组/行进算子/Tm 从未碰过）：
- 字面串转义：`\\(` `\\)` → 括号、`\\\\` → 反斜杠、
  `\\101\\102\\103` 八进制 → 'ABC octal'，嵌套平衡括号原样保留
- 十六进制串 `<486578...> Tj` → 'Hex text'
- TJ 数组：-250 千分位字距 → 词被**拆开** 'Kern ed text'；
  0 偏移 → 词**粘连** 'ZeroKern'
- 行进算子：T*（TL 14）与 `'` → 两行并段；
  TD 显式换行 → 'First Second' 跨两行 bbox；
  `"` 算子的隐式换行**不生效** → 'OneTwo' 单行 bbox
- Tm：6 操作数与 Td 等价；2 操作数残缺 Tm → **静默回退原点**
  bbox [0.0, 782.484, ...]；2x 缩放 Tm → bbox 高 24
- 不可映射字符码：`\\t` → '(cid:9)' 占位符；
  `\\<EOL>` 行接续被正确消除 → 'Split string'
- 空串 `() Tj` → 0 元素 + pdf_no_text_extracted
- 残缺操作数栈：`(Dropped) Td` 字符串操作数被 TD 丢弃 →
  只剩 'Kept'，无告警
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
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


# ---------- 字面串转义 ----------

def test_escaped_parens(tmp_path):
    p = _pdf(
        tmp_path, "esc.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" (Escaped \\(paren\\)"
        b" back\\\\slash) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "Escaped (paren) back\\slash"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        220.72799999999995,
        94.48400000000004]


def test_octal_escape(tmp_path):
    p = _pdf(
        tmp_path, "oct.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" (\\101\\102\\103 octal)"
        b" Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "ABC octal"
    assert doc.warnings == []


def test_nested_parens(tmp_path):
    p = _pdf(
        tmp_path, "np.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" (Balanced (nested)"
        b" parens) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "Balanced (nested) parens"


# ---------- 十六进制串 ----------

def test_hex_string(tmp_path):
    p = _pdf(
        tmp_path, "hex.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" <4865782074657874>"
        b" Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Hex text"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        116.01599999999999,
        94.48400000000004]


# ---------- TJ 数组 ----------

def test_tj_negative_kern_splits(
        tmp_path):
    p = _pdf(
        tmp_path, "tjn.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" [(Kern) -250"
        b" (ed text)] TJ ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Kern ed text"


def test_tj_zero_offset_joins(
        tmp_path):
    p = _pdf(
        tmp_path, "tjz.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" [(Zero) 0 (K) 0"
        b" (ern)] TJ ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "ZeroKern"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        122.01599999999999,
        94.48400000000004]


# ---------- 行进算子 ----------

def test_tstar_leading_merge(
        tmp_path):
    p = _pdf(
        tmp_path, "ts.pdf",
        b"BT /F1 12 Tf 14 TL"
        b" 72 700 Td (Line one)"
        b" Tj T* (Line two) Tj"
        b" ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "Line one Line two"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        118.032, 108.48400000000004]


def test_td_operator(tmp_path):
    p = _pdf(
        tmp_path, "tdop.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" (First) Tj 0 -20 TD"
        b" (Second) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "First Second"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        112.69200000000001,
        114.48400000000004]


def test_quote_operator(tmp_path):
    p = _pdf(
        tmp_path, "qo.pdf",
        b"BT /F1 12 Tf 14 TL"
        b" 72 700 Td (One) Tj"
        b" (Two)' ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "One Two"


def test_dquote_no_line_move(
        tmp_path):
    p = _pdf(
        tmp_path, "dq.pdf",
        b"BT /F1 12 Tf 14 TL"
        b" 72 700 Td 0 Tc 0 Tw"
        b" (One) Tj 5 0 (Two)\""
        b" ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "OneTwo"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        117.348, 94.48400000000004]


# ---------- Tm 矩阵 ----------

def test_tm_identity(tmp_path):
    p = _pdf(
        tmp_path, "tmi.pdf",
        b"BT /F1 12 Tf"
        b" 1 0 0 1 72 700 Tm"
        b" (Matrix text) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Matrix text"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        127.344, 94.48400000000004]


def test_tm_two_operand_origin(
        tmp_path):
    p = _pdf(
        tmp_path, "tm2.pdf",
        b"BT /F1 12 Tf 72 700 Tm"
        b" (Matrix text) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Matrix text"
    assert doc.elements[
        0].source_locator["bbox"] == [
        0.0, 782.484,
        55.343999999999994, 794.484]
    assert doc.warnings == []


def test_tm_scaled_2x(tmp_path):
    p = _pdf(
        tmp_path, "tms.pdf",
        b"BT /F1 12 Tf"
        b" 2 0 0 2 72 700 Tm"
        b" (Scaled text) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Scaled text"
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox == [
        72.0, 72.96799999999996,
        190.728, 96.96799999999996]
    assert (bbox[3] - bbox[1]) == 24.0


# ---------- 不可映射字符码 ----------

def test_cid_tab_placeholder(
        tmp_path):
    p = _pdf(
        tmp_path, "cidt.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" (Tab\\there tab) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "Tab(cid:9)here tab"


def test_line_continuation_joins(
        tmp_path):
    p = _pdf(
        tmp_path, "lc.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" (Split \\\n string)"
        b" Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Split string"


# ---------- 空串 / 残缺操作数 ----------

def test_empty_string_warning(
        tmp_path):
    p = _pdf(
        tmp_path, "es.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" () Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements == []
    assert [w.code
            for w in doc.warnings] == [
        "pdf_no_text_extracted"]


def test_string_operand_dropped(
        tmp_path):
    p = _pdf(
        tmp_path, "so.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" (Dropped) Td 0 -20 TD"
        b" (Kept) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Kept"]
    assert doc.warnings == []


# ---------- 通用 ----------

def test_operators_schema(
        tmp_path):
    from app.schema import is_valid
    p = _pdf(
        tmp_path, "osch.pdf",
        b"BT /F1 12 Tf"
        b" 1 0 0 1 72 700 Tm"
        b" [(Mixed) -100"
        b" ( operators)] TJ ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_operators_chunk(
        tmp_path):
    p = _pdf(
        tmp_path, "och.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" <4865782074657874>"
        b" Tj ET")
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert doc.chunks[
        0].text == "Hex text"
