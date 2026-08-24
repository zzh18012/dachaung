r"""app/pipeline.py 边角测试 - 第十轮（Round 1363）。

补强 edges-edges9 未覆盖的深度（probe 实证）：
- markdown 走全管线分块几何——heading 硬边界 + 表格 isolated_table +
  list 并入 sequential chunk
- max_chars 地板（<32 → chunker_failed 结构化错误，不崩溃）
- 空内容 md（仅主题分隔符）→ no_extracted_elements 带 source_type
- 扩展名 × parser 名交叉错配 → unsupported_type
- write_json 默认 True → 落盘
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.pipeline import process_single


MD = ("# Head\n\npara one two three four five six seven\n\n"
      "- a\n- b\n\n"
      "| x | y |\n| --- | --- |\n| 1 | 2 |\n\n"
      "## Sub\n\ntail text here\n")


def _run(tmp_path, md=MD, mc=64, parser="markdown",
         write=True):
    (tmp_path / "d.md").write_text(md, encoding="utf-8")
    return process_single(
        tmp_path / "d.md", tmp_path / "o.json",
        parser_name=parser, max_chars=mc,
        write_json=write)


# ---------- 分块几何 ----------

def test_md_pipeline_three_chunks(tmp_path):
    doc, errors = _run(tmp_path)
    assert errors == []
    assert len(doc.chunks) == 3


def test_first_chunk_merges_heading_para_list(
        tmp_path):
    doc, _ = _run(tmp_path)
    assert doc.chunks[0].text == (
        "Head para one two three four five "
        "six seven a b")
    assert doc.chunks[0].metadata["strategy"] == \
        "sequential"


def test_first_chunk_ids_in_order(tmp_path):
    doc, _ = _run(tmp_path)
    assert [i.rsplit("::", 1)[1]
            for i in doc.chunks[0].source_element_ids] \
        == ["e0000", "e0001", "e0002", "e0003"]


def test_table_isolated_strategy(tmp_path):
    doc, _ = _run(tmp_path)
    assert doc.chunks[1].metadata["strategy"] == \
        "isolated_table"
    assert doc.chunks[1].text == (
        "| x | y |\n| --- | --- |\n| 1 | 2 |")


def test_table_chunk_single_source(tmp_path):
    doc, _ = _run(tmp_path)
    assert doc.chunks[1].source_element_ids == [
        doc.elements[4].element_id]


def test_sub_heading_hard_boundary(tmp_path):
    doc, _ = _run(tmp_path)
    assert doc.chunks[2].text == "Sub tail text here"
    assert doc.chunks[2].source_element_ids == [
        doc.elements[5].element_id,
        doc.elements[6].element_id]


def test_chunk_ids_sequential(tmp_path):
    doc, _ = _run(tmp_path)
    assert [c.chunk_id.rsplit("c", 1)[1]
            for c in doc.chunks] == ["0000", "0001",
                                     "0002"]


def test_seven_elements(tmp_path):
    doc, errors = _run(tmp_path)
    assert errors == []
    assert len(doc.elements) == 7


# ---------- max_chars 地板 ----------

def test_mc31_chunker_failed(tmp_path):
    doc, errors = _run(tmp_path, mc=31)
    assert doc is None
    assert len(errors) == 1
    assert errors[0].code == "chunker_failed"


def test_mc31_details_exception_type(tmp_path):
    _, errors = _run(tmp_path, mc=31)
    assert errors[0].details == {
        "exception_type": "ValueError"}


def test_mc31_message_mentions_floor(tmp_path):
    _, errors = _run(tmp_path, mc=31)
    assert "max_chars 过小" in errors[0].message
    assert "31" in errors[0].message


def test_mc32_ok(tmp_path):
    doc, errors = _run(tmp_path, mc=32)
    assert errors == []
    assert doc is not None


def test_mc_floor_is_structured_not_crash(tmp_path):
    doc, errors = _run(tmp_path, mc=0)
    assert doc is None
    assert errors[0].code == "chunker_failed"


# ---------- 空内容 md ----------

def test_thematic_only_md_fails(tmp_path):
    doc, errors = _run(tmp_path, md="---\n")
    assert doc is None
    assert errors[0].code == "no_extracted_elements"


def test_empty_md_details_source_type(tmp_path):
    _, errors = _run(tmp_path, md="---\n")
    assert errors[0].details["source_type"] == \
        "markdown"


def test_empty_md_details_has_warnings(tmp_path):
    _, errors = _run(tmp_path, md="---\n")
    assert isinstance(
        errors[0].details["warnings"], list)
    assert errors[0].details["warnings"]


# ---------- 交叉错配 ----------

def test_md_via_text_parser_unsupported(tmp_path):
    (tmp_path / "d.md").write_text(MD, encoding="utf-8")
    doc, errors = process_single(
        tmp_path / "d.md", None, parser_name="text")
    assert doc is None
    assert errors[0].code == "unsupported_type"


def test_txt_via_markdown_unsupported(tmp_path):
    (tmp_path / "t.txt").write_text(
        "plain\n\nsecond\n", encoding="utf-8")
    doc, errors = process_single(
        tmp_path / "t.txt", None,
        parser_name="markdown")
    assert doc is None
    assert errors[0].code == "unsupported_type"


def test_txt_via_text_parser_ok(tmp_path):
    (tmp_path / "t.txt").write_text(
        "plain\n\nsecond\n", encoding="utf-8")
    doc, errors = process_single(
        tmp_path / "t.txt", None, parser_name="text")
    assert errors == []
    assert len(doc.elements) == 2


# ---------- 写盘 ----------

def test_write_json_default_writes(tmp_path):
    _run(tmp_path)
    assert (tmp_path / "o.json").is_file()


def test_written_json_round_trips(tmp_path):
    _run(tmp_path)
    on_disk = json.loads(
        (tmp_path / "o.json").read_text(
            encoding="utf-8"))
    assert on_disk["source_type"] == "markdown"
    assert len(on_disk["chunks"]) == 3


def test_write_false_skips_disk(tmp_path):
    _run(tmp_path, write=False)
    assert not (tmp_path / "o.json").exists()


# ---------- schema 通过 ----------

def test_md_doc_passes_schema(tmp_path):
    doc, errors = _run(tmp_path)
    assert errors == []
    from app.schema import validate
    validate(doc.to_dict())


def test_chunk_metadata_max_chars_echo(tmp_path):
    doc, _ = _run(tmp_path)
    for c in doc.chunks:
        assert c.metadata["max_chars"] == 64
