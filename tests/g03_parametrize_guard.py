# -*- coding: utf-8 -*-
"""G03 删除器安全前置：parametrize 装饰器严格等价守卫（R2056，r56 裁决②）。

本模块是 G03 L1 克隆冗余删除器的长期安全不变量（tracked 代码，供
outputs/autonomous/ 下的规划器/删除器按绝对路径 import；验证件 =
tests/test_g03_guard_r2056.py，全部合成源码，零真实语料接触）。

规则（r56 裁决②口径，四条）：
1. 函数体 L1 同体只是候选条件（上游 L1 分团负责，本模块不复核函数体）。
   团内任一成员存在 parametrize 时，团内各成员（含团代表）的完整
   decorator list 必须数量、顺序、原始源码文本逐字节一致，否则整团
   延期不删（parametrize_decorator_mismatch_deferred）。
2. parametrize 的参数必须是删除器能静态确认的自包含形式：内联字面量
   str/int/bool/None 与内联 list/tuple/dict 字面量（递归展开，键值同规）。
   出现外部 Name 引用、starred 展开、函数调用、动态构造等无法静态确认
   的形式 → 整团延期（parametrize_dynamic_deferred）。
3. 团内无任何成员存在 parametrize → 守卫恒放行
   （eligible / no_parametrize_unchanged）：非 parametrize 团行为与
   R2055 前完全一致，守卫不收紧也不放宽。
4. 既有 G03 其他安全条件（同文件完整团 / 跨文件 ≤3 文件 / 团规模 2–5 /
   重名 / 未收集 / 被引用排除、新鲜度复核等）全部在上游叠加，不因通过
   本守卫而放宽任何一条。

实现口径：
- "原始源码文本" = 首个装饰器行起至 def 行前一行的整段字节（含装饰器
  之间的注释/空行、多行调用的换行与缩进），不做任何 AST 归一或格式
  归一——允许安全假阴性，拒绝假阳性。
- parametrize 识别与 outputs/autonomous/dup_scan_r2032.has_parametrize
  同口径：装饰器（含 Call 形态时取其 func）为 Attribute.attr ==
  "parametrize" 或 Name.id == "parametrize"。
- 已知边界：parametrize 别名（如 PM = pytest.mark.parametrize 之后
  @PM(...)）不在识别口径内——与 R2035 打标 / R2055 延期的口径一致，
  语料若出现该形态须单批扩口径后再放行。
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

STATUS_ELIGIBLE = "eligible"
STATUS_DEFERRED = "deferred"

REASON_NO_PARAMETRIZE = "no_parametrize_unchanged"
REASON_EQUIVALENT = "parametrize_decorator_equivalent_static"
REASON_MISMATCH = "parametrize_decorator_mismatch_deferred"
REASON_DYNAMIC = "parametrize_dynamic_deferred"


# --------------------------------------------------------------------- inputs
@dataclass(frozen=True)
class MemberSource:
    """守卫输入：一个候选团成员（成员所在文件的源文本 + 其 AST 节点）。"""

    name: str
    source: str
    node: ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class GuardVerdict:
    """守卫裁决：status 为 eligible/deferred，reason 为机器可读原因码。"""

    status: str
    reason: str
    detail: str

    @property
    def eligible(self) -> bool:
        return self.status == STATUS_ELIGIBLE


# ---------------------------------------------------------------- detection
def _is_parametrize_target(target: ast.AST) -> bool:
    if isinstance(target, ast.Attribute):
        return target.attr == "parametrize"
    if isinstance(target, ast.Name):
        return target.id == "parametrize"
    return False


def has_parametrize(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """与 dup_scan_r2032.has_parametrize 同口径的 parametrize 侦测。"""
    for dec in fn.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if _is_parametrize_target(target):
            return True
    return False


def parametrize_calls(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Call]:
    """节点装饰器列表中的全部 parametrize 调用（裸形态不计，无参可查）。"""
    out: list[ast.Call] = []
    for dec in fn.decorator_list:
        if isinstance(dec, ast.Call) and _is_parametrize_target(dec.func):
            out.append(dec)
    return out


def decorator_block(source: str, fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """首个装饰器行至 def 行前一行的原始字节段（含注释/空行/换行形态）。

    无装饰器时返回空串。多行装饰器、装饰器间注释与空行全部落在该段内，
    逐字节比较即 r56 裁决要求的"原始源码文本"严格一致。
    """
    lines = source.splitlines(keepends=True)
    start = min([d.lineno for d in fn.decorator_list] + [fn.lineno])
    return "".join(lines[start - 1 : fn.lineno - 1])


# ------------------------------------------------------- static literal form
def is_static_literal(node: ast.AST) -> bool:
    """r56 裁决白名单：str/int/bool/None 常量 + 内联 list/tuple/dict 字面量。

    白名单之外一律 False（float/bytes/set 字面量、Name、Attribute、Call、
    Starred、BinOp、JoinedStr、Lambda、推导式、dict 的 ** 展开键等）。
    宁可假阴性（多延期），不做假阳性（误删除）。
    """
    if isinstance(node, ast.Constant):
        value = node.value
        return value is None or isinstance(value, (bool, str, int))
    if isinstance(node, (ast.List, ast.Tuple)):
        return all(is_static_literal(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        for key in node.keys:
            if key is None:  # dict 字面量内的 **other 展开
                return False
            if not is_static_literal(key):
                return False
        return all(is_static_literal(v) for v in node.values)
    return False


def first_nonstatic_parametrize_arg(
    source: str, fn: ast.FunctionDef | ast.AsyncFunctionDef
) -> str | None:
    """首个无法静态确认的 parametrize 实参/关键字值描述；全自包含则 None。"""
    for call in parametrize_calls(fn):
        for arg in list(call.args) + list(call.keywords):
            value = arg.value if isinstance(arg, ast.keyword) else arg
            if not is_static_literal(value):
                segment = ast.get_source_segment(source, value)
                shown = segment if segment is not None else "<unavailable>"
                return f"{type(value).__name__} {shown!r} (line {value.lineno})"
    return None


# ------------------------------------------------------------------- verdict
def guard_group(members: Sequence[MemberSource]) -> GuardVerdict:
    """对一个候选团（含团代表在内的全部成员）做装饰器维度裁决。

    输入假设：团已通过上游 L1 函数体同体分团（本守卫不复核函数体）。
    裁决只覆盖装饰器维度；其余 G03 安全条件由调用方叠加，不因此放宽。
    """
    if not members:
        return GuardVerdict(STATUS_DEFERRED, "empty_group", "no members supplied")

    parametrized = [m for m in members if has_parametrize(m.node)]
    if not parametrized:
        return GuardVerdict(
            STATUS_ELIGIBLE,
            REASON_NO_PARAMETRIZE,
            f"{len(members)} members, none parametrized; guard passes with "
            "zero behavior change (other G03 conditions apply upstream)",
        )

    counts = {len(m.node.decorator_list) for m in members}
    if len(counts) > 1:
        return GuardVerdict(
            STATUS_DEFERRED,
            REASON_MISMATCH,
            f"decorator count differs across group: {sorted(counts)}",
        )

    blocks = {decorator_block(m.source, m.node) for m in members}
    if len(blocks) > 1:
        return GuardVerdict(
            STATUS_DEFERRED,
            REASON_MISMATCH,
            f"raw decorator block text differs across group "
            f"({len(blocks)} distinct byte-strict texts)",
        )

    for member in members:
        offending = first_nonstatic_parametrize_arg(member.source, member.node)
        if offending is not None:
            return GuardVerdict(
                STATUS_DEFERRED,
                REASON_DYNAMIC,
                f"member {member.name}: parametrize argument not statically "
                f"confirmable: {offending}",
            )

    return GuardVerdict(
        STATUS_ELIGIBLE,
        REASON_EQUIVALENT,
        f"{len(members)} members, decorator blocks byte-identical, all "
        "parametrize arguments are inline literals",
    )


# -------------------------------------------------------------- conveniences
def members_from_module(source: str) -> list[MemberSource]:
    """枚举模块层 + 一层 class 内的 test* 函数（R2032/R2035 扫描同口径）。"""
    tree = ast.parse(source)
    out: list[MemberSource] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if (
                    isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and child.name.startswith("test")
                ):
                    out.append(MemberSource(child.name, source, child))
        elif (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test")
        ):
            out.append(MemberSource(node.name, source, node))
    return out


def member_from_file(path: str | Path, fn_name: str) -> MemberSource | None:
    """按函数名从测试文件取成员（首个命中；类内同名由调用方自行消歧）。"""
    source = Path(path).read_text(encoding="utf-8")
    for member in members_from_module(source):
        if member.name == fn_name:
            return member
    return None
