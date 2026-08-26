r"""cli 扩展名映射全表：html/ipynb/md 自动
选择；未知扩展落 fallback 即拒（Round 1805）。

新角度：R1804 锁错误分层——**自动选择
映射：.html→html、.ipynb→ipynb、
.md→markdown（INFO+OK+exit 0）；未知
扩展 .xyz → INFO '自动选择: fallback'
→ fallback 拒绝 exit 1 + stderr 错误
JSON（code unsupported_type、details
suffix '.xyz'）**零覆盖：

- **三扩展**：各自 INFO 名 + exit 0
- **.xyz**：INFO fallback + exit 1 +
  unsupported_type
"""

from __future__ import annotations

import json
import subprocess
import sys

from pathlib import Path

PY = sys.executable
ROOT = Path(__file__).resolve().parents[1]


def _cli(*args):
    return subprocess.run(
        [PY, "-m", "app.cli", *args],
        capture_output=True, text=True, cwd=ROOT,
        encoding="utf-8")


def test_cli_autoselect_known_extensions(tmp_path):
    cases = [
        ("d.html", "<p>a</p>", "html"),
        ("d.md", "## T", "markdown"),
    ]
    for name, content, parser in cases:
        src = tmp_path / name
        src.write_text(content, encoding="utf-8")
        out = tmp_path / (name + ".json")
        r = _cli("parse", str(src), "-o", str(out))
        assert r.returncode == 0, name
        assert "自动选择" in r.stderr, name
        assert parser in r.stderr, name
        assert "[OK]" in r.stdout, name


def test_cli_autoselect_ipynb(tmp_path):
    src = tmp_path / "d.ipynb"
    src.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": ["x"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    out = tmp_path / "o.json"
    r = _cli("parse", str(src), "-o", str(out))
    assert r.returncode == 0
    assert "自动选择" in r.stderr
    assert "ipynb" in r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["metadata"]["ipynb"] is True


def test_cli_autoselect_unknown_falls_back(tmp_path):
    src = tmp_path / "d.xyz"
    src.write_text("zzz", encoding="utf-8")
    out = tmp_path / "o.json"
    r = _cli("parse", str(src), "-o", str(out))
    assert r.returncode == 1
    assert "自动选择" in r.stderr
    assert "fallback" in r.stderr
    data = json.loads(r.stderr[r.stderr.find("{"):])
    assert data["errors"][0]["code"] == (
        "unsupported_type")
    assert data["errors"][0]["details"][
        "suffix"] == ".xyz"
    assert not out.exists()
