r"""app/parsers/text_parser.py 边角测试 - 第十二轮（Round 1462）。

新角度（probe 实证）**非 LF 换行系字符全部不是行分隔**
（edges1-11 未碰过；证明实现按 \\n/\\r 切而非 str.splitlines）：
- \\v（0x0B）/ \\f（0x0C）/ NEL（0x85）/ LS（U+2028）/
  PS（U+2029）/ FS（0x1C）/ GS（0x1D）夹在文本中间 →
  **留在内容里**、行号 1、单 paragraph（splitlines 会切的
  这些字符这里都不切）
- 混合 'a\\vb\\fc' 同样一整段保留
- 但**整行只有 \\v** 时按"含空白的空行"算分隔行（strip 后
  空）且计入行号：'a\\n\\v\\nb' → b 在 line 3
- 内容里带真 \\n 时按多行段落 join（首行行号）：
  'x\\u2028\\n\\u2028y' → 单 paragraph 原样保留
- _split_paragraphs 直连：LS/VT/FS 文本各返回单 tuple
"""

from __future__ import annotations

from app.hash import compute_file_hash
from app.parsers.text_parser import \
    TextParser, _split_paragraphs

TMP_NAME = "txt_edge12_probe.txt"
LS = chr(0x2028)
PS = chr(0x2029)


def _parse(tmp_path, data, name=TMP_NAME):
    p = tmp_path / name
    if isinstance(data, str):
        data = data.encode("utf-8")
    p.write_bytes(data)
    return TextParser().parse(
        p, compute_file_hash(p))


def _one_content(tmp_path, text):
    doc = _parse(tmp_path, text)
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.source_locator == \
        {"family": "line_address", "line": 1}
    return e.content


# ---------- 控制字符留在内容 ----------

def test_vt_not_line_break(tmp_path):
    assert _one_content(
        tmp_path, "a\vb") == "a\vb"


def test_ff_not_line_break(tmp_path):
    assert _one_content(
        tmp_path, "a\fb") == "a\fb"


def test_nel_not_line_break(tmp_path):
    assert _one_content(
        tmp_path, "a\x85b") == "a\x85b"


def test_ls_not_line_break(tmp_path):
    assert _one_content(
        tmp_path, "a" + LS + "b") \
        == "a" + LS + "b"


def test_ps_not_line_break(tmp_path):
    assert _one_content(
        tmp_path, "a" + PS + "b") \
        == "a" + PS + "b"


def test_fs_gs_not_line_break(
        tmp_path):
    assert _one_content(
        tmp_path, "a\x1cb") == "a\x1cb"
    assert _one_content(
        tmp_path, "a\x1db") == "a\x1db"


def test_mixed_separators_kept(
        tmp_path):
    assert _one_content(
        tmp_path, "a\vb\fc") \
        == "a\vb\fc"


# ---------- 整行 \v 是空行 ----------

def test_lone_vt_line_is_blank(
        tmp_path):
    doc = _parse(
        tmp_path, "a\n\v\nb")
    assert [(e.content,
             e.source_locator["line"])
            for e in doc.elements] == [
        ("a", 1), ("b", 3),
    ]


# ---------- 真换行 + LS 混合 ----------

def test_ls_around_real_newline_join(
        tmp_path):
    doc = _parse(
        tmp_path,
        "x" + LS + "\n" + LS + "y")
    assert len(doc.elements) == 1
    assert doc.elements[0].content \
        == "x" + LS + "\n" + LS + "y"
    assert doc.elements[
        0].source_locator == {"family": "line_address", "line": 1}


# ---------- _split_paragraphs 直连 ----------

def test_split_exotic_single_tuple():
    assert _split_paragraphs(
        "a\vb") == [(1, "a\vb")]
    assert _split_paragraphs(
        "a\x1cb") == [(1, "a\x1cb")]
    assert _split_paragraphs(
        "a" + LS + "b") == \
        [(1, "a" + LS + "b")]
