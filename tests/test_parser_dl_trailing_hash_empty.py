r"""parser 细节：dl 无分隔拼接、ATX 尾井号
剥离、空 p 丢弃、bq 平段化（Round 1790）。

新角度：R1789 锁实体单趟——**html
<dl> 的 dt+dd 直接拼接无空格 'termdef'
成单段；'## T ##' 尾井号剥离 heading
'T'；<p></p> 与 <p>  </p> 静默丢弃
（仅剩 'x'）；<blockquote> 不留标记——
'q1' 平段落与后续 'q1 after' 合并**零
覆盖：

- **'term'+'def'**：'termdef' 单元素
- **'## T ##'**：heading 'T' level 2
- **空 p ×2**：仅剩 'x'、无警告
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def test_html_dl_concatenates_no_space(tmp_path):
    doc, errors = _run(
        tmp_path, "d.html",
        "<dl><dt>term</dt><dd>def</dd></dl>")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "termdef")]


def test_md_trailing_hashes_stripped(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("## T ##\n\nbody\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "T", {"level": 2}),
        ("paragraph", "body", {})]


def test_html_empty_p_dropped(tmp_path):
    doc, errors = _run(
        tmp_path, "d.html", "<p></p><p>x</p><p>  </p>")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "x")]
    assert doc.warnings == []


def test_html_blockquote_plain_merges(tmp_path):
    doc, errors = _run(
        tmp_path, "d.html",
        "<blockquote><p>q1</p></blockquote><p>after</p>")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "q1"), ("paragraph", "after")]
    assert doc.chunks[0].text == "q1 after"
