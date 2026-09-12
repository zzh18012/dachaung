"""显式外部插件加载（Stage 8 批次 19 裁决）。

- dotted 模块名（importlib.import_module）或 .py 文件路径（Stage 10
  批次 5）；不做 entry_points 扫描、YAML 扩展或内容嗅探
- `--plugin` 可重复，按出现顺序加载；同一模块重复指定为模块缓存幂等
  no-op（parsers_added 为空）
- fail-fast：首个失败抛 PluginLoadError，整条命令中止（批量路径不启动池）
- 错误契约：
  - ParserRegistrationError（仅由 register() 抛出，即 @register 重名/缺名）
    → code=plugin_register_failed
  - 导入期其他任意异常（ModuleNotFoundError/SyntaxError/顶层 ValueError 等）
    → code=plugin_import_failed
- 标准 CLI 错误 JSON 不含 traceback（to_dict() 默认省略，仅日志层保留）

批次 24：每个 spec 的 import 全程包裹 registration context
（plugin_spec=规范化前原始字符串）；插件触发的注册在 register() 调用
瞬间冻结 provenance（loaded_via="plugin"）。

Stage 10 批次 5（路径形态 spec，r43 授权）：
- 判定规则：spec 含 "/" 或 "\\"，或（大小写不敏感）以 ".py" 结尾 →
  路径分支；否则 dotted 分支。合法 dotted 模块名不含分隔符也不以
  .py 结尾，故既有合法 dotted spec 的行为逐字节不变（历史上
  "foo.py" 形态本就 import 失败，仅错误码从 plugin_import_failed
  变为 plugin_path_not_found/invalid）
- 解析规则：Path(spec).resolve()（相对调用时 cwd）；必须为已存在的
  .py 文件且文件名 stem 为合法 Python 标识符（模块名 = stem）；
  否则 plugin_path_not_found（不存在）/ plugin_path_invalid
  （非 .py 文件 / 非常规文件 / stem 非法）
- 命名冲突规则：stem 已在 sys.modules 时比对模块 __file__（resolve
  后）与目标路径——同文件 → 幂等（import_module 命中缓存，不重复
  执行注册）；不同文件或 __file__ 缺失（内置/命名空间模块，身份
  不可证）→ plugin_path_conflict。该规则同时阻止插件 shadow 标准库
  （如 json.py）
- sys.path 注入规则：父目录 append 到 sys.path **末尾**（绝不遮蔽
  既有项），try/finally 恢复（成功与失败路径都移除）；不污染后续
  解析与 worker 状态（spawn worker 继承的 sys.path 不含注入项）
- provenance：registration context 收到的是**原始 spec 字符串**
  （路径拼写按用户输入冻结，不回写 resolved 绝对路径）
- 不新增任何插件执行能力：仅既有的 importlib 加载通道，无远程加载
"""

from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path

from app.parser_registry import (
    ParserRegistrationError,
    _plugin_registration_context,
    registered_names,
)

__all__ = ["PluginLoadError", "load_plugins"]

# 本进程内每个模块**首次** load_plugins 的真实注册增量备忘（批次 19 封口
# 裁决：plugin_loaded 事件须反映首次增量，CLI 校验阶段预加载后再由批量
# 路径发事件时不得恒为空）。重复加载命中备忘，不重复导入/注册。
_FIRST_LOAD: dict[str, dict] = {}


class PluginLoadError(Exception):
    """插件加载失败的可序列化结构化错误（CLI/批处理受控通道）。"""

    def __init__(
        self,
        code: str,
        plugin: str,
        error_type: str,
        error_message: str,
        traceback_str: str | None = None,
    ) -> None:
        super().__init__(error_message)
        self.code = code
        self.plugin = plugin
        self.error_type = error_type
        self.error_message = error_message
        self.traceback_str = traceback_str

    def to_dict(self, include_traceback: bool = False) -> dict:
        d = {
            "code": self.code,
            "message": self.error_message,
            "plugin": self.plugin,
            "error_type": self.error_type,
        }
        if include_traceback and self.traceback_str:
            d["traceback"] = self.traceback_str
        return d


def _is_path_spec(spec: str) -> bool:
    """路径形态判定（Stage 10 批次 5）。

    含 "/" 或 "\\"，或（大小写不敏感）以 ".py" 结尾 → 路径分支。
    合法 dotted 模块名不含路径分隔符、也不会以 .py 结尾——本判别不会
    把任何既有合法 dotted spec 误判为路径。
    """
    return "/" in spec or "\\" in spec or spec.lower().endswith(".py")


def _resolve_path_spec(spec: str) -> tuple[Path, str]:
    """确定性路径解析：返回 (resolved, 模块名=stem)。

    相对 spec 按调用时 cwd 解析；不存在 → plugin_path_not_found；
    存在但非 .py 常规文件或 stem 非合法标识符 → plugin_path_invalid。
    """
    resolved = Path(spec).resolve()
    if not resolved.exists():
        raise PluginLoadError(
            "plugin_path_not_found",
            spec,
            "PluginPathNotFound",
            f"插件文件不存在: {spec}",
        )
    name = resolved.stem
    if (
        not resolved.is_file()
        or resolved.suffix.lower() != ".py"
        or not name.isidentifier()
    ):
        raise PluginLoadError(
            "plugin_path_invalid",
            spec,
            "PluginPathInvalid",
            f"插件路径必须是 .py 文件且文件名 stem 为合法模块名: {spec}",
        )
    return resolved, name


def _load_path_plugin(spec: str) -> None:
    """路径分支（Stage 10 批次 5）：解析 → 冲突检查 → 临时 sys.path
    注入 → registration context 内 import → try/finally 恢复 sys.path。

    导入期异常映射与 dotted 分支一致（plugin_register_failed /
    plugin_import_failed）；路径自身问题在解析/冲突检查阶段抛
    plugin_path_* 错误码（此时尚未注入 sys.path，无需恢复）。
    """
    resolved, name = _resolve_path_spec(spec)
    existing = sys.modules.get(name)
    if existing is not None:
        existing_file = getattr(existing, "__file__", None)
        # __file__ 缺失（内置/命名空间模块）时身份不可证，保守拒绝
        if existing_file is None or Path(existing_file).resolve() != resolved:
            raise PluginLoadError(
                "plugin_path_conflict",
                spec,
                "PluginPathConflict",
                (
                    f"模块名 {name!r} 已被其他模块占用"
                    f"（{existing_file}），拒绝路径加载: {spec}"
                ),
            )
        # 同文件 → import_module 命中 sys.modules 缓存，不重复执行注册

    parent = str(resolved.parent)
    added = parent not in sys.path
    if added:
        # append 到末尾：绝不遮蔽既有 sys.path 项（含标准库）
        sys.path.append(parent)
    try:
        # 批次 24 同规：context 收到原始 spec 字符串（路径拼写按输入冻结）
        with _plugin_registration_context(spec):
            importlib.import_module(name)
    except ParserRegistrationError as e:
        raise PluginLoadError(
            "plugin_register_failed",
            spec,
            type(e).__name__,
            str(e),
            traceback.format_exc(),
        ) from None
    except Exception as e:  # noqa: BLE001 — 契约同 dotted 分支：导入期任意异常结构化
        raise PluginLoadError(
            "plugin_import_failed",
            spec,
            type(e).__name__,
            str(e),
            traceback.format_exc(),
        ) from None
    finally:
        if added and parent in sys.path:
            sys.path.remove(parent)


def load_plugins(modules: list[str]) -> list[dict]:
    """按顺序导入插件模块（dotted 名或 .py 路径），返回 [{plugin, parsers_added}]。

    parsers_added 始终为本进程**首次**加载该模块时的真实注册增量（命中
    _FIRST_LOAD 备忘，不重复导入/注册）；仅在模块被本函数之外的途径
    预先导入（diff 为空）或模块本身不注册 parser 时为空表。任一失败抛
    PluginLoadError（fail-fast，不继续加载后续模块）。
    """
    results: list[dict] = []
    for mod in modules:
        if mod in _FIRST_LOAD:
            results.append(dict(_FIRST_LOAD[mod]))
            continue
        before = set(registered_names())
        if _is_path_spec(mod):
            # 路径分支自带解析/冲突/注入/恢复与异常映射（Stage 10 批次 5）
            _load_path_plugin(mod)
        else:
            try:
                # 批次 24 D1：每个 spec 独立进入上下文，import 与其触发的
                # 注册 hook（顶层 @register / 副模块 / helper 转注册）全程在
                # plugin_spec 上下文内；contextmanager finally 保证异常恢复
                with _plugin_registration_context(mod):
                    importlib.import_module(mod)
            except ParserRegistrationError as e:
                raise PluginLoadError(
                    "plugin_register_failed",
                    mod,
                    type(e).__name__,
                    str(e),
                    traceback.format_exc(),
                ) from None
            except Exception as e:  # noqa: BLE001 — 契约：导入期任意异常都转为结构化失败
                raise PluginLoadError(
                    "plugin_import_failed",
                    mod,
                    type(e).__name__,
                    str(e),
                    traceback.format_exc(),
                ) from None
        entry = {
            "plugin": mod,
            "parsers_added": sorted(set(registered_names()) - before),
        }
        _FIRST_LOAD[mod] = entry
        results.append(dict(entry))
    return results
