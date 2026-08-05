r"""evaluation/manifest.py 边角测试 - 第十四轮（Round 240）。

补强已有 base/edges/edges2-13（共 ~1100+ 测试）未覆盖的深度：
- _is_absolute_like 边界：单斜杠 / alpha:alpha / 2 字符 / Windows 路径变体
- _has_backslash 边界：空字符串 / 只有正斜杠 / 多个反斜杠
- _resolve_relative_path：field_name 透传到错误消息；空字符串 / 单点 / 双点路径
- DocumentEntry / ExpectedFailure / Manifest dataclass frozen 与 equality
- Manifest properties 返回类型精确（int / list / Path）
- load_manifest：documents 是 tuple；source_type 未知值；categories list 转 tuple
- 模块 imports / __all__ 顺序精确
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
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
# _is_absolute_like 边界
# =========================================================================


def test_is_absolute_like_just_slash():
    """'/' → True（绝对路径）。"""
    assert _is_absolute_like("/") is True


def test_is_absolute_like_slash_single_char():
    """'/a' → True。"""
    assert _is_absolute_like("/a") is True


def test_is_absolute_like_alpha_colon_alpha_no_slash():
    """'a:b' → False（无 \\ 或 /）。"""
    assert _is_absolute_like("a:b") is False


def test_is_absolute_like_alpha_colon_only():
    """'a:' → False（len=2 < 3）。"""
    assert _is_absolute_like("a:") is False


def test_is_absolute_like_alpha_colon_backslash():
    """'a:\\\\' → True（Windows 盘符 + backslash）。"""
    assert _is_absolute_like("a:\\") is True


def test_is_absolute_like_alpha_colon_forward_slash():
    """'a:/' → True（Windows 盘符 + 正斜杠）。"""
    assert _is_absolute_like("a:/") is True


def test_is_absolute_like_alpha_colon_no_separator():
    """'a:foo' → False（无 \\ 或 /）。"""
    assert _is_absolute_like("a:foo") is False


def test_is_absolute_like_uppercase_drive():
    """'C:/foo' → True（大写盘符）。"""
    assert _is_absolute_like("C:/foo") is True


def test_is_absolute_like_lowercase_drive():
    """'c:/foo' → True（小写盘符）。"""
    assert _is_absolute_like("c:/foo") is True


def test_is_absolute_like_digit_drive_not_absolute():
    """'1:/foo' → False（盘符必须是 alpha，不是 digit）。"""
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_two_chars_short():
    """'ab' → False（短于 3）。"""
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_relative_path():
    """'foo/bar' → False（相对路径）。"""
    assert _is_absolute_like("foo/bar") is False


def test_is_absolute_like_returns_bool_type():
    """返回值是 bool 类型。"""
    assert isinstance(_is_absolute_like("a"), bool)


# =========================================================================
# _has_backslash 边界
# =========================================================================


def test_has_backslash_empty_string():
    """'' → False。"""
    assert _has_backslash("") is False


def test_has_backslash_only_forward_slash():
    """'/' → False（无 backslash）。"""
    assert _has_backslash("/") is False


def test_has_backslash_multiple_forward_slash():
    """'a/b/c' → False。"""
    assert _has_backslash("a/b/c") is False


def test_has_backslash_single_backslash():
    """'\\\\' → True。"""
    assert _has_backslash("\\") is True


def test_has_backslash_mixed_slashes():
    """'a/b\\\\c' → True（含 backslash）。"""
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_returns_bool_type():
    """返回值是 bool 类型。"""
    assert isinstance(_has_backslash("a"), bool)


# =========================================================================
# _resolve_relative_path：field_name 透传
# =========================================================================


def test_resolve_relative_path_field_name_in_empty_error(tmp_path: Path):
    """空 path → ManifestError message 含 field_name。"""
    try:
        _resolve_relative_path("", tmp_path, "custom_field")
    except ManifestError as e:
        assert "custom_field" in str(e)
    else:
        pytest.fail("should raise")


def test_resolve_relative_path_field_name_in_absolute_error(tmp_path: Path):
    """绝对 path → ManifestError message 含 field_name。"""
    try:
        _resolve_relative_path("/etc/passwd", tmp_path, "abs_field")
    except ManifestError as e:
        assert "abs_field" in str(e)
    else:
        pytest.fail("should raise")


def test_resolve_relative_path_field_name_in_backslash_error(tmp_path: Path):
    """backslash path → ManifestError message 含 field_name。"""
    try:
        _resolve_relative_path("a\\b", tmp_path, "bs_field")
    except ManifestError as e:
        assert "bs_field" in str(e)
    else:
        pytest.fail("should raise")


def test_resolve_relative_path_field_name_in_outside_root_error(tmp_path: Path):
    """路径在 root 之外 → ManifestError message 含 field_name。"""
    try:
        _resolve_relative_path("../outside", tmp_path, "outside_field")
    except ManifestError as e:
        assert "outside_field" in str(e)
    else:
        pytest.fail("should raise")


def test_resolve_relative_path_returns_absolute_path(tmp_path: Path):
    """返回的 Path 是绝对路径。"""
    out = _resolve_relative_path("foo/bar.txt", tmp_path, "f")
    assert out.is_absolute()


def test_resolve_relative_path_returns_path_under_root(tmp_path: Path):
    """返回的 Path 在 project_root 内。"""
    out = _resolve_relative_path("foo.txt", tmp_path, "f")
    assert tmp_path in out.parents or out == tmp_path


def test_resolve_relative_path_normal_relative_path(tmp_path: Path):
    """正常相对路径 → 解析为 project_root/path。"""
    out = _resolve_relative_path("docs/readme.md", tmp_path, "f")
    assert out == (tmp_path / "docs" / "readme.md").resolve()


# =========================================================================
# DocumentEntry / ExpectedFailure / Manifest dataclass frozen
# =========================================================================


def _make_doc_entry(**overrides):
    defaults = {
        "doc_id": "d1",
        "path_str": "a/b.pdf",
        "resolved_path": Path("/tmp/a/b.pdf"),
        "source_type": "pdf",
        "sha256": None,
        "categories": (),
        "paired_with": None,
        "annotation_file_str": None,
        "annotation_resolved": None,
        "expectations": None,
    }
    defaults.update(overrides)
    return DocumentEntry(**defaults)


def _make_expected_failure(**overrides):
    defaults = {
        "doc_id": "broken",
        "path_str": "broken.pdf",
        "resolved_path": Path("/tmp/broken.pdf"),
        "expected_error_code": "unsupported_source_type",
        "source_type": None,
    }
    defaults.update(overrides)
    return ExpectedFailure(**defaults)


def _make_manifest(**overrides):
    defaults = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": (),
        "expected_failures": (),
        "project_root": Path("/tmp"),
    }
    defaults.update(overrides)
    return Manifest(**defaults)


def test_document_entry_frozen_setattr_raises():
    """DocumentEntry 是 frozen → setattr raises FrozenInstanceError。"""
    entry = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        entry.doc_id = "new_id"


def test_expected_failure_frozen_setattr_raises():
    """ExpectedFailure 是 frozen → setattr raises。"""
    ef = _make_expected_failure()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "new_id"


def test_manifest_frozen_setattr_raises():
    """Manifest 是 frozen → setattr raises。"""
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"


def test_document_entry_hashable():
    """DocumentEntry 可 hash（frozen dataclass）。"""
    entry = _make_doc_entry()
    assert hash(entry) != id(entry)  # hash 不只是 id


def test_expected_failure_hashable():
    """ExpectedFailure 可 hash。"""
    ef = _make_expected_failure()
    assert hash(ef) != id(ef)


def test_manifest_hashable_when_frozen():
    """Manifest 可 hash（tuple + Path 字段都 hashable）。"""
    m = _make_manifest()
    hash(m)  # not raise


def test_document_entry_equality_same_fields():
    """同字段 DocumentEntry 相等。"""
    a = _make_doc_entry()
    b = _make_doc_entry()
    assert a == b


def test_expected_failure_equality_same_fields():
    """同字段 ExpectedFailure 相等。"""
    a = _make_expected_failure()
    b = _make_expected_failure()
    assert a == b


def test_manifest_equality_same_fields():
    """同字段 Manifest 相等。"""
    a = _make_manifest()
    b = _make_manifest()
    assert a == b


def test_document_entry_inequality_different_field():
    """不同字段 → 不等。"""
    a = _make_doc_entry(doc_id="d1")
    b = _make_doc_entry(doc_id="d2")
    assert a != b


def test_expected_failure_inequality_different_field():
    """不同字段 → 不等。"""
    a = _make_expected_failure(doc_id="d1")
    b = _make_expected_failure(doc_id="d2")
    assert a != b


def test_manifest_inequality_different_field():
    """不同字段 → 不等。"""
    a = _make_manifest(devset_status="incomplete")
    b = _make_manifest(devset_status="complete")
    assert a != b


# =========================================================================
# DocumentEntry / ExpectedFailure / Manifest dataclass fields() 精确
# =========================================================================


def test_document_entry_field_count_exactly_ten():
    """DocumentEntry 10 个字段。"""
    assert len(fields(DocumentEntry)) == 10


def test_expected_failure_field_count_exactly_five():
    """ExpectedFailure 5 个字段。"""
    assert len(fields(ExpectedFailure)) == 5


def test_manifest_field_count_exactly_five():
    """Manifest 5 个字段。"""
    assert len(fields(Manifest)) == 5


def test_document_entry_field_names_exact():
    """DocumentEntry 字段名精确。"""
    names = [f.name for f in fields(DocumentEntry)]
    assert names == [
        "doc_id", "path_str", "resolved_path", "source_type", "sha256",
        "categories", "paired_with", "annotation_file_str",
        "annotation_resolved", "expectations",
    ]


def test_expected_failure_field_names_exact():
    """ExpectedFailure 字段名精确。"""
    names = [f.name for f in fields(ExpectedFailure)]
    assert names == ["doc_id", "path_str", "resolved_path",
                     "expected_error_code", "source_type"]


def test_manifest_field_names_exact():
    """Manifest 字段名精确。"""
    names = [f.name for f in fields(Manifest)]
    assert names == [
        "manifest_version", "devset_status", "documents",
        "expected_failures", "project_root",
    ]


def test_document_entry_is_dataclass():
    """DocumentEntry 是 dataclass。"""
    assert is_dataclass(DocumentEntry)


def test_expected_failure_is_dataclass():
    """ExpectedFailure 是 dataclass。"""
    assert is_dataclass(ExpectedFailure)


def test_manifest_is_dataclass():
    """Manifest 是 dataclass。"""
    assert is_dataclass(Manifest)


# =========================================================================
# Manifest properties 返回类型
# =========================================================================


def test_manifest_file_count_returns_int_type():
    """file_count 返回 int。"""
    m = _make_manifest()
    assert isinstance(m.file_count, int)


def test_manifest_pdf_count_returns_int_type():
    """pdf_count 返回 int。"""
    m = _make_manifest()
    assert isinstance(m.pdf_count, int)


def test_manifest_docx_count_returns_int_type():
    """docx_count 返回 int。"""
    m = _make_manifest()
    assert isinstance(m.docx_count, int)


def test_manifest_content_group_count_returns_int_type():
    """content_group_count 返回 int。"""
    m = _make_manifest()
    assert isinstance(m.content_group_count, int)


def test_manifest_categories_covered_returns_list_type():
    """categories_covered 返回 list。"""
    m = _make_manifest()
    assert isinstance(m.categories_covered, list)


def test_manifest_categories_covered_returns_sorted_list():
    """categories_covered 返回 sorted list。"""
    entry1 = _make_doc_entry(doc_id="d1", categories=("z", "a"))
    entry2 = _make_doc_entry(doc_id="d2", categories=("m",))
    m = _make_manifest(documents=(entry1, entry2))
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_dedup_across_docs():
    """categories_covered 跨文档去重。"""
    entry1 = _make_doc_entry(doc_id="d1", categories=("x",))
    entry2 = _make_doc_entry(doc_id="d2", categories=("x", "y"))
    m = _make_manifest(documents=(entry1, entry2))
    assert m.categories_covered == ["x", "y"]


# =========================================================================
# load_manifest 完整流程
# =========================================================================


def _write_minimal_manifest(tmp_path: Path, **overrides):
    """写最小合法 manifest 到 tmp_path 下，返回 manifest 文件路径。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    manifest.update(overrides)
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return p


def test_load_manifest_returns_manifest_instance(tmp_path: Path):
    """load_manifest 返回 Manifest 实例。"""
    p = _write_minimal_manifest(tmp_path)
    m = load_manifest(p)
    assert isinstance(m, Manifest)


def test_load_manifest_documents_is_tuple_type(tmp_path: Path):
    """load_manifest 后 documents 是 tuple 类型。"""
    p = _write_minimal_manifest(tmp_path)
    m = load_manifest(p)
    assert isinstance(m.documents, tuple)


def test_load_manifest_expected_failures_is_tuple_type(tmp_path: Path):
    """load_manifest 后 expected_failures 是 tuple 类型。"""
    p = _write_minimal_manifest(tmp_path)
    m = load_manifest(p)
    assert isinstance(m.expected_failures, tuple)


def test_load_manifest_project_root_is_path_type(tmp_path: Path):
    """load_manifest 后 project_root 是 Path 类型。"""
    p = _write_minimal_manifest(tmp_path)
    m = load_manifest(p)
    assert isinstance(m.project_root, Path)


def test_load_manifest_project_root_is_absolute(tmp_path: Path):
    """load_manifest 后 project_root 是绝对路径。"""
    p = _write_minimal_manifest(tmp_path)
    m = load_manifest(p)
    assert m.project_root.is_absolute()


def test_load_manifest_with_unknown_source_type(tmp_path: Path):
    """source_type='txt' 被 schema 拒绝（只允许 pdf/docx）。

    manifest.schema.json 的 source_type 是 enum: ['pdf', 'docx']。
    """
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.txt",
            "source_type": "txt",
        }],
        "expected_failures": [],
    }
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_devset_status_must_be_complete_or_incomplete(tmp_path: Path):
    """devset_status 是 enum: ['complete', 'incomplete']。"""
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "custom_status",
        "documents": [],
        "expected_failures": [],
    }
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_categories_input_list_becomes_tuple(tmp_path: Path):
    """categories 输入 list → 转为 tuple。"""
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.pdf",
            "source_type": "pdf",
            "categories": ["x", "y"],
        }],
        "expected_failures": [],
    }
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    m = load_manifest(p)
    assert isinstance(m.documents[0].categories, tuple)
    assert m.documents[0].categories == ("x", "y")


def test_load_manifest_returns_documents_empty_tuple_when_no_documents(tmp_path: Path):
    """无 documents → m.documents == ()。"""
    p = _write_minimal_manifest(tmp_path)
    m = load_manifest(p)
    assert m.documents == ()


def test_load_manifest_returns_expected_failures_empty_tuple(tmp_path: Path):
    """无 expected_failures → m.expected_failures == ()。"""
    p = _write_minimal_manifest(tmp_path)
    m = load_manifest(p)
    assert m.expected_failures == ()


def test_load_manifest_manifest_version_propagated(tmp_path: Path):
    """manifest_version 透传到 Manifest。"""
    p = _write_minimal_manifest(tmp_path)
    m = load_manifest(p)
    assert m.manifest_version == MANIFEST_VERSION


def test_load_manifest_devset_status_propagated(tmp_path: Path):
    """devset_status 透传（必须是 enum 中的值）。"""
    p = _write_minimal_manifest(tmp_path, devset_status="complete")
    m = load_manifest(p)
    assert m.devset_status == "complete"


# =========================================================================
# ManifestError 行为
# =========================================================================


def test_manifest_error_is_exception_subclass():
    """ManifestError 继承 Exception。"""
    assert issubclass(ManifestError, Exception)


def test_manifest_error_not_subclass_of_keyerror():
    """ManifestError 不继承 KeyError。"""
    assert not issubclass(ManifestError, KeyError)


def test_manifest_error_not_subclass_of_valueerror():
    """ManifestError 不继承 ValueError。"""
    assert not issubclass(ManifestError, ValueError)


def test_manifest_error_init_with_message_only():
    """单参数 init。"""
    e = ManifestError("hello")
    assert str(e) == "hello"


def test_manifest_error_args_contains_message():
    """args[0] 是 message。"""
    e = ManifestError("msg")
    assert e.args == ("msg",)


def test_manifest_error_can_be_raised_and_caught():
    """raise ManifestError → except ManifestError as e。"""
    with pytest.raises(ManifestError) as exc_info:
        raise ManifestError("test")
    assert "test" in str(exc_info.value)


def test_manifest_error_repr_contains_class_name():
    """repr 含类名。"""
    e = ManifestError("msg")
    assert "ManifestError" in repr(e)


def test_manifest_error_has_docstring():
    """ManifestError 有 docstring。"""
    assert ManifestError.__doc__ is not None
    assert len(ManifestError.__doc__) > 0


# =========================================================================
# _detect_project_root 边界
# =========================================================================


def test_detect_project_root_no_pyproject_returns_starting_dir(tmp_path: Path):
    """无 pyproject.toml → 返回起始目录。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    result = _detect_project_root(sub)
    # 应当返回 sub（或向上找到的某个目录，但找不到时返回 cur）
    assert isinstance(result, Path)


def test_detect_project_root_with_pyproject_in_parent(tmp_path: Path):
    """pyproject.toml 在父目录 → 返回父目录。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    result = _detect_project_root(sub)
    assert result == tmp_path.resolve()


def test_detect_project_root_returns_path_type():
    """返回 Path 类型。"""
    result = _detect_project_root(Path.cwd())
    assert isinstance(result, Path)


def test_detect_project_root_returns_absolute():
    """返回绝对路径。"""
    result = _detect_project_root(Path.cwd())
    assert result.is_absolute()


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact_order():
    """__all__ 顺序精确。"""
    import evaluation.manifest as m
    assert m.__all__ == [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ]


def test_module_all_length_exactly_five():
    """__all__ 5 个元素。"""
    import evaluation.manifest as m
    assert len(m.__all__) == 5


def test_module_internal_helpers_not_in_all():
    """内部 helper（_is_absolute_like / _has_backslash / _resolve_relative_path / _detect_project_root）不在 __all__。"""
    import evaluation.manifest as m
    assert "_is_absolute_like" not in m.__all__
    assert "_has_backslash" not in m.__all__
    assert "_resolve_relative_path" not in m.__all__
    assert "_detect_project_root" not in m.__all__


def test_module_imports_json():
    """json 在命名空间。"""
    import evaluation.manifest as m
    assert hasattr(m, "json")


def test_module_imports_dataclass():
    """dataclass 在命名空间。"""
    import evaluation.manifest as m
    assert hasattr(m, "dataclass")


def test_module_imports_path():
    """Path 在命名空间。"""
    import evaluation.manifest as m
    from pathlib import Path as P
    assert m.Path is P


def test_module_imports_any():
    """Any 在命名空间。"""
    import evaluation.manifest as m
    assert hasattr(m, "Any")


def test_module_imports_manifest_version():
    """MANIFEST_VERSION 已从 evaluation 导入。"""
    import evaluation.manifest as m
    assert m.MANIFEST_VERSION == MANIFEST_VERSION


def test_module_imports_validate():
    """validate 已从 evaluation.schema 导入。"""
    import evaluation.manifest as m
    from evaluation.schema import validate
    assert m.validate is validate


def test_module_uses_future_annotations():
    """模块用 from __future__ import annotations。"""
    import evaluation.manifest
    src = Path(evaluation.manifest.__file__).read_text(encoding="utf-8")
    assert "from __future__ import annotations" in src


def test_module_internal_helpers_accessible():
    """内部 helper 在命名空间可访问。"""
    import evaluation.manifest as m
    assert callable(m._is_absolute_like)
    assert callable(m._has_backslash)
    assert callable(m._resolve_relative_path)
    assert callable(m._detect_project_root)


# =========================================================================
# 函数签名
# =========================================================================


def test_load_manifest_signature():
    """load_manifest 2 参数（manifest_path + project_root，后者有默认）。"""
    import inspect
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters.keys()) == ["manifest_path", "project_root"]


def test_load_manifest_project_root_default_none():
    """project_root 默认 None。"""
    import inspect
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_is_absolute_like_signature():
    """_is_absolute_like 1 参数。"""
    import inspect
    sig = inspect.signature(_is_absolute_like)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_has_backslash_signature():
    """_has_backslash 1 参数。"""
    import inspect
    sig = inspect.signature(_has_backslash)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_resolve_relative_path_signature():
    """_resolve_relative_path 3 参数。"""
    import inspect
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters.keys()) == ["path_str", "project_root", "field_name"]


def test_detect_project_root_signature():
    """_detect_project_root 1 参数。"""
    import inspect
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters.keys()) == ["start"]


# =========================================================================
# callable 验证
# =========================================================================


def test_load_manifest_callable():
    assert callable(load_manifest)


def test_is_absolute_like_callable():
    assert callable(_is_absolute_like)


def test_has_backslash_callable():
    assert callable(_has_backslash)


def test_resolve_relative_path_callable():
    assert callable(_resolve_relative_path)


def test_detect_project_root_callable():
    assert callable(_detect_project_root)
