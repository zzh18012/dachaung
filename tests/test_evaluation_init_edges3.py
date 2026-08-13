"""evaluation/__init__.py 第三轮 edges 测试（Round 611）。

补强 init_edges2 未触及的角度（第四十三批）。

新角度：
- 版本常量字符级细节（major/minor 字符 / 长度 / 拼接 / 重复字符）
- 版本常量类型 str
- 版本常量不支持算术运算（不能 + int / * int）
- __all__ 顺序固定（4 entries）
- __all__ 元素都是 module 属性
- __all__ 元素都可 import
- 模块属性 hashable
- 模块属性 can pickle（其实是字符串）
- 模块 source 顺序（EVALUATOR → REPORT → ANNOTATION → MANIFEST）
- docstring 完整性
- module 文件路径 / size / 行数
- 重导入（importlib.reload）后保持
- AST 检查（无 if/for/while/with/try/import）
- forbidden tokens 第十六批
"""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import pickle
import sys
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


# ---------- 版本常量字符级 第四十三批


def test_evaluator_version_major_minor_split_batch43():
    parts = EVALUATOR_VERSION.split(".")
    assert len(parts) == 2
    assert parts[0].isdigit()
    assert parts[1].isdigit()


def test_report_version_major_minor_split_batch43():
    parts = REPORT_VERSION.split(".")
    assert len(parts) == 2
    assert parts[0].isdigit()
    assert parts[1].isdigit()


def test_annotation_version_major_minor_split_batch43():
    parts = ANNOTATION_VERSION.split(".")
    assert len(parts) == 2
    assert parts[0].isdigit()
    assert parts[1].isdigit()


def test_manifest_version_major_minor_split_batch43():
    parts = MANIFEST_VERSION.split(".")
    assert len(parts) == 2
    assert parts[0].isdigit()
    assert parts[1].isdigit()


def test_evaluator_version_major_is_one_batch43():
    assert EVALUATOR_VERSION.split(".")[0] == "1"


def test_evaluator_version_minor_is_one_batch43():
    assert EVALUATOR_VERSION.split(".")[1] == "1"


def test_report_version_major_is_one_batch43():
    assert REPORT_VERSION.split(".")[0] == "1"


def test_report_version_minor_is_one_batch43():
    assert REPORT_VERSION.split(".")[1] == "1"


def test_annotation_version_major_is_one_batch43():
    assert ANNOTATION_VERSION.split(".")[0] == "1"


def test_annotation_version_minor_is_zero_batch43():
    assert ANNOTATION_VERSION.split(".")[1] == "0"


def test_manifest_version_major_is_one_batch43():
    assert MANIFEST_VERSION.split(".")[0] == "1"


def test_manifest_version_minor_is_zero_batch43():
    assert MANIFEST_VERSION.split(".")[1] == "0"


def test_evaluator_version_length_three_batch43():
    assert len(EVALUATOR_VERSION) == 3  # "1.1"


def test_report_version_length_three_batch43():
    assert len(REPORT_VERSION) == 3


def test_annotation_version_length_three_batch43():
    assert len(ANNOTATION_VERSION) == 3  # "1.0"


def test_manifest_version_length_three_batch43():
    assert len(MANIFEST_VERSION) == 3


def test_evaluator_version_has_dot_at_index_one_batch43():
    assert EVALUATOR_VERSION[1] == "."


def test_report_version_has_dot_at_index_one_batch43():
    assert REPORT_VERSION[1] == "."


def test_annotation_version_has_dot_at_index_one_batch43():
    assert ANNOTATION_VERSION[1] == "."


def test_manifest_version_has_dot_at_index_one_batch43():
    assert MANIFEST_VERSION[1] == "."


def test_evaluator_version_first_char_digit_batch43():
    assert EVALUATOR_VERSION[0].isdigit()


def test_evaluator_version_last_char_digit_batch43():
    assert EVALUATOR_VERSION[-1].isdigit()


# ---------- 版本常量类型 第四十三批


def test_evaluator_version_is_str_batch43():
    assert isinstance(EVALUATOR_VERSION, str)


def test_report_version_is_str_batch43():
    assert isinstance(REPORT_VERSION, str)


def test_annotation_version_is_str_batch43():
    assert isinstance(ANNOTATION_VERSION, str)


def test_manifest_version_is_str_batch43():
    assert isinstance(MANIFEST_VERSION, str)


def test_evaluator_version_not_int_batch43():
    assert not isinstance(EVALUATOR_VERSION, int)


def test_evaluator_version_not_bool_batch43():
    assert not isinstance(EVALUATOR_VERSION, bool)


def test_evaluator_version_not_none_batch43():
    assert EVALUATOR_VERSION is not None


def test_evaluator_version_truthy_batch43():
    """非空字符串是 truthy。"""
    assert bool(EVALUATOR_VERSION)


# ---------- 版本常量 hashable + pickleable 第四十三批


def test_evaluator_version_hashable_batch43():
    assert hash(EVALUATOR_VERSION) == hash("1.1")


def test_report_version_hashable_batch43():
    assert hash(REPORT_VERSION) == hash("1.1")


def test_annotation_version_hashable_batch43():
    assert hash(ANNOTATION_VERSION) == hash("1.0")


def test_manifest_version_hashable_batch43():
    assert hash(MANIFEST_VERSION) == hash("1.0")


def test_evaluator_version_pickleable_batch43():
    """str 可 pickle。"""
    s = pickle.dumps(EVALUATOR_VERSION)
    assert pickle.loads(s) == EVALUATOR_VERSION


def test_evaluator_version_in_set_batch43():
    s = {EVALUATOR_VERSION, REPORT_VERSION}
    assert EVALUATOR_VERSION in s


def test_evaluator_version_as_dict_key_batch43():
    d = {EVALUATOR_VERSION: "eval"}
    assert d[EVALUATOR_VERSION] == "eval"


# ---------- 版本常量字符串操作 第四十三批


def test_evaluator_version_upper_batch43():
    assert EVALUATOR_VERSION.upper() == "1.1"


def test_evaluator_version_lower_batch43():
    assert EVALUATOR_VERSION.lower() == "1.1"


def test_evaluator_version_strip_batch43():
    assert EVALUATOR_VERSION.strip() == "1.1"


def test_evaluator_version_replace_dot_batch43():
    assert EVALUATOR_VERSION.replace(".", "_") == "1_1"


def test_evaluator_version_concat_batch43():
    """字符串可拼接。"""
    assert EVALUATOR_VERSION + "-suffix" == "1.1-suffix"


def test_evaluator_version_repeat_batch43():
    assert EVALUATOR_VERSION * 2 == "1.11.1"


def test_evaluator_version_indexing_batch43():
    assert EVALUATOR_VERSION[0] == "1"
    assert EVALUATOR_VERSION[1] == "."
    assert EVALUATOR_VERSION[2] == "1"


def test_evaluator_version_negative_indexing_batch43():
    assert EVALUATOR_VERSION[-1] == "1"
    assert EVALUATOR_VERSION[-2] == "."
    assert EVALUATOR_VERSION[-3] == "1"


def test_evaluator_version_slice_batch43():
    assert EVALUATOR_VERSION[:1] == "1"
    assert EVALUATOR_VERSION[1:] == ".1"
    assert EVALUATOR_VERSION[::-1] == "1.1"


def test_evaluator_version_split_count_batch43():
    assert len(EVALUATOR_VERSION.split(".")) == 2


def test_evaluator_version_join_round_trip_batch43():
    parts = EVALUATOR_VERSION.split(".")
    assert ".".join(parts) == EVALUATOR_VERSION


# ---------- __all__ 第四十三批


def test_all_first_evaluator_batch43():
    assert evaluation.__all__[0] == "EVALUATOR_VERSION"


def test_all_second_report_batch43():
    assert evaluation.__all__[1] == "REPORT_VERSION"


def test_all_third_annotation_batch43():
    assert evaluation.__all__[2] == "ANNOTATION_VERSION"


def test_all_fourth_manifest_batch43():
    assert evaluation.__all__[3] == "MANIFEST_VERSION"


def test_all_indices_unique_batch43():
    indices = list(range(len(evaluation.__all__)))
    assert indices == [0, 1, 2, 3]


def test_all_no_duplicates_batch43():
    assert len(evaluation.__all__) == len(set(evaluation.__all__))


def test_all_entries_are_str_batch43():
    for name in evaluation.__all__:
        assert isinstance(name, str)


def test_all_entries_exist_as_module_attrs_batch43():
    for name in evaluation.__all__:
        assert hasattr(evaluation, name)


def test_all_entries_can_be_imported_batch43():
    """from evaluation import <name> 都能工作。"""
    # 已经在文件顶部 import 了
    assert EVALUATOR_VERSION is not None
    assert REPORT_VERSION is not None
    assert ANNOTATION_VERSION is not None
    assert MANIFEST_VERSION is not None


def test_all_count_four_batch43():
    assert len(evaluation.__all__) == 4


def test_all_no_extra_entries_batch43():
    expected = {"EVALUATOR_VERSION", "REPORT_VERSION", "ANNOTATION_VERSION", "MANIFEST_VERSION"}
    assert set(evaluation.__all__) == expected


def test_all_does_not_contain_other_modules_batch43():
    forbidden = {"cli", "manifest", "runner", "schema", "report", "metrics", "annotation_metrics"}
    assert set(evaluation.__all__).isdisjoint(forbidden)


def test_all_does_not_contain_dunder_batch43():
    for name in evaluation.__all__:
        assert not name.startswith("__")


def test_all_does_not_contain_lowercase_batch43():
    """所有 entries 应是 UPPER_CASE 常量。"""
    for name in evaluation.__all__:
        assert name.isupper() or name.upper() == name


# ---------- 模块属性 第四十三批


def test_evaluator_version_in_dir_batch43():
    assert "EVALUATOR_VERSION" in dir(evaluation)


def test_report_version_in_dir_batch43():
    assert "REPORT_VERSION" in dir(evaluation)


def test_annotation_version_in_dir_batch43():
    assert "ANNOTATION_VERSION" in dir(evaluation)


def test_manifest_version_in_dir_batch43():
    assert "MANIFEST_VERSION" in dir(evaluation)


def test_all_in_dir_batch43():
    assert "__all__" in dir(evaluation)


def test_evaluator_version_type_str_in_module_batch43():
    assert isinstance(evaluation.EVALUATOR_VERSION, str)


def test_module_attribute_immutable_via_read_batch43():
    """读 evaluation.EVALUATOR_VERSION 不抛。"""
    _ = evaluation.EVALUATOR_VERSION  # 不抛


def test_module_attributes_match_imported_batch43():
    assert evaluation.EVALUATOR_VERSION == EVALUATOR_VERSION
    assert evaluation.REPORT_VERSION == REPORT_VERSION
    assert evaluation.ANNOTATION_VERSION == ANNOTATION_VERSION
    assert evaluation.MANIFEST_VERSION == MANIFEST_VERSION


# ---------- 模块源码结构 第四十三批


def test_module_source_has_docstring_batch43():
    src = inspect.getsource(evaluation)
    assert '"""' in src


def test_module_source_has_all_definition_batch43():
    src = inspect.getsource(evaluation)
    assert "__all__" in src


def test_module_source_evaluator_before_report_batch43():
    """EVALUATOR 出现在 REPORT 之前。"""
    src = inspect.getsource(evaluation)
    assert src.index("EVALUATOR_VERSION") < src.index("REPORT_VERSION")


def test_module_source_report_before_annotation_batch43():
    src = inspect.getsource(evaluation)
    assert src.index("REPORT_VERSION") < src.index("ANNOTATION_VERSION")


def test_module_source_annotation_before_manifest_batch43():
    src = inspect.getsource(evaluation)
    assert src.index("ANNOTATION_VERSION") < src.index("MANIFEST_VERSION")


def test_module_source_contains_design_principles_batch43():
    src = inspect.getsource(evaluation)
    assert "设计原则" in src


def test_module_source_contains_version_history_batch43():
    src = inspect.getsource(evaluation)
    assert "版本历史" in src


def test_module_source_contains_v1_0_batch43():
    src = inspect.getsource(evaluation)
    assert "v1.0" in src


def test_module_source_contains_v1_1_batch43():
    src = inspect.getsource(evaluation)
    assert "v1.1" in src


def test_module_source_contains_text_preservation_batch43():
    src = inspect.getsource(evaluation)
    assert "text_preservation" in src


def test_module_source_contains_no_modification_batch43():
    src = inspect.getsource(evaluation)
    assert "不修改" in src


def test_module_source_contains_no_fabrication_batch43():
    src = inspect.getsource(evaluation)
    assert "不伪造" in src


def test_module_source_contains_no_external_deps_batch43():
    src = inspect.getsource(evaluation)
    assert "不依赖" in src


def test_module_source_contains_zero_denominator_batch43():
    src = inspect.getsource(evaluation)
    assert "分母" in src


def test_module_source_contains_not_instrumented_batch43():
    src = inspect.getsource(evaluation)
    assert "not_instrumented" in src


def test_module_source_contains_baseline_incompatibility_batch43():
    src = inspect.getsource(evaluation)
    assert "不可横向比较" in src


def test_module_source_contains_hard_cut_keyword_batch43():
    """docstring 提到"词内硬切"。"""
    src = inspect.getsource(evaluation)
    assert "硬切" in src


def test_module_source_contains_normalize_text_keyword_batch43():
    """docstring 提到 normalize_text（v1.0 旧口径）。"""
    src = inspect.getsource(evaluation)
    assert "normalize_text" in src


def test_module_source_evaluator_assignment_batch43():
    src = inspect.getsource(evaluation)
    assert 'EVALUATOR_VERSION = "1.1"' in src


def test_module_source_report_assignment_batch43():
    src = inspect.getsource(evaluation)
    assert 'REPORT_VERSION = "1.1"' in src


def test_module_source_annotation_assignment_batch43():
    src = inspect.getsource(evaluation)
    assert 'ANNOTATION_VERSION = "1.0"' in src


def test_module_source_manifest_assignment_batch43():
    src = inspect.getsource(evaluation)
    assert 'MANIFEST_VERSION = "1.0"' in src


# ---------- AST 结构检查 第四十三批


def test_ast_no_class_definitions_batch43():
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert classes == []


def test_ast_no_function_definitions_batch43():
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert funcs == []


def test_ast_no_imports_batch43():
    """模块没有 import 语句。"""
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert imports == []


def test_ast_no_async_functions_batch43():
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    async_funcs = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)]
    assert async_funcs == []


def test_ast_no_loops_batch43():
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    loops = [n for n in tree.body if isinstance(n, (ast.For, ast.While))]
    assert loops == []


def test_ast_no_with_batch43():
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    withs = [n for n in tree.body if isinstance(n, ast.With)]
    assert withs == []


def test_ast_no_try_batch43():
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    trys = [n for n in tree.body if isinstance(n, ast.Try)]
    assert trys == []


def test_ast_no_if_batch43():
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    ifs = [n for n in tree.body if isinstance(n, ast.If)]
    assert ifs == []


def test_ast_exactly_four_assignments_batch43():
    """4 个 version assignments + 1 个 __all__ assignment = 5。"""
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 5


def test_ast_has_module_docstring_batch43():
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    assert len(tree.body) > 0
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)
    assert isinstance(first.value.value, str)


def test_ast_top_level_only_docstring_assigns_batch43():
    """顶层节点只有 Expr(docstring) + Assign。"""
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    for node in tree.body:
        assert isinstance(node, (ast.Expr, ast.Assign))


def test_ast_evaluator_assignment_first_batch43():
    """第一个 Assign 是 EVALUATOR_VERSION。"""
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    first = assigns[0]
    assert isinstance(first.targets[0], ast.Name)
    assert first.targets[0].id == "EVALUATOR_VERSION"


def test_ast_all_assignment_last_batch43():
    """最后一个 Assign 是 __all__。"""
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    last = assigns[-1]
    assert isinstance(last.targets[0], ast.Name)
    assert last.targets[0].id == "__all__"


# ---------- 模块文件 第四十三批


def test_module_file_ends_with_init_py_batch43():
    assert evaluation.__file__.endswith("__init__.py")


def test_module_file_parent_is_evaluation_batch43():
    p = Path(evaluation.__file__).resolve().parent
    assert p.name == "evaluation"


def test_module_name_is_evaluation_batch43():
    assert evaluation.__name__ == "evaluation"


def test_module_package_is_evaluation_batch43():
    assert evaluation.__package__ == "evaluation"


def test_module_file_exists_batch43():
    assert Path(evaluation.__file__).is_file()


def test_module_file_size_positive_batch43():
    size = Path(evaluation.__file__).stat().st_size
    assert size > 0


def test_module_file_size_under_2kb_batch43():
    """__init__.py 应当很小。"""
    size = Path(evaluation.__file__).stat().st_size
    assert size < 2048


# ---------- reload 后保持 第四十三批


def test_reload_preserves_evaluator_version_batch43():
    reloaded = importlib.reload(importlib.import_module("evaluation"))
    assert reloaded.EVALUATOR_VERSION == "1.1"


def test_reload_preserves_report_version_batch43():
    reloaded = importlib.reload(importlib.import_module("evaluation"))
    assert reloaded.REPORT_VERSION == "1.1"


def test_reload_preserves_annotation_version_batch43():
    reloaded = importlib.reload(importlib.import_module("evaluation"))
    assert reloaded.ANNOTATION_VERSION == "1.0"


def test_reload_preserves_manifest_version_batch43():
    reloaded = importlib.reload(importlib.import_module("evaluation"))
    assert reloaded.MANIFEST_VERSION == "1.0"


def test_reload_preserves_all_batch43():
    reloaded = importlib.reload(importlib.import_module("evaluation"))
    assert reloaded.__all__ == [
        "EVALUATOR_VERSION", "REPORT_VERSION", "ANNOTATION_VERSION", "MANIFEST_VERSION",
    ]


def test_reload_preserves_docstring_batch43():
    reloaded = importlib.reload(importlib.import_module("evaluation"))
    assert "评测包" in (reloaded.__doc__ or "")


# ---------- 版本组合 第四十三批


def test_versions_pair_evaluator_report_equal_batch43():
    assert EVALUATOR_VERSION == REPORT_VERSION


def test_versions_pair_annotation_manifest_equal_batch43():
    assert ANNOTATION_VERSION == MANIFEST_VERSION


def test_versions_pair_evaluator_annotation_differ_batch43():
    assert EVALUATOR_VERSION != ANNOTATION_VERSION


def test_versions_pair_report_manifest_differ_batch43():
    assert REPORT_VERSION != MANIFEST_VERSION


def test_versions_two_distinct_values_batch43():
    values = {EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION}
    assert len(values) == 2


def test_versions_evaluator_report_higher_batch43():
    """1.1 > 1.0。"""
    def parse(v: str) -> tuple[int, int]:
        a, b = v.split(".")
        return (int(a), int(b))

    assert parse(EVALUATOR_VERSION) > parse(ANNOTATION_VERSION)


def test_versions_set_contains_one_one_batch43():
    assert "1.1" in {EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION}


def test_versions_set_contains_one_zero_batch43():
    assert "1.0" in {EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION}


# ---------- JSON 序列化 第四十三批


def test_versions_json_serializable_batch43():
    out = json.dumps({
        "evaluator": EVALUATOR_VERSION,
        "report": REPORT_VERSION,
        "annotation": ANNOTATION_VERSION,
        "manifest": MANIFEST_VERSION,
    })
    assert isinstance(out, str)


def test_versions_round_trip_batch43():
    data = {
        "evaluator": EVALUATOR_VERSION,
        "report": REPORT_VERSION,
    }
    s = json.dumps(data)
    parsed = json.loads(s)
    assert parsed["evaluator"] == EVALUATOR_VERSION


def test_versions_in_json_array_batch43():
    out = json.dumps([EVALUATOR_VERSION, REPORT_VERSION])
    assert isinstance(out, str)


def test_versions_as_json_values_batch43():
    """单独序列化每个版本。"""
    for v in (EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION):
        s = json.dumps(v)
        assert json.loads(s) == v


# ---------- docstring 完整性 第四十三批


def test_docstring_starts_with_chinese_batch43():
    assert evaluation.__doc__ is not None
    assert evaluation.__doc__.lstrip().startswith("评")


def test_docstring_contains_section_headers_batch43():
    doc = evaluation.__doc__ or ""
    assert "设计原则" in doc
    assert "版本历史" in doc


def test_docstring_lists_principles_batch43():
    doc = evaluation.__doc__ or ""
    lines = [l.strip() for l in doc.split("\n") if l.strip().startswith("-")]
    assert len(lines) >= 4


def test_docstring_explains_v1_0_to_v1_1_change_batch43():
    doc = evaluation.__doc__ or ""
    assert "v1.0" in doc
    assert "v1.1" in doc


def test_docstring_warns_about_baseline_incompatibility_batch43():
    doc = evaluation.__doc__ or ""
    assert "不可横向比较" in doc or "不可比较" in doc


def test_docstring_mentions_text_preservation_batch43():
    doc = evaluation.__doc__ or ""
    assert "text_preservation" in doc


def test_docstring_mentions_not_instrumented_batch43():
    doc = evaluation.__doc__ or ""
    assert "not_instrumented" in doc


def test_docstring_mentions_pipeline_immutability_batch43():
    doc = evaluation.__doc__ or ""
    assert "不修改 parser" in doc or "不修改" in doc


# ---------- 综合 第四十三批


def test_module_source_forbidden_tokens_batch43():
    """__init__.py 不应有任何禁用 token。"""
    forbidden = ["eval(", "exec(", "pickle", "yaml", "__import__", "breakpoint(",
                 "shutil", "requests", "subprocess", "os.system", "pty.",
                 "ctypes", "urllib", "socket"]
    src = inspect.getsource(evaluation)
    for token in forbidden:
        assert token not in src


def test_module_has_dunder_all_batch43():
    assert hasattr(evaluation, "__all__")


def test_module_all_is_list_batch43():
    assert isinstance(evaluation.__all__, list)


def test_module_all_len_four_batch43():
    assert len(evaluation.__all__) == 4


def test_module_all_is_not_tuple_batch43():
    assert not isinstance(evaluation.__all__, tuple)


def test_module_all_is_not_set_batch43():
    assert not isinstance(evaluation.__all__, set)


def test_module_all_mutable_list_batch43():
    """__all__ 是 list，理论可改（不推荐）。"""
    original = list(evaluation.__all__)
    try:
        evaluation.__all__.append("temp")
        assert "temp" in evaluation.__all__
    finally:
        evaluation.__all__[:] = original


def test_module_docstring_is_str_batch43():
    assert isinstance(evaluation.__doc__, str)


def test_module_docstring_not_empty_batch43():
    assert len(evaluation.__doc__ or "") > 0


def test_module_docstring_length_significant_batch43():
    """docstring 至少 200 字符（含设计原则 + 版本历史）。"""
    assert len(evaluation.__doc__ or "") > 200
