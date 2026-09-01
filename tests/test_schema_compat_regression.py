"""Schema 双向兼容回归测试（批次 8 技术债清理之④）。

裁决要求（ADOPTION §三十三，批次 8 任务 4）：
- 读兼容（旧→新）：0.1.0–0.5.0 各时代形状的文档必须能被当前 schema
  校验通过（旧产物永远合法读入，docs/schema-version-policy.md §4）。
- 写能力（新）：当前 writer 一律输出 0.6.0，不再产出任何旧版本。
- 消费兼容（新→旧）：0.5.0 文档喂给"只认识旧 relation type 集"的模拟
  旧 consumer，应优雅降级——跳过未知 type，不报错、不误读。
"""

from __future__ import annotations

from app.models import Document, Element, Relation, Chunk
from app.schema import validate as validate_udm


# ---------- 读兼容：各历史版本时代形状 ----------

def _doc(version: str, source_type: str, locator: dict, *,
         spans: bool = False, relation: dict | None = None) -> dict:
    chunk: dict = {
        "chunk_id": "d::c0000",
        "text": "t",
        "source_element_ids": ["e1"],
        "metadata": {},
    }
    if spans:
        chunk["source_spans"] = [{"element_id": "e1", "start": 0, "end": 1}]
    return {
        "schema_version": version,
        "document_id": "doc1",
        "source_path": "samples/x",
        "source_type": source_type,
        "source_hash": "a" * 64,
        "parser_name": "p",
        "parser_version": "1",
        "elements": [{
            "element_id": "e1", "type": "paragraph", "parent_id": None,
            "source_locator": locator, "content": "x", "resource_path": None,
            "confidence": 1.0, "metadata": {},
        }],
        "chunks": [chunk],
        "relations": [relation] if relation else [],
        "warnings": [], "errors": [], "metadata": {},
    }


def test_v010_pdf_era_shape_still_validates():
    validate_udm(_doc("0.1.0", "pdf", {"page": 1, "bbox": [0, 0, 1, 1]}))


def test_v010_docx_era_shape_still_validates():
    validate_udm(_doc("0.1.0", "docx", {"paragraph_index": 0}))


def test_v020_spans_era_shape_still_validates():
    validate_udm(
        _doc("0.2.0", "docx", {"paragraph_index": 0}, spans=True)
    )


def test_v030_family_era_shape_still_validates():
    validate_udm(_doc(
        "0.3.0", "docx",
        {"family": "structural_index", "paragraph_index": 0},
    ))


def test_v040_has_caption_era_shape_still_validates():
    validate_udm(_doc(
        "0.4.0", "docx",
        {"family": "structural_index", "paragraph_index": 0},
        relation={"type": "has_caption", "from_id": "e1", "to_id": "e1",
                  "metadata": {"rule": "docx_adjacent_paragraph"}},
    ))


def test_v050_both_relation_types_validates():
    validate_udm(_doc(
        "0.5.0", "docx",
        {"family": "structural_index", "paragraph_index": 0},
        relation={"type": "table_has_caption", "from_id": "e1",
                  "to_id": "e1",
                  "metadata": {"rule": "docx_adjacent_element_above"}},
    ))


# ---------- 写能力：当前 writer 只产 0.6.0 ----------

def test_writer_emits_only_current_version():
    d = Document(
        document_id="doc1", source_path="samples/x", source_type="pdf",
        source_hash="a" * 64, parser_name="p", parser_version="1",
        elements=[Element(element_id="e1", type="paragraph", content="x",
                          source_locator={"family": "page_geometry",
                                          "page": 1})],
        chunks=[Chunk(chunk_id="d::c0000", text="t",
                      source_element_ids=["e1"])],
        relations=[Relation(type="has_caption", from_id="e1", to_id="e1")],
    ).to_dict()
    assert d["schema_version"] == "0.6.0"
    validate_udm(d)


# ---------- 消费兼容：模拟旧 consumer 优雅降级 ----------

def _relation_endpoint_doc() -> dict:
    """0.5.0 文档：table e1 + 表题注 e2 + image e3 + 图题注 e4，
    同时含 table_has_caption 与 has_caption 两类 relation。"""
    els = [
        {"element_id": "e1", "type": "table", "parent_id": None,
         "source_locator": {"family": "structural_index",
                            "table_index": 0},
         "content": "a b", "resource_path": None,
         "confidence": 1.0, "metadata": {}},
        {"element_id": "e2", "type": "caption", "parent_id": None,
         "source_locator": {"family": "structural_index",
                            "paragraph_index": 1},
         "content": "Table 1. matrix", "resource_path": None,
         "confidence": 1.0, "metadata": {}},
        {"element_id": "e3", "type": "image", "parent_id": None,
         "source_locator": {"family": "structural_index",
                            "paragraph_index": 2},
         "content": None, "resource_path": "img.png",
         "confidence": 1.0, "metadata": {}},
        {"element_id": "e4", "type": "caption", "parent_id": None,
         "source_locator": {"family": "structural_index",
                            "paragraph_index": 3},
         "content": "Figure 1. flow", "resource_path": None,
         "confidence": 1.0, "metadata": {}},
    ]
    return {
        "schema_version": "0.5.0",
        "document_id": "doc1", "source_path": "samples/x",
        "source_type": "docx", "source_hash": "a" * 64,
        "parser_name": "p", "parser_version": "1",
        "elements": els,
        "chunks": [], "warnings": [], "errors": [], "metadata": {},
        "relations": [
            {"type": "has_caption", "from_id": "e3", "to_id": "e4",
             "metadata": {"rule": "docx_adjacent_paragraph"}},
            {"type": "table_has_caption", "from_id": "e1", "to_id": "e2",
             "metadata": {"rule": "docx_adjacent_element_above"}},
        ],
    }


def test_old_consumer_skips_unknown_relation_type():
    """批次 6 时代的 consumer 只认识 has_caption：0.5.0 文档中的
    table_has_caption 应被跳过（优雅降级），不报错、不误读。"""
    doc = _relation_endpoint_doc()
    known = {"has_caption"}  # 批次 6 consumer 的 type 集
    visible = [r for r in doc["relations"] if r["type"] in known]
    assert len(visible) == 1
    assert visible[0]["type"] == "has_caption"


def test_real_evaluator_path_ignores_unknown_type():
    """真实 evaluator 路径（match_relation_pairs 按 relation_type 过滤）
    在混排 0.5.0 文档上只统计目标 type：旧调用方式行为不变。"""
    from evaluation.annotation_metrics import match_relation_pairs

    doc = _relation_endpoint_doc()
    pairs = [{"figure_marker": "img", "caption_text": "Figure 1. flow"}]
    counts = match_relation_pairs(
        doc, pairs, relation_type="has_caption",
        from_marker_key="figure_marker", to_marker_key="caption_text",
    )
    assert counts == (1, 1, 1)  # table_has_caption 不计入 has_caption 预测


def test_doc_with_only_unknown_type_degrades_to_zero_predictions():
    """只含 table_has_caption 的 0.5.0 文档喂给旧 consumer 路径：
    has_caption 视角预测为 0，按契约降级（no_predicted_relations），
    不崩溃。"""
    from evaluation.annotation_metrics import match_relation_pairs

    doc = _relation_endpoint_doc()
    doc["relations"] = [r for r in doc["relations"]
                        if r["type"] == "table_has_caption"]
    counts = match_relation_pairs(
        doc, [{"figure_marker": "img", "caption_text": "Figure 1."}],
        relation_type="has_caption",
        from_marker_key="figure_marker", to_marker_key="caption_text",
    )
    assert counts == (0, 1, 0)
