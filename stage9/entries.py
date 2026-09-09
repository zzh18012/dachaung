# -*- coding: utf-8 -*-
"""结构化条目区划分层（标注指南 §3.1，R3' 裁决 2026-09-09）。

对可从来源辨识的结构化逻辑条目（参考文献/作者块/版权块），先按条目
边界强制 unit 断开，再在条目内部按冻结 v1 切分。冻结 v1 切分器本身
不动——本模块只是条目区之上的划分层（partition layer）。

机械规则（与一级 builder / 第二标注人 assembler 共用同一实现）：
- 视觉行折行不构成条目边界（锁一）：条目 = 起始行 + 其后所有非起始行；
- 条目内文本 = 各行 fold 后以单空格连接（等价 fold_ws("\\n".join)），
  条目内走 split_sentences（锁二）：有句末标点则多 unit，无则整条目
  一 unit；
- 每个 unit 的起始源行可追溯（span 布局回映射），调用方据此填 page；
- 首条目前的不匹配行（preamble）各自成组，机械按单行条目处理。
"""
import re

from .normalize import fold_ws
from .splitter import split_sentences


def group_line_indices(n_lines, starts):
    """把 [0, n_lines) 的行序切成分组行号表。

    starts 两种形态：
    - re.Pattern：行文本匹配该模式的行开新条目；
    - 0-based 行号可迭代对象：这些行开新条目（须非空、严格递增、
      落在界内）。

    返回 list[list[int]]；首边界之前的行（preamble）每行独立成组。
    """
    if isinstance(starts, re.Pattern):
        raise ValueError("regex 边界请用 partition_entries(parts, starts)")
    idx = list(starts)
    if not idx:
        raise ValueError("显式条目起点行号不能为空")
    if any(not isinstance(i, int) or isinstance(i, bool) for i in idx):
        raise ValueError("条目起点必须是 int 行号")
    if any(i < 0 or i >= n_lines for i in idx):
        raise ValueError("条目起点行号越界（共 %d 行）" % n_lines)
    if any(b <= a for a, b in zip(idx, idx[1:])):
        raise ValueError("条目起点行号必须严格递增")
    groups = []
    # preamble：首显式起点之前的行各自成组
    for i in range(0, idx[0]):
        groups.append([i])
    for a, b in zip(idx, idx[1:] + [n_lines]):
        groups.append(list(range(a, b)))
    return groups


def _layout(parts):
    """逐行 fold 后以单空格连接；返回 (text, spans)。

    spans = [(start, end, line_idx)]，start/end 为 text 内半开区间。
    空行不贡献文本，也不出现在 spans 中。
    """
    spans = []
    pos = 0
    for i, raw in enumerate(parts):
        fp = fold_ws(raw)
        if not fp:
            continue
        if pos:
            pos += 1  # 与前一非空行之间的分隔空格
        spans.append((pos, pos + len(fp), i))
        pos += len(fp)
    text = " ".join(s for s in (fold_ws(p) for p in parts) if s)
    return text, spans


def _line_of_offset(spans, off):
    for s, e, i in spans:
        if s <= off < e:
            return i
    for s, e, i in spans:  # 落在分隔空格上：归属后一行
        if off < s:
            return i
    return spans[-1][2] if spans else 0


def entry_units(parts):
    """单条目机械切分：parts = 该条目的源行文本（阅读序）。

    返回 [(unit_text, first_line_idx), ...]；first_line_idx 是 unit
    起始字符所在源行在 parts 内的 0-based 行号。条目无切分点则整条
    一个 unit；全空条目返回 []。
    """
    text, spans = _layout(parts)
    if not text:
        return []
    out = []
    cursor = 0
    for s in split_sentences(text):
        if not s:
            continue
        pos = text.find(s, cursor)
        assert pos >= 0, (s[:40], cursor)
        cursor = pos + len(s)
        out.append((s, _line_of_offset(spans, pos)))
    return out


def partition_entries(parts, starts):
    """条目区完整划分（blocks 只存来源区间 + 边界判断的机械执行）。

    parts：块内源行文本（阅读序）；starts：re.Pattern（匹配行开新
    条目）或显式起点行号可迭代对象（group_line_indices 契约）。

    返回 [(line_indices, [(unit_text, first_line_idx), ...]), ...]，
    组序 = 阅读序；first_line_idx 为 parts 内的绝对行号（0-based，
    非组内相对行号），调用方据此定位 unit 的页码/源键。hard 口径：
    首组首 unit 取块的 hard，其后每组（含 preamble 组）首 unit
    hard=True，组内其余 unit False。
    """
    if isinstance(starts, re.Pattern):
        matched = [i for i, p in enumerate(parts) if starts.match(p)]
        if not matched:
            raise ValueError("条目边界模式未命中任何行（%r）"
                             % starts.pattern)
        groups = group_line_indices(len(parts), matched)
    else:
        groups = group_line_indices(len(parts), starts)
    out = []
    for g in groups:
        units = [(text, g[li])
                 for text, li in entry_units([parts[i] for i in g])]
        out.append((g, units))
    return out
