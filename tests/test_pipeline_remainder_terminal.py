r"""pipeline 切分余块终结性：不吸后续短元
素；标题不拉超限元素（Round 1801）。

新角度：R1800 锁极限参数——**'好'*801
切 800+1 后，后随 '乙' 不并入 1 字余块
——自起 sequential 链（余块终结、吸邻
禁止在块级延续）；'好'*799+'乙' 合并后
801 超限故两块；'## A'+巨段+'## B'：
'A' 独块（标题不拉超限元素）、'B tail'
新链、元素路径 [A,A,B,B]（标题路径含
自身）**零覆盖：

- **801+乙**：800/1/乙(sequential) 三块
- **799+乙**：799+1 两块不合并
- **A巨B**：A 独块、B tail 拉取
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_cjk_801_remainder_terminal(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("好" * 801 + "\n\n乙\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"])
            for c in doc.chunks] == [
        (800, "long_paragraph_sentence_split"),
        (1, "long_paragraph_sentence_split"),
        (1, "sequential")]


def test_cjk_799_plus_short_no_join(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("好" * 799 + "\n\n乙\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"],
             len(c.source_element_ids))
            for c in doc.chunks] == [
        (799, "sequential", 1),
        (1, "sequential", 1)]


def test_heading_never_pulls_oversize(tmp_path):
    big = " ".join(f"w{i}" for i in range(226))
    p = tmp_path / "d.md"
    p.write_text(
        "## A\n\n" + big + "\n\n## B\n\ntail\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(c.text[:6], c.metadata["strategy"])
            for c in doc.chunks] == [
        ("A", "sequential"),
        ("w0 w1 ", "long_paragraph_sentence_split"),
        ("w182 w", "long_paragraph_sentence_split"),
        ("B tail", "sequential")]
    assert [e.source_locator["section_path"]
            for e in doc.elements] == ["A", "A",
                                       "B", "B"]
