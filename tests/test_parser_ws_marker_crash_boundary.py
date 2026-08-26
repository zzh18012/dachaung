r"""parser 空白标记崩溃边界：'## '/'##T'
非标题成段，2+ 空格崩溃（Round 1813）。

新角度：R1812 锁裸标签——**'##' 无空格
与 '##T' 无空格——非标题、字面段落
'##'/'##T'；'## ' 单空格——段落 '##'
不崩；'##  '（2+ 空格）与 '-   '——
unexpected_parser_error 崩溃（details
{path, parser_name}）——崩溃家族精确
边界 = 标记后 ≥2 空格且内容空白**零
覆盖：

- **'##'/'##T'**：字面段落
- **'## ' 单空格**：段落 '##' 不崩
- **'##  ' 2 空格**：unexpected_parser_
  error
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_marker_without_space_literal(tmp_path):
    for text, want in [("##\n\nbody\n", "##"),
                       ("##T\n\nbody\n", "##T")]:
        doc, errors = _run(tmp_path, text)
        assert errors == []
        assert doc.elements[0].type == "paragraph"
        assert doc.elements[0].content == want


def test_single_trailing_space_no_crash(tmp_path):
    doc, errors = _run(tmp_path, "## \n\nbody\n")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "##"),
        ("paragraph", "body")]
    assert doc.chunks[0].text == "## body"


def test_multi_trailing_space_crashes(tmp_path):
    for text in ["##  \n\nbody\n", "-   \n\nbody\n"]:
        doc, errors = _run(tmp_path, text)
        assert doc is None, text
        assert len(errors) == 1
        assert errors[0].code == (
            "unexpected_parser_error")
        assert set(errors[0].details) == {
            "path", "parser_name"}
        assert errors[0].details[
            "parser_name"] == "markdown"
