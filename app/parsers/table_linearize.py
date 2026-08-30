"""表格 → Markdown 线性化共享纯函数（Stage 6 批次 5）。

契约：docs/table-linearization-contract.md §2（2026-08-30 冻结）。
fallback（pdf/docx）/markdown/html 三处统一调用；ipynb 经
MarkdownParser 自动继承。单元格预处理顺序固定：
None→"" → CR 规整 → ``\\n``→``<br>`` → ``|``→``\\|`` → strip。
首行=表头、短行右侧补 ""、分隔行每列一个 ``---``；无 Unicode 归一、
无 HTML 实体转义；0 行表返回 ""（caller 不产出 table element）。
"""

from __future__ import annotations


def _cell(c: str | None) -> str:
    if c is None:
        c = ""
    s = str(c)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", "<br>")
    s = s.replace("|", "\\|")
    return s.strip()


def linearize_table(rows: list[list[str | None]]) -> str:
    """把行列数据渲染为 canonical markdown 表格字符串（逐字节确定）。"""
    if not rows:
        return ""
    norm = [[_cell(c) for c in r] for r in rows]
    width = max(len(r) for r in norm)
    norm = [r + [""] * (width - len(r)) for r in norm]
    header = norm[0]
    body = norm[1:]
    out = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for r in body:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


__all__ = ["linearize_table"]
