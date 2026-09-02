"""批次 24 Phase B 收口测试：inspect 契约封口（GPT Phase B 门槛）。

在 Phase A 四类验收与既有三个 JSON 键集锁（批次 21/22/23 契约测试 +
Phase A 键集锁回归）之外，补齐：
- inspect JSON 六键 exact-set 锁（对全部已注册 parser 参数化）；
- builtin 的 plugin_spec 恒为 null（全部内置注册逐一验证）；
- plugin spec 与输出均无路径泄漏（subprocess 真实 CLI + tmp_path 实证）；
- inspect ↔ snapshot 逐字段一致（CLI 输出即冻结快照，非活读）。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import app.parser_registry as pr
from app.cli import main as app_main
from app.parser_registry import capability

ROOT = Path(__file__).resolve().parent.parent

INSPECT_KEYS = {
    "name", "version", "module", "qualname", "loaded_via", "plugin_spec",
}


@pytest.mark.parametrize("name", sorted(pr._capabilities))
def test_inspect_json_exact_keys_and_snapshot_equality(name, capfd):
    """六键 exact-set 锁 + inspect↔snapshot 逐字段一致（含 null 不省略）。"""
    rc = app_main(["inspect-parser", name, "--json"])
    assert rc == 0
    payload = json.loads(capfd.readouterr().out)
    assert set(payload.keys()) == INSPECT_KEYS
    cap = capability(name)
    assert payload == {
        "name": cap.name,
        "version": cap.version,
        "module": cap.module,
        "qualname": cap.qualname,
        "loaded_via": cap.loaded_via,
        "plugin_spec": cap.plugin_spec,
    }


def test_builtin_plugin_spec_always_null(capfd):
    """builtin 的 plugin_spec 恒为 null：对全部内置注册逐一验证。"""
    builtins = [
        name for name, cap in pr._capabilities.items()
        if cap.loaded_via == "builtin"
    ]
    assert builtins, "预期至少存在内置注册"
    for name in builtins:
        rc = app_main(["inspect-parser", name, "--json"])
        assert rc == 0
        payload = json.loads(capfd.readouterr().out)
        assert payload["plugin_spec"] is None, name
        assert payload["loaded_via"] == "builtin", name


def _run_cli(argv: list[str], env_extra: dict | None = None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *argv],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(ROOT), env=env, timeout=120,
    )


_CLOSURE_PLUGIN = '''"""批次 24 Phase B 收口测试插件（.clos24）。"""
from app.parser_registry import register
from app.parsers.base import Parser


@register
class ClosurePlug(Parser):
    name = "closure_plug_b24"
    version = "test/1"
    supported_extensions = (".clos24",)
    priority = 2
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):  # pragma: no cover
        raise NotImplementedError
'''


def test_plugin_output_no_path_leak(tmp_path):
    """plugin spec 与输出均无路径泄漏：插件文件真实存在于带分隔符的
    tmp_path 下，经 --plugin 加载后 inspect 输出只含 dotted 名——
    原始 stdout 不含 tmp_path、不含任何路径分隔符（module/qualname/
    plugin_spec 三键逐一验证）。"""
    (tmp_path / "closure_plug_b24.py").write_text(_CLOSURE_PLUGIN, encoding="utf-8")
    r = _run_cli(
        ["inspect-parser", "closure_plug_b24",
         "--plugin", "closure_plug_b24", "--json"],
        env_extra={"PYTHONPATH": str(tmp_path)},
    )
    assert r.returncode == 0, r.stderr
    assert str(tmp_path) not in r.stdout
    payload = json.loads(r.stdout)
    assert set(payload.keys()) == INSPECT_KEYS
    assert payload["loaded_via"] == "plugin"
    assert payload["plugin_spec"] == "closure_plug_b24"
    for key in ("module", "qualname", "plugin_spec"):
        assert "/" not in payload[key], key
        assert "\\" not in payload[key], key
        assert not Path(payload[key]).is_absolute(), key


def test_plugin_inspect_values_match_frozen_registration(tmp_path):
    """插件 parser 的六键值与注册契约一致（dotted module 名 / 类名 /
    声明 version / plugin spec）——CLI 层与 registry 层同源封口。"""
    (tmp_path / "closure_plug_b24.py").write_text(_CLOSURE_PLUGIN, encoding="utf-8")
    r = _run_cli(
        ["inspect-parser", "closure_plug_b24",
         "--plugin", "closure_plug_b24", "--json"],
        env_extra={"PYTHONPATH": str(tmp_path)},
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["name"] == "closure_plug_b24"
    assert payload["module"] == "closure_plug_b24"
    assert payload["qualname"] == "ClosurePlug"
    assert payload["version"] == "test/1"
    assert payload["loaded_via"] == "plugin"
    assert payload["plugin_spec"] == "closure_plug_b24"
