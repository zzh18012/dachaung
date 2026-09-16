"""R2034：app/batch.py 并行通道族的 CLI 层边界（跨 worktree 真实 CLI）。

探针背景（outputs/autonomous/probe_batch_spawn_r2034.{py,out}，main
6c6d398，对照组 C0 先行通过：3 好 .md + workers=2 → rc 0 + summary 3/3 +
池路径事件信封完整）。main 侧覆盖对照：test_batch_parse.py 已锁（进程内）
顺序/并行一致性、错误隔离、stem 冲突、<3 文件顺序路径、CLI 冒烟
rc0/rc2/rc1；test_jsonlog.py 已锁事件流与 traceback 捕获（monkeypatch
进程内）；test_plugin_loader.py 已锁批量插件父加载失败/顺序/并行 + JSONL
（进程内 CLI）。以下三面在 main 与自跑 tests/ 均 grep 零覆盖：

1. `--workers` 钳制与顺序/池切换边界（CLI 层）：workers=0 / 负数经
   `max(1, int(w))` 钳到 1 → 顺序路径 rc 0；恰 2 文件（<SEQUENTIAL_
   THRESHOLD=3）× workers=2 → effective=1，恰 3 文件 → effective=2；
   summary.workers 与 JSONL batch_start.workers 都反映 effective 值。
   （非整数 → argparse rc 2 已是 argparse 通用行为，不重复锁。）
2. 三类后缀过滤的目录/glob 双通道不对称：目录递归扫描静默剔除 .txt
   （summary.total 不含、无任何 skip/warning 事件）；全部被剔 → rc 2
   且不写 summary.json；glob 通道**无**后缀过滤——'*.txt' 照样派发，
   fallback 的 detect_source_type 抛 unsupported_type → 结构化
   file_error + rc 1（同一文件两通道一静默一报错）。
3. 名为 *.md 的**子目录**混入：rglob 产出目录且 suffix 匹配通过
   过滤 → parse_one_file 的 is_file() 为 False → file_not_found
   （message 自述"输入文件不存在"，但该路径作为目录存在——措辞误导，
   特征锁定未修）；兄弟文件正常完成，rc 1。

被测对象解析：batch（批次 16）核心不在本分支基线（2c35244），测试经
`git worktree list` 动态定位 branch=refs/heads/main 的 worktree，
subprocess 走其 venv 真实 CLI（r54 只读跨 worktree 授权：探针只子进程 +
PYTHONDONTWRITEBYTECODE=1，cwd=临时目录 / PYTHONPATH=目标根，目标
worktree 零写入）。目标缺失 → 显式 SKIP，绝不伪造通过。运行时间预算：
仅 1 处真池路径（3 文件 × workers=2，探针实测全程 <1s/调用）。
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

_WORKTREE_ROOT = Path(__file__).resolve().parent.parent


def _resolve_main_worktree() -> Path | None:
    """`git worktree list --porcelain` 找 branch=refs/heads/main 的 worktree。"""
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
            if (current / "app" / "batch.py").is_file():
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
    reason="未找到含 app/batch.py 的 main worktree（git worktree list）",
)


def _run_batch(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    assert _MAIN_ROOT is not None
    py = _target_python(_MAIN_ROOT)
    assert py is not None, "main worktree 缺 .venv 解释器"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_MAIN_ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [py, "-m", "app.cli", "batch-parse", *args],
        capture_output=True, env=env, cwd=cwd, timeout=180,
        encoding="utf-8", errors="replace",
    )


def _write_docs(dir_: Path, n: int, tag: str) -> Path:
    dir_.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        (dir_ / f"{tag}{i}.md").write_text(
            f"# 标题 {tag}{i}\n\n正文 {tag} 标记 {i} 内容。\n", encoding="utf-8"
        )
    return dir_


def _load_summary(out_dir: Path) -> dict:
    return json.loads(
        (out_dir / "summary.json").read_text(encoding="utf-8")
    )


def _load_events(log: Path) -> list[dict]:
    lines = [l for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert lines, "日志文件为空"
    return [json.loads(l) for l in lines]  # 坏行直接 JSONDecodeError 失败


def test_workers_clamp_and_sequential_pool_boundary(tmp_path: Path) -> None:
    """--workers 0/负数钳到 1；恰 2 文件走顺序、恰 3 文件走池；
    summary.workers 与 JSONL batch_start.workers 均反映 effective 值。"""
    d2 = _write_docs(tmp_path / "d2", 2, "t")
    d3 = _write_docs(tmp_path / "d3", 3, "p")

    # 恰 2 文件 × workers=2 → <SEQUENTIAL_THRESHOLD(3) → 顺序路径
    log2 = tmp_path / "two.jsonl"
    r = _run_batch(
        tmp_path, str(d2), "-o", str(tmp_path / "o2"),
        "--workers", "2", "--log-file", str(log2),
    )
    assert r.returncode == 0
    s = _load_summary(tmp_path / "o2")
    assert s["workers"] == 1
    ev = _load_events(log2)
    assert ev[0]["event"] == "batch_start" and ev[0]["workers"] == 1
    assert ev[-1]["event"] == "batch_complete"
    # 顺序路径 file_complete 顺序与文件名字典序一致
    names = [Path(e["file"]).name for e in ev if e["event"] == "file_complete"]
    assert names == ["t0.md", "t1.md"]

    # 恰 3 文件 × workers=2 → 池路径（imap_unordered 顺序不作确定性断言）
    log3 = tmp_path / "three.jsonl"
    r = _run_batch(
        tmp_path, str(d3), "-o", str(tmp_path / "o3"),
        "--workers", "2", "--log-file", str(log3),
    )
    assert r.returncode == 0
    s = _load_summary(tmp_path / "o3")
    assert s["workers"] == 2
    ev = _load_events(log3)
    assert ev[0]["event"] == "batch_start" and ev[0]["workers"] == 2
    assert (
        [e["event"] for e in ev]
        == ["batch_start", "file_complete", "file_complete", "file_complete",
            "batch_complete"]
    )

    # 钳制：0 与负数都经 max(1, int(w)) → 顺序路径成功
    for w in ("0", "-5"):
        out_dir = tmp_path / f"ow{w}"
        r = _run_batch(
            tmp_path, str(d3), "-o", str(out_dir),
            "--workers", w,
        )
        assert r.returncode == 0
        s = _load_summary(out_dir)
        assert s["workers"] == 1
        assert s["success"] == 3 and s["failed"] == 0


def test_suffix_filter_dir_vs_glob_channel_asymmetry(tmp_path: Path) -> None:
    """目录扫描静默剔除三类后缀之外的文件；glob 通道无过滤照样派发。"""
    mixed = tmp_path / "mixed"
    mixed.mkdir()
    (mixed / "a.md").write_text("# a\n\n正文 a。\n", encoding="utf-8")
    (mixed / "b.md").write_text("# b\n\n正文 b。\n", encoding="utf-8")
    (mixed / "note.txt").write_text("plain text", encoding="utf-8")

    log = tmp_path / "mixed.jsonl"
    r = _run_batch(
        tmp_path, str(mixed), "-o", str(tmp_path / "omix"),
        "--log-file", str(log),
    )
    assert r.returncode == 0
    s = _load_summary(tmp_path / "omix")
    assert (s["total"], s["success"], s["failed"]) == (2, 2, 0)
    # .txt 完全不可见：summary 与 JSONL 原文均无痕迹（静默跳过，无事件）
    assert "note.txt" not in json.dumps(s, ensure_ascii=False)
    ev = _load_events(log)
    assert ev[0]["event"] == "batch_start" and ev[0]["file_count"] == 2
    assert "note.txt" not in log.read_text(encoding="utf-8")

    # 全部被剔 → rc 2 且不写 summary.json
    onlytxt = tmp_path / "onlytxt"
    onlytxt.mkdir()
    (onlytxt / "x.txt").write_text("plain", encoding="utf-8")
    (onlytxt / "y.log").write_text("log", encoding="utf-8")
    r = _run_batch(
        tmp_path, str(onlytxt), "-o", str(tmp_path / "otxt")
    )
    assert r.returncode == 2
    assert "未找到可解析文件" in r.stderr
    assert not (tmp_path / "otxt" / "summary.json").exists()

    # glob '*.txt'：同一文件换个通道即被派发 → unsupported_type 结构化失败
    log4 = tmp_path / "glob.jsonl"
    r = _run_batch(
        tmp_path, str(onlytxt / "*.txt"),
        "-o", str(tmp_path / "oglob"), "--log-file", str(log4),
    )
    assert r.returncode == 1
    s = _load_summary(tmp_path / "oglob")
    assert (s["total"], s["success"], s["failed"]) == (1, 0, 1)
    assert s["errors"][0]["code"] == "unsupported_type"
    errs = [e for e in _load_events(log4) if e["event"] == "file_error"]
    assert len(errs) == 1
    assert errs[0]["error_code"] == "unsupported_type"
    assert "error_message" in errs[0]  # "message" 是 LogRecord 保留属性

    # 对照：同目录 glob '*.md' 无匹配 → 同样 rc 2（无文件可派发）
    r = _run_batch(
        tmp_path, str(onlytxt / "*.md"),
        "-o", str(tmp_path / "oglobmd"),
    )
    assert r.returncode == 2


def test_directory_named_md_suffix_counted_as_file(tmp_path: Path) -> None:
    """子目录名为 trap.md：通过 rglob 后缀过滤被当作任务派发，
    is_file() 为 False → file_not_found（message 却说"输入文件不存在"）；
    兄弟文件正常完成，rc 1。"""
    trapped = tmp_path / "trapped"
    trapped.mkdir()
    (trapped / "real.md").write_text("# real\n\n正文。\n", encoding="utf-8")
    (trapped / "trap.md").mkdir()  # 存在，但是目录

    log = tmp_path / "trap.jsonl"
    r = _run_batch(
        tmp_path, str(trapped), "-o", str(tmp_path / "otrap"),
        "--log-file", str(log),
    )
    assert r.returncode == 1
    s = _load_summary(tmp_path / "otrap")
    assert (s["total"], s["success"], s["failed"]) == (2, 1, 1)
    err = s["errors"][0]
    assert err["code"] == "file_not_found"
    assert err["file"].endswith("trap.md")
    # 措辞误导特征：路径作为目录存在，message 却自述"输入文件不存在"
    assert "输入文件不存在" in err["message"]
    # 兄弟文件不受牵连
    assert (tmp_path / "otrap" / "real.json").is_file()
    ev_errs = [e for e in _load_events(log) if e["event"] == "file_error"]
    assert len(ev_errs) == 1
    assert ev_errs[0]["error_code"] == "file_not_found"
    assert ev_errs[0]["traceback"] is None  # 非异常路径（防御检查）无 traceback
