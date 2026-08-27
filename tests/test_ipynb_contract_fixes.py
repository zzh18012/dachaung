# -*- coding: utf-8 -*-
"""ipynb 契约修正的钉住测试（adoption 原创测试，docs/ipynb-contract.md）。

每个修正提交追加对应测试组；与机械搬运的 autoline 快照测试相互独立。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.parsers.base import ParserError
from app.parsers.ipynb_parser import IpynbParser


def _nb(cells, nbformat=4, nbformat_minor=5, metadata=None):
    return {
        "cells": cells,
        "metadata": metadata if metadata is not None else {},
        "nbformat": nbformat,
        "nbformat_minor": nbformat_minor,
    }


def _cell(ct, source, **extra):
    c = {"cell_type": ct, "metadata": {}, "source": source}
    if ct == "code":
        c["outputs"] = []
        c["execution_count"] = None
    c.update(extra)
    return c


def _write(tmp_path, nb, name="t.ipynb"):
    p = tmp_path / name
    p.write_text(json.dumps(nb, ensure_ascii=False), encoding="utf-8")
    return p


# ---------- 修正 1：版本字段整数类型检查 + nbformat == 4 精确范围（契约 §2） ----------


def test_version_missing_rejected_as_bad_structure(tmp_path):
    nb = _nb([_cell("markdown", "# x\n")])
    del nb["nbformat"]
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(_write(tmp_path, nb), source_hash="0" * 64)
    assert ei.value.code == "ipynb_bad_structure"
    assert ei.value.details["field"] == "nbformat"


def test_version_string_rejected_as_bad_structure(tmp_path):
    nb = _nb([_cell("markdown", "# x\n")], nbformat="4")
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(_write(tmp_path, nb), source_hash="0" * 64)
    assert ei.value.code == "ipynb_bad_structure"


def test_version_bool_rejected_as_bad_structure(tmp_path):
    nb = _nb([_cell("markdown", "# x\n")], nbformat=True)
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(_write(tmp_path, nb), source_hash="0" * 64)
    assert ei.value.code == "ipynb_bad_structure"


def test_version_float_rejected_as_bad_structure(tmp_path):
    nb = _nb([_cell("markdown", "# x\n")], nbformat=4.0)
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(_write(tmp_path, nb), source_hash="0" * 64)
    assert ei.value.code == "ipynb_bad_structure"


def test_future_major_unsupported(tmp_path):
    nb = _nb([_cell("markdown", "# x\n")], nbformat=5)
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(_write(tmp_path, nb), source_hash="0" * 64)
    assert ei.value.code == "ipynb_unsupported_version"


def test_old_major_unsupported(tmp_path):
    nb = _nb([_cell("markdown", "# x\n")], nbformat=3)
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(_write(tmp_path, nb), source_hash="0" * 64)
    assert ei.value.code == "ipynb_unsupported_version"


def test_minor_missing_rejected_as_bad_structure(tmp_path):
    nb = _nb([_cell("markdown", "# x\n")])
    del nb["nbformat_minor"]
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(_write(tmp_path, nb), source_hash="0" * 64)
    assert ei.value.code == "ipynb_bad_structure"
    assert ei.value.details["field"] == "nbformat_minor"


def test_minor_negative_rejected_as_bad_structure(tmp_path):
    nb = _nb([_cell("markdown", "# x\n")], nbformat_minor=-1)
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(_write(tmp_path, nb), source_hash="0" * 64)
    assert ei.value.code == "ipynb_bad_structure"


def test_minor_bool_rejected_as_bad_structure(tmp_path):
    nb = _nb([_cell("markdown", "# x\n")], nbformat_minor=False)
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(_write(tmp_path, nb), source_hash="0" * 64)
    assert ei.value.code == "ipynb_bad_structure"


def test_high_minor_parsed_by_known_fields(tmp_path):
    """更高 minor 按已知字段处理（契约 §1），不宣称支持其新增能力。"""
    nb = _nb([_cell("markdown", "# hi\n"), _cell("code", "x = 1")], nbformat_minor=9)
    doc = IpynbParser().parse(_write(tmp_path, nb), source_hash="0" * 64)
    assert doc.errors == []
    assert doc.metadata["nbformat"] == 4
    assert doc.metadata["nbformat_minor"] == 9
