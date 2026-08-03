"""文件指纹：SHA-256，用于 source_hash 字段，便于后续去重和追溯。"""

from __future__ import annotations

import hashlib
from pathlib import Path


def compute_file_hash(path: str | Path) -> str:
    """流式读取，避免大文件一次性进内存。返回 hex 摘要（小写 64 位）。"""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"hash 目标不是文件: {p}")

    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_text_hash(text: str) -> str:
    """对字符串做 hash，用于测试和 element 内容指纹。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
