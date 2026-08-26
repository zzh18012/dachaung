r"""pipeline 句界无阈值：早句号即切微块；
whitespace 多路；超限判定前先 strip
（Round 1783）。

新角度：R1782 锁家族统一——**'S0. '+1019
词：句号在第 3 字符也照切（首块 3 字
'S0.'），余文回退 whitespace 799+219——
句界无"距 max_chars 最小距离"阈值；
纯词 2499 → 799×3+99 中间块全
'whitespace'；799 词+10 尾空格不切（判定
前先 strip）**零覆盖：

- **早句号**：3 / 799 whitespace / 219
- **纯词 2499**：799+799+799+99
- **尾空格 799+10**：单块 799 不切
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_early_sentence_boundary_no_threshold(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text(
        "S0. " + " ".join(f"w{j}" for j in range(226))
        + "\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(len(c.text), c.text,
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (3, "S0.", None),
        (799, " ".join(f"w{j}" for j in range(182)),
         "whitespace"),
        (219, " ".join(f"w{j}" for j in range(182, 226)),
         None)]


def test_whitespace_multiway(tmp_path):
    words = " ".join(f"w{i:03d}" for i in range(500))
    p = tmp_path / "d.txt"
    p.write_text(words + "\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(len(c.text),
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (799, "whitespace"), (799, "whitespace"),
        (799, "whitespace"), (99, None)]


def test_oversize_check_after_strip(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("w" * 799 + " " * 10 + "\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [len(c.text) for c in doc.chunks] == [799]
