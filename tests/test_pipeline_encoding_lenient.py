r"""pipeline 非 UTF-8 输入的宽容解码（Round 1625）。

新角度：R1624 锁 BOM/CRLF——**编码错误从不抛出**
零覆盖（此前全部测试用 UTF-8）：

- **UTF-16 文件不报错**：BOM 两字节成两个
  替换符，内容成 'h\\x00e\\x00l\\x00…' 的
  NUL 交错形态，仍单段落
- **latin-1 高位字节 → \\ufffd 替换**：无
  encoding 错误码，结构识别不受影响（md
  heading 仍识别）
- **解码为 errors='replace' 语义**：字节级
  损坏只产生 U+FFFD，不失败
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single

REPL = chr(0xFFFD)


def _run(tmp_path, name, data, parser):
    p = tmp_path / name
    p.write_bytes(data)
    return process_single(
        p, write_json=False, parser_name=parser)


def test_utf16_lenient(tmp_path):
    raw = "hello world\n".encode("utf-16")
    doc, errors = _run(
        tmp_path, "u.txt", raw, "text")
    assert errors == []
    expected = (REPL * 2
                + "".join(ch + "\x00"
                          for ch in "hello world\n"))
    assert [e.content
            for e in doc.elements] == [
        expected]


def test_latin1_replacement(tmp_path):
    doc, errors = _run(
        tmp_path, "l.txt",
        "café naïve\n".encode("latin-1"),
        "text")
    assert errors == []
    assert [e.content
            for e in doc.elements] == [
        "caf" + REPL + " na"
        + REPL + "ve"]

    doc2, errors2 = _run(
        tmp_path, "m.md",
        "# café\n".encode("latin-1"),
        "markdown")
    assert errors2 == []
    assert [(e.type, e.content, e.metadata)
            for e in doc2.elements] == [
        ("heading", "caf" + REPL,
         {"level": 1})]
