r"""pipeline max_chars 下限契约：
chunker_failed 错误与 32 边界（Round 1761）。

新角度：R1760 锁表格实体——**max_chars
< 32 在 pipeline 层不抛异常而是
(None, [ErrorRecord(code='chunker_failed',
message='分块失败: max_chars 过小: N',
details={'exception_type':
'ValueError'})])；恰 32 成功**零覆盖：

- **max_chars=0/31**：两形态同壳、
  message 带具体数值
- **max_chars=32**：正常 1 chunk
- **details 恰一键** exception_type
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _mk(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("x\n", encoding="utf-8")
    return p


def test_floor_rejected_as_chunker_failed(tmp_path):
    p = _mk(tmp_path)
    for mc in (0, 31):
        doc, errors = process_single(
            p, write_json=False, parser_name="markdown",
            max_chars=mc)
        assert doc is None, mc
        e = errors[0]
        assert e.code == "chunker_failed", mc
        assert e.message == (
            f"分块失败: max_chars 过小: {mc}"), mc
        assert e.details == {
            "exception_type": "ValueError"}, mc


def test_floor_boundary_32_succeeds(tmp_path):
    p = _mk(tmp_path)
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown",
        max_chars=32)
    assert errors == []
    assert len(doc.chunks) == 1
    assert doc.chunks[0].text == "x"
    assert doc.chunks[0].metadata["max_chars"] == 32
