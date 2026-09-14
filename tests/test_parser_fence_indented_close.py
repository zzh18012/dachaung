r"""缩进闭合围栏 + 短围栏闭长围栏（Round 1868）。

新角度（probe 实证；闭合判定是 `lines[i].strip().startswith(
fence[0]*3)`——strip 后前缀匹配；既有测试只锁缩进**开栏**失效
（edges12）与规整闭合，缩进**闭栏**全库零覆盖）：
- **缩进闭合**：'   ```' / '\t```' / 6 空格缩进 → 照常闭合
  （CommonMark 只允许闭栏前 ≤3 空格，此实现任意缩进都吃）
- **缩进闭合携 junk**：'  ``` junk' 闭合且 'junk' 静默丢弃
  （strip 后前缀匹配，闭栏行余文不入内容、零 warning）
- **短闭长（隔离形态）**：'````py' 开栏被 '```' 闭——偏离
  CommonMark（闭合长度须 ≥ 开栏）；edges12 仅以双围栏构造隐式
  覆盖，此处隔离锁定 + language 元数据 + tail 段落
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path: Path, body: str) -> dict:
    p = tmp_path / "m.md"
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / "m.json"
    _, errs = process_single(p, out, parser_name="markdown")
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_indented_close_fence_closes(tmp_path: Path):
    for name, close in (("m.md", "   ```\n"), ("n.md", "\t```\n"),
                        ("o.md", "      ```\n")):
        data = _run(tmp_path, "```py\nx=1\n" + close)
        assert [(e["type"], e["content"], e["metadata"])
                for e in data["elements"]] == [
            ("paragraph", "x=1", {"kind": "code_block", "language": "py"})
        ], name


def test_indented_close_with_junk_discards(tmp_path: Path):
    data = _run(tmp_path, "```py\nx=1\n  ``` junk\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "x=1", {"kind": "code_block", "language": "py"})
    ]
    assert data["warnings"] == []


def test_shorter_closes_longer_isolated(tmp_path: Path):
    data = _run(tmp_path, "````py\nx=1\n```\ntail\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "x=1", {"kind": "code_block", "language": "py"}),
        ("paragraph", "tail", {}),
    ]
    assert data["warnings"] == []
