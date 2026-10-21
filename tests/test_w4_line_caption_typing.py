r"""W4 行级题注切分测试（r89-Q1 实现授权）。

裁决验收纪律（r89 §二"实现验收纪律"7 条）中的可单测面：
- 段中部题注行**移出**宿主段落（非复制），宿主 content 收缩；
- 同一文本不得同时存在于 caption 与 paragraph；
- 去重：same page + 行 bbox 被既有 caption bbox 包含 + same label
  → 跳过发射（行亦自宿主移除）；
- 纯题注段（段首命中）仍整段成 caption，不拆行；
- u0038 类（数字后纯空白）行级不命中；
- DOCX 零改动（docx 通道不经 `_split_caption_lines`）。

规格：design/w4-caption-typing-spec-v1.md（grammar §2.2 迭代 2 冻结
形态）。dev 面验收数字（new captions / duplicates suppressed /
false positives / paragraph text conservation）由 adoption 侧实现批
次探针报告，不在本文件。
"""

from __future__ import annotations

from app.parsers.fallback_parser import (
    _caption_label_key,
    _classify_pdf_paragraph,
    _lines_to_para,
    _split_caption_lines,
)


def _w(text: str, x0: float, x1: float, top: float, bottom: float) -> dict:
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": bottom}


def _para(lines: list[list[dict]]) -> dict:
    return _lines_to_para(lines)


# ---------- grammar：行级命中面 ----------

def test_mid_paragraph_caption_line_promoted():
    # acad-02/06 形：题注行被并进正文段（gap ≤ 1.5×median_h）
    para = _para([
        [_w("The", 50, 70, 100, 110), _w("results", 75, 110, 100, 110)],
        [_w("Table1:Comparisonwithpublishedmodels", 50, 300, 112, 122)],
        [_w("More", 50, 80, 124, 134), _w("text", 85, 110, 124, 134)],
    ])
    promoted, host = _split_caption_lines(para, [])
    assert len(promoted) == 1
    assert promoted[0]["text"] == "Table1:Comparisonwithpublishedmodels"
    assert promoted[0]["label_key"] == "table:1"
    assert "Table1" not in host["text"]
    assert host["text"].startswith("The results")
    assert host["text"].endswith("More text")


def test_u0038_form_line_not_promoted():
    # 数字后纯空白（"Figure 3 gives…"）行级不命中（r89 W4-C 同口径）
    para = _para([
        [_w("Figure", 50, 80, 100, 110), _w("3", 85, 92, 100, 110),
         _w("gives", 97, 125, 100, 110), _w("an", 130, 145, 100, 110)],
    ])
    promoted, host = _split_caption_lines(para, [])
    assert promoted == []
    assert host["text"] == "Figure 3 gives an"


def test_spaced_delimiter_line_promoted():
    para = _para([
        [_w("intro", 50, 90, 100, 110)],
        [_w("Figure", 50, 80, 112, 122), _w("1:", 85, 95, 112, 122),
         _w("Sketch", 100, 135, 112, 122), _w("of", 140, 152, 112, 122)],
    ])
    promoted, _ = _split_caption_lines(para, [])
    assert len(promoted) == 1
    assert promoted[0]["label_key"] == "figure:1"


def test_fullwidth_forms_promoted():
    para = _para([
        [_w("图", 50, 62, 100, 110), _w("３：", 67, 85, 100, 110),
         _w("系统架构", 90, 130, 100, 110)],
    ])
    promoted, _ = _split_caption_lines(para, [])
    assert len(promoted) == 1
    assert promoted[0]["label_key"] == "figure:3"  # 全角数字 NFKC 归一


# ---------- 去重（r89 验收纪律 §5）----------

def test_duplicate_contained_same_label_suppressed():
    # 既有 caption（同页同标签）bbox 包含候选行 → 跳过发射、行自宿主移除
    existing = ([40, 100, 400, 130], "table:1")
    page_captions = [existing]
    para = _para([
        [_w("body", 50, 90, 90, 98)],
        [_w("Table1:Comparison", 50, 300, 105, 115)],
    ])
    promoted, host = _split_caption_lines(para, page_captions)
    assert promoted == []
    assert "Table1" not in host["text"]  # 不双栖：文本已在既有 caption 内


def test_contained_but_different_label_promoted():
    # bbox 包含但标签不同（table:2 vs table:1）→ 正常发射
    page_captions = [([40, 100, 400, 130], "table:1")]
    para = _para([
        [_w("body", 50, 90, 90, 98)],
        [_w("Table2:Results", 50, 300, 105, 115)],
    ])
    promoted, _ = _split_caption_lines(para, page_captions)
    assert len(promoted) == 1
    assert promoted[0]["label_key"] == "table:2"


def test_same_label_not_contained_promoted():
    # 同标签但既有 caption 不包含该行 → 正常发射（不同页位/版面）
    page_captions = [([40, 300, 400, 330], "table:1")]
    para = _para([
        [_w("body", 50, 90, 90, 98)],
        [_w("Table1:Comparison", 50, 300, 105, 115)],
    ])
    promoted, _ = _split_caption_lines(para, page_captions)
    assert len(promoted) == 1


# ---------- 段首通道不拆行（11 条 DUP 的结构性保证）----------

def test_paragraph_start_caption_stays_whole():
    # 段首命中 → W1 整段 caption（_classify 层），不经行切分；
    # 此处验证分类 + 切分函数对独立成段的题注不发射多余候选：
    # 非题注段内不可能有行首命中（否则段首已命中），行 0 天然豁免
    text = "Figure1:ExamplesofDocumentAITasks."
    assert _classify_pdf_paragraph(text) == (
        "caption", {"heuristic": "caption_regex"})
    para = _para([
        [_w("Figure1:ExamplesofDocumentAITasks.", 50, 300, 100, 110)],
    ])
    # 若上游仍把该段送进行切分（防御路径），行 0 命中即发射——
    # 但 _parse_pdf 的 caption 分支先于切分，实际不会到达这里；
    # 行为钉住：切分函数对命中行照常发射（无隐藏段首特判）
    promoted, host = _split_caption_lines(para, [])
    assert len(promoted) == 1
    assert host["text"] == ""


def test_multiple_caption_lines_in_one_paragraph():
    # 同段两条题注行（连续题注被并段）→ 各自发射、宿主收缩
    para = _para([
        [_w("Table2:Accuracy", 50, 300, 100, 110)],
        [_w("Table3:Ablation", 50, 300, 112, 122)],
        [_w("tail", 50, 80, 124, 134)],
    ])
    # 段首 "Table2:…" 会让 W1 整段 caption（caption 分支），不切分；
    # 此处直接测切分函数的两行命中能力（防御路径同上钉住）
    promoted, host = _split_caption_lines(para, [])
    assert [p["label_key"] for p in promoted] == ["table:2", "table:3"]
    assert host["text"] == "tail"


# ---------- 退化路径（spec §1.3）----------

def test_degenerate_line_bbox_kept_in_paragraph():
    # 零宽行（bbox 退化）→ 放弃切分保持现状
    para = _para([
        [_w("body", 50, 90, 100, 110)],
        [_w("Table1:x", 50, 50, 112, 122)],  # x0 == x1 零宽
    ])
    promoted, host = _split_caption_lines(para, [])
    assert promoted == []
    assert host["text"] == "body Table1:x"


def test_missing_lines_key_passthrough():
    para = {"text": "legacy body", "bbox": [0, 0, 1, 1]}
    promoted, host = _split_caption_lines(para, [])
    assert promoted == []
    assert host is para


# ---------- label key ----------

def test_caption_label_key_families():
    assert _caption_label_key("Figure 3: x") == "figure:3"
    assert _caption_label_key("Fig. 4. x") == "figure:4"
    assert _caption_label_key("图 ３：x") == "figure:3"
    assert _caption_label_key("Table 12: x") == "table:12"
    assert _caption_label_key("表格 2：x") == "table:2"
    assert _caption_label_key("表 1、x") == "table:1"
    assert _caption_label_key("no caption here") is None
