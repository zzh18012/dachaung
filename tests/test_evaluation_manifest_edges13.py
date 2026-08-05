r"""evaluation/manifest.py 边角测试 - 第十三轮（Round 233）。

补强已有 base/edges/edges2-12（共 ~1378 测试）未覆盖的深度：
- _is_absolute_like：3 字符边界、4 字符组合、混合 case alpha、字符串第 [0]/[1]/[2] 位
- _has_backslash：与 forward slash 混合
- _resolve_relative_path：path_str 同时含正反斜杠；多层 subdir；path_str 是 dot/dotdot 混合
- DocumentEntry/ExpectedFailure/Manifest：dataclasses.fields() 字段名/类型精确
- Manifest properties：返回类型；每次调用返回新对象
- load_manifest：manifest 中 expectations 是 None / list / scalar；annotation_file 是 None
- module：__all__ 顺序；ManifestError 文档字符串
"""

from __future__ import annotations

import json
from dataclasses import fields, replace
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
from evaluation.schema import EvalSchemaError


# =========================================================================
# _is_absolute_like 深度补强
# =========================================================================


def test_is_absolute_like_three_char_alpha_lower_slash():
    """3 char 'a:/' → True。"""
    assert _is_absolute_like("a:/") is True


def test_is_absolute_like_three_char_alpha_upper_slash():
    assert _is_absolute_like("Z:/") is True


def test_is_absolute_like_three_char_alpha_lower_backslash():
    assert _is_absolute_like("a:\\") is True


def test_is_absolute_like_four_char_alpha_filename():
    """4 char 'a:/x' → True。"""
    assert _is_absolute_like("a:/x") is True


def test_is_absolute_like_three_char_alpha_no_separator():
    """3 char 'a:b' → False（无 \\ 或 /）。"""
    assert _is_absolute_like("a:b") is False


def test_is_absolute_like_three_char_digit_slash():
    """3 char '1:/' → False（first char 不是 alpha）。"""
    assert _is_absolute_like("1:/") is False


def test_is_absolute_like_two_char_alpha_colon():
    """2 char 'a:' → False（len < 3）。"""
    assert _is_absolute_like("a:") is False


def test_is_absolute_like_three_char_underscore_drive():
    """3 char '_:/' → False（_ 不是 alpha）。"""
    assert _is_absolute_like("_:/") is False


def test_is_absolute_like_three_char_dash_drive():
    """3 char '-:/' → False。"""
    assert _is_absolute_like("-:/") is False


def test_is_absolute_like_three_char_dot_drive():
    """3 char '.:/' → False。"""
    assert _is_absolute_like(".:/") is False


def test_is_absolute_like_mixed_case_drive():
    """中:/' 仍是 alpha → True。"""
    # 中.isalpha() True
    assert _is_absolute_like("中:/") is True


def test_is_absolute_like_unicode_alpha_drive():
    """日:/' 仍是 alpha → True。"""
    assert _is_absolute_like("日:/") is True


def test_is_absolute_like_just_a_slash():
    """'/' 单字符 → startswith('/') True。"""
    assert _is_absolute_like("/") is True


def test_is_absolute_like_just_a_colon():
    assert _is_absolute_like(":") is False


def test_is_absolute_like_three_char_second_not_colon():
    """3 char 'abc' → path_str[1] != ':' → False。"""
    assert _is_absolute_like("abc") is False


def test_is_absolute_like_three_char_first_alpha_third_not_separator():
    """3 char 'a:b' → [2] = 'b' not in ('\\', '/') → False。"""
    assert _is_absolute_like("a:b") is False


# =========================================================================
# _has_backslash 深度补强
# =========================================================================


def test_has_backslash_only_forward_slashes_false():
    """path 全 forward slash → False。"""
    assert _has_backslash("a/b/c") is False


def test_has_backslash_forward_then_back_true():
    """先 / 后 \\ → True。"""
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_back_then_forward_true():
    assert _has_backslash("a\\b/c") is True


def test_has_backslash_just_one_backslash_true():
    assert _has_backslash("\\") is True


def test_has_backslash_just_one_forward_slash_false():
    assert _has_backslash("/") is False


def test_has_backslash_empty_string_false():
    assert _has_backslash("") is False


def test_has_backslash_unicode_with_backslash_true():
    assert _has_backslash("中文\\path") is True


# =========================================================================
# _resolve_relative_path 深度补强
# =========================================================================


def test_resolve_relative_path_mixed_slashes_raises(tmp_path: Path):
    """path_str 含正反斜杠 → 触发 backslash 校验。"""
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("a/b\\c", tmp_path, "test")
    assert "正斜杠" in str(ei.value) or "反斜杠" in str(ei.value)


def test_resolve_relative_path_only_backslash_after_first_check(tmp_path: Path):
    """path_str 'a\\b/c' → backslash 在前；先抛 backslash 错。"""
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("a\\b/c", tmp_path, "test")
    assert "反斜杠" in str(ei.value)


def test_resolve_relative_path_three_level_subdir(tmp_path: Path):
    """多层 subdir 路径。"""
    result = _resolve_relative_path("a/b/c/d.txt", tmp_path, "test")
    assert result == (tmp_path / "a" / "b" / "c" / "d.txt").resolve()


def test_resolve_relative_path_root_level_file(tmp_path: Path):
    """根目录下的文件。"""
    result = _resolve_relative_path("file.txt", tmp_path, "test")
    assert result == (tmp_path / "file.txt").resolve()


def test_resolve_relative_path_with_dot_in_middle(tmp_path: Path):
    """'a/./b/file.txt' → resolve 后 . 折叠。"""
    result = _resolve_relative_path("a/./b/file.txt", tmp_path, "test")
    expected = (tmp_path / "a" / "b" / "file.txt").resolve()
    assert result == expected


def test_resolve_relative_path_with_double_dot_in_middle(tmp_path: Path):
    """'a/b/../c/file.txt' → resolve 后 .. 折叠（仍在 root 内）。"""
    result = _resolve_relative_path("a/b/../c/file.txt", tmp_path, "test")
    expected = (tmp_path / "a" / "c" / "file.txt").resolve()
    assert result == expected


def test_resolve_relative_path_trailing_slash(tmp_path: Path):
    """'dir/' → resolve 成 dir（Path 不在意 trailing slash）。"""
    result = _resolve_relative_path("dir/", tmp_path, "test")
    assert result == (tmp_path / "dir").resolve() or result == (tmp_path / "dir").resolve()


def test_resolve_relative_path_multiple_consecutive_slashes(tmp_path: Path):
    """'a//b' → resolve 折叠。"""
    result = _resolve_relative_path("a//b", tmp_path, "test")
    expected = (tmp_path / "a" / "b").resolve()
    assert result == expected


def test_resolve_relative_path_filename_with_dots(tmp_path: Path):
    """'.file' 隐藏文件。"""
    result = _resolve_relative_path(".hidden", tmp_path, "test")
    assert result == (tmp_path / ".hidden").resolve()


def test_resolve_relative_path_filename_with_spaces(tmp_path: Path):
    """文件名含空格。"""
    result = _resolve_relative_path("my file.txt", tmp_path, "test")
    assert result == (tmp_path / "my file.txt").resolve()


def test_resolve_relative_path_filename_with_unicode(tmp_path: Path):
    """文件名含中文。"""
    result = _resolve_relative_path("文档.pdf", tmp_path, "test")
    assert result == (tmp_path / "文档.pdf").resolve()


def test_resolve_relative_path_returns_path_type(tmp_path: Path):
    result = _resolve_relative_path("file.txt", tmp_path, "test")
    assert isinstance(result, Path)


def test_resolve_relative_path_field_name_in_error_empty():
    """空 path_str → error 消息含 field_name。"""
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", Path("/tmp"), "myfield")
    assert "myfield" in str(ei.value)


def test_resolve_relative_path_field_name_in_error_absolute():
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("/foo", Path("/tmp"), "myfield")
    assert "myfield" in str(ei.value)


def test_resolve_relative_path_field_name_in_error_backslash():
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("a\\b", Path("/tmp"), "myfield")
    assert "myfield" in str(ei.value)


# =========================================================================
# DocumentEntry 字段精确
# =========================================================================


def test_document_entry_field_names_exact():
    """DocumentEntry 字段名按顺序精确。"""
    field_names = [f.name for f in fields(DocumentEntry)]
    assert field_names == [
        "doc_id", "path_str", "resolved_path", "source_type",
        "sha256", "categories", "paired_with", "annotation_file_str",
        "annotation_resolved", "expectations",
    ]


def test_document_entry_field_count_exact_ten():
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_field_types():
    """字段类型（直接读 dataclass 字段定义）。"""
    field_types = {f.name: f.type for f in fields(DocumentEntry)}
    assert "doc_id" in field_types
    assert "path_str" in field_types
    assert "resolved_path" in field_types


def test_document_entry_with_minimal_fields(project_root: Path):
    """DocumentEntry 只给必需字段。"""
    de = DocumentEntry(
        doc_id="d1",
        path_str="x.pdf",
        resolved_path=project_root / "x.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    assert de.doc_id == "d1"
    assert de.sha256 is None
    assert de.categories == ()


# =========================================================================
# ExpectedFailure 字段精确
# =========================================================================


def test_expected_failure_field_names_exact():
    field_names = [f.name for f in fields(ExpectedFailure)]
    assert field_names == [
        "doc_id", "path_str", "resolved_path",
        "expected_error_code", "source_type",
    ]


def test_expected_failure_field_count_exact_five():
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_with_minimal_fields(project_root: Path):
    ef = ExpectedFailure(
        doc_id="ef1",
        path_str="bad.pdf",
        resolved_path=project_root / "bad.pdf",
        expected_error_code="parse_failed",
        source_type=None,
    )
    assert ef.doc_id == "ef1"
    assert ef.source_type is None


# =========================================================================
# Manifest 字段精确
# =========================================================================


def test_manifest_field_names_exact():
    field_names = [f.name for f in fields(Manifest)]
    assert field_names == [
        "manifest_version", "devset_status", "documents",
        "expected_failures", "project_root",
    ]


def test_manifest_field_count_exact_five():
    assert len(fields(Manifest)) == 5


# =========================================================================
# Manifest properties 返回类型
# =========================================================================


def test_manifest_file_count_returns_int():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("."),
    )
    assert isinstance(m.file_count, int)


def test_manifest_pdf_count_returns_int():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("."),
    )
    assert isinstance(m.pdf_count, int)


def test_manifest_docx_count_returns_int():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("."),
    )
    assert isinstance(m.docx_count, int)


def test_manifest_content_group_count_returns_int():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("."),
    )
    assert isinstance(m.content_group_count, int)


def test_manifest_categories_covered_returns_list():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("."),
    )
    assert isinstance(m.categories_covered, list)


def test_manifest_categories_covered_returns_new_list_each_call():
    """categories_covered 多次调用应返回独立 list（sorted 总返回新对象）。"""
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("."),
    )
    l1 = m.categories_covered
    l2 = m.categories_covered
    assert l1 == l2
    assert l1 is not l2


def test_manifest_pdf_count_zero_when_no_pdfs():
    de = DocumentEntry(
        doc_id="d1", path_str="x.docx", resolved_path=Path("/x.docx"),
        source_type="docx", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(de,), expected_failures=(),
        project_root=Path("."),
    )
    assert m.pdf_count == 0
    assert m.docx_count == 1


def test_manifest_pdf_count_one_when_only_pdf():
    de = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(de,), expected_failures=(),
        project_root=Path("."),
    )
    assert m.pdf_count == 1
    assert m.docx_count == 0


def test_manifest_pdf_count_with_unknown_source_type():
    """source_type='other' → pdf_count=0 + docx_count=0。"""
    de = DocumentEntry(
        doc_id="d1", path_str="x.txt", resolved_path=Path("/x.txt"),
        source_type="other", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(de,), expected_failures=(),
        project_root=Path("."),
    )
    assert m.pdf_count == 0
    assert m.docx_count == 0


# =========================================================================
# Manifest content_group_count 算法补强
# =========================================================================


def _mk_doc(doc_id, paired_with=None, categories=()):
    return DocumentEntry(
        doc_id=doc_id, path_str=f"{doc_id}.pdf",
        resolved_path=Path(f"/{doc_id}.pdf"),
        source_type="pdf", sha256=None, categories=categories,
        paired_with=paired_with, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )


def test_content_group_count_self_pair_treated_as_one():
    """doc.paired_with == doc.doc_id → frozenset({x, x}) = {x} → 1 group。"""
    docs = (_mk_doc("a", paired_with="a"),)
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("."),
    )
    assert m.content_group_count == 1


def test_content_group_count_pair_to_nonexistent_doc():
    """a paired_with missing → frozenset({a, missing}) → 1 group; a in seen."""
    docs = (_mk_doc("a", paired_with="missing"),)
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("."),
    )
    assert m.content_group_count == 1


def test_content_group_count_chain_two_groups():
    """A→B, B→C → frozenset({a,b}) + frozenset({b,c}) → 2 groups。"""
    docs = (
        _mk_doc("a", paired_with="b"),
        _mk_doc("b", paired_with="c"),
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("."),
    )
    assert m.content_group_count == 2


def test_content_group_count_three_way_cycle_three_groups():
    """A→B, B→C, C→A → 3 frozensets → 3 groups（去重仍 3，因 {a,b} ≠ {b,c} ≠ {c,a}）。"""
    docs = (
        _mk_doc("a", paired_with="b"),
        _mk_doc("b", paired_with="c"),
        _mk_doc("c", paired_with="a"),
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("."),
    )
    assert m.content_group_count == 3


def test_content_group_count_bidirectional_pair_one_group():
    """A→B, B→A → frozenset({a,b}) + frozenset({a,b}) = set 去重 → 1 group。"""
    docs = (
        _mk_doc("a", paired_with="b"),
        _mk_doc("b", paired_with="a"),
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("."),
    )
    assert m.content_group_count == 1


def test_content_group_count_two_disjoint_pairs_two_groups():
    docs = (
        _mk_doc("a", paired_with="b"),
        _mk_doc("b", paired_with="a"),
        _mk_doc("c", paired_with="d"),
        _mk_doc("d", paired_with="c"),
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("."),
    )
    assert m.content_group_count == 2


def test_content_group_count_pair_plus_unpaired():
    docs = (
        _mk_doc("a", paired_with="b"),
        _mk_doc("b"),
        _mk_doc("c"),
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("."),
    )
    # 1 pair group + 1 unpaired (c) = 2
    # 注意：b 在 frozenset seen 里，所以 b 不算 unpaired
    assert m.content_group_count == 2


# =========================================================================
# Manifest categories_covered 算法补强
# =========================================================================


def test_categories_covered_dedup_within_doc_one_per_call():
    """一个 doc 含重复 categories → set 去重。"""
    de = _mk_doc("a", categories=("x", "x", "y"))
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(de,), expected_failures=(),
        project_root=Path("."),
    )
    assert m.categories_covered == ["x", "y"]


def test_categories_covered_case_sensitive_sort():
    """sorted 是大小写敏感：'B' < 'a'。"""
    de = _mk_doc("a", categories=("b", "A", "a", "B"))
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(de,), expected_failures=(),
        project_root=Path("."),
    )
    # sorted(['a', 'A', 'b', 'B']) → ['A', 'B', 'a', 'b']
    assert m.categories_covered == ["A", "B", "a", "b"]


def test_categories_covered_unicode_sort():
    """unicode categories 也按 sorted 排序。"""
    de = _mk_doc("a", categories=("中", "文", "类", "目"))
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(de,), expected_failures=(),
        project_root=Path("."),
    )
    assert m.categories_covered == sorted(["中", "文", "类", "目"])


# =========================================================================
# ManifestError 文档字符串
# =========================================================================


def test_manifest_error_has_docstring():
    assert ManifestError.__doc__ is not None
    assert len(ManifestError.__doc__) > 0


def test_manifest_error_docstring_contains_keyword():
    """docstring 应提到 '清单' 或 'manifest'。"""
    assert "清单" in ManifestError.__doc__ or "manifest" in ManifestError.__doc__.lower()


def test_manifest_error_init_no_args():
    """ManifestError() 无参数。"""
    err = ManifestError()
    assert str(err) == ""


def test_manifest_error_init_with_empty_string():
    """ManifestError('') 空字符串。"""
    err = ManifestError("")
    assert str(err) == ""


# =========================================================================
# load_manifest：expectations 多种类型
# =========================================================================


def test_load_manifest_expectations_none_rejected_by_schema(tmp_path: Path):
    """schema 拒绝 expectations: null（必须 object 或缺省）。

    manifest.schema.json 中 expectations 定义为
    ``{"type": "object", "additionalProperties": false, ...}``，
    不允许 null，故 schema 验证会先抛 EvalSchemaError，
    走不到 ``d.get("expectations")`` 那一步。
    """
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.pdf",
            "source_type": "pdf", "expectations": None,
        }],
        "expected_failures": [],
    }
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_expectations_full_dict(tmp_path: Path):
    """document 的 expectations 含完整 element_count_by_type。"""
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.pdf",
            "source_type": "pdf",
            "expectations": {
                "element_count_by_type": {"paragraph": 5, "heading": 2},
            },
        }],
        "expected_failures": [],
    }
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    m = load_manifest(p)
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 5, "heading": 2}}


def test_load_manifest_annotation_file_resolved(tmp_path: Path):
    """document 的 annotation_file 字段被解析。"""
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.pdf",
            "source_type": "pdf",
            "annotation_file": "annotations/d1.json",
        }],
        "expected_failures": [],
    }
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    m = load_manifest(p)
    assert m.documents[0].annotation_file_str == "annotations/d1.json"
    assert m.documents[0].annotation_resolved == (tmp_path / "annotations" / "d1.json").resolve()


def test_load_manifest_no_annotation_file_default_none(tmp_path: Path):
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.pdf",
            "source_type": "pdf",
        }],
        "expected_failures": [],
    }
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    m = load_manifest(p)
    assert m.documents[0].annotation_file_str is None
    assert m.documents[0].annotation_resolved is None


def test_load_manifest_paired_with_propagated(tmp_path: Path):
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "a.docx", "source_type": "docx", "paired_with": "d1"},
        ],
        "expected_failures": [],
    }
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    m = load_manifest(p)
    assert m.documents[0].paired_with == "d2"
    assert m.documents[1].paired_with == "d1"


def test_load_manifest_categories_as_list(tmp_path: Path):
    """JSON categories 是 list → 转 tuple。"""
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.pdf",
            "source_type": "pdf",
            "categories": ["research", "paper"],
        }],
        "expected_failures": [],
    }
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    m = load_manifest(p)
    assert m.documents[0].categories == ("research", "paper")
    assert isinstance(m.documents[0].categories, tuple)


def test_load_manifest_categories_default_empty(tmp_path: Path):
    """缺 categories → 默认空 tuple。"""
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.pdf",
            "source_type": "pdf",
        }],
        "expected_failures": [],
    }
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    m = load_manifest(p)
    assert m.documents[0].categories == ()


def test_load_manifest_sha256_propagated(tmp_path: Path):
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.pdf",
            "source_type": "pdf",
            "sha256": "a" * 64,
        }],
        "expected_failures": [],
    }
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    m = load_manifest(p)
    assert m.documents[0].sha256 == "a" * 64


def test_load_manifest_no_sha256_default_none(tmp_path: Path):
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.pdf",
            "source_type": "pdf",
        }],
        "expected_failures": [],
    }
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    m = load_manifest(p)
    assert m.documents[0].sha256 is None


# =========================================================================
# load_manifest：expected_failures 行为
# =========================================================================


def test_load_manifest_expected_failure_source_type_propagated(tmp_path: Path):
    """ExpectedFailure source_type 字段透传。"""
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{
            "doc_id": "ef1", "path": "bad.pdf",
            "expected_error_code": "parse_failed",
            "source_type": "pdf",
        }],
    }
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    m = load_manifest(p)
    assert m.expected_failures[0].source_type == "pdf"


def test_load_manifest_expected_failure_source_type_default_none(tmp_path: Path):
    """ExpectedFailure 缺 source_type → None。"""
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{
            "doc_id": "ef1", "path": "bad.pdf",
            "expected_error_code": "parse_failed",
        }],
    }
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    m = load_manifest(p)
    assert m.expected_failures[0].source_type is None


def test_load_manifest_expected_failure_path_resolved(tmp_path: Path):
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{
            "doc_id": "ef1", "path": "subdir/bad.pdf",
            "expected_error_code": "parse_failed",
        }],
    }
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    m = load_manifest(p)
    assert m.expected_failures[0].resolved_path == (tmp_path / "subdir" / "bad.pdf").resolve()


# =========================================================================
# 模块结构补强
# =========================================================================


def test_module_all_exact_list():
    """__all__ 是精确 list（按定义顺序）。"""
    import evaluation.manifest as m
    assert list(m.__all__) == [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ]


def test_module_all_does_not_include_internal_helpers():
    import evaluation.manifest as m
    assert "_is_absolute_like" not in m.__all__
    assert "_has_backslash" not in m.__all__
    assert "_resolve_relative_path" not in m.__all__
    assert "_detect_project_root" not in m.__all__


def test_module_all_size_five():
    import evaluation.manifest as m
    assert len(m.__all__) == 5


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


def test_module_docstring_present():
    import evaluation.manifest as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_invariants():
    """docstring 应提到关键不变量。"""
    import evaluation.manifest as m
    assert "相对路径" in m.__doc__ or "absolute" in m.__doc__.lower()


def test_module_uses_future_annotations():
    import evaluation.manifest as m
    assert hasattr(m, "annotations")
