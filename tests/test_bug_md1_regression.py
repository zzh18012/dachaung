"""BUG-md-1 回归测试（提交 2 修复后：无 xfail，全参数化矩阵）。

缺陷：markdown 标记（ATX 标题 / 无序 / 有序列表）后跟 ≥2 个尾随空白且无内容
时，正则回溯让 group 捕获到单个空白，strip 后为空，push 出空 content 的
Element，触发 Element.__post_init__ 的 ValueError；经 pipeline 包装为
unexpected_parser_error（显式崩溃，非静默）。

修复语义（2026-08-27 与 ChatGPT 5.6 Sol 确认）：
合法但空的标记行 → 忽略该行（不发空节点、不发空 chunk、不发空文本段落），
不崩溃；该行仍中断段落吸收（块级边界）；记 empty_markdown_construct_ignored
警告（用现有 warnings 通道，不扩 schema）。

矩阵：标记类型（#/-/*/+/1./1)） × 尾随空白（2/3/4 空格、空格+tab、tab+空格、
双 tab） × 有/无末尾换行 × LF/CRLF × 单独/夹心（空行隔开）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.parsers.markdown_parser import MarkdownParser
from app.schema import validate

MARKERS = ["#", "-", "*", "+", "1.", "1)"]
TRAILING_WS = ["  ", "   ", "    ", " \t", "\t ", "\t\t"]


def _parse(tmp_path: Path, content: str, *, eol: str = "\n"):
    p = tmp_path / "case.md"
    p.write_bytes(content.encode("utf-8"))
    return MarkdownParser().parse(p, source_hash="a" * 64)


def _case(marker: str, ws: str, *, eof_newline: bool, crlf: bool, sandwich: bool) -> str:
    nl = "\r\n" if crlf else "\n"
    empty_line = marker + ws
    if sandwich:
        body = f"前段 MARKER_BEFORE{nl}{nl}{empty_line}{nl}{nl}后段 MARKER_AFTER{nl}"
    else:
        body = f"{empty_line}{nl}正文 MARKER_AFTER{nl}"
    if not eof_newline:
        body = body.rstrip("\r\n")
        # 无末尾换行时至少保证空标记行本身完整（EOF 直接落在正文后）
        body += ""
    return body


@pytest.mark.parametrize("marker", MARKERS)
@pytest.mark.parametrize("ws", TRAILING_WS)
@pytest.mark.parametrize("eof_newline", [True, False])
@pytest.mark.parametrize("crlf", [True, False])
@pytest.mark.parametrize("sandwich", [True, False])
def test_empty_marker_ignored_no_crash(
    tmp_path: Path, marker: str, ws: str, eof_newline: bool, crlf: bool, sandwich: bool
):
    content = _case(marker, ws, eof_newline=eof_newline, crlf=crlf, sandwich=sandwich)
    doc = _parse(tmp_path, content)

    # 1) 不崩溃；2) 无空节点 / 空文本段落
    for e in doc.elements:
        assert e.content or e.resource_path, f"empty element: {e.element_id}"
        if e.content is not None:
            assert e.content.strip(), f"whitespace-only content: {e.element_id}"

    # 3) 空标记行未以字面形式混入任何元素内容
    empty_marker = marker + ws
    for e in doc.elements:
        if e.content:
            assert empty_marker not in e.content, e.content[:40]

    # 4) 周围内容不受影响
    joined = "\n".join(e.content or "" for e in doc.elements)
    assert "MARKER_AFTER" in joined
    if sandwich:
        assert "MARKER_BEFORE" in joined

    # 5) 警告通道：记 empty_markdown_construct_ignored
    assert any(w.code == "empty_markdown_construct_ignored" for w in doc.warnings)

    # 6) 输出仍通过 UDM schema 校验（markdown → 0.2.0 快照）
    validate(doc.to_dict())


@pytest.mark.parametrize(
    "marker,ws", [("#", "  "), ("-", "  "), ("*", "   "), ("+", "    "),
                  ("1.", " \t"), ("1)", "\t ")]
)
def test_sandwich_invariance(tmp_path: Path, marker: str, ws: str):
    """夹心场景（空行隔开）：加入空标记行前后，元素序列完全不变。"""
    def elements_of(content: str):
        doc = _parse(tmp_path, content)
        return [(e.type, e.content) for e in doc.elements]

    empty_line = marker + ws
    with_marker = elements_of(f"前段\n\n{empty_line}\n\n后段\n")
    without_marker = elements_of("前段\n\n后段\n")
    assert with_marker == without_marker


def test_standalone_empty_marker_no_elements_leftover(tmp_path: Path):
    """整文件只有空标记行：无元素 + md_no_content 警告（既有通道）。"""
    doc = _parse(tmp_path, "-  \n")
    assert doc.elements == []
    codes = {w.code for w in doc.warnings}
    assert "empty_markdown_construct_ignored" in codes
    assert "md_no_content" in codes


def test_warning_details_carry_line_and_construct(tmp_path: Path):
    doc = _parse(tmp_path, "# 正常\n\n##  \n\n正文\n")
    hits = [w for w in doc.warnings if w.code == "empty_markdown_construct_ignored"]
    assert len(hits) == 1
    assert hits[0].details["line"] == 3
    assert hits[0].details["construct"] == "atx_heading"


def test_section_path_not_polluted_by_empty_heading(tmp_path: Path):
    """空标题不进 section_path：后续元素的 section_path 不含空标题。"""
    doc = _parse(tmp_path, "# 一级\n\n##  \n\n正文\n")
    para = [e for e in doc.elements if e.type == "paragraph"][0]
    assert para.source_locator.get("section_path") == "一级"


def test_empty_marker_still_interrupts_paragraph(tmp_path: Path):
    """空标记行仍是块级边界：紧邻段落在此断开（修复语义的一部分）。"""
    doc = _parse(tmp_path, "前段文字\n-  \n后段文字\n")
    paras = [e.content for e in doc.elements if e.type == "paragraph"]
    assert paras == ["前段文字", "后段文字"]


def test_non_crashing_neighbours_still_fine(tmp_path: Path):
    """单空格/tab/正常内容不受影响（防止修复误伤）。"""
    doc = _parse(tmp_path, "# \n-\t\n正文 MARKER_OK\n")
    assert any("MARKER_OK" in (e.content or "") for e in doc.elements)


def test_regression_fixture_parses(tmp_path: Path):
    """REG-MD-001 fixture：修复后不再 unexpected_parser_error，周围内容保留。"""
    src = Path("samples/private/devset-regressions/md-empty-marker-crash.md")
    if not src.is_file():
        pytest.skip("samples/private 为本机资产，不存在时跳过")
    doc = MarkdownParser().parse(src, source_hash="b" * 64)
    joined = "\n".join(e.content or "" for e in doc.elements)
    for marker in ("正常标题", "尾部正常", "REG_MD_AROUND"):
        assert marker in joined
    headings = [e for e in doc.elements if e.type == "heading"]
    assert len(headings) == 2  # ##（空）被忽略后：# 正常标题 + ### 末级正常
    validate(doc.to_dict())
