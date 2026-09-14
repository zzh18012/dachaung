r"""img 先行时结构类型丢失：标题/列表项退化（Round 1877）。

新角度（probe 实证；edges16:155 只锁 img **后置**（'Text <img>'
→ heading 保留 + image），img **先行**形态全库零覆盖——先行 img
冲掉 pending 元素的结构类型）：
- **img 先行标题**：'<h1><img ...>T</h1>' → [image, paragraph
  'T']——heading 类型丢失（后置形态则保留，edges16 对照）
- **img 先行列表项**：'<li><img ...>text</li>' → [image,
  paragraph 'text']——list_item 类型丢失；纯 img li → 仅 image
  （无空 list_item）
- **img 后置列表项**：'<li>text<img ...></li>' → [list_item
  'text', image]——类型保留（与先行形成对照）
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path: Path, body: str) -> dict:
    p = tmp_path / "a.html"
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / "a.json"
    _, errs = process_single(p, out, parser_name="html")
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_img_leading_heading_degrades(tmp_path: Path):
    data = _run(tmp_path, '<h1><img src="u.png" alt="pic">T</h1>')
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("image", None, {"alt": "pic"}),
        ("paragraph", "T", {}),
    ]


def test_img_leading_li_degrades(tmp_path: Path):
    data = _run(tmp_path, '<ul><li><img src="u.png" alt="p">text</li></ul>')
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("image", None, {"alt": "p"}),
        ("paragraph", "text", {}),
    ]

    data = _run(tmp_path, '<ul><li><img src="u.png" alt="only"></li></ul>')
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("image", None, {"alt": "only"})]


def test_img_trailing_li_keeps_type(tmp_path: Path):
    data = _run(tmp_path, '<ul><li>text<img src="u.png" alt="t"></li></ul>')
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("list_item", "text",
         {"ordered": False, "marker": "unordered"}),
        ("image", None, {"alt": "t"}),
    ]
