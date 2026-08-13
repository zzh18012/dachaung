"""evaluation/__init__.py 第九轮 edges 测试（Round 659）。

补强 edges8 未触及的角度（第四十九批）。

新角度：
- 4 个版本常量更深层比较（与不相关版本不匹配 / 排序结果 / 二进制 str 表示 / bytes 表示）
- __all__ 列表更深层（每个元素是 str / 无重复 / 与 dir() 中存在的名称匹配）
- 模块属性访问边界（getattr 默认值 / hasattr False for unknown / dir 包含版本常量）
- importlib.reload 不改变值（reload 后仍是原值）
- 模块 docstring 内容补强（v1.0 描述 / v1.1 描述 / "口径 D" / "词内硬切" / 不依赖 app/*）
- AST 结构补强（4 Assign / 1 __all__ list / module docstring / 无 FunctionDef / 无 ClassDef / 无 Import）
- forbidden tokens 第一百二十九批
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


# ---------- 4 个版本常量更深层比较 ----------

def test_evaluator_version_not_equal_other_versions_batch49():
    assert EVALUATOR_VERSION != "1.0"
    assert EVALUATOR_VERSION != "2.0"
    assert EVALUATOR_VERSION != "0.9"
    assert EVALUATOR_VERSION != ""


def test_report_version_not_equal_other_versions_batch49():
    assert REPORT_VERSION != "1.0"
    assert REPORT_VERSION != "2.0"


def test_annotation_version_not_equal_evaluator_batch49():
    """ANNOTATION_VERSION = '1.0' != EVALUATOR_VERSION '1.1'。"""
    assert ANNOTATION_VERSION != EVALUATOR_VERSION


def test_manifest_version_not_equal_evaluator_batch49():
    assert MANIFEST_VERSION != EVALUATOR_VERSION


def test_versions_sorting_batch49():
    """sorted 后顺序为 ['1.0', '1.0', '1.1', '1.1']。"""
    out = sorted([EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION])
    assert out == ["1.0", "1.0", "1.1", "1.1"]


def test_versions_bytes_representation_batch49():
    assert EVALUATOR_VERSION.encode() == b"1.1"
    assert REPORT_VERSION.encode() == b"1.1"
    assert ANNOTATION_VERSION.encode() == b"1.0"
    assert MANIFEST_VERSION.encode() == b"1.0"


def test_versions_repr_batch49():
    assert repr(EVALUATOR_VERSION) == "'1.1'"
    assert repr(REPORT_VERSION) == "'1.1'"
    assert repr(ANNOTATION_VERSION) == "'1.0'"
    assert repr(MANIFEST_VERSION) == "'1.0'"


def test_versions_concat_batch49():
    """字符串拼接保持原值。"""
    assert EVALUATOR_VERSION + "-beta" == "1.1-beta"
    assert MANIFEST_VERSION + "rc" == "1.0rc"


def test_versions_count_char_batch49():
    """count 字符次数。"""
    assert EVALUATOR_VERSION.count("1") == 2
    assert ANNOTATION_VERSION.count("0") == 1


def test_versions_index_dot_batch49():
    """index 找 '.' 位置。"""
    assert EVALUATOR_VERSION.index(".") == 1
    assert MANIFEST_VERSION.index(".") == 1


# ---------- __all__ 列表更深层 ----------

def test_all_elements_are_str_batch49():
    assert all(isinstance(x, str) for x in eval_mod.__all__)


def test_all_no_duplicates_batch49():
    assert len(eval_mod.__all__) == len(set(eval_mod.__all__))


def test_all_names_match_dir_batch49():
    """__all__ 中每个名称都存在于 dir(evaluation)。"""
    d = dir(eval_mod)
    for name in eval_mod.__all__:
        assert name in d


def test_all_names_accessible_via_getattr_batch49():
    for name in eval_mod.__all__:
        v = getattr(eval_mod, name)
        assert isinstance(v, str)


def test_all_specific_values_batch49():
    assert getattr(eval_mod, "EVALUATOR_VERSION") == "1.1"
    assert getattr(eval_mod, "REPORT_VERSION") == "1.1"
    assert getattr(eval_mod, "ANNOTATION_VERSION") == "1.0"
    assert getattr(eval_mod, "MANIFEST_VERSION") == "1.0"


def test_all_names_in_module_dict_batch49():
    """__all__ 中每个名称都存在于 evaluation.__dict__。"""
    for name in eval_mod.__all__:
        assert name in eval_mod.__dict__


# ---------- 模块属性访问边界 ----------

def test_getattr_default_for_unknown_batch49():
    """getattr 未知属性返回 default。"""
    assert getattr(eval_mod, "DOES_NOT_EXIST", None) is None


def test_getattr_default_value_for_unknown_batch49():
    assert getattr(eval_mod, "ALSO_MISSING", "default") == "default"


def test_hasattr_false_for_unknown_batch49():
    assert not hasattr(eval_mod, "TOTALLY_UNKNOWN_NAME_XYZ")


def test_hasattr_true_for_all_batch49():
    for name in eval_mod.__all__:
        assert hasattr(eval_mod, name)


def test_module_dir_contains_all_names_batch49():
    d = dir(eval_mod)
    for name in eval_mod.__all__:
        assert name in d


def test_module_dir_contains_dunder_doc_batch49():
    assert "__doc__" in dir(eval_mod)


def test_module_dir_contains_dunder_all_batch49():
    assert "__all__" in dir(eval_mod)


def test_module_dir_contains_dunder_name_batch49():
    assert "__name__" in dir(eval_mod)


# ---------- importlib.reload 不改变值 ----------

def test_reload_preserves_evaluator_version_batch49():
    """reload 后 EVALUATOR_VERSION 仍是 '1.1'。"""
    reloaded = importlib.reload(eval_mod)
    assert reloaded.EVALUATOR_VERSION == "1.1"
    assert eval_mod.EVALUATOR_VERSION == "1.1"


def test_reload_preserves_all_versions_batch49():
    importlib.reload(eval_mod)
    assert eval_mod.EVALUATOR_VERSION == "1.1"
    assert eval_mod.REPORT_VERSION == "1.1"
    assert eval_mod.ANNOTATION_VERSION == "1.0"
    assert eval_mod.MANIFEST_VERSION == "1.0"


def test_reload_preserves_all_list_batch49():
    importlib.reload(eval_mod)
    assert eval_mod.__all__ == [
        "EVALUATOR_VERSION",
        "REPORT_VERSION",
        "ANNOTATION_VERSION",
        "MANIFEST_VERSION",
    ]


def test_reload_preserves_docstring_batch49():
    """reload 后 docstring 仍存在。"""
    importlib.reload(eval_mod)
    assert eval_mod.__doc__ is not None
    assert "评测" in eval_mod.__doc__


# ---------- 模块 docstring 内容补强 ----------

def test_docstring_mentions_v1_0_batch49():
    assert "v1.0" in eval_mod.__doc__


def test_docstring_mentions_v1_1_batch49():
    assert "v1.1" in eval_mod.__doc__


def test_docstring_mentions_口径_d_batch49():
    """口径 D 来自之前讨论的设计决定。"""
    assert "口径 D" in eval_mod.__doc__


def test_docstring_mentions_word_internal_split_batch49():
    """词内硬切：v1.0 baseline 的痛点。"""
    assert "词内硬切" in eval_mod.__doc__


def test_docstring_mentions_no_app_dependency_batch49():
    """不依赖 app/* 之外的库（除 jsonschema）。"""
    assert "app" in eval_mod.__doc__


def test_docstring_mentions_text_preservation_batch49():
    assert "text_preservation" in eval_mod.__doc__


def test_docstring_mentions_not_instrumented_batch49():
    """parse/chunk 未插桩的 reason。"""
    assert "not_instrumented" in eval_mod.__doc__


def test_docstring_mentions_null_reason_batch49():
    """缺数据时填 null + reason 不伪造。"""
    assert "null" in eval_mod.__doc__ or "reason" in eval_mod.__doc__


def test_docstring_is_non_empty_string_batch49():
    assert isinstance(eval_mod.__doc__, str)
    assert len(eval_mod.__doc__) > 50


def test_docstring_starts_with_chinese_batch49():
    """docstring 开头是中文。"""
    assert eval_mod.__doc__.lstrip().startswith("评测")


# ---------- AST 结构补强 ----------

def test_ast_module_has_docstring_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_no_function_def_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.FunctionDef) for n in tree.body)


def test_ast_no_class_def_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_import_batch49():
    """模块没有 import（只定义常量）。"""
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in tree.body)


def test_ast_no_async_function_def_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_has_4_top_level_assigns_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    # 4 个常量 + 1 个 __all__ = 5
    assert len(assigns) == 5


def test_ast_all_list_has_4_elements_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    # 找到 __all__ Assign
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert isinstance(all_assign.value, ast.List)
    assert len(all_assign.value.elts) == 4


def test_ast_all_elements_are_constant_str_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    for elt in all_assign.value.elts:
        assert isinstance(elt, ast.Constant)
        assert isinstance(elt.value, str)


def test_ast_evaluator_version_assign_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    ev = next(
        n for n in tree.body
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "EVALUATOR_VERSION" for t in n.targets)
    )
    assert isinstance(ev.value, ast.Constant)
    assert ev.value.value == "1.1"


def test_ast_report_version_assign_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    rv = next(
        n for n in tree.body
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "REPORT_VERSION" for t in n.targets)
    )
    assert rv.value.value == "1.1"


def test_ast_annotation_version_assign_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    av = next(
        n for n in tree.body
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ANNOTATION_VERSION" for t in n.targets)
    )
    assert av.value.value == "1.0"


def test_ast_manifest_version_assign_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    mv = next(
        n for n in tree.body
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "MANIFEST_VERSION" for t in n.targets)
    )
    assert mv.value.value == "1.0"


def test_ast_module_no_try_except_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.Try) for n in tree.body)


def test_ast_module_no_with_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.With) for n in tree.body)


def test_ast_module_no_for_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.For) for n in tree.body)


def test_ast_module_no_if_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.If) for n in tree.body)


def test_ast_assign_targets_single_batch49():
    """每个 Assign 只有 1 个 target（不是 a = b = '1.0'）。"""
    tree = ast.parse(inspect.getsource(eval_mod))
    for n in tree.body:
        if isinstance(n, ast.Assign):
            assert len(n.targets) == 1


def test_ast_constant_values_are_str_batch49():
    tree = ast.parse(inspect.getsource(eval_mod))
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant):
            # __all__ 的 value 是 List 不是 Constant，跳过
            if isinstance(n.value.value, str) or isinstance(n.value.value, list):
                continue
            pytest.fail(f"unexpected constant type: {type(n.value.value)}")


# ---------- forbidden tokens 第一百二十九批 ----------

def _src() -> str:
    return inspect.getsource(eval_mod)


def test_source_no_eval_batch49():
    assert "eval(" not in _src()


def test_source_no_exec_batch49():
    assert "exec(" not in _src()


def test_source_no_compile_batch49():
    assert "compile(" not in _src()


def test_source_no_globals_batch49():
    assert "globals(" not in _src()


def test_source_no_locals_batch49():
    assert "locals(" not in _src()


def test_source_no_os_system_batch49():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch49():
    assert "subprocess" not in _src()


def test_source_no_popen_batch49():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch49():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch49():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch49():
    assert "socket" not in _src()


def test_source_no_requests_batch49():
    assert "requests" not in _src()


def test_source_no_urllib_batch49():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch49():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch49():
    assert "yield" not in _src()


def test_source_no_open_batch49():
    """__init__.py 完全不打开文件。"""
    assert "open(" not in _src()
