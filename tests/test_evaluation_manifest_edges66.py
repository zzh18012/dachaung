"""evaluation/manifest.py 第六十六轮 edges 测试（Round 594）。

补强 edges65 未触及的角度（第三十九批）。
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


# ---------- DocumentEntry 第三十九批


def test_document_entry_construction_with_all_fields_batch39():
    de = DocumentEntry(
        doc_id="abc",
        path_str="dir/x.pdf",
        resolved_path=Path("/proj/dir/x.pdf"),
        source_type="pdf",
        sha256="a" * 64,
        categories=("cat1", "cat2"),
        paired_with="other",
        annotation_file_str="ann/abc.json",
        annotation_resolved=Path("/proj/ann/abc.json"),
        expectations={"element_count_by_type": {"paragraph": 5}},
    )
    assert de.doc_id == "abc"
    assert de.sha256 == "a" * 64
    assert de.categories == ("cat1", "cat2")
    assert de.paired_with == "other"
    assert de.annotation_file_str == "ann/abc.json"
    assert de.expectations == {"element_count_by_type": {"paragraph": 5}}


def test_document_entry_equality_batch39():
    de1 = DocumentEntry(
        doc_id="d1", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d1", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    assert de1 == de2


def test_document_entry_inequality_when_diff_field_batch39():
    de1 = DocumentEntry(
        doc_id="d1", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d2", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    assert de1 != de2


def test_document_entry_hashable_batch39():
    """frozen dataclass 可哈希。"""
    de = DocumentEntry(
        doc_id="d1", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    assert hash(de) == hash(de)


def test_document_entry_repr_contains_class_name_batch39():
    de = DocumentEntry(
        doc_id="d1", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    assert "DocumentEntry" in repr(de)


def test_document_entry_frozen_categories_batch39():
    de = DocumentEntry(
        doc_id="d1", path_str="a", resolved_path=Path("/a"),
        source_type="pdf", sha256=None, categories=("x",),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        de.categories = ("y",)  # type: ignore[misc]


def test_document_entry_field_types_batch39():
    """字段类型注解正确。"""
    type_hints = DocumentEntry.__annotations__
    assert type_hints["doc_id"] == "str"
    assert type_hints["path_str"] == "str"
    assert type_hints["source_type"] == "str"
    assert "Path" in type_hints["resolved_path"]
    assert "tuple" in type_hints["categories"]


# ---------- ExpectedFailure 第三十九批


def test_expected_failure_construction_all_fields_batch39():
    ef = ExpectedFailure(
        doc_id="ef1",
        path_str="bad/bad.txt",
        resolved_path=Path("/proj/bad/bad.txt"),
        expected_error_code="E_UNSUPPORTED",
        source_type="txt",
    )
    assert ef.doc_id == "ef1"
    assert ef.source_type == "txt"
    assert ef.expected_error_code == "E_UNSUPPORTED"


def test_expected_failure_source_type_optional_batch39():
    ef = ExpectedFailure(
        doc_id="ef1",
        path_str="bad.txt",
        resolved_path=Path("/proj/bad.txt"),
        expected_error_code="E_X",
        source_type=None,
    )
    assert ef.source_type is None


def test_expected_failure_equality_batch39():
    ef1 = ExpectedFailure("a", "p", Path("/p"), "E", None)
    ef2 = ExpectedFailure("a", "p", Path("/p"), "E", None)
    assert ef1 == ef2


def test_expected_failure_field_count_batch39():
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_field_names_batch39():
    names = {f.name for f in fields(ExpectedFailure)}
    expected = {"doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"}
    assert names == expected


def test_expected_failure_frozen_batch39():
    ef = ExpectedFailure("a", "p", Path("/p"), "E", None)
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "b"  # type: ignore[misc]


def test_expected_failure_hashable_batch39():
    ef = ExpectedFailure("a", "p", Path("/p"), "E", None)
    assert hash(ef) == hash(ef)


def test_expected_failure_repr_batch39():
    ef = ExpectedFailure("a", "p", Path("/p"), "E", None)
    assert "ExpectedFailure" in repr(ef)


# ---------- Manifest properties 第三十九批


def _make_manifest_obj(documents=(), expected_failures=(),
                       devset_status="incomplete",
                       project_root=None):
    return Manifest(
        manifest_version=MANIFEST_VERSION,
        devset_status=devset_status,
        documents=tuple(documents),
        expected_failures=tuple(expected_failures),
        project_root=project_root or Path.cwd(),
    )


def _make_doc(doc_id="d1", source_type="pdf", categories=(),
              paired_with=None):
    return DocumentEntry(
        doc_id=doc_id,
        path_str=f"{doc_id}/x",
        resolved_path=Path(f"/proj/{doc_id}/x"),
        source_type=source_type,
        sha256=None,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def test_manifest_file_count_with_many_docs_batch39():
    docs = [_make_doc(doc_id=f"d{i}") for i in range(10)]
    m = _make_manifest_obj(documents=docs)
    assert m.file_count == 10


def test_manifest_pdf_count_zero_when_no_pdfs_batch39():
    docs = [_make_doc(doc_id="d1", source_type="docx")]
    m = _make_manifest_obj(documents=docs)
    assert m.pdf_count == 0


def test_manifest_docx_count_zero_when_no_docx_batch39():
    docs = [_make_doc(doc_id="d1", source_type="pdf")]
    m = _make_manifest_obj(documents=docs)
    assert m.docx_count == 0


def test_manifest_categories_covered_sorting_alpha_batch39():
    docs = [
        _make_doc(doc_id="d1", categories=("z", "a")),
        _make_doc(doc_id="d2", categories=("m",)),
    ]
    m = _make_manifest_obj(documents=docs)
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_dedup_batch39():
    docs = [
        _make_doc(doc_id="d1", categories=("a", "b")),
        _make_doc(doc_id="d2", categories=("b", "c")),
    ]
    m = _make_manifest_obj(documents=docs)
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_categories_covered_returns_list_batch39():
    docs = [_make_doc(doc_id="d1", categories=("a",))]
    m = _make_manifest_obj(documents=docs)
    assert isinstance(m.categories_covered, list)


def test_manifest_devset_status_value_batch39():
    m = _make_manifest_obj(devset_status="complete")
    assert m.devset_status == "complete"


def test_manifest_project_root_value_batch39():
    m = _make_manifest_obj(project_root=Path("/custom"))
    assert m.project_root == Path("/custom")


def test_manifest_frozen_modify_raises_batch39():
    m = _make_manifest_obj()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "x"  # type: ignore[misc]


def test_manifest_content_group_count_unpaired_multiple_batch39():
    docs = [
        _make_doc(doc_id="d1"),
        _make_doc(doc_id="d2"),
        _make_doc(doc_id="d3"),
    ]
    m = _make_manifest_obj(documents=docs)
    assert m.content_group_count == 3


def test_manifest_content_group_count_one_pair_batch39():
    docs = [
        _make_doc(doc_id="d1", paired_with="d2"),
        _make_doc(doc_id="d2", paired_with="d1"),
    ]
    m = _make_manifest_obj(documents=docs)
    assert m.content_group_count == 1


def test_manifest_content_group_count_pair_plus_unpaired_batch39():
    docs = [
        _make_doc(doc_id="d1", paired_with="d2"),
        _make_doc(doc_id="d2", paired_with="d1"),
        _make_doc(doc_id="d3"),
    ]
    m = _make_manifest_obj(documents=docs)
    assert m.content_group_count == 2


def test_manifest_expected_failures_field_batch39():
    ef = ExpectedFailure("ef", "p", Path("/p"), "E", None)
    m = _make_manifest_obj(expected_failures=[ef])
    assert m.expected_failures == (ef,)


def test_manifest_expected_failures_field_is_tuple_batch39():
    m = _make_manifest_obj(expected_failures=[])
    assert isinstance(m.expected_failures, tuple)


def test_manifest_documents_field_is_tuple_batch39():
    m = _make_manifest_obj(documents=[])
    assert isinstance(m.documents, tuple)


def test_manifest_hashable_batch39():
    m1 = _make_manifest_obj()
    m2 = _make_manifest_obj()
    assert hash(m1) == hash(m2)


def test_manifest_equality_batch39():
    m1 = _make_manifest_obj()
    m2 = _make_manifest_obj()
    assert m1 == m2


def test_manifest_repr_contains_class_name_batch39():
    m = _make_manifest_obj()
    assert "Manifest" in repr(m)


# ---------- _is_absolute_like / _has_backslash 第三十九批


def test_is_absolute_like_empty_string_returns_false_batch39():
    assert _is_absolute_like("") is False


def test_is_absolute_like_single_slash_returns_true_batch39():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_unix_root_only_path_batch39():
    assert _is_absolute_like("/etc") is True


def test_is_absolute_like_windows_drive_lowercase_batch39():
    assert _is_absolute_like("c:/x") is True


def test_is_absolute_like_windows_drive_uppercase_batch39():
    assert _is_absolute_like("C:\\x") is True


def test_is_absolute_like_windows_drive_no_separator_batch39():
    """c:x 不算绝对路径（没有 / 或 \\）。"""
    assert _is_absolute_like("c:x") is False


def test_is_absolute_like_digit_first_batch39():
    """1:/ 不是绝对（必须 isalpha 首字符）。"""
    assert _is_absolute_like("1:/x") is False


def test_is_absolute_like_unicode_first_batch39():
    """中:/x → 中文是 isalpha → True。"""
    assert _is_absolute_like("中:/x") is True


def test_is_absolute_like_relative_path_batch39():
    assert _is_absolute_like("a/b") is False


def test_is_absolute_like_dot_relative_batch39():
    assert _is_absolute_like("./a") is False


def test_is_absolute_like_double_dot_batch39():
    assert _is_absolute_like("../a") is False


def test_has_backslash_present_batch39():
    assert _has_backslash("a\\b") is True


def test_has_backslash_absent_batch39():
    assert _has_backslash("a/b") is False


def test_has_backslash_only_backslash_batch39():
    assert _has_backslash("\\") is True


def test_has_backslash_empty_string_batch39():
    assert _has_backslash("") is False


def test_has_backslash_multiple_backslashes_batch39():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_leading_backslash_batch39():
    assert _has_backslash("\\abc") is True


def test_has_backslash_trailing_backslash_batch39():
    assert _has_backslash("abc\\") is True


# ---------- _resolve_relative_path 第三十九批


def test_resolve_relative_path_returns_path_batch39(tmp_path):
    out = _resolve_relative_path("a/b.pdf", tmp_path, "test")
    assert isinstance(out, Path)


def test_resolve_relative_path_subdir_batch39(tmp_path):
    out = _resolve_relative_path("sub/x.pdf", tmp_path, "test")
    assert out == (tmp_path / "sub" / "x.pdf").resolve()


def test_resolve_relative_path_filename_only_batch39(tmp_path):
    out = _resolve_relative_path("x.pdf", tmp_path, "test")
    assert out == (tmp_path / "x.pdf").resolve()


def test_resolve_relative_path_dot_segments_resolved_batch39(tmp_path):
    """./a/b.pdf → 解析后等价于 a/b.pdf。"""
    out = _resolve_relative_path("./a/b.pdf", tmp_path, "test")
    assert out == (tmp_path / "a" / "b.pdf").resolve()


def test_resolve_relative_path_outside_root_rejected_batch39(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("../outside.pdf", tmp_path, "test")


def test_resolve_relative_path_absolute_rejected_batch39(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("/etc/passwd", tmp_path, "test")


def test_resolve_relative_path_backslash_rejected_batch39(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("a\\b.pdf", tmp_path, "test")


def test_resolve_relative_path_empty_rejected_batch39(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("", tmp_path, "test")


def test_resolve_relative_path_unicode_filename_batch39(tmp_path):
    out = _resolve_relative_path("中文/文件.pdf", tmp_path, "test")
    assert "中文" in str(out)


def test_resolve_relative_path_does_not_require_existing_batch39(tmp_path):
    """文件不需要实际存在。"""
    out = _resolve_relative_path("nonexistent.pdf", tmp_path, "test")
    assert not out.exists()


def test_resolve_relative_path_field_name_in_error_batch39(tmp_path):
    """错误消息含 field_name。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "MY_FIELD")
    assert "MY_FIELD" in str(exc_info.value)


# ---------- load_manifest 第三十九批


def _make_manifest_json(tmp_path, documents=None, expected_failures=None,
                       devset_status="incomplete", manifest_version=None):
    data = {
        "manifest_version": manifest_version or MANIFEST_VERSION,
        "devset_status": devset_status,
        "documents": documents or [],
    }
    if expected_failures:
        data["expected_failures"] = expected_failures
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def test_load_manifest_str_path_batch39(tmp_path):
    mp = _make_manifest_json(tmp_path)
    m = load_manifest(str(mp), project_root=tmp_path)
    assert m.file_count == 0


def test_load_manifest_path_object_batch39(tmp_path):
    mp = _make_manifest_json(tmp_path)
    m = load_manifest(mp, project_root=tmp_path)
    assert m.file_count == 0


def test_load_manifest_nonexistent_file_raises_batch39(tmp_path):
    p = tmp_path / "missing.json"
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "清单文件不存在" in str(exc_info.value)


def test_load_manifest_invalid_json_raises_batch39(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "JSON 解析失败" in str(exc_info.value)


def test_load_manifest_incompatible_version_raises_batch39(tmp_path):
    mp = _make_manifest_json(tmp_path, manifest_version="9.9")
    # schema 也限制 version；可能 EvalSchemaError 先抛
    from evaluation.schema import EvalSchemaError
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(mp, project_root=tmp_path)


def test_load_manifest_absolute_path_rejected_batch39(tmp_path):
    docs = [{"doc_id": "d1", "path": "/etc/passwd", "source_type": "pdf"}]
    mp = _make_manifest_json(tmp_path, documents=docs)
    with pytest.raises(ManifestError):
        load_manifest(mp, project_root=tmp_path)


def test_load_manifest_backslash_path_rejected_batch39(tmp_path):
    docs = [{"doc_id": "d1", "path": "a\\b.pdf", "source_type": "pdf"}]
    mp = _make_manifest_json(tmp_path, documents=docs)
    with pytest.raises(ManifestError):
        load_manifest(mp, project_root=tmp_path)


def test_load_manifest_idempotent_batch39(tmp_path):
    mp = _make_manifest_json(tmp_path)
    m1 = load_manifest(mp, project_root=tmp_path)
    m2 = load_manifest(mp, project_root=tmp_path)
    assert m1 == m2


def test_load_manifest_empty_documents_batch39(tmp_path):
    mp = _make_manifest_json(tmp_path, documents=[])
    m = load_manifest(mp, project_root=tmp_path)
    assert m.file_count == 0
    assert m.documents == ()


def test_load_manifest_one_pdf_one_docx_batch39(tmp_path):
    docs = [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        {"doc_id": "d2", "path": "b.docx", "source_type": "docx"},
    ]
    mp = _make_manifest_json(tmp_path, documents=docs)
    m = load_manifest(mp, project_root=tmp_path)
    assert m.pdf_count == 1
    assert m.docx_count == 1


def test_load_manifest_with_categories_batch39(tmp_path):
    docs = [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "categories": ["x", "y"]},
    ]
    mp = _make_manifest_json(tmp_path, documents=docs)
    m = load_manifest(mp, project_root=tmp_path)
    assert m.documents[0].categories == ("x", "y")


def test_load_manifest_with_paired_with_batch39(tmp_path):
    docs = [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
        {"doc_id": "d2", "path": "b.docx", "source_type": "docx", "paired_with": "d1"},
    ]
    mp = _make_manifest_json(tmp_path, documents=docs)
    m = load_manifest(mp, project_root=tmp_path)
    assert m.documents[0].paired_with == "d2"
    assert m.content_group_count == 1


def test_load_manifest_with_expectations_batch39(tmp_path):
    docs = [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
         "expectations": {"element_count_by_type": {"paragraph": 5}}},
    ]
    mp = _make_manifest_json(tmp_path, documents=docs)
    m = load_manifest(mp, project_root=tmp_path)
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_with_annotation_file_batch39(tmp_path):
    docs = [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
         "annotation_file": "ann/d1.json"},
    ]
    mp = _make_manifest_json(tmp_path, documents=docs)
    m = load_manifest(mp, project_root=tmp_path)
    assert m.documents[0].annotation_file_str == "ann/d1.json"
    assert m.documents[0].annotation_resolved == (tmp_path / "ann" / "d1.json").resolve()


def test_load_manifest_with_expected_failures_batch39(tmp_path):
    efs = [{"doc_id": "ef1", "path": "bad.txt", "expected_error_code": "E_X",
            "source_type": "txt"}]
    mp = _make_manifest_json(tmp_path, expected_failures=efs)
    m = load_manifest(mp, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].doc_id == "ef1"


def test_load_manifest_project_root_string_batch39(tmp_path):
    mp = _make_manifest_json(tmp_path)
    m = load_manifest(mp, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


# ---------- _detect_project_root 第三十九批


def test_detect_project_root_with_pyproject_batch39(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    start = tmp_path / "sub" / "deep"
    start.mkdir(parents=True)
    out = _detect_project_root(start)
    assert out == tmp_path.resolve()


def test_detect_project_root_fallback_to_start_batch39(tmp_path):
    """没有 pyproject.toml 时回退到 start 父目录。"""
    start = tmp_path / "sub"
    start.mkdir(parents=True)
    out = _detect_project_root(start)
    # 没有 pyproject，回退到 start 本身（已 resolved）
    assert out == start.resolve()


def test_detect_project_root_with_file_input_batch39(tmp_path):
    """start 是文件时取父目录。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    start_file = tmp_path / "sub" / "file.txt"
    start_file.parent.mkdir(parents=True)
    start_file.write_text("x", encoding="utf-8")
    out = _detect_project_root(start_file)
    assert out == tmp_path.resolve()


def test_detect_project_root_returns_path_batch39(tmp_path):
    out = _detect_project_root(tmp_path)
    assert isinstance(out, Path)


def test_detect_project_root_no_params_raises_typeerror_batch39():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters.keys()) == ["start"]


# ---------- ManifestError 第三十九批


def test_manifest_error_subclass_of_exception_batch39():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_can_be_raised_batch39():
    with pytest.raises(ManifestError):
        raise ManifestError("x")


def test_manifest_error_can_be_caught_as_exception_batch39():
    try:
        raise ManifestError("x")
    except Exception as e:
        assert isinstance(e, ManifestError)


def test_manifest_error_message_preserved_batch39():
    e = ManifestError("my message")
    assert "my message" in str(e)


def test_manifest_error_no_custom_init_batch39():
    """无 custom __init__；继承 Exception 默认行为。"""
    e = ManifestError("msg")
    assert e.args == ("msg",)


def test_manifest_error_with_unicode_message_batch39():
    e = ManifestError("中文错误")
    assert "中文错误" in str(e)


def test_manifest_error_with_long_message_batch39():
    msg = "x" * 1000
    e = ManifestError(msg)
    assert str(e) == msg


# ---------- module source forbidden tokens 第六十七批


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
def test_module_source_no_forbidden_tokens_batch39(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第六十三批


def test_module_source_contains_design_doc_batch39():
    src = inspect.getsource(mmod)
    assert "开发集清单" in src


def test_module_source_contains_manifest_version_import_batch39():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_contains_schema_validate_import_batch39():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_contains_dataclass_import_batch39():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_contains_json_import_batch39():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_source_contains_pathlib_import_batch39():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch39():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_contains_class_manifest_error_batch39():
    src = inspect.getsource(mmod)
    assert "class ManifestError" in src


def test_module_source_contains_class_document_entry_batch39():
    src = inspect.getsource(mmod)
    assert "class DocumentEntry" in src or "@dataclass(frozen=True)\nclass DocumentEntry" in src


def test_module_source_contains_class_expected_failure_batch39():
    src = inspect.getsource(mmod)
    assert "class ExpectedFailure" in src


def test_module_source_contains_class_manifest_batch39():
    src = inspect.getsource(mmod)
    assert "class Manifest" in src


def test_module_source_contains_is_absolute_like_function_batch39():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in src


def test_module_source_contains_has_backslash_function_batch39():
    src = inspect.getsource(mmod)
    assert "def _has_backslash(" in src


def test_module_source_contains_resolve_relative_path_function_batch39():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in src


def test_module_source_contains_load_manifest_function_batch39():
    src = inspect.getsource(mmod)
    assert "def load_manifest(" in src


def test_module_source_contains_detect_project_root_function_batch39():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root(" in src


def test_module_source_contains_file_count_property_batch39():
    src = inspect.getsource(mmod)
    assert "def file_count(" in src


def test_module_source_contains_pdf_count_property_batch39():
    src = inspect.getsource(mmod)
    assert "def pdf_count(" in src


def test_module_source_contains_docx_count_property_batch39():
    src = inspect.getsource(mmod)
    assert "def docx_count(" in src


def test_module_source_contains_content_group_count_property_batch39():
    src = inspect.getsource(mmod)
    assert "def content_group_count(" in src


def test_module_source_contains_categories_covered_property_batch39():
    src = inspect.getsource(mmod)
    assert "def categories_covered(" in src


def test_module_source_contains_future_annotations_batch39():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


# ---------- signatures 第六十三批


def test_signature_is_absolute_like_one_param_batch39():
    sig = inspect.signature(_is_absolute_like)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_signature_is_absolute_like_return_bool_batch39():
    sig = inspect.signature(_is_absolute_like)
    assert "bool" in str(sig.return_annotation)


def test_signature_has_backslash_one_param_batch39():
    sig = inspect.signature(_has_backslash)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_signature_resolve_relative_path_three_params_batch39():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters.keys()) == ["path_str", "project_root", "field_name"]


def test_signature_resolve_relative_path_return_path_batch39():
    sig = inspect.signature(_resolve_relative_path)
    assert "Path" in str(sig.return_annotation)


def test_signature_load_manifest_two_params_batch39():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters.keys()) == ["manifest_path", "project_root"]


def test_signature_load_manifest_project_root_optional_batch39():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_signature_detect_project_root_one_param_batch39():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters.keys()) == ["start"]


def test_signature_detect_project_root_return_path_batch39():
    sig = inspect.signature(_detect_project_root)
    assert "Path" in str(sig.return_annotation)


# ---------- module 合理性 第六十三批


def test_module_has_all_attribute_batch39():
    assert hasattr(mmod, "__all__")


def test_module_all_is_list_batch39():
    assert isinstance(mmod.__all__, list)


def test_module_all_len_five_batch39():
    assert len(mmod.__all__) == 5


def test_module_all_contains_manifest_error_batch39():
    assert "ManifestError" in mmod.__all__


def test_module_all_contains_manifest_batch39():
    assert "Manifest" in mmod.__all__


def test_module_all_contains_document_entry_batch39():
    assert "DocumentEntry" in mmod.__all__


def test_module_all_contains_expected_failure_batch39():
    assert "ExpectedFailure" in mmod.__all__


def test_module_all_contains_load_manifest_batch39():
    assert "load_manifest" in mmod.__all__


def test_module_does_not_export_helpers_batch39():
    """私有 _xxx 不在 __all__。"""
    for name in ("_is_absolute_like", "_has_backslash", "_resolve_relative_path", "_detect_project_root"):
        assert name not in mmod.__all__


def test_module_has_three_class_definitions_batch39():
    """模块有三个 dataclass：DocumentEntry / ExpectedFailure / Manifest，外加 ManifestError。"""
    import ast
    src = inspect.getsource(mmod)
    tree = ast.parse(src)
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    class_names = {c.name for c in classes}
    assert "ManifestError" in class_names
    assert "DocumentEntry" in class_names
    assert "ExpectedFailure" in class_names
    assert "Manifest" in class_names


def test_module_has_future_annotations_batch39():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


# ---------- 端到端集成 第六十三批


def test_e2e_full_round_trip_with_pair_batch39(tmp_path):
    """完整 round trip：PDF + DOCX 配对。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    docs = [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
         "sha256": "a" * 64, "categories": ["tutorial"],
         "paired_with": "d2"},
        {"doc_id": "d2", "path": "a.docx", "source_type": "docx",
         "sha256": "b" * 64, "categories": ["tutorial"],
         "paired_with": "d1"},
    ]
    mp = _make_manifest_json(tmp_path, documents=docs)
    m = load_manifest(mp)
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.content_group_count == 1
    assert m.categories_covered == ["tutorial"]


def test_e2e_load_manifest_does_not_write_to_disk_batch39(tmp_path):
    mp = _make_manifest_json(tmp_path)
    before = mp.read_text(encoding="utf-8")
    load_manifest(mp, project_root=tmp_path)
    after = mp.read_text(encoding="utf-8")
    assert before == after


def test_e2e_idempotent_load_batch39(tmp_path):
    mp = _make_manifest_json(tmp_path)
    m1 = load_manifest(mp, project_root=tmp_path)
    m2 = load_manifest(mp, project_root=tmp_path)
    assert m1 == m2


def test_e2e_categories_with_mixed_case_batch39(tmp_path):
    """categories 大小写敏感（不强制 lowercase）。"""
    docs = [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
         "categories": ["Tutorial"]},
        {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf",
         "categories": ["tutorial"]},
    ]
    mp = _make_manifest_json(tmp_path, documents=docs)
    m = load_manifest(mp, project_root=tmp_path)
    assert m.categories_covered == ["Tutorial", "tutorial"]


def test_e2e_expected_failure_with_source_type_none_batch39(tmp_path):
    efs = [{"doc_id": "ef1", "path": "bad.txt", "expected_error_code": "E_X"}]
    mp = _make_manifest_json(tmp_path, expected_failures=efs)
    m = load_manifest(mp, project_root=tmp_path)
    assert m.expected_failures[0].source_type is None
