r"""HTML `<table/>` 自闭合——startendtag 委托分支（Round 2006，a 优先级）。

html_parser.py:262-277 `handle_startendtag` 对非 img/br/hr 标签
**只转发 handle_starttag**（不补 endtag）→ `<table/>` 进入表格
模式但永不闭合。零覆盖（grep 实证 tests/ 无 `<table/>`；
edges22 锁的是缺 `</table>` 的普通开标签形态）。探针 R2006 实证：

- **T1 吞噬后续文档**：'<p>a</p><table/><p>b</p>' → 只有段落
  'a'——'b' 被吞（depth≥1 时 handle_data cell=None 丢弃）、
  无表元素、元素非空故无 html_no_content
- **T2 自开表被真表收口**：'<table/><table>...' → 第二个
  `<table>` 命中嵌套告警被忽略，但内层 tr/td 全记在**自开表**
  栈上，其 `</table>` 反而把自开表正常收口 → 表 '| x |' 出现
  + html_nested_table 告警
- **T3 空自开 + 游 `</table>`**：'<table/>x</table>' → rows 空
  md='' 无元素；'x' 被吞 → [] + html_no_content
- **T4 双自开**：'<table/><table/>' → 第二个命中嵌套告警；
  永不闭合 → [] + [html_nested_table, html_no_content]
  （追加分序：嵌套告警先于 no_content）

判别式：T1 若 'b' 存活翻；T2 若无表/无告警翻；T3 若 'x' 成段
翻；T4 告警序颠倒翻。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser


def _parse(tmp_path: Path, body: str):
    p = tmp_path / "s.html"
    p.write_text(body, encoding="utf-8", newline="")
    return HtmlParser().parse(p, compute_file_hash(p))


def test_selfclose_table_swallows_rest(tmp_path):
    """T1：'<p>a</p><table/><p>b</p>' → 只有段落 'a'，'b' 被吞，零告警。"""
    d = _parse(tmp_path, "<p>a</p><table/><p>b</p>")
    assert [(e.type, e.content) for e in d.elements] == [("paragraph", "a")]
    assert d.warnings == []


def test_selfclose_table_closed_by_real_table(tmp_path):
    """T2：自开表被后续真表的 tr/td 填充、真表 </table> 收口 → 表+嵌套告警。"""
    d = _parse(tmp_path, "<table/><table><tr><td>x</td></tr></table>")
    assert [(e.type, e.content) for e in d.elements] == [
        ("table", "| x |\n| --- |")]
    assert d.elements[0].metadata == {
        "row_count": 1, "col_count": 1, "source": "html_table"}
    assert [w.code for w in d.warnings] == ["html_nested_table"]


def test_selfclose_empty_with_stray_close(tmp_path):
    """T3：'<table/>x</table>' → rows 空、'x' 被吞 → 零元素+html_no_content。"""
    d = _parse(tmp_path, "<table/>x</table>")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["html_no_content"]


def test_double_selfclose_warning_order(tmp_path):
    """T4：'<table/><table/>' → [html_nested_table, html_no_content] 追加分序。"""
    d = _parse(tmp_path, "<table/><table/>")
    assert d.elements == []
    assert [w.code for w in d.warnings] == ["html_nested_table", "html_no_content"]
