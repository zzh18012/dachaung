"""批次 17 测试：结构化日志（JSON Lines，Stage 8 批次 17，Option A 裁决）。

覆盖裁决 6 项：formatter 格式 / 多 handler 与 NullHandler 静默 /
batch 事件完整性 / traceback 捕获与 file_not_found 之 null / append 模式 /
evaluation 事件（含 doc_error）。
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
    kinds = {type(h).__name__ for h in logger.handlers}
    assert kinds == {"FileHandler", "StreamHandler"}
    logger.handlers.clear()  # 摘掉 StreamHandler，避免污染后续 capfd


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


# ---------- 4b. file_warning 逐码发射（真实 parser 警告难稳定触发，直测发射逻辑） ----------

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
