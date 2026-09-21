"""Stage 10 批次 12 测试：PDF Tier-1 保守栏分区器（r66 授权）。

授权边界（ADOPTION §152）：
- 仅 Tier-1 区域形成：投影剖面全高空白河 + 数据驱动河宽下限
  max(15pt, 2.5×行内相邻词距中位数) + 行级双岸支持（空档 ≥
  max(下限, 2×该行中位字高））+ 质量守卫（两侧各 ≥2%）+ 宽度/深度/
  词数下限；区域顺序确定性左→右；
- 单区退化路径必须直接把原 words 交给既有 _group_words_to_paragraphs
  （不重排不重建，单栏页序列化零差异目标）；
- 禁止（越界即停链）：Tier-2 候选特征、元素去重替换、caption 配对
  门控、schema/locator/extract_words 参数变化；
- 参数与 shadow 证据（outputs/batch11_layout_shadow_report.txt，
  scripts/stage10_batch11_layout_prototype.py）逐项冻结。
全合成夹具，零真实语料；夹具构造与批次 11 shadow 原型同构。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import app.parsers.fallback_parser as fp
from app.models import Document, Element


# ---------- word-dict 夹具（与 shadow 原型同构造） ----------

def _w(text: str, x0: float, x1: float, top: float, h: float = 10.0) -> dict:
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": top + h}


def _line_words(text: str, x0: float, x1: float, top: float, n: int = 6,
                h: float = 10.0, fill: float = 0.9) -> list[dict]:
    span = (x1 - x0) / n
    out = []
    for i in range(n):
        a = x0 + i * span
        out.append(_w(text[i * 2:i * 2 + 2] or "x", a, a + span * fill, top, h))
    return out


def _fx_single_col() -> list[dict]:
    ws = []
    for i in range(25):
        ws += _line_words("aa bb cc dd ee ff", 80, 512, 100 + i * 14)
    return ws


def _fx_wide_word_gaps() -> list[dict]:
    ws = []
    for i in range(25):
        ws += _line_words("aa bb cc dd ee ff", 80, 512, 100 + i * 14, fill=0.72)
    return ws  # ~20pt 行内词距：数据驱动下限必须拒绝分裂


def _fx_two_col() -> list[dict]:
    ws = []
    for i in range(20):
        ws += _line_words("aa bb cc dd", 60, 280, 100 + i * 14)
        ws += _line_words("ee ff gg hh", 320, 540, 100 + i * 14)
    return ws  # 河 276.3..320 ≈ 43.7pt


def _fx_spanning_title() -> list[dict]:
    ws = _line_words("TITLE SPANS BOTH COLUMNS", 60, 540, 80, n=7, h=18, fill=0.86)
    ws += _fx_two_col()
    return ws


def _fx_numbered_realistic() -> list[dict]:
    ws, y = [], 100
    for n in range(1, 13):
        ws.append(_w(f"{n}.", 80, 96, y))
        ws += _line_words("item text body", 130, 500, y, n=5)
        y += 14
        if n % 3 == 0:
            ws += _line_words("cont body", 130, 500, y, n=5)
            y += 14
    return ws


def _fx_numbered_pure() -> list[dict]:
    ws, y = [], 100
    for n in range(1, 21):
        ws.append(_w(f"{n}.", 80, 96, y))
        ws += _line_words("item text body", 150, 500, y, n=5)
        y += 14
    return ws


def _fx_borderless_kv() -> list[dict]:
    ws, y = [], 100
    drift = [300, 312, 306, 340, 328, 356]
    for i in range(6):
        ws.append(_w("key001", 100, 140, y))
        ws.append(_w("val", drift[i], drift[i] + 60, y))
        ws.append(_w("tail", drift[i] + 80, drift[i] + 130, y))
        y += 16
    return ws


def _fx_borderless_sparse() -> list[dict]:
    ws, y = [], 100
    for i in range(3):
        ws.append(_w("k1", 100, 120, y))
        ws.append(_w("v1", 330, 400, y))
        y += 18
    return ws


# ---------- A：夹具矩阵（shadow 报告 8/8 的区域数钉死） ----------

FIXTURE_COUNTS = [
    ("single_col", _fx_single_col, 1),
    ("wide_word_gaps", _fx_wide_word_gaps, 1),
    ("two_col", _fx_two_col, 2),
    ("spanning_title", _fx_spanning_title, 1),
    ("numbered_realistic", _fx_numbered_realistic, 1),
    ("numbered_pure", _fx_numbered_pure, 1),
    ("borderless_kv", _fx_borderless_kv, 1),
    ("borderless_sparse", _fx_borderless_sparse, 1),
]


@pytest.mark.parametrize("name,make,expected", FIXTURE_COUNTS, ids=[n for n, _, _ in FIXTURE_COUNTS])
def test_a_fixture_region_counts(name, make, expected):
    regions = fp._split_words_into_column_regions(make())
    assert len(regions) == expected


def test_a_two_col_regions_disjoint_left_to_right():
    regions = fp._split_words_into_column_regions(_fx_two_col())
    assert len(regions) == 2
    assert max(float(w["x1"]) for w in regions[0]) < min(float(w["x0"]) for w in regions[1])
    # 分区无丢失无重复：两区词数之和 == 原词数（每行 6 词 × 2 栏 × 20 行）
    assert len(regions[0]) + len(regions[1]) == 20 * 2 * 6


def test_a_frozen_calibration_constants():
    """v1 校准参数冻结（与 shadow 证据一致，防意外漂移）。"""
    assert fp._COLUMN_MIN_RIVER_FLOOR_PT == 15.0
    assert fp._COLUMN_RIVER_GAP_FACTOR == 2.5
    assert fp._COLUMN_LINE_SUPPORT_HEIGHT_FACTOR == 2.0
    assert fp._COLUMN_MIN_REGION_MASS_RATIO == 0.02
    assert fp._COLUMN_MIN_REGION_WIDTH_PT == 20.0
    assert fp._COLUMN_MAX_SPLIT_DEPTH == 3
    assert fp._COLUMN_MIN_WORDS == 8


# ---------- B：_page_paragraphs 语义（跨栏合并消除 + 退化恒等） ----------

def test_b_two_col_no_cross_column_merge():
    paras = fp._page_paragraphs(_fx_two_col())
    # 20 行 × 14pt 间距、字高 10 → 每栏恰一段落，共 2 个
    assert len(paras) == 2
    for p in paras:
        x0, _top, x1, _bottom = p["bbox"]
        assert x1 <= 300 or x0 >= 300  # 整段落在一栏内
    left_words = [w for w in _fx_two_col() if w["x1"] <= 300]
    right_words = [w for w in _fx_two_col() if w["x0"] >= 300]
    expected = (fp._group_words_to_paragraphs(left_words)
                + fp._group_words_to_paragraphs(right_words))
    assert paras == expected


def test_b_two_col_left_before_right():
    paras = fp._page_paragraphs(_fx_two_col())
    assert paras[0]["bbox"][2] < 300  # 左栏在前
    assert paras[1]["bbox"][0] > 300  # 右栏在后


def test_b_old_behavior_merged_cross_column():
    """回归对照：未分区时既有分组会把同 y 左右栏词并成一行（§1 病灶）。"""
    words = _fx_two_col()
    old = fp._group_words_to_paragraphs(words)
    assert len(old) == 1  # 旧路径：单段落、文本左右交错
    assert "aa" in old[0]["text"] and "ee" in old[0]["text"]
    new = fp._page_paragraphs(words)
    assert not ("aa" in new[0]["text"] and "ee" in new[0]["text"])


def test_b_single_region_identity_pass_through(monkeypatch):
    """r66 护栏：单区退化必须以原 words 对象直通既有分组（一次调用，
    不重排不重建）。"""
    for make in (_fx_single_col, _fx_spanning_title, _fx_numbered_pure):
        words = make()
        captured = []
        orig = fp._group_words_to_paragraphs

        def spy(ws, _orig=orig, _cap=captured):
            _cap.append(ws)
            return _orig(ws)

        monkeypatch.setattr(fp, "_group_words_to_paragraphs", spy)
        try:
            fp._page_paragraphs(words)
        finally:
            monkeypatch.setattr(fp, "_group_words_to_paragraphs", orig)
        assert captured == [words]  # 恰一次且为同一 list 对象


def test_b_empty_words_identity():
    assert fp._page_paragraphs([]) == []


def test_b_line_support_refusal_big_font():
    """行级支持判据隔离验证：同一双栏正文，无标题 → 2 区；
    加一条 h=18 通栏行（空档 21pt < 2×18=36pt 需求）→ 拒绝开口 → 1 区。"""
    body = []
    for i in range(15):
        body += _line_words("aa bb cc", 100, 279, 200 + i * 14)
        body += _line_words("dd ee ff", 301, 480, 200 + i * 14)
    assert len(fp._split_words_into_column_regions(body)) == 2  # 河 279..301 = 22pt
    titled = [_w("BIGTITLELEFT", 100, 279.5, 160, h=18),
              _w("BIGTITLERIGHT", 300.5, 480, 160, h=18)] + body
    assert len(fp._split_words_into_column_regions(titled)) == 1


# ---------- C：多栏页 table/caption 邻域守护（r66 必备夹具） ----------

def _grid_words(x0: float, x1: float, top: float, rows: int, cols: int,
                pitch: float = 16.0, h: float = 10.0) -> list[dict]:
    """有框表格被 extract_words 抽出的词矩阵形态（满宽覆盖）。"""
    ws = []
    span = (x1 - x0) / cols
    for r in range(rows):
        for c in range(cols):
            a = x0 + c * span
            ws.append(_w(f"c{r}{c}", a, a + span * 0.8, top + r * pitch, h))
    return ws


def test_c_table_neighborhood_blocks_split():
    """双栏正文 + 页底满宽表格词矩阵：河被表格词占据 → 不分裂（保守），
    输出与既有分组恒等（表格邻域不得诱发栏切分）。"""
    words = _fx_two_col() + _grid_words(60, 540, 420, rows=5, cols=6)
    assert len(fp._split_words_into_column_regions(words)) == 1
    assert fp._page_paragraphs(words) == fp._group_words_to_paragraphs(words)


def test_c_caption_neighborhood_blocks_split():
    """双栏正文 + 页底满宽图注行：同样阻断全高河 → 不分裂（保守）。"""
    caption = _line_words("Figure 1. synthetic caption spanning both columns",
                          60, 540, 420, n=8)
    words = _fx_two_col() + caption
    assert len(fp._split_words_into_column_regions(words)) == 1
    assert fp._page_paragraphs(words) == fp._group_words_to_paragraphs(words)


def test_c_table_below_single_col_unaffected():
    """单栏正文 + 表格（无河可切）：退化路径，分区器零影响。"""
    words = _fx_single_col() + _grid_words(80, 512, 480, rows=4, cols=5)
    assert len(fp._split_words_into_column_regions(words)) == 1
    assert fp._page_paragraphs(words) == fp._group_words_to_paragraphs(words)


# ---------- D：手写最小 PDF 端到端（管线级，自包含） ----------

def _escape_pdf_literal(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _two_col_stream() -> str:
    """12 行双栏正文：左栏 x=60 起，右栏 x=320 起，同行同基线。"""
    ops = []
    for i in range(12):
        y = 700 - i * 14
        ops.append(f"BT /F1 10 Tf 60 {y} Td ({_escape_pdf_literal(f'ALPHA left column line {i} body')}) Tj ET")
        ops.append(f"BT /F1 10 Tf 320 {y} Td ({_escape_pdf_literal(f'beta right column line {i} body')}) Tj ET")
    return "\n".join(ops) + "\n"


def _single_col_stream() -> str:
    """4 行单栏正文：行距 32pt（行间空档 > 1.5×字高）→ 逐行独立成段。"""
    ops = [
        f"BT /F1 10 Tf 72 {y} Td ({_escape_pdf_literal(t)}) Tj ET"
        for t, y in [
            ("First single column line", 700),
            ("Second single column line", 668),
            ("Third single column line", 636),
            ("Fourth single column line", 604),
        ]
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


def _parse(tmp_path: Path, name: str, streams: list[str]) -> Document:
    path = _make_pdf(tmp_path / name, streams)
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return fp.FallbackParser().parse(path, source_hash=h)


def test_d_two_col_pdf_no_interleaved_elements(tmp_path: Path):
    doc = _parse(tmp_path, "twocol.pdf", [_two_col_stream()])
    paras = [e for e in doc.elements if e.type in ("paragraph", "heading", "caption")]
    assert len(paras) == 2  # 每栏一个段落
    first, second = paras
    assert "ALPHA" in first.content and "beta" not in first.content
    assert "beta" in second.content and "ALPHA" not in second.content
    assert first.source_locator["bbox"][2] < 320  # 左栏在前且 bbox 在栏内
    assert second.source_locator["bbox"][0] > 300  # 右栏在后


def test_d_single_col_pdf_reading_order_unchanged(tmp_path: Path):
    doc = _parse(tmp_path, "singlecol.pdf", [_single_col_stream()])
    paras = [e for e in doc.elements if e.type in ("paragraph", "heading", "caption")]
    assert [p.content for p in paras] == [
        "First single column line",
        "Second single column line",
        "Third single column line",
        "Fourth single column line",
    ]
