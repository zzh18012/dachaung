"""显式引用 references relation 契约测试（Stage 10 批次 1）。

契约：docs/reference-relation-contract.md。逐条映射：
- §1 编号 token 语法与前缀集（ASCII 数字、复合 token、英文词边界、
  表前禁图、全角不识别、复数前缀）
- §2 形状与排序（type=references、from=正文 to=对象、metadata、
  (type, from, to) 排序）
- §3 唯一性守卫（0/≥2 目标不产边，禁 nearest-wins；来源排除
  caption/image/table；同源同目标去重）
- §4 版本分支（0.7.0 writer；≤0.6.0 拒 references）
- §5 端到端（合成 DOCX 内嵌图 + 题注 + 引用；合成 PDF 图 XObject +
  题注 + 引用；纯文本无图零引用）

开发纪律（十六轮裁决）：24-core 私有 gold 零接触；本文件全部使用
合成夹具。
"""

from __future__ import annotations

import io
import struct
import zlib
from pathlib import Path

import pytest

from app.models import Element, Relation, SCHEMA_VERSION_CURRENT
from app.parsers.fallback_parser import (
    match_caption_relations_docx,
    match_caption_relations_pdf,
    match_reference_relations,
    match_table_caption_relations_docx,
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


def _dloc(pidx: int) -> dict:
    return {"family": "structural_index", "paragraph_index": pidx}


def _docx_caption_rels(els: list[Element]) -> list[Relation]:
    return (
        match_caption_relations_docx(els)
        + match_table_caption_relations_docx(els)
    )


# ---------- §3 唯一性守卫与基本命中 ----------

def test_unique_figure_reference_hits():
    els = [
        _el("p1", "paragraph", "如图 1 所示，系统整体流程如下。", _dloc(0)),
        _img("i1", _dloc(1)),
        _cap("c1", "图 1 系统流程图", _dloc(2)),
    ]
    rels = _rels(match_reference_relations(els, _docx_caption_rels(els)))
    assert rels == [
        {"type": "references", "from_id": "p1", "to_id": "i1",
         "metadata": {"rule": "explicit_reference_unique", "token": "1"}},
    ]


def test_unique_table_reference_hits():
    els = [
        _cap("c1", "表 1 参数表", _dloc(0)),
        _el("t1", "table", "| a | b |", _dloc(1)),
        _el("p1", "paragraph", "各参数含义见表 1。", _dloc(2)),
    ]
    rels = _rels(match_reference_relations(els, _docx_caption_rels(els)))
    assert rels == [
        {"type": "references", "from_id": "p1", "to_id": "t1",
         "metadata": {"rule": "explicit_reference_unique", "token": "1"}},
    ]


def test_family_separation_figure_token_never_binds_table():
    els = [
        _el("p1", "paragraph", "见图 1。", _dloc(0)),
        _cap("c1", "表 1 参数表", _dloc(1)),
        _el("t1", "table", "| a |", _dloc(2)),
    ]
    assert match_reference_relations(els, _docx_caption_rels(els)) == []


def test_zero_match_no_edge():
    els = [
        _el("p1", "paragraph", "如图 9 所示。", _dloc(0)),
        _img("i1", _dloc(1)),
        _cap("c1", "图 1 系统流程图", _dloc(2)),
    ]
    assert match_reference_relations(els, _docx_caption_rels(els)) == []


def test_ambiguous_number_two_objects_no_edge():
    """同编号两对象（如分章重复编号）→ 歧义不产边（禁 nearest-wins）。"""
    els = [
        _el("p1", "paragraph", "如图 1 所示。", _dloc(0)),
        _img("i1", _dloc(1)),
        _cap("c1", "图 1 章一图", _dloc(2)),
        _img("i2", _dloc(3)),
        _cap("c2", "图 1 章二图", _dloc(4)),
    ]
    assert match_reference_relations(els, _docx_caption_rels(els)) == []


def test_dedup_same_token_twice_one_edge():
    els = [
        _el("p1", "paragraph",
            "如图 1 所示开始；后续步骤仍见图 1。", _dloc(0)),
        _img("i1", _dloc(1)),
        _cap("c1", "图 1 系统流程图", _dloc(2)),
    ]
    rels = _rels(match_reference_relations(els, _docx_caption_rels(els)))
    assert len(rels) == 1


def test_two_targets_two_edges_sorted():
    els = [
        _el("p1", "paragraph", "对比图 1 与图 2 的差异。", _dloc(0)),
        _img("i1", _dloc(1)),
        _cap("c1", "图 1 甲方案", _dloc(2)),
        _img("i2", _dloc(3)),
        _cap("c2", "图 2 乙方案", _dloc(4)),
        _el("p2", "paragraph", "另一段，见图 1。", _dloc(5)),
    ]
    rels = _rels(match_reference_relations(els, _docx_caption_rels(els)))
    # (type, from_id, to_id) 排序：p1→i1, p1→i2, p2→i1
    assert [(r["from_id"], r["to_id"]) for r in rels] == [
        ("p1", "i1"), ("p1", "i2"), ("p2", "i1"),
    ]


# ---------- §3 来源排除 ----------

def test_caption_element_never_a_source():
    """题注文本自带编号（图 1 … 引用另一对象）也不作为引用来源。"""
    els = [
        _el("p1", "paragraph", "概述。", _dloc(0)),
        _img("i1", _dloc(1)),
        _cap("c1", "图 1 甲方案", _dloc(2)),
        _img("i2", _dloc(3)),
        _cap("c2", "图 2 乙方案，另见图 1 对比", _dloc(4)),
    ]
    rels = _rels(match_reference_relations(els, _docx_caption_rels(els)))
    assert rels == []


def test_image_and_table_not_sources():
    """图/表对象 content 里的引用字样不作为来源（对象是被引端）。"""
    els = [
        _el("t1", "table", "| 见图 1 |\n| x |", _dloc(0)),
        _el("p1", "paragraph", "表格内容如上。", _dloc(1)),
        _img("i1", _dloc(2)),
        _cap("c1", "图 1 系统流程图", _dloc(3)),
    ]
    cap_rels = [  # 手工构造：题注 c1 不邻接 image（段落 3 与 2 相邻即可）
        r for r in _docx_caption_rels(els)
    ]
    assert match_reference_relations(els, cap_rels) == []


def test_heading_is_valid_source():
    els = [
        _el("h1", "heading", "2.3 数据流（见图 1）", _dloc(0)),
        _img("i1", _dloc(1)),
        _cap("c1", "图 1 数据流图", _dloc(2)),
    ]
    rels = _rels(match_reference_relations(els, _docx_caption_rels(els)))
    assert [(r["from_id"], r["to_id"]) for r in rels] == [("h1", "i1")]


# ---------- §1 前缀集与 token 语法 ----------

def test_english_prefixes_and_word_boundary():
    els = [
        _el("p1", "paragraph", "see Figure 1 for details.", _dloc(0)),
        _el("p2", "paragraph", "as Fig. 2 shows", _dloc(1)),
        _el("p3", "paragraph", "in Figs 3 we plot", _dloc(2)),
        _el("p4", "paragraph", "from Figure4 the trend", _dloc(3)),
        _el("p5", "paragraph", "the subfigure 3 panel", _dloc(4)),
        _el("p6", "paragraph", "Config 3 items", _dloc(5)),
        _img("i1", _dloc(6)),
        _cap("c1", "Figure 1. flow", _dloc(7)),
        _img("i2", _dloc(8)),
        _cap("c2", "Figure 2. plot", _dloc(9)),
        _img("i3", _dloc(10)),
        _cap("c3", "Figure 3. chart", _dloc(11)),
        _img("i4", _dloc(12)),
        _cap("c4", "Figure 4. trend", _dloc(13)),
    ]
    rels = _rels(match_reference_relations(els, _docx_caption_rels(els)))
    got = {(r["from_id"], r["to_id"]) for r in rels}
    # Figure 1 / Fig. 2 / Figs 3 / Figure4（无空格）命中；
    # subfigure 3（词边界）与 Config 3（词边界）不命中
    assert got == {("p1", "i1"), ("p2", "i2"), ("p3", "i3"), ("p4", "i4")}


def test_english_plural_chain_only_first_number():
    """契约 §5：Figures 3 and 4 只解析首个编号（and 链不展开）。"""
    els = [
        _el("p1", "paragraph", "Figures 3 and 4 compare the runs.", _dloc(0)),
        _img("i3", _dloc(1)),
        _cap("c3", "Figure 3. a", _dloc(2)),
        _img("i4", _dloc(3)),
        _cap("c4", "Figure 4. b", _dloc(4)),
    ]
    rels = _rels(match_reference_relations(els, _docx_caption_rels(els)))
    assert [(r["from_id"], r["to_id"]) for r in rels] == [("p1", "i3")]


def test_compound_token_strict_equality():
    """复合 token（3.4）两侧同语法严格相等；3 ≠ 3.4。"""
    els = [
        _el("p1", "paragraph", "see Figure 3.4 for details", _dloc(0)),
        _el("p2", "paragraph", "see Figure 3 for details", _dloc(1)),
        _img("i1", _dloc(2)),
        _cap("c1", "Figure 3.4: zoomed view", _dloc(3)),
    ]
    rels = _rels(match_reference_relations(els, _docx_caption_rels(els)))
    assert [(r["from_id"], r["to_id"]) for r in rels] == [("p1", "i1")]


def test_decimal_section_reference_no_false_bind():
    """“图 3.5 节”属小节引用形态：token 3.5 ≠ 题注 3，不误绑。"""
    els = [
        _el("p1", "paragraph", "详见图书第 3 章图 3.5 节的说明。", _dloc(0)),
        _img("i1", _dloc(1)),
        _cap("c1", "图 3 架构图", _dloc(2)),
    ]
    assert match_reference_relations(els, _docx_caption_rels(els)) == []


def test_range_reference_not_enumerated():
    """“图 3-5”解析为复合 token（无匹配），不展开枚举区间成员。"""
    els = [
        _el("p1", "paragraph", "如图 3-5 所示的各阶段。", _dloc(0)),
        _img("i3", _dloc(1)),
        _cap("c3", "图 3 阶段三", _dloc(2)),
        _img("i4", _dloc(3)),
        _cap("c4", "图 4 阶段四", _dloc(4)),
        _img("i5", _dloc(5)),
        _cap("c5", "图 5 阶段五", _dloc(6)),
    ]
    assert match_reference_relations(els, _docx_caption_rels(els)) == []


def test_fullwidth_digits_not_matched():
    """数字限 ASCII（契约 §1，与批次 4/7 题注契约一致）。"""
    els = [
        _el("p1", "paragraph", "如图１所示。", _dloc(0)),
        _img("i1", _dloc(1)),
        _cap("c1", "图 1 系统流程图", _dloc(2)),
    ]
    assert match_reference_relations(els, _docx_caption_rels(els)) == []


def test_compound_word_tubiao_no_bind():
    """“图表 3”：图后非数字不落 figure；表前是图不落 table（§1）。"""
    els = [
        _el("p1", "paragraph", "整体图表 3 如下。", _dloc(0)),
        _el("t1", "table", "| a |", _dloc(1)),
        _cap("c1", "表 3 数据表", _dloc(2)),
    ]
    assert match_reference_relations(els, _docx_caption_rels(els)) == []


def test_no_space_cjk_reference():
    els = [
        _el("p1", "paragraph", "如图1所示，流程分为三步。", _dloc(0)),
        _img("i1", _dloc(1)),
        _cap("c1", "图 1 系统流程图", _dloc(2)),
    ]
    rels = _rels(match_reference_relations(els, _docx_caption_rels(els)))
    assert [(r["from_id"], r["to_id"]) for r in rels] == [("p1", "i1")]


# ---------- §3 防御路径 ----------

def test_unknown_caption_relation_type_skipped():
    els = [
        _el("p1", "paragraph", "如图 1 所示。", _dloc(0)),
        _img("i1", _dloc(1)),
        _cap("c1", "图 1 系统流程图", _dloc(2)),
    ]
    extra = Relation(type="custom", from_id="i1", to_id="c1")
    rels = match_reference_relations(els, _docx_caption_rels(els) + [extra])
    assert len(rels) == 1


def test_caption_endpoint_missing_from_elements_skipped():
    """caption relation 的 to_id 解析不到元素 → 防御跳过。"""
    els = [
        _el("p1", "paragraph", "如图 1 所示。", _dloc(0)),
        _img("i1", _dloc(1)),
    ]
    ghost = Relation(type="has_caption", from_id="i1", to_id="cX")
    assert match_reference_relations(els, [ghost]) == []


def test_caption_without_extractable_token_skipped():
    """题注有 has_caption 但文本提不出编号 token（真实契约下题注必过
    前缀正则，此为防御路径）：该对象不进索引，不影响唯一性判定。"""
    els = [
        _el("p1", "paragraph", "如图 1 所示。", _dloc(0)),
        _img("i1", _dloc(1)),
        _cap("c1", "图 1 系统流程图", _dloc(2)),
        _img("i2", _dloc(3)),
        _cap("c2", "无前缀形态的题注文本", _dloc(4)),
    ]
    hand = [
        Relation(type="has_caption", from_id="i1", to_id="c1"),
        Relation(type="has_caption", from_id="i2", to_id="c2"),
    ]
    rels = _rels(match_reference_relations(els, hand))
    assert [(r["from_id"], r["to_id"]) for r in rels] == [("p1", "i1")]


# ---------- §4 版本分支 ----------

def _udm(relation: dict, version: str = "0.7.0") -> dict:
    return {
        "schema_version": version,
        "document_id": "doc1",
        "source_path": "samples/x",
        "source_type": "pdf",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "parent_id": None,
             "source_locator": {"family": "page_geometry", "page": 1},
             "content": "see Figure 1", "resource_path": None,
             "confidence": 1.0, "metadata": {}},
            {"element_id": "e2", "type": "image", "parent_id": None,
             "source_locator": {"family": "page_geometry", "page": 1,
                                "bbox": [0, 0, 10, 10]},
             "content": None, "resource_path": "x.png",
             "confidence": 1.0, "metadata": {}},
        ],
        "chunks": [],
        "relations": [relation],
        "warnings": [], "errors": [], "metadata": {},
    }


_REF_REL = {
    "type": "references", "from_id": "e1", "to_id": "e2",
    "metadata": {"rule": "explicit_reference_unique", "token": "1"},
}


def test_v070_references_validates():
    validate_udm(_udm(_REF_REL, "0.7.0"))


@pytest.mark.parametrize("version", ["0.1.0", "0.2.0", "0.3.0",
                                     "0.4.0", "0.5.0", "0.6.0"])
def test_pre_v070_rejects_references(version):
    from app.schema import SchemaValidationError
    with pytest.raises(SchemaValidationError):
        validate_udm(_udm(_REF_REL, version))


def test_writer_version_is_current():
    import app.models as m
    assert SCHEMA_VERSION_CURRENT == "0.7.0"
    assert m.SCHEMA_VERSION_REFERENCE == "0.7.0"


# ---------- §5 端到端：合成 DOCX ----------

def _tiny_png() -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    idat = zlib.compress(b"\x00\xff\x00\x00")
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def _build_reference_docx(tmp_path: Path) -> Path:
    import docx as docxlib
    d = docxlib.Document()
    d.add_paragraph("如图 1 所示，系统整体流程分为三步。")
    d.add_picture(io.BytesIO(_tiny_png()),
                  width=docxlib.shared.Inches(1.5))
    d.add_paragraph("图 1 系统流程图")
    p = tmp_path / "ref.docx"
    d.save(str(p))
    return p


def test_e2e_docx_reference_chain(tmp_path: Path):
    from app.parsers.fallback_parser import FallbackParser
    p = _build_reference_docx(tmp_path)
    doc = FallbackParser().parse(p, source_hash="c" * 64)
    rels = _rels(doc.relations)
    types = [r["type"] for r in rels]
    assert types == ["has_caption", "references"]  # (type,from,to) 排序
    img_ids = [e.element_id for e in doc.elements if e.type == "image"]
    para_ids = [e.element_id for e in doc.elements
                if e.type == "paragraph" and "如图 1" in (e.content or "")]
    assert len(img_ids) == 1 and len(para_ids) == 1
    assert rels[1]["from_id"] == para_ids[0]
    assert rels[1]["to_id"] == img_ids[0]
    d = doc.to_dict()
    assert d["schema_version"] == "0.7.0"
    validate_udm(d)


# ---------- §5 端到端：合成 PDF（图 XObject + 题注 + 引用） ----------

def _build_reference_pdf(tmp_path: Path) -> Path:
    objs = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R '
        b'/Resources << /Font << /F1 5 0 R >> /XObject << /Im1 6 0 R >> >> >>',
    ]
    stream = (
        b'BT /F1 12 Tf 72 700 Td (See Figure 1 for the overall flow.) Tj ET\n'
        b'q 200 0 0 150 72 420 cm /Im1 Do Q\n'
        b'BT /F1 12 Tf 72 380 Td (Figure 1. flow diagram) Tj ET'
    )
    objs.append(b'<< /Length ' + str(len(stream)).encode()
                + b' >>\nstream\n' + stream + b'\nendstream')
    objs.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    img_data = zlib.compress(b"\x00" + b"\xff\x00\x00" * 4)  # 4x1 RGB
    objs.append(
        b'<< /Type /XObject /Subtype /Image /Width 4 /Height 1 '
        b'/ColorSpace /DeviceRGB /BitsPerComponent 8 '
        b'/Filter /FlateDecode /Length ' + str(len(img_data)).encode()
        + b' >>\nstream\n' + img_data + b'\nendstream')
    return _assemble_pdf(tmp_path / "ref.pdf", objs)


def _assemble_pdf(path: Path, objs: list[bytes]) -> Path:
    pdf = b'%PDF-1.4\n'
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += f'{i} 0 obj\n'.encode() + body + b'\nendobj\n'
    xref_pos = len(pdf)
    n = len(objs) + 1
    pdf += b'xref\n' + f'0 {n}\n'.encode() + b'0000000000 65535 f \n'
    for off in offsets:
        pdf += f'{off:010d} 00000 n \n'.encode()
    pdf += b'trailer\n<< /Size ' + str(n).encode() + b' /Root 1 0 R >>\nstartxref\n'
    pdf += str(xref_pos).encode() + b'\n%%EOF'
    path.write_bytes(pdf)
    return path


def test_e2e_pdf_reference_chain(tmp_path: Path):
    from app.parsers.fallback_parser import FallbackParser
    p = _build_reference_pdf(tmp_path)
    doc = FallbackParser().parse(p, source_hash="d" * 64)
    rels = _rels(doc.relations)
    types = [r["type"] for r in rels]
    assert types == ["has_caption", "references"]
    img_ids = [e.element_id for e in doc.elements if e.type == "image"]
    body_ids = [e.element_id for e in doc.elements
                if e.type == "paragraph" and "See Figure 1" in (e.content or "")]
    assert len(img_ids) == 1 and len(body_ids) == 1
    assert rels[1]["from_id"] == body_ids[0]
    assert rels[1]["to_id"] == img_ids[0]
    validate_udm(doc.to_dict())


def test_e2e_pdf_text_only_zero_references(tmp_path: Path):
    """纯文本 PDF（无图/表对象）零 references（无目标可绑）。"""
    from app.parsers.fallback_parser import FallbackParser
    objs = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R '
        b'/Resources << /Font << /F1 5 0 R >> >> >>',
    ]
    stream = (b'BT /F1 12 Tf 72 700 Td '
              b'(As Figure 1 shows, the pipeline works.) Tj ET')
    objs.append(b'<< /Length ' + str(len(stream)).encode()
                + b' >>\nstream\n' + stream + b'\nendstream')
    objs.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    p = _assemble_pdf(tmp_path / "textonly.pdf", objs)
    doc = FallbackParser().parse(p, source_hash="e" * 64)
    assert [r.type for r in doc.relations if r.type == "references"] == []
