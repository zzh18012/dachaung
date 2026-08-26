r"""pipeline JSON 成功态字段：relations/
errors 空数组、source_path 原样、警告
序列化无 details（Round 1806）。

新角度：R1805 锁 CLI 映射——**成功 JSON
里 relations=[]、errors=[]（空数组非
null）；source_path 原样保留（相对进
相对出、绝对进绝对出——不做 resolve）；
警告序列化 [{'code','reason'}]——
details=None 键省略在 JSON 层复证**零
覆盖：

- **relations/errors/warnings**：三空
  数组 + parser_version stdlib/0.1.0
- **相对路径**：'d.md' 进出原样
- **空围栏警告**：两键无 details
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_json_success_fields(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("## T\n\nbody\n", encoding="utf-8")
    out = tmp_path / "o.json"
    process_single(p, output_path=out,
                   parser_name="markdown")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["relations"] == []
    assert data["errors"] == []
    assert data["warnings"] == []
    assert data["parser_name"] == "markdown"
    assert data["parser_version"] == "stdlib/0.1.0"
    assert data["schema_version"] == "0.1.0"
    assert data["metadata"] == {"markdown": True}


def test_json_source_path_as_given(tmp_path):
    src = tmp_path / "d.md"
    src.write_text("body\n", encoding="utf-8")
    out = tmp_path / "o.json"
    process_single(src, output_path=out,
                   parser_name="markdown")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert Path(data["source_path"]).is_absolute()
    import os
    os.chdir(tmp_path)
    try:
        process_single("d.md", output_path="o2.json",
                       parser_name="markdown")
        data2 = json.loads(
            Path("o2.json").read_text(encoding="utf-8"))
        assert data2["source_path"] == "d.md"
    finally:
        os.chdir(Path(__file__).resolve().parents[1])


def test_json_warning_no_details_key(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("```\n```\n\nbody\n", encoding="utf-8")
    out = tmp_path / "o.json"
    process_single(p, output_path=out,
                   parser_name="markdown")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["warnings"] == [{
        "code": "md_empty_code_block",
        "reason": "line 1 处的代码块为空"}]
    assert "details" not in data["warnings"][0]
