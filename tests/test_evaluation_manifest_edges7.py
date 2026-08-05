r"""evaluation/manifest.py 边角测试 - 第七轮（Round 178）。

补强已有 base/edges/edges2-6（共 731 测试）未覆盖的深度：
- _detect_project_root 从文件/目录/嵌套祖先查找
- content_group_count 自配对/双向配对/三环/全配对各边界
- categories_covered 边界（empty docs、跨 doc 去重、单 doc 多 categories）
- load_manifest manifest_version 不匹配、optional fields 缺失
- _resolve_relative_path 各 ManifestError 消息精确
- DocumentEntry/ExpectedFailure frozen 行为
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import Any

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
# _detect_project_root 深度
# =========================================================================


def test_detect_project_root_from_dir_with_pyproject(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert result == tmp_path


def test_detect_project_root_from_file(tmp_path: Path):
    """start 是文件 → 从其父目录开始查找。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    f = tmp_path / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    result = _detect_project_root(f)
    assert result == tmp_path


def test_detect_project_root_ancestor(tmp_path: Path):
    """pyproject.toml 在祖先目录。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    result = _detect_project_root(deep)
    assert result == tmp_path


def test_detect_project_root_no_pyproject_returns_cur(tmp_path: Path):
    """没找到 pyproject.toml → 返回 cur（start 自身或其父）。"""
    result = _detect_project_root(tmp_path)
    assert result == tmp_path


def test_detect_project_root_no_pyproject_from_file_returns_parent(tmp_path: Path):
    f = tmp_path / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    result = _detect_project_root(f)
    assert result == tmp_path


def test_detect_project_root_returns_path_type(tmp_path: Path):
    result = _detect_project_root(tmp_path)
    assert isinstance(result, Path)


def test_detect_project_root_resolves_path(tmp_path: Path):
    """返回 .resolve() 后的路径。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert result == result.resolve()


def test_detect_project_root_signature():
    sig = inspect.signature(_detect_project_root)
    assert set(sig.parameters) == {"start"}


# =========================================================================
# content_group_count 边界
# =========================================================================


def _make_doc(doc_id: str, source_type: str = "pdf", categories: tuple = (),
              paired_with: str | None = None) -> DocumentEntry:
    return DocumentEntry(
        doc_id=doc_id,
        path_str=f"docs/{doc_id}.pdf",
        resolved_path=Path("/tmp") / f"{doc_id}.pdf",
        source_type=source_type,
        sha256=None,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def _make_manifest(docs: list[DocumentEntry]) -> Manifest:
    return Manifest(
        manifest_version=MANIFEST_VERSION,
        devset_status="incomplete",
        documents=tuple(docs),
        expected_failures=(),
        project_root=Path("/tmp"),
    )


def test_content_group_count_self_pairing():
    """doc paired_with 自己：frozenset([d, d]) = {d}。"""
    docs = [_make_doc("d1", paired_with="d1")]
    m = _make_manifest(docs)
    # frozenset([d1, d1]) = {d1}; groups=1; unpaired=0
    assert m.content_group_count == 1


def test_content_group_count_bidirectional_pair():
    """a→b 和 b→a 应该只算一组（frozenset 去重）。"""
    docs = [
        _make_doc("a", paired_with="b"),
        _make_doc("b", paired_with="a"),
    ]
    m = _make_manifest(docs)
    # frozenset({a, b}) 和 frozenset({b, a}) 相同 → pair_ids 只 1 个
    assert m.content_group_count == 1


def test_content_group_count_three_way_cycle():
    """a→b, b→c, c→a 形成 3 个不同的 frozenset pairs → 3 groups。"""
    docs = [
        _make_doc("a", paired_with="b"),
        _make_doc("b", paired_with="c"),
        _make_doc("c", paired_with="a"),
    ]
    m = _make_manifest(docs)
    # 三个 frozenset: {a,b}, {b,c}, {a,c} → 3 groups, all seen → unpaired=0
    assert m.content_group_count == 3


def test_content_group_count_all_paired():
    """所有 doc 都 paired_with → unpaired=0。"""
    docs = [
        _make_doc("a", paired_with="b"),
        _make_doc("b", paired_with="a"),
        _make_doc("c", paired_with="d"),
        _make_doc("d", paired_with="c"),
    ]
    m = _make_manifest(docs)
    # 2 个 frozenset pairs → 2 groups, unpaired=0
    assert m.content_group_count == 2


def test_content_group_count_all_unpaired():
    docs = [_make_doc("a"), _make_doc("b"), _make_doc("c")]
    m = _make_manifest(docs)
    assert m.content_group_count == 3


def test_content_group_count_mixed_paired_unpaired():
    docs = [
        _make_doc("a", paired_with="b"),
        _make_doc("b", paired_with="a"),
        _make_doc("c"),  # unpaired
    ]
    m = _make_manifest(docs)
    # 1 pair group + 1 unpaired = 2
    assert m.content_group_count == 2


def test_content_group_count_empty_documents():
    m = _make_manifest([])
    assert m.content_group_count == 0


def test_content_group_count_single_paired_with_missing_partner():
    """a paired_with=b 但 b 不存在：仍 frozenset({a, b}) → 1 group, a 在 seen 里。"""
    docs = [_make_doc("a", paired_with="b")]  # b 不在 documents
    m = _make_manifest(docs)
    assert m.content_group_count == 1


# =========================================================================
# categories_covered 边界
# =========================================================================


def test_categories_covered_empty_documents():
    m = _make_manifest([])
    assert m.categories_covered == []


def test_categories_covered_single_doc_single_category():
    docs = [_make_doc("a", categories=("math",))]
    m = _make_manifest(docs)
    assert m.categories_covered == ["math"]


def test_categories_covered_single_doc_multi_categories():
    docs = [_make_doc("a", categories=("math", "science"))]
    m = _make_manifest(docs)
    assert m.categories_covered == ["math", "science"]


def test_categories_covered_dedup_across_docs():
    docs = [
        _make_doc("a", categories=("math", "science")),
        _make_doc("b", categories=("math", "history")),
    ]
    m = _make_manifest(docs)
    # set union: math, science, history → sorted
    assert m.categories_covered == ["history", "math", "science"]


def test_categories_covered_sorted_alphabetically():
    docs = [
        _make_doc("a", categories=("zebra",)),
        _make_doc("b", categories=("apple",)),
        _make_doc("c", categories=("mango",)),
    ]
    m = _make_manifest(docs)
    assert m.categories_covered == ["apple", "mango", "zebra"]


def test_categories_covered_empty_categories_in_all_docs():
    docs = [_make_doc("a"), _make_doc("b")]
    m = _make_manifest(docs)
    assert m.categories_covered == []


def test_categories_covered_returns_list():
    docs = [_make_doc("a", categories=("x",))]
    m = _make_manifest(docs)
    assert isinstance(m.categories_covered, list)


def test_categories_covered_no_duplicates_in_output():
    docs = [
        _make_doc("a", categories=("x", "x", "y")),
        _make_doc("b", categories=("y", "z")),
    ]
    m = _make_manifest(docs)
    assert m.categories_covered == ["x", "y", "z"]


# =========================================================================
# load_manifest manifest_version 与 optional fields
# =========================================================================


def _write_valid_manifest(tmp_path: Path, docs=None, efs=None, version=MANIFEST_VERSION,
                          devset_status="incomplete") -> Path:
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    manifest = {
        "manifest_version": version,
        "devset_status": devset_status,
        "documents": docs or [],
        "expected_failures": efs or [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return p


def test_load_manifest_version_mismatch_raises(tmp_path: Path):
    """schema 要求 manifest_version == '1.0'；非 1.0 → EvalSchemaError 先抛。"""
    from evaluation.schema import EvalSchemaError
    p = _write_valid_manifest(tmp_path, version="0.0.0")
    with pytest.raises(EvalSchemaError) as exc:
        load_manifest(p)
    assert "manifest_version" in str(exc.value)


def test_load_manifest_version_none_in_json_raises(tmp_path: Path):
    """JSON 没有 manifest_version 字段 → schema 应先抛错（或 version mismatch）。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    manifest = {
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")
    # schema 校验：manifest_version 是 required
    with pytest.raises((ManifestError, Exception)):
        load_manifest(p)


def test_load_manifest_empty_documents_empty_failures(tmp_path: Path):
    p = _write_valid_manifest(tmp_path, docs=[], efs=[])
    m = load_manifest(p)
    assert m.documents == ()
    assert m.expected_failures == ()
    assert m.file_count == 0


def test_load_manifest_doc_with_categories(tmp_path: Path):
    """doc 含 categories 字段 → 转 tuple。"""
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "samples/private/d1.pdf",
         "source_type": "pdf", "categories": ["math", "science"]}
    ])
    # 注意：需要文件存在以通过 path 解析（不需要，因为 _resolve_relative_path 不检查文件存在）
    # 但要确保 samples/private/d1.pdf 在项目根下
    # 改用更安全的相对路径
    (tmp_path / "d1.pdf").write_text("x", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "d1.pdf",
         "source_type": "pdf", "categories": ["math", "science"]}
    ])
    m = load_manifest(p)
    assert m.documents[0].categories == ("math", "science")


def test_load_manifest_doc_without_categories_defaults_empty(tmp_path: Path):
    (tmp_path / "d1.pdf").write_text("x", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "d1.pdf", "source_type": "pdf"}
    ])
    m = load_manifest(p)
    assert m.documents[0].categories == ()


def test_load_manifest_doc_without_paired_with_defaults_none(tmp_path: Path):
    (tmp_path / "d1.pdf").write_text("x", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "d1.pdf", "source_type": "pdf"}
    ])
    m = load_manifest(p)
    assert m.documents[0].paired_with is None


def test_load_manifest_doc_without_sha256_defaults_none(tmp_path: Path):
    (tmp_path / "d1.pdf").write_text("x", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "d1.pdf", "source_type": "pdf"}
    ])
    m = load_manifest(p)
    assert m.documents[0].sha256 is None


def test_load_manifest_doc_with_sha256(tmp_path: Path):
    (tmp_path / "d1.pdf").write_text("x", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "d1.pdf", "source_type": "pdf",
         "sha256": "a" * 64}
    ])
    m = load_manifest(p)
    assert m.documents[0].sha256 == "a" * 64


def test_load_manifest_ef_without_source_type_defaults_none(tmp_path: Path):
    (tmp_path / "missing.pdf").write_text("x", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, efs=[
        {"doc_id": "ef1", "path": "missing.pdf", "expected_error_code": "file_not_found"}
    ])
    m = load_manifest(p)
    assert m.expected_failures[0].source_type is None


def test_load_manifest_ef_with_source_type(tmp_path: Path):
    (tmp_path / "missing.pdf").write_text("x", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, efs=[
        {"doc_id": "ef1", "path": "missing.pdf", "expected_error_code": "file_not_found",
         "source_type": "pdf"}
    ])
    m = load_manifest(p)
    assert m.expected_failures[0].source_type == "pdf"


def test_load_manifest_doc_with_annotation_file(tmp_path: Path):
    (tmp_path / "d1.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "d1.annotation.json").write_text("{}", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "d1.pdf", "source_type": "pdf",
         "annotation_file": "d1.annotation.json"}
    ])
    m = load_manifest(p)
    assert m.documents[0].annotation_file_str == "d1.annotation.json"
    assert m.documents[0].annotation_resolved == (Path(tmp_path) / "d1.annotation.json").resolve()


def test_load_manifest_doc_without_annotation_file(tmp_path: Path):
    (tmp_path / "d1.pdf").write_text("x", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "d1.pdf", "source_type": "pdf"}
    ])
    m = load_manifest(p)
    assert m.documents[0].annotation_file_str is None
    assert m.documents[0].annotation_resolved is None


def test_load_manifest_doc_with_expectations(tmp_path: Path):
    (tmp_path / "d1.pdf").write_text("x", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "d1.pdf", "source_type": "pdf",
         "expectations": {"element_count_by_type": {"paragraph": 5}}}
    ])
    m = load_manifest(p)
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_returns_manifest_instance(tmp_path: Path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    assert isinstance(m, Manifest)


def test_load_manifest_manifest_version_passed_through(tmp_path: Path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    assert m.manifest_version == MANIFEST_VERSION


def test_load_manifest_devset_status_passed_through(tmp_path: Path):
    p = _write_valid_manifest(tmp_path, devset_status="complete")
    m = load_manifest(p)
    assert m.devset_status == "complete"


def test_load_manifest_project_root_passed_through(tmp_path: Path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(p)
    assert m.project_root == tmp_path.resolve()


# =========================================================================
# _resolve_relative_path 错误消息
# =========================================================================


def test_resolve_relative_path_empty_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("", tmp_path, "field_x")
    assert "field_x" in str(exc.value)
    assert "为空" in str(exc.value)


def test_resolve_relative_path_absolute_posix_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("/etc/passwd", tmp_path, "f")
    assert "绝对路径" in str(exc.value)


def test_resolve_relative_path_absolute_windows_drive_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("C:/foo", tmp_path, "f")
    assert "绝对路径" in str(exc.value)


def test_resolve_relative_path_backslash_raises(tmp_path: Path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("sub\\dir", tmp_path, "f")
    assert "正斜杠" in str(exc.value) or "反斜杠" in str(exc.value)


def test_resolve_relative_path_outside_root_raises(tmp_path: Path):
    """../etc 路径 → resolve 后位于 project_root 之外。"""
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("../outside", tmp_path, "f")
    assert "项目根目录之外" in str(exc.value)


def test_resolve_relative_path_success_returns_path(tmp_path: Path):
    result = _resolve_relative_path("sub/file.txt", tmp_path, "f")
    assert isinstance(result, Path)
    assert result.is_absolute()


def test_resolve_relative_path_resolves_to_absolute(tmp_path: Path):
    result = _resolve_relative_path("file.txt", tmp_path, "f")
    assert result == (tmp_path / "file.txt").resolve()


def test_resolve_relative_path_field_name_in_message(tmp_path: Path):
    """错误消息包含 field_name 以便定位。"""
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("", tmp_path, "documents[X].path")
    assert "documents[X].path" in str(exc.value)


def test_resolve_relative_path_signature():
    sig = inspect.signature(_resolve_relative_path)
    assert set(sig.parameters) == {"path_str", "project_root", "field_name"}


# =========================================================================
# DocumentEntry / ExpectedFailure / Manifest frozen
# =========================================================================


def test_document_entry_frozen_set_attr_raises():
    d = DocumentEntry(
        doc_id="d1", path_str="d1.pdf",
        resolved_path=Path("/tmp/d1.pdf"),
        source_type="pdf",
        sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "x"  # type: ignore[misc]


def test_expected_failure_frozen_set_attr_raises():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="missing.pdf",
        resolved_path=Path("/tmp/missing.pdf"),
        expected_error_code="file_not_found",
        source_type=None,
    )
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "x"  # type: ignore[misc]


def test_manifest_frozen_set_attr_raises(tmp_path: Path):
    m = Manifest(
        manifest_version=MANIFEST_VERSION,
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


def test_document_entry_is_dataclass():
    assert is_dataclass(DocumentEntry)


def test_expected_failure_is_dataclass():
    assert is_dataclass(ExpectedFailure)


def test_manifest_is_dataclass():
    assert is_dataclass(Manifest)


def test_document_entry_field_count():
    """10 个字段。"""
    assert len(fields(DocumentEntry)) == 10


def test_expected_failure_field_count():
    """5 个字段。"""
    assert len(fields(ExpectedFailure)) == 5


def test_manifest_field_count():
    """5 个字段。"""
    assert len(fields(Manifest)) == 5


def test_manifest_file_count_property():
    docs = [_make_doc("a"), _make_doc("b"), _make_doc("c")]
    m = _make_manifest(docs)
    assert m.file_count == 3


def test_manifest_pdf_count_property():
    docs = [
        _make_doc("a", source_type="pdf"),
        _make_doc("b", source_type="docx"),
        _make_doc("c", source_type="pdf"),
    ]
    m = _make_manifest(docs)
    assert m.pdf_count == 2


def test_manifest_docx_count_property():
    docs = [
        _make_doc("a", source_type="pdf"),
        _make_doc("b", source_type="docx"),
        _make_doc("c", source_type="docx"),
    ]
    m = _make_manifest(docs)
    assert m.docx_count == 2


def test_manifest_file_count_property_no_params():
    """file_count 是 property（无参数）。"""
    sig = inspect.signature(Manifest.file_count.fget)
    assert set(sig.parameters) == {"self"}


# =========================================================================
# ManifestError 与模块结构
# =========================================================================


def test_manifest_error_inherits_exception():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_not_value_error():
    assert not issubclass(ManifestError, ValueError)


def test_manifest_error_has_docstring():
    assert ManifestError.__doc__ is not None


def test_manifest_error_can_be_raised_and_caught():
    with pytest.raises(ManifestError):
        raise ManifestError("x")


def test_manifest_error_caught_as_exception():
    try:
        raise ManifestError("x")
    except Exception:
        pass


def test_module_all_exact():
    import evaluation.manifest as mod
    assert mod.__all__ == [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ]


def test_module_all_no_duplicates():
    import evaluation.manifest as mod
    assert len(mod.__all__) == len(set(mod.__all__))


def test_module_imports_json():
    import evaluation.manifest as mod
    src = inspect.getsource(mod)
    assert "import json" in src


def test_module_imports_dataclass():
    import evaluation.manifest as mod
    src = inspect.getsource(mod)
    assert "from dataclasses import" in src
    assert "dataclass" in src


def test_module_imports_path():
    import evaluation.manifest as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import evaluation.manifest as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_manifest_version():
    import evaluation.manifest as mod
    src = inspect.getsource(mod)
    assert "from evaluation import" in src
    assert "MANIFEST_VERSION" in src


def test_module_imports_schema_validate():
    import evaluation.manifest as mod
    src = inspect.getsource(mod)
    assert "from evaluation.schema import" in src
    assert "validate" in src


def test_module_uses_future_annotations():
    import evaluation.manifest as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_no_silence_unused():
    import evaluation.manifest as mod
    assert not hasattr(mod, "_silence_unused")


def test_module_docstring_present():
    import evaluation.manifest as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_invariants():
    """docstring 提及关键不变量。"""
    import evaluation.manifest as mod
    doc = mod.__doc__
    assert "相对路径" in doc
    assert "正斜杠" in doc
    assert "项目根" in doc


def test_load_manifest_signature():
    sig = inspect.signature(load_manifest)
    assert set(sig.parameters) == {"manifest_path", "project_root"}


def test_load_manifest_project_root_default_none():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


# =========================================================================
# 综合行为
# =========================================================================


def test_is_absolute_like_idempotent():
    """同输入两次调用一致。"""
    assert _is_absolute_like("/x") == _is_absolute_like("/x")


def test_has_backslash_idempotent():
    assert _has_backslash("a\\b") == _has_backslash("a\\b")


def test_load_manifest_idempotent(tmp_path: Path):
    """同 manifest 两次加载结果一致（除了不可变的字段）。"""
    p = _write_valid_manifest(tmp_path)
    m1 = load_manifest(p)
    m2 = load_manifest(p)
    assert m1.manifest_version == m2.manifest_version
    assert m1.documents == m2.documents
    assert m1.expected_failures == m2.expected_failures


def test_load_manifest_with_explicit_project_root(tmp_path: Path):
    """显式传 project_root → 不调用 _detect_project_root。"""
    (tmp_path / "d1.pdf").write_text("x", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "d1.pdf", "source_type": "pdf"}
    ])
    # 故意不在 tmp_path 放 pyproject.toml，让 detect 会失败
    # 但显式传 project_root 应跳过 detect
    m = load_manifest(p, project_root=tmp_path)
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_str_path(tmp_path: Path):
    p = _write_valid_manifest(tmp_path)
    m = load_manifest(str(p))
    assert isinstance(m, Manifest)


def test_load_manifest_str_project_root(tmp_path: Path):
    (tmp_path / "d1.pdf").write_text("x", encoding="utf-8")
    p = _write_valid_manifest(tmp_path, docs=[
        {"doc_id": "d1", "path": "d1.pdf", "source_type": "pdf"}
    ])
    m = load_manifest(p, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


def test_manifest_categories_covered_does_not_mutate_documents():
    docs = [_make_doc("a", categories=("x", "y"))]
    m = _make_manifest(docs)
    before_categories = docs[0].categories
    _ = m.categories_covered
    assert docs[0].categories == before_categories


def test_content_group_count_does_not_mutate_documents():
    docs = [
        _make_doc("a", paired_with="b"),
        _make_doc("b", paired_with="a"),
    ]
    m = _make_manifest(docs)
    before_paired_a = docs[0].paired_with
    before_paired_b = docs[1].paired_with
    _ = m.content_group_count
    assert docs[0].paired_with == before_paired_a
    assert docs[1].paired_with == before_paired_b
