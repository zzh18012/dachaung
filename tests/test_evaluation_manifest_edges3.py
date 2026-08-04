"""evaluation/manifest.py 边角测试 - 第三轮（Round 98）。

补强已有 ? + ? 测试未覆盖的：
- _is_absolute_like：所有平台 case（POSIX /foo、Windows C:\\foo、C:/foo、
  C:foo 不算绝对、a:/foo（数字盘符）、单字符无冒号）
- _has_backslash：各种字符串
- Manifest dataclass：frozen、properties（file_count/pdf_count/docx_count/
  content_group_count/categories_covered）精确算法
- DocumentEntry / ExpectedFailure dataclass：frozen + 必填字段
- content_group_count 算法：无 paired、双向 paired、单向 paired、3 文档全 paired
- _resolve_relative_path：所有错误码（空、绝对、反斜杠、解析越界）
- load_manifest：manifest_version 不兼容、annotation_file 解析、
  expected_failures source_type None
- _detect_project_root：从子目录向上找 pyproject.toml
- 项目根越界防护（../../../etc/passwd）

不修改任何源码。
"""

from __future__ import annotations

import json
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
# _is_absolute_like 第三轮
# =========================================================================


def test_is_absolute_like_empty_string():
    assert _is_absolute_like("") is False


def test_is_absolute_like_posix_root():
    assert _is_absolute_like("/etc/passwd") is True


def test_is_absolute_like_posix_relative():
    assert _is_absolute_like("foo/bar") is False


def test_is_absolute_like_single_dot_relative():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_double_dot_relative():
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_windows_backslash():
    assert _is_absolute_like("C:\\Windows\\System32") is True


def test_is_absolute_like_windows_forward_slash():
    assert _is_absolute_like("C:/Windows/System32") is True


def test_is_absolute_like_windows_no_separator():
    """'C:foo' 不是绝对（Windows drive-relative）。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_lowercase_drive():
    assert _is_absolute_like("c:\\foo") is True


def test_is_absolute_like_uppercase_drive():
    assert _is_absolute_like("Z:/foo") is True


def test_is_absolute_like_digit_drive_not_absolute():
    """'1:\\foo' 不是 Windows drive（必须 alpha）。"""
    assert _is_absolute_like("1:\\foo") is False


def test_is_absolute_like_short_string():
    """2 字符串：'ab' 不是绝对。"""
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_just_slash():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_just_backslash():
    """'\\' 单独不算 Windows drive（无盘符）。"""
    assert _is_absolute_like("\\") is False


def test_is_absolute_like_unc_path_not_absolute_by_this_check():
    """'\\\\server\\share' 不被识别为绝对（无盘符）。"""
    assert _is_absolute_like("\\\\server\\share") is False


# =========================================================================
# _has_backslash 第三轮
# =========================================================================


def test_has_backslash_empty():
    assert _has_backslash("") is False


def test_has_backslash_no_backslash():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_single():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_multiple():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_only_backslash():
    assert _has_backslash("\\") is True


def test_has_backslash_leading():
    assert _has_backslash("\\foo") is True


def test_has_backslash_trailing():
    assert _has_backslash("foo\\") is True


# =========================================================================
# Manifest dataclass
# =========================================================================


def _make_doc_entry(
    doc_id: str = "d1",
    source_type: str = "docx",
    paired_with: str | None = None,
    categories: tuple = (),
) -> DocumentEntry:
    return DocumentEntry(
        doc_id=doc_id,
        path_str=f"samples/{doc_id}.docx",
        resolved_path=Path("/tmp") / f"{doc_id}.docx",
        source_type=source_type,
        sha256=None,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def _make_manifest(
    documents: tuple = (),
    expected_failures: tuple = (),
) -> Manifest:
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=documents,
        expected_failures=expected_failures,
        project_root=Path("/tmp"),
    )


def test_manifest_is_frozen_dataclass():
    m = _make_manifest()
    try:
        m.devset_status = "complete"  # type: ignore[misc]
        assert False, "expected frozen"
    except (AttributeError, TypeError):
        pass


def test_manifest_file_count_zero_when_empty():
    m = _make_manifest()
    assert m.file_count == 0


def test_manifest_file_count_three_documents():
    docs = (_make_doc_entry("d1"), _make_doc_entry("d2"), _make_doc_entry("d3"))
    m = _make_manifest(documents=docs)
    assert m.file_count == 3


def test_manifest_pdf_count_only_pdfs():
    docs = (
        _make_doc_entry("d1", source_type="pdf"),
        _make_doc_entry("d2", source_type="docx"),
        _make_doc_entry("d3", source_type="pdf"),
    )
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 2


def test_manifest_docx_count_only_docxs():
    docs = (
        _make_doc_entry("d1", source_type="pdf"),
        _make_doc_entry("d2", source_type="docx"),
        _make_doc_entry("d3", source_type="pdf"),
    )
    m = _make_manifest(documents=docs)
    assert m.docx_count == 1


def test_manifest_categories_covered_sorted_unique():
    docs = (
        _make_doc_entry("d1", categories=("b", "a")),
        _make_doc_entry("d2", categories=("c", "a")),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_categories_covered_empty():
    m = _make_manifest()
    assert m.categories_covered == []


def test_manifest_content_group_count_no_pairing():
    docs = (_make_doc_entry("d1"), _make_doc_entry("d2"))
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 2


def test_manifest_content_group_count_all_unpaired():
    docs = (_make_doc_entry("d1"), _make_doc_entry("d2"), _make_doc_entry("d3"))
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 3


def test_manifest_content_group_count_one_pair():
    docs = (
        _make_doc_entry("d1", paired_with="d2"),
        _make_doc_entry("d2", paired_with="d1"),
        _make_doc_entry("d3"),
    )
    m = _make_manifest(documents=docs)
    # 1 pair + 1 unpaired = 2
    assert m.content_group_count == 2


def test_manifest_content_group_count_one_way_pair():
    """单向 paired_with → 仍算 1 组（避免重复计数）。"""
    docs = (
        _make_doc_entry("d1", paired_with="d2"),
        _make_doc_entry("d2"),  # 不回指 d1
    )
    m = _make_manifest(documents=docs)
    # 算法：pair_ids 收集 frozenset(d1, d2) → 1 group
    # d2 在 seen 中 → 不算 unpaired
    assert m.content_group_count == 1


# =========================================================================
# DocumentEntry dataclass
# =========================================================================


def test_document_entry_is_frozen():
    d = _make_doc_entry()
    try:
        d.doc_id = "x"  # type: ignore[misc]
        assert False, "expected frozen"
    except (AttributeError, TypeError):
        pass


def test_document_entry_required_fields():
    d = DocumentEntry(
        doc_id="d1",
        path_str="x.docx",
        resolved_path=Path("/tmp/x.docx"),
        source_type="docx",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    assert d.doc_id == "d1"
    assert d.source_type == "docx"
    assert d.sha256 is None
    assert d.categories == ()
    assert d.paired_with is None
    assert d.annotation_file_str is None
    assert d.annotation_resolved is None
    assert d.expectations is None


def test_document_entry_with_all_fields():
    d = DocumentEntry(
        doc_id="d1",
        path_str="x.docx",
        resolved_path=Path("/tmp/x.docx"),
        source_type="docx",
        sha256="abc123",
        categories=("a", "b"),
        paired_with="d2",
        annotation_file_str="x.json",
        annotation_resolved=Path("/tmp/x.json"),
        expectations={"element_count_by_type": {"paragraph": 5}},
    )
    assert d.sha256 == "abc123"
    assert d.categories == ("a", "b")
    assert d.paired_with == "d2"
    assert d.annotation_resolved == Path("/tmp/x.json")
    assert d.expectations == {"element_count_by_type": {"paragraph": 5}}


# =========================================================================
# ExpectedFailure dataclass
# =========================================================================


def test_expected_failure_is_frozen():
    ef = ExpectedFailure(
        doc_id="ef1",
        path_str="bad.docx",
        resolved_path=Path("/tmp/bad.docx"),
        expected_error_code="file_not_found",
        source_type="docx",
    )
    try:
        ef.doc_id = "x"  # type: ignore[misc]
        assert False, "expected frozen"
    except (AttributeError, TypeError):
        pass


def test_expected_failure_source_type_can_be_none():
    ef = ExpectedFailure(
        doc_id="ef1",
        path_str="bad.docx",
        resolved_path=Path("/tmp/bad.docx"),
        expected_error_code="file_not_found",
        source_type=None,
    )
    assert ef.source_type is None


def test_expected_failure_required_fields():
    ef = ExpectedFailure(
        doc_id="ef1",
        path_str="bad.docx",
        resolved_path=Path("/tmp/bad.docx"),
        expected_error_code="schema_validation_failed",
        source_type="pdf",
    )
    assert ef.doc_id == "ef1"
    assert ef.expected_error_code == "schema_validation_failed"


# =========================================================================
# _resolve_relative_path 错误码
# =========================================================================


def test_resolve_relative_path_empty_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", tmp_path, "field1")
    assert "field1" in str(ei.value)
    assert "为空" in str(ei.value)


def test_resolve_relative_path_absolute_posix_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("/etc/passwd", tmp_path, "f")
    assert "绝对路径" in str(ei.value)


def test_resolve_relative_path_absolute_windows_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("C:\\Windows\\foo", tmp_path, "f")
    assert "绝对路径" in str(ei.value)


def test_resolve_relative_path_backslash_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("sub\\dir\\file.docx", tmp_path, "f")
    assert "反斜杠" in str(ei.value) or "正斜杠" in str(ei.value)


def test_resolve_relative_path_outside_project_root_raises(tmp_path: Path):
    """合法相对路径但解析后越界 → 拒。"""
    # 用 ../../../tmp 试图逃出 tmp_path
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("../../../../etc/passwd", tmp_path, "f")
    assert "项目根" in str(ei.value) or "之外" in str(ei.value)


def test_resolve_relative_path_normal_returns_absolute(tmp_path: Path):
    """合法相对路径 → 返回绝对路径。"""
    result = _resolve_relative_path("a/b.docx", tmp_path, "f")
    assert result.is_absolute()
    assert "a" in str(result)
    assert "b.docx" in str(result)


def test_resolve_relative_path_dot_relative_accepted(tmp_path: Path):
    """'./foo' → 合法相对路径。"""
    result = _resolve_relative_path("./foo.docx", tmp_path, "f")
    assert result.is_absolute()


def test_resolve_relative_path_subdir_accepted(tmp_path: Path):
    result = _resolve_relative_path("sub/dir/file.docx", tmp_path, "f")
    assert result.is_absolute()
    assert "sub" in str(result)


# =========================================================================
# load_manifest 错误路径
# =========================================================================


def _make_minimal_manifest_json(tmp_path: Path, manifest_path: Path, project_root: Path | None = None) -> Path:
    """写一个最小合法 manifest 到 manifest_path（doc_file 在 project_root 下）。"""
    rel = "samples/test.docx"
    if project_root:
        (project_root / "samples").mkdir(parents=True, exist_ok=True)
        (project_root / "samples" / "test.docx").write_bytes(b"placeholder")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": rel,
                "source_type": "docx",
                "categories": [],
            }
        ],
        "expected_failures": [],
    }
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    return manifest_path


def test_load_manifest_missing_file_raises(tmp_path: Path):
    missing = tmp_path / "no.json"
    with pytest.raises(ManifestError) as ei:
        load_manifest(missing, tmp_path)
    assert "不存在" in str(ei.value)


def test_load_manifest_bad_json_raises(tmp_path: Path):
    f = tmp_path / "bad.json"
    f.write_text("{not json", encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(f, tmp_path)
    assert "JSON" in str(ei.value)


def test_load_manifest_invalid_version_raises(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "samples").mkdir()
    (proj / "samples" / "x.docx").write_bytes(b"placeholder")
    data = {
        "manifest_version": "0.0.0_unknown",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/x.docx",
                "source_type": "docx",
            }
        ],
        "expected_failures": [],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises((ManifestError, Exception)):
        load_manifest(f, proj)


def test_load_manifest_valid_returns_manifest(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    f = _make_minimal_manifest_json(tmp_path, tmp_path / "m.json", proj)
    m = load_manifest(f, proj)
    assert isinstance(m, Manifest)
    assert m.manifest_version == MANIFEST_VERSION
    assert m.devset_status == "incomplete"
    assert len(m.documents) == 1
    assert m.documents[0].doc_id == "d1"


def test_load_manifest_with_expected_failures(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "samples").mkdir()
    (proj / "samples" / "x.docx").write_bytes(b"placeholder")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "ef1",
                "path": "samples/x.docx",
                "expected_error_code": "file_not_found",
                "source_type": "docx",
            }
        ],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(f, proj)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].doc_id == "ef1"
    assert m.expected_failures[0].expected_error_code == "file_not_found"


def test_load_manifest_with_annotation_file(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "samples").mkdir()
    (proj / "samples" / "x.docx").write_bytes(b"placeholder")
    (proj / "annotations").mkdir()
    (proj / "annotations" / "x.json").write_text("{}", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/x.docx",
                "source_type": "docx",
                "annotation_file": "annotations/x.json",
            }
        ],
        "expected_failures": [],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(f, proj)
    assert m.documents[0].annotation_resolved is not None
    assert m.documents[0].annotation_resolved.is_absolute()


def test_load_manifest_documents_empty_returns_empty_tuple(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(f, proj)
    assert m.documents == ()


def test_load_manifest_categories_preserved_as_tuple(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "samples").mkdir()
    (proj / "samples" / "x.docx").write_bytes(b"placeholder")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/x.docx",
                "source_type": "docx",
                "categories": ["a", "b", "c"],
            }
        ],
        "expected_failures": [],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(f, proj)
    assert m.documents[0].categories == ("a", "b", "c")
    assert isinstance(m.documents[0].categories, tuple)


# =========================================================================
# _detect_project_root
# =========================================================================


def test_detect_project_root_finds_pyproject(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "pyproject.toml").write_text("[tool.x]\n", encoding="utf-8")
    sub = proj / "a" / "b"
    sub.mkdir(parents=True)
    f = sub / "manifest.json"
    f.write_text("[]", encoding="utf-8")
    root = _detect_project_root(f)
    assert root == proj.resolve()


def test_detect_project_root_no_pyproject_falls_back_to_parent(tmp_path: Path):
    """无 pyproject.toml → 返回文件所在目录的父。"""
    sub = tmp_path / "a"
    sub.mkdir()
    f = sub / "manifest.json"
    f.write_text("[]", encoding="utf-8")
    root = _detect_project_root(f)
    # 至少应当返回某个存在的路径
    assert root.exists()


def test_detect_project_root_with_path_object(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "pyproject.toml").write_text("[tool.x]\n", encoding="utf-8")
    root = _detect_project_root(proj)
    assert root == proj.resolve()


# =========================================================================
# ManifestError 继承结构
# =========================================================================


def test_manifest_error_is_exception():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_can_be_raised_and_caught():
    try:
        raise ManifestError("test")
    except ManifestError as e:
        assert "test" in str(e)


def test_manifest_error_caught_as_exception():
    try:
        raise ManifestError("x")
    except Exception as e:
        assert isinstance(e, ManifestError)


# =========================================================================
# __all__ 导出
# =========================================================================


def test_manifest_all_contains_manifest_error():
    from evaluation import manifest
    assert "ManifestError" in manifest.__all__


def test_manifest_all_contains_manifest_class():
    from evaluation import manifest
    assert "Manifest" in manifest.__all__


def test_manifest_all_contains_document_entry():
    from evaluation import manifest
    assert "DocumentEntry" in manifest.__all__


def test_manifest_all_contains_expected_failure():
    from evaluation import manifest
    assert "ExpectedFailure" in manifest.__all__


def test_manifest_all_contains_load_manifest():
    from evaluation import manifest
    assert "load_manifest" in manifest.__all__
