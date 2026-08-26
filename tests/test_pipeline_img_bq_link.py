r"""pipeline 引用内图片 raw 与链接内图片提取
（Round 1674）。

新角度：R1673 锁围栏闭合变体——**blockquote
内图片语法不解析、&lt;a&gt; 内 img 照常提
取**零覆盖：

- **引用内图片 raw**：'&gt; ![alt](x.png)'
  → blockquote 段原样，无 image 元素
- **文字+图片混排引用**：全部原样保留
- **a 内 img**：链接包装透明，image 正常
  产出（alt 保留）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_img_in_blockquote_raw(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("> ![alt](x.png)\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "![alt](x.png)",
         {"kind": "blockquote"})]


def test_bq_mixed_text_img_raw(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "> before ![alt](x.png) after\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "before ![alt](x.png) after",
         {"kind": "blockquote"})]


def test_img_in_link_extracted(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<a><img src='x.png' alt='A'></a>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("image", None, {"alt": "A"})]
