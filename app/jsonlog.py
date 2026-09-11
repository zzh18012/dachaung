"""结构化日志（JSON Lines，Stage 8 批次 17，Option A 裁决）。

- JSONFormatter：record.msg → event；logging extra= 传入的字段展开到顶层
- setup_logger：--log-file（append，utf-8）与 --verbose（stderr）可同开；
  两者皆无时挂 NullHandler——否则 logging 的 lastResort 会把 WARNING+
  泄漏到 stderr，破坏"默认零输出变化"
- traceback 有界截断（Stage 10 批次 2 次项，修复批次 17 已知限制）：
  日志层 "traceback" 字段超界折叠/封顶（保头保尾），错误码/消息/结构化
  JSON 语义零变化；截断只发生在 formatter，进程内 dict 不动
- 已知限制（裁决边界 3/4）：无自动轮转（append 需手动清理，轮转属
  批次 2 后续项）；timestamp 为 epoch 秒
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

# Stage 10 批次 2 次项：traceback 有界截断参数。头保留外层调用框架，
# 尾保留最内层帧与异常行（诊断价值最高）；64 行内短 traceback 原样通过
TRACEBACK_MAX_LINES = 64
TRACEBACK_HEAD_LINES = 40
TRACEBACK_TAIL_LINES = 20
TRACEBACK_MAX_CHARS = 8000


def truncate_traceback(tb: str) -> str:
    """两段式有界截断：先按行折叠中段（保头保尾），再按字符封顶。

    标记含被折叠量，确定性输出（无时间戳/随机性）便于 diff 与测试。
    """
    lines = tb.splitlines()
    if len(lines) > TRACEBACK_MAX_LINES:
        omitted = len(lines) - TRACEBACK_HEAD_LINES - TRACEBACK_TAIL_LINES
        lines = (
            lines[:TRACEBACK_HEAD_LINES]
            + [f"...<truncated:{omitted} lines>..."]
            + lines[-TRACEBACK_TAIL_LINES:]
        )
    out = "\n".join(lines)
    if len(out) <= TRACEBACK_MAX_CHARS:
        return out
    # 字符封顶（防单行巨型 repr）：保头 1/4 + 保尾，标记夹中间
    head_keep = TRACEBACK_MAX_CHARS // 4
    tail_keep = TRACEBACK_MAX_CHARS - head_keep - 64  # 标记+换行预算
    omitted = len(out) - head_keep - tail_keep
    return (
        out[:head_keep]
        + f"\n...<truncated:{omitted} chars>...\n"
        + out[-tail_keep:]
    )


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
                if key == "traceback" and isinstance(value, str):
                    value = truncate_traceback(value)
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


__all__ = ["JSONFormatter", "setup_logger", "truncate_traceback"]
