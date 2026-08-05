r"""evaluation/manifest.py 边角测试 - 第八轮（Round 196）。

补强已有 base/edges/edges2-7（共 821 测试）未覆盖的深度：
- _is_absolute_like 各 Windows/POSIX/盘符边界（digit/underscore/无 separator）
- _has_backslash 单字符/混合路径
- _resolve_relative_path 错误消息精确（field_name 透传）
- DocumentEntry/ExpectedFailure/Manifest frozen 行为
- Manifest.content_group_count 自配对/单向/三向/混合
- Manifest.categories_covered 排序与去重
- load_manifest manifest_version mismatch / annotation_file / expected_failures source_type
- _detect_project_root 多 pyproject.toml 链
- 模块结构与签名深度
- 综合行为
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
# _is_absolute_like 深度
# =========================================================================


def test_is_absolute_like_empty_string():
    assert _is_absolute_like("") is False


def test_is_absolute_like_single_slash():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_posix_absolute():
    assert _is_absolute_like("/foo/bar") is True


def test_is_absolute_like_relative_no_slash():
    assert _is_absolute_like("foo") is False


def test_is_absolute_like_relative_with_slash():
    assert _is_absolute_like("foo/bar") is False


def test_is_absolute_like_windows_backslash_drive():
    assert _is_absolute_like("C:\\foo") is True


def test_is_absolute_like_windows_forward_slash_drive():
    assert _is_absolute_like("C:/foo") is True


def test_is_absolute_like_windows_drive_no_separator():
    """'C:foo' 没有 \\ 或 / 在 [2] → False。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_lowercase_drive():
    assert _is_absolute_like("c:\\foo") is True


def test_is_absolute_like_uppercase_drive_letter_only():
    """'C' 单字符 → len < 3 → False。"""
    assert _is_absolute_like("C") is False


def test_is_absolute_like_two_chars_no_colon():
    assert _is_absolute_like("CD") is False


def test_is_absolute_like_digit_drive():
    """'1:\\' → 第 0 字符是 digit 不是 alpha → False。"""
    assert _is_absolute_like("1:\\foo") is False


def test_is_absolute_like_underscore_drive():
    """'_:\\' → underscore 不是 alpha → False。"""
    assert _is_absolute_like("_:\\foo") is False


def test_is_absolute_like_two_letters_no_separator():
    """'AB' → [1]='B' 不是 ':' → False。"""
    assert _is_absolute_like("AB") is False


def test_is_absolute_like_two_letters_with_colon_no_sep():
    """'AB:' → [2]=':' 不是 \\ 或 / → False。"""
    assert _is_absolute_like("AB:") is False


def test_is_absolute_like_just_colon():
    assert _is_absolute_like(":") is False


def test_is_absolute_like_just_colon_slash():
    """len < 3 → False（':/' 只有 2 字符）。"""
    assert _is_absolute_like(":/") is False


def test_is_absolute_like_relative_with_subdir():
    assert _is_absolute_like("a/b/c") is False


def test_is_absolute_like_dot_relative():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_dotdot_relative():
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_z_drive_forward():
    assert _is_absolute_like("Z:/x") is True


# =========================================================================
# _has_backslash 深度
# =========================================================================


def test_has_backslash_single():
    assert _has_backslash("a\\b") is True


def test_has_backslash_only_backslash():
    assert _has_backslash("\\") is True


def test_has_backslash_empty():
    assert _has_backslash("") is False


def test_has_backslash_no_backslash():
    assert _has_backslash("a/b") is False


def test_has_backslash_mixed():
    """混合路径中有 \\ → True。"""
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_multiple_backslashes():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_only_forward():
    assert _has_backslash("////") is False


def test_has_backslash_trailing_backslash():
    assert _has_backslash("abc\\") is True


# =========================================================================
# _resolve_relative_path 深度
# =========================================================================


def test_resolve_relative_path_empty_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as excinfo:
        _resolve_relative_path("", tmp_path, "test_field")
    assert "test_field" in str(excinfo.value)
    assert "为空" in str(excinfo.value)


def test_resolve_relative_path_absolute_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as excinfo:
        _resolve_relative_path("/etc/passwd", tmp_path, "myfield")
    assert "myfield" in str(excinfo.value)
    assert "绝对路径" in str(excinfo.value)


def test_resolve_relative_path_windows_drive_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as excinfo:
        _resolve_relative_path("C:\\foo", tmp_path, "f")
    assert "绝对路径" in str(excinfo.value)


def test_resolve_relative_path_backslash_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as excinfo:
        _resolve_relative_path("a\\b", tmp_path, "myfield")
    assert "myfield" in str(excinfo.value)
    assert "反斜杠" in str(excinfo.value)


def test_resolve_relative_path_outside_project_root_raises(tmp_path: Path):
    """'..' 跳出 project_root → ManifestError。"""
    with pytest.raises(ManifestError) as excinfo:
        _resolve_relative_path("../outside.txt", tmp_path, "f")
    assert "项目根目录之外" in str(excinfo.value)


def test_resolve_relative_path_nested_outside_raises(tmp_path: Path):
    """'a/../../outside' → 解析后跳出。"""
    with pytest.raises(ManifestError) as excinfo:
        _resolve_relative_path("a/../../outside.txt", tmp_path, "f")
    assert "项目根目录之外" in str(excinfo.value)


def test_resolve_relative_path_valid_returns_path(tmp_path: Path):
    result = _resolve_relative_path("foo.txt", tmp_path, "f")
    assert isinstance(result, Path)
    assert result.is_absolute()
    assert result == (tmp_path / "foo.txt").resolve()


def test_resolve_relative_path_nested_subdir(tmp_path: Path):
    result = _resolve_relative_path("a/b/c.txt", tmp_path, "f")
    assert result == (tmp_path / "a" / "b" / "c.txt").resolve()


def test_resolve_relative_path_dot_stays_in_root(tmp_path: Path):
    """'.' 解析为 project_root 本身。"""
    result = _resolve_relative_path(".", tmp_path, "f")
    assert result == tmp_path.resolve()


def test_resolve_relative_path_dotdot_within_root(tmp_path: Path):
    """'a/../b' → 仍在 root 内。"""
    result = _resolve_relative_path("a/../b.txt", tmp_path, "f")
    assert result == (tmp_path / "b.txt").resolve()


def test_resolve_relative_path_field_name_in_message(tmp_path: Path):
    """field_name 应出现在错误消息中（debugging 友好）。"""
    with pytest.raises(ManifestError) as excinfo:
        _resolve_relative_path("", tmp_path, "documents[doc_x].path")
    assert "documents[doc_x].path" in str(excinfo.value)


def test_resolve_relative_path_returns_resolved_no_symlinks(tmp_path: Path):
    """resolve() 会规范化路径（无 .. 残留）。"""
    result = _resolve_relative_path("a/./b/c.txt", tmp_path, "f")
    # . 段被消除
    assert "/./" not in str(result)


# =========================================================================
# DocumentEntry frozen
# =========================================================================


def _make_doc_entry(**overrides) -> DocumentEntry:
    defaults = {
        "doc_id": "d1",
        "path_str": "foo.txt",
        "resolved_path": Path("/tmp/foo.txt"),
        "source_type": "text",
        "sha256": None,
        "categories": (),
        "paired_with": None,
        "annotation_file_str": None,
        "annotation_resolved": None,
        "expectations": None,
    }
    defaults.update(overrides)
    return DocumentEntry(**defaults)


def test_document_entry_is_dataclass():
    assert is_dataclass(DocumentEntry) is True


def test_document_entry_frozen_setattr_raises():
    e = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        e.doc_id = "other"


def test_document_entry_field_count():
    f = fields(DocumentEntry)
    assert len(f) == 10


def test_document_entry_field_names_exact():
    f = fields(DocumentEntry)
    names = {field.name for field in f}
    expected = {
        "doc_id", "path_str", "resolved_path", "source_type",
        "sha256", "categories", "paired_with",
        "annotation_file_str", "annotation_resolved", "expectations",
    }
    assert names == expected


def test_document_entry_equality():
    a = _make_doc_entry()
    b = _make_doc_entry()
    assert a == b


def test_document_entry_inequality_on_doc_id():
    a = _make_doc_entry(doc_id="d1")
    b = _make_doc_entry(doc_id="d2")
    assert a != b


def test_document_entry_hashable():
    """frozen dataclass 默认 hashable。"""
    e = _make_doc_entry()
    assert hash(e) == hash(e)


def test_document_entry_default_values():
    e = _make_doc_entry()
    assert e.sha256 is None
    assert e.categories == ()
    assert e.paired_with is None
    assert e.annotation_file_str is None
    assert e.annotation_resolved is None
    assert e.expectations is None


# =========================================================================
# ExpectedFailure frozen
# =========================================================================


def _make_expected_failure(**overrides) -> ExpectedFailure:
    defaults = {
        "doc_id": "ef1",
        "path_str": "missing.txt",
        "resolved_path": Path("/tmp/missing.txt"),
        "expected_error_code": "file_not_found",
        "source_type": None,
    }
    defaults.update(overrides)
    return ExpectedFailure(**defaults)


def test_expected_failure_is_dataclass():
    assert is_dataclass(ExpectedFailure) is True


def test_expected_failure_frozen_setattr_raises():
    e = _make_expected_failure()
    with pytest.raises(FrozenInstanceError):
        e.doc_id = "other"


def test_expected_failure_field_count():
    f = fields(ExpectedFailure)
    assert len(f) == 5


def test_expected_failure_field_names_exact():
    f = fields(ExpectedFailure)
    names = {field.name for field in f}
    expected = {
        "doc_id", "path_str", "resolved_path",
        "expected_error_code", "source_type",
    }
    assert names == expected


def test_expected_failure_default_source_type_none():
    e = _make_expected_failure()
    assert e.source_type is None


def test_expected_failure_equality():
    a = _make_expected_failure()
    b = _make_expected_failure()
    assert a == b


def test_expected_failure_hashable():
    e = _make_expected_failure()
    assert hash(e) == hash(e)


# =========================================================================
# Manifest frozen + properties
# =========================================================================


def _make_manifest(
    documents: tuple = (),
    expected_failures: tuple = (),
    project_root: Path | None = None,
) -> Manifest:
    if project_root is None:
        project_root = Path("/tmp")
    return Manifest(
        manifest_version=MANIFEST_VERSION,
        devset_status="incomplete",
        documents=documents,
        expected_failures=expected_failures,
        project_root=project_root,
    )


def test_manifest_is_dataclass():
    assert is_dataclass(Manifest) is True


def test_manifest_frozen_setattr_raises():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"


def test_manifest_field_count():
    f = fields(Manifest)
    assert len(f) == 5


def test_manifest_field_names_exact():
    f = fields(Manifest)
    names = {field.name for field in f}
    expected = {
        "manifest_version", "devset_status", "documents",
        "expected_failures", "project_root",
    }
    assert names == expected


def test_manifest_file_count_empty():
    m = _make_manifest(documents=())
    assert m.file_count == 0


def test_manifest_file_count_three():
    docs = (
        _make_doc_entry(doc_id=f"d{i}") for i in range(3)
    )
    m = _make_manifest(documents=tuple(docs))
    assert m.file_count == 3


def test_manifest_pdf_count():
    docs = (
        _make_doc_entry(doc_id="d1", source_type="pdf"),
        _make_doc_entry(doc_id="d2", source_type="pdf"),
        _make_doc_entry(doc_id="d3", source_type="docx"),
    )
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 2


def test_manifest_docx_count():
    docs = (
        _make_doc_entry(doc_id="d1", source_type="pdf"),
        _make_doc_entry(doc_id="d2", source_type="docx"),
        _make_doc_entry(doc_id="d3", source_type="docx"),
        _make_doc_entry(doc_id="d4", source_type="docx"),
    )
    m = _make_manifest(documents=docs)
    assert m.docx_count == 3


def test_manifest_pdf_docx_other_count():
    """other source_type 不计入 pdf/docx。"""
    docs = (
        _make_doc_entry(doc_id="d1", source_type="text"),
        _make_doc_entry(doc_id="d2", source_type="markdown"),
    )
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 0
    assert m.docx_count == 0


def test_manifest_content_group_count_empty():
    m = _make_manifest(documents=())
    assert m.content_group_count == 0


def test_manifest_content_group_count_all_unpaired():
    docs = (
        _make_doc_entry(doc_id="d1"),
        _make_doc_entry(doc_id="d2"),
        _make_doc_entry(doc_id="d3"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 3


def test_manifest_content_group_count_one_pair_bidirectional():
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
    )
    m = _make_manifest(documents=docs)
    # frozenset({d1, d2}) 去重为 1 组
    assert m.content_group_count == 1


def test_manifest_content_group_count_one_pair_unidirectional():
    """单方向 paired_with → 仍算 1 组（避免重复计数）。"""
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2"),  # d2 不指向 d1
    )
    m = _make_manifest(documents=docs)
    # frozenset({d1, d2}) → 1 组
    assert m.content_group_count == 1


def test_manifest_content_group_count_self_pair():
    """d.paired_with == d.doc_id → frozenset({d, d}) == frozenset({d}) → 1 组。"""
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d1"),
    )
    m = _make_manifest(documents=docs)
    # frozenset({d1, d1}) → {d1} → 1 组；d1 在 seen 中 → 不算 unpaired
    assert m.content_group_count == 1


def test_manifest_content_group_count_mixed_paired_unpaired():
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
        _make_doc_entry(doc_id="d3"),
        _make_doc_entry(doc_id="d4"),
    )
    m = _make_manifest(documents=docs)
    # 1 组 (d1-d2) + 2 unpaired = 3
    assert m.content_group_count == 3


def test_manifest_content_group_count_two_disjoint_pairs():
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
        _make_doc_entry(doc_id="d3", paired_with="d4"),
        _make_doc_entry(doc_id="d4", paired_with="d3"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 2


def test_manifest_content_group_count_three_chain():
    """d1→d2, d2→d3, d3→d1 → 三个 frozenset 都不同 → 3 组（但 d1/d2/d3 都 seen）。"""
    docs = (
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d3"),
        _make_doc_entry(doc_id="d3", paired_with="d1"),
    )
    m = _make_manifest(documents=docs)
    # 三个不同的 frozenset: {d1,d2}, {d2,d3}, {d1,d3} → 3 组
    assert m.content_group_count == 3


def test_manifest_categories_covered_empty():
    m = _make_manifest(documents=())
    assert m.categories_covered == []


def test_manifest_categories_covered_single_doc():
    docs = (_make_doc_entry(categories=("a", "b")),)
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "b"]


def test_manifest_categories_covered_multiple_dedup():
    docs = (
        _make_doc_entry(doc_id="d1", categories=("a", "b")),
        _make_doc_entry(doc_id="d2", categories=("b", "c")),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_categories_covered_sorted():
    docs = (
        _make_doc_entry(doc_id="d1", categories=("z", "a", "m")),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_unicode():
    docs = (
        _make_doc_entry(doc_id="d1", categories=("中文", "英文")),
    )
    m = _make_manifest(documents=docs)
    assert "中文" in m.categories_covered
    assert "英文" in m.categories_covered


def test_manifest_categories_covered_no_categories_field():
    """documents 都无 categories → [].。"""
    docs = (
        _make_doc_entry(doc_id="d1", categories=()),
        _make_doc_entry(doc_id="d2", categories=()),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == []


# =========================================================================
# load_manifest 完整路径
# =========================================================================


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _minimal_manifest_data() -> dict:
    return {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }


def test_load_manifest_file_not_exists(tmp_path: Path):
    missing = tmp_path / "missing.json"
    with pytest.raises(ManifestError) as excinfo:
        load_manifest(missing)
    assert "清单文件不存在" in str(excinfo.value)


def test_load_manifest_invalid_json(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(ManifestError) as excinfo:
        load_manifest(p)
    assert "JSON 解析失败" in str(excinfo.value)


def test_load_manifest_manifest_version_mismatch(tmp_path: Path, monkeypatch):
    """manifest_version 不匹配（schema const 是 "1.0"，monkeypatch 跳过 schema 才能测后续 check）。"""
    data = _minimal_manifest_data()
    data["manifest_version"] = "0.0.0"
    p = _write_manifest(tmp_path, data)
    # schema 会先拒绝（const="1.0"），monkeypatch 让 validate 通过
    import evaluation.manifest as manifest_mod
    monkeypatch.setattr(manifest_mod, "validate", lambda *a, **kw: None)
    with pytest.raises(ManifestError) as excinfo:
        load_manifest(p, project_root=tmp_path)
    assert "manifest_version 不兼容" in str(excinfo.value)


def test_load_manifest_empty_documents(tmp_path: Path):
    data = _minimal_manifest_data()
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents == ()
    assert m.file_count == 0


def test_load_manifest_empty_expected_failures(tmp_path: Path):
    data = _minimal_manifest_data()
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures == ()


def test_load_manifest_one_document(tmp_path: Path):
    (tmp_path / "doc.pdf").write_text("hello", encoding="utf-8")
    data = _minimal_manifest_data()
    data["documents"] = [{
        "doc_id": "d1",
        "path": "doc.pdf",
        "source_type": "pdf",
    }]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.file_count == 1
    assert m.documents[0].doc_id == "d1"


def test_load_manifest_document_with_categories(tmp_path: Path):
    (tmp_path / "doc.pdf").write_text("hello", encoding="utf-8")
    data = _minimal_manifest_data()
    data["documents"] = [{
        "doc_id": "d1",
        "path": "doc.pdf",
        "source_type": "pdf",
        "categories": ["a", "b"],
    }]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ("a", "b")
    assert m.categories_covered == ["a", "b"]


def test_load_manifest_document_with_paired_with(tmp_path: Path):
    (tmp_path / "a.pdf").write_text("a", encoding="utf-8")
    (tmp_path / "b.docx").write_text("b", encoding="utf-8")
    data = _minimal_manifest_data()
    data["documents"] = [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
        {"doc_id": "d2", "path": "b.docx", "source_type": "docx", "paired_with": "d1"},
    ]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].paired_with == "d2"
    assert m.content_group_count == 1


def test_load_manifest_document_with_sha256(tmp_path: Path):
    (tmp_path / "doc.pdf").write_text("hello", encoding="utf-8")
    data = _minimal_manifest_data()
    data["documents"] = [{
        "doc_id": "d1",
        "path": "doc.pdf",
        "source_type": "pdf",
        "sha256": "a" * 64,
    }]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 == "a" * 64


def test_load_manifest_document_with_annotation_file(tmp_path: Path):
    (tmp_path / "doc.pdf").write_text("hello", encoding="utf-8")
    (tmp_path / "ann.json").write_text("{}", encoding="utf-8")
    data = _minimal_manifest_data()
    data["documents"] = [{
        "doc_id": "d1",
        "path": "doc.pdf",
        "source_type": "pdf",
        "annotation_file": "ann.json",
    }]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_file_str == "ann.json"
    assert m.documents[0].annotation_resolved == (tmp_path / "ann.json").resolve()


def test_load_manifest_document_with_expectations(tmp_path: Path):
    (tmp_path / "doc.pdf").write_text("hello", encoding="utf-8")
    data = _minimal_manifest_data()
    data["documents"] = [{
        "doc_id": "d1",
        "path": "doc.pdf",
        "source_type": "pdf",
        "expectations": {"element_count_by_type": {"paragraph": 5}},
    }]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_expected_failure_with_source_type(tmp_path: Path):
    (tmp_path / "missing.pdf").write_text("x", encoding="utf-8")
    data = _minimal_manifest_data()
    data["expected_failures"] = [{
        "doc_id": "ef1",
        "path": "missing.pdf",
        "expected_error_code": "file_not_found",
        "source_type": "pdf",
    }]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].source_type == "pdf"


def test_load_manifest_expected_failure_no_source_type(tmp_path: Path):
    (tmp_path / "missing.txt").write_text("x", encoding="utf-8")
    data = _minimal_manifest_data()
    data["expected_failures"] = [{
        "doc_id": "ef1",
        "path": "missing.txt",
        "expected_error_code": "file_not_found",
    }]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].source_type is None


def test_load_manifest_path_outside_root_raises(tmp_path: Path):
    data = _minimal_manifest_data()
    data["documents"] = [{
        "doc_id": "d1",
        "path": "../outside.pdf",
        "source_type": "pdf",
    }]
    p = _write_manifest(tmp_path, data)
    with pytest.raises(ManifestError) as excinfo:
        load_manifest(p, project_root=tmp_path)
    assert "项目根目录之外" in str(excinfo.value)


def test_load_manifest_path_absolute_raises(tmp_path: Path):
    data = _minimal_manifest_data()
    data["documents"] = [{
        "doc_id": "d1",
        "path": "/etc/passwd",
        "source_type": "pdf",
    }]
    p = _write_manifest(tmp_path, data)
    with pytest.raises(ManifestError) as excinfo:
        load_manifest(p, project_root=tmp_path)
    assert "绝对路径" in str(excinfo.value)


def test_load_manifest_path_backslash_raises(tmp_path: Path):
    data = _minimal_manifest_data()
    data["documents"] = [{
        "doc_id": "d1",
        "path": "a\\b.pdf",
        "source_type": "pdf",
    }]
    p = _write_manifest(tmp_path, data)
    with pytest.raises(ManifestError) as excinfo:
        load_manifest(p, project_root=tmp_path)
    assert "反斜杠" in str(excinfo.value)


def test_load_manifest_project_root_explicit_string(tmp_path: Path):
    (tmp_path / "doc.pdf").write_text("hello", encoding="utf-8")
    data = _minimal_manifest_data()
    data["documents"] = [{
        "doc_id": "d1",
        "path": "doc.pdf",
        "source_type": "pdf",
    }]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_manifest_path_as_string(tmp_path: Path):
    (tmp_path / "doc.pdf").write_text("hello", encoding="utf-8")
    data = _minimal_manifest_data()
    p = _write_manifest(tmp_path, data)
    m = load_manifest(str(p), project_root=tmp_path)
    assert m is not None


# =========================================================================
# _detect_project_root
# =========================================================================


def test_detect_project_root_from_file_in_root(tmp_path: Path):
    """文件在 project_root 内，project_root 含 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("[tool]", encoding="utf-8")
    p = tmp_path / "manifest.json"
    result = _detect_project_root(p)
    assert result == tmp_path.resolve()


def test_detect_project_root_from_nested_file(tmp_path: Path):
    """文件在 project_root/sub1/sub2 内。"""
    (tmp_path / "pyproject.toml").write_text("[tool]", encoding="utf-8")
    sub = tmp_path / "sub1" / "sub2"
    sub.mkdir(parents=True)
    p = sub / "manifest.json"
    result = _detect_project_root(p)
    assert result == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_start(tmp_path: Path):
    """找不到 pyproject.toml → 返回 start 的目录。"""
    p = tmp_path / "manifest.json"
    p.write_text("{}", encoding="utf-8")  # 文件必须存在才能 is_file()
    result = _detect_project_root(p)
    # 没找到 → 返回 start.resolve()（文件 → 取 parent）
    assert result == tmp_path.resolve()


def test_detect_project_root_directory_input(tmp_path: Path):
    """start 是目录。"""
    (tmp_path / "pyproject.toml").write_text("[tool]", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert result == tmp_path.resolve()


def test_detect_project_root_picks_first_pyproject_in_chain(tmp_path: Path):
    """多 pyproject.toml → 取最深（最近的祖先）。"""
    (tmp_path / "pyproject.toml").write_text("[tool]", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "pyproject.toml").write_text("[tool]", encoding="utf-8")
    p = sub / "manifest.json"
    result = _detect_project_root(p)
    # sub 是最近的祖先含 pyproject.toml
    assert result == sub.resolve()


# =========================================================================
# 模块结构与签名
# =========================================================================


def test_module_all_exports():
    import evaluation.manifest as m
    assert m.__all__ == [
        "ManifestError", "Manifest", "DocumentEntry",
        "ExpectedFailure", "load_manifest",
    ]


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


def test_manifest_error_is_exception():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_can_be_raised():
    with pytest.raises(ManifestError):
        raise ManifestError("test")


def test_manifest_error_with_message():
    try:
        raise ManifestError("custom message")
    except ManifestError as e:
        assert "custom message" in str(e)


def test_is_absolute_like_signature():
    sig = inspect.signature(_is_absolute_like)
    assert set(sig.parameters) == {"path_str"}


def test_has_backslash_signature():
    sig = inspect.signature(_has_backslash)
    assert set(sig.parameters) == {"path_str"}


def test_resolve_relative_path_signature():
    sig = inspect.signature(_resolve_relative_path)
    assert set(sig.parameters) == {"path_str", "project_root", "field_name"}


def test_load_manifest_signature():
    sig = inspect.signature(load_manifest)
    assert set(sig.parameters) == {"manifest_path", "project_root"}
    assert sig.parameters["manifest_path"].default is inspect.Parameter.empty
    assert sig.parameters["project_root"].default is None


def test_load_manifest_manifest_path_annotation_path_or_str():
    sig = inspect.signature(load_manifest)
    annotation = str(sig.parameters["manifest_path"].annotation)
    assert "Path" in annotation
    assert "str" in annotation


def test_load_manifest_project_root_annotation_optional():
    sig = inspect.signature(load_manifest)
    annotation = str(sig.parameters["project_root"].annotation)
    assert "Path" in annotation or "str" in annotation or "None" in annotation


def test_detect_project_root_signature():
    sig = inspect.signature(_detect_project_root)
    assert set(sig.parameters) == {"start"}


def test_load_manifest_return_annotation_manifest():
    sig = inspect.signature(load_manifest)
    assert "Manifest" in str(sig.return_annotation)


def test_is_absolute_like_callable():
    assert callable(_is_absolute_like)


def test_has_backslash_callable():
    assert callable(_has_backslash)


def test_resolve_relative_path_callable():
    assert callable(_resolve_relative_path)


def test_load_manifest_callable():
    assert callable(load_manifest)


def test_detect_project_root_callable():
    assert callable(_detect_project_root)


# =========================================================================
# idempotency
# =========================================================================


def test_is_absolute_like_idempotent():
    assert _is_absolute_like("/foo") == _is_absolute_like("/foo")


def test_has_backslash_idempotent():
    assert _has_backslash("a\\b") == _has_backslash("a\\b")


def test_resolve_relative_path_idempotent(tmp_path: Path):
    a = _resolve_relative_path("foo.txt", tmp_path, "f")
    b = _resolve_relative_path("foo.txt", tmp_path, "f")
    assert a == b


def test_load_manifest_idempotent(tmp_path: Path):
    (tmp_path / "doc.pdf").write_text("hello", encoding="utf-8")
    data = _minimal_manifest_data()
    data["documents"] = [{
        "doc_id": "d1",
        "path": "doc.pdf",
        "source_type": "pdf",
    }]
    p = _write_manifest(tmp_path, data)
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1 == m2


def test_document_entry_idempotent_construction():
    a = _make_doc_entry()
    b = _make_doc_entry()
    assert a == b


# =========================================================================
# 综合行为
# =========================================================================


def test_load_manifest_full_pipeline(tmp_path: Path):
    """完整 manifest：3 docs + 1 EF + categories + paired_with。"""
    (tmp_path / "a.pdf").write_text("a", encoding="utf-8")
    (tmp_path / "b.docx").write_text("b", encoding="utf-8")
    (tmp_path / "c.pdf").write_text("c", encoding="utf-8")
    (tmp_path / "missing.pdf")  # 不创建 → 期待失败
    data = _minimal_manifest_data()
    data["documents"] = [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
         "categories": ["intro"], "paired_with": "d2"},
        {"doc_id": "d2", "path": "b.docx", "source_type": "docx",
         "categories": ["intro"], "paired_with": "d1"},
        {"doc_id": "d3", "path": "c.pdf", "source_type": "pdf",
         "categories": ["advanced"]},
    ]
    data["expected_failures"] = [{
        "doc_id": "ef1", "path": "missing.pdf",
        "expected_error_code": "file_not_found",
    }]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.file_count == 3
    assert m.pdf_count == 2
    assert m.docx_count == 1
    assert m.content_group_count == 2  # d1-d2 pair + d3
    assert m.categories_covered == ["advanced", "intro"]
    assert len(m.expected_failures) == 1


def test_manifest_properties_after_load(tmp_path: Path):
    """所有 properties 在 load_manifest 后正确计算。"""
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "b.docx").write_text("x", encoding="utf-8")
    data = _minimal_manifest_data()
    data["documents"] = [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        {"doc_id": "d2", "path": "b.docx", "source_type": "docx"},
    ]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.content_group_count == 2
    assert m.categories_covered == []
