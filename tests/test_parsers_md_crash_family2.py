r"""markdown 空内容 element 家族测试（Round 1487）。

R1484/R1486 发现 ATX 空标题崩溃；本轮（probe 实证）扫出
**列表标记同样崩溃**（edges1-18 与 crash-family 首轮未碰
过）：

- **列表标记 + 纯空白 → 崩溃**：'-   \\n' / '*   \\n' /
  '1.   \\n' 全部命中列表 RE、strip 后空 content →
  ValueError 穿透（与 '#   \\n' 同一 Element 校验）
- **无尾换行同样崩**：'-   '（EOF 无 \\n）
- **bq 纯空白安全**：'>   \\n' → 不崩，md_no_content
- **bq 内 '-   ' 降级为段**：内容 '- '（marker 不在 bq
  内识别，剩 '-' 字面）
- **缩进 '#   ' 安全**：'  #   \\n' 不成标题 → paragraph
  '#'（ATX RE 不容许前导缩进）

修复建议（R1484 起累积）：push 前统一跳过 strip 后为空
的 content，可一并消掉标题与列表两类崩溃。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.markdown_parser import \
    MarkdownParser


def _md(tmp_path, text):
    p = tmp_path / "probe.md"
    p.write_text(text, encoding="utf-8",
                 newline="")
    return MarkdownParser().parse(
        p, compute_file_hash(p))


# ---------- 列表标记崩溃 ----------

def test_list_markers_ws_only_crash(
        tmp_path):
    for text in ("-   \nbody\n",
                 "*   \n",
                 "1.   \n"):
        with pytest.raises(
                ValueError, match=
                "必须至少有 content 或"
                " resource_path"):
            _md(tmp_path, text)


def test_list_ws_no_newline_crash(
        tmp_path):
    with pytest.raises(ValueError):
        _md(tmp_path, "-   ")


# ---------- 安全边界 ----------

def test_bq_ws_only_safe(tmp_path):
    doc = _md(tmp_path, ">   \n")
    assert doc.elements == []
    assert [w.code for w in doc.warnings] \
        == ["md_no_content"]


def test_bq_dash_ws_paragraph(tmp_path):
    doc = _md(tmp_path, "> -   \n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "-"),
    ]
    assert doc.elements[0].metadata == {
        "kind": "blockquote"}


def test_indented_hash_paragraph(tmp_path):
    doc = _md(tmp_path, "  #   \n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "#"),
    ]
