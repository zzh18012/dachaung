r"""pipeline JSON 落盘与 schema 回验闭环
（Round 1745）。

新角度：R1744 锁结构字段——**write_json
默认 True 但无 output_path 不落盘；给
output_path 才写 13 顶层键 JSON；写出的
JSON 过 validate/validate_file 且
document_id 与返回 Document 一致**零覆盖：

- **默认调用**：目录无新文件（write 需显
  式 output_path）
- **output_path 落盘**：13 键、
  schema_version '0.1.0'、source_hash
  64 位 hex
- **回验**：validate/is_valid/
  validate_file 全过，JSON document_id ==
  Document.document_id；element 8 键、
  chunk 5 键
"""

from __future__ import annotations

import json
import re

from pathlib import Path

from app.pipeline import process_single
from app.schema import is_valid, validate, validate_file


def _src(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("## T\n\nbbb\n", encoding="utf-8")
    return p


def test_no_file_without_output_path(tmp_path):
    src = _src(tmp_path)
    doc, errors = process_single(src, parser_name="markdown")
    assert errors == []
    assert doc is not None
    assert [p.name for p in tmp_path.iterdir()] == ["d.md"]


def test_output_json_shape_and_validity(tmp_path):
    src = _src(tmp_path)
    out = tmp_path / "o.json"
    doc, errors = process_single(
        src, output_path=out, parser_name="markdown")
    assert errors == []
    data = json.loads(out.read_text(encoding="utf-8"))
    assert sorted(data.keys()) == [
        "chunks", "document_id", "elements", "errors",
        "metadata", "parser_name", "parser_version",
        "relations", "schema_version", "source_hash",
        "source_path", "source_type", "warnings"]
    assert data["schema_version"] == "0.1.0"
    assert re.fullmatch(r"[0-9a-f]{64}", data["source_hash"])
    validate(data)
    assert is_valid(data)
    validate_file(out)
    assert data["document_id"] == doc.document_id


def test_json_element_chunk_keys(tmp_path):
    src = _src(tmp_path)
    out = tmp_path / "o.json"
    doc, errors = process_single(
        src, output_path=out, parser_name="markdown")
    assert errors == []
    data = json.loads(out.read_text(encoding="utf-8"))
    assert sorted(data["elements"][0].keys()) == [
        "confidence", "content", "element_id", "metadata",
        "parent_id", "resource_path", "source_locator",
        "type"]
    assert sorted(data["chunks"][0].keys()) == [
        "chunk_id", "metadata", "source_element_ids",
        "source_spans", "text"]
    assert [s["element_id"] for s in
            data["chunks"][0]["source_spans"]] == [
        e["element_id"] for e in data["elements"]]
