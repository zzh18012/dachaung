r"""PDF xref/全局行尾变体全通（Round 1979，a 优先级）。

既有 277 处 xref builder 全部 \n 行尾；Windows .NET/老工具
产物常见 CRLF。规范 xref 条目 20 字节含 2 字节 EOL（\r\n
或 空格+\n）。探针 R1979 实证（pdfminer 行尾宽容全过）：

- **E1 xref 条目 \r\n EOL**（其余行尾 \n）→ 'CRLFTEST' 照
  提、零告警
- **E2 全文件 CRLF**（header/对象/表/trailer/startxref 全
  \r\n，流内 \r\n 进 /Length 计数）→ 同上
- **E3 裸 \r 条目**（19 字节非规范形态）→ 同上——条目扫
  描按分隔符而非定长

判别式：若条目解析改按 20 字节定长读则 E3 翻红；若行尾
规约收紧为仅 \n 则 E1/E2 翻红。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _parse(eol_entry: bytes, xref_eol: bytes, base_eol: bytes):
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    body = b"BT /F1 12 Tf 100 700 Td (CRLFTEST) Tj ET"
    objs[4] = (b"<< /Length " + str(len(body)).encode()
               + b" >>" + base_eol + b"stream" + base_eol + body
               + base_eol + b"endstream")
    out = bytearray(b"%PDF-1.4" + base_eol)
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj".encode() + base_eol + objs[oid] \
            + base_eol + b"endobj" + base_eol
    xref = len(out)
    m = max(objs)
    out += b"xref" + xref_eol + f"0 {m + 1}".encode() + xref_eol \
        + b"0000000000 65535 f" + eol_entry
    for oid in range(1, m + 1):
        out += ("%010d 00000 n" % offsets[oid]).encode() + eol_entry
    out += (b"trailer" + xref_eol + b"<< /Size " + str(m + 1).encode()
            + b" /Root 1 0 R >>" + xref_eol + b"startxref" + xref_eol
            + str(xref).encode() + xref_eol + b"%%EOF")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "c.pdf"
        p.write_bytes(bytes(out))
        return FallbackParser().parse(p, compute_file_hash(p))


def _assert_ok(d):
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "CRLFTEST"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 162.0, 94.484], abs=0.01)
    assert d.warnings == []


def test_xref_entry_crlf_eol():
    """E1：xref 条目 \r\n EOL → 照提零告警。"""
    _assert_ok(_parse(b" \r\n", b"\n", b"\n"))


def test_whole_file_crlf():
    """E2：全文件 \r\n（含流内字节进 /Length）→ 照提零告警。"""
    _assert_ok(_parse(b" \r\n", b"\r\n", b"\r\n"))


def test_bare_cr_entries():
    """E3：裸 \r 条目（19 字节）→ 条目按分隔符扫描照提。"""
    _assert_ok(_parse(b"\r", b"\n", b"\n"))
