"""evaluation/manifest.py 第六十五轮 edges 测试（Round 587）。

补强 edges64 未触及的角度（第三十八批）。
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import MANIFEST_VERSION
from evaluation import manifest as mmod
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


# ---------- DocumentEntry 第三十八批


def test_document_entry_dataclass_batch38():
    assert is_dataclass(DocumentEntry)


def test_document_entry_frozen_batch38():
    """frozen=True → 不可修改字段。"""
    de = DocumentEntry(
        doc_id="d1",
        path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        de.doc_id = "new"  # type: ignore[misc]


def test_document_entry_field_count_batch38():
    """10 个字段。"""
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_field_names_batch38():
    names = {f.name for f in fields(DocumentEntry)}
    expected = {
        "doc_id", "path_str", "resolved_path", "source_type",
        "sha256", "categories", "paired_with",
        "annotation_file_str", "annotation_resolved", "expectations",
    }
    assert names == expected


def test_document_entry_optional_fields_default_none_batch38():
    """可选字段默认 None。"""
    de = DocumentEntry(
        doc_id="d1",
        path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    assert de.sha256 is None
    assert de.paired_with is None
    assert de.annotation_file_str is None
    assert de.annotation_resolved is None
    assert de.expectations is None


def test_document_entry_categories_default_empty_tuple_batch38():
    de = DocumentEntry(
        doc_id="d1", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    assert de.categories == ()


def test_document_entry_full_construction_batch38():
    de = DocumentEntry(
        doc_id="d_full",
        path_str="dir/file.pdf",
        resolved_path=Path("/proj/dir/file.pdf"),
        source_type="pdf",
        sha256="a" * 64,
        categories=("tutorial", "advanced"),
        paired_with="d_full_docx",
        annotation_file_str="annotations/d_full.json",
        annotation_resolved=Path("/proj/annotations/d_full.json"),
        expectations={"element_count_by_type": {"paragraph": 5}},
    )
    assert de.doc_id == "d_full"
    assert de.categories == ("tutorial", "advanced")
    assert de.paired_with == "d_full_docx"


def test_document_entry_equality_batch38():
    d1 = DocumentEntry(
        doc_id="x", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    d2 = DocumentEntry(
        doc_id="x", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    assert d1 == d2


def test_document_entry_inequality_batch38():
    d1 = DocumentEntry(
        doc_id="x", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    d2 = DocumentEntry(
        doc_id="y", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    assert d1 != d2


def test_document_entry_hash_with_categories_batch38():
    """frozen dataclass 是 hashable。"""
    de = DocumentEntry(
        doc_id="x", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=("a",),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    # 不抛异常即成功
    hash(de)


def test_document_entry_repr_batch38():
    de = DocumentEntry(
        doc_id="x", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    r = repr(de)
    assert "DocumentEntry" in r
    assert "x" in r


# ---------- ExpectedFailure 第三十八批


def test_expected_failure_dataclass_batch38():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_frozen_batch38():
    ef = ExpectedFailure(
        doc_id="ef1",
        path_str="bad.pdf",
        resolved_path=Path("/tmp/bad.pdf"),
        expected_error_code="E_PARSE",
        source_type="pdf",
    )
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "new"  # type: ignore[misc]


def test_expected_failure_field_count_batch38():
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_field_names_batch38():
    names = {f.name for f in fields(ExpectedFailure)}
    expected = {"doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"}
    assert names == expected


def test_expected_failure_source_type_optional_batch38():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="a", resolved_path=Path("/a"),
        expected_error_code="E_PARSE", source_type=None,
    )
    assert ef.source_type is None


def test_expected_failure_full_construction_batch38():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="bad.pdf",
        resolved_path=Path("/proj/bad.pdf"),
        expected_error_code="E_UNSUPPORTED",
        source_type="txt",
    )
    assert ef.expected_error_code == "E_UNSUPPORTED"
    assert ef.source_type == "txt"


def test_expected_failure_equality_batch38():
    e1 = ExpectedFailure(
        doc_id="x", path_str="a", resolved_path=Path("/a"),
        expected_error_code="E", source_type=None,
    )
    e2 = ExpectedFailure(
        doc_id="x", path_str="a", resolved_path=Path("/a"),
        expected_error_code="E", source_type=None,
    )
    assert e1 == e2


def test_expected_failure_hash_batch38():
    ef = ExpectedFailure(
        doc_id="x", path_str="a", resolved_path=Path("/a"),
        expected_error_code="E", source_type=None,
    )
    hash(ef)


# ---------- Manifest properties 第三十八批


def _make_doc(doc_id, source_type="pdf", categories=(), paired_with=None):
    return DocumentEntry(
        doc_id=doc_id, path_str=f"{doc_id}.pdf", resolved_path=Path(f"/proj/{doc_id}.pdf"),
        source_type=source_type, sha256=None, categories=categories,
        paired_with=paired_with, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )


def _make_manifest(docs=(), expected_failures=(), project_root=None, devset_status="incomplete"):
    return Manifest(
        manifest_version=MANIFEST_VERSION,
        devset_status=devset_status,
        documents=tuple(docs),
        expected_failures=tuple(expected_failures),
        project_root=project_root or Path("/proj"),
    )


def test_manifest_properties_correct_for_mixed_batch38():
    docs = [
        _make_doc("d1", source_type="pdf"),
        _make_doc("d2", source_type="docx"),
        _make_doc("d3", source_type="pdf"),
    ]
    m = _make_manifest(docs=docs)
    assert m.file_count == 3
    assert m.pdf_count == 2
    assert m.docx_count == 1


def test_manifest_pdf_count_zero_when_all_docx_batch38():
    docs = [_make_doc("d1", source_type="docx"), _make_doc("d2", source_type="docx")]
    m = _make_manifest(docs=docs)
    assert m.pdf_count == 0
    assert m.docx_count == 2


def test_manifest_categories_covered_sorted_batch38():
    docs = [
        _make_doc("d1", categories=("z", "a")),
        _make_doc("d2", categories=("m",)),
    ]
    m = _make_manifest(docs=docs)
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_dedup_batch38():
    docs = [
        _make_doc("d1", categories=("a", "b")),
        _make_doc("d2", categories=("a", "c")),
    ]
    m = _make_manifest(docs=docs)
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_categories_covered_empty_batch38():
    m = _make_manifest()
    assert m.categories_covered == []


def test_manifest_content_group_count_unpaired_batch38():
    docs = [_make_doc("d1"), _make_doc("d2")]
    m = _make_manifest(docs=docs)
    assert m.content_group_count == 2


def test_manifest_content_group_count_paired_batch38():
    docs = [
        _make_doc("d1", paired_with="d2"),
        _make_doc("d2", paired_with="d1"),
    ]
    m = _make_manifest(docs=docs)
    assert m.content_group_count == 1


def test_manifest_content_group_count_mixed_batch38():
    docs = [
        _make_doc("d1", paired_with="d2"),
        _make_doc("d2", paired_with="d1"),
        _make_doc("d3"),  # unpaired
    ]
    m = _make_manifest(docs=docs)
    assert m.content_group_count == 2


def test_manifest_devset_status_value_batch38():
    m = _make_manifest(devset_status="complete")
    assert m.devset_status == "complete"


def test_manifest_devset_status_incomplete_batch38():
    m = _make_manifest(devset_status="incomplete")
    assert m.devset_status == "incomplete"


def test_manifest_frozen_dataclass_batch38():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


def test_manifest_project_root_value_batch38():
    pr = Path("/some/path")
    m = _make_manifest(project_root=pr)
    assert m.project_root == pr


# ---------- _is_absolute_like / _has_backslash 第三十八批


def test_is_absolute_like_unix_root_batch38():
    assert _is_absolute_like("/etc/passwd") is True


def test_is_absolute_like_unix_root_only_batch38():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_windows_backslash_batch38():
    assert _is_absolute_like("C:\\Windows") is True


def test_is_absolute_like_windows_forward_batch38():
    assert _is_absolute_like("C:/Windows") is True


def test_is_absolute_like_lowercase_drive_batch38():
    assert _is_absolute_like("c:/foo") is True


def test_is_absolute_like_relative_path_batch38():
    assert _is_absolute_like("foo/bar") is False


def test_is_absolute_like_single_char_batch38():
    assert _is_absolute_like("a") is False


def test_is_absolute_like_two_chars_batch38():
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_drive_no_separator_batch38():
    """C:foo 不是绝对路径（Windows 行为：相对于当前目录的 drive）。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_number_first_batch38():
    """数字开头不是 Windows drive。"""
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_unicode_first_batch38():
    """Unicode 字母也会被 .isalpha() 接受（Python str.isalpha 支持 unicode）。"""
    # "中" 是 Unicode 字母，isalpha() 返回 True → 被当作 drive letter
    assert _is_absolute_like("中:/foo") is True


def test_has_backslash_present_batch38():
    assert _has_backslash("a\\b") is True


def test_has_backslash_absent_batch38():
    assert _has_backslash("a/b") is False


def test_has_backslash_empty_string_batch38():
    assert _has_backslash("") is False


def test_has_backslash_only_backslash_batch38():
    assert _has_backslash("\\") is True


def test_has_backslash_multiple_backslash_batch38():
    assert _has_backslash("a\\b\\c") is True


# ---------- _resolve_relative_path 第三十八批


def test_resolve_relative_path_returns_absolute_batch38(tmp_path):
    out = _resolve_relative_path("a/b.pdf", tmp_path, "test")
    assert out.is_absolute()


def test_resolve_relative_path_subdir_batch38(tmp_path):
    out = _resolve_relative_path("sub/file.pdf", tmp_path, "test")
    assert str(out).endswith("sub/file.pdf") or str(out).endswith("sub\\file.pdf")


def test_resolve_relative_path_filename_only_batch38(tmp_path):
    out = _resolve_relative_path("file.pdf", tmp_path, "test")
    assert out.name == "file.pdf"


def test_resolve_relative_path_with_dot_segments_batch38(tmp_path):
    """含 . 或 .. 的路径。"""
    # 注意：.. 会让路径跑到 project_root 外，会被拒绝
    out = _resolve_relative_path("a/./b.pdf", tmp_path, "test")
    assert out.is_absolute()


def test_resolve_relative_path_outside_root_rejected_batch38(tmp_path):
    """.. 跑出 project_root → ManifestError。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("../outside.pdf", tmp_path, "test")


def test_resolve_relative_path_absolute_rejected_batch38(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("/etc/passwd", tmp_path, "test")


def test_resolve_relative_path_backslash_rejected_batch38(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("a\\b.pdf", tmp_path, "test")


def test_resolve_relative_path_empty_rejected_batch38(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("", tmp_path, "test")


def test_resolve_relative_path_unicode_batch38(tmp_path):
    out = _resolve_relative_path("中文/文件.pdf", tmp_path, "test")
    assert out.is_absolute()


def test_resolve_relative_path_does_not_require_existing_file_batch38(tmp_path):
    """不要求文件真实存在（仅做路径形式校验）。"""
    out = _resolve_relative_path("nonexistent.pdf", tmp_path, "test")
    assert out.is_absolute()
    assert not out.is_file()


# ---------- load_manifest 第三十八批


def _make_manifest_json(tmp_path, documents=None, expected_failures=None,
                         manifest_version=None, devset_status="incomplete"):
    """在 tmp_path 写一个合法 manifest.json，并返回路径。"""
    # 先创建所需的实际文件
    if documents:
        for d in documents:
            p = tmp_path / d["path"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"sample content")
    if expected_failures:
        for ef in expected_failures:
            p = tmp_path / ef["path"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"bad content")

    data = {
        "manifest_version": manifest_version or MANIFEST_VERSION,
        "devset_status": devset_status,
        "documents": documents or [],
    }
    if expected_failures is not None:
        data["expected_failures"] = expected_failures

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    return manifest_path


def test_load_manifest_empty_documents_batch38(tmp_path):
    mp = _make_manifest_json(tmp_path)
    m = load_manifest(mp, project_root=tmp_path)
    assert m.documents == ()


def test_load_manifest_empty_expected_failures_omitted_batch38(tmp_path):
    """expected_failures 字段可省略。"""
    mp = _make_manifest_json(tmp_path)
    m = load_manifest(mp, project_root=tmp_path)
    assert m.expected_failures == ()


def test_load_manifest_devset_status_complete_batch38(tmp_path):
    mp = _make_manifest_json(tmp_path, devset_status="complete")
    m = load_manifest(mp, project_root=tmp_path)
    assert m.devset_status == "complete"


def test_load_manifest_one_document_batch38(tmp_path):
    docs = [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "sha256": "a" * 64, "categories": ["x"]}]
    mp = _make_manifest_json(tmp_path, documents=docs)
    m = load_manifest(mp, project_root=tmp_path)
    assert len(m.documents) == 1
    assert m.documents[0].doc_id == "d1"
    assert m.documents[0].source_type == "pdf"


def test_load_manifest_one_docx_document_batch38(tmp_path):
    docs = [{"doc_id": "d1", "path": "a.docx", "source_type": "docx",
             "sha256": "b" * 64}]
    mp = _make_manifest_json(tmp_path, documents=docs)
    m = load_manifest(mp, project_root=tmp_path)
    assert m.documents[0].source_type == "docx"


def test_load_manifest_with_categories_batch38(tmp_path):
    docs = [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "sha256": "a" * 64, "categories": ["tut", "adv"]}]
    mp = _make_manifest_json(tmp_path, documents=docs)
    m = load_manifest(mp, project_root=tmp_path)
    assert m.documents[0].categories == ("tut", "adv")


def test_load_manifest_with_paired_with_batch38(tmp_path):
    docs = [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
         "sha256": "a" * 64, "paired_with": "d2"},
        {"doc_id": "d2", "path": "a.docx", "source_type": "docx",
         "sha256": "b" * 64, "paired_with": "d1"},
    ]
    mp = _make_manifest_json(tmp_path, documents=docs)
    m = load_manifest(mp, project_root=tmp_path)
    assert m.documents[0].paired_with == "d2"
    assert m.content_group_count == 1


def test_load_manifest_with_expectations_batch38(tmp_path):
    docs = [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "sha256": "a" * 64,
             "expectations": {"element_count_by_type": {"paragraph": 5}}}]
    mp = _make_manifest_json(tmp_path, documents=docs)
    m = load_manifest(mp, project_root=tmp_path)
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_with_annotation_file_batch38(tmp_path):
    """annotation_file 字段会触发 _resolve_relative_path。"""
    # 先创建 annotation 文件
    ann = tmp_path / "ann.json"
    ann.write_text("{}", encoding="utf-8")
    docs = [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "sha256": "a" * 64, "annotation_file": "ann.json"}]
    mp = _make_manifest_json(tmp_path, documents=docs)
    m = load_manifest(mp, project_root=tmp_path)
    assert m.documents[0].annotation_file_str == "ann.json"
    assert m.documents[0].annotation_resolved == ann.resolve()


def test_load_manifest_with_expected_failures_batch38(tmp_path):
    efs = [{"doc_id": "ef1", "path": "bad.pdf", "expected_error_code": "E_PARSE",
            "source_type": "pdf"}]
    mp = _make_manifest_json(tmp_path, expected_failures=efs)
    m = load_manifest(mp, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].doc_id == "ef1"
    assert m.expected_failures[0].expected_error_code == "E_PARSE"


def test_load_manifest_nonexistent_file_raises_batch38(tmp_path):
    with pytest.raises(ManifestError):
        load_manifest(tmp_path / "nonexistent.json", project_root=tmp_path)


def test_load_manifest_invalid_json_raises_batch38(tmp_path):
    mp = tmp_path / "manifest.json"
    mp.write_text("{invalid", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(mp, project_root=tmp_path)


def test_load_manifest_incompatible_version_raises_batch38(tmp_path):
    """manifest_version 不兼容 → ManifestError（schema 限制为 const "1.0"）。

    注：schema 可能先拒绝（const 检查），抛 EvalSchemaError；代码层后续也有版本检查。
    """
    from evaluation.schema import EvalSchemaError
    mp = _make_manifest_json(tmp_path, manifest_version="0.0.0")
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(mp, project_root=tmp_path)


def test_load_manifest_absolute_path_rejected_batch38(tmp_path):
    """document path 是绝对路径 → schema 拒绝。"""
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "/etc/passwd", "source_type": "pdf"}],
    }
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(data), encoding="utf-8")
    # schema 或 ManifestError 任一抛出
    with pytest.raises((ManifestError, Exception)):
        load_manifest(mp, project_root=tmp_path)


def test_load_manifest_str_path_batch38(tmp_path):
    """传 str 路径而非 Path。"""
    mp = _make_manifest_json(tmp_path)
    m = load_manifest(str(mp), project_root=str(tmp_path))
    assert m.file_count == 0


def test_load_manifest_idempotent_batch38(tmp_path):
    mp = _make_manifest_json(tmp_path)
    m1 = load_manifest(mp, project_root=tmp_path)
    m2 = load_manifest(mp, project_root=tmp_path)
    assert m1 == m2


def test_load_manifest_project_root_default_detection_batch38(tmp_path):
    """project_root=None 时自动检测（找 pyproject.toml）。"""
    # 创建 pyproject.toml
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    mp = _make_manifest_json(tmp_path)
    m = load_manifest(mp)
    assert m.project_root == tmp_path.resolve()


# ---------- _detect_project_root 第三十八批


def test_detect_project_root_with_pyproject_batch38(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    out = _detect_project_root(tmp_path / "anyfile")
    assert out == tmp_path.resolve()


def test_detect_project_root_from_file_batch38(tmp_path):
    """start 是文件路径 → 从 parent 开始找。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    f = tmp_path / "deep" / "file.json"
    f.parent.mkdir(parents=True)
    f.write_text("{}", encoding="utf-8")
    out = _detect_project_root(f)
    assert out == tmp_path.resolve()


def test_detect_project_root_fallback_to_cur_batch38(tmp_path):
    """没找到 pyproject.toml → 返回 cur。"""
    # /tmp 下应该没有 pyproject.toml（或可能存在系统级的；这里只验证返回 Path）
    out = _detect_project_root(tmp_path / "anyfile")
    assert isinstance(out, Path)


def test_detect_project_root_returns_path_batch38(tmp_path):
    out = _detect_project_root(tmp_path)
    assert isinstance(out, Path)


# ---------- ManifestError 第三十八批


def test_manifest_error_is_exception_batch38():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_can_be_raised_batch38():
    with pytest.raises(ManifestError):
        raise ManifestError("msg")


def test_manifest_error_can_be_caught_as_exception_batch38():
    try:
        raise ManifestError("x")
    except Exception as e:
        assert isinstance(e, ManifestError)


def test_manifest_error_message_preserved_batch38():
    e = ManifestError("custom message")
    assert str(e) == "custom message"


def test_manifest_error_no_custom_init_batch38():
    """ManifestError 没自定义 __init__（继承 Exception）。"""
    assert ManifestError.__init__ is Exception.__init__


def test_manifest_error_with_unicode_message_batch38():
    e = ManifestError("中文错误")
    assert str(e) == "中文错误"


# ---------- module source forbidden tokens 第六十二批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch38(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第五十八批


def test_module_source_contains_design_doc_batch38():
    src = inspect.getsource(mmod)
    assert "开发集清单加载器" in src


def test_module_source_contains_no_absolute_path_keyword_batch38():
    src = inspect.getsource(mmod)
    assert "拒绝绝对路径" in src


def test_module_source_contains_no_backslash_keyword_batch38():
    src = inspect.getsource(mmod)
    assert "禁止反斜杠" in src


def test_module_source_contains_dataclass_import_batch38():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_contains_manifest_version_import_batch38():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_contains_validate_import_batch38():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_contains_manifest_error_class_batch38():
    src = inspect.getsource(mmod)
    assert "class ManifestError" in src


def test_module_source_contains_document_entry_class_batch38():
    src = inspect.getsource(mmod)
    assert "class DocumentEntry" in src


def test_module_source_contains_expected_failure_class_batch38():
    src = inspect.getsource(mmod)
    assert "class ExpectedFailure" in src


def test_module_source_contains_manifest_class_batch38():
    src = inspect.getsource(mmod)
    assert "class Manifest" in src


def test_module_source_contains_is_absolute_like_function_batch38():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in src


def test_module_source_contains_has_backslash_function_batch38():
    src = inspect.getsource(mmod)
    assert "def _has_backslash(" in src


def test_module_source_contains_resolve_relative_path_function_batch38():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in src


def test_module_source_contains_load_manifest_function_batch38():
    src = inspect.getsource(mmod)
    assert "def load_manifest(" in src


def test_module_source_contains_detect_project_root_function_batch38():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root(" in src


def test_module_source_contains_content_group_count_property_batch38():
    src = inspect.getsource(mmod)
    assert "def content_group_count" in src


def test_module_source_contains_categories_covered_property_batch38():
    src = inspect.getsource(mmod)
    assert "def categories_covered" in src


def test_module_source_contains_pyproject_toml_keyword_batch38():
    src = inspect.getsource(mmod)
    assert "pyproject.toml" in src


def test_module_source_contains_frozen_true_keyword_batch38():
    src = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in src


def test_module_source_contains_resolve_call_batch38():
    src = inspect.getsource(mmod)
    assert ".resolve()" in src


# ---------- signatures 第五十八批


def test_signature_load_manifest_two_params_batch38():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters.keys()) == ["manifest_path", "project_root"]


def test_signature_load_manifest_project_root_optional_batch38():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_signature_load_manifest_return_manifest_batch38():
    sig = inspect.signature(load_manifest)
    assert "Manifest" in str(sig.return_annotation)


def test_signature_resolve_relative_path_three_params_batch38():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters.keys()) == ["path_str", "project_root", "field_name"]


def test_signature_resolve_relative_path_return_path_batch38():
    sig = inspect.signature(_resolve_relative_path)
    assert "Path" in str(sig.return_annotation)


def test_signature_detect_project_root_one_param_batch38():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters.keys()) == ["start"]


def test_signature_detect_project_root_return_path_batch38():
    sig = inspect.signature(_detect_project_root)
    assert "Path" in str(sig.return_annotation)


def test_signature_is_absolute_like_one_param_batch38():
    sig = inspect.signature(_is_absolute_like)
    assert list(sig.parameters.keys()) == ["path_str"]


# ---------- module 合理性 第五十八批


def test_module_has_manifest_error_batch38():
    assert hasattr(mmod, "ManifestError")


def test_module_has_manifest_batch38():
    assert hasattr(mmod, "Manifest")


def test_module_has_document_entry_batch38():
    assert hasattr(mmod, "DocumentEntry")


def test_module_has_expected_failure_batch38():
    assert hasattr(mmod, "ExpectedFailure")


def test_module_has_load_manifest_batch38():
    assert hasattr(mmod, "load_manifest")


def test_module_has_all_attribute_batch38():
    assert hasattr(mmod, "__all__")


def test_module_all_is_list_batch38():
    assert isinstance(mmod.__all__, list)


def test_module_all_len_five_batch38():
    assert len(mmod.__all__) == 5


def test_module_load_manifest_callable_batch38():
    assert callable(mmod.load_manifest)


def test_module_manifest_error_subclass_of_exception_batch38():
    assert issubclass(mmod.ManifestError, Exception)


# ---------- 端到端集成 第五十八批


def test_e2e_load_manifest_full_round_trip_batch38(tmp_path):
    """完整 round trip：写 manifest → load → 验证属性。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    docs = [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
         "sha256": "a" * 64, "categories": ["x"]},
        {"doc_id": "d2", "path": "a.docx", "source_type": "docx",
         "sha256": "b" * 64, "paired_with": "d1"},
    ]
    mp = _make_manifest_json(tmp_path, documents=docs)
    m = load_manifest(mp)
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.categories_covered == ["x"]


def test_e2e_load_manifest_does_not_write_to_disk_batch38(tmp_path):
    """load_manifest 不修改 manifest 文件。"""
    mp = _make_manifest_json(tmp_path)
    before = mp.read_text(encoding="utf-8")
    load_manifest(mp, project_root=tmp_path)
    after = mp.read_text(encoding="utf-8")
    assert before == after


def test_e2e_idempotent_load_batch38(tmp_path):
    mp = _make_manifest_json(tmp_path)
    m1 = load_manifest(mp, project_root=tmp_path)
    m2 = load_manifest(mp, project_root=tmp_path)
    assert m1 == m2


def test_e2e_manifest_with_expected_failure_batch38(tmp_path):
    efs = [{"doc_id": "ef1", "path": "bad.txt", "expected_error_code": "E_UNSUPPORTED",
            "source_type": "txt"}]
    mp = _make_manifest_json(tmp_path, expected_failures=efs)
    m = load_manifest(mp, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    ef = m.expected_failures[0]
    assert ef.doc_id == "ef1"
    assert ef.expected_error_code == "E_UNSUPPORTED"
    assert ef.source_type == "txt"


def test_e2e_categories_covered_with_unicode_batch38(tmp_path):
    docs = [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
         "sha256": "a" * 64, "categories": ["教程", "API"]},
        {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf",
         "sha256": "b" * 64, "categories": ["教程", "高级"]},
    ]
    mp = _make_manifest_json(tmp_path, documents=docs)
    m = load_manifest(mp, project_root=tmp_path)
    # 排序后的 unicode 类别（按 code point 排序）
    assert m.categories_covered == ["API", "教程", "高级"]
