"""r55 C12：--log-file 前置结构化校验。

目录/空串/不可写目标在批处理/评测启动前以 rc 2 拒绝（此前
setup_logger 的 FileHandler 裸 PermissionError/IsADirectoryError
traceback 穿透到用户）；合法目标（含需新建的嵌套父目录）保持
可用（回归守卫）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.cli import main as app_main
from app.jsonlog import LogFileInvalidError, verify_log_file_target
from evaluation.cli import main as eval_main


def _write_md(directory: Path, name: str, marker: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    p = directory / name
    p.write_text(f"# 标题 {name}\n\n正文 {marker}。\n", encoding="utf-8")
    return p


def _read_events(log_path: Path) -> list[dict]:
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines, "日志文件为空"
    return [json.loads(line) for line in lines]


# ---------- 单元：verify_log_file_target ----------


def test_verify_rejects_directory(tmp_path: Path):
    d = tmp_path / "adir"
    d.mkdir()
    with pytest.raises(LogFileInvalidError) as ei:
        verify_log_file_target(d)
    assert ei.value.code == "log_file_is_directory"
    assert "目录" in ei.value.message


def test_verify_rejects_empty_string(tmp_path: Path):
    # Path('') 归一为 '.'（cwd 目录）→ 按目录拒绝，不再落到
    # FileHandler 的隐晦 traceback
    with pytest.raises(LogFileInvalidError) as ei:
        verify_log_file_target("")
    assert ei.value.code == "log_file_is_directory"


def test_verify_rejects_unwritable(tmp_path: Path, monkeypatch):
    target = tmp_path / "sub" / "log.jsonl"

    def _denied(self: Path, *args, **kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "open", _denied)
    with pytest.raises(LogFileInvalidError) as ei:
        verify_log_file_target(target)
    assert ei.value.code == "log_file_unwritable"


def test_verify_accepts_valid_target_creates_parents(tmp_path: Path):
    target = tmp_path / "new" / "deep" / "batch.jsonl"
    result = verify_log_file_target(target)
    assert result == target
    # 与 setup_logger 同规则预建父目录 + append 试开一次
    assert target.parent.is_dir()
    assert target.is_file()


# ---------- CLI：batch-parse 启动前拒绝 ----------


def test_batch_parse_log_file_directory_rc2(tmp_path: Path, capsys):
    docs = tmp_path / "docs"
    _write_md(docs, "a.md", "A")
    out = tmp_path / "out"
    log_dir = tmp_path / "logsdir"
    log_dir.mkdir()

    rc = app_main(
        ["batch-parse", str(docs), "-o", str(out), "--log-file", str(log_dir)]
    )

    assert rc == 2
    captured = capsys.readouterr()
    assert "--log-file 不能是目录" in captured.err
    assert "Traceback" not in captured.err
    # 校验先于一切批处理动作：无 summary.json
    assert not (out / "summary.json").exists()


def test_batch_parse_log_file_empty_string_rc2(tmp_path: Path, capsys):
    docs = tmp_path / "docs"
    _write_md(docs, "a.md", "A")

    rc = app_main(
        ["batch-parse", str(docs), "-o", str(tmp_path / "o"), "--log-file", ""]
    )

    assert rc == 2
    captured = capsys.readouterr()
    assert "--log-file" in captured.err
    assert "Traceback" not in captured.err


def test_batch_parse_log_file_valid_nested_parents_rc0(tmp_path: Path):
    docs = tmp_path / "docs"
    _write_md(docs, "a.md", "A")
    out = tmp_path / "out"
    log_file = out / "logs" / "deep" / "batch.jsonl"

    rc = app_main(
        ["batch-parse", str(docs), "-o", str(out), "--log-file", str(log_file)]
    )

    # 需新建嵌套父目录的合法目标不受校验影响（回归守卫）
    assert rc == 0
    assert any(e["event"] == "batch_start" for e in _read_events(log_file))


# ---------- CLI：evaluation run 启动前拒绝 ----------


def test_evaluation_run_log_file_directory_rc2(tmp_path: Path, capsys):
    log_dir = tmp_path / "ldir"
    log_dir.mkdir()

    rc = eval_main(
        [
            "run",
            # 清单故意不存在：证明 log-file 校验先于清单存在性检查
            "--manifest",
            str(tmp_path / "no-such-manifest.json"),
            "--output",
            str(tmp_path / "r.json"),
            "--log-file",
            str(log_dir),
        ]
    )

    assert rc == 2
    captured = capsys.readouterr()
    assert "--log-file 不能是目录" in captured.err
    assert "Traceback" not in captured.err
    assert "清单不存在" not in captured.err
    assert not (tmp_path / "r.json").exists()
