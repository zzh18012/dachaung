"""结构化日志（JSON Lines，Stage 8 批次 17，Option A 裁决）。

- JSONFormatter：record.msg → event；logging extra= 传入的字段展开到顶层
- setup_logger：--log-file（append，utf-8）与 --verbose（stderr）可同开；
  两者皆无时挂 NullHandler——否则 logging 的 lastResort 会把 WARNING+
  泄漏到 stderr，破坏"默认零输出变化"
- 已知限制（裁决边界 3/4）：无自动轮转（append 需手动清理）；
  traceback 首版不截断
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# LogRecord 的标准属性集（extra 字段不得与之重叠，扫描时排除）
_RESERVED = set(
    logging.LogRecord("", logging.INFO, "", 0, "", (), None).__dict__
) | {"message", "asctime"}


class JSONFormatter(logging.Formatter):
    """单行 JSON：timestamp（epoch 秒）/ level / event + extra 字段顶层展开。"""

    def format(self, record: logging.LogRecord) -> str:
        obj: dict[str, object] = {
            "timestamp": record.created,
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                obj[key] = value
        return json.dumps(obj, ensure_ascii=False)


def setup_logger(
    name: str,
    log_file: str | Path | None = None,
    verbose: bool = False,
) -> logging.Logger:
    """配置结构化 logger；重复调用会先清空既有 handler（防重复输出）。"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()
    formatter = JSONFormatter()

    if log_file is not None:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    if verbose:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


class LogFileInvalidError(Exception):
    """--log-file 指向目录/空串/不可写目标（r55 C12：CLI 结构化信封）。"""

    def __init__(self, path: str, code: str, message: str) -> None:
        super().__init__(message)
        self.path = path
        self.code = code
        self.message = message


def verify_log_file_target(log_file: str | Path) -> Path:
    """--log-file 前置校验（r55 C12）。

    目录/空串（Path('')→cwd）/不可写目标在批处理启动前以
    LogFileInvalidError 拒绝，不再让 FileHandler 的裸
    PermissionError/IsADirectoryError traceback 穿透到用户。
    合法时与 setup_logger 同规则预建父目录（append 试开一次）。
    """
    p = Path(log_file)
    if p.is_dir():
        raise LogFileInvalidError(
            str(p), "log_file_is_directory", f"--log-file 不能是目录: {p}"
        )
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8"):
            pass
    except OSError as e:
        raise LogFileInvalidError(
            str(p), "log_file_unwritable", f"--log-file 不可写: {p} ({e})"
        ) from e
    return p


__all__ = [
    "JSONFormatter",
    "LogFileInvalidError",
    "setup_logger",
    "verify_log_file_target",
]
