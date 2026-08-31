"""显式外部插件加载（Stage 8 批次 19 裁决）。

- 仅接受 dotted 模块名（importlib.import_module）；不做文件路径加载、
  entry_points 扫描、YAML 扩展或内容嗅探
- `--plugin` 可重复，按出现顺序加载；同一模块重复指定为模块缓存幂等
  no-op（parsers_added 为空）
- fail-fast：首个失败抛 PluginLoadError，整条命令中止（批量路径不启动池）
- 错误契约：
  - ParserRegistrationError（仅由 register() 抛出，即 @register 重名/缺名）
    → code=plugin_register_failed
  - 导入期其他任意异常（ModuleNotFoundError/SyntaxError/顶层 ValueError 等）
    → code=plugin_import_failed
- 标准 CLI 错误 JSON 不含 traceback（to_dict() 默认省略，仅日志层保留）
"""

from __future__ import annotations

import importlib
import traceback

from app.parser_registry import ParserRegistrationError, registered_names

__all__ = ["PluginLoadError", "load_plugins"]


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


def load_plugins(modules: list[str]) -> list[dict]:
    """按顺序导入插件模块，返回 [{plugin, parsers_added}]。

    parsers_added 由注册表名单快照前后 diff 得出；重复模块命中
    importlib 缓存，返回 parsers_added=[]。任一失败抛 PluginLoadError
    （fail-fast，不继续加载后续模块）。
    """
    results: list[dict] = []
    for mod in modules:
        before = set(registered_names())
        try:
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
        results.append(
            {"plugin": mod, "parsers_added": sorted(set(registered_names()) - before)}
        )
    return results
