r"""pipeline ipynb 语言来源优先级：
kernelspec > language_info > 空（Round 1757）。

新角度：R1756 锁 WarningRecord——**code
cell 元素 language 与 doc.metadata
language 同源解析：仅 kernelspec →
'python'；仅 language_info → 'julia'；
两者并存 kernelspec 胜（'python' 压过
'r'）；都无 → ''（空串非 null）**零覆盖：

- **both**：element 与 doc 都 'python'
- **language_info only**：都 'julia'
- **neither**：element metadata
  {'kind': 'code_cell', 'language': ''}
  且 doc.metadata['language'] == ''
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, meta):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "code",
                   "source": ["x = 1"]}],
        "metadata": meta, "nbformat": 4}),
        encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="ipynb")


def test_kernelspec_wins_over_language_info(tmp_path):
    doc, errors = _run(tmp_path, {
        "kernelspec": {"language": "python"},
        "language_info": {"name": "r"}})
    assert errors == []
    assert doc.elements[0].metadata == {
        "kind": "code_cell", "language": "python"}
    assert doc.metadata["language"] == "python"


def test_language_info_fallback(tmp_path):
    doc, errors = _run(tmp_path, {
        "language_info": {"name": "julia"}})
    assert errors == []
    assert doc.elements[0].metadata == {
        "kind": "code_cell", "language": "julia"}
    assert doc.metadata["language"] == "julia"


def test_no_language_sources_empty_string(tmp_path):
    doc, errors = _run(tmp_path, {})
    assert errors == []
    assert doc.elements[0].metadata == {
        "kind": "code_cell", "language": ""}
    assert doc.metadata["language"] == ""
