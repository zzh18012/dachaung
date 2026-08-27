"""BUG-md-1 回归登记（严格 xfail，MD 提交 2 修复后必须移除 xfail 标记）。

缺陷：markdown 标记（ATX 标题 / 无序 / 有序列表）后跟 ≥2 个尾随空白且无内容
时，正则回溯让 group 捕获到单个空白，strip 后为空，push 出空 content 的
Element，触发 Element.__post_init__ 的 ValueError；经 pipeline 包装为
unexpected_parser_error（显式崩溃，非静默）。

修复语义（2026-08-27 与 ChatGPT 5.6 Sol 确认）：
合法但空的标记行 → 忽略该行（不发空节点、不发空 chunk、不发空文本段落），
不崩溃；有警告通道时记 empty_markdown_construct_ignored（不扩 schema）。

本文件在提交 1（机械搬运）阶段以 strict xfail 锁定崩溃现状；
提交 2 修复后：去掉 xfail、扩充参数化矩阵（标记类型 × 空格数 × tab ×
EOF/末尾换行 × LF/CRLF × 单独/夹心）。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.parsers.markdown_parser import MarkdownParser


def _parse(tmp_path: Path, content: str):
    p = tmp_path / "case.md"
    p.write_text(content, encoding="utf-8")
    return MarkdownParser().parse(p, source_hash="a" * 64)


@pytest.mark.xfail(strict=True, reason="BUG-md-1: 空 markdown 标记行触发 ValueError")
def test_bug_md1_unordered_dash_two_spaces_crashes(tmp_path: Path):
    doc = _parse(tmp_path, "-  \n正文\n")
    assert all(e.content or e.resource_path for e in doc.elements)


@pytest.mark.xfail(strict=True, reason="BUG-md-1: 空 markdown 标记行触发 ValueError")
def test_bug_md1_atx_hash_two_spaces_crashes(tmp_path: Path):
    doc = _parse(tmp_path, "#  \n正文\n")
    assert all(e.content or e.resource_path for e in doc.elements)


@pytest.mark.xfail(strict=True, reason="BUG-md-1: 空 markdown 标记行触发 ValueError")
def test_bug_md1_unordered_star_three_spaces_crashes(tmp_path: Path):
    doc = _parse(tmp_path, "*   \n正文\n")
    assert all(e.content or e.resource_path for e in doc.elements)


@pytest.mark.xfail(strict=True, reason="BUG-md-1: 空 markdown 标记行触发 ValueError")
def test_bug_md1_sandwiched_empty_marker_crashes(tmp_path: Path):
    doc = _parse(tmp_path, "前段\n\n-  \n\n后段\n")
    assert all(e.content or e.resource_path for e in doc.elements)


def test_non_crashing_neighbours_still_fine(tmp_path: Path):
    """单空格/tab/正常内容不受影响（现状即正确，防止修复时误伤）。"""
    doc = _parse(tmp_path, "# \n-\t\n正文 MARKER_OK\n")
    assert any("MARKER_OK" in (e.content or "") for e in doc.elements)
