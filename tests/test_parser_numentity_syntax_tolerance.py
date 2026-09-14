r"""数字实体语法容忍：大写 X / 无分号 / 前导零 / 空十六进制（Round 1866）。

新角度（probe 实证，grep 核实 '&#X'/'&#65 '/'&#065'/'&#x;' 全库
零覆盖——既有实体测试全用规范小写 x + 分号形态）：
- **大写 X**：'&#X41;' → 'A'（xX 都接受）
- **无分号**：'a&#65 b' → 'aA b'（数字实体缺 ';' 照常解码；
  命名实体无分号已锁 &copy——数字形态是另一条路径）
- **空十六进制**：'z&#x;' → **字面保留** 'z&#x; empty'（无数字
  不匹配 charref RE，不解码不丢弃）
- **前导零**：'&#065;' → 'A'（int() 容忍补零）
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path: Path, body: str) -> str:
    p = tmp_path / "a.html"
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / "a.json"
    _, errs = process_single(p, out, parser_name="html")
    assert errs == []
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["elements"]) == 1
    return data["elements"][0]["content"]


def test_numentity_uppercase_x_and_leading_zero(tmp_path: Path):
    assert _run(tmp_path, "<p>&#X41; up</p>") == "A up"
    assert _run(tmp_path, "<p>&#065; pad</p>") == "A pad"


def test_numentity_missing_semicolon_decoded(tmp_path: Path):
    assert _run(tmp_path, "<p>a&#65 b</p>") == "aA b"


def test_numentity_empty_hex_literal(tmp_path: Path):
    assert _run(tmp_path, "<p>z&#x; empty</p>") == "z&#x; empty"
