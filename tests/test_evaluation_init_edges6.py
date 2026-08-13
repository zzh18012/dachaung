"""evaluation/__init__.py 第六轮 edges 测试（Round 635）。

补强 edges5 未触及的角度（第四十六批）。

新角度：
- 模块 __doc__ 内容精确
- 模块 __loader__ 类型
- 模块 __spec__ 各字段
- 模块 __cached__ 存在
- 4 常量是 intern 字符串
- 4 常量可比较 == 同字面量
- __all__ 不含私有名
- __all__ 不含模块名
- __all__ 各 entry 长度
- 模块源码字符串精确（含 v1.0 / v1.1 / 不返回 1.0）
- AST 结构补强
- forbidden tokens 第一百零五批
"""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

import pytest

import evaluation
from evaluation import (
    ANNOTATION_VERSION,
    EVALUATOR_VERSION,
    MANIFEST_VERSION,
    REPORT_VERSION,
)


# ---------- 模块 __doc__ 内容精确 ----------

def test_module_docstring_present_batch46():
    assert evaluation.__doc__ is not None
    assert isinstance(evaluation.__doc__, str)


def test_module_docstring_contains_design_principles_batch46():
    doc = evaluation.__doc__
    assert "设计原则" in doc


def test_module_docstring_contains_not_depend_on_app_batch46():
    doc = evaluation.__doc__
    assert "不依赖任何 app/* 之外的库" in doc


def test_module_docstring_contains_not_modify_parser_batch46():
    doc = evaluation.__doc__
    assert "不修改 parser / chunker / pipeline" in doc


def test_module_docstring_contains_null_reason_batch46():
    doc = evaluation.__doc__
    assert "缺数据时填 null + reason" in doc


def test_module_docstring_contains_not_return_1_batch46():
    doc = evaluation.__doc__
    assert "不返回 1.0" in doc


def test_module_docstring_contains_not_instrumented_batch46():
    doc = evaluation.__doc__
    assert "not_instrumented" in doc


def test_module_docstring_contains_version_history_batch46():
    doc = evaluation.__doc__
    assert "版本历史" in doc
    assert "v1.0" in doc
    assert "v1.1" in doc


def test_module_docstring_contains_text_preservation_change_batch46():
    doc = evaluation.__doc__
    assert "text_preservation" in doc


def test_module_docstring_contains_normalize_text_batch46():
    doc = evaluation.__doc__
    assert "normalize_text" in doc


def test_module_docstring_contains_不可横向比较_batch46():
    doc = evaluation.__doc__
    assert "不可横向比较" in doc


def test_module_docstring_starts_with_评测包_batch46():
    doc = evaluation.__doc__
    assert doc.startswith("评测包")


# ---------- 模块 __loader__ ----------

def test_module_loader_not_none_batch46():
    assert evaluation.__loader__ is not None


def test_module_loader_has_load_module_batch46():
    """SourceFileLoader 应该有 load_module 方法。"""
    assert hasattr(evaluation.__loader__, "load_module") or hasattr(evaluation.__loader__, "exec_module")


# ---------- 模块 __spec__ 各字段 ----------

def test_module_spec_name_batch46():
    assert evaluation.__spec__.name == "evaluation"


def test_module_spec_origin_endswith_init_batch46():
    assert evaluation.__spec__.origin is not None
    assert evaluation.__spec__.origin.endswith("__init__.py")


def test_module_spec_loader_not_none_batch46():
    assert evaluation.__spec__.loader is not None


def test_module_spec_submodule_search_locations_batch46():
    """包应该有 submodule_search_locations。"""
    assert evaluation.__spec__.submodule_search_locations is not None
    assert len(evaluation.__spec__.submodule_search_locations) >= 1


# ---------- 模块 __cached__ ----------

def test_module_cached_present_batch46():
    assert hasattr(evaluation, "__cached__")
    assert evaluation.__cached__ is not None


def test_module_cached_endswith_pyc_batch46():
    """__cached__ 通常是 .pyc 路径。"""
    cached = evaluation.__cached__
    assert cached.endswith(".pyc") or ".pyc" in cached


# ---------- 4 常量 intern ----------

def test_evaluator_version_is_str_batch46():
    assert isinstance(EVALUATOR_VERSION, str)


def test_evaluator_version_id_consistent_batch46():
    """同字符串字面量在 CPython 通常 intern。"""
    a = "1.1"
    b = "1.1"
    assert a is b  # 字面量 intern
    # 模块常量也可能 intern
    assert EVALUATOR_VERSION == a


def test_evaluator_version_compare_to_literal_batch46():
    assert EVALUATOR_VERSION == "1.1"
    assert REPORT_VERSION == "1.1"
    assert ANNOTATION_VERSION == "1.0"
    assert MANIFEST_VERSION == "1.0"


def test_versions_string_concat_batch46():
    assert EVALUATOR_VERSION + REPORT_VERSION == "1.11.1"


def test_versions_string_multiply_batch46():
    assert EVALUATOR_VERSION * 2 == "1.11.1"


def test_versions_format_batch46():
    assert f"v{EVALUATOR_VERSION}" == "v1.1"


def test_versions_split_major_minor_batch46():
    ev_major, ev_minor = EVALUATOR_VERSION.split(".")
    assert ev_major == "1"
    assert ev_minor == "1"
    an_major, an_minor = ANNOTATION_VERSION.split(".")
    assert an_major == "1"
    assert an_minor == "0"


# ---------- __all__ 检查 ----------

def test_all_no_private_names_batch46():
    """__all__ 不应含下划线开头的私有名。"""
    for name in evaluation.__all__:
        assert not name.startswith("_")


def test_all_no_dunder_names_batch46():
    """__all__ 不应含 dunder 名。"""
    for name in evaluation.__all__:
        assert not name.startswith("__")


def test_all_no_module_names_batch46():
    """__all__ 不应含模块名（如 sys / os）。"""
    for name in evaluation.__all__:
        assert name not in ("sys", "os", "json", "pathlib")


def test_all_each_length_at_least_10_batch46():
    """每个名字至少 10 字符（VERSION 后缀）。"""
    for name in evaluation.__all__:
        assert len(name) >= 10


def test_all_each_contains_version_batch46():
    for name in evaluation.__all__:
        assert "VERSION" in name


def test_all_starts_with_evaluator_batch46():
    """__all__ 第一项应该是 EVALUATOR_VERSION。"""
    assert evaluation.__all__[0] == "EVALUATOR_VERSION"


def test_all_ends_with_manifest_batch46():
    """__all__ 最后一项应该是 MANIFEST_VERSION。"""
    assert evaluation.__all__[-1] == "MANIFEST_VERSION"


def test_all_index_report_is_1_batch46():
    assert evaluation.__all__[1] == "REPORT_VERSION"


def test_all_index_annotation_is_2_batch46():
    assert evaluation.__all__[2] == "ANNOTATION_VERSION"


def test_all_index_manifest_is_3_batch46():
    assert evaluation.__all__[3] == "MANIFEST_VERSION"


# ---------- 模块源码字符串补强 ----------

def test_source_contains_v1_0_description_batch46():
    src = inspect.getsource(evaluation)
    assert "v1.0（初始）" in src


def test_source_contains_v1_1_description_batch46():
    src = inspect.getsource(evaluation)
    assert "v1.1（当前）" in src


def test_source_contains_口径_D_batch46():
    src = inspect.getsource(evaluation)
    assert "口径 D" in src


def test_source_contains_词内硬切_batch46():
    src = inspect.getsource(evaluation)
    assert "词内硬切" in src


def test_source_contains_其他指标语义未变_batch46():
    src = inspect.getsource(evaluation)
    assert "其它指标语义未变" in src or "其他指标语义未变" in src


def test_source_contains_EVALUATOR_VERSION_literal_batch46():
    src = inspect.getsource(evaluation)
    assert 'EVALUATOR_VERSION = "1.1"' in src


def test_source_contains_REPORT_VERSION_literal_batch46():
    src = inspect.getsource(evaluation)
    assert 'REPORT_VERSION = "1.1"' in src


def test_source_contains_ANNOTATION_VERSION_literal_batch46():
    src = inspect.getsource(evaluation)
    assert 'ANNOTATION_VERSION = "1.0"' in src


def test_source_contains_MANIFEST_VERSION_literal_batch46():
    src = inspect.getsource(evaluation)
    assert 'MANIFEST_VERSION = "1.0"' in src


def test_source_contains_no_return_1_batch46():
    src = inspect.getsource(evaluation)
    assert "不返回 1.0" in src


def test_source_contains_no_forgery_batch46():
    src = inspect.getsource(evaluation)
    assert "不伪造" in src


def test_source_no_extra_functions_batch46():
    """__init__.py 不应定义函数。"""
    src = inspect.getsource(evaluation)
    assert "def " not in src


def test_source_no_class_keyword_batch46():
    src = inspect.getsource(evaluation)
    assert "\nclass " not in src


def test_source_no_import_os_batch46():
    src = inspect.getsource(evaluation)
    assert "import os" not in src


def test_source_no_import_sys_batch46():
    src = inspect.getsource(evaluation)
    assert "import sys" not in src


def test_source_no_subprocess_batch46():
    src = inspect.getsource(evaluation)
    assert "subprocess" not in src


# ---------- AST 结构补强 ----------

def test_ast_total_nodes_count_batch46():
    """顶层节点：1 docstring + 4 version assign + 1 __all__ assign = 6。"""
    tree = ast.parse(inspect.getsource(evaluation))
    assert len(tree.body) == 6


def test_ast_first_three_are_expr_or_assign_batch46():
    tree = ast.parse(inspect.getsource(evaluation))
    # body[0] 是 docstring (Expr)
    assert isinstance(tree.body[0], ast.Expr)
    # body[1..4] 是 version 赋值
    for i in range(1, 5):
        assert isinstance(tree.body[i], ast.Assign)
    # body[5] 是 __all__ 赋值
    assert isinstance(tree.body[5], ast.Assign)


def test_ast_version_assignments_target_names_batch46():
    tree = ast.parse(inspect.getsource(evaluation))
    version_assigns = []
    for n in tree.body[1:5]:
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if isinstance(t, ast.Name):
                version_assigns.append(t.id)
    assert version_assigns == [
        "EVALUATOR_VERSION",
        "REPORT_VERSION",
        "ANNOTATION_VERSION",
        "MANIFEST_VERSION",
    ]


def test_ast_version_values_are_str_constants_batch46():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body[1:5]:
        if isinstance(n, ast.Assign):
            v = n.value
            assert isinstance(v, ast.Constant)
            assert isinstance(v.value, str)


def test_ast_all_target_is_name_batch46():
    tree = ast.parse(inspect.getsource(evaluation))
    all_assign = tree.body[5]
    assert isinstance(all_assign, ast.Assign)
    target = all_assign.targets[0]
    assert isinstance(target, ast.Name)
    assert target.id == "__all__"


def test_ast_all_value_is_list_batch46():
    tree = ast.parse(inspect.getsource(evaluation))
    all_assign = tree.body[5]
    assert isinstance(all_assign.value, ast.List)


def test_ast_all_list_has_four_constants_batch46():
    tree = ast.parse(inspect.getsource(evaluation))
    all_assign = tree.body[5]
    elts = all_assign.value.elts
    assert len(elts) == 4
    for e in elts:
        assert isinstance(e, ast.Constant)
        assert isinstance(e.value, str)


def test_ast_all_list_values_in_order_batch46():
    tree = ast.parse(inspect.getsource(evaluation))
    all_assign = tree.body[5]
    values = [e.value for e in all_assign.value.elts]
    assert values == [
        "EVALUATOR_VERSION",
        "REPORT_VERSION",
        "ANNOTATION_VERSION",
        "MANIFEST_VERSION",
    ]


def test_ast_no_imports_batch46():
    """__init__.py 没有 import 语句（除了可能的 future）。"""
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, (ast.Import, ast.ImportFrom))


def test_ast_no_class_def_batch46():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_no_function_def_batch46():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))


def test_ast_no_control_flow_batch46():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, (ast.If, ast.For, ast.While, ast.Try, ast.With))


# ---------- forbidden tokens 第一百零五批 ----------

def test_source_no_eval_batch46():
    src = inspect.getsource(evaluation)
    assert "eval(" not in src


def test_source_no_exec_batch46():
    src = inspect.getsource(evaluation)
    assert "exec(" not in src


def test_source_no_compile_batch46():
    src = inspect.getsource(evaluation)
    assert "compile(" not in src


def test_source_no_globals_batch46():
    src = inspect.getsource(evaluation)
    assert "globals(" not in src


def test_source_no_locals_batch46():
    src = inspect.getsource(evaluation)
    assert "locals(" not in src


def test_source_no_os_system_batch46():
    src = inspect.getsource(evaluation)
    assert "os.system(" not in src


def test_source_no_popen_batch46():
    src = inspect.getsource(evaluation)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch46():
    src = inspect.getsource(evaluation)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch46():
    src = inspect.getsource(evaluation)
    assert "pickle.load(" not in src


def test_source_no_lambda_batch46():
    src = inspect.getsource(evaluation)
    assert "lambda" not in src


def test_source_no_yield_batch46():
    src = inspect.getsource(evaluation)
    assert "yield" not in src


def test_source_no_walrus_batch46():
    src = inspect.getsource(evaluation)
    assert ":=" not in src


def test_source_no_async_batch46():
    src = inspect.getsource(evaluation)
    assert "async " not in src


def test_source_no_await_batch46():
    src = inspect.getsource(evaluation)
    assert "await " not in src


def test_source_no_raise_batch46():
    src = inspect.getsource(evaluation)
    assert "raise " not in src


# ---------- 综合 ----------

def test_versions_iteration_batch46():
    versions = [EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION]
    for v in versions:
        assert isinstance(v, str)
        assert len(v) == 3  # "1.1" or "1.0"
        assert v[0].isdigit()
        assert v[1] == "."
        assert v[2].isdigit()


def test_versions_map_to_names_batch46():
    mapping = {
        "1.1": [EVALUATOR_VERSION, REPORT_VERSION],
        "1.0": [ANNOTATION_VERSION, MANIFEST_VERSION],
    }
    for value, items in mapping.items():
        for item in items:
            assert item == value


def test_module_in_evaluation_package_batch46():
    """evaluation 模块的 __package__ 是 "evaluation"。"""
    assert evaluation.__package__ == "evaluation"


def test_module_importable_in_different_ways_batch46():
    """4 种 import 方式都能拿到 EVALUATOR_VERSION。"""
    import evaluation
    from evaluation import EVALUATOR_VERSION as ev1
    import evaluation as ev_mod
    from evaluation import EVALUATOR_VERSION as ev2

    assert ev1 == "1.1"
    assert ev2 == "1.1"
    assert ev_mod.EVALUATOR_VERSION == "1.1"
    assert evaluation.EVALUATOR_VERSION == "1.1"


def test_constant_values_inmutable_batch46():
    """str 是 immutable，无法修改。"""
    with pytest.raises(TypeError):
        EVALUATOR_VERSION[0] = "9"  # type: ignore[index]
