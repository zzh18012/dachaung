r"""pipeline document_id 内容派生与 img src
变体（Round 1619）。

新角度：R1618 锁成功警告——**document_id 与
文件名/扩展名无关**、**img src 变体**零覆盖：

- **document_id = f(内容字节)**：同内容不同
  文件名/扩展名（.md/.markdown）→ 同 id；内容
  变一字节 → 不同 id；element_id 共享 doc 前缀
- **img src 原样保留**：绝对 URL / 绝对路径 /
  data URI 均不处理；alt 缺省 ''；
  **src=""（空串）当无 src 丢弃**
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_document_id_content_derived(
        tmp_path):
    content = "# Same\n\nbody text\n"
    ids = []
    for name in ("a.md", "b.md",
                 "c.markdown"):
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        doc, errors = process_single(
            p, write_json=False,
            parser_name="markdown")
        assert errors == []
        ids.append(doc.document_id)
    assert ids[0] == ids[1] == ids[2]

    d = tmp_path / "d.md"
    d.write_text("# Different\n\nbody text\n",
                 encoding="utf-8")
    doc2, errors2 = process_single(
        d, write_json=False,
        parser_name="markdown")
    assert errors2 == []
    assert doc2.document_id != ids[0]

    doc3, _ = process_single(
        tmp_path / "a.md", write_json=False,
        parser_name="markdown")
    assert [e.element_id
            for e in doc3.elements] == [
        ids[0] + "::e0000",
        ids[0] + "::e0001"]


def test_img_src_variants(tmp_path):
    p = tmp_path / "i.html"
    p.write_text(
        '<img src="http://example.com/x.png">'
        '<img src="/abs/path.png">'
        '<img src="data:image/png;base64,iVBOR">'
        '<img src=""><p>t</p>',
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    got = [(e.type, e.resource_path,
            e.metadata)
           for e in doc.elements]
    assert got == [
        ("image",
         "http://example.com/x.png",
         {"alt": ""}),
        ("image", "/abs/path.png",
         {"alt": ""}),
        ("image",
         "data:image/png;base64,iVBOR",
         {"alt": ""}),
        ("paragraph", None, {})]
    assert [c.text for c in doc.chunks] == ["t"]
