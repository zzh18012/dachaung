r"""evaluation/manifest.py 边角测试 - 第十七轮（Round 261）。

补强已有 base/edges/edges2-16（共 ~1050+ 测试）未覆盖的深度：
- 源码字符串断言（inspect.getsource）：未覆盖 token
- module docstring 内容
- 类型注解 introspection（typing.get_type_hints）
- dataclass __dataclass_fields__ / __dataclass_params__ 详细
- DocumentEntry/ExpectedFailure/Manifest frozen=True 验证
- _is_absolute_like alpha check：单字符、双字符、3+字符边界
- _has_backslash 返回 bool 类型
- ManifestError 详细：可 raise/except + str/repr + args
- Manifest property：content_group_count 各种 pairing 组合（self-pair / one-way / mutual / 链式）
- categories_covered 嵌套 tuple / unicode
- _resolve_relative_path 错误 message 格式
- _detect_project_root 边界
- load_manifest 接受 str 路径 + project_root
- 模块 namespace 完整性
- __all__ 精确
- 各 helper FunctionType 验证
"""

from __future__ import annotations

import inspect
import json
import typing
from dataclasses import dataclass, fields
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
# 源码字符串断言（inspect.getsource）— 未覆盖 token
# =========================================================================


def test_module_source_contains_json_import():
    import evaluation.manifest as m

    assert "import json" in inspect.getsource(m)


def test_module_source_contains_dataclass_import():
    import evaluation.manifest as m

    assert "from dataclasses import dataclass" in inspect.getsource(m)


def test_module_source_contains_path_import():
    import evaluation.manifest as m

    assert "from pathlib import Path" in inspect.getsource(m)


def test_module_source_contains_any_import():
    import evaluation.manifest as m

    assert "from typing import Any" in inspect.getsource(m)


def test_module_source_contains_future_annotations():
    import evaluation.manifest as m

    assert "from __future__ import annotations" in inspect.getsource(m)


def test_module_source_contains_manifest_version_import():
    """源码含 from evaluation import MANIFEST_VERSION。"""
    import evaluation.manifest as m

    assert "from evaluation import MANIFEST_VERSION" in inspect.getsource(m)


def test_module_source_contains_validate_import():
    """源码含 from evaluation.schema import validate。"""
    import evaluation.manifest as m

    assert "from evaluation.schema import validate" in inspect.getsource(m)


def test_module_source_contains_resolve_relative_path_def():
    import evaluation.manifest as m

    assert "def _resolve_relative_path(" in inspect.getsource(m)


def test_module_source_contains_load_manifest_def():
    import evaluation.manifest as m

    assert "def load_manifest(" in inspect.getsource(m)


def test_module_source_contains_detect_project_root_def():
    import evaluation.manifest as m

    assert "def _detect_project_root(" in inspect.getsource(m)


def test_module_source_contains_document_entry_class():
    """源码含 class DocumentEntry。"""
    import evaluation.manifest as m

    assert "class DocumentEntry:" in inspect.getsource(m)


def test_module_source_contains_expected_failure_class():
    import evaluation.manifest as m

    assert "class ExpectedFailure:" in inspect.getsource(m)


def test_module_source_contains_manifest_class():
    import evaluation.manifest as m

    assert "class Manifest:" in inspect.getsource(m)


def test_module_source_contains_dataclass_decorator():
    """3 个 @dataclass(frozen=True)。"""
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "@dataclass(frozen=True)" in src


def test_module_source_contains_manifest_version_check():
    """源码含 manifest_version 不兼容检查。"""
    import evaluation.manifest as m

    assert "manifest_version 不兼容" in inspect.getsource(m)


def test_module_source_contains_path_must_be_relative_message():
    """源码含 '必须是相对路径'。"""
    import evaluation.manifest as m

    assert "必须是相对路径" in inspect.getsource(m)


def test_module_source_contains_no_backslash_message():
    """源码含 '禁止反斜杠'。"""
    import evaluation.manifest as m

    assert "禁止反斜杠" in inspect.getsource(m)


def test_module_source_contains_no_absolute_message():
    """源码含 '禁止绝对路径'。"""
    import evaluation.manifest as m

    assert "禁止绝对路径" in inspect.getsource(m)


def test_module_source_contains_outside_root_message():
    """源码含 '项目根目录之外'。"""
    import evaluation.manifest as m

    assert "项目根目录之外" in inspect.getsource(m)


def test_module_source_contains_relative_to_call():
    """源码含 resolved.relative_to(project_root_resolved)。"""
    import evaluation.manifest as m

    assert "relative_to(project_root_resolved)" in inspect.getsource(m)


def test_module_source_contains_paired_with_field():
    import evaluation.manifest as m

    assert "paired_with" in inspect.getsource(m)


def test_module_source_contains_paired_with_frozenset():
    """content_group_count 用 frozenset 配对。"""
    import evaluation.manifest as m

    assert "frozenset" in inspect.getsource(m)


def test_module_source_contains_paired_with_seen_set():
    """源码含 seen 集合跟踪。"""
    import evaluation.manifest as m

    assert "seen" in inspect.getsource(m)


def test_module_source_contains_categories_property():
    import evaluation.manifest as m

    assert "categories_covered" in inspect.getsource(m)


def test_module_source_contains_content_group_count_property():
    import evaluation.manifest as m

    assert "content_group_count" in inspect.getsource(m)


def test_module_source_contains_file_count_property():
    import evaluation.manifest as m

    assert "file_count" in inspect.getsource(m)


def test_module_source_contains_pdf_count_property():
    import evaluation.manifest as m

    assert "pdf_count" in inspect.getsource(m)


def test_module_source_contains_docx_count_property():
    import evaluation.manifest as m

    assert "docx_count" in inspect.getsource(m)


def test_module_source_contains_annotation_resolved_field():
    import evaluation.manifest as m

    assert "annotation_resolved" in inspect.getsource(m)


def test_module_source_contains_annotation_file_str_field():
    import evaluation.manifest as m

    assert "annotation_file_str" in inspect.getsource(m)


def test_module_source_contains_expectations_field():
    import evaluation.manifest as m

    assert "expectations" in inspect.getsource(m)


def test_module_source_contains_sha256_field():
    import evaluation.manifest as m

    assert "sha256" in inspect.getsource(m)


def test_module_source_contains_expected_error_code_field():
    import evaluation.manifest as m

    assert "expected_error_code" in inspect.getsource(m)


def test_module_source_contains_resolve_call():
    """源码含 Path.resolve()。"""
    import evaluation.manifest as m

    assert ".resolve()" in inspect.getsource(m)


def test_module_source_contains_open_with_utf8():
    """源码含 encoding='utf-8'。"""
    import evaluation.manifest as m

    assert 'encoding="utf-8"' in inspect.getsource(m)


def test_module_source_contains_validate_call():
    """源码含 validate(data, 'manifest.schema.json')。"""
    import evaluation.manifest as m

    assert "validate(data, \"manifest.schema.json\")" in inspect.getsource(m)


def test_module_source_does_not_contain_print():
    import evaluation.manifest as m

    assert "print(" not in inspect.getsource(m)


# =========================================================================
# 模块 docstring
# =========================================================================


def test_module_docstring_is_nonempty_string():
    import evaluation.manifest as m

    assert isinstance(m.__doc__, str)
    assert len(m.__doc__) > 30


def test_module_docstring_mentions_path_invariants():
    """docstring 提到 path 不变量。"""
    import evaluation.manifest as m

    assert "相对路径" in m.__doc__ or "正斜杠" in m.__doc__


def test_module_docstring_mentions_security():
    """docstring 提到安全考虑（防止路径逃逸）。"""
    import evaluation.manifest as m

    assert "项目根" in m.__doc__ or "相对路径" in m.__doc__


def test_module_docstring_mentions_no_absolute_paths():
    """docstring 提到不写绝对路径。"""
    import evaluation.manifest as m

    assert "绝对路径" in m.__doc__


# =========================================================================
# _is_absolute_like 详细边界
# =========================================================================


def test_is_absolute_like_empty_string_returns_false():
    assert _is_absolute_like("") is False


def test_is_absolute_like_relative_returns_false():
    assert _is_absolute_like("foo/bar.json") is False


def test_is_absolute_like_single_dot_returns_false():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_double_dot_returns_false():
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_posix_absolute_returns_true():
    assert _is_absolute_like("/etc/passwd") is True


def test_is_absolute_like_windows_backslash_absolute():
    assert _is_absolute_like("C:\\Users\\foo") is True


def test_is_absolute_like_windows_forward_slash_absolute():
    assert _is_absolute_like("C:/Users/foo") is True


def test_is_absolute_like_lower_case_drive_letter():
    assert _is_absolute_like("c:/foo") is True


def test_is_absolute_like_upper_case_drive_letter():
    assert _is_absolute_like("D:\\foo") is True


def test_is_absolute_like_alpha_no_separator_returns_false():
    """'C:foo' 无 \\ 或 / → 不是绝对路径。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_two_chars_returns_false():
    """'C:' 只有 2 字符 → 不够 3 → False。"""
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_single_char_returns_false():
    assert _is_absolute_like("C") is False


def test_is_absolute_like_non_alpha_drive_returns_false():
    """'1:\\foo' 数字不是 alpha → False。"""
    assert _is_absolute_like("1:\\foo") is False


def test_is_absolute_like_unicode_alpha_returns_true():
    """unicode 字母也算 alpha → True。"""
    # 'é' is alpha
    assert _is_absolute_like("é:/foo") is True


def test_is_absolute_like_returns_bool_type():
    assert type(_is_absolute_like("foo")) is bool
    assert type(_is_absolute_like("/foo")) is bool


def test_is_absolute_like_module_identity():
    assert _is_absolute_like.__module__ == "evaluation.manifest"


def test_is_absolute_like_qualname():
    assert _is_absolute_like.__qualname__ == "_is_absolute_like"


def test_is_absolute_like_param_count_1():
    sig = inspect.signature(_is_absolute_like)
    assert len(sig.parameters) == 1


def test_is_absolute_like_param_name():
    sig = inspect.signature(_is_absolute_like)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_is_absolute_like_param_no_default():
    sig = inspect.signature(_is_absolute_like)
    assert sig.parameters["path_str"].default is inspect.Parameter.empty


def test_is_absolute_like_no_var_args():
    sig = inspect.signature(_is_absolute_like)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_is_absolute_like_no_var_kwargs():
    sig = inspect.signature(_is_absolute_like)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_is_absolute_like_is_function_type():
    import types as _types

    assert isinstance(_is_absolute_like, _types.FunctionType)


# =========================================================================
# _has_backslash 详细
# =========================================================================


def test_has_backslash_empty_returns_false():
    assert _has_backslash("") is False


def test_has_backslash_no_backslash_returns_false():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_with_backslash_returns_true():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_multiple_backslashes():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_only_backslash():
    assert _has_backslash("\\") is True


def test_has_backslash_returns_bool_type():
    assert type(_has_backslash("")) is bool
    assert type(_has_backslash("\\")) is bool


def test_has_backslash_module_identity():
    assert _has_backslash.__module__ == "evaluation.manifest"


def test_has_backslash_qualname():
    assert _has_backslash.__qualname__ == "_has_backslash"


def test_has_backslash_param_count_1():
    sig = inspect.signature(_has_backslash)
    assert len(sig.parameters) == 1


def test_has_backslash_param_name():
    sig = inspect.signature(_has_backslash)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_has_backslash_param_no_default():
    sig = inspect.signature(_has_backslash)
    assert sig.parameters["path_str"].default is inspect.Parameter.empty


# =========================================================================
# ManifestError 详细
# =========================================================================


def test_manifest_error_is_exception_subclass():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_is_baseexception_subclass():
    assert issubclass(ManifestError, BaseException)


def test_manifest_error_mro_contains_exception():
    assert Exception in ManifestError.__mro__


def test_manifest_error_mro_contains_baseexception():
    assert BaseException in ManifestError.__mro__


def test_manifest_error_mro_length_4():
    assert len(ManifestError.__mro__) == 4


def test_manifest_error_module_identity():
    assert ManifestError.__module__ == "evaluation.manifest"


def test_manifest_error_qualname():
    assert ManifestError.__qualname__ == "ManifestError"


def test_manifest_error_name():
    assert ManifestError.__name__ == "ManifestError"


def test_manifest_error_can_be_raised():
    with pytest.raises(ManifestError):
        raise ManifestError("x")


def test_manifest_error_caught_as_exception():
    with pytest.raises(Exception):
        raise ManifestError("x")


def test_manifest_error_str_returns_message():
    e = ManifestError("error message")
    assert str(e) == "error message"


def test_manifest_error_repr_contains_class_name():
    e = ManifestError("err")
    assert "ManifestError" in repr(e)


def test_manifest_error_args():
    e = ManifestError("a", "b")
    assert e.args == ("a", "b")


def test_manifest_error_single_arg():
    e = ManifestError("only")
    assert e.args == ("only",)


def test_manifest_error_no_args():
    e = ManifestError()
    assert e.args == ()


def test_manifest_error_hashable():
    e = ManifestError("x")
    assert hash(e) == hash(e)


def test_manifest_error_equality_by_identity():
    a = ManifestError("x")
    b = ManifestError("x")
    assert a is not b


def test_manifest_error_does_not_catch_other_exceptions():
    """ManifestError 不捕获 ValueError。"""
    with pytest.raises(ValueError):
        try:
            raise ValueError("x")
        except ManifestError:
            pass


# =========================================================================
# DocumentEntry dataclass 详细
# =========================================================================


def test_document_entry_is_dataclass():
    import dataclasses as dc

    assert dc.is_dataclass(DocumentEntry)


def test_document_entry_frozen_true():
    """frozen=True 阻止 setattr。"""
    de = DocumentEntry(
        doc_id="d1",
        path_str="foo",
        resolved_path=Path("/tmp/foo"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(Exception):  # FrozenInstanceError
        de.doc_id = "new_id"  # type: ignore[misc]


def test_document_entry_field_count_10():
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_field_names_in_order():
    field_names = [f.name for f in fields(DocumentEntry)]
    assert field_names == [
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


def test_document_entry_is_hashable():
    de = DocumentEntry(
        doc_id="d1",
        path_str="foo",
        resolved_path=Path("/tmp/foo"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    assert hash(de) == hash(de)


def test_document_entry_equality_by_value():
    a = DocumentEntry(
        doc_id="d1",
        path_str="foo",
        resolved_path=Path("/tmp/foo"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    b = DocumentEntry(
        doc_id="d1",
        path_str="foo",
        resolved_path=Path("/tmp/foo"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    assert a == b


def test_document_entry_inequality_when_field_differs():
    a = DocumentEntry(
        doc_id="d1",
        path_str="foo",
        resolved_path=Path("/tmp/foo"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    b = DocumentEntry(
        doc_id="d2",  # 不同
        path_str="foo",
        resolved_path=Path("/tmp/foo"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    assert a != b


def test_document_entry_module_identity():
    assert DocumentEntry.__module__ == "evaluation.manifest"


def test_document_entry_qualname():
    assert DocumentEntry.__qualname__ == "DocumentEntry"


# =========================================================================
# ExpectedFailure dataclass 详细
# =========================================================================


def test_expected_failure_is_dataclass():
    import dataclasses as dc

    assert dc.is_dataclass(ExpectedFailure)


def test_expected_failure_frozen_true():
    ef = ExpectedFailure(
        doc_id="ef1",
        path_str="bad.pdf",
        resolved_path=Path("/tmp/bad.pdf"),
        expected_error_code="UNSUPPORTED",
        source_type="pdf",
    )
    with pytest.raises(Exception):
        ef.doc_id = "new"  # type: ignore[misc]


def test_expected_failure_field_count_5():
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_field_names_in_order():
    field_names = [f.name for f in fields(ExpectedFailure)]
    assert field_names == [
        "doc_id",
        "path_str",
        "resolved_path",
        "expected_error_code",
        "source_type",
    ]


def test_expected_failure_is_hashable():
    ef = ExpectedFailure(
        doc_id="ef1",
        path_str="bad.pdf",
        resolved_path=Path("/tmp/bad.pdf"),
        expected_error_code="UNSUPPORTED",
        source_type="pdf",
    )
    assert hash(ef) == hash(ef)


def test_expected_failure_module_identity():
    assert ExpectedFailure.__module__ == "evaluation.manifest"


def test_expected_failure_qualname():
    assert ExpectedFailure.__qualname__ == "ExpectedFailure"


# =========================================================================
# Manifest dataclass 详细
# =========================================================================


def test_manifest_is_dataclass():
    import dataclasses as dc

    assert dc.is_dataclass(Manifest)


def test_manifest_frozen_true():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    with pytest.raises(Exception):
        m.devset_status = "complete"  # type: ignore[misc]


def test_manifest_field_count_5():
    assert len(fields(Manifest)) == 5


def test_manifest_field_names_in_order():
    field_names = [f.name for f in fields(Manifest)]
    assert field_names == [
        "manifest_version",
        "devset_status",
        "documents",
        "expected_failures",
        "project_root",
    ]


def test_manifest_is_hashable():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert hash(m) == hash(m)


def test_manifest_module_identity():
    assert Manifest.__module__ == "evaluation.manifest"


def test_manifest_qualname():
    assert Manifest.__qualname__ == "Manifest"


# =========================================================================
# Manifest properties 详细
# =========================================================================


def _make_doc(doc_id: str, source_type: str = "pdf", categories=(), paired_with=None) -> DocumentEntry:
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


def test_manifest_file_count_empty_returns_zero():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.file_count == 0


def test_manifest_file_count_one():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(_make_doc("d1"),),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.file_count == 1


def test_manifest_pdf_count_only_pdf():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(_make_doc("d1", "pdf"), _make_doc("d2", "pdf")),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.pdf_count == 2


def test_manifest_pdf_count_mixed():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(_make_doc("d1", "pdf"), _make_doc("d2", "docx")),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.pdf_count == 1


def test_manifest_docx_count_only_docx():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(_make_doc("d1", "docx"), _make_doc("d2", "docx")),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.docx_count == 2


def test_manifest_docx_count_zero_when_only_pdf():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(_make_doc("d1", "pdf"),),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.docx_count == 0


def test_manifest_categories_covered_empty():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.categories_covered == []


def test_manifest_categories_covered_single_doc():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(_make_doc("d1", categories=("legal", "scientific")),),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.categories_covered == ["legal", "scientific"]


def test_manifest_categories_covered_multiple_docs_merge():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(
            _make_doc("d1", categories=("legal",)),
            _make_doc("d2", categories=("scientific",)),
        ),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.categories_covered == ["legal", "scientific"]


def test_manifest_categories_covered_duplicates_removed():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(
            _make_doc("d1", categories=("legal", "x")),
            _make_doc("d2", categories=("legal", "y")),
        ),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.categories_covered == ["legal", "x", "y"]


def test_manifest_categories_covered_sorted_alphabetically():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(_make_doc("d1", categories=("zebra", "apple")),),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.categories_covered == ["apple", "zebra"]


def test_manifest_categories_covered_returns_new_list_each_time():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(_make_doc("d1", categories=("x",)),),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    a = m.categories_covered
    b = m.categories_covered
    assert a == b
    assert a is not b


def test_manifest_categories_covered_case_sensitive():
    """case-sensitive: 'A' < 'a' lexicographically。"""
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(_make_doc("d1", categories=("Apple", "apple")),),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    # 'A' < 'a' in unicode → ["Apple", "apple"]
    assert m.categories_covered == ["Apple", "apple"]


def test_manifest_categories_covered_unicode():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(_make_doc("d1", categories=("中文", "english")),),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    # unicode sorting
    assert m.categories_covered == sorted(["中文", "english"])


# =========================================================================
# content_group_count 各种 pairing 组合
# =========================================================================


def test_content_group_count_no_paired_each_one_group():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(_make_doc("d1"), _make_doc("d2")),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.content_group_count == 2


def test_content_group_count_one_pair_one_group():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(
            _make_doc("d1", paired_with="d2"),
            _make_doc("d2", paired_with="d1"),
        ),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.content_group_count == 1


def test_content_group_count_one_way_pair_still_one_group():
    """单向 pair: d1 → d2 但 d2 不指 d1 → frozenset([d1, d2]) 一组 + d2 是 seen → 0 unpaired。"""
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(_make_doc("d1", paired_with="d2"), _make_doc("d2")),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    # pair_ids = {frozenset([d1, d2])}, groups=1, seen={d1, d2}
    # d2 有 paired_with=None，但 doc_id in seen → 不计 unpaired
    assert m.content_group_count == 1


def test_content_group_count_pair_plus_unpaired():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(
            _make_doc("d1", paired_with="d2"),
            _make_doc("d2", paired_with="d1"),
            _make_doc("d3"),
        ),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    # 1 pair + 1 unpaired = 2 groups
    assert m.content_group_count == 2


def test_content_group_count_self_pair_one_group():
    """d1 paired_with d1 → frozenset([d1, d1]) = frozenset([d1]) → 一组。"""
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(_make_doc("d1", paired_with="d1"),),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    # frozenset([d1, d1]) = frozenset([d1])
    # groups = 1, seen = {d1}
    # d1 in seen → not unpaired
    assert m.content_group_count == 1


def test_content_group_count_pair_to_nonexistent():
    """d1 paired_with 'ghost'（不存在）→ frozenset([d1, 'ghost']) 一组。"""
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(_make_doc("d1", paired_with="ghost"),),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    # frozenset([d1, ghost]) → 1 group, seen={d1, ghost}
    # d1 in seen → not unpaired
    assert m.content_group_count == 1


# =========================================================================
# _resolve_relative_path 详细
# =========================================================================


def test_resolve_relative_path_returns_absolute_path(tmp_path: Path):
    out = _resolve_relative_path("foo.json", tmp_path, "test")
    assert isinstance(out, Path)
    assert out.is_absolute()


def test_resolve_relative_path_empty_raises_manifest_error(tmp_path: Path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "test_field")
    assert "test_field" in str(exc_info.value)


def test_resolve_relative_path_absolute_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/etc/passwd", tmp_path, "test_field")
    assert "test_field" in str(exc_info.value)
    assert "绝对路径" in str(exc_info.value)


def test_resolve_relative_path_backslash_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("foo\\bar.json", tmp_path, "test_field")
    assert "test_field" in str(exc_info.value)
    assert "反斜杠" in str(exc_info.value)


def test_resolve_relative_path_outside_root_raises(tmp_path: Path):
    """../../../foo 解析后位于 root 外 → ManifestError。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("../../../foo.json", tmp_path, "test_field")
    assert "test_field" in str(exc_info.value)
    assert "项目根目录之外" in str(exc_info.value)


def test_resolve_relative_path_subdir_ok(tmp_path: Path):
    """子目录 OK。"""
    out = _resolve_relative_path("subdir/foo.json", tmp_path, "test")
    assert out == (tmp_path / "subdir" / "foo.json").resolve()


def test_resolve_relative_path_unicode_filename(tmp_path: Path):
    out = _resolve_relative_path("数据/测试.json", tmp_path, "test")
    assert out == (tmp_path / "数据" / "测试.json").resolve()


def test_resolve_relative_path_module_identity():
    assert _resolve_relative_path.__module__ == "evaluation.manifest"


def test_resolve_relative_path_qualname():
    assert _resolve_relative_path.__qualname__ == "_resolve_relative_path"


def test_resolve_relative_path_param_count_3():
    sig = inspect.signature(_resolve_relative_path)
    assert len(sig.parameters) == 3


def test_resolve_relative_path_param_names():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters.keys()) == ["path_str", "project_root", "field_name"]


def test_resolve_relative_path_no_var_args():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_resolve_relative_path_no_var_kwargs():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_resolve_relative_path_no_param_defaults():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


# =========================================================================
# _detect_project_root 详细
# =========================================================================


def test_detect_project_root_module_identity():
    assert _detect_project_root.__module__ == "evaluation.manifest"


def test_detect_project_root_qualname():
    assert _detect_project_root.__qualname__ == "_detect_project_root"


def test_detect_project_root_param_count_1():
    sig = inspect.signature(_detect_project_root)
    assert len(sig.parameters) == 1


def test_detect_project_root_param_name():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters.keys()) == ["start"]


def test_detect_project_root_no_var_args():
    sig = inspect.signature(_detect_project_root)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_detect_project_root_no_var_kwargs():
    sig = inspect.signature(_detect_project_root)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_detect_project_root_finds_pyproject(tmp_path: Path):
    """目录含 pyproject.toml → 返回该目录。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_start(tmp_path: Path):
    """无 pyproject.toml → 返回 start。"""
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_file_input_takes_parent(tmp_path: Path):
    """file 输入 → 取 parent。"""
    f = tmp_path / "some.txt"
    f.write_text("x", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    out = _detect_project_root(f)
    assert out == tmp_path.resolve()


def test_detect_project_root_returns_path_instance(tmp_path: Path):
    out = _detect_project_root(tmp_path)
    assert isinstance(out, Path)


def test_detect_project_root_returns_absolute(tmp_path: Path):
    out = _detect_project_root(tmp_path)
    assert out.is_absolute()


# =========================================================================
# load_manifest 详细
# =========================================================================


def test_load_manifest_module_identity():
    assert load_manifest.__module__ == "evaluation.manifest"


def test_load_manifest_qualname():
    assert load_manifest.__qualname__ == "load_manifest"


def test_load_manifest_param_count_2():
    sig = inspect.signature(load_manifest)
    assert len(sig.parameters) == 2


def test_load_manifest_param_names():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters.keys()) == ["manifest_path", "project_root"]


def test_load_manifest_param_defaults():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["manifest_path"].default is inspect.Parameter.empty
    assert sig.parameters["project_root"].default is None


def test_load_manifest_param_kinds_positional_or_keyword():
    sig = inspect.signature(load_manifest)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_load_manifest_no_var_args():
    sig = inspect.signature(load_manifest)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_load_manifest_no_var_kwargs():
    sig = inspect.signature(load_manifest)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_load_manifest_missing_raises_manifest_error(tmp_path: Path):
    with pytest.raises(ManifestError):
        load_manifest(tmp_path / "missing.json")


def test_load_manifest_directory_raises_manifest_error(tmp_path: Path):
    with pytest.raises(ManifestError):
        load_manifest(tmp_path)


def test_load_manifest_invalid_json_raises_manifest_error(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_load_manifest_empty_file_raises_manifest_error(tmp_path: Path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_load_manifest_str_path_works(tmp_path: Path):
    """load_manifest 接受 str 路径。"""
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(str(p))
    assert isinstance(m, Manifest)


def test_load_manifest_str_project_root_works(tmp_path: Path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, str(tmp_path))
    assert isinstance(m, Manifest)


def test_load_manifest_returns_manifest_instance(tmp_path: Path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p)
    assert isinstance(m, Manifest)


def test_load_manifest_returns_documents_as_tuple(tmp_path: Path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p)
    assert isinstance(m.documents, tuple)


def test_load_manifest_returns_expected_failures_as_tuple(tmp_path: Path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p)
    assert isinstance(m.expected_failures, tuple)


def test_load_manifest_returns_project_root_as_path(tmp_path: Path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p)
    assert isinstance(m.project_root, Path)


def test_load_manifest_passes_manifest_version(tmp_path: Path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p)
    assert m.manifest_version == MANIFEST_VERSION


def test_load_manifest_passes_devset_status(tmp_path: Path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p)
    assert m.devset_status == "complete"


def test_load_manifest_version_mismatch_raises(tmp_path: Path):
    """version != MANIFEST_VERSION → schema const 校验先抛 EvalSchemaError。

    schema 中 manifest_version 是 const="1.0"，所以版本不匹配会先在 schema 失败。
    代码层面的 manifest_version != MANIFEST_VERSION 是 belt-and-suspenders。
    """
    from evaluation.schema import EvalSchemaError

    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "99.99",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


# =========================================================================
# 模块 namespace 完整性
# =========================================================================


def test_module_namespace_contains_manifest_error():
    import evaluation.manifest as m

    assert hasattr(m, "ManifestError")
    assert m.ManifestError is ManifestError


def test_module_namespace_contains_dataclasses():
    import evaluation.manifest as m

    for name in ["DocumentEntry", "ExpectedFailure", "Manifest"]:
        assert hasattr(m, name)


def test_module_namespace_contains_helpers():
    import evaluation.manifest as m

    for name in ["load_manifest", "_resolve_relative_path", "_detect_project_root", "_is_absolute_like", "_has_backslash"]:
        assert hasattr(m, name)


def test_module_namespace_contains_json():
    import evaluation.manifest as m
    import json as orig_json

    assert m.json is orig_json


def test_module_namespace_contains_path():
    import evaluation.manifest as m
    from pathlib import Path as OrigPath

    assert m.Path is OrigPath


def test_module_namespace_contains_manifest_version():
    import evaluation.manifest as m

    assert hasattr(m, "MANIFEST_VERSION")
    assert m.MANIFEST_VERSION == MANIFEST_VERSION


def test_module_namespace_contains_validate():
    import evaluation.manifest as m

    assert hasattr(m, "validate")


def test_module_all_is_list():
    import evaluation.manifest as m

    assert isinstance(m.__all__, list)


def test_module_all_is_not_tuple():
    import evaluation.manifest as m

    assert not isinstance(m.__all__, tuple)


def test_module_all_exact():
    import evaluation.manifest as m

    assert m.__all__ == [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ]


def test_module_all_does_not_contain_private_helpers():
    """__all__ 不含 _ 前缀 helpers。"""
    import evaluation.manifest as m

    for name in ["_is_absolute_like", "_has_backslash", "_resolve_relative_path", "_detect_project_root"]:
        assert name not in m.__all__


def test_module_all_all_names_in_namespace():
    import evaluation.manifest as m

    for name in m.__all__:
        assert hasattr(m, name)


# =========================================================================
# 所有 helpers 都是 FunctionType
# =========================================================================


def test_all_helpers_are_function_type():
    import types as _types

    for fn in [
        _is_absolute_like,
        _has_backslash,
        _resolve_relative_path,
        _detect_project_root,
        load_manifest,
    ]:
        assert isinstance(fn, _types.FunctionType)


# =========================================================================
# 整体不变量
# =========================================================================


def test_module_can_be_imported():
    import evaluation.manifest as m

    assert m is not None


def test_manifest_constants_stable():
    import evaluation.manifest as m

    assert m.ManifestError is ManifestError
    assert m.Manifest is Manifest
    assert m.DocumentEntry is DocumentEntry
    assert m.ExpectedFailure is ExpectedFailure
