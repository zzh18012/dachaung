r"""p 标签畸形形态精确锁定：兄弟嵌开合并 / 多余闭合（Round 1870）。

新角度（probe 实证；edges.py:410 '<p>hello<p>world' 只断言
len>=1，edges3:677 '<p><p>text</p></p>' 只断言 >=1——**精确内容
与元素数从未锁定**；'</p>' 打头与纯多余闭合全库零覆盖）：
- **兄弟嵌开合并**：'a<p>b' 形 → 单 paragraph 'ab'（第二 <p>
  同 _cur_kind 被忽略，文本无分隔连续累积）
- **多余闭合无效**：'<p>a</p></p>' → 恰一个 paragraph 'a'；
  '</p>' 打头（无开标签）同样无副作用
- **未闭跑到 EOF**：'<p>abc' → 恰一个 paragraph 'abc'；
  'x<p>y'（文本先于 p）→ 合并 'xy'
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path: Path, body: str) -> dict:
    p = tmp_path / "a.html"
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / "a.json"
    _, errs = process_single(p, out, parser_name="html")
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_sibling_open_p_merges_text_exact(tmp_path: Path):
    for name, body in (("a", "<p>hello<p>world"),
                       ("b", "<p>a<p>b</p></p>"),
                       ("c", "x<p>y")):
        data = _run(tmp_path, body)
        assert [(e["type"], e["content"]) for e in data["elements"]] == \
            [("paragraph", {"a": "helloworld", "b": "ab", "c": "xy"}[name])]


def test_stray_close_noop(tmp_path: Path):
    data = _run(tmp_path, "<p>a</p></p>")
    assert [(e["type"], e["content"])
            for e in data["elements"]] == [("paragraph", "a")]

    data = _run(tmp_path, "</p><p>a</p>")
    assert [(e["type"], e["content"])
            for e in data["elements"]] == [("paragraph", "a")]


def test_unclosed_p_to_eof_exact(tmp_path: Path):
    data = _run(tmp_path, "<p>abc")
    assert [(e["type"], e["content"])
            for e in data["elements"]] == [("paragraph", "abc")]
    assert data["warnings"] == []
