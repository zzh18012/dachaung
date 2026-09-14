r"""PDF WinAnsi 高区字节锁定（Round 1935，a 优先级）。

_pdf 构造器字体无 /Encoding（StandardEncoding 低位 ASCII）；
**WinAnsi 高区**（0x80-0x9F 特殊标点 / NBSP / 未定义位）此前
零覆盖。探针 R1935 实证（/Encoding /WinAnsiEncoding 字体）：

- **W1 高区标点直通**：0x93/0x94/0x97 → 弯引号 + em dash
  （U+201C/U+201D/U+2014）原样进 content，零告警
- **W2 NBSP 词边界归一**："a\\xa0b" → content 恰 **'a b'**
  （U+0020）——NBSP 被 pdfplumber 当词分隔，解析器空格连接
  重插 ASCII 空格（非保留 U+00A0 在词内）
- **W3 未定义位 (cid:N) 直通**：0x81（WinAnsi 未定义）→
  content 含字面 **'(cid:129)'** 11 字符标记——pdfminer 未映射
  回退原样落 content、零告警（静默损伤形态）

探针还证伪连字预设：WinAnsi 0xFB = 'û'（Latin-1 一致区），
连字 ﬁ 不在 WinAnsi 表内。

判别式：若高区标点被过滤/替换则 W1 码点断言翻红；若 NBSP
保留在词内则 W2 'a b' 全等断言翻红（对照 'a\\xa0b'）；若
(cid:N) 标记被清洗则 W3 全等断言翻红。
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tests.test_parser_pdf_image_numbering as numbering
from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

_WINANSI_FONT = (b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
                 b"/Encoding /WinAnsiEncoding >>")


@pytest.fixture
def winansi(monkeypatch):
    monkeypatch.setattr(numbering, "_FONT", _WINANSI_FONT)


def _parse(tmp_path: Path, text_bytes: bytes):
    p = tmp_path / "wa.pdf"
    p.write_bytes(numbering._pdf([
        b"BT /F1 12 Tf 72 700 Td (" + text_bytes + b") Tj ET"]))
    return FallbackParser().parse(p, compute_file_hash(p))


def test_high_zone_punctuation_passthrough(tmp_path, winansi):
    """W1：0x93/0x94/0x97 → '“hi” —'（U+201C/U+201D/U+2014）原样
    进 content，零告警。"""
    d = _parse(tmp_path, b"\x93hi\x94 \x97")
    assert len(d.elements) == 1
    assert d.elements[0].content == "“hi” —"
    assert [ord(c) for c in d.elements[0].content] == [
        0x201C, 0x68, 0x69, 0x201D, 0x20, 0x2014]
    assert d.warnings == []


def test_nbsp_normalized_to_ascii_space(tmp_path, winansi):
    """W2："a\\xa0b" → 'a b'（U+0020）——NBSP 当词分隔、空格连接
    重插，非保留在词内。"""
    d = _parse(tmp_path, b"a\xa0b")
    assert len(d.elements) == 1
    assert d.elements[0].content == "a b"
    assert 0xA0 not in [ord(c) for c in d.elements[0].content]
    assert d.warnings == []


def test_undefined_byte_cid_marker_passthrough(tmp_path, winansi):
    """W3：0x81（WinAnsi 未定义）→ content 含字面 '(cid:129)'
    标记、零告警——未映射字节的静默损伤形态。"""
    d = _parse(tmp_path, b"x\x81y")
    assert len(d.elements) == 1
    assert d.elements[0].content == "x(cid:129)y"
    assert d.warnings == []
