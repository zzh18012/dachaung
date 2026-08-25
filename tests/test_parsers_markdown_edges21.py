r"""markdown 文本链接家族全字面测试（Round 1504）。

probe 实证（图片链接已覆盖、autolink 字面已由 edges10
锁，**纯文本链接语法零处理**）：

- **行内链接逐字保留**：'[the docs](url)' 不解不提取
  href、无链接元数据；带 title 的 '[here](url "t")'
  同样
- **引用式链接 + 定义都成段**：'[text][1]' 与定义行
  '[1]: url' 是两个独立 paragraph，定义不被消费/合并
- **shortcut 引用同样**：'[text]' + '[text]: url' 两段
- **裸 URL / 嵌套方括号逐字**：不识别为任何链接语法
- **链接语法在 heading/list_item 内照常进 content**：
  '## See [guide](x)' → heading 'See [guide](x)'
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.markdown_parser import \
    MarkdownParser


def _md(tmp_path, text):
    p = tmp_path / "probe.md"
    p.write_text(text, encoding="utf-8",
                 newline="")
    return MarkdownParser().parse(
        p, compute_file_hash(p))


# ---------- 行内链接 ----------

def test_inline_link_literal(tmp_path):
    doc = _md(
        tmp_path,
        "see [the docs]"
        "(https://example.com) now\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph",
         "see [the docs]"
         "(https://example.com) now"),
    ]
    assert doc.elements[0].metadata == {}
    assert doc.warnings == []


def test_link_with_title_literal(
        tmp_path):
    doc = _md(
        tmp_path,
        'click [here](https://x.com'
        ' "the title") now\n')
    assert [e.content
            for e in doc.elements] == [
        'click [here](https://x.com'
        ' "the title") now',
    ]


def test_nested_brackets_literal(
        tmp_path):
    doc = _md(
        tmp_path,
        "see [a [b] c](u) end\n")
    assert [e.content
            for e in doc.elements] == [
        "see [a [b] c](u) end",
    ]


# ---------- 引用式链接 ----------

def test_ref_link_and_def_two_paras(
        tmp_path):
    doc = _md(
        tmp_path,
        "see [text][1] end\n\n"
        "[1]: https://example.com\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "see [text][1] end"),
        ("paragraph",
         "[1]: https://example.com"),
    ]
    assert doc.warnings == []


def test_shortcut_ref_two_paras(
        tmp_path):
    doc = _md(
        tmp_path,
        "see [text] end\n\n"
        "[text]: https://example.com\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "see [text] end"),
        ("paragraph",
         "[text]: https://example.com"),
    ]


# ---------- 其他形态 ----------

def test_bare_url_literal(tmp_path):
    doc = _md(
        tmp_path,
        "go to https://example.com"
        " now\n")
    assert [e.content
            for e in doc.elements] == [
        "go to https://example.com now",
    ]
    assert doc.warnings == []


def test_link_syntax_in_heading_and_list(
        tmp_path):
    doc = _md(
        tmp_path,
        "## See [guide](https://x)\n"
        "- [item](https://y)\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading",
         "See [guide](https://x)"),
        ("list_item", "[item](https://y)"),
    ]
    assert doc.elements[0].metadata == {
        "level": 2}
    assert doc.elements[1].metadata == {
        "ordered": False,
        "marker": "unordered"}
    assert doc.warnings == []
