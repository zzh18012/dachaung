r"""pipeline image 元素细节：URL/data URI
src、重复不去重、confidence 0.9 与四图夹段
（Round 1749）。

新角度：R1748 锁 doc id 派生——**image
resource_path 原样保留（http:// 与
data:...;base64 均不处理）；重复 src 不去
重（两个元素）；image confidence 0.9 低
于文本 0.95；4 图夹在两段间不碍合并**
零覆盖：

- **URL+data URI 两图**：src 原样、
  metadata 仅 {'alt': ...}
- **同 src 两图**：e0003/e0004 都在，
  confidence 0.9、locator 有 line
- **p+4 图+p**：'a b'（2 ids）合并如常
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


IMGS = ('<img src="http://x/y.png" alt="U">'
        '<img src="data:image/png;base64,AAAA" alt="D">'
        '<img src="y.png" alt="S">'
        '<img src="y.png" alt="S2">')


def _run(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def test_url_and_data_uri_preserved(tmp_path):
    doc, errors = _run(tmp_path, IMGS)
    assert errors == []
    imgs = [e for e in doc.elements if e.type == "image"]
    assert [e.resource_path for e in imgs[:2]] == [
        "http://x/y.png",
        "data:image/png;base64,AAAA"]
    assert [e.metadata for e in imgs[:2]] == [
        {"alt": "U"}, {"alt": "D"}]


def test_duplicate_src_not_deduped(tmp_path):
    doc, errors = _run(tmp_path, IMGS)
    assert errors == []
    imgs = [e for e in doc.elements if e.type == "image"]
    assert len(imgs) == 4
    assert [e.resource_path for e in imgs[2:]] == [
        "y.png", "y.png"]
    assert len({e.element_id for e in imgs}) == 4
    assert all(e.confidence == 0.9 for e in imgs)
    assert all(e.source_locator == {"line": 1}
               for e in imgs)


def test_four_images_no_merge_interrupt(tmp_path):
    doc, errors = _run(
        tmp_path, "<p>a</p>" + IMGS + "<p>b</p>")
    assert errors == []
    assert len(doc.elements) == 6
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("a b", 2)]
