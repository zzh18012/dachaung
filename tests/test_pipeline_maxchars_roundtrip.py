r"""app/pipeline max_chars 边界与回环测试（Round 1549）。

新角度：max_chars 无效值在 pipeline 层此前只断言"不
崩"（test_pipeline_edges.py 仅 isinstance）——本轮锁
**精确错误**与**阈值边界**（StructuralChunker 要求
max_chars >= 32）：

- **max_chars ∈ {0, 1, -5, 10, 31}** → doc=None + 单条
  chunker_failed（message 'max_chars 过小: {n}'、
  details.exception_type='ValueError'）
- **边界 32 正好可用** → 正常分块、所有 chunk ≤32、
  ids 非空
- **写盘→validate_only 回环** → process_single 写出
  JSON 后 validate_only 返回 (True, 'OK')
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.pipeline import process_single, \
    validate_only

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")
_WORDS = " ".join(
    f"word{i}" for i in range(50))
_C = (f"BT /F1 12 Tf 72 700 Td"
      f" ({_WORDS}) Tj ET")


def _pdf(tmp_path: Path) -> Path:
    objs = [
        "<< /Type /Catalog"
        " /Pages 2 0 R >>",
        "<< /Type /Pages"
        " /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page"
        " /Parent 2 0 R"
        " /MediaBox [0 0 612 792]"
        " /Resources << /Font"
        " << /F1 5 0 R >> >>"
        " /Contents 4 0 R >>",
        f"<< /Length {len(_C)} >>"
        f"\nstream\n{_C}\n"
        f"endstream",
        _FONT,
    ]
    pdf = b"%PDF-1.4\n"
    for i, o in enumerate(objs):
        pdf += (f"{i + 1} 0 obj\n{o}"
                f"\nendobj\n"
                ).encode("latin-1")
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 6 >>\n%%EOF")
    p = tmp_path / "doc.pdf"
    p.write_bytes(pdf)
    return p


@pytest.mark.parametrize(
    "mc", [0, 1, -5, 10, 31])
def test_max_chars_too_small(
        tmp_path, mc):
    doc, errors = process_single(
        _pdf(tmp_path),
        write_json=False,
        max_chars=mc)
    assert doc is None
    assert len(errors) == 1
    e = errors[0]
    assert e.code == "chunker_failed"
    assert f"max_chars 过小: {mc}" \
        in e.message
    assert e.details[
        "exception_type"] == \
        "ValueError"


def test_max_chars_boundary_32(
        tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path),
        write_json=False,
        max_chars=32)
    assert errors == []
    assert doc.chunks
    assert all(
        len(c.text) <= 32
        for c in doc.chunks)
    assert all(
        c.source_element_ids
        for c in doc.chunks)


def test_write_then_validate_roundtrip(
        tmp_path):
    out = tmp_path / "out.json"
    doc, errors = process_single(
        _pdf(tmp_path), out,
        write_json=True)
    assert errors == []
    assert out.exists()
    ok, msg = validate_only(out)
    assert ok is True
    assert msg == "OK"
