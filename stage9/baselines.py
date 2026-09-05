# -*- coding: utf-8 -*-
"""Stage 9 批次 26：零依赖基线切分（B1 固定长度 / B2-foldws-v1 递归切分）。

设计依据 docs/stage9-batch26-design.md §5 + GPT 裁决（2026-09-05 C3）：
- B1：规范化字符流上按 N 字符硬切，无重叠、无分隔符；
- **B2-foldws-v1**：设计 §5 原定 B2（保留换行的原始文本输入）记为
  未执行/不可复现——标注 JSON 只存 fold-ws 流，无统一原始阅读序文本
  源，用 gold unit 边界合成换行会泄漏标注决策。冻结显式变体
  B2-foldws-v1：input_view=fold_ws，RecursiveCharacterTextSplitter 语义
  的零依赖重实现，分隔符层级冻结 ["\n\n", "\n", "。", "！", "？",
  "；", ". ", "! ", "? ", " ", ""]，重叠 0。fold-ws 流上不含换行 →
  前两级分隔符（\\n\\n 与 \\n）恒不命中（newline_level_hits=0，结构性
  事实），层级退化为句读级——保守（更难）设定。
- N 搜索范围 {200, 500, 800, 1200, 2000}，dev 上按 ARI 选优后冻结
  （硬门槛：最终 14 篇 dev 全网格重跑后才可冻结 N*）。
"""
B1_N_GRID = (200, 500, 800, 1200, 2000)
B2_SEPARATORS = ("\n\n", "\n", "。", "！", "？", "；", ". ", "! ", "? ",
                 " ", "")
B2_VARIANT = "B2-foldws-v1"
B2_INPUT_VIEW = "fold_ws"


def b1_fixed_length(stream, n):
    """fold-ws 流上按 N 硬切。输入必须已规范化。"""
    if n <= 0:
        raise ValueError("n 必须为正整数")
    if not stream:
        return []
    return [stream[i:i + n] for i in range(0, len(stream), n)]


def _split_on_separator(text, sep):
    if sep == "":
        return list(text)
    parts = text.split(sep)
    out = []
    for i, part in enumerate(parts):
        if i < len(parts) - 1:
            out.append(part + sep)
        else:
            out.append(part)
    return [p for p in out if p]


def b2_recursive(text, n, separators=B2_SEPARATORS):
    """递归字符切分（重叠 0）。piece 超限且仍有下一级分隔符时递归细分；
    末级 "" 空分隔符 = 逐字符回退（贪心合并恢复到 ≤n 块）。
    """
    if n <= 0:
        raise ValueError("n 必须为正整数")
    if not text:
        return []
    if len(text) <= n:
        return [text]
    sep, rest = separators[0], separators[1:]
    chunks = []
    buf = ""
    for piece in _split_on_separator(text, sep):
        if len(piece) > n:
            if buf:
                chunks.append(buf)
                buf = ""
            if rest:
                chunks.extend(b2_recursive(piece, n, rest))
            else:
                chunks.append(piece[:n])  # 理论不可达（"" 逐字符）
        elif len(buf) + len(piece) <= n:
            buf += piece
        else:
            if buf:
                chunks.append(buf)
            buf = piece
    if buf:
        chunks.append(buf)
    return chunks
