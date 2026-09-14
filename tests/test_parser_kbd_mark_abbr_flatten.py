r"""html kbd/mark/abbr 行内语义标签测试（Round 1841）。

新角度（probe 实证，grep -c 核实 `<kbd`/`<mark`/`<abbr` 全库零覆盖；
sub/sup 在 edges15、figure/caption 在 edges12 等已锁）：
- **kbd 剥壳并入段落**：<p>press <kbd>Ctrl</kbd>+<kbd>C</kbd> now</p>
  → paragraph 'press Ctrl+C now'——标签剥离、内文无缝拼接（'Ctrl+C'
  中间不加空格）、metadata 空；顶层裸 <kbd>Standalone</kbd> outside
  同样压成单段 'Standalone outside'
- **mark 高亮剥壳**：<mark>highlighted</mark> → 'note highlighted
  text'，无 highlight 相关 metadata（装饰语义全弃，与 style/dir 同哲学）
- **abbr title 属性整弃**：<abbr title="HyperText">HT</abbr> →
  'HT means markup'——只留元素文本，title 展开词不并入 content、
  也不入 metadata；顶层裸 abbr 同规（'SA bare'）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser


def _html(tmp_path: Path, text: str):
    p = tmp_path / "r1841.html"
    p.write_text(text, encoding="utf-8", newline="")
    return HtmlParser().parse(p, compute_file_hash(p))


def test_html_kbd_inline_and_standalone(tmp_path: Path):
    doc = _html(tmp_path, "<p>press <kbd>Ctrl</kbd>+<kbd>C</kbd> now</p>")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "press Ctrl+C now"
    assert e.metadata == {}

    bare = _html(tmp_path, "<kbd>Standalone</kbd> outside")
    assert len(bare.elements) == 1
    assert bare.elements[0].type == "paragraph"
    assert bare.elements[0].content == "Standalone outside"


def test_html_mark_highlight_flattened(tmp_path: Path):
    doc = _html(tmp_path, "<p>note <mark>highlighted</mark> text</p>")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "note highlighted text"
    assert e.metadata == {}


def test_html_abbr_title_dropped(tmp_path: Path):
    doc = _html(tmp_path, '<p><abbr title="HyperText">HT</abbr> means markup</p>')
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "HT means markup"
    assert e.metadata == {}

    bare = _html(tmp_path, '<abbr title="Alone">SA</abbr> bare')
    assert len(bare.elements) == 1
    assert bare.elements[0].content == "SA bare"
    assert bare.elements[0].metadata == {}
