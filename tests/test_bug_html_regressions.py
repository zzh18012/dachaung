"""BUG-html-1 / BUG-html-2 回归（提交 2a 后：BUG-html-1 已修，BUG-html-2 仍 xfail）。

BUG-html-1（已修，2026-08-27 提交 2a）：td 内嵌 table 时外层单元格文本
静默丢失。修复语义（ChatGPT 5.6 Sol 确认）：外层单元格直接文本在嵌套点
前/后各保留为一个 paragraph；内层 table 独立解析一次，不折叠进外层；
每段文本恰好出现一次；table 计数精确；顺序 前文本→内层→后文本 可追踪。

BUG-html-2（xfail，提交 2b 修复）：th 内 <img> 静默丢弃——无 image 元素、
无警告。修复目标：复用现有 body/td 图片路径，恰好一个 image element，
不重复计入，缺 src/alt 沿用现有诊断政策。

按 ChatGPT 5.6 Sol 指示，xfail 写成"未来正确行为"断言（解析成功、
无静默丢失），不把当前缺陷行为固化为期望。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.parsers.html_parser import HtmlParser
from app.schema import validate

REG_DIR = Path("samples/private/devset-regressions")


def _parse(content: str, tmp_path: Path) -> object:
    p = tmp_path / "case.html"
    p.write_text(content, encoding="utf-8")
    return HtmlParser().parse(p, source_hash="c" * 64)


def _texts(doc: object) -> list[str]:
    return [e.content for e in doc.elements if e.content]


@pytest.mark.parametrize("outer_prefix", ["REG_OUTER_TEXT", "前文"])
@pytest.mark.parametrize("inner", ["REG_INNER_TEXT", "内层内容"])
def test_bug_html1_nested_table_preserves_both(
    tmp_path: Path, outer_prefix: str, inner: str
):
    """外层文本与内层表格都保留；恰好各出现一次；table 计数精确。"""
    html = (
        "<table><tr><td>"
        f"{outer_prefix}<table><tr><td>{inner}</td></tr></table>"
        "</td></tr></table>"
    )
    doc = _parse(html, tmp_path)
    joined = "\n".join(_texts(doc))
    assert outer_prefix in joined, "外层文本不得静默丢失"
    assert inner in joined, "内层表格内容不得丢失"
    # 精确出现次数：各恰好一次（防"修复丢失但引入重复"）
    assert joined.count(outer_prefix) == 1
    assert joined.count(inner) == 1
    # 精确 table 计数：内层 + 外层 = 2
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 2
    assert inner in tables[0].content and outer_prefix not in tables[0].content
    assert outer_prefix not in tables[1].content, "内层文本不得折叠进外层单元格"
    # 外层直接文本以独立 paragraph 保留
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert [p.content for p in paras] == [outer_prefix]
    # 警告通道
    assert sum(1 for w in doc.warnings if w.code == "html_nested_table") == 1
    validate(doc.to_dict())


def test_bug_html1_outer_order_before_inner(tmp_path: Path):
    """前文本 → 内层表格 → 后文本：元素顺序与来源顺序一致。"""
    html = (
        "<table><tr><td>OUTER_MARK"
        "<table><tr><td>INNER_MARK</td></tr></table>"
        "POST_MARK</td></tr></table>"
    )
    doc = _parse(html, tmp_path)
    seq = [(e.type, e.content) for e in doc.elements]
    assert seq == [
        ("paragraph", "OUTER_MARK"),
        ("table", "| INNER_MARK |\n| --- |"),
        ("paragraph", "POST_MARK"),
        ("table", "|  |\n| --- |"),
    ]


def test_bug_html1_deep_nesting_each_once(tmp_path: Path):
    """三层嵌套：每层文本恰好一次，table 计数 = 3，逐层警告。"""
    html = (
        "<table><tr><td>L1"
        "<table><tr><td>L2"
        "<table><tr><td>L3</td></tr></table>"
        "</td></tr></table>"
        "</td></tr></table>"
    )
    doc = _parse(html, tmp_path)
    joined = "\n".join(_texts(doc))
    for mark in ("L1", "L2", "L3"):
        assert joined.count(mark) == 1
    assert sum(1 for e in doc.elements if e.type == "table") == 3
    assert sum(1 for w in doc.warnings if w.code == "html_nested_table") == 2
    validate(doc.to_dict())


def test_bug_html1_sibling_cell_not_affected(tmp_path: Path):
    """同 row 的未嵌套 cell 仍按普通单元格并入外层表格。"""
    html = (
        "<table><tr>"
        "<td>NESTED_PRE<table><tr><td>IN</td></tr></table></td>"
        "<td>PLAIN_SIBLING</td>"
        "</tr></table>"
    )
    doc = _parse(html, tmp_path)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 2
    assert "PLAIN_SIBLING" in tables[1].content
    assert "PLAIN_SIBLING" not in tables[0].content
    joined = "\n".join(_texts(doc))
    assert joined.count("PLAIN_SIBLING") == 1


@pytest.mark.xfail(strict=True, reason="BUG-html-2: th 内 img 静默丢弃，提交 2 修复")
@pytest.mark.parametrize("alt", ["REG_TH_IMG_ALT", ""])
@pytest.mark.parametrize("neighbour_th", ["REG_TH_TEXT", ""])
def test_bug_html2_th_img_preserved(
    tmp_path: Path, alt: str, neighbour_th: str
):
    """th 内 img → image element（resource_path 保留）；alt 可空。"""
    html = (
        "<table><tr>"
        f"<th><img src='fixture-image.png' alt='{alt}'></th>"
        f"<th>{neighbour_th}</th>"
        "</tr></table>"
    )
    doc = _parse(html, tmp_path)
    imgs = [e for e in doc.elements if e.type == "image"]
    assert imgs, "th 内图片不得静默消失"
    assert imgs[0].resource_path == "fixture-image.png"
    if alt:
        assert imgs[0].metadata.get("alt") == alt
    if neighbour_th:
        assert neighbour_th in "\n".join(_texts(doc))
    validate(doc.to_dict())


@pytest.mark.xfail(strict=True, reason="BUG-html-2: th 内 img 静默丢弃，提交 2 修复")
def test_bug_html2_no_silent_drop_either_element_or_diagnostic(tmp_path: Path):
    """最低语义：图片要么保留为 image，要么有显式诊断；两者皆无 = 静默丢失。"""
    html = "<table><tr><th><img src='x.png'></th></tr></table>"
    doc = _parse(html, tmp_path)
    has_image = any(e.type == "image" for e in doc.elements)
    has_diagnostic = any("img" in w.code.lower() or "image" in w.code.lower()
                         for w in doc.warnings)
    assert has_image or has_diagnostic, "不得既无 image 元素又无任何诊断"


def test_non_nested_table_unchanged(tmp_path: Path):
    """邻域不回归：普通表格（无嵌套、无 img）行为不变。"""
    doc = _parse(
        "<table><tr><th>H</th></tr><tr><td>REG_PLAIN_CELL</td></tr></table>",
        tmp_path,
    )
    assert "REG_PLAIN_CELL" in "\n".join(_texts(doc))
    assert [(e.type, e.resource_path) for e in doc.elements] == [("table", None)]
    assert doc.warnings == []


@pytest.mark.parametrize("fixture", ["html-nested-table-loss.html", "html-th-img-drop.html"])
def test_regression_fixture_current_state(tmp_path: Path, fixture: str):
    """REG fixture 存在且可读（BUG-html-1 已修，BUG-html-2 由 xfail 用例锁定）。"""
    p = REG_DIR / fixture
    if not p.is_file():
        pytest.skip("samples/private 为本机资产，不存在时跳过")
    doc = HtmlParser().parse(p, source_hash="d" * 64)
    validate(doc.to_dict())


def test_regression_fixture_html1_fixed(tmp_path: Path):
    """REG-HTML-001 fixture：外层文本保留恰好一次，table 数 = 2。"""
    p = REG_DIR / "html-nested-table-loss.html"
    if not p.is_file():
        pytest.skip("samples/private 为本机资产，不存在时跳过")
    doc = HtmlParser().parse(p, source_hash="e" * 64)
    joined = "\n".join(_texts(doc))
    assert joined.count("REG_OUTER_TEXT") == 1
    assert joined.count("REG_INNER_TEXT") == 1
    assert sum(1 for e in doc.elements if e.type == "table") == 2
    validate(doc.to_dict())
