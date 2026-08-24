r"""app/pipeline.py 边角测试 - 第十二轮（Round 1365）。

补强 edges11 未覆盖的深度（probe 实证）：
- html 走全管线——pre 的换行在 chunk 文本中存活（chunker 只用空格
  join part，part 内 \n 原样保留）
- image element 被分块器完全跳过（不产生 chunk、不进 source_ids）
- heading 硬边界 / 表格 isolated_table / 不丢不重
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.pipeline import process_single


HTML = """<html><body>
<h1>Head</h1>
<p>para text here</p>
<pre>line1
<b>bold</b>
line3</pre>
<blockquote>quote text</blockquote>
<img src="pic.png" alt="p">
<h2>Sub</h2>
<p>tail</p>
</body></html>
"""


def _run(tmp_path, html=HTML, mc=200):
    (tmp_path / "d.html").write_text(html,
                                     encoding="utf-8")
    return process_single(
        tmp_path / "d.html", tmp_path / "o.json",
        parser_name="html", max_chars=mc)


# ---------- 分块几何 ----------

def test_html_two_chunks(tmp_path):
    doc, errors = _run(tmp_path)
    assert errors == []
    assert len(doc.chunks) == 2


def test_pre_newlines_survive(tmp_path):
    doc, _ = _run(tmp_path)
    assert doc.chunks[0].text == (
        "Head para text here "
        "line1\nbold\nline3 quote text")


def test_seven_elements(tmp_path):
    doc, errors = _run(tmp_path)
    assert errors == []
    assert len(doc.elements) == 7


def test_element_kinds(tmp_path):
    doc, _ = _run(tmp_path)
    kinds = [(e.type, e.metadata.get("kind"))
             for e in doc.elements]
    assert kinds == [
        ("heading", None),
        ("paragraph", None),
        ("paragraph", "preformatted"),
        ("paragraph", "blockquote"),
        ("image", None),
        ("heading", None),
        ("paragraph", None)]


# ---------- image 跳过 ----------

def test_image_not_in_any_chunk(tmp_path):
    doc, _ = _run(tmp_path)
    img = [e for e in doc.elements
           if e.type == "image"][0]
    assert not any(img.element_id in
                   c.source_element_ids
                   for c in doc.chunks)


def test_image_still_in_elements(tmp_path):
    doc, _ = _run(tmp_path)
    assert any(e.type == "image"
               for e in doc.elements)


def test_image_resource_path(tmp_path):
    doc, _ = _run(tmp_path)
    img = [e for e in doc.elements
           if e.type == "image"][0]
    assert img.resource_path == "pic.png"


def test_image_does_not_break_sequence(tmp_path):
    doc, _ = _run(tmp_path)
    # c0000 含 image 之前的 4 个元素
    assert len(doc.chunks[0].source_element_ids) == 4


# ---------- heading 硬边界 ----------

def test_sub_starts_second_chunk(tmp_path):
    doc, _ = _run(tmp_path)
    assert doc.chunks[1].text == "Sub tail"


def test_sub_chunk_two_sources(tmp_path):
    doc, _ = _run(tmp_path)
    assert len(doc.chunks[1].source_element_ids) == 2


# ---------- 表格隔离 ----------

TABLE = """<html><body>
<h1>T</h1>
<p>lead in</p>
<table><tr><th>x</th><th>y</th></tr>
<tr><td>1</td><td>2</td></tr></table>
<p>after</p>
</body></html>
"""


def test_table_isolated_chunk(tmp_path):
    doc, errors = _run(tmp_path, html=TABLE)
    assert errors == []
    assert len(doc.chunks) == 3
    assert doc.chunks[1].metadata["strategy"] == \
        "isolated_table"


def test_table_keeps_md_render(tmp_path):
    doc, _ = _run(tmp_path, html=TABLE)
    assert doc.chunks[1].text == (
        "| x | y |\n| --- | --- |\n| 1 | 2 |")


def test_table_chunk_single_source(tmp_path):
    doc, _ = _run(tmp_path, html=TABLE)
    assert len(doc.chunks[1].source_element_ids) == 1


def test_after_table_new_buffer(tmp_path):
    doc, _ = _run(tmp_path, html=TABLE)
    assert doc.chunks[2].text == "after"


# ---------- 不丢不重 ----------

def test_no_loss_normalize(tmp_path):
    from app.chunkers import normalize_text
    doc, _ = _run(tmp_path)
    orig = " ".join(
        (e.content or "") for e in doc.elements
        if e.type != "image")
    joined = " ".join(c.text for c in doc.chunks)
    assert normalize_text(orig) == \
        normalize_text(joined)


def test_no_loss_with_table(tmp_path):
    from app.chunkers import normalize_text
    doc, _ = _run(tmp_path, html=TABLE)
    orig = " ".join(
        (e.content or "") for e in doc.elements
        if e.type != "image")
    joined = " ".join(c.text for c in doc.chunks)
    assert normalize_text(orig) == \
        normalize_text(joined)


# ---------- schema + 写盘 ----------

def test_html_doc_passes_schema(tmp_path):
    doc, errors = _run(tmp_path)
    assert errors == []
    from app.schema import validate
    validate(doc.to_dict())


def test_written_json_keeps_newline(tmp_path):
    _run(tmp_path)
    on_disk = json.loads(
        (tmp_path / "o.json").read_text(
            encoding="utf-8"))
    assert "line1\nbold\nline3" in \
        on_disk["chunks"][0]["text"]


def test_written_json_source_type(tmp_path):
    _run(tmp_path)
    on_disk = json.loads(
        (tmp_path / "o.json").read_text(
            encoding="utf-8"))
    assert on_disk["source_type"] == "html"


# ---------- chunk 元数据 ----------

def test_chunk_strategy_sequential(tmp_path):
    doc, _ = _run(tmp_path)
    for c in doc.chunks:
        assert c.metadata["strategy"] == \
            "sequential"


def test_chunk_char_count_matches(tmp_path):
    doc, _ = _run(tmp_path)
    for c in doc.chunks:
        assert c.metadata["char_count"] == \
            len(c.text)
