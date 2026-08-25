r"""pipeline 失败路径输出不变式与句界补充（Round 1617）。

新角度：R1616 锁拆分精度——**失败时绝不落盘**
与**省略号/小写句界**零覆盖：

- **失败不写 JSON**：chunker_failed /
  no_extracted_elements 时 output_path 文件不
  创建；**已有旧文件原样保留**（写盘仅发生在
  成功路径）
- **省略号单边界**：'Wait...' 整体一个句尾
  （非 'Wait.' + '..'）
- **小写句界**：'stop. next' 句号后小写同样切
  （无大写要求）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_no_json_written_on_failure(tmp_path):
    p = tmp_path / "f.md"
    p.write_text("hello\n", encoding="utf-8")
    out = tmp_path / "f.json"
    doc, errors = process_single(
        p, output_path=out,
        parser_name="markdown", max_chars=10)
    assert doc is None
    assert [e.code for e in errors] == [
        "chunker_failed"]
    assert not out.exists()

    empty = tmp_path / "e.md"
    empty.write_text("", encoding="utf-8")
    out2 = tmp_path / "e.json"
    doc2, errors2 = process_single(
        empty, output_path=out2,
        parser_name="markdown")
    assert doc2 is None
    assert [e.code for e in errors2] == [
        "no_extracted_elements"]
    assert not out2.exists()


def test_existing_output_untouched(tmp_path):
    p = tmp_path / "f.md"
    p.write_text("hello\n", encoding="utf-8")
    out = tmp_path / "f.json"
    out.write_text('{"old": true}',
                   encoding="utf-8")
    doc, errors = process_single(
        p, output_path=out,
        parser_name="markdown", max_chars=10)
    assert [e.code for e in errors] == [
        "chunker_failed"]
    assert (out.read_text(encoding="utf-8")
            == '{"old": true}')


def test_ellipsis_lowercase_boundaries(
        tmp_path):
    def chunks(name, text):
        f = tmp_path / name
        f.write_text(text + "\n",
                     encoding="utf-8")
        d, e = process_single(
            f, write_json=False,
            parser_name="text", max_chars=32)
        assert e == []
        return [c.text for c in d.chunks]

    assert chunks("e.txt",
                  "Wait... " + "B" * 35) == [
        "Wait...", "B" * 32, "BBB"]
    assert chunks("l.txt",
                  "stop. " + "B" * 35) == [
        "stop.", "B" * 32, "BBB"]
