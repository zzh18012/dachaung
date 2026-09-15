"""HTML 数字字符引用退化形态（Round 2014，a 优先级）。

html.parser convert_charrefs=True（html_parser.py:72）自动转
换字符引用，走 HTML5 语义表（同 html.unescape）。edges15 已锁
未知命名实体字面（'&nosuch; stays'）；**数字退化形态零覆盖**
（grep 实证 &#0;/超界/代理/双重编码无夹具）。探针 R2014 实证：

- **T1 十进制/十六进制**：'&#65;' 与 '&#x41;' → 都是 'A'
- **T2 NUL**：'a&#0;b' → 'a\\ufffdb'（HTML5 规定 0 →
  REPLACEMENT CHARACTER，不是 NUL 也不是丢弃）
- **T3 超界/代理**：'&#x110000;' 与 '&#xD800;' → '\\ufffd'
- **T4 双重编码**：'&#38;#41;' → '&#41;' 字面（'&#38;'→'&'
  后不再重解析剩余文本，单遍语义）

判别式：T2/T3 若空串/异常/原字面翻；T4 若 ')' 翻（重解析）；
T1 若任一形态非 'A' 翻。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser


def _parse(tmp_path: Path, body: str):
    p = tmp_path / "b.html"
    p.write_text(body, encoding="utf-8", newline="")
    return HtmlParser().parse(p, compute_file_hash(p))


def test_decimal_and_hex_forms(tmp_path):
    """T1：'&#65;' / '&#x41;' → 两段各 'A'。"""
    d = _parse(tmp_path, "<p>&#65;</p><p>&#x41;</p>")
    assert [(e.type, e.content) for e in d.elements] == [
        ("paragraph", "A"), ("paragraph", "A")]
    assert d.warnings == []


def test_nul_charref_to_replacement(tmp_path):
    """T2：'a&#0;b' → 'a\\ufffdb'。"""
    d = _parse(tmp_path, "<p>a&#0;b</p>")
    assert [(e.type, e.content) for e in d.elements] == [
        ("paragraph", "a�b")]
    assert d.warnings == []


def test_out_of_range_and_surrogate(tmp_path):
    """T3：超界 &#x110000; 与代理 &#xD800; → '\\ufffd'。"""
    d = _parse(tmp_path, "<p>&#x110000;</p><p>&#xD800;</p>")
    assert [(e.type, e.content) for e in d.elements] == [
        ("paragraph", "�"), ("paragraph", "�")]
    assert d.warnings == []


def test_double_encoded_single_pass(tmp_path):
    """T4：'&#38;#41;' → '&#41;' 字面（单遍不重解析）。"""
    d = _parse(tmp_path, "<p>&#38;#41;</p>")
    assert [(e.type, e.content) for e in d.elements] == [
        ("paragraph", "&#41;")]
    assert d.warnings == []
