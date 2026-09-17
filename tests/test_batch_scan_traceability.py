"""r55 C09/C10：批量扫描通道的可观测性与误导性失败修复。

- C09：目录扫描的排除项（.txt/.log 等不支持后缀）此前在 summary 与
  JSONL 零痕迹；现在逐项发 file_skipped 事件 + summary["skipped"] 记录
- C10：形如 *.md 的目录名此前通过后缀过滤被派发，以误导性的
  file_not_found（"输入文件不存在"）失败；现在扫描期排除 + 留痕
  （目录/glob 两通道同守卫）
"""

from __future__ import annotations

import json
from pathlib import Path

from app.batch import batch_parse_files
from app.cli import main as app_main


def _write_md(directory: Path, name: str, marker: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    p = directory / name
    p.write_text(f"# 标题 {name}\n\n正文 {marker}。\n", encoding="utf-8")
    return p


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ---------- C09：目录扫描排除留痕 ----------


def test_directory_scan_skips_leave_trace(tmp_path: Path, capsys):
    docs = tmp_path / "docs"
    _write_md(docs, "a.md", "A")
    _write_md(docs, "b.md", "B")
    (docs / "notes.txt").write_text("plain text", encoding="utf-8")
    (docs / "debug.log").write_text("log line", encoding="utf-8")
    out = tmp_path / "out"
    log_file = tmp_path / "out" / "batch.jsonl"

    rc = app_main(
        ["batch-parse", str(docs), "-o", str(out), "--log-file", str(log_file)]
    )
    assert rc == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["total"] == 2
    assert summary["success"] == 2
    assert summary["failed"] == 0
    assert {
        (s["file"], s["reason"]) for s in summary["skipped"]
    } == {
        (str(docs / "notes.txt"), "unsupported_suffix"),
        (str(docs / "debug.log"), "unsupported_suffix"),
    }
    # JSONL：逐项 file_skipped 事件 + batch_start.skipped_count
    events = _read_jsonl(log_file)
    skip_events = [e for e in events if e["event"] == "file_skipped"]
    assert sorted(e["file"] for e in skip_events) == sorted(
        [str(docs / "notes.txt"), str(docs / "debug.log")]
    )
    assert all(e["reason"] == "unsupported_suffix" for e in skip_events)
    start = next(e for e in events if e["event"] == "batch_start")
    assert start["skipped_count"] == 2
    # 终行含排除计数
    captured = capsys.readouterr()
    assert "排除 2 项" in captured.out


def test_directory_scan_only_unsupported_rc2_details(tmp_path: Path, capsys):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "only.txt").write_text("x", encoding="utf-8")
    rc = app_main(["batch-parse", str(docs), "-o", str(tmp_path / "o")])
    assert rc == 2
    captured = capsys.readouterr()
    assert "未找到可解析文件" in captured.err
    # 零痕迹修复：排除原因计数随错误信息输出
    assert "unsupported_suffix=1" in captured.err


# ---------- C10：形如 *.md 的目录名 ----------


def test_directory_named_md_not_dispatched(tmp_path: Path):
    docs = tmp_path / "docs"
    _write_md(docs, "real.md", "REAL")
    (docs / "trap.md").mkdir()  # 目录名带 .md 后缀
    out = tmp_path / "out"

    rc = app_main(["batch-parse", str(docs), "-o", str(out)])
    assert rc == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["total"] == 1
    assert summary["success"] == 1
    # 此前：trap.md 被派发 → file_not_found（"输入文件不存在"措辞误导）
    assert summary["failed"] == 0
    assert [
        (s["file"], s["reason"]) for s in summary["skipped"]
    ] == [(str(docs / "trap.md"), "not_a_regular_file")]


def test_glob_channel_directory_named_md_guarded(tmp_path: Path):
    docs = tmp_path / "docs"
    _write_md(docs, "real.md", "REAL")
    (docs / "trap.md").mkdir()
    out = tmp_path / "out"

    rc = app_main(
        ["batch-parse", str(docs / "*.md"), "-o", str(out)]
    )
    assert rc == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["total"] == 1
    assert summary["success"] == 1
    assert [
        (s["file"], s["reason"]) for s in summary["skipped"]
    ] == [(str(docs / "trap.md"), "not_a_regular_file")]


# ---------- API 默认值回归 ----------


def test_batch_parse_files_skipped_defaults_empty(tmp_path: Path):
    docs = tmp_path / "docs"
    f = _write_md(docs, "solo.md", "S")
    summary = batch_parse_files([f], tmp_path / "out", workers=1)
    assert summary["skipped"] == []
    assert summary["total"] == 1
    assert summary["success"] == 1
