"""结构化日志（JSON Lines，Stage 8 批次 17，Option A 裁决）。

- JSONFormatter：record.msg → event；logging extra= 传入的字段展开到顶层
- setup_logger：--log-file（append，utf-8）与 --verbose（stderr）可同开；
  两者皆无时挂 NullHandler——否则 logging 的 lastResort 会把 WARNING+
  泄漏到 stderr，破坏"默认零输出变化"
- traceback 有界截断（Stage 10 批次 2 次项，修复批次 17 已知限制）：
  日志层 "traceback" 字段超界折叠/封顶（保头保尾），错误码/消息/结构化
  JSON 语义零变化；截断只发生在 formatter，进程内 dict 不动
- 日志轮转（Stage 10 批次 2 第三项，修复批次 17 已知限制剩余项）：
  RotatingFileHandler 按大小轮转，默认 50 MiB / 保留 5 份备份；
  max_bytes=0 禁用（回退普通 FileHandler，与批次 17 行为逐字节一致）。
  轮转只重命名文件、不写任何标记行——每个文件（含 .1/.2…）独立合法
  JSONL。每次运行单写者（父进程独占日志，Pool worker 不写盘），无跨
  进程 rollover 竞争；并发独立进程写同一日志文件时轮转不安全（stdlib
  既有边界，文档化为已知限制）
- 已知限制：timestamp 为 epoch 秒；跨进程并发写同一日志文件时轮转
  不安全
"""

from __future__ import annotations

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
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

# Stage 10 批次 2 第三项：日志轮转默认值。50 MiB 对正常批次远不可及
# （成功路径单文件行为不变），只在"需手动清理"的真实痛点尺寸生效
DEFAULT_LOG_MAX_BYTES = 50 * 1024 * 1024
DEFAULT_LOG_BACKUP_COUNT = 5


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
    max_bytes: int = DEFAULT_LOG_MAX_BYTES,
    backup_count: int = DEFAULT_LOG_BACKUP_COUNT,
) -> logging.Logger:
    """配置结构化 logger；重复调用会先清空既有 handler（防重复输出）。

    max_bytes > 0 时启用按大小轮转（保留 backup_count 份 .N 备份，
    backup_count=0 表示轮转时旧文件直接丢弃）；max_bytes <= 0 禁用
    轮转，行为与批次 17 的普通 append FileHandler 一致。
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()
    formatter = JSONFormatter()

    if log_file is not None:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        if max_bytes > 0:
            file_handler: logging.Handler = RotatingFileHandler(
                path,
                mode="a",
                encoding="utf-8",
                maxBytes=max_bytes,
                backupCount=backup_count,
            )
        else:
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


__all__ = [
    "DEFAULT_LOG_BACKUP_COUNT",
    "DEFAULT_LOG_MAX_BYTES",
    "JSONFormatter",
    "setup_logger",
    "truncate_traceback",
]
