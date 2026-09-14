r"""fence info 字符类边界：空格级联 / CJK / 大写与连字符（Round 1869）。

新角度（probe 实证；edges8:258 只锁 RE 级 m is None，parse 级联
与 CJK/大写全库零覆盖——\w 在 Python re 含 CJK）：
- **info 含空格级联**：'```python 3' 开栏行不匹配 → 与后文合并
  paragraph，行尾 '```' 反而开栏到 EOF → md_empty_code_block
- **CJK info**：'```中文' → language '中文' 逐字（\w 含 CJK）
- **大小写与连字符**：'```PY' → 'PY' 原样保留（无小写归一）；
  '```py-3' → 'py-3'（字符类含 '-'，与 c++ 的 '+' 合成全景）
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


def test_info_with_space_cascades_to_paragraph(tmp_path: Path):
    data = _run(tmp_path, "```python 3\nx=1\n```\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "```python 3\nx=1", {})
    ]
    assert [w["code"] for w in data["warnings"]] == ["md_empty_code_block"]


def test_cjk_info_language_kept(tmp_path: Path):
    data = _run(tmp_path, "```中文\nx=1\n```\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "x=1", {"kind": "code_block", "language": "中文"})
    ]


def test_uppercase_and_hyphen_info_preserved(tmp_path: Path):
    data = _run(tmp_path, "```PY\nx=1\n```\n")
    assert data["elements"][0]["metadata"]["language"] == "PY"

    data = _run(tmp_path, "```py-3\nx=1\n```\n")
    assert data["elements"][0]["metadata"]["language"] == "py-3"
