r"""pipeline 语义容器透明与 CR 字节精确性
（Round 1658）。

新角度：R1657 锁连续表/img——**main 等
六种语义容器透明、精确 \\r\\n 与畸形 \\r\\r\\n
的家族一致行为**零覆盖：

- **六种语义容器**：main/article/header/
  footer/nav/aside 与 div/section 一致透明
- **精确 CRLF 字节（write_bytes）**：text
  与 md 都合并连续行 'para one.\\nstill
  one.'（CR 剥除、空行分段）
- **畸形 '\\r\\r\\n'（双 CR）**：每个孤立 \\r
  都是分隔符 → 成空白行 → 逐行各成段
  （两家族行为一致）；教训：write_text 在
  Windows 会把字符串里 \\r\\n 再翻译成
  \\r\\r\\n，测 CRLF 必须 write_bytes
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_semantic_wrappers_transparent(tmp_path):
    for tag in ("main", "article", "header",
                "footer", "nav", "aside"):
        p = tmp_path / "d.html"
        p.write_text(
            f"<{tag}><p>x</p></{tag}>",
            encoding="utf-8")
        doc, errors = process_single(
            p, write_json=False, parser_name="html")
        assert errors == [], tag
        assert [(e.type, e.content)
                for e in doc.elements] == [
            ("paragraph", "x")], tag


def test_exact_crlf_merged_both_families(
        tmp_path):
    data = (b"para one.\r\nstill one.\r\n"
            b"\r\npara two.")
    for suffix, parser in [
            (".txt", "text"), (".md", "markdown")]:
        p = tmp_path / ("d" + suffix)
        p.write_bytes(data)
        doc, errors = process_single(
            p, write_json=False, parser_name=parser)
        assert errors == [], suffix
        assert [(e.type, e.content)
                for e in doc.elements] == [
            ("paragraph", "para one.\nstill one."),
            ("paragraph", "para two.")], suffix


def test_doubled_cr_splits_both_families(
        tmp_path):
    data = (b"para one.\r\r\nstill one.\r\r\n"
            b"\r\r\npara two.")
    for suffix, parser in [
            (".txt", "text"), (".md", "markdown")]:
        p = tmp_path / ("d" + suffix)
        p.write_bytes(data)
        doc, errors = process_single(
            p, write_json=False, parser_name=parser)
        assert errors == [], suffix
        assert [(e.type, e.content)
                for e in doc.elements] == [
            ("paragraph", "para one."),
            ("paragraph", "still one."),
            ("paragraph", "para two.")], suffix
