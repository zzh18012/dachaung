r"""PDF 退化 /Contents 五形态统一容忍（Round 2009，a 优先级）。

edges115 已锁 /Contents 指向 dict（非流）与 /Length 间接；
**null / 空数组 / 键缺失 / 空流 / 纯空白流**五种退化形态
零覆盖（grep 实证）。探针 R2009 实证：五者**同一下场**——
0 元素 + 仅 pdf_no_text_extracted，不抛异常、无额外告警
（页对象本身合法，pdfplumber 把页当空页处理）。

判别式：任一形态若抛 pdfplumber_open_failed 或出现
word_extract_failed 等额外告警则翻红；若有元素翻红。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _build(contents_field: bytes, stream_body: bytes = b"") -> bytes:
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Resources << /Font << /F1 5 0 R >> >> "
            + contents_field + b" >>"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        4: (b"<< /Length " + str(len(stream_body)).encode()
            + b" >>\nstream\n" + stream_body + b"\nendstream"),
    }
    out = bytearray(b"%PDF-1.5\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref = len(out)
    m = max(objs)
    out += f"xref\n0 {m + 1}\n".encode() + b"0000000000 65535 f \n"
    for oid in range(1, m + 1):
        out += ("%010d 00000 n \n" % offsets[oid]).encode()
    out += (b"trailer\n<< /Size " + str(m + 1).encode()
            + b" /Root 1 0 R >>\nstartxref\n" + str(xref).encode()
            + b"\n%%EOF")
    return bytes(out)


def _parse(tmp_path: Path, contents_field: bytes, stream_body: bytes = b""):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "c.pdf"
        p.write_bytes(_build(contents_field, stream_body))
        return FallbackParser().parse(p, compute_file_hash(p))


def _assert_empty(d):
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["pdf_no_text_extracted"]


def test_contents_null(tmp_path):
    """T1：/Contents null → 0 元素 + 仅 pdf_no_text_extracted。"""
    _assert_empty(_parse(tmp_path, b"/Contents null"))


def test_contents_empty_array(tmp_path):
    """T2：/Contents [ ]（空数组）→ 同 T1。"""
    _assert_empty(_parse(tmp_path, b"/Contents [ ]"))


def test_contents_missing(tmp_path):
    """T3：页 dict 无 /Contents 键 → 同 T1。"""
    _assert_empty(_parse(tmp_path, b""))


def test_contents_empty_stream(tmp_path):
    """T4：指向 /Length 0 空流 → 同 T1。"""
    _assert_empty(_parse(tmp_path, b"/Contents 4 0 R", b""))


def test_contents_whitespace_only_stream(tmp_path):
    """T5：指向纯空白流（'   \\n   '）→ 同 T1（无操作数无算子）。"""
    _assert_empty(_parse(tmp_path, b"/Contents 4 0 R", b"   \n   "))
