r"""app/pipeline.py + app/cli.py markdown 崩溃遏制测试（Round 1485）。

背景：R1484 发现 markdown_parser 对 '#   \\n'（纯 '#' +
空白、空标题文本）抛 ValueError 穿透 parse（非
ParserError）。本轮锁**管线级遏制不变量**（CLAUDE.md：
"单文件失败 → 结构化 errors JSON + 非零退出码，不崩溃"）：

- **process_single 遏制**：doc=None + 单条
  unexpected_parser_error，message 以 'ValueError:' 开头、
  details 带 path 与 parser_name='markdown'
- **CLI 遏制**：main(['parse', ...]) 返回 1、不写
  output JSON

若未来修复 markdown_parser（空标题跳过），这两个测试将
失败——届时应替换为"空标题被跳过"的正向锁定。
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single


def _crash_md(tmp_path):
    p = tmp_path / "crash.md"
    p.write_text("#   \nbody\n",
                 encoding="utf-8")
    return p


def test_process_single_contains_md_crash(
        tmp_path):
    p = _crash_md(tmp_path)
    doc, errors = process_single(
        p, parser_name="markdown")
    assert doc is None
    assert len(errors) == 1
    e = errors[0]
    assert e.code == \
        "unexpected_parser_error"
    assert e.message.startswith(
        "ValueError:")
    assert e.details["parser_name"] \
        == "markdown"
    assert e.details["path"] == str(p)


def test_cli_md_crash_exit_1_no_output(
        tmp_path, capsys):
    from app.cli import main
    p = _crash_md(tmp_path)
    out = tmp_path / "out.json"
    rc = main(["parse", str(p),
               "-o", str(out),
               "--parser", "markdown"])
    assert rc == 1
    assert not out.exists()
    captured = capsys.readouterr()
    printed = json.loads(
        captured.out + captured.err)
    assert printed["errors"][0][
        "code"] == \
        "unexpected_parser_error"
