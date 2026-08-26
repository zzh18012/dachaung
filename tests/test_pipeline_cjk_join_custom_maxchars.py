r"""pipeline CJK 元素拼接加空格与自定义
max_chars 拉段（Round 1747）。

新角度：R1746 锁家族 locator——**CJK 元
素间拼接恒加半角空格（'标 内容甲 内容
乙'）；超长 CJK 段同样 800 forced_char
且标题不沾切分块；max_chars=100 时拉段
边界随参数移动（99 合并/101 分开）且
metadata 记录 max_chars: 100**零覆盖：

- **'## 标\\n\\n内容甲\\n\\n内容乙'**：
  单 chunk '标 内容甲 内容乙'（3 ids）
- **'## 标'+'好'×900**：'标'（1 id）+
  800 forced_char + 100
- **max_chars=100**：798 字符版 97 段 →
  99 合并（2 ids）；99 段 → 'T'+99 分开
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, **kw):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown", **kw)


def test_cjk_elements_join_with_space(tmp_path):
    doc, errors = _run(
        tmp_path, "## 标\n\n内容甲\n\n内容乙\n")
    assert errors == []
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [
        ("标 内容甲 内容乙", 3)]


def test_cjk_oversize_para_heading_separate(tmp_path):
    doc, errors = _run(
        tmp_path, "## 标\n\n" + "好" * 900 + "\n")
    assert errors == []
    assert [(len(c.text), len(c.source_element_ids),
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (1, 1, None), (800, 1, "forced_char"),
        (100, 1, None)]


def test_custom_maxchars_pull_boundary(tmp_path):
    p97 = " ".join(["ab"] * 32 + ["a"])
    p99 = " ".join(["ab"] * 32 + ["abc"])
    assert (len(p97), len(p99)) == (97, 99)
    doc, errors = _run(
        tmp_path, "## T\n\n" + p97 + "\n", max_chars=100)
    assert errors == []
    assert [(len(c.text), len(c.source_element_ids))
            for c in doc.chunks] == [(99, 2)]
    doc, errors = _run(
        tmp_path, "## T\n\n" + p99 + "\n", max_chars=100)
    assert errors == []
    assert [(len(c.text), len(c.source_element_ids))
            for c in doc.chunks] == [(1, 1), (99, 1)]
    assert doc.chunks[0].metadata["max_chars"] == 100
