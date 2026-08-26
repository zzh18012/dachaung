r"""pipeline section_path 嵌套算法：' > '
连接、同级替换、跳级追加与 h1 重置
（Round 1768）。

新角度：R1767 锁超限隔离——**标题层级
栈：子标题追加（'T > U'）、同级替换末
段（'A'→'B'）、跳级直接追加（h2→h4
'A > D' 无中间层）、h1 任意处全重置、
六层最深 'a > b > … > f'**零覆盖：

- **'## T\\n\\n### U'**：'T' / 'T > U'
- **'## A\\n\\n## B'**：'A'→'B' 同级替换
- **'#### D' in '## A'**：'A > D' 跳级
  追加；'# H' in '### A>#### B'：全重置
- **h1–h6 全嵌**：六段 ' > ' 路径
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _paths(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    return [e.source_locator["section_path"]
            for e in doc.elements]


def test_nested_append(tmp_path):
    assert _paths(
        tmp_path, "## T\n\n### U\n\nx\n") == [
        "T", "T > U", "T > U"]


def test_sibling_replaces_last(tmp_path):
    assert _paths(
        tmp_path, "## A\n\nx\n\n## B\n\ny\n") == [
        "A", "A", "B", "B"]


def test_jump_append_and_h1_reset(tmp_path):
    assert _paths(
        tmp_path, "## A\n\n#### D\n\ny\n") == [
        "A", "A > D", "A > D"]
    assert _paths(
        tmp_path, "### A\n\n#### B\n\n# H\n\ny\n") == [
        "A", "A > B", "H", "H"]


def test_six_level_full_path(tmp_path):
    assert _paths(tmp_path, (
        "# a\n\n## b\n\n### c\n\n#### d\n"
        "\n##### e\n\n###### f\n\nx\n")) == [
        "a", "a > b", "a > b > c", "a > b > c > d",
        "a > b > c > d > e", "a > b > c > d > e > f",
        "a > b > c > d > e > f"]
