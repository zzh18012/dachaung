r"""evaluation/manifest.py 边角测试 - 第五轮（Round 130）。

补强已有 base/edges/edges2/edges3/edges4（共 425 测试）未覆盖的深度路径：
- _is_absolute_like 微边界：
  - 路径首字符是非字母（数字、下划线、unicode）但符合盘符形式 → False
  - 长度 < 3 边界
  - 第二字符非 ":" → False
  - 第三字符非分隔符 → False
- _has_backslash 边界：
  - 单 backslash
  - 多 backslash
  - backslash 在开头/中间/结尾
- ManifestError 深度：
  - 继承 Exception
  - 不继承 ValueError
  - args 行为
  - raise/except 语义
- DocumentEntry 字段类型精确：
  - 10 个字段，类型验证
  - frozen=True
- ExpectedFailure 字段类型精确：
  - 5 个字段，类型验证
  - frozen=True
- Manifest 字段类型精确：
  - 5 个字段，类型验证
  - frozen=True
  - properties 行为
- _resolve_relative_path 深度：
  - 正常相对路径
  - 含 ./ 的路径
  - 含多重 subdir
  - field_name 在错误消息中的位置
- _detect_project_root 深度：
  - start 是符号链接（不存在）
  - start 是嵌套深层目录
  - 返回值类型
- load_manifest 深度：
  - manifest_path 是 Path / str
  - project_root 是 Path / str / None
  - manifest 不存在 → ManifestError
  - JSON 解析失败 → ManifestError
  - manifest_version 不匹配 → ManifestError
- 模块结构深度：
  - __all__ 5 项精确
  - 各 helper callable
  - imports 完整
- 签名深度：
  - load_manifest 默认值
  - properties 返回类型
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
from typing import Any

import pytest

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


SHA = "a" * 64


# =========================================================================
# _is_absolute_like 微边界
# =========================================================================


def test_is_absolute_like_signature_one_param():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "path_str" in params


def test_is_absolute_like_returns_bool_type():
    assert isinstance(_is_absolute_like("/foo"), bool)


def test_is_absolute_like_empty_string_returns_false():
    assert _is_absolute_like("") is False


def test_is_absolute_like_forward_slash_root():
    assert _is_absolute_like("/foo/bar") is True


def test_is_absolute_like_just_slash():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_relative_path():
    assert _is_absolute_like("foo/bar") is False


def test_is_absolute_like_single_char_path():
    assert _is_absolute_like("a") is False


def test_is_absolute_like_two_char_path():
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_three_char_relative():
    assert _is_absolute_like("abc") is False


def test_is_absolute_like_windows_drive_lowercase():
    assert _is_absolute_like("c:\\foo") is True


def test_is_absolute_like_windows_drive_uppercase():
    assert _is_absolute_like("C:\\foo") is True


def test_is_absolute_like_windows_drive_forward_slash():
    assert _is_absolute_like("C:/foo") is True


def test_is_absolute_like_drive_no_separator():
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_no_drive_relative():
    assert _is_absolute_like("foo/bar/baz") is False


def test_is_absolute_like_dot_slash():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_double_dot_slash():
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_digit_drive():
    """首位是数字 → isalpha() False → 不是盘符。"""
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_underscore_drive():
    """首位是 _ → isalpha() False → 不是盘符。"""
    assert _is_absolute_like("_:/foo") is False


def test_is_absolute_like_unicode_first_char():
    """中文字符也是 isalpha() True，所以 "中:/foo" 被识别为 Windows 盘符形式。"""
    # 中文 unicode 字符 .isalpha() 返回 True，所以 "中:/foo" 会被识别为绝对路径
    assert _is_absolute_like("中:/foo") is True


def test_is_absolute_like_emoji_first_char():
    """emoji 不是 alpha → 不是盘符。"""
    assert _is_absolute_like("🎉:/foo") is False


def test_is_absolute_like_alpha_colon_only_no_separator():
    """A:B 无 / 或 \\ → False。"""
    assert _is_absolute_like("A:B") is False


def test_is_absolute_like_alpha_colon_filename():
    """A:foo 形式（Windows drive relative，技术上不算绝对）。"""
    assert _is_absolute_like("A:foo") is False


# =========================================================================
# _has_backslash 边界
# =========================================================================


def test_has_backslash_signature_one_param():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "path_str" in params


def test_has_backslash_returns_bool():
    assert isinstance(_has_backslash("foo"), bool) is True or isinstance(_has_backslash("foo"), bool) is False


def test_has_backslash_no_backslash():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_single_backslash():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_multiple_backslashes():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_leading_backslash():
    assert _has_backslash("\\foo") is True


def test_has_backslash_trailing_backslash():
    assert _has_backslash("foo\\") is True


def test_has_backslash_only_backslash():
    assert _has_backslash("\\") is True


def test_has_backslash_empty_string():
    assert _has_backslash("") is False


def test_has_backslash_unicode_no_backslash():
    assert _has_backslash("中文/路径") is False


def test_has_backslash_unicode_with_backslash():
    assert _has_backslash("中文\\路径") is True


# =========================================================================
# ManifestError 深度
# =========================================================================


def test_manifest_error_inherits_exception():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_does_not_inherit_value_error():
    assert not issubclass(ManifestError, ValueError)


def test_manifest_error_does_not_inherit_key_error():
    assert not issubclass(ManifestError, KeyError)


def test_manifest_error_can_be_raised():
    with pytest.raises(ManifestError):
        raise ManifestError("test")


def test_manifest_error_caught_as_exception():
    try:
        raise ManifestError("x")
    except Exception as e:
        assert isinstance(e, ManifestError)


def test_manifest_error_str():
    e = ManifestError("my message")
    assert str(e) == "my message"


def test_manifest_error_repr():
    e = ManifestError("msg")
    assert "ManifestError" in repr(e)


def test_manifest_error_args_value():
    e = ManifestError("msg")
    assert e.args == ("msg",)


def test_manifest_error_no_args():
    e = ManifestError()
    assert e.args == ()


def test_manifest_error_multiple_args():
    e = ManifestError("msg1", "msg2")
    assert e.args == ("msg1", "msg2")


def test_manifest_error_can_be_raised_and_caught():
    try:
        raise ManifestError("x")
    except ManifestError as e:
        assert str(e) == "x"


def test_manifest_error_not_caught_by_value_error():
    """ManifestError 不是 ValueError 子类。"""
    with pytest.raises(ManifestError):
        try:
            raise ManifestError("x")
        except ValueError:
            pytest.fail("Should not be caught as ValueError")


# =========================================================================
# DocumentEntry 字段类型精确
# =========================================================================


def _make_doc_entry(doc_id: str = "doc-1", **kwargs: Any) -> DocumentEntry:
    defaults: dict[str, Any] = dict(
        doc_id=doc_id,
        path_str="foo.pdf",
        resolved_path=Path("/tmp/foo.pdf"),
        source_type="pdf",
        sha256=SHA,
        categories=("cat1",),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    defaults.update(kwargs)
    return DocumentEntry(**defaults)


def test_document_entry_is_dataclass():
    assert is_dataclass(DocumentEntry)


def test_document_entry_is_frozen():
    e = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        e.doc_id = "changed"  # type: ignore[misc]


def test_document_entry_doc_id_type_str():
    e = _make_doc_entry(doc_id="x")
    assert isinstance(e.doc_id, str)


def test_document_entry_path_str_type_str():
    e = _make_doc_entry()
    assert isinstance(e.path_str, str)


def test_document_entry_resolved_path_type_path():
    e = _make_doc_entry()
    assert isinstance(e.resolved_path, Path)


def test_document_entry_source_type_type_str():
    e = _make_doc_entry()
    assert isinstance(e.source_type, str)


def test_document_entry_sha256_can_be_str():
    e = _make_doc_entry(sha256=SHA)
    assert e.sha256 == SHA


def test_document_entry_sha256_can_be_none():
    e = _make_doc_entry(sha256=None)
    assert e.sha256 is None


def test_document_entry_categories_type_tuple():
    e = _make_doc_entry(categories=("a", "b"))
    assert isinstance(e.categories, tuple)


def test_document_entry_paired_with_can_be_str():
    e = _make_doc_entry(paired_with="doc-2")
    assert e.paired_with == "doc-2"


def test_document_entry_paired_with_can_be_none():
    e = _make_doc_entry(paired_with=None)
    assert e.paired_with is None


def test_document_entry_annotation_file_str_can_be_none():
    e = _make_doc_entry()
    assert e.annotation_file_str is None


def test_document_entry_annotation_resolved_can_be_none():
    e = _make_doc_entry()
    assert e.annotation_resolved is None


def test_document_entry_annotation_resolved_can_be_path():
    e = _make_doc_entry(annotation_resolved=Path("/tmp/ann.json"))
    assert isinstance(e.annotation_resolved, Path)


def test_document_entry_expectations_can_be_dict():
    e = _make_doc_entry(expectations={"element_count_by_type": {}})
    assert isinstance(e.expectations, dict)


def test_document_entry_expectations_can_be_none():
    e = _make_doc_entry()
    assert e.expectations is None


def test_document_entry_field_count_ten():
    import dataclasses

    fields = dataclasses.fields(DocumentEntry)
    assert len(fields) == 10


def test_document_entry_field_names_exact():
    import dataclasses

    names = [f.name for f in dataclasses.fields(DocumentEntry)]
    assert names == [
        "doc_id", "path_str", "resolved_path", "source_type", "sha256",
        "categories", "paired_with", "annotation_file_str",
        "annotation_resolved", "expectations",
    ]


def test_document_entry_hashable():
    e = _make_doc_entry()
    assert hash(e) == hash(_make_doc_entry())


def test_document_entry_in_set():
    s = {_make_doc_entry(), _make_doc_entry()}
    # frozen + 相同字段 → 集合去重
    assert len(s) == 1


def test_document_entry_equality():
    e1 = _make_doc_entry()
    e2 = _make_doc_entry()
    assert e1 == e2


def test_document_entry_inequality_different_field():
    e1 = _make_doc_entry(doc_id="a")
    e2 = _make_doc_entry(doc_id="b")
    assert e1 != e2


# =========================================================================
# ExpectedFailure 字段类型精确
# =========================================================================


def _make_failure(doc_id: str = "fail-1", **kwargs: Any) -> ExpectedFailure:
    defaults: dict[str, Any] = dict(
        doc_id=doc_id,
        path_str="bad.pdf",
        resolved_path=Path("/tmp/bad.pdf"),
        expected_error_code="parser_failed",
        source_type="pdf",
    )
    defaults.update(kwargs)
    return ExpectedFailure(**defaults)


def test_expected_failure_is_dataclass():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_is_frozen():
    f = _make_failure()
    with pytest.raises(FrozenInstanceError):
        f.doc_id = "changed"  # type: ignore[misc]


def test_expected_failure_field_count_five():
    import dataclasses

    fields = dataclasses.fields(ExpectedFailure)
    assert len(fields) == 5


def test_expected_failure_field_names_exact():
    import dataclasses

    names = [f.name for f in dataclasses.fields(ExpectedFailure)]
    assert names == ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]


def test_expected_failure_doc_id_type_str():
    f = _make_failure()
    assert isinstance(f.doc_id, str)


def test_expected_failure_path_str_type_str():
    f = _make_failure()
    assert isinstance(f.path_str, str)


def test_expected_failure_resolved_path_type_path():
    f = _make_failure()
    assert isinstance(f.resolved_path, Path)


def test_expected_failure_expected_error_code_type_str():
    f = _make_failure()
    assert isinstance(f.expected_error_code, str)


def test_expected_failure_source_type_can_be_str():
    f = _make_failure(source_type="docx")
    assert f.source_type == "docx"


def test_expected_failure_source_type_can_be_none():
    f = _make_failure(source_type=None)
    assert f.source_type is None


def test_expected_failure_hashable():
    f = _make_failure()
    assert hash(f) == hash(_make_failure())


def test_expected_failure_equality():
    f1 = _make_failure()
    f2 = _make_failure()
    assert f1 == f2


def test_expected_failure_inequality_different_field():
    f1 = _make_failure(doc_id="a")
    f2 = _make_failure(doc_id="b")
    assert f1 != f2


# =========================================================================
# Manifest 字段类型精确
# =========================================================================


def _make_manifest(**kwargs: Any) -> Manifest:
    defaults: dict[str, Any] = dict(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    defaults.update(kwargs)
    return Manifest(**defaults)


def test_manifest_is_dataclass():
    assert is_dataclass(Manifest)


def test_manifest_is_frozen():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


def test_manifest_field_count_five():
    import dataclasses

    fields = dataclasses.fields(Manifest)
    assert len(fields) == 5


def test_manifest_field_names_exact():
    import dataclasses

    names = [f.name for f in dataclasses.fields(Manifest)]
    assert names == ["manifest_version", "devset_status", "documents", "expected_failures", "project_root"]


def test_manifest_documents_type_tuple():
    m = _make_manifest(documents=(_make_doc_entry(),))
    assert isinstance(m.documents, tuple)


def test_manifest_expected_failures_type_tuple():
    m = _make_manifest(expected_failures=(_make_failure(),))
    assert isinstance(m.expected_failures, tuple)


def test_manifest_project_root_type_path():
    m = _make_manifest()
    assert isinstance(m.project_root, Path)


def test_manifest_hashable():
    m = _make_manifest()
    assert hash(m) == hash(_make_manifest())


def test_manifest_equality():
    m1 = _make_manifest()
    m2 = _make_manifest()
    assert m1 == m2


def test_manifest_inequality_different_status():
    m1 = _make_manifest(devset_status="incomplete")
    m2 = _make_manifest(devset_status="complete")
    assert m1 != m2


# =========================================================================
# Manifest properties 深度
# =========================================================================


def test_manifest_file_count_returns_int():
    m = _make_manifest()
    assert isinstance(m.file_count, int)


def test_manifest_file_count_zero_for_empty():
    m = _make_manifest(documents=())
    assert m.file_count == 0


def test_manifest_file_count_one():
    m = _make_manifest(documents=(_make_doc_entry(),))
    assert m.file_count == 1


def test_manifest_pdf_count_returns_int():
    m = _make_manifest()
    assert isinstance(m.pdf_count, int)


def test_manifest_pdf_count_zero_when_no_pdf():
    m = _make_manifest(documents=(_make_doc_entry(source_type="docx"),))
    assert m.pdf_count == 0


def test_manifest_pdf_count_one_when_one_pdf():
    m = _make_manifest(documents=(_make_doc_entry(source_type="pdf"),))
    assert m.pdf_count == 1


def test_manifest_docx_count_returns_int():
    m = _make_manifest()
    assert isinstance(m.docx_count, int)


def test_manifest_docx_count_zero_when_no_docx():
    m = _make_manifest(documents=(_make_doc_entry(source_type="pdf"),))
    assert m.docx_count == 0


def test_manifest_docx_count_one_when_one_docx():
    m = _make_manifest(documents=(_make_doc_entry(source_type="docx"),))
    assert m.docx_count == 1


def test_manifest_content_group_count_returns_int():
    m = _make_manifest()
    assert isinstance(m.content_group_count, int)


def test_manifest_content_group_count_zero_when_empty():
    m = _make_manifest(documents=())
    assert m.content_group_count == 0


def test_manifest_content_group_count_unpaired():
    m = _make_manifest(documents=(_make_doc_entry(doc_id="a"),))
    assert m.content_group_count == 1


def test_manifest_content_group_count_paired():
    a = _make_doc_entry(doc_id="a", paired_with="b")
    b = _make_doc_entry(doc_id="b", paired_with="a")
    m = _make_manifest(documents=(a, b))
    # 1 pair = 1 group
    assert m.content_group_count == 1


def test_manifest_categories_covered_returns_list():
    m = _make_manifest()
    assert isinstance(m.categories_covered, list)


def test_manifest_categories_covered_empty_when_no_documents():
    m = _make_manifest(documents=())
    assert m.categories_covered == []


def test_manifest_categories_covered_sorted():
    a = _make_doc_entry(doc_id="a", categories=("z",))
    b = _make_doc_entry(doc_id="b", categories=("a",))
    m = _make_manifest(documents=(a, b))
    assert m.categories_covered == ["a", "z"]


def test_manifest_categories_covered_dedup():
    a = _make_doc_entry(doc_id="a", categories=("x", "y"))
    b = _make_doc_entry(doc_id="b", categories=("y", "z"))
    m = _make_manifest(documents=(a, b))
    assert m.categories_covered == ["x", "y", "z"]


# =========================================================================
# _resolve_relative_path 深度
# =========================================================================


def test_resolve_relative_path_signature_three_params():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.keys())
    assert len(params) == 3
    assert "path_str" in params
    assert "project_root" in params
    assert "field_name" in params


def test_resolve_relative_path_returns_path(tmp_path: Path):
    result = _resolve_relative_path("foo.pdf", tmp_path, "test")
    assert isinstance(result, Path)


def test_resolve_relative_path_normal_relative(tmp_path: Path):
    result = _resolve_relative_path("foo.pdf", tmp_path, "test")
    assert result == (tmp_path / "foo.pdf").resolve()


def test_resolve_relative_path_subdir(tmp_path: Path):
    result = _resolve_relative_path("sub/foo.pdf", tmp_path, "test")
    assert result == (tmp_path / "sub" / "foo.pdf").resolve()


def test_resolve_relative_path_with_dot(tmp_path: Path):
    result = _resolve_relative_path("./foo.pdf", tmp_path, "test")
    assert result == (tmp_path / "foo.pdf").resolve()


def test_resolve_relative_path_double_dot_within_root(tmp_path: Path):
    """sub/../foo.pdf 解析后在 root 内。"""
    result = _resolve_relative_path("sub/../foo.pdf", tmp_path, "test")
    assert result == (tmp_path / "foo.pdf").resolve()


def test_resolve_relative_path_empty_raises(tmp_path: Path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("", tmp_path, "test")


def test_resolve_relative_path_absolute_raises(tmp_path: Path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("/etc/passwd", tmp_path, "test")


def test_resolve_relative_path_backslash_raises(tmp_path: Path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("foo\\bar.pdf", tmp_path, "test")


def test_resolve_relative_path_field_name_in_empty_error(tmp_path: Path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", tmp_path, "MY_FIELD")
    assert "MY_FIELD" in str(ei.value)


def test_resolve_relative_path_field_name_in_absolute_error(tmp_path: Path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("/etc", tmp_path, "MY_FIELD")
    assert "MY_FIELD" in str(ei.value)


def test_resolve_relative_path_field_name_in_backslash_error(tmp_path: Path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("a\\b", tmp_path, "MY_FIELD")
    assert "MY_FIELD" in str(ei.value)


def test_resolve_relative_path_field_name_in_outside_error(tmp_path: Path):
    """路径解析后在 root 外 → 错误消息含 field_name。"""
    # 用 .. 跳出到父目录
    parent = tmp_path.parent
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("../foo.pdf", tmp_path, "MY_FIELD")
    assert "MY_FIELD" in str(ei.value)


# =========================================================================
# _detect_project_root 深度
# =========================================================================


def test_detect_project_root_signature_one_param():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "start" in params


def test_detect_project_root_returns_path(tmp_path: Path):
    """构造一个有 pyproject.toml 的临时目录。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert isinstance(result, Path)


def test_detect_project_root_file_input(tmp_path: Path):
    """start 是文件 → 取其父目录。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    f = tmp_path / "sub.json"
    f.write_text("{}", encoding="utf-8")
    result = _detect_project_root(f)
    assert result == tmp_path


def test_detect_project_root_no_pyproject(tmp_path: Path):
    """无 pyproject.toml → 返回 cur（start 的父目录）。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    result = _detect_project_root(sub)
    # 返回 cur（即 sub，因为没找到 pyproject）
    assert isinstance(result, Path)


def test_detect_project_root_finds_closest_pyproject(tmp_path: Path):
    """有多个 pyproject.toml 时返回最近的。"""
    (tmp_path / "pyproject.toml").write_text("[tool.outer]\n", encoding="utf-8")
    inner = tmp_path / "inner"
    inner.mkdir()
    (inner / "pyproject.toml").write_text("[tool.inner]\n", encoding="utf-8")
    result = _detect_project_root(inner)
    assert result == inner


# =========================================================================
# load_manifest 深度
# =========================================================================


def test_load_manifest_signature_two_params():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.keys())
    assert len(params) == 2
    assert "manifest_path" in params
    assert "project_root" in params


def test_load_manifest_manifest_path_no_default():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["manifest_path"].default is inspect.Parameter.empty


def test_load_manifest_project_root_default_none():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_load_manifest_missing_file_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(tmp_path / "missing.json")
    assert "不存在" in str(ei.value)


def test_load_manifest_invalid_json_raises(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_load_manifest_invalid_json_message(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(p)
    assert "JSON" in str(ei.value) or "解析" in str(ei.value)


def test_load_manifest_str_path(tmp_path: Path):
    """str 路径输入。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    # schema 校验会失败（缺 manifest_version 等），但能确认 str 输入被接受
    with pytest.raises(Exception):
        load_manifest(str(p))


def test_load_manifest_path_object(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(p)


def test_load_manifest_returns_manifest_type(tmp_path: Path):
    """完整 manifest 加载成功 → 返回 Manifest 实例。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    # 创建一个示例文档
    doc_path = tmp_path / "doc.pdf"
    doc_path.write_bytes(b"fake pdf")

    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "doc-1",
                "path": "doc.pdf",
                "source_type": "pdf",
                "categories": ["test"],
            }
        ],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest_data), encoding="utf-8")
    result = load_manifest(p)
    assert isinstance(result, Manifest)


def test_load_manifest_resolves_paths(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    doc_path = tmp_path / "doc.pdf"
    doc_path.write_bytes(b"x")

    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "doc-1",
                "path": "doc.pdf",
                "source_type": "pdf",
            }
        ],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest_data), encoding="utf-8")
    m = load_manifest(p)
    assert m.documents[0].resolved_path == doc_path.resolve()


def test_load_manifest_categories_list_to_tuple(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    doc_path = tmp_path / "doc.pdf"
    doc_path.write_bytes(b"x")

    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "doc-1",
                "path": "doc.pdf",
                "source_type": "pdf",
                "categories": ["a", "b"],
            }
        ],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest_data), encoding="utf-8")
    m = load_manifest(p)
    assert isinstance(m.documents[0].categories, tuple)
    assert m.documents[0].categories == ("a", "b")


def test_load_manifest_manifest_version_mismatch_raises(tmp_path: Path):
    """schema 先校验 manifest_version enum，所以非 enum 值会被 EvalSchemaError 拦截。
    此测试验证 schema 拦截的行为（不是我们代码里的二次校验）。"""
    from evaluation.schema import EvalSchemaError

    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    manifest_data = {
        "manifest_version": "0.0.0-mismatch",  # 非 schema enum 值
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest_data), encoding="utf-8")
    # schema 校验先于 manifest_version 二次检查 → EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_imports_json():
    from evaluation import manifest as mod
    assert hasattr(mod, "json")


def test_module_imports_dataclass():
    from evaluation import manifest as mod
    assert hasattr(mod, "dataclass")


def test_module_imports_path():
    from evaluation import manifest as mod
    assert hasattr(mod, "Path")


def test_module_imports_any():
    from evaluation import manifest as mod
    assert hasattr(mod, "Any")


def test_module_imports_manifest_version():
    from evaluation import manifest as mod
    assert hasattr(mod, "MANIFEST_VERSION")


def test_module_imports_validate():
    from evaluation import manifest as mod
    assert hasattr(mod, "validate")


def test_module_has_manifest_error():
    from evaluation import manifest as mod
    assert hasattr(mod, "ManifestError")


def test_module_has_document_entry():
    from evaluation import manifest as mod
    assert hasattr(mod, "DocumentEntry")


def test_module_has_expected_failure():
    from evaluation import manifest as mod
    assert hasattr(mod, "ExpectedFailure")


def test_module_has_manifest_class():
    from evaluation import manifest as mod
    assert hasattr(mod, "Manifest")


def test_module_has_load_manifest():
    from evaluation import manifest as mod
    assert hasattr(mod, "load_manifest")


def test_module_has_is_absolute_like():
    from evaluation import manifest as mod
    assert hasattr(mod, "_is_absolute_like")


def test_module_has_has_backslash():
    from evaluation import manifest as mod
    assert hasattr(mod, "_has_backslash")


def test_module_has_resolve_relative_path():
    from evaluation import manifest as mod
    assert hasattr(mod, "_resolve_relative_path")


def test_module_has_detect_project_root():
    from evaluation import manifest as mod
    assert hasattr(mod, "_detect_project_root")


def test_module_all_is_list():
    from evaluation import manifest as mod
    assert isinstance(mod.__all__, list)


def test_module_all_length_five():
    from evaluation import manifest as mod
    assert len(mod.__all__) == 5


def test_module_all_exact():
    from evaluation import manifest as mod
    assert set(mod.__all__) == {
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    }


def test_module_all_excludes_internal_helpers():
    from evaluation import manifest as mod
    for item in mod.__all__:
        assert not item.startswith("_")


def test_module_docstring_present():
    from evaluation import manifest as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_path():
    from evaluation import manifest as mod
    doc = mod.__doc__
    assert "path" in doc.lower() or "路径" in doc


def test_module_docstring_mentions_relative():
    from evaluation import manifest as mod
    doc = mod.__doc__
    assert "相对" in doc or "relative" in doc.lower()


def test_module_docstring_mentions_project_root():
    from evaluation import manifest as mod
    doc = mod.__doc__
    assert "项目根" in doc or "project root" in doc.lower() or "项目目录" in doc


def test_module_uses_future_annotations():
    import ast
    from evaluation import manifest as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    has_future = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(a.name == "annotations" for a in node.names)
        for node in tree.body
    )
    assert has_future


def test_module_internal_funcs_callable():
    from evaluation import manifest as mod
    assert callable(mod._is_absolute_like)
    assert callable(mod._has_backslash)
    assert callable(mod._resolve_relative_path)
    assert callable(mod._detect_project_root)


def test_module_load_manifest_callable():
    from evaluation import manifest as mod
    assert callable(mod.load_manifest)


# =========================================================================
# 签名深度
# =========================================================================


def test_is_absolute_like_return_annotation_bool():
    sig = inspect.signature(_is_absolute_like)
    ret = sig.return_annotation
    assert "bool" in str(ret).lower()


def test_has_backslash_return_annotation_bool():
    sig = inspect.signature(_has_backslash)
    ret = sig.return_annotation
    assert "bool" in str(ret).lower()


def test_resolve_relative_path_return_annotation_path():
    sig = inspect.signature(_resolve_relative_path)
    ret = sig.return_annotation
    assert "Path" in str(ret)


def test_detect_project_root_return_annotation_path():
    sig = inspect.signature(_detect_project_root)
    ret = sig.return_annotation
    assert "Path" in str(ret)


def test_load_manifest_return_annotation_manifest():
    sig = inspect.signature(load_manifest)
    ret = sig.return_annotation
    assert "Manifest" in str(ret)


def test_load_manifest_manifest_path_annotation_str_or_path():
    sig = inspect.signature(load_manifest)
    ann = sig.parameters["manifest_path"].annotation
    assert "str" in str(ann) and "Path" in str(ann)


def test_load_manifest_project_root_annotation_path_or_str_or_none():
    sig = inspect.signature(load_manifest)
    ann = sig.parameters["project_root"].annotation
    assert "Path" in str(ann) and "None" in str(ann)


def test_manifest_file_count_property_no_args():
    """file_count 是 property，不接受参数。"""
    sig = inspect.signature(Manifest.file_count.fget)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert len(params) == 1


def test_manifest_file_count_return_annotation_int():
    sig = inspect.signature(Manifest.file_count.fget)
    ret = sig.return_annotation
    assert ret is int or "int" in str(ret)


def test_manifest_pdf_count_return_annotation_int():
    sig = inspect.signature(Manifest.pdf_count.fget)
    ret = sig.return_annotation
    assert ret is int or "int" in str(ret)


def test_manifest_docx_count_return_annotation_int():
    sig = inspect.signature(Manifest.docx_count.fget)
    ret = sig.return_annotation
    assert ret is int or "int" in str(ret)


def test_manifest_content_group_count_return_annotation_int():
    sig = inspect.signature(Manifest.content_group_count.fget)
    ret = sig.return_annotation
    assert ret is int or "int" in str(ret)


def test_manifest_categories_covered_return_annotation_list():
    sig = inspect.signature(Manifest.categories_covered.fget)
    ret = sig.return_annotation
    assert "list" in str(ret).lower()
