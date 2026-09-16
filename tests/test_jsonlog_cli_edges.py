"""R2033：jsonlog 结构化日志族的 CLI 层边界（跨 worktree 真实 CLI）。

探针背景（outputs/autonomous/probe_jsonlog_r2033*.out，main 6c6d398，
对照组 C0 先行通过）：main 侧 test_jsonlog.py 已锁 happy path /
NullHandler 静默 / 同进程两次调用 append / traceback 捕获 / evaluation
事件；以下三面零覆盖（自跑 tests/ git grep jsonlog/JSONFormatter/
setup_logger/--log-file 零命中）：

1. `--log-file` 指向目录（或空串 → Path('.')）：setup_logger 的
   FileHandler 打开失败以**原生 PermissionError/IsADirectoryError
   traceback + rc 1** 穿透，无结构化 errors 信封——batch-parse 与
   evaluation.cli run 双通道同路径（特征锁定未修 + 指示线候选）。
2. 跨进程顺序 append：两个独立 CLI 进程先后写同一 --log-file，
   28 行全部合法 JSON 且严格按进程分组（先者 14 行连续在前）。
   main 只锁了同进程内两次调用；跨进程文件句柄面是新的。
   （并发同时 append 偶发静默丢行：1/7 观察，不可确定性断言，
   见 STATE.md R2033，不入测试。）
3. `--verbose` + `--log-file` 同开：stderr 同时承载 JSON 事件行与
   "[i/N] parse" 进度行（混流，help 文本自述"与进度输出可能交错"），
   stderr 可解析 JSON 事件序列与文件事件序列逐项相等。

被测对象解析：jsonlog（批次 17）不存在于本分支基线（2c35244），测试经
`git worktree list` 动态定位 branch=refs/heads/main 的 worktree，
subprocess 走其 venv 真实 CLI（r54 只读跨 worktree 授权：探针只子进程 +
PYTHONDONTWRITEBYTECODE=1，cwd/PYTHONPATH 指向临时目录与目标根，目标
worktree 零写入）。目标缺失（单仓检出 / 无 venv / 无 jsonlog）→ 显式
SKIP，绝不伪造通过。
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

_WORKTREE_ROOT = Path(__file__).resolve().parent.parent


def _resolve_main_worktree() -> Path | None:
    """`git worktree list --porcelain` 找 branch=refs/heads/main 的 worktree。

    本文件在自跑分支（基线无 jsonlog）时定位并列的 main worktree；
    被搬运回 main 后定位 main 自身——两种部署形态同一解析逻辑。
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(_WORKTREE_ROOT), "worktree", "list", "--porcelain"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    current: Path | None = None
    for line in out.stdout.splitlines():
        if line.startswith("worktree "):
            current = Path(line.split(" ", 1)[1])
        elif line == "branch refs/heads/main" and current is not None:
            if (current / "app" / "jsonlog.py").is_file():
                return current
    return None


_MAIN_ROOT = _resolve_main_worktree()


def _target_python(root: Path) -> str | None:
    for cand in (
        root / ".venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
    ):
        if cand.is_file():
            return str(cand)
    return None


pytestmark = pytest.mark.skipif(
    _MAIN_ROOT is None,
    reason="未找到含 app/jsonlog.py 的 main worktree（git worktree list）",
)


def _run(
    cwd: Path, root: Path, module: str, *args: str
) -> subprocess.CompletedProcess:
    py = _target_python(root)
    assert py is not None, "main worktree 缺 .venv 解释器"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [py, "-m", module, *args],
        capture_output=True, env=env, cwd=cwd, timeout=120,
        encoding="utf-8", errors="replace",
    )


def _write_docs(dir_: Path, n: int, tag: str) -> Path:
    dir_.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        (dir_ / f"{tag}{i}.md").write_text(
            f"# 标题 {tag}{i}\n\n正文 {tag} 标记 {i} 内容。\n", encoding="utf-8"
        )
    return dir_


def _load_events(log: Path) -> list[dict]:
    lines = [l for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert lines, "日志文件为空"
    return [json.loads(l) for l in lines]  # 坏行直接 JSONDecodeError 失败


def _make_eval_project(base: Path) -> Path:
    """最小 evaluation 项目：pyproject + manifest（相对正斜杠路径）+ 1 文档。"""
    base.mkdir(parents=True, exist_ok=True)
    (base / "pyproject.toml").write_text(
        "[project]\nname='r2033-probe'\n", encoding="utf-8"
    )
    _write_docs(base / "docs", 1, "ee")
    m = base / "manifest.json"
    m.write_text(
        json.dumps(
            {
                "manifest_version": "1.1",
                "devset_status": "incomplete",
                "documents": [
                    {"doc_id": "EE-0", "path": "docs/ee0.md",
                     "source_type": "markdown"}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return m


def test_log_file_bad_path_raw_traceback_both_clis(tmp_path: Path) -> None:
    """--log-file 指向目录/空串 → rc 1 + 原生 OSError traceback 穿透
    （无结构化 errors 信封）；batch-parse 与 evaluation.cli 同路径。"""
    assert _MAIN_ROOT is not None
    docs = _write_docs(tmp_path / "docs", 2, "bad")
    adir = tmp_path / "adir"
    adir.mkdir()
    # (a) batch-parse：目录与空串（Path('') → cwd '.'，同 FamilyOf OSError）
    for bad in (str(adir), ""):
        r = _run(
            tmp_path, _MAIN_ROOT, "app.cli",
            "batch-parse", str(docs), "-o", str(tmp_path / "out"),
            "--log-file", bad,
        )
        assert r.returncode == 1, f"bad={bad!r} rc={r.returncode}"
        assert "Traceback" in r.stderr, f"bad={bad!r} 缺原生 traceback"
        assert (
            "PermissionError" in r.stderr or "IsADirectoryError" in r.stderr
        ), f"bad={bad!r} 非 OSError 家族: {r.stderr[:200]}"
        with pytest.raises(json.JSONDecodeError):
            json.loads(r.stderr)  # 绝不是结构化 errors 信封
    # (b) evaluation.cli run：同一 setup_logger 路径
    proj = tmp_path / "evproj"
    manifest = _make_eval_project(proj)
    adir2 = proj / "adir"
    adir2.mkdir()
    re_ = _run(
        proj, _MAIN_ROOT, "evaluation.cli",
        "run", "--manifest", str(manifest),
        "--output", str(tmp_path / "report.json"),
        "--log-file", str(adir2),
    )
    assert re_.returncode == 1
    assert "Traceback" in re_.stderr
    assert "PermissionError" in re_.stderr or "IsADirectoryError" in re_.stderr


def test_cross_process_sequential_append(tmp_path: Path) -> None:
    """两个独立 CLI 进程先后 append 同一 --log-file：28 行全合法 JSON，
    且严格按进程分组（先者 batch_start..batch_complete 14 行连续在前）。"""
    assert _MAIN_ROOT is not None
    docs_a = _write_docs(tmp_path / "pa", 12, "pa")
    docs_b = _write_docs(tmp_path / "pb", 12, "pb")
    log = tmp_path / "seq.jsonl"

    r1 = _run(tmp_path, _MAIN_ROOT, "app.cli",
              "batch-parse", str(docs_a), "-o", str(tmp_path / "out_a"),
              "--log-file", str(log))
    assert r1.returncode == 0, r1.stderr[-300:]
    r2 = _run(tmp_path, _MAIN_ROOT, "app.cli",
              "batch-parse", str(docs_b), "-o", str(tmp_path / "out_b"),
              "--log-file", str(log))
    assert r2.returncode == 0, r2.stderr[-300:]

    events = _load_events(log)
    seq = [e["event"] for e in events]
    assert len(events) == 28  # 2 × (batch_start + 12×file_complete + batch_complete)
    assert seq.count("batch_start") == 2
    assert seq.count("file_complete") == 24
    assert seq.count("batch_complete") == 2

    # 进程分组：前 14 行全部 pa、后 14 行全部 pb（append 顺序，无交错）
    head = [e for e in events[:14] if e["event"] == "file_complete"]
    tail = [e for e in events[14:] if e["event"] == "file_complete"]
    assert len(head) == 12 and all("pa" in e["file"] for e in head)
    assert len(tail) == 12 and all("pb" in e["file"] for e in tail)


def test_verbose_stderr_mixes_json_events_and_progress(tmp_path: Path) -> None:
    """--verbose + --log-file 同开：stderr 混流（JSON 事件行 + "[i/N] parse"
    进度行同流），stderr 可解析 JSON 事件序列与文件事件序列逐项相等。"""
    assert _MAIN_ROOT is not None
    docs = _write_docs(tmp_path / "docs", 2, "vv")
    log = tmp_path / "verbose.jsonl"
    r = _run(tmp_path, _MAIN_ROOT, "app.cli",
             "batch-parse", str(docs), "-o", str(tmp_path / "out"),
             "--log-file", str(log), "--verbose")
    assert r.returncode == 0, r.stderr[-300:]

    file_events = _load_events(log)
    stderr_lines = [l for l in r.stderr.splitlines() if l.strip()]
    json_events: list[dict] = []
    progress_lines: list[str] = []
    for line in stderr_lines:
        if line.startswith("{"):
            json_events.append(json.loads(line))
        elif "] parse " in line:
            progress_lines.append(line)

    assert len(json_events) == len(file_events) == 4  # 双写完整
    assert [e["event"] for e in json_events] == [e["event"] for e in file_events]
    assert progress_lines, "stderr 应含进度行（与 JSON 事件混流）"
    # 混流形态：首条进度行出现在首条 JSON 事件（batch_start）之后
    first_json_idx = next(
        i for i, l in enumerate(stderr_lines) if l.startswith("{")
    )
    first_progress_idx = stderr_lines.index(progress_lines[0])
    assert first_progress_idx > first_json_idx
