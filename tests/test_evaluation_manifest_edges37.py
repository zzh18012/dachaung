"""evaluation/manifest.py 第三十七轮 edges 测试（Round 391）。

补强 edges36 未触及的角度：
- _is_absolute_like 数学边界第十批
- _has_backslash 数学边界第十批
- _resolve_relative_path 行为深度第十批
- _detect_project_root 行为深度第十批
- DocumentEntry/ExpectedFailure/Manifest dataclass 行为第十批
- Manifest properties algorithm 行为深度第十批
- load_manifest malformed data 第十批
- module source forbidden tokens 第十三批
- module source 字符串精确补强第八批
- signatures 第十批
- module 合理性第十批
- 端到端集成第十批
"""

from __future__ import annotations

import inspect
import json
import os
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path

import pytest

from evaluation import MANIFEST_VERSION, manifest as mmod
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


# ---------- _is_absolute_like 数学边界第十批 ----------


def test_is_absolute_like_empty_batch10():
    assert _is_absolute_like("") is False


def test_is_absolute_like_slash_only_batch10():
    """仅 '/' → 视为绝对路径（startswith '/'）→ True。"""
    assert _is_absolute_like("/") is True


def test_is_absolute_like_double_slash_batch10():
    """//foo 也 startswith '/' → True。"""
    assert _is_absolute_like("//foo") is True


def test_is_absolute_like_triple_slash_batch10():
    assert _is_absolute_like("///foo") is True


def test_is_absolute_like_uppercase_drive_posix_sep_batch10():
    assert _is_absolute_like("Z:/x") is True


def test_is_absolute_like_uppercase_drive_windows_sep_batch10():
    assert _is_absolute_like("Z:\\x") is True


def test_is_absolute_like_drive_lowercase_letter_batch10():
    """a:/ → drive + sep → True。"""
    assert _is_absolute_like("a:/x") is True


def test_is_absolute_like_drive_z_letter_batch10():
    """z:/ → drive + sep → True。"""
    assert _is_absolute_like("z:/x") is True


def test_is_absolute_like_unicode_first_letter_batch10():
    """Unicode 字母（中文）+ : → isalpha() True 但加 sep 也算绝对路径。"""
    # 注意：str.isalpha() 对 Unicode 字母也返 True
    # 例：'中:/foo' - 第一个字符 '中' isalpha() True，1:':'，2:'/'
    assert _is_absolute_like("中:/foo") is True


def test_is_absolute_like_digit_drive_not_absolute_batch10():
    """数字开头 + : → isalpha() False → 不是绝对路径。"""
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_underscore_drive_not_absolute_batch10():
    """下划线 isalpha() False → 不是绝对路径。"""
    assert _is_absolute_like("_:/foo") is False


def test_is_absolute_like_dot_drive_not_absolute_batch10():
    """.:/foo → '.'.isalpha() False → False。"""
    assert _is_absolute_like(".:/foo") is False


def test_is_absolute_like_dash_drive_not_absolute_batch10():
    assert _is_absolute_like("-:/foo") is False


def test_is_absolute_like_short_string_one_char_batch10():
    assert _is_absolute_like("a") is False


def test_is_absolute_like_short_string_two_chars_batch10():
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_just_colon_batch10():
    assert _is_absolute_like(":") is False


def test_is_absolute_like_just_colon_slash_batch10():
    """':/' - 第一个字符 ':' isalpha() False → False。"""
    assert _is_absolute_like(":/foo") is False


def test_is_absolute_like_returns_bool_type_batch10():
    assert isinstance(_is_absolute_like("foo"), bool)


def test_is_absolute_like_repeated_calls_batch10():
    """多次调用同一参数结果一致。"""
    for _ in range(5):
        assert _is_absolute_like("/x") is True
    for _ in range(5):
        assert _is_absolute_like("foo") is False


# ---------- _has_backslash 数学边界第十批 ----------


def test_has_backslash_empty_batch10():
    assert _has_backslash("") is False


def test_has_backslash_single_backslash_batch10():
    assert _has_backslash("\\") is True


def test_has_backslash_no_backslash_batch10():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_with_backslash_batch10():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_starts_with_backslash_batch10():
    assert _has_backslash("\\foo") is True


def test_has_backslash_ends_with_backslash_batch10():
    assert _has_backslash("foo\\") is True


def test_has_backslash_unicode_with_backslash_batch10():
    assert _has_backslash("中文\\路径") is True


def test_has_backslash_unicode_no_backslash_batch10():
    assert _has_backslash("中文/路径") is False


def test_has_backslash_mixed_separators_batch10():
    assert _has_backslash("foo/bar\\baz") is True


def test_has_backslash_only_backslashes_batch10():
    assert _has_backslash("\\\\\\") is True


def test_has_backslash_returns_bool_type_batch10():
    assert isinstance(_has_backslash("foo"), bool)


def test_has_backslash_long_string_no_backslash_batch10():
    assert _has_backslash("a" * 1000) is False


def test_has_backslash_long_string_with_backslash_at_end_batch10():
    assert _has_backslash("a" * 999 + "\\") is True


# ---------- _resolve_relative_path 行为深度第十批 ----------


def test_resolve_relative_path_empty_raises_batch10(tmp_path):
    with pytest.raises(ManifestError, match="为空"):
        _resolve_relative_path("", tmp_path, "test")


def test_resolve_relative_path_absolute_posix_raises_batch10(tmp_path):
    with pytest.raises(ManifestError, match="绝对路径"):
        _resolve_relative_path("/etc/passwd", tmp_path, "test")


def test_resolve_relative_path_absolute_windows_drive_raises_batch10(tmp_path):
    with pytest.raises(ManifestError, match="绝对路径"):
        _resolve_relative_path("C:/Users/foo", tmp_path, "test")


def test_resolve_relative_path_backslash_raises_batch10(tmp_path):
    with pytest.raises(ManifestError, match="反斜杠"):
        _resolve_relative_path("foo\\bar", tmp_path, "test")


def test_resolve_relative_path_normal_relative_resolves_batch10(tmp_path):
    out = _resolve_relative_path("foo/bar", tmp_path, "test")
    assert isinstance(out, Path)
    assert out.is_absolute()


def test_resolve_relative_path_returns_path_object_batch10(tmp_path):
    out = _resolve_relative_path("foo", tmp_path, "test")
    assert isinstance(out, Path)


def test_resolve_relative_path_dot_path_resolves_batch10(tmp_path):
    out = _resolve_relative_path(".", tmp_path, "test")
    assert out == tmp_path.resolve()


def test_resolve_relative_path_double_dot_escape_raises_batch10(tmp_path):
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("../foo", tmp_path, "test")


def test_resolve_relative_path_double_dot_escape_two_levels_raises_batch10(tmp_path):
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("../../foo", tmp_path, "test")


def test_resolve_relative_path_field_name_in_error_batch10(tmp_path):
    with pytest.raises(ManifestError, match="my_field"):
        _resolve_relative_path("", tmp_path, "my_field")


def test_resolve_relative_path_double_dot_in_middle_allowed_batch10(tmp_path):
    out = _resolve_relative_path("foo/../bar", tmp_path, "test")
    assert out == (tmp_path / "bar").resolve()


def test_resolve_relative_path_normal_path_with_subdir_batch10(tmp_path):
    out = _resolve_relative_path("a/b/c/d.txt", tmp_path, "test")
    assert out == (tmp_path / "a" / "b" / "c" / "d.txt").resolve()


def test_resolve_relative_path_returns_resolved_batch10(tmp_path):
    out = _resolve_relative_path("foo", tmp_path, "test")
    assert out == out.resolve()


def test_resolve_relative_path_unicode_filename_batch10(tmp_path):
    """Unicode 文件名（中文）能解析（不抛）。"""
    out = _resolve_relative_path("中文/文件.pdf", tmp_path, "test")
    assert isinstance(out, Path)
    assert "中文" in str(out) or "中文" in out.as_posix()


def test_resolve_relative_path_long_relative_batch10(tmp_path):
    """多级相对路径。"""
    out = _resolve_relative_path("a/b/c/d/e/f/g.txt", tmp_path, "test")
    assert out == (tmp_path / "a/b/c/d/e/f/g.txt").resolve()


def test_resolve_relative_path_one_segment_batch10(tmp_path):
    out = _resolve_relative_path("file.pdf", tmp_path, "test")
    assert out == (tmp_path / "file.pdf").resolve()


def test_resolve_relative_path_filename_with_dots_batch10(tmp_path):
    """filename with .. only as path level 1 - 试图逃出。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("..", tmp_path, "test")


def test_resolve_relative_path_filename_with_dot_only_batch10(tmp_path):
    """'.' 解析为 project_root 本身。"""
    out = _resolve_relative_path(".", tmp_path, "test")
    assert out == tmp_path.resolve()


# ---------- _detect_project_root 行为深度第十批 ----------


def test_detect_project_root_returns_path_object_batch10(tmp_path):
    out = _detect_project_root(tmp_path)
    assert isinstance(out, Path)


def test_detect_project_root_finds_pyproject_batch10(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_walks_up_batch10(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    out = _detect_project_root(nested)
    assert out == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_input_batch10(tmp_path):
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_start_is_file_batch10(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("hi", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    out = _detect_project_root(f)
    assert out == tmp_path.resolve()


def test_detect_project_root_with_str_input_raises_batch10(tmp_path):
    """_detect_project_root 仅接受 Path。"""
    with pytest.raises(AttributeError):
        _detect_project_root(str(tmp_path))  # type: ignore[arg-type]


def test_detect_project_root_idempotent_batch10(tmp_path):
    out1 = _detect_project_root(tmp_path)
    out2 = _detect_project_root(tmp_path)
    assert out1 == out2


def test_detect_project_root_deeply_nested_batch10(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c" / "d" / "e"
    deep.mkdir(parents=True)
    out = _detect_project_root(deep)
    assert out == tmp_path.resolve()


def test_detect_project_root_returns_resolved_batch10(tmp_path):
    """返回值总是 resolve() 后的路径。"""
    out = _detect_project_root(tmp_path)
    assert out == out.resolve()


def test_detect_project_root_first_pyproject_wins_batch10(tmp_path):
    """多个 pyproject.toml 时，最近的（深度最浅的）优先。"""
    (tmp_path / "pyproject.toml").write_text("outer", encoding="utf-8")
    nested = tmp_path / "a"
    nested.mkdir()
    (nested / "pyproject.toml").write_text("inner", encoding="utf-8")
    # 从 a/b 启动 → 找到 a/pyproject.toml
    deep = nested / "b"
    deep.mkdir()
    out = _detect_project_root(deep)
    assert out == nested.resolve()


# ---------- DocumentEntry/ExpectedFailure/Manifest dataclass 行为第十批 ----------


def _make_doc(doc_id="d1", path_str="a.pdf", source_type="pdf", categories=("normal",), paired_with=None, expectations=None):
    return DocumentEntry(
        doc_id=doc_id,
        path_str=path_str,
        resolved_path=Path("/tmp") / path_str,
        source_type=source_type,
        sha256=None,
        categories=tuple(categories),
        paired_with=paired_with,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=expectations,
    )


def _make_ef(doc_id="ef1", path_str="bad.pdf"):
    return ExpectedFailure(
        doc_id=doc_id,
        path_str=path_str,
        resolved_path=Path("/tmp") / path_str,
        expected_error_code="parse_failed",
        source_type="pdf",
    )


def _make_manifest(documents=None, expected_failures=None, project_root=None):
    return Manifest(
        manifest_version=MANIFEST_VERSION,
        devset_status="incomplete",
        documents=tuple(documents or []),
        expected_failures=tuple(expected_failures or []),
        project_root=project_root or Path("/tmp"),
    )


def test_document_entry_is_dataclass_batch10():
    assert is_dataclass(DocumentEntry)


def test_document_entry_is_frozen_batch10():
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "new"


def test_document_entry_field_count_batch10():
    f = fields(DocumentEntry)
    assert len(f) == 10


def test_document_entry_field_names_batch10():
    f = fields(DocumentEntry)
    names = [field.name for field in f]
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


def test_document_entry_equality_batch10():
    d1 = _make_doc()
    d2 = _make_doc()
    assert d1 == d2


def test_document_entry_inequality_batch10():
    d1 = _make_doc(doc_id="d1")
    d2 = _make_doc(doc_id="d2")
    assert d1 != d2


def test_document_entry_hash_batch10():
    d1 = _make_doc()
    d2 = _make_doc()
    assert hash(d1) == hash(d2)


def test_document_entry_in_set_batch10():
    d1 = _make_doc()
    d2 = _make_doc()
    s = {d1, d2}
    assert len(s) == 1  # frozen dataclass with equal hash


def test_document_entry_str_repr_batch10():
    d = _make_doc(doc_id="my_doc")
    s = repr(d)
    assert "my_doc" in s
    assert "DocumentEntry" in s


def test_expected_failure_is_dataclass_batch10():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_is_frozen_batch10():
    ef = _make_ef()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "new"


def test_expected_failure_field_count_batch10():
    f = fields(ExpectedFailure)
    assert len(f) == 5


def test_expected_failure_field_names_batch10():
    f = fields(ExpectedFailure)
    names = [field.name for field in f]
    assert names == ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]


def test_expected_failure_equality_batch10():
    ef1 = _make_ef()
    ef2 = _make_ef()
    assert ef1 == ef2


def test_expected_failure_hash_batch10():
    ef1 = _make_ef()
    ef2 = _make_ef()
    assert hash(ef1) == hash(ef2)


def test_expected_failure_in_set_batch10():
    ef1 = _make_ef()
    ef2 = _make_ef()
    s = {ef1, ef2}
    assert len(s) == 1


def test_manifest_is_dataclass_batch10():
    assert is_dataclass(Manifest)


def test_manifest_is_frozen_batch10():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"


def test_manifest_field_count_batch10():
    f = fields(Manifest)
    assert len(f) == 5


def test_manifest_field_names_batch10():
    f = fields(Manifest)
    names = [field.name for field in f]
    assert names == [
        "manifest_version",
        "devset_status",
        "documents",
        "expected_failures",
        "project_root",
    ]


def test_manifest_equality_batch10():
    m1 = _make_manifest()
    m2 = _make_manifest()
    assert m1 == m2


def test_manifest_inequality_batch10():
    m1 = _make_manifest()
    m2 = Manifest(
        manifest_version=MANIFEST_VERSION,
        devset_status="complete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m1 != m2


def test_manifest_hash_batch10():
    m1 = _make_manifest()
    m2 = _make_manifest()
    assert hash(m1) == hash(m2)


def test_manifest_in_set_batch10():
    m1 = _make_manifest()
    m2 = _make_manifest()
    s = {m1, m2}
    assert len(s) == 1


# ---------- Manifest properties algorithm 行为深度第十批 ----------


def test_manifest_file_count_zero_batch10():
    m = _make_manifest(documents=[])
    assert m.file_count == 0


def test_manifest_file_count_one_batch10():
    m = _make_manifest(documents=[_make_doc()])
    assert m.file_count == 1


def test_manifest_file_count_three_batch10():
    m = _make_manifest(documents=[_make_doc(), _make_doc(doc_id="d2"), _make_doc(doc_id="d3")])
    assert m.file_count == 3


def test_manifest_pdf_count_zero_batch10():
    m = _make_manifest(documents=[_make_doc(source_type="docx")])
    assert m.pdf_count == 0


def test_manifest_pdf_count_two_batch10():
    m = _make_manifest(documents=[_make_doc(), _make_doc(doc_id="d2")])
    assert m.pdf_count == 2


def test_manifest_docx_count_zero_batch10():
    m = _make_manifest(documents=[_make_doc()])
    assert m.docx_count == 0


def test_manifest_docx_count_two_batch10():
    m = _make_manifest(
        documents=[_make_doc(source_type="docx"), _make_doc(doc_id="d2", source_type="docx")]
    )
    assert m.docx_count == 2


def test_manifest_mixed_counts_batch10():
    m = _make_manifest(
        documents=[
            _make_doc(),
            _make_doc(doc_id="d2", source_type="docx"),
            _make_doc(doc_id="d3"),
        ]
    )
    assert m.pdf_count == 2
    assert m.docx_count == 1


def test_manifest_content_group_count_all_unpaired_batch10():
    m = _make_manifest(
        documents=[
            _make_doc(),
            _make_doc(doc_id="d2"),
        ]
    )
    assert m.content_group_count == 2


def test_manifest_content_group_count_paired_batch10():
    d1 = _make_doc(doc_id="d1", paired_with="d2")
    d2 = _make_doc(doc_id="d2", paired_with="d1")
    m = _make_manifest(documents=[d1, d2])
    assert m.content_group_count == 1


def test_manifest_content_group_count_single_direction_paired_batch10():
    d1 = _make_doc(doc_id="d1", paired_with="d2")
    d2 = _make_doc(doc_id="d2")
    m = _make_manifest(documents=[d1, d2])
    assert m.content_group_count == 1


def test_manifest_content_group_count_mixed_batch10():
    d1 = _make_doc(doc_id="d1", paired_with="d2")
    d2 = _make_doc(doc_id="d2", paired_with="d1")
    d3 = _make_doc(doc_id="d3")
    m = _make_manifest(documents=[d1, d2, d3])
    assert m.content_group_count == 2


def test_manifest_content_group_count_three_paired_batch10():
    d1 = _make_doc(doc_id="d1", paired_with="d2")
    d2 = _make_doc(doc_id="d2", paired_with="d1")
    d3 = _make_doc(doc_id="d3", paired_with="d1")
    m = _make_manifest(documents=[d1, d2, d3])
    assert m.content_group_count == 2


def test_manifest_categories_covered_empty_batch10():
    m = _make_manifest(documents=[])
    assert m.categories_covered == []


def test_manifest_categories_covered_single_doc_batch10():
    m = _make_manifest(documents=[_make_doc(categories=("normal",))])
    assert m.categories_covered == ["normal"]


def test_manifest_categories_covered_multiple_docs_union_batch10():
    d1 = _make_doc(categories=("normal", "edge"))
    d2 = _make_doc(doc_id="d2", categories=("edge", "extreme"))
    m = _make_manifest(documents=[d1, d2])
    assert m.categories_covered == ["edge", "extreme", "normal"]


def test_manifest_categories_covered_sorted_batch10():
    d1 = _make_doc(categories=("z", "a", "m"))
    m = _make_manifest(documents=[d1])
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_deduplication_batch10():
    d1 = _make_doc(categories=("normal", "edge"))
    d2 = _make_doc(doc_id="d2", categories=("normal", "edge"))
    m = _make_manifest(documents=[d1, d2])
    assert m.categories_covered == ["edge", "normal"]


def test_manifest_categories_covered_returns_list_batch10():
    m = _make_manifest(documents=[])
    assert isinstance(m.categories_covered, list)


def test_manifest_properties_return_correct_types_batch10():
    m = _make_manifest()
    assert isinstance(m.file_count, int)
    assert isinstance(m.pdf_count, int)
    assert isinstance(m.docx_count, int)
    assert isinstance(m.content_group_count, int)


def test_manifest_categories_covered_unicode_batch10():
    """categories 含 Unicode 字符。"""
    m = _make_manifest(documents=[_make_doc(categories=("中文", "edge"))])
    s = m.categories_covered
    assert "中文" in s
    assert "edge" in s


def test_manifest_categories_covered_empty_string_batch10():
    """空字符串 category 也算一个。"""
    m = _make_manifest(documents=[_make_doc(categories=("",))])
    assert m.categories_covered == [""]


# ---------- load_manifest malformed data 第十批 ----------


def _write_manifest(tmp_path, data):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_missing_file_raises_batch10(tmp_path):
    with pytest.raises(ManifestError, match="不存在"):
        load_manifest(tmp_path / "no.json", project_root=tmp_path)


def test_load_manifest_invalid_json_raises_batch10(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON 解析失败"):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_empty_dict_raises_batch10(tmp_path):
    from evaluation.schema import EvalSchemaError

    p = _write_manifest(tmp_path, {})
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_valid_minimal_returns_manifest_batch10(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    assert isinstance(out, Manifest)


def test_load_manifest_with_one_document_batch10(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [
                {
                    "doc_id": "d1",
                    "path": "foo/bar.pdf",
                    "source_type": "pdf",
                }
            ],
            "expected_failures": [],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    assert len(out.documents) == 1
    assert out.documents[0].doc_id == "d1"
    assert out.documents[0].source_type == "pdf"


def test_load_manifest_absolute_path_raises_batch10(tmp_path):
    from evaluation.schema import EvalSchemaError

    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [
                {
                    "doc_id": "d1",
                    "path": "/etc/passwd",
                    "source_type": "pdf",
                }
            ],
            "expected_failures": [],
        },
    )
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_backslash_path_raises_batch10(tmp_path):
    from evaluation.schema import EvalSchemaError

    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [
                {
                    "doc_id": "d1",
                    "path": "foo\\bar.pdf",
                    "source_type": "pdf",
                }
            ],
            "expected_failures": [],
        },
    )
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_path_outside_root_raises_batch10(tmp_path):
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [
                {
                    "doc_id": "d1",
                    "path": "../escape.pdf",
                    "source_type": "pdf",
                }
            ],
            "expected_failures": [],
        },
    )
    with pytest.raises(ManifestError, match="项目根目录之外|relative"):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_str_input_batch10(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    out = load_manifest(str(p), project_root=str(tmp_path))
    assert isinstance(out, Manifest)


def test_load_manifest_devset_status_complete_batch10(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "complete",
            "documents": [],
            "expected_failures": [],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    assert out.devset_status == "complete"


def test_load_manifest_with_categories_batch10(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [
                {
                    "doc_id": "d1",
                    "path": "foo.pdf",
                    "source_type": "pdf",
                    "categories": ["normal", "edge"],
                }
            ],
            "expected_failures": [],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].categories == ("normal", "edge")


def test_load_manifest_with_paired_with_batch10(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [
                {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
                {"doc_id": "d2", "path": "a.docx", "source_type": "docx", "paired_with": "d1"},
            ],
            "expected_failures": [],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].paired_with == "d2"


def test_load_manifest_with_expected_failures_batch10(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [
                {
                    "doc_id": "ef1",
                    "path": "bad.pdf",
                    "expected_error_code": "parse_failed",
                }
            ],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    assert len(out.expected_failures) == 1
    assert out.expected_failures[0].doc_id == "ef1"
    assert out.expected_failures[0].expected_error_code == "parse_failed"


def test_load_manifest_with_sha256_batch10(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [
                {
                    "doc_id": "d1",
                    "path": "a.pdf",
                    "source_type": "pdf",
                    "sha256": "a" * 64,
                }
            ],
            "expected_failures": [],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].sha256 == "a" * 64


def test_load_manifest_with_annotation_file_batch10(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [
                {
                    "doc_id": "d1",
                    "path": "a.pdf",
                    "source_type": "pdf",
                    "annotation_file": "annotations/a.json",
                }
            ],
            "expected_failures": [],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].annotation_file_str == "annotations/a.json"
    assert out.documents[0].annotation_resolved is not None


def test_load_manifest_with_expectations_batch10(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [
                {
                    "doc_id": "d1",
                    "path": "a.pdf",
                    "source_type": "pdf",
                    "expectations": {"element_count_by_type": {"paragraph": 5}},
                }
            ],
            "expected_failures": [],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_default_project_root_uses_detection_batch10(tmp_path):
    """project_root=None → 通过 _detect_project_root 自动检测。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    out = load_manifest(p)  # 不传 project_root
    assert isinstance(out, Manifest)
    assert out.project_root == tmp_path.resolve()


def test_load_manifest_returns_manifest_with_correct_version_batch10(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    assert out.manifest_version == MANIFEST_VERSION


def test_load_manifest_returns_documents_as_tuple_batch10(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    assert isinstance(out.documents, tuple)
    assert isinstance(out.expected_failures, tuple)


# ---------- module source forbidden tokens 第十三批 ----------


def test_manifest_source_no_os_system_batch10():
    source = inspect.getsource(mmod)
    assert "os.system" not in source


def test_manifest_source_no_subprocess_batch10():
    source = inspect.getsource(mmod)
    assert "subprocess.Popen" not in source
    assert "subprocess.check_call" not in source
    assert "subprocess.call" not in source


def test_manifest_source_no_pickle_load_batch10():
    source = inspect.getsource(mmod)
    assert "pickle.load" not in source


def test_manifest_source_no_yaml_load_batch10():
    source = inspect.getsource(mmod)
    assert "yaml.load" not in source


def test_manifest_source_no_eval_exec_batch10():
    source = inspect.getsource(mmod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_manifest_source_no_compile_batch10():
    source = inspect.getsource(mmod)
    assert "compile(" not in source


def test_manifest_source_no_sys_exit_batch10():
    source = inspect.getsource(mmod)
    assert "sys.exit" not in source
    assert "exit(" not in source
    assert "quit(" not in source


def test_manifest_source_no_global_keyword_batch10():
    source = inspect.getsource(mmod)
    assert "\nglobal " not in source


def test_manifest_source_no_async_def_batch10():
    source = inspect.getsource(mmod)
    assert "async def" not in source


def test_manifest_source_no_yield_batch10():
    source = inspect.getsource(mmod)
    assert "yield" not in source


def test_manifest_source_no_walrus_batch10():
    source = inspect.getsource(mmod)
    assert ":=" not in source


def test_manifest_source_no_rmtree_batch10():
    source = inspect.getsource(mmod)
    assert ".rmtree(" not in source


def test_manifest_source_no_unlink_remove_batch10():
    source = inspect.getsource(mmod)
    assert ".unlink(" not in source
    assert ".remove(" not in source


def test_manifest_source_no_logging_batch10():
    source = inspect.getsource(mmod)
    assert "logging" not in source
    assert "logger" not in source


def test_manifest_source_no_sleep_batch10():
    source = inspect.getsource(mmod)
    assert "time.sleep" not in source


def test_manifest_source_no_hardcoded_path_batch10():
    source = inspect.getsource(mmod)
    assert "C:\\\\Users" not in source
    assert "/Users/" not in source


# ---------- module source 字符串精确补强第八批 ----------


def test_module_source_has_future_annotations_batch10():
    source = inspect.getsource(mmod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_json_batch10():
    source = inspect.getsource(mmod)
    assert "import json" in source


def test_module_source_imports_dataclass_batch10():
    source = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in source


def test_module_source_imports_path_batch10():
    source = inspect.getsource(mmod)
    assert "from pathlib import Path" in source


def test_module_source_imports_typing_any_batch10():
    source = inspect.getsource(mmod)
    assert "from typing import Any" in source


def test_module_source_imports_manifest_version_batch10():
    source = inspect.getsource(mmod)
    assert "MANIFEST_VERSION" in source
    assert "from evaluation import" in source


def test_module_source_imports_validate_batch10():
    source = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in source


def test_module_source_has_manifest_error_class_batch10():
    source = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in source


def test_module_source_has_is_absolute_like_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in source


def test_module_source_has_has_backslash_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _has_backslash(" in source


def test_module_source_has_resolve_relative_path_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in source


def test_module_source_has_load_manifest_def_batch10():
    source = inspect.getsource(mmod)
    assert "def load_manifest(" in source


def test_module_source_has_detect_project_root_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _detect_project_root(" in source


def test_module_source_has_document_entry_dataclass_batch10():
    source = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in source
    assert "class DocumentEntry:" in source


def test_module_source_has_expected_failure_dataclass_batch10():
    source = inspect.getsource(mmod)
    assert "class ExpectedFailure:" in source


def test_module_source_has_manifest_dataclass_batch10():
    source = inspect.getsource(mmod)
    assert "class Manifest:" in source


def test_module_source_no_main_block_batch10():
    source = inspect.getsource(mmod)
    assert "if __name__" not in source


def test_module_source_uses_frozen_true_batch10():
    source = inspect.getsource(mmod)
    # 3 个 @dataclass(frozen=True)：DocumentEntry / ExpectedFailure / Manifest
    assert source.count("@dataclass(frozen=True)") == 3


def test_module_source_docstring_present_batch10():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 30


def test_module_source_docstring_mentions_path_batch10():
    assert "path" in mmod.__doc__.lower() or "路径" in mmod.__doc__


def test_module_source_docstring_mentions_relative_batch10():
    assert "相对" in mmod.__doc__ or "relative" in mmod.__doc__.lower()


def test_module_source_uses_relative_to_batch10():
    source = inspect.getsource(mmod)
    assert ".relative_to(" in source


def test_module_source_uses_resolve_batch10():
    source = inspect.getsource(mmod)
    assert ".resolve()" in source


def test_module_source_uses_isfile_batch10():
    source = inspect.getsource(mmod)
    assert ".is_file()" in source


def test_module_source_uses_pyproject_toml_batch10():
    source = inspect.getsource(mmod)
    assert '"pyproject.toml"' in source


def test_module_source_no_print_batch10():
    source = inspect.getsource(mmod)
    assert "print(" not in source


# ---------- signatures 第十批 ----------


def test_signature_is_absolute_like_param_count_batch10():
    sig = inspect.signature(_is_absolute_like)
    assert len(sig.parameters) == 1


def test_signature_is_absolute_like_param_name_batch10():
    sig = inspect.signature(_is_absolute_like)
    assert "path_str" in sig.parameters


def test_signature_is_absolute_like_param_kind_batch10():
    sig = inspect.signature(_is_absolute_like)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_is_absolute_like_return_annotation_batch10():
    sig = inspect.signature(_is_absolute_like)
    assert sig.return_annotation == "bool"


def test_signature_has_backslash_param_count_batch10():
    sig = inspect.signature(_has_backslash)
    assert len(sig.parameters) == 1


def test_signature_has_backslash_param_name_batch10():
    sig = inspect.signature(_has_backslash)
    assert "path_str" in sig.parameters


def test_signature_has_backslash_return_annotation_batch10():
    sig = inspect.signature(_has_backslash)
    assert sig.return_annotation == "bool"


def test_signature_resolve_relative_path_param_count_batch10():
    sig = inspect.signature(_resolve_relative_path)
    assert len(sig.parameters) == 3


def test_signature_resolve_relative_path_param_names_batch10():
    sig = inspect.signature(_resolve_relative_path)
    names = list(sig.parameters)
    assert names == ["path_str", "project_root", "field_name"]


def test_signature_resolve_relative_path_param_kinds_batch10():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_resolve_relative_path_return_annotation_batch10():
    sig = inspect.signature(_resolve_relative_path)
    assert sig.return_annotation == "Path"


def test_signature_load_manifest_param_count_batch10():
    sig = inspect.signature(load_manifest)
    assert len(sig.parameters) == 2


def test_signature_load_manifest_param_names_batch10():
    sig = inspect.signature(load_manifest)
    names = list(sig.parameters)
    assert names == ["manifest_path", "project_root"]


def test_signature_load_manifest_manifest_path_annotation_batch10():
    sig = inspect.signature(load_manifest)
    p = sig.parameters["manifest_path"]
    assert p.annotation == "Path | str"


def test_signature_load_manifest_project_root_annotation_batch10():
    sig = inspect.signature(load_manifest)
    p = sig.parameters["project_root"]
    assert p.annotation == "Path | str | None"


def test_signature_load_manifest_project_root_default_batch10():
    sig = inspect.signature(load_manifest)
    p = sig.parameters["project_root"]
    assert p.default is None


def test_signature_load_manifest_return_annotation_batch10():
    sig = inspect.signature(load_manifest)
    assert sig.return_annotation == "Manifest"


def test_signature_detect_project_root_param_count_batch10():
    sig = inspect.signature(_detect_project_root)
    assert len(sig.parameters) == 1


def test_signature_detect_project_root_param_name_batch10():
    sig = inspect.signature(_detect_project_root)
    assert "start" in sig.parameters


def test_signature_detect_project_root_param_annotation_batch10():
    sig = inspect.signature(_detect_project_root)
    p = list(sig.parameters.values())[0]
    assert p.annotation == "Path"


def test_signature_detect_project_root_return_annotation_batch10():
    sig = inspect.signature(_detect_project_root)
    assert sig.return_annotation == "Path"


def test_signature_5_funcs_are_function_type_batch10():
    for func in (_is_absolute_like, _has_backslash, _resolve_relative_path, load_manifest, _detect_project_root):
        assert inspect.isfunction(func)


def test_signature_5_funcs_module_eq_batch10():
    for func in (_is_absolute_like, _has_backslash, _resolve_relative_path, load_manifest, _detect_project_root):
        assert func.__module__ == "evaluation.manifest"


def test_signature_manifest_error_is_class_batch10():
    assert inspect.isclass(ManifestError)


def test_signature_manifest_error_subclass_exception_batch10():
    assert issubclass(ManifestError, Exception)


# ---------- module 合理性第十批 ----------


def test_module_all_attribute_value_batch10():
    assert set(mmod.__all__) == {
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    }


def test_module_all_is_list_batch10():
    assert isinstance(mmod.__all__, list)


def test_module_all_entries_unique_batch10():
    assert len(mmod.__all__) == len(set(mmod.__all__))


def test_module_has_dunder_file_batch10():
    assert hasattr(mmod, "__file__")
    assert mmod.__file__ is not None


def test_module_dunder_file_endswith_manifest_py_batch10():
    sep = os.sep
    assert mmod.__file__.endswith("evaluation" + sep + "manifest.py") or mmod.__file__.endswith(
        "evaluation/manifest.py"
    )


def test_module_dunder_name_batch10():
    assert mmod.__name__ == "evaluation.manifest"


def test_module_function_count_batch10():
    """5 module-level functions + 1 ManifestError class。"""
    funcs = [
        n
        for n, v in vars(mmod).items()
        if inspect.isfunction(v) and v.__module__ == mmod.__name__
    ]
    assert set(funcs) == {
        "_is_absolute_like",
        "_has_backslash",
        "_resolve_relative_path",
        "load_manifest",
        "_detect_project_root",
    }
    assert len(funcs) == 5


def test_module_class_count_batch10():
    """4 user classes：ManifestError / DocumentEntry / ExpectedFailure / Manifest。"""
    classes = [
        n for n, v in vars(mmod).items() if inspect.isclass(v) and v.__module__ == mmod.__name__
    ]
    assert set(classes) == {"ManifestError", "DocumentEntry", "ExpectedFailure", "Manifest"}
    assert len(classes) == 4


def test_module_no_call_at_top_level_batch10():
    source = inspect.getsource(mmod)
    lines = source.split("\n")
    for line in lines:
        if not line.startswith(" "):
            stripped = line.strip()
            ok_prefixes = (
                "def ",
                "import ",
                "from ",
                "__all__",
                "#",
                '"""',
                "'''",
                "",
                "@",
                "class ",
            )
            if stripped and not any(stripped.startswith(p) for p in ok_prefixes):
                if "(" in stripped:
                    raise AssertionError(f"unexpected top-level call: {line}")


def test_module_docstring_present_batch10():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 30


def test_module_docstring_in_chinese_batch10():
    """docstring 含中文（关键不变量描述）。"""
    assert "相对" in mmod.__doc__ or "路径" in mmod.__doc__


def test_module_public_api_via_all_batch10():
    """__all__ 包含公开 API。"""
    for name in ("ManifestError", "Manifest", "DocumentEntry", "ExpectedFailure", "load_manifest"):
        assert name in mmod.__all__


def test_module_internal_funcs_not_in_all_batch10():
    for name in ("_is_absolute_like", "_has_backslash", "_resolve_relative_path", "_detect_project_root"):
        assert name not in mmod.__all__


# ---------- 端到端集成第十批 ----------


def test_e2e_is_absolute_like_and_has_backslash_combined_batch10():
    """组合：absolute + backslash 同时为 True。"""
    assert _is_absolute_like("C:\\Users") is True
    assert _has_backslash("C:\\Users") is True


def test_e2e_resolve_relative_path_idempotent_batch10(tmp_path):
    out1 = _resolve_relative_path("foo", tmp_path, "test")
    out2 = _resolve_relative_path("foo", tmp_path, "test")
    assert out1 == out2


def test_e2e_load_manifest_no_unexpected_exceptions_batch10(tmp_path):
    """连续调用不抛异常。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    for _ in range(3):
        out = load_manifest(p, project_root=tmp_path)
        assert isinstance(out, Manifest)


def test_e2e_load_manifest_full_round_trip_batch10(tmp_path):
    """加载 manifest → 检查字段 → Manifest 不变。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [
                {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
                {"doc_id": "d2", "path": "b.docx", "source_type": "docx"},
            ],
            "expected_failures": [
                {"doc_id": "ef1", "path": "bad.pdf", "expected_error_code": "parse_failed"}
            ],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    assert out.manifest_version == MANIFEST_VERSION
    assert out.devset_status == "incomplete"
    assert len(out.documents) == 2
    assert len(out.expected_failures) == 1
    assert out.file_count == 2
    assert out.pdf_count == 1
    assert out.docx_count == 1


def test_e2e_module_can_be_imported_batch10():
    import evaluation.manifest as m
    assert m is mmod


def test_e2e_manifest_error_can_be_raised_and_caught_batch10():
    try:
        raise ManifestError("test")
    except ManifestError as e:
        assert "test" in str(e)
    except Exception:
        raise AssertionError("ManifestError not caught as itself")


def test_e2e_manifest_error_caught_as_exception_batch10():
    try:
        raise ManifestError("test")
    except Exception as e:
        assert isinstance(e, ManifestError)


def test_e2e_dataclass_equality_preserved_with_deep_copy_batch10():
    import copy

    d1 = _make_doc()
    d2 = copy.deepcopy(d1)
    assert d1 == d2


def test_e2e_load_manifest_json_serialize_round_trip_batch10(tmp_path):
    """加载 manifest 后字段值都能 JSON 序列化（除了 Path）。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    # 关键字段都能 JSON 序列化
    text = json.dumps({
        "manifest_version": out.manifest_version,
        "devset_status": out.devset_status,
        "documents_count": len(out.documents),
        "expected_failures_count": len(out.expected_failures),
    })
    parsed = json.loads(text)
    assert parsed["manifest_version"] == MANIFEST_VERSION
    assert parsed["documents_count"] == 0


def test_e2e_load_manifest_uses_project_root_for_path_resolution_batch10(tmp_path):
    """path 字段必须相对于 project_root 解析。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [
                {"doc_id": "d1", "path": "deep/nested/file.pdf", "source_type": "pdf"}
            ],
            "expected_failures": [],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    resolved = out.documents[0].resolved_path
    assert resolved == (tmp_path / "deep" / "nested" / "file.pdf").resolve()


def test_e2e_load_manifest_changing_devset_status_batch10(tmp_path):
    """不同 devset_status 都能加载。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    for status in ("incomplete", "complete"):
        p = _write_manifest(
            tmp_path,
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": status,
                "documents": [],
                "expected_failures": [],
            },
        )
        out = load_manifest(p, project_root=tmp_path)
        assert out.devset_status == status
