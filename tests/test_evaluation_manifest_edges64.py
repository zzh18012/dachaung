"""evaluation/manifest.py 第六十四轮 edges 测试（Round 579）。

补强 edges63 未触及的角度（第三十七批）。
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, fields
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


# ---------- DocumentEntry 第三十七批


def test_document_entry_no_optional_fields_batch37():
    """只有必需字段（其他全 None/()）。"""
    d = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None)
    assert d.doc_id == "d1"
    assert d.path_str == "a.pdf"


def test_document_entry_with_all_optional_batch37():
    d = DocumentEntry(
        doc_id="d_full",
        path_str="sub/a.pdf",
        resolved_path=Path("/x/sub/a.pdf"),
        source_type="pdf",
        sha256="a" * 64,
        categories=("essay",),
        paired_with="d_other",
        annotation_file_str="sub/a.json",
        annotation_resolved=Path("/x/sub/a.json"),
        expectations={"k": "v"},
    )
    assert d.sha256 == "a" * 64
    assert d.categories == ("essay",)


def test_document_entry_with_empty_string_doc_id_batch37():
    """空字符串 doc_id（schema 不允许，但 dataclass 不限制）。"""
    d = DocumentEntry("", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None)
    assert d.doc_id == ""


def test_document_entry_with_empty_path_str_batch37():
    d = DocumentEntry("d1", "", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None)
    assert d.path_str == ""


def test_document_entry_with_unicode_doc_id_batch37():
    d = DocumentEntry("文档1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None)
    assert d.doc_id == "文档1"


def test_document_entry_with_invalid_source_type_batch37():
    """source_type 任意字符串（dataclass 不限制）。"""
    d = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "txt", None, (),
                     None, None, None, None)
    assert d.source_type == "txt"


def test_document_entry_categories_with_duplicates_batch37():
    """categories 可以含重复（dataclass 不限制）。"""
    d = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None,
                     ("a", "a", "b"), None, None, None, None)
    assert d.categories == ("a", "a", "b")


def test_document_entry_expectations_nested_dict_batch37():
    exp = {"element_count_by_type": {"paragraph": 5}, "nested": {"deep": [1, 2]}}
    d = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, exp)
    assert d.expectations == exp


def test_document_entry_source_type_docx_batch37():
    d = DocumentEntry("d1", "a.docx", Path("/x/a.docx"), "docx", None, (),
                     None, None, None, None)
    assert d.source_type == "docx"


# ---------- ExpectedFailure 第三十七批


def test_expected_failure_with_empty_doc_id_batch37():
    ef = ExpectedFailure("", "bad.pdf", Path("/x/bad.pdf"), "E_PARSE", None)
    assert ef.doc_id == ""


def test_expected_failure_with_unicode_path_batch37():
    ef = ExpectedFailure("d1", "中文.pdf", Path("/x/中文.pdf"),
                        "E_PARSE", "pdf")
    assert ef.path_str == "中文.pdf"


def test_expected_failure_with_long_error_code_batch37():
    ef = ExpectedFailure("d1", "p", Path("/x/p"),
                        "E_VERY_LONG_AND_DESCRIPTIVE_ERROR_CODE", None)
    assert ef.expected_error_code == "E_VERY_LONG_AND_DESCRIPTIVE_ERROR_CODE"


def test_expected_failure_with_empty_error_code_batch37():
    ef = ExpectedFailure("d1", "p", Path("/x/p"), "", None)
    assert ef.expected_error_code == ""


def test_expected_failure_with_all_source_types_batch37():
    for st in ("pdf", "docx", "txt", "other"):
        ef = ExpectedFailure("d1", "p", Path("/x/p"), "E", st)
        assert ef.source_type == st


def test_expected_failure_doc_id_and_path_differ_batch37():
    ef = ExpectedFailure("doc_a", "path_b.pdf", Path("/x/path_b.pdf"),
                        "E_PARSE", None)
    assert ef.doc_id != ef.path_str


# ---------- Manifest properties 第三十七批


def test_manifest_file_count_with_many_docs_batch37():
    docs = tuple(
        DocumentEntry(f"d{i}", f"a{i}.pdf", Path(f"/x/a{i}.pdf"), "pdf", None, (),
                     None, None, None, None)
        for i in range(10)
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.file_count == 10


def test_manifest_pdf_count_with_many_pdfs_batch37():
    docs = tuple(
        DocumentEntry(f"d{i}", f"a{i}.pdf", Path(f"/x/a{i}.pdf"), "pdf", None, (),
                     None, None, None, None)
        for i in range(5)
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.pdf_count == 5


def test_manifest_docx_count_with_many_docx_batch37():
    docs = tuple(
        DocumentEntry(f"d{i}", f"a{i}.docx", Path(f"/x/a{i}.docx"), "docx", None, (),
                     None, None, None, None)
        for i in range(7)
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.docx_count == 7


def test_manifest_categories_covered_unicode_batch37():
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None,
                     ("中文", "english"), None, None, None, None),
        DocumentEntry("d2", "b.pdf", Path("/x/b.pdf"), "pdf", None,
                     ("日本語",), None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    cats = m.categories_covered
    assert "中文" in cats
    assert "english" in cats
    assert "日本語" in cats


def test_manifest_content_group_count_all_paired_batch37():
    """3 对配对（6 docs，3 pairs）→ 3 组。"""
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     "d2", None, None, None),
        DocumentEntry("d2", "b.docx", Path("/x/b.docx"), "docx", None, (),
                     "d1", None, None, None),
        DocumentEntry("d3", "c.pdf", Path("/x/c.pdf"), "pdf", None, (),
                     "d4", None, None, None),
        DocumentEntry("d4", "d.docx", Path("/x/d.docx"), "docx", None, (),
                     "d3", None, None, None),
        DocumentEntry("d5", "e.pdf", Path("/x/e.pdf"), "pdf", None, (),
                     "d6", None, None, None),
        DocumentEntry("d6", "f.docx", Path("/x/f.docx"), "docx", None, (),
                     "d5", None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.content_group_count == 3


def test_manifest_pdf_count_zero_when_all_docx_batch37():
    docs = (
        DocumentEntry("d1", "a.docx", Path("/x/a.docx"), "docx", None, (),
                     None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.pdf_count == 0
    assert m.docx_count == 1


def test_manifest_devset_status_complete_batch37():
    m = Manifest("1.0", "complete", (), (), Path("/x"))
    assert m.devset_status == "complete"


def test_manifest_equality_with_documents_batch37():
    """带 documents 的 Manifest 也能比较（documents 是 tuple 是 hashable）。"""
    docs1 = (DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                          None, None, None, None),)
    docs2 = (DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                          None, None, None, None),)
    m1 = Manifest("1.0", "incomplete", docs1, (), Path("/x"))
    m2 = Manifest("1.0", "incomplete", docs2, (), Path("/x"))
    assert m1 == m2


# ---------- _is_absolute_like / _has_backslash 第三十七批


def test_is_absolute_like_two_letter_drive_batch37():
    """两个字母开头：第一字母是 alpha。"""
    assert _is_absolute_like("AB:/foo") is False  # AB 不算绝对（第二个字符不是 :）

def test_is_absolute_like_just_drive_letter_colon_batch37():
    """'C:' 单独（无后缀斜杠）→ 不是绝对。"""
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_with_query_string_batch37():
    assert _is_absolute_like("?foo") is False


def test_is_absolute_like_with_hash_batch37():
    assert _is_absolute_like("#foo") is False


def test_is_absolute_like_double_slash_batch37():
    """'//' 不算绝对（不是单 /）。"""
    # "//foo" 第一个字符是 / → True
    assert _is_absolute_like("//foo") is True


def test_is_absolute_like_triple_slash_batch37():
    assert _is_absolute_like("///foo") is True


def test_has_backslash_with_forward_then_back_batch37():
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_with_back_then_forward_batch37():
    assert _has_backslash("a\\b/c") is True


def test_has_backslash_with_only_backslashes_batch37():
    assert _has_backslash("\\\\\\") is True


def test_has_backslash_with_spaces_only_batch37():
    assert _has_backslash("   ") is False


def test_has_backslash_with_special_chars_batch37():
    assert _has_backslash("a\tb\nc") is False


# ---------- _resolve_relative_path 第三十七批


def test_resolve_path_returns_absolute_batch37(tmp_path):
    """返回的 Path 是绝对路径。"""
    p = _resolve_relative_path("a.pdf", tmp_path, "f")
    assert p.is_absolute()


def test_resolve_path_subdir_path_batch37(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    p = _resolve_relative_path("sub", tmp_path, "f")
    assert p == sub.resolve()


def test_resolve_path_filename_with_dots_batch37(tmp_path):
    p = _resolve_relative_path("a.b.c.pdf", tmp_path, "f")
    assert p.name == "a.b.c.pdf"


def test_resolve_path_filename_with_spaces_batch37(tmp_path):
    p = _resolve_relative_path("my file.pdf", tmp_path, "f")
    assert p.name == "my file.pdf"


def test_resolve_path_filename_with_unicode_batch37(tmp_path):
    p = _resolve_relative_path("中文.pdf", tmp_path, "f")
    assert "中文" in p.name


def test_resolve_path_drive_letter_backslash_batch37(tmp_path):
    """Windows C:\\xxx → 绝对路径。"""
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("C:\\foo", tmp_path, "f")
    assert "绝对路径" in str(exc.value)


def test_resolve_path_drive_letter_forward_batch37(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("D:/foo", tmp_path, "f")
    assert "绝对路径" in str(exc.value)


def test_resolve_path_backslash_in_middle_batch37(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("a\\b.pdf", tmp_path, "f")
    assert "正斜杠" in str(exc.value)


def test_resolve_path_double_dot_in_filename_batch37(tmp_path):
    """'..' 作为文件名一部分（非路径分隔）。"""
    # "a..pdf" 没有路径分隔，但是 .. 在 normalize 中无影响
    p = _resolve_relative_path("a..pdf", tmp_path, "f")
    assert p.name == "a..pdf"


def test_resolve_path_does_not_create_file_batch37(tmp_path):
    """解析不会创建文件。"""
    _resolve_relative_path("nonexistent.pdf", tmp_path, "f")
    assert not (tmp_path / "nonexistent.pdf").exists()


# ---------- load_manifest 第三十七批


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_with_empty_documents_list_batch37(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents == ()


def test_load_manifest_with_empty_expected_failures_list_batch37(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures == ()


def test_load_manifest_complete_status_batch37(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.devset_status == "complete"


def test_load_manifest_devset_status_invalid_value_batch37(tmp_path):
    """devset_status 不在 enum → schema 失败。"""
    from evaluation.schema import EvalSchemaError
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "pending",
        "documents": [],
        "expected_failures": [],
    })
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_doc_missing_doc_id_batch37(tmp_path):
    """document 缺 doc_id → schema 失败。"""
    from evaluation.schema import EvalSchemaError
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"path": "a.pdf", "source_type": "pdf"}],  # missing doc_id
        "expected_failures": [],
    })
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_doc_missing_path_batch37(tmp_path):
    from evaluation.schema import EvalSchemaError
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "source_type": "pdf"}],  # missing path
        "expected_failures": [],
    })
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_doc_missing_source_type_batch37(tmp_path):
    from evaluation.schema import EvalSchemaError
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf"}],  # missing source_type
        "expected_failures": [],
    })
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_doc_invalid_source_type_batch37(tmp_path):
    """source_type 不在 enum（pdf/docx）→ schema 失败。"""
    from evaluation.schema import EvalSchemaError
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "txt"}],
        "expected_failures": [],
    })
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_doc_with_invalid_sha256_short_batch37(tmp_path):
    """sha256 不是 64 字符 → schema 失败。"""
    from evaluation.schema import EvalSchemaError
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
                       "sha256": "short"}],
        "expected_failures": [],
    })
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_doc_with_invalid_sha256_uppercase_batch37(tmp_path):
    """sha256 含大写字母 → schema pattern 失败（只允许小写 hex）。"""
    from evaluation.schema import EvalSchemaError
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
                       "sha256": "A" * 64}],
        "expected_failures": [],
    })
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_doc_with_valid_sha256_lowercase_batch37(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
                       "sha256": "a" * 64}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 == "a" * 64


def test_load_manifest_doc_with_invalid_paired_with_empty_batch37(tmp_path):
    """schema 限定 paired_with 是 string，不限定 minLength。"""
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    b = tmp_path / "b.docx"
    b.write_text("y", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "paired_with": "d2"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx",
             "paired_with": "d1"},
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].paired_with == "d2"


def test_load_manifest_expected_failure_missing_path_batch37(tmp_path):
    from evaluation.schema import EvalSchemaError
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{"doc_id": "bad1", "expected_error_code": "E_PARSE"}],
    })
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_expected_failure_missing_code_batch37(tmp_path):
    from evaluation.schema import EvalSchemaError
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{"doc_id": "bad1", "path": "bad.pdf"}],
    })
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_expected_failure_invalid_source_type_batch37(tmp_path):
    """expected_failure.source_type 含 'invalid' → schema 失败。"""
    from evaluation.schema import EvalSchemaError
    bad = tmp_path / "bad.pdf"
    bad.write_text("y", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{"doc_id": "bad1", "path": "bad.pdf",
                              "expected_error_code": "E_PARSE",
                              "source_type": "invalid"}],
    })
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_expected_failure_with_txt_source_type_batch37(tmp_path):
    """expected_failure.source_type 允许 txt。"""
    bad = tmp_path / "bad.txt"
    bad.write_text("y", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{"doc_id": "bad1", "path": "bad.txt",
                              "expected_error_code": "E_PARSE",
                              "source_type": "txt"}],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].source_type == "txt"


def test_load_manifest_expected_failure_with_other_source_type_batch37(tmp_path):
    bad = tmp_path / "bad.bin"
    bad.write_text("y", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{"doc_id": "bad1", "path": "bad.bin",
                              "expected_error_code": "E_PARSE",
                              "source_type": "other"}],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].source_type == "other"


def test_load_manifest_does_not_mutate_disk_file_batch37(tmp_path):
    """load_manifest 不修改磁盘文件。"""
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    before = p.read_text(encoding="utf-8")
    load_manifest(p, project_root=tmp_path)
    after = p.read_text(encoding="utf-8")
    assert before == after


def test_load_manifest_idempotent_batch37(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1 == m2


def test_load_manifest_unicode_categories_batch37(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
                       "categories": ["散文", "小说", "随笔"]}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ("散文", "小说", "随笔")


def test_load_manifest_with_str_path_argument_batch37(tmp_path):
    """manifest_path 接受 str（内部用 Path 转换）。"""
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(str(p), project_root=str(tmp_path))
    assert m.file_count == 1


# ---------- _detect_project_root 第三十七批


def test_detect_project_root_from_deep_subdir_batch37(tmp_path):
    """从深层子目录向上找到 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    assert _detect_project_root(deep) == tmp_path.resolve()


def test_detect_project_root_from_file_in_subdir_batch37(tmp_path):
    """传入文件路径 → 从 parent 开始。"""
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    sub = tmp_path / "a"
    sub.mkdir()
    f = sub / "any.json"
    f.write_text("{}", encoding="utf-8")
    assert _detect_project_root(f) == tmp_path.resolve()


def test_detect_project_root_no_pyproject_fallback_cur_batch37(tmp_path):
    """无 pyproject.toml → 返回 cur（resolve 后）。"""
    sub = tmp_path / "x" / "y"
    sub.mkdir(parents=True)
    result = _detect_project_root(sub)
    assert result == sub.resolve()


def test_detect_project_root_already_file_dir_batch37(tmp_path):
    """start 是文件 → cur=start.parent。"""
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    f = tmp_path / "any.json"
    f.write_text("{}", encoding="utf-8")
    # cur 是 tmp_path，有 pyproject.toml → 返回 tmp_path
    assert _detect_project_root(f) == tmp_path.resolve()


# ---------- ManifestError 第三十七批


def test_manifest_error_repr_batch37():
    e = ManifestError("custom message")
    r = repr(e)
    assert "ManifestError" in r
    assert "custom message" in r


def test_manifest_error_can_be_pickled_via_args_batch37():
    """args 元组保留。"""
    e = ManifestError("msg1", "msg2")
    assert e.args == ("msg1", "msg2")


def test_manifest_error_str_with_special_chars_batch37():
    """str 不抛错（含特殊字符）。"""
    e = ManifestError("line1\nline2\ttab 中文 emoji 🎉")
    assert "line1" in str(e)


def test_manifest_error_inherits_from_exception_only_batch37():
    """ManifestError 直接继承 Exception（不是其他子类）。"""
    bases = ManifestError.__bases__
    assert Exception in bases
    # 不是 RuntimeError/ValueError 等的子类
    assert not issubclass(ManifestError, RuntimeError)


# ---------- module source forbidden tokens 第六十一批


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
def test_module_source_no_forbidden_tokens_batch37(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第五十七批


def test_module_source_contains_manifest_version_check_batch37():
    src = inspect.getsource(mmod)
    assert "!= MANIFEST_VERSION" in src


def test_module_source_contains_resolve_call_in_func_batch37():
    src = inspect.getsource(mmod)
    assert "project_root.resolve()" in src


def test_module_source_contains_resolve_relative_path_call_batch37():
    src = inspect.getsource(mmod)
    assert "_resolve_relative_path(" in src


def test_module_source_contains_load_manifest_func_batch37():
    src = inspect.getsource(mmod)
    assert "def load_manifest(" in src


def test_module_source_contains_dataclass_decorator_batch37():
    src = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in src


def test_module_source_contains_doc_id_field_batch37():
    src = inspect.getsource(mmod)
    assert "doc_id: str" in src


def test_module_source_contains_path_str_comment_batch37():
    src = inspect.getsource(mmod)
    assert "原始相对路径" in src


def test_module_source_contains_paired_with_field_batch37():
    src = inspect.getsource(mmod)
    assert "paired_with: str | None" in src


def test_module_source_contains_categories_covered_sort_batch37():
    src = inspect.getsource(mmod)
    assert "return sorted(s)" in src


def test_module_source_contains_pdf_count_logic_batch37():
    src = inspect.getsource(mmod)
    assert 'd.source_type == "pdf"' in src


def test_module_source_contains_docx_count_logic_batch37():
    src = inspect.getsource(mmod)
    assert 'd.source_type == "docx"' in src


def test_module_source_contains_content_group_comment_batch37():
    src = inspect.getsource(mmod)
    assert "配对的 DOCX+PDF" in src


def test_module_source_contains_pair_ids_set_batch37():
    src = inspect.getsource(mmod)
    assert "pair_ids" in src


def test_module_source_contains_frozenset_import_batch37():
    src = inspect.getsource(mmod)
    assert "frozenset" in src


def test_module_source_contains_validate_call_batch37():
    src = inspect.getsource(mmod)
    assert 'validate(data, "manifest.schema.json")' in src


def test_module_source_contains_json_load_batch37():
    src = inspect.getsource(mmod)
    assert "json.load(f)" in src


def test_module_source_contains_encoding_utf8_in_open_batch37():
    src = inspect.getsource(mmod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_file_not_exist_msg_batch37():
    src = inspect.getsource(mmod)
    assert "清单文件不存在" in src


def test_module_source_contains_json_decode_error_msg_batch37():
    src = inspect.getsource(mmod)
    assert "清单 JSON 解析失败" in src


def test_module_source_contains_manifest_version_msg_batch37():
    src = inspect.getsource(mmod)
    assert "manifest_version 不兼容" in src


# ---------- signatures 第五十七批


def test_signature_load_manifest_manifest_path_annotation_batch37():
    sig = inspect.signature(load_manifest)
    p = sig.parameters["manifest_path"]
    assert "Path" in str(p.annotation)
    assert "str" in str(p.annotation)


def test_signature_load_manifest_project_root_annotation_batch37():
    sig = inspect.signature(load_manifest)
    p = sig.parameters["project_root"]
    assert "Path" in str(p.annotation)
    assert "None" in str(p.annotation)


def test_signature_resolve_relative_path_field_name_no_default_batch37():
    sig = inspect.signature(_resolve_relative_path)
    assert sig.parameters["field_name"].default is inspect.Parameter.empty


def test_signature_detect_project_root_start_no_default_batch37():
    sig = inspect.signature(_detect_project_root)
    assert sig.parameters["start"].default is inspect.Parameter.empty


def test_signature_document_entry_constructor_batch37():
    sig = inspect.signature(DocumentEntry.__init__)
    params = list(sig.parameters.keys())
    # self + 10 fields
    assert len(params) == 11


def test_signature_expected_failure_constructor_batch37():
    sig = inspect.signature(ExpectedFailure.__init__)
    params = list(sig.parameters.keys())
    # self + 5 fields
    assert len(params) == 6


def test_signature_manifest_constructor_batch37():
    sig = inspect.signature(Manifest.__init__)
    params = list(sig.parameters.keys())
    # self + 5 fields
    assert len(params) == 6


# ---------- module 合理性第五十七批


def test_module_has_manifest_dataclass_batch37():
    assert isinstance(mmod.Manifest, type)


def test_module_has_document_entry_dataclass_batch37():
    assert isinstance(mmod.DocumentEntry, type)


def test_module_has_expected_failure_dataclass_batch37():
    assert isinstance(mmod.ExpectedFailure, type)


def test_module_has_manifest_error_class_batch37():
    assert isinstance(mmod.ManifestError, type)
    assert issubclass(mmod.ManifestError, Exception)


def test_module_document_entry_is_frozen_batch37():
    """frozen=True。"""
    d = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None)
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "changed"  # type: ignore[misc]


def test_module_manifest_is_frozen_batch37():
    m = Manifest("1.0", "incomplete", (), (), Path("/x"))
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


def test_module_expected_failure_is_frozen_batch37():
    ef = ExpectedFailure("d1", "p", Path("/x/p"), "E", None)
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "changed"  # type: ignore[misc]


def test_module_manifest_error_inherits_exception_batch37():
    assert issubclass(mmod.ManifestError, Exception)


def test_module_all_contains_5_entries_batch37():
    assert len(mmod.__all__) == 5


# ---------- 端到端集成第五十七批


def test_e2e_load_manifest_full_real_flow_batch37(tmp_path):
    """端到端：完整 manifest，含所有可选字段。"""
    pdf = tmp_path / "a.pdf"
    pdf.write_text("x", encoding="utf-8")
    docx = tmp_path / "b.docx"
    docx.write_text("y", encoding="utf-8")
    ann = tmp_path / "a.json"
    ann.write_text("{}", encoding="utf-8")
    bad = tmp_path / "bad.pdf"
    bad.write_text("z", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["essay", "report"], "paired_with": "d2",
             "annotation_file": "a.json", "sha256": "a" * 64,
             "expectations": {"element_count_by_type": {"paragraph": 3}}},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx",
             "categories": ["essay"], "paired_with": "d1"},
        ],
        "expected_failures": [
            {"doc_id": "bad1", "path": "bad.pdf",
             "expected_error_code": "E_PARSE", "source_type": "pdf"},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.content_group_count == 1
    assert sorted(m.categories_covered) == ["essay", "report"]
    assert len(m.expected_failures) == 1
    assert m.documents[0].sha256 == "a" * 64
    assert m.documents[0].annotation_file_str == "a.json"
    assert m.documents[0].annotation_resolved == ann.resolve()
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 3}}


def test_e2e_load_manifest_three_unpaired_docs_batch37(tmp_path):
    """3 个独立 doc → content_group_count=3。"""
    paths = []
    for i in range(3):
        f = tmp_path / f"a{i}.pdf"
        f.write_text(str(i), encoding="utf-8")
        paths.append(f"a{i}.pdf")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": f"d{i}", "path": name, "source_type": "pdf"}
            for i, name in enumerate(paths)
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 3


def test_e2e_load_manifest_two_pairs_batch37(tmp_path):
    """2 对配对 → content_group_count=2。"""
    paths = {}
    for name in ["a.pdf", "b.docx", "c.pdf", "d.docx"]:
        f = tmp_path / name
        f.write_text("x", encoding="utf-8")
        paths[name] = True
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx", "paired_with": "d1"},
            {"doc_id": "d3", "path": "c.pdf", "source_type": "pdf", "paired_with": "d4"},
            {"doc_id": "d4", "path": "d.docx", "source_type": "docx", "paired_with": "d3"},
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 2


def test_e2e_load_manifest_with_subdir_paths_batch37(tmp_path):
    """深层子目录路径正常解析。"""
    sub = tmp_path / "data" / "2024" / "jan"
    sub.mkdir(parents=True)
    f = sub / "doc.pdf"
    f.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "data/2024/jan/doc.pdf",
                       "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].resolved_path == f.resolve()


def test_e2e_load_manifest_idempotent_with_files_batch37(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    b = tmp_path / "b.docx"
    b.write_text("y", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx"},
        ],
        "expected_failures": [],
    })
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1 == m2
    assert m1.project_root == m2.project_root
