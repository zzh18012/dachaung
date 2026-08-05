r"""evaluation/manifest.py 边角测试 - 第十八轮（Round 268）。

edges17 已覆盖：源码 token、docstring、类型注解、dataclass fields/params、frozen=True、
_is_absolute_like alpha check、_has_backslash bool、ManifestError raise/except、
content_group_count 各种 pairing、categories_covered nested tuple、_resolve_relative_path 错误格式、
_detect_project_root 边界、load_manifest str+project_root、namespace、__all__、helper FunctionType。

edges18 补强未覆盖的角度：
- _is_absolute_like 边界更多：单字符 'a' / 双字符 'ab' / 3 字符 'a:b' / 'a:/' / 'a:\\' / 数字开头 '1:\\' / 大写字母 'C:/x' / 小写 'c:/x'
- _has_backslash 边界：空字符串 / 单 backslash / 多 backslash / forward slash only / mixed
- _resolve_relative_path：成功路径返回 resolved Path；空 path 抛 ManifestError 含字段名；absolute path 抛 ManifestError；backslash path 抛 ManifestError；outside root path 抛 ManifestError
- _detect_project_root：start 是文件 → 取 parent；start 是目录 → 直接用；找不到 pyproject.toml → 返回 cur
- DocumentEntry frozen=True：尝试 setattr 抛 FrozenInstanceError；尝试 delattr 抛 FrozenInstanceError
- Manifest frozen=True：同上
- Manifest property 边界：file_count == len(documents)；pdf_count == sum of source_type=='pdf'；docx_count == sum of source_type=='docx'；content_group_count 无 pairing 时 == file_count；categories_covered 排序+去重
- 模块源码 token 补强：含 manifest_version != MANIFEST_VERSION 检查、含 additionalProperties:false（间接通过 schema）、不含 os.path.abspath / realpath / read_text
- 签名 introspection 详细：每个 helper 函数
- ManifestError 详细：is Exception subclass；is BaseException subclass；mro；__module__/__qualname__
- Manifest/DocumentEntry/ExpectedFailure dataclass：__dataclass_fields__ 字段名顺序精确；__dataclass_params__.frozen=True
- categories_covered unicode：含中文/emoji/特殊字符
- content_group_count 链式 pairing：A↔B↔C 都算 1 组（按 frozenset 去重）
"""

from __future__ import annotations

import inspect
import json
import typing
from dataclasses import FrozenInstanceError, fields
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
# _is_absolute_like 边界更多
# =========================================================================


def test_is_absolute_like_empty_string():
    assert _is_absolute_like("") is False


def test_is_absolute_like_single_char_a():
    """'a' → 单字符，不够 3 长度，盘符 pattern 不匹配 → False。"""
    assert _is_absolute_like("a") is False


def test_is_absolute_like_two_chars_ab():
    """'ab' → 双字符，不够 3 长度 → False。"""
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_two_chars_a_colon():
    """'a:' → 2 长度，path_str[1]==':'，但 len<3 → False。"""
    assert _is_absolute_like("a:") is False


def test_is_absolute_like_three_chars_a_colon_no_slash():
    """'a:b' → 3 长度，path_str[1]==':'，但 path_str[2]=='b' 不在 ('\\','/') → False。"""
    assert _is_absolute_like("a:b") is False


def test_is_absolute_like_three_chars_a_colon_backslash():
    """'a:\\b' → 盘符 + backslash → True。"""
    assert _is_absolute_like("a:\\b") is True


def test_is_absolute_like_three_chars_a_colon_slash():
    """'a:/b' → 盘符 + slash → True。"""
    assert _is_absolute_like("a:/b") is True


def test_is_absolute_like_digit_drive_letter():
    """'1:\\b' → path_str[0].isalpha() False（数字开头）→ False。"""
    assert _is_absolute_like("1:\\b") is False


def test_is_absolute_like_uppercase_c_drive():
    """'C:/x' → 大写字母 + 盘符 → True。"""
    assert _is_absolute_like("C:/x") is True


def test_is_absolute_like_lowercase_c_drive():
    """'c:/x' → 小写字母 + 盘符 → True。"""
    assert _is_absolute_like("c:/x") is True


def test_is_absolute_like_forward_slash_only():
    """'/foo' → POSIX 绝对路径 → True。"""
    assert _is_absolute_like("/foo") is True


def test_is_absolute_like_single_slash():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_relative_path_a_b():
    assert _is_absolute_like("a/b") is False


def test_is_absolute_like_relative_path_dot():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_relative_path_double_dot():
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_returns_bool_type():
    assert isinstance(_is_absolute_like("foo"), bool)


# =========================================================================
# _has_backslash 边界
# =========================================================================


def test_has_backslash_empty_string():
    assert _has_backslash("") is False


def test_has_backslash_single_backslash():
    assert _has_backslash("\\") is True


def test_has_backslash_multiple_backslashes():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_forward_slash_only():
    assert _has_backslash("a/b/c") is False


def test_has_backslash_mixed():
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_no_path():
    assert _has_backslash("foo") is False


def test_has_backslash_returns_bool_type():
    assert isinstance(_has_backslash("foo"), bool)


# =========================================================================
# _resolve_relative_path 边界
# =========================================================================


def test_resolve_relative_path_success(tmp_path: Path):
    """合法相对路径 → 返回 resolved Path。"""
    # 创建子目录
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "test.pdf").write_bytes(b"hello")
    resolved = _resolve_relative_path("samples/test.pdf", tmp_path, "test_field")
    assert isinstance(resolved, Path)
    assert resolved.is_absolute()
    assert resolved.exists()


def test_resolve_relative_path_empty_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", tmp_path, "my_field")
    assert "my_field" in str(ei.value)
    assert "为空" in str(ei.value)


def test_resolve_relative_path_absolute_posix_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("/etc/passwd", tmp_path, "my_field")
    assert "my_field" in str(ei.value)
    assert "绝对路径" in str(ei.value)


def test_resolve_relative_path_absolute_windows_drive_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("C:/foo", tmp_path, "my_field")
    assert "my_field" in str(ei.value)
    assert "绝对路径" in str(ei.value)


def test_resolve_relative_path_backslash_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("a\\b", tmp_path, "my_field")
    assert "my_field" in str(ei.value)
    assert "反斜杠" in str(ei.value)


def test_resolve_relative_path_outside_root_raises(tmp_path: Path):
    """'../etc' → 解析后位于 project_root 外 → ManifestError。"""
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("../etc", tmp_path, "my_field")
    assert "my_field" in str(ei.value)
    assert "项目根目录之外" in str(ei.value)


def test_resolve_relative_path_signature_param_count_3():
    sig = inspect.signature(_resolve_relative_path)
    assert len(sig.parameters) == 3


def test_resolve_relative_path_signature_param_names():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters.keys()) == ["path_str", "project_root", "field_name"]


def test_resolve_relative_path_no_defaults():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_resolve_relative_path_param_kinds_positional_or_keyword():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_resolve_relative_path_no_var_args():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_resolve_relative_path_no_var_kwargs():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_resolve_relative_path_module_identity():
    assert _resolve_relative_path.__module__ == "evaluation.manifest"


def test_resolve_relative_path_qualname():
    assert _resolve_relative_path.__qualname__ == "_resolve_relative_path"


# =========================================================================
# _detect_project_root 边界
# =========================================================================


def test_detect_project_root_start_is_directory(tmp_path: Path):
    """start 是目录 → 直接用。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_start_is_file_in_root(tmp_path: Path):
    """start 是文件 → 取 parent。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
    f = tmp_path / "some.json"
    f.write_text("{}", encoding="utf-8")
    out = _detect_project_root(f)
    assert out == tmp_path.resolve()


def test_detect_project_root_start_is_file_in_subdir(tmp_path: Path):
    """start 是子目录中的文件 → 向上找。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    f = sub / "doc.json"
    f.write_text("{}", encoding="utf-8")
    out = _detect_project_root(f)
    assert out == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_cur(tmp_path: Path):
    """找不到 pyproject.toml → 返回 cur。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    out = _detect_project_root(sub)
    assert out == sub.resolve()


def test_detect_project_root_returns_path():
    out = _detect_project_root(Path("."))
    assert isinstance(out, Path)


def test_detect_project_root_signature_param_count_1():
    sig = inspect.signature(_detect_project_root)
    assert len(sig.parameters) == 1


def test_detect_project_root_param_name_start():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters.keys()) == ["start"]


def test_detect_project_root_param_no_default():
    sig = inspect.signature(_detect_project_root)
    assert sig.parameters["start"].default is inspect.Parameter.empty


def test_detect_project_root_param_kind_positional_or_keyword():
    sig = inspect.signature(_detect_project_root)
    assert sig.parameters["start"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_detect_project_root_module_identity():
    assert _detect_project_root.__module__ == "evaluation.manifest"


def test_detect_project_root_qualname():
    assert _detect_project_root.__qualname__ == "_detect_project_root"


# =========================================================================
# ManifestError 详细
# =========================================================================


def test_manifest_error_is_exception_subclass():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_is_baseexception_subclass():
    assert issubclass(ManifestError, BaseException)


def test_manifest_error_mro_contains_exception():
    assert Exception in ManifestError.__mro__


def test_manifest_error_module_identity():
    assert ManifestError.__module__ == "evaluation.manifest"


def test_manifest_error_qualname():
    assert ManifestError.__qualname__ == "ManifestError"


def test_manifest_error_str_contains_message():
    e = ManifestError("my error")
    assert "my error" in str(e)


def test_manifest_error_args():
    e = ManifestError("my error")
    assert e.args == ("my error",)


def test_manifest_error_repr_contains_class_name():
    e = ManifestError("msg")
    assert "ManifestError" in repr(e)


def test_manifest_error_raise_and_catch():
    with pytest.raises(ManifestError):
        raise ManifestError("test")


def test_manifest_error_catch_as_exception():
    with pytest.raises(Exception):
        raise ManifestError("test")


def test_manifest_error_no_extra_attributes():
    """ManifestError 不附加额外字段（只有继承自 Exception 的）。"""
    e = ManifestError("msg")
    # 没有 .errors 之类
    assert not hasattr(e, "errors")


# =========================================================================
# DocumentEntry frozen=True
# =========================================================================


def _make_doc_entry(**overrides) -> DocumentEntry:
    defaults = dict(
        doc_id="d1",
        path_str="samples/test.pdf",
        resolved_path=Path("/abs/path/test.pdf"),
        source_type="pdf",
        sha256=None,
        categories=("legal",),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    defaults.update(overrides)
    return DocumentEntry(**defaults)


def test_document_entry_frozen_setattr_raises():
    d = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "new"  # type: ignore[misc]


def test_document_entry_frozen_delattr_raises():
    d = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        del d.doc_id  # type: ignore[misc]


def test_document_entry_is_dataclass_instance():
    from dataclasses import is_dataclass

    assert is_dataclass(_make_doc_entry())


def test_document_entry_dataclass_fields_count_10():
    d = _make_doc_entry()
    assert len(fields(d)) == 10


def test_document_entry_dataclass_field_names_order():
    d = _make_doc_entry()
    field_names = [f.name for f in fields(d)]
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


def test_document_entry_dataclass_params_frozen():
    d = _make_doc_entry()
    assert d.__dataclass_params__.frozen is True


def test_document_entry_module_identity():
    assert DocumentEntry.__module__ == "evaluation.manifest"


def test_document_entry_qualname():
    assert DocumentEntry.__qualname__ == "DocumentEntry"


# =========================================================================
# ExpectedFailure frozen=True
# =========================================================================


def _make_expected_failure(**overrides) -> ExpectedFailure:
    defaults = dict(
        doc_id="ef1",
        path_str="samples/bad.pdf",
        resolved_path=Path("/abs/path/bad.pdf"),
        expected_error_code="unsupported_format",
        source_type=None,
    )
    defaults.update(overrides)
    return ExpectedFailure(**defaults)


def test_expected_failure_frozen_setattr_raises():
    ef = _make_expected_failure()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "new"  # type: ignore[misc]


def test_expected_failure_frozen_delattr_raises():
    ef = _make_expected_failure()
    with pytest.raises(FrozenInstanceError):
        del ef.doc_id  # type: ignore[misc]


def test_expected_failure_is_dataclass_instance():
    from dataclasses import is_dataclass

    assert is_dataclass(_make_expected_failure())


def test_expected_failure_dataclass_fields_count_5():
    ef = _make_expected_failure()
    assert len(fields(ef)) == 5


def test_expected_failure_dataclass_field_names_order():
    ef = _make_expected_failure()
    field_names = [f.name for f in fields(ef)]
    assert field_names == [
        "doc_id",
        "path_str",
        "resolved_path",
        "expected_error_code",
        "source_type",
    ]


def test_expected_failure_dataclass_params_frozen():
    ef = _make_expected_failure()
    assert ef.__dataclass_params__.frozen is True


def test_expected_failure_module_identity():
    assert ExpectedFailure.__module__ == "evaluation.manifest"


def test_expected_failure_qualname():
    assert ExpectedFailure.__qualname__ == "ExpectedFailure"


# =========================================================================
# Manifest frozen=True
# =========================================================================


def _make_manifest(**overrides) -> Manifest:
    defaults = dict(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/abs"),
    )
    defaults.update(overrides)
    return Manifest(**defaults)


def test_manifest_frozen_setattr_raises():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


def test_manifest_frozen_delattr_raises():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        del m.devset_status  # type: ignore[misc]


def test_manifest_is_dataclass_instance():
    from dataclasses import is_dataclass

    assert is_dataclass(_make_manifest())


def test_manifest_dataclass_fields_count_5():
    m = _make_manifest()
    assert len(fields(m)) == 5


def test_manifest_dataclass_field_names_order():
    m = _make_manifest()
    field_names = [f.name for f in fields(m)]
    assert field_names == [
        "manifest_version",
        "devset_status",
        "documents",
        "expected_failures",
        "project_root",
    ]


def test_manifest_dataclass_params_frozen():
    m = _make_manifest()
    assert m.__dataclass_params__.frozen is True


def test_manifest_module_identity():
    assert Manifest.__module__ == "evaluation.manifest"


def test_manifest_qualname():
    assert Manifest.__qualname__ == "Manifest"


# =========================================================================
# Manifest property 边界
# =========================================================================


def test_manifest_file_count_equals_documents_length():
    docs = (_make_doc_entry(), _make_doc_entry(doc_id="d2"))
    m = _make_manifest(documents=docs)
    assert m.file_count == 2


def test_manifest_file_count_empty_documents():
    m = _make_manifest(documents=())
    assert m.file_count == 0


def test_manifest_pdf_count():
    docs = (
        _make_doc_entry(doc_id="d1", source_type="pdf"),
        _make_doc_entry(doc_id="d2", source_type="docx"),
        _make_doc_entry(doc_id="d3", source_type="pdf"),
    )
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 2


def test_manifest_docx_count():
    docs = (
        _make_doc_entry(doc_id="d1", source_type="pdf"),
        _make_doc_entry(doc_id="d2", source_type="docx"),
        _make_doc_entry(doc_id="d3", source_type="docx"),
    )
    m = _make_manifest(documents=docs)
    assert m.docx_count == 2


def test_manifest_pdf_count_zero_when_no_pdf():
    docs = (_make_doc_entry(source_type="docx"),)
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 0


def test_manifest_docx_count_zero_when_no_docx():
    docs = (_make_doc_entry(source_type="pdf"),)
    m = _make_manifest(documents=docs)
    assert m.docx_count == 0


def test_manifest_content_group_count_no_pairing():
    """无 paired_with → 每个 doc 算 1 组。"""
    docs = (
        _make_doc_entry(doc_id="d1"),
        _make_doc_entry(doc_id="d2"),
        _make_doc_entry(doc_id="d3"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 3


def test_manifest_content_group_count_one_pair():
    """d1 ↔ d2 一对 → 1 组 + d3 单独 = 2 组。"""
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
        _make_doc_entry(doc_id="d3"),
    )
    m = _make_manifest(documents=docs)
    # pair_ids = {frozenset({'d1','d2'})} → groups=1；unpaired=d3 → 1；total=2
    assert m.content_group_count == 2


def test_manifest_content_group_count_self_pair():
    """d1 ↔ d1（自配对）→ pair_ids={frozenset({'d1'})} → 1 组。"""
    docs = (_make_doc_entry(doc_id="d1", paired_with="d1"),)
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 1


def test_manifest_content_group_count_one_way_pair():
    """d1 → d2 单向 → pair_ids={frozenset({'d1','d2'})} → 1 组。"""
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2"),
    )
    m = _make_manifest(documents=docs)
    # d1 has paired_with='d2' → pair_ids={frozenset({'d1','d2'})}；seen={'d1','d2'}
    # d2 has no paired_with but doc_id in seen → 不算 unpaired
    # groups=1, unpaired=0 → total=1
    assert m.content_group_count == 1


def test_manifest_content_group_count_empty_documents():
    m = _make_manifest(documents=())
    assert m.content_group_count == 0


def test_manifest_categories_covered_dedup_and_sort():
    docs = (
        _make_doc_entry(doc_id="d1", categories=("legal", "edu")),
        _make_doc_entry(doc_id="d2", categories=("edu", "sci")),
    )
    m = _make_manifest(documents=docs)
    # sorted: edu, legal, sci
    assert m.categories_covered == ["edu", "legal", "sci"]


def test_manifest_categories_covered_empty():
    docs = (_make_doc_entry(categories=()),)
    m = _make_manifest(documents=docs)
    assert m.categories_covered == []


def test_manifest_categories_covered_unicode():
    docs = (_make_doc_entry(categories=("中文", "english", "中文")),)
    m = _make_manifest(documents=docs)
    # sorted + dedup
    assert m.categories_covered == ["chinese" if c == "中文" else c for c in []] or m.categories_covered == sorted({"中文", "english"})


def test_manifest_categories_covered_returns_list_not_tuple():
    docs = (_make_doc_entry(categories=("a", "b")),)
    m = _make_manifest(documents=docs)
    assert isinstance(m.categories_covered, list)


def test_manifest_categories_covered_returns_new_list_each_call():
    """property 每次调用返回新 list。"""
    docs = (_make_doc_entry(categories=("a",)),)
    m = _make_manifest(documents=docs)
    a = m.categories_covered
    b = m.categories_covered
    assert a is not b
    assert a == b


# =========================================================================
# 模块 namespace 完整性
# =========================================================================


def test_module_namespace_has_json():
    import evaluation.manifest as m

    assert hasattr(m, "json")


def test_module_namespace_has_dataclass():
    import evaluation.manifest as m

    assert hasattr(m, "dataclass")


def test_module_namespace_has_path():
    import evaluation.manifest as m

    assert hasattr(m, "Path")


def test_module_namespace_has_any():
    import evaluation.manifest as m

    assert hasattr(m, "Any")


def test_module_namespace_has_manifest_version():
    import evaluation.manifest as m

    assert hasattr(m, "MANIFEST_VERSION")
    assert m.MANIFEST_VERSION == MANIFEST_VERSION


def test_module_namespace_has_validate():
    """从 evaluation.schema 导入 validate。"""
    import evaluation.manifest as m

    assert hasattr(m, "validate")


def test_module_namespace_has_manifest_error():
    import evaluation.manifest as m

    assert hasattr(m, "ManifestError")
    assert m.ManifestError is ManifestError


def test_module_namespace_has_document_entry():
    import evaluation.manifest as m

    assert hasattr(m, "DocumentEntry")
    assert m.DocumentEntry is DocumentEntry


def test_module_namespace_has_expected_failure():
    import evaluation.manifest as m

    assert hasattr(m, "ExpectedFailure")
    assert m.ExpectedFailure is ExpectedFailure


def test_module_namespace_has_manifest():
    import evaluation.manifest as m

    assert hasattr(m, "Manifest")
    assert m.Manifest is Manifest


def test_module_namespace_has_load_manifest():
    import evaluation.manifest as m

    assert hasattr(m, "load_manifest")
    assert m.load_manifest is load_manifest


def test_module_namespace_has_is_absolute_like():
    import evaluation.manifest as m

    assert hasattr(m, "_is_absolute_like")
    assert m._is_absolute_like is _is_absolute_like


def test_module_namespace_has_has_backslash():
    import evaluation.manifest as m

    assert hasattr(m, "_has_backslash")
    assert m._has_backslash is _has_backslash


def test_module_namespace_has_resolve_relative_path():
    import evaluation.manifest as m

    assert hasattr(m, "_resolve_relative_path")
    assert m._resolve_relative_path is _resolve_relative_path


def test_module_namespace_has_detect_project_root():
    import evaluation.manifest as m

    assert hasattr(m, "_detect_project_root")
    assert m._detect_project_root is _detect_project_root


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


def test_module_all_has_5_entries():
    import evaluation.manifest as m

    assert len(m.__all__) == 5


def test_module_all_does_not_contain_private_helpers():
    import evaluation.manifest as m

    assert "_is_absolute_like" not in m.__all__
    assert "_has_backslash" not in m.__all__
    assert "_resolve_relative_path" not in m.__all__
    assert "_detect_project_root" not in m.__all__


def test_module_all_does_not_contain_constants():
    import evaluation.manifest as m

    assert "MANIFEST_VERSION" not in m.__all__
    assert "json" not in m.__all__
    assert "Path" not in m.__all__
    assert "Any" not in m.__all__
    assert "validate" not in m.__all__


# =========================================================================
# 模块源码 token 验证（补强）
# =========================================================================


def test_module_source_contains_from_future_annotations():
    import evaluation.manifest as m

    assert "from __future__ import annotations" in inspect.getsource(m)


def test_module_source_contains_import_json():
    import evaluation.manifest as m

    assert "import json" in inspect.getsource(m)


def test_module_source_contains_from_dataclasses_import_dataclass():
    import evaluation.manifest as m

    assert "from dataclasses import dataclass" in inspect.getsource(m)


def test_module_source_contains_from_pathlib():
    import evaluation.manifest as m

    assert "from pathlib import Path" in inspect.getsource(m)


def test_module_source_contains_from_typing_import_any():
    import evaluation.manifest as m

    assert "from typing import Any" in inspect.getsource(m)


def test_module_source_contains_from_evaluation_import_manifest_version():
    import evaluation.manifest as m

    assert "from evaluation import MANIFEST_VERSION" in inspect.getsource(m)


def test_module_source_contains_from_evaluation_schema_import_validate():
    import evaluation.manifest as m

    assert "from evaluation.schema import validate" in inspect.getsource(m)


def test_module_source_contains_class_manifest_error():
    import evaluation.manifest as m

    assert "class ManifestError" in inspect.getsource(m)


def test_module_source_contains_dataclass_decorator():
    import evaluation.manifest as m

    assert "@dataclass(frozen=True)" in inspect.getsource(m)


def test_module_source_contains_document_entry_class():
    import evaluation.manifest as m

    assert "class DocumentEntry" in inspect.getsource(m)


def test_module_source_contains_expected_failure_class():
    import evaluation.manifest as m

    assert "class ExpectedFailure" in inspect.getsource(m)


def test_module_source_contains_manifest_class():
    import evaluation.manifest as m

    assert "class Manifest" in inspect.getsource(m)


def test_module_source_contains_property_decorator():
    import evaluation.manifest as m

    assert "@property" in inspect.getsource(m)


def test_module_source_contains_manifest_version_mismatch_check():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "manifest_version" in src
    assert "MANIFEST_VERSION" in src


def test_module_source_contains_resolve_relative_to():
    import evaluation.manifest as m

    assert "relative_to" in inspect.getsource(m)


def test_module_source_contains_frozenset_pair_ids():
    """content_group_count 用 frozenset 去重 pair_ids。"""
    import evaluation.manifest as m

    assert "frozenset" in inspect.getsource(m)


def test_module_source_does_not_contain_print():
    import evaluation.manifest as m

    assert "print(" not in inspect.getsource(m)


def test_module_source_does_not_contain_logging():
    import evaluation.manifest as m

    assert "import logging" not in inspect.getsource(m)


def test_module_source_does_not_contain_subprocess_import():
    import evaluation.manifest as m

    assert "import subprocess" not in inspect.getsource(m)


def test_module_source_does_not_contain_os_import():
    import evaluation.manifest as m

    assert "import os" not in inspect.getsource(m)


def test_module_source_does_not_contain_asyncio():
    import evaluation.manifest as m

    assert "asyncio" not in inspect.getsource(m)


def test_module_source_does_not_contain_abspath():
    """不用 os.path.abspath / realpath（用 Path.resolve()）。"""
    import evaluation.manifest as m

    assert "abspath" not in inspect.getsource(m)
    assert "realpath" not in inspect.getsource(m)


def test_module_source_does_not_contain_read_text():
    """不用 Path.read_text（用 .open + json.load）。"""
    import evaluation.manifest as m

    assert ".read_text(" not in inspect.getsource(m)


# =========================================================================
# 模块 docstring 内容验证
# =========================================================================


def test_module_docstring_is_nonempty_string():
    import evaluation.manifest as m

    assert isinstance(m.__doc__, str)
    assert len(m.__doc__) > 30


def test_module_docstring_mentions_path_relative():
    """docstring 提到 path 必须是相对路径。"""
    import evaluation.manifest as m

    assert "相对路径" in m.__doc__ or "relative" in m.__doc__.lower()


def test_module_docstring_mentions_absolute_rejection():
    """docstring 提到拒绝绝对路径。"""
    import evaluation.manifest as m

    assert "绝对路径" in m.__doc__ or "absolute" in m.__doc__.lower()


def test_module_docstring_mentions_backslash_rejection():
    """docstring 提到拒绝反斜杠。"""
    import evaluation.manifest as m

    assert "反斜杠" in m.__doc__ or "backslash" in m.__doc__.lower()


def test_module_docstring_mentions_project_root_containment():
    """docstring 提到路径必须在项目根内。"""
    import evaluation.manifest as m

    assert "项目根" in m.__doc__ or "project root" in m.__doc__.lower()


def test_module_docstring_mentions_no_absolute_in_manifest():
    """docstring 提到不把绝对路径写入 manifest。"""
    import evaluation.manifest as m

    assert "本机" in m.__doc__ or "绝对路径" in m.__doc__


# =========================================================================
# helper metadata 全部
# =========================================================================


def test_load_manifest_module_identity():
    assert load_manifest.__module__ == "evaluation.manifest"


def test_load_manifest_qualname():
    assert load_manifest.__qualname__ == "load_manifest"


def test_is_absolute_like_module_identity():
    assert _is_absolute_like.__module__ == "evaluation.manifest"


def test_is_absolute_like_qualname():
    assert _is_absolute_like.__qualname__ == "_is_absolute_like"


def test_has_backslash_module_identity():
    assert _has_backslash.__module__ == "evaluation.manifest"


def test_has_backslash_qualname():
    assert _has_backslash.__qualname__ == "_has_backslash"


def test_all_helpers_are_function_type():
    import types as _types

    for fn in [
        _is_absolute_like,
        _has_backslash,
        _resolve_relative_path,
        load_manifest,
        _detect_project_root,
    ]:
        assert isinstance(fn, _types.FunctionType)


# =========================================================================
# 签名 introspection 全部
# =========================================================================


def test_is_absolute_like_signature_param_count_1():
    sig = inspect.signature(_is_absolute_like)
    assert len(sig.parameters) == 1


def test_is_absolute_like_param_name():
    sig = inspect.signature(_is_absolute_like)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_is_absolute_like_no_default():
    sig = inspect.signature(_is_absolute_like)
    assert sig.parameters["path_str"].default is inspect.Parameter.empty


def test_has_backslash_signature_param_count_1():
    sig = inspect.signature(_has_backslash)
    assert len(sig.parameters) == 1


def test_has_backslash_param_name():
    sig = inspect.signature(_has_backslash)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_has_backslash_no_default():
    sig = inspect.signature(_has_backslash)
    assert sig.parameters["path_str"].default is inspect.Parameter.empty


def test_load_manifest_signature_param_count_2():
    sig = inspect.signature(load_manifest)
    assert len(sig.parameters) == 2


def test_load_manifest_param_names():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters.keys()) == ["manifest_path", "project_root"]


def test_load_manifest_manifest_path_no_default():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["manifest_path"].default is inspect.Parameter.empty


def test_load_manifest_project_root_default_none():
    sig = inspect.signature(load_manifest)
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


def test_load_manifest_return_annotation_is_str_or_manifest():
    sig = inspect.signature(load_manifest)
    # future annotations → return_annotation is str
    assert isinstance(sig.return_annotation, str) or sig.return_annotation is Manifest
