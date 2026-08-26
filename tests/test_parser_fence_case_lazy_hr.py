r"""parser fence 语言原样大小写、bq 懒
续行不识别、hr 星号变体丢弃
（Round 1832）。

新角度：R1831 锁家族统一切分——**
'```PyThon' 语言原样存 'PyThon' 不
小写化；'> a' 后无标记行 'b' 是独立
paragraph（懒续行不合并）；'***'
单置 → hr 丢弃 → no_extracted_
elements，混排时静默消失**零覆盖：

- **语言原样**：'PyThon' 不归一
- **懒续行**：bq 'a' + para 'b' 分裂
- **hr 星号**：单置报空/混排消失
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_fence_language_raw_case(tmp_path):
    doc, errors = _run(tmp_path, "```PyThon\nx\n```\n")
    assert errors == []
    assert doc.elements[0].metadata == {
        "kind": "code_block", "language": "PyThon"}


def test_bq_lazy_continuation_split(tmp_path):
    doc, errors = _run(tmp_path, "> a\nb\n")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a", {"kind": "blockquote"}),
        ("paragraph", "b", {})]


def test_hr_star_variant_dropped(tmp_path):
    doc, errors = _run(tmp_path, "***\n")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    doc, errors = _run(tmp_path, "***\n\npara\n")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "para")]
