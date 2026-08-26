r"""pipeline output_path 行为：自动建目录、
静默覆盖与字符串路径（Round 1763）。

新角度：R1762 锁 max_chars 极值——**
output_path 指向不存在目录 → 自动创建
（含嵌套）无错误；已有文件静默覆盖；字
符串路径等价 Path**零覆盖：

- **nodir/o.json**：目录被建、JSON 落
  盘、errors []
- **已写 'OLD' 的文件**：内容被替换为
  JSON
- **str 路径**：同样建目录成功
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _mk(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("x\n", encoding="utf-8")
    return p


def test_output_creates_missing_dirs(tmp_path):
    src = _mk(tmp_path)
    out = tmp_path / "a" / "b" / "o.json"
    doc, errors = process_single(
        src, output_path=out, parser_name="markdown")
    assert errors == []
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source_type"] == "markdown"


def test_output_overwrites_existing(tmp_path):
    src = _mk(tmp_path)
    out = tmp_path / "o.json"
    out.write_text("OLD", encoding="utf-8")
    doc, errors = process_single(
        src, output_path=out, parser_name="markdown")
    assert errors == []
    content = out.read_text(encoding="utf-8")
    assert content.startswith("{")
    assert "OLD" not in content


def test_string_output_path(tmp_path):
    src = _mk(tmp_path)
    out_str = str(tmp_path / "sub" / "o.json")
    doc, errors = process_single(
        src, output_path=out_str, parser_name="markdown")
    assert errors == []
    assert (tmp_path / "sub" / "o.json").exists()
