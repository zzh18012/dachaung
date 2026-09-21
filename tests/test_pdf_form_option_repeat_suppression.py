"""Stage 10 批次 12 acceptance-hardening 测试：表单选项同列堆叠 heading
页级后置过滤（r68 D-safe = S1a ∧ S2a 授权）。

裁决边界（ADOPTION §156）：
- 仅当元素已是 heading，且规范化全文 ∈ 冻结封闭词集
  {yes, no, n/a, no n/a, yes no n/a}（S1a），且同一物理页上同一规范化
  文本 ≥3 个 heading 的 bbox x 区间经重叠聚类属于同一列簇（S2a），
  才抑制为 paragraph + metadata.heading_suppressed=form_option_repeat；
- 规范化仅 trim + 连续空白折叠 + 大小写归一——不删标点、不模糊匹配、
  不同义词扩展、不 token 编辑距离、不加词（'Yes.' 必须存活）；
- 分属不同 x 列簇的实例各自计数，不跨簇合并整体压制；
- x 聚类为区间重叠（含边界相接），非绝对坐标 rounding；
- 落点为独立页级 post-filter，不进批次 6 _form_label_signal；
- 不硬编码 real-02 真实样本内容，夹具字符串全部为等义合成行。

r68 必备八项（本文件钉死前七项 + 既有批次 6/9/12 回归由测试套整体保持）：
1 同页同列 ≥3 Yes → suppress；2 ≥3 No N/A → suppress；
3 单独合法 Yes heading 存活；4 'Yes.' 存活；
5 ≥3 重复合法非 option heading 存活；6 option 重复不足 3 次存活；
7 option ≥3 次但分属不同 x 列簇不整体压制。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.models import Element
from app.parsers.fallback_parser import (
    FallbackParser,
    _option_heading_key,
    _suppress_form_option_repeat_headings,
)
from app.pipeline import process_single


# ---------- 单元级夹具 ----------

def _mk_heading(eid: str, text: str, page: int, x0: float, x1: float) -> Element:
    return Element(
        element_id=eid,
        type="heading",
        content=text,
        source_locator={
            "family": "page_geometry", "page": page, "bbox": [x0, 100.0, x1, 110.0],
        },
        confidence=0.85,
        metadata={"level": 0, "heuristic": "short_line"},
    )


LEFT_X = (72.0, 120.0)
RIGHT_X = (400.0, 440.0)


# ---------- 1/2：同页同列 ≥3 → 抑制 ----------

def test_same_page_same_column_yes_x3_suppressed():
    els = [
        _mk_heading("d::e0000", "Yes", 1, *RIGHT_X),
        _mk_heading("d::e0001", "Yes", 1, *RIGHT_X),
        _mk_heading("d::e0002", "Yes", 1, *RIGHT_X),
    ]
    out = _suppress_form_option_repeat_headings(els)
    assert all(e.type == "paragraph" for e in out)
    assert all(e.metadata["heading_suppressed"] == "form_option_repeat" for e in out)


def test_same_page_same_column_no_na_x3_suppressed():
    els = [
        _mk_heading("d::e0000", "No N/A", 1, *RIGHT_X),
        _mk_heading("d::e0001", "no  n/a", 1, *RIGHT_X),   # 空白折叠后同文
        _mk_heading("d::e0002", "NO N/A", 1, *RIGHT_X),    # 大小写归一后同文
    ]
    out = _suppress_form_option_repeat_headings(els)
    assert all(e.type == "paragraph" for e in out)
    assert all(e.metadata["heading_suppressed"] == "form_option_repeat" for e in out)


# ---------- 3：单独合法 Yes 存活 ----------

def test_single_legal_yes_survives():
    els = [_mk_heading("d::e0000", "Yes", 1, *RIGHT_X)]
    out = _suppress_form_option_repeat_headings(els)
    assert out[0].type == "heading"
    assert "heading_suppressed" not in out[0].metadata


# ---------- 4：'Yes.' 存活（规范化不删标点） ----------

def test_yes_with_period_survives():
    els = [
        _mk_heading("d::e0000", "Yes.", 1, *RIGHT_X),
        _mk_heading("d::e0001", "Yes.", 1, *RIGHT_X),
        _mk_heading("d::e0002", "Yes.", 1, *RIGHT_X),
    ]
    out = _suppress_form_option_repeat_headings(els)
    assert all(e.type == "heading" for e in out)
    # 词集整行精确匹配：带标点不入词集（同理逗号/分号/编辑距离形态）
    for text in ("Yes,", "yes;", "Yse", "ye s"):
        assert _option_heading_key(_mk_heading("d::x", text, 1, *RIGHT_X)) is None


# ---------- 5：≥3 重复合法非 option heading 存活 ----------

def test_repeated_non_option_heading_survives():
    els = [
        _mk_heading("d::e0000", "Interview", 1, *LEFT_X),
        _mk_heading("d::e0001", "Interview", 1, *LEFT_X),
        _mk_heading("d::e0002", "Interview", 1, *LEFT_X),
        _mk_heading("d::e0003", "Details:", 1, *LEFT_X),
    ]
    out = _suppress_form_option_repeat_headings(els)
    assert all(e.type == "heading" for e in out)
    assert all("heading_suppressed" not in e.metadata for e in out)


# ---------- 6：option 重复不足 3 次（恰 2）存活 ----------

def test_option_repeat_below_threshold_survives():
    els = [
        _mk_heading("d::e0000", "Yes", 1, *RIGHT_X),
        _mk_heading("d::e0001", "Yes", 1, *RIGHT_X),
        _mk_heading("d::e0002", "No N/A", 1, *RIGHT_X),
        _mk_heading("d::e0003", "No N/A", 1, *RIGHT_X),
    ]
    out = _suppress_form_option_repeat_headings(els)
    assert all(e.type == "heading" for e in out)


# ---------- 7：option ≥3 次分属不同 x 列簇 → 簇内各自计数 ----------

def test_option_x3_split_across_columns_not_whole_suppressed():
    """2+2 分两列：两簇各 <3 → 全部存活，不得跨簇合并整体压制。"""
    els = [
        _mk_heading("d::e0000", "Yes", 1, *LEFT_X),
        _mk_heading("d::e0001", "Yes", 1, *LEFT_X),
        _mk_heading("d::e0002", "Yes", 1, *RIGHT_X),
        _mk_heading("d::e0003", "Yes", 1, *RIGHT_X),
    ]
    out = _suppress_form_option_repeat_headings(els)
    assert all(e.type == "heading" for e in out)


def test_option_3_plus_2_cluster_local_suppression():
    """3+2 分两列：仅 ≥3 的列簇抑制，另一簇 2 条存活。"""
    els = [
        _mk_heading("d::e0000", "Yes", 1, *RIGHT_X),
        _mk_heading("d::e0001", "Yes", 1, *RIGHT_X),
        _mk_heading("d::e0002", "Yes", 1, *RIGHT_X),
        _mk_heading("d::e0003", "Yes", 1, *LEFT_X),
        _mk_heading("d::e0004", "Yes", 1, *LEFT_X),
    ]
    out = _suppress_form_option_repeat_headings(els)
    for e in out:
        if e.element_id in ("d::e0000", "d::e0001", "d::e0002"):
            assert e.type == "paragraph"
            assert e.metadata["heading_suppressed"] == "form_option_repeat"
        else:
            assert e.type == "heading"
            assert "heading_suppressed" not in e.metadata


# ---------- 词集边界（r68 钉死的规范化三步之外一律不做） ----------

def test_vocab_membership_exact():
    in_vocab = ["Yes", "  YES  ", "No", "n/a", "N/A", "No N/A", "no  n/a",
                "Yes No N/A", "yes  no   n/a"]
    for i, text in enumerate(in_vocab):
        el = _mk_heading(f"d::v{i}", text, 1, *RIGHT_X)
        key = _option_heading_key(el)
        assert key is not None, text
        assert key[0] == " ".join(text.casefold().split())
    not_in_vocab = ["Yes.", "Yes,", "yes;", "yea", "n/a.", "N.A", "NoN/A",
                    "Yes No", "Maybe", "Not applicable", "yes/no"]
    for i, text in enumerate(not_in_vocab):
        assert _option_heading_key(_mk_heading(f"d::w{i}", text, 1, *RIGHT_X)) is None


def test_page_local_no_cross_page_aggregation():
    """S2a 是页内证据：不同页各 2/1 条不聚合。"""
    els = [
        _mk_heading("d::e0000", "Yes", 1, *RIGHT_X),
        _mk_heading("d::e0001", "Yes", 1, *RIGHT_X),
        _mk_heading("d::e0002", "Yes", 2, *RIGHT_X),
    ]
    out = _suppress_form_option_repeat_headings(els)
    assert all(e.type == "heading" for e in out)


def test_x_clustering_interval_overlap_inclusive_edge():
    """x 聚类为区间重叠：round 边界差 1pt 仍同簇；大幅错开则拆簇。"""
    near = [
        _mk_heading("d::e0000", "Yes", 1, 400.0, 440.0),
        _mk_heading("d::e0001", "Yes", 1, 401.0, 441.0),   # 重叠
        _mk_heading("d::e0002", "Yes", 1, 440.0, 480.0),   # 边界相接（含）
    ]
    out = _suppress_form_option_repeat_headings(near)
    assert all(e.type == "paragraph" for e in out)


def test_non_heading_and_missing_bbox_untouched():
    para = Element(
        element_id="d::e0000", type="paragraph", content="Yes",
        source_locator={"family": "page_geometry", "page": 1,
                        "bbox": list(RIGHT_X) + [100.0, 110.0]},
        metadata={},
    )
    no_bbox = Element(
        element_id="d::e0001", type="heading", content="Yes",
        source_locator={"family": "page_geometry", "page": 1},
        metadata={"level": 0},
    )
    els = [para, no_bbox,
           _mk_heading("d::e0002", "Yes", 1, *RIGHT_X),
           _mk_heading("d::e0003", "Yes", 1, *RIGHT_X)]
    out = _suppress_form_option_repeat_headings(els)
    assert out[0].type == "paragraph"            # 已是 paragraph 不动
    assert out[1].type == "heading"              # 缺 bbox 不参与
    # 文本计数 3（含缺 bbox 者），但有效参与仅 2 < 3 → 全部存活
    assert out[2].type == out[3].type == "heading"


def test_suppression_preserves_structure():
    """命中抑制仅改 type 与追加 metadata 键；element_id/顺序/文本/
    locator/bbox/置信度/其余 metadata 一律不变。"""
    els = [
        _mk_heading("d::e0000", "Training", 1, *LEFT_X),
        _mk_heading("d::e0001", "Yes", 1, *RIGHT_X),
        _mk_heading("d::e0002", "Yes", 1, *RIGHT_X),
        _mk_heading("d::e0003", "Yes", 1, *RIGHT_X),
    ]
    before = [(e.element_id, e.content, dict(e.source_locator), e.confidence)
              for e in els]
    out = _suppress_form_option_repeat_headings(els)
    assert [e.element_id for e in out] == [b[0] for b in before]
    assert [e.content for e in out] == [b[1] for b in before]
    assert [e.source_locator for e in out] == [b[2] for b in before]
    assert [e.confidence for e in out] == [b[3] for b in before]
    assert out[0].type == "heading"
    assert out[0].metadata == {"level": 0, "heuristic": "short_line"}
    for e in out[1:]:
        assert e.type == "paragraph"
        assert e.metadata == {"level": 0, "heuristic": "short_line",
                              "heading_suppressed": "form_option_repeat"}


# ---------- 端到端：手写最小 PDF（自包含合成夹具） ----------

def _escape_pdf_literal(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _stream(positions: list[tuple[str, float, float]]) -> str:
    """单页多行文本；positions = [(文本, x 基线, y 基线), ...]。

    行距全部 > 30pt（> 1.5×10pt 行高阈值），确保逐行独立成段；
    左右栏 y 交错（差 > 3pt 行聚类阈值），无论 Tier-1 分区器是否
    分裂都不会跨栏并线。
    """
    ops = [
        f"BT /F1 10 Tf {x} {y} Td ({_escape_pdf_literal(t)}) Tj ET"
        for t, x, y in positions
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


QUESTION = ("Was the mandatory safety training for this reporting period "
            "completed and recorded.")

LX = 72    # 左栏（问题行）基线 x
RX = 440   # 右栏（应答碎片）基线 x

# 相邻基线差须 > 25pt（空白 = 基线差 − 行高 10pt > 1.5×行高 15pt），
# 否则跨栏相邻行会被并段；本表全部 ≥ 30pt。
QUESTION_YS = (700.0, 500.0, 350.0)
YES_SLOTS = (660.0, 630.0, 600.0, 570.0, 540.0)


def _form_page(yes_count: int, extra: list[tuple[str, float, float]] | None = None) -> str:
    """表单页：左栏问题行（句号结尾 → paragraph）+ 右栏 Yes 碎片。"""
    positions: list[tuple[str, float, float]] = [
        (QUESTION, LX, y) for y in QUESTION_YS
    ]
    positions.extend(("Yes", RX, YES_SLOTS[i]) for i in range(yes_count))
    if extra:
        positions.extend(extra)
    return _stream(positions)


def _parse_doc(pdf_path: Path):
    h = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    return FallbackParser().parse(pdf_path, source_hash=h)


def test_e2e_form_option_column_suppressed(tmp_path: Path):
    """右栏 4 个 Yes 碎片（≥3 同列堆叠）→ 全部抑制；
    左栏问题行仍 paragraph；左栏合法短标题存活。"""
    pdf = _make_pdf(tmp_path / "form.pdf", [
        _form_page(4, extra=[("Training", LX, 300.0)]),
    ])
    doc = _parse_doc(pdf)
    yes_els = [e for e in doc.elements if e.content == "Yes"]
    assert len(yes_els) == 4
    assert all(e.type == "paragraph" for e in yes_els)
    assert all(e.metadata.get("heading_suppressed") == "form_option_repeat"
               for e in yes_els)
    assert sum(1 for e in doc.elements if e.content == QUESTION
               and e.type == "paragraph") == 3
    training = [e for e in doc.elements if e.content == "Training"]
    assert len(training) == 1
    assert training[0].type == "heading"
    assert "heading_suppressed" not in training[0].metadata
    ids = [e.element_id for e in doc.elements]
    assert ids == sorted(ids)


def test_e2e_two_yes_fragments_survive(tmp_path: Path):
    """同页同列仅 2 个 Yes：不足 3，存活 heading（页级证据不满足）。"""
    pdf = _make_pdf(tmp_path / "two.pdf", [_form_page(2)])
    doc = _parse_doc(pdf)
    yes_els = [e for e in doc.elements if e.content == "Yes"]
    assert len(yes_els) == 2
    assert all(e.type == "heading" for e in yes_els)


def test_e2e_suppressed_document_passes_pipeline_schema(tmp_path: Path):
    """抑制后的文档仍通过管线 schema 校验（process_single 全链）。"""
    pdf = _make_pdf(tmp_path / "pipe.pdf", [
        _form_page(5),
        _form_page(3),
    ])
    out = tmp_path / "pipe.json"
    doc, errs = process_single(pdf, out)
    assert errs == []
    assert out.exists()
    assert doc is not None
    suppressed = [e for e in doc.elements
                  if e.metadata.get("heading_suppressed") == "form_option_repeat"]
    # p1：5 个 Yes 同列堆叠 ≥3 → 抑制；p2：3 个也 ≥3 → 抑制
    assert len(suppressed) == 8
