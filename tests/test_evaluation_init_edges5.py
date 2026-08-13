"""evaluation/__init__.py 第五轮 edges 测试（Round 627）。

补强 edges4 未触及的角度（第四十五批）。

新角度：
- 模块对象属性（__name__/__package__/__file__/__loader__/__spec__/__builtins__/__path__）
- sys.modules 中 evaluation 与导入一致
- dir(evaluation) / vars(evaluation) 包含 4 个常量
- 模块 hashable / picklable
- 模块 not __main__
- 模块 __path__ 是 list
- 模块 __spec__.name == "evaluation"
- 4 个常量 hashable + id 一致
- 版本字符串 hex 检查 / 点位置 / 末尾非点
- __all__ 各 entry 在 __dict__
- 模块源码字符串（EVALUATOR_VERSION = "1.1" / v1.0/v1.1 版本历史）
- AST 结构（首节点 docstring / 第二 future / 末节点 __all__）
- forbidden tokens 第九十七批
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


# ---------- 模块对象属性 ----------

def test_module_name_batch45():
    assert evaluation.__name__ == "evaluation"


def test_module_package_batch45():
    assert evaluation.__package__ == "evaluation"


def test_module_file_endswith_init_batch45():
    assert evaluation.__file__.endswith("__init__.py")


def test_module_file_absolute_batch45():
    assert Path(evaluation.__file__).is_absolute()


def test_module_file_exists_batch45():
    assert Path(evaluation.__file__).is_file()


def test_module_loader_present_batch45():
    assert hasattr(evaluation, "__loader__")
    assert evaluation.__loader__ is not None


def test_module_spec_present_batch45():
    assert hasattr(evaluation, "__spec__")
    assert evaluation.__spec__ is not None


def test_module_spec_name_batch45():
    assert evaluation.__spec__.name == "evaluation"


def test_module_builtins_present_batch45():
    assert hasattr(evaluation, "__builtins__")


def test_module_path_is_list_batch45():
    assert isinstance(evaluation.__path__, list)
    assert len(evaluation.__path__) >= 1


def test_module_path_entries_exist_batch45():
    for p in evaluation.__path__:
        assert Path(p).is_dir()


def test_module_not_main_batch45():
    assert evaluation.__name__ != "__main__"


# ---------- sys.modules 一致性 ----------

def test_sys_modules_consistency_batch45():
    assert sys.modules.get("evaluation") is evaluation


def test_sys_modules_identity_batch45():
    """两次导入同一对象。"""
    import evaluation as ev2  # noqa: F401
    assert ev2 is evaluation


# ---------- dir / vars ----------

def test_dir_contains_all_four_batch45():
    names = dir(evaluation)
    for n in ("EVALUATOR_VERSION", "REPORT_VERSION", "ANNOTATION_VERSION", "MANIFEST_VERSION"):
        assert n in names


def test_dir_contains_all_batch45():
    assert "__all__" in dir(evaluation)


def test_vars_contains_all_four_batch45():
    v = vars(evaluation)
    for n in ("EVALUATOR_VERSION", "REPORT_VERSION", "ANNOTATION_VERSION", "MANIFEST_VERSION"):
        assert n in v


def test_vars_all_value_batch45():
    v = vars(evaluation)
    assert v["__all__"] == [
        "EVALUATOR_VERSION",
        "REPORT_VERSION",
        "ANNOTATION_VERSION",
        "MANIFEST_VERSION",
    ]


def test_evaluation_dict_is_module_dict_batch45():
    """vars(evaluation) 是 evaluation.__dict__。"""
    assert vars(evaluation) is evaluation.__dict__


# ---------- 模块 hashable / picklable ----------

def test_module_hashable_batch45():
    """模块对象可 hash（按 id）。"""
    h = hash(evaluation)
    assert isinstance(h, int)


def test_module_not_picklable_batch45():
    """模块对象不能 pickle（CPython 限制）。"""
    import pickle
    with pytest.raises(TypeError):
        pickle.dumps(evaluation)


def test_module_identity_batch45():
    """evaluation 是单例。"""
    import evaluation as ev2  # noqa: F401
    assert id(ev2) == id(evaluation)


# ---------- 常量 hash + id ----------

def test_evaluator_version_hashable_batch45():
    h = hash(EVALUATOR_VERSION)
    assert isinstance(h, int)


def test_report_version_hashable_batch45():
    assert isinstance(hash(REPORT_VERSION), int)


def test_annotation_version_hashable_batch45():
    assert isinstance(hash(ANNOTATION_VERSION), int)


def test_manifest_version_hashable_batch45():
    assert isinstance(hash(MANIFEST_VERSION), int)


def test_versions_same_value_share_hash_batch45():
    """同字符串字面量在 CPython 通常被 intern。"""
    assert hash(EVALUATOR_VERSION) == hash("1.1")
    assert hash(REPORT_VERSION) == hash("1.1")
    assert hash(ANNOTATION_VERSION) == hash("1.0")
    assert hash(MANIFEST_VERSION) == hash("1.0")


def test_version_in_dict_key_batch45():
    """版本字符串可做 dict key。"""
    d = {EVALUATOR_VERSION: "ev", REPORT_VERSION: "rp"}
    assert d["1.1"] in ("ev", "rp")


def test_version_in_set_batch45():
    s = {EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION}
    # EVALUATOR == REPORT，所以 set 只有 2 个
    assert len(s) == 2


# ---------- 版本字符串结构 ----------

def test_evaluator_version_one_dot_batch45():
    assert EVALUATOR_VERSION.count(".") == 1


def test_report_version_one_dot_batch45():
    assert REPORT_VERSION.count(".") == 1


def test_annotation_version_one_dot_batch45():
    assert ANNOTATION_VERSION.count(".") == 1


def test_manifest_version_one_dot_batch45():
    assert MANIFEST_VERSION.count(".") == 1


def test_evaluator_version_starts_with_digit_batch45():
    assert EVALUATOR_VERSION[0].isdigit()


def test_evaluator_version_ends_with_digit_batch45():
    assert EVALUATOR_VERSION[-1].isdigit()


def test_evaluator_version_no_alpha_batch45():
    assert not any(c.isalpha() for c in EVALUATOR_VERSION)


def test_evaluator_version_no_underscore_batch45():
    assert "_" not in EVALUATOR_VERSION


def test_evaluator_version_no_dash_batch45():
    assert "-" not in EVALUATOR_VERSION


def test_evaluator_version_no_space_batch45():
    assert " " not in EVALUATOR_VERSION


def test_evaluator_version_no_hex_letters_batch45():
    """版本字符串不包含 a-f。"""
    for c in EVALUATOR_VERSION.lower():
        assert c not in "abcdef"


def test_evaluator_version_split_dot_batch45():
    parts = EVALUATOR_VERSION.split(".")
    assert parts == ["1", "1"]


def test_annotation_version_split_dot_batch45():
    parts = ANNOTATION_VERSION.split(".")
    assert parts == ["1", "0"]


def test_evaluator_version_major_minor_batch45():
    parts = EVALUATOR_VERSION.split(".")
    assert int(parts[0]) == 1  # major
    assert int(parts[1]) == 1  # minor


def test_annotation_version_major_minor_batch45():
    parts = ANNOTATION_VERSION.split(".")
    assert int(parts[0]) == 1
    assert int(parts[1]) == 0


# ---------- __all__ entries in __dict__ ----------

def test_all_entries_in_dict_batch45():
    for name in evaluation.__all__:
        assert name in evaluation.__dict__


def test_all_entries_callable_false_batch45():
    """__all__ 里都是字符串字面量，不是 callable。"""
    for name in evaluation.__all__:
        v = getattr(evaluation, name)
        assert not callable(v)


def test_all_entries_str_type_batch45():
    for name in evaluation.__all__:
        v = getattr(evaluation, name)
        assert isinstance(v, str)


def test_all_count_four_batch45():
    assert len(evaluation.__all__) == 4


def test_all_unique_batch45():
    assert len(set(evaluation.__all__)) == len(evaluation.__all__)


def test_all_each_length_3_batch45():
    """每个名字长度都是 3 个字符以上。"""
    for name in evaluation.__all__:
        assert len(name) >= 3


def test_all_each_uppercase_batch45():
    """每个名字都是大写+下划线。"""
    for name in evaluation.__all__:
        for c in name:
            assert c.isupper() or c == "_"


def test_all_each_ends_with_version_batch45():
    """每个名字都以 _VERSION 结尾。"""
    for name in evaluation.__all__:
        assert name.endswith("_VERSION")


# ---------- 模块源码字符串 ----------

def test_source_contains_evaluator_version_assignment_batch45():
    src = inspect.getsource(evaluation)
    assert 'EVALUATOR_VERSION = "1.1"' in src


def test_source_contains_report_version_assignment_batch45():
    src = inspect.getsource(evaluation)
    assert 'REPORT_VERSION = "1.1"' in src


def test_source_contains_annotation_version_assignment_batch45():
    src = inspect.getsource(evaluation)
    assert 'ANNOTATION_VERSION = "1.0"' in src


def test_source_contains_manifest_version_assignment_batch45():
    src = inspect.getsource(evaluation)
    assert 'MANIFEST_VERSION = "1.0"' in src


def test_source_contains_docstring_design_principles_batch45():
    src = inspect.getsource(evaluation)
    assert "设计原则" in src
    assert "不依赖任何 app/* 之外的库" in src
    assert "不修改 parser / chunker / pipeline" in src
    assert "缺数据时填 null + reason" in src


def test_source_contains_version_history_v1_0_batch45():
    src = inspect.getsource(evaluation)
    assert "v1.0" in src


def test_source_contains_version_history_v1_1_batch45():
    src = inspect.getsource(evaluation)
    assert "v1.1" in src


def test_source_contains_text_preservation_change_note_batch45():
    src = inspect.getsource(evaluation)
    assert "text_preservation" in src


def test_source_contains_normalize_text_note_batch45():
    src = inspect.getsource(evaluation)
    assert "normalize_text" in src


def test_source_contains_not_instrumented_batch45():
    src = inspect.getsource(evaluation)
    assert "not_instrumented" in src


def test_source_contains_all_definition_batch45():
    src = inspect.getsource(evaluation)
    assert "__all__ = [" in src


def test_source_contains_all_four_names_batch45():
    src = inspect.getsource(evaluation)
    for name in ("EVALUATOR_VERSION", "REPORT_VERSION", "ANNOTATION_VERSION", "MANIFEST_VERSION"):
        assert name in src


def test_source_no_relative_import_batch45():
    src = inspect.getsource(evaluation)
    assert "from ." not in src
    assert "from .." not in src


def test_source_no_import_batch45():
    """模块顶层没有 import 语句（除了 future）。"""
    src = inspect.getsource(evaluation)
    # 实际只有 from __future__ ... 但本文件没用，所以源里没有 import
    # 验证：不含 'import os' / 'import sys' / 'from json' 等
    for forbidden in ("import os", "import sys", "import json", "from json", "from pathlib", "from typing"):
        assert forbidden not in src


# ---------- AST 结构 ----------

def test_ast_first_node_docstring_batch45():
    tree = ast.parse(inspect.getsource(evaluation))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)
    assert isinstance(first.value.value, str)


def test_ast_no_future_import_batch45():
    """这个文件没有 from __future__，因为 __init__.py 没用到 PEP 604 union。"""
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            assert n.module != "__future__"


def test_ast_four_assignments_for_versions_batch45():
    tree = ast.parse(inspect.getsource(evaluation))
    assigns = [
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and len(n.targets) == 1
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id.endswith("_VERSION")
    ]
    assert len(assigns) == 4


def test_ast_all_assignment_batch45():
    tree = ast.parse(inspect.getsource(evaluation))
    all_assigns = [
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and len(n.targets) == 1
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == "__all__"
    ]
    assert len(all_assigns) == 1


def test_ast_all_is_list_of_str_batch45():
    tree = ast.parse(inspect.getsource(evaluation))
    all_assign = [
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and len(n.targets) == 1
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == "__all__"
    ][0]
    assert isinstance(all_assign.value, ast.List)
    for elt in all_assign.value.elts:
        assert isinstance(elt, ast.Constant)
        assert isinstance(elt.value, str)


def test_ast_last_node_is_all_batch45():
    tree = ast.parse(inspect.getsource(evaluation))
    last = tree.body[-1]
    assert isinstance(last, ast.Assign)
    assert isinstance(last.targets[0], ast.Name)
    assert last.targets[0].id == "__all__"


def test_ast_no_class_def_batch45():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_no_function_def_batch45():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, ast.FunctionDef)
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_no_for_batch45():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, ast.For)


def test_ast_no_while_batch45():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_no_if_batch45():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, ast.If)


def test_ast_no_try_batch45():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, ast.Try)


def test_ast_no_with_batch45():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, (ast.With, ast.AsyncWith))


def test_ast_total_top_level_nodes_batch45():
    """顶层节点：1 docstring + 4 版本赋值 + 1 __all__ 赋值 = 6。"""
    tree = ast.parse(inspect.getsource(evaluation))
    assert len(tree.body) == 6


def test_ast_node_types_in_order_batch45():
    tree = ast.parse(inspect.getsource(evaluation))
    types = [type(n).__name__ for n in tree.body]
    assert types == ["Expr", "Assign", "Assign", "Assign", "Assign", "Assign"]


def test_ast_assign_targets_count_batch45():
    """每个 Assign 都是单 target。"""
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        if isinstance(n, ast.Assign):
            assert len(n.targets) == 1


# ---------- forbidden tokens 第九十七批 ----------

def test_source_no_eval_batch45():
    src = inspect.getsource(evaluation)
    assert "eval(" not in src


def test_source_no_exec_batch45():
    src = inspect.getsource(evaluation)
    assert "exec(" not in src


def test_source_no_compile_batch45():
    src = inspect.getsource(evaluation)
    assert "compile(" not in src


def test_source_no_globals_batch45():
    src = inspect.getsource(evaluation)
    assert "globals(" not in src


def test_source_no_locals_batch45():
    src = inspect.getsource(evaluation)
    assert "locals(" not in src


def test_source_no_os_system_batch45():
    src = inspect.getsource(evaluation)
    assert "os.system(" not in src


def test_source_no_popen_batch45():
    src = inspect.getsource(evaluation)
    assert "popen(" not in src


def test_source_no_yaml_load_batch45():
    src = inspect.getsource(evaluation)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch45():
    src = inspect.getsource(evaluation)
    assert "pickle.load(" not in src


def test_source_no_class_keyword_batch45():
    src = inspect.getsource(evaluation)
    assert "class " not in src


def test_source_no_def_keyword_batch45():
    src = inspect.getsource(evaluation)
    assert "\ndef " not in src
    assert src.startswith('"""')  # 模块以 docstring 开头


def test_source_no_async_keyword_batch45():
    src = inspect.getsource(evaluation)
    assert "async " not in src


def test_source_no_yield_keyword_batch45():
    src = inspect.getsource(evaluation)
    assert "yield" not in src


def test_source_no_lambda_batch45():
    src = inspect.getsource(evaluation)
    assert "lambda" not in src


def test_source_no_walrus_batch45():
    src = inspect.getsource(evaluation)
    assert ":=" not in src


# ---------- 综合 ----------

def test_versions_set_values_batch45():
    s = {EVALUATOR_VERSION, ANNOTATION_VERSION}
    assert s == {"1.1", "1.0"}


def test_versions_tuple_unpack_batch45():
    e, r, a, m = (EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION)
    assert e == "1.1"
    assert r == "1.1"
    assert a == "1.0"
    assert m == "1.0"


def test_versions_format_string_batch45():
    out = f"{EVALUATOR_VERSION}/{REPORT_VERSION}/{ANNOTATION_VERSION}/{MANIFEST_VERSION}"
    assert out == "1.1/1.1/1.0/1.0"


def test_versions_zip_batch45():
    pairs = list(zip([EVALUATOR_VERSION, REPORT_VERSION], [ANNOTATION_VERSION, MANIFEST_VERSION]))
    assert pairs == [("1.1", "1.0"), ("1.1", "1.0")]


def test_versions_sorted_batch45():
    out = sorted([MANIFEST_VERSION, EVALUATOR_VERSION, ANNOTATION_VERSION, REPORT_VERSION])
    assert out == ["1.0", "1.0", "1.1", "1.1"]


def test_versions_count_in_tuple_batch45():
    t = (EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION)
    assert t.count("1.1") == 2
    assert t.count("1.0") == 2


def test_versions_index_in_tuple_batch45():
    t = (EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION)
    assert t.index("1.0") == 2  # 第一个出现的 1.0
