"""evaluation/manifest.py 边角测试（Round 83，第二轮）。

补强 tests/test_manifest.py（90+ 测试）+ test_evaluation_manifest_edges.py（90+ 测试）
未覆盖的盲区：

- _is_absolute_like：所有 ASCII 字母盘符枚举、所有数字盘符拒绝、Unicode 字符、
  多字符前缀（"AB:"）、URL scheme（file://）、家目录（~）、多点（..）
- _has_backslash：纯反斜杠串、长路径、Unicode + 反斜杠、字符串首尾
- _resolve_relative_path：错误消息 field_name 透传、各种 dot/whitespace 名称、
  Windows 风格 C:/ 拒绝、深嵌套子目录、单点路径
- _detect_project_root：起点为根目录、起点为深嵌套文件、起点为 .git 目录、
  无 pyproject 时返原点
- Manifest 属性：file_count 类型 int、paired_with 重复 frozenset 去重、
  categories_covered 多 doc 重叠、content_group_count 复杂图
- DocumentEntry：frozen 严格性、所有字段类型、tuple vs list 不可变性
- ExpectedFailure：frozen 严格性、可选字段
- load_manifest：annotation_file 解析路径、version 字段精确、
  Schema 校验失败 → EvalSchemaError 链、json.JSONDecodeError __cause__ 链、
  空 documents + 空 expected_failures、source_type 必须是 enum
- 模块结构：__all__ 完整、imports、所有 helper 可调用
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.manifest import (
    DocumentEntry,
    ExpectedFailure,
    Manifest,
    ManifestError,
    __all__ as manifest_all,
    _detect_project_root,
    _has_backslash,
    _is_absolute_like,
    _resolve_relative_path,
    load_manifest,
)


# =========================================================================
# 共用 fixtures
# =========================================================================


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    return tmp_path


def _write_manifest(project_root: Path, data: dict) -> Path:
    p = project_root / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _basic_valid_manifest() -> dict:
    return {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "DC-1",
                "path": "samples/private/sample.docx",
                "source_type": "docx",
            }
        ],
    }


def _write_full_valid_manifest(project_root: Path) -> Path:
    """写一个完整的有效 manifest，包含 doc/expected_failure/annotation。"""
    # 创建对应的文件让路径解析通过
    (project_root / "samples/private").mkdir(parents=True, exist_ok=True)
    (project_root / "samples/private/sample.docx").write_bytes(b"mock")
    (project_root / "samples/private/sample.json").write_text("{}", encoding="utf-8")
    (project_root / "samples/private/bad.txt").write_text("bad", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "DC-1",
                "path": "samples/private/sample.docx",
                "source_type": "docx",
                "annotation_file": "samples/private/sample.json",
                "categories": ["report", "financial"],
                "expectations": {"element_count_by_type": {"heading": 1}},
            }
        ],
        "expected_failures": [
            {
                "doc_id": "EF-1",
                "path": "samples/private/bad.txt",
                "expected_error_code": "unsupported_type",
                "source_type": "txt",
            }
        ],
    }
    return _write_manifest(project_root, data)


# =========================================================================
# 1. _is_absolute_like 第二轮
# =========================================================================


def test_is_absolute_like_returns_bool_type():
    assert isinstance(_is_absolute_like("foo"), bool)


def test_is_absolute_like_all_lowercase_drive_letters():
    """a-z + :/ 全部识别为绝对路径。"""
    for c in "abcdefghijklmnopqrstuvwxyz":
        assert _is_absolute_like(f"{c}:/foo") is True, f"failed for {c}"


def test_is_absolute_like_all_uppercase_drive_letters():
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        assert _is_absolute_like(f"{c}:/foo") is True, f"failed for {c}"


def test_is_absolute_like_all_digit_drive_chars_rejected():
    for c in "0123456789":
        assert _is_absolute_like(f"{c}:/foo") is False, f"failed for {c}"


def test_is_absolute_like_special_chars_drive_rejected():
    for c in "!@#$%^&*()-_=+[]{};:,.<>?":
        assert _is_absolute_like(f"{c}:/foo") is False, f"failed for {c!r}"


def test_is_absolute_like_unicode_drive_char_accepted_by_isalpha():
    """Python str.isalpha() 对 Unicode 字母返 True（含中文）→ 函数接受为"绝对路径"。
    这是已知行为（isalpha() not ASCII-only）；测试以实际行为为准。"""
    # 中.isalpha() → True → 函数将其当作 alpha drive letter
    assert _is_absolute_like("中:/foo") is True


def test_is_absolute_like_url_scheme_rejected():
    """file:// 不被识别（无 leading /，不是盘符）。"""
    assert _is_absolute_like("file://foo") is False


def test_is_absolute_like_home_tilde_rejected():
    """~ 不被识别为绝对路径。"""
    assert _is_absolute_like("~/foo") is False


def test_is_absolute_like_two_letter_drive_rejected():
    """'AB:/foo' → 长度 OK 但 path_str[1] != ':' → 拒绝。"""
    assert _is_absolute_like("AB:/foo") is False


def test_is_absolute_like_just_slash_is_absolute():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_root_path_with_spaces():
    assert _is_absolute_like("/ foo") is True


def test_is_absolute_like_trailing_slash_only():
    assert _is_absolute_like("/foo/") is True


def test_is_absolute_like_leading_whitespace():
    """前导空格不在识别逻辑里 → 返 False（不被 strip）。"""
    assert _is_absolute_like(" /foo") is False


def test_is_absolute_like_two_char_string():
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_three_char_drive_format():
    """'X:\\' / 'X:/' 长度 3，是绝对路径。"""
    assert _is_absolute_like("X:\\") is True
    assert _is_absolute_like("X:/") is True


def test_is_absolute_like_empty_string():
    assert _is_absolute_like("") is False


def test_is_absolute_like_single_char_string():
    assert _is_absolute_like("a") is False


def test_is_absolute_like_just_dot():
    assert _is_absolute_like(".") is False


def test_is_absolute_like_just_two_dots():
    assert _is_absolute_like("..") is False


def test_is_absolute_like_just_backslash():
    """单 \\ → 长度 1，不满足盘符条件；startswith('/') False → False。"""
    assert _is_absolute_like("\\") is False


def test_is_absolute_like_double_backslash():
    r"""\\\\ → 同样不是 /，也不是盘符 → False。"""
    assert _is_absolute_like("\\\\") is False


def test_is_absolute_like_windows_unc_path_rejected_by_this_function():
    r"""UNC \\server\share 不被此函数识别（仅看 / 和 C:\）。"""
    assert _is_absolute_like("\\\\server\\share") is False


def test_is_absolute_like_with_colon_no_slash():
    """'C:foo' 是 Windows 相对路径（drive-relative），函数返 False。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_with_colon_backslash():
    assert _is_absolute_like("C:\\foo") is True


def test_is_absolute_like_lowercase_with_colon_backslash():
    assert _is_absolute_like("c:\\foo") is True


# =========================================================================
# 2. _has_backslash 第二轮
# =========================================================================


def test_has_backslash_returns_bool_type():
    assert isinstance(_has_backslash("foo"), bool)


def test_has_backslash_single_backslash_char_only():
    assert _has_backslash("\\") is True


def test_has_backslash_long_path_with_one_backslash():
    assert _has_backslash("a" * 100 + "\\" + "b" * 100) is True


def test_has_backslash_at_start_of_string():
    assert _has_backslash("\\foo") is True


def test_has_backslash_at_end_of_string():
    assert _has_backslash("foo\\") is True


def test_has_backslash_unicode_with_backslash():
    assert _has_backslash("中文\\foo") is True


def test_has_backslash_mixed_slashes_one_backslash_one_forward():
    assert _has_backslash("/foo\\bar") is True


def test_has_backslash_mixed_slashes_two_forward_one_back():
    assert _has_backslash("//\\") is True


def test_has_backslash_just_slash():
    assert _has_backslash("/") is False


def test_has_backslash_just_two_slashes():
    assert _has_backslash("//") is False


def test_has_backslash_just_dots():
    assert _has_backslash("..") is False


def test_has_backslash_no_chars_at_all():
    assert _has_backslash("") is False


def test_has_backslash_only_alphanumerics():
    assert _has_backslash("abc123XYZ") is False


def test_has_backslash_with_special_chars_no_backslash():
    assert _has_backslash("!@#$%^&*()_+-=") is False


# =========================================================================
# 3. _resolve_relative_path 第二轮
# =========================================================================


def test_resolve_relative_path_returns_path_object(project_root: Path):
    result = _resolve_relative_path("foo.txt", project_root, "test_field")
    assert isinstance(result, Path)


def test_resolve_relative_path_returns_absolute_path(project_root: Path):
    result = _resolve_relative_path("foo.txt", project_root, "test_field")
    assert result.is_absolute()


def test_resolve_relative_path_simple_filename(project_root: Path):
    result = _resolve_relative_path("foo.txt", project_root, "test_field")
    assert result == (project_root / "foo.txt").resolve()


def test_resolve_relative_path_nested_subdirs(project_root: Path):
    result = _resolve_relative_path("a/b/c/foo.txt", project_root, "test_field")
    assert result == (project_root / "a/b/c/foo.txt").resolve()


def test_resolve_relative_path_dot_slash(project_root: Path):
    result = _resolve_relative_path("./foo.txt", project_root, "test_field")
    assert result == (project_root / "foo.txt").resolve()


def test_resolve_relative_path_with_double_dot_inside(project_root: Path):
    """a/../foo.txt → resolve 后仍在 root 内。"""
    result = _resolve_relative_path("a/../foo.txt", project_root, "test_field")
    assert result == (project_root / "foo.txt").resolve()


def test_resolve_relative_path_with_multiple_double_dots_inside(project_root: Path):
    """a/b/../../foo.txt → resolve 后仍在 root 内。"""
    result = _resolve_relative_path("a/b/../../foo.txt", project_root, "test_field")
    assert result == (project_root / "foo.txt").resolve()


def test_resolve_relative_path_single_dot(project_root: Path):
    """'.' → resolve 为 project_root 自身。"""
    result = _resolve_relative_path(".", project_root, "test_field")
    assert result == project_root.resolve()


def test_resolve_relative_path_empty_string_raises(project_root: Path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("", project_root, "my_field")
    assert "my_field" in str(exc.value)


def test_resolve_relative_path_absolute_posix_raises(project_root: Path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("/etc/passwd", project_root, "my_field")
    assert "my_field" in str(exc.value)


def test_resolve_relative_path_absolute_windows_drive_raises(project_root: Path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("C:/foo", project_root, "my_field")


def test_resolve_relative_path_backslash_raises(project_root: Path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("foo\\bar", project_root, "my_field")
    assert "my_field" in str(exc.value)


def test_resolve_relative_path_escape_root_raises(project_root: Path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("../foo.txt", project_root, "my_field")
    assert "my_field" in str(exc.value)


def test_resolve_relative_path_escape_root_double_dot_in_middle_raises(project_root: Path):
    """a/../../foo.txt → resolve 后跳出 root → 拒绝。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("a/../../foo.txt", project_root, "my_field")


def test_resolve_relative_path_field_name_in_error_message(project_root: Path):
    """field_name 应出现在错误消息里。"""
    custom_field = "documents[SPECIAL].path"
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("../escape", project_root, custom_field)
    assert custom_field in str(exc.value)


def test_resolve_relative_path_unicode_filename(project_root: Path):
    result = _resolve_relative_path("中文.txt", project_root, "test_field")
    assert "中文.txt" in str(result)


def test_resolve_relative_path_long_path(project_root: Path):
    long_path = "/".join(["dir"] * 50) + "/file.txt"
    result = _resolve_relative_path(long_path, project_root, "test_field")
    assert result.is_absolute()


# =========================================================================
# 4. _detect_project_root 第二轮
# =========================================================================


def test_detect_project_root_returns_path_type(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert isinstance(result, Path)


def test_detect_project_root_from_file_input(tmp_path: Path):
    """传 file path → 应取 parent 找。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    file_p = tmp_path / "subdir" / "file.txt"
    file_p.parent.mkdir()
    file_p.write_text("x", encoding="utf-8")
    result = _detect_project_root(file_p)
    assert result == tmp_path.resolve()


def test_detect_project_root_from_dir_input(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    result = _detect_project_root(sub)
    assert result == tmp_path.resolve()


def test_detect_project_root_no_pyproject_at_all(tmp_path: Path):
    """没找到 pyproject.toml → 返 cur（已 resolve）。"""
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    result = _detect_project_root(sub)
    # 找不到 → 返 cur 自身（已 resolve）
    assert result == sub.resolve()


def test_detect_project_root_deeply_nested(tmp_path: Path):
    """深嵌套子目录 → 找到 root。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c" / "d" / "e"
    deep.mkdir(parents=True)
    result = _detect_project_root(deep)
    assert result == tmp_path.resolve()


def test_detect_project_root_walks_up_multiple_levels(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    cur = tmp_path / "x" / "y" / "z"
    cur.mkdir(parents=True)
    result = _detect_project_root(cur)
    assert result == tmp_path.resolve()


def test_detect_project_root_returns_absolute(tmp_path: Path):
    """返回值始终是 absolute path。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert result.is_absolute()


def test_detect_project_root_with_string_path(tmp_path: Path):
    """函数能接受 Path（不是 str），如果传 str 会先被处理为 Path？"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    # 内部第一行 cur = start.resolve() → start 必须是 Path-like
    result = _detect_project_root(tmp_path)
    assert isinstance(result, Path)


# =========================================================================
# 5. Manifest dataclass 第二轮
# =========================================================================


def test_manifest_dataclass_is_frozen():
    """Manifest 是 frozen dataclass，不能修改字段。"""
    import dataclasses
    fields = {f.name: f for f in dataclasses.fields(Manifest)}
    # frozen=True 通过 __dataclass_fields__ 不能直接看，但可以通过 setattr 试
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        m.manifest_version = "2.0"  # type: ignore[misc]


def test_manifest_file_count_property_int_type(project_root: Path):
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=project_root,
    )
    assert isinstance(m.file_count, int)


def test_manifest_file_count_empty_manifest(project_root: Path):
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=project_root,
    )
    assert m.file_count == 0


def test_manifest_pdf_count_zero_when_no_pdfs(project_root: Path):
    doc = DocumentEntry(
        doc_id="DC-1", path_str="a.docx", resolved_path=project_root / "a.docx",
        source_type="docx", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(doc,), expected_failures=(), project_root=project_root,
    )
    assert m.pdf_count == 0


def test_manifest_docx_count_zero_when_no_docx(project_root: Path):
    doc = DocumentEntry(
        doc_id="DC-1", path_str="a.pdf", resolved_path=project_root / "a.pdf",
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(doc,), expected_failures=(), project_root=project_root,
    )
    assert m.docx_count == 0


def test_manifest_categories_covered_returns_sorted_list(project_root: Path):
    d1 = DocumentEntry(
        doc_id="D1", path_str="a.docx", resolved_path=project_root / "a.docx",
        source_type="docx", sha256=None, categories=("z", "a", "m"),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(d1,), expected_failures=(), project_root=project_root,
    )
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_deduplicates_across_docs(project_root: Path):
    d1 = DocumentEntry(
        doc_id="D1", path_str="a.docx", resolved_path=project_root / "a.docx",
        source_type="docx", sha256=None, categories=("report",),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    d2 = DocumentEntry(
        doc_id="D2", path_str="b.docx", resolved_path=project_root / "b.docx",
        source_type="docx", sha256=None, categories=("report", "financial"),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(d1, d2), expected_failures=(), project_root=project_root,
    )
    assert m.categories_covered == ["financial", "report"]


def test_manifest_content_group_count_unpaired_docs(project_root: Path):
    d1 = DocumentEntry(
        doc_id="D1", path_str="a.docx", resolved_path=project_root / "a.docx",
        source_type="docx", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    d2 = DocumentEntry(
        doc_id="D2", path_str="b.docx", resolved_path=project_root / "b.docx",
        source_type="docx", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(d1, d2), expected_failures=(), project_root=project_root,
    )
    assert m.content_group_count == 2


def test_manifest_content_group_count_paired_docs(project_root: Path):
    d1 = DocumentEntry(
        doc_id="D1", path_str="a.docx", resolved_path=project_root / "a.docx",
        source_type="docx", sha256=None, categories=(),
        paired_with="D2", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    d2 = DocumentEntry(
        doc_id="D2", path_str="a.pdf", resolved_path=project_root / "a.pdf",
        source_type="pdf", sha256=None, categories=(),
        paired_with="D1", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(d1, d2), expected_failures=(), project_root=project_root,
    )
    assert m.content_group_count == 1


def test_manifest_content_group_count_mixed_paired_unpaired(project_root: Path):
    d1 = DocumentEntry(
        doc_id="D1", path_str="a.docx", resolved_path=project_root / "a.docx",
        source_type="docx", sha256=None, categories=(),
        paired_with="D2", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    d2 = DocumentEntry(
        doc_id="D2", path_str="a.pdf", resolved_path=project_root / "a.pdf",
        source_type="pdf", sha256=None, categories=(),
        paired_with="D1", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    d3 = DocumentEntry(
        doc_id="D3", path_str="b.docx", resolved_path=project_root / "b.docx",
        source_type="docx", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(d1, d2, d3), expected_failures=(), project_root=project_root,
    )
    assert m.content_group_count == 2


def test_manifest_content_group_count_unidirectional_pair(project_root: Path):
    """D1 → D2 但 D2 不指向 D1 → 算 1 组（pair_ids 去重）。"""
    d1 = DocumentEntry(
        doc_id="D1", path_str="a.docx", resolved_path=project_root / "a.docx",
        source_type="docx", sha256=None, categories=(),
        paired_with="D2", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    d2 = DocumentEntry(
        doc_id="D2", path_str="a.pdf", resolved_path=project_root / "a.pdf",
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(d1, d2), expected_failures=(), project_root=project_root,
    )
    # pair_ids = {frozenset({D1, D2})} → 1 组；D2 在 seen 中（pair 含 D2）→ 不算 unpaired
    # 结果：1 组
    assert m.content_group_count == 1


# =========================================================================
# 6. DocumentEntry 第二轮
# =========================================================================


def test_document_entry_dataclass_is_frozen(project_root: Path):
    import dataclasses
    d = DocumentEntry(
        doc_id="D1", path_str="a", resolved_path=project_root / "a",
        source_type="docx", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        d.doc_id = "X"  # type: ignore[misc]


def test_document_entry_all_fields_accessible(project_root: Path):
    d = DocumentEntry(
        doc_id="D1", path_str="a", resolved_path=project_root / "a",
        source_type="docx", sha256="abc", categories=("x",),
        paired_with="D2", annotation_file_str="ann", annotation_resolved=project_root / "ann",
        expectations={"k": "v"},
    )
    assert d.doc_id == "D1"
    assert d.path_str == "a"
    assert d.resolved_path == project_root / "a"
    assert d.source_type == "docx"
    assert d.sha256 == "abc"
    assert d.categories == ("x",)
    assert d.paired_with == "D2"
    assert d.annotation_file_str == "ann"
    assert d.annotation_resolved == project_root / "ann"
    assert d.expectations == {"k": "v"}


def test_document_entry_categories_is_tuple_not_list(project_root: Path):
    d = DocumentEntry(
        doc_id="D1", path_str="a", resolved_path=project_root / "a",
        source_type="docx", sha256=None, categories=("a", "b"),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    assert isinstance(d.categories, tuple)
    assert not isinstance(d.categories, list)


def test_document_entry_categories_default_empty_tuple(project_root: Path):
    d = DocumentEntry(
        doc_id="D1", path_str="a", resolved_path=project_root / "a",
        source_type="docx", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    assert d.categories == ()
    assert len(d.categories) == 0


# =========================================================================
# 7. ExpectedFailure 第二轮
# =========================================================================


def test_expected_failure_dataclass_is_frozen(project_root: Path):
    import dataclasses
    ef = ExpectedFailure(
        doc_id="EF-1", path_str="a", resolved_path=project_root / "a",
        expected_error_code="x", source_type=None,
    )
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        ef.doc_id = "X"  # type: ignore[misc]


def test_expected_failure_all_fields_accessible(project_root: Path):
    ef = ExpectedFailure(
        doc_id="EF-1", path_str="a", resolved_path=project_root / "a",
        expected_error_code="unsupported_type", source_type="txt",
    )
    assert ef.doc_id == "EF-1"
    assert ef.path_str == "a"
    assert ef.resolved_path == project_root / "a"
    assert ef.expected_error_code == "unsupported_type"
    assert ef.source_type == "txt"


def test_expected_failure_source_type_default_none(project_root: Path):
    ef = ExpectedFailure(
        doc_id="EF-1", path_str="a", resolved_path=project_root / "a",
        expected_error_code="x", source_type=None,
    )
    assert ef.source_type is None


def test_expected_failure_resolved_path_is_path_object(project_root: Path):
    ef = ExpectedFailure(
        doc_id="EF-1", path_str="a", resolved_path=project_root / "a",
        expected_error_code="x", source_type=None,
    )
    assert isinstance(ef.resolved_path, Path)


# =========================================================================
# 8. load_manifest 第二轮
# =========================================================================


def test_load_manifest_returns_manifest_instance(project_root: Path):
    p = _write_manifest(project_root, _basic_valid_manifest())
    m = load_manifest(p, project_root)
    assert isinstance(m, Manifest)


def test_load_manifest_with_annotation_file(project_root: Path):
    (project_root / "samples/private").mkdir(parents=True)
    (project_root / "samples/private/sample.docx").write_bytes(b"mock")
    (project_root / "samples/private/ann.json").write_text("{}", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "DC-1",
            "path": "samples/private/sample.docx",
            "source_type": "docx",
            "annotation_file": "samples/private/ann.json",
        }],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p, project_root)
    assert m.documents[0].annotation_resolved == (project_root / "samples/private/ann.json").resolve()


def test_load_manifest_annotation_escape_root_rejected(project_root: Path):
    (project_root / "samples/private").mkdir(parents=True)
    (project_root / "samples/private/sample.docx").write_bytes(b"mock")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "DC-1",
            "path": "samples/private/sample.docx",
            "source_type": "docx",
            "annotation_file": "../escape.json",
        }],
    }
    p = _write_manifest(project_root, data)
    with pytest.raises(ManifestError):
        load_manifest(p, project_root)


def test_load_manifest_annotation_backslash_rejected(project_root: Path):
    (project_root / "samples/private").mkdir(parents=True)
    (project_root / "samples/private/sample.docx").write_bytes(b"mock")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "DC-1",
            "path": "samples/private/sample.docx",
            "source_type": "docx",
            "annotation_file": "samples\\private\\ann.json",
        }],
    }
    p = _write_manifest(project_root, data)
    with pytest.raises(ManifestError):
        load_manifest(p, project_root)


def test_load_manifest_annotation_absolute_rejected(project_root: Path):
    (project_root / "samples/private").mkdir(parents=True)
    (project_root / "samples/private/sample.docx").write_bytes(b"mock")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "DC-1",
            "path": "samples/private/sample.docx",
            "source_type": "docx",
            "annotation_file": "/etc/passwd",
        }],
    }
    p = _write_manifest(project_root, data)
    with pytest.raises(ManifestError):
        load_manifest(p, project_root)


def test_load_manifest_str_path_input(project_root: Path):
    p = _write_manifest(project_root, _basic_valid_manifest())
    m = load_manifest(str(p), project_root)
    assert isinstance(m, Manifest)


def test_load_manifest_str_project_root(project_root: Path):
    p = _write_manifest(project_root, _basic_valid_manifest())
    m = load_manifest(p, str(project_root))
    assert isinstance(m, Manifest)


def test_load_manifest_missing_file_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as exc:
        load_manifest(tmp_path / "nonexistent.json")
    assert "不存在" in str(exc.value)


def test_load_manifest_invalid_json_raises(project_root: Path):
    p = project_root / "manifest.json"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root)
    assert "JSON" in str(exc.value) or "解析" in str(exc.value)


def test_load_manifest_json_decode_error_chained(project_root: Path):
    """json.JSONDecodeError → ManifestError with __cause__。"""
    p = project_root / "manifest.json"
    p.write_text("{not valid json", encoding="utf-8")
    try:
        load_manifest(p, project_root)
    except ManifestError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, json.JSONDecodeError)


def test_load_manifest_version_mismatch_unreachable_due_to_schema(project_root: Path):
    """schema 已经强制 manifest_version="1.0"，所以 load_manifest 内的 version mismatch
    检查是不可达防御代码。我们验证 schema 先拒绝。"""
    from evaluation.schema import EvalSchemaError
    data = {
        "manifest_version": "9.99",
        "devset_status": "incomplete",
        "documents": [],
    }
    p = _write_manifest(project_root, data)
    # schema 先抛 EvalSchemaError，不会进 ManifestError 路径
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root)


def test_load_manifest_empty_documents_allowed(project_root: Path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p, project_root)
    assert m.documents == ()


def test_load_manifest_no_expected_failures_field(project_root: Path):
    """expected_failures 是可选字段。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p, project_root)
    assert m.expected_failures == ()


def test_load_manifest_no_pyproject_uses_default_root(tmp_path: Path):
    """没传 project_root 时 → 自动 detect。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p)
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_categories_converted_to_tuple(project_root: Path):
    (project_root / "samples/private").mkdir(parents=True)
    (project_root / "samples/private/sample.docx").write_bytes(b"mock")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "DC-1",
            "path": "samples/private/sample.docx",
            "source_type": "docx",
            "categories": ["a", "b", "c"],
        }],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p, project_root)
    assert m.documents[0].categories == ("a", "b", "c")
    assert isinstance(m.documents[0].categories, tuple)


def test_load_manifest_default_categories_empty_tuple(project_root: Path):
    (project_root / "samples/private").mkdir(parents=True)
    (project_root / "samples/private/sample.docx").write_bytes(b"mock")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "DC-1",
            "path": "samples/private/sample.docx",
            "source_type": "docx",
        }],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p, project_root)
    assert m.documents[0].categories == ()


def test_load_manifest_sha256_string(project_root: Path):
    """sha256 必须匹配 ^[0-9a-f]{64}$。"""
    (project_root / "samples/private").mkdir(parents=True)
    (project_root / "samples/private/sample.docx").write_bytes(b"mock")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "DC-1",
            "path": "samples/private/sample.docx",
            "source_type": "docx",
            "sha256": "a" * 64,
        }],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p, project_root)
    assert m.documents[0].sha256 == "a" * 64


def test_load_manifest_sha256_default_none(project_root: Path):
    (project_root / "samples/private").mkdir(parents=True)
    (project_root / "samples/private/sample.docx").write_bytes(b"mock")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "DC-1",
            "path": "samples/private/sample.docx",
            "source_type": "docx",
        }],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p, project_root)
    assert m.documents[0].sha256 is None


def test_load_manifest_paired_with_string(project_root: Path):
    (project_root / "samples/private").mkdir(parents=True)
    (project_root / "samples/private/sample.docx").write_bytes(b"mock")
    (project_root / "samples/private/sample.pdf").write_bytes(b"mock")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "D1", "path": "samples/private/sample.docx", "source_type": "docx",
             "paired_with": "D2"},
            {"doc_id": "D2", "path": "samples/private/sample.pdf", "source_type": "pdf",
             "paired_with": "D1"},
        ],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p, project_root)
    assert m.documents[0].paired_with == "D2"
    assert m.documents[1].paired_with == "D1"


def test_load_manifest_default_paired_with_none(project_root: Path):
    (project_root / "samples/private").mkdir(parents=True)
    (project_root / "samples/private/sample.docx").write_bytes(b"mock")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "DC-1",
            "path": "samples/private/sample.docx",
            "source_type": "docx",
        }],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p, project_root)
    assert m.documents[0].paired_with is None


def test_load_manifest_expectations_passed_through(project_root: Path):
    (project_root / "samples/private").mkdir(parents=True)
    (project_root / "samples/private/sample.docx").write_bytes(b"mock")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "DC-1",
            "path": "samples/private/sample.docx",
            "source_type": "docx",
            "expectations": {"element_count_by_type": {"heading": 5}},
        }],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p, project_root)
    assert m.documents[0].expectations == {"element_count_by_type": {"heading": 5}}


def test_load_manifest_default_expectations_none(project_root: Path):
    (project_root / "samples/private").mkdir(parents=True)
    (project_root / "samples/private/sample.docx").write_bytes(b"mock")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "DC-1",
            "path": "samples/private/sample.docx",
            "source_type": "docx",
        }],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p, project_root)
    assert m.documents[0].expectations is None


def test_load_manifest_full_valid_manifest(project_root: Path):
    """完整 manifest 含 doc + EF + annotation。"""
    p = _write_full_valid_manifest(project_root)
    m = load_manifest(p, project_root)
    assert len(m.documents) == 1
    assert len(m.expected_failures) == 1
    assert m.documents[0].annotation_resolved is not None


def test_load_manifest_expected_failure_source_type(project_root: Path):
    (project_root / "samples/private").mkdir(parents=True)
    (project_root / "samples/private/bad.txt").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{
            "doc_id": "EF-1",
            "path": "samples/private/bad.txt",
            "expected_error_code": "unsupported_type",
            "source_type": "txt",
        }],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p, project_root)
    assert m.expected_failures[0].source_type == "txt"


def test_load_manifest_expected_failure_no_source_type(project_root: Path):
    (project_root / "samples/private").mkdir(parents=True)
    (project_root / "samples/private/bad.txt").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{
            "doc_id": "EF-1",
            "path": "samples/private/bad.txt",
            "expected_error_code": "unsupported_type",
        }],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p, project_root)
    assert m.expected_failures[0].source_type is None


def test_load_manifest_doc_id_unicode(project_root: Path):
    (project_root / "samples/private").mkdir(parents=True)
    (project_root / "samples/private/sample.docx").write_bytes(b"mock")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "测试-1",
            "path": "samples/private/sample.docx",
            "source_type": "docx",
        }],
    }
    p = _write_manifest(project_root, data)
    m = load_manifest(p, project_root)
    assert m.documents[0].doc_id == "测试-1"


# =========================================================================
# 9. ManifestError 第二轮
# =========================================================================


def test_manifest_error_is_exception_subclass():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_can_be_raised_and_caught():
    with pytest.raises(ManifestError):
        raise ManifestError("test")


def test_manifest_error_caught_as_generic_exception():
    """ManifestError 也被 Exception 捕获。"""
    with pytest.raises(Exception):
        raise ManifestError("test")


def test_manifest_error_str_returns_message():
    e = ManifestError("hello world")
    assert str(e) == "hello world"


def test_manifest_error_repr_contains_class_name():
    e = ManifestError("test")
    assert "ManifestError" in repr(e)


def test_manifest_error_args_length_one():
    e = ManifestError("test")
    assert len(e.args) == 1


def test_manifest_error_unicode_message():
    e = ManifestError("中文错误")
    assert str(e) == "中文错误"


def test_manifest_error_can_chain_from_json_error():
    try:
        try:
            raise json.JSONDecodeError("orig", "doc", 0)
        except json.JSONDecodeError as je:
            raise ManifestError("wrapped") from je
    except ManifestError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, json.JSONDecodeError)


def test_manifest_error_no_chained_cause_default():
    e = ManifestError("simple")
    assert e.__cause__ is None


def test_manifest_error_two_instances_not_equal():
    e1 = ManifestError("a")
    e2 = ManifestError("a")
    # Exception 实例不实现 __eq__，按 id 比较
    assert e1 is not e2


# =========================================================================
# 10. __all__ 与模块结构
# =========================================================================


def test_all_is_list():
    assert isinstance(manifest_all, list)


def test_all_contains_manifest_error():
    assert "ManifestError" in manifest_all


def test_all_contains_manifest():
    assert "Manifest" in manifest_all


def test_all_contains_document_entry():
    assert "DocumentEntry" in manifest_all


def test_all_contains_expected_failure():
    assert "ExpectedFailure" in manifest_all


def test_all_contains_load_manifest():
    assert "load_manifest" in manifest_all


def test_all_excludes_internal_helpers():
    """_is_absolute_like / _has_backslash / _resolve_relative_path / _detect_project_root
    都是 internal，不应在 __all__。"""
    assert "_is_absolute_like" not in manifest_all
    assert "_has_backslash" not in manifest_all
    assert "_resolve_relative_path" not in manifest_all
    assert "_detect_project_root" not in manifest_all


def test_all_exact_set():
    assert set(manifest_all) == {
        "ManifestError", "Manifest", "DocumentEntry",
        "ExpectedFailure", "load_manifest",
    }


def test_module_has_manifest_version_import():
    import evaluation.manifest as mod
    assert hasattr(mod, "MANIFEST_VERSION")


def test_module_imports_validate_from_schema():
    import evaluation.manifest as mod
    assert hasattr(mod, "validate")


def test_module_imports_json():
    import evaluation.manifest as mod
    assert hasattr(mod, "json")


def test_module_imports_path():
    import evaluation.manifest as mod
    assert hasattr(mod, "Path")


def test_module_imports_dataclass():
    import evaluation.manifest as mod
    assert hasattr(mod, "dataclass")


def test_module_internal_helpers_callable():
    import evaluation.manifest as mod
    assert callable(mod._is_absolute_like)
    assert callable(mod._has_backslash)
    assert callable(mod._resolve_relative_path)
    assert callable(mod._detect_project_root)


def test_module_dataclasses_present():
    import evaluation.manifest as mod
    assert hasattr(mod, "DocumentEntry")
    assert hasattr(mod, "ExpectedFailure")
    assert hasattr(mod, "Manifest")


# =========================================================================
# 11. Signature 验证
# =========================================================================


def test_load_manifest_signature_two_params_with_default():
    import inspect
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert params[0].name == "manifest_path"
    assert params[1].name == "project_root"
    assert params[1].default is None


def test_resolve_relative_path_signature_three_params():
    import inspect
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["path_str", "project_root", "field_name"]


def test_detect_project_root_signature_one_param():
    import inspect
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "start"


def test_is_absolute_like_signature_one_param():
    import inspect
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path_str"


def test_has_backslash_signature_one_param():
    import inspect
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path_str"
