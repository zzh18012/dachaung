r"""app/parsers_fallback PDF 边角测试 - 第一百轮（Round 1530）。

新角度（probe 实证）垃圾/截断 PDF 家族（此前仅
evaluation 层有一个 broken 样例，parser 层零覆盖）：

- **纯文本字节** → ParserError 'No /Root object!'
- **错误魔数 %PSD** → ParserError 'No /Root object!'
  （魔数不校验，只看结构）
- **仅头 + EOF** → ParserError 'No /Root object!'
- **空文件** → ParserError 'No /Root object!'
- **有效 PDF 从中截断** → ParserError 'Unexpected EOF'
  （截断位置在流内 → 与无 Root 不同的底层错误）
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.base import ParserError
from app.parsers.fallback_parser import \
    FallbackParser

from tests.test_parsers_fallback_edges66 \
    import _pdf


def _raises(tmp_path, name, data,
            needle):
    p = tmp_path / name
    p.write_bytes(data)
    with pytest.raises(ParserError) as ei:
        FallbackParser().parse(
            p, compute_file_hash(p))
    assert "pdfplumber 打开/解析" \
        " PDF 失败" in str(ei.value)
    assert needle in str(ei.value)


def test_plain_text_bytes(tmp_path):
    _raises(
        tmp_path, "garbage.pdf",
        b"this is not a pdf at"
        b" all, just plain text"
        b" bytes",
        "No /Root object!")


def test_wrong_magic(tmp_path):
    _raises(
        tmp_path, "wrongmagic.pdf",
        b"%PSD-Adobe fake\n%%EOF",
        "No /Root object!")


def test_header_only(tmp_path):
    _raises(
        tmp_path, "headeronly.pdf",
        b"%PDF-1.4\n%%EOF",
        "No /Root object!")


def test_empty_file(tmp_path):
    _raises(
        tmp_path, "empty.pdf", b"",
        "No /Root object!")


def test_truncated_mid_stream(
        tmp_path):
    full = _pdf(
        tmp_path, "ok.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (BODY) Tj ET"
    ).read_bytes()
    _raises(
        tmp_path, "trunc.pdf",
        full[:len(full) // 2],
        "Unexpected EOF")
