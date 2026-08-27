"""BUG-html-1 / BUG-html-2 回归登记（提交 1：strict xfail 锁未来正确行为）。

BUG-html-1：td 内嵌 table 时，外层单元格文本静默丢失——输出只剩内层
表格内容，外层文本（REG_OUTER_TEXT 类）不进任何 element。现有警告
html_nested_table（"已忽略内层"）与实际行为（丢的是外层文本）不符。
修复目标（ADOPTION.md 回归语义）：外层文本与内层表格都保留，
顺序稳定不重复。

BUG-html-2：th 内 <img> 静默丢弃——无 image 元素、无警告，图片在
统一模型中消失。修复目标：图片按统一模型保留（image element +
resource_path）；模型不支持时必须显式诊断，不得静默消失。

按 ChatGPT 5.6 Sol 指示，xfail 写成"未来正确行为"断言（解析成功、
无静默丢失），不把当前缺陷行为固化为期望。修复在阶段 4 提交 2，
届时移除 xfail。
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


@pytest.mark.xfail(strict=True, reason="BUG-html-1: 外层单元格文本静默丢失，提交 2 修复")
@pytest.mark.parametrize("outer_prefix", ["REG_OUTER_TEXT", "前文"])
@pytest.mark.parametrize("inner", ["REG_INNER_TEXT", "内层内容"])
def test_bug_html1_nested_table_preserves_both(
    tmp_path: Path, outer_prefix: str, inner: str
):
    """外层文本与内层表格都保留；顺序稳定；不重复。"""
    html = (
        "<table><tr><td>"
        f"{outer_prefix}<table><tr><td>{inner}</td></tr></table>"
        "</td></tr></table>"
    )
    doc = _parse(html, tmp_path)
    joined = "\n".join(_texts(doc))
    assert outer_prefix in joined, "外层文本不得静默丢失"
    assert inner in joined, "内层表格内容不得丢失"
    # 不重复：外层文本只出现一次
    assert joined.count(outer_prefix) == 1
    validate(doc.to_dict())


@pytest.mark.xfail(strict=True, reason="BUG-html-1: 外层文本静默丢失，提交 2 修复")
def test_bug_html1_outer_order_before_inner(tmp_path: Path):
    """外层文本出现在内层表格内容之前（顺序稳定）。"""
    html = (
        "<table><tr><td>OUTER_MARK"
        "<table><tr><td>INNER_MARK</td></tr></table>"
        "</td></tr></table>"
    )
    doc = _parse(html, tmp_path)
    joined = "\n".join(_texts(doc))
    assert joined.index("OUTER_MARK") < joined.index("INNER_MARK")


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
    """REG fixture 存在且可读（缺陷行为本身由上面 xfail 用例锁定）。"""
    p = REG_DIR / fixture
    if not p.is_file():
        pytest.skip("samples/private 为本机资产，不存在时跳过")
    doc = HtmlParser().parse(p, source_hash="d" * 64)
    validate(doc.to_dict())
