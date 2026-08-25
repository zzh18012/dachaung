r"""pipeline Markdown 引用机制缺失与图片标题
（Round 1620）。

新角度：R1619 锁 docid/img src——**引用式链接/
图片、autolink、图片标题**零覆盖：

- **图片标题不剥离**：`![alt](src.png "the
  title")` → resource_path = 'src.png "the
  title"'（括号内整体原样）
- **引用定义不解析**：`[ref]: url` 定义行成
  普通段落；`![alt][ref]` 不解析为图片，原样
  成段落；`[text][ref]` 同样原样
- **autolink 原样**：`<http://…>` 不识别为
  链接，整体保留在段落文本中
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    return doc


def test_image_title_not_stripped(tmp_path):
    doc = _run(
        tmp_path,
        '![alt](src.png "the title")\n')
    assert [(e.type, e.content,
             e.resource_path, e.metadata)
            for e in doc.elements] == [
        ("image", None,
         'src.png "the title"',
         {"alt": "alt"})]


def test_reference_not_resolved(tmp_path):
    doc = _run(
        tmp_path,
        "[ref]: http://x/y.png\n\n"
        "![alt][ref]\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph",
         "[ref]: http://x/y.png"),
        ("paragraph", "![alt][ref]")]

    doc2 = _run(
        tmp_path,
        "[ref]: http://x/target\n\n"
        "See [text][ref] here\n")
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("paragraph",
         "[ref]: http://x/target"),
        ("paragraph",
         "See [text][ref] here")]


def test_autolink_raw(tmp_path):
    doc = _run(
        tmp_path,
        "See <http://example.com> now\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph",
         "See <http://example.com> now")]
