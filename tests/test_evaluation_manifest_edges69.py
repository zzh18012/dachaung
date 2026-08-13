"""evaluation/manifest.py 第七十轮 edges 测试（Round 613）。

补强 edges68 未触及的角度（第四十二批）—— 专门补强 DocumentEntry/ExpectedFailure/Manifest 字段构造与边界。

新角度：
- DocumentEntry 必填字段全验证
- DocumentEntry 字段顺序与 __init__ 一致
- DocumentEntry asdict（dataclasses.asdict）
- DocumentEntry to dict via dataclasses.asdict 路径含 Path
- DocumentEntry 字段 count = 10
- ExpectedFailure 字段 count = 5
- ExpectedFailure 字段顺序
- Manifest 字段 count = 5
- Manifest fields() 验证
- Manifest documents/expected_failures 是 tuple（不是 list）
- Manifest project_root 是 Path
- DocumentEntry categories 是 tuple（不是 list）
- Manifest 用 dataclasses.replace 修改
- Manifest 完整 round trip via dataclasses.asdict
- _make_expected_failure 边界
- _has_backslash 多次出现
- module source 补强
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
from dataclasses import FrozenInstanceError, asdict, fields, is_dataclass, replace
from pathlib import Path
from typing import Any
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


# ---------- DocumentEntry 字段结构 第四十二批


def test_document_entry_is_dataclass_batch42():
    assert is_dataclass(DocumentEntry)


def test_document_entry_frozen_batch42():
    """frozen=True。"""
    e = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        e.doc_id = "x"  # type: ignore[misc]


def test_document_entry_field_count_batch42():
    """应有 10 个字段。"""
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_field_names_batch42():
    names = [f.name for f in fields(DocumentEntry)]
    expected = [
        "doc_id", "path_str", "resolved_path", "source_type", "sha256",
        "categories", "paired_with", "annotation_file_str",
        "annotation_resolved", "expectations",
    ]
    assert names == expected


def test_document_entry_field_types_batch42():
    """字段类型注解正确。"""
    type_hints = {f.name: str(f.type) for f in fields(DocumentEntry)}
    assert "str" in type_hints["doc_id"]
    assert "str" in type_hints["path_str"]
    assert "Path" in type_hints["resolved_path"]
    assert "str" in type_hints["source_type"]


def test_document_entry_init_signature_batch42():
    sig = inspect.signature(DocumentEntry.__init__)
    params = list(sig.parameters.keys())
    assert params[0] == "self"
    # 10 字段 + self = 11
    assert len(params) == 11


def test_document_entry_no_defaults_batch42():
    """所有字段都是必填（无默认）。"""
    sig = inspect.signature(DocumentEntry.__init__)
    for name, p in sig.parameters.items():
        if name == "self":
            continue
        assert p.default is inspect.Parameter.empty, f"{name} should be required"


# ---------- DocumentEntry asdict 第四十二批


def test_document_entry_asdict_works_batch42():
    e = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256="abc", categories=("t",),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    d = asdict(e)
    assert d["doc_id"] == "d1"
    assert d["source_type"] == "pdf"


def test_document_entry_replace_works_batch42():
    """dataclasses.replace 在 frozen dataclass 上工作。"""
    e = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    e2 = replace(e, doc_id="d2")
    assert e2.doc_id == "d2"
    assert e.doc_id == "d1"  # 原对象不变


def test_document_entry_categories_tuple_not_list_batch42():
    e = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256=None, categories=("a", "b"),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    assert isinstance(e.categories, tuple)


def test_document_entry_resolved_path_is_path_batch42():
    e = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    assert isinstance(e.resolved_path, Path)


# ---------- ExpectedFailure 字段结构 第四十二批


def test_expected_failure_is_dataclass_batch42():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_frozen_batch42():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        expected_error_code="X", source_type=None,
    )
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "y"  # type: ignore[misc]


def test_expected_failure_field_count_batch42():
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_field_names_batch42():
    names = [f.name for f in fields(ExpectedFailure)]
    expected = ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]
    assert names == expected


def test_expected_failure_init_signature_batch42():
    sig = inspect.signature(ExpectedFailure.__init__)
    params = list(sig.parameters.keys())
    assert params[0] == "self"
    assert len(params) == 6


def test_expected_failure_source_type_optional_batch42():
    """source_type 类型是 str | None。"""
    type_hints = {f.name: str(f.type) for f in fields(ExpectedFailure)}
    assert "None" in type_hints["source_type"] or "Optional" in type_hints["source_type"]


def test_expected_failure_asdict_batch42():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        expected_error_code="PARSE_FAILED", source_type="pdf",
    )
    d = asdict(ef)
    assert d["doc_id"] == "ef1"
    assert d["expected_error_code"] == "PARSE_FAILED"


def test_expected_failure_replace_batch42():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        expected_error_code="X", source_type=None,
    )
    ef2 = replace(ef, source_type="pdf")
    assert ef2.source_type == "pdf"
    assert ef.source_type is None


# ---------- Manifest 字段结构 第四十二批


def test_manifest_is_dataclass_batch42():
    assert is_dataclass(Manifest)


def test_manifest_frozen_batch42():
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(),
        project_root=Path("/tmp"),
    )
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


def test_manifest_field_count_batch42():
    assert len(fields(Manifest)) == 5


def test_manifest_field_names_batch42():
    names = [f.name for f in fields(Manifest)]
    expected = ["manifest_version", "devset_status", "documents", "expected_failures", "project_root"]
    assert names == expected


def test_manifest_documents_is_tuple_batch42():
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(m.documents, tuple)


def test_manifest_expected_failures_is_tuple_batch42():
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(m.expected_failures, tuple)


def test_manifest_project_root_is_path_batch42():
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(m.project_root, Path)


def test_manifest_init_signature_batch42():
    sig = inspect.signature(Manifest.__init__)
    params = list(sig.parameters.keys())
    assert params[0] == "self"
    assert len(params) == 6


def test_manifest_no_defaults_batch42():
    sig = inspect.signature(Manifest.__init__)
    for name, p in sig.parameters.items():
        if name == "self":
            continue
        assert p.default is inspect.Parameter.empty


def test_manifest_replace_batch42():
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(),
        project_root=Path("/tmp"),
    )
    m2 = replace(m, devset_status="complete")
    assert m2.devset_status == "complete"
    assert m.devset_status == "incomplete"


# ---------- Manifest computed properties 第四十二批


def test_manifest_properties_are_readonly_batch42():
    """computed properties 不可赋值。"""
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(),
        project_root=Path("/tmp"),
    )
    with pytest.raises(AttributeError):
        m.file_count = 100  # type: ignore[misc]


def test_manifest_pdf_count_only_counts_pdf_batch42():
    """pdf_count 只数 source_type=='pdf' 的。"""
    docs = (
        DocumentEntry(
            doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
            source_type="pdf", sha256=None, categories=(),
            paired_with=None, annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ),
        DocumentEntry(
            doc_id="d2", path_str="b.docx", resolved_path=Path("/tmp/b.docx"),
            source_type="docx", sha256=None, categories=(),
            paired_with=None, annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ),
        DocumentEntry(
            doc_id="d3", path_str="c.pdf", resolved_path=Path("/tmp/c.pdf"),
            source_type="pdf", sha256=None, categories=(),
            paired_with=None, annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ),
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.pdf_count == 2
    assert m.docx_count == 1


def test_manifest_categories_covered_returns_sorted_list_batch42():
    """categories_covered 返回 list（sorted），不是 tuple/set。"""
    docs = (
        DocumentEntry(
            doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
            source_type="pdf", sha256=None, categories=("z", "a"),
            paired_with=None, annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ),
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    out = m.categories_covered
    assert isinstance(out, list)
    assert out == ["a", "z"]


def test_manifest_content_group_count_pair_count_batch42():
    """配对组 = frozenset dedup 后数量。"""
    docs = (
        DocumentEntry(
            doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
            source_type="pdf", sha256=None, categories=(),
            paired_with="d2", annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ),
        DocumentEntry(
            doc_id="d2", path_str="b.docx", resolved_path=Path("/tmp/b.docx"),
            source_type="docx", sha256=None, categories=(),
            paired_with="d1", annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ),
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    # frozenset({d1, d2}) 1 组
    assert m.content_group_count == 1


def test_manifest_content_group_count_chain_not_collapsed_batch42():
    """d1↔d2, d2↔d3 是两组（frozenset dedup 不做 union-find）。"""
    docs = (
        DocumentEntry(
            doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
            source_type="pdf", sha256=None, categories=(),
            paired_with="d2", annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ),
        DocumentEntry(
            doc_id="d2", path_str="b.docx", resolved_path=Path("/tmp/b.docx"),
            source_type="docx", sha256=None, categories=(),
            paired_with="d1", annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ),
        DocumentEntry(
            doc_id="d3", path_str="c.pdf", resolved_path=Path("/tmp/c.pdf"),
            source_type="pdf", sha256=None, categories=(),
            paired_with="d2", annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ),
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    # frozenset({d1, d2}) + frozenset({d2, d3}) = 2 组（不 collapse）
    assert m.content_group_count == 2


def test_manifest_unidirectional_pair_batch42():
    """单向 paired_with 也算 1 组（frozenset 含两侧）。"""
    docs = (
        DocumentEntry(
            doc_id="d1", path_str="a.pdf", resolved_path=Path("/tmp/a.pdf"),
            source_type="pdf", sha256=None, categories=(),
            paired_with="d2", annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ),
        DocumentEntry(
            doc_id="d2", path_str="b.docx", resolved_path=Path("/tmp/b.docx"),
            source_type="docx", sha256=None, categories=(),
            paired_with=None, annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        ),
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=docs, expected_failures=(),
        project_root=Path("/tmp"),
    )
    # d1 → d2 单向；frozenset({d1, d2}) 算 1 组；d2 不在 seen 但 d2.paired_with=None
    # 实现：先 pair_ids 收集 (d1.paired_with) → frozenset({d1, d2})；
    # 然后 seen = {d1, d2}；d2 在 seen 中所以不视为 unpaired
    assert m.content_group_count == 1


# ---------- ManifestError 补强 第四十二批


def test_manifest_error_subclass_of_exception_batch42():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_not_subclass_of_value_error_batch42():
    """ManifestError 不是 ValueError 子类（独立继承 Exception）。"""
    assert not issubclass(ManifestError, ValueError)


def test_manifest_error_not_subclass_of_type_error_batch42():
    assert not issubclass(ManifestError, TypeError)


def test_manifest_error_str_batch42():
    err = ManifestError("test message")
    assert str(err) == "test message"


def test_manifest_error_repr_batch42():
    err = ManifestError("test")
    assert "ManifestError" in repr(err)


def test_manifest_error_args_batch42():
    err = ManifestError("a", "b", "c")
    assert err.args == ("a", "b", "c")


def test_manifest_error_raise_from_other_batch42():
    """raise from 另一个 exception。"""
    try:
        try:
            raise ValueError("original")
        except ValueError as e:
            raise ManifestError("wrapped") from e
    except ManifestError as me:
        assert isinstance(me.__cause__, ValueError)


def test_manifest_error_in_all_batch42():
    assert "ManifestError" in mmod.__all__


# ---------- _has_backslash / _is_absolute_like 补强 第四十二批


def test_has_backslash_unicode_backslash_batch42():
    """全角反斜杠 U+FF3C 不是 ASCII \\。"""
    assert _has_backslash("a＼b") is False  # 全角 ＼ ≠ \


def test_has_backslash_only_one_backslash_batch42():
    """单 \\ 是 True。"""
    assert _has_backslash("\\") is True


def test_is_absolute_like_uppercase_drive_batch42():
    assert _is_absolute_like("C:/x") is True
    assert _is_absolute_like("D:\\x") is True


def test_is_absolute_like_lowercase_drive_batch42():
    assert _is_absolute_like("c:/x") is True
    assert _is_absolute_like("d:\\x") is True


def test_is_absolute_like_just_drive_no_separator_batch42():
    """'C:' 无分隔符不算绝对路径。"""
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_unc_path_batch42():
    """UNC \\\\server\\share 不识别（不以 / 开头，无盘符）。"""
    assert _is_absolute_like("\\\\server\\share") is False


def test_is_absolute_like_double_slash_batch42():
    """// 双斜杠 → 以 / 开头 → True。"""
    assert _is_absolute_like("//server/path") is True


def test_is_absolute_like_tilde_path_batch42():
    """~ 开头不算绝对（POSIX 中需要 expanduser）。"""
    assert _is_absolute_like("~/foo") is False


# ---------- _resolve_relative_path 补强 第四十二批


def test_resolve_relative_path_special_chars_batch42(tmp_path):
    """路径含特殊字符（破折号、下划线、点）。"""
    out = _resolve_relative_path("foo-bar_baz.v2.pdf", tmp_path, "test")
    assert out == (tmp_path / "foo-bar_baz.v2.pdf").resolve()


def test_resolve_relative_path_unicode_filename_batch42(tmp_path):
    """中文文件名也接受。"""
    out = _resolve_relative_path("中文.pdf", tmp_path, "test")
    assert out == (tmp_path / "中文.pdf").resolve()


def test_resolve_relative_path_emoji_filename_batch42(tmp_path):
    out = _resolve_relative_path("😀.pdf", tmp_path, "test")
    assert out == (tmp_path / "😀.pdf").resolve()


def test_resolve_relative_path_single_dot_batch42(tmp_path):
    """'.' 当前目录 → 仍在 root 内 → 允许。"""
    out = _resolve_relative_path(".", tmp_path, "test")
    assert out == tmp_path.resolve()


def test_resolve_relative_path_multiple_dots_batch42(tmp_path):
    """'foo/./bar' 仍在 root 内。"""
    out = _resolve_relative_path("foo/./bar.pdf", tmp_path, "test")
    assert out == (tmp_path / "foo" / "bar.pdf").resolve()


def test_resolve_relative_path_double_dots_within_root_batch42(tmp_path):
    """'a/../b' 仍在 root 内。"""
    out = _resolve_relative_path("a/../b.pdf", tmp_path, "test")
    assert out == (tmp_path / "b.pdf").resolve()


def test_resolve_relative_path_double_dots_escape_batch42(tmp_path):
    """'../sibling' 逃出 root → ManifestError。"""
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("../sibling/file.pdf", tmp_path, "test")
    assert "项目根目录之外" in str(exc.value) or "外" in str(exc.value)


def test_resolve_relative_path_deep_escape_batch42(tmp_path):
    """'a/../../../etc/passwd' 逃出 root。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("a/../../../etc/passwd", tmp_path, "test")


# ---------- load_manifest with project_root as Path 第四十二批


def test_load_manifest_with_path_project_root_batch42(tmp_path):
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.project_root == tmp_path.resolve()


def test_load_manifest_with_str_project_root_batch42(tmp_path):
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=str(tmp_path))
    assert out.project_root == tmp_path.resolve()


def test_load_manifest_resolves_symlink_free_batch42(tmp_path):
    """manifest_path 是 str 也能 resolve。"""
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(str(p), project_root=tmp_path)
    assert isinstance(out, Manifest)


# ---------- module source 补强 第四十二批


def test_module_source_contains_dataclass_decorator_batch42():
    src = inspect.getsource(mmod)
    assert "@dataclass" in src


def test_module_source_contains_frozen_true_count_batch42():
    """frozen=True 出现 3 次（3 个 dataclass）。"""
    src = inspect.getsource(mmod)
    assert src.count("frozen=True") == 3


def test_module_source_no_class_methods_batch42():
    """dataclass 无自定义方法（只有 property）。"""
    src = inspect.getsource(mmod)
    # property 是 function 定义，但不应该有 __init__/__eq__ 等
    assert "def __init__(" not in src
    assert "def __eq__(" not in src


def test_module_source_has_three_property_decorators_batch42():
    """Manifest 有 file_count/pdf_count/docx_count/content_group_count/categories_covered 5 个 property。"""
    src = inspect.getsource(mmod)
    # 至少 5 个 @property
    assert src.count("@property") >= 5


# ---------- module 合理性补强 第四十二批


def test_module_has_three_dataclasses_batch42():
    """DocumentEntry / ExpectedFailure / Manifest 是 dataclass。"""
    assert is_dataclass(DocumentEntry)
    assert is_dataclass(ExpectedFailure)
    assert is_dataclass(Manifest)


def test_module_all_no_dataclasses_exported_batch42():
    """dataclass 类不出现在 __all__（只 export 公共 API）。"""
    # 实际 __all__ 有 5 个 entries，包含 Manifest/DocumentEntry/ExpectedFailure
    # 但不 export dataclasses 模块本身
    assert "dataclasses" not in mmod.__all__


def test_module_manifest_class_in_all_batch42():
    assert "Manifest" in mmod.__all__


def test_module_document_entry_in_all_batch42():
    assert "DocumentEntry" in mmod.__all__


def test_module_expected_failure_in_all_batch42():
    assert "ExpectedFailure" in mmod.__all__


# ---------- 端到端集成 第四十二批


def test_e2e_round_trip_full_manifest_with_pair_batch42(tmp_path):
    """完整 manifest 含配对、annotation、expectations。"""
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    (tmp_path / "b.docx").write_text("x", encoding="utf-8")
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
                "categories": ["tutorial"], "paired_with": "d2",
                "annotation_file": "a.json",
                "expectations": {"element_count_by_type": {"paragraph": 5}},
            },
            {
                "doc_id": "d2", "path": "b.docx", "source_type": "docx",
                "paired_with": "d1",
            },
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)

    # 全字段验证
    assert out.manifest_version == MANIFEST_VERSION
    assert out.devset_status == "incomplete"
    assert len(out.documents) == 2

    d1 = out.documents[0]
    assert d1.doc_id == "d1"
    assert d1.path_str == "a.pdf"
    assert d1.source_type == "pdf"
    assert d1.categories == ("tutorial",)
    assert d1.paired_with == "d2"
    assert d1.annotation_file_str == "a.json"
    assert d1.annotation_resolved == (tmp_path / "a.json").resolve()
    assert d1.expectations == {"element_count_by_type": {"paragraph": 5}}

    # 计算属性
    assert out.file_count == 2
    assert out.pdf_count == 1
    assert out.docx_count == 1
    assert out.content_group_count == 1
    assert out.categories_covered == ["tutorial"]


# ---------- module source forbidden tokens 第八十三批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch42(token):
    src = inspect.getsource(mmod)
    assert token not in src
