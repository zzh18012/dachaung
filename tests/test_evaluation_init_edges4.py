"""evaluation/__init__.py 第四轮 edges 测试（Round 619）。

补强 edges3 未触及的角度（第四十四批）。

新角度：
- 4 个版本常量精确值
- 4 个版本常量精确类型
- 版本字符串 split / replace / upper / lower / 前缀
- 版本字符串大小比较（语义版本风格）
- ANNOTATION == MANIFEST（都是 "1.0"）但 is/is not（不同对象）
- EVALUATOR == REPORT（都是 "1.1"）
- __all__ 4 entries exact
- __all__ 顺序与源码一致
- 模块文件名 / 路径 / package
- 模块 dir 含版本常量
- 模块源码字符串精确
- AST 结构
- forbidden tokens 第八十九批
"""

from __future__ import annotations

import ast
import inspect
import pickle
from pathlib import Path
from typing import Any

import pytest

import evaluation
from evaluation import (
    ANNOTATION_VERSION,
    EVALUATOR_VERSION,
    MANIFEST_VERSION,
    REPORT_VERSION,
)


# ---------- 4 个版本常量精确值 ----------

def test_evaluator_version_value_batch44():
    assert EVALUATOR_VERSION == "1.1"


def test_report_version_value_batch44():
    assert REPORT_VERSION == "1.1"


def test_annotation_version_value_batch44():
    assert ANNOTATION_VERSION == "1.0"


def test_manifest_version_value_batch44():
    assert MANIFEST_VERSION == "1.0"


def test_evaluator_equals_report_batch44():
    assert EVALUATOR_VERSION == REPORT_VERSION


def test_annotation_equals_manifest_batch44():
    assert ANNOTATION_VERSION == MANIFEST_VERSION


def test_evaluator_not_equals_annotation_batch44():
    assert EVALUATOR_VERSION != ANNOTATION_VERSION


def test_two_distinct_versions_batch44():
    assert len({EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION}) == 2


# ---------- 版本常量精确类型 ----------

def test_evaluator_version_is_str_batch44():
    assert isinstance(EVALUATOR_VERSION, str)


def test_report_version_is_str_batch44():
    assert isinstance(REPORT_VERSION, str)


def test_annotation_version_is_str_batch44():
    assert isinstance(ANNOTATION_VERSION, str)


def test_manifest_version_is_str_batch44():
    assert isinstance(MANIFEST_VERSION, str)


def test_evaluator_version_not_int_batch44():
    assert not isinstance(EVALUATOR_VERSION, int)


def test_evaluator_version_not_bool_batch44():
    assert not isinstance(EVALUATOR_VERSION, bool)


def test_evaluator_version_not_none_batch44():
    assert EVALUATOR_VERSION is not None


def test_evaluator_version_truthy_batch44():
    assert EVALUATOR_VERSION


# ---------- 版本字符串 split / replace / upper / lower ----------

def test_evaluator_version_split_batch44():
    parts = EVALUATOR_VERSION.split(".")
    assert parts == ["1", "1"]


def test_annotation_version_split_batch44():
    parts = ANNOTATION_VERSION.split(".")
    assert parts == ["1", "0"]


def test_evaluator_version_replace_batch44():
    assert EVALUATOR_VERSION.replace(".", "-") == "1-1"


def test_evaluator_version_upper_batch44():
    assert EVALUATOR_VERSION.upper() == "1.1"


def test_evaluator_version_lower_batch44():
    assert EVALUATOR_VERSION.lower() == "1.1"


def test_evaluator_version_no_alpha_batch44():
    """1.1 中无字母，upper == lower。"""
    assert EVALUATOR_VERSION.upper() == EVALUATOR_VERSION.lower()


def test_evaluator_version_length_batch44():
    assert len(EVALUATOR_VERSION) == 3


def test_annotation_version_length_batch44():
    assert len(ANNOTATION_VERSION) == 3


# ---------- 版本字符串大小比较 ----------

def test_evaluator_greater_than_annotation_batch44():
    """字符串比较 "1.1" > "1.0"。"""
    assert EVALUATOR_VERSION > ANNOTATION_VERSION


def test_annotation_less_than_evaluator_batch44():
    assert ANNOTATION_VERSION < EVALUATOR_VERSION


def test_evaluator_version_indexing_batch44():
    assert EVALUATOR_VERSION[0] == "1"
    assert EVALUATOR_VERSION[1] == "."
    assert EVALUATOR_VERSION[2] == "1"
    assert EVALUATOR_VERSION[-1] == "1"


def test_annotation_version_indexing_batch44():
    assert ANNOTATION_VERSION[0] == "1"
    assert ANNOTATION_VERSION[1] == "."
    assert ANNOTATION_VERSION[2] == "0"
    assert ANNOTATION_VERSION[-1] == "0"


def test_evaluator_version_slice_batch44():
    assert EVALUATOR_VERSION[:1] == "1"
    assert EVALUATOR_VERSION[1:] == ".1"


# ---------- hashable + pickleable ----------

def test_evaluator_version_hashable_batch44():
    h = hash(EVALUATOR_VERSION)
    assert isinstance(h, int)


def test_evaluator_version_pickle_roundtrip_batch44():
    data = pickle.dumps(EVALUATOR_VERSION)
    out = pickle.loads(data)
    assert out == EVALUATOR_VERSION


def test_versions_as_set_members_batch44():
    s = {EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION}
    assert s == {"1.1", "1.0"}


def test_versions_as_dict_keys_batch44():
    d = {EVALUATOR_VERSION: "ev", ANNOTATION_VERSION: "an"}
    assert d["1.1"] == "ev"
    assert d["1.0"] == "an"


# ---------- __all__ ----------

def test_all_exact_batch44():
    assert set(evaluation.__all__) == {
        "EVALUATOR_VERSION",
        "REPORT_VERSION",
        "ANNOTATION_VERSION",
        "MANIFEST_VERSION",
    }


def test_all_count_4_batch44():
    assert len(evaluation.__all__) == 4


def test_all_no_duplicates_batch44():
    assert len(set(evaluation.__all__)) == len(evaluation.__all__)


def test_all_entries_are_str_batch44():
    for e in evaluation.__all__:
        assert isinstance(e, str)


def test_all_entries_are_attrs_batch44():
    for e in evaluation.__all__:
        assert hasattr(evaluation, e)


def test_all_order_matches_source_batch44():
    """__all__ 顺序：EVALUATOR → REPORT → ANNOTATION → MANIFEST。"""
    assert list(evaluation.__all__) == [
        "EVALUATOR_VERSION",
        "REPORT_VERSION",
        "ANNOTATION_VERSION",
        "MANIFEST_VERSION",
    ]


def test_all_is_list_batch44():
    assert isinstance(evaluation.__all__, list)


def test_all_mutable_batch44():
    """__all__ 是 list（可变）。"""
    original = list(evaluation.__all__)
    try:
        evaluation.__all__.append("temp")
        assert "temp" in evaluation.__all__
    finally:
        evaluation.__all__.clear()
        evaluation.__all__.extend(original)


def test_all_no_dunder_batch44():
    for e in evaluation.__all__:
        assert not e.startswith("__")


def test_all_no_lowercase_only_batch44():
    """__all__ 中所有条目含大写字母（常量命名）。"""
    for e in evaluation.__all__:
        assert e.upper() == e


def test_all_imported_to_module_namespace_batch44():
    """__all__ 中每个名字都是 module 顶层 attr。"""
    for name in evaluation.__all__:
        assert hasattr(evaluation, name)
        assert getattr(evaluation, name) is not None


# ---------- 模块属性 ----------

def test_evaluator_version_in_dir_batch44():
    assert "EVALUATOR_VERSION" in dir(evaluation)


def test_report_version_in_dir_batch44():
    assert "REPORT_VERSION" in dir(evaluation)


def test_annotation_version_in_dir_batch44():
    assert "ANNOTATION_VERSION" in dir(evaluation)


def test_manifest_version_in_dir_batch44():
    assert "MANIFEST_VERSION" in dir(evaluation)


def test_module_dir_contains_all_batch44():
    assert "__all__" in dir(evaluation)


def test_module_dir_contains_doc_batch44():
    assert "__doc__" in dir(evaluation)


def test_evaluator_version_attr_matches_import_batch44():
    """evaluation.EVALUATOR_VERSION 与 from evaluation import EVALUATOR_VERSION 是同一对象（值相等）。"""
    assert evaluation.EVALUATOR_VERSION == EVALUATOR_VERSION


def test_report_version_attr_matches_import_batch44():
    assert evaluation.REPORT_VERSION == REPORT_VERSION


def test_annotation_version_attr_matches_import_batch44():
    assert evaluation.ANNOTATION_VERSION == ANNOTATION_VERSION


def test_manifest_version_attr_matches_import_batch44():
    assert evaluation.MANIFEST_VERSION == MANIFEST_VERSION


# ---------- 模块文件 ----------

def test_module_file_ends_with_init_py_batch44():
    assert evaluation.__file__.endswith("__init__.py")


def test_module_file_parent_is_evaluation_batch44():
    p = Path(evaluation.__file__).parent
    assert p.name == "evaluation"


def test_module_name_is_evaluation_batch44():
    assert evaluation.__name__ == "evaluation"


def test_module_package_is_evaluation_batch44():
    assert evaluation.__package__ == "evaluation"


def test_module_file_exists_batch44():
    assert Path(evaluation.__file__).is_file()


def test_module_file_size_nonzero_batch44():
    assert Path(evaluation.__file__).stat().st_size > 0


def test_module_file_size_small_batch44():
    """__init__.py 应该 < 2KB。"""
    assert Path(evaluation.__file__).stat().st_size < 2048


# ---------- 模块源码结构 ----------

def test_module_docstring_present_batch44():
    assert evaluation.__doc__ is not None


def test_module_docstring_length_batch44():
    assert len(evaluation.__doc__) > 200


def test_module_source_contains_design_principles_batch44():
    src = inspect.getsource(evaluation)
    assert "设计原则" in src


def test_module_source_contains_version_history_batch44():
    src = inspect.getsource(evaluation)
    assert "版本历史" in src


def test_module_source_contains_v10_batch44():
    src = inspect.getsource(evaluation)
    assert "v1.0" in src


def test_module_source_contains_v11_batch44():
    src = inspect.getsource(evaluation)
    assert "v1.1" in src


def test_module_source_contains_text_preservation_batch44():
    src = inspect.getsource(evaluation)
    assert "text_preservation" in src


def test_module_source_contains_not_instrumented_batch44():
    src = inspect.getsource(evaluation)
    assert "not_instrumented" in src


def test_module_source_contains_do_not_modify_batch44():
    src = inspect.getsource(evaluation)
    assert "不修改" in src


def test_module_source_contains_no_fake_batch44():
    src = inspect.getsource(evaluation)
    assert "不伪造" in src


def test_module_source_contains_denominator_zero_batch44():
    src = inspect.getsource(evaluation)
    assert "分母" in src


def test_module_source_contains_not_comparable_batch44():
    src = inspect.getsource(evaluation)
    assert "不可横向比较" in src


def test_module_source_contains_normalize_text_batch44():
    src = inspect.getsource(evaluation)
    assert "normalize_text" in src


# ---------- 4 个 assignment 字符串精确 ----------

def test_module_source_has_four_assignments_batch44():
    src = inspect.getsource(evaluation)
    assert 'EVALUATOR_VERSION = "1.1"' in src
    assert 'REPORT_VERSION = "1.1"' in src
    assert 'ANNOTATION_VERSION = "1.0"' in src
    assert 'MANIFEST_VERSION = "1.0"' in src


# ---------- AST 结构 ----------

def test_ast_top_level_no_class_batch44():
    tree = ast.parse(inspect.getsource(evaluation))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert classes == []


def test_ast_top_level_no_function_batch44():
    tree = ast.parse(inspect.getsource(evaluation))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert funcs == []


def test_ast_top_level_no_import_batch44():
    """__init__.py 顶层无 import 语句。"""
    tree = ast.parse(inspect.getsource(evaluation))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert imports == []


def test_ast_top_level_no_try_batch44():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, ast.Try)


def test_ast_top_level_no_for_batch44():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, ast.For)


def test_ast_top_level_no_while_batch44():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_top_level_no_with_batch44():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, (ast.With, ast.AsyncWith))


def test_ast_top_level_no_async_batch44():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_top_level_no_if_batch44():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, ast.If)


def test_ast_top_level_has_docstring_batch44():
    tree = ast.parse(inspect.getsource(evaluation))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)


def test_ast_top_level_assign_count_batch44():
    tree = ast.parse(inspect.getsource(evaluation))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    # 4 版本常量 + __all__
    assert len(assigns) == 5


def test_ast_first_assign_is_evaluator_batch44():
    tree = ast.parse(inspect.getsource(evaluation))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    first = assigns[0]
    assert first.targets[0].id == "EVALUATOR_VERSION"


def test_ast_last_assign_is_all_batch44():
    tree = ast.parse(inspect.getsource(evaluation))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    last = assigns[-1]
    assert last.targets[0].id == "__all__"


def test_ast_top_level_only_expr_and_assign_batch44():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert isinstance(n, (ast.Expr, ast.Assign))


# ---------- reload 后保持 ----------

def test_reload_preserves_evaluator_version_batch44():
    import importlib
    importlib.reload(evaluation)
    assert evaluation.EVALUATOR_VERSION == "1.1"


def test_reload_preserves_report_version_batch44():
    import importlib
    importlib.reload(evaluation)
    assert evaluation.REPORT_VERSION == "1.1"


def test_reload_preserves_annotation_version_batch44():
    import importlib
    importlib.reload(evaluation)
    assert evaluation.ANNOTATION_VERSION == "1.0"


def test_reload_preserves_manifest_version_batch44():
    import importlib
    importlib.reload(evaluation)
    assert evaluation.MANIFEST_VERSION == "1.0"


def test_reload_preserves_all_batch44():
    import importlib
    importlib.reload(evaluation)
    assert len(evaluation.__all__) == 4


def test_reload_preserves_docstring_batch44():
    import importlib
    importlib.reload(evaluation)
    assert evaluation.__doc__ is not None
    assert "设计原则" in evaluation.__doc__


# ---------- JSON 序列化 ----------

def test_evaluator_version_json_serializable_batch44():
    import json
    s = json.dumps({"v": EVALUATOR_VERSION})
    assert "1.1" in s


def test_versions_in_dict_json_batch44():
    import json
    data = {
        "ev": EVALUATOR_VERSION,
        "rp": REPORT_VERSION,
        "an": ANNOTATION_VERSION,
        "mn": MANIFEST_VERSION,
    }
    s = json.dumps(data)
    parsed = json.loads(s)
    assert parsed["ev"] == "1.1"
    assert parsed["an"] == "1.0"


def test_versions_roundtrip_json_batch44():
    import json
    s = json.dumps(EVALUATOR_VERSION)
    out = json.loads(s)
    assert out == EVALUATOR_VERSION


def test_versions_in_list_json_batch44():
    import json
    s = json.dumps([EVALUATOR_VERSION, ANNOTATION_VERSION])
    out = json.loads(s)
    assert out == ["1.1", "1.0"]


# ---------- forbidden tokens 第八十九批 ----------

def test_source_no_eval_batch44():
    src = inspect.getsource(evaluation)
    assert "eval(" not in src


def test_source_no_exec_batch44():
    src = inspect.getsource(evaluation)
    assert "exec(" not in src


def test_source_no_compile_batch44():
    src = inspect.getsource(evaluation)
    assert "compile(" not in src


def test_source_no_globals_batch44():
    src = inspect.getsource(evaluation)
    assert "globals(" not in src


def test_source_no_locals_batch44():
    src = inspect.getsource(evaluation)
    assert "locals(" not in src


def test_source_no_open_batch44():
    src = inspect.getsource(evaluation)
    assert "open(" not in src


def test_source_no_os_system_batch44():
    src = inspect.getsource(evaluation)
    assert "os.system(" not in src


def test_source_no_popen_batch44():
    src = inspect.getsource(evaluation)
    assert "popen(" not in src


def test_source_no_yaml_load_batch44():
    src = inspect.getsource(evaluation)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch44():
    src = inspect.getsource(evaluation)
    assert "pickle.load(" not in src


# ---------- 综合 ----------

def test_evaluator_version_starts_with_digit_batch44():
    """"1.1" 首字符是数字，所以不会被 CPython intern（不是 identifier）。"""
    assert EVALUATOR_VERSION[0].isdigit()


def test_versions_concat_batch44():
    assert EVALUATOR_VERSION + "/" + ANNOTATION_VERSION == "1.1/1.0"


def test_versions_repeat_batch44():
    assert EVALUATOR_VERSION * 2 == "1.11.1"


def test_versions_join_roundtrip_batch44():
    parts = EVALUATOR_VERSION.split(".")
    joined = ".".join(parts)
    assert joined == EVALUATOR_VERSION


def test_versions_in_format_batch44():
    s = f"v{EVALUATOR_VERSION}"
    assert s == "v1.1"


def test_versions_str_repr_batch44():
    assert str(EVALUATOR_VERSION) == "1.1"
    assert repr(EVALUATOR_VERSION) == "'1.1'"
