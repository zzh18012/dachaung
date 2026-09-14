r"""section_path 分隔符碰撞：标题内容含 ' > '（Round 1873）。

新角度（probe 实证，grep 核实 '&gt;' 进标题 + 路径断言全库零
覆盖——R1872 锁实体解码入路径，本批锁解码出的 **' > ' 与路径
分隔符同形**的碰撞）：
- **html 实体形态**：'<h1>a &gt; b</h1>' → 路径 'a > b'，
  嵌套 h2 后 'a > b > c'——内容 ' > ' 与分隔符 ' > ' 不可区分
- **md 字面形态**：'# a > b' → 同一碰撞（字面 '>' 原样入路径）
- **双重碰撞**：两级标题都含 ' > ' → 'a > b > c > d'
  （4 段路径中 3 个 ' > ' 只有一个是真分隔符）
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path: Path, name: str, body: str, parser: str) -> dict:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / (name + ".json")
    _, errs = process_single(p, out, parser_name=parser)
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_html_gt_entity_heading_path_collision(tmp_path: Path):
    data = _run(tmp_path, "a.html",
                "<h1>a &gt; b</h1><h2>c</h2><p>t</p>", "html")
    assert [e["source_locator"]["section_path"]
            for e in data["elements"]] == \
        ["a > b", "a > b > c", "a > b > c"]


def test_md_literal_gt_heading_path_collision(tmp_path: Path):
    data = _run(tmp_path, "b.md", "# a > b\n\n## c\n\nt\n", "markdown")
    assert [e["source_locator"]["section_path"]
            for e in data["elements"]] == \
        ["a > b", "a > b > c", "a > b > c"]


def test_double_collision_four_segment_path(tmp_path: Path):
    data = _run(tmp_path, "c.html",
                "<h1>a &gt; b</h1><h2>c &gt; d</h2><p>t</p>", "html")
    assert [e["source_locator"]["section_path"]
            for e in data["elements"]] == \
        ["a > b", "a > b > c > d", "a > b > c > d"]
