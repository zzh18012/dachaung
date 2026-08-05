r"""evaluation/manifest.py 边角测试 - 第十二轮（Round 226）。

补强已有 base/edges/edges2-11（共 ~1010 测试）未覆盖的深度：
- _is_absolute_like：bytes/None/数字开头/Unicode 数字；3-char 边界
- _has_backslash：bytes/None；只在末尾/中间/开头
- _resolve_relative_path：field_name 出现在错误消息；空字符串触发不同错误；project_root 是 file
- load_manifest：manifest_path str/Path；project_root str/Path/None；documents 空 list；expectations 空 dict；JSON 解析错误
- Manifest properties：file_count/pdf_count/docx_count 与 source_type 非预期值；categories_covered 排序稳定
- _detect_project_root：返回 Path 对象；遇到 .git 也算项目根吗（实际只看 pyproject.toml）
- 模块结构补强
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import Any

import pytest

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
# _is_absolute_like 深度（补强 edges11）
# =========================================================================


def test_is_absolute_like_bytes_input_raises_typeerror():
    """bytes 输入：bytes.startswith 需要 bytes 输入，但路径下标返回 int。"""
    with pytest.raises(TypeError):
        _is_absolute_like(b"/foo")  # type: ignore[arg-type]


def test_is_absolute_like_none_input_returns_false():
    """None 是 falsy → `if not path_str: return False` 命中，不抛错。"""
    assert _is_absolute_like(None) is False  # type: ignore[arg-type]


def test_is_absolute_like_int_input_raises_attribute_error():
    """int 没有 .startswith → AttributeError。"""
    with pytest.raises(AttributeError):
        _is_absolute_like(123)  # type: ignore[arg-type]


def test_is_absolute_like_digit_drive_returns_false():
    """数字开头不是绝对路径（盘符必须是字母）。"""
    assert _is_absolute_like("1:/foo") is False
    assert _is_absolute_like("9:\\foo") is False


def test_is_absolute_like_underscore_drive_returns_false():
    """下划线开头不是绝对路径。"""
    assert _is_absolute_like("_:/foo") is False
    assert _is_absolute_like("_:\\foo") is False


def test_is_absolute_like_dot_drive_returns_false():
    """.:/foo → . 不是字母。"""
    assert _is_absolute_like(".:/foo") is False


def test_is_absolute_like_dash_drive_returns_false():
    """-:/foo → - 不是字母。"""
    assert _is_absolute_like("-:/foo") is False


def test_is_absolute_like_three_char_drive_with_separator_true():
    """3 字符 + [1]==':' + [0].isalpha() + [2] in '\\/' → True。"""
    assert _is_absolute_like("C:\\") is True


def test_is_absolute_like_three_char_drive_forward_slash_true():
    assert _is_absolute_like("C:/") is True


def test_is_absolute_like_three_char_no_separator_false():
    """C:x → 没有 \\ 或 / 在 [2] → False。"""
    assert _is_absolute_like("C:x") is False


def test_is_absolute_like_just_two_chars_false():
    """'C:' → 长度 < 3 → False。"""
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_lowercase_alpha_drive_with_separator():
    assert _is_absolute_like("a:\\foo") is True
    assert _is_absolute_like("z:/bar") is True


def test_is_absolute_like_uppercase_alpha_drive_with_separator():
    assert _is_absolute_like("A:\\foo") is True
    assert _is_absolute_like("Z:/bar") is True


def test_is_absolute_like_double_slash_network_path():
    """\\\\server\\share → 不被识别为绝对路径（仅识别 / 或 drive:sep）。"""
    # 注意：在 Python 字符串中 '\\\\' 是 2 个反斜杠
    assert _is_absolute_like("\\\\server\\share") is False


def test_is_absolute_like_unicode_alpha_drive_true():
    """é: \\ → é.isalpha() True → True。"""
    assert _is_absolute_like("é:\\foo") is True


def test_is_absolute_like_returns_bool_type():
    assert isinstance(_is_absolute_like("/foo"), bool)
    assert isinstance(_is_absolute_like("foo"), bool)


def test_is_absolute_like_relative_path_returns_false():
    assert _is_absolute_like("foo/bar.txt") is False


def test_is_absolute_like_just_filename_returns_false():
    assert _is_absolute_like("foo.txt") is False


def test_is_absolute_like_single_dot_filename_returns_false():
    assert _is_absolute_like(".gitignore") is False


def test_is_absolute_like_double_dot_relative_returns_false():
    assert _is_absolute_like("../foo.txt") is False


# =========================================================================
# _has_backslash 深度（补强 edges11）
# =========================================================================


def test_has_backslash_bytes_input_returns_false():
    """bytes 输入：'\\\\' in b'\\\\' 是合法的（bytes in bytes）。

    但 'foo\\\\bar' 是 str → bytes 输入会搜索 str 子串 → TypeError。
    """
    with pytest.raises(TypeError):
        _has_backslash(b"foo\\bar")  # type: ignore[arg-type]


def test_has_backslash_none_input_raises_typeerror():
    with pytest.raises(TypeError):
        _has_backslash(None)  # type: ignore[arg-type]


def test_has_backslash_empty_string_false():
    assert _has_backslash("") is False


def test_has_backslash_only_backslash_true():
    assert _has_backslash("\\") is True


def test_has_backslash_at_start_true():
    assert _has_backslash("\\foo") is True


def test_has_backslash_at_middle_true():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_at_end_true():
    assert _has_backslash("foo\\") is True


def test_has_backslash_multiple_true():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_forward_slash_only_false():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_mixed_true():
    assert _has_backslash("foo/bar\\baz") is True


def test_has_backslash_returns_bool_type():
    assert isinstance(_has_backslash("foo"), bool)


# =========================================================================
# _resolve_relative_path 深度（补强 edges11）
# =========================================================================


def test_resolve_relative_path_empty_raises_with_field_name(tmp_path):
    """空字符串错误消息应含 field_name。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "MY_FIELD")
    assert "MY_FIELD" in str(exc_info.value)


def test_resolve_relative_path_absolute_raises_with_field_name(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/etc/passwd", tmp_path, "ABS_FIELD")
    assert "ABS_FIELD" in str(exc_info.value)


def test_resolve_relative_path_backslash_raises_with_field_name(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("foo\\bar", tmp_path, "BS_FIELD")
    assert "BS_FIELD" in str(exc_info.value)


def test_resolve_relative_path_outside_root_raises_with_field_name(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("../outside.txt", tmp_path, "OUT_FIELD")
    assert "OUT_FIELD" in str(exc_info.value)


def test_resolve_relative_path_returns_path_object(tmp_path):
    result = _resolve_relative_path("foo.txt", tmp_path, "f")
    assert isinstance(result, Path)


def test_resolve_relative_path_resolved_is_absolute(tmp_path):
    result = _resolve_relative_path("foo.txt", tmp_path, "f")
    assert result.is_absolute()


def test_resolve_relative_path_result_is_within_project_root(tmp_path):
    result = _resolve_relative_path("foo.txt", tmp_path, "f")
    assert result.relative_to(tmp_path.resolve())


def test_resolve_relative_path_subdirectory(tmp_path):
    result = _resolve_relative_path("sub/dir/foo.txt", tmp_path, "f")
    # result = tmp_path/sub/dir/foo.txt
    # parent = tmp_path/sub/dir
    # parent.parent = tmp_path/sub
    # parent.parent.parent = tmp_path
    assert result.parent.parent.parent == tmp_path.resolve()


def test_resolve_relative_path_explicit_dot(tmp_path):
    result = _resolve_relative_path("./foo.txt", tmp_path, "f")
    assert result.name == "foo.txt"


def test_resolve_relative_path_double_slash_collapsed(tmp_path):
    result = _resolve_relative_path("foo//bar.txt", tmp_path, "f")
    # Pathway collapse 多斜杠
    assert result.name == "bar.txt"


def test_resolve_relative_path_returns_existing_path_form(tmp_path):
    """返回值是 resolved path（如果有文件，应能 is_file() True）。"""
    (tmp_path / "foo.txt").write_text("hi", encoding="utf-8")
    result = _resolve_relative_path("foo.txt", tmp_path, "f")
    assert result.is_file()


def test_resolve_relative_path_project_root_file_does_not_raise(tmp_path):
    """project_root 是 file 时，Path 拼接与 relative_to 都按 path component 工作。
    (file / 'sub.txt').resolve() = file/sub.txt（虚拟）
    file/sub.txt.relative_to(file) = 'sub.txt'（成功）
    → 不抛错。行为记录。
    """
    f = tmp_path / "marker.txt"
    f.write_text("", encoding="utf-8")
    result = _resolve_relative_path("sub.txt", f, "f")
    assert isinstance(result, Path)


# =========================================================================
# load_manifest 深度（补强 edges11）
# =========================================================================


def _mk_doc(doc_id="d1", path="samples/x.txt", source_type="text",
            categories=None, paired_with=None, sha256=None,
            annotation_file=None, expectations=None):
    d: dict[str, Any] = {
        "doc_id": doc_id,
        "path": path,
        "source_type": source_type,
    }
    if categories is not None:
        d["categories"] = categories
    if paired_with is not None:
        d["paired_with"] = paired_with
    if sha256 is not None:
        d["sha256"] = sha256
    if annotation_file is not None:
        d["annotation_file"] = annotation_file
    if expectations is not None:
        d["expectations"] = expectations
    return d


def _mk_ef(doc_id="ef1", path="bad.txt", expected_error_code="file_not_found",
           source_type=None):
    d: dict[str, Any] = {
        "doc_id": doc_id,
        "path": path,
        "expected_error_code": expected_error_code,
    }
    if source_type is not None:
        d["source_type"] = source_type
    return d


def _mk_manifest(docs=None, efs=None, devset_status="incomplete"):
    return {
        "manifest_version": "1.0",
        "devset_status": devset_status,
        "documents": docs or [],
        "expected_failures": efs or [],
    }


def _write_manifest(tmp_path, manifest_dict, name="m.json"):
    p = tmp_path / name
    p.write_text(json.dumps(manifest_dict), encoding="utf-8")
    return p


def test_load_manifest_accepts_str_path(tmp_path):
    """manifest_path 可以是 str。"""
    p = _write_manifest(tmp_path, _mk_manifest())
    code_path = str(p)
    result = load_manifest(code_path, project_root=tmp_path)
    assert isinstance(result, Manifest)


def test_load_manifest_accepts_path_object(tmp_path):
    p = _write_manifest(tmp_path, _mk_manifest())
    result = load_manifest(p, project_root=tmp_path)
    assert isinstance(result, Manifest)


def test_load_manifest_accepts_str_project_root(tmp_path):
    p = _write_manifest(tmp_path, _mk_manifest())
    result = load_manifest(p, project_root=str(tmp_path))
    assert isinstance(result, Manifest)


def test_load_manifest_accepts_path_project_root(tmp_path):
    p = _write_manifest(tmp_path, _mk_manifest())
    result = load_manifest(p, project_root=tmp_path)
    assert isinstance(result, Manifest)


def test_load_manifest_missing_file_raises(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(tmp_path / "missing.json", project_root=tmp_path)
    assert "清单文件不存在" in str(exc_info.value)


def test_load_manifest_directory_raises(tmp_path):
    """manifest_path 指向目录 → is_file() False → 报错。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(ManifestError):
        load_manifest(sub, project_root=tmp_path)


def test_load_manifest_invalid_json_raises(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "JSON 解析失败" in str(exc_info.value)


def test_load_manifest_empty_file_raises(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_empty_documents_list(tmp_path):
    """documents 是空 list → Manifest.documents 是空 tuple。"""
    p = _write_manifest(tmp_path, _mk_manifest(docs=[]))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents == ()


def test_load_manifest_empty_expected_failures_list(tmp_path):
    p = _write_manifest(tmp_path, _mk_manifest(efs=[]))
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures == ()


def test_load_manifest_both_documents_and_expected_failures(tmp_path):
    """documents 与 expected_failures 共存。"""
    # 在 tmp_path 下创建实际文件
    (tmp_path / "doc1.pdf").write_text("hi", encoding="utf-8")
    p = _write_manifest(tmp_path, _mk_manifest(
        docs=[_mk_doc(doc_id="d1", path="doc1.pdf", source_type="pdf")],
        efs=[_mk_ef(doc_id="ef1", path="missing.txt")]
    ))
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.documents) == 1
    assert len(m.expected_failures) == 1


def test_load_manifest_round_trip_resolved_path(tmp_path):
    (tmp_path / "doc1.pdf").write_text("hi", encoding="utf-8")
    p = _write_manifest(tmp_path, _mk_manifest(
        docs=[_mk_doc(doc_id="d1", path="doc1.pdf", source_type="pdf")]
    ))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].resolved_path == (tmp_path / "doc1.pdf").resolve()


def test_load_manifest_round_trip_path_str_preserved(tmp_path):
    """path_str 应保留原始字符串。"""
    (tmp_path / "doc1.pdf").write_text("hi", encoding="utf-8")
    p = _write_manifest(tmp_path, _mk_manifest(
        docs=[_mk_doc(doc_id="d1", path="doc1.pdf", source_type="pdf")]
    ))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].path_str == "doc1.pdf"


def test_load_manifest_round_trip_source_type_preserved(tmp_path):
    (tmp_path / "doc1.docx").write_text("hi", encoding="utf-8")
    p = _write_manifest(tmp_path, _mk_manifest(
        docs=[_mk_doc(doc_id="d1", path="doc1.docx", source_type="docx")]
    ))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].source_type == "docx"


def test_load_manifest_round_trip_categories_as_tuple(tmp_path):
    (tmp_path / "doc1.pdf").write_text("hi", encoding="utf-8")
    p = _write_manifest(tmp_path, _mk_manifest(
        docs=[_mk_doc(doc_id="d1", path="doc1.pdf", source_type="pdf", categories=["a", "b"])]
    ))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ("a", "b")
    assert isinstance(m.documents[0].categories, tuple)


def test_load_manifest_round_trip_categories_default_empty_tuple(tmp_path):
    (tmp_path / "doc1.pdf").write_text("hi", encoding="utf-8")
    p = _write_manifest(tmp_path, _mk_manifest(
        docs=[_mk_doc(doc_id="d1", path="doc1.pdf", source_type="pdf")]
    ))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ()


def test_load_manifest_round_trip_paired_with(tmp_path):
    (tmp_path / "doc1.pdf").write_text("hi", encoding="utf-8")
    p = _write_manifest(tmp_path, _mk_manifest(
        docs=[_mk_doc(doc_id="d1", path="doc1.pdf", source_type="pdf", paired_with="d2")]
    ))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].paired_with == "d2"


def test_load_manifest_round_trip_sha256(tmp_path):
    (tmp_path / "doc1.pdf").write_text("hi", encoding="utf-8")
    p = _write_manifest(tmp_path, _mk_manifest(
        docs=[_mk_doc(doc_id="d1", path="doc1.pdf", source_type="pdf",
                      sha256="a" * 64)]
    ))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 == "a" * 64


def test_load_manifest_round_trip_annotation_file(tmp_path):
    (tmp_path / "doc1.pdf").write_text("hi", encoding="utf-8")
    (tmp_path / "ann.json").write_text("{}", encoding="utf-8")
    p = _write_manifest(tmp_path, _mk_manifest(
        docs=[_mk_doc(doc_id="d1", path="doc1.pdf", source_type="pdf", annotation_file="ann.json")]
    ))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_file_str == "ann.json"
    assert m.documents[0].annotation_resolved == (tmp_path / "ann.json").resolve()


def test_load_manifest_round_trip_expectations(tmp_path):
    (tmp_path / "doc1.pdf").write_text("hi", encoding="utf-8")
    p = _write_manifest(tmp_path, _mk_manifest(
        docs=[_mk_doc(doc_id="d1", path="doc1.pdf", source_type="pdf",
                       expectations={"element_count_by_type": {"paragraph": 5}})]
    ))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_round_trip_expected_failure(tmp_path):
    p = _write_manifest(tmp_path, _mk_manifest(
        efs=[_mk_ef(doc_id="ef1", path="missing.txt",
                    expected_error_code="file_not_found")]
    ))
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].doc_id == "ef1"
    assert m.expected_failures[0].path_str == "missing.txt"
    assert m.expected_failures[0].expected_error_code == "file_not_found"
    assert m.expected_failures[0].resolved_path == (tmp_path / "missing.txt").resolve()


def test_load_manifest_expected_failure_with_source_type(tmp_path):
    p = _write_manifest(tmp_path, _mk_manifest(
        efs=[_mk_ef(doc_id="ef1", path="missing.txt",
                    expected_error_code="file_not_found",
                    source_type="pdf")]
    ))
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].source_type == "pdf"


def test_load_manifest_expected_failure_default_source_type_none(tmp_path):
    p = _write_manifest(tmp_path, _mk_manifest(
        efs=[_mk_ef(doc_id="ef1", path="missing.txt",
                    expected_error_code="file_not_found")]
    ))
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].source_type is None


# =========================================================================
# Manifest properties 深度
# =========================================================================


def _mk_doc_entry(doc_id="d1", source_type="text", categories=(),
                  paired_with=None):
    return DocumentEntry(
        doc_id=doc_id,
        path_str=f"samples/{doc_id}.txt",
        resolved_path=Path(f"/tmp/{doc_id}.txt"),
        source_type=source_type,
        sha256=None,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def _mk_manifest_obj(docs=None, efs=None, project_root=None):
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=tuple(docs or []),
        expected_failures=tuple(efs or []),
        project_root=project_root or Path("."),
    )


def test_manifest_pdf_count_with_unknown_source_type():
    """source_type='unknown' 既不算 pdf 也不算 docx。"""
    docs = [
        _mk_doc_entry(doc_id="d1", source_type="unknown"),
        _mk_doc_entry(doc_id="d2", source_type="pdf"),
    ]
    m = _mk_manifest_obj(docs=docs)
    assert m.pdf_count == 1
    assert m.docx_count == 0


def test_manifest_docx_count_with_unknown_source_type():
    docs = [
        _mk_doc_entry(doc_id="d1", source_type="docx"),
        _mk_doc_entry(doc_id="d2", source_type="unknown"),
    ]
    m = _mk_manifest_obj(docs=docs)
    assert m.docx_count == 1


def test_manifest_pdf_count_and_docx_count_distinct():
    docs = [
        _mk_doc_entry(doc_id="d1", source_type="pdf"),
        _mk_doc_entry(doc_id="d2", source_type="docx"),
        _mk_doc_entry(doc_id="d3", source_type="pdf"),
        _mk_doc_entry(doc_id="d4", source_type="text"),
    ]
    m = _mk_manifest_obj(docs=docs)
    assert m.pdf_count == 2
    assert m.docx_count == 1
    assert m.file_count == 4


def test_manifest_categories_covered_returns_new_list_each_call():
    docs = [_mk_doc_entry(doc_id="d1", categories=("a", "b"))]
    m = _mk_manifest_obj(docs=docs)
    l1 = m.categories_covered
    l2 = m.categories_covered
    assert l1 == l2
    assert l1 is not l2


def test_manifest_categories_covered_sorted_case_sensitive():
    """大写在小写之前（ASCII 排序）。"""
    docs = [_mk_doc_entry(doc_id="d1", categories=("Z", "a", "M"))]
    m = _mk_manifest_obj(docs=docs)
    assert m.categories_covered == ["M", "Z", "a"]


def test_manifest_categories_covered_stable_for_empty():
    m = _mk_manifest_obj(docs=[])
    assert m.categories_covered == []


def test_manifest_file_count_consistency():
    """file_count == len(documents)。"""
    docs = [_mk_doc_entry(doc_id=f"d{i}") for i in range(5)]
    m = _mk_manifest_obj(docs=docs)
    assert m.file_count == 5 == len(m.documents)


def test_manifest_file_count_property_no_parens_needed():
    """file_count 是 property，不是方法。"""
    docs = [_mk_doc_entry()]
    m = _mk_manifest_obj(docs=docs)
    # 不需要调用：m.file_count()，直接 m.file_count
    assert isinstance(m.file_count, int)


def test_manifest_pdf_count_property_no_parens_needed():
    docs = [_mk_doc_entry(source_type="pdf")]
    m = _mk_manifest_obj(docs=docs)
    assert isinstance(m.pdf_count, int)


def test_manifest_docx_count_property_no_parens_needed():
    docs = [_mk_doc_entry(source_type="docx")]
    m = _mk_manifest_obj(docs=docs)
    assert isinstance(m.docx_count, int)


def test_manifest_content_group_count_property_no_parens_needed():
    docs = [_mk_doc_entry()]
    m = _mk_manifest_obj(docs=docs)
    assert isinstance(m.content_group_count, int)


def test_manifest_categories_covered_property_no_parens_needed():
    docs = [_mk_doc_entry(categories=("a",))]
    m = _mk_manifest_obj(docs=docs)
    assert isinstance(m.categories_covered, list)


def test_manifest_dataclass_replace_preserves_other_fields():
    docs = (_mk_doc_entry(doc_id="d1"),)
    m = _mk_manifest_obj(docs=docs)
    new_docs = (_mk_doc_entry(doc_id="d2"),)
    m2 = replace(m, documents=new_docs)
    assert m2.documents == new_docs
    assert m2.devset_status == m.devset_status
    assert m2.manifest_version == m.manifest_version
    assert m2.project_root == m.project_root


def test_manifest_frozen_cannot_set_attribute():
    m = _mk_manifest_obj()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


def test_document_entry_frozen_cannot_set_attribute():
    d = _mk_doc_entry()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "changed"  # type: ignore[misc]


def test_expected_failure_frozen_cannot_set_attribute():
    ef = ExpectedFailure(
        doc_id="ef1",
        path_str="x.txt",
        resolved_path=Path("/tmp/x.txt"),
        expected_error_code="file_not_found",
        source_type=None,
    )
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "changed"  # type: ignore[misc]


# =========================================================================
# _detect_project_root 深度
# =========================================================================


def test_detect_project_root_returns_path_object(tmp_path):
    """返回值应是 Path 对象，不是 str。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert isinstance(result, Path)


def test_detect_project_root_resolves_input(tmp_path):
    """返回值是 resolved path（absolute）。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert result.is_absolute()


def test_detect_project_root_with_dotgit_only(tmp_path):
    """只有 .git 没有 pyproject.toml → 不被识别为 project root。"""
    (tmp_path / ".git").mkdir()
    result = _detect_project_root(tmp_path)
    # 不应等于 tmp_path，应是 tmp_path 自己（fallback）
    # 实际：没有 pyproject 就 fallback 到 cur
    # 注意 cur 是 start.resolve() 后再 .parent（如果是 file）
    assert result == tmp_path.resolve()


def test_detect_project_root_with_subdir_pyproject(tmp_path):
    """多层目录中找最近的 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "pyproject.toml").write_text("", encoding="utf-8")
    result = _detect_project_root(sub)
    # 应该返回 sub（最近的）
    assert result == sub.resolve()


def test_detect_project_root_callable():
    assert callable(_detect_project_root)


def test_detect_project_root_signature():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters) == ["start"]


# =========================================================================
# 模块结构（补强 edges11）
# =========================================================================


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


def test_module_all_exact_set():
    import evaluation.manifest as m
    assert set(m.__all__) == {
        "ManifestError", "Manifest", "DocumentEntry",
        "ExpectedFailure", "load_manifest",
    }


def test_module_all_is_list():
    import evaluation.manifest as m
    assert isinstance(m.__all__, list)


def test_module_all_length_five():
    import evaluation.manifest as m
    assert len(m.__all__) == 5


def test_module_all_does_not_include_internal_helpers():
    import evaluation.manifest as m
    assert "_is_absolute_like" not in m.__all__
    assert "_has_backslash" not in m.__all__
    assert "_resolve_relative_path" not in m.__all__
    assert "_detect_project_root" not in m.__all__


def test_module_docstring_present():
    import evaluation.manifest as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 20


def test_module_docstring_mentions_invariants():
    """docstring 应提及 '相对路径' / '绝对路径' / '反斜杠'。"""
    import evaluation.manifest as m
    doc = m.__doc__
    assert "相对路径" in doc or "absolute" in doc.lower()


def test_module_uses_future_annotations():
    import evaluation.manifest as m
    sig = inspect.signature(m.load_manifest)
    assert isinstance(sig.return_annotation, str)


def test_module_has_manifest_error_class():
    import evaluation.manifest as m
    assert isinstance(m.ManifestError, type)
    assert issubclass(m.ManifestError, Exception)


def test_module_has_dataclass_types():
    import evaluation.manifest as m
    # dataclass 是 decorator，但 dataclass 类型本身在模块 namespace
    assert callable(m.dataclass)


def test_module_manifest_error_has_docstring():
    import evaluation.manifest as m
    assert m.ManifestError.__doc__ is not None
    assert len(m.ManifestError.__doc__) > 0


def test_load_manifest_signature():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters) == ["manifest_path", "project_root"]


def test_load_manifest_manifest_path_kind():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["manifest_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_load_manifest_project_root_kind():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_load_manifest_project_root_default_none():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_load_manifest_return_annotation_str():
    sig = inspect.signature(load_manifest)
    assert isinstance(sig.return_annotation, str)


def test_is_absolute_like_signature():
    sig = inspect.signature(_is_absolute_like)
    assert list(sig.parameters) == ["path_str"]


def test_has_backslash_signature():
    sig = inspect.signature(_has_backslash)
    assert list(sig.parameters) == ["path_str"]


def test_resolve_relative_path_signature():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters) == ["path_str", "project_root", "field_name"]


def test_resolve_relative_path_field_name_no_default():
    sig = inspect.signature(_resolve_relative_path)
    assert sig.parameters["field_name"].default is inspect.Parameter.empty


# =========================================================================
# 综合行为
# =========================================================================


def test_load_manifest_full_round_trip(tmp_path):
    """完整 round-trip：3 docs + 2 efs + annotation + expectations。"""
    (tmp_path / "d1.pdf").write_text("hi", encoding="utf-8")
    (tmp_path / "d2.docx").write_text("docx", encoding="utf-8")
    (tmp_path / "ann1.json").write_text("{}", encoding="utf-8")
    p = _write_manifest(tmp_path, _mk_manifest(
        docs=[
            _mk_doc(doc_id="d1", path="d1.pdf", source_type="pdf",
                   categories=["a", "b"], paired_with="d2",
                   sha256="a" * 64, annotation_file="ann1.json",
                   expectations={"element_count_by_type": {"paragraph": 5}}),
            _mk_doc(doc_id="d2", path="d2.docx", source_type="docx",
                   categories=["a"], paired_with="d1"),
        ],
        efs=[
            _mk_ef(doc_id="ef1", path="missing.txt",
                   expected_error_code="file_not_found"),
            _mk_ef(doc_id="ef2", path="bad.pdf",
                   expected_error_code="parse_failed", source_type="pdf"),
        ]
    ))
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.documents) == 2
    assert len(m.expected_failures) == 2
    # 验证第一个 doc
    d1 = m.documents[0]
    assert d1.doc_id == "d1"
    assert d1.source_type == "pdf"
    assert d1.categories == ("a", "b")
    assert d1.paired_with == "d2"
    assert d1.sha256 == "a" * 64
    assert d1.annotation_file_str == "ann1.json"
    assert d1.annotation_resolved == (tmp_path / "ann1.json").resolve()
    assert d1.expectations == {"element_count_by_type": {"paragraph": 5}}
    # 验证 ef
    ef2 = m.expected_failures[1]
    assert ef2.source_type == "pdf"
    # properties
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.content_group_count == 1  # 1 pair (d1, d2)
    assert m.categories_covered == ["a", "b"]


def test_manifest_error_subclass_of_exception():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_not_subclass_of_runtime_error():
    assert not issubclass(ManifestError, RuntimeError)


def test_manifest_error_init_with_message():
    err = ManifestError("test message")
    assert str(err) == "test message"


def test_manifest_error_init_no_args():
    err = ManifestError()
    assert str(err) == ""


def test_manifest_error_init_multiple_args():
    err = ManifestError("a", "b", "c")
    assert err.args == ("a", "b", "c")


def test_document_entry_field_count_ten():
    """DocumentEntry 应有 10 个字段（doc_id/path_str/resolved_path/source_type/sha256/categories/paired_with/annotation_file_str/annotation_resolved/expectations）。"""
    import dataclasses
    fields = dataclasses.fields(DocumentEntry)
    assert len(fields) == 10


def test_expected_failure_field_count_five():
    import dataclasses
    fields = dataclasses.fields(ExpectedFailure)
    assert len(fields) == 5


def test_manifest_field_count_five():
    import dataclasses
    fields = dataclasses.fields(Manifest)
    assert len(fields) == 5
