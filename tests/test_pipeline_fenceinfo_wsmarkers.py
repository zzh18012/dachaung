r"""fence info 前导空白剥离 + 标记分隔 \\s + section_path 保 NBSP（Round 1865）。

新角度（probe 实证；'``` py' 带空格 info、U+3000 分隔列表、
'>\\t' bq、section_path 含 NBSP 全库零覆盖；空 heading 静默跳
过复核弃用——edges13:37 已锁 '<h2></h2>' 同终点）：
- **fence info 前导空白剥离**：'``` py' / '```  py'（多空格）/
  '```\\u3000py'（全角）→ language 全部 'py'（前导 \\s 整体剥）
- **标记分隔 \\s 族**：'1.\\tfirst' / '1.\\u3000first' →
  ordered list_item 'first'；'+\\tplus' → unordered；
  '>\\tq' → blockquote 'q'
- **section_path 保 NBSP**：'<h1>T\\xa0U</h1>' → 后续段落
  section_path 'T\\xa0U' 逐字（NBSP 不在路径里折叠/剥离）
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single

NB = chr(0xA0)
WIDE = chr(0x3000)


def _run(tmp_path: Path, name: str, body: str, parser: str = "markdown"
         ) -> dict:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / (name + ".json")
    _, errs = process_single(p, out, parser_name=parser)
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_fence_info_leading_ws_stripped(tmp_path: Path):
    fence = "x=1\n```\n"
    for name, prefix in (("g.md", "``` py\n"), ("h.md", "```  py\n"),
                         ("i.md", "```" + WIDE + "py\n")):
        data = _run(tmp_path, name, prefix + fence)
        assert [(e["type"], e["content"], e["metadata"])
                for e in data["elements"]] == [
            ("paragraph", "x=1", {"kind": "code_block", "language": "py"})
        ], name


def test_marker_separators_s_family(tmp_path: Path):
    data = _run(tmp_path, "j.md", "1.\tfirst\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("list_item", "first", {"ordered": True, "marker": "ordered"})]

    data = _run(tmp_path, "k.md", "1." + WIDE + "first\n")
    assert [(e["type"], e["content"]) for e in data["elements"]] == [
        ("list_item", "first")]

    data = _run(tmp_path, "l.md", "+\tplus\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("list_item", "plus", {"ordered": False, "marker": "unordered"})]

    data = _run(tmp_path, "m.md", ">\tq\n")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("paragraph", "q", {"kind": "blockquote"})]


def test_section_path_keeps_nbsp(tmp_path: Path):
    data = _run(tmp_path, "n.html",
                "<h1>T" + NB + "U</h1><p>b</p>", parser="html")
    assert data["elements"][1]["source_locator"]["section_path"] == \
        "T" + NB + "U"
