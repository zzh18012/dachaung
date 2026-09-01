"""图片 caption 关联契约测试（Stage 6 批次 4）。

契约：docs/caption-relation-contract.md。逐条映射：
- §1 图题注前缀集（ASCII 数字；Table/表 排除）
- §2 形状与排序（type/from/to 方向、metadata.rule、(type,from,to) 排序）
- §3 docx 紧邻下一段规则；pdf 同页下方几何 + 唯一贪心配对
- §4 版本分支（≤0.3.0 拒 has_caption relation；0.4.0 含/不含均合法；
  family const 在 0.4.0 延续）
- §5 不变量：md/html/text/ipynb 零 has_caption；devset 真样本方向与
  rule 值
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models import Element
from app.parsers.fallback_parser import (
    CAPTION_MAX_GAP_PT,
    match_caption_relations_docx,
    match_caption_relations_pdf,
)
from app.schema import validate as validate_udm

ROOT = Path(__file__).resolve().parent.parent


def _el(eid: str, etype: str, content: str, locator: dict) -> Element:
    return Element(
        element_id=eid, type=etype, content=content or None,
        resource_path=None if content else "x.png",
        source_locator=locator,
    )


def _img(eid: str, locator: dict) -> Element:
    return _el(eid, "image", "", locator)


def _cap(eid: str, content: str, locator: dict) -> Element:
    return _el(eid, "caption", content, locator)


def _rels(rels) -> list[dict]:
    return [
        {"type": r.type, "from_id": r.from_id, "to_id": r.to_id,
         "metadata": r.metadata}
        for r in rels
    ]


# ---------- §3 docx：紧邻下一段 ----------

def test_docx_adjacent_paragraph_hits():
    els = [
        _img("i1", {"family": "structural_index", "paragraph_index": 3}),
        _cap("c1", "Figure 1. flow",
             {"family": "structural_index", "paragraph_index": 4}),
    ]
    assert _rels(match_caption_relations_docx(els)) == [
        {"type": "has_caption", "from_id": "i1", "to_id": "c1",
         "metadata": {"rule": "docx_adjacent_paragraph"}},
    ]


def test_docx_caption_above_not_matched():
    els = [
        _cap("c1", "Figure 1. flow",
             {"family": "structural_index", "paragraph_index": 3}),
        _img("i1", {"family": "structural_index", "paragraph_index": 4}),
    ]
    assert match_caption_relations_docx(els) == []


def test_docx_table_prefix_not_figure_caption():
    els = [
        _img("i1", {"family": "structural_index", "paragraph_index": 3}),
        _cap("c1", "Table 1. matrix",
             {"family": "structural_index", "paragraph_index": 4}),
        _cap("c2", "表 1 矩阵",
             {"family": "structural_index", "paragraph_index": 5}),
    ]
    assert match_caption_relations_docx(els) == []


def test_docx_no_caption_no_relation():
    els = [
        _img("i1", {"family": "structural_index", "paragraph_index": 3}),
        _el("p1", "paragraph", "plain",
            {"family": "structural_index", "paragraph_index": 4}),
    ]
    assert match_caption_relations_docx(els) == []


def test_docx_two_images_share_next_slot_only_closest_index_wins():
    """图@3 与图@4，题注@5：只有 paragraph_index 恰为 4 的图命中。"""
    els = [
        _img("i1", {"family": "structural_index", "paragraph_index": 3}),
        _img("i2", {"family": "structural_index", "paragraph_index": 4}),
        _cap("c1", "Figure 2. flow",
             {"family": "structural_index", "paragraph_index": 5}),
    ]
    assert _rels(match_caption_relations_docx(els)) == [
        {"type": "has_caption", "from_id": "i2", "to_id": "c1",
         "metadata": {"rule": "docx_adjacent_paragraph"}},
    ]


# ---------- §3 pdf：同页下方几何 ----------

def _ploc(page: int, x0: float, top: float, x1: float, bottom: float) -> dict:
    return {"family": "page_geometry", "page": page, "bbox": [x0, top, x1, bottom]}


def test_pdf_geometry_below_hits_with_gap():
    els = [
        _img("i1", _ploc(2, 84.6, 134.4, 527.4, 330.5)),
        _cap("c1", "Figure 1. flow", _ploc(2, 72.1, 342.0, 511.1, 388.75)),
    ]
    rels = _rels(match_caption_relations_pdf(els))
    assert len(rels) == 1
    r = rels[0]
    assert r["type"] == "has_caption" and r["from_id"] == "i1" and r["to_id"] == "c1"
    assert r["metadata"]["rule"] == "pdf_geometry_below"
    assert r["metadata"]["gap_pt"] == pytest.approx(342.0 - 330.5)


def test_pdf_gap_zero_rejected():
    els = [
        _img("i1", _ploc(1, 0, 0, 100, 50)),
        _cap("c1", "Figure 1. x", _ploc(1, 0, 50, 100, 80)),
    ]
    assert match_caption_relations_pdf(els) == []


def test_pdf_gap_over_threshold_rejected():
    els = [
        _img("i1", _ploc(1, 0, 0, 100, 50)),
        _cap("c1", "Figure 1. x", _ploc(1, 0, 50 + CAPTION_MAX_GAP_PT + 0.1, 100, 200)),
    ]
    assert match_caption_relations_pdf(els) == []


def test_pdf_caption_above_image_rejected():
    els = [
        _img("i1", _ploc(1, 0, 100, 100, 150)),
        _cap("c1", "Figure 1. x", _ploc(1, 0, 50, 100, 90)),
    ]
    assert match_caption_relations_pdf(els) == []


def test_pdf_no_x_overlap_rejected():
    els = [
        _img("i1", _ploc(1, 0, 0, 100, 50)),
        _cap("c1", "Figure 1. x", _ploc(1, 150, 10, 250, 40)),
    ]
    assert match_caption_relations_pdf(els) == []


def test_pdf_different_page_rejected():
    els = [
        _img("i1", _ploc(1, 0, 0, 100, 50)),
        _cap("c1", "Figure 1. x", _ploc(3, 0, 10, 100, 40)),
    ]
    assert match_caption_relations_pdf(els) == []


def test_pdf_two_images_compete_smallest_gap_wins():
    els = [
        _img("i_far", _ploc(1, 0, 0, 100, 10)),
        _img("i_near", _ploc(1, 0, 0, 100, 40)),
        _cap("c1", "Figure 1. x", _ploc(1, 0, 50, 100, 80)),
    ]
    rels = _rels(match_caption_relations_pdf(els))
    assert [(r["from_id"], r["to_id"]) for r in rels] == [("i_near", "c1")]


def test_pdf_two_captions_compete_smallest_gap_wins():
    els = [
        _img("i1", _ploc(1, 0, 0, 100, 50)),
        _cap("c_near", "Figure 1. x", _ploc(1, 0, 52, 100, 70)),
        _cap("c_far", "Figure 2. y", _ploc(1, 0, 90, 100, 120)),
    ]
    rels = _rels(match_caption_relations_pdf(els))
    assert [(r["from_id"], r["to_id"]) for r in rels] == [("i1", "c_near")]


def test_pdf_output_sorted_by_from_id():
    els = [
        _img("i_b", _ploc(1, 0, 0, 100, 10)),
        _img("i_a", _ploc(1, 0, 0, 100, 10)),
        _cap("c2", "Figure 2. y", _ploc(1, 0, 12, 100, 30)),
        _cap("c1", "Figure 1. x", _ploc(1, 0, 12, 100, 30)),
    ]
    rels = _rels(match_caption_relations_pdf(els))
    # 各图各得一个 caption（端点不重复），输出按 (type, from, to) 排序
    assert [(r["from_id"], r["to_id"]) for r in rels] == sorted(
        [(r["from_id"], r["to_id"]) for r in rels]
    )
    assert len(rels) == 2


# ---------- §4 版本分支 ----------

def _udm_with_relation(version: str, relation: dict | None) -> dict:
    doc = {
        "schema_version": version,
        "document_id": "doc1",
        "source_path": "samples/x.pdf",
        "source_type": "pdf",
        "source_hash": "a" * 64,
        "parser_name": "p",
        "parser_version": "1",
        "elements": [{
            "element_id": "e1", "type": "paragraph", "parent_id": None,
            "source_locator": {"family": "page_geometry", "page": 1},
            "content": "x", "resource_path": None,
            "confidence": 1.0, "metadata": {},
        }],
        "chunks": [],
        "relations": [relation] if relation else [],
        "warnings": [], "errors": [], "metadata": {},
    }
    return doc


_HAS_CAPTION_RELATION = {
    "type": "has_caption", "from_id": "i1", "to_id": "c1",
    "metadata": {"rule": "pdf_geometry_below", "gap_pt": 11.5},
}


@pytest.mark.parametrize("version", ["0.1.0", "0.2.0", "0.3.0"])
def test_old_versions_reject_has_caption_relation(version):
    with pytest.raises(Exception):
        validate_udm(_udm_with_relation(version, _HAS_CAPTION_RELATION))


def test_040_accepts_has_caption_relation():
    validate_udm(_udm_with_relation("0.4.0", _HAS_CAPTION_RELATION))


def test_040_empty_relations_valid():
    validate_udm(_udm_with_relation("0.4.0", None))


def test_040_keeps_family_const_enforcement():
    doc = _udm_with_relation("0.4.0", None)
    del doc["elements"][0]["source_locator"]["family"]
    with pytest.raises(Exception):
        validate_udm(doc)


def test_unknown_version_still_rejected():
    with pytest.raises(Exception):
        validate_udm(_udm_with_relation("0.7.0", None))


# ---------- §5 不变量：无 caption 来源零 relation ----------

def test_non_fallback_parsers_emit_no_has_caption(tmp_path: Path):
    from app.parsers.html_parser import HtmlParser
    from app.parsers.ipynb_parser import IpynbParser
    from app.parsers.markdown_parser import MarkdownParser
    from app.parsers.text_parser import TextParser
    import json

    cases = []
    md = tmp_path / "a.md"
    md.write_text("![alt](i.png)\n\nFigure 1. not a caption element\n",
                  encoding="utf-8")
    cases.append(MarkdownParser().parse(md, source_hash="a" * 64))
    html = tmp_path / "a.html"
    html.write_text("<img src='i.png'>\n<p>Figure 1. plain text</p>",
                    encoding="utf-8")
    cases.append(HtmlParser().parse(html, source_hash="a" * 64))
    txt = tmp_path / "a.txt"
    txt.write_text("Figure 1. plain\n", encoding="utf-8")
    cases.append(TextParser().parse(txt, source_hash="a" * 64))
    nb = tmp_path / "a.ipynb"
    nb.write_text(json.dumps({
        "nbformat": 4, "nbformat_minor": 5, "metadata": {},
        "cells": [
            {"cell_type": "markdown",
             "source": ["![alt](i.png)", "", "Figure 1. plain"]},
            {"cell_type": "code", "source": ["print(1)"]},
        ],
    }), encoding="utf-8")
    cases.append(IpynbParser().parse(nb, source_hash="a" * 64))
    for doc in cases:
        assert doc.relations == []


# ---------- §6 devset 真样本（skip-if-missing） ----------

def _devset_entry(source_type: str):
    devset = ROOT / "samples/private/devset/manifest.json"
    if not devset.is_file():
        pytest.skip("samples/private 为本机资产，不存在时跳过")
    from evaluation.manifest import load_manifest
    m = load_manifest(devset, project_root=ROOT)
    return next((d for d in m.documents if d.source_type == source_type), None)


def test_devset_docx_figure_relation():
    entry = _devset_entry("docx")
    if entry is None:
        pytest.skip("devset 无 docx 样本")
    from app.parsers.fallback_parser import FallbackParser
    doc = FallbackParser().parse(entry.resolved_path, source_hash="a" * 64)
    rels = _rels(doc.relations)
    assert rels == [
        {
            "type": "has_caption",
            "from_id": doc.document_id + "::e0018",
            "to_id": doc.document_id + "::e0019",
            "metadata": {"rule": "docx_adjacent_paragraph"},
        },
        {
            "type": "table_has_caption",
            "from_id": doc.document_id + "::e0013",
            "to_id": doc.document_id + "::e0012",
            "metadata": {"rule": "docx_adjacent_element_above"},
        },
    ]
    d = doc.to_dict()
    assert d["schema_version"] == "0.6.0"
    validate_udm(d)


def test_devset_pdf_figure_relation():
    entry = _devset_entry("pdf")
    if entry is None:
        pytest.skip("devset 无 pdf 样本")
    from app.parsers.fallback_parser import FallbackParser
    doc = FallbackParser().parse(entry.resolved_path, source_hash="a" * 64)
    rels = _rels(doc.relations)
    assert len(rels) == 1
    r = rels[0]
    assert r["type"] == "has_caption"
    assert r["from_id"] == doc.document_id + "::e0011"
    assert r["to_id"] == doc.document_id + "::e0009"
    assert r["metadata"]["rule"] == "pdf_geometry_below"
    assert r["metadata"]["gap_pt"] == pytest.approx(342.025 - 330.5, abs=0.1)
    validate_udm(doc.to_dict())
