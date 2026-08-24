r"""跨 parser 同文本对照测试 - 第一轮（Round 1403）。

新角度（probe 实证）：同一语义文本（标题 + 段落）穿
markdown/html/text/ipynb 四个 stdlib parser 的横向对照
（历史都单 parser 锁，从未并排比较同文本的行为差异）：
- md/html/ipynb 都产出 heading+paragraph，txt 全 paragraph
- section_path ' > ' 连接在 md/html/ipynb 一致；
  txt locator 只有 line 无 section_path
- line 语义三种：md 真文件行（1/3/5/7）、html 恒 1、
  ipynb cell 内行（1/2/4/5，空行不计）
- chunk 文本四种 parser 完全相同（'Same Title Same body
  text here.'），H2 处切双 chunk 也三态一致
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.pipeline import process_single


_SIMPLE = {
    "markdown": (
        "# Same Title\n\n"
        "Same body text here.\n",
        "a.md"),
    "html": (
        "<html><body>"
        "<h1>Same Title</h1>"
        "<p>Same body text here.</p>"
        "</body></html>",
        "b.html"),
    "text": (
        "Same Title\n\n"
        "Same body text here.\n",
        "c.txt"),
    "ipynb": None,
}

_NESTED_MD = (
    "# Root H1\n\nroot body.\n\n"
    "## Sub H2\n\nsub body.\n")
_NESTED_HTML = (
    "<html><body><h1>Root H1</h1>"
    "<p>root body.</p>"
    "<h2>Sub H2</h2>"
    "<p>sub body.</p></body></html>")
_NESTED_NB = {
    "cells": [
        {"cell_type": "markdown",
         "metadata": {},
         "source": [
             "# Root H1\n", "root body.\n",
             "\n", "## Sub H2\n",
             "sub body.\n"]}],
    "metadata": {},
    "nbformat": 4,
    "nbformat_minor": 5}


def _nb(simple):
    body = ("# Same Title\n"
            "Same body text here.\n")
    if simple:
        return json.dumps({
            "cells": [
                {"cell_type": "markdown",
                 "metadata": {},
                 "source": [
                     "# Same Title\n",
                     "Same body text "
                     "here.\n"]}],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 5})
    return json.dumps(_NESTED_NB)


def _run(tmp_path, parser, content,
         name):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    doc, errors = process_single(
        p, None, parser_name=parser,
        max_chars=800)
    assert errors == []
    return doc


def _simple_docs(tmp_path):
    out = {}
    for parser, board in _SIMPLE.items():
        if board is None:
            content, name = (
                _nb(simple=True),
                "d.ipynb")
        else:
            content, name = board
        out[parser] = _run(
            tmp_path, parser, content,
            name)
    return out


def _nested_docs(tmp_path):
    return {
        "markdown": _run(
            tmp_path, "markdown",
            _NESTED_MD, "n.md"),
        "html": _run(
            tmp_path, "html",
            _NESTED_HTML, "n.html"),
        "ipynb": _run(
            tmp_path, "ipynb",
            _nb(simple=False),
            "n.ipynb"),
    }


# ---------- 简单板：元素 ----------

def test_types_three_vs_txt(
        tmp_path):
    docs = _simple_docs(tmp_path)
    for parser in ("markdown",
                   "html", "ipynb"):
        assert [e.type for e in
                docs[parser].elements
                ] == ["heading",
                      "paragraph"]
    assert [e.type for e in
            docs["text"].elements
            ] == ["paragraph",
                  "paragraph"]


def test_contents_identical_all_four(
        tmp_path):
    docs = _simple_docs(tmp_path)
    for parser, doc in docs.items():
        assert [e.content for e in
                doc.elements] == [
            "Same Title",
            "Same body text here."]


def test_heading_level_three(
        tmp_path):
    docs = _simple_docs(tmp_path)
    for parser in ("markdown",
                   "html", "ipynb"):
        assert docs[parser].elements[
            0].metadata == {"level": 1}
    assert docs["text"].elements[
        0].metadata == {}


def test_source_types(tmp_path):
    docs = _simple_docs(tmp_path)
    for parser, doc in docs.items():
        assert doc.source_type \
            == parser


def test_document_ids_distinct(
        tmp_path):
    docs = _simple_docs(tmp_path)
    ids = [d.document_id
           for d in docs.values()]
    assert len(set(ids)) == 4


# ---------- 简单板：locator ----------

def test_txt_locator_keys_line_only(
        tmp_path):
    docs = _simple_docs(tmp_path)
    for e in docs["text"].elements:
        assert list(
            e.source_locator) == [
            "line"]


def test_md_paragraph_line3(
        tmp_path):
    docs = _simple_docs(tmp_path)
    assert docs["markdown"].elements[
        1].source_locator == {
        "line": 3,
        "section_path": "Same Title"}


def test_html_both_lines_one(
        tmp_path):
    docs = _simple_docs(tmp_path)
    for e in docs["html"].elements:
        assert e.source_locator == {
            "line": 1,
            "section_path": "Same Title"}


def test_ipynb_cell_fields(
        tmp_path):
    docs = _simple_docs(tmp_path)
    assert docs["ipynb"].elements[
        1].source_locator == {
        "cell_index": 0,
        "cell_type": "markdown",
        "line": 2,
        "section_path": "Same Title"}


def test_section_path_simple(
        tmp_path):
    docs = _simple_docs(tmp_path)
    for parser in ("markdown",
                   "html", "ipynb"):
        for e in docs[parser].elements:
            assert e.source_locator[
                "section_path"] \
                == "Same Title"


# ---------- 简单板：chunk ----------

def test_chunk_identical_all_four(
        tmp_path):
    docs = _simple_docs(tmp_path)
    for doc in docs.values():
        assert [c.text for c in
                doc.chunks] == [
            "Same Title Same body "
            "text here."]


def test_chunk_refs_all_four(
        tmp_path):
    docs = _simple_docs(tmp_path)
    for doc in docs.values():
        assert [len(c.source_element_ids)
                for c in doc.chunks] == [2]


# ---------- 嵌套板（md/html/ipynb） ----------

def test_nested_section_path_join(
        tmp_path):
    docs = _nested_docs(tmp_path)
    for doc in docs.values():
        assert doc.elements[2
                            ].source_locator[
            "section_path"] == (
            "Root H1 > Sub H2")
        assert doc.elements[3
                            ].source_locator[
            "section_path"] == (
            "Root H1 > Sub H2")


def test_nested_levels(tmp_path):
    docs = _nested_docs(tmp_path)
    for doc in docs.values():
        assert [e.metadata.get("level")
                for e in doc.elements
                ] == [1, None, 2, None]


def test_nested_two_chunks(
        tmp_path):
    docs = _nested_docs(tmp_path)
    for doc in docs.values():
        assert [c.text for c in
                doc.chunks] == [
            "Root H1 root body.",
            "Sub H2 sub body."]


def test_nested_md_lines(tmp_path):
    doc = _nested_docs(
        tmp_path)["markdown"]
    assert [e.source_locator["line"]
            for e in doc.elements
            ] == [1, 3, 5, 7]


def test_nested_html_lines_all_one(
        tmp_path):
    doc = _nested_docs(
        tmp_path)["html"]
    assert [e.source_locator["line"]
            for e in doc.elements
            ] == [1, 1, 1, 1]


def test_nested_ipynb_incell_lines(
        tmp_path):
    doc = _nested_docs(
        tmp_path)["ipynb"]
    assert [e.source_locator["line"]
            for e in doc.elements
            ] == [1, 2, 4, 5]


def test_nested_root_section(
        tmp_path):
    docs = _nested_docs(tmp_path)
    for doc in docs.values():
        assert doc.elements[0
                            ].source_locator[
            "section_path"] == "Root H1"
        assert doc.elements[1
                            ].source_locator[
            "section_path"] == "Root H1"
