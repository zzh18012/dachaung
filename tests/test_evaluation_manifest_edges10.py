r"""evaluation/manifest.py 边角测试 - 第十轮（Round 215）。

补强已有 base/edges/edges2-9（共 ~1084 测试）未覆盖的深度：
- Manifest properties 深度：content_group_count 多 pair / 单向 pair / 完全无 pair
- categories_covered：tuple / mixed unicode / 排序稳定性
- DocumentEntry / ExpectedFailure 字段默认值
- Manifest dataclass frozen / equality
- _detect_project_root：start 是根目录 / 多层嵌套 / 跨链
- _resolve_relative_path：深层 dotdot / 双斜杠 / 末尾斜杠
- load_manifest：annotation_file 解析 / expectations 传播 / sha256 传播
- load_manifest：paired_with 传播
- load_manifest：manifest_version mismatch
- load_manifest：Schema 校验失败传播 EvalSchemaError
- load_manifest：devset_status 各种取值
- 模块结构 / __all__ / imports 深度
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

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
from evaluation.schema import EvalSchemaError


# =========================================================================
# 共用辅助
# =========================================================================


def _mk_doc(doc_id="d1", path_str="x.txt", source_type="text",
            categories=None, paired_with=None, sha256=None,
            annotation_file_str=None, expectations=None) -> DocumentEntry:
    return DocumentEntry(
        doc_id=doc_id,
        path_str=path_str,
        resolved_path=Path(path_str),
        source_type=source_type,
        sha256=sha256,
        categories=tuple(categories) if categories else (),
        paired_with=paired_with,
        annotation_file_str=annotation_file_str,
        annotation_resolved=Path(annotation_file_str) if annotation_file_str else None,
        expectations=expectations,
    )


def _mk_ef(doc_id="ef1", path_str="bad.txt", code="file_not_found",
           source_type=None) -> ExpectedFailure:
    return ExpectedFailure(
        doc_id=doc_id,
        path_str=path_str,
        resolved_path=Path(path_str),
        expected_error_code=code,
        source_type=source_type,
    )


def _mk_manifest(docs=None, efs=None, project_root=None) -> Manifest:
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=tuple(docs or ()),
        expected_failures=tuple(efs or ()),
        project_root=project_root or Path("."),
    )


def _write_manifest(tmp_path: Path, documents=None, expected_failures=None,
                    manifest_version="1.0", devset_status="incomplete",
                    extra_top_keys=None) -> Path:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    data = {
        "manifest_version": manifest_version,
        "devset_status": devset_status,
        "documents": documents or [],
        "expected_failures": expected_failures or [],
    }
    if extra_top_keys:
        data.update(extra_top_keys)
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# =========================================================================
# Manifest.content_group_count 深度
# =========================================================================


def test_content_group_count_no_documents_is_zero():
    m = _mk_manifest(docs=[])
    assert m.content_group_count == 0


def test_content_group_count_single_unpaired():
    m = _mk_manifest(docs=[_mk_doc(doc_id="d1")])
    assert m.content_group_count == 1


def test_content_group_count_two_unpaired():
    m = _mk_manifest(docs=[_mk_doc(doc_id="d1"), _mk_doc(doc_id="d2")])
    assert m.content_group_count == 2


def test_content_group_count_pair_counts_as_one():
    d1 = _mk_doc(doc_id="d1", paired_with="d2")
    d2 = _mk_doc(doc_id="d2", paired_with="d1")
    m = _mk_manifest(docs=[d1, d2])
    assert m.content_group_count == 1


def test_content_group_count_pair_plus_unpaired():
    d1 = _mk_doc(doc_id="d1", paired_with="d2")
    d2 = _mk_doc(doc_id="d2", paired_with="d1")
    d3 = _mk_doc(doc_id="d3")
    m = _mk_manifest(docs=[d1, d2, d3])
    assert m.content_group_count == 2


def test_content_group_count_one_directional_pair():
    """d1.paired_with=d2 但 d2 未标 → 仍按 1 组算。"""
    d1 = _mk_doc(doc_id="d1", paired_with="d2")
    d2 = _mk_doc(doc_id="d2")
    m = _mk_manifest(docs=[d1, d2])
    assert m.content_group_count == 1


def test_content_group_count_three_unpaired():
    m = _mk_manifest(docs=[
        _mk_doc(doc_id="d1"),
        _mk_doc(doc_id="d2"),
        _mk_doc(doc_id="d3"),
    ])
    assert m.content_group_count == 3


def test_content_group_count_two_disjoint_pairs():
    d1 = _mk_doc(doc_id="d1", paired_with="d2")
    d2 = _mk_doc(doc_id="d2", paired_with="d1")
    d3 = _mk_doc(doc_id="d3", paired_with="d4")
    d4 = _mk_doc(doc_id="d4", paired_with="d3")
    m = _mk_manifest(docs=[d1, d2, d3, d4])
    assert m.content_group_count == 2


def test_content_group_count_two_pairs_plus_two_unpaired():
    d1 = _mk_doc(doc_id="d1", paired_with="d2")
    d2 = _mk_doc(doc_id="d2", paired_with="d1")
    d3 = _mk_doc(doc_id="d3")
    d4 = _mk_doc(doc_id="d4")
    m = _mk_manifest(docs=[d1, d2, d3, d4])
    # 1 pair + 2 unpaired = 3
    assert m.content_group_count == 3


def test_content_group_count_pair_to_nonexistent_doc():
    """paired_with 指向不存在的 doc_id：仍按一组算（避免重复计数）。"""
    d1 = _mk_doc(doc_id="d1", paired_with="ghost")
    m = _mk_manifest(docs=[d1])
    # frozenset({d1, ghost}) → 1 组
    assert m.content_group_count == 1


def test_content_group_count_chain_a_to_b_b_to_c():
    """d1.paired_with=d2, d2.paired_with=d3 → 两个 frozenset 各算 1 组（共 2 组）。

    这是当前实现的行为：每条 paired_with 引用产生一个 frozenset，
    不会合并成 {d1, d2, d3}。
    """
    d1 = _mk_doc(doc_id="d1", paired_with="d2")
    d2 = _mk_doc(doc_id="d2", paired_with="d3")
    d3 = _mk_doc(doc_id="d3")
    m = _mk_manifest(docs=[d1, d2, d3])
    # frozenset({d1,d2}) + frozenset({d2,d3}) → 2 组
    assert m.content_group_count == 2


def test_content_group_count_self_pair():
    """doc_id paired_with itself → frozenset({d1, d1}) = {d1} → 1 组。"""
    d1 = _mk_doc(doc_id="d1", paired_with="d1")
    m = _mk_manifest(docs=[d1])
    assert m.content_group_count == 1


def test_content_group_count_returns_int_type():
    m = _mk_manifest(docs=[_mk_doc()])
    assert isinstance(m.content_group_count, int)


# =========================================================================
# Manifest.categories_covered 深度
# =========================================================================


def test_categories_covered_returns_list():
    m = _mk_manifest(docs=[_mk_doc(categories=["a"])])
    assert isinstance(m.categories_covered, list)


def test_categories_covered_empty_when_no_docs():
    m = _mk_manifest(docs=[])
    assert m.categories_covered == []


def test_categories_covered_empty_when_docs_no_categories():
    m = _mk_manifest(docs=[_mk_doc(), _mk_doc()])
    assert m.categories_covered == []


def test_categories_covered_single_doc_single_category():
    m = _mk_manifest(docs=[_mk_doc(categories=["text"])])
    assert m.categories_covered == ["text"]


def test_categories_covered_single_doc_multiple_categories():
    m = _mk_manifest(docs=[_mk_doc(categories=["text", "table"])])
    assert m.categories_covered == ["table", "text"]


def test_categories_covered_dedup_within_doc():
    """同 doc 内重复 category 也 dedup。"""
    m = _mk_manifest(docs=[_mk_doc(categories=["a", "a", "b"])])
    assert m.categories_covered == ["a", "b"]


def test_categories_covered_dedup_across_docs():
    m = _mk_manifest(docs=[
        _mk_doc(doc_id="d1", categories=["a", "b"]),
        _mk_doc(doc_id="d2", categories=["b", "c"]),
    ])
    assert m.categories_covered == ["a", "b", "c"]


def test_categories_covered_sorted_alphabetically():
    m = _mk_manifest(docs=[
        _mk_doc(doc_id="d1", categories=["z", "a", "m"]),
    ])
    assert m.categories_covered == ["a", "m", "z"]


def test_categories_covered_unicode_categories():
    m = _mk_manifest(docs=[_mk_doc(categories=["中文", "abc"])])
    # 排序按 Unicode 码点（ASCII 字母 < 中文）
    assert m.categories_covered == ["abc", "中文"]


def test_categories_covered_sorted_case_sensitive():
    """大写字母 ASCII < 小写 → 'Z' 排在 'a' 前。"""
    m = _mk_manifest(docs=[_mk_doc(categories=["apple", "Zebra"])])
    assert m.categories_covered == ["Zebra", "apple"]


def test_categories_covered_returns_new_list_each_call():
    m = _mk_manifest(docs=[_mk_doc(categories=["a"])])
    a = m.categories_covered
    b = m.categories_covered
    assert a == b
    assert a is not b  # 每次返回新 list


def test_categories_covered_does_not_mutate_after_sort():
    """返回的 list 应已被 sorted（不依赖外部排序）。"""
    m = _mk_manifest(docs=[_mk_doc(categories=["c", "a", "b"])])
    result = m.categories_covered
    assert result == ["a", "b", "c"]


# =========================================================================
# Manifest.pdf_count / docx_count / file_count
# =========================================================================


def test_pdf_count_zero_when_no_docs():
    m = _mk_manifest(docs=[])
    assert m.pdf_count == 0


def test_pdf_count_counts_only_pdf():
    m = _mk_manifest(docs=[
        _mk_doc(doc_id="d1", source_type="pdf"),
        _mk_doc(doc_id="d2", source_type="docx"),
        _mk_doc(doc_id="d3", source_type="pdf"),
    ])
    assert m.pdf_count == 2


def test_docx_count_counts_only_docx():
    m = _mk_manifest(docs=[
        _mk_doc(doc_id="d1", source_type="pdf"),
        _mk_doc(doc_id="d2", source_type="docx"),
        _mk_doc(doc_id="d3", source_type="docx"),
    ])
    assert m.docx_count == 2


def test_pdf_count_ignores_other_types():
    m = _mk_manifest(docs=[
        _mk_doc(doc_id="d1", source_type="text"),
        _mk_doc(doc_id="d2", source_type="html"),
    ])
    assert m.pdf_count == 0
    assert m.docx_count == 0


def test_file_count_returns_int():
    m = _mk_manifest(docs=[_mk_doc()])
    assert isinstance(m.file_count, int)


def test_file_count_zero_when_no_docs():
    m = _mk_manifest(docs=[])
    assert m.file_count == 0


# =========================================================================
# Manifest dataclass 行为
# =========================================================================


def test_manifest_is_dataclass():
    assert is_dataclass(Manifest)


def test_manifest_is_frozen():
    m = _mk_manifest(docs=[_mk_doc()])
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


def test_manifest_field_count():
    fl = fields(Manifest)
    assert len(fl) == 5


def test_manifest_field_names_exact():
    fl = fields(Manifest)
    names = [f.name for f in fl]
    assert names == [
        "manifest_version", "devset_status", "documents",
        "expected_failures", "project_root",
    ]


def test_manifest_equality_same_values():
    m1 = _mk_manifest(docs=[_mk_doc(doc_id="d1")])
    m2 = _mk_manifest(docs=[_mk_doc(doc_id="d1")])
    assert m1 == m2


def test_manifest_inequality_different_docs():
    m1 = _mk_manifest(docs=[_mk_doc(doc_id="d1")])
    m2 = _mk_manifest(docs=[_mk_doc(doc_id="d2")])
    assert m1 != m2


def test_manifest_equality_with_self():
    m = _mk_manifest(docs=[_mk_doc()])
    assert m == m


def test_manifest_hashable_when_frozen():
    """frozen dataclass 默认 hashable（如果所有字段 hashable）。"""
    m = _mk_manifest(docs=())
    # 简单 hash() 不抛异常即可（Path is hashable）
    assert isinstance(hash(m), int)


def test_manifest_replace_creates_new_instance():
    m = _mk_manifest(docs=())
    m2 = replace(m, devset_status="complete")
    assert m.devset_status == "incomplete"
    assert m2.devset_status == "complete"
    assert m is not m2


# =========================================================================
# DocumentEntry 默认值
# =========================================================================


def test_document_entry_default_sha256_is_none():
    d = _mk_doc()
    assert d.sha256 is None


def test_document_entry_default_paired_with_is_none():
    d = _mk_doc()
    assert d.paired_with is None


def test_document_entry_default_annotation_file_str_is_none():
    d = _mk_doc()
    assert d.annotation_file_str is None


def test_document_entry_default_annotation_resolved_is_none():
    d = _mk_doc()
    assert d.annotation_resolved is None


def test_document_entry_default_categories_is_empty_tuple():
    d = _mk_doc()
    assert d.categories == ()


def test_document_entry_default_expectations_is_none():
    d = _mk_doc()
    assert d.expectations is None


def test_document_entry_is_frozen():
    d = _mk_doc()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "x"  # type: ignore[misc]


def test_document_entry_field_count():
    fl = fields(DocumentEntry)
    assert len(fl) == 10


def test_document_entry_field_names_exact():
    fl = fields(DocumentEntry)
    names = [f.name for f in fl]
    assert names == [
        "doc_id", "path_str", "resolved_path", "source_type",
        "sha256", "categories", "paired_with",
        "annotation_file_str", "annotation_resolved", "expectations",
    ]


# =========================================================================
# ExpectedFailure 默认值
# =========================================================================


def test_expected_failure_default_source_type_is_none():
    ef = _mk_ef()
    assert ef.source_type is None


def test_expected_failure_is_frozen():
    ef = _mk_ef()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "x"  # type: ignore[misc]


def test_expected_failure_field_count():
    fl = fields(ExpectedFailure)
    assert len(fl) == 5


def test_expected_failure_field_names_exact():
    fl = fields(ExpectedFailure)
    names = [f.name for f in fl]
    assert names == [
        "doc_id", "path_str", "resolved_path",
        "expected_error_code", "source_type",
    ]


def test_expected_failure_equality():
    ef1 = _mk_ef(doc_id="a")
    ef2 = _mk_ef(doc_id="a")
    assert ef1 == ef2


# =========================================================================
# _detect_project_root 边界
# =========================================================================


def test_detect_project_root_returns_absolute_path(tmp_path):
    (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert result.is_absolute()


def test_detect_project_root_resolves_to_input_when_no_pyproject(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    result = _detect_project_root(sub)
    assert result == sub.resolve()


def test_detect_project_root_file_input_uses_parent(tmp_path):
    (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
    f = tmp_path / "x.txt"
    f.write_text("x", encoding="utf-8")
    result = _detect_project_root(f)
    assert result == tmp_path.resolve()


def test_detect_project_root_deeply_nested(tmp_path):
    (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    result = _detect_project_root(deep)
    assert result == tmp_path.resolve()


def test_detect_project_root_picks_nearest_when_multiple(tmp_path):
    (tmp_path / "pyproject.toml").write_text("outer", encoding="utf-8")
    inner = tmp_path / "inner"
    inner.mkdir()
    (inner / "pyproject.toml").write_text("inner", encoding="utf-8")
    result = _detect_project_root(inner)
    assert result == inner.resolve()


def test_detect_project_root_callable():
    assert callable(_detect_project_root)


# =========================================================================
# _resolve_relative_path 边界
# =========================================================================


def test_resolve_relative_path_dotdot_within_root_deep(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b").mkdir()
    (tmp_path / "c").mkdir()
    p = _resolve_relative_path("a/b/../../c", tmp_path, "f")
    assert p == (tmp_path / "c").resolve()


def test_resolve_relative_path_double_slash_collapsed(tmp_path):
    """a//b 等价于 a/b（POSIX 路径允许 //）。"""
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b").mkdir()
    p = _resolve_relative_path("a//b", tmp_path, "f")
    assert p == (tmp_path / "a" / "b").resolve()


def test_resolve_relative_path_trailing_slash(tmp_path):
    (tmp_path / "a").mkdir()
    p = _resolve_relative_path("a/", tmp_path, "f")
    assert p == (tmp_path / "a").resolve()


def test_resolve_relative_path_single_dot(tmp_path):
    """'.' 解析为 project_root 自身。"""
    p = _resolve_relative_path(".", tmp_path, "f")
    assert p == tmp_path.resolve()


def test_resolve_relative_path_dotdot_to_root_raises(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("..", tmp_path, "f")
    assert "项目根目录之外" in str(exc_info.value)


def test_resolve_relative_path_idempotent_resolve(tmp_path):
    """重复 resolve 不改变结果。"""
    (tmp_path / "a").mkdir()
    p1 = _resolve_relative_path("a", tmp_path, "f")
    p2 = _resolve_relative_path("a", tmp_path, "f")
    assert p1 == p2


# =========================================================================
# load_manifest 深度（补强 edges9）
# =========================================================================


def test_load_manifest_propagates_paired_with(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_text("a", encoding="utf-8")
    (tmp_path / "samples" / "a.docx").write_text("a", encoding="utf-8")
    p = _write_manifest(tmp_path, documents=[
        {
            "doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf",
            "categories": ["text"], "paired_with": "d2",
        },
        {
            "doc_id": "d2", "path": "samples/a.docx", "source_type": "docx",
            "categories": ["text"], "paired_with": "d1",
        },
    ])
    m = load_manifest(p)
    assert m.documents[0].paired_with == "d2"
    assert m.documents[1].paired_with == "d1"


def test_load_manifest_propagates_sha256(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_text("a", encoding="utf-8")
    sha = "0" * 64
    p = _write_manifest(tmp_path, documents=[
        {
            "doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf",
            "categories": ["text"], "sha256": sha,
        },
    ])
    m = load_manifest(p)
    assert m.documents[0].sha256 == sha


def test_load_manifest_propagates_annotation_file(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_text("a", encoding="utf-8")
    (tmp_path / "samples" / "a.annotation.json").write_text("{}", encoding="utf-8")
    p = _write_manifest(tmp_path, documents=[
        {
            "doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf",
            "categories": ["text"],
            "annotation_file": "samples/a.annotation.json",
        },
    ])
    m = load_manifest(p)
    assert m.documents[0].annotation_file_str == "samples/a.annotation.json"
    assert m.documents[0].annotation_resolved is not None
    assert m.documents[0].annotation_resolved == (tmp_path / "samples" / "a.annotation.json").resolve()


def test_load_manifest_propagates_expectations(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_text("a", encoding="utf-8")
    p = _write_manifest(tmp_path, documents=[
        {
            "doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf",
            "categories": ["text"],
            "expectations": {"element_count_by_type": {"paragraph": 5}},
        },
    ])
    m = load_manifest(p)
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_propagates_categories_as_tuple(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_text("a", encoding="utf-8")
    p = _write_manifest(tmp_path, documents=[
        {
            "doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf",
            "categories": ["text", "table"],
        },
    ])
    m = load_manifest(p)
    assert m.documents[0].categories == ("text", "table")
    assert isinstance(m.documents[0].categories, tuple)


def test_load_manifest_categories_default_empty_tuple(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_text("a", encoding="utf-8")
    p = _write_manifest(tmp_path, documents=[
        {
            "doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf",
        },
    ])
    m = load_manifest(p)
    assert m.documents[0].categories == ()


def test_load_manifest_expected_failure_with_source_type(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "bad.pdf").write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, expected_failures=[
        {
            "doc_id": "ef1", "path": "samples/bad.pdf",
            "expected_error_code": "file_not_found",
            "source_type": "pdf",
        },
    ])
    m = load_manifest(p)
    assert m.expected_failures[0].source_type == "pdf"


def test_load_manifest_expected_failure_default_source_type_none(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "bad.pdf").write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, expected_failures=[
        {
            "doc_id": "ef1", "path": "samples/bad.pdf",
            "expected_error_code": "file_not_found",
        },
    ])
    m = load_manifest(p)
    assert m.expected_failures[0].source_type is None


def test_load_manifest_manifest_version_mismatch_raises(tmp_path):
    """schema const="1.0" → 任意非 1.0 版本被 schema 拒（EvalSchemaError）。"""
    p = _write_manifest(tmp_path, manifest_version="0.0.0")
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_manifest_version_none_in_data_raises(tmp_path):
    """Schema 要求 manifest_version 必填，缺失应被 Schema 拒。"""
    (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_devset_status_variants(tmp_path):
    """schema 仅允许 ['complete', 'incomplete']。"""
    for status in ["incomplete", "complete"]:
        p = _write_manifest(tmp_path, devset_status=status)
        m = load_manifest(p)
        assert m.devset_status == status


def test_load_manifest_devset_status_invalid_rejected(tmp_path):
    """schema enum → 'partial' 被拒。"""
    p = _write_manifest(tmp_path, devset_status="partial")
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_propagates_resolved_path(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, documents=[
        {
            "doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf",
            "categories": [],
        },
    ])
    m = load_manifest(p)
    assert m.documents[0].resolved_path == (tmp_path / "samples" / "a.pdf").resolve()
    assert m.documents[0].resolved_path.is_absolute()


def test_load_manifest_path_str_preserves_original(tmp_path):
    """path_str 是 manifest 中的原始字符串（不解析）。"""
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, documents=[
        {
            "doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf",
            "categories": [],
        },
    ])
    m = load_manifest(p)
    assert m.documents[0].path_str == "samples/a.pdf"


def test_load_manifest_annotation_file_outside_root_raises(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, documents=[
        {
            "doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf",
            "categories": [],
            "annotation_file": "../outside.json",
        },
    ])
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p)
    assert "项目根目录之外" in str(exc_info.value) or "annotation_file" in str(exc_info.value)


def test_load_manifest_extra_top_level_keys_rejected(tmp_path):
    """Schema additionalProperties=False → 额外字段被拒。"""
    (tmp_path / "samples").mkdir()
    p = _write_manifest(
        tmp_path,
        extra_top_keys={"comment": "test", "version": "9.9.9"},
    )
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_path_object_project_root_str(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "a.pdf").write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path)
    m = load_manifest(p, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


# =========================================================================
# 模块结构深度（补强 edges9）
# =========================================================================


def test_module_imports_manifest_version():
    import evaluation.manifest as m
    assert hasattr(m, "MANIFEST_VERSION")


def test_module_imports_validate():
    import evaluation.manifest as m
    assert callable(m.validate)


def test_module_manifest_error_is_exception_subclass():
    assert issubclass(ManifestError, Exception)


def test_module_manifest_error_not_value_error():
    """ManifestError 直接继承 Exception，不是 ValueError。"""
    assert not issubclass(ManifestError, ValueError)


def test_module_manifest_error_not_key_error():
    assert not issubclass(ManifestError, KeyError)


def test_module_manifest_error_has_empty_default_args():
    err = ManifestError("msg")
    assert err.args == ("msg",)


def test_module_manifest_error_str():
    err = ManifestError("custom message")
    assert str(err) == "custom message"


def test_module_manifest_error_can_be_raised_and_caught():
    with pytest.raises(ManifestError) as exc_info:
        raise ManifestError("boom")
    assert "boom" in str(exc_info.value)


def test_module_manifest_error_caught_as_exception():
    with pytest.raises(Exception) as exc_info:
        raise ManifestError("boom")
    assert isinstance(exc_info.value, ManifestError)


def test_module_all_does_not_include_internal_helpers():
    """__all__ 不应暴露 _is_absolute_like / _has_backslash / _resolve_relative_path / _detect_project_root。"""
    import evaluation.manifest as m
    assert "_is_absolute_like" not in m.__all__
    assert "_has_backslash" not in m.__all__
    assert "_resolve_relative_path" not in m.__all__
    assert "_detect_project_root" not in m.__all__


def test_module_docstring_mentions_invariants():
    import evaluation.manifest as m
    doc = m.__doc__
    assert "相对路径" in doc
    assert "项目根" in doc


def test_module_uses_future_annotations():
    import evaluation.manifest as m
    sig = inspect.signature(m.load_manifest)
    assert isinstance(sig.return_annotation, str)


def test_module_load_manifest_first_param_kind():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["manifest_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_module_load_manifest_second_param_kind():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_module_load_manifest_param_count():
    sig = inspect.signature(load_manifest)
    assert len(sig.parameters) == 2
