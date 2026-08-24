r"""app/cli.py 边角测试 - 第十轮（Round 1397）。

新角度（probe 实证）：四个 stdlib parser 穿 CLI 子进程纵向
（R1386 只做了真 PDF/DOCX，md/html/txt/ipynb 的 parse→
validate→inspect 三连未锁）：
- 各自 source_type/parser_name 自动推断（markdown/html/
  text/ipynb + vstdlib/0.1.0）
- 元素序列与类型（txt 无 heading、ipynb code → paragraph）
- validate rc 0；inspect counts 行 'elements=2 chunks=1
  relations=0 warnings=0 errors=0'
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


VENV_PYTHON = str(
    Path(__file__).resolve().parent.parent
    / ".venv" / "Scripts" / "python.exe")
PROJECT_ROOT = \
    Path(__file__).resolve().parent.parent
_PYTHON = (VENV_PYTHON
           if Path(VENV_PYTHON).is_file()
           else sys.executable)


def _run_cli(args):
    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH":
            str(PROJECT_ROOT)
            + os.pathsep
            + os.environ.get("PYTHONPATH", ""),
    }
    proc = subprocess.run(
        [_PYTHON, "-X", "utf8",
         "-m", "app.cli", *args],
        capture_output=True, text=True,
        encoding="utf-8",
        errors="replace", env=env)
    return (proc.returncode,
            proc.stdout, proc.stderr)


_NB = json.dumps({
    "cells": [
        {"cell_type": "markdown",
         "metadata": {},
         "source": ["# NB Title\n"]},
        {"cell_type": "code",
         "metadata": {},
         "source": ["print(1)\n"],
         "outputs": [],
         "execution_count": None}],
    "metadata": {},
    "nbformat": 4,
    "nbformat_minor": 5})

_FILES = {
    "a.md": ("# MD Title\n\n"
             "md body paragraph.\n"),
    "b.html": ("<html><body>"
               "<h2>HTML Title</h2>"
               "<p>html body</p>"
               "</body></html>"),
    "c.txt": ("plain text title\n\n"
              "second paragraph\n"),
    "d.ipynb": _NB,
}


def _parse(tmp_path, name):
    p = tmp_path / name
    p.write_text(_FILES[name],
                 encoding="utf-8")
    out = tmp_path / (name + ".json")
    rc, so, _ = _run_cli(
        ["parse", str(p), "-o", str(out)])
    data = json.loads(
        out.read_text(encoding="utf-8"))
    return rc, so, data, out


# ---------- markdown ----------

def test_md_rc0(tmp_path):
    rc, so, _, _ = _parse(tmp_path, "a.md")
    assert rc == 0
    assert so.startswith("[OK]")


def test_md_source_type(tmp_path):
    _, _, data, _ = _parse(tmp_path, "a.md")
    assert data["source_type"] == \
        "markdown"
    assert data["parser_name"] == \
        "markdown"


def test_md_elements(tmp_path):
    _, _, data, _ = _parse(tmp_path, "a.md")
    assert [(e["type"], e["content"])
            for e in data["elements"]] == [
        ("heading", "MD Title"),
        ("paragraph",
         "md body paragraph.")]


def test_md_validate(tmp_path):
    _, _, _, out = _parse(tmp_path,
                          "a.md")
    rc, so, _ = _run_cli(
        ["validate", str(out)])
    assert rc == 0
    assert "通过 Schema 校验" in so


def test_md_inspect(tmp_path):
    _, _, _, out = _parse(tmp_path,
                          "a.md")
    _, so, _ = _run_cli(
        ["inspect", str(out)])
    assert "parser:      markdown " \
        "vstdlib/0.1.0" in so
    assert ("counts:      elements=2 "
            "chunks=1 relations=0 "
            "warnings=0 errors=0") in so


# ---------- html ----------

def test_html_rc0(tmp_path):
    rc, so, _, _ = _parse(tmp_path,
                          "b.html")
    assert rc == 0


def test_html_source_type(tmp_path):
    _, _, data, _ = _parse(tmp_path,
                           "b.html")
    assert data["source_type"] == "html"


def test_html_elements(tmp_path):
    _, _, data, _ = _parse(tmp_path,
                           "b.html")
    assert [(e["type"], e["content"])
            for e in data["elements"]] == [
        ("heading", "HTML Title"),
        ("paragraph", "html body")]


def test_html_validate(tmp_path):
    _, _, _, out = _parse(tmp_path,
                          "b.html")
    rc, _, _ = _run_cli(
        ["validate", str(out)])
    assert rc == 0


def test_html_inspect(tmp_path):
    _, _, _, out = _parse(tmp_path,
                          "b.html")
    _, so, _ = _run_cli(
        ["inspect", str(out)])
    assert "parser:      html " \
        "vstdlib/0.1.0" in so


# ---------- text ----------

def test_txt_rc0(tmp_path):
    rc, _, _, _ = _parse(tmp_path,
                         "c.txt")
    assert rc == 0


def test_txt_source_type(tmp_path):
    _, _, data, _ = _parse(tmp_path,
                           "c.txt")
    assert data["source_type"] == "text"


def test_txt_no_headings(tmp_path):
    _, _, data, _ = _parse(tmp_path,
                           "c.txt")
    assert [(e["type"], e["content"])
            for e in data["elements"]] == [
        ("paragraph",
         "plain text title"),
        ("paragraph",
         "second paragraph")]


def test_txt_validate(tmp_path):
    _, _, _, out = _parse(tmp_path,
                          "c.txt")
    rc, _, _ = _run_cli(
        ["validate", str(out)])
    assert rc == 0


def test_txt_inspect(tmp_path):
    _, _, _, out = _parse(tmp_path,
                          "c.txt")
    _, so, _ = _run_cli(
        ["inspect", str(out)])
    assert "parser:      text " \
        "vstdlib/0.1.0" in so


# ---------- ipynb ----------

def test_ipynb_rc0(tmp_path):
    rc, _, _, _ = _parse(tmp_path,
                         "d.ipynb")
    assert rc == 0


def test_ipynb_source_type(tmp_path):
    _, _, data, _ = _parse(tmp_path,
                           "d.ipynb")
    assert data["source_type"] == \
        "ipynb"


def test_ipynb_elements(tmp_path):
    _, _, data, _ = _parse(tmp_path,
                           "d.ipynb")
    assert [(e["type"], e["content"])
            for e in data["elements"]] == [
        ("heading", "NB Title"),
        ("paragraph", "print(1)")]


def test_ipynb_validate(tmp_path):
    _, _, _, out = _parse(tmp_path,
                          "d.ipynb")
    rc, _, _ = _run_cli(
        ["validate", str(out)])
    assert rc == 0


def test_ipynb_inspect(tmp_path):
    _, _, _, out = _parse(tmp_path,
                          "d.ipynb")
    _, so, _ = _run_cli(
        ["inspect", str(out)])
    assert "parser:      ipynb " \
        "vstdlib/0.1.0" in so


# ---------- 跨类型 ----------

def test_all_four_counts_line(tmp_path):
    for name in _FILES:
        _, _, _, out = _parse(tmp_path,
                              name)
        _, so, _ = _run_cli(
            ["inspect", str(out)])
        assert ("counts:      "
                "elements=2 chunks=1 "
                "relations=0 warnings=0 "
                "errors=0") in so


def test_all_four_single_chunk(tmp_path):
    for name in _FILES:
        _, _, data, _ = _parse(tmp_path,
                               name)
        assert len(data["chunks"]) == 1
