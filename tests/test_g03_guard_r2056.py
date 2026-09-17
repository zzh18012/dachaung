# -*- coding: utf-8 -*-
"""R2056 合成验证件：G03 parametrize 装饰器严格等价守卫（r56 裁决②）。

被测对象 = tests/g03_parametrize_guard.py（tracked 守卫模块，G03 删除器
的长期安全前置）。全部用合成源码字符串直接驱动守卫函数，零真实语料
接触、零删除动作：
① 函数体同体 + decorator/parametrize 完全同体（内联字面量）→ eligible
② 函数体同体 + parametrize 参数清单不同 → deferred，不得删除
③ decorator 文本同体但参数引用外部模块级名字 → parametrize_dynamic_deferred
④ 无 parametrize 团零变化回归（守卫恒放行，不收紧非守卫维度）
另含边界件：装饰器数量不一致 / 装饰器块原始文本严格性（注释与空行）/
关键字与动态形态 / 白名单单元 / 外部脚本上下文 import 接线证明。
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import g03_parametrize_guard as guard  # noqa: E402


# ---------------------------------------------------------------- ① eligible
GROUP_EQUIV_A = '''import pytest

FORBIDDEN = frozenset({"alpha", "beta", "gamma"})


@pytest.mark.parametrize("token", ["alpha", "beta", "gamma"])
@pytest.mark.slow
def test_forbidden_fourth(token):
    assert token not in {"", " "}
'''

GROUP_EQUIV_B = '''import pytest


@pytest.mark.parametrize("token", ["alpha", "beta", "gamma"])
@pytest.mark.slow
def test_forbidden_sixth(token):
    assert token not in {"", " "}
'''


def test_parametrize_identical_inline_literals_eligible():
    """①体同体 + 装饰器块逐字节同体（内联字面量清单，双装饰器保序）。"""
    members = (guard.members_from_module(GROUP_EQUIV_A)
               + guard.members_from_module(GROUP_EQUIV_B))
    assert [m.name for m in members] == ["test_forbidden_fourth",
                                         "test_forbidden_sixth"]
    verdict = guard.guard_group(members)
    assert verdict.eligible
    assert verdict.reason == "parametrize_decorator_equivalent_static"


# ------------------------------------------------------- ② arglist mismatch
GROUP_DIFF_A = '''import pytest


@pytest.mark.parametrize("token", ["alpha", "beta", "gamma"])
def test_tokens_fourth(token):
    assert token not in {"", " "}
'''

GROUP_DIFF_B = '''import pytest


@pytest.mark.parametrize("token", ["alpha", "beta"])
def test_tokens_sixth(token):
    assert token not in {"", " "}
'''


def test_parametrize_arglist_differs_deferred():
    """②体同体但 parametrize 清单不同（R2055 forbidden_tokens 实况）→ 延期。"""
    members = (guard.members_from_module(GROUP_DIFF_A)
               + guard.members_from_module(GROUP_DIFF_B))
    verdict = guard.guard_group(members)
    assert not verdict.eligible
    assert verdict.status == "deferred"
    assert verdict.reason == "parametrize_decorator_mismatch_deferred"


# ------------------------------------------------------------- ③ dynamic
GROUP_DYN_A = '''import pytest

TOKENS = ["alpha", "beta"]


@pytest.mark.parametrize("token", TOKENS)
def test_tokens_fourth(token):
    assert token not in {"", " "}
'''

GROUP_DYN_B = '''import pytest

TOKENS = ["alpha", "beta", "gamma", "delta"]


@pytest.mark.parametrize("token", TOKENS)
def test_tokens_seventh(token):
    assert token not in {"", " "}
'''


def test_parametrize_external_name_dynamic_deferred():
    """③装饰器文本逐字节同体但实参是外部模块级名字（各自 TOKENS）→ 动态延期。"""
    members = (guard.members_from_module(GROUP_DYN_A)
               + guard.members_from_module(GROUP_DYN_B))
    # 前置自证：装饰器块确实逐字节一致（延期原因必须来自动态形态而非文本差）
    block_a = guard.decorator_block(members[0].source, members[0].node)
    block_b = guard.decorator_block(members[1].source, members[1].node)
    assert block_a == block_b
    verdict = guard.guard_group(members)
    assert not verdict.eligible
    assert verdict.reason == "parametrize_dynamic_deferred"
    assert "test_tokens_fourth" in verdict.detail or "test_tokens_seventh" in verdict.detail


# ---------------------------------------------------------- ④ zero change
GROUP_PLAIN_A = '''def test_plain_fourth():
    assert 1 + 1 == 2
'''

GROUP_PLAIN_B = '''def test_plain_fifth():
    assert 1 + 1 == 2
'''

GROUP_MARKED_A = '''import pytest


@pytest.mark.slow
def test_marked_fourth():
    assert 1 + 1 == 2
'''

GROUP_MARKED_B = '''def test_marked_fifth():
    assert 1 + 1 == 2
'''


def test_no_parametrize_group_zero_change_eligible():
    """④团内无 parametrize → 守卫恒放行（含装饰器不一致的非 parametrize 团）。"""
    plain = guard.guard_group(
        guard.members_from_module(GROUP_PLAIN_A)
        + guard.members_from_module(GROUP_PLAIN_B))
    assert plain.eligible
    assert plain.reason == "no_parametrize_unchanged"

    marked = guard.guard_group(
        guard.members_from_module(GROUP_MARKED_A)
        + guard.members_from_module(GROUP_MARKED_B))
    assert marked.eligible
    assert marked.reason == "no_parametrize_unchanged"


# ------------------------------------------------- count mismatch (boundary)
GROUP_COUNT_A = '''import pytest


@pytest.mark.parametrize("t", [1])
@pytest.mark.slow
def test_count_fourth(t):
    assert t > 0
'''

GROUP_COUNT_B = '''import pytest


@pytest.mark.parametrize("t", [1])
def test_count_fifth(t):
    assert t > 0
'''


def test_decorator_count_mismatch_deferred():
    """装饰器数量不一致（2 vs 1）→ 数量闸先于文本闸触发，整团延期。"""
    members = (guard.members_from_module(GROUP_COUNT_A)
               + guard.members_from_module(GROUP_COUNT_B))
    verdict = guard.guard_group(members)
    assert not verdict.eligible
    assert verdict.reason == "parametrize_decorator_mismatch_deferred"
    assert "decorator count differs" in verdict.detail


# --------------------------------------------- raw-text strictness (byte)
GROUP_RAW_STRICT_A = '''import pytest


@pytest.mark.parametrize("t", [1])
@pytest.mark.slow
def test_raw_fourth(t):
    assert t > 0
'''

GROUP_RAW_COMMENT_B = '''import pytest


@pytest.mark.parametrize("t", [1])
# batch note between decorators
@pytest.mark.slow
def test_raw_sixth(t):
    assert t > 0
'''

GROUP_RAW_BLANK_B = '''import pytest


@pytest.mark.parametrize("t", [1])

@pytest.mark.slow
def test_raw_seventh(t):
    assert t > 0
'''


def test_decorator_block_rawtext_strictness_deferred():
    """装饰器块含差异注释/差异空行（AST 结构等价）→ 逐字节闸延期，证明未做 AST 归一。"""
    base = guard.members_from_module(GROUP_RAW_STRICT_A)
    with_comment = guard.guard_group(
        base + guard.members_from_module(GROUP_RAW_COMMENT_B))
    assert not with_comment.eligible
    assert with_comment.reason == "parametrize_decorator_mismatch_deferred"

    with_blank = guard.guard_group(
        base + guard.members_from_module(GROUP_RAW_BLANK_B))
    assert not with_blank.eligible
    assert with_blank.reason == "parametrize_decorator_mismatch_deferred"
    assert "distinct byte-strict texts" in with_blank.detail


# ----------------------------------------------- keyword / dynamic forms
GROUP_KW_STATIC_A = '''import pytest


@pytest.mark.parametrize(
    ["a", "b"],
    [(1, "x"), (2, "y")],
    ids=["one", "two"],
)
def test_pairs_fourth(a, b):
    assert a > 0 and b
'''

GROUP_KW_STATIC_B = '''import pytest


@pytest.mark.parametrize(
    ["a", "b"],
    [(1, "x"), (2, "y")],
    ids=["one", "two"],
)
def test_pairs_fifth(a, b):
    assert a > 0 and b
'''


def test_parametrize_keyword_and_dynamic_forms():
    """多行装饰器 + 全自包含关键字 → eligible；ids 调用 / starred / BinOp → 动态延期。"""
    static_pair = guard.guard_group(
        guard.members_from_module(GROUP_KW_STATIC_A)
        + guard.members_from_module(GROUP_KW_STATIC_B))
    assert static_pair.eligible
    assert static_pair.reason == "parametrize_decorator_equivalent_static"

    ids_call_src = '''import pytest


@pytest.mark.parametrize("t", [1, 2], ids=make_ids())
def test_ids_call_fourth(t):
    assert t > 0
'''
    ids_call_other = '''import pytest


@pytest.mark.parametrize("t", [1, 2], ids=make_ids())
def test_ids_call_fifth(t):
    assert t > 0
'''
    v_ids = guard.guard_group(
        guard.members_from_module(ids_call_src)
        + guard.members_from_module(ids_call_other))
    assert not v_ids.eligible
    assert v_ids.reason == "parametrize_dynamic_deferred"

    starred_src = '''import pytest


@pytest.mark.parametrize("t", [*TOKENS])
def test_star_fourth(t):
    assert t > 0
'''
    starred_other = '''import pytest


@pytest.mark.parametrize("t", [*TOKENS])
def test_star_fifth(t):
    assert t > 0
'''
    v_star = guard.guard_group(
        guard.members_from_module(starred_src)
        + guard.members_from_module(starred_other))
    assert not v_star.eligible
    assert v_star.reason == "parametrize_dynamic_deferred"

    binop_src = '''import pytest


@pytest.mark.parametrize("t", ["a" + "b"])
def test_binop_fourth(t):
    assert t
'''
    binop_other = '''import pytest


@pytest.mark.parametrize("t", ["a" + "b"])
def test_binop_fifth(t):
    assert t
'''
    v_binop = guard.guard_group(
        guard.members_from_module(binop_src)
        + guard.members_from_module(binop_other))
    assert not v_binop.eligible
    assert v_binop.reason == "parametrize_dynamic_deferred"


# --------------------------------------------------- whitelist unit checks
def test_static_literal_whitelist_unit():
    """白名单单元：str/int/bool/None + 内联 list/tuple/dict 递归通过；其余拒绝。"""
    accepted = ['"abc"', "123", "True", "False", "None",
                '[1, "x", None]', '("a", [1, 2])',
                '{"k": (1, None), "j": [True]}']
    for expr in accepted:
        node = ast.parse(expr, mode="eval").body
        assert guard.is_static_literal(node), expr

    rejected = ["1.5", 'b"bytes"', "TOKENS", "pytest.mark", "{1, 2}",
                "[x for x in y]", 'f"a{b}"', '"a" + "b"', "(lambda: 1)",
                "make_ids()", "{**other}", "[*vals]", "...", "-1",
                "sys.maxsize"]
    for expr in rejected:
        node = ast.parse(expr, mode="eval").body
        assert not guard.is_static_literal(node), expr


# ------------------------------------------------- external-script context
def test_guard_importable_from_external_script_context():
    """接线证明：outputs/ 下删除器脚本不经 sys.path、按文件绝对路径加载守卫。"""
    module_path = HERE / "g03_parametrize_guard.py"
    spec = importlib.util.spec_from_file_location(
        "g03_guard_wiring_probe_r2056", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # 注册进 sys.modules 再 exec：dataclasses 解析字符串注解需经
    # sys.modules[cls.__module__]，外部加载器（outputs/ 删除器）同此模式。
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    eligible_case = module.guard_group(
        module.members_from_module(GROUP_EQUIV_A)
        + module.members_from_module(GROUP_EQUIV_B))
    assert eligible_case.eligible

    dynamic_case = module.guard_group(
        module.members_from_module(GROUP_DYN_A)
        + module.members_from_module(GROUP_DYN_B))
    assert dynamic_case.reason == "parametrize_dynamic_deferred"

    file_case = module.member_from_file(module_path, "guard_group")
    assert file_case is None  # 非 test* 函数不在成员枚举口径内
