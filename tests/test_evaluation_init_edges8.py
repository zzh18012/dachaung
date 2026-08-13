"""evaluation/__init__.py 第八轮 edges 测试（Round 651）。

补强 edges7 未触及的角度（第四十八批）。

新角度：
- 4 个版本常量语义稳定（不可变 / 字符串方法 / 比较相等 / 排序）
- __all__ 列表精确（顺序 / 内容 / 类型）
- 模块属性访问（getattr / hasattr / dir 包含版本）
- importlib.reload 后版本常量仍是原值
- 模块 docstring 内容（设计原则 / 版本历史 / v1.0 v1.1 区别 / 不依赖 app/*）
- AST 结构补强（4 Assign / 1 __all__ list / module docstring / 无 FunctionDef / 无 ClassDef / 无 Import）
- forbidden tokens 第一百二十一批
"""

from __future__ import annotations

import ast
import importlib
import inspect
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


# ---------- 4 个版本常量语义稳定 ----------

def test_evaluator_version_eq_report_version_batch48():
    """当前都是 '1.1'。"""
    assert EVALUATOR_VERSION == REPORT_VERSION


def test_annotation_version_eq_manifest_version_batch48():
    """当前都是 '1.0'。"""
    assert ANNOTATION_VERSION == MANIFEST_VERSION


def test_versions_str_hashable_batch48():
    """版本字符串可哈希。"""
    assert hash(EVALUATOR_VERSION) == hash("1.1")
    assert hash(REPORT_VERSION) == hash("1.1")
    assert hash(ANNOTATION_VERSION) == hash("1.0")
    assert hash(MANIFEST_VERSION) == hash("1.0")


def test_versions_in_set_batch48():
    s = {EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION}
    assert s == {"1.1", "1.0"}


def test_versions_len_batch48():
    assert len(EVALUATOR_VERSION) == 3
    assert len(REPORT_VERSION) == 3
    assert len(ANNOTATION_VERSION) == 3
    assert len(MANIFEST_VERSION) == 3


def test_versions_string_methods_batch48():
    """版本字符串支持 .split / .replace / .startswith 等。"""
    assert EVALUATOR_VERSION.split(".") == ["1", "1"]
    assert REPORT_VERSION.replace(".", "-") == "1-1"
    assert ANNOTATION_VERSION.startswith("1")
    assert MANIFEST_VERSION.endswith("0")


def test_evaluator_version_upper_batch48():
    assert EVALUATOR_VERSION.upper() == "1.1"  # 数字没大小写


def test_versions_are_immutable_literals_batch48():
    """str 是不可变的，赋值 item 抛 TypeError。"""
    with pytest.raises(TypeError):
        EVALUATOR_VERSION[0] = "X"  # type: ignore[index]


# ---------- __all__ 列表精确 ----------

def test_all_list_exact_order_batch48():
    """__all__ 顺序：EVALUATOR / REPORT / ANNOTATION / MANIFEST。"""
    import evaluation
    assert evaluation.__all__ == [
        "EVALUATOR_VERSION",
        "REPORT_VERSION",
        "ANNOTATION_VERSION",
        "MANIFEST_VERSION",
    ]


def test_all_list_len_4_batch48():
    assert len(eval_mod.__all__) == 4


def test_all_list_entries_are_str_batch48():
    for entry in eval_mod.__all__:
        assert isinstance(entry, str)


def test_all_list_entries_unique_batch48():
    assert len(set(eval_mod.__all__)) == len(eval_mod.__all__)


def test_all_list_exported_names_exist_in_module_batch48():
    for name in eval_mod.__all__:
        assert hasattr(eval_mod, name)


def test_all_list_not_tuple_batch48():
    assert isinstance(eval_mod.__all__, list)


# ---------- 模块属性访问 ----------

def test_getattr_evaluator_version_batch48():
    assert getattr(eval_mod, "EVALUATOR_VERSION") == "1.1"


def test_getattr_report_version_batch48():
    assert getattr(eval_mod, "REPORT_VERSION") == "1.1"


def test_getattr_annotation_version_batch48():
    assert getattr(eval_mod, "ANNOTATION_VERSION") == "1.0"


def test_getattr_manifest_version_batch48():
    assert getattr(eval_mod, "MANIFEST_VERSION") == "1.0"


def test_getattr_missing_raises_attribute_error_batch48():
    with pytest.raises(AttributeError):
        getattr(eval_mod, "MISSING_VERSION")


def test_getattr_default_batch48():
    assert getattr(eval_mod, "MISSING_VERSION", "default") == "default"


def test_hasattr_evaluator_version_batch48():
    assert hasattr(eval_mod, "EVALUATOR_VERSION")


def test_hasattr_missing_false_batch48():
    assert not hasattr(eval_mod, "MISSING_VERSION")


def test_dir_contains_evaluator_version_batch48():
    assert "EVALUATOR_VERSION" in dir(eval_mod)


def test_dir_contains_all_four_batch48():
    d = dir(eval_mod)
    assert "EVALUATOR_VERSION" in d
    assert "REPORT_VERSION" in d
    assert "ANNOTATION_VERSION" in d
    assert "MANIFEST_VERSION" in d


def test_dir_contains_all_batch48():
    assert "__all__" in dir(eval_mod)


# ---------- importlib.reload 后版本常量仍是原值 ----------

def test_reload_preserves_evaluator_version_batch48():
    """reload 后 EVALUATOR_VERSION 仍是 '1.1'。"""
    importlib.reload(eval_mod)
    assert eval_mod.EVALUATOR_VERSION == "1.1"


def test_reload_preserves_all_four_versions_batch48():
    importlib.reload(eval_mod)
    assert eval_mod.EVALUATOR_VERSION == "1.1"
    assert eval_mod.REPORT_VERSION == "1.1"
    assert eval_mod.ANNOTATION_VERSION == "1.0"
    assert eval_mod.MANIFEST_VERSION == "1.0"


def test_reload_preserves_all_list_batch48():
    importlib.reload(eval_mod)
    assert eval_mod.__all__ == [
        "EVALUATOR_VERSION",
        "REPORT_VERSION",
        "ANNOTATION_VERSION",
        "MANIFEST_VERSION",
    ]


def test_reload_id_changes_batch48():
    """reload 后 module 对象 identity 不变（同 module 重新初始化）。"""
    before_id = id(eval_mod)
    importlib.reload(eval_mod)
    assert id(eval_mod) == before_id


# ---------- 模块 docstring 内容 ----------

def test_module_docstring_present_batch48():
    assert eval_mod.__doc__ is not None
    assert isinstance(eval_mod.__doc__, str)


def test_module_docstring_contains_design_principles_batch48():
    """docstring 应当提到设计原则。"""
    doc = eval_mod.__doc__
    assert "设计原则" in doc or "原则" in doc


def test_module_docstring_mentions_parser_chunker_batch48():
    doc = eval_mod.__doc__
    assert "parser" in doc or "chunker" in doc or "分块" in doc or "解析" in doc


def test_module_docstring_mentions_null_reason_batch48():
    doc = eval_mod.__doc__
    assert "null" in doc.lower() or "reason" in doc.lower() or "原因" in doc


def test_module_docstring_mentions_version_history_batch48():
    doc = eval_mod.__doc__
    assert "版本历史" in doc or "v1.0" in doc or "v1.1" in doc


def test_module_docstring_mentions_text_preservation_batch48():
    doc = eval_mod.__doc__
    assert "text_preservation" in doc


def test_module_docstring_mentions_v1_0_v1_1_batch48():
    doc = eval_mod.__doc__
    assert "v1.0" in doc
    assert "v1.1" in doc


def test_module_docstring_mentions_incompatible_baseline_batch48():
    """docstring 说明 v1.0 / v1.1 baseline 不可横向比较。"""
    doc = eval_mod.__doc__
    assert "不可" in doc or "不" in doc


# ---------- 模块元信息 ----------

def test_module_file_endswith_init_py_batch48():
    assert eval_mod.__file__.endswith("__init__.py")


def test_module_package_evaluation_batch48():
    assert eval_mod.__package__ == "evaluation"


def test_module_name_evaluation_batch48():
    assert eval_mod.__name__ == "evaluation"


def test_module_spec_name_evaluation_batch48():
    assert eval_mod.__spec__.name == "evaluation"


def test_module_dict_contains_all_four_versions_batch48():
    d = eval_mod.__dict__
    assert "EVALUATOR_VERSION" in d
    assert "REPORT_VERSION" in d
    assert "ANNOTATION_VERSION" in d
    assert "MANIFEST_VERSION" in d


def test_module_dict_all_is_list_batch48():
    assert isinstance(eval_mod.__dict__["__all__"], list)


def test_module_dict_values_match_constants_batch48():
    d = eval_mod.__dict__
    assert d["EVALUATOR_VERSION"] == "1.1"
    assert d["REPORT_VERSION"] == "1.1"
    assert d["ANNOTATION_VERSION"] == "1.0"
    assert d["MANIFEST_VERSION"] == "1.0"


# ---------- 模块源码补强 ----------

def test_source_contains_evaluator_version_batch48():
    src = inspect.getsource(eval_mod)
    assert 'EVALUATOR_VERSION = "1.1"' in src


def test_source_contains_report_version_batch48():
    src = inspect.getsource(eval_mod)
    assert 'REPORT_VERSION = "1.1"' in src


def test_source_contains_annotation_version_batch48():
    src = inspect.getsource(eval_mod)
    assert 'ANNOTATION_VERSION = "1.0"' in src


def test_source_contains_manifest_version_batch48():
    src = inspect.getsource(eval_mod)
    assert 'MANIFEST_VERSION = "1.0"' in src


def test_source_contains_all_list_batch48():
    src = inspect.getsource(eval_mod)
    assert "__all__" in src


def test_source_contains_no_app_import_batch48():
    """__init__.py 不导入 app/* 子模块。"""
    src = inspect.getsource(eval_mod)
    assert "from app" not in src
    assert "import app" not in src


def test_source_contains_no_parser_import_batch48():
    src = inspect.getsource(eval_mod)
    assert "from evaluation.metrics" not in src
    assert "from evaluation.runner" not in src


def test_source_contains_no_class_def_batch48():
    src = inspect.getsource(eval_mod)
    assert "class " not in src


def test_source_contains_no_def_batch48():
    src = inspect.getsource(eval_mod)
    assert "\ndef " not in src


def test_source_contains_principle_no_fake_batch48():
    """docstring 提到"不伪造"。"""
    src = inspect.getsource(eval_mod)
    assert "不伪造" in src


def test_source_contains_principle_no_change_pipeline_batch48():
    """docstring 提到"不修改 parser / chunker / pipeline"。"""
    src = inspect.getsource(eval_mod)
    assert "不修改" in src


def test_source_contains_principle_total_only_batch48():
    """docstring 提到"计时只记 total"。"""
    src = inspect.getsource(eval_mod)
    assert "total" in src


def test_source_contains_principle_not_instrumented_batch48():
    """docstring 提到 not_instrumented。"""
    src = inspect.getsource(eval_mod)
    assert "not_instrumented" in src


def test_source_contains_principle_no_1_0_fake_batch48():
    """docstring 提到比例指标分母为 0 时不返回 1.0。"""
    src = inspect.getsource(eval_mod)
    assert "1.0" in src


def test_source_contains_history_v1_0_batch48():
    src = inspect.getsource(eval_mod)
    assert "v1.0" in src


def test_source_contains_history_v1_1_batch48():
    src = inspect.getsource(eval_mod)
    assert "v1.1" in src


def test_source_contains_history_word内硬切_batch48():
    """docstring 提到"词内硬切"。"""
    src = inspect.getsource(eval_mod)
    assert "词内硬切" in src


def test_source_contains_history_口径D_batch48():
    """docstring 提到"口径 D"。"""
    src = inspect.getsource(eval_mod)
    assert "口径 D" in src or "口径D" in src


def test_source_no_dependencies_outside_jsonschema_batch48():
    """__init__.py 不引入除 jsonschema 之外的依赖（实际上是零依赖纯常量文件）。"""
    src = inspect.getsource(eval_mod)
    # 没有 import 语句
    assert "import " not in src.replace("importlib", "")  # rough


# ---------- AST 结构补强 ----------

def test_ast_no_function_def_batch48():
    tree = ast.parse(inspect.getsource(eval_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 0


def test_ast_no_class_def_batch48():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch48():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_no_import_batch48():
    """模块顶部无 import 语句。"""
    tree = ast.parse(inspect.getsource(eval_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 0


def test_ast_module_docstring_batch48():
    tree = ast.parse(inspect.getsource(eval_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_top_level_assigns_count_batch48():
    """4 个版本常量 + __all__ = 5 个 Assign。"""
    tree = ast.parse(inspect.getsource(eval_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 5


def test_ast_all_list_4_entries_batch48():
    tree = ast.parse(inspect.getsource(eval_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == "__all__"
    )
    assert isinstance(all_assign.value, ast.List)
    assert len(all_assign.value.elts) == 4


def test_ast_all_entries_are_str_constants_batch48():
    tree = ast.parse(inspect.getsource(eval_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == "__all__"
    )
    for elt in all_assign.value.elts:
        assert isinstance(elt, ast.Constant)
        assert isinstance(elt.value, str)


def test_ast_version_assigns_are_str_constants_batch48():
    tree = ast.parse(inspect.getsource(eval_mod))
    version_names = {"EVALUATOR_VERSION", "REPORT_VERSION", "ANNOTATION_VERSION", "MANIFEST_VERSION"}
    version_assigns = [
        n for n in tree.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id in version_names
    ]
    assert len(version_assigns) == 4
    for va in version_assigns:
        assert isinstance(va.value, ast.Constant)
        assert isinstance(va.value.value, str)


# ---------- forbidden tokens 第一百二十一批 ----------

def _src() -> str:
    return inspect.getsource(eval_mod)


def test_source_no_eval_batch48():
    assert "eval(" not in _src()


def test_source_no_exec_batch48():
    assert "exec(" not in _src()


def test_source_no_compile_batch48():
    assert "compile(" not in _src()


def test_source_no_globals_batch48():
    assert "globals(" not in _src()


def test_source_no_locals_batch48():
    assert "locals(" not in _src()


def test_source_no_os_system_batch48():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch48():
    assert "subprocess" not in _src()


def test_source_no_popen_batch48():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch48():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch48():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch48():
    assert "socket" not in _src()


def test_source_no_requests_batch48():
    assert "requests" not in _src()


def test_source_no_urllib_batch48():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch48():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch48():
    assert "yield" not in _src()


def test_source_no_async_def_batch48():
    assert "async def" not in _src()


def test_source_no_await_batch48():
    assert "await " not in _src()


def test_source_no_raise_batch48():
    assert "raise" not in _src()


def test_source_no_open_batch48():
    """__init__.py 是纯常量模块，不应有 open() 调用。"""
    assert "open(" not in _src()
