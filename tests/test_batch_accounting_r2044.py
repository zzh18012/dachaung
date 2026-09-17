"""R2044：app.cli batch-parse 三方记账一致性锁（真实 CLI 子进程）。

探针背景（outputs/autonomous/probe_batch_accounting_r2044.py + .out，main
6c6d398，C0 通过 + E1–E7 全 17 项成立零偏差，main 前后 clean）：批次 16/17 的
summary.json / stdout 汇总行 / --log-file JSONL 三方对账面，main 仅进程内锁
（test_batch_parse.py 的 batch_parse_files 直调 + test_jsonlog.py 的 workers=1
事件完整性/合成 file_warning 单元发射），**CLI 子进程面的三方计数对账零覆盖**。
本轮锁三组：

1. **混合批三方对账**（2 好 .md + 1 随机字节坏 .docx）——rc 1（部分失败即 1，
   `0 if failed == 0 else 1`）；stdout `[FAIL] batch-parse: 2/3 成功，workers=N`
   与 summary.success/total/workers 逐值相等；JSONL 恰 5 事件
   （batch_start.file_count=3 → 2 file_complete + 1 file_error → batch_complete
   与 summary 的 success/failed/wall_time_seconds 逐值相等）；file_error 含
   非空 error_message（"message" 为 LogRecord 保留字）且 traceback=None
   （结构化 ParserError 通道）；summary.errors 形状 {file, code, message}。
   全好批实为 5 事件（start + N complete + complete），任务简报"4 事件"为笔误。
2. **rc/summary 信封**——空目录与 glob 零命中 → rc 2 + stderr
   `未找到可解析文件` + summary.json 不存在 + JSONL 不存在 + 输出目录不创建
   （batch_parse_files 未被调用的三通道零痕迹）；全坏批（2 坏 .docx）→ rc 1
   + failed=2 + 除 summary.json 外无半成品 JSON 残留。
3. **file_warning 真实触发 + 后缀过滤计数**——(a) frontmatter 嵌套/列表值 .md
   经 `--parser auto`（发现 markdown_enhanced）→ rc 0 + 两个 file_warning
   （frontmatter_line_skipped / frontmatter_value_skipped）且均发射于该文件
   file_complete 之后，warning 不改 success 记账（summary.success=1）——
   main test_jsonlog 4b 为合成单元发射，真实输入 CLI 面首次锁；(b) 3 .md +
   1 .txt 混入目录 → 三方计数全部只算 3（R2034 已锁静默剔除，本轮锁剔除后
   对账），.txt 在 stdout/summary/JSONL 三通道零出现。

被测对象解析：与 test_parse_edges_r2043.py 同规——经 `git worktree list`
动态定位 branch=refs/heads/main 的 worktree，subprocess 走其 venv（只读跨
worktree 授权：PYTHONDONTWRITEBYTECODE=1，cwd/PYTHONPATH 指向临时目录与
目标根，目标 worktree 零写入）。目标缺失 → 显式 SKIP，绝不伪造通过。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

_WORKTREE_ROOT = Path(__file__).resolve().parent.parent

GOOD_MD = (
    "# 标题 {n}\n\n正文段落 {n}，包含足够长度文本用于结构分块。\n\n"
    "## 小节 {n}\n\n第二段内容 {n}。\n"
)

# 确定性伪随机字节（非 ZIP 头）→ fallback DOCX 通道 docx_open_failed
BAD_DOCX = bytes(range(256)) * 7

WARN_MD = (
    "---\n"
    "title: 有标量值的键\n"
    "- 嵌套列表行应被跳过\n"
    "tags: [a, b]\n"
    "---\n\n"
    "# 正文标题\n\n段落内容足够长以便分块。\n"
)


def _resolve_main_worktree() -> Path | None:
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
            if (current / "app" / "cli.py").is_file():
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
    _MAIN_ROOT is None or _target_python(_MAIN_ROOT) is None,
    reason="未找到含 app/cli.py + venv 的 main worktree（git worktree list）",
)


def _run_cli(args: list[str], cwd: Path) -> tuple[int, str, str]:
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(_MAIN_ROOT),
    }
    p = subprocess.run(
        [_target_python(_MAIN_ROOT), "-m", "app.cli", *args],  # type: ignore[list-item]
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(cwd), env=env, timeout=300,
    )
    return p.returncode, p.stdout, p.stderr


def _read_events(log_path: Path) -> list[dict]:
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(ln) for ln in lines if ln.strip()]


def _make_docs(root: Path, spec: list[tuple[str, bytes | str]]) -> Path:
    docs = root / "docs"
    docs.mkdir(parents=True)
    for name, content in spec:
        p = docs / name
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")
    return docs


def _parse_stdout_line(so: str) -> tuple[str, int, int, int]:
    m = re.search(
        r"^(\[OK\]|\[FAIL\]) batch-parse: (\d+)/(\d+) 成功，workers=(\d+)，",
        so, re.M,
    )
    assert m, f"stdout 汇总行缺失: {so!r}"
    return m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))


# ---------- 1. 混合批三方对账 ----------

def test_mixed_batch_three_way_reconciliation(tmp_path: Path):
    """2 好 .md + 1 坏 .docx：stdout 行 / summary.json / JSONL 三方逐值对账。"""
    docs = _make_docs(tmp_path, [
        ("ok0.md", GOOD_MD.format(n=0)),
        ("ok1.md", GOOD_MD.format(n=1)),
        ("bad.docx", BAD_DOCX),
    ])
    out = tmp_path / "out"
    log = tmp_path / "log.jsonl"
    rc, so, se = _run_cli(
        ["batch-parse", str(docs), "-o", str(out),
         "--log-file", str(log), "--workers", "1"],
        cwd=tmp_path,
    )

    assert rc == 1, f"部分失败期望 rc 1，实际 {rc}\nstderr={se[:400]}"
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert (summary["total"], summary["success"], summary["failed"]) == (3, 2, 1)
    assert summary["success"] + summary["failed"] == summary["total"]

    # stdout 汇总行 vs summary（状态/S/T/workers 四值）
    status, s_, t_, w_ = _parse_stdout_line(so)
    assert status == "[FAIL]"
    assert (s_, t_, w_) == (summary["success"], summary["total"], summary["workers"])

    # JSONL vs summary（计数封闭 + batch_complete 三值逐等）
    events = _read_events(log)
    kinds = [e["event"] for e in events]
    assert kinds.count("batch_start") == 1
    assert kinds.count("file_complete") == summary["success"]
    assert kinds.count("file_error") == summary["failed"]
    assert kinds.count("batch_complete") == 1
    assert set(kinds) <= {
        "batch_start", "file_complete", "file_warning", "file_error",
        "batch_complete",
    }
    assert events[0]["event"] == "batch_start" and events[0]["file_count"] == 3
    done = events[-1]
    assert done["event"] == "batch_complete"
    assert done["success"] == summary["success"]
    assert done["failed"] == summary["failed"]
    assert done["wall_time_seconds"] == summary["wall_time_seconds"]

    # file_error 信封：error_message 非空 str + traceback None + .md 路由可证
    err = next(e for e in events if e["event"] == "file_error")
    assert err["error_code"] == "docx_open_failed"
    assert isinstance(err["error_message"], str) and err["error_message"].strip()
    assert err["traceback"] is None and err["parser"] == "fallback"
    comps = [e for e in events if e["event"] == "file_complete"]
    assert {e["parser"] for e in comps} == {"markdown"}  # fallback 下 .md 路由

    # summary.errors 形状
    assert len(summary["errors"]) == 1
    assert set(summary["errors"][0]) == {"file", "code", "message"}
    assert summary["errors"][0]["code"] == "docx_open_failed"


# ---------- 2. rc / summary 信封（零命中与全坏） ----------

def test_empty_and_all_bad_rc_envelope(tmp_path: Path):
    """空目录 / glob 零命中 → rc 2 三通道零痕迹；全坏批 → rc 1 无半成品。"""
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    out = tmp_path / "out"
    log = tmp_path / "log.jsonl"
    rc, so, se = _run_cli(
        ["batch-parse", str(docs), "-o", str(out), "--log-file", str(log)],
        cwd=tmp_path,
    )
    assert rc == 2
    assert "未找到可解析文件" in se
    # batch_parse_files 未被调用：summary/JSONL/输出目录三通道零痕迹
    assert not (out / "summary.json").exists()
    assert not log.exists()
    assert not out.exists()

    rc2, _, se2 = _run_cli(
        ["batch-parse", str(docs / "*.zzz"), "-o", str(tmp_path / "out2"),
         "--log-file", str(tmp_path / "log2.jsonl")],
        cwd=tmp_path,
    )
    assert rc2 == 2 and "未找到可解析文件" in se2

    # 全坏批（2 坏 .docx，<3 文件 → workers=1 顺序）：rc 1 + 全计失败 + 无残留
    docs_bad = _make_docs(tmp_path / "allbad", [
        ("b0.docx", BAD_DOCX), ("b1.docx", BAD_DOCX),
    ])
    out3 = tmp_path / "out3"
    rc3, so3, _ = _run_cli(
        ["batch-parse", str(docs_bad), "-o", str(out3), "--workers", "1"],
        cwd=tmp_path,
    )
    assert rc3 == 1
    summary3 = json.loads((out3 / "summary.json").read_text(encoding="utf-8"))
    assert (summary3["total"], summary3["success"], summary3["failed"]) == (2, 0, 2)
    leftovers = [p.name for p in out3.glob("*.json") if p.name != "summary.json"]
    assert leftovers == [], f"失败批不得残留半成品 JSON: {leftovers}"
    status, s3, t3, _ = _parse_stdout_line(so3)
    assert (status, s3, t3) == ("[FAIL]", 0, 2)


# ---------- 3. file_warning 真实触发 + 后缀过滤计数对账 ----------

def test_warning_trigger_and_suffix_filter_accounting(tmp_path: Path):
    """frontmatter 跳过 → 真实 file_warning；.txt 混入 → 三方计数只算 .md。"""
    # (a) 真实 warning 路径：--parser auto 发现 markdown_enhanced，
    #     嵌套列表行 + 列表值键 → 两个 warning 码，均发射于 file_complete 之后
    docs_w = _make_docs(tmp_path / "w", [("warn.md", WARN_MD)])
    outw = tmp_path / "outw"
    logw = tmp_path / "logw.jsonl"
    rcw, _, _ = _run_cli(
        ["batch-parse", str(docs_w), "-o", str(outw),
         "--log-file", str(logw), "--parser", "auto"],
        cwd=tmp_path,
    )
    assert rcw == 0
    summary_w = json.loads((outw / "summary.json").read_text(encoding="utf-8"))
    # warning 不改成败记账：仍是 1 成功 0 失败
    assert (summary_w["success"], summary_w["failed"]) == (1, 0)
    events = _read_events(logw)
    comp = next(e for e in events if e["event"] == "file_complete")
    assert comp["parser"] == "markdown_enhanced"  # auto 发现胜者（priority 5）
    warns = [e for e in events if e["event"] == "file_warning"]
    assert {w["warning_code"] for w in warns} == {
        "frontmatter_line_skipped", "frontmatter_value_skipped",
    }
    assert all(events.index(w) > events.index(comp) for w in warns)

    # (b) 后缀过滤计数对账：3 .md + 1 .txt → 三方计数只算 3，.txt 零出现
    docs_m = _make_docs(tmp_path / "m", [
        ("m0.md", GOOD_MD.format(n=0)),
        ("m1.md", GOOD_MD.format(n=1)),
        ("m2.md", GOOD_MD.format(n=2)),
        ("note.txt", "纯文本不进批\n"),
    ])
    outm = tmp_path / "outm"
    logm = tmp_path / "logm.jsonl"
    rcm, som, _ = _run_cli(
        ["batch-parse", str(docs_m), "-o", str(outm),
         "--log-file", str(logm), "--parser", "auto"],
        cwd=tmp_path,
    )
    assert rcm == 0
    summary_m = json.loads((outm / "summary.json").read_text(encoding="utf-8"))
    assert (summary_m["total"], summary_m["success"], summary_m["failed"]) == (3, 3, 0)
    statusm, sm, tm_, _ = _parse_stdout_line(som)
    assert (statusm, sm, tm_) == ("[OK]", 3, 3)
    evm = _read_events(logm)
    assert evm[0]["event"] == "batch_start" and evm[0]["file_count"] == 3
    assert sum(1 for e in evm if e["event"] == "file_complete") == 3
    assert not any("note.txt" in json.dumps(e, ensure_ascii=False) for e in evm)
    assert "note.txt" not in json.dumps(summary_m, ensure_ascii=False)
    assert not (outm / "note.json").exists()
