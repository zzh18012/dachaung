"""Stage 11 批次 18 测试：D3 底带裸数字页码抑制（r76 授权）。

裁决边界（ADOPTION §173）：
- D3 = heading ∧ 底带(≥0.93) ∧ 全文本 1-4 位裸数字 ∧ 元素主导字体
  圈外（∉ 文档级 top-3，词计数）∧ 元素最大字号/文档字号众数 ≤ 1.2；
- 判定顺序 D1 → D2 → D3：D1/D2 行为零变化（重复裸数字仍归 D2）；
- reason code = page_furniture_digit_page_number；
- 消费点仅 _suppress_page_furniture_headings；不触碰
  _classify_pdf_paragraph / short_line / DOCX / table detector；
- 保守退化：词属性缺失（fontname/font_size None）或文档级统计不可得
  → 不命中 D3（存活）；
- r76④ 参数钉死：top-3 = 全文档词级 fontname 计数前 3（文档级）；
  body mode = 全文档词级 font_size 众数；元素字号取最大（混排以最
  显眼字号为准）。

夹具标定沿用批次 9（MediaBox [0 0 612 792]，10pt）：
bbox 下边缘 = 792 - y + 2.07；y=57.4 → 93.014%（底带）。
多字体正例夹具：3 种正文字体（各 2 行长句）挤满 top-3，
第 4 种字体（Times-Bold）渲染页码 → 圈外。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.models import Element
from app.parsers.fallback_parser import (
    FallbackParser,
    _suppress_page_furniture_headings,
)
from app.pipeline import process_single


# ---------- 手写最小多字体 PDF 夹具（自包含） ----------

def _escape_pdf_literal(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", r"\(").replace(")", r"\)")


def _make_pdf(
    path: Path,
    page_lines: list[list[tuple[str, str, float, float]]],
) -> Path:
    """page_lines: 每页 [(文本, 资源名, 字号, 基线 y), ...]。

    字体对象固定四个：/F1 Helvetica /F2 Courier /F3 Times-Roman
    /F4 Times-Bold（对象 3-6）；正例夹具用 F4 作页码圈外字体。
    """
    n = len(page_lines)
    kids = " ".join(f"{7 + 2 * i} 0 R" for i in range(n))
    objs: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold >>",
    ]
    for lines in page_lines:
        ops = [
            f"BT /{res} {size} Tf 72 {y} Td ({_escape_pdf_literal(t)}) Tj ET"
            for t, res, size, y in lines
        ]
        content = ("\n".join(ops) + "\n").encode("latin-1")
        objs.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Contents " + str(len(objs) + 2).encode() + b" 0 R"
            b" /Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R"
            b" /F4 6 0 R >> >> >>"
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
    xref = len(pdf)
    total = len(objs) + 1
    pdf += b"xref\n" + f"0 {total}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += (
        b"trailer\n<< /Size " + str(total).encode() + b" /Root 1 0 R >>\n"
        b"startxref\n" + str(xref).encode() + b"\n%%EOF"
    )
    path.write_bytes(pdf)
    return path


BAND_Y = 57.4   # 93.014% ≥ 93：底带（批次 9 标定）
MID_Y = 400     # 49.76%：页中

BODY_A = "Quarterly audit findings were reviewed in detail by the committee."
BODY_B = "Regional results showed consistent improvement across all units."
BODY_C = "Detailed notes accompany the summary in the final section."


def _body_lines(y0: float) -> list[tuple[str, str, float, float]]:
    """三种正文字体各 1 行。行距 40pt（视觉空隙 29pt > 1.5×行高
    16pt，独立成段；20pt 间距视觉空隙仅 9.3pt 会被行聚类并段）。"""
    return [
        (BODY_A, "F1", 10.0, y0),
        (BODY_B, "F2", 10.0, y0 - 40),
        (BODY_C, "F3", 10.0, y0 - 80),
    ]


def _parse_doc(pdf_path: Path):
    h = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    return FallbackParser().parse(pdf_path, source_hash=h)


def _by_content(pdf_path: Path) -> dict[str, Element]:
    doc = _parse_doc(pdf_path)
    return {e.content: e for e in doc.elements}


# ---------- 端到端：D3 命中 ----------

def test_e2e_band_digits_outside_font_suppressed(tmp_path: Path):
    """底带裸数字（1-4 位）+ 圈外字体（F4）+ 小字号 → D3 抑制；
    页中同字体数字存活（band 防护）。"""
    pdf = _make_pdf(tmp_path / "d3.pdf", [
        _body_lines(700) + [("1", "F4", 10.0, BAND_Y)],
        _body_lines(700) + [("2", "F4", 10.0, BAND_Y)],
        _body_lines(700) + [("3", "F4", 10.0, BAND_Y)],
        _body_lines(700) + [("9", "F4", 10.0, MID_Y)],  # 页中：存活
    ])
    got = _by_content(pdf)
    for digit in ("1", "2", "3"):
        assert got[digit].type == "paragraph", digit
        assert got[digit].metadata["heading_suppressed"] == (
            "page_furniture_digit_page_number")
    assert got["9"].type == "heading"
    assert "heading_suppressed" not in got["9"].metadata


def test_e2e_d1_priority_unchanged_with_font_channel(tmp_path: Path):
    """D1 形态优先且行为零变化：底带 'Page 01'（正文族字体）仍走
    page_furniture_page_number，不因 font 通道接入改变。"""
    pdf = _make_pdf(tmp_path / "d1.pdf", [
        _body_lines(700) + [("Page 01", "F1", 10.0, BAND_Y)],
        _body_lines(700) + [("2", "F4", 10.0, BAND_Y)],
    ])
    got = _by_content(pdf)
    assert got["Page 01"].type == "paragraph"
    assert got["Page 01"].metadata["heading_suppressed"] == (
        "page_furniture_page_number")
    assert got["2"].metadata["heading_suppressed"] == (
        "page_furniture_digit_page_number")


# ---------- 端到端：保守存活（三合取各自的反向） ----------

def test_e2e_digit_in_body_font_survives_fontout(tmp_path: Path):
    """底带裸数字但用 top-1 正文字体（F1）→ fontOut=False → 存活。"""
    pdf = _make_pdf(tmp_path / "infont.pdf", [
        _body_lines(700) + [("1", "F1", 10.0, BAND_Y)],
        _body_lines(700) + [("2", "F1", 10.0, BAND_Y)],
    ])
    got = _by_content(pdf)
    for digit in ("1", "2"):
        assert got[digit].type == "heading", digit
        assert "heading_suppressed" not in got[digit].metadata


def test_e2e_oversize_digit_survives_size_cap(tmp_path: Path):
    """底带裸数字 + 圈外字体但 24pt（r=2.4 > 1.2）→ size-cap → 存活。"""
    pdf = _make_pdf(tmp_path / "big.pdf", [
        _body_lines(700) + [("1", "F4", 24.0, BAND_Y)],
        _body_lines(700) + [("2", "F4", 24.0, BAND_Y)],
    ])
    got = _by_content(pdf)
    for digit in ("1", "2"):
        assert got[digit].type == "heading", digit
        assert "heading_suppressed" not in got[digit].metadata


def test_e2e_repeated_band_digit_goes_to_d2(tmp_path: Path):
    """同一裸数字在 ≥2 页底带逐字出现 → D2 优先（band_repeat），
    D3 不重复判定。"""
    pdf = _make_pdf(tmp_path / "rep.pdf", [
        _body_lines(700) + [("5", "F4", 10.0, BAND_Y)],
        _body_lines(700) + [("5", "F4", 10.0, BAND_Y)],
    ])
    doc = _parse_doc(pdf)
    hits = [e for e in doc.elements if e.content == "5"]
    assert len(hits) == 2
    for e in hits:
        assert e.type == "paragraph"
        assert e.metadata["heading_suppressed"] == "page_furniture_band_repeat"


# ---------- 端到端：管线/schema ----------

def test_e2e_pipeline_schema_and_order(tmp_path: Path):
    """混合 D1+D3 文档过完整管线：schema 通过、element_id 严格递增、
    抑制计数精确。"""
    pdf = _make_pdf(tmp_path / "pipe.pdf", [
        _body_lines(700) + [("Page 01", "F1", 10.0, BAND_Y),
                            ("1", "F4", 10.0, 25.0)],
        _body_lines(700) + [("2", "F4", 10.0, BAND_Y)],
    ])
    out = tmp_path / "pipe.json"
    doc, errs = process_single(pdf, out)
    assert errs == []
    assert out.exists() and doc is not None
    reasons = sorted(
        e.metadata.get("heading_suppressed")
        for e in doc.elements
        if e.metadata.get("heading_suppressed", "").startswith("page_furniture_")
    )
    assert reasons == [
        "page_furniture_digit_page_number",
        "page_furniture_digit_page_number",
        "page_furniture_page_number",
    ]
    ids = [e.element_id for e in doc.elements]
    assert ids == sorted(ids)


# ---------- 单元级：谓词矩阵与保守退化（不依赖 PDF） ----------

def _heading(eid: str, text: str, page: int = 1) -> Element:
    return Element(
        element_id=eid,
        type="heading",
        content=text,
        source_locator={"family": "page_geometry", "page": page,
                        "bbox": [72.0, 726.0, 120.0, 736.67]},
        confidence=0.85,
        metadata={"level": 0, "heuristic": "short_line"},
    )


def _word(text: str, fontname, font_size,
          x0=72.0, x1=110.0, top=728.0, bottom=736.0) -> dict:
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": bottom,
            "fontname": fontname, "font_size": font_size}


HEIGHTS = {1: 792.0, 2: 792.0}


def _words_for(*fonts_sizes) -> dict[int, list[dict]]:
    """构造 words_by_page[1]：元素词逐个给定 (fontname, font_size)；
    追加 30 个正文词（Body×3 字体各 10，挤满 top-3）。"""
    inside = [_word(str(i), fn, fs) for i, (fn, fs) in enumerate(fonts_sizes)]
    body_words = [
        _word(f"w{i}", f"Body{k}", 10.0, x0=200.0 + i, x1=240.0 + i,
              top=100.0 + (i % 30) * 2, bottom=108.0 + (i % 30) * 2)
        for i in range(30)
        for k in (i % 3,)
    ]
    return {1: inside + body_words, 2: []}


def test_unit_d3_hit_and_full_matrix():
    el = _heading("d::e0001", "7")
    out = _suppress_page_furniture_headings(
        [el], HEIGHTS, _words_for(("Outside", 10.0)))
    assert out[0].type == "paragraph"
    assert out[0].metadata["heading_suppressed"] == "page_furniture_digit_page_number"


def test_unit_d3_fontout_false_survives():
    el = _heading("d::e0001", "7")
    out = _suppress_page_furniture_headings(
        [el], HEIGHTS, _words_for(("Body0", 10.0)))
    assert out[0].type == "heading"
    assert "heading_suppressed" not in out[0].metadata


def test_unit_d3_size_cap_survives():
    el = _heading("d::e0001", "7")
    out = _suppress_page_furniture_headings(
        [el], HEIGHTS, _words_for(("Outside", 13.0)))  # r = 1.3 > 1.2
    assert out[0].type == "heading"


def test_unit_d3_boundary_size_12_passes():
    el = _heading("d::e0001", "7")
    out = _suppress_page_furniture_headings(
        [el], HEIGHTS, _words_for(("Outside", 12.0)))  # r = 1.2 恰过
    assert out[0].type == "paragraph"


def test_unit_d3_no_attr_words_survive():
    """元素词 fontname/font_size 全 None → 主导字体/字号不可得 →
    保守不命中（r76③④ 空属性退化）。"""
    el = _heading("d::e0001", "7")
    out = _suppress_page_furniture_headings(
        [el], HEIGHTS, _words_for((None, None)))
    assert out[0].type == "heading"
    assert "heading_suppressed" not in out[0].metadata


def test_unit_d3_missing_size_survives():
    """fontname 圈外但 font_size None → size-cap 不可算 → 保守不命中。"""
    el = _heading("d::e0001", "7")
    out = _suppress_page_furniture_headings(
        [el], HEIGHTS, _words_for(("Outside", None)))
    assert out[0].type == "heading"


def test_unit_d3_words_channel_none_inactive():
    """words_by_page=None（无 font 通道）→ D3 整体不激活：底带裸
    数字存活，D1/D2 照常。"""
    el = _heading("d::e0001", "7")
    out = _suppress_page_furniture_headings([el], HEIGHTS)
    assert out[0].type == "heading"
    d1 = _heading("d::e0002", "Page 7")
    out2 = _suppress_page_furniture_headings([d1], HEIGHTS)
    assert out2[0].metadata["heading_suppressed"] == "page_furniture_page_number"


def test_unit_d3_no_sizes_anywhere_inactive():
    """全文档无任何 font_size（body_mode 不可得）→ D3 整体不激活。"""
    el = _heading("d::e0001", "7")
    words = {1: [_word("w", None, None)], 2: []}
    out = _suppress_page_furniture_headings([el], HEIGHTS, words)
    assert out[0].type == "heading"


def test_unit_d3_mixed_size_element_uses_max():
    """混排元素字号取最大：圈外主导 + 混入 10/14pt → r=1.4 → 存活。"""
    el = _heading("d::e0001", "7")
    out = _suppress_page_furniture_headings(
        [el], HEIGHTS, _words_for(("Outside", 10.0), ("Outside", 14.0)))
    assert out[0].type == "heading"


def test_unit_d3_digit_shape_bounded():
    r"""裸数字形态边界：5 位数字/带标点/罗马数字/文件名形态不命中；
    4 位年份形（2026）在 \d{1,4} 冻结边界内，命中。"""
    for text in ("12345", "7.", "iv", "report.pdf", "-3"):
        el = _heading("d::e0001", text)
        out = _suppress_page_furniture_headings(
            [el], HEIGHTS, _words_for(("Outside", 10.0)))
        assert out[0].type == "heading", text
    el = _heading("d::e0001", "2026")
    out = _suppress_page_furniture_headings(
        [el], HEIGHTS, _words_for(("Outside", 10.0)))
    assert out[0].type == "paragraph"
    assert out[0].metadata["heading_suppressed"] == (
        "page_furniture_digit_page_number")


def test_unit_structure_preserved():
    """命中仅改 type 与追加 metadata 键；element_id/顺序/文本/
    locator/bbox/置信度/其余 metadata 不变。"""
    els = [_heading("d::e0000", "First Topic", page=2),
           _heading("d::e0001", "7")]
    # e0000 在第 2 页（无词 → 不命中）；e0001 命中
    words = _words_for(("Outside", 10.0))
    before = [(e.element_id, e.content, dict(e.source_locator),
               e.confidence, dict(e.metadata)) for e in els]
    out = _suppress_page_furniture_headings(list(els), HEIGHTS, words)
    assert [e.element_id for e in out] == [b[0] for b in before]
    assert [e.content for e in out] == [b[1] for b in before]
    assert [e.source_locator for e in out] == [b[2] for b in before]
    assert [e.confidence for e in out] == [b[3] for b in before]
    assert out[0].type == "heading"
    assert out[1].type == "paragraph"
    assert out[1].metadata == {
        "level": 0, "heuristic": "short_line",
        "heading_suppressed": "page_furniture_digit_page_number",
    }


def test_unit_d3_deterministic_repeat():
    """同一输入两次运行输出恒等（top-3 并列按词序，确定性）。"""
    els = [_heading("d::e0001", "7"), _heading("d::e0002", "8")]
    words = _words_for(("Outside", 10.0))
    r1 = _suppress_page_furniture_headings(list(els), HEIGHTS, words)
    r2 = _suppress_page_furniture_headings(list(els), HEIGHTS, words)
    assert [(e.element_id, e.type, dict(e.metadata)) for e in r1] == \
           [(e.element_id, e.type, dict(e.metadata)) for e in r2]
