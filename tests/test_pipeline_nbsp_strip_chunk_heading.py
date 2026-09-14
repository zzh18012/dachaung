r"""NBSP 四态：尾随剥离 / chunk 切分点 / md 标题分隔 / 前导惰性（Round 1862）。

新角度（probe 实证；edges14:208 只锁**内容中间** '&nbsp;' →
\xa0 保留——尾随剥离、chunk 切分、md 标题分隔零覆盖）：
- **尾随剥离**：'<p>a&nbsp;</p>' → content 'a'（\xa0.isspace()
  True → 段级 strip 杀尾随 NBSP；中间保留的 edges14 形成对照）
- **chunk 切分点**：'ab&nbsp;'×30 @40 → content 'ab\xa0'×29+'ab'
  （89），切 38/38/11——NBSP 与 \r/\t/U+2028 同为 isspace 窗口
  切分位（R1860 机制）
- **md 标题分隔**：'#\\xa0T' → **heading 'T'**（标题 RE 的
  分隔符类匹配 NBSP）；前导 '\\xa0#T' → 惰性 paragraph '#T'
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single

NB = chr(0xA0)


def _run(tmp_path: Path, name: str, parser: str, body: str,
         max_chars: int = 800) -> dict:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / (name + ".json")
    _, errs = process_single(p, out, parser_name=parser,
                             max_chars=max_chars)
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_html_trailing_nbsp_stripped(tmp_path: Path):
    data = _run(tmp_path, "a.html", "html", "<p>a&nbsp;</p>")
    assert data["elements"][0]["content"] == "a"


def test_html_nbsp_chunk_split_point(tmp_path: Path):
    data = _run(tmp_path, "b.html", "html",
                "<p>" + "ab&nbsp;" * 30 + "</p>", max_chars=40)
    assert data["elements"][0]["content"] == "ab\xa0" * 29 + "ab"
    assert [c["text"] for c in data["chunks"]] == [
        "ab\xa0" * 12 + "ab",
        "ab\xa0" * 12 + "ab",
        "ab\xa0" * 3 + "ab"]


def test_md_nbsp_heading_separator(tmp_path: Path):
    data = _run(tmp_path, "c.md", "markdown",
                "#" + NB + "T\n\nbody\n")
    assert [(e["type"], e["content"]) for e in data["elements"]] == [
        ("heading", "T"), ("paragraph", "body")]

    data = _run(tmp_path, "d.md", "markdown", NB + "#T\n")
    assert [(e["type"], e["content"]) for e in data["elements"]] == [
        ("paragraph", "#T")]
