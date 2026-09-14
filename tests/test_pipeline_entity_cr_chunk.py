r"""html 实体 \r 存活到 chunk 切分 + 孤立源 \r 转 \n + md 字面 forced 切（Round 1861）。

新角度（probe 实证；R1856 只锁 parser 层实体控制符、R1858 只锁
CRLF 剥离与 tags 间裸 CR 计行——实体 \r 进 chunker 作切分点、
**孤立源 \r 在文本内容里转 \n**、md 实体字面 forced 切全零覆盖）：
- **实体 \r 是 chunk 切分点**：'ab&#xD;'×30（html）→ content
  'ab\r'×29+'ab'（89 字符），@40 切 38/38/11——R1858 的源级
  CR 归一化碰不到实体解码产物
- **孤立 \r → \n**：'<p>a\\r b</p>' → content 'a\\n b'（文本内
  单个 \\r 归一成 \\n 而非剥离；CRLF→\\n 与 tags 间行为之外的
  第三种形态）
- **md 字面实体 forced 切**：'ab&#xD;'×30（md）→ 210 字符
  paragraph **原样**（md 不解实体），无任何空白 → forced_char
  恰 40 硬切（5×40+10），第二段以 'D;' 开头（**实体中间被切**）
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path: Path, name: str, parser: str, body: str,
         max_chars: int = 40) -> dict:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8", newline="")
    out = tmp_path / (name + ".json")
    _, errs = process_single(p, out, parser_name=parser,
                             max_chars=max_chars)
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_html_entity_cr_chunk_split_point(tmp_path: Path):
    data = _run(tmp_path, "a.html", "html",
                "<p>" + "ab&#xD;" * 30 + "</p>")
    assert data["elements"][0]["content"] == "ab\r" * 29 + "ab"
    assert [c["text"] for c in data["chunks"]] == [
        "ab\r" * 12 + "ab",
        "ab\r" * 12 + "ab",
        "ab\r" * 3 + "ab"]


def test_html_lone_cr_becomes_lf_in_content(tmp_path: Path):
    data = _run(tmp_path, "b.html", "html", "<p>a\r b</p>")
    assert data["elements"][0]["content"] == "a\n b"


def test_md_entity_literal_forced_char_split(tmp_path: Path):
    body = "ab&#xD;" * 30 + "\n"
    data = _run(tmp_path, "c.md", "markdown", body)
    assert data["elements"][0]["content"] == "ab&#xD;" * 30
    chunks = data["chunks"]
    assert [len(c["text"]) for c in chunks] == [40] * 5 + [10]
    assert chunks[1]["text"].startswith("D;ab")
