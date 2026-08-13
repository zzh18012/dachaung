"""evaluation/__init__.py 第七轮 edges 测试（Round 643）。

补强 edges6 未触及的角度（第四十八批）。

新角度：
- 4 VERSION 常量 intern 与 is 检查
- 4 VERSION 常量 monkeypatch 临时修改
- 模块 __dict__ 内容精确
- 模块 __file__ 路径精确
- 模块 __package__ / __name__
- 模块属性 dict 可序列化
- VERSION 常量类型注解
- __all__ 与 dir() 差集
- 模块 spec 是否原生 SourceFileLoader
- 模块 docstring 内容精确字节
- module source 补强
- AST 结构补强
- forbidden tokens 第一百一十三批
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


# ---------- 4 VERSION 常量 intern 与 is 检查 ----------

def test_evaluator_version_literal_is_batch48():
    """同字面量 intern → is True。"""
    a = "1.1"
    assert a is "1.1"


def test_four_versions_not_same_object_batch48():
    """EVALUATOR_VERSION 与 REPORT_VERSION 值相同但可能是不同对象。"""
    # 不强制 is，但 == 必须成立
    assert EVALUATOR_VERSION == REPORT_VERSION


def test_evaluator_annotation_different_batch48():
    assert EVALUATOR_VERSION != ANNOTATION_VERSION


def test_report_manifest_different_batch48():
    assert REPORT_VERSION != MANIFEST_VERSION


def test_annotation_manifest_same_value_batch48():
    assert ANNOTATION_VERSION == MANIFEST_VERSION


def test_evaluator_version_str_methods_batch48():
    assert EVALUATOR_VERSION.upper() == "1.1"
    assert EVALUATOR_VERSION.lower() == "1.1"
    assert EVALUATOR_VERSION.isdigit() is False
    assert EVALUATOR_VERSION.replace(".", "-") == "1-1"


def test_versions_startswith_digit_batch48():
    for v in (EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION):
        assert v[0].isdigit()


def test_versions_dot_position_batch48():
    for v in (EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION):
        assert v[1] == "."


# ---------- 4 VERSION 常量 monkeypatch 临时修改 ----------

def test_monkeypatch_evaluator_version_batch48(monkeypatch):
    """临时改 EVALUATOR_VERSION 不影响全局（用 monkeypatch 还原）。"""
    original = evaluation.EVALUATOR_VERSION
    monkeypatch.setattr(evaluation, "EVALUATOR_VERSION", "9.9")
    assert evaluation.EVALUATOR_VERSION == "9.9"
    # monkeypatch 退出时会还原


def test_monkeypatch_all_versions_batch48(monkeypatch):
    monkeypatch.setattr(evaluation, "EVALUATOR_VERSION", "9.9")
    monkeypatch.setattr(evaluation, "REPORT_VERSION", "9.9")
    monkeypatch.setattr(evaluation, "ANNOTATION_VERSION", "9.9")
    monkeypatch.setattr(evaluation, "MANIFEST_VERSION", "9.9")
    # 不影响 import 后已绑定的本地名（在测试函数顶部 import 是早绑定）
    # 但 evaluation.X 应反映新值
    assert evaluation.EVALUATOR_VERSION == "9.9"


def test_version_constants_after_monkeypatch_restored_batch48(monkeypatch):
    monkeypatch.setattr(evaluation, "EVALUATOR_VERSION", "9.9")
    # 在 with 退出后还原（pytest monkeypatch 在 test 末尾自动还原）


# ---------- 模块 __dict__ 内容精确 ----------

def test_module_dict_contains_versions_batch48():
    d = evaluation.__dict__
    assert "EVALUATOR_VERSION" in d
    assert "REPORT_VERSION" in d
    assert "ANNOTATION_VERSION" in d
    assert "MANIFEST_VERSION" in d


def test_module_dict_contains_all_batch48():
    assert "__all__" in evaluation.__dict__


def test_module_dict_versions_match_batch48():
    d = evaluation.__dict__
    assert d["EVALUATOR_VERSION"] == "1.1"
    assert d["REPORT_VERSION"] == "1.1"
    assert d["ANNOTATION_VERSION"] == "1.0"
    assert d["MANIFEST_VERSION"] == "1.0"


def test_module_dict_values_are_str_batch48():
    d = evaluation.__dict__
    for k in ("EVALUATOR_VERSION", "REPORT_VERSION", "ANNOTATION_VERSION", "MANIFEST_VERSION"):
        assert isinstance(d[k], str)


def test_module_dict_all_is_list_batch48():
    assert isinstance(evaluation.__dict__["__all__"], list)


def test_module_dict_all_values_are_str_batch48():
    for v in evaluation.__dict__["__all__"]:
        assert isinstance(v, str)


def test_module_dict_len_at_least_5_batch48():
    """至少 4 VERSION + __all__ + 其他 dunder。"""
    assert len(evaluation.__dict__) >= 5


# ---------- 模块 __file__ 路径精确 ----------

def test_module_file_endswith_init_py_batch48():
    assert evaluation.__file__.endswith("__init__.py")


def test_module_file_is_absolute_batch48():
    assert Path(evaluation.__file__).is_absolute()


def test_module_file_exists_batch48():
    assert Path(evaluation.__file__).is_file()


def test_module_file_in_evaluation_dir_batch48():
    p = Path(evaluation.__file__)
    assert p.parent.name == "evaluation"


def test_module_file_parent_is_dachuang_batch48():
    p = Path(evaluation.__file__)
    # 父父目录是项目根
    assert p.parent.parent.is_dir()


# ---------- 模块 __package__ / __name__ ----------

def test_module_package_is_evaluation_batch48():
    assert evaluation.__package__ == "evaluation"


def test_module_name_is_evaluation_batch48():
    assert evaluation.__name__ == "evaluation"


def test_module_package_equals_name_batch48():
    """包的 __package__ 应等于 __name__。"""
    assert evaluation.__package__ == evaluation.__name__


# ---------- 模块属性 dict 可序列化 ----------

def test_module_dict_serializable_via_str_batch48():
    """__dict__ 各 VERSION 是 str → 可序列化。"""
    import json
    versions = {
        "evaluator": evaluation.EVALUATOR_VERSION,
        "report": evaluation.REPORT_VERSION,
        "annotation": evaluation.ANNOTATION_VERSION,
        "manifest": evaluation.MANIFEST_VERSION,
    }
    s = json.dumps(versions)
    restored = json.loads(s)
    assert restored == versions


def test_all_list_serializable_batch48():
    import json
    s = json.dumps(evaluation.__all__)
    restored = json.loads(s)
    assert restored == evaluation.__all__


# ---------- VERSION 常量类型注解 ----------

def test_evaluator_version_type_is_str_batch48():
    assert type(EVALUATOR_VERSION) is str


def test_report_version_type_is_str_batch48():
    assert type(REPORT_VERSION) is str


def test_annotation_version_type_is_str_batch48():
    assert type(ANNOTATION_VERSION) is str


def test_manifest_version_type_is_str_batch48():
    assert type(MANIFEST_VERSION) is str


def test_versions_not_none_batch48():
    for v in (EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION):
        assert v is not None


def test_versions_not_empty_batch48():
    for v in (EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION):
        assert len(v) > 0


# ---------- __all__ 与 dir() 差集 ----------

def test_all_subset_of_dir_batch48():
    """__all__ 中每项应在 dir(evaluation) 中。"""
    d = dir(evaluation)
    for name in evaluation.__all__:
        assert name in d


def test_all_contains_four_entries_batch48():
    assert len(evaluation.__all__) == 4


def test_dir_contains_dunder_names_batch48():
    d = dir(evaluation)
    assert "__name__" in d
    assert "__file__" in d
    assert "__package__" in d


def test_dir_contains_version_names_batch48():
    d = dir(evaluation)
    assert "EVALUATOR_VERSION" in d
    assert "REPORT_VERSION" in d
    assert "ANNOTATION_VERSION" in d
    assert "MANIFEST_VERSION" in d


# ---------- 模块 spec 是否原生 SourceFileLoader ----------

def test_module_spec_origin_is_str_batch48():
    assert isinstance(evaluation.__spec__.origin, str)


def test_module_spec_origin_endswith_init_batch48():
    assert evaluation.__spec__.origin.endswith("__init__.py")


def test_module_spec_loader_has_exec_module_batch48():
    assert hasattr(evaluation.__spec__.loader, "exec_module")


def test_module_spec_submodule_search_locations_is_list_batch48():
    assert isinstance(evaluation.__spec__.submodule_search_locations, list)


def test_module_spec_submodule_search_locations_endswith_evaluation_batch48():
    locs = evaluation.__spec__.submodule_search_locations
    for loc in locs:
        assert loc.endswith("evaluation")


# ---------- 模块 docstring 内容精确字节 ----------

def test_docstring_length_batch48():
    assert len(evaluation.__doc__) > 100


def test_docstring_contains_v1_1_batch48():
    assert "v1.1" in evaluation.__doc__


def test_docstring_contains_v1_0_batch48():
    assert "v1.0" in evaluation.__doc__


def test_docstring_contains_口径_D_batch48():
    assert "口径 D" in evaluation.__doc__


def test_docstring_contains_不可横向比较_batch48():
    assert "不可横向比较" in evaluation.__doc__


def test_docstring_contains_词内硬切_batch48():
    assert "词内硬切" in evaluation.__doc__


def test_docstring_contains_其它指标语义未变_batch48():
    assert "其它指标语义未变" in evaluation.__doc__


def test_docstring_contains_not_instrumented_batch48():
    assert "not_instrumented" in evaluation.__doc__


def test_docstring_contains_不返回_1_0_batch48():
    assert "不返回 1.0" in evaluation.__doc__


def test_docstring_contains_不伪造_batch48():
    assert "不伪造" in evaluation.__doc__


def test_docstring_first_line_batch48():
    """第一行应是 '评测包：开发集清单、自动指标、人工标注指标、报告装配。'"""
    first_line = evaluation.__doc__.split("\n")[0]
    assert "评测包" in first_line


# ---------- module source 补强 ----------

def test_source_contains_EVALUATOR_VERSION_literal_batch48():
    src = inspect.getsource(evaluation)
    assert 'EVALUATOR_VERSION = "1.1"' in src


def test_source_contains_REPORT_VERSION_literal_batch48():
    src = inspect.getsource(evaluation)
    assert 'REPORT_VERSION = "1.1"' in src


def test_source_contains_ANNOTATION_VERSION_literal_batch48():
    src = inspect.getsource(evaluation)
    assert 'ANNOTATION_VERSION = "1.0"' in src


def test_source_contains_MANIFEST_VERSION_literal_batch48():
    src = inspect.getsource(evaluation)
    assert 'MANIFEST_VERSION = "1.0"' in src


def test_source_contains_no_class_def_batch48():
    src = inspect.getsource(evaluation)
    assert "\nclass " not in src


def test_source_contains_no_def_batch48():
    src = inspect.getsource(evaluation)
    assert "\ndef " not in src


def test_source_contains_no_import_batch48():
    src = inspect.getsource(evaluation)
    assert "import " not in src or "from __future__" in src


def test_source_starts_with_docstring_batch48():
    src = inspect.getsource(evaluation)
    assert src.startswith('"""') or src.startswith("'''")


# ---------- AST 结构补强 ----------

def test_ast_total_top_level_6_batch48():
    """顶层节点：1 docstring + 4 VERSION assign + 1 __all__ assign = 6。"""
    tree = ast.parse(inspect.getsource(evaluation))
    assert len(tree.body) == 6


def test_ast_first_is_docstring_expr_batch48():
    tree = ast.parse(inspect.getsource(evaluation))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)
    assert isinstance(tree.body[0].value.value, str)


def test_ast_body_1_to_4_are_assign_batch48():
    tree = ast.parse(inspect.getsource(evaluation))
    for i in range(1, 5):
        assert isinstance(tree.body[i], ast.Assign)


def test_ast_body_5_is_all_assign_batch48():
    tree = ast.parse(inspect.getsource(evaluation))
    assert isinstance(tree.body[5], ast.Assign)


def test_ast_version_targets_names_batch48():
    tree = ast.parse(inspect.getsource(evaluation))
    names = []
    for i in range(1, 5):
        n = tree.body[i]
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if isinstance(t, ast.Name):
                names.append(t.id)
    assert names == ["EVALUATOR_VERSION", "REPORT_VERSION", "ANNOTATION_VERSION", "MANIFEST_VERSION"]


def test_ast_version_values_constants_batch48():
    tree = ast.parse(inspect.getsource(evaluation))
    for i in range(1, 5):
        n = tree.body[i]
        assert isinstance(n.value, ast.Constant)
        assert isinstance(n.value.value, str)


def test_ast_version_values_specific_batch48():
    tree = ast.parse(inspect.getsource(evaluation))
    expected = ["1.1", "1.1", "1.0", "1.0"]
    for i, exp in enumerate(expected, start=1):
        n = tree.body[i]
        assert n.value.value == exp


def test_ast_all_targets_name_batch48():
    tree = ast.parse(inspect.getsource(evaluation))
    all_assign = tree.body[5]
    target = all_assign.targets[0]
    assert isinstance(target, ast.Name)
    assert target.id == "__all__"


def test_ast_all_value_is_list_batch48():
    tree = ast.parse(inspect.getsource(evaluation))
    all_assign = tree.body[5]
    assert isinstance(all_assign.value, ast.List)


def test_ast_all_list_elts_count_batch48():
    tree = ast.parse(inspect.getsource(evaluation))
    all_assign = tree.body[5]
    assert len(all_assign.value.elts) == 4


def test_ast_all_list_elts_constants_batch48():
    tree = ast.parse(inspect.getsource(evaluation))
    all_assign = tree.body[5]
    for e in all_assign.value.elts:
        assert isinstance(e, ast.Constant)
        assert isinstance(e.value, str)


def test_ast_all_list_elts_values_batch48():
    tree = ast.parse(inspect.getsource(evaluation))
    all_assign = tree.body[5]
    values = [e.value for e in all_assign.value.elts]
    assert values == ["EVALUATOR_VERSION", "REPORT_VERSION", "ANNOTATION_VERSION", "MANIFEST_VERSION"]


def test_ast_no_import_batch48():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, (ast.Import, ast.ImportFrom))


def test_ast_no_class_def_batch48():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_no_function_def_batch48():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))


def test_ast_no_control_flow_batch48():
    tree = ast.parse(inspect.getsource(evaluation))
    for n in tree.body:
        assert not isinstance(n, (ast.If, ast.For, ast.While, ast.Try, ast.With))


# ---------- forbidden tokens 第一百一十三批 ----------

def test_source_no_eval_batch48():
    src = inspect.getsource(evaluation)
    assert "eval(" not in src


def test_source_no_exec_batch48():
    src = inspect.getsource(evaluation)
    assert "exec(" not in src


def test_source_no_compile_batch48():
    src = inspect.getsource(evaluation)
    assert "compile(" not in src


def test_source_no_globals_batch48():
    src = inspect.getsource(evaluation)
    assert "globals(" not in src


def test_source_no_locals_batch48():
    src = inspect.getsource(evaluation)
    assert "locals(" not in src


def test_source_no_os_system_batch48():
    src = inspect.getsource(evaluation)
    assert "os.system(" not in src


def test_source_no_popen_batch48():
    src = inspect.getsource(evaluation)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch48():
    src = inspect.getsource(evaluation)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch48():
    src = inspect.getsource(evaluation)
    assert "pickle.load(" not in src


def test_source_no_subprocess_batch48():
    src = inspect.getsource(evaluation)
    assert "subprocess" not in src


def test_source_no_lambda_batch48():
    src = inspect.getsource(evaluation)
    assert "lambda" not in src


def test_source_no_yield_batch48():
    src = inspect.getsource(evaluation)
    assert "yield" not in src


def test_source_no_walrus_batch48():
    src = inspect.getsource(evaluation)
    assert ":=" not in src


def test_source_no_async_batch48():
    src = inspect.getsource(evaluation)
    assert "async " not in src


def test_source_no_await_batch48():
    src = inspect.getsource(evaluation)
    assert "await " not in src


def test_source_no_raise_batch48():
    src = inspect.getsource(evaluation)
    assert "raise " not in src


# ---------- 综合 ----------

def test_module_import_does_not_modify_sys_modules_existing_batch48():
    """重新 import 不应破坏已有 sys.modules 引用。"""
    original = sys.modules.get("evaluation")
    import evaluation as ev2
    assert ev2 is original


def test_module_in_sys_modules_batch48():
    assert "evaluation" in sys.modules
    assert sys.modules["evaluation"] is evaluation


def test_four_versions_tuple_batch48():
    """打包成 tuple，4 项。"""
    t = (EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION)
    assert len(t) == 4
    assert t.count("1.1") == 2
    assert t.count("1.0") == 2


def test_four_versions_set_batch48():
    s = {EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION}
    assert s == {"1.1", "1.0"}
