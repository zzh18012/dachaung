r"""bq 内 img：kind 只保 img 前段（Round 1878）。

新角度（probe 实证；R1877 锁 img 先行冲掉 heading/li 类型，本批
锁 **blockquote kind** 的分裂语义——img 把 bq 文本切成两段，
kind 只留在 img 之前的段）：
- **文本-img-文本**：'<blockquote>a<img ...>b</blockquote>' →
  paragraph 'a'（kind blockquote）+ image + paragraph 'b'
  （kind **丢失**）——kind 不跨 img 存活
- **img 先行 bq**：'<blockquote><img ...>q</blockquote>' →
  [image, paragraph 'q']——整段 kind 丢失
- **纯 img bq**：'<blockquote><img ...></blockquote><p>after</p>'
  → [image, paragraph 'after']——无空 bq 残留
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


def test_bq_text_img_text_kind_split(tmp_path: Path):
    data = _run(tmp_path,
                '<blockquote>a<img src="u.png" alt="p">b</blockquote>')
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "a", {"kind": "blockquote"}),
        ("image", None, {"alt": "p"}),
        ("paragraph", "b", {}),
    ]


def test_bq_leading_img_kind_lost(tmp_path: Path):
    data = _run(tmp_path,
                '<blockquote><img src="u.png" alt="p">q</blockquote>')
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("image", None, {"alt": "p"}),
        ("paragraph", "q", {}),
    ]


def test_bq_img_only_no_remnant(tmp_path: Path):
    data = _run(tmp_path,
                '<blockquote><img src="u.png" alt="x"></blockquote>'
                "<p>after</p>")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("image", None, {"alt": "x"}),
        ("paragraph", "after", {}),
    ]
