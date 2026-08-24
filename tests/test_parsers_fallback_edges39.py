r"""app/parsers/fallback_parser.py 边角测试 - 第三十九轮（Round 1430）。

新角度（probe 实证）字体 /Encoding 字典（历史字体全裸
/BaseFont，R1419 锁的 0xE9→'Ø' 是 StandardEncoding 默认）：
- 同字节 (caf\351 ...) 三种编码三样输出：
  WinAnsi → 'café'；MacRoman → 'cafÈ'（0xE9 是 È）；
  默认 Standard → 'cafØ'（R1419 同款）
- /Encoding << /Differences [65 /Delta /E] >>：'ABC def'
  → '∆EC def'（65=A→∆ U+2206、66=B→E，自定义字形重映射
  生效）
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _build(font_extra, content):
    objs = {
        5: (b"<< /Type /Font /Subtype "
            b"/Type1 /BaseFont "
            b"/Helvetica "
            + font_extra + b" >>"),
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


def _enc_pdf(tmp_path, name,
             font_extra, content):
    p = tmp_path / name
    p.write_bytes(_build(font_extra,
                         content))
    return p


_CAFE = (b"BT /F1 12 Tf 72 700 Td "
         b"(caf\\351 winansi) Tj ET")


# ---------- 三编码同字节 ----------

def test_winansi(tmp_path):
    p = _enc_pdf(
        tmp_path, "wa.pdf",
        b"/Encoding /WinAnsi"
        b"Encoding", _CAFE)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "café winansi"


def test_macroman(tmp_path):
    p = _enc_pdf(
        tmp_path, "mr.pdf",
        b"/Encoding /MacRoman"
        b"Encoding", _CAFE)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "cafÈ winansi"


def test_default_std(tmp_path):
    p = _enc_pdf(
        tmp_path, "def.pdf", b"",
        _CAFE)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "cafØ winansi"


def test_encodings_differ(
        tmp_path):
    outs = []
    for name, extra in (
            ("wa.pdf",
             b"/Encoding /WinAnsi"
             b"Encoding"),
            ("mr.pdf",
             b"/Encoding /MacRoman"
             b"Encoding"),
            ("def.pdf", b"")):
        p = _enc_pdf(
            tmp_path, name, extra,
            _CAFE)
        doc = FallbackParser(
        ).parse(p,
                compute_file_hash(p))
        outs.append(doc.elements[
            0].content)
    assert len(set(outs)) == 3


def test_encodings_no_warnings(
        tmp_path):
    for name, extra in (
            ("wa.pdf",
             b"/Encoding /WinAnsi"
             b"Encoding"),
            ("mr.pdf",
             b"/Encoding /MacRoman"
             b"Encoding")):
        p = _enc_pdf(
            tmp_path, name, extra,
            _CAFE)
        doc = FallbackParser(
        ).parse(p,
                compute_file_hash(p))
        assert doc.warnings == []


def test_winansi_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _enc_pdf(
        tmp_path, "wa.pdf",
        b"/Encoding /WinAnsi"
        b"Encoding", _CAFE)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_winansi_chunk(tmp_path):
    p = _enc_pdf(
        tmp_path, "wa.pdf",
        b"/Encoding /WinAnsi"
        b"Encoding", _CAFE)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert doc.chunks[
        0].text == "café winansi"


# ---------- Differences 数组 ----------

def test_differences_remap(
        tmp_path):
    p = _enc_pdf(
        tmp_path, "dif.pdf",
        b"/Encoding << /Differences "
        b"[65 /Delta /E] >>",
        b"BT /F1 12 Tf 72 700 Td "
        b"(ABC def) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "∆EC def"


def test_differences_no_warnings(
        tmp_path):
    p = _enc_pdf(
        tmp_path, "dif.pdf",
        b"/Encoding << /Differences "
        b"[65 /Delta /E] >>",
        b"BT /F1 12 Tf 72 700 Td "
        b"(ABC def) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.warnings == []


def test_differences_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _enc_pdf(
        tmp_path, "dif.pdf",
        b"/Encoding << /Differences "
        b"[65 /Delta /E] >>",
        b"BT /F1 12 Tf 72 700 Td "
        b"(ABC def) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())
