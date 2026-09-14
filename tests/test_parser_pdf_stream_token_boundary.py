r"""PDF 内容流边界落 token 中间——pdfminer 垫 \\n 截断锁定（Round 1940）。

PDF 规范语义：页 /Contents 多流应等同单一拼接流。edges44 锁
token **之间**分界（两 BT 拼接、跨流未闭合 BT 无缝）；**边界
落在 token 中间**零覆盖。探针 R1940 实证根因（pdfminer
psparser.PSStackParser.nexttoken，#1157 修复）：流切换时若有
半截 token 在途，垫 `\\n` 强行截断再续——拼接并非无缝：

- **T1 字符串中间断**：流 4 末 "(Str" + 流 6 "eam joined)" →
  content 恰 **'Str(cid:10)eam joined'**——垫入的 \\n 落进字面
  串成 0x0A 字符（StandardEncoding 无映射 → (cid:10) 标记，
  R1935 W3 家族的 EOL 触发形态），后半仍被提取、同元素、零告警
- **T2 数字中间断**："1" + "2 Tf" → 12 被截成 1/2 两 token
  （仅字号受损）——文本 'num split' 完整提取、单元素
- **T3 操作符中间断**："E" + "T" → ET 不再是 ET——首个文本对
  不闭合；后续 BT 照常开新元素 → 两元素 ['text','two']
  （edges34 missing-ET 容忍家族的多流触发形态）
- **T4 单流串内 EOL**（对照，非多流）：字面串含裸 \\n / \\r →
  (cid:10) / (cid:13) 直通 content（PDF 规范称 EOL 应归一为
  \\n——pdfminer 按 cid 标记保留）

判别式：若 pdfminer 改真无缝拼接（去掉 #1157 垫 \\n）则 T1
全等断言翻红（变 'Stream joined'）；若串内 EOL 被归一成普通
空格则 T4 cid 断言翻红。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf


def _stream_exact(c: bytes) -> bytes:
    return (b"<< /Length " + str(len(c)).encode()
            + b" >>\nstream\n" + c + b"\nendstream")


def _build_two_streams(c4: bytes, c6: bytes) -> bytes:
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> "
            b"/Contents [4 0 R 6 0 R] >>"),
        4: _stream_exact(c4),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        6: _stream_exact(c6),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref = len(out)
    mx = max(objs)
    out += b"xref\n0 " + str(mx + 1).encode() + b"\n0000000000 65535 f \n"
    for oid in range(1, mx + 1):
        out += ("%010d 00000 n \n" % offsets[oid]).encode()
    out += (b"trailer\n<< /Size " + str(mx + 1).encode()
            + b" /Root 1 0 R >>\nstartxref\n" + str(xref).encode()
            + b"\n%%EOF")
    return bytes(out)


def _parse_two(tmp_path: Path, c4: bytes, c6: bytes):
    p = tmp_path / "m.pdf"
    p.write_bytes(_build_two_streams(c4, c6))
    return FallbackParser().parse(p, compute_file_hash(p))


def test_mid_string_boundary_cid10(tmp_path):
    """T1：流边界落在字面串中间 → 'Str(cid:10)eam joined'
    （垫 \\n 成 0x0A → cid 标记），单元素零告警。"""
    d = _parse_two(tmp_path,
                   b"BT /F1 12 Tf 72 700 Td (Str",
                   b"eam joined) Tj ET")
    assert len(d.elements) == 1
    assert d.elements[0].content == "Str(cid:10)eam joined"
    assert d.warnings == []


def test_mid_number_boundary_text_intact(tmp_path):
    """T2：流边界落在字号数字中间（"1"+"2"）→ 文本完整
    'num split' 单元素（仅字号受损）。"""
    d = _parse_two(tmp_path,
                   b"BT /F1 1",
                   b"2 Tf 72 700 Td (num split) Tj ET")
    assert len(d.elements) == 1
    assert d.elements[0].content == "num split"
    assert d.warnings == []


def test_mid_operator_boundary_two_elements(tmp_path):
    """T3：流边界落在 ET 中间（"E"+"T"）→ 首文本对不闭合仍
    提取，后续 BT 开新元素 → ['text','two']。"""
    d = _parse_two(tmp_path,
                   b"BT /F1 12 Tf 72 700 Td (text) Tj E",
                   b"T\nBT /F1 12 Tf 72 600 Td (two) Tj ET")
    assert [e.content for e in d.elements] == ["text", "two"]
    assert d.warnings == []


def test_string_embedded_eol_cid_markers(tmp_path):
    """T4（对照，单流）：串内裸 \\n / \\r → (cid:10)/(cid:13)
    直通 content，不归一为空格。"""
    p = tmp_path / "e.pdf"
    p.write_bytes(_pdf([b"BT /F1 12 Tf 72 700 Td (a\nb) Tj ET"]))
    d1 = FallbackParser().parse(p, compute_file_hash(p))
    assert d1.elements[0].content == "a(cid:10)b"
    p2 = tmp_path / "e2.pdf"
    p2.write_bytes(_pdf([b"BT /F1 12 Tf 72 700 Td (a\rb) Tj ET"]))
    d2 = FallbackParser().parse(p2, compute_file_hash(p2))
    assert d2.elements[0].content == "a(cid:13)b"
