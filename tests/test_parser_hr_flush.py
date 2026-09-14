r"""hr 冲刷结构类型：heading/li/bq 后段退化（Round 1881）。

新角度（probe 实证；edges2:424/edges3:455 只锁 hr 不产生
element 与 only-hr 告警，hr 在结构元素**内部**的冲刷零覆盖——
与 R1877/78 img 同族但 hr 自身不产生 image）：
- **h1 内 hr**：'<h1>a<hr>b</h1>' → [heading 'a',
  paragraph 'b']——hr 后文本退化 paragraph
- **li 内 hr**：'<li>a<hr>b</li>' → [list_item 'a',
  paragraph 'b']——同型退化
- **bq 内 hr**：'<blockquote>a<hr>b</blockquote>' →
  paragraph 'a'（kind blockquote）+ paragraph 'b'（kind
  丢失）——kind 只保 hr 前段（与 img 分裂语义一致）
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


def test_hr_in_heading_flushes(tmp_path: Path):
    data = _run(tmp_path, "<h1>a<hr>b</h1>")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("heading", "a", {"level": 1}),
        ("paragraph", "b", {}),
    ]


def test_hr_in_li_flushes(tmp_path: Path):
    data = _run(tmp_path, "<ul><li>a<hr>b</li></ul>")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("list_item", "a",
         {"ordered": False, "marker": "unordered"}),
        ("paragraph", "b", {}),
    ]


def test_hr_in_bq_kind_split(tmp_path: Path):
    data = _run(tmp_path, "<blockquote>a<hr>b</blockquote>")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "a", {"kind": "blockquote"}),
        ("paragraph", "b", {}),
    ]
