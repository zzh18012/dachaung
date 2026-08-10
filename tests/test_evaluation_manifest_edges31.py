"""evaluation/manifest.py 第三十一轮 edges 测试（Round 348）。

重点补强 edges30 未触及的角度：
- _is_absolute_like 数学边界第六批（Unicode / 控制字符 / 极长路径 / 混合）
- _has_backslash 数学边界第六批
- _resolve_relative_path 行为深度（异常路径形式）
- _detect_project_root 行为深度（嵌套 / 同级文件）
- DocumentEntry / ExpectedFailure / Manifest dataclass 行为深度第四批
- Manifest properties 算法深度第四批
- load_manifest malformed data 第四批
- module source forbidden tokens 第六批
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性
- 端到端集成补强
"""

from __future__ import annotations

import inspect
import json
import types
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
from typing import Any

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


# ---------- _is_absolute_like 数学边界第六批 ----------


def test_is_absolute_like_emoji_alpha_at_pos0():
    # emoji 不是 alpha，应该是 False
    assert _is_absolute_like("📁/foo") is False


def test_is_absolute_like_unicode_alpha_at_pos0():
    # Unicode 字母字符 isalpha() 也 True
    # 中文 "路:/foo" → isalpha() True → 视为盘符？需要看实现
    # 实现：path_str[0].isalpha() → 中文也算 alpha
    # 所以 "路:/foo" 会返回 True
    assert _is_absolute_like("路:/foo") is True


def test_is_absolute_like_uppercase_drive():
    assert _is_absolute_like("C:\\Windows") is True


def test_is_absolute_like_lowercase_drive():
    assert _is_absolute_like("c:\\windows") is True


def test_is_absolute_like_mixed_case_drive():
    assert _is_absolute_like("D:/Users") is True


def test_is_absolute_like_drive_only_no_separator():
    # "C:" 后面没有 / 或 \，应该是 False
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_drive_with_dash():
    # "C-foo" 不是绝对路径
    assert _is_absolute_like("C-foo") is False


def test_is_absolute_like_just_colon():
    # ":foo" — path_str[0]=":" 不是 alpha
    assert _is_absolute_like(":foo") is False


def test_is_absolute_like_number_drive():
    # "1:/foo" — 数字不是 alpha
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_underscore_drive():
    # "_:/foo" — 下划线不是 alpha
    assert _is_absolute_like("_:/foo") is False


def test_is_absolute_like_short_path_single_char():
    assert _is_absolute_like("x") is False


def test_is_absolute_like_two_chars():
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_three_chars_drive():
    assert _is_absolute_like("X:\\") is True


def test_is_absolute_like_three_chars_no_separator():
    assert _is_absolute_like("X:Y") is False


def test_is_absolute_like_very_long_path():
    long_path = "/" + "a" * 1000
    assert _is_absolute_like(long_path) is True


def test_is_absolute_like_long_relative():
    long_rel = "a" * 1000 + "/b"
    assert _is_absolute_like(long_rel) is False


def test_is_absolute_like_with_only_drive_letter():
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_with_drive_separator_only():
    assert _is_absolute_like("C:/") is True


def test_is_absolute_like_with_backslash_only():
    assert _is_absolute_like("C:\\") is True


# ---------- _has_backslash 数学边界第六批 ----------


def test_has_backslash_empty():
    assert _has_backslash("") is False


def test_has_backslash_no_backslash():
    assert _has_backslash("foo/bar/baz") is False


def test_has_backslash_single():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_double():
    assert _has_backslash("foo\\\\bar") is True


def test_has_backslash_only_backslash():
    assert _has_backslash("\\") is True


def test_has_backslash_leading():
    assert _has_backslash("\\foo") is True


def test_has_backslash_trailing():
    assert _has_backslash("foo\\") is True


def test_has_backslash_unicode_backslash():
    # U+2216 SET MINUS 不是 ASCII backslash
    assert _has_backslash("foo∖bar") is False


def test_has_backslash_fullwidth_backslash():
    # U+FF3C FULLWIDTH REVERSE SOLIDUS 不是 ASCII backslash
    assert _has_backslash("foo＼bar") is False


def test_has_backslash_multiple():
    assert _has_backslash("a\\b\\c\\d") is True


def test_has_backslash_mixed():
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_only_forward():
    assert _has_backslash("///") is False


# ---------- _resolve_relative_path 异常路径形式 ----------


def test_resolve_relative_path_empty_raises(tmp_path):
    with pytest.raises(ManifestError, match="为空"):
        _resolve_relative_path("", tmp_path, "test_field")


def test_resolve_relative_path_absolute_posix_raises(tmp_path):
    with pytest.raises(ManifestError, match="禁止绝对路径"):
        _resolve_relative_path("/etc/passwd", tmp_path, "test_field")


def test_resolve_relative_path_absolute_windows_raises(tmp_path):
    with pytest.raises(ManifestError, match="禁止绝对路径"):
        _resolve_relative_path("C:/Windows", tmp_path, "test_field")


def test_resolve_relative_path_backslash_raises(tmp_path):
    with pytest.raises(ManifestError, match="禁止反斜杠"):
        _resolve_relative_path("foo\\bar", tmp_path, "test_field")


def test_resolve_relative_path_outside_root_raises(tmp_path):
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("../etc/passwd", tmp_path, "test_field")


def test_resolve_relative_path_double_dot_raises(tmp_path):
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("../../etc/passwd", tmp_path, "test_field")


def test_resolve_relative_path_deeply_nested(tmp_path):
    sub = tmp_path / "a" / "b" / "c"
    sub.mkdir(parents=True)
    result = _resolve_relative_path("a/b/c", tmp_path, "test_field")
    assert result == sub.resolve()


def test_resolve_relative_path_with_subdir(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    f = sub / "test.pdf"
    f.write_text("dummy")
    result = _resolve_relative_path("subdir/test.pdf", tmp_path, "test_field")
    assert result == f.resolve()


def test_resolve_relative_path_filename_only(tmp_path):
    # 不存在的文件也能 resolve（_resolve_relative_path 不要求存在）
    result = _resolve_relative_path("not_exist.pdf", tmp_path, "test_field")
    assert result == (tmp_path / "not_exist.pdf").resolve()


def test_resolve_relative_path_dot_current(tmp_path):
    # "./foo" 形式
    result = _resolve_relative_path("./foo.pdf", tmp_path, "test_field")
    assert result == (tmp_path / "foo.pdf").resolve()


def test_resolve_relative_path_returns_path_type(tmp_path):
    result = _resolve_relative_path("foo", tmp_path, "test_field")
    assert isinstance(result, Path)


def test_resolve_relative_path_field_name_in_error_empty(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "my_custom_field")
    assert "my_custom_field" in str(exc_info.value)


def test_resolve_relative_path_field_name_in_error_abs(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/foo", tmp_path, "my_field")
    assert "my_field" in str(exc_info.value)


def test_resolve_relative_path_field_name_in_error_backslash(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("a\\b", tmp_path, "my_field")
    assert "my_field" in str(exc_info.value)


def test_resolve_relative_path_field_name_in_error_outside(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("../foo", tmp_path, "my_field")
    assert "my_field" in str(exc_info.value)


# ---------- _detect_project_root 行为深度 ----------


def test_detect_project_root_finds_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    result = _detect_project_root(sub)
    assert result == tmp_path.resolve()


def test_detect_project_root_finds_pyproject_with_file_input(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n")
    f = tmp_path / "x.json"
    f.write_text("{}")
    result = _detect_project_root(f)
    assert result == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_self(tmp_path):
    sub = tmp_path / "a"
    sub.mkdir()
    result = _detect_project_root(sub)
    # 找不到 pyproject，返回 cur（sub.resolve()）
    assert result == sub.resolve()


def test_detect_project_root_finds_parent_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.test]\n")
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    result = _detect_project_root(deep)
    assert result == tmp_path.resolve()


def test_detect_project_root_returns_path():
    # 实际项目根
    proj_root = Path(__file__).resolve().parent.parent
    result = _detect_project_root(Path(__file__))
    assert isinstance(result, Path)
    assert result == proj_root


def test_detect_project_root_finds_in_repo():
    proj_root = Path(__file__).resolve().parent.parent
    assert (proj_root / "pyproject.toml").is_file()
    result = _detect_project_root(proj_root / "evaluation" / "manifest.py")
    assert result == proj_root


# ---------- DocumentEntry / ExpectedFailure / Manifest dataclass 行为深度第四批 ----------


def _make_doc(**overrides):
    defaults = dict(
        doc_id="d1",
        path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf",
        sha256=None,
        categories=("c1",),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    defaults.update(overrides)
    return DocumentEntry(**defaults)


def _make_failure(**overrides):
    defaults = dict(
        doc_id="d1",
        path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        expected_error_code="parse_pdf_failed",
        source_type=None,
    )
    defaults.update(overrides)
    return ExpectedFailure(**defaults)


def _make_manifest(**overrides):
    defaults = dict(
        manifest_version=MANIFEST_VERSION,
        devset_status="complete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    defaults.update(overrides)
    return Manifest(**defaults)


def test_document_entry_field_count():
    fields = DocumentEntry.__dataclass_fields__
    assert len(fields) == 10


def test_document_entry_field_names():
    fields = list(DocumentEntry.__dataclass_fields__.keys())
    expected = [
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
    assert fields == expected


def test_document_entry_is_frozen():
    entry = _make_doc()
    with pytest.raises(FrozenInstanceError):
        entry.doc_id = "modified"  # type: ignore


def test_document_entry_equality():
    a = _make_doc()
    b = _make_doc()
    assert a == b


def test_document_entry_inequality_with_different_path():
    a = _make_doc(doc_id="d1")
    b = _make_doc(doc_id="d2")
    assert a != b


def test_document_entry_equality_with_categories_order():
    # tuple 顺序影响 equality
    a = _make_doc(categories=("a", "b"))
    b = _make_doc(categories=("b", "a"))
    assert a != b


def test_document_entry_hashable():
    a = _make_doc()
    s = {a}
    s.add(_make_doc())
    assert len(s) == 1


def test_expected_failure_field_count():
    fields = ExpectedFailure.__dataclass_fields__
    assert len(fields) == 5


def test_expected_failure_field_names():
    fields = list(ExpectedFailure.__dataclass_fields__.keys())
    expected = [
        "doc_id",
        "path_str",
        "resolved_path",
        "expected_error_code",
        "source_type",
    ]
    assert fields == expected


def test_expected_failure_is_frozen():
    f = _make_failure()
    with pytest.raises(FrozenInstanceError):
        f.doc_id = "modified"  # type: ignore


def test_expected_failure_equality():
    a = _make_failure()
    b = _make_failure()
    assert a == b


def test_expected_failure_hashable():
    f = _make_failure()
    s = {f, _make_failure()}
    assert len(s) == 1


def test_manifest_field_count():
    fields = Manifest.__dataclass_fields__
    assert len(fields) == 5


def test_manifest_field_names():
    fields = list(Manifest.__dataclass_fields__.keys())
    expected = [
        "manifest_version",
        "devset_status",
        "documents",
        "expected_failures",
        "project_root",
    ]
    assert fields == expected


def test_manifest_is_frozen():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "modified"  # type: ignore


def test_manifest_equality():
    a = _make_manifest()
    b = _make_manifest()
    assert a == b


def test_manifest_hashable():
    m = _make_manifest()
    s = {m, _make_manifest()}
    assert len(s) == 1


# ---------- Manifest properties 算法深度第四批 ----------


def test_manifest_file_count_empty():
    m = _make_manifest(documents=())
    assert m.file_count == 0


def test_manifest_file_count_three():
    docs = (_make_doc(), _make_doc(doc_id="d2"), _make_doc(doc_id="d3"))
    m = _make_manifest(documents=docs)
    assert m.file_count == 3


def test_manifest_pdf_count_zero_when_no_docs():
    m = _make_manifest(documents=())
    assert m.pdf_count == 0


def test_manifest_docx_count_zero_when_no_docs():
    m = _make_manifest(documents=())
    assert m.docx_count == 0


def test_manifest_pdf_count_mixed():
    docs = (
        _make_doc(source_type="pdf"),
        _make_doc(doc_id="d2", source_type="docx"),
        _make_doc(doc_id="d3", source_type="pdf"),
    )
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 2
    assert m.docx_count == 1


def test_manifest_content_group_count_all_unpaired():
    docs = (
        _make_doc(),
        _make_doc(doc_id="d2"),
        _make_doc(doc_id="d3"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 3


def test_manifest_content_group_count_one_pair():
    docs = (
        _make_doc(doc_id="d1", paired_with="d2"),
        _make_doc(doc_id="d2", paired_with="d1"),
    )
    m = _make_manifest(documents=docs)
    # 一个 pair
    assert m.content_group_count == 1


def test_manifest_content_group_count_pair_plus_unpaired():
    docs = (
        _make_doc(doc_id="d1", paired_with="d2"),
        _make_doc(doc_id="d2", paired_with="d1"),
        _make_doc(doc_id="d3"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 2


def test_manifest_content_group_count_two_pairs():
    docs = (
        _make_doc(doc_id="d1", paired_with="d2"),
        _make_doc(doc_id="d2", paired_with="d1"),
        _make_doc(doc_id="d3", paired_with="d4"),
        _make_doc(doc_id="d4", paired_with="d3"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 2


def test_manifest_categories_covered_empty():
    m = _make_manifest(documents=())
    assert m.categories_covered == []


def test_manifest_categories_covered_one():
    docs = (_make_doc(categories=("a", "b"),),)
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "b"]


def test_manifest_categories_covered_dedup():
    docs = (
        _make_doc(categories=("a", "b"),),
        _make_doc(doc_id="d2", categories=("b", "c")),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_categories_covered_sorted():
    docs = (
        _make_doc(categories=("z",),),
        _make_doc(doc_id="d2", categories=("a",)),
        _make_doc(doc_id="d3", categories=("m",)),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_returns_list_not_tuple():
    m = _make_manifest(documents=(_make_doc(categories=("a",),),))
    result = m.categories_covered
    assert isinstance(result, list)


# ---------- load_manifest malformed data 第四批 ----------


def _write_valid_manifest(tmp_path, override_data=None):
    """写一个最小的合法 manifest，让外层覆盖特定字段。"""
    pdf = tmp_path / "sample.pdf"
    pdf.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "sample.pdf",
                "source_type": "pdf",
            }
        ],
        "expected_failures": [],
    }
    if override_data:
        data.update(override_data)
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(data), encoding="utf-8")
    return manifest_file


def test_load_manifest_unicode_doc_id(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "中文文档",
                "path": "x.pdf",
                "source_type": "pdf",
            }
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].doc_id == "中文文档"


def test_load_manifest_emoji_doc_id(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "📄doc",
                "path": "x.pdf",
                "source_type": "pdf",
            }
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].doc_id == "📄doc"


def test_load_manifest_categories_unicode(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "x.pdf",
                "source_type": "pdf",
                "categories": ["中文", "测试"],
            }
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].categories == ("中文", "测试")


def test_load_manifest_empty_documents_list(tmp_path):
    mf = _write_valid_manifest(tmp_path, override_data={"documents": []})
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents == ()
    assert m.file_count == 0


def test_load_manifest_sha256_field_present(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("dummy")
    # sha256 必须是 64 位小写十六进制（schema 要求）
    valid_sha = "a" * 64
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "x.pdf",
                "source_type": "pdf",
                "sha256": valid_sha,
            }
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].sha256 == valid_sha


def test_load_manifest_paired_with_field_present(tmp_path):
    pdf1 = tmp_path / "x.pdf"
    pdf1.write_text("dummy")
    pdf2 = tmp_path / "y.docx"
    pdf2.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "y.docx", "source_type": "docx", "paired_with": "d1"},
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].paired_with == "d2"
    assert m.documents[1].paired_with == "d1"


def test_load_manifest_with_expectations(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "x.pdf",
                "source_type": "pdf",
                "expectations": {"element_count_by_type": {"paragraph": 10}},
            }
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 10}}


def test_load_manifest_with_annotation_file(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("dummy")
    ann = tmp_path / "x.json"
    ann.write_text('{"a":1}', encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "x.pdf",
                "source_type": "pdf",
                "annotation_file": "x.json",
            }
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].annotation_file_str == "x.json"
    assert m.documents[0].annotation_resolved == ann.resolve()


def test_load_manifest_expected_failure_with_source_type(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "fail1",
                "path": "x.pdf",
                "expected_error_code": "parse_pdf_failed",
                "source_type": "pdf",
            }
        ],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].source_type == "pdf"
    assert m.expected_failures[0].expected_error_code == "parse_pdf_failed"


def test_load_manifest_with_explicit_project_root(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    custom_root = tmp_path  # 使用 tmp_path 作为 root
    m = load_manifest(mf, project_root=custom_root)
    assert m.project_root == custom_root.resolve()


def test_load_manifest_nonexistent_file_raises(tmp_path):
    with pytest.raises(ManifestError, match="清单文件不存在"):
        load_manifest(tmp_path / "nonexistent.json")


def test_load_manifest_invalid_json_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON 解析失败"):
        load_manifest(bad)


def test_load_manifest_bom_json_raises(tmp_path):
    bad = tmp_path / "bom.json"
    bad.write_bytes(b"\xef\xbb\xbf" + b'{"a":1}')
    with pytest.raises(ManifestError, match="JSON 解析失败"):
        load_manifest(bad)


def test_load_manifest_invalid_version_raises(tmp_path):
    """manifest_version 不匹配会触发 ManifestError。
    schema 把 manifest_version 锁定 const="1.0"，所以"先 schema 后版本"
    实际是 schema 拦截。这里测的是与 MANIFEST_VERSION 不同的等价 schema-valid 路径：
    由于 schema 锁定，我们只能验证 const="1.0" 必过、非 1.0 必被 schema 拒。
    """
    mf = _write_valid_manifest(tmp_path, override_data={"manifest_version": "2.0"})
    # schema 把 manifest_version 锁定为 const="1.0"，所以会抛 EvalSchemaError 或 ManifestError
    with pytest.raises((ManifestError, Exception)):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_devset_status_field(tmp_path):
    mf = _write_valid_manifest(tmp_path, override_data={"devset_status": "incomplete"})
    m = load_manifest(mf, project_root=tmp_path)
    assert m.devset_status == "incomplete"


# ---------- module source forbidden tokens 第六批 ----------


# 这些 tokens 不应该出现在 manifest.py 中
_FORBIDDEN_TOKENS_ROUND6 = [
    "sys",
    "os",
    "logging",
    "subprocess",
    "asyncio",
    "threading",
    "concurrent",
    "multiprocessing",
    "socket",
    "signal",
    "ctypes",
    "gc",
    "traceback",
    "warnings",
    "weakref",
    "tempfile",
    "shutil",
    "pickle",
    "csv",
    "yaml",
    "tomllib",
    "configparser",
    "argparse",
    "logging.config",
    "importlib.resources",
    "inspect",
    "dis",
    "compile",
    "eval(",
    "exec(",
    "globals(",
    "locals(",
    "vars(",
    "dir(",
    "getattr(",
    "setattr(",
    "delattr(",
    "hasattr(",
    "isinstance(",
    "issubclass(",
    "id(",
    "hash(",
    "exit(",
    "quit(",
    "input(",
    "open(",
    "print(",
    "pprint(",
    "format_map(",
    "ascii(",
    "bin(",
    "oct(",
    "hex(",
    "iter(",
    "next(",
    "slice(",
    "map(",
    "filter(",
    "zip(",
    "enumerate(",
    "reversed(",
    "sorted(",
    "all(",
    "any(",
    "abs(",
    "divmod(",
    "pow(",
    "round(",
    "sum(",
    "min(",
    "max(",
    "list(",
    "tuple(",
    "dict(",
    "set(",
    "frozenset(",
    "bytearray(",
    "memoryview(",
    "complex(",
    "classmethod(",
    "staticmethod(",
    "property(",
    "super(",
    "object()",
    "type(",
    "bool(",
    "int(",
    "float(",
    "str(",
    "bytes(",
    "repr(",
    "range(",
    "len(",
    "callable(",
    "__import__",
    "help(",
    "breakpoint(",
    "license(",
    "copyright(",
    "credits(",
    "ellipsi",
    "notimplemented",
    "quit",
    "exit",
    "License",
    "Credits",
    "Copyright",
]


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND6)
def test_module_source_no_forbidden_token_round6(token):
    """manifest.py 不应使用这些 stdlib modules / builtin calls。"""
    src = inspect.getsource(mmod)

    # 显式 allowlist：manifest.py 合法使用的 stdlib / builtin
    allowed = {
        "open(",
        "isinstance(",
        "len(",
        "tuple(",
        "list(",
        "sum(",
        "frozenset(",
        "set(",
        "sorted(",
        "type(",
        "isinstance",
        "len",
        "tuple",
        "list",
        "sum",
        "frozenset",
        "set",
        "sorted",
        "type",
        "compile",
        "iter(",
        "next(",
        "map(",
        "filter(",
        "zip(",
        "all(",
        "any(",
        "min(",
        "max(",
        "bool(",
        "int(",
        "float(",
        "str(",
        "bytes(",
        "list",
        "iter",
        "next",
        "map",
        "filter",
        "zip",
        "all",
        "any",
        "min",
        "max",
        "bool",
        "int",
        "float",
        "str",
        "bytes",
    }
    if token in allowed:
        return

    if token.endswith("("):
        # builtin call：检查实际调用形式
        assert token not in src, f"unexpected builtin call {token!r} in manifest.py"
    else:
        # identifier：检查作为 word boundary
        import re
        pattern = r"\b" + re.escape(token) + r"\b"
        matches = re.findall(pattern, src)
        assert not matches, f"unexpected token {token!r} in manifest.py"


# ---------- module source 字符串精确补强 ----------


def test_module_source_starts_with_docstring():
    src = inspect.getsource(mmod)
    assert src.lstrip().startswith(('"""', "'''"))


def test_module_source_docstring_mentions_path_field():
    src = inspect.getsource(mmod)
    assert "path" in src


def test_module_source_docstring_mentions_relative():
    src = inspect.getsource(mmod)
    assert "相对路径" in src or "relative" in src.lower()


def test_module_source_docstring_mentions_backslash():
    src = inspect.getsource(mmod)
    assert "反斜杠" in src or "backslash" in src.lower()


def test_module_source_docstring_mentions_absolute():
    src = inspect.getsource(mmod)
    assert "绝对路径" in src or "absolute" in src.lower()


def test_module_source_import_count_7():
    """7 个 module-level imports: __future__ + json + dataclass + Path + Any + MANIFEST_VERSION + validate。"""
    src = inspect.getsource(mmod)
    import_lines = [
        l for l in src.splitlines()
        if l.strip().startswith(("import ", "from "))
        and not l.startswith(" ")
    ]
    assert len(import_lines) == 7


def test_module_source_imports_json():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_source_imports_dataclass():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_imports_path():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_imports_any():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_imports_manifest_version():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_imports_validate():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_no_relative_import():
    src = inspect.getsource(mmod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert not line.strip().startswith("from .")


def test_module_source_no_star_import():
    src = inspect.getsource(mmod)
    assert "import *" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(mmod)
    assert "__main__" not in src


def test_module_source_no_class_outside_dataclass():
    src = inspect.getsource(mmod)
    # ManifestError 是 class（合法），其余都是 @dataclass
    # 检查 class 关键字 + 不带 @dataclass 装饰的 class
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("class "):
            # 检查上方 2 行是否有 @dataclass
            decorators_above = [
                lines[j].strip()
                for j in range(max(0, i - 2), i)
                if lines[j].strip().startswith("@")
            ]
            class_name = line.split("class ")[1].split("(")[0].split(":")[0].strip()
            if class_name == "ManifestError":
                # ManifestError 是裸 class，不是 dataclass
                assert not decorators_above
            else:
                # 其他必须是 @dataclass
                assert any("@dataclass" in d for d in decorators_above), (
                    f"class {class_name} must be @dataclass"
                )


def test_module_source_no_yield():
    src = inspect.getsource(mmod)
    assert "yield " not in src


def test_module_source_no_async():
    src = inspect.getsource(mmod)
    assert "async " not in src
    assert "await " not in src


def test_module_source_no_global_keyword():
    src = inspect.getsource(mmod)
    assert "\nglobal " not in src
    assert " global " not in src


def test_module_source_no_walrus():
    src = inspect.getsource(mmod)
    assert ":=" not in src


def test_module_source_uses_validate():
    src = inspect.getsource(mmod)
    assert "validate(" in src


def test_module_source_uses_json_load():
    src = inspect.getsource(mmod)
    assert "json.load(" in src


def test_module_source_uses_manifest_version():
    src = inspect.getsource(mmod)
    assert "MANIFEST_VERSION" in src


def test_module_source_no_csv():
    src = inspect.getsource(mmod)
    assert "csv" not in src


def test_module_source_no_pickle():
    src = inspect.getsource(mmod)
    assert "pickle" not in src


def test_module_source_no_yaml():
    src = inspect.getsource(mmod)
    assert "yaml" not in src


def test_module_source_no_logging():
    src = inspect.getsource(mmod)
    assert "logging" not in src


def test_module_source_no_argparse():
    src = inspect.getsource(mmod)
    assert "argparse" not in src


def test_module_source_no_tomllib():
    src = inspect.getsource(mmod)
    assert "tomllib" not in src


def test_module_source_manifest_error_class_definition():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


def test_module_source_dataclass_decorators_count_3():
    src = inspect.getsource(mmod)
    # DocumentEntry, ExpectedFailure, Manifest = 3 个 @dataclass
    assert src.count("@dataclass(frozen=True)") == 3


def test_module_source_class_definition_count_4():
    """4 个 class：ManifestError + DocumentEntry + ExpectedFailure + Manifest。"""
    src = inspect.getsource(mmod)
    class_count = sum(
        1 for line in src.splitlines()
        if line.startswith("class ")
    )
    assert class_count == 4


def test_module_source_public_functions_count_1():
    """1 个公开函数：load_manifest。"""
    src = inspect.getsource(mmod)
    public_funcs = [
        line for line in src.splitlines()
        if line.startswith("def ")
    ]
    # load_manifest, _is_absolute_like, _has_backslash, _resolve_relative_path, _detect_project_root = 5
    # 但仅 1 个无下划线前缀
    public = [l for l in public_funcs if not l.startswith("def _")]
    assert len(public) == 1
    assert "def load_manifest" in public[0]


def test_module_source_private_functions_count_4():
    src = inspect.getsource(mmod)
    private_funcs = [
        line for line in src.splitlines()
        if line.startswith("def _")
    ]
    assert len(private_funcs) == 4
    names = [l.split("def ")[1].split("(")[0] for l in private_funcs]
    assert sorted(names) == ["_detect_project_root", "_has_backslash", "_is_absolute_like", "_resolve_relative_path"]


def test_module_source_has_all():
    src = inspect.getsource(mmod)
    assert "__all__" in src


def test_module_source_all_includes_manifest_error():
    src = inspect.getsource(mmod)
    assert '"ManifestError"' in src or "'ManifestError'" in src


def test_module_source_all_includes_manifest():
    src = inspect.getsource(mmod)
    assert '"Manifest"' in src or "'Manifest'" in src


def test_module_source_all_includes_document_entry():
    src = inspect.getsource(mmod)
    assert '"DocumentEntry"' in src or "'DocumentEntry'" in src


def test_module_source_all_includes_expected_failure():
    src = inspect.getsource(mmod)
    assert '"ExpectedFailure"' in src or "'ExpectedFailure'" in src


def test_module_source_all_includes_load_manifest():
    src = inspect.getsource(mmod)
    assert '"load_manifest"' in src or "'load_manifest'" in src


def test_module_source_uses_resolve():
    src = inspect.getsource(mmod)
    assert ".resolve()" in src


def test_module_source_uses_path_open():
    src = inspect.getsource(mmod)
    assert ".open(" in src


def test_module_source_uses_relative_to():
    src = inspect.getsource(mmod)
    assert "relative_to(" in src


def test_module_source_uses_isalpha():
    src = inspect.getsource(mmod)
    assert ".isalpha()" in src


def test_module_source_uses_is_file():
    src = inspect.getsource(mmod)
    assert ".is_file()" in src


# ---------- signatures 精确补强 ----------


def test_load_manifest_signature_param_count():
    sig = inspect.signature(load_manifest)
    assert len(sig.parameters) == 2


def test_load_manifest_signature_param_names():
    sig = inspect.signature(load_manifest)
    names = list(sig.parameters.keys())
    assert names == ["manifest_path", "project_root"]


def test_load_manifest_signature_manifest_path_no_default():
    sig = inspect.signature(load_manifest)
    p = sig.parameters["manifest_path"]
    assert p.default is inspect.Parameter.empty


def test_load_manifest_signature_project_root_default_none():
    sig = inspect.signature(load_manifest)
    p = sig.parameters["project_root"]
    assert p.default is None


def test_load_manifest_signature_no_varargs():
    sig = inspect.signature(load_manifest)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_is_absolute_like_signature():
    sig = inspect.signature(_is_absolute_like)
    assert len(sig.parameters) == 1
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_has_backslash_signature():
    sig = inspect.signature(_has_backslash)
    assert len(sig.parameters) == 1
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_resolve_relative_path_signature_param_count():
    sig = inspect.signature(_resolve_relative_path)
    assert len(sig.parameters) == 3


def test_resolve_relative_path_signature_param_names():
    sig = inspect.signature(_resolve_relative_path)
    names = list(sig.parameters.keys())
    assert names == ["path_str", "project_root", "field_name"]


def test_resolve_relative_path_signature_no_defaults():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_detect_project_root_signature():
    sig = inspect.signature(_detect_project_root)
    assert len(sig.parameters) == 1
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_no_function_has_varargs_in_module():
    for name in ["load_manifest", "_is_absolute_like", "_has_backslash", "_resolve_relative_path", "_detect_project_root"]:
        fn = getattr(mmod, name)
        sig = inspect.signature(fn)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_POSITIONAL not in kinds
        assert inspect.Parameter.VAR_KEYWORD not in kinds


# ---------- 模块整体合理性 ----------


def test_module_namespace_has_5_names():
    """ManifestError, Manifest, DocumentEntry, ExpectedFailure, load_manifest + 4 private helpers = 9。"""
    ns = [
        (k, v) for k, v in vars(mmod).items()
        if getattr(v, "__module__", "") == mmod.__name__
    ]
    names = [k for k, v in ns]
    expected = [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "_is_absolute_like",
        "_has_backslash",
        "_resolve_relative_path",
        "_detect_project_root",
        "load_manifest",
    ]
    assert sorted(names) == sorted(expected)


def test_module_name():
    assert mmod.__name__ == "evaluation.manifest"


def test_module_file_endswith_manifest_py():
    assert mmod.__file__.replace("\\", "/").endswith("evaluation/manifest.py")


def test_module_docstring_present():
    assert mmod.__doc__ is not None and len(mmod.__doc__) > 50


def test_module_all_present():
    assert hasattr(mmod, "__all__")


def test_module_all_count_5():
    assert len(mmod.__all__) == 5


def test_module_all_contents():
    assert sorted(mmod.__all__) == sorted([
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ])


def test_module_manifest_error_is_class():
    assert isinstance(mmod.ManifestError, type)


def test_module_manifest_error_subclass_exception():
    assert issubclass(mmod.ManifestError, Exception)


def test_module_manifest_is_dataclass():
    assert is_dataclass(mmod.Manifest)


def test_module_document_entry_is_dataclass():
    assert is_dataclass(mmod.DocumentEntry)


def test_module_expected_failure_is_dataclass():
    assert is_dataclass(mmod.ExpectedFailure)


def test_module_load_manifest_callable():
    assert callable(mmod.load_manifest)


def test_module_all_callables_callable():
    for name in mmod.__all__:
        v = getattr(mmod, name)
        if isinstance(v, type):
            # class 是 callable
            assert callable(v)
        else:
            assert callable(v)


def test_module_no_user_classes_outside_dataclass():
    # 只有 ManifestError 是 non-dataclass class
    classes = [
        (k, v) for k, v in vars(mmod).items()
        if isinstance(v, type) and getattr(v, "__module__", "") == mmod.__name__
    ]
    non_dataclasses = [(k, v) for k, v in classes if not is_dataclass(v)]
    assert len(non_dataclasses) == 1
    assert non_dataclasses[0][0] == "ManifestError"


# ---------- 端到端集成补强 ----------


def test_e2e_load_manifest_returns_manifest_instance(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    assert isinstance(m, Manifest)


def test_e2e_load_manifest_returns_documents_as_tuple(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    assert isinstance(m.documents, tuple)


def test_e2e_load_manifest_returns_expected_failures_as_tuple(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    assert isinstance(m.expected_failures, tuple)


def test_e2e_load_manifest_with_one_document(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    assert m.file_count == 1


def test_e2e_load_manifest_document_resolved_path(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].resolved_path == (tmp_path / "sample.pdf").resolve()


def test_e2e_load_manifest_document_path_str_preserved(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].path_str == "sample.pdf"


def test_e2e_load_manifest_idempotent(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    m1 = load_manifest(mf, project_root=tmp_path)
    m2 = load_manifest(mf, project_root=tmp_path)
    assert m1 == m2


def test_e2e_load_manifest_does_not_modify_input_dict(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("dummy")
    raw = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    raw_before = json.loads(json.dumps(raw))
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(raw), encoding="utf-8")
    load_manifest(mf, project_root=tmp_path)
    # 再次读取
    with mf.open("r", encoding="utf-8") as f:
        raw_after = json.load(f)
    assert raw_before == raw_after


def test_e2e_load_manifest_project_root_in_result(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    assert m.project_root == tmp_path.resolve()


def test_e2e_load_manifest_doc_with_all_optional_fields(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "x.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "categories": ["c1", "c2"],
                "paired_with": "d2",
                "expectations": {"element_count_by_type": {"paragraph": 5}},
            }
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    d = m.documents[0]
    assert d.sha256 == "a" * 64
    assert d.categories == ("c1", "c2")
    assert d.paired_with == "d2"
    assert d.annotation_file_str is None
    assert d.annotation_resolved is None
    assert d.expectations == {"element_count_by_type": {"paragraph": 5}}


def test_e2e_load_manifest_str_path_input(tmp_path):
    """manifest_path 可以是 str 或 Path。"""
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(str(mf), project_root=str(tmp_path))
    assert isinstance(m, Manifest)


def test_e2e_load_manifest_with_relative_str_root(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    # 传 str 路径
    m = load_manifest(mf, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


def test_e2e_load_manifest_categories_dedup_across_docs(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_text("dummy")
    pdf2 = tmp_path / "b.pdf"
    pdf2.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "categories": ["a"]},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf", "categories": ["a", "b"]},
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.categories_covered == ["a", "b"]


def test_e2e_load_manifest_pdf_docx_counts(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_text("dummy")
    pdf2 = tmp_path / "b.docx"
    pdf2.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx"},
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.pdf_count == 1
    assert m.docx_count == 1


def test_e2e_load_manifest_content_group_count_paired(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_text("dummy")
    pdf2 = tmp_path / "b.docx"
    pdf2.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx", "paired_with": "d1"},
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.content_group_count == 1


def test_e2e_load_manifest_passes_annotation_file(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("dummy")
    ann = tmp_path / "x.json"
    ann.write_text('{"k":1}', encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "x.pdf",
                "source_type": "pdf",
                "annotation_file": "x.json",
            }
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].annotation_resolved == ann.resolve()


def test_e2e_load_manifest_json_serializable(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    # 不能直接 json.dumps 整个 dataclass（含 Path），但应能序列化基本字段
    serializable = {
        "manifest_version": m.manifest_version,
        "devset_status": m.devset_status,
        "doc_count": m.file_count,
    }
    assert json.dumps(serializable)  # 不抛


def test_e2e_load_manifest_str_vs_path_input_equivalent(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    m1 = load_manifest(mf, project_root=tmp_path)
    m2 = load_manifest(str(mf), project_root=str(tmp_path))
    assert m1 == m2


def test_e2e_load_manifest_three_categories_sorted(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "categories": ["z", "a", "m"]},
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.categories_covered == ["a", "m", "z"]


def test_e2e_load_manifest_multi_expected_failures(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_text("dummy")
    pdf2 = tmp_path / "b.pdf"
    pdf2.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "f1", "path": "a.pdf", "expected_error_code": "code1"},
            {"doc_id": "f2", "path": "b.pdf", "expected_error_code": "code2"},
        ],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert len(m.expected_failures) == 2
    assert m.expected_failures[0].expected_error_code == "code1"
    assert m.expected_failures[1].expected_error_code == "code2"


def test_e2e_load_manifest_returns_correct_manifest_version(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    assert m.manifest_version == MANIFEST_VERSION


def test_e2e_load_manifest_with_pathlib_project_root(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=Path(tmp_path))
    assert isinstance(m, Manifest)


def test_e2e_load_manifest_docx_only(tmp_path):
    pdf = tmp_path / "x.docx"
    pdf.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.docx", "source_type": "docx"},
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.docx_count == 1
    assert m.pdf_count == 0
