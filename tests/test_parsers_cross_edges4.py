r"""跨 parser 对照测试 - 第四轮（Round 1433）。

新角度（probe 实证）闭合 ATX 标题全管线 + 标题内原始
inline + 非 BMP 实体（edges2 只锁过 _ATX_HEADING_RE 单元
层，未穿管线）：
- '# Closed One #' / '## Closed Two ##'：尾 # 剥掉、层级
  照认（section_path 'Closed One > Closed Two'）
- '### Deep closed ###' 前后数量一致才剥
- 标题内 inline 标记**原样保留**（'*stars*'、'`code`' 进
  content 与 section_path，不解析不剥离）
- html &#x1F600; 非 BMP 实体 → 😀 正常解码
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, parser,
         data):
    p = tmp_path / name
    if isinstance(data, bytes):
        p.write_bytes(data)
    else:
        p.write_text(data,
                     encoding="utf-8")
    doc, errors = process_single(
        p, None, parser_name=parser,
        max_chars=800)
    assert errors == []
    return doc


# ---------- 闭合 ATX ----------

def test_closed_h1_stripped(
        tmp_path):
    doc = _run(
        tmp_path, "c.md", "markdown",
        "# Closed One #\n\nbody one."
        "\n\n## Closed Two ##\n\n"
        "body two.\n")
    assert doc.elements[
        0].content == "Closed One"
    assert doc.elements[
        0].type == "heading"


def test_closed_h2_nested(
        tmp_path):
    doc = _run(
        tmp_path, "c.md", "markdown",
        "# Closed One #\n\nbody one."
        "\n\n## Closed Two ##\n\n"
        "body two.\n")
    assert doc.elements[
        2].source_locator == {
        "line": 5,
        "section_path":
            "Closed One > "
            "Closed Two"}


def test_closed_lines(tmp_path):
    doc = _run(
        tmp_path, "c.md", "markdown",
        "# Closed One #\n\nbody one."
        "\n\n## Closed Two ##\n\n"
        "body two.\n")
    assert [e.source_locator["line"]
            for e in doc.elements] == [
        1, 3, 5, 7]


def test_closed_triple_stripped(
        tmp_path):
    doc = _run(
        tmp_path, "d.md", "markdown",
        "### Deep closed ###\n\n"
        "para.\n")
    assert doc.elements[
        0].content == "Deep closed"
    assert doc.elements[
        1].source_locator[
        "section_path"] == \
        "Deep closed"


# ---------- 标题内原始 inline ----------

def test_inline_kept_raw(
        tmp_path):
    doc = _run(
        tmp_path, "i.md", "markdown",
        "# Title with *stars* and "
        "`code`\n\nbody.\n")
    assert doc.elements[
        0].content == \
        "Title with *stars* and " \
        "`code`"


def test_inline_in_section_path(
        tmp_path):
    doc = _run(
        tmp_path, "i.md", "markdown",
        "# Title with *stars* and "
        "`code`\n\nbody.\n")
    assert doc.elements[
        1].source_locator == {
        "line": 3,
        "section_path":
            "Title with *stars* "
            "and `code`"}


def test_inline_chunks(tmp_path):
    doc = _run(
        tmp_path, "i.md", "markdown",
        "# Title with *stars* and "
        "`code`\n\nbody.\n")
    assert [c.text
            for c in doc.chunks] == [
        "Title with *stars* and "
        "`code` body."]


# ---------- 非 BMP 实体 ----------

def test_emoji_entity_decoded(
        tmp_path):
    doc = _run(
        tmp_path, "e.html", "html",
        b"<html><body><h1>Emoji "
        b"&#x1F600; test</h1>"
        b"<p>ok</p></body></html>")
    assert doc.elements[
        0].content == \
        "Emoji \U0001F600 test"


def test_emoji_section_path(
        tmp_path):
    doc = _run(
        tmp_path, "e.html", "html",
        b"<html><body><h1>Emoji "
        b"&#x1F600; test</h1>"
        b"<p>ok</p></body></html>")
    assert doc.elements[
        1].source_locator == {
        "line": 1,
        "section_path":
            "Emoji \U0001F600 test"}


def test_emoji_schema_valid(
        tmp_path):
    from app.schema import is_valid
    doc = _run(
        tmp_path, "e.html", "html",
        b"<html><body><h1>Emoji "
        b"&#x1F600; test</h1>"
        b"<p>ok</p></body></html>")
    assert is_valid(doc.to_dict())


def test_closed_schema_valid(
        tmp_path):
    from app.schema import is_valid
    doc = _run(
        tmp_path, "c.md", "markdown",
        "# Closed One #\n\nbody one."
        "\n\n## Closed Two ##\n\n"
        "body two.\n")
    assert is_valid(doc.to_dict())
