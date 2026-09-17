"""R2043：app.cli parse 的输入/参数边界信封锁（真实 CLI 子进程）。

探针背景（outputs/autonomous/probe_parse_edges_r2043.py + .out，main 6c6d398，
C0 通过 + E1–E8 全部核实，main 前后 clean）：main 侧 test_pipeline_integration
的 CLI 面仅锁 happy path + 缺文件/假 PDF/未知扩展三负例（另有 legacy
positional 拒绝一测）；--max-chars 边界、垃圾输入 × 扩展名矩阵、编码
边缘、-o 输出路径族的 CLI 面**零覆盖**。本轮锁三组：

1. **--max-chars 边界信封**——0 / -5 / 31 → rc 1 + 结构化 errors JSON
   `chunker_failed`（StructuralChunker 下限 32 的 ValueError 被 process_single
   兜底，不崩溃、无 traceback、无半成品输出文件残留）；32（下限边界）与
   10^9 → rc 0 且每 chunk 非空 source_element_ids（关键不变量在极值下守住）。
   argparse type=int 对负数的解析（`-5` 非选项前缀冲突）一并锁。
2. **垃圾输入 × 扩展名矩阵**——0 字节 .pdf → `pdfplumber_open_failed`；
   0 字节 .docx / 随机非 ZIP 字节 .docx / 截断 ZIP .docx → `docx_open_failed`；
   0 字节 .md（--parser markdown）→ `no_extracted_elements`（空内容检查
   先于写盘）；坏 JSON .ipynb（--parser auto 发现 ipynb parser）→
   `ipynb_invalid_json`。全形态：rc 1 + errors JSON 可解析 + 无残留 + 无
   traceback（单文件失败不崩溃契约的 CLI 面）。
3. **编码边缘 + 输出路径族**——UTF-8 BOM .md → rc 0 且 `\\ufeff` **留存**
   content（main 进程内已锁基线：test_parsers_text_edges10 "留在 content 里
   不剥" + test_parsers_markdown_edges12 BOM 杀标题；CLI 面首次确认，非缺陷）；
   CRLF .md → CR 不残留 content；中文+emoji .md → 内容保真 + validate rc 0；
   Latin-1 字节 .md → rc 0 + `\\ufffd` 替换符进 content（markdown_parser
   UnicodeDecodeError → errors="replace" 回退，main 进程内已锁
   test_parsers_markdown_edges2/3/4/7；CLI 面首次确认，静默替换零 warning
   属已锁沉默，观察记录）；-o 深不存在目录 → 自动 mkdir parents + rc 0；
   -o 已存在目录 → `write_failed` rc 1。

被测对象解析：与 test_annotation_env_r2041.py 同规——经
`git worktree list` 动态定位 branch=refs/heads/main 的 worktree，subprocess
走其 venv（只读跨 worktree 授权：PYTHONDONTWRITEBYTECODE=1，cwd/PYTHONPATH
指向临时目录与目标根，目标 worktree 零写入）。目标缺失 → 显式 SKIP，
绝不伪造通过。
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import zipfile
from pathlib import Path

import pytest

_WORKTREE_ROOT = Path(__file__).resolve().parent.parent

MD_BODY = (
    "# 标题一\n\n这是第一个段落，包含足够长度的文本以便分块。\n\n"
    "## 小节\n\n第二个段落内容。\n"
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


def _stderr_errors(stderr: str) -> list[dict]:
    """提取结构化 errors JSON（失败信封固定形态 {"schema_version","input","errors"}）。"""
    m = re.search(r"\{.*\"errors\".*\}", stderr, re.S)
    if not m:
        return []
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    return obj.get("errors", []) if isinstance(obj, dict) else []


def _codes(stderr: str) -> list[str]:
    return [e.get("code", "") for e in _stderr_errors(stderr)]


def _element_texts(out_json: Path) -> str:
    v = json.loads(out_json.read_text(encoding="utf-8"))
    return "\n".join(el.get("content") or "" for el in v.get("elements", []))


# ---------- 1. --max-chars 边界信封 ----------

def test_max_chars_boundary_envelope_cli(tmp_path: Path):
    """0/-5/31 → chunker_failed 结构化信封；32/10^9 → rc 0 + 不变量守住。"""
    src = tmp_path / "in.md"
    src.write_text(MD_BODY, encoding="utf-8")

    for bad in ("0", "-5", "31"):
        out = tmp_path / f"mc_{bad.replace('-', 'neg')}.json"
        rc, so, se = _run_cli(
            ["parse", str(src), "-o", str(out), "--parser", "markdown",
             "--max-chars", bad], tmp_path)
        assert rc == 1, f"max-chars {bad}: 期望 rc 1，实际 {rc}\nstderr={se[:500]}"
        assert _codes(se) == ["chunker_failed"], (
            f"max-chars {bad}: codes={_codes(se)}")
        assert not out.exists(), f"max-chars {bad}: 失败不得残留输出文件"
        assert "Traceback (most recent call last)" not in se

    for good in ("32", "1000000000"):
        out = tmp_path / f"mc_ok_{good}.json"
        rc, so, se = _run_cli(
            ["parse", str(src), "-o", str(out), "--parser", "markdown",
             "--max-chars", good], tmp_path)
        assert rc == 0, f"max-chars {good}: 期望 rc 0，实际 {rc}\nstderr={se[:500]}"
        v = json.loads(out.read_text(encoding="utf-8"))
        assert len(v["chunks"]) >= 1
        # 关键不变量：极小/极大 max_chars 下每 chunk 非空 source_element_ids
        for c in v["chunks"]:
            assert c["source_element_ids"], (
                f"max-chars {good}: 出现空 source_element_ids chunk")


# ---------- 2. 垃圾输入 × 扩展名矩阵 ----------

def _build_valid_docx_bytes() -> bytes:
    """最小合法 DOCX（zipfile 构造，形状复制 R2041 夹具法）。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?>\n<Types xmlns="http://schemas.openxmlformats.'
            'org/package/2006/content-types"/>',
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0"?>\n<Relationships xmlns="http://schemas.'
            'openxmlformats.org/package/2006/relationships"/>',
        )
    return buf.getvalue()


def test_garbage_input_extension_matrix_cli(tmp_path: Path):
    """六形态垃圾输入 → rc 1 + 精确错误码 + 无残留 + 无 traceback。"""
    valid = _build_valid_docx_bytes()
    cases: list[tuple[str, Path, list[str], list[str]]] = []

    p = tmp_path / "empty.pdf"; p.write_bytes(b"")
    cases.append(("0字节 .pdf", p, [], ["pdfplumber_open_failed"]))

    p = tmp_path / "empty.docx"; p.write_bytes(b"")
    cases.append(("0字节 .docx", p, [], ["docx_open_failed"]))

    p = tmp_path / "rand.docx"; p.write_bytes(bytes(range(256)) * 4)
    cases.append(("随机字节 .docx", p, [], ["docx_open_failed"]))

    p = tmp_path / "trunc.docx"; p.write_bytes(valid[: max(1, len(valid) // 3)])
    cases.append(("截断 ZIP .docx", p, [], ["docx_open_failed"]))

    p = tmp_path / "empty.md"; p.write_bytes(b"")
    cases.append(("0字节 .md", p, ["markdown"], ["no_extracted_elements"]))

    p = tmp_path / "bad.ipynb"; p.write_text("{not json at all", encoding="utf-8")
    cases.append(("坏 JSON .ipynb", p, ["auto"], ["ipynb_invalid_json"]))

    for name, src, extra, want_codes in cases:
        out = tmp_path / f"out_{src.name}.json"
        args = ["parse", str(src), "-o", str(out)]
        for flag in extra:
            args += ["--parser", flag]
        rc, so, se = _run_cli(args, tmp_path)
        assert rc == 1, f"{name}: 期望 rc 1，实际 {rc}\nstderr={se[:500]}"
        assert _codes(se) == want_codes, f"{name}: codes={_codes(se)}"
        # errors JSON 信封可解析（结构化失败而非崩溃）
        errs = _stderr_errors(se)
        assert errs and errs[0].get("message")
        assert not out.exists(), f"{name}: 失败不得残留输出文件"
        assert "Traceback (most recent call last)" not in se, f"{name}: 泄漏 traceback"


# ---------- 3. 编码边缘 + 输出路径族 ----------

def test_encoding_edges_and_output_path_family_cli(tmp_path: Path):
    """BOM 留存/CRLF 清理/中文 emoji 保真/Latin-1 替换 + 深目录自动建/目录拒绝。"""
    # BOM：main 已锁基线 = ﻿ 留存 content（CLI 面首次锁）
    p = tmp_path / "bom.md"
    p.write_bytes(b"\xef\xbb\xbf# Title BOM\n\nParagraph one under BOM.\n")
    out = tmp_path / "bom.json"
    rc, _, se = _run_cli(["parse", str(p), "-o", str(out), "--parser", "markdown"],
                         tmp_path)
    assert rc == 0, se[:500]
    assert "﻿" in _element_texts(out)

    # CRLF：CR 不得残留 content
    p = tmp_path / "crlf.md"
    p.write_bytes("# Title CRLF\r\n\r\nPara one line.\r\n\r\nPara two line.\r\n"
                  .encode("utf-8"))
    out = tmp_path / "crlf.json"
    rc, _, se = _run_cli(["parse", str(p), "-o", str(out), "--parser", "markdown"],
                         tmp_path)
    assert rc == 0, se[:500]
    assert "\r" not in _element_texts(out)

    # 中文 + emoji + 日文假名 + 重音符：内容保真 + validate rc 0
    body = ("# 中文标题测试\n\n段落包含中文与表情 🚀🔥 和日文 かな，"
            "以及重音符 àéü。\n\n## 第二节\n\n更多中文内容，长度足够。\n")
    p = tmp_path / "zh.md"
    p.write_text(body, encoding="utf-8")
    out = tmp_path / "zh.json"
    rc, _, se = _run_cli(["parse", str(p), "-o", str(out), "--parser", "markdown"],
                         tmp_path)
    assert rc == 0, se[:500]
    joined = _element_texts(out)
    for needle in ("中文标题测试", "🚀", "かな", "àéü"):
        assert needle in joined, f"保真失败: 缺 {needle!r}"
    rc2, _, _ = _run_cli(["validate", str(out)], tmp_path)
    assert rc2 == 0

    # Latin-1 字节（非法 UTF-8）：errors="replace" 回退 → rc 0 + � 进 content
    # （main 已锁基线 test_parsers_markdown_edges2/3/4/7；CLI 面首次锁）
    p = tmp_path / "latin.md"
    p.write_bytes(b"# Caf\xe9 Latin\n\nContenu avec accent: \xe0\xe9\xe8.\n")
    out = tmp_path / "latin.json"
    rc, _, se = _run_cli(["parse", str(p), "-o", str(out), "--parser", "markdown"],
                         tmp_path)
    assert rc == 0, se[:500]
    assert "�" in _element_texts(out)

    # -o 深不存在目录：mkdir parents 自动建 + rc 0
    src_ok = tmp_path / "zh.md"
    deep = tmp_path / "a" / "b" / "c" / "deep.json"
    rc, _, se = _run_cli(["parse", str(src_ok), "-o", str(deep),
                          "--parser", "markdown"], tmp_path)
    assert rc == 0, se[:500]
    assert deep.is_file()

    # -o 已存在目录：write_failed 结构化错误 + rc 1
    adir = tmp_path / "adir"
    adir.mkdir()
    rc, _, se = _run_cli(["parse", str(src_ok), "-o", str(adir),
                          "--parser", "markdown"], tmp_path)
    assert rc == 1, se[:500]
    assert _codes(se) == ["write_failed"]
    assert "Traceback (most recent call last)" not in se
