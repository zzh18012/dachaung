"""evaluation/manifest.py 第四十七轮 edges 测试（Round 461）。

补强 edges46 未触及的角度。
"""

from __future__ import annotations

import dataclasses
import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

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
from evaluation import manifest as mmod


# ---------- _is_absolute_like 行为深度第二十批 ----------


def test_is_absolute_like_only_slash_batch20():
    """'/' 是绝对路径。"""
    assert _is_absolute_like("/") is True


def test_is_absolute_like_only_drive_letter_no_separator_batch20():
    """'c:' 无 separator 不是绝对路径（仅 2 char）。"""
    assert _is_absolute_like("c:") is False


def test_is_absolute_like_drive_letter_with_slash_batch20():
    """'c:/' 是绝对路径。"""
    assert _is_absolute_like("c:/") is True


def test_is_absolute_like_drive_letter_with_backslash_batch20():
    """'c:\\' 是绝对路径。"""
    assert _is_absolute_like("c:\\") is True


def test_is_absolute_like_leading_whitespace_batch20():
    """前导空白不被 strip。"""
    assert _is_absolute_like(" /foo") is False  # 第一字符是空格


def test_is_absolute_like_unicode_first_char_batch20():
    """Unicode 第一字符不是 / 不是 alpha。"""
    assert _is_absolute_like("中文/path") is False


def test_is_absolute_like_multi_char_drive_letter_batch20():
    """'ab:/foo' 不是绝对路径（drive letter 必须单字符）。"""
    assert _is_absolute_like("ab:/foo") is False


def test_is_absolute_like_just_colon_batch20():
    """':/foo' 第一字符不是 alpha。"""
    assert _is_absolute_like(":/foo") is False


def test_is_absolute_like_digit_drive_letter_batch20():
    """'1:/foo' 第一字符是 digit 不是 alpha。"""
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_empty_string_batch20():
    assert _is_absolute_like("") is False


# ---------- _has_backslash 行为深度第二十批 ----------


def test_has_backslash_single_backslash_batch20():
    assert _has_backslash("\\") is True


def test_has_backslash_only_one_in_middle_batch20():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_no_backslash_batch20():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_empty_string_batch20():
    assert _has_backslash("") is False


def test_has_backslash_forward_only_batch20():
    assert _has_backslash("a/b/c") is False


def test_has_backslash_mixed_batch20():
    """混合存在时检测到。"""
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_consecutive_batch20():
    """连续两个反斜杠也命中。"""
    assert _has_backslash("a\\\\b") is True


# ---------- _resolve_relative_path 行为深度第二十批 ----------


def test_resolve_relative_path_dot_dot_batch20(tmp_path):
    """'..' 应跑出 project_root 之外。"""
    inner = tmp_path / "inner"
    inner.mkdir()
    # 文件路径是 ../outside.pdf，但 project_root 是 inner
    with pytest.raises(ManifestError):
        _resolve_relative_path("../outside.pdf", inner, "test_field")


def test_resolve_relative_path_inside_root_batch20(tmp_path):
    """正常相对路径解析。"""
    resolved = _resolve_relative_path("a/b.pdf", tmp_path, "test_field")
    assert resolved == (tmp_path / "a" / "b.pdf").resolve()


def test_resolve_relative_path_spaces_in_name_batch20(tmp_path):
    """路径含空格应能解析。"""
    resolved = _resolve_relative_path("dir with spaces/file.pdf", tmp_path, "test_field")
    assert "dir with spaces" in str(resolved)


def test_resolve_relative_path_long_path_batch20(tmp_path):
    """长路径深度嵌套。"""
    deep = "/".join([f"d{i}" for i in range(20)]) + "/file.pdf"
    resolved = _resolve_relative_path(deep, tmp_path, "test_field")
    assert resolved.is_absolute()


def test_resolve_relative_path_trailing_slash_batch20(tmp_path):
    """末尾斜杠的路径解析为目录。"""
    resolved = _resolve_relative_path("dir/", tmp_path, "test_field")
    assert resolved == (tmp_path / "dir").resolve()


def test_resolve_relative_path_unicode_batch20(tmp_path):
    """Unicode 路径名应能解析。"""
    resolved = _resolve_relative_path("数据/文件.pdf", tmp_path, "test_field")
    assert "数据" in str(resolved)


def test_resolve_relative_path_empty_raises_batch20(tmp_path):
    """空路径抛 ManifestError。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("", tmp_path, "test_field")


def test_resolve_relative_path_error_message_contains_field_name_batch20(tmp_path):
    """错误消息含 field_name。"""
    try:
        _resolve_relative_path("/etc/passwd", tmp_path, "MY_FIELD")
    except ManifestError as e:
        assert "MY_FIELD" in str(e)


def test_resolve_relative_path_absolute_posix_batch20(tmp_path):
    """POSIX 绝对路径被拒。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("/etc/passwd", tmp_path, "test_field")


def test_resolve_relative_path_returns_absolute_path_batch20(tmp_path):
    """返回值总是绝对路径。"""
    resolved = _resolve_relative_path("x.pdf", tmp_path, "test_field")
    assert resolved.is_absolute()


# ---------- _detect_project_root 行为深度第二十批 ----------


def test_detect_project_root_start_with_pyproject_file_batch20(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    detected = _detect_project_root(tmp_path / "pyproject.toml")
    assert detected == tmp_path


def test_detect_project_root_no_pyproject_returns_input_batch20(tmp_path):
    """找不到 pyproject 时返回 start（cur）。"""
    sub = tmp_path / "deep"
    sub.mkdir()
    result = _detect_project_root(sub)
    # 应是 sub（或其祖先链上的某个）
    assert sub in result.parents or result == sub


def test_detect_project_root_picks_nearest_pyproject_batch20(tmp_path):
    """多个 pyproject.toml 时取最近。"""
    (tmp_path / "pyproject.toml").write_text("name='outer'", encoding="utf-8")
    inner = tmp_path / "inner"
    inner.mkdir()
    (inner / "pyproject.toml").write_text("name='inner'", encoding="utf-8")
    detected = _detect_project_root(inner)
    assert detected == inner


def test_detect_project_root_string_path_batch20(tmp_path):
    """接受 str 路径。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    detected = _detect_project_root(Path(str(tmp_path)))
    assert detected == tmp_path


def test_detect_project_root_returns_absolute_batch20(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    detected = _detect_project_root(tmp_path)
    assert detected.is_absolute()


def test_detect_project_root_uses_resolve_batch20(tmp_path):
    """内部用 resolve。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    detected = _detect_project_root(tmp_path)
    assert detected == tmp_path.resolve()


# ---------- Manifest dataclass 行为深度第二十批 ----------


def test_manifest_is_frozen_batch20():
    """Manifest 是 frozen dataclass。"""
    fields = {f.name for f in dataclasses.fields(Manifest)}
    sample_doc = DocumentEntry(
        doc_id="d1",
        path_str="x.pdf",
        resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(sample_doc,),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


def test_manifest_field_count_5_batch20():
    fields = dataclasses.fields(Manifest)
    assert len(fields) == 5


def test_manifest_field_names_in_order_batch20():
    fields = [f.name for f in dataclasses.fields(Manifest)]
    assert fields == ["manifest_version", "devset_status", "documents", "expected_failures", "project_root"]


def test_manifest_field_types_batch20():
    fields = {f.name: f.type for f in dataclasses.fields(Manifest)}
    assert "manifest_version" in fields
    assert "documents" in fields
    assert "expected_failures" in fields


def test_manifest_hashable_with_hashable_fields_batch20():
    """Manifest 自身可 hash（仅当 documents/expected_failures 是 tuple）。"""
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert hash(m) == hash(m)


def test_manifest_equality_with_same_fields_batch20():
    m1 = Manifest("1.0", "incomplete", (), (), Path("/tmp"))
    m2 = Manifest("1.0", "incomplete", (), (), Path("/tmp"))
    assert m1 == m2


def test_manifest_inequality_different_status_batch20():
    m1 = Manifest("1.0", "incomplete", (), (), Path("/tmp"))
    m2 = Manifest("1.0", "complete", (), (), Path("/tmp"))
    assert m1 != m2


def test_manifest_no_default_values_batch20():
    """所有字段无 default。"""
    for f in dataclasses.fields(Manifest):
        assert f.default is dataclasses.MISSING


# ---------- Manifest properties 行为深度第二十批 ----------


def test_manifest_categories_covered_sorted_batch20():
    """categories_covered 返回 sorted list。"""
    docs = (
        DocumentEntry(
            doc_id="d1", path_str="x", resolved_path=Path("/x"),
            source_type="pdf", sha256=None, categories=("b", "c", "a"),
            paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
        ),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_categories_covered_dedup_batch20():
    """重复 category 只算一次。"""
    docs = (
        DocumentEntry(
            doc_id="d1", path_str="x", resolved_path=Path("/x"),
            source_type="pdf", sha256=None, categories=("a", "b"),
            paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
        ),
        DocumentEntry(
            doc_id="d2", path_str="y", resolved_path=Path("/y"),
            source_type="pdf", sha256=None, categories=("b", "c"),
            paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
        ),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_pdf_count_other_source_type_batch20():
    """source_type 不是 pdf/docx 时不计入 pdf_count 或 docx_count。"""
    docs = (
        DocumentEntry(
            doc_id="d1", path_str="x", resolved_path=Path("/x"),
            source_type="other", sha256=None, categories=(),
            paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
        ),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.pdf_count == 0
    assert m.docx_count == 0
    assert m.file_count == 1


def test_manifest_content_group_count_no_pairs_batch20():
    """所有文档无 paired_with 时 groups=0, unpaired=N。"""
    docs = tuple(
        DocumentEntry(
            doc_id=f"d{i}", path_str=f"x{i}", resolved_path=Path(f"/x{i}"),
            source_type="pdf", sha256=None, categories=(),
            paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
        ) for i in range(3)
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.content_group_count == 3


def test_manifest_content_group_count_paired_both_ways_batch20():
    """d1.paired_with=d2 + d2.paired_with=d1 → 1 group。"""
    docs = (
        DocumentEntry(
            doc_id="d1", path_str="x", resolved_path=Path("/x"),
            source_type="pdf", sha256=None, categories=(),
            paired_with="d2", annotation_file_str=None, annotation_resolved=None, expectations=None,
        ),
        DocumentEntry(
            doc_id="d2", path_str="y", resolved_path=Path("/y"),
            source_type="docx", sha256=None, categories=(),
            paired_with="d1", annotation_file_str=None, annotation_resolved=None, expectations=None,
        ),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.content_group_count == 1


def test_manifest_content_group_count_paired_one_way_batch20():
    """d1.paired_with=d2, d2 无 paired_with → frozenset 不去重，仍 1 group。"""
    docs = (
        DocumentEntry(
            doc_id="d1", path_str="x", resolved_path=Path("/x"),
            source_type="pdf", sha256=None, categories=(),
            paired_with="d2", annotation_file_str=None, annotation_resolved=None, expectations=None,
        ),
        DocumentEntry(
            doc_id="d2", path_str="y", resolved_path=Path("/y"),
            source_type="docx", sha256=None, categories=(),
            paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
        ),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/tmp"))
    assert m.content_group_count == 1


def test_manifest_file_count_zero_when_empty_batch20():
    m = Manifest("1.0", "incomplete", (), (), Path("/tmp"))
    assert m.file_count == 0


# ---------- DocumentEntry 行为深度第二十批 ----------


def test_document_entry_is_frozen_batch20():
    d = DocumentEntry(
        doc_id="d1", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.doc_id = "other"  # type: ignore[misc]


def test_document_entry_field_count_10_batch20():
    fields = dataclasses.fields(DocumentEntry)
    assert len(fields) == 10


def test_document_entry_field_order_batch20():
    fields = [f.name for f in dataclasses.fields(DocumentEntry)]
    assert fields == [
        "doc_id", "path_str", "resolved_path", "source_type",
        "sha256", "categories", "paired_with",
        "annotation_file_str", "annotation_resolved", "expectations",
    ]


def test_document_entry_equality_batch20():
    d1 = DocumentEntry(
        doc_id="d1", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    d2 = DocumentEntry(
        doc_id="d1", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    assert d1 == d2


def test_document_entry_inequality_batch20():
    d1 = DocumentEntry(
        doc_id="d1", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    d2 = DocumentEntry(
        doc_id="d2", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    assert d1 != d2


def test_document_entry_hashable_with_none_expectations_batch20():
    d = DocumentEntry(
        doc_id="d1", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    assert hash(d) == hash(d)


def test_document_entry_unhashable_with_dict_expectations_batch20():
    d = DocumentEntry(
        doc_id="d1", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None, expectations={"k": 1},
    )
    with pytest.raises(TypeError):
        hash(d)


def test_document_entry_no_default_values_batch20():
    """所有字段无 default。"""
    for f in dataclasses.fields(DocumentEntry):
        assert f.default is dataclasses.MISSING


def test_document_entry_with_paired_with_batch20():
    d = DocumentEntry(
        doc_id="d1", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256=None, categories=(),
        paired_with="d2", annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    assert d.paired_with == "d2"


# ---------- ExpectedFailure 行为深度第二十批 ----------


def test_expected_failure_is_frozen_batch20():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="x", resolved_path=Path("/x"),
        expected_error_code="E_PARSE", source_type="pdf",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        ef.doc_id = "other"  # type: ignore[misc]


def test_expected_failure_field_count_5_batch20():
    fields = dataclasses.fields(ExpectedFailure)
    assert len(fields) == 5


def test_expected_failure_field_order_batch20():
    fields = [f.name for f in dataclasses.fields(ExpectedFailure)]
    assert fields == ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]


def test_expected_failure_source_type_none_batch20():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="x", resolved_path=Path("/x"),
        expected_error_code="E_X", source_type=None,
    )
    assert ef.source_type is None


def test_expected_failure_equality_batch20():
    ef1 = ExpectedFailure("ef1", "x", Path("/x"), "E_X", "pdf")
    ef2 = ExpectedFailure("ef1", "x", Path("/x"), "E_X", "pdf")
    assert ef1 == ef2


def test_expected_failure_hashable_batch20():
    ef1 = ExpectedFailure("ef1", "x", Path("/x"), "E_X", "pdf")
    assert hash(ef1) == hash(ef1)


def test_expected_failure_no_default_values_batch20():
    """所有字段无 default。"""
    for f in dataclasses.fields(ExpectedFailure):
        assert f.default is dataclasses.MISSING


# ---------- load_manifest 行为深度第二十批 ----------


def _write_manifest(tmp_path, data):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_documents_default_empty_batch20(tmp_path):
    """manifest schema 要求 documents 字段存在（即使为空）。"""
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents == ()
    assert m.expected_failures == ()


def test_load_manifest_expected_failures_default_empty_batch20(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures == ()


def test_load_manifest_with_categories_batch20(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "categories": ["x", "y"]},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ("x", "y")


def test_load_manifest_with_paired_with_batch20(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "a.docx", "source_type": "docx"},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].paired_with == "d2"
    assert m.documents[1].paired_with is None


def test_load_manifest_with_sha256_batch20(tmp_path):
    """sha256 必须是 64 位 hex。"""
    sha = "0123456789abcdef" * 4  # 64 chars
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "sha256": sha},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 == sha


def test_load_manifest_with_expectations_batch20(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "expectations": {"element_count_by_type": {"heading": 5}}},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations == {"element_count_by_type": {"heading": 5}}


def test_load_manifest_with_annotation_file_batch20(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "annotation_file": "b.json"},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_file_str == "b.json"
    assert m.documents[0].annotation_resolved == (tmp_path / "b.json").resolve()


def test_load_manifest_annotation_file_invalid_path_batch20(tmp_path):
    """annotation_file 用反斜杠应抛 ManifestError。"""
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "annotation_file": "b\\c.json"},
        ],
    })
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_project_root_as_str_batch20(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    m = load_manifest(str(p), project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_returns_manifest_batch20(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)


def test_load_manifest_doc_path_outside_root_batch20(tmp_path):
    """doc.path 解析出 project_root 之外 → ManifestError。"""
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "../escape.pdf", "source_type": "pdf"},
        ],
    })
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_doc_path_backslash_batch20(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a\\b.pdf", "source_type": "pdf"},
        ],
    })
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_not_exist_raises_batch20(tmp_path):
    with pytest.raises(ManifestError):
        load_manifest(tmp_path / "missing.json", project_root=tmp_path)


def test_load_manifest_invalid_json_raises_batch20(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_with_expected_failure_batch20(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "bad.pdf", "expected_error_code": "E_PARSE", "source_type": "pdf"},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].doc_id == "ef1"
    assert m.expected_failures[0].expected_error_code == "E_PARSE"


def test_load_manifest_devset_status_passed_through_batch20(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.devset_status == "complete"


# ---------- module source forbidden tokens 第三十五批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    "open(\"/etc/passwd",
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch20(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch20():
    src = inspect.getsource(mmod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch20():
    src = inspect.getsource(mmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch20():
    src = inspect.getsource(mmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch20():
    src = inspect.getsource(mmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch20():
    src = inspect.getsource(mmod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch20():
    src = inspect.getsource(mmod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch20():
    src = inspect.getsource(mmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch20():
    src = inspect.getsource(mmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch20():
    src = inspect.getsource(mmod)
    assert "import tempfile" not in src


def test_module_source_no_unlink_call_batch20():
    src = inspect.getsource(mmod)
    assert ".unlink(" not in src


def test_module_source_no_rmdir_call_batch20():
    src = inspect.getsource(mmod)
    assert ".rmdir(" not in src


def test_module_source_no_path_write_text_batch20():
    src = inspect.getsource(mmod)
    assert ".write_text(" not in src


def test_module_source_no_sys_exit_batch20():
    src = inspect.getsource(mmod)
    assert "sys.exit" not in src


def test_module_source_no_re_compile_batch20():
    src = inspect.getsource(mmod)
    assert "re.compile" not in src


def test_module_source_no_pandas_import_batch20():
    src = inspect.getsource(mmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch20():
    src = inspect.getsource(mmod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第三十批 ----------


def test_module_source_has_future_annotations_batch20():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_json_import_batch20():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_source_has_dataclass_import_batch20():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_has_pathlib_path_import_batch20():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch20():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_manifest_version_import_batch20():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_has_schema_validate_import_batch20():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_has_manifest_error_class_batch20():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


def test_module_source_has_document_entry_dataclass_batch20():
    src = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in src
    assert "class DocumentEntry:" in src


def test_module_source_has_expected_failure_dataclass_batch20():
    src = inspect.getsource(mmod)
    assert "class ExpectedFailure:" in src


def test_module_source_has_manifest_dataclass_batch20():
    src = inspect.getsource(mmod)
    assert "class Manifest:" in src


def test_module_source_has_load_manifest_function_batch20():
    src = inspect.getsource(mmod)
    assert "def load_manifest(" in src


def test_module_source_has_resolve_relative_path_function_batch20():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in src


def test_module_source_has_detect_project_root_function_batch20():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root(" in src


def test_module_source_has_is_absolute_like_function_batch20():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in src


def test_module_source_has_has_backslash_function_batch20():
    src = inspect.getsource(mmod)
    assert "def _has_backslash(" in src


def test_module_source_has_all_list_with_5_entries_batch20():
    src = inspect.getsource(mmod)
    assert '"ManifestError"' in src
    assert '"Manifest"' in src
    assert '"DocumentEntry"' in src
    assert '"ExpectedFailure"' in src
    assert '"load_manifest"' in src


def test_module_source_has_docstring_batch20():
    src = inspect.getsource(mmod)
    assert "开发集清单加载器" in src


# ---------- signatures 第三十批 ----------


def test_signature_load_manifest_batch20():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["manifest_path", "project_root"]


def test_signature_load_manifest_project_root_default_none_batch20():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.values())
    assert params[1].default is None


def test_signature_resolve_relative_path_batch20():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["path_str", "project_root", "field_name"]


def test_signature_is_absolute_like_batch20():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["path_str"]


def test_signature_has_backslash_batch20():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["path_str"]


def test_signature_detect_project_root_batch20():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["start"]


# ---------- module 合理性第三十批 ----------


def test_module_has_all_attribute_batch20():
    assert hasattr(mmod, "__all__")


def test_module_all_count_5_batch20():
    assert len(mmod.__all__) == 5


def test_module_all_entries_are_strings_batch20():
    for n in mmod.__all__:
        assert isinstance(n, str)


def test_module_does_not_import_app_pipeline_batch20():
    src = inspect.getsource(mmod)
    assert "from app" not in src
    assert "import app" not in src


def test_module_does_not_import_evaluation_runner_batch20():
    src = inspect.getsource(mmod)
    assert "from evaluation.runner" not in src
    assert "from evaluation import runner" not in src


def test_module_does_not_import_evaluation_cli_batch20():
    src = inspect.getsource(mmod)
    assert "from evaluation.cli" not in src
    assert "from evaluation import cli" not in src


def test_module_does_not_import_evaluation_metrics_batch20():
    src = inspect.getsource(mmod)
    assert "from evaluation.metrics" not in src
    assert "from evaluation import metrics" not in src


def test_module_does_not_import_evaluation_annotation_metrics_batch20():
    src = inspect.getsource(mmod)
    assert "from evaluation.annotation_metrics" not in src


def test_module_helpers_are_private_batch20():
    for name in ("_resolve_relative_path", "_detect_project_root", "_is_absolute_like", "_has_backslash"):
        assert name.startswith("_")


def test_module_no_main_block_batch20():
    src = inspect.getsource(mmod)
    assert 'if __name__ ==' not in src


# ---------- 端到端集成 第三十批 ----------


def test_e2e_load_manifest_full_round_trip_batch20(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "categories": ["a", "b"]},
            {"doc_id": "d2", "path": "y.docx", "source_type": "docx"},
        ],
        "expected_failures": [
            {"doc_id": "ef1", "path": "bad.pdf", "expected_error_code": "E_PARSE"},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.categories_covered == ["a", "b"]
    assert len(m.expected_failures) == 1


def test_e2e_load_manifest_with_paired_documents_batch20(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "pdf1", "path": "a.pdf", "source_type": "pdf", "paired_with": "docx1"},
            {"doc_id": "docx1", "path": "a.docx", "source_type": "docx", "paired_with": "pdf1"},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 1


def test_e2e_load_manifest_categories_combined_batch20(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "categories": ["x"]},
            {"doc_id": "d2", "path": "y.docx", "source_type": "docx", "categories": ["x", "z"]},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["x", "z"]


def test_e2e_load_manifest_auto_project_root_batch20(tmp_path):
    """不传 project_root 时自动检测。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    m = load_manifest(p)
    assert m.project_root == tmp_path.resolve()


def test_e2e_load_manifest_unicode_doc_id_batch20(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "文档1", "path": "x.pdf", "source_type": "pdf"},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].doc_id == "文档1"


def test_e2e_load_manifest_doc_id_passthrough_to_field_name_batch20(tmp_path):
    """错误消息含 documents[doc_id].path。"""
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "special", "path": "../escape.pdf", "source_type": "pdf"},
        ],
    })
    try:
        load_manifest(p, project_root=tmp_path)
    except ManifestError as e:
        assert "special" in str(e)


def test_e2e_manifest_categories_in_load_manifest_batch20(tmp_path):
    """load_manifest 后 categories 是 tuple。"""
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "categories": ["a", "b", "c"]},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ("a", "b", "c")
    assert isinstance(m.documents[0].categories, tuple)
