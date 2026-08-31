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


__all__ = ["JSONFormatter", "setup_logger"]
