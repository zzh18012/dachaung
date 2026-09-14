r"""空白分类学：U+3000/BOM 位/软连字符/制表符列表（Round 1864）。

新角度（probe 实证；R1862/R1863 建立 isspace×\\s 二分——本轮
补齐第三批字符与**新位置变体**，全库零覆盖）：
- **U+3000 全角空格**：'\\u3000' isspace 且 \\s——'#\\u3000T' →
  heading 'T'；'<p>a\\u3000</p>' → content 'a'（尾随剥离），
  行为与 NBSP 同桶
- **BOM 新位置**：'#\\ufeffT' → paragraph 原样（BOM 非 \\s；
  R1853 只锁行首 BOM '\\ufeff#' 杀标题——# **后**的 BOM 是
  不同位置变体）
- **软连字符保留**：'<p>a\\xad</p>' → 'a\\xad'（U+00AD 非
  isspace，与 U+3000 尾随行为成对反衬）
- **制表符列表标记**：'-\\titem' → list_item 'item'（列表
  标记分隔符 \\s 含 \\t）
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path: Path, name: str, parser: str, body: str) -> dict:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / (name + ".json")
    _, errs = process_single(p, out, parser_name=parser)
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_md_u3000_heading_and_tab_list(tmp_path: Path):
    data = _run(tmp_path, "a.md", "markdown",
                "#" + chr(0x3000) + "T\n\nbody\n")
    assert [(e["type"], e["content"]) for e in data["elements"]] == [
        ("heading", "T"), ("paragraph", "body")]

    data = _run(tmp_path, "e.md", "markdown", "-\titem\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("list_item", "item", {"ordered": False, "marker": "unordered"})]


def test_md_bom_after_hash_inert(tmp_path: Path):
    data = _run(tmp_path, "b.md", "markdown", "#" + chr(0xFEFF) + "T\n")
    assert [(e["type"], e["content"]) for e in data["elements"]] == [
        ("paragraph", "#" + chr(0xFEFF) + "T")]


def test_html_u3000_stripped_softhyphen_kept(tmp_path: Path):
    data = _run(tmp_path, "c.html", "html",
                "<p>a" + chr(0x3000) + "</p>")
    assert data["elements"][0]["content"] == "a"

    data = _run(tmp_path, "d.html", "html", "<p>a\xad</p>")
    assert data["elements"][0]["content"] == "a\xad"
