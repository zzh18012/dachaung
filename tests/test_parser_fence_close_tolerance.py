r"""闭合围栏容忍：尾随空白 / 携带 info / 更长围栏（Round 1867）。

新角度（probe 实证，grep 核实 '```extra'/'`````'/'``` '（尾随
空白闭合）全库零覆盖——既有围栏测试只锁开栏与规整 '```' 闭合）：
- **尾随空白**：'``` ' / '```\t' 仍闭合（与 CommonMark 一致：
  闭合围栏后仅允许空白）
- **携带 info**：'```extra' **照常闭合**且 'extra' 静默丢弃
  （偏离 CommonMark——规范规定闭合围栏不得带 info，此实现按
  前缀匹配，'x=1' 之后无第二元素）
- **更长闭合**：'`````'（5 反引号）闭合 3 反引号围栏
  （与 CommonMark 一致：闭合长度 ≥ 开栏即可）
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


def test_close_fence_trailing_ws_still_closes(tmp_path: Path):
    for name, close in (("m.md", "``` \n"), ("n.md", "```\t\n")):
        data = _run(tmp_path, "```py\nx=1\n" + close)
        assert [(e["type"], e["content"], e["metadata"])
                for e in data["elements"]] == [
            ("paragraph", "x=1", {"kind": "code_block", "language": "py"})
        ], name


def test_close_fence_with_info_closes_and_discards(tmp_path: Path):
    data = _run(tmp_path, "```py\nx=1\n```extra\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "x=1", {"kind": "code_block", "language": "py"})
    ]


def test_longer_close_fence_closes(tmp_path: Path):
    data = _run(tmp_path, "```py\nx=1\n`````\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "x=1", {"kind": "code_block", "language": "py"})
    ]
