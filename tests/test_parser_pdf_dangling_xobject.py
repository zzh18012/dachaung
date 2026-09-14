r"""PDF 悬空 XObject 引用静默跳过锁定（Round 1939，a 优先级）。

edges35/105 锁未定义**字体** /F9（文本仍提取）；**未注册
XObject 的 Do** 与 **Resources 有名但对象号悬空**零覆盖。
探针 R1939 实证（两形态同归：无 image 元素、文本完好、
零告警——图片静默丢失无痕迹）：

- **G1 未注册名**：Do /Im9（/Im9 不在 Resources）→ 悬空 Do
  前后文本照常两元素、无图、零告警
- **G2 q/Q 包裹**：悬空 Do 为页面唯一图像操作 → 文本独存、
  q/Q 不受影响
- **G3 对象号悬空**：Resources 有 /Im1 但指向不存在的
  99 0 R（对象缺失）→ 同归静默跳过

判别式：若悬空 Do 升级为告警则零告警断言翻红；若未注册名
导致整页解析失败则文本元素数断言翻红。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf


def _parse(tmp_path: Path, content: bytes, patch: tuple[bytes, bytes] | None = None):
    raw = _pdf([content])
    if patch:
        old, new = patch
        assert old in raw
        raw = raw.replace(old, new)
    p = tmp_path / "d.pdf"
    p.write_bytes(raw)
    return FallbackParser().parse(p, compute_file_hash(p))


def test_unregistered_name_do_silent(tmp_path):
    """G1：Do /Im9（未注册）→ 两文本元素、无图、零告警。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf 72 700 Td (Text around) Tj ET\n"
               b"q 100 0 0 100 450 600 cm /Im9 Do Q\n"
               b"BT /F1 12 Tf 72 600 Td (after) Tj ET")
    assert [e.type for e in d.elements] == ["heading", "heading"]
    assert [e.content for e in d.elements] == ["Text around", "after"]
    assert d.warnings == []


def test_dangling_do_in_qq_only_image(tmp_path):
    """G2：悬空 Do 为唯一图像操作（q/Q 包裹）→ 文本独存、
    无图、零告警。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf 72 700 Td (only text) Tj ET\n"
               b"q 100 0 0 100 450 600 cm /Im9 Do Q")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "only text"
    assert d.warnings == []


def test_named_but_missing_object_silent(tmp_path):
    """G3：Resources 有 /Im1 但指向不存在的 99 0 R →
    文本完好、无图、零告警。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf 72 700 Td (host text) Tj ET\n"
               b"q 100 0 0 100 450 600 cm /Im1 Do Q",
               patch=(b"/Im1 5 0 R", b"/Im1 99 0 R"))
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "host text"
    assert d.warnings == []
