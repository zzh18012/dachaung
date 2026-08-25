r"""pipeline 拆分精度：引号/括号内句号、缩写、
换行边界（Round 1616）。

新角度：R1615 锁句界字符集——**句号后跟非空格
字符、缩写无感知、换行非句界**零覆盖：

- **句号在引号/括号内不是句界**（'now."',
  'note.)'）→ 落回词界拆分，句子完整保留
- **缩写无感知**：'Dr. ' 与 'End. ' 拆分结果
  完全一致（['Dr.', A×32, 'AAA']，无空格尾巴
  硬切 32/3）
- **换行不是句界只是普通字符**：跨行内容在
  空格处词界拆分，\\n 留在 chunk 内
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _chunks(tmp_path, name, text, mc=32):
    p = tmp_path / name
    p.write_text(text + "\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False,
        parser_name="text", max_chars=mc)
    assert errors == []
    return [c.text for c in doc.chunks]


def test_period_inside_punct(tmp_path):
    got = _chunks(
        tmp_path, "q.txt",
        'He said "go away now." '
        "Then left quickly.")
    assert got == [
        'He said "go away now." Then left',
        "quickly."]
    got2 = _chunks(
        tmp_path, "p.txt",
        "(See the note.) Then more text "
        "follows ok.")
    assert got2 == [
        "(See the note.) Then more text",
        "follows ok."]


def test_naive_abbreviation(tmp_path):
    dr = _chunks(
        tmp_path, "d.txt",
        "Dr. " + "A" * 35)
    ctl = _chunks(
        tmp_path, "c.txt",
        "End. " + "A" * 35)
    assert dr == ["Dr.", "A" * 32, "AAA"]
    assert ctl == ["End.", "A" * 32, "AAA"]


def test_newline_not_sentence_boundary(
        tmp_path):
    got = _chunks(
        tmp_path, "n.txt",
        "line one stays\nline two stays here")
    assert got == [
        "line one stays\nline two stays",
        "here"]
    assert "\n" in got[0]
