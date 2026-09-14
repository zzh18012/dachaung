r"""ZWSP 三态反衬 NBSP：尾随保留 / md 标题不识别 / chunk forced 硬切（Round 1863）。

新角度（probe 实证；ZWSP 在管线测试零覆盖——metrics/exotic 的
零宽是 bbox 语义）——U+200B 非 isspace() 也非 \\s，与 R1862
NBSP（isspace 且 \\s）处处成对反衬：
- **尾随保留**：'<p>a\\u200b</p>' → content 'a\\u200b'（段级
  strip 剥不掉）；'ab\\u200b'×30 → content **90 字符**（尾随
  ZWSP 不剥，NBSP 同型输入是 89）
- **md 标题不识别**：'#\\u200bT' → paragraph 原样 '#\\u200bT'
  （标题 RE 分隔符 \\s 不含 ZWSP；'#\\xa0T' 是 heading）
- **chunk forced 硬切**：无 isspace 字符 → forced_char 恰 40
  硬切（40/40/10，三段纯切片含尾随 ZWSP；NBSP 同型输入是
  38/38/11 窗口切）
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single

ZW = chr(0x200B)


def _run(tmp_path: Path, name: str, parser: str, body: str,
         max_chars: int = 800) -> dict:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / (name + ".json")
    _, errs = process_single(p, out, parser_name=parser,
                             max_chars=max_chars)
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_html_trailing_zwsp_preserved(tmp_path: Path):
    data = _run(tmp_path, "a.html", "html", "<p>a" + ZW + "</p>")
    assert data["elements"][0]["content"] == "a" + ZW


def test_md_zwsp_heading_not_recognized(tmp_path: Path):
    data = _run(tmp_path, "b.md", "markdown", "#" + ZW + "T\n")
    assert [(e["type"], e["content"]) for e in data["elements"]] == [
        ("paragraph", "#" + ZW + "T")]


def test_chunk_zwsp_forced_hard_split(tmp_path: Path):
    src = ("ab" + ZW) * 30
    data = _run(tmp_path, "c.html", "html",
                "<p>" + src + "</p>", max_chars=40)
    assert data["elements"][0]["content"] == src
    assert [c["text"] for c in data["chunks"]] == [
        src[0:40], src[40:80], src[80:90]]
    assert len(data["chunks"][2]["text"]) == 10
