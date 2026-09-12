"""本地 HTTP API 服务（Stage 11 批次 1，W1 裁决 WITH BOUNDARIES）。

FastAPI 应用工厂 + 三端点 + 极简静态前端挂载；`app.cli serve` 启动。

边界（W1 裁决，逐条对应）：
- 默认仅监听 127.0.0.1；非 loopback 须 CLI 层显式 --unsafe-expose
  （见 cli.py serve；本模块不重复判断）；
- 上传上限在流式写入临时文件时实际计量（不信任 Content-Length），
  超限 413；成功/失败/超限全路径清理临时文件（try/finally）；
- 响应不泄露服务器临时路径：source_path 只用净化后的上传文件名，
  错误 message/details 里的临时路径同样被替换；
- 静态根挂载在全部 API 路由之后，不遮蔽 /api/*、/docs、/openapi.json；
- 不做：评测端点、鉴权、持久化、批量端点、真实 KVFS 接入。

错误 envelope：{"error": {"code", "message", "details"?}}；
成功响应 = 与 CLI `parse -o` 同构的统一文档 JSON（source_path 为
净化上传名）。HTTP 映射表见 docs/stage11-web-api.md（W4 后置裁定，
首报送审）。process_single 在事件循环内同步执行——本地单用户工具
的已知边界，不做异步任务队列。
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError

from app.parser_registry import list_parsers, registered_names
from app.pipeline import process_single

DEFAULT_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MiB（W1 裁决值）
_STATIC_DIR = Path(__file__).parent / "static"
_LOGGER = logging.getLogger("app.service")

# W4 固定 + 首报送审的映射表：业务失败 422、服务端集成缺陷 500、
# 超限 413、请求非法 422、未预期异常 500（无 traceback）。
_SERVER_DEFECT_CODES = frozenset(
    {"parser_contract_mismatch", "unexpected_parser_error", "chunker_failed"}
)


class ServiceError(Exception):
    """服务层结构化错误（code + HTTP status），由统一 handler 序列化。"""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def sanitize_filename(name: str | None) -> str:
    """净化上传文件名：只保留 basename、去控制字符，长度封顶 100。

    输出仅用于响应里的 source_path 展示与临时文件后缀推导，
    永不参与服务器路径构造（临时文件由 tempfile.mkstemp 生成）。
    """
    if not name:
        return "upload"
    base = name.replace("\\", "/").split("/")[-1]
    base = "".join(ch for ch in base if ch.isprintable())
    base = base.strip().strip(".")
    if not base:
        return "upload"
    if len(base) > 100:
        suffix = Path(base).suffix
        base = base[: max(1, 100 - len(suffix))] + suffix
    return base


def _temp_suffix(display_name: str) -> str:
    """从净化名推导临时文件后缀（parser 按扩展名分发/discover 需要）。"""
    suffix = Path(display_name).suffix.lower()
    if (
        suffix
        and len(suffix) <= 20
        and all(ch.isalnum() or ch == "." for ch in suffix)
    ):
        return suffix
    return ""


def _scrub_paths(obj: Any, replacements: list[tuple[str, str]]) -> Any:
    """递归替换响应中的服务器临时路径（W1：不泄露临时路径）。"""
    if isinstance(obj, str):
        for old, new in replacements:
            if old in obj:
                obj = obj.replace(old, new)
        return obj
    if isinstance(obj, dict):
        return {k: _scrub_paths(v, replacements) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub_paths(v, replacements) for v in obj]
    return obj


def _app_version() -> str:
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("kvfs-doc-parser")
    except PackageNotFoundError:  # 未安装（源码树直跑）
        return "0.1.0"


def create_app(
    *,
    plugins: list[str] | None = None,
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    temp_dir: Path | str | None = None,
) -> FastAPI:
    """构建服务应用。plugins 在创建时一次性加载（等价 CLI 预加载语义，
    失败即抛 PluginLoadError——serve 启动失败而非运行时半死状态）。

    temp_dir 仅测试注入用（验证临时文件清理）；生产走系统临时目录。
    """
    if plugins:
        from app.plugin_loader import load_plugins

        load_plugins(plugins)  # fail-fast（PluginLoadError 向上传播）

    app = FastAPI(
        title="kvfs-doc-parser",
        description=(
            "面向 KVFS 的复合文档解析与结构分块原型——本地 HTTP API"
            "（无鉴权，不适合公开暴露）"
        ),
        version=_app_version(),
    )

    @app.exception_handler(ServiceError)
    async def _service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
        body: dict[str, Any] = {"code": exc.code, "message": exc.message}
        if exc.details is not None:
            body["details"] = exc.details
        return JSONResponse({"error": body}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            {
                "error": {
                    "code": "invalid_request",
                    "message": "请求参数缺失或类型不符（multipart 表单：file 必填）",
                    "details": {"errors": exc.errors()[:20]},
                }
            },
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def _unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # W4：未预期异常 = 无 traceback 的 500；traceback 只进服务器日志
        _LOGGER.exception(
            "unhandled exception on %s %s", request.method, request.url.path
        )
        return JSONResponse(
            {"error": {"code": "internal_error", "message": "服务器内部错误"}},
            status_code=500,
        )

    @app.get("/api/v1/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "version": _app_version(),
            "parser_count": len(list_parsers()),
        }

    @app.get("/api/v1/parsers")
    async def parsers() -> list[dict[str, Any]]:
        return list_parsers()

    @app.post("/api/v1/parse")
    async def parse(
        file: UploadFile,
        parser: str = Form(default="fallback"),
        max_chars: int = Form(default=800),
    ) -> JSONResponse:
        from app.parser_registry import discover_parser

        display_name = sanitize_filename(file.filename)
        tmp: Path | None = None
        try:
            # 1. 流式落盘 + 实际计量（不信任 Content-Length，W1）
            fd, tmp_name = tempfile.mkstemp(
                suffix=_temp_suffix(display_name), dir=temp_dir
            )
            tmp = Path(tmp_name)
            replacements = [(str(tmp), display_name)]
            written = 0
            try:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > max_upload_bytes:
                        raise ServiceError(
                            413,
                            "upload_too_large",
                            f"上传超过上限 {max_upload_bytes} 字节（实际计量）",
                            details={"limit_bytes": max_upload_bytes},
                        )
                    os.write(fd, chunk)
            finally:
                os.close(fd)

            # 2. parser 校验 + auto 发现（与 CLI parse 同序：先名后 auto）
            if parser != "auto" and parser not in registered_names():
                known = ", ".join([*registered_names(), "auto"])
                raise ServiceError(
                    400,
                    "unknown_parser",
                    f"未知 parser: {parser}（支持: {known}）",
                )
            try:
                parser_name = (
                    discover_parser(tmp) if parser == "auto" else parser
                )
            except ValueError as e:
                raise ServiceError(400, "unsupported_type", str(e)) from e

            # 3. 解析（复用 CLI 同一实现；不写盘、无图片输出目录）
            document, errors = process_single(
                tmp,
                None,
                parser_name=parser_name,
                max_chars=max_chars,
                write_json=False,
            )
            if errors:
                first = _scrub_paths(errors[0].to_dict(), replacements)
                status = 500 if first["code"] in _SERVER_DEFECT_CODES else 422
                raise ServiceError(
                    status,
                    first["code"],
                    first["message"],
                    details=first.get("details"),
                )
            assert document is not None
            payload = document.to_dict()
            payload["source_path"] = display_name
            return JSONResponse(payload)
        finally:
            if tmp is not None:
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass
            await file.close()

    # 静态根在全部 API 路由之后挂载：路由按注册序匹配，
    # /api/* 与 FastAPI 自带 /docs、/openapi.json 先注册故不被遮蔽
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
    return app


__all__ = [
    "DEFAULT_MAX_UPLOAD_BYTES",
    "ServiceError",
    "create_app",
    "sanitize_filename",
]
