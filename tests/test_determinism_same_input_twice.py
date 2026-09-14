r"""同输入重复解析/重复管线确定性测试（Round 1845）。

新角度（probe 实证，grep 核实 parser/pipeline 层"同一输入两次
结果全等"的确定性断言全库零覆盖——annotation 系的 determinis
是指标层）：
- **md/html Document 全等**：同一文件解析两次，Document dataclass
  深比较相等（elements/locator/section_path/metadata/warnings 全同）
- **text/ipynb 同规**：text 多段（含连续空行）、ipynb 三型 cell
  （markdown/code/raw + kernelspec language）两次全等
- **管线输出字节全等**：process_single 同输入跑两次，输出 JSON
  文件**逐字节相同**（无时间戳/随机序/路径差异泄漏），errors 空
"""

from __future__ import annotations

import json
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser
from app.parsers.ipynb_parser import IpynbParser
from app.parsers.markdown_parser import MarkdownParser
from app.parsers.text_parser import TextParser
from app.pipeline import process_single

MD = "# Head\n\npara one\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n"
HTML = "<h1>T</h1><p>a <b>b</b></p><table><tr><th>x</th></tr></table>"
NB = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {"kernelspec": {"language": "python", "name": "python3"}},
    "cells": [
        {"cell_type": "markdown", "source": ["# Title\n", "text"]},
        {"cell_type": "code", "source": "print(1)\n",
         "outputs": [], "execution_count": 1},
        {"cell_type": "raw", "source": "raw line"},
    ],
}


def test_md_html_document_determinism(tmp_path: Path):
    p = tmp_path / "a.md"
    p.write_text(MD, encoding="utf-8", newline="")
    d1 = MarkdownParser().parse(p, compute_file_hash(p))
    d2 = MarkdownParser().parse(p, compute_file_hash(p))
    assert d1 == d2
    assert len(d1.elements) == 3

    h = tmp_path / "a.html"
    h.write_text(HTML, encoding="utf-8", newline="")
    h1 = HtmlParser().parse(h, compute_file_hash(h))
    h2 = HtmlParser().parse(h, compute_file_hash(h))
    assert h1 == h2
    assert len(h1.elements) == 3


def test_text_ipynb_document_determinism(tmp_path: Path):
    t = tmp_path / "a.txt"
    t.write_text("para one\n\npara two\n\n\npara three\n",
                 encoding="utf-8", newline="")
    t1 = TextParser().parse(t, compute_file_hash(t))
    t2 = TextParser().parse(t, compute_file_hash(t))
    assert t1 == t2
    assert len(t1.elements) == 3

    n = tmp_path / "a.ipynb"
    n.write_text(json.dumps(NB), encoding="utf-8", newline="")
    i1 = IpynbParser().parse(n, compute_file_hash(n))
    i2 = IpynbParser().parse(n, compute_file_hash(n))
    assert i1 == i2
    assert len(i1.elements) == 4
    assert i1.metadata["language"] == "python"


def test_pipeline_output_byte_determinism(tmp_path: Path):
    src = tmp_path / "in.md"
    src.write_text(MD, encoding="utf-8", newline="")
    o1, e1 = process_single(src, tmp_path / "out1.json", parser_name="markdown")
    o2, e2 = process_single(src, tmp_path / "out2.json", parser_name="markdown")
    assert e1 == []
    assert e2 == []
    assert o1 == o2
    b1 = (tmp_path / "out1.json").read_bytes()
    b2 = (tmp_path / "out2.json").read_bytes()
    assert b1 == b2
    parsed1 = json.loads(b1)
    parsed2 = json.loads(b2)
    assert parsed1 == parsed2
    assert parsed1["source_path"] == str(src)
