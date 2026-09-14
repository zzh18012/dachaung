r"""BACKLOG 候选 B / 候选 C 根因合成复现（Round 1887，b 优先级首轮）。

**特征锁定（characterization），不是期望行为规格**——锁定主线
docs/BACKLOG.md §1（候选 B：多栏题注碎字符）/ §2（候选 C：表单
域标签误判 heading）在自跑线代码中的确切机制，供指示线裁决修复
时对照。单元级合成复现（pdfplumber word-dict 形状），不读
real-*、不需要真 PDF。

根因定位（app/parsers/fallback_parser.py）：
- 候选 B：:121 排序键 (y_center, x0) + :127-131 行聚类只看 y
  （±3.0 容差）**无 x 栏目聚类**——双栏同行词跨栏并成一行，
  题注文本被右栏正文词污染（bbox 横跨两栏）；:50 caption 正则
  前缀锚定，污染文本仍判 caption → 内容错、计数偏
- 候选 C：:184 `len(t) <= 80 and not t.endswith(终止标点)`
  → heading(level 0, short_line)——无字体/语境信号，表单域
  标签（短行无句读）全部命中
"""

from __future__ import annotations

from app.parsers.fallback_parser import (
    _classify_pdf_paragraph,
    _group_words_to_paragraphs,
)

_H = 12.0


def _w(text: str, x0: float, x1: float, top: float, bottom: float) -> dict:
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": bottom}


def _row(words: list[tuple[str, float, float]], top: float) -> list[dict]:
    return [_w(t, x0, x1, top, top + _H) for t, x0, x1 in words]


def test_backlog_candB_multicolumn_caption_crosscolumn_fusion():
    """候选 B 机制：左栏题注 + 右栏正文同 y 带 → 跨栏并成一段，
    题注内容被右栏词污染，bbox 横跨两栏，仍按前缀判 caption。"""
    left_cap_1 = _row(
        [("图", 50, 62), ("1", 66, 72), ("系统", 78, 102), ("架构", 106, 130)],
        500.0,
    )
    right_body_1 = _row(
        [("The", 320, 344), ("model", 350, 386), ("achieves", 392, 448)],
        500.0,
    )
    left_cap_2 = _row(
        [("与", 50, 62), ("模块", 66, 98), ("划分", 102, 134)], 514.0
    )
    right_body_2 = _row([("95%", 320, 348), ("accuracy", 354, 410)], 514.0)
    paras = _group_words_to_paragraphs(
        left_cap_1 + right_body_1 + left_cap_2 + right_body_2
    )
    # 行距 514-512=2 < 1.5*字高12=18 → 段落聚类不分段 → 单段融合
    assert len(paras) == 1
    fused = paras[0]["text"]
    assert fused == "图 1 系统 架构 The model achieves 与 模块 划分 95% accuracy"
    # 右栏正文词混入题注段
    assert "The model achieves" in fused
    assert "95% accuracy" in fused
    # bbox 横跨两栏（左栏 x0=50 起，右栏 x1=448 止）
    assert paras[0]["bbox"] == [50.0, 500.0, 448.0, 526.0]
    # 污染文本仍按 caption 前缀正则判 caption（内容已错）
    etype, meta = _classify_pdf_paragraph(fused)
    assert etype == "caption"
    assert meta == {"heuristic": "caption_regex"}


def test_backlog_candC_form_field_labels_all_become_headings():
    """候选 C 机制：表单域标签（短行无句读）全部误判 heading
    level 0（short_line 启发式，无字体信号）——表单页 heading
    计数膨胀（BACKLOG 实测 +246%）的单元级根源；带句读对照行
    走 paragraph。"""
    labels = [
        "姓名",
        "出生日期",
        "身份证号",
        "Name",
        "Date of Birth",
        "Contact Phone",
        "Signature",
        "申请人签名",
        "请填写以下信息后提交",
        "同意上述条款",
    ]
    for t in labels:
        etype, meta = _classify_pdf_paragraph(t)
        assert etype == "heading", f"{t!r} 应误判 heading（缺陷机制锁定）"
        assert meta == {"level": 0, "heuristic": "short_line"}
    # 对照：同标签加终止标点 → paragraph（启发式只看句尾）
    for t in ["Name.", "出生日期。", "I agree to the terms."]:
        etype, _ = _classify_pdf_paragraph(t)
        assert etype == "paragraph"


def test_backlog_candC_short_line_threshold_exactly_80():
    """候选 C 边界：无句读短行阈值恰 80 字符（≤80 heading，
    81 paragraph）——决定哪些表单标签会误判的确切分界。"""
    etype80, meta80 = _classify_pdf_paragraph("a" * 80)
    assert etype80 == "heading"
    assert meta80 == {"level": 0, "heuristic": "short_line"}
    etype81, _ = _classify_pdf_paragraph("a" * 81)
    assert etype81 == "paragraph"
