r"""evaluation/manifest.py 边角测试 - 第九轮（Round 209）。

补强已有 base/edges/edges2-8（共 ~953 测试）未覆盖的深度：
- 模块结构 / __all__ exact / imports 完整集合
- ManifestError 类层级（Exception 子类）/ args 透传
- DocumentEntry 字段类型注解 + 默认值矩阵
- ExpectedFailure 字段类型注解 + 默认值
- Manifest dataclass 字段数 / 类型 / frozen 行为
- _is_absolute_like 穷举边界（多字符盘符 / 单字母无 separator / 1 字符 / 非 ASCII）
- _has_backslash 边界（仅反斜杠 / 混合多次）
- _resolve_relative_path 返回 Path / resolves symlinks
- load_manifest project_root 是 Path 对象 / None 自动检测
- load_manifest documents 缺字段默认值
- load_manifest manifest_version 字段读取
- Manifest properties 类型 / 行为
- 综合行为 / 不可变性
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path

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
# 模块结构
# =========================================================================


def test_module_all_exact_set():
    import evaluation.manifest as m
    assert set(m.__all__) == {
        "ManifestError", "Manifest", "DocumentEntry",
        "ExpectedFailure", "load_manifest",
    }


def test_module_all_is_list():
    import evaluation.manifest as m
    assert isinstance(m.__all__, list)


def test_module_all_length_is_five():
    import evaluation.manifest as m
    assert len(m.__all__) == 5


def test_module_imports_json():
    import evaluation.manifest as m
    assert hasattr(m, "json")


def test_module_imports_dataclass():
    import evaluation.manifest as m
    assert hasattr(m, "dataclass")


def test_module_imports_path():
    import evaluation.manifest as m
    assert hasattr(m, "Path")


def test_module_imports_any():
    import evaluation.manifest as m
    assert hasattr(m, "Any")


def test_module_imports_manifest_version():
    import evaluation.manifest as m
    assert hasattr(m, "MANIFEST_VERSION")


def test_module_imports_validate():
    import evaluation.manifest as m
    assert hasattr(m, "validate")


def test_module_docstring_present():
    import evaluation.manifest as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_invariants():
    import evaluation.manifest as m
    doc = m.__doc__
    assert "相对路径" in doc
    assert "绝对路径" in doc
    assert "正斜杠" in doc


def test_module_uses_future_annotations():
    import evaluation.manifest as m
    sig = inspect.signature(m.load_manifest)
    assert isinstance(sig.return_annotation, str)


def test_module_no_silence_unused():
    import evaluation.manifest as m
    assert not hasattr(m, "_silence_unused_import")


def test_module_internal_helpers_present():
    import evaluation.manifest as m
    for name in ("_is_absolute_like", "_has_backslash", "_resolve_relative_path", "_detect_project_root"):
        assert hasattr(m, name), name


# =========================================================================
# ManifestError
# =========================================================================


def test_manifest_error_is_class():
    assert isinstance(ManifestError, type)


def test_manifest_error_is_exception_subclass():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_can_be_instantiated():
    e = ManifestError("msg")
    assert isinstance(e, ManifestError)


def test_manifest_error_str_returns_message():
    e = ManifestError("specific error")
    assert str(e) == "specific error"


def test_manifest_error_args_preserved():
    e = ManifestError("a", "b", "c")
    assert e.args == ("a", "b", "c")


def test_manifest_error_no_args():
    e = ManifestError()
    assert e.args == ()


def test_manifest_error_can_be_raised_and_caught():
    with pytest.raises(ManifestError) as exc_info:
        raise ManifestError("boom")
    assert "boom" in str(exc_info.value)


def test_manifest_error_caught_as_exception():
    """ManifestError 是 Exception 子类，可被裸 except/Exception 捕获。"""
    with pytest.raises(Exception):
        raise ManifestError("x")


def test_manifest_error_not_value_error():
    assert not issubclass(ManifestError, ValueError)


def test_manifest_error_not_key_error():
    assert not issubclass(ManifestError, KeyError)


# =========================================================================
# DocumentEntry dataclass 深度
# =========================================================================


def test_document_entry_is_dataclass():
    assert is_dataclass(DocumentEntry)


def test_document_entry_is_frozen_dataclass():
    """dataclass(frozen=True) → setattr 触发 FrozenInstanceError。"""
    de = DocumentEntry(
        doc_id="d1", path_str="a/b.pdf", resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        de.doc_id = "x"


def test_document_entry_field_count_is_ten():
    de_fields = fields(DocumentEntry)
    assert len(de_fields) == 10


def test_document_entry_field_names_exact():
    de_fields = fields(DocumentEntry)
    names = [f.name for f in de_fields]
    assert names == [
        "doc_id", "path_str", "resolved_path", "source_type",
        "sha256", "categories", "paired_with",
        "annotation_file_str", "annotation_resolved", "expectations",
    ]


def test_document_entry_field_types():
    """字段类型注解（future annotations 让 type 变 str）。"""
    de_fields = {f.name: f for f in fields(DocumentEntry)}
    assert de_fields["doc_id"].type == "str"
    assert de_fields["path_str"].type == "str"
    assert de_fields["resolved_path"].type == "Path"
    assert de_fields["source_type"].type == "str"
    assert de_fields["sha256"].type == "str | None"
    assert de_fields["categories"].type == "tuple[str, ...]"
    assert de_fields["paired_with"].type == "str | None"
    assert de_fields["annotation_file_str"].type == "str | None"
    assert de_fields["annotation_resolved"].type == "Path | None"
    assert de_fields["expectations"].type == "dict[str, Any] | None"


def test_document_entry_construction_minimal():
    de = DocumentEntry(
        doc_id="d1", path_str="a/b.pdf", resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    assert de.doc_id == "d1"


def test_document_entry_construction_full():
    de = DocumentEntry(
        doc_id="d1", path_str="a/b.pdf", resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf", sha256="abc", categories=("c1", "c2"),
        paired_with="d2", annotation_file_str="a/ann.json",
        annotation_resolved=Path("/tmp/a/ann.json"),
        expectations={"k": "v"},
    )
    assert de.sha256 == "abc"
    assert de.categories == ("c1", "c2")
    assert de.paired_with == "d2"
    assert de.expectations == {"k": "v"}


def test_document_entry_equality():
    de1 = DocumentEntry(
        doc_id="d1", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d1", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    assert de1 == de2


def test_document_entry_inequality_different_field():
    de1 = DocumentEntry(
        doc_id="d1", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d2", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    assert de1 != de2


def test_document_entry_hashable():
    de = DocumentEntry(
        doc_id="d1", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    assert hash(de) is not None
    s = {de}
    assert de in s


# =========================================================================
# ExpectedFailure dataclass 深度
# =========================================================================


def test_expected_failure_is_dataclass():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_field_count_is_five():
    ef_fields = fields(ExpectedFailure)
    assert len(ef_fields) == 5


def test_expected_failure_field_names_exact():
    ef_fields = fields(ExpectedFailure)
    names = [f.name for f in ef_fields]
    assert names == ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]


def test_expected_failure_field_types():
    ef_fields = {f.name: f for f in fields(ExpectedFailure)}
    assert ef_fields["doc_id"].type == "str"
    assert ef_fields["path_str"].type == "str"
    assert ef_fields["resolved_path"].type == "Path"
    assert ef_fields["expected_error_code"].type == "str"
    assert ef_fields["source_type"].type == "str | None"


def test_expected_failure_frozen():
    ef = ExpectedFailure(
        doc_id="d1", path_str="a", resolved_path=Path("/a"),
        expected_error_code="file_not_found", source_type=None,
    )
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "x"


def test_expected_failure_hashable():
    ef = ExpectedFailure(
        doc_id="d1", path_str="a", resolved_path=Path("/a"),
        expected_error_code="x", source_type=None,
    )
    assert hash(ef) is not None


def test_expected_failure_equality():
    ef1 = ExpectedFailure(
        doc_id="d1", path_str="a", resolved_path=Path("/a"),
        expected_error_code="x", source_type=None,
    )
    ef2 = ExpectedFailure(
        doc_id="d1", path_str="a", resolved_path=Path("/a"),
        expected_error_code="x", source_type=None,
    )
    assert ef1 == ef2


# =========================================================================
# Manifest dataclass 深度
# =========================================================================


def test_manifest_is_dataclass():
    assert is_dataclass(Manifest)


def test_manifest_field_count_is_five():
    m_fields = fields(Manifest)
    assert len(m_fields) == 5


def test_manifest_field_names_exact():
    m_fields = fields(Manifest)
    names = [f.name for f in m_fields]
    assert names == [
        "manifest_version", "devset_status",
        "documents", "expected_failures", "project_root",
    ]


def test_manifest_field_types():
    m_fields = {f.name: f for f in fields(Manifest)}
    assert m_fields["manifest_version"].type == "str"
    assert m_fields["devset_status"].type == "str"
    assert m_fields["documents"].type == "tuple[DocumentEntry, ...]"
    assert m_fields["expected_failures"].type == "tuple[ExpectedFailure, ...]"
    assert m_fields["project_root"].type == "Path"


def test_manifest_frozen():
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(), project_root=Path("/x"),
    )
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"


def test_manifest_hashable():
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(), project_root=Path("/x"),
    )
    assert hash(m) is not None


# =========================================================================
# Manifest properties 深度
# =========================================================================


def _make_manifest(documents=None, expected_failures=None):
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=tuple(documents or []),
        expected_failures=tuple(expected_failures or []),
        project_root=Path("/tmp"),
    )


def _make_doc(doc_id="d1", source_type="pdf", categories=(), paired_with=None):
    return DocumentEntry(
        doc_id=doc_id, path_str=f"a/{doc_id}.x", resolved_path=Path(f"/tmp/a/{doc_id}.x"),
        source_type=source_type, sha256=None, categories=categories,
        paired_with=paired_with, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )


def test_manifest_file_count_returns_int():
    m = _make_manifest([_make_doc(), _make_doc("d2")])
    assert isinstance(m.file_count, int)


def test_manifest_file_count_zero():
    m = _make_manifest([])
    assert m.file_count == 0


def test_manifest_pdf_count_zero_when_no_pdf():
    m = _make_manifest([_make_doc(source_type="docx")])
    assert m.pdf_count == 0


def test_manifest_docx_count_zero_when_no_docx():
    m = _make_manifest([_make_doc(source_type="pdf")])
    assert m.docx_count == 0


def test_manifest_pdf_count_returns_int():
    m = _make_manifest([_make_doc(source_type="pdf")])
    assert isinstance(m.pdf_count, int)


def test_manifest_docx_count_returns_int():
    m = _make_manifest([_make_doc(source_type="docx")])
    assert isinstance(m.docx_count, int)


def test_manifest_content_group_count_returns_int():
    m = _make_manifest([_make_doc()])
    assert isinstance(m.content_group_count, int)


def test_manifest_content_group_count_single_unpaired():
    m = _make_manifest([_make_doc()])
    assert m.content_group_count == 1


def test_manifest_categories_covered_returns_list():
    m = _make_manifest([_make_doc(categories=("a",))])
    assert isinstance(m.categories_covered, list)


def test_manifest_categories_covered_empty_when_no_categories():
    m = _make_manifest([_make_doc(categories=())])
    assert m.categories_covered == []


def test_manifest_categories_covered_sorted_alphabetically():
    m = _make_manifest([_make_doc(categories=("z", "a", "m"))])
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_dedup_across_docs():
    m = _make_manifest([
        _make_doc("d1", categories=("a", "b")),
        _make_doc("d2", categories=("b", "c")),
    ])
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_categories_covered_no_docs():
    m = _make_manifest([])
    assert m.categories_covered == []


# =========================================================================
# _is_absolute_like 穷举（补充未覆盖边界）
# =========================================================================


def test_is_absolute_like_signature():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters)
    assert params == ["path_str"]


def test_is_absolute_like_return_annotation_is_bool_str():
    sig = inspect.signature(_is_absolute_like)
    assert sig.return_annotation == "bool"


def test_is_absolute_like_callable():
    assert callable(_is_absolute_like)


def test_is_absolute_like_normal_relative_path():
    assert _is_absolute_like("folder/file.pdf") is False


def test_is_absolute_like_dot_only():
    assert _is_absolute_like(".") is False


def test_is_absolute_like_double_dot():
    assert _is_absolute_like("..") is False


def test_is_absolute_like_filename_only():
    assert _is_absolute_like("file.pdf") is False


def test_is_absolute_like_two_chars_no_colon():
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_three_chars_no_colon():
    assert _is_absolute_like("abc") is False


def test_is_absolute_like_uppercase_drive_with_separator():
    assert _is_absolute_like("C:\\foo") is True


def test_is_absolute_like_lowercase_drive_with_separator():
    assert _is_absolute_like("c:/foo") is True


def test_is_absolute_like_drive_letter_no_separator():
    """'C:foo' 不是绝对路径（Windows relative drive）。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_colon_only():
    assert _is_absolute_like(":") is False


def test_is_absolute_like_colon_slash():
    assert _is_absolute_like(":/foo") is False


def test_is_absolute_like_just_colon_slash_three_chars():
    """长度恰好 3 但 path_str[0]=':' 不是字母 → False。"""
    assert _is_absolute_like(":/x") is False


def test_is_absolute_like_two_letters_with_colon_no_sep():
    assert _is_absolute_like("a:b") is False


def test_is_absolute_like_digit_drive_with_separator():
    """'1:\\foo' —— path_str[0]='1'.isalpha() → False。"""
    assert _is_absolute_like("1:\\foo") is False


def test_is_absolute_like_underscore_drive():
    """'_:/foo' —— '_'.isalpha() → False。"""
    assert _is_absolute_like("_:/foo") is False


def test_is_absolute_like_unicode_letter_drive():
    """'中:/foo' —— '中'.isalpha() → True → absolute。"""
    assert _is_absolute_like("中:/foo") is True


def test_is_absolute_like_space_relative():
    assert _is_absolute_like(" path/file") is False


def test_is_absolute_like_single_char():
    assert _is_absolute_like("a") is False


# =========================================================================
# _has_backslash 穷举
# =========================================================================


def test_has_backslash_signature():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters)
    assert params == ["path_str"]


def test_has_backslash_return_annotation_is_bool_str():
    sig = inspect.signature(_has_backslash)
    assert sig.return_annotation == "bool"


def test_has_backslash_callable():
    assert callable(_has_backslash)


def test_has_backslash_empty_string():
    assert _has_backslash("") is False


def test_has_backslash_no_backslash():
    assert _has_backslash("a/b/c") is False


def test_has_backslash_single_backslash():
    assert _has_backslash("a\\b") is True


def test_has_backslash_multiple_backslashes():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_only_backslash():
    assert _has_backslash("\\") is True


def test_has_backslash_trailing_backslash():
    assert _has_backslash("a\\") is True


def test_has_backslash_leading_backslash():
    """单个反斜杠开头 → 既被 _is_absolute_like 拒，也被 _has_backslash 拒。"""
    assert _has_backslash("\\a") is True


def test_has_backslash_mixed_separators():
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_filename_with_backslash():
    assert _has_backslash("file\\name.pdf") is True


# =========================================================================
# _resolve_relative_path 深度
# =========================================================================


def test_resolve_relative_path_signature():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters)
    assert params == ["path_str", "project_root", "field_name"]


def test_resolve_relative_path_return_annotation_is_path_str():
    sig = inspect.signature(_resolve_relative_path)
    assert sig.return_annotation == "Path"


def test_resolve_relative_path_callable():
    assert callable(_resolve_relative_path)


def test_resolve_relative_path_returns_path_instance(tmp_path):
    """合法路径返回 Path 实例。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    p = _resolve_relative_path("sub", tmp_path, "test")
    assert isinstance(p, Path)


def test_resolve_relative_path_returns_absolute_path(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    p = _resolve_relative_path("sub", tmp_path, "test")
    assert p.is_absolute()


def test_resolve_relative_path_dotdot_within_root(tmp_path):
    """a/../b 在 root 内 → OK。"""
    a = tmp_path / "a"
    a.mkdir()
    b = tmp_path / "b"
    b.mkdir()
    p = _resolve_relative_path("a/../b", tmp_path, "test")
    assert p == b.resolve()


def test_resolve_relative_path_empty_raises(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "f")
    assert "为空" in str(exc_info.value)


def test_resolve_relative_path_absolute_posix_raises(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/etc/passwd", tmp_path, "f")
    assert "绝对路径" in str(exc_info.value)


def test_resolve_relative_path_absolute_windows_raises(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("C:\\foo", tmp_path, "f")
    assert "绝对路径" in str(exc_info.value)


def test_resolve_relative_path_backslash_raises(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("a\\b", tmp_path, "f")
    assert "正斜杠" in str(exc_info.value)


def test_resolve_relative_path_field_name_in_message(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("a\\b", tmp_path, "my_field")
    assert "my_field" in str(exc_info.value)


def test_resolve_relative_path_outside_root_raises(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("../outside", tmp_path, "f")
    assert "项目根目录之外" in str(exc_info.value)


# =========================================================================
# _detect_project_root 深度
# =========================================================================


def test_detect_project_root_signature():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters)
    assert params == ["start"]


def test_detect_project_root_return_annotation_is_path_str():
    sig = inspect.signature(_detect_project_root)
    assert sig.return_annotation == "Path"


def test_detect_project_root_callable():
    assert callable(_detect_project_root)


def test_detect_project_root_from_file(tmp_path):
    """从文件向上找 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    f = tmp_path / "x.txt"
    f.write_text("x", encoding="utf-8")
    assert _detect_project_root(f) == tmp_path.resolve()


def test_detect_project_root_from_dir(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    assert _detect_project_root(sub) == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_start(tmp_path):
    """找不到 pyproject.toml → 返回 start 的目录形式。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    result = _detect_project_root(sub)
    assert result == sub.resolve()


def test_detect_project_root_picks_nearest_pyproject(tmp_path):
    """多个 pyproject.toml 链 → 取最近的（start 那层先扫）。"""
    (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "pyproject.toml").write_text("y", encoding="utf-8")
    deep = nested / "deep"
    deep.mkdir()
    # deep 的最近祖先是 nested
    assert _detect_project_root(deep) == nested.resolve()


# =========================================================================
# load_manifest 深度
# =========================================================================


def _write_manifest(tmp_path: Path, documents=None, expected_failures=None,
                    manifest_version="1.0", devset_status="incomplete",
                    extra_top_keys=None) -> Path:
    """写一个合法 manifest 文件。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    data = {
        "manifest_version": manifest_version,
        "devset_status": devset_status,
        "documents": documents or [],
        "expected_failures": expected_failures or [],
    }
    if extra_top_keys:
        data.update(extra_top_keys)
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_signature():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters)
    assert params == ["manifest_path", "project_root"]


def test_load_manifest_return_annotation_is_manifest_str():
    sig = inspect.signature(load_manifest)
    assert sig.return_annotation == "Manifest"


def test_load_manifest_project_root_default_none():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_load_manifest_callable():
    assert callable(load_manifest)


def test_load_manifest_accepts_path_str(tmp_path):
    p = _write_manifest(tmp_path)
    # 传 str 而不是 Path
    m = load_manifest(str(p))
    assert isinstance(m, Manifest)


def test_load_manifest_accepts_path_object(tmp_path):
    p = _write_manifest(tmp_path)
    m = load_manifest(p)
    assert isinstance(m, Manifest)


def test_load_manifest_project_root_as_path_object(tmp_path):
    p = _write_manifest(tmp_path)
    m = load_manifest(p, project_root=tmp_path)
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_project_root_as_str(tmp_path):
    p = _write_manifest(tmp_path)
    m = load_manifest(p, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_file_not_exists(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(tmp_path / "missing.json")
    assert "不存在" in str(exc_info.value)


def test_load_manifest_invalid_json(tmp_path):
    (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text("{not json}", encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p)
    assert "JSON 解析失败" in str(exc_info.value)


def test_load_manifest_returns_manifest_instance(tmp_path):
    p = _write_manifest(tmp_path)
    m = load_manifest(p)
    assert isinstance(m, Manifest)


def test_load_manifest_manifest_version_propagated(tmp_path):
    p = _write_manifest(tmp_path, manifest_version="1.0")
    m = load_manifest(p)
    assert m.manifest_version == "1.0"


def test_load_manifest_devset_status_propagated(tmp_path):
    p = _write_manifest(tmp_path, devset_status="complete")
    m = load_manifest(p)
    assert m.devset_status == "complete"


def test_load_manifest_empty_documents(tmp_path):
    p = _write_manifest(tmp_path, documents=[])
    m = load_manifest(p)
    assert m.documents == ()


def test_load_manifest_empty_expected_failures(tmp_path):
    p = _write_manifest(tmp_path, expected_failures=[])
    m = load_manifest(p)
    assert m.expected_failures == ()


def test_load_manifest_documents_as_tuple(tmp_path):
    """Manifest.documents 是 tuple，不是 list。"""
    p = _write_manifest(tmp_path, documents=[])
    m = load_manifest(p)
    assert isinstance(m.documents, tuple)


def test_load_manifest_expected_failures_as_tuple(tmp_path):
    p = _write_manifest(tmp_path, expected_failures=[])
    m = load_manifest(p)
    assert isinstance(m.expected_failures, tuple)


def test_load_manifest_project_root_resolved(tmp_path):
    p = _write_manifest(tmp_path)
    m = load_manifest(p)
    assert m.project_root.is_absolute()


def test_load_manifest_full_round_trip(tmp_path):
    (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").write_text("dummy", encoding="utf-8")
    p = _write_manifest(tmp_path, documents=[
        {
            "doc_id": "d1", "path": "samples/x.pdf", "source_type": "pdf",
            "categories": ["text"],
        },
    ])
    m = load_manifest(p)
    assert len(m.documents) == 1
    assert m.documents[0].doc_id == "d1"
    assert m.documents[0].source_type == "pdf"
    assert m.documents[0].categories == ("text",)
