"""批次 24 Phase A 测试：registration provenance（D1 上下文 + D2 快照冻结）。

裁决边界（Batch 24 Step 1 APPROVED AFTER D1 REVISION）：
- loader 建立上下文、register() 在调用瞬间消费冻结；禁止任何事后推断
  （cls.__module__ / sys.modules / 已加载模块集合 / import graph）；
- 无上下文注册（内置/预 import）→ loaded_via="builtin", plugin_spec=null；
- load_plugins 每个 spec 独立进入上下文（plugin_spec=原始 spec 字符串），
  import 与注册 hook 全程在上下文内；
- 注册语法（装饰器/直接调用）≠ 加载来源；同一 class 不同时刻经不同
  spec 注册 → 各 snapshot 各归各 provenance，禁止按 class identity 合并；
- 上下文栈式可嵌套（最内层生效、退出恢复外层）、异常安全；
- loaded_via 值域封闭 "builtin"|"plugin"；plugin_spec 拒绝路径形态。
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

import app.parser_registry as pr
from app.parser_registry import (
    ParserRegistrationError,
    capability,
    register,
)
from app.parsers.base import Parser


@pytest.fixture
def fresh_registry(monkeypatch):
    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    monkeypatch.setattr(pr, "_capabilities", dict(pr._capabilities))
    return pr._capabilities


@pytest.fixture
def plugin_env(tmp_path: Path, monkeypatch):
    """sys.path 注入 + 注册表副本隔离 + 首载备忘重置 + sys.modules 清理。"""
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    monkeypatch.setattr(pr, "_capabilities", dict(pr._capabilities))
    from app import plugin_loader as pl

    monkeypatch.setattr(pl, "_FIRST_LOAD", {})
    yield tmp_path
    for key, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and str(tmp_path) in str(f):
            del sys.modules[key]


def _make_cls(name: str, ext: str):
    """构造可注册的最小 parser 类（动态创建，__qualname__/__module__ 可控）。"""
    return type(
        f"Prov_{name}",
        (Parser,),
        {
            "name": name,
            "version": "test/24",
            "supported_extensions": (ext,),
            "priority": 70,
            "source_types": ("text",),
            "locator_family": "line_address",
            "parse": lambda self, path, source_hash: None,  # pragma: no cover
        },
    )


def _write_plugin(directory: Path, mod_name: str, source: str) -> None:
    (directory / f"{mod_name}.py").write_text(source, encoding="utf-8")


# ---------- 类别①：顶层 / 副模块 / helper 转注册均归当前 plugin spec ----------

_PLUGIN_TOPLEVEL = '''"""批次 24 测试插件：顶层 @register 自注册。"""
from app.parser_registry import register
from app.parsers.base import Parser


@register
class TopPlug(Parser):
    name = "prov_top"
    version = "test/1"
    supported_extensions = (".provtop",)
    priority = 61
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):  # pragma: no cover
        raise NotImplementedError
'''

_PKG_INIT = "from . import leaf\n"

_PKG_LEAF = '''"""批次 24 测试插件包的副模块：注册发生在 leaf，加载发生在包。"""
from app.parser_registry import register
from app.parsers.base import Parser


@register
class PkgLeafPlug(Parser):
    name = "prov_pkg_leaf"
    version = "test/1"
    supported_extensions = (".provleaf",)
    priority = 62
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):  # pragma: no cover
        raise NotImplementedError
'''

_HOLDER = '''"""批次 24 测试：只定义类、不注册（类定义在 prov_holder）。"""
from app.parsers.base import Parser


class HolderPlug(Parser):
    name = "prov_helper"
    version = "test/1"
    supported_extensions = (".provhelp",)
    priority = 63
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):  # pragma: no cover
        raise NotImplementedError
'''

_REGISTRAR = '''"""批次 24 测试：helper 转注册别处定义的类（直接调用 register）。"""
from app.parser_registry import register
from prov_holder import HolderPlug

register(HolderPlug)
'''


def test_toplevel_registration_attributed_to_spec(plugin_env: Path):
    from app.plugin_loader import load_plugins

    _write_plugin(plugin_env, "prov_top_plug", _PLUGIN_TOPLEVEL)
    load_plugins(["prov_top_plug"])
    cap = capability("prov_top")
    assert cap.loaded_via == "plugin"
    assert cap.plugin_spec == "prov_top_plug"
    assert cap.module == "prov_top_plug"
    assert cap.qualname == "TopPlug"


def test_submodule_registration_attributed_to_spec(plugin_env: Path):
    """包加载触发副模块注册：provenance 归进入上下文的 spec（包名），
    identity 冻结真实定义模块（prov_pkg.leaf）。"""
    from app.plugin_loader import load_plugins

    pkg = plugin_env / "prov_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(_PKG_INIT, encoding="utf-8")
    (pkg / "leaf.py").write_text(_PKG_LEAF, encoding="utf-8")
    load_plugins(["prov_pkg"])
    cap = capability("prov_pkg_leaf")
    assert cap.loaded_via == "plugin"
    assert cap.plugin_spec == "prov_pkg"
    assert cap.module == "prov_pkg.leaf"
    assert cap.qualname == "PkgLeafPlug"


def test_helper_registration_no_module_guessing(plugin_env: Path):
    """helper 转注册：provenance 归调用时刻的 spec（registrar），而非
    按 cls.__module__ 猜成 holder——注册位置 ≠ 加载来源。"""
    from app.plugin_loader import load_plugins

    _write_plugin(plugin_env, "prov_holder", _HOLDER)
    _write_plugin(plugin_env, "prov_registrar", _REGISTRAR)
    load_plugins(["prov_registrar"])
    cap = capability("prov_helper")
    assert cap.loaded_via == "plugin"
    assert cap.plugin_spec == "prov_registrar"
    assert cap.module == "prov_holder"
    assert cap.qualname == "HolderPlug"


# ---------- 类别②：registration-by-registration 冻结 + 预 import 反证 ----------

_PLUGIN_PREIMPORT = '''"""批次 24 测试插件：预 import 反证用（顶层自注册）。"""
from app.parser_registry import register
from app.parsers.base import Parser


@register
class PrePlug(Parser):
    name = "prov_pre"
    version = "test/1"
    supported_extensions = (".provpre",)
    priority = 64
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):  # pragma: no cover
        raise NotImplementedError
'''


def test_preimported_plugin_registers_as_builtin(plugin_env: Path):
    """反证：插件模块经普通 import（不经 load_plugins）→ 无上下文 →
    builtin；事后补 load_plugins 也不改写已冻结的 provenance
    （禁止按已加载模块集合做事后推断）。"""
    from app.plugin_loader import load_plugins

    _write_plugin(plugin_env, "prov_pre_plug", _PLUGIN_PREIMPORT)
    importlib.import_module("prov_pre_plug")
    cap = capability("prov_pre")
    assert cap.loaded_via == "builtin"
    assert cap.plugin_spec is None
    out = load_plugins(["prov_pre_plug"])  # 模块已缓存，无新注册
    assert out == [{"plugin": "prov_pre_plug", "parsers_added": []}]
    assert capability("prov_pre").loaded_via == "builtin"
    assert capability("prov_pre").plugin_spec is None


def test_same_class_different_spec_own_provenance(fresh_registry, monkeypatch):
    """同一 class 对象不同时刻经不同 spec 注册 → 各 snapshot 各归各，
    禁止按 class identity 合并；旧快照不被新注册改写。"""
    cls = _make_cls("prov_dual", ".provdual")
    with pr._plugin_registration_context("plug.alpha"):
        register(cls)
    cap_alpha = capability("prov_dual")
    assert (cap_alpha.loaded_via, cap_alpha.plugin_spec) == ("plugin", "plug.alpha")

    monkeypatch.setattr(pr, "_registry", {})
    monkeypatch.setattr(pr, "_capabilities", {})
    with pr._plugin_registration_context("plug.beta"):
        register(cls)
    cap_beta = capability("prov_dual")
    assert (cap_beta.loaded_via, cap_beta.plugin_spec) == ("plugin", "plug.beta")
    assert cap_alpha.plugin_spec == "plug.alpha"


def test_decorator_vs_direct_same_provenance(fresh_registry):
    """注册语法（装饰器/直接调用）不构成不同 loaded_via——只认当前
    active context。"""
    with pr._plugin_registration_context("plug.style"):
        @register
        class DecoPlug(Parser):
            name = "prov_deco"
            version = "test/1"
            supported_extensions = (".provdeco",)
            priority = 65
            source_types = ("text",)
            locator_family = "line_address"

            def parse(self, path, source_hash):  # pragma: no cover
                raise NotImplementedError

        register(_make_cls("prov_direct", ".provdirect"))
    assert capability("prov_deco").plugin_spec == "plug.style"
    assert capability("prov_direct").plugin_spec == "plug.style"
    # 无上下文注册仍是 builtin（基线）
    register(_make_cls("prov_plain", ".provplain"))
    plain = capability("prov_plain")
    assert plain.loaded_via == "builtin" and plain.plugin_spec is None


# ---------- 类别③：嵌套 / 异常上下文恢复 ----------

def test_nested_context_innermost_wins(fresh_registry):
    with pr._plugin_registration_context("plug.outer"):
        register(_make_cls("prov_out", ".provout"))
        with pr._plugin_registration_context("plug.inner"):
            register(_make_cls("prov_in", ".provin"))
        register(_make_cls("prov_out2", ".provout2"))
    assert capability("prov_out").plugin_spec == "plug.outer"
    assert capability("prov_in").plugin_spec == "plug.inner"
    assert capability("prov_out2").plugin_spec == "plug.outer"
    assert pr._registration_context.get() is None


def test_exception_restores_context_to_none(fresh_registry):
    with pytest.raises(RuntimeError):
        with pr._plugin_registration_context("plug.boom"):
            register(_make_cls("prov_boom", ".provboom"))
            raise RuntimeError("boom")
    assert pr._registration_context.get() is None
    register(_make_cls("prov_after", ".provafter"))
    cap = capability("prov_after")
    assert cap.loaded_via == "builtin" and cap.plugin_spec is None


def test_nested_exception_restores_outer(fresh_registry):
    with pr._plugin_registration_context("plug.outer2"):
        with pytest.raises(RuntimeError):
            with pr._plugin_registration_context("plug.inner2"):
                raise RuntimeError("inner boom")
        register(_make_cls("prov_still_out", ".provstillout"))
    assert capability("prov_still_out").plugin_spec == "plug.outer2"
    assert pr._registration_context.get() is None


def test_failed_plugin_load_leaves_context_clean(plugin_env: Path):
    """loader 层异常安全：导入抛错 → PluginLoadError，上下文恢复干净，
    后续注册不受污染。"""
    from app.plugin_loader import PluginLoadError, load_plugins

    _write_plugin(plugin_env, "prov_fail_plug", 'raise RuntimeError("load boom")\n')
    with pytest.raises(PluginLoadError) as ei:
        load_plugins(["prov_fail_plug"])
    assert ei.value.code == "plugin_import_failed"
    assert pr._registration_context.get() is None
    register(_make_cls("prov_clean", ".provclean"))
    cap = capability("prov_clean")
    assert cap.loaded_via == "builtin" and cap.plugin_spec is None


def test_plugin_spec_rejects_paths(fresh_registry):
    """plugin_spec 保存原始字符串但拒绝路径形态（绝对路径/分隔符）。"""
    for bad in ("C:/abs/path.py", "/abs/path.py", "rel/path.py", "a\\b.py", ""):
        with pytest.raises(ValueError):
            with pr._plugin_registration_context(bad):
                pass
    assert pr._registration_context.get() is None


# ---------- 类别④：注册后漂移不影响快照 ----------

def test_snapshot_frozen_against_class_and_context_mutation(fresh_registry):
    cls = _make_cls("prov_drift", ".provdrift")
    orig_module, orig_qualname = cls.__module__, cls.__qualname__
    with pr._plugin_registration_context("plug.freeze"):
        register(cls)
    cap_frozen = capability("prov_drift")
    # 注册后改 class identity 属性 + version + 进入新上下文 → 不漂移
    cls.__module__ = "fake.smuggled"
    cls.__qualname__ = "FakeSmuggled"
    cls.version = "hacked/1"
    with pr._plugin_registration_context("plug.late"):
        cap_late = capability("prov_drift")
        cap_by_cls = capability(cls)
    for cap in (cap_frozen, cap_late, cap_by_cls):
        assert cap.module == orig_module
        assert cap.qualname == orig_qualname
        assert cap.version == "test/24"
        assert cap.loaded_via == "plugin"
        assert cap.plugin_spec == "plug.freeze"


def test_builtin_registered_names_all_builtin(fresh_registry):
    """内置注册路径（含随项目分发的 markdown_enhanced）全为 builtin/null。"""
    for name, cap in fresh_registry.items():
        assert cap.loaded_via == "builtin", name
        assert cap.plugin_spec is None, name
        assert isinstance(cap.module, str) and cap.module
        assert isinstance(cap.qualname, str) and cap.qualname


def test_capability_unknown_name_still_explicit_failure(fresh_registry):
    """provenance 纯只读：不参与错误分支，未注册仍显式失败。"""
    with pytest.raises(ParserRegistrationError):
        capability("never_registered_prov")
