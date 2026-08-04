"""HTML parser 的单元测试 + 端到端 pipeline 测试。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.models import Document
from app.parsers import ParserError
from app.parsers.html_parser import HtmlParser


VENV_PYTHON = str(
    Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe"
)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PYTHON = VENV_PYTHON if Path(VENV_PYTHON).is_file() else sys.executable


def _write_html(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _wrap(body: str, title: str = "Test") -> str:
    return (
        "<!DOCTYPE html>\n"
        "<html><head><title>" + title + "</title></head>\n"
        "<body>\n" + body + "\n</body></html>\n"
    )


# ---------- 基础块 ----------


def test_html_heading_levels(tmp_path: Path):
    body = "<h1>H1</h1><h2>H2</h2><h3>H3</h3><h4>H4</h4><h5>H5</h5><h6>H6</h6>"
    p = _write_html(tmp_path, "h.html", _wrap(body))
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    assert doc.source_type == "html"
    headings = [e for e in doc.elements if e.type == "heading"]
    assert len(headings) == 6
    assert [h.metadata["level"] for h in headings] == [1, 2, 3, 4, 5, 6]
    assert [h.content for h in headings] == ["H1", "H2", "H3", "H4", "H5", "H6"]


def test_html_paragraph_basic(tmp_path: Path):
    p = _write_html(tmp_path, "p.html", _wrap("<p>Hello world.</p>"))
    doc = HtmlParser().parse(p, source_hash="b" * 64)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].content == "Hello world."


def test_html_loose_text_becomes_paragraph(tmp_path: Path):
    """body 直接子文本（不在 <p> 内）也成为 paragraph。"""
    p = _write_html(tmp_path, "loose.html", _wrap("Just a loose line.\n"))
    doc = HtmlParser().parse(p, source_hash="c" * 64)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert "loose line" in paras[0].content


def test_html_inline_tags_text_concatenated(tmp_path: Path):
    """<b>、<i>、<a>、<span> 等 inline 的文本拼接到当前段落。"""
    body = "<p>Hello <b>bold</b> and <i>italic</i> text.</p>"
    p = _write_html(tmp_path, "inline.html", _wrap(body))
    doc = HtmlParser().parse(p, source_hash="d" * 64)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert "Hello bold and italic text." == paras[0].content


def test_html_unordered_list(tmp_path: Path):
    body = "<ul><li>apple</li><li>banana</li><li>cherry</li></ul>"
    p = _write_html(tmp_path, "ul.html", _wrap(body))
    doc = HtmlParser().parse(p, source_hash="e" * 64)
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 3
    assert [it.content for it in items] == ["apple", "banana", "cherry"]
    assert all(it.metadata["ordered"] is False for it in items)


def test_html_ordered_list(tmp_path: Path):
    body = "<ol><li>first</li><li>second</li></ol>"
    p = _write_html(tmp_path, "ol.html", _wrap(body))
    doc = HtmlParser().parse(p, source_hash="f" * 64)
    items = [e for e in doc.elements if e.type == "list_item"]
    assert len(items) == 2
    assert [it.content for it in items] == ["first", "second"]
    assert all(it.metadata["ordered"] is True for it in items)


def test_html_pre_block(tmp_path: Path):
    body = "<pre>line 1\nline 2\n  indented\n</pre>"
    p = _write_html(tmp_path, "pre.html", _wrap(body))
    doc = HtmlParser().parse(p, source_hash="10" * 32)
    pres = [e for e in doc.elements if e.metadata.get("kind") == "preformatted"]
    assert len(pres) == 1
    # 保留换行与缩进
    assert "line 1" in pres[0].content
    assert "  indented" in pres[0].content


def test_html_blockquote(tmp_path: Path):
    body = "<blockquote>This is a quote.</blockquote>"
    p = _write_html(tmp_path, "q.html", _wrap(body))
    doc = HtmlParser().parse(p, source_hash="11" * 32)
    bqs = [e for e in doc.elements if e.metadata.get("kind") == "blockquote"]
    assert len(bqs) == 1
    assert bqs[0].content == "This is a quote."


def test_html_blockquote_with_inner_p(tmp_path: Path):
    """<blockquote><p>...</p></blockquote>：保留 blockquote 类型。"""
    body = "<blockquote><p>First para.</p><p>Second para.</p></blockquote>"
    p = _write_html(tmp_path, "qp.html", _wrap(body))
    doc = HtmlParser().parse(p, source_hash="12" * 32)
    bqs = [e for e in doc.elements if e.metadata.get("kind") == "blockquote"]
    # 两个 <p> 都被吸收进 blockquote 块（合并或分块）
    assert len(bqs) >= 1
    combined = " ".join(bq.content for bq in bqs)
    assert "First para." in combined
    assert "Second para." in combined


def test_html_table_basic(tmp_path: Path):
    body = (
        "<table>"
        "<tr><th>Name</th><th>Age</th></tr>"
        "<tr><td>Alice</td><td>30</td></tr>"
        "<tr><td>Bob</td><td>25</td></tr>"
        "</table>"
    )
    p = _write_html(tmp_path, "t.html", _wrap(body))
    doc = HtmlParser().parse(p, source_hash="13" * 32)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1
    t = tables[0]
    assert "Name" in t.content and "Age" in t.content
    assert "Alice" in t.content and "Bob" in t.content
    assert t.metadata["row_count"] == 3
    assert t.metadata["col_count"] == 2


def test_html_image_element(tmp_path: Path):
    body = '<p>Before.</p><img src="assets/diagram.png" alt="diagram"><p>After.</p>'
    p = _write_html(tmp_path, "img.html", _wrap(body))
    doc = HtmlParser().parse(p, source_hash="14" * 32)
    imgs = [e for e in doc.elements if e.type == "image"]
    assert len(imgs) == 1
    assert imgs[0].resource_path == "assets/diagram.png"
    assert imgs[0].metadata["alt"] == "diagram"


def test_html_hr_skipped(tmp_path: Path):
    body = "<p>before</p><hr><p>after</p>"
    p = _write_html(tmp_path, "hr.html", _wrap(body))
    doc = HtmlParser().parse(p, source_hash="15" * 32)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 2
    assert paras[0].content == "before"
    assert paras[1].content == "after"


def test_html_entities_decoded(tmp_path: Path):
    """&amp; / &lt; / &gt; / &quot; / &#39; 等字符实体自动解码。"""
    body = "<p>A &amp; B &lt; C &gt; D</p>"
    p = _write_html(tmp_path, "ent.html", _wrap(body))
    doc = HtmlParser().parse(p, source_hash="16" * 32)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert paras[0].content == "A & B < C > D"


def test_html_skip_script_style(tmp_path: Path):
    """script/style 内容不应进入 elements。"""
    body = (
        "<p>real content</p>"
        "<script>var x = '<p>fake</p>';</script>"
        "<style>p { color: red; }</style>"
    )
    p = _write_html(tmp_path, "skip.html", _wrap(body))
    doc = HtmlParser().parse(p, source_hash="17" * 32)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].content == "real content"


def test_html_skip_head_title(tmp_path: Path):
    """<head>/<title> 内容不应进入 elements。"""
    p = _write_html(
        tmp_path,
        "head.html",
        "<!DOCTYPE html><html><head><title>My Title</title>"
        "<meta charset='utf-8'></head><body><p>body text</p></body></html>",
    )
    doc = HtmlParser().parse(p, source_hash="18" * 32)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    assert paras[0].content == "body text"
    # title 文本不应出现
    assert all("My Title" not in (e.content or "") for e in doc.elements)


def test_html_br_as_space(tmp_path: Path):
    body = "<p>line one<br>line two<br>line three</p>"
    p = _write_html(tmp_path, "br.html", _wrap(body))
    doc = HtmlParser().parse(p, source_hash="19" * 32)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paras) == 1
    # <br> 被替换为空格
    assert "line one line two line three" == paras[0].content


# ---------- section_path / 行号 ----------


def test_html_section_path_tracking(tmp_path: Path):
    body = (
        "<h1>Chapter</h1>"
        "<p>Intro.</p>"
        "<h2>Section A</h2>"
        "<p>Text in A.</p>"
        "<h2>Section B</h2>"
        "<p>Text in B.</p>"
        "<h1>Chapter 2</h1>"
        "<p>Text in ch2.</p>"
    )
    p = _write_html(tmp_path, "sec.html", _wrap(body))
    doc = HtmlParser().parse(p, source_hash="20" * 32)
    paras = [e for e in doc.elements if e.type == "paragraph"]
    assert paras[0].source_locator["section_path"] == "Chapter"
    assert paras[1].source_locator["section_path"] == "Chapter > Section A"
    assert paras[2].source_locator["section_path"] == "Chapter > Section B"
    assert paras[3].source_locator["section_path"] == "Chapter 2"


def test_html_line_numbers_in_locator(tmp_path: Path):
    """locator.line 来自 HTMLParser.getpos()，1-indexed。"""
    p = _write_html(
        tmp_path,
        "lines.html",
        "<!DOCTYPE html>\n<html>\n<head><title>t</title></head>\n<body>\n<p>hi</p>\n</body>\n</html>\n",
    )
    doc = HtmlParser().parse(p, source_hash="21" * 32)
    para = doc.elements[0]
    assert para.source_locator["line"] >= 5  # <p>hi</p> 在第 5 行


# ---------- 错误路径 ----------


def test_html_missing_file_raises(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        HtmlParser().parse(tmp_path / "nope.html", source_hash="x" * 64)
    assert exc.value.code == "file_not_found"


def test_html_unsupported_extension_raises(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello")
    with pytest.raises(ParserError) as exc:
        HtmlParser().parse(p, source_hash="y" * 64)
    assert exc.value.code == "unsupported_type"


def test_html_htm_extension_accepted(tmp_path: Path):
    p = _write_html(tmp_path, "x.htm", _wrap("<p>hi</p>"))
    doc = HtmlParser().parse(p, source_hash="z" * 64)
    assert doc.source_type == "html"
    assert doc.elements[0].type == "paragraph"


def test_html_empty_body_yields_warning(tmp_path: Path):
    p = _write_html(tmp_path, "empty.html", _wrap(""))
    doc = HtmlParser().parse(p, source_hash="0" * 64)
    assert doc.elements == []
    codes = [w.code for w in doc.warnings]
    assert "html_no_content" in codes


# ---------- Document 字段 / schema ----------


def test_html_parser_name_and_version(tmp_path: Path):
    p = _write_html(tmp_path, "x.html", _wrap("<p>hi</p>"))
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    assert doc.parser_name == "html"
    assert doc.parser_version.startswith("stdlib/")
    assert doc.chunks == []
    assert doc.errors == []


def test_html_full_document_schema_valid(tmp_path: Path):
    from app.schema import validate

    body = (
        "<h1>Title</h1>"
        "<p>Intro paragraph.</p>"
        "<h2>Sub</h2>"
        "<ul><li>a</li><li>b</li></ul>"
        "<pre>x = 1</pre>"
        "<blockquote>quote</blockquote>"
        "<table><tr><th>K</th><th>V</th></tr><tr><td>1</td><td>2</td></tr></table>"
        '<img src="pic.png" alt="x">'
    )
    p = _write_html(tmp_path, "full.html", _wrap(body))
    doc = HtmlParser().parse(p, source_hash="b" * 64)
    validate(doc.to_dict())


def test_html_pipeline_end_to_end(tmp_path: Path):
    from app.pipeline import process_single

    body = (
        "<h1>Project</h1>"
        "<p>Intro paragraph with enough text.</p>"
        "<h2>Background</h2>"
        "<p>More content. Lorem ipsum dolor sit amet.</p>"
        "<ul><li>one</li><li>two</li></ul>"
    )
    src = _write_html(tmp_path, "doc.html", _wrap(body))
    out = tmp_path / "out.json"
    document, errors = process_single(src, out, parser_name="html", write_json=True)
    assert errors == []
    assert document is not None
    assert document.source_type == "html"
    types = {e.type for e in document.elements}
    assert {"heading", "paragraph", "list_item"}.issubset(types)
    assert len(document.chunks) >= 1
    for c in document.chunks:
        assert c.source_element_ids


def test_cli_parse_html_end_to_end(tmp_path: Path):
    body = "<h1>Title</h1><p>Hello HTML world.</p>"
    src = tmp_path / "doc.html"
    src.write_text(_wrap(body), encoding="utf-8")
    out = tmp_path / "out.json"

    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(PROJECT_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    proc = subprocess.run(
        [_PYTHON, "-m", "app.cli", "parse", str(src),
         "-o", str(out), "--parser", "html"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    assert "[OK]" in proc.stdout
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source_type"] == "html"
    assert data["parser_name"] == "html"
    assert len(data["elements"]) >= 2


# ---------- 内部 helpers（纯函数）----------

from pathlib import Path as _Path  # noqa: E402

from app.parsers.html_parser import _detect_html_source_type, _rows_to_md  # noqa: E402


def test_detect_html_source_type_accepts_html_and_htm():
    assert _detect_html_source_type(_Path("foo.html")) == "html"
    assert _detect_html_source_type(_Path("foo.htm")) == "html"
    # 大小写不敏感
    assert _detect_html_source_type(_Path("FOO.HTML")) == "html"


def test_detect_html_source_type_rejects_other_extensions():
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(_Path("foo.txt"))
    assert exc.value.code == "unsupported_type"


def test_html_rows_to_md_empty():
    assert _rows_to_md([]) == ""


def test_html_rows_to_md_single_row_no_body():
    md = _rows_to_md([["h1", "h2"]])
    lines = md.splitlines()
    assert len(lines) == 2  # header + separator
    assert "| h1 | h2 |" in lines[0]


def test_html_rows_to_md_pads_uneven():
    md = _rows_to_md([["a", "b", "c"], ["d"]])
    lines = md.splitlines()
    # 数据行 d 应被填充到 3 列
    assert lines[2].count("|") == lines[0].count("|")


# ---------- 边角与缺漏补强（Round 38） ----------


# _detect_html_source_type 直接单测


def test_detect_html_source_type_accepts_uppercase_extensions():
    """扩展名 lower() 后比较，.HTML / .HTM 也接受。"""
    from app.parsers.html_parser import _detect_html_source_type
    assert _detect_html_source_type(Path("doc.HTML")) == "html"
    assert _detect_html_source_type(Path("doc.HTM")) == "html"


def test_detect_html_source_type_rejects_unknown_suffix():
    from app.parsers.html_parser import _detect_html_source_type
    with pytest.raises(ParserError) as exc:
        _detect_html_source_type(Path("doc.xml"))
    assert exc.value.code == "unsupported_type"


def test_detect_html_source_type_rejects_no_suffix():
    from app.parsers.html_parser import _detect_html_source_type
    with pytest.raises(ParserError):
        _detect_html_source_type(Path("noext"))


# 常量


def test_heading_levels_constant_has_all_six():
    from app.parsers.html_parser import _HEADING_LEVELS
    assert _HEADING_LEVELS == {
        "h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6,
    }


def test_skip_tags_constant_includes_script_style():
    from app.parsers.html_parser import _SKIP_TAGS
    assert "script" in _SKIP_TAGS
    assert "style" in _SKIP_TAGS
    assert "head" in _SKIP_TAGS
    assert "title" in _SKIP_TAGS


# HtmlParser metadata / element 边角


def test_html_parser_metadata_has_html_true(tmp_path: Path):
    p = tmp_path / "doc.html"
    p.write_text("<html><body><p>hi</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    assert doc.metadata.get("html") is True


def test_html_parser_element_id_format(tmp_path: Path):
    p = tmp_path / "doc.html"
    p.write_text("<html><body><p>hi</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    expected_prefix = "doc-" + "a" * 16
    for i, el in enumerate(doc.elements):
        assert el.element_id == f"{expected_prefix}::e{i:04d}"


def test_html_parser_document_id_derived_from_hash(tmp_path: Path):
    p = tmp_path / "doc.html"
    p.write_text("<html><body><p>hi</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    assert doc.document_id == "doc-" + "a" * 16


def test_html_parser_chunks_empty_by_default(tmp_path: Path):
    p = tmp_path / "doc.html"
    p.write_text("<html><body><p>hi</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    assert doc.chunks == []


def test_html_parser_relations_empty_by_default(tmp_path: Path):
    p = tmp_path / "doc.html"
    p.write_text("<html><body><p>hi</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    assert doc.relations == []


def test_html_parser_errors_empty_by_default(tmp_path: Path):
    p = tmp_path / "doc.html"
    p.write_text("<html><body><p>hi</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    assert doc.errors == []


# 各种 HTML 结构边角


def test_html_parser_nested_list_inner_items_emitted(tmp_path: Path):
    """嵌套 ul：内层 li 也应被识别。"""
    p = tmp_path / "doc.html"
    p.write_text(
        "<html><body>"
        "<ul><li>outer"
        "<ul><li>inner</li></ul>"
        "</li></ul>"
        "</body></html>",
        encoding="utf-8",
    )
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    list_items = [e for e in doc.elements if e.type == "list_item"]
    # 至少识别出 outer 和 inner
    assert len(list_items) >= 2


def test_html_parser_blockquote_with_kind_metadata(tmp_path: Path):
    p = tmp_path / "doc.html"
    p.write_text("<html><body><blockquote>quoted</blockquote></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    blockquotes = [e for e in doc.elements if e.metadata.get("kind") == "blockquote"]
    assert len(blockquotes) >= 1


def test_html_parser_pre_with_kind_metadata(tmp_path: Path):
    p = tmp_path / "doc.html"
    p.write_text("<html><body><pre>code line</pre></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    pre_elements = [e for e in doc.elements if e.metadata.get("kind") == "preformatted"]
    assert len(pre_elements) >= 1


def test_html_parser_image_element_has_resource_path(tmp_path: Path):
    p = tmp_path / "doc.html"
    p.write_text(
        '<html><body><img src="http://example.com/x.png" alt="alt"></body></html>',
        encoding="utf-8",
    )
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    images = [e for e in doc.elements if e.type == "image"]
    assert len(images) == 1
    assert images[0].resource_path == "http://example.com/x.png"
    assert images[0].content is None


def test_html_parser_table_emits_table_element(tmp_path: Path):
    p = tmp_path / "doc.html"
    p.write_text(
        "<html><body><table>"
        "<tr><th>a</th><th>b</th></tr>"
        "<tr><td>1</td><td>2</td></tr>"
        "</table></body></html>",
        encoding="utf-8",
    )
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    tables = [e for e in doc.elements if e.type == "table"]
    assert len(tables) == 1


def test_html_parser_skips_meta_tags(tmp_path: Path):
    """<meta> 在 _SKIP_TAGS 中，应被跳过。"""
    p = tmp_path / "doc.html"
    p.write_text(
        '<html><head><meta charset="utf-8"></head>'
        '<body><p>visible</p></body></html>',
        encoding="utf-8",
    )
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    contents = [e.content for e in doc.elements if e.content]
    assert all("charset" not in c for c in contents)


def test_html_parser_skips_noscript_tags(tmp_path: Path):
    p = tmp_path / "doc.html"
    p.write_text(
        '<html><body><noscript>JS required</noscript><p>visible</p></body></html>',
        encoding="utf-8",
    )
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    contents = [e.content for e in doc.elements if e.content]
    assert all("JS required" not in c for c in contents)


def test_html_parser_skips_link_tags(tmp_path: Path):
    p = tmp_path / "doc.html"
    p.write_text(
        '<html><head><link rel="stylesheet" href="x.css"></head>'
        '<body><p>visible</p></body></html>',
        encoding="utf-8",
    )
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    contents = [e.content for e in doc.elements if e.content]
    assert all("stylesheet" not in c for c in contents)


# _rows_to_md 多种输入


def test_html_rows_to_md_returns_empty_for_empty_list():
    from app.parsers.html_parser import _rows_to_md
    assert _rows_to_md([]) == ""


def test_html_rows_to_md_single_row_no_body_lines():
    from app.parsers.html_parser import _rows_to_md
    md = _rows_to_md([["only", "header"]])
    lines = md.splitlines()
    assert len(lines) == 2  # header + separator


def test_html_rows_to_md_three_rows_includes_two_body():
    from app.parsers.html_parser import _rows_to_md
    md = _rows_to_md([["h"], ["a"], ["b"]])
    lines = md.splitlines()
    assert len(lines) == 4


# HTML 实体 / 字符引用


def test_html_parser_numeric_entity_decoded(tmp_path: Path):
    """&#65; → 'A'（convert_charrefs=True 自动转换数字实体）。"""
    p = tmp_path / "doc.html"
    p.write_text("<html><body><p>&#65;</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    contents = [e.content for e in doc.elements if e.content]
    assert any("A" in c for c in contents)


def test_html_parser_named_entity_decoded(tmp_path: Path):
    """&amp; → '&'。"""
    p = tmp_path / "doc.html"
    p.write_text("<html><body><p>a &amp; b</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    contents = [e.content for e in doc.elements if e.content]
    assert any("a & b" in c for c in contents)


# locator 边角


def test_html_parser_locator_markdown_carries_section_path(tmp_path: Path):
    """heading 后的 paragraph locator 应含 section_path。"""
    p = tmp_path / "doc.html"
    p.write_text(
        "<html><body><h1>Title</h1><p>under title</p></body></html>",
        encoding="utf-8",
    )
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    paragraphs = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paragraphs) >= 1
    p0 = paragraphs[0]
    assert "section_path" in p0.source_locator
    assert "Title" in p0.source_locator["section_path"]


def test_html_parser_heading_element_emitted_with_level(tmp_path: Path):
    p = tmp_path / "doc.html"
    p.write_text("<html><body><h2>Section</h2></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    headings = [e for e in doc.elements if e.type == "heading"]
    assert len(headings) == 1
    assert headings[0].metadata.get("level") == 2


def test_html_parser_empty_body_emits_warning(tmp_path: Path):
    """完全空 body → html_no_content 警告。"""
    p = tmp_path / "doc.html"
    p.write_text("<html><body></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    warning_codes = [w.code for w in doc.warnings]
    assert "html_no_content" in warning_codes


def test_html_parser_invalid_utf8_uses_replace(tmp_path: Path):
    """非法 UTF-8 字节 → 用 errors=replace 而不是抛 UnicodeDecodeError。"""
    p = tmp_path / "doc.html"
    p.write_bytes(b"<html><body><p>\xff\xfe hello</p></body></html>")
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    assert len(doc.elements) >= 1


# hr 标签


def test_html_parser_hr_does_not_emit_element(tmp_path: Path):
    """<hr> 是主题分隔符，被忽略，不产 element。"""
    p = tmp_path / "doc.html"
    p.write_text("<html><body><p>before</p><hr><p>after</p></body></html>", encoding="utf-8")
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    contents = [e.content for e in doc.elements if e.content]
    assert all(c.strip() != "---" for c in contents)


# 多个连续空行


def test_html_parser_multiple_blank_lines_dont_create_elements(tmp_path: Path):
    p = tmp_path / "doc.html"
    p.write_text(
        "<html><body>\n\n\n<p>only</p>\n\n\n</body></html>",
        encoding="utf-8",
    )
    doc = HtmlParser().parse(p, source_hash="a" * 64)
    paragraphs = [e for e in doc.elements if e.type == "paragraph"]
    assert len(paragraphs) == 1
