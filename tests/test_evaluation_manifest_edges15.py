r"""evaluation/manifest.py 边角测试 - 第十五轮（Round 247）。

补强已有 base/edges/edges2-14（共 ~1150+ 测试）未覆盖的深度：
- 模块 namespace identity：typing.Any / dataclass / Path / json / MANIFEST_VERSION / validate
- _resolve_relative_path 错误消息含 field_name 各种路径
- _detect_project_root 行为：start 是目录 / start 是文件 / 不存在 pyproject
- Manifest properties 类型精确
- DocumentEntry/ExpectedFailure dataclass fields() 精确
- categories_covered 大小写敏感、unicode、空字符串
- 模块源码字符串：docstring 含关键不变量
- 函数签名精确
- callable 验证
"""

from __future__ import annotations

import inspect
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
# 模块 namespace identity
# =========================================================================


def test_module_typing_any_in_namespace_identity():
    """typing.Any 在 evaluation.manifest 命名空间。"""
    import evaluation.manifest as m
    assert m.Any is Any


def test_module_dataclass_in_namespace_identity():
    """dataclass 装饰器在命名空间。"""
    import evaluation.manifest as m
    assert m.dataclass is dataclass


def test_module_path_in_namespace_identity():
    """Path 在命名空间。"""
    import evaluation.manifest as m
    assert m.Path is Path


def test_module_json_in_namespace_identity():
    """json 在命名空间。"""
    import evaluation.manifest as m
    import json as json_mod
    assert m.json is json_mod


def test_module_manifest_version_in_namespace():
    """MANIFEST_VERSION 在命名空间。"""
    import evaluation.manifest as m
    assert hasattr(m, "MANIFEST_VERSION")


def test_module_manifest_version_identity():
    """evaluation.manifest.MANIFEST_VERSION is evaluation.MANIFEST_VERSION。"""
    import evaluation.manifest as m
    assert m.MANIFEST_VERSION is MANIFEST_VERSION


def test_module_manifest_version_value():
    """MANIFEST_VERSION 是字符串。"""
    assert isinstance(MANIFEST_VERSION, str)
    assert "." in MANIFEST_VERSION


def test_module_validate_in_namespace():
    """validate 函数从 evaluation.schema 导入到命名空间。"""
    import evaluation.manifest as m
    from evaluation.schema import validate as schema_validate
    assert m.validate is schema_validate


# =========================================================================
# __all__ 精确
# =========================================================================


def test_module_all_is_list():
    """__all__ 是 list。"""
    import evaluation.manifest as m
    assert isinstance(m.__all__, list)


def test_module_all_exact_order():
    """__all__ 顺序精确 5 元素。"""
    import evaluation.manifest as m
    assert m.__all__ == [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ]


def test_module_all_length_five():
    """__all__ 5 个元素。"""
    import evaluation.manifest as m
    assert len(m.__all__) == 5


def test_module_all_no_duplicates():
    """__all__ 无重复。"""
    import evaluation.manifest as m
    assert len(m.__all__) == len(set(m.__all__))


def test_module_all_does_not_contain_private_helpers():
    """__all__ 不含私有 helper。"""
    import evaluation.manifest as m
    assert "_is_absolute_like" not in m.__all__
    assert "_has_backslash" not in m.__all__
    assert "_resolve_relative_path" not in m.__all__
    assert "_detect_project_root" not in m.__all__


def test_module_private_helpers_accessible():
    """私有 helper 仍可在命名空间访问。"""
    import evaluation.manifest as m
    assert callable(m._is_absolute_like)
    assert callable(m._has_backslash)
    assert callable(m._resolve_relative_path)
    assert callable(m._detect_project_root)


# =========================================================================
# 模块 docstring
# =========================================================================


def test_module_docstring_present():
    """模块有 docstring。"""
    import evaluation.manifest as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_relative_path():
    """docstring 提到相对路径约束。"""
    import evaluation.manifest as m
    doc = (m.__doc__ or "")
    assert "相对路径" in doc or "relative" in doc.lower()


def test_module_docstring_mentions_no_absolute():
    """docstring 提到拒绝绝对路径。"""
    import evaluation.manifest as m
    doc = (m.__doc__ or "")
    assert "绝对路径" in doc or "absolute" in doc.lower()


def test_module_docstring_mentions_no_backslash():
    """docstring 提到禁止反斜杠。"""
    import evaluation.manifest as m
    doc = (m.__doc__ or "")
    assert "反斜杠" in doc or "backslash" in doc.lower()


def test_module_docstring_mentions_project_root():
    """docstring 提到项目根。"""
    import evaluation.manifest as m
    doc = (m.__doc__ or "")
    assert "项目根" in doc or "project root" in doc.lower()


# =========================================================================
# ManifestError 详细
# =========================================================================


def test_manifest_error_subclass_of_exception():
    """ManifestError 是 Exception 子类。"""
    assert issubclass(ManifestError, Exception)


def test_manifest_error_not_subclass_of_value_error():
    """ManifestError 不继承 ValueError。"""
    assert not issubclass(ManifestError, ValueError)


def test_manifest_error_init_with_message():
    """ManifestError('msg') → args[0]='msg'。"""
    e = ManifestError("test message")
    assert e.args[0] == "test message"


def test_manifest_error_str_returns_message():
    """str(error) == message。"""
    e = ManifestError("hello")
    assert str(e) == "hello"


def test_manifest_error_repr_contains_class_name():
    """repr 含类名。"""
    e = ManifestError("msg")
    assert "ManifestError" in repr(e)


def test_manifest_error_can_be_raised_and_caught():
    """可 raise 与 except。"""
    with pytest.raises(ManifestError) as exc_info:
        raise ManifestError("test")
    assert "test" in str(exc_info.value)


def test_manifest_error_caught_as_exception():
    """可被通用 except Exception 捕获。"""
    try:
        raise ManifestError("msg")
    except Exception as e:
        assert isinstance(e, ManifestError)


# =========================================================================
# _is_absolute_like 边界
# =========================================================================


def test_is_absolute_like_empty_string_returns_false():
    """空字符串 → False。"""
    assert _is_absolute_like("") is False


def test_is_absolute_like_just_slash_returns_true():
    """'/' → True。"""
    assert _is_absolute_like("/") is True


def test_is_absolute_like_alpha_colon_backslash():
    """'C:\\' → True。"""
    assert _is_absolute_like("C:\\") is True


def test_is_absolute_like_alpha_colon_forward_slash():
    """'C:/' → True。"""
    assert _is_absolute_like("C:/") is True


def test_is_absolute_like_alpha_colon_only():
    """'C:' → False（缺分隔符）。"""
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_alpha_colon_letter():
    """'C:foo' → False（缺 / 或 \\）。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_digit_colon_backslash():
    """'1:\\' → False（数字非字母）。"""
    assert _is_absolute_like("1:\\") is False


def test_is_absolute_like_two_chars_only():
    """'ab' → False（长度 < 3）。"""
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_three_chars_no_colon():
    """'abc' → False（无 colon）。"""
    assert _is_absolute_like("abc") is False


# =========================================================================
# _has_backslash 边界
# =========================================================================


def test_has_backslash_empty_returns_false():
    assert _has_backslash("") is False


def test_has_backslash_forward_only_returns_false():
    assert _has_backslash("a/b/c") is False


def test_has_backslash_single_returns_true():
    assert _has_backslash("a\\b") is True


def test_has_backslash_multiple_returns_true():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_mixed_returns_true():
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_only_backslash_returns_true():
    assert _has_backslash("\\") is True


# =========================================================================
# _resolve_relative_path 错误消息含 field_name
# =========================================================================


def test_resolve_relative_path_empty_includes_field_name(tmp_path: Path):
    """空 path → ManifestError message 含 field_name。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "documents[test].path")
    assert "documents[test].path" in str(exc_info.value)


def test_resolve_relative_path_absolute_includes_field_name(tmp_path: Path):
    """绝对 path → message 含 field_name。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/etc/passwd", tmp_path, "documents[test].path")
    assert "documents[test].path" in str(exc_info.value)


def test_resolve_relative_path_backslash_includes_field_name(tmp_path: Path):
    """反斜杠 path → message 含 field_name。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("a\\b", tmp_path, "documents[test].path")
    assert "documents[test].path" in str(exc_info.value)


def test_resolve_relative_path_outside_root_includes_field_name(tmp_path: Path):
    """超出项目根的相对路径 → message 含 field_name。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("../../outside.txt", tmp_path, "documents[test].path")
    assert "documents[test].path" in str(exc_info.value)


def test_resolve_relative_path_success_returns_absolute(tmp_path: Path):
    """合法相对路径 → 返回绝对路径。"""
    out = _resolve_relative_path("a/b.pdf", tmp_path, "test")
    assert isinstance(out, Path)
    assert out.is_absolute()
    assert out == (tmp_path / "a" / "b.pdf").resolve()


def test_resolve_relative_path_success_under_project_root(tmp_path: Path):
    """返回的路径在 project_root 内。"""
    out = _resolve_relative_path("sub/file.pdf", tmp_path, "test")
    assert str(out).startswith(str(tmp_path.resolve()))


def test_resolve_relative_path_with_unicode_filename(tmp_path: Path):
    """unicode 文件名 OK。"""
    out = _resolve_relative_path("中文/文件.pdf", tmp_path, "test")
    assert out.name == "文件.pdf"


# =========================================================================
# _detect_project_root 边界
# =========================================================================


def test_detect_project_root_with_pyproject(tmp_path: Path):
    """目录含 pyproject.toml → 返回该目录。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_with_pyproject_in_parent(tmp_path: Path):
    """pyproject 在父目录 → 返回父目录。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    sub = tmp_path / "sub" / "deeper"
    sub.mkdir(parents=True)
    out = _detect_project_root(sub)
    assert out == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_start(tmp_path: Path):
    """无 pyproject.toml → 返回 start 自身（已在 start.parent 上）。"""
    sub = tmp_path / "noschema"
    sub.mkdir()
    out = _detect_project_root(sub)
    # 没有 pyproject → 返回 cur（start.resolve()）
    # start 是 sub 目录（不是文件）→ cur=sub
    assert out == sub.resolve()


def test_detect_project_root_start_is_file_returns_parent(tmp_path: Path):
    """start 是文件 → 返回父目录中含 pyproject 的。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    f = tmp_path / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    out = _detect_project_root(f)
    assert out == tmp_path.resolve()


def test_detect_project_root_returns_absolute_path(tmp_path: Path):
    """返回的是绝对路径。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out.is_absolute()


# =========================================================================
# DocumentEntry dataclass
# =========================================================================


def test_document_entry_is_frozen():
    """DocumentEntry 是 frozen dataclass。"""
    import dataclasses
    assert getattr(DocumentEntry, "__dataclass_params__").frozen is True


def test_document_entry_field_count_ten():
    """DocumentEntry 含 10 个 field。"""
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_field_names_exact():
    """DocumentEntry field 名字精确。"""
    names = [f.name for f in fields(DocumentEntry)]
    assert names == [
        "doc_id", "path_str", "resolved_path", "source_type",
        "sha256", "categories", "paired_with", "annotation_file_str",
        "annotation_resolved", "expectations",
    ]


def test_document_entry_hashable_with_dict_none():
    """expectations=None 时 hashable。"""
    de = DocumentEntry(
        doc_id="d1", path_str="a.pdf",
        resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256=None,
        categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    assert hash(de) is not None


# =========================================================================
# ExpectedFailure dataclass
# =========================================================================


def test_expected_failure_is_frozen():
    """ExpectedFailure 是 frozen dataclass。"""
    assert getattr(ExpectedFailure, "__dataclass_params__").frozen is True


def test_expected_failure_field_count_five():
    """ExpectedFailure 含 5 个 field。"""
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_field_names_exact():
    """ExpectedFailure field 名字精确。"""
    names = [f.name for f in fields(ExpectedFailure)]
    assert names == [
        "doc_id", "path_str", "resolved_path",
        "expected_error_code", "source_type",
    ]


def test_expected_failure_hashable():
    """ExpectedFailure hashable。"""
    ef = ExpectedFailure(
        doc_id="d1", path_str="a.pdf",
        resolved_path=Path("/tmp/a.pdf"),
        expected_error_code="err1",
        source_type=None,
    )
    assert hash(ef) is not None


# =========================================================================
# Manifest dataclass
# =========================================================================


def test_manifest_is_frozen():
    """Manifest 是 frozen dataclass。"""
    assert getattr(Manifest, "__dataclass_params__").frozen is True


def test_manifest_field_count_five():
    """Manifest 含 5 个 field。"""
    assert len(fields(Manifest)) == 5


def test_manifest_field_names_exact():
    """Manifest field 名字精确。"""
    names = [f.name for f in fields(Manifest)]
    assert names == [
        "manifest_version", "devset_status", "documents",
        "expected_failures", "project_root",
    ]


def _make_manifest(docs=(), expected_failures=()) -> Manifest:
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=tuple(docs),
        expected_failures=tuple(expected_failures),
        project_root=Path("/tmp"),
    )


def _make_doc_entry(doc_id="d1", source_type="pdf", categories=(),
                    paired_with=None, annotation_file_str=None) -> DocumentEntry:
    return DocumentEntry(
        doc_id=doc_id,
        path_str=f"{doc_id}.pdf",
        resolved_path=Path(f"/tmp/{doc_id}.pdf"),
        source_type=source_type,
        sha256=None,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=annotation_file_str,
        annotation_resolved=None,
        expectations=None,
    )


def test_manifest_properties_return_correct_types():
    """Manifest properties 返回正确类型。"""
    m = _make_manifest()
    assert isinstance(m.file_count, int)
    assert isinstance(m.pdf_count, int)
    assert isinstance(m.docx_count, int)
    assert isinstance(m.content_group_count, int)
    assert isinstance(m.categories_covered, list)


def test_manifest_file_count_zero_when_empty():
    """空 manifest → file_count=0。"""
    m = _make_manifest()
    assert m.file_count == 0


def test_manifest_pdf_count_zero_when_no_pdf():
    """无 PDF → pdf_count=0。"""
    m = _make_manifest([_make_doc_entry(source_type="docx")])
    assert m.pdf_count == 0
    assert m.docx_count == 1


def test_manifest_categories_covered_empty_when_no_categories():
    """无 categories → []."""
    m = _make_manifest()
    assert m.categories_covered == []


def test_manifest_categories_covered_sorted_unique():
    """categories_covered 是 sorted 且 unique。"""
    m = _make_manifest([
        _make_doc_entry(doc_id="d1", categories=("math", "science")),
        _make_doc_entry(doc_id="d2", categories=("science", "art")),
    ])
    assert m.categories_covered == ["art", "math", "science"]


def test_manifest_categories_covered_case_sensitive():
    """categories_covered 大小写敏感。"""
    m = _make_manifest([
        _make_doc_entry(doc_id="d1", categories=("Math",)),
        _make_doc_entry(doc_id="d2", categories=("math",)),
    ])
    assert m.categories_covered == ["Math", "math"]  # 不同 case


def test_manifest_categories_covered_unicode():
    """categories_covered unicode 处理。"""
    m = _make_manifest([
        _make_doc_entry(doc_id="d1", categories=("数学", "物理")),
    ])
    assert m.categories_covered == ["数学", "物理"]


# =========================================================================
# load_manifest signature
# =========================================================================


def test_load_manifest_signature_exact():
    """signature: (manifest_path, project_root=None)。"""
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters.keys()) == ["manifest_path", "project_root"]
    assert sig.parameters["project_root"].default is None


def test_load_manifest_signature_return_annotation():
    """return annotation 是 Manifest。"""
    sig = inspect.signature(load_manifest)
    assert isinstance(sig.return_annotation, str)
    assert "Manifest" in sig.return_annotation


def test_is_absolute_like_signature_exact():
    """signature: (path_str)。"""
    sig = inspect.signature(_is_absolute_like)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_has_backslash_signature_exact():
    """signature: (path_str)。"""
    sig = inspect.signature(_has_backslash)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_resolve_relative_path_signature_exact():
    """signature: (path_str, project_root, field_name)。"""
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters.keys()) == ["path_str", "project_root", "field_name"]


def test_detect_project_root_signature_exact():
    """signature: (start)。"""
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters.keys()) == ["start"]


# =========================================================================
# callable 验证
# =========================================================================


def test_manifest_error_callable_as_constructor():
    """ManifestError 可作为构造器。"""
    e = ManifestError("msg")
    assert isinstance(e, ManifestError)


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


# =========================================================================
# 端到端：load_manifest 完整流程
# =========================================================================


def test_load_manifest_missing_file_raises(tmp_path: Path):
    """manifest 文件不存在 → ManifestError。"""
    with pytest.raises(ManifestError):
        load_manifest(tmp_path / "missing.json")


def test_load_manifest_directory_raises(tmp_path: Path):
    """manifest 是目录 → ManifestError。"""
    with pytest.raises(ManifestError):
        load_manifest(tmp_path)


def test_load_manifest_invalid_json_raises(tmp_path: Path):
    """manifest 是非法 JSON → ManifestError。"""
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_load_manifest_returns_manifest_instance(tmp_path: Path):
    """合法 manifest → 返回 Manifest 实例。"""
    import json as json_mod
    m = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json_mod.dumps(m), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert isinstance(out, Manifest)


def test_load_manifest_propagates_manifest_version(tmp_path: Path):
    """manifest_version 透传到 Manifest。"""
    import json as json_mod
    m = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json_mod.dumps(m), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.manifest_version == MANIFEST_VERSION


def test_load_manifest_documents_is_tuple(tmp_path: Path):
    """documents 是 tuple（不是 list）。"""
    import json as json_mod
    m = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json_mod.dumps(m), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert isinstance(out.documents, tuple)
    assert isinstance(out.expected_failures, tuple)


def test_load_manifest_project_root_is_path(tmp_path: Path):
    """project_root 是 Path。"""
    import json as json_mod
    m = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json_mod.dumps(m), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert isinstance(out.project_root, Path)
    assert out.project_root.is_absolute()
