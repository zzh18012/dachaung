"""BUG-html-1 / BUG-html-2 回归（提交 2a/2b 后：均已修复，无 xfail）。

BUG-html-1（已修，提交 2a）：td 内嵌 table 时外层单元格文本静默丢失。
修复语义（ChatGPT 5.6 Sol 确认）：外层单元格直接文本在嵌套点前/后
各保留为一个 paragraph；内层 table 独立解析一次，不折叠进外层；
每段文本恰好出现一次；table 计数精确；顺序 前文本→内层→后文本 可追踪。

BUG-html-2（已修，提交 2b）：th 内 <img> 静默丢弃——无 image 元素、
无警告。修复语义：复用现有 body/td 图片路径（image element +
resource_path + metadata.alt），恰好一个 image element，不与单元格
文本重复计入，缺 src 沿用现有诊断政策（跳过）。
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


@pytest.mark.parametrize("alt", ["REG_TH_IMG_ALT", ""])
@pytest.mark.parametrize("neighbour_th", ["REG_TH_TEXT", ""])
def test_bug_html2_th_img_preserved(
    tmp_path: Path, alt: str, neighbour_th: str
):
    """th 内 img → 恰好一个 image element（resource_path 保留）；alt 可空。"""
    html = (
        "<table><tr>"
        f"<th><img src='fixture-image.png' alt='{alt}'></th>"
        f"<th>{neighbour_th}</th>"
        "</tr></table>"
    )
    doc = _parse(html, tmp_path)
    imgs = [e for e in doc.elements if e.type == "image"]
    assert len(imgs) == 1, "恰好一个 image element，不重复计入"
    assert imgs[0].resource_path == "fixture-image.png"
    if alt:
        assert imgs[0].metadata.get("alt") == alt
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    if neighbour_th:
        joined = "\n".join(_texts(doc))
        assert neighbour_th in joined
        # 表头文本不因图片重复计入
        assert joined.count(neighbour_th) == 1
    validate(doc.to_dict())


def test_bug_html2_no_silent_drop_either_element_or_diagnostic(tmp_path: Path):
    """最低语义：图片要么保留为 image，要么有显式诊断；两者皆无 = 静默丢失。"""
    html = "<table><tr><th><img src='x.png'></th></tr></table>"
    doc = _parse(html, tmp_path)
    has_image = any(e.type == "image" for e in doc.elements)
    has_diagnostic = any("img" in w.code.lower() or "image" in w.code.lower()
                         for w in doc.warnings)
    assert has_image or has_diagnostic, "不得既无 image 元素又无任何诊断"


def test_bug_html2_td_img_same_path_as_th(tmp_path: Path):
    """td 与 th 走同一图片路径：行为一致，各恰好一个 image。"""
    for cell_tag in ("td", "th"):
        html = f"<table><tr><{cell_tag}><img src='c.png'></{cell_tag}></tr></table>"
        doc = _parse(html, tmp_path)
        imgs = [e for e in doc.elements if e.type == "image"]
        assert len(imgs) == 1 and imgs[0].resource_path == "c.png", cell_tag
        validate(doc.to_dict())


def test_bug_html2_missing_src_follows_existing_policy(tmp_path: Path):
    """缺 src 沿用既有诊断政策：跳过（与 body 内缺 src img 一致）。"""
    doc = _parse("<table><tr><th><img alt='no-src'></th></tr></table>", tmp_path)
    assert not any(e.type == "image" for e in doc.elements)
    body = _parse("<p><img alt='no-src'></p>", tmp_path)
    assert not any(e.type == "image" for e in body.elements)


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
    """REG fixture 存在且可读（两个缺陷均已修复）。"""
    p = REG_DIR / fixture
    if not p.is_file():
        pytest.skip("samples/private 为本机资产，不存在时跳过")
    doc = HtmlParser().parse(p, source_hash="d" * 64)
    validate(doc.to_dict())


def test_regression_fixture_html2_fixed(tmp_path: Path):
    """REG-HTML-002 fixture：恰好一个 image（BUG-html-2 门），表头文本保留。"""
    p = REG_DIR / "html-th-img-drop.html"
    if not p.is_file():
        pytest.skip("samples/private 为本机资产，不存在时跳过")
    doc = HtmlParser().parse(p, source_hash="f" * 64)
    imgs = [e for e in doc.elements if e.type == "image"]
    assert len(imgs) == 1
    assert imgs[0].resource_path == "fixture-image.png"
    assert imgs[0].metadata.get("alt") == "REG_TH_IMG_ALT"
    joined = "\n".join(_texts(doc))
    assert joined.count("REG_TH_TEXT") == 1
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


# ---------- 结构归属（ChatGPT 5.6 Sol 2026-08-27 核对点①） ----------
# paragraph 不只"文本出现一次"，还必须能通过 metadata 回溯到原外层
# 单元格：{origin, table_start_line, row_index, cell_index, position}。


def test_bug_html1_cell_text_attribution_to_outer_cell(tmp_path: Path):
    """前/后文本段的 metadata 精确指向原 cell；table_start_line 与外层
    table element 的 locator.line 一致（同一坐标系的互证）。"""
    html = (
        "<table><tr><td>OUTER_MARK"
        "<table><tr><td>INNER_MARK</td></tr></table>"
        "POST_MARK</td></tr></table>"
    )
    doc = _parse(html, tmp_path)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    outer_tables = [e for e in doc.elements if e.type == "table"
                    and "INNER_MARK" not in (e.content or "")]
    assert len(paras) == 2 and len(outer_tables) == 1
    outer_line = outer_tables[0].source_locator["line"]

    before, after = paras
    assert before.content == "OUTER_MARK"
    assert after.content == "POST_MARK"
    for para, position in ((before, "before_inner_table"),
                           (after, "after_inner_table")):
        meta = para.metadata
        assert meta["origin"] == "table_cell_text"
        assert meta["position"] == position
        assert meta["row_index"] == 0
        assert meta["cell_index"] == 0
        # 与外层 table element 的 locator.line 同源，可互相关联
        assert meta["table_start_line"] == outer_line
    validate(doc.to_dict())


def test_bug_html1_attribution_row_and_cell_indices(tmp_path: Path):
    """多行多列：row_index/cell_index 精确到发生嵌套的那个 cell。"""
    html = (
        "<table>"
        "<tr><td>KEEP_A</td><td>NEST_R0C1<table><tr><td>IN1</td></tr></table></td></tr>"
        "<tr><td>NEST_R1C0<table><tr><td>IN2</td></tr></table></td><td>KEEP_D</td></tr>"
        "</table>"
    )
    doc = _parse(html, tmp_path)
    attr = {e.content: e.metadata for e in doc.elements
            if e.type == "paragraph" and e.metadata.get("origin")}
    assert set(attr) == {"NEST_R0C1", "NEST_R1C0"}
    assert attr["NEST_R0C1"]["row_index"] == 0
    assert attr["NEST_R0C1"]["cell_index"] == 1
    assert attr["NEST_R1C0"]["row_index"] == 1
    assert attr["NEST_R1C0"]["cell_index"] == 0
    # 未嵌套 cell 正常并入外层表格，不产生归属段
    joined = "\n".join(_texts(doc))
    assert joined.count("KEEP_A") == 1 and joined.count("KEEP_D") == 1
    validate(doc.to_dict())


def test_bug_html1_deep_nesting_immediate_outer_attribution(tmp_path: Path):
    """三层嵌套：L2 段归属中间层 table，L1 段归属最外层 table（各table
    起始行不同，可区分）。"""
    html = (
        "<table><tr><td>L1\n"
        "<table><tr><td>L2\n"
        "<table><tr><td>L3</td></tr></table>\n"
        "</td></tr></table>\n"
        "</td></tr></table>\n"
    )
    doc = _parse(html, tmp_path)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 3  # 产出顺序：L3 内层 → L2 中间 → L1 外层
    line_l3 = tables[0].source_locator["line"]
    line_l2 = tables[1].source_locator["line"]
    line_l1 = tables[2].source_locator["line"]
    assert len({line_l1, line_l2, line_l3}) == 3

    attr = [e for e in doc.elements
            if e.type == "paragraph" and e.metadata.get("origin")]
    assert [p.content for p in attr] == ["L1", "L2"]
    by_content = {p.content: p for p in attr}
    assert by_content["L2"].metadata["table_start_line"] == line_l2, \
        "L2 段应归属中间层（直接外层）table"
    assert by_content["L2"].metadata["position"] == "before_inner_table"
    assert by_content["L1"].metadata["table_start_line"] == line_l1, \
        "L1 段应归属最外层 table"
    validate(doc.to_dict())


def test_bug_html1_body_paragraph_not_mislabeled(tmp_path: Path):
    """邻域不回归：普通 body 段落不带 cell 归属 metadata（可区分两类段）。"""
    html = (
        "<p>BODY_PARA</p>"
        "<table><tr><td>CELL_PARA<table><tr><td>IN</td></tr></table></td></tr></table>"
    )
    doc = _parse(html, tmp_path)
    paras = {e.content: e for e in doc.elements if e.type == "paragraph"}
    assert set(paras) == {"BODY_PARA", "CELL_PARA"}
    assert "origin" not in paras["BODY_PARA"].metadata
    assert paras["CELL_PARA"].metadata["origin"] == "table_cell_text"
    validate(doc.to_dict())


# ---------- table_index 唯一 join key（ChatGPT 5.6 Sol 2026-08-27 边界①） ----------
# 单行 HTML 中多个 table 的起始行、行列索引都可能相同，坐标不能单独
# 作身份；归属必须经 table_index 唯一解析到直接外层 table 元素。


def test_bug_html1_same_line_deep_nesting_unique_join(tmp_path: Path):
    """同一行三层嵌套：三个 table 起始行相同，table_index 互异；
    每个归属段经 table_index 唯一解析到直接外层（非首个同起始行匹配）。"""
    html = (
        "<table><tr><td>L1"
        "<table><tr><td>L2"
        "<table><tr><td>L3</td></tr></table>"
        "</td></tr></table>"
        "</td></tr></table>"
    )
    doc = _parse(html, tmp_path)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 3
    # 全部同一起始行（碰撞前提）
    assert len({t.source_locator["line"] for t in tables}) == 1
    idx = [t.metadata["table_index"] for t in tables]
    assert len(set(idx)) == 3, "table_index 必须全文档唯一"

    def resolve(table_index: int) -> list:
        return [t for t in tables if t.metadata["table_index"] == table_index]

    attr = {e.content: e for e in doc.elements
            if e.type == "paragraph" and e.metadata.get("origin")}
    assert set(attr) == {"L1", "L2"}
    for content, expect_depth in (("L2", 1), ("L1", 2)):
        ti = attr[content].metadata["table_index"]
        matches = resolve(ti)
        assert len(matches) == 1, "join key 必须唯一解析到一个 table"
        # tables 产出顺序：内层在前（L3→L2→L1），直接外层即对应深度
        assert matches[0] is tables[expect_depth], content
    validate(doc.to_dict())


def test_bug_html1_same_line_multiple_outer_tables(tmp_path: Path):
    """同一行两个并列外层表格各自嵌套：坐标完全同形（起始行/行列均同），
    归属经 table_index 区分并各自指向自己的直接外层。"""
    html = (
        "<table><tr><td>NEST_A<table><tr><td>IN_A</td></tr></table></td></tr></table>"
        "<table><tr><td>NEST_B<table><tr><td>IN_B</td></tr></table></td></tr></table>"
    )
    doc = _parse(html, tmp_path)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 4  # 内A、外A、内B、外B（产出顺序）
    assert len({t.source_locator["line"] for t in tables}) == 1

    outer_a, outer_b = tables[1], tables[3]
    assert outer_a.metadata["table_index"] != outer_b.metadata["table_index"]

    attr = {e.content: e for e in doc.elements
            if e.type == "paragraph" and e.metadata.get("origin")}
    assert set(attr) == {"NEST_A", "NEST_B"}
    # 坐标完全同形（同为 row 0 / cell 0 / 同起始行）
    for content in ("NEST_A", "NEST_B"):
        m = attr[content].metadata
        assert (m["table_start_line"], m["row_index"], m["cell_index"]) == (
            outer_a.source_locator["line"], 0, 0), content
    # 唯一解析且各归其主
    ti_a = attr["NEST_A"].metadata["table_index"]
    ti_b = attr["NEST_B"].metadata["table_index"]
    assert ti_a != ti_b, "同形坐标必须由 table_index 区分"
    assert [t for t in tables if t.metadata["table_index"] == ti_a] == [outer_a]
    assert [t for t in tables if t.metadata["table_index"] == ti_b] == [outer_b]
    validate(doc.to_dict())


def test_bug_html1_table_index_repeat_parse_deterministic(tmp_path: Path):
    """ChatGPT 验收条件：相同输入重复解析，索引分配一致。"""
    html = (
        "<table><tr><td>A<table><tr><td>X</td></tr></table></td></tr></table>"
        "<table><tr><td>B</td></tr></table>"
    )
    p = tmp_path / "case.html"
    p.write_text(html, encoding="utf-8")
    d1 = HtmlParser().parse(p, source_hash="1" * 64)
    d2 = HtmlParser().parse(p, source_hash="1" * 64)
    k1 = [(e.type, e.content, e.metadata.get("table_index")) for e in d1.elements]
    k2 = [(e.type, e.content, e.metadata.get("table_index")) for e in d2.elements]
    assert k1 == k2


def test_bug_html1_table_index_counter_not_shared_across_documents(tmp_path: Path):
    """ChatGPT 验收条件：不同文档不共享计数状态（计数器随 parser 实例新建）。"""
    html = "<table><tr><td>T</td></tr></table>"
    p = tmp_path / "case.html"
    p.write_text(html, encoding="utf-8")
    d1 = HtmlParser().parse(p, source_hash="1" * 64)
    d2 = HtmlParser().parse(p, source_hash="2" * 64)
    for d in (d1, d2):
        tables = [e for e in d.elements if e.type == "table"]
        assert len(tables) == 1
        assert tables[0].metadata["table_index"] == 0, "每个文档从 0 重新计数"
