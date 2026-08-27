r"""app/parsers/ipynb_parser.py 边角测试 - 第九轮（Round 1362）。

补强 edges-edges8 未覆盖的深度（probe 实证）：
- 跳格重编号——cell 3-6 被跳过后 element_id 仍连续（e0007 对应 cell_index 7）
- 空 raw 静默 vs 空 code 告警——同板不对称
- 未知 cell_type 'weird' → ipynb_unknown_cell_type + repr 渲染
- markdown cell 内 image resource_path 透传
- code cell source 列表拼接 + outputs/execution_count 丢弃
- section_path cell 间独立（cell 7 的 'Second' 不继承 cell 0 的 'Head'）
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.ipynb_parser import IpynbParser


def _nb():
    return {
        "cells": [
            {"cell_type": "markdown",
             "source": ["# Head\n", "\n", "- a\n", "- b\n", "\n",
                        "| x | y |\n", "| --- | --- |\n", "| 1 | 2 |\n",
                        "\n", "![pic](img.png)\n"]},
            {"cell_type": "code",
             "source": ["print(1)\n", "print(2)"],
             "outputs": [{"text": "1\n2"}],
             "execution_count": 5},
            {"cell_type": "raw", "source": "raw text"},
            {"cell_type": "raw", "source": "   "},
            {"cell_type": "code", "source": ""},
            {"cell_type": "weird", "source": "???"},
            "not a dict",
            {"cell_type": "markdown",
             "source": "## Second\n\nmid text"},
        ],
        "metadata": {"kernelspec": {"language": "python",
                                    "name": "python3"}},
        "nbformat": 4, "nbformat_minor": 5}


def _parse(nb):
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "n.ipynb").write_text(
            json.dumps(nb, ensure_ascii=False),
            encoding="utf-8")
        return IpynbParser().parse(
            tp / "n.ipynb",
            compute_file_hash(tp / "n.ipynb"))


def _full():
    return _parse(_nb())


# ---------- 跳格重编号 ----------

def test_gap_renumbering_continuous_ids():
    ids = [e.element_id for e in _full().elements]
    suffixes = [i.rsplit("e", 1)[1] for i in ids]
    assert suffixes == ["%04d" % k
                        for k in range(len(suffixes))]


def test_gap_cell_index_seven():
    doc = _full()
    assert doc.elements[7].source_locator[
        "cell_index"] == 7


def test_gap_ids_dont_track_cell_index():
    doc = _full()
    locs = [e.source_locator["cell_index"]
            for e in doc.elements]
    assert locs == [0, 0, 0, 0, 0, 1, 2, 7, 7]


def test_gap_nine_elements():
    assert len(_full().elements) == 9


# ---------- 空 raw 静默 vs 空 code 告警 ----------

def test_empty_raw_no_warning():
    doc = _full()
    codes = [w.code for w in doc.warnings]
    assert "ipynb_empty_raw_cell" not in codes


def test_empty_code_cell_warns():
    doc = _full()
    w = [w for w in doc.warnings
         if w.code == "ipynb_empty_code_cell"]
    assert len(w) == 1
    assert "cell #4" in w[0].reason


def test_empty_raw_skipped_not_element():
    doc = _full()
    raws = [e for e in doc.elements
            if e.source_locator.get("cell_type")
            == "raw"]
    assert len(raws) == 1


def test_warning_order_matches_cell_order():
    doc = _full()
    idxs = [w.details["cell_index"] for w
            in doc.warnings
            if "cell_index" in (w.details or {})]
    assert idxs == [4, 5, 6]


# ---------- 未知 cell_type ----------

def test_weird_cell_type_warning():
    doc = _full()
    w = [w for w in doc.warnings
         if w.code == "ipynb_unknown_cell_type"]
    assert len(w) == 1
    assert "'weird'" in w[0].reason


def test_weird_cell_details():
    doc = _full()
    w = [w for w in doc.warnings
         if w.code == "ipynb_unknown_cell_type"][0]
    assert w.details == {"cell_index": 5,
                         "cell_type": "weird"}


def test_weird_not_element():
    doc = _full()
    assert all(
        e.source_locator.get("cell_type") != "weird"
        for e in doc.elements)


def test_non_dict_cell_warning():
    doc = _full()
    w = [w for w in doc.warnings
         if w.code == "ipynb_bad_cell"]
    assert len(w) == 1
    assert "cell #6" in w[0].reason


# ---------- markdown cell 内 image ----------

def test_md_image_resource_path():
    doc = _full()
    img = [e for e in doc.elements
           if e.type == "image"][0]
    assert img.resource_path == "img.png"


def test_md_image_alt():
    doc = _full()
    img = [e for e in doc.elements
           if e.type == "image"][0]
    assert img.metadata["alt"] == "pic"


def test_md_image_cell_scoped():
    doc = _full()
    img = [e for e in doc.elements
           if e.type == "image"][0]
    assert img.source_locator["cell_index"] == 0
    assert img.source_locator["line"] == 10


def test_md_table_in_cell():
    doc = _full()
    t = [e for e in doc.elements
         if e.type == "table"][0]
    assert t.metadata["source"] == \
        "markdown_pipe_table"
    assert t.source_locator["line"] == 6


# ---------- code cell ----------

def test_code_list_source_joined():
    doc = _full()
    code = [e for e in doc.elements
            if e.metadata.get("kind")
            == "code_cell"][0]
    assert code.content == "print(1)\nprint(2)"


def test_code_outputs_dropped():
    doc = _full()
    code = [e for e in doc.elements
            if e.metadata.get("kind")
            == "code_cell"][0]
    assert "1\n2" not in code.content
    assert code.metadata == {
        "kind": "code_cell", "language": "python"}


# adoption 契约 §5/§8 注记（2026-08-27）：source 非法输入归一为 None（跳过 cell +
# ipynb_bad_cell）；code/raw 正文保留原始缩进换行（strip 仅判空）；locator 补 line=1。
# 以下原快照期望已按定稿契约改写。
def test_code_line1_in_locator():
    doc = _full()
    code = [e for e in doc.elements
            if e.metadata.get("kind")
            == "code_cell"][0]
    assert code.source_locator["line"] == 1
    assert code.source_locator == {
        "cell_index": 1, "cell_type": "code",
        "line": 1}


# ---------- section_path cell 间独立 ----------

def test_section_scoped_per_cell():
    doc = _full()
    heads = [e for e in doc.elements
             if e.type == "heading"]
    assert heads[0].source_locator[
        "section_path"] == "Head"
    assert heads[1].source_locator[
        "section_path"] == "Second"


def test_second_cell_para_under_second():
    doc = _full()
    paras_md = [e for e in doc.elements
                if e.type == "paragraph"
                and e.source_locator.get(
                    "cell_index") == 7]
    assert paras_md[0].source_locator[
        "section_path"] == "Second"


def test_no_cross_cell_section_inheritance():
    doc = _full()
    assert all(
        "Head > Second" not in str(
            e.source_locator)
        for e in doc.elements)


# ---------- doc 元信息 ----------

def test_doc_metadata_cell_count():
    assert _full().metadata["cell_count"] == 8


def test_doc_metadata_language():
    assert _full().metadata["language"] == "python"


def test_doc_metadata_nbformat():
    m = _full().metadata
    assert m["nbformat"] == 4
    assert m["nbformat_minor"] == 5
    assert m["ipynb"] is True


def test_doc_identity():
    doc = _full()
    assert doc.parser_name == "ipynb"
    assert doc.parser_version == "stdlib/0.1.0"
    assert doc.source_type == "ipynb"


# ---------- kernelspec 回退链 ----------

def test_language_fallback_to_ks_name():
    nb = _nb()
    nb["metadata"]["kernelspec"] = {"name": "julia-1.9"}
    assert _parse(nb).metadata["language"] == \
        "julia-1.9"


def test_language_fallback_to_language_info():
    nb = _nb()
    nb["metadata"] = {"language_info": {"name": "r"}}
    assert _parse(nb).metadata["language"] == "r"


def test_language_empty_when_nothing():
    nb = _nb()
    nb["metadata"] = {}
    assert _parse(nb).metadata["language"] == ""


def test_code_language_follows_fallback():
    nb = _nb()
    nb["metadata"] = {"language_info": {"name": "r"}}
    doc = _parse(nb)
    code = [e for e in doc.elements
            if e.metadata.get("kind")
            == "code_cell"][0]
    assert code.metadata["language"] == "r"
