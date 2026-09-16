"""R2036：parser_registry 快照冻结 + 契约拒绝矩阵的 CLI 端到端面（真实子进程）。

探针背景（outputs/autonomous/probe_registry_r2036.py，main 6c6d398）：
main 侧 test_capability_snapshot.py / test_source_types.py 已在**进程内**
锁死快照冻结与 register() 拒绝矩阵，test_plugin_myx_fullchain 仅经子进程
覆盖 source_type pattern 一种拒绝形态（"MyX"）；批次 21 行为收紧（注册后
改类属性不影响注册表）与批次 20 契约拒绝（bool/0/负 priority、大写/无点
extension、空 source_types、未知 family、内置绑定冲突、双插件类型绑定
先注册者胜）在**真实 CLI 通道**（--plugin 导入 → 结构化 errors 信封）
零覆盖。本文件锁三项，全部 subprocess 走 main venv 真实 CLI。

被测对象解析：与 test_plugin_cli_spec_forms.py 同规——经
`git worktree list` 动态定位 branch=refs/heads/main 的 worktree，subprocess
走其 venv（r54 只读跨 worktree 授权：PYTHONDONTWRITEBYTECODE=1，cwd/
PYTHONPATH 指向临时目录与目标根，目标 worktree 零写入）。目标缺失 →
显式 SKIP，绝不伪造通过。
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

_WORKTREE_ROOT = Path(__file__).resolve().parent.parent

# 注册后再改类属性（模块顶层，import 期完成）——批次 21 行为收紧场景：
# priority/extensions/source_types/version/locator_family/__qualname__ 全部
# 在 @register 之后被改写，注册表面必须仍显示注册瞬间冻结值。
_PLUGIN_MUTATE = (
    "from app.parser_registry import register\n"
    "from app.parsers.base import Parser\n"
    "\n"
    "\n"
    "@register\n"
    "class FrzDemoParser(Parser):\n"
    '    name = "r2036_frz"\n'
    '    version = "1.0.0"\n'
    '    supported_extensions = (".r2036frz",)\n'
    "    priority = 50\n"
    '    source_types = ("r2036frz_type",)\n'
    '    locator_family = "line_address"\n'
    "\n"
    "    def parse(self, path, source_hash):\n"
    "        raise NotImplementedError\n"
    "\n"
    "\n"
    "FrzDemoParser.priority = 1\n"
    'FrzDemoParser.supported_extensions = (".r2036hij",)\n'
    'FrzDemoParser.source_types = ("hijacked_type",)\n'
    'FrzDemoParser.version = "9.9.9"\n'
    'FrzDemoParser.locator_family = "container_line"\n'
    'FrzDemoParser.__qualname__ = "FakeQualname"\n'
)


def _bad_plugin(name: str, body: str) -> str:
    # 基底契约字段齐全且合法，body 的改写是唯一非法点（单一变量原则）
    return (
        "from app.parser_registry import register\n"
        "from app.parsers.base import Parser\n"
        "\n"
        "\n"
        "@register\n"
        f"class BadParser(Parser):\n"
        f"    name = {name!r}\n"
        '    version = "test/2036"\n'
        '    supported_extensions = (".r2036bad",)\n'
        "    priority = 50\n"
        '    source_types = ("r2036bad_type",)\n'
        '    locator_family = "line_address"\n'
        f"{body}\n"
        "    def parse(self, path, source_hash):\n"
        "        raise NotImplementedError\n"
    )


# (模块名, 非法声明体, message 必含的字段级线索)——11 类拒绝形态的代表 8 类
_REJECT_CASES = [
    (
        "r2036t_boolpri", "    priority = True\n", "priority",
    ),  # bool 是 int 子类但显式拒绝
    ("r2036t_zeropri", "    priority = 0\n", "priority"),
    (
        "r2036t_upperext", '    supported_extensions = (".R2036X",)\n',
        "supported_extensions",
    ),
    (
        "r2036t_nodotext", '    supported_extensions = ("r2036x",)\n',
        "supported_extensions",
    ),
    ("r2036t_emptyst", "    source_types = ()\n", "不得为空"),
    (
        "r2036t_hyphenst",
        '    source_types = ("r2036-x",)\n    locator_family = "line_address"\n',
        "pattern",
    ),
    (
        "r2036t_badfam",
        '    source_types = ("r2036fam",)\n    locator_family = "vector"\n',
        "locator_family",
    ),
    (
        "r2036t_builtinclash",
        '    source_types = ("pdf",)\n    locator_family = "line_address"\n',
        "pdf",
    ),
]


def _bind_plugin(name: str, ext: str, priority: int, family: str, cls: str) -> str:
    return (
        "from app.parser_registry import register\n"
        "from app.parsers.base import Parser\n"
        "\n"
        "\n"
        "@register\n"
        f"class {cls}(Parser):\n"
        f"    name = {name!r}\n"
        '    version = "test/2036"\n'
        f"    supported_extensions = ({ext!r},)\n"
        f"    priority = {priority}\n"
        '    source_types = ("r2036shared",)\n'
        f"    locator_family = {family!r}\n"
        "\n"
        "    def parse(self, path, source_hash):\n"
        "        raise NotImplementedError\n"
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
            if (current / "app" / "parser_registry.py").is_file():
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
    reason="未找到含 app/parser_registry.py 的 main worktree（git worktree list）",
)


def _run_cli(plugin_dir: Path, root: Path, *args: str) -> subprocess.CompletedProcess:
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


def test_post_registration_mutation_frozen_on_cli(tmp_path: Path) -> None:
    """注册后改类属性（含 __qualname__）经真实 CLI 三面全部显示注册瞬间值：

    - list-parsers --json 行五字段（priority/extensions/source_types/
      locator_family/version）全为 @register 瞬间值，不吃改写；
    - explain-parser 胜者候选 priority 用快照值；被劫持扩展名（改写注入的
      .r2036hij）对 auto 发现不可见 → unsupported_type rc 1；
    - inspect-parser 六键中 qualname 冻结为真名（非 FakeQualname）。
    """
    assert _MAIN_ROOT is not None
    (tmp_path / "r2036t_frz_mod.py").write_text(_PLUGIN_MUTATE, encoding="utf-8")

    r = _run_cli(tmp_path, _MAIN_ROOT, "list-parsers", "--plugin", "r2036t_frz_mod", "--json")
    assert r.returncode == 0, f"rc={r.returncode} err={r.stderr}"
    row = next(x for x in json.loads(r.stdout) if x["name"] == "r2036_frz")
    assert row["priority"] == 50          # 改写 priority=1 不生效
    assert row["extensions"] == [".r2036frz"]  # 改写 .r2036hij 不生效
    assert row["source_types"] == ["r2036frz_type"]
    assert row["locator_family"] == "line_address"
    assert row["version"] == "1.0.0"

    e = _run_cli(
        tmp_path, _MAIN_ROOT,
        "explain-parser", "x.r2036frz", "--plugin", "r2036t_frz_mod", "--json",
    )
    assert e.returncode == 0
    exp = json.loads(e.stdout)
    assert set(exp) == {"extension", "candidates", "winner", "reason", "tied_names"}
    assert exp["winner"] == "r2036_frz"
    assert exp["candidates"][0]["priority"] == 50

    hij = _run_cli(
        tmp_path, _MAIN_ROOT,
        "explain-parser", "x.r2036hij", "--plugin", "r2036t_frz_mod", "--json",
    )
    assert hij.returncode == 1
    assert json.loads(hij.stderr)["errors"][0]["code"] == "unsupported_type"

    i = _run_cli(
        tmp_path, _MAIN_ROOT,
        "inspect-parser", "r2036_frz", "--plugin", "r2036t_frz_mod", "--json",
    )
    assert i.returncode == 0
    cap = json.loads(i.stdout)
    assert set(cap) == {
        "name", "version", "module", "qualname", "loaded_via", "plugin_spec",
    }
    assert cap["qualname"] == "FrzDemoParser"  # 非改写的 FakeQualname
    assert cap["version"] == "1.0.0"
    assert cap["loaded_via"] == "plugin"
    assert cap["plugin_spec"] == "r2036t_frz_mod"


def test_contract_rejection_matrix_via_cli(tmp_path: Path) -> None:
    """契约拒绝矩阵经 --plugin 导入 → 每类均 plugin_register_failed：
    rc 1 / error_type=ParserRegistrationError / plugin 字段保留原 spec /
    无 traceback / message 含对应字段级线索（与 CLAUDE.md 批次 20/21 逐项一致）。"""
    assert _MAIN_ROOT is not None
    for mod, body, hint in _REJECT_CASES:
        (tmp_path / f"{mod}.py").write_text(
            _bad_plugin(mod.replace("r2036t_", "r2036tb_"), body), encoding="utf-8"
        )
        r = _run_cli(tmp_path, _MAIN_ROOT, "list-parsers", "--plugin", mod)
        assert r.returncode == 1, (
            f"module={mod} rc={r.returncode}（契约非法必须 fail-fast 拒绝）"
            f" out={r.stdout[:200]} err={r.stderr[:300]}"
        )
        err = json.loads(r.stderr)["errors"][0]
        assert err["code"] == "plugin_register_failed", f"{mod}: {err}"
        assert err["error_type"] == "ParserRegistrationError", f"{mod}: {err}"
        assert err["plugin"] == mod
        assert "traceback" not in err
        assert hint in err["message"], f"{mod}: message={err['message']!r}"


def test_two_plugin_family_binding_first_registered_wins(tmp_path: Path) -> None:
    """两插件声明同一新 source_type 不同 family：后注册者被拒（两种加载序
    均拒绝第二个 spec），错误带"已全局绑定……先注册者胜"并可追溯到败者类。"""
    assert _MAIN_ROOT is not None
    (tmp_path / "r2036t_bind_a.py").write_text(
        _bind_plugin("r2036t_bind_a", ".r2036sza", 60, "line_address", "BindAParser"),
        encoding="utf-8",
    )
    (tmp_path / "r2036t_bind_b.py").write_text(
        _bind_plugin(
            "r2036t_bind_b", ".r2036szb", 61, "structural_index", "BindBParser"
        ),
        encoding="utf-8",
    )
    for first, second in (("r2036t_bind_a", "r2036t_bind_b"),
                          ("r2036t_bind_b", "r2036t_bind_a")):
        r = _run_cli(
            tmp_path, _MAIN_ROOT, "list-parsers",
            "--plugin", first, "--plugin", second,
        )
        assert r.returncode == 1, f"{first}->{second}: rc={r.returncode}"
        err = json.loads(r.stderr)["errors"][0]
        assert err["code"] == "plugin_register_failed"
        assert err["error_type"] == "ParserRegistrationError"
        # 先注册者胜：失败的总是第二个 spec
        assert err["plugin"] == second, f"{first}->{second}: {err}"
        assert "已全局绑定" in err["message"]
        assert "r2036shared" in err["message"]
        assert "先注册者胜" in err["message"]
