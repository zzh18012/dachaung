"""evaluation/__init__.py 第二轮 edges 测试（Round 603）。

补强 init_edges 未触及的角度。
"""

from __future__ import annotations

import ast
import importlib
import inspect
import json
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


# ---------- 版本常量补强


def test_evaluator_version_no_patch_segment_batch37():
    """格式是 X.Y 而非 X.Y.Z。"""
    assert EVALUATOR_VERSION.count(".") == 1


def test_report_version_no_patch_segment_batch37():
    assert REPORT_VERSION.count(".") == 1


def test_annotation_version_no_patch_segment_batch37():
    assert ANNOTATION_VERSION.count(".") == 1


def test_manifest_version_no_patch_segment_batch37():
    assert MANIFEST_VERSION.count(".") == 1


def test_evaluator_version_only_digits_and_dot_batch37():
    assert all(c.isdigit() or c == "." for c in EVALUATOR_VERSION)


def test_report_version_only_digits_and_dot_batch37():
    assert all(c.isdigit() or c == "." for c in REPORT_VERSION)


def test_annotation_version_only_digits_and_dot_batch37():
    assert all(c.isdigit() or c == "." for c in ANNOTATION_VERSION)


def test_manifest_version_only_digits_and_dot_batch37():
    assert all(c.isdigit() or c == "." for c in MANIFEST_VERSION)


def test_evaluator_version_starts_with_digit_batch37():
    assert EVALUATOR_VERSION[0].isdigit()


def test_report_version_starts_with_digit_batch37():
    assert REPORT_VERSION[0].isdigit()


def test_annotation_version_starts_with_digit_batch37():
    assert ANNOTATION_VERSION[0].isdigit()


def test_manifest_version_starts_with_digit_batch37():
    assert MANIFEST_VERSION[0].isdigit()


def test_evaluator_version_no_spaces_batch37():
    assert " " not in EVALUATOR_VERSION


def test_evaluator_version_no_newlines_batch37():
    assert "\n" not in EVALUATOR_VERSION


def test_evaluator_version_no_leading_zero_batch37():
    """主版本号不以 0 开头（除非版本就是 0.x）。"""
    major = EVALUATOR_VERSION.split(".")[0]
    assert not (major.startswith("0") and len(major) > 1)


# ---------- 与 schema 一致性


def test_evaluator_version_matches_schema_const_batch37():
    """evaluation-report.schema.json 应该有 evaluator_version 字段。"""
    from evaluation.schema import load_schema
    schema = load_schema("evaluation-report.schema.json")
    # provenance 用 $ref → 在 $defs.provenance.properties
    provenance_props = schema.get("$defs", {}).get("provenance", {}).get("properties", {})
    assert "evaluator_version" in provenance_props


def test_report_version_matches_schema_const_batch37():
    """evaluation-report.schema.json 应该有 report_version 字段。"""
    from evaluation.schema import load_schema
    schema = load_schema("evaluation-report.schema.json")
    provenance_props = schema.get("$defs", {}).get("provenance", {}).get("properties", {})
    assert "report_version" in provenance_props


def test_manifest_version_matches_schema_const_batch37():
    """manifest.schema.json 应该有 manifest_version const。"""
    from evaluation.schema import load_schema
    schema = load_schema("manifest.schema.json")
    props = schema.get("properties", {})
    assert "manifest_version" in props


def test_annotation_version_in_schema_batch37():
    """annotation.schema.json 应该有 annotation_version 字段。"""
    from evaluation.schema import load_schema
    schema = load_schema("annotation.schema.json")
    props = schema.get("properties", {})
    assert "annotation_version" in props


# ---------- __all__ 补强


def test_all_no_extra_entries_batch37():
    """__all__ 只包含 4 个版本常量。"""
    expected = {"EVALUATOR_VERSION", "REPORT_VERSION", "ANNOTATION_VERSION", "MANIFEST_VERSION"}
    assert set(evaluation.__all__) == expected


def test_all_no_subpackages_exported_batch37():
    """__all__ 不应该把 evaluation 子模块（cli/manifest/...）export。"""
    forbidden = {"cli", "manifest", "runner", "schema", "report", "metrics", "annotation_metrics"}
    assert set(evaluation.__all__).isdisjoint(forbidden)


def test_all_contains_only_strings_batch37():
    for name in evaluation.__all__:
        assert isinstance(name, str)


# ---------- 模块属性


def test_evaluator_version_attribute_exists_batch37():
    assert hasattr(evaluation, "EVALUATOR_VERSION")


def test_report_version_attribute_exists_batch37():
    assert hasattr(evaluation, "REPORT_VERSION")


def test_annotation_version_attribute_exists_batch37():
    assert hasattr(evaluation, "ANNOTATION_VERSION")


def test_manifest_version_attribute_exists_batch37():
    assert hasattr(evaluation, "MANIFEST_VERSION")


def test_evaluator_version_in_dir_batch37():
    assert "EVALUATOR_VERSION" in dir(evaluation)


def test_report_version_in_dir_batch37():
    assert "REPORT_VERSION" in dir(evaluation)


def test_annotation_version_in_dir_batch37():
    assert "ANNOTATION_VERSION" in dir(evaluation)


def test_manifest_version_in_dir_batch37():
    assert "MANIFEST_VERSION" in dir(evaluation)


# ---------- 模块源码结构


def test_module_source_has_assignments_batch37():
    src = inspect.getsource(evaluation)
    assert 'EVALUATOR_VERSION = "1.1"' in src
    assert 'REPORT_VERSION = "1.1"' in src
    assert 'ANNOTATION_VERSION = "1.0"' in src
    assert 'MANIFEST_VERSION = "1.0"' in src


def test_module_source_has_all_definition_batch37():
    src = inspect.getsource(evaluation)
    assert "__all__" in src


def test_module_source_has_docstring_batch37():
    src = inspect.getsource(evaluation)
    assert '"""' in src


def test_module_source_contains_design_principles_batch37():
    src = inspect.getsource(evaluation)
    assert "设计原则" in src


def test_module_source_contains_version_history_batch37():
    src = inspect.getsource(evaluation)
    assert "版本历史" in src


def test_module_source_contains_v1_0_batch37():
    src = inspect.getsource(evaluation)
    assert "v1.0" in src


def test_module_source_contains_v1_1_batch37():
    src = inspect.getsource(evaluation)
    assert "v1.1" in src


def test_module_source_contains_no_app_dependencies_batch37():
    src = inspect.getsource(evaluation)
    assert "不依赖" in src


def test_module_source_contains_text_preservation_batch37():
    src = inspect.getsource(evaluation)
    assert "text_preservation" in src


def test_module_source_contains_pipeline_immutability_batch37():
    src = inspect.getsource(evaluation)
    assert "不修改 parser" in src or "不修改" in src


def test_module_source_contains_no_fabrication_batch37():
    src = inspect.getsource(evaluation)
    assert "不伪造" in src


def test_module_source_contains_zero_denominator_batch37():
    src = inspect.getsource(evaluation)
    assert "分母为 0" in src or "分母" in src


def test_module_source_contains_not_instrumented_batch37():
    src = inspect.getsource(evaluation)
    assert "not_instrumented" in src


def test_module_source_contains_total_only_batch37():
    src = inspect.getsource(evaluation)
    assert "只记 total" in src or "计时只记" in src


def test_module_source_contains_baseline_incompatibility_batch37():
    src = inspect.getsource(evaluation)
    assert "不可横向比较" in src


# ---------- AST 结构检查


def test_ast_no_class_definitions_batch37():
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert classes == []


def test_ast_no_function_definitions_batch37():
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert funcs == []


def test_ast_no_imports_batch37():
    """模块没有 import 语句。"""
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert imports == []


def test_ast_exactly_four_assignments_batch37():
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    # 4 个 version assignments + 1 个 __all__ assignment = 5
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 5


def test_ast_has_module_docstring_batch37():
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    assert len(tree.body) > 0
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)
    assert isinstance(first.value.value, str)


def test_ast_top_level_only_docstring_assigns_batch37():
    """顶层节点只有 Expr(docstring) + Assign。"""
    src = inspect.getsource(evaluation)
    tree = ast.parse(src)
    for node in tree.body:
        assert isinstance(node, (ast.Expr, ast.Assign))


# ---------- 模块文件


def test_module_file_in_evaluation_dir_batch37():
    assert evaluation.__file__.endswith("__init__.py")


def test_module_file_parent_is_evaluation_batch37():
    p = Path(evaluation.__file__).resolve().parent
    assert p.name == "evaluation"


def test_module_name_is_evaluation_batch37():
    assert evaluation.__name__ == "evaluation"


def test_module_package_is_evaluation_batch37():
    assert evaluation.__package__ == "evaluation"


# ---------- __all__ 顺序补强


def test_all_first_entry_evaluator_batch37():
    assert evaluation.__all__[0] == "EVALUATOR_VERSION"


def test_all_last_entry_manifest_batch37():
    assert evaluation.__all__[-1] == "MANIFEST_VERSION"


def test_all_indices_evaluator_zero_batch37():
    assert evaluation.__all__.index("EVALUATOR_VERSION") == 0


def test_all_indices_report_one_batch37():
    assert evaluation.__all__.index("REPORT_VERSION") == 1


def test_all_indices_annotation_two_batch37():
    assert evaluation.__all__.index("ANNOTATION_VERSION") == 2


def test_all_indices_manifest_three_batch37():
    assert evaluation.__all__.index("MANIFEST_VERSION") == 3


# ---------- 版本组合


def test_versions_pair_evaluator_report_equal_batch37():
    assert EVALUATOR_VERSION == REPORT_VERSION


def test_versions_pair_annotation_manifest_equal_batch37():
    assert ANNOTATION_VERSION == MANIFEST_VERSION


def test_versions_pair_evaluator_annotation_differ_batch37():
    assert EVALUATOR_VERSION != ANNOTATION_VERSION


def test_versions_pair_report_manifest_differ_batch37():
    assert REPORT_VERSION != MANIFEST_VERSION


def test_versions_two_distinct_values_batch37():
    values = {EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION}
    assert len(values) == 2


def test_versions_evaluator_report_higher_than_annotation_manifest_batch37():
    """1.1 > 1.0（major 相同时比 minor）。"""
    def parse(v: str) -> tuple[int, int]:
        a, b = v.split(".")
        return (int(a), int(b))

    assert parse(EVALUATOR_VERSION) > parse(ANNOTATION_VERSION)


# ---------- reload 后保持


def test_reload_preserves_evaluator_version_batch37():
    reloaded = importlib.reload(importlib.import_module("evaluation"))
    assert reloaded.EVALUATOR_VERSION == "1.1"


def test_reload_preserves_report_version_batch37():
    reloaded = importlib.reload(importlib.import_module("evaluation"))
    assert reloaded.REPORT_VERSION == "1.1"


def test_reload_preserves_annotation_version_batch37():
    reloaded = importlib.reload(importlib.import_module("evaluation"))
    assert reloaded.ANNOTATION_VERSION == "1.0"


def test_reload_preserves_manifest_version_batch37():
    reloaded = importlib.reload(importlib.import_module("evaluation"))
    assert reloaded.MANIFEST_VERSION == "1.0"


def test_reload_preserves_all_batch37():
    reloaded = importlib.reload(importlib.import_module("evaluation"))
    assert reloaded.__all__ == [
        "EVALUATOR_VERSION", "REPORT_VERSION", "ANNOTATION_VERSION", "MANIFEST_VERSION"
    ]


# ---------- 与其它模块的一致性


def test_report_uses_evaluator_version_constant_batch37():
    """evaluation.report 应该 import EVALUATOR_VERSION。"""
    from evaluation import report
    src = inspect.getsource(report)
    assert "EVALUATOR_VERSION" in src


def test_report_uses_report_version_constant_batch37():
    from evaluation import report
    src = inspect.getsource(report)
    assert "REPORT_VERSION" in src


def test_runner_uses_report_version_constant_batch37():
    from evaluation import runner
    src = inspect.getsource(runner)
    assert "REPORT_VERSION" in src


def test_manifest_uses_manifest_version_constant_batch37():
    from evaluation import manifest
    src = inspect.getsource(manifest)
    assert "MANIFEST_VERSION" in src


def test_cli_does_not_hardcode_versions_batch37():
    """CLI 不应硬编码版本字符串。"""
    from evaluation import cli
    src = inspect.getsource(cli)
    assert '"1.1"' not in src
    assert '"1.0"' not in src


# ---------- 跨子模块一致


def test_evaluator_version_consistent_across_submodules_batch37():
    """所有 evaluation 子模块看到的 EVALUATOR_VERSION 一致。"""
    from evaluation import report, runner
    assert report.EVALUATOR_VERSION == EVALUATOR_VERSION
    assert runner.REPORT_VERSION == REPORT_VERSION


def test_manifest_version_in_load_manifest_batch37():
    """load_manifest 检查 manifest_version 是否匹配 MANIFEST_VERSION。"""
    from evaluation.manifest import MANIFEST_VERSION as manifest_local
    assert manifest_local == MANIFEST_VERSION


# ---------- docstring 完整性


def test_docstring_starts_with_chinese_batch37():
    """docstring 以中文开头。"""
    assert evaluation.__doc__ is not None
    assert evaluation.__doc__.lstrip().startswith("评")


def test_docstring_contains_section_headers_batch37():
    """docstring 含 '设计原则' 和 '版本历史' 章节标题。"""
    doc = evaluation.__doc__ or ""
    assert "设计原则" in doc
    assert "版本历史" in doc


def test_docstring_lists_principles_batch37():
    """docstring 列出至少 4 条原则。"""
    doc = evaluation.__doc__ or ""
    # 至少 4 行以 "- " 开头
    lines = [l.strip() for l in doc.split("\n") if l.strip().startswith("-")]
    assert len(lines) >= 4


def test_docstring_explains_v1_0_to_v1_1_change_batch37():
    """docstring 解释 v1.0 → v1.1 的语义变化。"""
    doc = evaluation.__doc__ or ""
    assert "v1.0" in doc
    assert "v1.1" in doc


def test_docstring_warns_about_baseline_incompatibility_batch37():
    """docstring 警告 v1.0 baseline 与 v1.1 不可比较。"""
    doc = evaluation.__doc__ or ""
    assert "不可横向比较" in doc or "不可比较" in doc


# ---------- JSON 序列化


def test_versions_json_serializable_batch37():
    """版本常量能 JSON 序列化。"""
    out = json.dumps({
        "evaluator": EVALUATOR_VERSION,
        "report": REPORT_VERSION,
        "annotation": ANNOTATION_VERSION,
        "manifest": MANIFEST_VERSION,
    })
    assert isinstance(out, str)


def test_versions_round_trip_batch37():
    """JSON 序列化 → 反序列化 → 与原值一致。"""
    data = {
        "evaluator": EVALUATOR_VERSION,
        "report": REPORT_VERSION,
    }
    s = json.dumps(data)
    parsed = json.loads(s)
    assert parsed["evaluator"] == EVALUATOR_VERSION


# ---------- 综合


def test_module_source_forbidden_tokens_batch37():
    """__init__.py 不应有任何禁用 token。"""
    forbidden = ["eval(", "exec(", "pickle", "yaml", "__import__", "breakpoint(",
                 "shutil", "requests", "subprocess", "os.system", "pty.",
                 "ctypes", "urllib", "socket"]
    src = inspect.getsource(evaluation)
    for token in forbidden:
        assert token not in src


def test_module_has_dunder_all_batch37():
    assert hasattr(evaluation, "__all__")


def test_module_all_is_list_batch37():
    assert isinstance(evaluation.__all__, list)


def test_module_all_len_four_batch37():
    assert len(evaluation.__all__) == 4
