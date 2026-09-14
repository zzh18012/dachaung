r"""md 独立图片行的段落冲刷 + 链接包裹不中断（Round 1882）。

新角度（probe 实证；edges2:929 只锁段落被独立图片行中断的
before 侧，**after 侧文本去向**与**链接包裹图片**零覆盖）：
- **后段独立成段**：'para\\n![alt](i.png)\\nafter' →
  [paragraph 'para', image, paragraph 'after']——图片后文本
  冲刷为独立段落（html img 冲刷结构类型的 md 对偶）
- **链接包裹不中断**：'para\\n[![alt](i.png)](u)\\nafter' →
  单个三行合并 paragraph——[ 开头不匹配独立图片正则，整行
  被段落吸收（内容保留 \\n）
- **交替链**：'a\\n![i](1.png)\\nb\\n![j](2.png)\\nc' →
  段/图/段/图/段 五元素——中断规则对称重复
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


def test_post_image_text_flushes_to_paragraph(tmp_path: Path):
    data = _run(tmp_path, "para\n![alt](i.png)\nafter")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "para", {}),
        ("image", None, {"alt": "alt"}),
        ("paragraph", "after", {}),
    ]


def test_link_wrapped_image_absorbed(tmp_path: Path):
    data = _run(tmp_path,
                "para\n[![alt](i.png)](u.com)\nafter")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph",
         "para\n[![alt](i.png)](u.com)\nafter", {}),
    ]


def test_alternating_para_image_chain(tmp_path: Path):
    data = _run(tmp_path,
                "a\n![i](1.png)\nb\n![j](2.png)\nc")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "a", {}),
        ("image", None, {"alt": "i"}),
        ("paragraph", "b", {}),
        ("image", None, {"alt": "j"}),
        ("paragraph", "c", {}),
    ]
