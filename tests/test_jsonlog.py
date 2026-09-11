"""批次 17 测试：结构化日志（JSON Lines，Stage 8 批次 17，Option A 裁决）。

覆盖裁决 6 项：formatter 格式 / 多 handler 与 NullHandler 静默 /
batch 事件完整性 / traceback 捕获与 file_not_found 之 null / append 模式 /
evaluation 事件（含 doc_error）。
另含 Stage 10 批次 2 次项（traceback 有界截断，4b 节）与第三项
（日志轮转，7 节）。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.batch import batch_parse_files
from app.cli import main as app_main
from app.jsonlog import JSONFormatter, setup_logger
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


def _write_md(directory: Path, name: str, marker: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    p = directory / name
    p.write_text(f"# 标题 {name}\n\n正文 {marker} 标记内容。\n", encoding="utf-8")
    return p


def _read_events(log_path: Path) -> list[dict]:
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines, "日志文件为空"
    return [json.loads(line) for line in lines]


# ---------- 1. JSONFormatter 格式 ----------

def test_formatter_json_format():
    record = logging.LogRecord(
        "t", logging.INFO, __file__, 1, "my_event", (), None
    )
    record.k1 = "v1"
    record.k2 = 7
    obj = json.loads(JSONFormatter().format(record))

    assert obj["event"] == "my_event"
    assert obj["level"] == "INFO"
    assert isinstance(obj["timestamp"], float)
    assert obj["k1"] == "v1" and obj["k2"] == 7
    # 保留属性不得泄漏到顶层
    assert "message" not in obj and "asctime" not in obj
    assert "module" not in obj and "filename" not in obj


def test_formatter_keeps_unicode_and_extra_roundtrip(tmp_path: Path):
    log = tmp_path / "fmt.jsonl"
    logger = setup_logger("app.jsonlog.fmt", log)
    logger.info("中文事件", extra={"workers": 8})
    evt = _read_events(log)[0]
    assert evt["event"] == "中文事件"
    assert evt["workers"] == 8


# ---------- 2. setup_logger：多 handler 与 NullHandler 静默 ----------

def test_setup_logger_both_handlers(tmp_path: Path):
    logger = setup_logger(
        "app.jsonlog.both", tmp_path / "both.jsonl", verbose=True
    )
    # 批次 2 第三项起默认按大小轮转（50 MiB）；文件 handler 类型随之变化
    kinds = {type(h).__name__ for h in logger.handlers}
    assert kinds == {"RotatingFileHandler", "StreamHandler"}
    logger.handlers.clear()  # 摘掉 StreamHandler，避免污染后续 capfd

    disabled = setup_logger(  # max_bytes=0 回退批次 17 普通 FileHandler
        "app.jsonlog.both0", tmp_path / "both0.jsonl", max_bytes=0
    )
    assert [type(h).__name__ for h in disabled.handlers] == ["FileHandler"]


def test_setup_logger_silent_by_default_no_leak(tmp_path: Path, capfd):
    logger = setup_logger("app.jsonlog.silent")
    assert [type(h).__name__ for h in logger.handlers] == ["NullHandler"]
    logger.warning("不应泄漏到 stderr")  # 无 handler 时 lastResort 会泄漏
    captured = capfd.readouterr()
    assert captured.out == "" and captured.err == ""


# ---------- 3. batch 事件完整性 ----------

def test_batch_events_complete(tmp_path: Path):
    docs = tmp_path / "docs"
    good = [_write_md(docs, f"g{i}.md", f"M{i}") for i in range(3)]
    missing = docs / "nope.md"
    log = tmp_path / "batch.jsonl"

    summary = batch_parse_files(
        good + [missing], tmp_path / "out", log_file=log, workers=1
    )
    events = _read_events(log)

    start = events[0]
    assert start["event"] == "batch_start"
    assert start["workers"] == 1
    assert start["file_count"] == 4
    assert start["parser"] == "fallback"
    assert start["max_chars"] == 800

    completes = [e for e in events if e["event"] == "file_complete"]
    assert len(completes) == 3
    for e in completes:
        assert set(e) >= {"file", "parser", "elements", "chunks", "seconds"}
        assert e["parser"] == "markdown"  # .md 由批模式路由
        assert e["elements"] > 0 and e["chunks"] > 0

    errors = [e for e in events if e["event"] == "file_error"]
    assert len(errors) == 1
    assert errors[0]["error_code"] == "file_not_found"
    assert errors[0]["traceback"] is None

    done = events[-1]
    assert done["event"] == "batch_complete"
    assert done["success"] == summary["success"] == 3
    assert done["failed"] == summary["failed"] == 1
    assert done["wall_time_seconds"] > 0


def test_batch_stem_collision_logged_as_file_error(tmp_path: Path):
    f1 = _write_md(tmp_path / "a", "dup.md", "FIRST")
    f2 = _write_md(tmp_path / "b", "dup.md", "SECOND")
    log = tmp_path / "coll.jsonl"

    batch_parse_files([f1, f2], tmp_path / "out", log_file=log, workers=1)

    errors = [e for e in _read_events(log) if e["event"] == "file_error"]
    assert len(errors) == 1
    assert errors[0]["error_code"] == "stem_collision"
    assert errors[0]["traceback"] is None
    assert "未覆盖" in errors[0]["error_message"]


# ---------- 4. traceback 捕获 ----------

def test_traceback_captured_on_exception(tmp_path: Path, monkeypatch):
    import app.batch as batch_mod

    f = _write_md(tmp_path / "docs", "boom.md", "BOOM")
    log = tmp_path / "tb.jsonl"

    def _raise(*a, **kw):
        raise RuntimeError("爆炸现场")

    monkeypatch.setattr(batch_mod, "process_single", _raise)
    summary = batch_parse_files([f], tmp_path / "out", log_file=log, workers=1)

    assert summary["failed"] == 1
    err = [e for e in _read_events(log) if e["event"] == "file_error"][0]
    assert err["error_code"] == "RuntimeError"
    assert "爆炸现场" in err["error_message"]
    assert "RuntimeError: 爆炸现场" in err["traceback"]
    assert "Traceback" in err["traceback"]


# ---------- 4b. traceback 有界截断（Stage 10 批次 2 次项） ----------

from app.jsonlog import (  # noqa: E402
    TRACEBACK_HEAD_LINES,
    TRACEBACK_MAX_CHARS,
    TRACEBACK_MAX_LINES,
    TRACEBACK_TAIL_LINES,
    truncate_traceback,
)


def test_truncate_traceback_short_unchanged():
    tb = (
        'Traceback (most recent call last):\n'
        '  File "x.py", line 1, in <module>\n'
        "ValueError: boom"
    )
    assert truncate_traceback(tb) == tb


def test_truncate_traceback_lines_bounded_head_tail_kept():
    lines = [f"frame line {i}" for i in range(500)]
    out_lines = truncate_traceback("\n".join(lines)).splitlines()
    assert len(out_lines) <= TRACEBACK_MAX_LINES
    # 头 40 原样 + 标记行（含折叠量）+ 尾 20 原样（异常行在尾部）
    assert out_lines[:TRACEBACK_HEAD_LINES] == lines[:TRACEBACK_HEAD_LINES]
    assert out_lines[-TRACEBACK_TAIL_LINES:] == lines[-TRACEBACK_TAIL_LINES:]
    marker = out_lines[TRACEBACK_HEAD_LINES]
    assert marker == f"...<truncated:{500 - TRACEBACK_HEAD_LINES - TRACEBACK_TAIL_LINES} lines>..."


def test_truncate_traceback_chars_bounded_tail_kept():
    tb = "Traceback (most recent call last):\n" + "x" * 100_000 + "\nValueError: boom"
    out = truncate_traceback(tb)
    assert len(out) <= TRACEBACK_MAX_CHARS
    assert out.endswith("ValueError: boom")
    assert "...<truncated:" in out and "chars>..." in out


def test_formatter_truncates_only_traceback_field():
    record = logging.LogRecord(
        "t", logging.ERROR, __file__, 1, "file_error", (), None
    )
    record.traceback = "\n".join(f"line {i}" for i in range(1000))
    record.error_code = "X"
    record.other = "\n".join(f"o{i}" for i in range(1000))  # 非 traceback 字段不动
    obj = json.loads(JSONFormatter().format(record))
    assert len(obj["traceback"].splitlines()) <= TRACEBACK_MAX_LINES
    assert "<truncated:" in obj["traceback"]
    assert obj["error_code"] == "X"
    assert obj["other"].splitlines()[0] == "o0"
    assert len(obj["other"].splitlines()) == 1000


def test_batch_file_error_traceback_bounded(tmp_path: Path, monkeypatch):
    import app.batch as batch_mod

    def _deep_raise(*a, **kw):
        # exec 生成 200 个互异命名帧：真实递归会被 Python 折叠成
        # "[Previous line repeated N more times]"（8 行），永远到不了 64 行界
        src = "".join(f"def f{i}():\n    return f{i + 1}()\n" for i in range(200))
        src += "def f200():\n    raise RuntimeError('深崩')\n"
        ns: dict = {}
        exec(src, ns)  # noqa: S102
        ns["f0"]()

    f = _write_md(tmp_path / "docs", "deep.md", "DEEP")
    log = tmp_path / "deep.jsonl"
    monkeypatch.setattr(batch_mod, "process_single", _deep_raise)
    batch_parse_files([f], tmp_path / "out", log_file=log, workers=1)

    err = [e for e in _read_events(log) if e["event"] == "file_error"][0]
    assert err["error_code"] == "RuntimeError"
    assert len(err["traceback"].splitlines()) <= TRACEBACK_MAX_LINES
    assert "<truncated:" in err["traceback"]
    assert "RuntimeError: 深崩" in err["traceback"]  # 尾部异常行保留


# ---------- 4c. file_warning 逐码发射（真实 parser 警告难稳定触发，直测发射逻辑） ----------

def test_file_warning_event_per_code(tmp_path: Path):
    import logging

    from app.batch import _log_file_event

    captured: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    lg = logging.getLogger("app.batch.cap")
    lg.handlers.clear()
    lg.addHandler(_Capture())
    lg.setLevel(logging.INFO)

    _log_file_event(
        lg,
        {
            "file": "a.pdf",
            "success": True,
            "parser": "fallback",
            "elements": 3,
            "chunks": 2,
            "warnings": ["w1", "w2"],
            "seconds": 0.1,
        },
    )

    assert [r.getMessage() for r in captured] == [
        "file_complete",
        "file_warning",
        "file_warning",
    ]
    assert all(r.levelname == "WARNING" for r in captured[1:])
    assert [r.warning_code for r in captured[1:]] == ["w1", "w2"]


# ---------- 5. append 模式 ----------

def test_log_file_append_mode(tmp_path: Path):
    f = _write_md(tmp_path / "docs", "app.md", "APP")
    log = tmp_path / "append.jsonl"
    for _ in range(2):
        batch_parse_files([f], tmp_path / "out", log_file=log, workers=1)

    events = _read_events(log)  # 全部行须仍为合法 JSON
    starts = [e for e in events if e["event"] == "batch_start"]
    dones = [e for e in events if e["event"] == "batch_complete"]
    assert len(starts) == 2 and len(dones) == 2


# ---------- 6. evaluation 事件（含 doc_error） ----------

def _make_manifest(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='test'\n", encoding="utf-8"
    )
    docs = tmp_path / "docs"
    entries = []
    for i in range(3):
        rel = _write_md(docs, f"ev{i}.md", f"EV{i}")
        entries.append(
            {
                "doc_id": f"EV-{i}",
                "path": rel.relative_to(tmp_path).as_posix(),
                "source_type": "markdown",
            }
        )
    p = tmp_path / "manifest.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.1",
                "devset_status": "incomplete",
                "documents": entries,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return p


def test_evaluation_events(tmp_path: Path):
    manifest = load_manifest(_make_manifest(tmp_path), project_root=tmp_path)
    log = tmp_path / "eval.jsonl"

    run_evaluation(
        manifest,
        tmp_path / "report.json",
        parser_name="fallback",  # fallback 不支持 .md → 3 个 doc_error
        log_file=log,
        manifest_label="samples/private/devset/manifest.json",
        workers=1,
    )
    events = _read_events(log)

    start = events[0]
    assert start["event"] == "eval_start"
    assert start["parser"] == "fallback"
    assert start["doc_count"] == 3
    assert start["manifest_label"] == "samples/private/devset/manifest.json"

    doc_errors = [e for e in events if e["event"] == "doc_error"]
    assert len(doc_errors) == 3
    assert {e["doc_id"] for e in doc_errors} == {"EV-0", "EV-1", "EV-2"}
    for e in doc_errors:
        assert e["error_code"] == "unsupported_type"
        assert "error_message" in e  # "message" 为 LogRecord 保留字

    done = events[-1]
    assert done["event"] == "eval_complete"
    assert done["success"] == 0 and done["failed"] == 3
    assert done["wall_time_seconds"] > 0


def test_evaluation_doc_complete_fields(tmp_path: Path):
    manifest = load_manifest(_make_manifest(tmp_path), project_root=tmp_path)
    log = tmp_path / "eval-ok.jsonl"

    run_evaluation(
        manifest, tmp_path / "report.json",
        parser_name="markdown", log_file=log, workers=1,
    )
    completes = [e for e in _read_events(log) if e["event"] == "doc_complete"]
    assert len(completes) == 3
    for e in completes:
        assert set(e) >= {"doc_id", "source_type", "parser_used", "seconds"}
        assert e["source_type"] == "markdown"
        assert e["parser_used"] == "markdown"


# ---------- CLI 透传 ----------

def test_cli_batch_parse_log_file(tmp_path: Path):
    docs = tmp_path / "docs"
    _write_md(docs, "cli.md", "CLI")
    log = tmp_path / "cli.jsonl"
    rc = app_main(
        [
            "batch-parse", str(docs), "-o", str(tmp_path / "out"),
            "--log-file", str(log),
        ]
    )
    assert rc == 0
    assert any(e["event"] == "batch_start" for e in _read_events(log))


# ---------- 7. 日志轮转（Stage 10 批次 2 第三项） ----------

def _emit_padded(logger, n: int) -> None:
    for i in range(n):
        logger.info(f"rot_event_{i}", extra={"pad": "x" * 120})


def _sibling(log: Path, n: int) -> Path:
    return log.parent / f"{log.name}.{n}"


def test_rotation_creates_backups_all_valid_jsonl(tmp_path: Path):
    log = tmp_path / "rot.jsonl"
    # 每条事件 ~175B，1000B 阈值 → 5 条/文件，12 条恰装 3 文件
    # （.2/.1/main）——backup_count=2 内零丢弃，可断言事件并集完整
    logger = setup_logger(
        "app.jsonlog.rot", log, max_bytes=1000, backup_count=2
    )
    _emit_padded(logger, 12)

    assert log.exists()
    assert _sibling(log, 1).exists() and _sibling(log, 2).exists()
    assert not _sibling(log, 3).exists()  # backup_count=2 封顶

    # 每个文件（含轮转件）独立合法 JSONL；并集恰为全部事件
    total = 0
    for p in [log, _sibling(log, 1), _sibling(log, 2)]:
        for line in p.read_text(encoding="utf-8").strip().splitlines():
            obj = json.loads(line)
            assert obj["event"].startswith("rot_event_")
            total += 1
    assert total == 12


def test_rotation_disabled_zero_max_bytes(tmp_path: Path):
    log = tmp_path / "norot.jsonl"
    logger = setup_logger(
        "app.jsonlog.norot", log, max_bytes=0, backup_count=2
    )
    _emit_padded(logger, 10)

    assert log.exists()
    assert not _sibling(log, 1).exists()
    events = _read_events(log)
    assert len(events) == 10  # 无轮转：全部事件单文件


def test_rotation_backup_count_zero_discards_old(tmp_path: Path):
    log = tmp_path / "bc0.jsonl"
    logger = setup_logger(
        "app.jsonlog.bc0", log, max_bytes=300, backup_count=0
    )
    _emit_padded(logger, 12)

    assert log.exists()
    assert not _sibling(log, 1).exists()  # backup_count=0：不留备份
    events = _read_events(log)  # 主文件仍是合法 JSONL（旧事件被丢弃）
    assert all(e["event"].startswith("rot_event_") for e in events)


def test_cli_batch_parse_rotation_flags(tmp_path: Path):
    docs = tmp_path / "docs"
    for i in range(3):
        _write_md(docs, f"r{i}.md", f"R{i}")
    log = tmp_path / "cli-rot.jsonl"
    rc = app_main(
        [
            "batch-parse", str(docs), "-o", str(tmp_path / "out"),
            "--log-file", str(log),
            "--log-max-bytes", "400", "--log-backup-count", "2",
        ]
    )
    assert rc == 0
    assert _sibling(log, 1).exists()  # 总量超 400B，发生过轮转


def test_evaluation_rotation_wiring(tmp_path: Path):
    manifest = load_manifest(_make_manifest(tmp_path), project_root=tmp_path)
    log = tmp_path / "eval-rot.jsonl"

    run_evaluation(
        manifest, tmp_path / "report.json",
        parser_name="markdown", log_file=log, workers=1,
        log_max_bytes=250, log_backup_count=3,
    )
    assert _sibling(log, 1).exists()
