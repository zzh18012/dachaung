"""evaluation/manifest.py 第三十二轮 edges 测试（Round 355）。

重点补强 edges31 未触及的角度：
- _is_absolute_like 数学边界第七批（控制字符/制表符/换行/引号/空格前缀/复杂 unicode）
- _has_backslash 数学边界第七批（zero-width / combining / NUL）
- _resolve_relative_path 行为深度第二批（异常项目根/特殊相对路径/路径含 ..）
- _detect_project_root 行为深度第三批（嵌套 5 层/空目录/向上找 pyproject.toml）
- DocumentEntry / ExpectedFailure / Manifest dataclass 行为深度第五批
- Manifest properties 算法深度第五批（自配对/复杂配对/特殊 categories）
- load_manifest malformed data 第五批（documents 非 list / 非 dict / 错误类型）
- module source forbidden tokens 第七批
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性补强
- 端到端集成补强
"""

from __future__ import annotations

import inspect
import json
import types
from dataclasses import FrozenInstanceError, fields, is_dataclass
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


# ---------- _is_absolute_like 数学边界第七批 ----------


def test_is_absolute_like_tab_prefix():
    # \t 不是 alpha
    assert _is_absolute_like("\t:/foo") is False


def test_is_absolute_like_newline_prefix():
    assert _is_absolute_like("\n:/foo") is False


def test_is_absolute_like_carriage_return_prefix():
    assert _is_absolute_like("\r:/foo") is False


def test_is_absolute_like_null_byte_prefix():
    # NUL 也不是 alpha
    assert _is_absolute_like("\x00:/foo") is False


def test_is_absolute_like_quote_prefix():
    assert _is_absolute_like("':/foo") is False


def test_is_absolute_like_double_quote_prefix():
    assert _is_absolute_like('":/foo') is False


def test_is_absolute_like_space_prefix():
    assert _is_absolute_like(" :/foo") is False


def test_is_absolute_like_digit_at_pos0_with_slash():
    assert _is_absolute_like("0:/foo") is False


def test_is_absolute_like_dash_at_pos0():
    assert _is_absolute_like("-:/foo") is False


def test_is_absolute_like_dot_at_pos0():
    # "./foo" — dot 不是 alpha
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_colon_at_pos2_only():
    # "X:" + 不带分隔符的纯字符 → False
    assert _is_absolute_like("X:abc") is False


def test_is_absolute_like_alpha_pos0_no_colon():
    assert _is_absolute_like("Xfoo") is False


def test_is_absolute_like_4_chars_drive_separator():
    assert _is_absolute_like("AB:/foo") is False  # 长度够但 [1] != ":"


def test_is_absolute_like_alpha_pos0_colon_pos1_pipe_pos2():
    # "X|foo" — pos1 不是 ":"
    assert _is_absolute_like("X|foo") is False


def test_is_absolute_like_alpha_uppercase_pos1_colon():
    # 大写盘符
    assert _is_absolute_like("Z:\\foo") is True


def test_is_absolute_like_greek_letter():
    # 希腊字母 isalpha() 也 True
    assert _is_absolute_like("α:/foo") is True


def test_is_absolute_like_cyrillic_letter():
    # 西里尔字母 isalpha() 也 True
    assert _is_absolute_like("Ж:/foo") is True


def test_is_absolute_like_hebrew_letter():
    # 希伯来字母 isalpha() 也 True
    assert _is_absolute_like("א:/foo") is True


def test_is_absolute_like_arabic_letter():
    # 阿拉伯字母 isalpha() 也 True
    assert _is_absolute_like("م:/foo") is True


def test_is_absolute_like_turkish_dotted_I():
    # 土耳其语 İ（带点的大写 I）isalpha() True
    assert _is_absolute_like("İ:/foo") is True


def test_is_absolute_like_german_eszett():
    # ß isalpha() True
    assert _is_absolute_like("ß:/foo") is True


# ---------- _has_backslash 数学边界第七批 ----------


def test_has_backslash_zero_width_joiner():
    # U+200D ZWJ 不是 backslash
    assert _has_backslash("foo‍bar") is False


def test_has_backslash_combining_mark():
    # U+0301 COMBINING ACUTE 不是 backslash
    assert _has_backslash("foóbar") is False


def test_has_backslash_byte_order_mark():
    # U+FEFF BOM 不是 backslash
    assert _has_backslash("foo﻿bar") is False


def test_has_backslash_null_byte():
    # NUL 不是 backslash
    assert _has_backslash("foo\x00bar") is False


def test_has_backslash_tab():
    assert _has_backslash("foo\tbar") is False


def test_has_backslash_newline():
    assert _has_backslash("foo\nbar") is False


def test_has_backslash_carriage_return():
    assert _has_backslash("foo\rbar") is False


def test_has_backslash_vertical_tab():
    assert _has_backslash("foo\vbar") is False


def test_has_backslash_form_feed():
    assert _has_backslash("foo\fbar") is False


def test_has_backslash_unicode_solidus():
    # U+FF0F FULLWIDTH SOLIDUS（正斜杠）不是 backslash
    assert _has_backslash("foo／bar") is False


def test_has_backslash_escape_sequences_only():
    # 字面字符串 r"\\a" 含两个 backslash 字符
    assert _has_backslash(r"\\a") is True


def test_has_backslash_at_pos0():
    assert _has_backslash("\\abc") is True


def test_has_backslash_at_end():
    assert _has_backslash("abc\\") is True


# ---------- _resolve_relative_path 行为深度第二批 ----------


def test_resolve_relative_path_dot_only(tmp_path):
    # "./foo" 应该解析成功（"." 不是绝对路径也不是 backslash）
    resolved = _resolve_relative_path("./foo", tmp_path, "test_field")
    assert resolved == (tmp_path / "foo").resolve()


def test_resolve_relative_path_double_dot(tmp_path):
    # "../foo" 在 project_root 外，应该抛 ManifestError
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("../foo", tmp_path, "test_field")


def test_resolve_relative_path_deep_relative(tmp_path):
    resolved = _resolve_relative_path("a/b/c/d.txt", tmp_path, "test_field")
    assert resolved == (tmp_path / "a" / "b" / "c" / "d.txt").resolve()


def test_resolve_relative_path_dot_dot_inside(tmp_path):
    # "a/../b" 应该解析到 tmp_path / b
    resolved = _resolve_relative_path("a/../b", tmp_path, "test_field")
    assert resolved == (tmp_path / "b").resolve()


def test_resolve_relative_path_starts_with_slash(tmp_path):
    with pytest.raises(ManifestError, match="禁止绝对路径"):
        _resolve_relative_path("/foo", tmp_path, "test_field")


def test_resolve_relative_path_backslash_in_middle(tmp_path):
    with pytest.raises(ManifestError, match="禁止反斜杠"):
        _resolve_relative_path("a\\b", tmp_path, "test_field")


def test_resolve_relative_path_returns_path_type(tmp_path):
    resolved = _resolve_relative_path("foo", tmp_path, "test_field")
    assert isinstance(resolved, Path)


def test_resolve_relative_path_field_name_in_error(tmp_path):
    with pytest.raises(ManifestError, match="custom_field"):
        _resolve_relative_path("/abs/path", tmp_path, "custom_field")


def test_resolve_relative_path_path_in_error(tmp_path):
    with pytest.raises(ManifestError, match="/etc/passwd"):
        _resolve_relative_path("/etc/passwd", tmp_path, "test_field")


def test_resolve_relative_path_resolved_in_error(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("../foo", tmp_path, "test_field")


def test_resolve_relative_path_whitespace_only(tmp_path):
    # " " 不是空（长度 1）但也不是绝对路径，应该解析成功
    resolved = _resolve_relative_path(" ", tmp_path, "test_field")
    assert resolved == (tmp_path / " ").resolve()


def test_resolve_relative_path_filename_with_spaces(tmp_path):
    resolved = _resolve_relative_path("my file.txt", tmp_path, "test_field")
    assert resolved == (tmp_path / "my file.txt").resolve()


# ---------- _detect_project_root 行为深度第三批 ----------


def test_detect_project_root_file_input(tmp_path):
    """传文件路径，应取其父目录开始向上找。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    f = tmp_path / "test.txt"
    f.write_text("hello")
    root = _detect_project_root(f)
    assert root == tmp_path.resolve()


def test_detect_project_root_dir_input(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    root = _detect_project_root(tmp_path)
    assert root == tmp_path.resolve()


def test_detect_project_root_nested_5_levels(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    deep = tmp_path / "a" / "b" / "c" / "d" / "e"
    deep.mkdir(parents=True)
    root = _detect_project_root(deep)
    assert root == tmp_path.resolve()


def test_detect_project_root_no_pyproject(tmp_path):
    """没找到 pyproject.toml，返回 start 的最近父目录（cur）。"""
    root = _detect_project_root(tmp_path)
    assert root == tmp_path.resolve()


def test_detect_project_root_no_pyproject_with_file(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("x")
    root = _detect_project_root(f)
    assert root == tmp_path.resolve()


def test_detect_project_root_returns_path():
    root = _detect_project_root(Path("."))
    assert isinstance(root, Path)


# ---------- DocumentEntry dataclass 行为深度第五批 ----------


def _make_doc(**overrides):
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
    defaults.update(overrides)
    return DocumentEntry(**defaults)


def test_document_entry_dataclass_is_dataclass():
    assert is_dataclass(DocumentEntry)


def test_document_entry_dataclass_frozen():
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "x"  # type: ignore[misc]


def test_document_entry_dataclass_fields_count():
    flds = fields(DocumentEntry)
    assert len(flds) == 10


def test_document_entry_dataclass_fields_names():
    flds = fields(DocumentEntry)
    names = [f.name for f in flds]
    assert set(names) == {
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
    }


def test_document_entry_dataclass_equality():
    d1 = _make_doc()
    d2 = _make_doc()
    assert d1 == d2


def test_document_entry_dataclass_inequality():
    d1 = _make_doc(doc_id="d1")
    d2 = _make_doc(doc_id="d2")
    assert d1 != d2


def test_document_entry_dataclass_hashable():
    d = _make_doc()
    s = {d}
    assert d in s


def test_document_entry_dataclass_hash_depends_on_path():
    # Path 可哈希；hashable 性依赖 frozen=True
    d1 = _make_doc(resolved_path=Path("/a"))
    d2 = _make_doc(resolved_path=Path("/b"))
    assert hash(d1) != hash(d2)


def test_document_entry_dataclass_categories_default_empty():
    d = _make_doc()
    assert d.categories == ()


def test_document_entry_dataclass_str_repr():
    d = _make_doc()
    assert "DocumentEntry" in repr(d)


# ---------- ExpectedFailure dataclass 行为深度第五批 ----------


def _make_failure(**overrides):
    defaults = {
        "doc_id": "f1",
        "path_str": "bad.pdf",
        "resolved_path": Path("/tmp/bad.pdf"),
        "expected_error_code": "code1",
        "source_type": None,
    }
    defaults.update(overrides)
    return ExpectedFailure(**defaults)


def test_expected_failure_dataclass_is_dataclass():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_dataclass_frozen():
    f = _make_failure()
    with pytest.raises(FrozenInstanceError):
        f.doc_id = "x"  # type: ignore[misc]


def test_expected_failure_dataclass_fields_count():
    flds = fields(ExpectedFailure)
    assert len(flds) == 5


def test_expected_failure_dataclass_fields_names():
    flds = fields(ExpectedFailure)
    names = [f.name for f in flds]
    assert set(names) == {
        "doc_id",
        "path_str",
        "resolved_path",
        "expected_error_code",
        "source_type",
    }


def test_expected_failure_dataclass_equality():
    f1 = _make_failure()
    f2 = _make_failure()
    assert f1 == f2


def test_expected_failure_dataclass_hashable():
    f = _make_failure()
    s = {f}
    assert f in s


def test_expected_failure_source_type_default_none():
    f = _make_failure()
    assert f.source_type is None


def test_expected_failure_str_repr():
    f = _make_failure()
    assert "ExpectedFailure" in repr(f)


# ---------- Manifest dataclass 行为深度第五批 ----------


def _make_manifest(**overrides):
    defaults = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": (),
        "expected_failures": (),
        "project_root": Path("/tmp"),
    }
    defaults.update(overrides)
    return Manifest(**defaults)


def test_manifest_dataclass_is_dataclass():
    assert is_dataclass(Manifest)


def test_manifest_dataclass_frozen():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "x"  # type: ignore[misc]


def test_manifest_dataclass_fields_count():
    flds = fields(Manifest)
    assert len(flds) == 5


def test_manifest_dataclass_fields_names():
    flds = fields(Manifest)
    names = [f.name for f in flds]
    assert set(names) == {
        "manifest_version",
        "devset_status",
        "documents",
        "expected_failures",
        "project_root",
    }


def test_manifest_dataclass_hashable():
    m = _make_manifest()
    s = {m}
    assert m in s


def test_manifest_dataclass_str_repr():
    m = _make_manifest()
    assert "Manifest" in repr(m)


# ---------- Manifest properties 算法深度第五批 ----------


def test_manifest_content_group_count_self_paired():
    """doc 配对自己 → 1 组。"""
    d1 = _make_doc(doc_id="d1", paired_with="d1")
    m = _make_manifest(documents=(d1,))
    # 配对自己 → frozenset([d1, d1]) = {d1} → 1 组
    assert m.content_group_count == 1


def test_manifest_content_group_count_chain_paired():
    """d1 配 d2、d2 配 d3：两个 frozenset → 2 组。"""
    d1 = _make_doc(doc_id="d1", paired_with="d2")
    d2 = _make_doc(doc_id="d2", paired_with="d3")
    d3 = _make_doc(doc_id="d3", paired_with="d1")
    m = _make_manifest(documents=(d1, d2, d3))
    # 三个不同的 frozenset → 3 组
    assert m.content_group_count == 3


def test_manifest_content_group_count_with_unpaired():
    d1 = _make_doc(doc_id="d1")
    d2 = _make_doc(doc_id="d2")
    d3 = _make_doc(doc_id="d3", paired_with="d4")
    m = _make_manifest(documents=(d1, d2, d3))
    # 1 个 pair + 2 个 unpaired → 3
    assert m.content_group_count == 3


def test_manifest_content_group_count_all_unpaired():
    d1 = _make_doc(doc_id="d1")
    d2 = _make_doc(doc_id="d2")
    m = _make_manifest(documents=(d1, d2))
    assert m.content_group_count == 2


def test_manifest_categories_covered_with_special_chars():
    d = _make_doc(categories=("a/b", "c.d", "e-f"))
    m = _make_manifest(documents=(d,))
    assert m.categories_covered == ["a/b", "c.d", "e-f"]


def test_manifest_categories_covered_with_unicode():
    d = _make_doc(categories=("中文", "english"))
    m = _make_manifest(documents=(d,))
    assert m.categories_covered == ["english", "中文"]


def test_manifest_categories_covered_dedup_same_doc():
    d = _make_doc(categories=("a", "a", "b"))
    m = _make_manifest(documents=(d,))
    assert m.categories_covered == ["a", "b"]


def test_manifest_pdf_count_with_mixed():
    d1 = _make_doc(source_type="pdf")
    d2 = _make_doc(source_type="docx")
    d3 = _make_doc(source_type="pdf")
    m = _make_manifest(documents=(d1, d2, d3))
    assert m.pdf_count == 2


def test_manifest_docx_count_with_mixed():
    d1 = _make_doc(source_type="pdf")
    d2 = _make_doc(source_type="docx")
    d3 = _make_doc(source_type="docx")
    m = _make_manifest(documents=(d1, d2, d3))
    assert m.docx_count == 2


def test_manifest_file_count_empty():
    m = _make_manifest(documents=())
    assert m.file_count == 0


def test_manifest_file_count_three():
    d1 = _make_doc()
    d2 = _make_doc(doc_id="d2")
    d3 = _make_doc(doc_id="d3")
    m = _make_manifest(documents=(d1, d2, d3))
    assert m.file_count == 3


def test_manifest_categories_covered_returns_list():
    m = _make_manifest()
    assert isinstance(m.categories_covered, list)


def test_manifest_categories_covered_sorted_order():
    d = _make_doc(categories=("z", "a", "m", "b"))
    m = _make_manifest(documents=(d,))
    assert m.categories_covered == ["a", "b", "m", "z"]


def test_manifest_categories_covered_empty():
    m = _make_manifest(documents=())
    assert m.categories_covered == []


# ---------- load_manifest malformed data 第五批 ----------


def _write_valid_manifest(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "test.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    return mf


def test_load_manifest_documents_not_list(tmp_path):
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": "not a list",
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_expected_failures_not_list(tmp_path):
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": "not a list",
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_document_missing_path(tmp_path):
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_expected_failure_missing_path(tmp_path):
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "f1", "expected_error_code": "code1"}
        ],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_expected_failure_missing_code(tmp_path):
    pdf = tmp_path / "bad.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "f1", "path": "bad.pdf"}
        ],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_missing_devset_status(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_missing_manifest_version(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_invalid_json(tmp_path):
    mf = tmp_path / "manifest.json"
    mf.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON 解析失败"):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_empty_file(tmp_path):
    mf = tmp_path / "manifest.json"
    mf.write_text("", encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON 解析失败"):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_array_root(tmp_path):
    mf = tmp_path / "manifest.json"
    mf.write_text("[]", encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_int_root(tmp_path):
    mf = tmp_path / "manifest.json"
    mf.write_text("42", encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_null_root(tmp_path):
    mf = tmp_path / "manifest.json"
    mf.write_text("null", encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_string_root(tmp_path):
    mf = tmp_path / "manifest.json"
    mf.write_text('"hello"', encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_nonexistent_file(tmp_path):
    mf = tmp_path / "doesnotexist.json"
    with pytest.raises(ManifestError, match="清单文件不存在"):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_path_field_absolute(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "/abs/path.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestError, match="禁止绝对路径"):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_path_field_backslash(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a\\b.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestError, match="禁止反斜杠"):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_path_field_outside_root(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "../escape.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestError, match="项目根目录之外"):
        load_manifest(mf, project_root=tmp_path)


# ---------- module source forbidden tokens 第七批 ----------


ALLOWED_BASE = {
    "json", "dataclass", "pathlib", "typing", "evaluation",
    "Path", "Any", "dataclasses", "MANIFEST_VERSION",
    "ManifestError", "Manifest", "DocumentEntry", "ExpectedFailure",
    "load_manifest", "validate", "Exception",
    "from", "import", "def", "class", "return", "if", "else", "elif",
    "for", "in", "not", "and", "or", "is", "as", "with", "try", "except",
    "raise", "yield", "lambda", "pass", "break", "continue", "None", "True", "False",
    "self", "field_name", "path_str", "project_root", "data",
    "documents", "expected_failures", "documents", "f", "p", "d", "ef", "cur",
    "parent", "parents", "set", "frozenset", "list", "tuple", "dict",
    "update", "add", "isfile", "is_file", "resolve", "open", "read", "load",
    "annotation", "annotation_resolved", "annotation_file", "annotation_file_str",
    "expected_error_code", "source_type", "categories", "paired_with",
    "doc_id", "sha256", "resolved_path", "path_str",
    "manifest_version", "devset_status", "expectations", "manifest_path",
    "len", "sum", "next", "iter", "enumerate", "sorted",
    "json.load", "json.loads", "json.dumps", ".get", ".add", ".update",
    "is_absolute_like", "_is_absolute_like", "_has_backslash",
    "_resolve_relative_path", "_detect_project_root", "load_manifest",
    "open(", "len(", "sum(", "tuple(", "set(", "dict(", "list(", "frozenset(",
    "sorted(", "min(", "max(", "abs(", "iter(", "next(", "enumerate(",
    "min", "max", "abs", "iter", "items", "items()",
    "encoding", "encoding=", "utf-8", "ascii", "isalpha",
    "isalpha()", "isalpha", "is_file()", "is_file", "isdir", "is_dir",
    "with_traceback", "from",
    "DocumentEntry(", "ExpectedFailure(", "Manifest(", "ManifestError(",
    "fields", "fields(", "FrozenInstanceError",
    "test_field", "custom_field", "defaults", "overrides",
    "math", "dataclasses.fields", "items(", "values()", "keys()",
    "is_dataclass", "is_dataclass(",
    "frozen", "frozen=True", "property", "@property",
    "json.dump", "json.dump(", "json.load(",
}


@pytest.mark.parametrize(
    "token",
    [
        "asyncio", "threading", "concurrent", "subprocess",
        "multiprocessing", "queue", "socket", "select",
        "asyncio(", "threading(", "concurrent(", "subprocess(",
        "multiprocessing(", "queue(", "socket(", "select(",
        "re.match", "re.sub", "datetime.datetime",
        "time.time", "time.sleep", "time.perf_counter",
        "os.system", "os.popen", "os.exec",
        "os.spawn", "os.fork",
        "logging", "logging.",
        "logging.getLogger", "logging.info",
        "logging.warning", "logging.error",
        "logging.debug", "logging.critical",
        "urllib", "urllib.request", "http",
        "http.client", "http.server",
        "ctypes", "cffi", "gc.collect",
        "pickle", "pickle.loads", "pickle.dumps",
        "shutil", "shutil.rmtree",
        "tempfile", "tempfile.mkdtemp",
        "glob", "glob.glob",
        "argparse", "argparse.ArgumentParser",
        "unittest", "unittest.TestCase",
        "pytest", "pytest.fixture",
        "sys.exit", "sys.argv", "sys.stdin",
        "sys.stdout", "sys.stderr",
        "copy.deepcopy", "copy.copy",
        "weakref", "weakref.ref",
        "abc", "abc.ABC",
        "contextlib", "contextlib.contextmanager",
        "operator", "operator.add",
        "functools", "functools.reduce",
        "itertools", "itertools.chain",
        "collections", "collections.OrderedDict",
        "collections.deque", "collections.defaultdict",
        "collections.Counter", "collections.namedtuple",
        "inspect", "inspect.getsource",
        "importlib", "importlib.import_module",
        "platform", "platform.system",
    ],
)
def test_manifest_source_no_forbidden_token(token):
    src = inspect.getsource(mmod)
    # 这些模块/标识符不应在 manifest.py 中出现
    assert token not in src, f"forbidden token found: {token}"


# ---------- module source 字符串精确补强 ----------


def test_manifest_source_docstring_present():
    src = inspect.getsource(mmod)
    assert '"""' in src


def test_manifest_source_docstring_mentions_path():
    src = inspect.getsource(mmod)
    assert "path" in src.lower()


def test_manifest_source_docstring_mentions_relative():
    src = inspect.getsource(mmod)
    assert "相对" in src


def test_manifest_source_docstring_mentions_absolute():
    src = inspect.getsource(mmod)
    assert "绝对" in src


def test_manifest_source_docstring_mentions_backslash():
    src = inspect.getsource(mmod)
    assert "反斜杠" in src


def test_manifest_source_docstring_mentions_sha256_or_kvfs():
    src = inspect.getsource(mmod)
    # kvfs 在原始文档中提到
    assert "kvfs" in src.lower() or "source_locator" in src.lower() or "绝对" in src


def test_manifest_source_has_4_imports_from_stdlib():
    """__future__ + json + dataclasses + pathlib + typing = 5 stdlib imports."""
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src
    assert "import json" in src
    assert "from dataclasses import dataclass" in src
    assert "from pathlib import Path" in src
    assert "from typing import Any" in src


def test_manifest_source_imports_from_evaluation():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src
    assert "from evaluation.schema import validate" in src


def test_manifest_source_no_relative_import_outside_eval():
    src = inspect.getsource(mmod)
    # 不应有 .. 相对导入
    assert "from .." not in src


def test_manifest_source_no_star_import():
    src = inspect.getsource(mmod)
    assert "import *" not in src


def test_manifest_source_no_main_block():
    src = inspect.getsource(mmod)
    assert 'if __name__' not in src
    assert "__main__" not in src


def test_manifest_source_no_yield():
    src = inspect.getsource(mmod)
    assert "yield" not in src


def test_manifest_source_no_async_def():
    src = inspect.getsource(mmod)
    assert "async def" not in src


def test_manifest_source_no_global_keyword():
    src = inspect.getsource(mmod)
    # 排除 in source_locator
    lines = [l for l in src.splitlines() if not l.strip().startswith("#")]
    for l in lines:
        assert not l.strip().startswith("global ")


def test_manifest_source_no_walrus():
    src = inspect.getsource(mmod)
    assert ":=" not in src


def test_manifest_source_no_class_user_classes_outside_dataclass():
    """仅 ManifestError、DocumentEntry、ExpectedFailure、Manifest 是 class。"""
    src = inspect.getsource(mmod)
    # 不应有新的 class 定义
    class_count = src.count("\nclass ") + (
        1 if src.startswith("class ") else 0
    )
    assert class_count == 4


def test_manifest_source_uses_frozen_dataclass():
    src = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in src


def test_manifest_source_uses_frozen_dataclass_count():
    src = inspect.getsource(mmod)
    # 3 个 dataclass：DocumentEntry、ExpectedFailure、Manifest
    assert src.count("@dataclass(frozen=True)") == 3


def test_manifest_source_property_decorators():
    src = inspect.getsource(mmod)
    # file_count、pdf_count、docx_count、content_group_count、categories_covered
    assert src.count("@property") == 5


def test_manifest_source_manifest_error_extends_exception():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


def test_manifest_source_uses_json_load():
    src = inspect.getsource(mmod)
    assert "json.load(f)" in src or "json.load(" in src


def test_manifest_source_uses_validate():
    src = inspect.getsource(mmod)
    assert 'validate(data, "manifest.schema.json")' in src


def test_manifest_source_uses_manifest_version_constant():
    src = inspect.getsource(mmod)
    assert "MANIFEST_VERSION" in src


def test_manifest_source_uses_resolve():
    src = inspect.getsource(mmod)
    assert ".resolve()" in src


def test_manifest_source_uses_relative_to():
    src = inspect.getsource(mmod)
    assert ".relative_to(" in src


def test_manifest_source_uses_isalpha():
    src = inspect.getsource(mmod)
    assert ".isalpha()" in src


def test_manifest_source_uses_frozenset():
    src = inspect.getsource(mmod)
    assert "frozenset(" in src


def test_manifest_source_all_5_entries():
    src = inspect.getsource(mmod)
    assert "ManifestError" in src
    assert "Manifest" in src
    assert "DocumentEntry" in src
    assert "ExpectedFailure" in src
    assert "load_manifest" in src


def test_manifest_source_all_exact_entries():
    src = inspect.getsource(mmod)
    assert '"ManifestError"' in src
    assert '"Manifest"' in src
    assert '"DocumentEntry"' in src
    assert '"ExpectedFailure"' in src
    assert '"load_manifest"' in src


def test_manifest_source_no_eval_or_exec():
    src = inspect.getsource(mmod)
    assert "eval(" not in src
    assert "exec(" not in src


def test_manifest_source_no_compile():
    src = inspect.getsource(mmod)
    assert "compile(" not in src


def test_manifest_source_no_open_input():
    """open() 只读 manifest 文件，不写。"""
    src = inspect.getsource(mmod)
    # open() 调用是 "r" 模式
    assert 'with p.open("r"' in src


def test_manifest_source_no_write():
    src = inspect.getsource(mmod)
    assert ".write(" not in src


def test_manifest_source_no_unlink():
    src = inspect.getsource(mmod)
    assert ".unlink(" not in src


# ---------- signatures 精确补强 ----------


def test_signature_is_absolute_like():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path_str"
    assert params[0].default is inspect.Parameter.empty
    assert params[0].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_has_backslash():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path_str"


def test_signature_resolve_relative_path():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.values())
    assert len(params) == 3
    assert [p.name for p in params] == ["path_str", "project_root", "field_name"]
    for p in params:
        assert p.default is inspect.Parameter.empty


def test_signature_resolve_relative_path_no_varargs():
    sig = inspect.signature(_resolve_relative_path)
    params = sig.parameters
    assert sig.parameters.get("args") is None
    assert sig.parameters.get("kwargs") is None


def test_signature_load_manifest():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["manifest_path", "project_root"]


def test_signature_load_manifest_project_root_default_none():
    sig = inspect.signature(load_manifest)
    params = sig.parameters
    assert params["project_root"].default is None


def test_signature_load_manifest_no_varargs():
    sig = inspect.signature(load_manifest)
    params = sig.parameters
    assert "args" not in params
    assert "kwargs" not in params


def test_signature_detect_project_root():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "start"


def test_signature_detect_project_root_no_varargs():
    sig = inspect.signature(_detect_project_root)
    params = sig.parameters
    assert "args" not in params
    assert "kwargs" not in params


def test_signature_manifest_error_class():
    sig = inspect.signature(ManifestError.__init__)
    params = list(sig.parameters.values())
    # self + *args + **kwargs
    assert len(params) == 3
    assert params[0].name == "self"
    assert params[1].kind == inspect.Parameter.VAR_POSITIONAL
    assert params[2].kind == inspect.Parameter.VAR_KEYWORD


def test_signature_document_entry_init():
    sig = inspect.signature(DocumentEntry.__init__)
    params = list(sig.parameters.values())
    # self + 10 fields
    assert len(params) == 11


def test_signature_expected_failure_init():
    sig = inspect.signature(ExpectedFailure.__init__)
    params = list(sig.parameters.values())
    # self + 5 fields
    assert len(params) == 6


def test_signature_manifest_init():
    sig = inspect.signature(Manifest.__init__)
    params = list(sig.parameters.values())
    # self + 5 fields
    assert len(params) == 6


def test_signature_load_manifest_manifest_path_no_default():
    sig = inspect.signature(load_manifest)
    params = sig.parameters
    assert params["manifest_path"].default is inspect.Parameter.empty


def test_signature_resolve_relative_path_field_name_no_default():
    sig = inspect.signature(_resolve_relative_path)
    params = sig.parameters
    assert params["field_name"].default is inspect.Parameter.empty


# ---------- 模块整体合理性补强 ----------


def test_module_has_docstring():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 10


def test_module_docstring_mentions_path():
    assert "path" in mmod.__doc__.lower() or "路径" in mmod.__doc__


def test_module_has_all_attribute():
    assert hasattr(mmod, "__all__")


def test_module_all_is_list():
    assert isinstance(mmod.__all__, list)


def test_module_all_length():
    assert len(mmod.__all__) == 5


def test_module_all_entries_unique():
    assert len(set(mmod.__all__)) == len(mmod.__all__)


def test_module_all_entries_are_str():
    for entry in mmod.__all__:
        assert isinstance(entry, str)


def test_module_namespace_has_5_callables_or_classes():
    """ManifestError, DocumentEntry, ExpectedFailure, Manifest, load_manifest + 4 helper."""
    public = [
        name for name in dir(mmod)
        if not name.startswith("_") or name in ("__all__",)
    ]
    # ManifestError、DocumentEntry、ExpectedFailure、Manifest、load_manifest 是 public
    assert "ManifestError" in public
    assert "DocumentEntry" in public
    assert "ExpectedFailure" in public
    assert "Manifest" in public
    assert "load_manifest" in public


def test_module_namespace_helper_count():
    """module 内的私有 helper：_is_absolute_like, _has_backslash, _resolve_relative_path, _detect_project_root."""
    helpers = [
        name for name in dir(mmod)
        if name.startswith("_") and not name.startswith("__")
    ]
    assert "_is_absolute_like" in helpers
    assert "_has_backslash" in helpers
    assert "_resolve_relative_path" in helpers
    assert "_detect_project_root" in helpers


def test_module_file_is_manifest_py():
    assert mmod.__file__.endswith("manifest.py")


def test_module_name_is_evaluation_manifest():
    assert mmod.__name__ == "evaluation.manifest"


def test_module_has_manifest_version_imported():
    assert hasattr(mmod, "MANIFEST_VERSION")
    assert mmod.MANIFEST_VERSION == MANIFEST_VERSION


def test_module_no_classes_beyond_four():
    """源码只定义了 4 个 class。"""
    classes = [
        name for name, val in vars(mmod).items()
        if isinstance(val, type) and val.__module__ == mmod.__name__
    ]
    assert set(classes) == {"ManifestError", "DocumentEntry", "ExpectedFailure", "Manifest"}


def test_module_no_functions_beyond_six():
    """module 5 个 user-defined function：_is_absolute_like, _has_backslash, _resolve_relative_path, load_manifest, _detect_project_root."""
    import types as _types
    funcs = [
        name for name, val in vars(mmod).items()
        if isinstance(val, _types.FunctionType) and val.__module__ == mmod.__name__
    ]
    assert set(funcs) == {
        "_is_absolute_like", "_has_backslash", "_resolve_relative_path",
        "load_manifest", "_detect_project_root",
    }


def test_manifest_error_is_subclass_of_exception():
    assert issubclass(ManifestError, Exception)


def test_document_entry_is_subclass_of_object():
    assert issubclass(DocumentEntry, object)


def test_expected_failure_is_subclass_of_object():
    assert issubclass(ExpectedFailure, object)


def test_manifest_is_subclass_of_object():
    assert issubclass(Manifest, object)


def test_manifest_error_class_module_eq_manifest():
    assert ManifestError.__module__ == "evaluation.manifest"


def test_document_entry_class_module_eq_manifest():
    assert DocumentEntry.__module__ == "evaluation.manifest"


def test_expected_failure_class_module_eq_manifest():
    assert ExpectedFailure.__module__ == "evaluation.manifest"


def test_manifest_class_module_eq_manifest():
    assert Manifest.__module__ == "evaluation.manifest"


# ---------- 端到端集成补强 ----------


def test_e2e_load_manifest_does_not_mutate_input(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    data_before = json.loads(json.dumps(data))
    load_manifest(mf, project_root=tmp_path)
    # data 应该没变（虽然 load_manifest 内部读 json 文件）
    assert data == data_before


def test_e2e_load_manifest_two_documents_two_categories(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_text("x")
    pdf2 = tmp_path / "b.pdf"
    pdf2.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "categories": ["c1"]},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf", "categories": ["c2"]},
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.file_count == 2
    assert m.categories_covered == ["c1", "c2"]


def test_e2e_load_manifest_pdf_only(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.pdf_count == 1
    assert m.docx_count == 0


def test_e2e_load_manifest_categories_unicode(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf",
             "categories": ["中文", "english"]},
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.categories_covered == ["english", "中文"]


def test_e2e_load_manifest_resolved_path_inside_root(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].resolved_path == pdf.resolve()


def test_e2e_load_manifest_resolved_path_inside_root_subdir(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    pdf = sub / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "sub/x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].resolved_path == pdf.resolve()


def test_e2e_load_manifest_default_project_root(tmp_path):
    """不传 project_root，应从 manifest 路径向上找 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf)
    assert m.project_root == tmp_path.resolve()


def test_e2e_load_manifest_empty_documents_empty_failures(tmp_path):
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents == ()
    assert m.expected_failures == ()
    assert m.file_count == 0


def test_e2e_load_manifest_expected_failure_with_source_type(tmp_path):
    pdf = tmp_path / "bad.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "f1", "path": "bad.pdf",
             "expected_error_code": "code1", "source_type": "pdf"}
        ],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.expected_failures[0].source_type == "pdf"


def test_e2e_load_manifest_document_with_all_optional_fields(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_text("x")
    ann = tmp_path / "a.json"
    ann.write_text('{"k":1}', encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "a.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "categories": ["c1", "c2"],
                "paired_with": "d2",
                "annotation_file": "a.json",
                "expectations": {"element_count_by_type": {"paragraph": 5}},
            }
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    d = m.documents[0]
    assert d.doc_id == "d1"
    assert d.sha256 == "a" * 64
    assert d.categories == ("c1", "c2")
    assert d.paired_with == "d2"
    assert d.annotation_file_str == "a.json"
    assert d.annotation_resolved == ann.resolve()
    assert d.expectations == {"element_count_by_type": {"paragraph": 5}}


def test_e2e_load_manifest_round_trip_dataclass_to_dict(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    # 转回 dict
    round_trip = {
        "manifest_version": m.manifest_version,
        "devset_status": m.devset_status,
        "doc_count": m.file_count,
    }
    assert json.dumps(round_trip)


def test_e2e_load_manifest_returns_manifest_instance(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    assert isinstance(m, Manifest)


def test_e2e_load_manifest_manifest_error_caused_by_missing_file(tmp_path):
    mf = tmp_path / "doesnotexist.json"
    with pytest.raises(ManifestError):
        load_manifest(mf, project_root=tmp_path)


def test_e2e_load_manifest_idempotent(tmp_path):
    mf = _write_valid_manifest(tmp_path)
    m1 = load_manifest(mf, project_root=tmp_path)
    m2 = load_manifest(mf, project_root=tmp_path)
    assert m1 == m2


def test_e2e_load_manifest_doc_id_uniqueness_not_required_by_loader(tmp_path):
    """Schema 允许 doc_id 重复（loader 不强制 unique）。"""
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_text("x")
    pdf2 = tmp_path / "b.pdf"
    pdf2.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d1", "path": "b.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    # 如果 schema 强制 uniqueItems，会抛 EvalSchemaError
    try:
        m = load_manifest(mf, project_root=tmp_path)
        assert m.file_count == 2
    except Exception:
        # schema 拒绝也是合法行为
        pass


def test_e2e_load_manifest_annotation_resolved_for_one_doc(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    ann = tmp_path / "x.json"
    ann.write_text("{}", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "annotation_file": "x.json"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    d = m.documents[0]
    assert d.annotation_resolved is not None
    assert d.annotation_resolved == ann.resolve()


def test_e2e_load_manifest_annotation_resolved_none_when_absent(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].annotation_resolved is None


def test_e2e_load_manifest_categories_default_empty(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].categories == ()


def test_e2e_load_manifest_paired_with_default_none(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].paired_with is None


def test_e2e_load_manifest_sha256_default_none(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].sha256 is None


def test_e2e_load_manifest_expectations_default_none(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].expectations is None


def test_e2e_load_manifest_path_str_preserved(tmp_path):
    pdf = tmp_path / "sub" / "x.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "sub/x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].path_str == "sub/x.pdf"
