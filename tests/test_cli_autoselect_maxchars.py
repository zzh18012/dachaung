r"""cli 扩展名自动选 parser、显式 --parser
无 INFO、--max-chars 传达到切分（Round 1803）。

新角度：R1802 锁 CLI 基本面——**省略
--parser 时按扩展名自动选择：'[INFO]
未指定 --parser，按扩展名 .txt 自动
选择: text'（INFO 行走 stderr）；显式
--parser 不出 INFO；--max-chars 100 →
300 词文本切 14 块、全部 ≤100、块
metadata max_chars=100**零覆盖：

- **无 --parser**：INFO + OK + exit 0
- **显式 --parser**：无自动选择 INFO
- **--max-chars 100**：14 块全 ≤100
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


def test_cli_auto_selects_parser_by_ext(tmp_path):
    src = tmp_path / "d.txt"
    src.write_text("aaa bbb\n", encoding="utf-8")
    out = tmp_path / "o.json"
    r = _cli("parse", str(src), "-o", str(out))
    assert r.returncode == 0
    assert "自动选择" in r.stderr
    assert "text" in r.stderr
    assert "[OK]" in r.stdout
    assert out.exists()


def test_cli_explicit_parser_no_info(tmp_path):
    src = tmp_path / "d.txt"
    src.write_text("aaa bbb\n", encoding="utf-8")
    out = tmp_path / "o.json"
    r = _cli("parse", str(src), "-o", str(out),
             "--parser", "text")
    assert r.returncode == 0
    assert "自动选择" not in r.stderr
    assert "[OK]" in r.stdout


def test_cli_max_chars_flag_splits(tmp_path):
    src = tmp_path / "big.txt"
    src.write_text(
        " ".join(f"w{i}" for i in range(300)) + "\n",
        encoding="utf-8")
    out = tmp_path / "big.json"
    r = _cli("parse", str(src), "-o", str(out),
             "--parser", "text", "--max-chars", "100")
    assert r.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    lens = [len(c["text"]) for c in data["chunks"]]
    assert len(lens) == 14
    assert all(n <= 100 for n in lens)
    assert data["chunks"][0]["metadata"]["max_chars"] == 100
