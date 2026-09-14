r"""实体标题 → section_path：html 解码流入 / md 字面流入（Round 1872）。

新角度（probe 实证；R1826 只锁标题 **content** 的实体对照与 md
'<b>B</b>' 字面路径传播，html 实体解码后的 **section_path** 断言
与 md 实体字面路径传播零覆盖）：
- **html 数字实体**：'<h1>&#65;B</h1>' → heading 'AB' 且后续段
  section_path 'AB'（SAX 解码在路径建立之前）
- **html 命名实体 NBSP**：'<h1>a&nbsp;b</h1>' → 路径 'a\\xa0b'
  （实体解码出的 NBSP 逐字进路径，不折叠——R1865 锁源码 NBSP，
  此处锁实体来源）
- **md 对照**：'# T &amp; U' → 路径 'T &amp; U' 字面（md 不解码
  实体，字面标题原样入路径）
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single

NB = chr(0xA0)


def _run(tmp_path: Path, name: str, body: str, parser: str) -> dict:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / (name + ".json")
    _, errs = process_single(p, out, parser_name=parser)
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_html_numentity_heading_decoded_into_path(tmp_path: Path):
    data = _run(tmp_path, "a.html", "<h1>&#65;B</h1><p>x</p>", "html")
    assert [(e["type"], e["content"]) for e in data["elements"]] == [
        ("heading", "AB"), ("paragraph", "x")]
    assert [e["source_locator"]["section_path"]
            for e in data["elements"]] == ["AB", "AB"]


def test_html_nbsp_entity_heading_path_kept(tmp_path: Path):
    data = _run(tmp_path, "b.html", "<h1>a&nbsp;b</h1><p>y</p>", "html")
    assert [e["source_locator"]["section_path"]
            for e in data["elements"]] == ["a" + NB + "b", "a" + NB + "b"]


def test_md_entity_heading_path_literal(tmp_path: Path):
    data = _run(tmp_path, "c.md", "# T &amp; U\n\nbody\n", "markdown")
    assert [e["source_locator"]["section_path"]
            for e in data["elements"]] == ["T &amp; U", "T &amp; U"]
