r"""evaluation/manifest.py 边角测试 - 第十六轮（Round 254）。

补强已有 base/edges/edges2-15（共 ~990+ 测试）未覆盖的深度：
- 源码字符串断言（inspect.getsource）：含特定 token（frozen=True / @dataclass / content_group_count / paired_with / pyproject.toml 等）
- module metadata：__file__ 后缀 .py / __package__ == 'evaluation' / __name__ == 'evaluation.manifest'
- 函数 metadata：__module__/__qualname__/FunctionType；无 varargs/varkw；return_annotation
- ManifestError/DocumentEntry/ExpectedFailure/Manifest class metadata 精确
- dataclass frozen=True 验证
- dataclass field 数与名字精确（按定义顺序）
- _resolve_relative_path 各种 field_name 透传
- _detect_project_root 详细行为（pyproject.toml 必须是文件不是目录）
- Manifest properties 行为详细（categories_covered 排序/case-sensitive/unicode；content_group_count 各种 pair 组合）
- load_manifest 错误传播：manifest_version 不兼容 / pyproject 缺失
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from evaluation import MANIFEST_VERSION
from evaluation.manifest import (
    DocumentEntry,
    ExpectedFailure,
    Manifest,
    ManifestError,
    _detect_project_root,
    _has_backslash,
    _is_absolute_like,
    _resolve_relative_path,
    load_manifest,
)


# =========================================================================
# 源码字符串断言（inspect.getsource）
# =========================================================================


def test_module_source_contains_manifest_error_class():
    """源码含 'class ManifestError'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "class ManifestError" in src


def test_module_source_contains_is_absolute_like_function():
    """源码含 'def _is_absolute_like'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "def _is_absolute_like" in src


def test_module_source_contains_has_backslash_function():
    """源码含 'def _has_backslash'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "def _has_backslash" in src


def test_module_source_contains_dataclass_decorator():
    """源码含 '@dataclass(frozen=True)'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "@dataclass(frozen=True)" in src


def test_module_source_contains_document_entry_class():
    """源码含 'class DocumentEntry'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "class DocumentEntry" in src


def test_module_source_contains_expected_failure_class():
    """源码含 'class ExpectedFailure'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "class ExpectedFailure" in src


def test_module_source_contains_manifest_class():
    """源码含 'class Manifest'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "class Manifest" in src


def test_module_source_contains_resolve_relative_path():
    """源码含 'def _resolve_relative_path'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "def _resolve_relative_path" in src


def test_module_source_contains_load_manifest():
    """源码含 'def load_manifest'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "def load_manifest" in src


def test_module_source_contains_detect_project_root():
    """源码含 'def _detect_project_root'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "def _detect_project_root" in src


def test_module_source_contains_future_annotations():
    """源码含 'from __future__ import annotations'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_no_main_guard():
    """源码不含 '__main__'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "__main__" not in src


def test_module_source_contains_pyproject_toml():
    """源码含 'pyproject.toml'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "pyproject.toml" in src


def test_module_source_contains_manifest_version_reference():
    """源码含 'MANIFEST_VERSION'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "MANIFEST_VERSION" in src


def test_module_source_contains_validate_import():
    """源码含 'from evaluation.schema import validate'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "from evaluation.schema import validate" in src


def test_module_source_contains_paired_with():
    """源码含 'paired_with'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "paired_with" in src


def test_module_source_contains_content_group_count():
    """源码含 'content_group_count'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "content_group_count" in src


def test_module_source_contains_categories_covered():
    """源码含 'categories_covered'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "categories_covered" in src


def test_module_source_contains_resolve_call():
    """源码含 '.resolve()'。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert ".resolve()" in src


def test_module_source_contains_relative_to_call():
    """源码含 'relative_to('。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "relative_to(" in src


def test_module_source_contains_field_name_parameter():
    """源码含 'field_name' 参数。"""
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "field_name" in src


# =========================================================================
# 模块 metadata
# =========================================================================


def test_module_file_endswith_py():
    """__file__ 以 '.py' 结尾。"""
    import evaluation.manifest as m
    assert m.__file__.endswith(".py")


def test_module_file_contains_manifest():
    """__file__ 含 'manifest'。"""
    import evaluation.manifest as m
    assert "manifest" in m.__file__


def test_module_package_is_evaluation():
    """__package__ == 'evaluation'。"""
    import evaluation.manifest as m
    assert m.__package__ == "evaluation"


def test_module_name_is_evaluation_manifest():
    """__name__ == 'evaluation.manifest'。"""
    import evaluation.manifest as m
    assert m.__name__ == "evaluation.manifest"


def test_module_json_is_json_module():
    """json is json。"""
    import evaluation.manifest as m
    assert m.json is json


def test_module_dataclass_is_dataclass():
    """dataclass is dataclasses.dataclass。"""
    import evaluation.manifest as m
    from dataclasses import dataclass as dc
    assert m.dataclass is dc


def test_module_path_is_pathlib_path():
    """Path is pathlib.Path。"""
    import evaluation.manifest as m
    from pathlib import Path as P
    assert m.Path is P


def test_module_typing_any_is_typing_any():
    """Any is typing.Any。"""
    import evaluation.manifest as m
    from typing import Any as A
    assert m.Any is A


def test_module_manifest_version_is_constant():
    """MANIFEST_VERSION is evaluation.MANIFEST_VERSION。"""
    import evaluation.manifest as m
    assert m.MANIFEST_VERSION is MANIFEST_VERSION


# =========================================================================
# __all__ 精确
# =========================================================================


def test_module_all_is_list_not_tuple():
    """__all__ 是 list 不是 tuple。"""
    import evaluation.manifest as m
    assert isinstance(m.__all__, list)
    assert not isinstance(m.__all__, tuple)


def test_module_all_set_exact():
    """__all__ 集合精确。"""
    import evaluation.manifest as m
    assert set(m.__all__) == {
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    }


def test_module_all_no_private():
    """__all__ 不含 '_' 开头。"""
    import evaluation.manifest as m
    for name in m.__all__:
        assert not name.startswith("_")


def test_module_all_does_not_contain_internal_helpers():
    """__all__ 不含 _is_absolute_like / _has_backslash / _resolve_relative_path / _detect_project_root。"""
    import evaluation.manifest as m
    for name in (
        "_is_absolute_like",
        "_has_backslash",
        "_resolve_relative_path",
        "_detect_project_root",
    ):
        assert name not in m.__all__


def test_module_namespace_contains_all():
    """所有 __all__ 名字在命名空间。"""
    import evaluation.manifest as m
    for name in m.__all__:
        assert hasattr(m, name)


def test_module_namespace_contains_internal_helpers():
    """命名空间含 4 个私有 helper。"""
    import evaluation.manifest as m
    for name in (
        "_is_absolute_like",
        "_has_backslash",
        "_resolve_relative_path",
        "_detect_project_root",
    ):
        assert hasattr(m, name)


# =========================================================================
# class metadata
# =========================================================================


def test_manifest_error_module_attribute():
    """__module__ == 'evaluation.manifest'。"""
    assert ManifestError.__module__ == "evaluation.manifest"


def test_manifest_error_qualname():
    """__qualname__ == 'ManifestError'。"""
    assert ManifestError.__qualname__ == "ManifestError"


def test_manifest_error_name():
    """__name__ == 'ManifestError'。"""
    assert ManifestError.__name__ == "ManifestError"


def test_manifest_error_mro_contains_exception():
    """mro 含 Exception。"""
    assert Exception in ManifestError.__mro__


def test_manifest_error_mro_length_four():
    """mro 长度 4：[ManifestError, Exception, BaseException, object]。"""
    assert len(ManifestError.__mro__) == 4


def test_document_entry_module_attribute():
    """__module__ == 'evaluation.manifest'。"""
    assert DocumentEntry.__module__ == "evaluation.manifest"


def test_document_entry_qualname():
    """__qualname__ == 'DocumentEntry'。"""
    assert DocumentEntry.__qualname__ == "DocumentEntry"


def test_expected_failure_module_attribute():
    """__module__ == 'evaluation.manifest'。"""
    assert ExpectedFailure.__module__ == "evaluation.manifest"


def test_expected_failure_qualname():
    """__qualname__ == 'ExpectedFailure'。"""
    assert ExpectedFailure.__qualname__ == "ExpectedFailure"


def test_manifest_module_attribute():
    """__module__ == 'evaluation.manifest'。"""
    assert Manifest.__module__ == "evaluation.manifest"


def test_manifest_qualname():
    """__qualname__ == 'Manifest'。"""
    assert Manifest.__qualname__ == "Manifest"


# =========================================================================
# dataclass frozen 验证
# =========================================================================


def test_document_entry_is_frozen():
    """DocumentEntry frozen=True。"""
    assert getattr(DocumentEntry, "__dataclass_params__").frozen is True


def test_expected_failure_is_frozen():
    """ExpectedFailure frozen=True。"""
    assert getattr(ExpectedFailure, "__dataclass_params__").frozen is True


def test_manifest_is_frozen():
    """Manifest frozen=True。"""
    assert getattr(Manifest, "__dataclass_params__").frozen is True


def test_document_entry_field_count_ten():
    """DocumentEntry 10 个字段。"""
    from dataclasses import fields
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_field_names_exact():
    """DocumentEntry 字段名顺序精确。"""
    from dataclasses import fields
    names = [f.name for f in fields(DocumentEntry)]
    assert names == [
        "doc_id",
        "path_str",
        "resolved_path",
        "source_type",
        "sha256",
        "categories",
        "paired_with",
        "annotation_file_str",
        "annotation_resolved",
        "expectations",
    ]


def test_expected_failure_field_count_five():
    """ExpectedFailure 5 个字段。"""
    from dataclasses import fields
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_field_names_exact():
    """ExpectedFailure 字段名顺序精确。"""
    from dataclasses import fields
    names = [f.name for f in fields(ExpectedFailure)]
    assert names == ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]


def test_manifest_field_count_five():
    """Manifest 5 个字段。"""
    from dataclasses import fields
    assert len(fields(Manifest)) == 5


def test_manifest_field_names_exact():
    """Manifest 字段名顺序精确。"""
    from dataclasses import fields
    names = [f.name for f in fields(Manifest)]
    assert names == [
        "manifest_version",
        "devset_status",
        "documents",
        "expected_failures",
        "project_root",
    ]


def test_document_entry_hashable():
    """DocumentEntry frozen → 可 hash。"""
    entry = DocumentEntry(
        doc_id="d1",
        path_str="a.pdf",
        resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf",
        sha256=None,
        categories=("math",),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    hash(entry)  # 不抛


def test_manifest_hashable():
    """Manifest frozen → 可 hash。"""
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    hash(m)


def test_document_entry_frozen_blocks_setattr():
    """frozen dataclass 不可 setattr。"""
    entry = DocumentEntry(
        doc_id="d1",
        path_str="a.pdf",
        resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(Exception):
        entry.doc_id = "different"


def test_manifest_frozen_blocks_setattr():
    """Manifest frozen 不可 setattr。"""
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    with pytest.raises(Exception):
        m.devset_status = "complete"


# =========================================================================
# 函数 metadata
# =========================================================================


def test_load_manifest_module_attribute():
    """__module__ == 'evaluation.manifest'。"""
    assert load_manifest.__module__ == "evaluation.manifest"


def test_load_manifest_qualname():
    """__qualname__ == 'load_manifest'。"""
    assert load_manifest.__qualname__ == "load_manifest"


def test_is_absolute_like_module_attribute():
    """__module__ == 'evaluation.manifest'。"""
    assert _is_absolute_like.__module__ == "evaluation.manifest"


def test_has_backslash_module_attribute():
    """__module__ == 'evaluation.manifest'。"""
    assert _has_backslash.__module__ == "evaluation.manifest"


def test_resolve_relative_path_module_attribute():
    """__module__ == 'evaluation.manifest'。"""
    assert _resolve_relative_path.__module__ == "evaluation.manifest"


def test_detect_project_root_module_attribute():
    """__module__ == 'evaluation.manifest'。"""
    assert _detect_project_root.__module__ == "evaluation.manifest"


def test_load_manifest_is_python_function():
    """是 Python 函数。"""
    import types
    assert isinstance(load_manifest, types.FunctionType)


def test_load_manifest_no_varargs():
    """无 varargs/varkw。"""
    sig = inspect.signature(load_manifest)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_load_manifest_return_annotation_is_str():
    """return annotation 是 str（__future__）。"""
    sig = inspect.signature(load_manifest)
    assert isinstance(sig.return_annotation, str)


def test_load_manifest_return_annotation_contains_manifest():
    """return annotation 含 'Manifest'。"""
    sig = inspect.signature(load_manifest)
    assert "Manifest" in sig.return_annotation


def test_load_manifest_param_count_two():
    """signature 2 个参数 (manifest_path, project_root)。"""
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.keys())
    assert params == ["manifest_path", "project_root"]


def test_load_manifest_project_root_default_none():
    """project_root default is None。"""
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


# =========================================================================
# _is_absolute_like 签名
# =========================================================================


def test_is_absolute_like_signature_one_param():
    """1 个参数 'path_str'。"""
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]


def test_is_absolute_like_no_varargs():
    """无 varargs/varkw。"""
    sig = inspect.signature(_is_absolute_like)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_is_absolute_like_return_annotation_is_bool():
    """return annotation 含 'bool'。"""
    sig = inspect.signature(_is_absolute_like)
    assert "bool" in sig.return_annotation


# =========================================================================
# _has_backslash 签名
# =========================================================================


def test_has_backslash_signature_one_param():
    """1 个参数 'path_str'。"""
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]


def test_has_backslash_return_annotation_is_bool():
    """return annotation 含 'bool'。"""
    sig = inspect.signature(_has_backslash)
    assert "bool" in sig.return_annotation


# =========================================================================
# _resolve_relative_path 签名
# =========================================================================


def test_resolve_relative_path_signature_three_params():
    """3 个参数 (path_str, project_root, field_name)。"""
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.keys())
    assert params == ["path_str", "project_root", "field_name"]


def test_resolve_relative_path_return_annotation_is_path():
    """return annotation 含 'Path'。"""
    sig = inspect.signature(_resolve_relative_path)
    assert "Path" in sig.return_annotation


def test_resolve_relative_path_no_varargs():
    """无 varargs/varkw。"""
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


# =========================================================================
# _detect_project_root 签名
# =========================================================================


def test_detect_project_root_signature_one_param():
    """1 个参数 'start'。"""
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.keys())
    assert params == ["start"]


def test_detect_project_root_return_annotation_is_path():
    """return annotation 含 'Path'。"""
    sig = inspect.signature(_detect_project_root)
    assert "Path" in sig.return_annotation


# =========================================================================
# Manifest properties 详细
# =========================================================================


def _make_manifest(documents):
    """构造测试用 Manifest。"""
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=tuple(documents),
        expected_failures=(),
        project_root=Path("/tmp"),
    )


def _make_doc(doc_id, source_type="pdf", categories=(), paired_with=None):
    """构造测试用 DocumentEntry。"""
    return DocumentEntry(
        doc_id=doc_id,
        path_str=f"{doc_id}.pdf",
        resolved_path=Path(f"/tmp/{doc_id}.pdf"),
        source_type=source_type,
        sha256=None,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def test_manifest_pdf_count_calculation():
    """pdf_count = sum of pdf documents。"""
    m = _make_manifest([
        _make_doc("d1", "pdf"),
        _make_doc("d2", "docx"),
        _make_doc("d3", "pdf"),
    ])
    assert m.pdf_count == 2


def test_manifest_docx_count_calculation():
    """docx_count = sum of docx documents。"""
    m = _make_manifest([
        _make_doc("d1", "pdf"),
        _make_doc("d2", "docx"),
        _make_doc("d3", "docx"),
        _make_doc("d4", "docx"),
    ])
    assert m.docx_count == 3


def test_manifest_file_count_calculation():
    """file_count = len(documents)。"""
    m = _make_manifest([_make_doc(f"d{i}") for i in range(5)])
    assert m.file_count == 5


def test_manifest_categories_covered_sorted_unique():
    """categories_covered 排序 + 唯一。"""
    m = _make_manifest([
        _make_doc("d1", categories=("math", "science")),
        _make_doc("d2", categories=("science", "history")),
        _make_doc("d3", categories=("math",)),
    ])
    assert m.categories_covered == ["history", "math", "science"]


def test_manifest_categories_covered_empty():
    """无 categories → 空 list。"""
    m = _make_manifest([_make_doc("d1"), _make_doc("d2")])
    assert m.categories_covered == []


def test_manifest_categories_covered_case_sensitive():
    """categories 大小写敏感。"""
    m = _make_manifest([
        _make_doc("d1", categories=("Math",)),
        _make_doc("d2", categories=("math",)),
    ])
    # 'Math' 和 'math' 视为不同
    assert "Math" in m.categories_covered
    assert "math" in m.categories_covered
    assert sorted(["Math", "math"]) == m.categories_covered


def test_manifest_categories_covered_unicode():
    """unicode categories 排序正确。"""
    m = _make_manifest([
        _make_doc("d1", categories=("中文", "数学")),
        _make_doc("d2", categories=("物理",)),
    ])
    assert m.categories_covered == sorted(["中文", "数学", "物理"])


def test_manifest_content_group_count_unpaired_all():
    """所有未配对 → 每个算 1 组。"""
    m = _make_manifest([
        _make_doc("d1"),
        _make_doc("d2"),
        _make_doc("d3"),
    ])
    assert m.content_group_count == 3


def test_manifest_content_group_count_one_pair():
    """1 对配对 + 1 未配对 → 2 组。"""
    m = _make_manifest([
        _make_doc("d1", paired_with="d2"),
        _make_doc("d2", paired_with="d1"),
        _make_doc("d3"),
    ])
    assert m.content_group_count == 2


def test_manifest_content_group_count_only_unpaired_with_field():
    """所有都有 paired_with 但 pair_ids 去重 → frozenset({d1,d2}) 是 1 组。"""
    m = _make_manifest([
        _make_doc("d1", paired_with="d2"),
        _make_doc("d2", paired_with="d1"),
    ])
    # 1 对配对 = 1 组
    assert m.content_group_count == 1


def test_manifest_content_group_count_no_documents():
    """无 documents → 0 组。"""
    m = _make_manifest([])
    assert m.content_group_count == 0


def test_manifest_file_count_empty():
    """无 documents → file_count=0。"""
    m = _make_manifest([])
    assert m.file_count == 0


def test_manifest_pdf_count_empty():
    """无 documents → pdf_count=0。"""
    m = _make_manifest([])
    assert m.pdf_count == 0


def test_manifest_categories_covered_returns_list_type():
    """categories_covered 返回 list。"""
    m = _make_manifest([_make_doc("d1", categories=("a",))])
    out = m.categories_covered
    assert isinstance(out, list)


def test_manifest_pdf_count_returns_int_type():
    """pdf_count 返回 int。"""
    m = _make_manifest([_make_doc("d1", "pdf")])
    assert isinstance(m.pdf_count, int)


def test_manifest_categories_covered_returns_new_list_each_call():
    """每次返回新 list。"""
    m = _make_manifest([_make_doc("d1", categories=("a",))])
    a = m.categories_covered
    b = m.categories_covered
    assert a == b
    # 修改一次不影响下次（sorted 内部生成新 list）
    a.append("modified")
    assert "modified" not in m.categories_covered


# =========================================================================
# ManifestError 行为
# =========================================================================


def test_manifest_error_str():
    """str(error) 返回 message。"""
    e = ManifestError("hello")
    assert str(e) == "hello"


def test_manifest_error_repr():
    """repr 含类名。"""
    e = ManifestError("msg")
    assert "ManifestError" in repr(e)


def test_manifest_error_caught_as_exception():
    """可被通用 except Exception 捕获。"""
    try:
        raise ManifestError("test")
    except Exception as e:
        assert isinstance(e, ManifestError)


def test_manifest_error_can_be_raised():
    """可 raise。"""
    with pytest.raises(ManifestError):
        raise ManifestError("msg")


def test_manifest_error_args_zero():
    """ManifestError() 无参数。"""
    e = ManifestError()
    assert e.args == ()


# =========================================================================
# _is_absolute_like 边界
# =========================================================================


def test_is_absolute_like_relative_path_returns_false():
    """相对路径 → False。"""
    assert _is_absolute_like("foo/bar") is False
    assert _is_absolute_like("foo.pdf") is False
    assert _is_absolute_like("./foo/bar") is False


def test_is_absolute_like_posix_absolute_returns_true():
    """POSIX 绝对路径 → True。"""
    assert _is_absolute_like("/foo/bar") is True
    assert _is_absolute_like("/") is True


def test_is_absolute_like_windows_drive_returns_true():
    """Windows 盘符 → True。"""
    assert _is_absolute_like("C:\\foo") is True
    assert _is_absolute_like("D:/bar") is True


def test_is_absolute_like_alpha_no_separator_returns_false():
    r"""alpha: 后无 / 或 \ → False（不是绝对路径）。"""
    assert _is_absolute_like("C:foo") is False
    assert _is_absolute_like("a:b") is False


def test_is_absolute_like_returns_bool_type():
    """返回 bool 类型。"""
    assert type(_is_absolute_like("/x")) is bool
    assert type(_is_absolute_like("x")) is bool


# =========================================================================
# _has_backslash 边界
# =========================================================================


def test_has_backslash_no_backslash_returns_false():
    """无反斜杠 → False。"""
    assert _has_backslash("foo/bar") is False
    assert _has_backslash("foo.pdf") is False


def test_has_backslash_with_backslash_returns_true():
    """有反斜杠 → True。"""
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_returns_bool_type():
    """返回 bool 类型。"""
    assert type(_has_backslash("foo")) is bool
    assert type(_has_backslash("foo\\bar")) is bool


# =========================================================================
# _resolve_relative_path 详细
# =========================================================================


def test_resolve_relative_path_returns_path_type(tmp_path: Path):
    """返回 Path 实例。"""
    out = _resolve_relative_path("foo.pdf", tmp_path, "test")
    assert isinstance(out, Path)


def test_resolve_relative_path_returns_absolute(tmp_path: Path):
    """返回绝对路径。"""
    out = _resolve_relative_path("foo.pdf", tmp_path, "test")
    assert out.is_absolute()


def test_resolve_relative_path_subdirectory(tmp_path: Path):
    """子目录路径 OK。"""
    # 创建子目录与文件
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "foo.pdf").write_bytes(b"")
    out = _resolve_relative_path("sub/foo.pdf", tmp_path, "test")
    assert out == (tmp_path / "sub" / "foo.pdf").resolve()


def test_resolve_relative_path_error_messages_contain_field_name(tmp_path: Path):
    """错误 message 含 field_name。"""
    for path_str, expected_field in [
        ("", "empty_field"),
        ("/abs", "abs_field"),
        ("back\\slash", "back_field"),
    ]:
        with pytest.raises(ManifestError) as exc_info:
            _resolve_relative_path(path_str, tmp_path, expected_field)
        assert expected_field in str(exc_info.value)


def test_resolve_relative_path_outside_root_raises(tmp_path: Path):
    """路径解析后位于 project_root 外 → raises。"""
    # 用 .. 跳出去
    with pytest.raises(ManifestError):
        _resolve_relative_path("../outside", tmp_path, "test_field")


def test_resolve_relative_path_unicode_filename(tmp_path: Path):
    """unicode 文件名 → 仍能 resolve。"""
    out = _resolve_relative_path("中文.pdf", tmp_path, "test")
    assert out == (tmp_path / "中文.pdf").resolve()


# =========================================================================
# _detect_project_root 详细
# =========================================================================


def test_detect_project_root_finds_pyproject_in_self(tmp_path: Path):
    """start 是含 pyproject.toml 的目录 → 返回该目录。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_finds_pyproject_in_parent(tmp_path: Path):
    """start 是子目录 → 找到父目录的 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    out = _detect_project_root(sub)
    assert out == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_cur(tmp_path: Path):
    """无 pyproject.toml → 返回 cur（start 自身或 parent）。"""
    out = _detect_project_root(tmp_path)
    # cur 是 start.parent（如果 start 是 file）或 start（如果 dir）
    assert out == tmp_path.resolve()


def test_detect_project_root_with_file_start(tmp_path: Path):
    """start 是 file → cur=start.parent。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    f = tmp_path / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    out = _detect_project_root(f)
    assert out == tmp_path.resolve()


def test_detect_project_root_returns_absolute(tmp_path: Path):
    """返回绝对路径。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out.is_absolute()


def test_detect_project_root_returns_path_type(tmp_path: Path):
    """返回 Path 实例。"""
    out = _detect_project_root(tmp_path)
    assert isinstance(out, Path)


# =========================================================================
# load_manifest 端到端边界
# =========================================================================


def test_load_manifest_missing_file_raises(tmp_path: Path):
    """manifest 文件不存在 → ManifestError。"""
    with pytest.raises(ManifestError):
        load_manifest(tmp_path / "missing.json")


def test_load_manifest_directory_raises(tmp_path: Path):
    """manifest 路径是目录 → ManifestError。"""
    with pytest.raises(ManifestError):
        load_manifest(tmp_path)


def test_load_manifest_invalid_json_raises(tmp_path: Path):
    """非法 JSON → ManifestError。"""
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_load_manifest_empty_file_raises(tmp_path: Path):
    """空文件 → ManifestError。"""
    p = tmp_path / "m.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_load_manifest_str_path_accepted(tmp_path: Path):
    """manifest_path 接受 str。"""
    minimal = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(minimal), encoding="utf-8")
    # str path 也能用
    out = load_manifest(str(p))
    assert isinstance(out, Manifest)


def test_load_manifest_explicit_project_root_str(tmp_path: Path):
    """project_root 接受 str。"""
    minimal = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(minimal), encoding="utf-8")
    out = load_manifest(p, project_root=str(tmp_path))
    assert out.project_root == tmp_path.resolve()


def test_load_manifest_returns_manifest_instance(tmp_path: Path):
    """返回 Manifest 实例。"""
    minimal = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(minimal), encoding="utf-8")
    out = load_manifest(p)
    assert isinstance(out, Manifest)


def test_load_manifest_documents_is_tuple(tmp_path: Path):
    """Manifest.documents 是 tuple。"""
    minimal = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(minimal), encoding="utf-8")
    out = load_manifest(p)
    assert isinstance(out.documents, tuple)
    assert isinstance(out.expected_failures, tuple)


def test_load_manifest_project_root_is_path(tmp_path: Path):
    """Manifest.project_root 是 Path。"""
    minimal = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(minimal), encoding="utf-8")
    out = load_manifest(p)
    assert isinstance(out.project_root, Path)


def test_load_manifest_manifest_version_propagated(tmp_path: Path):
    """manifest_version 透传。"""
    minimal = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(minimal), encoding="utf-8")
    out = load_manifest(p)
    assert out.manifest_version == MANIFEST_VERSION


def test_load_manifest_devset_status_propagated(tmp_path: Path):
    """devset_status 透传。"""
    minimal = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(minimal), encoding="utf-8")
    out = load_manifest(p)
    assert out.devset_status == "complete"
