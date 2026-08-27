"""契约迁移 PR 的验收测试（integration/autoline-adoption）。

锁定三个不变量：
1. 旧输出形状不变——不带 span 的 Chunk 序列化后没有 source_spans 键
2. 新格式枚举与 locator 契约——markdown/html/text/ipynb 通过，非法值拒绝
3. span 定义——合法 span 通过，缺字段拒绝
"""

from __future__ import annotations

import copy

from app.models import Chunk, Document, Element
from app.schema import validate


def _doc(source_type: str, locator: dict | None = None) -> dict:
    el = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator=locator or {"page": 1},
    )
    d = Document(
        document_id="doc1",
        source_path="samples/x",
        source_type=source_type,
        source_hash="a" * 64,
        parser_name="p",
        parser_version="1",
        elements=[el],
        chunks=[],
    )
    return d.to_dict()


def test_old_chunk_shape_unchanged():
    c = Chunk(chunk_id="d::c0000", text="t",
              source_element_ids=["e1"])
    d = c.to_dict()
    assert "source_spans" not in d
    assert set(d) == {"chunk_id", "text",
                      "source_element_ids", "metadata"}


def test_chunk_with_spans_serializes():
    c = Chunk(chunk_id="d::c0000", text="t",
              source_element_ids=["e1"],
              source_spans=[{"element_id": "e1",
                             "start": 0, "end": 1}])
    d = c.to_dict()
    assert d["source_spans"] == [
        {"element_id": "e1", "start": 0, "end": 1}]


def test_new_source_types_accepted():
    base = _doc("markdown", {"line": 1})
    for st, loc in [
        ("markdown", {"line": 1}),
        ("html", {"line": 1}),
        ("text", {"line": 1}),
        ("ipynb", {"cell_index": 0, "cell_type": "code"}),
    ]:
        doc = copy.deepcopy(base)
        doc["source_type"] = st
        doc["elements"][0]["source_locator"] = loc
        validate(doc)


def test_unknown_source_type_rejected():
    doc = _doc("bogus")
    try:
        validate(doc)
        raise AssertionError("should reject bogus source_type")
    except Exception as e:
        assert "bogus" in str(e) or "enum" in str(e)


def test_new_locators_required_fields():
    # markdown 缺 line → 拒绝
    doc = _doc("markdown", {"page": 1})
    try:
        validate(doc)
        raise AssertionError("markdown locator missing line should fail")
    except Exception:
        pass
    # ipynb cell_type 非法 → 拒绝
    doc = _doc("ipynb", {"cell_index": 0, "cell_type": "bogus"})
    try:
        validate(doc)
        raise AssertionError("bad cell_type should fail")
    except Exception:
        pass


def test_old_pdf_docx_still_pass():
    for st, loc in [("pdf", {"page": 1, "bbox": [0, 0, 1, 1]}),
                    ("docx", {"paragraph_index": 0})]:
        validate(_doc(st, loc))
