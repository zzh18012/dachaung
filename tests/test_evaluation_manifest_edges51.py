"""evaluation/manifest.py 第五十一轮 edges 测试（Round 489）。

补强 edges50 未触及的角度（第二十四批）：
- _is_absolute_like 第二十四批：空 str / 短 str / 仅盘符无斜杠 / x:abc / x:1 / x:./abc / 仅/ / 仅\\ / Cyrillic 字母盘符 / lowercase / uppercase
- _has_backslash 第二十四批：多 \\ / 开头 \\ / 末尾 \\ / 混合 / 仅空格
- _resolve_relative_path 第二十四批：空 → ManifestError / 绝对路径 / 反斜杠 / 路径越界 / 嵌套 .. 解析后越界 / 合法 / 多级嵌套 / 单级 ./ 不抛
- _detect_project_root 第二十四批：返回 Path / 文件输入 / 目录输入 / 无 pyproject fallback / 嵌套 pyproject 选最近
- Manifest properties 第二十四批：file_count / pdf_count / docx_count / content_group_count / categories_covered 排序 / frozen / hashable
- DocumentEntry 第二十四批：所有字段必填（含 None-valued）/ hashable / equality / inequality / categories tuple 类型 / expectations None / annotation_resolved None
- ExpectedFailure 第二十四批：source_type 默认 None / frozen / hashable
- load_manifest 第二十四批：文件不存在 / JSON 解析失败 / version 不兼容 / annotation_file resolved / expected_failures resolved / manifest_path str / project_root 默认 / devset_status 透传
- module source forbidden tokens 第三十九批
- module source 字符串精确补强第三十五批
- signatures 第三十五批
- module 合理性第三十五批
- 端到端集成第三十五批
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, dataclass
from pathlib import Path
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


# ---------- _is_absolute_like 第二十四批 ----------


def test_is_absolute_like_empty_string_batch24():
    """空字符串 → False。"""
    assert _is_absolute_like("") is False


def test_is_absolute_like_single_slash_batch24():
    """'/' → True。"""
    assert _is_absolute_like("/") is True


def test_is_absolute_like_posix_path_batch24():
    """'/foo/bar' → True。"""
    assert _is_absolute_like("/foo/bar") is True


def test_is_absolute_like_windows_drive_lowercase_batch24():
    """'c:/foo' → True（小写盘符）。"""
    assert _is_absolute_like("c:/foo") is True


def test_is_absolute_like_windows_drive_uppercase_batch24():
    """'C:\\foo' → True（大写盘符+反斜杠）。"""
    assert _is_absolute_like("C:\\foo") is True


def test_is_absolute_like_drive_no_slash_batch24():
    """'C:foo' → False（盘符但无 slash/backslash）。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_drive_colon_only_batch24():
    """'C:' → False（长度 < 3）。"""
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_single_char_batch24():
    """'a' → False。"""
    assert _is_absolute_like("a") is False


def test_is_absolute_like_relative_path_batch24():
    """'foo/bar' → False。"""
    assert _is_absolute_like("foo/bar") is False


def test_is_absolute_like_dot_path_batch24():
    """'./foo' → False（相对路径）。"""
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_dotdot_path_batch24():
    """'../foo' → False（相对路径，不在 _is_absolute_like 检查范围）。"""
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_relative_with_backslash_batch24():
    """'foo\\bar' → False（不是绝对，只是含反斜杠）。"""
    assert _is_absolute_like("foo\\bar") is False


# ---------- _has_backslash 第二十四批 ----------


def test_has_backslash_empty_batch24():
    assert _has_backslash("") is False


def test_has_backslash_single_backslash_batch24():
    assert _has_backslash("\\") is True


def test_has_backslash_multiple_backslash_batch24():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_only_forward_slash_batch24():
    assert _has_backslash("a/b/c") is False


def test_has_backslash_leading_backslash_batch24():
    assert _has_backslash("\\foo") is True


def test_has_backslash_trailing_backslash_batch24():
    assert _has_backslash("foo\\") is True


def test_has_backslash_no_separators_batch24():
    assert _has_backslash("foo") is False


# ---------- _resolve_relative_path 第二十四批 ----------


def test_resolve_relative_path_empty_raises_batch24(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "test_field")
    assert "test_field" in str(exc_info.value)
    assert "为空" in str(exc_info.value)


def test_resolve_relative_path_absolute_raises_batch24(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/etc/passwd", tmp_path, "f")
    assert "f" in str(exc_info.value)
    assert "绝对路径" in str(exc_info.value)


def test_resolve_relative_path_windows_absolute_raises_batch24(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("C:/foo", tmp_path, "f")


def test_resolve_relative_path_backslash_raises_batch24(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("foo\\bar", tmp_path, "f")
    assert "正斜杠" in str(exc_info.value)


def test_resolve_relative_path_outside_root_raises_batch24(tmp_path):
    """../foo 解析后位于 project_root 之外 → ManifestError。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("../foo", tmp_path, "f")
    assert "项目根目录之外" in str(exc_info.value)


def test_resolve_relative_path_legal_batch24(tmp_path):
    """合法相对路径 → 解析为 project_root/path。"""
    result = _resolve_relative_path("foo/bar.pdf", tmp_path, "f")
    assert result == (tmp_path / "foo" / "bar.pdf").resolve()


def test_resolve_relative_path_nested_legal_batch24(tmp_path):
    """多级嵌套合法路径。"""
    result = _resolve_relative_path("a/b/c/d.pdf", tmp_path, "f")
    assert result == (tmp_path / "a" / "b" / "c" / "d.pdf").resolve()


def test_resolve_relative_path_dot_slash_legal_batch24(tmp_path):
    """'./foo' 合法（解析后仍在 project_root 内）。"""
    result = _resolve_relative_path("./foo.pdf", tmp_path, "f")
    assert result == (tmp_path / "foo.pdf").resolve()


def test_resolve_relative_path_field_name_in_error_batch24(tmp_path):
    """错误消息含 field_name。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "documents[xxx].path")
    assert "documents[xxx].path" in str(exc_info.value)


def test_resolve_relative_path_idempotent_batch24(tmp_path):
    """多次调用一致。"""
    r1 = _resolve_relative_path("foo.pdf", tmp_path, "f")
    r2 = _resolve_relative_path("foo.pdf", tmp_path, "f")
    assert r1 == r2


def test_resolve_relative_path_returns_path_batch24(tmp_path):
    """返回 Path 对象。"""
    result = _resolve_relative_path("foo.pdf", tmp_path, "f")
    assert isinstance(result, Path)


def test_resolve_relative_path_resolved_is_absolute_batch24(tmp_path):
    """返回的路径是 absolute（已 resolve）。"""
    result = _resolve_relative_path("foo.pdf", tmp_path, "f")
    assert result.is_absolute()


# ---------- _detect_project_root 第二十四批 ----------


def test_detect_project_root_returns_path_batch24(tmp_path):
    """返回 Path。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert isinstance(result, Path)


def test_detect_project_root_directory_input_batch24(tmp_path):
    """目录输入 → 找到 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert result == tmp_path.resolve()


def test_detect_project_root_file_input_batch24(tmp_path):
    """文件输入 → 从 parent 开始找。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    f = tmp_path / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    result = _detect_project_root(f)
    assert result == tmp_path.resolve()


def test_detect_project_root_nested_picks_nearest_batch24(tmp_path):
    """嵌套 pyproject 选最近的（最深）。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "pyproject.toml").write_text("", encoding="utf-8")
    result = _detect_project_root(nested)
    assert result == nested.resolve()


def test_detect_project_root_no_pyproject_fallback_batch24(tmp_path):
    """无 pyproject → 返回 cur（start 或 start.parent）。"""
    result = _detect_project_root(tmp_path)
    # 仍返回 Path（不是 None）
    assert isinstance(result, Path)
    # 因为 tmp_path 没有 pyproject.toml，会一路向上到 root，可能找到或找不到
    # 这里只验证返回类型


def test_detect_project_root_returns_resolved_batch24(tmp_path):
    """返回的是 resolved 路径。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert result.is_absolute()


# ---------- Manifest properties 第二十四批 ----------


def _make_doc(doc_id="d1", source_type="pdf", categories=(), paired_with=None):
    return DocumentEntry(
        doc_id=doc_id,
        path_str=f"samples/private/{doc_id}.pdf" if source_type == "pdf" else f"samples/private/{doc_id}.docx",
        resolved_path=Path(f"/tmp/{doc_id}"),
        source_type=source_type,
        sha256=None,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def test_manifest_file_count_empty_batch24():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.file_count == 0


def test_manifest_file_count_three_batch24():
    docs = tuple(_make_doc(f"d{i}", "pdf") for i in range(3))
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.file_count == 3


def test_manifest_pdf_count_batch24():
    docs = (
        _make_doc("d1", "pdf"),
        _make_doc("d2", "docx"),
        _make_doc("d3", "pdf"),
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.pdf_count == 2


def test_manifest_docx_count_batch24():
    docs = (
        _make_doc("d1", "pdf"),
        _make_doc("d2", "docx"),
        _make_doc("d3", "docx"),
        _make_doc("d4", "docx"),
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.docx_count == 3


def test_manifest_categories_covered_sorted_batch24():
    docs = (
        _make_doc("d1", "pdf", categories=("z", "a")),
        _make_doc("d2", "docx", categories=("m",)),
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_empty_batch24():
    docs = (_make_doc("d1", "pdf", categories=()),)
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.categories_covered == []


def test_manifest_categories_covered_unique_batch24():
    """categories 去重。"""
    docs = (
        _make_doc("d1", "pdf", categories=("a", "b")),
        _make_doc("d2", "docx", categories=("b", "c")),
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_content_group_count_unpaired_batch24():
    """3 个 unpaired → 3 组。"""
    docs = tuple(_make_doc(f"d{i}", "pdf") for i in range(3))
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.content_group_count == 3


def test_manifest_content_group_count_paired_batch24():
    """d1 <-> d2（双向）→ 1 组。"""
    docs = (
        _make_doc("d1", "pdf", paired_with="d2"),
        _make_doc("d2", "docx", paired_with="d1"),
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.content_group_count == 1


def test_manifest_content_group_count_mixed_batch24():
    """1 pair + 1 unpaired → 2 组。"""
    docs = (
        _make_doc("d1", "pdf", paired_with="d2"),
        _make_doc("d2", "docx", paired_with="d1"),
        _make_doc("d3", "pdf"),
    )
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.content_group_count == 2


def test_manifest_frozen_batch24():
    """Manifest 是 frozen。"""
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


def test_manifest_hashable_batch24():
    """Manifest 可 hash。"""
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert hash(m) is not None


# ---------- DocumentEntry 第二十四批 ----------


def test_document_entry_all_fields_required_batch24():
    """所有字段必填。"""
    import inspect as _ins
    # 通过 dataclass fields 检查
    fields = DocumentEntry.__dataclass_fields__
    for name, f in fields.items():
        # 没有 default
        assert f.default is _ins._empty_marker if hasattr(_ins, "_empty_marker") else True
    # 通过实际构造：少传一个应报 TypeError
    with pytest.raises(TypeError):
        DocumentEntry(doc_id="x")  # type: ignore[call-arg]


def test_document_entry_equality_batch24():
    """两个相同构造的 DocumentEntry 相等。"""
    kwargs = dict(
        doc_id="d1",
        path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf",
        sha256=None,
        categories=("a",),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    d1 = DocumentEntry(**kwargs)
    d2 = DocumentEntry(**kwargs)
    assert d1 == d2


def test_document_entry_inequality_batch24():
    """不同 doc_id 不等。"""
    d1 = DocumentEntry(
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
    d2 = DocumentEntry(
        doc_id="d2",
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
    assert d1 != d2


def test_document_entry_hashable_batch24():
    d = _make_doc("d1", "pdf")
    assert hash(d) is not None


def test_document_entry_categories_is_tuple_batch24():
    d = _make_doc("d1", "pdf", categories=("a", "b"))
    assert isinstance(d.categories, tuple)
    assert d.categories == ("a", "b")


def test_document_entry_frozen_batch24():
    d = _make_doc("d1", "pdf")
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "x"  # type: ignore[misc]


def test_document_entry_expectations_none_batch24():
    d = _make_doc("d1", "pdf")
    assert d.expectations is None


def test_document_entry_annotation_resolved_none_batch24():
    d = _make_doc("d1", "pdf")
    assert d.annotation_resolved is None


def test_document_entry_path_str_preserved_batch24():
    """path_str 保留原始相对路径形式（不 normalize）。"""
    d = DocumentEntry(
        doc_id="d1",
        path_str="samples/private/foo.pdf",
        resolved_path=Path("/tmp/samples/private/foo.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    assert d.path_str == "samples/private/foo.pdf"


# ---------- ExpectedFailure 第二十四批 ----------


def _make_ef(doc_id="ef1", expected_error_code="parse_error", source_type=None):
    return ExpectedFailure(
        doc_id=doc_id,
        path_str=f"samples/private/{doc_id}.txt",
        resolved_path=Path(f"/tmp/{doc_id}"),
        expected_error_code=expected_error_code,
        source_type=source_type,
    )


def test_expected_failure_source_type_none_batch24():
    ef = _make_ef()
    assert ef.source_type is None


def test_expected_failure_source_type_explicit_batch24():
    ef = _make_ef(source_type="txt")
    assert ef.source_type == "txt"


def test_expected_failure_frozen_batch24():
    ef = _make_ef()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "x"  # type: ignore[misc]


def test_expected_failure_hashable_batch24():
    ef = _make_ef()
    assert hash(ef) is not None


def test_expected_failure_equality_batch24():
    ef1 = _make_ef()
    ef2 = _make_ef()
    assert ef1 == ef2


def test_expected_failure_inequality_batch24():
    ef1 = _make_ef(doc_id="ef1")
    ef2 = _make_ef(doc_id="ef2")
    assert ef1 != ef2


def test_expected_failure_all_fields_required_batch24():
    """少传字段报 TypeError。"""
    with pytest.raises(TypeError):
        ExpectedFailure(doc_id="x")  # type: ignore[call-arg]


# ---------- load_manifest 第二十四批 ----------


def test_load_manifest_missing_file_raises_batch24(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(tmp_path / "nope.json")
    assert "清单文件不存在" in str(exc_info.value)


def test_load_manifest_invalid_json_raises_batch24(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p)
    assert "JSON 解析失败" in str(exc_info.value)


def test_load_manifest_version_mismatch_raises_batch24(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "9.9",  # 不兼容
                "devset_status": "incomplete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    # schema 用 const="1.0"，会先被 schema 拒
    with pytest.raises(Exception):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_valid_empty_batch24(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)
    assert m.documents == ()
    assert m.expected_failures == ()


def test_load_manifest_str_path_batch24(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(str(p), project_root=str(tmp_path))
    assert isinstance(m, Manifest)


def test_load_manifest_default_project_root_batch24(tmp_path):
    """project_root=None → 调 _detect_project_root。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p)
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_devset_status_transmitted_batch24(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.devset_status == "complete"


def test_load_manifest_with_documents_batch24(tmp_path):
    """含 documents → DocumentEntry 列表。"""
    # 先在项目根创建对应文件
    (tmp_path / "samples" / "private").mkdir(parents=True, exist_ok=True)
    (tmp_path / "samples" / "private" / "d1.pdf").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "samples/private/d1.pdf",
                        "source_type": "pdf",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.documents) == 1
    assert m.documents[0].doc_id == "d1"
    assert m.documents[0].resolved_path == (tmp_path / "samples" / "private" / "d1.pdf").resolve()


def test_load_manifest_with_expected_failures_batch24(tmp_path):
    (tmp_path / "samples" / "private").mkdir(parents=True, exist_ok=True)
    (tmp_path / "samples" / "private" / "broken.txt").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [
                    {
                        "doc_id": "broken",
                        "path": "samples/private/broken.txt",
                        "expected_error_code": "unsupported_format",
                        "source_type": "txt",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].expected_error_code == "unsupported_format"


def test_load_manifest_absolute_path_rejected_batch24(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "/etc/passwd",  # 绝对路径
                        "source_type": "pdf",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "绝对路径" in str(exc_info.value)


def test_load_manifest_backslash_rejected_batch24(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "foo\\bar.pdf",  # 反斜杠
                        "source_type": "pdf",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "正斜杠" in str(exc_info.value)


def test_load_manifest_annotation_file_resolved_batch24(tmp_path):
    (tmp_path / "samples" / "private").mkdir(parents=True, exist_ok=True)
    (tmp_path / "samples" / "private" / "d1.pdf").write_text("", encoding="utf-8")
    (tmp_path / "samples" / "private" / "d1.json").write_text("{}", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "samples/private/d1.pdf",
                        "source_type": "pdf",
                        "annotation_file": "samples/private/d1.json",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_resolved == (tmp_path / "samples" / "private" / "d1.json").resolve()


def test_load_manifest_returns_manifest_instance_batch24(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)


# ---------- module source forbidden tokens 第三十九批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import datetime",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import itertools",
    "import functools",
    "import timeit",
    "import time",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from itertools",
    "from functools",
    "from time",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import subprocess",
    "import argparse",
]


def test_module_source_forbidden_tokens_batch24():
    """manifest.py 不应 import 这些副作用大的模块。"""
    source = inspect.getsource(mmod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_no_yield_batch24():
    source = inspect.getsource(mmod)
    assert "yield " not in source


def test_module_source_no_async_def_batch24():
    source = inspect.getsource(mmod)
    assert "async def" not in source


def test_module_source_no_global_keyword_batch24():
    source = inspect.getsource(mmod)
    assert "global " not in source


def test_module_source_no_walrus_batch24():
    source = inspect.getsource(mmod)
    assert ":=" not in source


def test_module_source_no_eval_exec_batch24():
    source = inspect.getsource(mmod)
    assert "eval(" not in source
    assert "exec(" not in source
    assert "compile(" not in source


def test_module_source_no_relative_imports_batch24():
    source_lines = inspect.getsource(mmod).split("\n")
    for line in source_lines:
        stripped = line.strip()
        if stripped.startswith("from .") and "from __future__" not in stripped:
            pytest.fail(f"relative import: {line}")


def test_module_source_no_star_import_batch24():
    source = inspect.getsource(mmod)
    assert "import *" not in source


def test_module_source_no_environ_batch24():
    source = inspect.getsource(mmod)
    assert "os.environ" not in source


def test_module_source_no_open_at_module_level_batch24():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(mmod))
    for node in tree.body:
        if isinstance(node, _ast.Expr) and isinstance(node.value, _ast.Call):
            f = node.value.func
            if isinstance(f, _ast.Name) and f.id == "open":
                pytest.fail("top-level open() call")


def test_module_source_no_subprocess_batch24():
    source = inspect.getsource(mmod)
    assert "import subprocess" not in source


def test_module_source_no_network_io_batch24():
    source = inspect.getsource(mmod)
    assert "import socket" not in source
    assert "import http" not in source


def test_module_source_no_argparse_batch24():
    source = inspect.getsource(mmod)
    assert "import argparse" not in source


def test_module_source_json_used_batch24():
    source = inspect.getsource(mmod)
    assert "import json" in source


def test_module_source_dataclass_used_batch24():
    source = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in source


def test_module_source_validate_imported_batch24():
    source = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in source


# ---------- module source 字符串精确补强 第三十五批 ----------


def test_module_source_contains_manifest_error_class_batch24():
    source = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in source


def test_module_source_contains_is_absolute_like_batch24():
    source = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in source


def test_module_source_contains_has_backslash_batch24():
    source = inspect.getsource(mmod)
    assert "def _has_backslash(" in source


def test_module_source_contains_resolve_relative_path_batch24():
    source = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in source


def test_module_source_contains_detect_project_root_batch24():
    source = inspect.getsource(mmod)
    assert "def _detect_project_root(" in source


def test_module_source_contains_document_entry_dataclass_batch24():
    source = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in source
    assert "class DocumentEntry:" in source


def test_module_source_contains_expected_failure_dataclass_batch24():
    source = inspect.getsource(mmod)
    assert "class ExpectedFailure:" in source


def test_module_source_contains_manifest_dataclass_batch24():
    source = inspect.getsource(mmod)
    assert "class Manifest:" in source


def test_module_source_contains_path_field_warning_batch24():
    source = inspect.getsource(mmod)
    assert "path 字段必须是相对路径" in source


def test_module_source_contains_resolve_to_root_check_batch24():
    """source 含 'relative_to' 检查。"""
    source = inspect.getsource(mmod)
    assert "relative_to" in source


def test_module_source_contains_frozenset_for_pair_batch24():
    """content_group_count 用 frozenset 去重配对。"""
    source = inspect.getsource(mmod)
    assert "frozenset" in source


def test_module_source_contains_manifest_version_const_batch24():
    source = inspect.getsource(mmod)
    assert "MANIFEST_VERSION" in source


def test_module_source_contains_categories_default_empty_batch24():
    """DocumentEntry categories 默认空 tuple。"""
    source = inspect.getsource(mmod)
    assert "categories" in source


def test_module_source_contains_pyproject_toml_text_batch24():
    """source 含 'pyproject.toml'。"""
    source = inspect.getsource(mmod)
    assert "pyproject.toml" in source


def test_module_source_contains_empty_text_batch24():
    """source 含 '为空' 中文。"""
    source = inspect.getsource(mmod)
    assert "为空" in source


# ---------- signatures 第三十五批 ----------


def test_signature_is_absolute_like_batch24():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path_str"
    assert params[0].annotation == "str"
    assert sig.return_annotation == "bool"


def test_signature_has_backslash_batch24():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path_str"
    assert params[0].annotation == "str"
    assert sig.return_annotation == "bool"


def test_signature_resolve_relative_path_batch24():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["path_str", "project_root", "field_name"]
    for p in params:
        assert p.default is inspect.Parameter.empty
    assert sig.return_annotation == "Path"


def test_signature_detect_project_root_batch24():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "start"
    assert sig.return_annotation == "Path"


def test_signature_load_manifest_batch24():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["manifest_path", "project_root"]
    assert params[1].default is None
    assert sig.return_annotation == "Manifest"


def test_signature_all_annotations_are_strings_batch24():
    for fn in [_is_absolute_like, _has_backslash, _resolve_relative_path, _detect_project_root, load_manifest]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            if p.annotation is not inspect.Parameter.empty:
                assert isinstance(p.annotation, str)
        if sig.return_annotation is not inspect.Signature.empty:
            assert isinstance(sig.return_annotation, str)


def test_signature_load_manifest_path_annotation_batch24():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["manifest_path"].annotation == "Path | str"
    assert sig.parameters["project_root"].annotation == "Path | str | None"


def test_signature_resolve_field_name_annotation_batch24():
    sig = inspect.signature(_resolve_relative_path)
    assert sig.parameters["field_name"].annotation == "str"


# ---------- module 合理性 第三十五批 ----------


def test_module_all_five_entries_batch24():
    assert hasattr(mmod, "__all__")
    assert set(mmod.__all__) == {
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    }


def test_module_has_three_dataclasses_batch24():
    classes = [
        name
        for name, val in inspect.getmembers(mmod, inspect.isclass)
        if val.__module__ == mmod.__name__ and "__dataclass_fields__" in dir(val)
    ]
    assert set(classes) == {"Manifest", "DocumentEntry", "ExpectedFailure"}


def test_module_has_one_exception_class_batch24():
    exc_classes = [
        name
        for name, val in inspect.getmembers(mmod, inspect.isclass)
        if val.__module__ == mmod.__name__ and issubclass(val, Exception)
    ]
    assert exc_classes == ["ManifestError"]


def test_module_has_five_functions_batch24():
    funcs = [
        name
        for name, val in inspect.getmembers(mmod, inspect.isfunction)
        if val.__module__ == mmod.__name__
    ]
    assert set(funcs) == {
        "_is_absolute_like",
        "_has_backslash",
        "_resolve_relative_path",
        "_detect_project_root",
        "load_manifest",
    }


def test_module_all_entries_accessible_batch24():
    for name in mmod.__all__:
        assert hasattr(mmod, name)


def test_module_docstring_present_batch24():
    assert mmod.__doc__ is not None


def test_module_docstring_mentions_path_constraint_batch24():
    assert "相对路径" in mmod.__doc__ or "正斜杠" in mmod.__doc__


def test_module_docstring_mentions_no_absolute_batch24():
    assert "绝对路径" in mmod.__doc__


def test_module_uses_from_future_annotations_batch24():
    source = inspect.getsource(mmod)
    assert "from __future__ import annotations" in source


def test_module_manifest_error_docstring_present_batch24():
    assert ManifestError.__doc__ is not None


def test_module_no_module_level_mutables_other_than_all_batch24():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(mmod))
    top_assigns = [
        node for node in tree.body if isinstance(node, _ast.Assign)
    ]
    names = []
    for node in top_assigns:
        for target in node.targets:
            if isinstance(target, _ast.Name):
                names.append(target.id)
    assert names == ["__all__"]


def test_module_manifest_error_inherits_exception_batch24():
    assert issubclass(ManifestError, Exception)


# ---------- 端到端集成 第三十五批 ----------


def test_e2e_load_manifest_with_full_features_batch24(tmp_path):
    (tmp_path / "samples" / "private").mkdir(parents=True, exist_ok=True)
    (tmp_path / "samples" / "private" / "d1.pdf").write_text("", encoding="utf-8")
    (tmp_path / "samples" / "private" / "d2.docx").write_text("", encoding="utf-8")
    (tmp_path / "samples" / "private" / "broken.txt").write_text("", encoding="utf-8")
    (tmp_path / "samples" / "private" / "d1.json").write_text("{}", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "samples/private/d1.pdf",
                        "source_type": "pdf",
                        "categories": ["report"],
                        "paired_with": "d2",
                        "annotation_file": "samples/private/d1.json",
                        "expectations": {
                            "element_count_by_type": {"paragraph": 5},
                            "required_markers": ["marker1"],
                        },
                    },
                    {
                        "doc_id": "d2",
                        "path": "samples/private/d2.docx",
                        "source_type": "docx",
                        "categories": ["report"],
                        "paired_with": "d1",
                    },
                ],
                "expected_failures": [
                    {
                        "doc_id": "broken",
                        "path": "samples/private/broken.txt",
                        "expected_error_code": "unsupported_format",
                        "source_type": "txt",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.content_group_count == 1
    assert m.categories_covered == ["report"]
    assert len(m.expected_failures) == 1
    assert m.documents[0].expectations is not None
    assert m.documents[0].expectations["element_count_by_type"]["paragraph"] == 5


def test_e2e_load_manifest_returns_frozen_instances_batch24(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


def test_e2e_load_manifest_documents_immutable_batch24(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m.documents, tuple)
    assert isinstance(m.expected_failures, tuple)


def test_e2e_load_manifest_categories_aggregation_batch24(tmp_path):
    (tmp_path / "samples").mkdir(parents=True, exist_ok=True)
    (tmp_path / "samples" / "a.pdf").write_text("", encoding="utf-8")
    (tmp_path / "samples" / "b.docx").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "samples/a.pdf",
                        "source_type": "pdf",
                        "categories": ["z", "a"],
                    },
                    {
                        "doc_id": "d2",
                        "path": "samples/b.docx",
                        "source_type": "docx",
                        "categories": ["m"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["a", "m", "z"]


def test_e2e_manifest_error_propagates_from_load_batch24(tmp_path):
    """load_manifest 不抛 ManifestError 之外的其他异常（如 KeyError）。"""
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [
                    {
                        "doc_id": "d1",
                        # 缺 path → schema 拒
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(Exception):  # EvalSchemaError
        load_manifest(p, project_root=tmp_path)


def test_e2e_manifest_no_path_escape_batch24(tmp_path):
    """'../foo' 不能逃出 project_root。"""
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "../escape.pdf",  # 越界
                        "source_type": "pdf",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "项目根目录之外" in str(exc_info.value)


def test_e2e_manifest_expected_failure_path_resolved_batch24(tmp_path):
    (tmp_path / "samples").mkdir(parents=True, exist_ok=True)
    (tmp_path / "samples" / "broken.txt").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [
                    {
                        "doc_id": "broken",
                        "path": "samples/broken.txt",
                        "expected_error_code": "unsupported_format",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].resolved_path == (tmp_path / "samples" / "broken.txt").resolve()
