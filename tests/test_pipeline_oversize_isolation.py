r"""pipeline 超限元素隔离：切分块不吸邻
与尾部重组（Round 1767）。

新角度：R1766 锁混型链——**1019 字符巨
段切 799/219 后：前邻 'a'、后邻 'b' 都
不并入任何切分块；巨段后的两个小段重组
新链 'b c'（2 ids）；标题+巨段+列表组
合四块各 1 id**零覆盖：

- **'a'+巨+'b'**：1/799/219/1 四块
- **巨+'b'+'c'**：799/219/'b c'（2）
- **'## T'+巨+'- x'**：'T'/799/219/
  'x' 四块
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single

BIG = " ".join(f"w{i}" for i in range(226))
assert len(BIG) == 1019


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_neighbors_never_join_splits(tmp_path):
    doc, errors = _run(
        tmp_path, "a\n\n" + BIG + "\n\nb\n")
    assert errors == []
    assert [(len(c.text), len(c.source_element_ids),
             c.text[:1]) for c in doc.chunks] == [
        (1, 1, "a"), (799, 1, "w"),
        (219, 1, "w"), (1, 1, "b")]


def test_trailing_smalls_form_new_chain(tmp_path):
    doc, errors = _run(
        tmp_path, BIG + "\n\nb\n\nc\n")
    assert errors == []
    assert [(len(c.text), len(c.source_element_ids))
            for c in doc.chunks] == [
        (799, 1), (219, 1), (3, 2)]
    assert doc.chunks[2].text == "b c"


def test_heading_big_list_four_chunks(tmp_path):
    doc, errors = _run(
        tmp_path, "## T\n\n" + BIG + "\n\n- x\n")
    assert errors == []
    assert [(len(c.text), len(c.source_element_ids),
             c.text[:1]) for c in doc.chunks] == [
        (1, 1, "T"), (799, 1, "w"),
        (219, 1, "w"), (1, 1, "x")]
