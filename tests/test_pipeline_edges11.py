r"""app/pipeline.py 边角测试 - 第十一轮（Round 1364）。

补强 edges10 未覆盖的深度（probe 实证）：
- ipynb 走全管线分块几何——code cell 内换行在 chunk 文本中存活
  （chunker 只用空格 join part，part 自身含 \n 原样保留）
- cell 边界不是 chunk 边界——markdown heading 才是硬边界
- 长 code cell → long_paragraph_sentence_split（". " 句点切分）
- raw cell 并入后续 heading chunk
- 空 notebook → no_extracted_elements
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.pipeline import process_single


NB = {
    "cells": [
        {"cell_type": "markdown",
         "source": ["# Head\n", "\n",
                    "para one two three\n"]},
        {"cell_type": "code",
         "source": ["print(1)\n", "print(2)"]},
        {"cell_type": "markdown",
         "source": "## Sub\n\ntail text"},
        {"cell_type": "raw", "source": "raw stuff"},
    ],
    "metadata": {"kernelspec": {"language": "python"}},
    "nbformat": 4, "nbformat_minor": 5,
}


def _run(tmp_path, nb=NB, mc=64):
    (tmp_path / "n.ipynb").write_text(
        json.dumps(nb, ensure_ascii=False),
        encoding="utf-8")
    return process_single(
        tmp_path / "n.ipynb", tmp_path / "o.json",
        parser_name="ipynb", max_chars=mc)


# ---------- 分块几何 ----------

def test_ipynb_two_chunks(tmp_path):
    doc, errors = _run(tmp_path)
    assert errors == []
    assert len(doc.chunks) == 2


def test_code_newline_survives_in_chunk(tmp_path):
    doc, _ = _run(tmp_path)
    assert doc.chunks[0].text == (
        "Head para one two three "
        "print(1)\nprint(2)")


def test_cells_merge_across_boundary(tmp_path):
    doc, _ = _run(tmp_path)
    ids0 = doc.chunks[0].source_element_ids
    locs = {doc.elements[
        list(e.element_id for e in
             doc.elements).index(i)
    ].source_locator.get("cell_index")
        for i in ids0}
    assert locs == {0, 1}


def test_heading_is_hard_boundary(tmp_path):
    doc, _ = _run(tmp_path)
    assert doc.chunks[1].text == \
        "Sub tail text raw stuff"


def test_raw_merges_into_heading_chunk(tmp_path):
    doc, _ = _run(tmp_path)
    raw_ids = [e.element_id for e in
               doc.elements
               if e.metadata.get("kind")
               == "raw_cell"]
    assert raw_ids[0] in doc.chunks[
        1].source_element_ids


def test_six_elements(tmp_path):
    doc, errors = _run(tmp_path)
    assert errors == []
    assert len(doc.elements) == 6


def test_element_kinds(tmp_path):
    doc, _ = _run(tmp_path)
    kinds = [(e.type, e.metadata.get("kind"))
             for e in doc.elements]
    assert kinds == [
        ("heading", None),
        ("paragraph", None),
        ("paragraph", "code_cell"),
        ("heading", None),
        ("paragraph", None),
        ("paragraph", "raw_cell")]


# ---------- 长 code cell 句子切分 ----------

def long_nb():
    return {
        "cells": [
            {"cell_type": "code",
             "source": "x = 1. " * 30}],
        "metadata": {},
        "nbformat": 4,
    }


def test_long_code_four_chunks(tmp_path):
    doc, errors = _run(tmp_path, nb=long_nb())
    assert errors == []
    assert len(doc.chunks) == 4


def test_long_code_strategy(tmp_path):
    doc, _ = _run(tmp_path, nb=long_nb())
    for c in doc.chunks:
        assert c.metadata["strategy"] == \
            "long_paragraph_sentence_split"


def test_long_code_last_chunk_short(tmp_path):
    doc, _ = _run(tmp_path, nb=long_nb())
    lens = [len(c.text) for c in doc.chunks]
    assert lens[-1] == len("x = 1. " * 3) - 1 \
        or lens[-1] < lens[0]


def test_long_code_all_same_source(tmp_path):
    doc, _ = _run(tmp_path, nb=long_nb())
    assert all(
        c.source_element_ids == [
            doc.elements[0].element_id]
        for c in doc.chunks)


def test_long_code_no_char_loss(tmp_path):
    from app.chunkers import normalize_text
    doc, _ = _run(tmp_path, nb=long_nb())
    joined = " ".join(c.text for c in doc.chunks)
    assert normalize_text(joined) == \
        normalize_text(doc.elements[0].content)


# ---------- 空 notebook ----------

def test_empty_nb_no_elements(tmp_path):
    doc, errors = _run(tmp_path, nb={
        "cells": [], "metadata": {},
        "nbformat": 4})
    assert doc is None
    assert errors[0].code == \
        "no_extracted_elements"


def test_empty_nb_details_source_type(tmp_path):
    _, errors = _run(tmp_path, nb={
        "cells": [], "metadata": {},
        "nbformat": 4})
    assert errors[0].details[
        "source_type"] == "ipynb"


def test_all_blank_cells_no_elements(tmp_path):
    doc, errors = _run(tmp_path, nb={
        "cells": [{"cell_type": "code",
                   "source": " "},
                  {"cell_type": "raw",
                   "source": ""}],
        "metadata": {}, "nbformat": 4})
    assert doc is None
    assert errors[0].code == \
        "no_extracted_elements"


# ---------- schema 通过 + 写盘 ----------

def test_ipynb_doc_passes_schema(tmp_path):
    doc, errors = _run(tmp_path)
    assert errors == []
    from app.schema import validate
    validate(doc.to_dict())


def test_written_json_two_chunks(tmp_path):
    _run(tmp_path)
    on_disk = json.loads(
        (tmp_path / "o.json").read_text(
            encoding="utf-8"))
    assert on_disk["source_type"] == "ipynb"
    assert len(on_disk["chunks"]) == 2


def test_written_chunk_keeps_newline(tmp_path):
    _run(tmp_path)
    on_disk = json.loads(
        (tmp_path / "o.json").read_text(
            encoding="utf-8"))
    assert "print(1)\nprint(2)" in \
        on_disk["chunks"][0]["text"]


# ---------- chunk 元数据 ----------

def test_chunk_strategy_sequential(tmp_path):
    doc, _ = _run(tmp_path)
    for c in doc.chunks:
        assert c.metadata["strategy"] == \
            "sequential"


def test_chunk_max_chars_echo(tmp_path):
    doc, _ = _run(tmp_path)
    for c in doc.chunks:
        assert c.metadata["max_chars"] == 64
