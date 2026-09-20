"""Stage 10 批次 9 测试：PDF 底带页面家具 heading 后置过滤（r62 授权）。

裁决边界（ADOPTION §147）：
- D1 = 已判 heading 候选 + bbox 下边缘/页高 ≥ 0.93 + 全文本匹配通用
  Page+数字 形态（大小写不敏感；不要求显示页码==物理页；不扩展到
  裸数字/日期/罗马数字/文件名）；
- D2 = 已判 heading 且位于底带的候选，规范化文本（仅首尾空白清理 +
  连续空白折叠，大小写敏感）在 ≥2 个不同物理页的底带逐字出现
  （两个实例自身均须在底带）；
- 命中 → type 改 paragraph + metadata.heading_suppressed=page_furniture_*；
  文本/locator/bbox/页号/element_id/顺序/置信度与批次 6 form_label_*
  语义不动；
- 93% 为 r62④ 冻结阈值；页首 running header 不进 v1；
- 不硬编码 real-02 真实样本内容，夹具字符串全部为等义合成行。

夹具标定（MediaBox [0 0 612 792]，/F1 10 Tf，Helvetica）：
pdfplumber 段落 bbox 下边缘 = 792 - y + 2.07。
- y=57.4 → 93.014%（≥93，底带）
- y=58.4 → 92.888%（<93，带外）
- y=49.5 → 94.008%（底带）
- y=400  → 49.76%（页中）
- y=760  → 4.30%（页首带）
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.models import Element
from app.parsers.fallback_parser import (
    FallbackParser,
    _band_heading_key,
    _suppress_page_furniture_headings,
)
from app.pipeline import process_single


# ---------- 手写最小 PDF 夹具（与批次 6 同构造，自包含） ----------

def _escape_pdf_literal(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _stream(positions: list[tuple[str, float]]) -> str:
    """单页多行文本；positions = [(文本, 基线 y), ...]。

    同页行距全部 > 15pt（> 1.5×10pt 字高），确保逐行独立成段。
    """
    ops = [
        f"BT /F1 10 Tf 72 {y} Td ({_escape_pdf_literal(t)}) Tj ET"
        for t, y in positions
    ]
    return "\n".join(ops) + "\n"


def _make_pdf(path: Path, page_streams: list[str]) -> Path:
    n = len(page_streams)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n))
    objs: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for stream in page_streams:
        content = stream.encode("latin-1")
        objs.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Contents " + str(len(objs) + 2).encode() + b" 0 R"
            b" /Resources << /Font << /F1 3 0 R >> >> >>"
        )
        objs.append(
            b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"
        )
    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_pos = len(pdf)
    total = len(objs) + 1
    pdf += b"xref\n" + f"0 {total}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += (
        b"trailer\n<< /Size " + str(total).encode() + b" /Root 1 0 R >>\n"
        b"startxref\n" + str(xref_pos).encode() + b"\n%%EOF"
    )
    path.write_bytes(pdf)
    return path


BAND_Y = 57.4        # 93.014% ≥ 93：底带
BELOW_BAND_Y = 58.4  # 92.888% < 93：带外
DEEP_BAND_Y = 49.5   # 94.008%：底带
LOWER_BAND_Y = 35    # 95.843%：底带（与 BAND_Y 相距 22.4pt > 15pt，同页不并段）
MID_Y = 400          # 49.76%：页中
TOP_Y = 760          # 4.30%：页首带（running head 区）

BODY = "Normal body sentence about the quarterly audit findings."


def _parse_doc(pdf_path: Path):
    h = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    return FallbackParser().parse(pdf_path, source_hash=h)


def _by_content(pdf_path: Path) -> dict[str, Element]:
    doc = _parse_doc(pdf_path)
    return {e.content: e for e in doc.elements}


# ---------- F1：抑制（家具应被压掉） ----------

def test_f1_band_page_numbers_suppressed_via_d1(tmp_path: Path):
    """底带页码逐页文本不同（Page 01/02/03），走 D1 模板而非重复证据。"""
    pdf = _make_pdf(tmp_path / "pageno.pdf", [
        _stream([("Introduction", MID_Y), (BODY, 300), ("Page 01", BAND_Y)]),
        _stream([("Findings", MID_Y), (BODY, 300), ("Page 02", BAND_Y)]),
        _stream([(BODY, 300), ("Page 03", BAND_Y)]),
    ])
    got = _by_content(pdf)
    for c in ("Page 01", "Page 02", "Page 03"):
        assert got[c].type == "paragraph"
        assert got[c].metadata["heading_suppressed"] == "page_furniture_page_number"
    assert got["Introduction"].type == "heading"
    assert got["Findings"].type == "heading"


def test_f1_band_repeated_slogan_suppressed_via_d2(tmp_path: Path):
    """底带跨页逐字重复宣传语（非页码形态），走 D2 重复证据。"""
    slogan = "Delivering Verified Outcomes"
    pdf = _make_pdf(tmp_path / "slogan.pdf", [
        _stream([("Introduction", MID_Y), (slogan, BAND_Y)]),
        _stream([(BODY, 300), (slogan, BAND_Y)]),
    ])
    got = _by_content(pdf)
    assert got[slogan].type == "paragraph"
    assert got[slogan].metadata["heading_suppressed"] == "page_furniture_band_repeat"
    assert got["Introduction"].type == "heading"


def test_f1_band_repeated_bare_date_suppressed_via_d2(tmp_path: Path):
    """底带跨页重复裸日期：无 D1 形态匹配，仅凭 D2 重复证据抑制。"""
    date = "December 2025"
    pdf = _make_pdf(tmp_path / "date.pdf", [
        _stream([("Overview", MID_Y), (date, BAND_Y)]),
        _stream([(BODY, 300), (date, BAND_Y)]),
    ])
    got = _by_content(pdf)
    assert got[date].type == "paragraph"
    assert got[date].metadata["heading_suppressed"] == "page_furniture_band_repeat"


# ---------- F2：存活（合法 heading 不受影响） ----------

def test_f2_midpage_page_number_survives(tmp_path: Path):
    pdf = _make_pdf(tmp_path / "mid.pdf", [
        _stream([(BODY, 300), ("Page 07", MID_Y)]),
    ])
    el = _by_content(pdf)["Page 07"]
    assert el.type == "heading"
    assert "heading_suppressed" not in el.metadata


def test_f2_midpage_bare_date_survives(tmp_path: Path):
    pdf = _make_pdf(tmp_path / "midd.pdf", [
        _stream([(BODY, 300), ("March 2026", MID_Y)]),
    ])
    el = _by_content(pdf)["March 2026"]
    assert el.type == "heading"
    assert "heading_suppressed" not in el.metadata


def test_f2_deep_band_single_page_title_survives(tmp_path: Path):
    """底缘 94% 单页合法标题：在底带但无页码形态、无跨页重复 → 存活。"""
    pdf = _make_pdf(tmp_path / "deep.pdf", [
        _stream([(BODY, 300), ("Appendix Notes", DEEP_BAND_Y)]),
    ])
    el = _by_content(pdf)["Appendix Notes"]
    assert el.type == "heading"
    assert "heading_suppressed" not in el.metadata


def test_f2_midpage_repeated_title_survives(tmp_path: Path):
    """跨页重复但两处都在页中 → 不参与底带聚合，逐处存活。"""
    title = "Regional Overview"
    pdf = _make_pdf(tmp_path / "repeatmid.pdf", [
        _stream([(title, MID_Y), (BODY, 300)]),
        _stream([(title, MID_Y), (BODY, 300)]),
    ])
    got = _by_content(pdf)
    assert got[title].type == "heading"
    assert "heading_suppressed" not in got[title].metadata


def test_f2_running_head_top_band_survives(tmp_path: Path):
    """页首 running header 跨页逐字重复：v1 明确不处理页首带。"""
    head = "Internal Use Only"
    pdf = _make_pdf(tmp_path / "runhead.pdf", [
        _stream([(head, TOP_Y), (BODY, 300)]),
        _stream([(head, TOP_Y), (BODY, 300)]),
    ])
    got = _by_content(pdf)
    assert got[head].type == "heading"
    assert "heading_suppressed" not in got[head].metadata


# ---------- F3：阈值 ----------

def test_f3_threshold_93_suppress_vs_929_survive(tmp_path: Path):
    """93.0% 抑制 / 92.9% 存活（同在页底缘，仅带宽之差）。"""
    pdf = _make_pdf(tmp_path / "thr.pdf", [
        _stream([(BODY, 300), ("Page 41", BAND_Y)]),
        _stream([(BODY, 300), ("Page 42", BELOW_BAND_Y)]),
    ])
    doc = _parse_doc(pdf)
    by_page = {e.source_locator["page"]: e for e in doc.elements if e.content.startswith("Page 4")}
    assert len(by_page) == 2
    bot1 = by_page[1].source_locator["bbox"][3] / 792
    bot2 = by_page[2].source_locator["bbox"][3] / 792
    assert bot1 >= 0.93 and bot1 < 0.931
    assert 0.928 <= bot2 < 0.93
    assert by_page[1].type == "paragraph"
    assert by_page[1].metadata["heading_suppressed"] == "page_furniture_page_number"
    assert by_page[2].type == "heading"
    assert "heading_suppressed" not in by_page[2].metadata


def test_f3_repeat_requires_two_distinct_pages(tmp_path: Path):
    """底带文本仅单页出现（另一页底带是不同文本）→ 不满足 D2 → 存活。"""
    once = "Standing Notice"
    pdf = _make_pdf(tmp_path / "once.pdf", [
        _stream([(BODY, 300), (once, BAND_Y)]),
        _stream([(BODY, 300), ("Final Wrap", BAND_Y)]),
    ])
    got = _by_content(pdf)
    assert got[once].type == "heading"
    assert got["Final Wrap"].type == "heading"


# ---------- r62⑤ 两项实现级守护 ----------

def test_guard_d2_requires_both_instances_in_band(tmp_path: Path):
    """同一文本一处底带、一处页中：页中实例不在底带不判，底带实例
    仅 1 个底带页 → D2 不满足，两处均存活。"""
    text = "Shared Banner Line"
    pdf = _make_pdf(tmp_path / "halfband.pdf", [
        _stream([(BODY, 300), (text, BAND_Y)]),
        _stream([(BODY, 300), (text, MID_Y)]),
    ])
    doc = _parse_doc(pdf)
    hits = [e for e in doc.elements if e.content == text]
    assert len(hits) == 2
    for e in hits:
        assert e.type == "heading"
        assert "heading_suppressed" not in e.metadata


def test_guard_d2_near_identical_texts_not_merged(tmp_path: Path):
    """D2 normalization 仅空白折叠：数字差异/标点差异/大小写差异的
    近似文本不得判为重复。"""
    pairs = [
        ("Summary Review 2024", "Summary Review 2025"),  # 数字变化
        ("Interim Findings", "Interim Findings;"),       # 标点差异
        ("Notice A", "notice a"),                        # 大小写差异
    ]
    for i, (t1, t2) in enumerate(pairs):
        pdf = _make_pdf(tmp_path / f"near{i}.pdf", [
            _stream([(BODY, 300), (t1, BAND_Y)]),
            _stream([(BODY, 300), (t2, BAND_Y)]),
        ])
        got = _by_content(pdf)
        assert got[t1].type == "heading", t1
        assert got[t2].type == "heading", t2
        assert "heading_suppressed" not in got[t1].metadata
        assert "heading_suppressed" not in got[t2].metadata


def test_guard_d2_whitespace_folding_merges(tmp_path: Path):
    """正控制：仅空白差异（多空格 vs 单空格）经折叠后判重 → 抑制。
    pdfplumber extract_words 本身不保留词间空格数，两页段落文本均折叠
    为单空格形态。"""
    pdf = _make_pdf(tmp_path / "fold.pdf", [
        _stream([(BODY, 300), ("Quality  Assurance  Report", BAND_Y)]),
        _stream([(BODY, 300), ("Quality Assurance Report", BAND_Y)]),
    ])
    doc = _parse_doc(pdf)
    hits = [e for e in doc.elements if e.content == "Quality Assurance Report"]
    assert len(hits) == 2
    for e in hits:
        assert e.type == "paragraph"
        assert e.metadata["heading_suppressed"] == "page_furniture_band_repeat"


# ---------- 单元级：结构约束（不依赖 PDF） ----------

def _mk_heading(eid: str, text: str, page: int, bbox: list[float]) -> Element:
    return Element(
        element_id=eid,
        type="heading",
        content=text,
        source_locator={"family": "page_geometry", "page": page, "bbox": bbox},
        confidence=0.85,
        metadata={"level": 0, "heuristic": "short_line"},
    )


HEIGHTS = {1: 792.0, 2: 792.0}


def test_unit_band_key_requires_page_bbox_height():
    el = _mk_heading("d::e0001", "Page 9", 1, [72.0, 726.0, 120.0, 736.67])
    assert _band_heading_key(el, HEIGHTS) == ("Page 9", 1)
    no_bbox = Element(element_id="d::e0002", type="heading", content="Page 9",
                      source_locator={"family": "page_geometry", "page": 1},
                      metadata={})
    assert _band_heading_key(no_bbox, HEIGHTS) is None
    no_page = Element(element_id="d::e0003", type="heading", content="Page 9",
                      source_locator={"family": "page_geometry",
                                      "page": 3, "bbox": [0, 0, 10, 790]},
                      metadata={})
    assert _band_heading_key(no_page, HEIGHTS) is None  # 页高未知
    unknown_page = _mk_heading("d::e0004", "Page 9", 9, [0, 0, 10, 790])
    assert _band_heading_key(unknown_page, HEIGHTS) is None


def test_unit_suppression_preserves_structure():
    """命中抑制仅改 type 与追加 metadata 键；element_id/顺序/文本/
    locator/bbox/置信度/其余 metadata 一律不变。"""
    els = [
        _mk_heading("d::e0000", "First Topic", 1, [72.0, 300.0, 200.0, 310.0]),
        _mk_heading("d::e0001", "Page 9", 1, [72.0, 726.0, 120.0, 736.67]),
        _mk_heading("d::e0002", "Shared Line", 1, [72.0, 726.0, 200.0, 736.67]),
        _mk_heading("d::e0003", "Shared Line", 2, [72.0, 726.0, 200.0, 736.67]),
    ]
    before = [(e.element_id, e.content, dict(e.source_locator),
               e.confidence, dict(e.metadata)) for e in els]
    out = _suppress_page_furniture_headings(list(els), HEIGHTS)
    assert [e.element_id for e in out] == [b[0] for b in before]
    assert [e.content for e in out] == [b[1] for b in before]
    assert [e.source_locator for e in out] == [b[2] for b in before]
    assert [e.confidence for e in out] == [b[3] for b in before]
    assert out[0].type == "heading"          # 带外
    assert out[1].type == "paragraph"        # D1
    assert out[1].metadata == {
        "level": 0, "heuristic": "short_line",
        "heading_suppressed": "page_furniture_page_number",
    }
    assert out[2].type == "paragraph"        # D2
    assert out[2].metadata["heading_suppressed"] == "page_furniture_band_repeat"
    assert out[3].type == "paragraph"
    # 其余 metadata 键原样保留（批次 6 语义共存）
    assert out[0].metadata == before[0][4]


def test_unit_non_heading_and_form_label_untouched():
    form = Element(
        element_id="d::e0000", type="paragraph", content="Contact address:",
        source_locator={"family": "page_geometry", "page": 1,
                        "bbox": [72.0, 726.0, 200.0, 736.67]},
        metadata={"heading_suppressed": "form_label_short_colon"},
    )
    table = Element(
        element_id="d::e0001", type="table", content="| a | b |",
        source_locator={"family": "page_geometry", "page": 1,
                        "bbox": [72.0, 720.0, 500.0, 740.0]},
        metadata={"row_count": 1},
    )
    out = _suppress_page_furniture_headings([form, table], HEIGHTS)
    assert out[0].type == "paragraph"
    assert out[0].metadata == {"heading_suppressed": "form_label_short_colon"}
    assert out[1].type == "table"
    assert out[1].metadata == {"row_count": 1}


def test_unit_d1_case_and_spacing_insensitive_but_form_bounded():
    """D1 容许大小写/空白归一；Page+N of M / 裸数字不属 D1 形态。"""
    heights = {1: 792.0}
    cases = [
        ("page 3", True), ("PAGE  7", True), ("Page 12", True),
        ("Page 7 of 30", False), ("12", False), ("Page iv", False),
        ("Page report", False), ("Pages 12", False),
    ]
    for text, should_match in cases:
        el = _mk_heading("d::e0001", text, 1, [72.0, 726.0, 200.0, 736.67])
        if should_match:
            out = _suppress_page_furniture_headings([el], heights)
            assert out[0].type == "paragraph", text
            assert out[0].metadata["heading_suppressed"] == "page_furniture_page_number"
        else:
            # 单页出现：无 D2，形态不匹配 → 存活
            probe = _mk_heading("d::e0002", text, 1, [72.0, 726.0, 200.0, 736.67])
            out = _suppress_page_furniture_headings([probe], heights)
            assert out[0].type == "heading", text


# ---------- F4：端到端回归 ----------

def test_f4_e2e_mixed_document_composition(tmp_path: Path):
    """混合文档：底带页码（D1）+ 底带跨页宣传语（D2）被抑制；
    页中合法 heading 与正文不受影响。"""
    slogan = "Delivering Verified Outcomes"
    pdf = _make_pdf(tmp_path / "mixed.pdf", [
        _stream([("Section Overview", MID_Y), (BODY, 300), (slogan, BAND_Y)]),
        _stream([("Regional Results", MID_Y), (BODY, 300), ("Page 02", BAND_Y)]),
        _stream([(BODY, 300), (slogan, LOWER_BAND_Y)]),
        _stream([(BODY, 300), ("Page 04", BAND_Y)]),
    ])
    doc = _parse_doc(pdf)
    types = [(e.content, e.type) for e in doc.elements]
    assert types.count((slogan, "paragraph")) == 2
    assert ("Page 02", "paragraph") in types
    assert ("Page 04", "paragraph") in types
    assert ("Section Overview", "heading") in types
    assert ("Regional Results", "heading") in types
    assert types.count((BODY, "paragraph")) == 4
    suppressed = [e.metadata.get("heading_suppressed") for e in doc.elements
                  if e.type == "paragraph"]
    assert sorted(s for s in suppressed if s) == [
        "page_furniture_band_repeat", "page_furniture_band_repeat",
        "page_furniture_page_number", "page_furniture_page_number",
    ]
    # element_id 严格递增无重排
    ids = [e.element_id for e in doc.elements]
    assert ids == sorted(ids)


def test_f4_suppressed_document_passes_pipeline_schema(tmp_path: Path):
    pdf = _make_pdf(tmp_path / "pipe.pdf", [
        _stream([(BODY, 300), ("Page 01", BAND_Y)]),
        _stream([(BODY, 300), ("Page 02", BAND_Y)]),
    ])
    out = tmp_path / "pipe.json"
    doc, errs = process_single(pdf, out)
    assert errs == []
    assert out.exists()
    assert doc is not None
    furniture = [e for e in doc.elements if e.type == "paragraph"
                 and e.metadata.get("heading_suppressed", "").startswith("page_furniture_")]
    assert len(furniture) == 2
