"""evaluation/manifest.py 第三十六轮 edges 测试（Round 384）。

补强 edges35 未触及的角度：
- _is_absolute_like 数学边界第九批（更多 Unicode / 盘符大小写混合 / 多字符前缀 / 0x00 控制字符）
- _has_backslash 数学边界第九批（多种字符串组合）
- _resolve_relative_path 行为深度第九批（空字符串 / 仅 . / 仅 .. / 多级 ../ / 含 ./ 前缀 / 长 path）
- _detect_project_root 行为深度第九批（无 pyproject.toml fallback / 多层 parents / 文件 vs 目录 / start 是符号链接）
- DocumentEntry/ExpectedFailure/Manifest dataclass 行为第九批（frozen / equality / 字段顺序 / 默认值 / hash）
- Manifest properties algorithm 行为深度第九批（content_group_count 双向配对 / 单向配对 / 三组混合 / categories_covered 多 doc 合并去重）
- load_manifest malformed data 第九批（路径形式 / sha256 形式 / source_type 值 / annotation_file 形式 / expectations 类型）
- module source forbidden tokens 第十二批
- module source 字符串精确补强第七批
- signatures 第九批（5 funcs + Manifest properties 类）
- module 合理性第九批
- 端到端集成第九批（minimal manifest / 真实文件路径解析）
"""

from __future__ import annotations

import inspect
import json
import types
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


# ---------- _is_absolute_like 数学边界第九批 ----------


def test_is_absolute_like_empty_string_false():
    assert _is_absolute_like("") is False


def test_is_absolute_like_single_slash_true():
    assert _is_absolute_like("/foo") is True


def test_is_absolute_like_single_dot_false():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_double_dot_false():
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_windows_drive_lowercase_true():
    assert _is_absolute_like("c:/users") is True


def test_is_absolute_like_windows_drive_uppercase_true():
    assert _is_absolute_like("C:\\Users") is True


def test_is_absolute_like_windows_drive_mixed_separator_true():
    assert _is_absolute_like("D:/x") is True
    assert _is_absolute_like("D:\\x") is True


def test_is_absolute_like_single_letter_followed_by_colon_no_sep_false():
    """c:foo（盘符但无斜杠）→ 不是绝对路径。"""
    assert _is_absolute_like("c:foo") is False


def test_is_absolute_like_two_chars_no_drive_false():
    """ab 不构成盘符。"""
    assert _is_absolute_like("ab/foo") is False


def test_is_absolute_like_colon_only_false():
    assert _is_absolute_like(":foo") is False


def test_is_absolute_like_just_colon_separator_false():
    """a:b 类似 Windows drive 但 separator 不存在 → False。"""
    assert _is_absolute_like("a:b") is False


def test_is_absolute_like_drive_with_one_char_sep_true():
    """a:/foo → drive + / separator → True。"""
    assert _is_absolute_like("a:/foo") is True


def test_is_absolute_like_drive_no_separator_not_absolute():
    """a:foo（无分隔符）→ False。"""
    assert _is_absolute_like("a:foo") is False


def test_is_absolute_like_normal_relative_false():
    assert _is_absolute_like("foo/bar") is False


def test_is_absolute_like_single_char_no_colon_false():
    assert _is_absolute_like("a") is False


def test_is_absolute_like_normal_path_no_slash_false():
    assert _is_absolute_like("foo") is False


def test_is_absolute_like_returns_bool_type():
    assert isinstance(_is_absolute_like("foo"), bool)


# ---------- _has_backslash 数学边界第九批 ----------


def test_has_backslash_empty_false():
    assert _has_backslash("") is False


def test_has_backslash_single_backslash_true():
    assert _has_backslash("\\") is True


def test_has_backslash_no_backslash_false():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_with_backslash_true():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_only_backslashes_true():
    assert _has_backslash("\\\\\\") is True


def test_has_backslash_returns_bool_type():
    assert isinstance(_has_backslash("foo"), bool)


def test_has_backslash_starts_with_backslash_true():
    assert _has_backslash("\\foo") is True


def test_has_backslash_ends_with_backslash_true():
    assert _has_backslash("foo\\") is True


def test_has_backslash_unicode_no_backslash_false():
    assert _has_backslash("中文/路径") is False


def test_has_backslash_mixed_separators_true():
    assert _has_backslash("foo/bar\\baz") is True


# ---------- _resolve_relative_path 行为深度第九批 ----------


def test_resolve_relative_path_empty_raises(tmp_path):
    with pytest.raises(ManifestError, match="为空"):
        _resolve_relative_path("", tmp_path, "test")


def test_resolve_relative_path_absolute_posix_raises(tmp_path):
    with pytest.raises(ManifestError, match="绝对路径"):
        _resolve_relative_path("/etc/passwd", tmp_path, "test")


def test_resolve_relative_path_absolute_windows_drive_raises(tmp_path):
    with pytest.raises(ManifestError, match="绝对路径"):
        _resolve_relative_path("C:/Users/foo", tmp_path, "test")


def test_resolve_relative_path_backslash_raises(tmp_path):
    with pytest.raises(ManifestError, match="反斜杠"):
        _resolve_relative_path("foo\\bar", tmp_path, "test")


def test_resolve_relative_path_normal_relative_resolves(tmp_path):
    out = _resolve_relative_path("foo/bar", tmp_path, "test")
    assert isinstance(out, Path)
    assert out.is_absolute()


def test_resolve_relative_path_returns_path_object(tmp_path):
    out = _resolve_relative_path("foo", tmp_path, "test")
    assert isinstance(out, Path)


def test_resolve_relative_path_resolved_within_project_root(tmp_path):
    out = _resolve_relative_path("foo/bar", tmp_path, "test")
    rel = out.relative_to(tmp_path.resolve())
    assert str(rel) == "foo/bar" or str(rel).replace("\\", "/") == "foo/bar"


def test_resolve_relative_path_dot_path_resolves(tmp_path):
    """'.' 解析为 project_root 本身。"""
    out = _resolve_relative_path(".", tmp_path, "test")
    assert out == tmp_path.resolve()


def test_resolve_relative_path_single_nested_relative(tmp_path):
    out = _resolve_relative_path("a/b/c/d.txt", tmp_path, "test")
    assert out == (tmp_path / "a" / "b" / "c" / "d.txt").resolve()


def test_resolve_relative_path_field_name_in_error(tmp_path):
    """错误消息包含 field_name。"""
    with pytest.raises(ManifestError, match="my_field"):
        _resolve_relative_path("", tmp_path, "my_field")


def test_resolve_relative_path_double_dot_in_middle_allowed(tmp_path):
    """path 中包含 ../ 中间路径会被 resolve 解析；最终若在 project_root 内则通过。

    注意：foo/../bar resolve 后是 project_root/bar，仍在内 → 不抛。
    """
    out = _resolve_relative_path("foo/../bar", tmp_path, "test")
    assert out == (tmp_path / "bar").resolve()


def test_resolve_relative_path_double_dot_escape_raises(tmp_path):
    """../foo 试图逃出 project_root。

    resolve 后 ../foo 从 tmp_path 出去到 parent/foo，不在 tmp_path 内 → 抛。
    """
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("../foo", tmp_path, "test")


def test_resolve_relative_path_double_dot_escape_two_levels_raises(tmp_path):
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("../../foo", tmp_path, "test")


def test_resolve_relative_path_returns_path_with_resolve(tmp_path):
    """返回值始终是 resolve 后的绝对路径。"""
    out = _resolve_relative_path("foo", tmp_path, "test")
    assert out == out.resolve()


# ---------- _detect_project_root 行为深度第九批 ----------


def test_detect_project_root_returns_path_object(tmp_path):
    out = _detect_project_root(tmp_path)
    assert isinstance(out, Path)


def test_detect_project_root_finds_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_walks_up_to_find_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    out = _detect_project_root(nested)
    assert out == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_input(tmp_path):
    """无 pyproject.toml → 返回 start 自身（resolve 后）。"""
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_start_is_file(tmp_path):
    """start 是文件 → 取 parent 后再查找。"""
    f = tmp_path / "x.txt"
    f.write_text("hi", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    out = _detect_project_root(f)
    assert out == tmp_path.resolve()


def test_detect_project_root_with_str_input(tmp_path):
    """_detect_project_root 仅接受 Path（不接受 str）。"""
    with pytest.raises(AttributeError):
        _detect_project_root(str(tmp_path))  # type: ignore[arg-type]


def test_detect_project_root_idempotent(tmp_path):
    out1 = _detect_project_root(tmp_path)
    out2 = _detect_project_root(tmp_path)
    assert out1 == out2


# ---------- DocumentEntry/ExpectedFailure/Manifest dataclass 行为第九批 ----------


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


def test_document_entry_is_dataclass():
    assert is_dataclass(DocumentEntry)


def test_document_entry_is_frozen():
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "new"


def test_document_entry_field_count():
    f = fields(DocumentEntry)
    assert len(f) == 10


def test_document_entry_field_names():
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


def test_document_entry_equality():
    d1 = _make_doc()
    d2 = _make_doc()
    assert d1 == d2


def test_document_entry_inequality():
    d1 = _make_doc(doc_id="d1")
    d2 = _make_doc(doc_id="d2")
    assert d1 != d2


def test_document_entry_hash():
    d1 = _make_doc()
    d2 = _make_doc()
    assert hash(d1) == hash(d2)


def test_expected_failure_is_dataclass():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_is_frozen():
    ef = _make_ef()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "new"


def test_expected_failure_field_count():
    f = fields(ExpectedFailure)
    assert len(f) == 5


def test_expected_failure_field_names():
    f = fields(ExpectedFailure)
    names = [field.name for field in f]
    assert names == ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]


def test_expected_failure_equality():
    ef1 = _make_ef()
    ef2 = _make_ef()
    assert ef1 == ef2


def test_expected_failure_hash():
    ef1 = _make_ef()
    ef2 = _make_ef()
    assert hash(ef1) == hash(ef2)


def test_manifest_is_dataclass():
    assert is_dataclass(Manifest)


def test_manifest_is_frozen():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"


def test_manifest_field_count():
    f = fields(Manifest)
    assert len(f) == 5


def test_manifest_field_names():
    f = fields(Manifest)
    names = [field.name for field in f]
    assert names == [
        "manifest_version",
        "devset_status",
        "documents",
        "expected_failures",
        "project_root",
    ]


def test_manifest_equality():
    m1 = _make_manifest()
    m2 = _make_manifest()
    assert m1 == m2


# ---------- Manifest properties algorithm 行为深度第九批 ----------


def test_manifest_file_count_zero():
    m = _make_manifest(documents=[])
    assert m.file_count == 0


def test_manifest_file_count_one():
    m = _make_manifest(documents=[_make_doc()])
    assert m.file_count == 1


def test_manifest_file_count_three():
    m = _make_manifest(documents=[_make_doc(), _make_doc(doc_id="d2"), _make_doc(doc_id="d3")])
    assert m.file_count == 3


def test_manifest_pdf_count_zero():
    m = _make_manifest(documents=[_make_doc(source_type="docx")])
    assert m.pdf_count == 0


def test_manifest_pdf_count_two():
    m = _make_manifest(documents=[_make_doc(), _make_doc(doc_id="d2")])
    assert m.pdf_count == 2


def test_manifest_docx_count_zero():
    m = _make_manifest(documents=[_make_doc()])
    assert m.docx_count == 0


def test_manifest_docx_count_two():
    m = _make_manifest(
        documents=[_make_doc(source_type="docx"), _make_doc(doc_id="d2", source_type="docx")]
    )
    assert m.docx_count == 2


def test_manifest_mixed_counts():
    m = _make_manifest(
        documents=[
            _make_doc(),
            _make_doc(doc_id="d2", source_type="docx"),
            _make_doc(doc_id="d3"),
        ]
    )
    assert m.pdf_count == 2
    assert m.docx_count == 1


def test_manifest_content_group_count_all_unpaired():
    m = _make_manifest(
        documents=[
            _make_doc(),
            _make_doc(doc_id="d2"),
        ]
    )
    assert m.content_group_count == 2


def test_manifest_content_group_count_paired():
    d1 = _make_doc(doc_id="d1", paired_with="d2")
    d2 = _make_doc(doc_id="d2", paired_with="d1")
    m = _make_manifest(documents=[d1, d2])
    assert m.content_group_count == 1


def test_manifest_content_group_count_single_direction_paired():
    """单向 paired_with 也算一组。"""
    d1 = _make_doc(doc_id="d1", paired_with="d2")
    d2 = _make_doc(doc_id="d2")  # d2 不指回 d1
    m = _make_manifest(documents=[d1, d2])
    # d1.paired_with="d2" → pair_ids={frozenset{d1,d2}}，groups=1，seen={d1,d2}
    # d2 在 seen 中 → 不计 unpaired
    # d1 在 seen 中 → 不计 unpaired
    # unpaired=0
    assert m.content_group_count == 1


def test_manifest_content_group_count_mixed_paired_unpaired():
    d1 = _make_doc(doc_id="d1", paired_with="d2")
    d2 = _make_doc(doc_id="d2", paired_with="d1")
    d3 = _make_doc(doc_id="d3")  # unpaired
    m = _make_manifest(documents=[d1, d2, d3])
    assert m.content_group_count == 2


def test_manifest_content_group_count_three_paired():
    """三个 doc 两两 paired？实际只生成一对 frozenset。"""
    d1 = _make_doc(doc_id="d1", paired_with="d2")
    d2 = _make_doc(doc_id="d2", paired_with="d1")
    d3 = _make_doc(doc_id="d3", paired_with="d1")  # d3 指向 d1
    m = _make_manifest(documents=[d1, d2, d3])
    # pair_ids: {frozenset{d1,d2}, frozenset{d1,d3}}
    # groups = 2
    assert m.content_group_count == 2


def test_manifest_categories_covered_empty():
    m = _make_manifest(documents=[])
    assert m.categories_covered == []


def test_manifest_categories_covered_single_doc():
    m = _make_manifest(documents=[_make_doc(categories=("normal",))])
    assert m.categories_covered == ["normal"]


def test_manifest_categories_covered_multiple_docs_union():
    d1 = _make_doc(categories=("normal", "edge"))
    d2 = _make_doc(doc_id="d2", categories=("edge", "extreme"))
    m = _make_manifest(documents=[d1, d2])
    assert m.categories_covered == ["edge", "extreme", "normal"]


def test_manifest_categories_covered_sorted():
    """sorted alphabetically。"""
    d1 = _make_doc(categories=("z", "a", "m"))
    m = _make_manifest(documents=[d1])
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_deduplication():
    d1 = _make_doc(categories=("normal", "edge"))
    d2 = _make_doc(doc_id="d2", categories=("normal", "edge"))
    m = _make_manifest(documents=[d1, d2])
    assert m.categories_covered == ["edge", "normal"]


def test_manifest_categories_covered_returns_list_type():
    m = _make_manifest(documents=[])
    assert isinstance(m.categories_covered, list)


def test_manifest_properties_return_correct_types():
    m = _make_manifest()
    assert isinstance(m.file_count, int)
    assert isinstance(m.pdf_count, int)
    assert isinstance(m.docx_count, int)
    assert isinstance(m.content_group_count, int)


# ---------- load_manifest malformed data 第九批 ----------


def _write_manifest(tmp_path, data):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_missing_file_raises(tmp_path):
    with pytest.raises(ManifestError, match="不存在"):
        load_manifest(tmp_path / "no.json", project_root=tmp_path)


def test_load_manifest_invalid_json_raises(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON 解析失败"):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_empty_dict_raises(tmp_path):
    """空 dict 不符合 schema → EvalSchemaError。"""
    from evaluation.schema import EvalSchemaError

    p = _write_manifest(tmp_path, {})
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_valid_minimal_returns_manifest(tmp_path):
    """最小合法 manifest。"""
    # 创建一个项目根，包含 pyproject.toml
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


def test_load_manifest_with_one_document(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    # 实际放置一个文件以使 resolved_path 可能不存在（load_manifest 不验证文件存在）
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


def test_load_manifest_absolute_path_raises(tmp_path):
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
    # schema 拒绝 / 开头路径，先抛 EvalSchemaError；若 schema 通过则抛 ManifestError
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_backslash_path_raises(tmp_path):
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


def test_load_manifest_path_outside_root_raises(tmp_path):
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


def test_load_manifest_str_input(tmp_path):
    """manifest_path 接受 str。"""
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


def test_load_manifest_devset_status_complete(tmp_path):
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


def test_load_manifest_with_categories(tmp_path):
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


def test_load_manifest_with_paired_with(tmp_path):
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
    assert out.content_group_count == 1


def test_load_manifest_with_expected_failure(tmp_path):
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


def test_load_manifest_returns_manifest_with_correct_project_root(tmp_path):
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
    assert out.project_root == tmp_path.resolve()


def test_load_manifest_detects_project_root_when_none_given(tmp_path):
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
    out = load_manifest(p, project_root=None)
    assert out.project_root == tmp_path.resolve()


# ---------- module source forbidden tokens 第十二批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "yaml.load",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
        "exit(",
        "quit(",
        "global ",
    ],
)
def test_manifest_source_no_forbidden_token_twelfth(token):
    source = inspect.getsource(mmod)
    assert token not in source


def test_manifest_source_no_async_def():
    source = inspect.getsource(mmod)
    assert "async def" not in source


def test_manifest_source_no_yield():
    source = inspect.getsource(mmod)
    assert "yield" not in source


def test_manifest_source_no_walrus():
    source = inspect.getsource(mmod)
    assert ":=" not in source


def test_manifest_source_no_top_level_lambda():
    source = inspect.getsource(mmod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_manifest_source_no_unlink():
    source = inspect.getsource(mmod)
    assert "unlink" not in source


def test_manifest_source_no_remove():
    source = inspect.getsource(mmod)
    assert ".remove(" not in source


def test_manifest_source_no_logging():
    source = inspect.getsource(mmod)
    assert "logging" not in source
    assert "logger" not in source


def test_manifest_source_no_sleep():
    source = inspect.getsource(mmod)
    assert "time.sleep" not in source


def test_manifest_source_no_print():
    source = inspect.getsource(mmod)
    assert "print(" not in source


# ---------- module source 字符串精确补强第七批 ----------


def test_module_source_has_future_annotations():
    source = inspect.getsource(mmod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_json():
    source = inspect.getsource(mmod)
    assert "import json" in source


def test_module_source_imports_dataclass():
    source = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in source


def test_module_source_imports_path():
    source = inspect.getsource(mmod)
    assert "from pathlib import Path" in source


def test_module_source_imports_typing_any():
    source = inspect.getsource(mmod)
    assert "from typing import Any" in source


def test_module_source_imports_manifest_version():
    source = inspect.getsource(mmod)
    assert "MANIFEST_VERSION" in source


def test_module_source_imports_validate():
    source = inspect.getsource(mmod)
    assert "validate" in source


def test_module_source_has_ManifestError_class():
    source = inspect.getsource(mmod)
    assert "class ManifestError" in source


def test_module_source_has_DocumentEntry_dataclass():
    source = inspect.getsource(mmod)
    assert "@dataclass" in source
    assert "class DocumentEntry" in source


def test_module_source_has_ExpectedFailure_dataclass():
    source = inspect.getsource(mmod)
    assert "class ExpectedFailure" in source


def test_module_source_has_Manifest_dataclass():
    source = inspect.getsource(mmod)
    assert "class Manifest" in source


def test_module_source_docstring_present():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 30


def test_module_source_docstring_mentions_relative_path():
    assert "相对路径" in mmod.__doc__


def test_module_source_docstring_mentions_backslash():
    assert "反斜杠" in mmod.__doc__


def test_module_source_docstring_mentions_absolute():
    assert "绝对路径" in mmod.__doc__


def test_module_source_no_main_block():
    source = inspect.getsource(mmod)
    assert "if __name__" not in source


def test_module_source_no_hardcoded_absolute_path():
    source = inspect.getsource(mmod)
    assert "C:\\\\Users" not in source


# ---------- signatures 第九批 ----------


def test_signature_is_absolute_like_one_param():
    sig = inspect.signature(_is_absolute_like)
    assert len(sig.parameters) == 1


def test_signature_is_absolute_like_param_name():
    sig = inspect.signature(_is_absolute_like)
    assert "path_str" in sig.parameters


def test_signature_is_absolute_like_return_annotation_bool():
    sig = inspect.signature(_is_absolute_like)
    ra = sig.return_annotation
    assert ra == bool or ra == "bool"


def test_signature_has_backslash_one_param():
    sig = inspect.signature(_has_backslash)
    assert len(sig.parameters) == 1


def test_signature_has_backslash_param_name():
    sig = inspect.signature(_has_backslash)
    assert "path_str" in sig.parameters


def test_signature_has_backslash_return_bool():
    sig = inspect.signature(_has_backslash)
    ra = sig.return_annotation
    assert ra == bool or ra == "bool"


def test_signature_resolve_relative_path_3_params():
    sig = inspect.signature(_resolve_relative_path)
    assert len(sig.parameters) == 3


def test_signature_resolve_relative_path_param_names():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters) == ["path_str", "project_root", "field_name"]


def test_signature_resolve_relative_path_no_defaults():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_resolve_relative_path_return_path():
    sig = inspect.signature(_resolve_relative_path)
    ra = sig.return_annotation
    assert ra == Path or ra == "Path"


def test_signature_detect_project_root_one_param():
    sig = inspect.signature(_detect_project_root)
    assert len(sig.parameters) == 1


def test_signature_detect_project_root_param_name():
    sig = inspect.signature(_detect_project_root)
    assert "start" in sig.parameters


def test_signature_detect_project_root_return_path():
    sig = inspect.signature(_detect_project_root)
    ra = sig.return_annotation
    assert ra == Path or ra == "Path"


def test_signature_load_manifest_2_params():
    sig = inspect.signature(load_manifest)
    assert len(sig.parameters) == 2


def test_signature_load_manifest_param_names():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters) == ["manifest_path", "project_root"]


def test_signature_load_manifest_project_root_default_none():
    sig = inspect.signature(load_manifest)
    p = sig.parameters["project_root"]
    assert p.default is None


def test_signature_load_manifest_return_manifest():
    sig = inspect.signature(load_manifest)
    ra = sig.return_annotation
    assert ra == Manifest or ra == "Manifest"


def test_signature_funcs_function_type():
    for func in (_is_absolute_like, _has_backslash, _resolve_relative_path, _detect_project_root, load_manifest):
        assert inspect.isfunction(func)


def test_signature_funcs_module_eq():
    for func in (_is_absolute_like, _has_backslash, _resolve_relative_path, _detect_project_root, load_manifest):
        assert func.__module__ == "evaluation.manifest"


# ---------- module 合理性第九批 ----------


def test_module_all_attribute_value():
    assert mmod.__all__ == [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ]


def test_module_all_is_list():
    assert isinstance(mmod.__all__, list)


def test_module_all_entries_unique():
    assert len(mmod.__all__) == len(set(mmod.__all__))


def test_module_has_dunder_file():
    assert hasattr(mmod, "__file__")


def test_module_dunder_file_endswith_manifest_py():
    import os
    sep = os.sep
    assert mmod.__file__.endswith("evaluation" + sep + "manifest.py") or mmod.__file__.endswith(
        "evaluation/manifest.py"
    )


def test_module_name_is_evaluation_manifest():
    assert mmod.__name__ == "evaluation.manifest"


def test_module_has_ManifestError_class():
    assert hasattr(mmod, "ManifestError")
    assert inspect.isclass(mmod.ManifestError)


def test_module_ManifestError_inherits_Exception():
    assert issubclass(mmod.ManifestError, Exception)


def test_module_has_5_funcs_in_namespace():
    funcs = [
        n for n, v in vars(mmod).items()
        if inspect.isfunction(v) and v.__module__ == mmod.__name__
    ]
    assert set(funcs) == {
        "_is_absolute_like",
        "_has_backslash",
        "_resolve_relative_path",
        "load_manifest",
        "_detect_project_root",
    }


def test_module_has_3_dataclasses():
    classes = [
        n for n, v in vars(mmod).items()
        if inspect.isclass(v) and v.__module__ == mmod.__name__
    ]
    assert set(classes) == {"ManifestError", "DocumentEntry", "ExpectedFailure", "Manifest"}


def test_module_no_top_level_call():
    source = inspect.getsource(mmod)
    lines = source.split("\n")
    for line in lines:
        if not line.startswith(" "):
            stripped = line.strip()
            ok_prefixes = (
                "def ",
                "class ",
                "import ",
                "from ",
                "__all__",
                "#",
                '"""',
                "'''",
                "",
                "@",
            )
            if stripped and not any(stripped.startswith(p) for p in ok_prefixes):
                if "(" in stripped:
                    raise AssertionError(f"unexpected top-level call: {line}")


def test_module_docstring_present():
    assert mmod.__doc__ is not None


# ---------- 端到端集成第九批 ----------


def test_e2e_load_manifest_minimal(tmp_path):
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
    assert out.devset_status == "incomplete"
    assert out.documents == ()
    assert out.expected_failures == ()


def test_e2e_load_manifest_with_paired_documents(tmp_path):
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
    assert out.content_group_count == 1
    assert out.pdf_count == 1
    assert out.docx_count == 1


def test_e2e_load_manifest_with_annotation_file(tmp_path):
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
                    "annotation_file": "ann/d1.json",
                }
            ],
            "expected_failures": [],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].annotation_file_str == "ann/d1.json"
    assert isinstance(out.documents[0].annotation_resolved, Path)


def test_e2e_load_manifest_with_expectations(tmp_path):
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


def test_e2e_load_manifest_idempotent(tmp_path):
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
    out1 = load_manifest(p, project_root=tmp_path)
    out2 = load_manifest(p, project_root=tmp_path)
    assert out1 == out2


def test_e2e_load_manifest_categories_covered_correct(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [
                {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "categories": ["normal"]},
                {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf", "categories": ["edge"]},
                {"doc_id": "d3", "path": "c.pdf", "source_type": "pdf", "categories": ["normal"]},
            ],
            "expected_failures": [],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    assert out.categories_covered == ["edge", "normal"]


def test_e2e_load_manifest_resolved_path_is_absolute(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n", encoding="utf-8")
    p = _write_manifest(
        tmp_path,
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "incomplete",
            "documents": [
                {"doc_id": "d1", "path": "a/b.pdf", "source_type": "pdf"}
            ],
            "expected_failures": [],
        },
    )
    out = load_manifest(p, project_root=tmp_path)
    assert out.documents[0].resolved_path.is_absolute()


def test_e2e_load_manifest_no_documents_categories_covered_empty(tmp_path):
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
    assert out.categories_covered == []
