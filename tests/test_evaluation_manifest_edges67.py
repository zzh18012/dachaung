"""evaluation/manifest.py 第六十八轮 edges 测试（Round 600）。

补强 edges66 未触及的角度（第四十批）。
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, dataclass, fields, is_dataclass
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


# ---------- _is_absolute_like 第四十批


def test_is_absolute_like_callable_batch40():
    assert callable(_is_absolute_like)


def test_is_absolute_like_only_slash_batch40():
    """单个 / → True（POSIX 根）。"""
    assert _is_absolute_like("/") is True


def test_is_absolute_like_double_backslash_not_absolute_batch40():
    """UNC 路径 \\\\server 不被识别（不 以 / 开头，也不是盘符）。"""
    assert _is_absolute_like("\\\\server\\share") is False


def test_is_absolute_like_three_letter_prefix_no_separator_batch40():
    """'abc' 不被识别为绝对路径（无盘符分隔符）。"""
    assert _is_absolute_like("abc/def") is False


def test_is_absolute_like_windows_drive_with_forward_slash_batch40():
    """'C:/foo' → True。"""
    assert _is_absolute_like("C:/foo") is True


def test_is_absolute_like_lowercase_drive_with_forward_slash_batch40():
    assert _is_absolute_like("c:/foo") is True


def test_is_absolute_like_uppercase_drive_with_backslash_batch40():
    assert _is_absolute_like("D:\\foo") is True


def test_is_absolute_like_relative_with_colon_batch40():
    """'a:b' 不被识别为绝对路径（无分隔符）。"""
    assert _is_absolute_like("a:b") is False


def test_is_absolute_like_relative_path_batch40():
    assert _is_absolute_like("foo/bar.pdf") is False


def test_is_absolute_like_unicode_first_char_batch40():
    """中文字母 str.isalpha() 也为 True（Python Unicode 支持），所以会被识别为盘符。"""
    assert _is_absolute_like("中:/x") is True


def test_is_absolute_like_space_first_batch40():
    """空格不是字母。"""
    assert _is_absolute_like(" :/x") is False


def test_is_absolute_like_digit_first_not_alpha_batch40():
    """'1:/x' → 数字不是字母 → False。"""
    assert _is_absolute_like("1:/x") is False


def test_is_absolute_like_underscore_first_not_alpha_batch40():
    """'_:/x' → 下划线不是 isalpha → False。"""
    assert _is_absolute_like("_:/x") is False


# ---------- _has_backslash 第四十批


def test_has_backslash_callable_batch40():
    assert callable(_has_backslash)


def test_has_backslash_empty_string_batch40():
    assert _has_backslash("") is False


def test_has_backslash_only_backslash_batch40():
    assert _has_backslash("\\") is True


def test_has_backslash_no_backslash_batch40():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_mixed_separators_batch40():
    assert _has_backslash("foo\\bar/baz") is True


def test_has_backslash_multiple_backslashes_batch40():
    assert _has_backslash("\\\\") is True


# ---------- _resolve_relative_path 第四十批


def test_resolve_relative_path_callable_batch40():
    assert callable(_resolve_relative_path)


def test_resolve_relative_path_valid_batch40(tmp_path):
    (tmp_path / "sub").mkdir()
    p = _resolve_relative_path("sub/x.pdf", tmp_path, "field")
    assert isinstance(p, Path)
    assert p == (tmp_path / "sub" / "x.pdf").resolve()


def test_resolve_relative_path_empty_raises_batch40(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("", tmp_path, "field")
    assert "field" in str(exc.value)
    assert "为空" in str(exc.value)


def test_resolve_relative_path_absolute_unix_raises_batch40(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("/etc/passwd", tmp_path, "field")
    assert "绝对路径" in str(exc.value)


def test_resolve_relative_path_windows_drive_raises_batch40(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("C:/foo", tmp_path, "field")
    assert "绝对路径" in str(exc.value)


def test_resolve_relative_path_backslash_raises_batch40(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("foo\\bar", tmp_path, "field")
    assert "反斜杠" in str(exc.value)


def test_resolve_relative_path_outside_project_raises_batch40(tmp_path):
    """../../foo 通过路径校验但 resolve 后位于项目根外。"""
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("../../foo", tmp_path, "field")
    assert "项目根目录之外" in str(exc.value)


def test_resolve_relative_path_dot_current_batch40(tmp_path):
    """'./foo' 合法。"""
    (tmp_path / "foo.pdf").write_text("x", encoding="utf-8")
    p = _resolve_relative_path("./foo.pdf", tmp_path, "field")
    assert p == (tmp_path / "foo.pdf").resolve()


def test_resolve_relative_path_deeply_nested_batch40(tmp_path):
    """深层目录合法。"""
    p = _resolve_relative_path("a/b/c/d/e.pdf", tmp_path, "field")
    assert p == (tmp_path / "a/b/c/d/e.pdf").resolve()


def test_resolve_relative_path_returns_resolved_path_batch40(tmp_path):
    """返回的 Path 是 resolve 后的（绝对路径）。"""
    p = _resolve_relative_path("foo.pdf", tmp_path, "field")
    assert p.is_absolute()


def test_resolve_relative_path_signature_3_params_batch40():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters.keys()) == ["path_str", "project_root", "field_name"]


def test_resolve_relative_path_no_defaults_batch40():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


# ---------- DocumentEntry 第四十批


def _make_doc_entry(**kwargs):
    defaults = {
        "doc_id": "d1",
        "path_str": "foo.pdf",
        "resolved_path": Path("/tmp/foo.pdf"),
        "source_type": "pdf",
        "sha256": None,
        "categories": (),
        "paired_with": None,
        "annotation_file_str": None,
        "annotation_resolved": None,
        "expectations": None,
    }
    defaults.update(kwargs)
    return DocumentEntry(**defaults)


def test_document_entry_dataclass_batch40():
    assert is_dataclass(DocumentEntry)


def test_document_entry_field_count_ten_batch40():
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_field_names_batch40():
    names = {f.name for f in fields(DocumentEntry)}
    expected = {
        "doc_id", "path_str", "resolved_path", "source_type", "sha256",
        "categories", "paired_with", "annotation_file_str",
        "annotation_resolved", "expectations",
    }
    assert names == expected


def test_document_entry_frozen_batch40():
    d = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "modified"  # type: ignore


def test_document_entry_sha256_optional_batch40():
    d = _make_doc_entry(sha256=None)
    assert d.sha256 is None


def test_document_entry_sha256_str_batch40():
    d = _make_doc_entry(sha256="a" * 64)
    assert d.sha256 == "a" * 64


def test_document_entry_categories_default_empty_tuple_batch40():
    d = _make_doc_entry()
    assert d.categories == ()


def test_document_entry_categories_with_values_batch40():
    d = _make_doc_entry(categories=("tutorial", "reference"))
    assert d.categories == ("tutorial", "reference")


def test_document_entry_paired_with_optional_batch40():
    d = _make_doc_entry(paired_with="d2")
    assert d.paired_with == "d2"


def test_document_entry_annotation_resolved_optional_batch40():
    d = _make_doc_entry(annotation_resolved=None)
    assert d.annotation_resolved is None


def test_document_entry_annotation_resolved_path_batch40():
    p = Path("/tmp/ann.json")
    d = _make_doc_entry(annotation_resolved=p)
    assert d.annotation_resolved == p


def test_document_entry_expectations_dict_batch40():
    e = {"element_count_by_type": {"paragraph": 5}}
    d = _make_doc_entry(expectations=e)
    assert d.expectations == e


def test_document_entry_equality_same_fields_batch40():
    d1 = _make_doc_entry()
    d2 = _make_doc_entry()
    assert d1 == d2


def test_document_entry_inequality_diff_doc_id_batch40():
    d1 = _make_doc_entry(doc_id="d1")
    d2 = _make_doc_entry(doc_id="d2")
    assert d1 != d2


def test_document_entry_hashable_with_hashable_categories_batch40():
    d = _make_doc_entry(categories=("a", "b"))
    h = hash(d)
    assert isinstance(h, int)


def test_document_entry_hashable_with_hashable_expectations_none_batch40():
    d = _make_doc_entry(expectations=None)
    h = hash(d)
    assert isinstance(h, int)


def test_document_entry_not_hashable_with_dict_expectations_batch40():
    """dict expectations → 不可 hash。"""
    d = _make_doc_entry(expectations={"a": 1})
    with pytest.raises(TypeError):
        hash(d)


# ---------- ExpectedFailure 第四十批


def _make_ef(**kwargs):
    defaults = {
        "doc_id": "ef1",
        "path_str": "bad.pdf",
        "resolved_path": Path("/tmp/bad.pdf"),
        "expected_error_code": "E_PARSE",
        "source_type": None,
    }
    defaults.update(kwargs)
    return ExpectedFailure(**defaults)


def test_expected_failure_dataclass_batch40():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_field_count_five_batch40():
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_field_names_batch40():
    names = {f.name for f in fields(ExpectedFailure)}
    expected = {"doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"}
    assert names == expected


def test_expected_failure_frozen_batch40():
    ef = _make_ef()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "modified"  # type: ignore


def test_expected_failure_source_type_optional_batch40():
    ef = _make_ef(source_type=None)
    assert ef.source_type is None


def test_expected_failure_source_type_str_batch40():
    ef = _make_ef(source_type="pdf")
    assert ef.source_type == "pdf"


def test_expected_failure_expected_error_code_str_batch40():
    ef = _make_ef(expected_error_code="E_ANY")
    assert ef.expected_error_code == "E_ANY"


def test_expected_failure_equality_batch40():
    ef1 = _make_ef()
    ef2 = _make_ef()
    assert ef1 == ef2


def test_expected_failure_inequality_diff_code_batch40():
    ef1 = _make_ef(expected_error_code="E_PARSE")
    ef2 = _make_ef(expected_error_code="E_OTHER")
    assert ef1 != ef2


def test_expected_failure_hashable_batch40():
    ef = _make_ef()
    h = hash(ef)
    assert isinstance(h, int)


# ---------- Manifest properties 第四十批


def _make_manifest(docs=None, failures=None, project_root=None, devset_status="incomplete"):
    return Manifest(
        manifest_version=MANIFEST_VERSION,
        devset_status=devset_status,
        documents=tuple(docs or []),
        expected_failures=tuple(failures or []),
        project_root=project_root or Path.cwd(),
    )


def test_manifest_dataclass_batch40():
    assert is_dataclass(Manifest)


def test_manifest_field_count_five_batch40():
    assert len(fields(Manifest)) == 5


def test_manifest_field_names_batch40():
    names = {f.name for f in fields(Manifest)}
    expected = {"manifest_version", "devset_status", "documents", "expected_failures", "project_root"}
    assert names == expected


def test_manifest_frozen_batch40():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore


def test_manifest_file_count_empty_batch40():
    m = _make_manifest(docs=[])
    assert m.file_count == 0


def test_manifest_file_count_three_batch40():
    docs = [_make_doc_entry(doc_id=f"d{i}") for i in range(3)]
    m = _make_manifest(docs=docs)
    assert m.file_count == 3


def test_manifest_pdf_count_only_pdfs_batch40():
    docs = [
        _make_doc_entry(doc_id="d1", source_type="pdf"),
        _make_doc_entry(doc_id="d2", source_type="pdf"),
    ]
    m = _make_manifest(docs=docs)
    assert m.pdf_count == 2


def test_manifest_docx_count_only_docx_batch40():
    docs = [
        _make_doc_entry(doc_id="d1", source_type="docx"),
        _make_doc_entry(doc_id="d2", source_type="docx"),
    ]
    m = _make_manifest(docs=docs)
    assert m.docx_count == 2


def test_manifest_pdf_plus_docx_batch40():
    docs = [
        _make_doc_entry(doc_id="d1", source_type="pdf"),
        _make_doc_entry(doc_id="d2", source_type="docx"),
    ]
    m = _make_manifest(docs=docs)
    assert m.pdf_count == 1
    assert m.docx_count == 1


def test_manifest_no_other_source_types_counted_batch40():
    """非 pdf/docx 的 source_type 不算入 pdf/docx count。"""
    docs = [_make_doc_entry(doc_id="d1", source_type="txt")]
    m = _make_manifest(docs=docs)
    assert m.pdf_count == 0
    assert m.docx_count == 0
    assert m.file_count == 1


def test_manifest_categories_covered_sorted_batch40():
    docs = [
        _make_doc_entry(doc_id="d1", categories=("z", "a")),
        _make_doc_entry(doc_id="d2", categories=("m",)),
    ]
    m = _make_manifest(docs=docs)
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_empty_batch40():
    m = _make_manifest(docs=[])
    assert m.categories_covered == []


def test_manifest_categories_covered_returns_list_batch40():
    m = _make_manifest(docs=[])
    assert isinstance(m.categories_covered, list)


def test_manifest_content_group_count_no_pairs_batch40():
    docs = [
        _make_doc_entry(doc_id="d1"),
        _make_doc_entry(doc_id="d2"),
    ]
    m = _make_manifest(docs=docs)
    assert m.content_group_count == 2


def test_manifest_content_group_count_one_pair_batch40():
    docs = [
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
    ]
    m = _make_manifest(docs=docs)
    # frozenset({d1, d2}) 一个 group
    assert m.content_group_count == 1


def test_manifest_content_group_count_pair_plus_unpaired_batch40():
    docs = [
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
        _make_doc_entry(doc_id="d3"),
    ]
    m = _make_manifest(docs=docs)
    assert m.content_group_count == 2  # 1 group + 1 unpaired


def test_manifest_content_group_count_one_sided_pair_batch40():
    """单向 paired_with → 也算 1 组（d2 视为 unpaired）。"""
    docs = [
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2"),  # 无反向
    ]
    m = _make_manifest(docs=docs)
    # pair_ids = {frozenset({d1, d2})} → groups=1, seen={d1, d2}
    # d2 in seen → 不算 unpaired
    # 总数 = 1
    assert m.content_group_count == 1


def test_manifest_devset_status_value_batch40():
    m = _make_manifest(devset_status="complete")
    assert m.devset_status == "complete"


def test_manifest_project_root_value_batch40():
    pr = Path("/some/project")
    m = _make_manifest(project_root=pr)
    assert m.project_root == pr


def test_manifest_equality_batch40():
    m1 = _make_manifest()
    m2 = _make_manifest()
    assert m1 == m2


def test_manifest_hashable_no_dict_expectations_batch40():
    """Manifest 含 tuple of frozen dataclass → 可 hash（前提是内部 field 可 hash）。"""
    m = _make_manifest()  # docs / failures 都是空 tuple
    h = hash(m)
    assert isinstance(h, int)


def test_manifest_documents_field_is_tuple_batch40():
    m = _make_manifest(docs=[_make_doc_entry()])
    assert isinstance(m.documents, tuple)


def test_manifest_expected_failures_field_is_tuple_batch40():
    m = _make_manifest(failures=[_make_ef()])
    assert isinstance(m.expected_failures, tuple)


def test_manifest_manifest_version_value_batch40():
    m = _make_manifest()
    assert m.manifest_version == MANIFEST_VERSION


# ---------- ManifestError 第四十批


def test_manifest_error_is_exception_batch40():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_default_message_batch40():
    err = ManifestError()
    assert str(err) == ""


def test_manifest_error_with_message_batch40():
    err = ManifestError("boom")
    assert str(err) == "boom"


def test_manifest_error_can_be_raised_batch40():
    with pytest.raises(ManifestError) as exc:
        raise ManifestError("test")
    assert "test" in str(exc.value)


def test_manifest_error_can_be_caught_as_exception_batch40():
    with pytest.raises(Exception):
        raise ManifestError("caught")


def test_manifest_error_module_level_batch40():
    assert hasattr(mmod, "ManifestError")


# ---------- _detect_project_root 第四十批


def test_detect_project_root_callable_batch40():
    assert callable(_detect_project_root)


def test_detect_project_root_with_pyproject_batch40(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    # 从子目录开始找
    sub = tmp_path / "sub"
    sub.mkdir()
    assert _detect_project_root(sub) == tmp_path


def test_detect_project_root_no_pyproject_returns_input_batch40(tmp_path):
    """找不到 pyproject.toml → 返回 start 的 parent。"""
    out = _detect_project_root(tmp_path)
    # cur = tmp_path.resolve()
    assert out == tmp_path.resolve()


def test_detect_project_root_with_file_input_batch40(tmp_path):
    """传入文件路径 → 从 parent 开始找。"""
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    f = tmp_path / "a.txt"
    f.write_text("x", encoding="utf-8")
    assert _detect_project_root(f) == tmp_path


def test_detect_project_root_deep_nested_batch40(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    assert _detect_project_root(deep) == tmp_path


# ---------- load_manifest 第四十批


def _write_valid_manifest(tmp_path: Path) -> Path:
    """在 tmp_path 写一个合法 manifest，并返回其路径。"""
    manifest_data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "foo.pdf",
                "source_type": "pdf",
                "categories": ["tutorial"],
            },
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest_data), encoding="utf-8")
    # 创建实际文件以通过路径校验
    (tmp_path / "foo.pdf").write_text("x", encoding="utf-8")
    return p


def test_load_manifest_callable_batch40():
    assert callable(load_manifest)


def test_load_manifest_missing_file_raises_batch40(tmp_path):
    with pytest.raises(ManifestError) as exc:
        load_manifest(tmp_path / "missing.json")
    assert "清单文件不存在" in str(exc.value)


def test_load_manifest_invalid_json_raises_batch40(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p)
    assert "JSON 解析失败" in str(exc.value)


def test_load_manifest_str_path_input_batch40(tmp_path):
    """manifest_path 接受 str。"""
    p = _write_valid_manifest(tmp_path)
    out = load_manifest(str(p), project_root=tmp_path)
    assert isinstance(out, Manifest)


def test_load_manifest_returns_manifest_batch40(tmp_path):
    p = _write_valid_manifest(tmp_path)
    out = load_manifest(p, project_root=tmp_path)
    assert isinstance(out, Manifest)


def test_load_manifest_devset_status_batch40(tmp_path):
    p = _write_valid_manifest(tmp_path)
    out = load_manifest(p, project_root=tmp_path)
    assert out.devset_status == "incomplete"


def test_load_manifest_manifest_version_batch40(tmp_path):
    p = _write_valid_manifest(tmp_path)
    out = load_manifest(p, project_root=tmp_path)
    assert out.manifest_version == MANIFEST_VERSION


def test_load_manifest_documents_count_batch40(tmp_path):
    p = _write_valid_manifest(tmp_path)
    out = load_manifest(p, project_root=tmp_path)
    assert len(out.documents) == 1


def test_load_manifest_documents_resolved_path_batch40(tmp_path):
    p = _write_valid_manifest(tmp_path)
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].resolved_path == (tmp_path / "foo.pdf").resolve()


def test_load_manifest_documents_categories_batch40(tmp_path):
    p = _write_valid_manifest(tmp_path)
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].categories == ("tutorial",)


def test_load_manifest_project_root_batch40(tmp_path):
    p = _write_valid_manifest(tmp_path)
    out = load_manifest(p, project_root=tmp_path)
    assert out.project_root == tmp_path.resolve()


def test_load_manifest_with_expected_failures_batch40(tmp_path):
    """带 expected_failures 的 manifest。"""
    (tmp_path / "bad.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "ef1",
                "path": "bad.pdf",
                "expected_error_code": "E_PARSE",
                "source_type": "pdf",
            },
        ],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert len(out.expected_failures) == 1
    assert out.expected_failures[0].doc_id == "ef1"


def test_load_manifest_with_annotation_file_batch40(tmp_path):
    """带 annotation_file 的文档。"""
    (tmp_path / "foo.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "foo.ann.json").write_text("{}", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "foo.pdf",
                "source_type": "pdf",
                "annotation_file": "foo.ann.json",
            },
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].annotation_file_str == "foo.ann.json"
    assert out.documents[0].annotation_resolved == (tmp_path / "foo.ann.json").resolve()


def test_load_manifest_with_expectations_batch40(tmp_path):
    (tmp_path / "foo.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "foo.pdf",
                "source_type": "pdf",
                "expectations": {"element_count_by_type": {"paragraph": 5}},
            },
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_with_paired_with_batch40(tmp_path):
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "b.docx").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx", "paired_with": "d1"},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].paired_with == "d2"
    assert out.content_group_count == 1


def test_load_manifest_wrong_version_raises_batch40(tmp_path):
    (tmp_path / "foo.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": "0.0.0",  # 错误版本
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises((ManifestError, Exception)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_auto_detect_project_root_batch40(tmp_path):
    """project_root=None → 自动检测。"""
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    p = _write_valid_manifest(tmp_path)
    out = load_manifest(p)  # 不传 project_root
    assert out.project_root == tmp_path.resolve()


def test_load_manifest_path_field_absolute_raises_batch40(tmp_path):
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "/etc/passwd", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "绝对路径" in str(exc.value)


def test_load_manifest_path_field_backslash_raises_batch40(tmp_path):
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "foo\\bar.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "反斜杠" in str(exc.value)


def test_load_manifest_path_field_outside_project_raises_batch40(tmp_path):
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "../../foo.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "项目根目录之外" in str(exc.value)


def test_load_manifest_signature_two_params_batch40():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters.keys()) == ["manifest_path", "project_root"]


def test_load_manifest_project_root_default_none_batch40():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_load_manifest_manifest_path_no_default_batch40():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["manifest_path"].default is inspect.Parameter.empty


# ---------- module source forbidden tokens 第七十三批


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
def test_module_source_no_forbidden_tokens_batch40(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第六十九批


def test_module_source_contains_design_doc_batch40():
    src = inspect.getsource(mmod)
    assert "开发集清单加载器" in src


def test_module_source_contains_future_annotations_batch40():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_json_import_batch40():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_source_contains_dataclass_import_batch40():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_contains_pathlib_path_import_batch40():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch40():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_contains_manifest_version_import_batch40():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_contains_schema_validate_import_batch40():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_contains_manifest_error_class_batch40():
    src = inspect.getsource(mmod)
    assert "class ManifestError" in src


def test_module_source_contains_document_entry_class_batch40():
    src = inspect.getsource(mmod)
    assert "class DocumentEntry" in src
    assert "@dataclass(frozen=True)" in src


def test_module_source_contains_expected_failure_class_batch40():
    src = inspect.getsource(mmod)
    assert "class ExpectedFailure" in src


def test_module_source_contains_manifest_class_batch40():
    src = inspect.getsource(mmod)
    assert "class Manifest" in src


def test_module_source_contains_load_manifest_function_batch40():
    src = inspect.getsource(mmod)
    assert "def load_manifest(" in src


def test_module_source_contains_detect_project_root_function_batch40():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root(" in src


def test_module_source_contains_resolve_relative_path_function_batch40():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in src


def test_module_source_contains_is_absolute_like_function_batch40():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in src


def test_module_source_contains_has_backslash_function_batch40():
    src = inspect.getsource(mmod)
    assert "def _has_backslash(" in src


def test_module_source_contains_pyproject_keyword_batch40():
    src = inspect.getsource(mmod)
    assert "pyproject.toml" in src


def test_module_source_contains_utf8_keyword_batch40():
    src = inspect.getsource(mmod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_relative_path_keyword_batch40():
    src = inspect.getsource(mmod)
    assert "相对路径" in src


def test_module_source_contains_absolute_path_keyword_batch40():
    src = inspect.getsource(mmod)
    assert "绝对路径" in src


def test_module_source_contains_backslash_keyword_batch40():
    src = inspect.getsource(mmod)
    assert "反斜杠" in src


def test_module_source_contains_categories_keyword_batch40():
    src = inspect.getsource(mmod)
    assert "categories" in src


def test_module_source_contains_paired_with_keyword_batch40():
    src = inspect.getsource(mmod)
    assert "paired_with" in src


def test_module_source_contains_annotation_file_keyword_batch40():
    src = inspect.getsource(mmod)
    assert "annotation_file" in src


def test_module_source_contains_expectations_keyword_batch40():
    src = inspect.getsource(mmod)
    assert "expectations" in src


def test_module_source_contains_all_export_batch40():
    src = inspect.getsource(mmod)
    assert "__all__" in src


# ---------- signatures 第六十九批


def test_signature_load_manifest_params_batch40():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters.keys()) == ["manifest_path", "project_root"]


def test_signature_load_manifest_manifest_path_annotation_batch40():
    sig = inspect.signature(load_manifest)
    ann = str(sig.parameters["manifest_path"].annotation)
    assert "Path" in ann
    assert "str" in ann


def test_signature_load_manifest_project_root_annotation_batch40():
    sig = inspect.signature(load_manifest)
    ann = str(sig.parameters["project_root"].annotation)
    assert "Path" in ann
    assert "str" in ann
    assert "None" in ann


def test_signature_load_manifest_return_manifest_batch40():
    sig = inspect.signature(load_manifest)
    assert "Manifest" in str(sig.return_annotation)


def test_signature_resolve_relative_path_params_batch40():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters.keys()) == ["path_str", "project_root", "field_name"]


def test_signature_resolve_relative_path_return_path_batch40():
    sig = inspect.signature(_resolve_relative_path)
    assert "Path" in str(sig.return_annotation)


def test_signature_detect_project_root_params_batch40():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters.keys()) == ["start"]


def test_signature_detect_project_root_return_path_batch40():
    sig = inspect.signature(_detect_project_root)
    assert "Path" in str(sig.return_annotation)


def test_signature_is_absolute_like_one_param_batch40():
    sig = inspect.signature(_is_absolute_like)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_signature_is_absolute_like_return_bool_batch40():
    sig = inspect.signature(_is_absolute_like)
    assert "bool" in str(sig.return_annotation)


def test_signature_has_backslash_one_param_batch40():
    sig = inspect.signature(_has_backslash)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_signature_has_backslash_return_bool_batch40():
    sig = inspect.signature(_has_backslash)
    assert "bool" in str(sig.return_annotation)


# ---------- module 合理性 第六十九批


def test_module_has_all_attribute_batch40():
    assert hasattr(mmod, "__all__")


def test_module_all_is_list_batch40():
    assert isinstance(mmod.__all__, list)


def test_module_all_five_entries_batch40():
    assert len(mmod.__all__) == 5


def test_module_all_contains_manifest_error_batch40():
    assert "ManifestError" in mmod.__all__


def test_module_all_contains_manifest_batch40():
    assert "Manifest" in mmod.__all__


def test_module_all_contains_document_entry_batch40():
    assert "DocumentEntry" in mmod.__all__


def test_module_all_contains_expected_failure_batch40():
    assert "ExpectedFailure" in mmod.__all__


def test_module_all_contains_load_manifest_batch40():
    assert "load_manifest" in mmod.__all__


def test_module_does_not_export_helpers_batch40():
    for name in ("_is_absolute_like", "_has_backslash", "_resolve_relative_path", "_detect_project_root"):
        assert name not in mmod.__all__


def test_module_has_manifest_error_attr_batch40():
    assert hasattr(mmod, "ManifestError")


def test_module_has_document_entry_attr_batch40():
    assert hasattr(mmod, "DocumentEntry")


def test_module_has_expected_failure_attr_batch40():
    assert hasattr(mmod, "ExpectedFailure")


def test_module_has_manifest_attr_batch40():
    assert hasattr(mmod, "Manifest")


def test_module_has_load_manifest_attr_batch40():
    assert hasattr(mmod, "load_manifest")


def test_module_load_manifest_callable_batch40():
    assert callable(mmod.load_manifest)


def test_module_no_module_level_code_outside_functions_batch40():
    """AST：顶层只有 import / class / function def / __all__。"""
    import ast
    src = inspect.getsource(mmod)
    tree = ast.parse(src)
    for node in tree.body:
        assert isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.FunctionDef, ast.Assign, ast.Expr))


# ---------- 端到端集成 第六十九批


def test_e2e_load_manifest_minimal_batch40(tmp_path):
    """最小合法 manifest 端到端加载。"""
    p = _write_valid_manifest(tmp_path)
    out = load_manifest(p, project_root=tmp_path)
    assert isinstance(out, Manifest)
    assert len(out.documents) == 1
    assert out.documents[0].doc_id == "d1"


def test_e2e_load_manifest_idempotent_batch40(tmp_path):
    """同一 manifest 两次加载结果一致。"""
    p = _write_valid_manifest(tmp_path)
    out1 = load_manifest(p, project_root=tmp_path)
    out2 = load_manifest(p, project_root=tmp_path)
    assert out1 == out2


def test_e2e_load_manifest_pdf_count_batch40(tmp_path):
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "b.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "c.docx").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf"},
            {"doc_id": "d3", "path": "c.docx", "source_type": "docx"},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.pdf_count == 2
    assert out.docx_count == 1
    assert out.file_count == 3


def test_e2e_load_manifest_categories_covered_batch40(tmp_path):
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "b.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "categories": ["tutorial", "intro"]},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf", "categories": ["tutorial", "advanced"]},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.categories_covered == ["advanced", "intro", "tutorial"]
