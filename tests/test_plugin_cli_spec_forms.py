"""R2031：`--plugin` spec 形态的 CLI 层结构化分类（跨 worktree 真实 CLI）。

探针背景（outputs/autonomous/probe_plugin_loader_r2031.py，main 6c6d398）：
main 侧 test_plugin_loader.py 的 CLI 结构化失败只覆盖 missing-module 与
重名两类 spec；路径形态 / 空 spec / 带 .py 后缀 spec 只在库层
（test_parser_provenance.test_plugin_spec_rejects_paths 直接调
_plugin_registration_context）有覆盖，CLI 通道（rc 1 + errors JSON 信封
+ plugin 字段保留原始 spec + 无 traceback）零覆盖；合法插件的
inspect-parser 端到端（subprocess 真实 CLI）亦零覆盖。本文件锁这三项。

被测对象解析：插件系统（批次 18/19/24）不存在于本分支基线（2c35244），
测试经 `git worktree list` 动态定位 branch=refs/heads/main 的 worktree，
subprocess 走其 venv 真实 CLI（r54 只读跨 worktree 授权：探针只子进程 +
PYTHONDONTWRITEBYTECODE=1，cwd/PYTHONPATH 指向临时目录与目标根，目标
worktree 零写入）。目标缺失（单仓检出 / 无 venv / 无 plugin_loader）→
显式 SKIP，绝不伪造通过。
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

_WORKTREE_ROOT = Path(__file__).resolve().parent.parent

# 最小合法外部插件（批次 20/21 契约字段齐全；基类实名 Parser）
_PLUGIN_OK = (
    "from app.parser_registry import register\n"
    "from app.parsers.base import Parser\n"
    "\n"
    "\n"
    "@register\n"
    "class POkParser(Parser):\n"
    '    name = "r2031_probe"\n'
    '    version = "test/2031"\n'
    '    supported_extensions = (".r2031p",)\n'
    "    priority = 9\n"
    '    source_types = ("text",)\n'
    '    locator_family = "line_address"\n'
    "\n"
    "    def parse(self, path, source_hash):\n"
    "        raise NotImplementedError\n"
)


def _resolve_main_worktree() -> Path | None:
    """`git worktree list --porcelain` 找 branch=refs/heads/main 的 worktree。

    本文件在自跑分支（基线无插件系统）时定位并列的 main worktree；
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
            if (current / "app" / "plugin_loader.py").is_file():
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
    reason="未找到含 app/plugin_loader.py 的 main worktree（git worktree list）",
)


def _run_cli(
    plugin_dir: Path, root: Path, *args: str
) -> subprocess.CompletedProcess:
    py = _target_python(root)
    assert py is not None, "main worktree 缺 .venv 解释器"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root) + os.pathsep + str(plugin_dir)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [py, "-m", "app.cli", *args],
        capture_output=True, env=env, cwd=plugin_dir, timeout=90,
        encoding="utf-8", errors="replace",
    )


def test_cli_path_and_empty_spec_structured(tmp_path: Path) -> None:
    """路径形态与空 spec 经 CLI 通道 → rc 1 + plugin_import_failed
    （error_type=ValueError，plugin 字段保留原始 spec，无 traceback）。"""
    assert _MAIN_ROOT is not None
    (tmp_path / "r2031_probe.py").write_text(_PLUGIN_OK, encoding="utf-8")
    bad_specs = [
        "./r2031_probe.py",            # 点前缀路径形态
        str(tmp_path / "r2031_probe.py"),  # 绝对路径（含原生分隔符）
        "",                            # 空 spec
    ]
    for spec in bad_specs:
        r = _run_cli(tmp_path, _MAIN_ROOT, "list-parsers", "--plugin", spec)
        assert r.returncode == 1, f"spec={spec!r} rc={r.returncode} err={r.stderr}"
        envelope = json.loads(r.stderr)
        err = envelope["errors"][0]
        assert err["code"] == "plugin_import_failed"
        assert err["error_type"] == "ValueError"
        assert err["plugin"] == spec
        assert "traceback" not in err
        assert "dotted" in err["message"] or "路径" in err["message"]


def test_cli_dotpy_suffix_spec_module_not_package(tmp_path: Path) -> None:
    """带 .py 后缀的 spec 按 dotted 语义拆父子模块：父模块在 PYTHONPATH
    真实存在也失败 → plugin_import_failed / ModuleNotFoundError
    （"is not a package"），不做文件路径加载。"""
    assert _MAIN_ROOT is not None
    (tmp_path / "r2031_probe.py").write_text(_PLUGIN_OK, encoding="utf-8")
    r = _run_cli(tmp_path, _MAIN_ROOT, "list-parsers", "--plugin", "r2031_probe.py")
    assert r.returncode == 1
    err = json.loads(r.stderr)["errors"][0]
    assert err["code"] == "plugin_import_failed"
    assert err["error_type"] == "ModuleNotFoundError"
    assert err["plugin"] == "r2031_probe.py"
    assert "is not a package" in err["message"]


def test_cli_valid_plugin_listed_and_inspectable(tmp_path: Path) -> None:
    """合法 dotted 插件端到端 happy path：list-parsers 列出 + inspect-parser
    六键可查，provenance loaded_via=plugin / plugin_spec=原始 spec。"""
    assert _MAIN_ROOT is not None
    (tmp_path / "r2031_probe.py").write_text(_PLUGIN_OK, encoding="utf-8")
    r = _run_cli(tmp_path, _MAIN_ROOT, "list-parsers", "--plugin", "r2031_probe")
    assert r.returncode == 0
    assert "r2031_probe" in r.stdout

    i = _run_cli(
        tmp_path, _MAIN_ROOT,
        "inspect-parser", "r2031_probe", "--plugin", "r2031_probe", "--json",
    )
    assert i.returncode == 0
    cap = json.loads(i.stdout)
    assert set(cap) == {
        "name", "version", "module", "qualname", "loaded_via", "plugin_spec",
    }
    assert cap["loaded_via"] == "plugin"
    assert cap["plugin_spec"] == "r2031_probe"
