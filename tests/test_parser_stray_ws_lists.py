r"""parser 游离文本、内部空白保留、松散列
表与续行分离（Round 1796）。

新角度：R1795 锁嵌套扁平——**html
'loose<p>a</p>tail'——前游离文本并入
段 'loosea'（无空格拼接）、后游离文本
'tail' 独立成段（前后不对称）；段内三
空格 'a   b' 原样保留（仅剥两端）；md
松散列表（项间空行）仍 2×list_item 合
并；'- a\\n  cont' 续行剥缩进独立成
段**零覆盖：

- **'loose<p>a</p>tail'**：
  'loosea'+'tail' 两段
- **'  a   b  '**：'a   b'
- **'  cont'**：paragraph 'cont'
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_html_stray_text_asymmetric(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("loose<p>a</p>tail", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "loosea"),
        ("paragraph", "tail")]
    assert doc.chunks[0].text == "loosea tail"


def test_html_internal_whitespace_preserved(
        tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<p>  a   b  </p>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "a   b"]


def test_md_loose_list_still_items(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("- a\n\n- b\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "a"), ("list_item", "b")]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("a b", 2)]


def test_md_list_continuation_separate(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("- a\n  cont\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "a"), ("paragraph", "cont")]
