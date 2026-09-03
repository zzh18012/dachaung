# -*- coding: utf-8 -*-
"""Stage 9 批次 26：规范化口径（fold-ws-v1）。

与 app/chunkers/structural.py normalize_text 同源规则（所有空白压成
单空格、strip 两端），语义一致、实现独立（stage9 工具零依赖，不耦合
app 内部模块）。设计依据 docs/stage9-batch26-design.md §3。
"""
import re

_WHITESPACE_RE = re.compile(r"\s+")


def fold_ws(s: str) -> str:
    if not s:
        return ""
    return _WHITESPACE_RE.sub(" ", s).strip()


def is_folded(s: str) -> bool:
    return fold_ws(s) == s
