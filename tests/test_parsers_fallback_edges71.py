r"""app/parsers/fallback_parser.py PDF 边角测试 - 第七十一轮（Round 1494）。

新角度（probe 实证）文本显示/渲染操作符家族（edges1-70 未
碰的 ' / " / Tr / 非常规 TL）：

- **Tr 3 隐形文本照常提取**：渲染模式 3（不可见，OCR
  文本层的实现方式）pdfminer 仍提取 'ghost'（可见性与
  提取无关）
- **Tr 3 → Tr 0 混排顺序倒置**：先画的 ghost（y=700）
  后出、后画的 real（y=650）先出 → ['real','ghost']
  （3 次复跑稳定）
- **' 撇号 op 默认 TL=0 三行重叠交错**：'line1'/'line2'/
  'line3' 同位交错 → 'llliiinnneee123'（与 R1483 overprint
  同现象、不同触发路径）
- **" 双引号 op 正常显示**：'2 2 (b) "' → 'ab'
- **" 后接 Tj 直接拼接**：'(first) \" (second) Tj' →
  'firstsecond'（Tw/Tc 不在 content 里留空隙）
- **负 TL 反序**：TL=-20 的 T* 把下一行上移 → 'b a'
  （b 在 a 上方，自上而下输出）
- **多余 Q 不崩**：ET 后三个裸 Q → 'a' 照常
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

from tests.test_parsers_fallback_edges66 \
    import _pdf


def _parse(tmp_path, name, content):
    p = _pdf(tmp_path, name, content)
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- 渲染模式 ----------

def test_tr3_invisible_extracted(
        tmp_path):
    doc = _parse(
        tmp_path, "tr3.pdf",
        "BT /F1 12 Tf 3 Tr 72 700 Td"
        " (ghost) Tj ET")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "ghost"),
    ]
    assert doc.warnings == []


def test_tr3_then_tr0_order(
        tmp_path):
    doc = _parse(
        tmp_path, "tr30.pdf",
        "BT /F1 12 Tf 3 Tr 72 700 Td"
        " (ghost) Tj 0 Tr 72 650 Td"
        " (real) Tj ET")
    assert [e.content
            for e in doc.elements] == [
        "real", "ghost",
    ]
    assert doc.warnings == []


# ---------- 引号显示 op ----------

def test_apostrophe_default_tl_interleave(
        tmp_path):
    doc = _parse(
        tmp_path, "apo.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (line1) Tj (line2) '"
        " (line3) ' ET")
    assert [e.content
            for e in doc.elements] == [
        "llliiinnneee123",
    ]


def test_dq_op_shows(tmp_path):
    doc = _parse(
        tmp_path, "dq.pdf",
        'BT /F1 12 Tf 72 700 Td'
        ' (a) Tj 2 2 (b) " ET')
    assert [e.content
            for e in doc.elements] == [
        "ab",
    ]


def test_dq_then_tj_concat(
        tmp_path):
    doc = _parse(
        tmp_path, "dqt.pdf",
        'BT /F1 12 Tf 72 700 Td'
        ' 5 1 (first) "'
        ' (second) Tj ET')
    assert [e.content
            for e in doc.elements] == [
        "firstsecond",
    ]


# ---------- 非常规 TL / 栈 ----------

def test_negative_tl_reverse_order(
        tmp_path):
    doc = _parse(
        tmp_path, "ntl.pdf",
        "BT /F1 12 Tf -20 TL"
        " 72 700 Td (a) Tj T*"
        " (b) Tj ET")
    assert [e.content
            for e in doc.elements] == [
        "b a",
    ]


def test_extra_Q_harmless(tmp_path):
    doc = _parse(
        tmp_path, "qq.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (a) Tj ET Q Q Q")
    assert [e.content
            for e in doc.elements] == [
        "a",
    ]
    assert doc.warnings == []
