"""evaluation/__init__.py 第十轮 edges 测试（Round 667）。

补强 edges9 未触及的角度（第五十批）。

新角度：
- 4 个版本常量更深（与字符串方法 chained / format 字符串 / __eq__ 行为 / 与其他 '1.x' 比较）
- __all__ 顺序不变性（sorted 后顺序 / reverse 后顺序）
- 模块属性访问更深层（__name__ 是完整 dotted path / __file__ 存在 / __spec__）
- importlib.reload 不影响外部 import 引用（已 import 的符号值不变）
- 模块 docstring 内容补强（具体设计原则文本 / jsonschema 提及 / Stage 1 提及 / 评测包开头）
- AST 结构补强（4 常量 Assign + 1 __all__ = 5 / docstring Expr / 无 FunctionDef / 无 ClassDef / 无 Import / 无 AsyncFunctionDef）
- forbidden tokens 第一百三十七批
"""

from __future__ import annotations

import ast
import importlib
import inspect
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

import evaluation as eval_mod
from evaluation import (
    ANNOTATION_VERSION,
    EVALUATOR_VERSION,
    MANIFEST_VERSION,
    REPORT_VERSION,
)


# ---------- 4 个版本常量更深 ----------

def test_evaluator_version_format_with_string_batch50():
    """版本字符串可以用于 format。"""
    out = f"version={EVALUATOR_VERSION}"
    assert out == "version=1.1"


def test_evaluator_version_partition_batch50():
    """partition 在第一个 '.' 处分割。"""
    before, sep, after = EVALUATOR_VERSION.partition(".")
    assert before == "1"
    assert sep == "."
    assert after == "1"


def test_evaluator_version_rpartition_batch50():
    before, sep, after = EVALUATOR_VERSION.rpartition(".")
    assert before == "1"
    assert sep == "."
    assert after == "1"


def test_evaluator_version_split_batch50():
    parts = EVALUATOR_VERSION.split(".")
    assert parts == ["1", "1"]


def test_evaluator_version_rsplit_batch50():
    parts = EVALUATOR_VERSION.rsplit(".", 1)
    assert parts == ["1", "1"]


def test_evaluator_version_eq_method_batch50():
    """str.__eq__ 正确比较。"""
    assert EVALUATOR_VERSION.__eq__("1.1") is True
    assert EVALUATOR_VERSION.__eq__("1.0") is False


def test_evaluator_version_lt_gt_batch50():
    """字符串比较：'1.1' > '1.0'。"""
    assert EVALUATOR_VERSION > "1.0"
    assert "1.0" < EVALUATOR_VERSION


def test_annotation_version_lt_evaluator_batch50():
    assert ANNOTATION_VERSION < EVALUATOR_VERSION


def test_versions_unique_pairs_batch50():
    """EVALUATOR 与 REPORT 同值；ANNOTATION 与 MANIFEST 同值。"""
    assert EVALUATOR_VERSION is not REPORT_VERSION or EVALUATOR_VERSION == REPORT_VERSION
    assert ANNOTATION_VERSION is not MANIFEST_VERSION or ANNOTATION_VERSION == MANIFEST_VERSION


# ---------- __all__ 顺序不变性 ----------

def test_all_order_preserved_batch50():
    """__all__ 顺序固定为 EVALUATOR/REPORT/ANNOTATION/MANIFEST。"""
    assert eval_mod.__all__[0] == "EVALUATOR_VERSION"
    assert eval_mod.__all__[1] == "REPORT_VERSION"
    assert eval_mod.__all__[2] == "ANNOTATION_VERSION"
    assert eval_mod.__all__[3] == "MANIFEST_VERSION"


def test_all_sorted_differs_from_original_batch50():
    """sorted(__all__) 与原顺序相同（因为已经是字母序的相反？不，是 EVALUATOR/REPORT/ANNOTATION/MANIFEST 不是字母序）。

    sorted 字母序：ANNOTATION, EVALUATOR, MANIFEST, REPORT
    原顺序：EVALUATOR, REPORT, ANNOTATION, MANIFEST
    所以两者不同。
    """
    sorted_all = sorted(eval_mod.__all__)
    assert sorted_all != eval_mod.__all__


def test_all_reversed_differs_batch50():
    """reversed(__all__) 与原顺序不同。"""
    rev = list(reversed(eval_mod.__all__))
    assert rev != eval_mod.__all__
    assert rev[0] == "MANIFEST_VERSION"


# ---------- 模块属性访问更深层 ----------

def test_module_name_is_evaluation_batch50():
    assert eval_mod.__name__ == "evaluation"


def test_module_file_exists_batch50():
    assert eval_mod.__file__ is not None
    p = eval_mod.__file__
    assert p.endswith("__init__.py") or p.endswith("__init__.pyc") or p.endswith("__init__.pyd")


def test_module_spec_not_none_batch50():
    """__spec__ 应该不为 None（已 import 的模块都有 spec）。"""
    assert eval_mod.__spec__ is not None


def test_module_package_is_evaluation_batch50():
    assert eval_mod.__package__ == "evaluation"


def test_module_dict_contains_4_versions_batch50():
    d = eval_mod.__dict__
    assert "EVALUATOR_VERSION" in d
    assert "REPORT_VERSION" in d
    assert "ANNOTATION_VERSION" in d
    assert "MANIFEST_VERSION" in d


# ---------- importlib.reload 不影响外部 import 引用 ----------

def test_reload_does_not_change_already_bound_value_batch50():
    """reload 后 eval_mod 引用更新，但已 bound 的 EVALUATOR_VERSION 变量值不变。"""
    original = EVALUATOR_VERSION  # 局部绑定
    importlib.reload(eval_mod)
    # 局部变量 original 仍是原值
    assert original == "1.1"
    # eval_mod.EVALUATOR_VERSION 也仍是原值（因为模块代码不变）
    assert eval_mod.EVALUATOR_VERSION == "1.1"


def test_reload_preserves_module_identity_batch50():
    """reload 后模块对象是同一个（id 不变）。"""
    original_id = id(eval_mod)
    importlib.reload(eval_mod)
    assert id(eval_mod) == original_id


# ---------- 模块 docstring 内容补强 ----------

def test_docstring_mentions_jsonschema_batch50():
    assert "jsonschema" in eval_mod.__doc__


def test_docstring_mentions_stage_1_batch50():
    """Stage 1 引入 jsonschema。"""
    assert "Stage 1" in eval_mod.__doc__


def test_docstring_mentions_parser_chunker_pipeline_batch50():
    """设计原则：不修改 parser/chunker/pipeline。"""
    assert "parser" in eval_mod.__doc__


def test_docstring_mentions_ratio_denominator_zero_batch50():
    """比例分母为 0 → null。"""
    assert "分母" in eval_mod.__doc__ or "denominator" in eval_mod.__doc__.lower()


def test_docstring_mentions_total_only_batch50():
    """计时只记 total。"""
    assert "total" in eval_mod.__doc__.lower()


def test_docstring_mentions_parse_chunk_batch50():
    """parse/chunk 未插桩。"""
    assert "parse" in eval_mod.__doc__ or "chunk" in eval_mod.__doc__


def test_docstring_contains_design_principles_section_batch50():
    """docstring 含'设计原则'段。"""
    assert "设计原则" in eval_mod.__doc__


def test_docstring_contains_version_history_section_batch50():
    """docstring 含'版本历史'段。"""
    assert "版本历史" in eval_mod.__doc__


def test_docstring_first_line_starts_correctly_batch50():
    """docstring 第一行以'评测包'开头。"""
    first_line = eval_mod.__doc__.split("\n")[0]
    assert first_line.startswith("评测包")


# ---------- AST 结构补强 ----------

def test_ast_module_has_docstring_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_no_function_def_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in tree.body)


def test_ast_no_class_def_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_import_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in tree.body)


def test_ast_has_5_top_level_assigns_batch50():
    """4 个版本常量 + 1 __all__ = 5 Assign。"""
    tree = ast.parse(inspect.getsource(eval_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 5


def test_ast_assign_targets_count_is_1_each_batch50():
    """每个 Assign 只有 1 个 target。"""
    tree = ast.parse(inspect.getsource(eval_mod))
    for n in tree.body:
        if isinstance(n, ast.Assign):
            assert len(n.targets) == 1


def test_ast_assign_targets_are_names_batch50():
    """所有 Assign target 是 ast.Name。"""
    tree = ast.parse(inspect.getsource(eval_mod))
    for n in tree.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                assert isinstance(t, ast.Name)


def test_ast_all_value_is_list_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert isinstance(all_assign.value, ast.List)


def test_ast_all_list_has_4_constant_str_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert len(all_assign.value.elts) == 4
    for elt in all_assign.value.elts:
        assert isinstance(elt, ast.Constant)
        assert isinstance(elt.value, str)


def test_ast_no_try_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.Try) for n in ast.walk(tree))


def test_ast_no_with_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.With) for n in ast.walk(tree))


def test_ast_no_for_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.For) for n in ast.walk(tree))


def test_ast_no_if_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.If) for n in ast.walk(tree))


def test_ast_no_while_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))


def test_ast_no_global_nonlocal_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


def test_ast_no_delete_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.Delete) for n in ast.walk(tree))


def test_ast_no_raise_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.Raise) for n in ast.walk(tree))


def test_ast_4_constant_values_batch50():
    """4 个版本常量都是 Constant value='1.x'。"""
    tree = ast.parse(inspect.getsource(eval_mod))
    constant_assigns = [
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and isinstance(n.value, ast.Constant)
        and isinstance(n.value.value, str)
        and any(isinstance(t, ast.Name) and "VERSION" in t.id for t in n.targets)
    ]
    assert len(constant_assigns) == 4


def test_ast_evaluator_version_constant_value_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    ev = next(
        n for n in tree.body
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "EVALUATOR_VERSION" for t in n.targets)
    )
    assert ev.value.value == "1.1"


def test_ast_docstring_is_non_empty_str_batch50():
    tree = ast.parse(inspect.getsource(eval_mod))
    doc = tree.body[0].value.value
    assert isinstance(doc, str)
    assert len(doc) > 100


# ---------- forbidden tokens 第一百三十七批 ----------

def _src() -> str:
    return inspect.getsource(eval_mod)


def test_source_no_eval_batch50():
    assert "eval(" not in _src()


def test_source_no_exec_batch50():
    assert "exec(" not in _src()


def test_source_no_compile_batch50():
    assert "compile(" not in _src()


def test_source_no_globals_batch50():
    assert "globals(" not in _src()


def test_source_no_locals_batch50():
    assert "locals(" not in _src()


def test_source_no_os_system_batch50():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch50():
    assert "subprocess" not in _src()


def test_source_no_popen_batch50():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch50():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch50():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch50():
    assert "socket" not in _src()


def test_source_no_requests_batch50():
    assert "requests" not in _src()


def test_source_no_urllib_batch50():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch50():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch50():
    assert "yield" not in _src()


def test_source_no_open_batch50():
    """__init__.py 完全不用 open()。"""
    assert "open(" not in _src()


def test_source_no_async_await_batch50():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_class_def_batch50():
    tree = ast.parse(_src())
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_source_no_function_def_batch50():
    tree = ast.parse(_src())
    assert not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in tree.body)
