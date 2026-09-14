r"""数字实体三向分裂：静默丢弃 / 字面控制符 / U+FFFD（Round 1856）。

新角度（probe 实证，grep 核实零覆盖——既有实体测试只锁
&#65;/&#x41;/&#x1F600;/&#128512; 解码与 &#0; → U+FFFD，
控制符丢弃、非字符丢弃、CR/LF/TAB 字面透传无覆盖）：
- **静默丢弃**：'&#1;'（Cc 控制）与 '&#x10FFFF;'（非字符）
  → content 'ab' 零错误——**不是** U+FFFD，与 &#0; → U+FFFD
  （wsli_nullentity 已锁）形成同族三向分裂
- **字面控制符**：'&#9;'/'&#10;'/'&#xD;' → '\t'/'\n'/'\r' 逐字
  保留在 content——实体 LF **不拆段**（一个 paragraph 含 \n）
- **安全半边**：'&#xD800;'（代理区）/ '&#1114113;'（超平面）
  → U+FFFD——unescape 已消毒，**不产生** lone surrogate（与
  R1854/R1855 JSON 转义通道的写盘 UnicodeEncodeError 对照）
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single

FFFD = chr(0xFFFD)


def _run(tmp_path: Path, name: str, body: str) -> dict:
    p = tmp_path / name
    p.write_text(f"<p>{body}</p>", encoding="utf-8")
    out = tmp_path / (name + ".json")
    _, errs = process_single(p, out, parser_name="html")
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_numentity_control_and_nonchar_dropped(tmp_path: Path):
    for body in ("a&#1;b", "a&#x10FFFF;b"):
        data = _run(tmp_path, "d.html", body)
        assert data["elements"][0]["content"] == "ab", body


def test_numentity_ctl_chars_verbatim(tmp_path: Path):
    for body, want in (("a&#9;b", "a\tb"), ("a&#10;b", "a\nb"),
                       ("a&#xD;b", "a\rb")):
        data = _run(tmp_path, "e.html", body)
        elems = data["elements"]
        assert len(elems) == 1, (body, len(elems))
        assert elems[0]["type"] == "paragraph"
        assert elems[0]["content"] == want, body


def test_numentity_surrogate_and_beyond_fffd(tmp_path: Path):
    for body in ("a&#xD800;b", "a&#1114113;b"):
        data = _run(tmp_path, "f.html", body)
        assert data["elements"][0]["content"] == f"a{FFFD}b", body
