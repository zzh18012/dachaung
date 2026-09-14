r"""img 在表行间静默丢弃 + image 承接 section_path（Round 1879）。

新角度（probe 实证，grep 零覆盖；R1877/78 锁 img 冲刷结构类型，
本批锁 img 在**表行之间**与 image 的 **section_path** 承接）：
- **行间 img 静默丢弃**：'<tr>a</tr><img ...><tr>b</tr>' → 单个
  表 row_count 2，img 元素消失（与 td 内 img 丢弃同终点、不同
  位置）
- **连续 img**：'<p><img><img>t</p>' → 两个 image + paragraph
  't'（每个 img 独立冲刷，不合并）
- **image 承接路径**：'<h1>T<img ...></h1><p>b</p>' →
  heading 'T' + image（section_path 'T'）+ 段落 'b'（'T'）
  ——img 不中断路径栈，image 元素自身也带路径
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


def test_img_between_rows_silently_dropped(tmp_path: Path):
    data = _run(tmp_path,
                '<table><tr><td>a</td></tr>'
                '<img src="u.png" alt="x">'
                "<tr><td>b</td></tr></table>")
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("table", "| a |\n| --- |\n| b |",
         {"row_count": 2, "col_count": 1,
          "source": "html_table"})]


def test_consecutive_images_each_flush(tmp_path: Path):
    data = _run(tmp_path,
                '<p><img src="u.png" alt="1">'
                '<img src="v.png" alt="2">t</p>')
    assert [(e["type"], e["content"], e["metadata"])
            for e in data["elements"]] == [
        ("image", None, {"alt": "1"}),
        ("image", None, {"alt": "2"}),
        ("paragraph", "t", {}),
    ]


def test_image_carries_section_path(tmp_path: Path):
    data = _run(tmp_path,
                '<h1>T<img src="u.png" alt="i"></h1><p>b</p>')
    assert [(e["type"], e["content"])
            for e in data["elements"]] == [
        ("heading", "T"), ("image", None), ("paragraph", "b")]
    assert [e["source_locator"]["section_path"]
            for e in data["elements"]] == ["T", "T", "T"]
