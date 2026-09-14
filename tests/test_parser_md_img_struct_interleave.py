r"""md 独立图片行插入列表项之间 / 终止 bq（Round 1883）。

新角度（probe 实证；edges2:929 段落中断只涉段落侧，图片行与
**列表项交错**、**bq 运行终止**零覆盖——grep 全部 md 图片行用例
只有 para-image / image-image / bq、li 内包裹形态）：
- **项间图片**：'- a\\n![i](1.png)\\n- b' → [list_item 'a',
  image, list_item 'b']——列表项不跨图片合并
- **bq 运行终止**：'> q\\n![i](1.png)\\nafter' → paragraph
  'q'（kind blockquote）+ image + paragraph 'after'——图片
  行切断 '>' 连续行；后续文本**不回归** bq（kind 丢失）
- **缩进图片行**：'- a\\n  ![i](1.png)\\n- b' → 同项间冲刷
  ——standalone 匹配用 stripped，前导空格不豁免
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path: Path, body: str) -> dict:
    p = tmp_path / "a.md"
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / "a.json"
    _, errs = process_single(p, out, parser_name="markdown")
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_image_between_list_items(tmp_path: Path):
    data = _run(tmp_path, "- a\n![i](1.png)\n- b")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("list_item", "a",
         {"ordered": False, "marker": "unordered"}),
        ("image", None, {"alt": "i"}),
        ("list_item", "b",
         {"ordered": False, "marker": "unordered"}),
    ]


def test_image_terminates_blockquote_run(tmp_path: Path):
    data = _run(tmp_path, "> q\n![i](1.png)\nafter")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "q", {"kind": "blockquote"}),
        ("image", None, {"alt": "i"}),
        ("paragraph", "after", {}),
    ]


def test_indented_image_line_still_flushes(tmp_path: Path):
    data = _run(tmp_path, "- a\n  ![i](1.png)\n- b")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("list_item", "a",
         {"ordered": False, "marker": "unordered"}),
        ("image", None, {"alt": "i"}),
        ("list_item", "b",
         {"ordered": False, "marker": "unordered"}),
    ]
