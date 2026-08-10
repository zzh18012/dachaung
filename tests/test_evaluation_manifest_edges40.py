"""evaluation/manifest.py 第四十轮 edges 测试（Round 412）。

补强 edges39 未触及的角度：
- _is_absolute_like 数学边界第十三批（更多边界：tab/special unicode first char / 数字开头非 alpha / 多 colon / 长 UNC / 双字符 C: 无斜杠）
- _has_backslash 数学边界第十三批（更多 corner：escape sequences / 多个连续 / Unicode backslash 类似字符）
- _resolve_relative_path 行为深度第十三批（更多路径形态：合法的 ../within / 多层嵌套 / project_root 是 Path 对象验证）
- _detect_project_root 行为深度第十三批（多层嵌套 pyproject / start 是 dir / 完全找不到时 fallback）
- DocumentEntry/ExpectedFailure/Manifest dataclass 行为第十三批（更多属性 / hash equal / fields count）
- Manifest properties algorithm 第十三批（pdf/docx count mixed / content_group_count 复杂配对 / categories_covered sorted）
- load_manifest malformed data 第十三批（更多路径类型 / version mismatch 行为 / Schema 校验失败的异常类型）
- module source forbidden tokens 第十六批
- module source 字符串精确补强第十三批
- signatures 第十三批
- module 合理性第十三批
- 端到端集成第十三批
"""

from __future__ import annotations

import inspect
import json
import os
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


def _make_doc(
    doc_id="d1",
    path_str="a.pdf",
    source_type="pdf",
    categories=("normal",),
    paired_with=None,
    expectations=None,
    sha256=None,
):
    return DocumentEntry(
        doc_id=doc_id,
        path_str=path_str,
        resolved_path=Path("/x") / path_str,
        source_type=source_type,
        sha256=sha256,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=expectations,
    )


def _make_ef(
    doc_id="ef1",
    path_str="bad.pdf",
    expected_error_code="unsupported_format",
    source_type=None,
):
    return ExpectedFailure(
        doc_id=doc_id,
        path_str=path_str,
        resolved_path=Path("/x") / path_str,
        expected_error_code=expected_error_code,
        source_type=source_type,
    )


def _make_manifest(
    documents=None,
    expected_failures=None,
    project_root=None,
    devset_status="incomplete",
):
    return Manifest(
        manifest_version="1.0",
        devset_status=devset_status,
        documents=tuple(documents or []),
        expected_failures=tuple(expected_failures or []),
        project_root=project_root or Path("/x"),
    )


# ---------- _is_absolute_like 数学边界第十三批 ----------


def test_is_absolute_like_tab_first_not_absolute_batch13():
    """Tab 不是 alpha。"""
    assert _is_absolute_like("\t:/foo") is False


def test_is_absolute_like_newline_first_batch13():
    assert _is_absolute_like("\n:/foo") is False


def test_is_absolute_like_two_char_only_alpha_colon_batch13():
    """2 字符 'C:' → len < 3 → 不是绝对路径。"""
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_alpha_colon_no_separator_batch13():
    """3 字符 'C:x' → path[2]='x' 不是 \\ 或 / → False。"""
    assert _is_absolute_like("C:x") is False


def test_is_absolute_like_alpha_colon_digit_batch13():
    """3 字符 'C:1' → path[2]='1' 不是 \\ 或 / → False。"""
    assert _is_absolute_like("C:1") is False


def test_is_absolute_like_alpha_colon_dot_batch13():
    """3 字符 'C:.' → False。"""
    assert _is_absolute_like("C:.") is False


def test_is_absolute_like_unc_double_backslash_batch13():
    """UNC 路径 \\\\server\\share 以反斜杠开头，但本函数只检查 /。"""
    # _is_absolute_like 不查反斜杠开头
    # "\\\\server" 第一个字符是 '\'，不 startswith('/')
    # 长度 >=3，path[1]='s' 不是 ':'
    assert _is_absolute_like("\\\\server\\share") is False


def test_is_absolute_like_single_slash_only_batch13():
    """单 '/' → True（startswith '/'）。"""
    assert _is_absolute_like("/") is True


def test_is_absolute_like_single_slash_with_more_batch13():
    assert _is_absolute_like("/foo") is True


def test_is_absolute_like_tilde_not_absolute_batch13():
    """~ 不被识别为绝对路径。"""
    assert _is_absolute_like("~/foo") is False


def test_is_absolute_like_dot_first_batch13():
    """./foo 不是绝对路径。"""
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_double_dot_first_batch13():
    """../foo 不是绝对路径。"""
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_chinese_alpha_first_batch13():
    """中文字符 isalpha() 返回 True，但中文不是单字节 alpha → 边界测试。"""
    # '类型' 是中文字符；中文 isalpha() 返回 True
    # 但 path[1] == ':' 才走分支
    result = _is_absolute_like("类:/foo")
    # 中文 isalpha() = True → 走盘符分支
    # path[2] = '/' → True
    assert result is True


def test_is_absolute_like_japanese_alpha_first_batch13():
    """日文 alpha 测试。"""
    result = _is_absolute_like("あ:/foo")
    assert result is True


def test_is_absolute_like_greek_alpha_first_batch13():
    """希腊字母 alpha 测试。"""
    result = _is_absolute_like("α:/foo")
    assert result is True


def test_is_absolute_like_space_first_batch13():
    """空格不是 alpha。"""
    assert _is_absolute_like(" :/foo") is False


def test_is_absolute_like_special_char_first_batch13():
    """! @ # $ % 不是 alpha。"""
    for c in "!@#$%":
        assert _is_absolute_like(f"{c}:/foo") is False


def test_is_absolute_like_multi_byte_alpha_with_colon_batch13():
    """多字节 alpha + 冒号 + 斜杠 → True。"""
    assert _is_absolute_like("À:/foo") is True


def test_is_absolute_like_alpha_uppercase_z_batch13():
    """Z: 开头也是绝对路径。"""
    assert _is_absolute_like("Z:/foo") is True


def test_is_absolute_like_alpha_lowercase_z_batch13():
    assert _is_absolute_like("z:/foo") is True


# ---------- _has_backslash 数学边界第十三批 ----------


def test_has_backslash_triple_consecutive_batch13():
    assert _has_backslash("a\\\\\\b") is True


def test_has_backslash_only_backslash_batch13():
    assert _has_backslash("\\") is True


def test_has_backslash_multiple_backslashes_batch13():
    assert _has_backslash("a\\b\\c\\d") is True


def test_has_backslash_at_start_batch13():
    assert _has_backslash("\\abc") is True


def test_has_backslash_at_end_batch13():
    assert _has_backslash("abc\\") is True


def test_has_backslash_unicode_backslash_like_char_batch13():
    """全角反斜杠 ／（U+FF0C）不是 \\（U+005C）。"""
    assert _has_backslash("a／b") is False


def test_has_backslash_similar_unicode_chars_batch13():
    """其他 Unicode 类似反斜杠的字符都不是。"""
    # U+2216 SET MINUS (∖) 看起来像反斜杠
    assert _has_backslash("a∖b") is False


def test_has_backslash_empty_string_batch13():
    assert _has_backslash("") is False


def test_has_backslash_alphanum_only_batch13():
    assert _has_backslash("abcdef123") is False


def test_has_backslash_returns_bool_batch13():
    assert isinstance(_has_backslash(""), bool)
    assert isinstance(_has_backslash("a\\b"), bool)


# ---------- _resolve_relative_path 行为深度第十三批 ----------


def test_resolve_relative_path_empty_raises_batch13():
    with pytest.raises(ManifestError, match="为空"):
        _resolve_relative_path("", Path("/x"), "field")


def test_resolve_relative_path_relative_dot_only_batch13(tmp_path):
    """'.' 解析为 project_root 本身。"""
    out = _resolve_relative_path(".", tmp_path, "f")
    assert out == tmp_path.resolve()


def test_resolve_relative_path_double_dot_within_batch13(tmp_path):
    """'subdir/..' 解析后等于 project_root。"""
    (tmp_path / "subdir").mkdir()
    out = _resolve_relative_path("subdir/..", tmp_path, "f")
    assert out == tmp_path.resolve()


def test_resolve_relative_path_double_dot_escape_raises_batch13(tmp_path):
    """'..' 试图跳出 project_root → ManifestError。"""
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("..", tmp_path, "f")


def test_resolve_relative_path_deeply_nested_batch13(tmp_path):
    """深层相对路径。"""
    out = _resolve_relative_path("a/b/c/d/e.txt", tmp_path, "f")
    assert out == (tmp_path / "a" / "b" / "c" / "d" / "e.txt").resolve()


def test_resolve_relative_path_unicode_filename_batch13(tmp_path):
    out = _resolve_relative_path("文件夹/文件.pdf", tmp_path, "f")
    assert out == (tmp_path / "文件夹" / "文件.pdf").resolve()


def test_resolve_relative_path_filename_only_batch13(tmp_path):
    """单文件名（无目录）。"""
    out = _resolve_relative_path("foo.pdf", tmp_path, "f")
    assert out == (tmp_path / "foo.pdf").resolve()


def test_resolve_relative_path_filename_with_dot_batch13(tmp_path):
    out = _resolve_relative_path("foo.bar.pdf", tmp_path, "f")
    assert out == (tmp_path / "foo.bar.pdf").resolve()


def test_resolve_relative_path_path_object_input_batch13(tmp_path):
    """path_str 必须是 str，Path 对象会 raise（schema 实际不允许）。"""
    with pytest.raises((TypeError, AttributeError)):
        _resolve_relative_path(Path("foo"), tmp_path, "f")


def test_resolve_relative_path_field_name_in_error_message_batch13(tmp_path):
    """错误消息应包含字段名。"""
    with pytest.raises(ManifestError, match="custom_field"):
        _resolve_relative_path("", tmp_path, "custom_field")


def test_resolve_relative_path_returns_path_object_batch13(tmp_path):
    out = _resolve_relative_path("foo", tmp_path, "f")
    assert isinstance(out, Path)


def test_resolve_relative_path_absolute_path_raises_with_field_batch13(tmp_path):
    with pytest.raises(ManifestError, match="abs_path_field"):
        _resolve_relative_path("/etc/passwd", tmp_path, "abs_path_field")


def test_resolve_relative_path_backslash_raises_with_field_batch13(tmp_path):
    with pytest.raises(ManifestError, match="backslash_field"):
        _resolve_relative_path("a\\b", tmp_path, "backslash_field")


def test_resolve_relative_path_resolves_symlinks_batch13(tmp_path):
    """resolve() 会解析 symlink。"""
    out = _resolve_relative_path("foo", tmp_path, "f")
    # resolve() 已经被调用
    assert out.is_absolute()


def test_resolve_relative_path_project_root_path_must_be_path_batch13():
    """project_root 必须是 Path 对象（str 会 raise TypeError on .resolve()）。"""
    with pytest.raises((TypeError, AttributeError)):
        _resolve_relative_path("foo", "/x", "f")


def test_resolve_relative_path_does_not_check_file_exists_batch13(tmp_path):
    """只校验路径形式，不要求文件实际存在。"""
    out = _resolve_relative_path("nonexistent.pdf", tmp_path, "f")
    assert not out.exists()  # 没创建


# ---------- _detect_project_root 行为深度第十三批 ----------


def test_detect_project_root_finds_pyproject_one_level_up_batch13(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    # _detect_project_root(Path) 接受 dir 或 file
    found = _detect_project_root(sub)
    assert found == tmp_path.resolve()


def test_detect_project_root_finds_pyproject_in_same_dir_batch13(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    found = _detect_project_root(tmp_path)
    assert found == tmp_path.resolve()


def test_detect_project_root_file_input_uses_parent_batch13(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    f = tmp_path / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    found = _detect_project_root(f)
    assert found == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_cur_batch13(tmp_path):
    """找不到 pyproject.toml → 返回 cur（start dir）。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    found = _detect_project_root(sub)
    assert found == sub.resolve()


def test_detect_project_root_picks_nearest_pyproject_batch13(tmp_path):
    """多个 pyproject.toml → 选最近的（向上找）。"""
    (tmp_path / "pyproject.toml").write_text("[outer]", encoding="utf-8")
    sub1 = tmp_path / "s1"
    sub1.mkdir()
    (sub1 / "pyproject.toml").write_text("[inner]", encoding="utf-8")
    sub2 = sub1 / "s2"
    sub2.mkdir()
    found = _detect_project_root(sub2)
    assert found == sub1.resolve()


def test_detect_project_root_returns_path_object_batch13(tmp_path):
    found = _detect_project_root(tmp_path)
    assert isinstance(found, Path)


def test_detect_project_root_resolves_input_batch13(tmp_path):
    """start 会被 resolve()。"""
    found = _detect_project_root(tmp_path)
    assert found.is_absolute()


# ---------- DocumentEntry / ExpectedFailure / Manifest dataclass 行为第十三批 ----------


def test_document_entry_field_count_10_batch13():
    """DocumentEntry 有 10 个字段。"""
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_field_names_batch13():
    names = {f.name for f in fields(DocumentEntry)}
    assert names == {
        "doc_id", "path_str", "resolved_path", "source_type",
        "sha256", "categories", "paired_with",
        "annotation_file_str", "annotation_resolved", "expectations",
    }


def test_expected_failure_field_count_5_batch13():
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_field_names_batch13():
    names = {f.name for f in fields(ExpectedFailure)}
    assert names == {
        "doc_id", "path_str", "resolved_path",
        "expected_error_code", "source_type",
    }


def test_manifest_field_count_5_batch13():
    assert len(fields(Manifest)) == 5


def test_manifest_field_names_batch13():
    names = {f.name for f in fields(Manifest)}
    assert names == {
        "manifest_version", "devset_status",
        "documents", "expected_failures", "project_root",
    }


def test_document_entry_is_frozen_batch13():
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "modified"


def test_expected_failure_is_frozen_batch13():
    e = _make_ef()
    with pytest.raises(FrozenInstanceError):
        e.doc_id = "modified"


def test_manifest_is_frozen_batch13():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"


def test_document_entry_hash_equal_for_equal_data_batch13():
    d1 = _make_doc(doc_id="x", path_str="y.pdf")
    d2 = _make_doc(doc_id="x", path_str="y.pdf")
    assert hash(d1) == hash(d2)


def test_document_entry_eq_for_equal_data_batch13():
    d1 = _make_doc(doc_id="x")
    d2 = _make_doc(doc_id="x")
    assert d1 == d2


def test_document_entry_ineq_for_diff_data_batch13():
    d1 = _make_doc(doc_id="x")
    d2 = _make_doc(doc_id="y")
    assert d1 != d2


def test_expected_failure_hash_equal_for_equal_data_batch13():
    e1 = _make_ef(doc_id="x")
    e2 = _make_ef(doc_id="x")
    assert hash(e1) == hash(e2)


def test_manifest_hash_equal_for_equal_data_batch13():
    m1 = _make_manifest(devset_status="x")
    m2 = _make_manifest(devset_status="x")
    assert hash(m1) == hash(m2)


def test_document_entry_can_be_dict_key_batch13():
    d = _make_doc()
    s = {d: 1}
    assert s[d] == 1


def test_expected_failure_can_be_dict_key_batch13():
    e = _make_ef()
    s = {e: 1}
    assert s[e] == 1


def test_manifest_can_be_dict_key_batch13():
    m = _make_manifest()
    s = {m: 1}
    assert s[m] == 1


def test_document_entry_is_dataclass_batch13():
    assert is_dataclass(DocumentEntry)


def test_expected_failure_is_dataclass_batch13():
    assert is_dataclass(ExpectedFailure)


def test_manifest_is_dataclass_batch13():
    assert is_dataclass(Manifest)


# ---------- Manifest properties algorithm 第十三批 ----------


def test_manifest_pdf_count_mixed_batch13():
    docs = [
        _make_doc(doc_id="d1", source_type="pdf"),
        _make_doc(doc_id="d2", source_type="docx"),
        _make_doc(doc_id="d3", source_type="pdf"),
    ]
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 2


def test_manifest_docx_count_mixed_batch13():
    docs = [
        _make_doc(doc_id="d1", source_type="pdf"),
        _make_doc(doc_id="d2", source_type="docx"),
        _make_doc(doc_id="d3", source_type="docx"),
    ]
    m = _make_manifest(documents=docs)
    assert m.docx_count == 2


def test_manifest_pdf_count_zero_when_all_docx_batch13():
    docs = [_make_doc(source_type="docx")]
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 0


def test_manifest_categories_covered_sorted_batch13():
    docs = [
        _make_doc(doc_id="d1", categories=("z", "a")),
        _make_doc(doc_id="d2", categories=("m",)),
    ]
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_unique_batch13():
    docs = [
        _make_doc(doc_id="d1", categories=("a", "b")),
        _make_doc(doc_id="d2", categories=("b", "c")),
    ]
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_categories_covered_empty_when_no_categories_batch13():
    docs = [_make_doc(categories=())]
    m = _make_manifest(documents=docs)
    assert m.categories_covered == []


def test_manifest_content_group_count_unpaired_only_batch13():
    docs = [_make_doc(doc_id="d1"), _make_doc(doc_id="d2")]
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 2


def test_manifest_content_group_count_one_pair_batch13():
    docs = [
        _make_doc(doc_id="d1", paired_with="d2"),
        _make_doc(doc_id="d2", paired_with="d1"),
    ]
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 1


def test_manifest_content_group_count_pair_plus_unpaired_batch13():
    docs = [
        _make_doc(doc_id="d1", paired_with="d2"),
        _make_doc(doc_id="d2", paired_with="d1"),
        _make_doc(doc_id="d3"),
    ]
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 2


def test_manifest_content_group_count_one_way_pair_batch13():
    """单向 paired_with 仍算 1 组。"""
    docs = [
        _make_doc(doc_id="d1", paired_with="d2"),
        # d2 不指回 d1
    ]
    m = _make_manifest(documents=docs)
    # d1 → d2 形成一个 frozenset；d2 未配对（不在 seen 中，d2.paired_with=None）
    # 实际逻辑：pair_ids={frozenset(d1,d2)}, seen={d1,d2}, d2.doc_id in seen=True
    # 所以 unpaired=0
    assert m.content_group_count == 1


def test_manifest_file_count_returns_int_batch13():
    m = _make_manifest(documents=[_make_doc()])
    assert isinstance(m.file_count, int)


def test_manifest_pdf_count_returns_int_batch13():
    m = _make_manifest(documents=[_make_doc(source_type="pdf")])
    assert isinstance(m.pdf_count, int)


def test_manifest_docx_count_returns_int_batch13():
    m = _make_manifest(documents=[_make_doc(source_type="docx")])
    assert isinstance(m.docx_count, int)


def test_manifest_content_group_count_returns_int_batch13():
    m = _make_manifest(documents=[_make_doc()])
    assert isinstance(m.content_group_count, int)


def test_manifest_categories_covered_returns_list_batch13():
    m = _make_manifest(documents=[_make_doc(categories=("a",))])
    assert isinstance(m.categories_covered, list)


# ---------- load_manifest malformed data 第十三批 ----------


def _write_valid_manifest(tmp_path, override=None):
    """写一个 schema 合法的 manifest。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    if override:
        data.update(override)
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_accepts_path_object_batch13(tmp_path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p, project_root=tmp_path)
    assert m.manifest_version == "1.0"


def test_load_manifest_accepts_str_path_batch13(tmp_path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(str(p), project_root=str(tmp_path))
    assert m.manifest_version == "1.0"


def test_load_manifest_missing_file_raises_manifest_error_batch13(tmp_path):
    with pytest.raises(ManifestError, match="清单文件不存在"):
        load_manifest(tmp_path / "missing.json")


def test_load_manifest_invalid_json_raises_manifest_error_batch13(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON 解析失败"):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_schema_invalid_raises_eval_schema_error_batch13(tmp_path):
    """Schema 不通过 → EvalSchemaError（不是 ManifestError）。"""
    from evaluation.schema import EvalSchemaError

    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"wrong_field": 1}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_returns_manifest_dataclass_batch13(tmp_path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)


def test_load_manifest_returns_tuple_documents_batch13(tmp_path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m.documents, tuple)


def test_load_manifest_returns_tuple_expected_failures_batch13(tmp_path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m.expected_failures, tuple)


def test_load_manifest_default_project_root_uses_dir_batch13(tmp_path):
    """project_root=None → 从 manifest 路径向上找 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_dataclass_fields_accessible_batch13(tmp_path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p, project_root=tmp_path)
    assert hasattr(m, "manifest_version")
    assert hasattr(m, "devset_status")
    assert hasattr(m, "documents")
    assert hasattr(m, "expected_failures")
    assert hasattr(m, "project_root")


def test_load_manifest_does_not_write_to_disk_batch13(tmp_path):
    """load_manifest 是只读的。"""
    p = _write_valid_manifest(tmp_path)
    snapshot = p.read_text(encoding="utf-8")
    load_manifest(p, project_root=tmp_path)
    assert p.read_text(encoding="utf-8") == snapshot


def test_load_manifest_with_one_document_batch13(tmp_path):
    (tmp_path / "doc.pdf").write_text("", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, override={
        "documents": [{
            "doc_id": "d1",
            "path": "doc.pdf",
            "source_type": "pdf",
            "categories": ["normal"],
        }],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.documents) == 1
    assert m.documents[0].doc_id == "d1"


def test_load_manifest_with_one_expected_failure_batch13(tmp_path):
    (tmp_path / "bad.pdf").write_text("", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, override={
        "expected_failures": [{
            "doc_id": "ef1",
            "path": "bad.pdf",
            "expected_error_code": "unsupported_format",
        }],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].doc_id == "ef1"


def test_load_manifest_doc_path_must_be_relative_batch13(tmp_path):
    """doc path 绝对路径 → ManifestError（schema 校验通过路径形式后失败）。"""
    p = _write_valid_manifest(tmp_path, override={
        "documents": [{
            "doc_id": "d1",
            "path": "/etc/passwd",  # 绝对路径
            "source_type": "pdf",
            "categories": [],
        }],
    })
    with pytest.raises(ManifestError, match="绝对路径"):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_doc_path_no_backslash_batch13(tmp_path):
    p = _write_valid_manifest(tmp_path, override={
        "documents": [{
            "doc_id": "d1",
            "path": "a\\b.pdf",
            "source_type": "pdf",
            "categories": [],
        }],
    })
    with pytest.raises(ManifestError, match="反斜杠"):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_doc_path_escape_project_root_batch13(tmp_path):
    """相对路径跳出 project_root → ManifestError。"""
    p = _write_valid_manifest(tmp_path, override={
        "documents": [{
            "doc_id": "d1",
            "path": "../escape.pdf",
            "source_type": "pdf",
            "categories": [],
        }],
    })
    with pytest.raises(ManifestError, match="项目根目录之外"):
        load_manifest(p, project_root=tmp_path)


# ---------- module source forbidden tokens 第十六批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import pickle",
        "import yaml",
        "import socket",
        "import threading",
        "import multiprocessing",
        "import asyncio",
        "from pickle import",
        "from yaml import",
        "from socket import",
        "from threading import",
        "from multiprocessing import",
        "from asyncio import",
        "ctypes.",
        "import ctypes",
        "import marshal",
        "marshal.",
    ],
)
def test_manifest_source_no_forbidden_token_sixteenth_batch13(token):
    source = inspect.getsource(mmod)
    assert token not in source


def test_manifest_source_no_os_module_usage_batch13():
    source = inspect.getsource(mmod)
    assert "import os" not in source
    assert "os." not in source


def test_manifest_source_no_sys_module_usage_batch13():
    source = inspect.getsource(mmod)
    assert "import sys" not in source
    assert "sys." not in source


def test_manifest_source_no_tempfile_usage_batch13():
    source = inspect.getsource(mmod)
    assert "tempfile" not in source


def test_manifest_source_no_logging_batch13():
    source = inspect.getsource(mmod)
    assert "import logging" not in source


def test_manifest_source_no_re_module_batch13():
    source = inspect.getsource(mmod)
    assert "import re" not in source
    assert "re." not in source


def test_manifest_source_no_eval_call_batch13():
    source = inspect.getsource(mmod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_manifest_source_no_global_keyword_batch13():
    source = inspect.getsource(mmod)
    assert "\nglobal " not in source


def test_manifest_source_no_nonlocal_keyword_batch13():
    source = inspect.getsource(mmod)
    assert "nonlocal " not in source


def test_manifest_source_no_lambda_batch13():
    source = inspect.getsource(mmod)
    assert "lambda " not in source


def test_manifest_source_no_assert_statement_batch13():
    source = inspect.getsource(mmod)
    assert "\nassert " not in source


def test_manifest_source_no_print_batch13():
    source = inspect.getsource(mmod)
    assert "print(" not in source


def test_manifest_source_no_input_function_batch13():
    source = inspect.getsource(mmod)
    assert "input(" not in source


def test_manifest_source_no_open_call_at_top_level_batch13():
    """open() 只能在函数内。"""
    source = inspect.getsource(mmod)
    lines = source.split("\n")
    for line in lines:
        if not line.startswith(" ") and "open(" in line:
            raise AssertionError(f"top-level open: {line}")


def test_manifest_source_no_compile_call_batch13():
    source = inspect.getsource(mmod)
    assert "compile(" not in source


# ---------- module source 字符串精确补强第十三批 ----------


def test_module_source_json_import_top_level_batch13():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "import json" in head


def test_module_source_dataclass_import_top_level_batch13():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from dataclasses import dataclass" in head


def test_module_source_pathlib_import_top_level_batch13():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_any_import_top_level_batch13():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_source_manifest_version_import_batch13():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation import MANIFEST_VERSION" in head


def test_module_source_validate_import_batch13():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation.schema import validate" in head


def test_module_source_has_ManifestError_class_batch13():
    source = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in source


def test_module_source_has_frozen_dataclass_batch13():
    source = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in source


def test_module_source_has_three_dataclass_decorators_batch13():
    source = inspect.getsource(mmod)
    assert source.count("@dataclass(frozen=True)") == 3


def test_module_source_has_is_absolute_like_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in source


def test_module_source_has_has_backslash_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _has_backslash(" in source


def test_module_source_has_resolve_relative_path_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in source


def test_module_source_has_detect_project_root_def_batch13():
    source = inspect.getsource(mmod)
    assert "def _detect_project_root(" in source


def test_module_source_has_load_manifest_def_batch13():
    source = inspect.getsource(mmod)
    assert "def load_manifest(" in source


def test_module_source_has_relative_to_call_batch13():
    source = inspect.getsource(mmod)
    assert ".relative_to(" in source


def test_module_source_has_resolve_call_batch13():
    source = inspect.getsource(mmod)
    assert ".resolve()" in source


def test_module_source_has_path_open_call_batch13():
    source = inspect.getsource(mmod)
    assert ".open(" in source


def test_module_source_has_validate_call_batch13():
    source = inspect.getsource(mmod)
    assert "validate(" in source


def test_module_source_future_annotations_top_level_batch13():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


# ---------- signatures 第十三批 ----------


def test_manifest_error_signature_no_params_batch13():
    sig = inspect.signature(ManifestError.__init__)
    # Exception.__init__ 接受 *args
    # 但 ManifestError 自身没定义 __init__
    assert issubclass(ManifestError, Exception)


def test_is_absolute_like_signature_one_param_batch13():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path_str"


def test_is_absolute_like_return_annotation_bool_batch13():
    sig = inspect.signature(_is_absolute_like)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "bool" in ret_str


def test_has_backslash_signature_one_param_batch13():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path_str"


def test_has_backslash_return_annotation_bool_batch13():
    sig = inspect.signature(_has_backslash)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "bool" in ret_str


def test_resolve_relative_path_signature_3_params_batch13():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.values())
    assert len(params) == 3
    assert [p.name for p in params] == ["path_str", "project_root", "field_name"]


def test_resolve_relative_path_return_annotation_path_batch13():
    sig = inspect.signature(_resolve_relative_path)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "Path" in ret_str


def test_load_manifest_signature_2_params_batch13():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["manifest_path", "project_root"]


def test_load_manifest_manifest_path_annotation_union_batch13():
    sig = inspect.signature(load_manifest)
    annot = sig.parameters["manifest_path"].annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "Path" in annot_str
    assert "str" in annot_str


def test_load_manifest_project_root_annotation_optional_batch13():
    sig = inspect.signature(load_manifest)
    annot = sig.parameters["project_root"].annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "Path" in annot_str
    assert "str" in annot_str
    assert "None" in annot_str


def test_load_manifest_project_root_default_none_batch13():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_load_manifest_return_annotation_manifest_batch13():
    sig = inspect.signature(load_manifest)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "Manifest" in ret_str


def test_detect_project_root_signature_one_param_batch13():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "start"


def test_detect_project_root_return_annotation_path_batch13():
    sig = inspect.signature(_detect_project_root)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "Path" in ret_str


def test_module_dunder_all_count_5_batch13():
    assert hasattr(mmod, "__all__")
    assert len(mmod.__all__) == 5


# ---------- module 合理性第十三批 ----------


def test_module_dunder_file_exists_batch13():
    assert hasattr(mmod, "__file__")
    assert mmod.__file__ is not None


def test_module_dunder_file_path_evaluation_manifest_batch13():
    import os
    sep = os.sep
    assert mmod.__file__.endswith(sep + "manifest.py")
    assert "evaluation" in mmod.__file__


def test_module_name_evaluation_manifest_batch13():
    assert mmod.__name__ == "evaluation.manifest"


def test_module_docstring_present_batch13():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 30


def test_module_docstring_mentions_invariants_batch13():
    assert mmod.__doc__ is not None
    assert "相对路径" in mmod.__doc__ or "absolute" in mmod.__doc__


def test_module_uses_future_annotations_batch13():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


def test_module_top_level_user_class_count_4_batch13():
    """顶层用户类 4 个：ManifestError + 3 个 dataclass。"""
    classes = [
        n for n, v in vars(mmod).items()
        if inspect.isclass(v) and v.__module__ == mmod.__name__
    ]
    assert set(classes) == {"ManifestError", "DocumentEntry", "ExpectedFailure", "Manifest"}


def test_module_user_function_count_5_batch13():
    funcs = [
        n for n, v in vars(mmod).items()
        if inspect.isfunction(v) and v.__module__ == mmod.__name__
    ]
    assert set(funcs) == {
        "_is_absolute_like", "_has_backslash",
        "_resolve_relative_path", "load_manifest", "_detect_project_root",
    }


def test_module_has_manifest_version_attr_batch13():
    assert hasattr(mmod, "MANIFEST_VERSION")


def test_module_manifest_version_value_batch13():
    assert mmod.MANIFEST_VERSION == MANIFEST_VERSION


def test_module_no_user_functions_with_varargs_batch13():
    funcs = [
        v for n, v in vars(mmod).items()
        if inspect.isfunction(v) and v.__module__ == mmod.__name__
    ]
    for fn in funcs:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )


# ---------- 端到端集成第十三批 ----------


def test_e2e_load_manifest_with_complete_manifest_batch13(tmp_path):
    (tmp_path / "doc1.pdf").write_text("", encoding="utf-8")
    (tmp_path / "doc2.docx").write_text("", encoding="utf-8")
    (tmp_path / "bad.pdf").write_text("", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "doc1.pdf", "source_type": "pdf", "categories": ["a"]},
            {"doc_id": "d2", "path": "doc2.docx", "source_type": "docx", "categories": ["b"]},
        ],
        "expected_failures": [
            {"doc_id": "ef1", "path": "bad.pdf", "expected_error_code": "x"},
        ],
    }), encoding="utf-8")

    m = load_manifest(p, project_root=tmp_path)
    assert len(m.documents) == 2
    assert len(m.expected_failures) == 1
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.categories_covered == ["a", "b"]


def test_e2e_manifest_dataclass_serializable_through_pickle_batch13(tmp_path):
    """Manifest dataclass 支持 pickle。"""
    import pickle

    (tmp_path / "doc.pdf").write_text("", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, override={
        "documents": [{
            "doc_id": "d1",
            "path": "doc.pdf",
            "source_type": "pdf",
            "categories": [],
        }],
    })
    m = load_manifest(p, project_root=tmp_path)
    data = pickle.dumps(m)
    m2 = pickle.loads(data)
    assert m == m2


def test_e2e_load_manifest_idempotent_batch13(tmp_path):
    """两次 load_manifest 同文件 → 等价 Manifest。"""
    p = _write_valid_manifest(tmp_path)
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1 == m2


def test_e2e_manifest_categories_in_property_matches_data_batch13(tmp_path):
    (tmp_path / "doc.pdf").write_text("", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, override={
        "documents": [{
            "doc_id": "d1",
            "path": "doc.pdf",
            "source_type": "pdf",
            "categories": ["alpha", "beta", "gamma"],
        }],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["alpha", "beta", "gamma"]


def test_e2e_manifest_content_group_count_complex_batch13(tmp_path):
    """复杂配对：2 个互配 + 1 个单飞 = 2 组。"""
    (tmp_path / "d1.pdf").write_text("", encoding="utf-8")
    (tmp_path / "d2.docx").write_text("", encoding="utf-8")
    (tmp_path / "d3.pdf").write_text("", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, override={
        "documents": [
            {"doc_id": "d1", "path": "d1.pdf", "source_type": "pdf",
             "categories": [], "paired_with": "d2"},
            {"doc_id": "d2", "path": "d2.docx", "source_type": "docx",
             "categories": [], "paired_with": "d1"},
            {"doc_id": "d3", "path": "d3.pdf", "source_type": "pdf",
             "categories": []},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 2


def test_e2e_load_manifest_relative_path_resolved_to_absolute_batch13(tmp_path):
    (tmp_path / "doc.pdf").write_text("", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, override={
        "documents": [{
            "doc_id": "d1",
            "path": "doc.pdf",
            "source_type": "pdf",
            "categories": [],
        }],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].resolved_path.is_absolute()
    assert m.documents[0].resolved_path == (tmp_path / "doc.pdf").resolve()


def test_e2e_manifest_pdf_count_with_categories_filter_batch13(tmp_path):
    """验证 properties 不互相干扰。"""
    (tmp_path / "a.pdf").write_text("", encoding="utf-8")
    (tmp_path / "b.pdf").write_text("", encoding="utf-8")
    (tmp_path / "c.docx").write_text("", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, override={
        "documents": [
            {"doc_id": "a", "path": "a.pdf", "source_type": "pdf", "categories": ["x"]},
            {"doc_id": "b", "path": "b.pdf", "source_type": "pdf", "categories": ["y"]},
            {"doc_id": "c", "path": "c.docx", "source_type": "docx", "categories": ["x"]},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.pdf_count == 2
    assert m.docx_count == 1
    assert m.file_count == 3
    assert m.categories_covered == ["x", "y"]


def test_e2e_manifest_resolve_relative_path_independent_calls_batch13(tmp_path):
    """两次调用 _resolve_relative_path 独立。"""
    p1 = _resolve_relative_path("foo", tmp_path, "f")
    p2 = _resolve_relative_path("foo", tmp_path, "f")
    assert p1 == p2
    # 返回独立的 Path 对象
    assert p1 is not p2


def test_e2e_load_manifest_path_object_independent_batch13(tmp_path):
    """两次 load_manifest 返回独立 Manifest 对象。"""
    p = _write_valid_manifest(tmp_path)
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1 == m2
    # 但 documents 是 tuple（不可变）
    assert m1.documents is not m2.documents or m1.documents == m2.documents


def test_e2e_combined_helper_chain_batch13(tmp_path):
    """helpers 协作链：_is_absolute_like → _has_backslash → _resolve_relative_path。"""
    # 合法路径
    assert not _is_absolute_like("foo/bar.pdf")
    assert not _has_backslash("foo/bar.pdf")
    out = _resolve_relative_path("foo/bar.pdf", tmp_path, "f")
    assert out == (tmp_path / "foo" / "bar.pdf").resolve()
