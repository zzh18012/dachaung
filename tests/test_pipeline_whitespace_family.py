r"""pipeline 空白家族：CRLF/制表符/不间断空格/
BOM（Round 1622）。

新角度：R1621 锁实体（&nbsp;→\\xa0）——**\\xa0、
\\t 作为词界、CRLF 归一、BOM 保留**零覆盖：

- **CRLF 归一**：\\r\\n → \\n（CR 剥除），空行
  分段不受影响
- **\\xa0 与 \\t 均为完整词界**：拆分缝隙为
  该空白字符本身（35 字符 @32 → 31/3 与 32/2）
- **BOM 不剥离**：\\ufeff 进入段落内容开头
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, data, mc=800):
    p = tmp_path / name
    if isinstance(data, bytes):
        p.write_bytes(data)
    else:
        p.write_text(data, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False,
        parser_name="text", max_chars=mc)
    assert errors == []
    return doc


def test_crlf_normalized(tmp_path):
    doc = _run(
        tmp_path, "c.txt",
        b"para one.\r\nstill one.\r\n"
        b"\r\npara two.\r\n")
    assert [e.content
            for e in doc.elements] == [
        "para one.\nstill one.", "para two."]


def test_nbsp_tab_boundaries(tmp_path):
    nbsp_text = "a\xa0" * 17 + "a"
    doc = _run(
        tmp_path, "n.txt", nbsp_text + "\n",
        mc=32)
    c1, c2 = doc.chunks
    assert len(c1.text) == 31
    assert len(c2.text) == 3
    assert c2.text == "a\xa0a"

    tab_text = "aa\t" * 11 + "aa"
    doc2 = _run(
        tmp_path, "t.txt", tab_text + "\n",
        mc=32)
    d1, d2 = doc2.chunks
    assert (len(d1.text),
            len(d2.text)) == (32, 2)
    assert d2.text == "aa"
    assert "\t" in d1.text


def test_bom_not_stripped(tmp_path):
    doc = _run(
        tmp_path, "b.txt",
        b"\xef\xbb\xbfBOM text here.\n")
    assert [e.content
            for e in doc.elements] == [
        "﻿BOM text here."]
