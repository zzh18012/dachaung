"""表格题注关联契约测试（Stage 6 批次 7）。

契约：docs/table-caption-relation-contract.md。逐条映射：
- §2 表题注前缀集（^(?:Table|表格|表)\\s*[0-9]+[\\.、\\s]；与图题注互斥）
- §3 docx 紧邻上一元素规则（表题注在表上方）；pdf 同页上方几何 +
  唯一贪心配对（批次 4 下方规则的镜像）
- §4 版本分支（0.4.0 拒 table_has_caption；0.5.0 含/不含均合法；
  ≤0.3.0 双拒 has_caption 与 table_has_caption）；两类 type 混排排序
- §6 评测消费路径：合成 docx → fallback 解析 → match_relation_pairs(
  relation_type="table_has_caption")（签名冻结，仅传新 type）
- §6 dev 验收（skipif 无私样）：DC-MVP-001 docx e0013→e0012；PDF 零
  表关联（§0 归因：题注文本被融合进段落）；md/html/text/ipynb 零回归
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models import Element
from app.parsers.fallback_parser import (
    CAPTION_MAX_GAP_PT,
    _sort_relations,
    match_caption_relations_pdf,
    match_table_caption_relations_docx,
    match_table_caption_relations_pdf,
)
from app.schema import validate as validate_udm

ROOT = Path(__file__).resolve().parent.parent


def _el(eid: str, etype: str, content: str, locator: dict) -> Element:
    return Element(
        element_id=eid, type=etype, content=content or None,
        resource_path=None if content else "x.png",
        source_locator=locator,
    )


def _tbl(eid: str, locator: dict) -> Element:
    return _el(eid, "table", "a b", locator)


def _cap(eid: str, content: str, locator: dict) -> Element:
    return _el(eid, "caption", content, locator)


def _rels(rels) -> list[dict]:
    return [
        {"type": r.type, "from_id": r.from_id, "to_id": r.to_id,
         "metadata": r.metadata}
        for r in rels
    ]


def _ploc(page: int, x0: float, top: float, x1: float, bottom: float) -> dict:
    return {"family": "page_geometry", "page": page, "bbox": [x0, top, x1, bottom]}


# ---------- §2 表题注前缀集 ----------

@pytest.mark.parametrize("text", [
    "Table 1. Module status matrix",
    "table 2 overview",           # IGNORECASE
    "表格 3、说明",
    "表4 支出",
    "Table 5、混合",
])
def test_prefix_set_hits(text):
    els = [
        _cap("c1", text, {"family": "structural_index", "paragraph_index": 0}),
        _tbl("t1", {"family": "structural_index", "table_index": 0}),
    ]
    assert len(match_table_caption_relations_docx(els)) == 1


@pytest.mark.parametrize("text", [
    "Table A. 非数字",            # 数字限 ASCII
    "Tab 1. 前缀不足",
    "Tables 1. 复数",
    "Figure 1. flow",             # 图题注前缀（互斥）
    "Fig 2. flow",
    "图 3 流程",
    "Table 1overview",            # 数字后必须有 [\.、\s]
])
def test_prefix_set_misses(text):
    els = [
        _cap("c1", text, {"family": "structural_index", "paragraph_index": 0}),
        _tbl("t1", {"family": "structural_index", "table_index": 0}),
    ]
    assert match_table_caption_relations_docx(els) == []


# ---------- §3 docx：紧邻上一元素（表题注在表上方） ----------

def test_docx_adjacent_element_above_hits():
    els = [
        _el("p0", "paragraph", "intro",
            {"family": "structural_index", "paragraph_index": 0}),
        _cap("c1", "Table 1. Module status matrix",
             {"family": "structural_index", "paragraph_index": 1}),
        _tbl("t1", {"family": "structural_index", "table_index": 0}),
    ]
    assert _rels(match_table_caption_relations_docx(els)) == [
        {"type": "table_has_caption", "from_id": "t1", "to_id": "c1",
         "metadata": {"rule": "docx_adjacent_element_above"}},
    ]


def test_docx_caption_below_table_not_matched():
    """表题注惯例在表上方（§0 devset 实证）；下方不生成。"""
    els = [
        _tbl("t1", {"family": "structural_index", "table_index": 0}),
        _cap("c1", "Table 1. x",
             {"family": "structural_index", "paragraph_index": 1}),
    ]
    assert match_table_caption_relations_docx(els) == []


def test_docx_prev_not_caption_no_relation():
    els = [
        _el("p0", "paragraph", "plain",
            {"family": "structural_index", "paragraph_index": 0}),
        _tbl("t1", {"family": "structural_index", "table_index": 0}),
    ]
    assert match_table_caption_relations_docx(els) == []


def test_docx_figure_prefix_caption_not_table_relation():
    """图题注紧邻表上方：前缀互斥，不命中（§6 holdout T4 负例）。"""
    els = [
        _cap("c1", "Figure 1. flow",
             {"family": "structural_index", "paragraph_index": 0}),
        _tbl("t1", {"family": "structural_index", "table_index": 0}),
    ]
    assert match_table_caption_relations_docx(els) == []


def test_docx_table_at_first_position_no_relation():
    els = [
        _tbl("t1", {"family": "structural_index", "table_index": 0}),
    ]
    assert match_table_caption_relations_docx(els) == []


def test_docx_caption_used_by_at_most_one_table():
    """[caption, t1, t2]：仅 t1 的前邻是题注；t2 前邻是 t1 不生成。"""
    els = [
        _cap("c1", "Table 1. x",
             {"family": "structural_index", "paragraph_index": 0}),
        _tbl("t1", {"family": "structural_index", "table_index": 0}),
        _tbl("t2", {"family": "structural_index", "table_index": 1}),
    ]
    rels = _rels(match_table_caption_relations_docx(els))
    assert [(r["from_id"], r["to_id"]) for r in rels] == [("t1", "c1")]


# ---------- §3 pdf：同页上方几何 ----------

def test_pdf_geometry_above_hits_with_gap():
    els = [
        _cap("c1", "Table 1. x", _ploc(2, 72.1, 342.0, 511.1, 388.75)),
        _tbl("t1", _ploc(2, 84.6, 391.0, 527.4, 470.5)),
    ]
    rels = _rels(match_table_caption_relations_pdf(els))
    assert rels == [{
        "type": "table_has_caption", "from_id": "t1", "to_id": "c1",
        "metadata": {"rule": "pdf_geometry_above", "gap_pt": 391.0 - 388.75},
    }]


def test_pdf_caption_below_table_not_matched():
    els = [
        _tbl("t1", _ploc(1, 0, 0, 100, 50)),
        _cap("c1", "Table 1. x", _ploc(1, 0, 52, 100, 70)),
    ]
    assert match_table_caption_relations_pdf(els) == []


def test_pdf_gap_over_threshold_not_matched():
    gap = CAPTION_MAX_GAP_PT + 0.5
    els = [
        _cap("c1", "Table 1. x", _ploc(1, 0, 0, 100, 10)),
        _tbl("t1", _ploc(1, 0, 10 + gap, 100, 200)),
    ]
    assert match_table_caption_relations_pdf(els) == []


def test_pdf_touching_bbox_gap_zero_not_matched():
    els = [
        _cap("c1", "Table 1. x", _ploc(1, 0, 0, 100, 10)),
        _tbl("t1", _ploc(1, 0, 10, 100, 200)),
    ]
    assert match_table_caption_relations_pdf(els) == []


def test_pdf_no_x_overlap_not_matched():
    els = [
        _cap("c1", "Table 1. x", _ploc(1, 0, 0, 40, 10)),
        _tbl("t1", _ploc(1, 50, 12, 100, 200)),
    ]
    assert match_table_caption_relations_pdf(els) == []


def test_pdf_different_page_not_matched():
    els = [
        _cap("c1", "Table 1. x", _ploc(1, 0, 0, 100, 10)),
        _tbl("t1", _ploc(2, 0, 12, 100, 200)),
    ]
    assert match_table_caption_relations_pdf(els) == []


def test_pdf_two_tables_compete_smallest_gap_wins():
    els = [
        _cap("c1", "Table 1. x", _ploc(1, 0, 0, 100, 10)),
        _tbl("t_far", _ploc(1, 0, 44, 100, 200)),
        _tbl("t_near", _ploc(1, 0, 14, 100, 200)),
    ]
    rels = _rels(match_table_caption_relations_pdf(els))
    assert [(r["from_id"], r["to_id"]) for r in rels] == [("t_near", "c1")]


def test_pdf_two_captions_compete_smallest_gap_wins():
    els = [
        _cap("c_far", "Table 1. x", _ploc(1, 0, 0, 100, 10)),
        _cap("c_near", "Table 2. y", _ploc(1, 0, 30, 100, 40)),
        _tbl("t1", _ploc(1, 0, 42, 100, 200)),
    ]
    rels = _rels(match_table_caption_relations_pdf(els))
    assert [(r["from_id"], r["to_id"]) for r in rels] == [("t1", "c_near")]


def test_pdf_no_table_no_caption_zero_relations():
    els = [
        _el("p1", "paragraph", "x", _ploc(1, 0, 0, 100, 10)),
    ]
    assert match_table_caption_relations_pdf(els) == []
    assert match_table_caption_relations_docx(els) == []


# ---------- §4 两类 type 混排排序 ----------

def test_mixed_types_sorted_by_type_from_to():
    """parse() 的 wiring 表达式：两类 relation 合并后 (type, from, to) 字典序。"""
    els = [
        _cap("c1", "Table 1. x", _ploc(1, 0, 0, 100, 10)),
        _tbl("t1", _ploc(1, 0, 12, 100, 200)),
        _el("i1", "image", "", _ploc(1, 0, 40, 100, 50)),
        _cap("c2", "Figure 2. y", _ploc(1, 0, 52, 100, 62)),
    ]
    combined = _sort_relations(
        match_caption_relations_pdf(els) + match_table_caption_relations_pdf(els)
    )
    rels = _rels(combined)
    keys = [(r["type"], r["from_id"], r["to_id"]) for r in rels]
    assert keys == sorted(keys)
    assert len(rels) == 2
    assert keys[0][0] == "has_caption"      # h < t
    assert keys[1][0] == "table_has_caption"


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


_TABLE_CAPTION_RELATION = {
    "type": "table_has_caption", "from_id": "t1", "to_id": "c1",
    "metadata": {"rule": "pdf_geometry_above", "gap_pt": 12.5},
}

_HAS_CAPTION_RELATION = {
    "type": "has_caption", "from_id": "i1", "to_id": "c1",
    "metadata": {"rule": "pdf_geometry_below", "gap_pt": 11.5},
}


def test_040_rejects_table_has_caption():
    with pytest.raises(Exception):
        validate_udm(_udm_with_relation("0.4.0", _TABLE_CAPTION_RELATION))


def test_050_accepts_with_table_has_caption():
    validate_udm(_udm_with_relation("0.5.0", _TABLE_CAPTION_RELATION))


def test_050_accepts_without_relations():
    validate_udm(_udm_with_relation("0.5.0", None))


@pytest.mark.parametrize("relation", [_TABLE_CAPTION_RELATION, _HAS_CAPTION_RELATION])
def test_030_rejects_both_relation_types(relation):
    """≤0.3.0 双拒：relations 字段激活前（批次 4）的旧产物不含任何
    relation，两类都不允许出现。"""
    with pytest.raises(Exception):
        validate_udm(_udm_with_relation("0.3.0", relation))


# ---------- §5 Determinism ----------

def test_same_input_same_relations_docx():
    els = [
        _cap("c1", "表 1 模块状态",
             {"family": "structural_index", "paragraph_index": 1}),
        _tbl("t1", {"family": "structural_index", "table_index": 0}),
    ]
    assert _rels(match_table_caption_relations_docx(els)) == _rels(
        match_table_caption_relations_docx(list(els))
    )


# ---------- §6 评测消费路径（裁决步骤④：签名不改，仅传新 type） ----------

def _synthetic_table_docx(tmp_path: Path) -> Path:
    docx = pytest.importorskip("docx")
    d = docx.Document()
    d.add_paragraph("Intro paragraph.")
    d.add_paragraph("Table 1. Module status matrix")
    table = d.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "AlphaCell"
    table.cell(0, 1).text = "BetaCell"
    p = tmp_path / "synthetic_table.docx"
    d.save(str(p))
    return p


def test_evaluator_consumes_table_has_caption(tmp_path: Path):
    from app.parsers.fallback_parser import FallbackParser
    from evaluation.annotation_metrics import match_relation_pairs

    doc = FallbackParser().parse(
        _synthetic_table_docx(tmp_path), source_hash="a" * 64
    )
    d = doc.to_dict()
    assert d["schema_version"] == "0.5.0"
    validate_udm(d)
    table_rels = [r for r in d["relations"] if r["type"] == "table_has_caption"]
    assert len(table_rels) == 1

    pairs = [{"table_marker": "AlphaCell",
              "table_caption_text": "Table 1. Module status matrix"}]
    counts = match_relation_pairs(
        d, pairs,
        relation_type="table_has_caption",
        from_marker_key="table_marker",
        to_marker_key="table_caption_text",
    )
    assert counts == (1, 1, 1)


def test_evaluator_table_has_caption_zero_match_on_wrong_marker(tmp_path: Path):
    from app.parsers.fallback_parser import FallbackParser
    from evaluation.annotation_metrics import match_relation_pairs

    d = FallbackParser().parse(
        _synthetic_table_docx(tmp_path), source_hash="a" * 64
    ).to_dict()
    counts = match_relation_pairs(
        d, [{"table_marker": "NoSuchCell", "table_caption_text": "Table 1."}],
        relation_type="table_has_caption",
        from_marker_key="table_marker",
        to_marker_key="table_caption_text",
    )
    assert counts == (1, 1, 0)


# ---------- §5/§6 不变量：非 fallback 来源零 table_has_caption ----------

def test_non_fallback_parsers_emit_no_table_has_caption(tmp_path: Path):
    from app.parsers.html_parser import HtmlParser
    from app.parsers.ipynb_parser import IpynbParser
    from app.parsers.markdown_parser import MarkdownParser
    from app.parsers.text_parser import TextParser
    import json

    cases = []
    md = tmp_path / "a.md"
    md.write_text("| a | b |\n|---|---|\n| 1 | 2 |\n\nTable 1. plain\n",
                  encoding="utf-8")
    cases.append(MarkdownParser().parse(md, source_hash="a" * 64))
    html = tmp_path / "a.html"
    html.write_text("<table><tr><td>1</td></tr></table><p>Table 1. plain</p>",
                    encoding="utf-8")
    cases.append(HtmlParser().parse(html, source_hash="a" * 64))
    txt = tmp_path / "a.txt"
    txt.write_text("Table 1. plain\n", encoding="utf-8")
    cases.append(TextParser().parse(txt, source_hash="a" * 64))
    nb = tmp_path / "a.ipynb"
    nb.write_text(json.dumps({
        "nbformat": 4, "nbformat_minor": 5, "metadata": {},
        "cells": [
            {"cell_type": "markdown",
             "source": ["| a | b |", "", "Table 1. plain"]},
            {"cell_type": "code", "source": ["print(1)"]},
        ],
    }), encoding="utf-8")
    cases.append(IpynbParser().parse(nb, source_hash="a" * 64))
    for doc in cases:
        assert all(
            r.type != "table_has_caption" for r in doc.relations
        ), f"{type(doc).__name__} 不应产出 table_has_caption"


# ---------- §6 devset 真样本（skip-if-missing） ----------

def _devset_doc(source_type: str):
    devset = ROOT / "samples/private/devset/manifest.json"
    if not devset.is_file():
        pytest.skip("samples/private 为本机资产，不存在时跳过")
    from evaluation.manifest import load_manifest
    m = load_manifest(devset, project_root=ROOT)
    entry = next((d for d in m.documents if d.source_type == source_type), None)
    if entry is None:
        pytest.skip(f"devset 无 {source_type} 样本")
    from app.parsers.fallback_parser import FallbackParser
    return FallbackParser().parse(entry.resolved_path, source_hash="a" * 64)


def test_devset_docx_table_relation():
    """期望冻结于批次 7 §0 盘点（2026-08-30；图关联基线 5750aef 批次 4）：
    caption e0012 "Table 1. Module status matrix" @para:12 紧邻
    table e0013 @tbl:0 之前 → e0013 --table_has_caption--> e0012。"""
    doc = _devset_doc("docx")
    rels = _rels(
        r for r in doc.relations if r.type == "table_has_caption"
    )
    assert rels == [{
        "type": "table_has_caption",
        "from_id": doc.document_id + "::e0013",
        "to_id": doc.document_id + "::e0012",
        "metadata": {"rule": "docx_adjacent_element_above"},
    }]
    d = doc.to_dict()
    assert d["schema_version"] == "0.5.0"
    validate_udm(d)


def test_devset_pdf_zero_table_relations():
    """期望冻结于批次 7 §0 盘点：PDF 表题注文本被 pdfplumber 融合进
    前一段落（e0004 以 "2. Structured elements" 开头），无独立 caption
    element → devset 上 pdf 表关联为 0 条。"""
    doc = _devset_doc("pdf")
    assert all(r.type != "table_has_caption" for r in doc.relations)
    d = doc.to_dict()
    assert d["schema_version"] == "0.5.0"
    validate_udm(d)
