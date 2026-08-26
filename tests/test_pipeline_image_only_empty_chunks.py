r"""pipeline 纯图文档：chunks 空列表合法
与零 chunk JSON 过 schema（Round 1765）。

新角度：R1764 锁空表——**只有 image 元素
的文档成功返回（非 None）：elements N、
chunks []（空列表）、无警告；零 chunk
JSON 照常落盘且过 schema 校验**零覆盖：

- **两图无文**：chunks == []、errors []
- **落盘 JSON**：data['chunks'] == []
  且 validate 通过
- **两图夹一段**：恰好 1 chunk（旁路另一
  侧印证）
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single
from app.schema import validate


def test_image_only_empty_chunk_list(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "![a](a.png)\n\n![b](b.png)\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "image", "image"]
    assert doc.chunks == []
    assert doc.warnings == []


def test_zero_chunk_json_validates(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("![a](a.png)\n", encoding="utf-8")
    out = tmp_path / "o.json"
    doc, errors = process_single(
        p, output_path=out, parser_name="markdown")
    assert errors == []
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["chunks"] == []
    validate(data)


def test_images_around_one_paragraph(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "![a](a.png)\n\nmid\n\n![b](b.png)\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert len(doc.elements) == 3
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("mid", 1)]
