"""Jupyter Notebook (.ipynb) parser 的单元测试 + 端到端 pipeline 测试。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.models import Document
from app.parsers import ParserError
from app.parsers.ipynb_parser import IpynbParser


VENV_PYTHON = str(
    Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe"
)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PYTHON = VENV_PYTHON if Path(VENV_PYTHON).is_file() else sys.executable


def _nb(cells: list[dict], language: str = "python") -> dict:
    """构造最小 nbformat 4 notebook。"""
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": f"{language.capitalize()} 3",
                "language": language,
                "name": f"{language}3",
            },
            "language_info": {"name": language},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _write_nb(tmp_path: Path, name: str, nb: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(nb, ensure_ascii=False), encoding="utf-8")
    return p


# ---------- 基础 cell 类型 ----------


def test_ipynb_markdown_cell_emits_heading_and_paragraph(tmp_path: Path):
    nb = _nb([
        {"cell_type": "markdown", "source": ["# Title\n", "Body text."], "metadata": {}},
    ])
    p = _write_nb(tmp_path, "a.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    assert doc.source_type == "ipynb"
    types = [e.type for e in doc.elements]
    assert "heading" in types
    assert "paragraph" in types
    # heading 内容
    headings = [e for e in doc.elements if e.type == "heading"]
    assert len(headings) == 1
    assert headings[0].content == "Title"


def test_ipynb_code_cell_emits_paragraph_with_kind(tmp_path: Path):
    nb = _nb([
        {"cell_type": "code", "source": "print('hi')\nx = 1", "metadata": {}, "outputs": [], "execution_count": 1},
    ])
    p = _write_nb(tmp_path, "b.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="b" * 64)
    code = [e for e in doc.elements if e.metadata.get("kind") == "code_cell"]
    assert len(code) == 1
    assert "print('hi')" in code[0].content
    assert code[0].metadata["language"] == "python"


def test_ipynb_raw_cell_emits_paragraph_with_kind(tmp_path: Path):
    nb = _nb([
        {"cell_type": "raw", "source": "raw content", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "c.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="c" * 64)
    raws = [e for e in doc.elements if e.metadata.get("kind") == "raw_cell"]
    assert len(raws) == 1
    assert raws[0].content == "raw content"


def test_ipynb_mixed_cells(tmp_path: Path):
    nb = _nb([
        {"cell_type": "markdown", "source": "# Section", "metadata": {}},
        {"cell_type": "code", "source": "x = 1", "metadata": {}},
        {"cell_type": "markdown", "source": "More text.", "metadata": {}},
        {"cell_type": "raw", "source": "raw", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "d.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="d" * 64)
    assert doc.metadata["cell_count"] == 4
    # markdown cell 1: 1 heading
    # code cell 2: 1 paragraph (code_cell)
    # markdown cell 3: 1 paragraph
    # raw cell 4: 1 paragraph (raw_cell)
    assert len(doc.elements) == 4


# ---------- source_locator ----------


def test_ipynb_locator_markdown_carries_cell_index_and_line(tmp_path: Path):
    nb = _nb([
        {"cell_type": "markdown", "source": "# H\n\nbody", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "e.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="e" * 64)
    heading = doc.elements[0]
    assert heading.source_locator["cell_index"] == 0
    assert heading.source_locator["cell_type"] == "markdown"
    assert heading.source_locator["line"] == 1
    # section_path 在该 cell 内
    assert heading.source_locator["section_path"] == "H"


def test_ipynb_locator_code_cell_basic(tmp_path: Path):
    nb = _nb([
        {"cell_type": "code", "source": "x = 1", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "f.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="10" * 32)
    code = doc.elements[0]
    assert code.source_locator["cell_index"] == 0
    assert code.source_locator["cell_type"] == "code"
    # code cell 没有 line / section_path
    assert "line" not in code.source_locator
    assert "section_path" not in code.source_locator


def test_ipynb_element_ids_consecutive_across_cells(tmp_path: Path):
    """跨 cell 的 element_id 连续编号。"""
    nb = _nb([
        {"cell_type": "markdown", "source": "# A\n\nB\n\nC", "metadata": {}},  # 3 element
        {"cell_type": "markdown", "source": "D\n\nE", "metadata": {}},  # 2 element
    ])
    p = _write_nb(tmp_path, "g.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="11" * 32)
    ids = [e.element_id for e in doc.elements]
    suffixes = [eid.split("::e")[1] for eid in ids]
    assert suffixes == ["0000", "0001", "0002", "0003", "0004"]


def test_ipynb_metadata_records_language_and_counts(tmp_path: Path):
    nb = _nb([
        {"cell_type": "code", "source": "print('a')", "metadata": {}},
        {"cell_type": "code", "source": "print('b')", "metadata": {}},
    ], language="julia")
    p = _write_nb(tmp_path, "h.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="12" * 32)
    assert doc.metadata["cell_count"] == 2
    assert doc.metadata["language"] == "julia"
    assert doc.metadata["nbformat"] == 4


# ---------- 边界 ----------


def test_ipynb_source_as_list_concatenated(tmp_path: Path):
    """source 可以是 list[str]，需正确拼接。"""
    nb = _nb([
        {"cell_type": "code", "source": ["line1\n", "line2\n", "line3"], "metadata": {}},
    ])
    p = _write_nb(tmp_path, "i.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="13" * 32)
    code = [e for e in doc.elements if e.metadata.get("kind") == "code_cell"][0]
    assert "line1" in code.content
    assert "line2" in code.content
    assert "line3" in code.content


def test_ipynb_empty_code_cell_skipped_with_warning(tmp_path: Path):
    nb = _nb([
        {"cell_type": "code", "source": "", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "j.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="14" * 32)
    assert doc.elements == []
    codes = [w.code for w in doc.warnings]
    assert "ipynb_empty_code_cell" in codes


def test_ipynb_empty_notebook_yields_warning(tmp_path: Path):
    nb = _nb([])
    p = _write_nb(tmp_path, "k.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="15" * 32)
    assert doc.elements == []
    codes = [w.code for w in doc.warnings]
    assert "ipynb_no_content" in codes


def test_ipynb_unknown_cell_type_warning(tmp_path: Path):
    nb = _nb([
        {"cell_type": "weird", "source": "stuff", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "l.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="16" * 32)
    codes = [w.code for w in doc.warnings]
    assert "ipynb_unknown_cell_type" in codes


# ---------- 错误路径 ----------


def test_ipynb_missing_file_raises(tmp_path: Path):
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(tmp_path / "nope.ipynb", source_hash="x" * 64)
    assert exc.value.code == "file_not_found"


def test_ipynb_unsupported_extension_raises(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hi")
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, source_hash="y" * 64)
    assert exc.value.code == "unsupported_type"


def test_ipynb_invalid_json_raises(tmp_path: Path):
    p = tmp_path / "bad.ipynb"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, source_hash="z" * 64)
    assert exc.value.code == "ipynb_invalid_json"


def test_ipynb_unsupported_nbformat_version_raises(tmp_path: Path):
    nb = {
        "cells": [{"cell_type": "code", "source": "x", "metadata": {}}],
        "metadata": {},
        "nbformat": 3,
        "nbformat_minor": 0,
    }
    p = _write_nb(tmp_path, "old.ipynb", nb)
    with pytest.raises(ParserError) as exc:
        IpynbParser().parse(p, source_hash="0" * 64)
    assert exc.value.code == "ipynb_unsupported_version"


# ---------- Document / schema ----------


def test_ipynb_parser_name_and_version(tmp_path: Path):
    p = _write_nb(tmp_path, "x.ipynb", _nb([
        {"cell_type": "code", "source": "x=1", "metadata": {}}
    ]))
    doc = IpynbParser().parse(p, source_hash="a" * 64)
    assert doc.parser_name == "ipynb"
    assert doc.parser_version.startswith("stdlib/")
    assert doc.chunks == []
    assert doc.errors == []


def test_ipynb_full_document_schema_valid(tmp_path: Path):
    from app.schema import validate

    nb = _nb([
        {"cell_type": "markdown", "source": "# Title\n\nIntro paragraph.", "metadata": {}},
        {"cell_type": "code", "source": "x = 1\nprint(x)", "metadata": {}},
        {"cell_type": "markdown", "source": "## Sub\n\nMore.", "metadata": {}},
        {"cell_type": "raw", "source": "raw text", "metadata": {}},
    ])
    p = _write_nb(tmp_path, "full.ipynb", nb)
    doc = IpynbParser().parse(p, source_hash="b" * 64)
    validate(doc.to_dict())


def test_ipynb_pipeline_end_to_end(tmp_path: Path):
    from app.pipeline import process_single

    nb = _nb([
        {"cell_type": "markdown", "source": "# Project\n\nIntro.", "metadata": {}},
        {"cell_type": "code", "source": "x = 1\ny = 2\nprint(x+y)", "metadata": {}},
        {"cell_type": "markdown", "source": "## Background\n\nMore content here.", "metadata": {}},
    ])
    src = _write_nb(tmp_path, "doc.ipynb", nb)
    out = tmp_path / "out.json"
    document, errors = process_single(src, out, parser_name="ipynb", write_json=True)
    assert errors == []
    assert document is not None
    assert document.source_type == "ipynb"
    types = {e.type for e in document.elements}
    assert "heading" in types
    assert "paragraph" in types
    assert len(document.chunks) >= 1
    for c in document.chunks:
        assert c.source_element_ids


def test_cli_parse_ipynb_end_to_end(tmp_path: Path):
    nb = _nb([
        {"cell_type": "markdown", "source": "# Title", "metadata": {}},
        {"cell_type": "code", "source": "print('hi')", "metadata": {}},
    ])
    src = tmp_path / "doc.ipynb"
    src.write_text(json.dumps(nb, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "out.json"

    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(PROJECT_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    proc = subprocess.run(
        [_PYTHON, "-m", "app.cli", "parse", str(src),
         "-o", str(out), "--parser", "ipynb"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    assert "[OK]" in proc.stdout
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source_type"] == "ipynb"
    assert data["parser_name"] == "ipynb"
    assert len(data["elements"]) >= 2
