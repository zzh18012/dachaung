r"""app/parsers/fallback_parser.py PDF 边角测试 - 第七十四轮（Round 1497）。

新角度（probe 实证）退化文本状态参数（edges1-73 未碰）：

- **Tf 0 无害**：零号字号照常提取 'zero size'
- **⚠ Tf 负值整串倒序**：Tf -12 的 'neg size' →
  **'ezis gen'**（负字号翻转排布方向，字符逆序——与
  R1496 Tm 旋转倒序同族）
- **Tz 0 / Tz 1000 不影响提取**：横缩放不改变 content
- **Ts 上升不影响提取**：基线偏移照常
- **十六进制串容空格**：'<48 65 6C 6C 6F>' → 'Hello'
- **空 BT/ET 对象无害**：'BT ET' 后照常提取
- **空字符串 Tj 跳过**：'() Tj (real) Tj' → 只留 'real'
- **WinAnsi 0x92 → U+2019**：'(it\\x92s)' → 'it’s'
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


def _only_content(doc):
    return [e.content
            for e in doc.elements]


# ---------- 字号退化 ----------

def test_tf_zero_extracted(tmp_path):
    doc = _parse(
        tmp_path, "tz0.pdf",
        "BT /F1 0 Tf 72 700 Td"
        " (zero size) Tj ET")
    assert _only_content(doc) == [
        "zero size"]
    assert doc.warnings == []


def test_tf_negative_reverses(
        tmp_path):
    doc = _parse(
        tmp_path, "tfn.pdf",
        "BT /F1 -12 Tf 72 700 Td"
        " (neg size) Tj ET")
    assert _only_content(doc) == [
        "ezis gen"]
    assert doc.warnings == []


# ---------- 缩放/基线 ----------

def test_tz_zero_normal(tmp_path):
    doc = _parse(
        tmp_path, "z0.pdf",
        "BT /F1 12 Tf 0 Tz"
        " 72 700 Td (noscale) Tj ET")
    assert _only_content(doc) == [
        "noscale"]


def test_tz_1000_normal(tmp_path):
    doc = _parse(
        tmp_path, "z1k.pdf",
        "BT /F1 12 Tf 1000 Tz"
        " 72 700 Td (wide) Tj ET")
    assert _only_content(doc) == [
        "wide"]


def test_ts_rise_normal(tmp_path):
    doc = _parse(
        tmp_path, "tsr.pdf",
        "BT /F1 12 Tf 5 Ts"
        " 72 700 Td (risen) Tj ET")
    assert _only_content(doc) == [
        "risen"]


# ---------- 字符串形态 ----------

def test_hex_string_spaces(tmp_path):
    doc = _parse(
        tmp_path, "hx.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " <48 65 6C 6C 6F> Tj ET")
    assert _only_content(doc) == [
        "Hello"]


def test_empty_bt_et_harmless(
        tmp_path):
    doc = _parse(
        tmp_path, "ebt.pdf",
        "BT ET BT /F1 12 Tf"
        " 72 700 Td"
        " (after empty) Tj ET")
    assert _only_content(doc) == [
        "after empty"]
    assert doc.warnings == []


def test_empty_string_tj_skipped(
        tmp_path):
    doc = _parse(
        tmp_path, "es.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " () Tj (real) Tj ET")
    assert _only_content(doc) == [
        "real"]
    assert doc.warnings == []


def test_winansi_0x92_smart_quote(
        tmp_path):
    doc = _parse(
        tmp_path, "wa.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (it\x92s) Tj ET")
    assert _only_content(doc) == [
        "it’s"]
    assert doc.warnings == []
