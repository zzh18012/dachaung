r"""pipeline max_chars 变体类型：float 限内
可行/切分即败、bool ValueError、None
TypeError（Round 1818）。

新角度：R1817 锁行号——**float 800.5：
限内文档正常合并 'aaa bbb'（仅比较）；
一旦需要切分 → chunker_failed
TypeError（切片要 int）；True/False →
ValueError（按 1/0 判过小）；None →
TypeError（比较即败）**零覆盖：

- **800.5 限内**：正常合并
- **800.5 需切分**：chunker_failed
- **True/False/None**：三型各归其位
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_float_maxchars_under_limit_ok(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("aaa\n\nbbb\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text",
        max_chars=800.5)
    assert errors == []
    assert [c.text for c in doc.chunks] == [
        "aaa bbb"]


def test_float_maxchars_split_fails(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("字" * 900 + "\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text",
        max_chars=800.5)
    assert doc is None
    assert len(errors) == 1
    assert errors[0].code == "chunker_failed"
    assert errors[0].details[
        "exception_type"] == "TypeError"


def test_bool_none_maxchars(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("aaa\n\nbbb\n", encoding="utf-8")
    for mc, want in [(True, "ValueError"),
                     (False, "ValueError"),
                     (None, "TypeError")]:
        doc, errors = process_single(
            p, write_json=False, parser_name="text",
            max_chars=mc)
        assert doc is None, mc
        assert errors[0].code == "chunker_failed"
        assert errors[0].details[
            "exception_type"] == want
