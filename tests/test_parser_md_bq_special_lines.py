r"""md bq 内特殊行不递归解析：标记字面化（Round 1884）。

新角度（probe 实证；grep '> #' / '> -' / '> |' 全库零命中，
现有 bq 测试全是纯文本内容；机制 markdown_parser.py:260-273
bq 分支把 quoted 内容 join 后直接 push 单个 paragraph，
**不递归解析**）：
- **heading 标记字面**：'> # Fake\\n\\n## Real\\n\\ntext' →
  paragraph '# Fake'（kind blockquote）+ heading 'Real' +
  paragraph 'text'——bq 内 # 不产 heading 也**不进
  section 栈**（首个元素 section_path 键省略 = 空路径）
- **list 标记字面**：'> - item' → paragraph '- item'
  （kind blockquote）——不产 list_item
- **table 语法字面**：'> | a | b |\\n> | --- | --- |' →
  paragraph 管道符原样（kind blockquote）——不产 table
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


def test_bq_heading_marker_literal_no_section(tmp_path: Path):
    data = _run(tmp_path, "> # Fake\n\n## Real\n\ntext\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "# Fake", {"kind": "blockquote"}),
        ("heading", "Real", {"level": 2}),
        ("paragraph", "text", {}),
    ]
    assert "section_path" not in \
        data["elements"][0]["source_locator"]
    assert [e["source_locator"].get("section_path")
            for e in data["elements"][1:]] == ["Real", "Real"]


def test_bq_list_marker_literal(tmp_path: Path):
    data = _run(tmp_path, "> - item\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "- item", {"kind": "blockquote"}),
    ]


def test_bq_table_syntax_literal(tmp_path: Path):
    data = _run(tmp_path,
                "> | a | b |\n> | --- | --- |\n> | 1 | 2 |")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph",
         "| a | b |\n| --- | --- |\n| 1 | 2 |",
         {"kind": "blockquote"}),
    ]
