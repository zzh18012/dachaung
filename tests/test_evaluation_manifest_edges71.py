"""evaluation/manifest.py 第八十六轮 edges 测试（Round 629）。

补强 edges70 未触及的角度（第四十五批）。

新角度：
- _is_absolute_like Unicode 盘符（U+00E9 / 中文 / 日文）
- _is_absolute_like 各种边界
- _has_backslash 各种边界
- DocumentEntry frozen / hash / equality
- ExpectedFailure frozen / hash / equality
- Manifest frozen / hash / equality
- Manifest.file_count/pdf_count/docx_count 各种组合
- Manifest.content_group_count 各种配对场景
- Manifest.categories_covered 排序与去重
- _resolve_relative_path 各种错误（空 / 绝对 / 反斜杠 / 跨根）
- _detect_project_root 各种起点
- load_manifest 各种失败（FileNotFoundError / JSONDecodeError / Schema / version mismatch）
- module source 字符串精确
- AST 结构
- forbidden tokens 第九十九批
"""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import FrozenInstanceError, asdict, fields, replace
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.manifest as manifest_mod
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


# ---------- _is_absolute_like 各种 ----------

def test_is_absolute_like_empty_string_batch45():
    assert _is_absolute_like("") is False


def test_is_absolute_like_posix_absolute_batch45():
    assert _is_absolute_like("/etc/passwd") is True


def test_is_absolute_like_posix_root_only_batch45():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_relative_simple_batch45():
    assert _is_absolute_like("foo/bar") is False


def test_is_absolute_like_relative_dot_batch45():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_relative_double_dot_batch45():
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_windows_backslash_batch45():
    assert _is_absolute_like("C:\\Windows") is True


def test_is_absolute_like_windows_forward_slash_batch45():
    assert _is_absolute_like("C:/Windows") is True


def test_is_absolute_like_lowercase_drive_batch45():
    assert _is_absolute_like("c:\\Windows") is True


def test_is_absolute_like_drive_no_separator_batch45():
    """C:foo 没有 \\ 或 / → 相对路径（Windows 当前目录）。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_single_char_batch45():
    assert _is_absolute_like("C") is False


def test_is_absolute_like_colon_only_batch45():
    assert _is_absolute_like(":") is False


def test_is_absolute_like_two_chars_batch45():
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_unicode_drive_é_batch45():
    """Unicode 字母 é: 作为盘符 → isalpha() True。"""
    assert _is_absolute_like("é:\\foo") is True


def test_is_absolute_like_unicode_drive_chinese_batch45():
    """中文字符是 isalpha()。"""
    assert _is_absolute_like("文:/foo") is True


def test_is_absolute_like_unicode_drive_japanese_batch45():
    assert _is_absolute_like("あ:\\foo") is True


def test_is_absolute_like_digit_drive_batch45():
    """数字不是 isalpha()。"""
    assert _is_absolute_like("1:\\foo") is False


def test_is_absolute_like_underscore_drive_batch45():
    """下划线不是 isalpha()。"""
    assert _is_absolute_like("_:\\foo") is False


def test_is_absolute_like_space_first_batch45():
    assert _is_absolute_like(" :\\foo") is False


def test_is_absolute_like_pathlib_root_batch45():
    """Path("/") is absolute, but string is what we test."""
    assert _is_absolute_like("/home/user") is True


# ---------- _has_backslash 各种 ----------

def test_has_backslash_simple_batch45():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_none_batch45():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_empty_batch45():
    assert _has_backslash("") is False


def test_has_backslash_only_batch45():
    assert _has_backslash("\\") is True


def test_has_backslash_double_batch45():
    assert _has_backslash("foo\\\\bar") is True


def test_has_backslash_at_end_batch45():
    assert _has_backslash("foo\\") is True


def test_has_backslash_at_start_batch45():
    assert _has_backslash("\\foo") is True


def test_has_backslash_forward_only_batch45():
    assert _has_backslash("/foo/bar") is False


# ---------- DocumentEntry frozen ----------

def _make_doc_entry(
    doc_id="d1",
    path_str="a/b.pdf",
    resolved_path=None,
    source_type="pdf",
    sha256=None,
    categories=(),
    paired_with=None,
    annotation_file_str=None,
    annotation_resolved=None,
    expectations=None,
):
    return DocumentEntry(
        doc_id=doc_id,
        path_str=path_str,
        resolved_path=resolved_path or Path("/tmp/a/b.pdf"),
        source_type=source_type,
        sha256=sha256,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=annotation_file_str,
        annotation_resolved=annotation_resolved,
        expectations=expectations,
    )


def test_document_entry_frozen_batch45():
    d = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "x"  # type: ignore[misc]


def test_document_entry_hashable_batch45():
    d = _make_doc_entry()
    h = hash(d)
    assert isinstance(h, int)


def test_document_entry_equality_batch45():
    d1 = _make_doc_entry()
    d2 = _make_doc_entry()
    assert d1 == d2


def test_document_entry_inequality_batch45():
    d1 = _make_doc_entry(doc_id="d1")
    d2 = _make_doc_entry(doc_id="d2")
    assert d1 != d2


def test_document_entry_in_set_batch45():
    d1 = _make_doc_entry()
    d2 = _make_doc_entry()
    s = {d1, d2}
    assert len(s) == 1  # same hash + eq


def test_document_entry_asdict_batch45():
    d = _make_doc_entry(categories=("a", "b"))
    out = asdict(d)
    assert out["doc_id"] == "d1"
    assert out["categories"] == ("a", "b")  # tuple preserved


def test_document_entry_replace_batch45():
    d1 = _make_doc_entry()
    d2 = replace(d1, doc_id="x")
    assert d2.doc_id == "x"
    assert d1.doc_id == "d1"  # 不变


def test_document_entry_fields_count_batch45():
    fs = fields(DocumentEntry)
    assert len(fs) == 10


def test_document_entry_field_names_batch45():
    fs = fields(DocumentEntry)
    names = [f.name for f in fs]
    assert "doc_id" in names
    assert "path_str" in names
    assert "resolved_path" in names
    assert "source_type" in names
    assert "sha256" in names
    assert "categories" in names
    assert "paired_with" in names
    assert "annotation_file_str" in names
    assert "annotation_resolved" in names
    assert "expectations" in names


def test_document_entry_default_categories_is_tuple_batch45():
    d = DocumentEntry(
        doc_id="d",
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
    assert isinstance(d.categories, tuple)


# ---------- ExpectedFailure frozen ----------

def _make_expected_failure(
    doc_id="ef1",
    path_str="bad/corrupt.pdf",
    resolved_path=None,
    expected_error_code="parse_failed",
    source_type="pdf",
):
    return ExpectedFailure(
        doc_id=doc_id,
        path_str=path_str,
        resolved_path=resolved_path or Path("/tmp/bad/corrupt.pdf"),
        expected_error_code=expected_error_code,
        source_type=source_type,
    )


def test_expected_failure_frozen_batch45():
    ef = _make_expected_failure()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "x"  # type: ignore[misc]


def test_expected_failure_hashable_batch45():
    ef = _make_expected_failure()
    h = hash(ef)
    assert isinstance(h, int)


def test_expected_failure_equality_batch45():
    ef1 = _make_expected_failure()
    ef2 = _make_expected_failure()
    assert ef1 == ef2


def test_expected_failure_fields_count_batch45():
    fs = fields(ExpectedFailure)
    assert len(fs) == 5


def test_expected_failure_field_names_batch45():
    fs = fields(ExpectedFailure)
    names = [f.name for f in fs]
    assert names == ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]


def test_expected_failure_replace_batch45():
    ef1 = _make_expected_failure()
    ef2 = replace(ef1, expected_error_code="x")
    assert ef2.expected_error_code == "x"


def test_expected_failure_source_type_can_be_none_batch45():
    ef = ExpectedFailure(
        doc_id="ef",
        path_str="x.pdf",
        resolved_path=Path("/tmp/x.pdf"),
        expected_error_code="err",
        source_type=None,
    )
    assert ef.source_type is None


# ---------- Manifest frozen + property ----------

def _make_manifest(
    documents=(),
    expected_failures=(),
    project_root=None,
    devset_status="incomplete",
):
    return Manifest(
        manifest_version="1.0",
        devset_status=devset_status,
        documents=tuple(documents),
        expected_failures=tuple(expected_failures),
        project_root=project_root or Path("/tmp"),
    )


def test_manifest_frozen_batch45():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.manifest_version = "9.9"  # type: ignore[misc]


def test_manifest_hashable_batch45():
    m = _make_manifest()
    h = hash(m)
    assert isinstance(h, int)


def test_manifest_fields_count_batch45():
    fs = fields(Manifest)
    assert len(fs) == 5


def test_manifest_field_names_batch45():
    fs = fields(Manifest)
    names = [f.name for f in fs]
    assert names == ["manifest_version", "devset_status", "documents", "expected_failures", "project_root"]


def test_manifest_file_count_empty_batch45():
    m = _make_manifest(documents=())
    assert m.file_count == 0


def test_manifest_file_count_three_batch45():
    docs = [_make_doc_entry(doc_id=f"d{i}") for i in range(3)]
    m = _make_manifest(documents=docs)
    assert m.file_count == 3


def test_manifest_pdf_count_batch45():
    docs = [
        _make_doc_entry(doc_id="d1", source_type="pdf"),
        _make_doc_entry(doc_id="d2", source_type="docx"),
        _make_doc_entry(doc_id="d3", source_type="pdf"),
    ]
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 2


def test_manifest_docx_count_batch45():
    docs = [
        _make_doc_entry(doc_id="d1", source_type="pdf"),
        _make_doc_entry(doc_id="d2", source_type="docx"),
        _make_doc_entry(doc_id="d3", source_type="docx"),
    ]
    m = _make_manifest(documents=docs)
    assert m.docx_count == 2


def test_manifest_no_other_source_type_batch45():
    docs = [
        _make_doc_entry(doc_id="d1", source_type="html"),
        _make_doc_entry(doc_id="d2", source_type="txt"),
    ]
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 0
    assert m.docx_count == 0
    assert m.file_count == 2


def test_manifest_content_group_count_all_unpaired_batch45():
    docs = [
        _make_doc_entry(doc_id="d1"),
        _make_doc_entry(doc_id="d2"),
        _make_doc_entry(doc_id="d3"),
    ]
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 3


def test_manifest_content_group_count_all_paired_batch45():
    docs = [
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
    ]
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 1


def test_manifest_content_group_count_mixed_batch45():
    docs = [
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
        _make_doc_entry(doc_id="d3"),
        _make_doc_entry(doc_id="d4"),
    ]
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 3  # 1 pair + 2 unpaired


def test_manifest_content_group_count_one_way_pair_batch45():
    """单向配对也算一组（避免重复计数）。"""
    docs = [
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2"),  # d2 不指回 d1
    ]
    m = _make_manifest(documents=docs)
    # pair_ids = {frozenset({d1, d2})} → 1 group
    # d2 在 seen 中（seen.update(pair)），所以 unpaired=0
    assert m.content_group_count == 1


def test_manifest_categories_covered_sorted_batch45():
    docs = [
        _make_doc_entry(doc_id="d1", categories=("z", "a")),
        _make_doc_entry(doc_id="d2", categories=("m",)),
    ]
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_dedup_batch45():
    docs = [
        _make_doc_entry(doc_id="d1", categories=("a", "b")),
        _make_doc_entry(doc_id="d2", categories=("a", "c")),
    ]
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_categories_covered_empty_batch45():
    m = _make_manifest(documents=())
    assert m.categories_covered == []


def test_manifest_categories_covered_returns_list_batch45():
    docs = [_make_doc_entry(categories=("a",))]
    m = _make_manifest(documents=docs)
    assert isinstance(m.categories_covered, list)


# ---------- _resolve_relative_path 各种错误 ----------

def test_resolve_relative_path_empty_batch45(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "x")
    assert "为空" in str(exc_info.value)


def test_resolve_relative_path_absolute_posix_batch45(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/etc/passwd", tmp_path, "x")
    assert "禁止绝对路径" in str(exc_info.value)


def test_resolve_relative_path_absolute_windows_batch45(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("C:\\Windows", tmp_path, "x")
    assert "禁止绝对路径" in str(exc_info.value)


def test_resolve_relative_path_backslash_batch45(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("foo\\bar", tmp_path, "x")
    assert "禁止反斜杠" in str(exc_info.value)


def test_resolve_relative_path_escape_root_batch45(tmp_path):
    """../../../ 跨出 project_root。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("../../etc/passwd", tmp_path, "x")
    assert "项目根目录之外" in str(exc_info.value)


def test_resolve_relative_path_success_batch45(tmp_path):
    (tmp_path / "sub").mkdir()
    out = _resolve_relative_path("sub/file.pdf", tmp_path, "x")
    assert out == (tmp_path / "sub" / "file.pdf").resolve()


def test_resolve_relative_path_returns_path_batch45(tmp_path):
    out = _resolve_relative_path("file.pdf", tmp_path, "x")
    assert isinstance(out, Path)


def test_resolve_relative_path_resolved_absolute_batch45(tmp_path):
    out = _resolve_relative_path("file.pdf", tmp_path, "x")
    assert out.is_absolute()


# ---------- _detect_project_root 各种 ----------

def test_detect_project_root_from_file_batch45():
    """传文件路径 → 从父目录开始找。"""
    p = Path(__file__).resolve()
    root = _detect_project_root(p)
    assert (root / "pyproject.toml").is_file()


def test_detect_project_root_from_dir_batch45():
    p = Path(__file__).resolve().parent
    root = _detect_project_root(p)
    assert (root / "pyproject.toml").is_file()


def test_detect_project_root_returns_path_batch45():
    p = Path(__file__).resolve()
    root = _detect_project_root(p)
    assert isinstance(root, Path)


def test_detect_project_root_fallback_when_no_pyproject_batch45(tmp_path):
    """没有 pyproject.toml 时回退到 cur。"""
    root = _detect_project_root(tmp_path)
    assert root == tmp_path.resolve()


# ---------- load_manifest 各种 ----------

def test_load_manifest_file_not_found_batch45(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(tmp_path / "missing.json")
    assert "清单文件不存在" in str(exc_info.value)


def test_load_manifest_json_decode_error_batch45(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p)
    assert "清单 JSON 解析失败" in str(exc_info.value)


def test_load_manifest_invalid_schema_batch45(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_version_mismatch_via_schema_enum_batch45(tmp_path):
    """manifest_version="9.9" → Schema enum 拒绝。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "9.9",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_success_empty_documents_batch45(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.manifest_version == "1.0"
    assert m.devset_status == "incomplete"
    assert m.documents == ()
    assert m.expected_failures == ()


def test_load_manifest_with_expected_failures_batch45(tmp_path):
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "x.pdf").write_text("x", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "ef1",
                "path": "bad/x.pdf",
                "expected_error_code": "parse_failed",
                "source_type": "pdf",
            }
        ],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    ef = m.expected_failures[0]
    assert ef.doc_id == "ef1"
    assert ef.expected_error_code == "parse_failed"


def test_load_manifest_path_field_with_backslash_batch45(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a\\b.pdf", "source_type": "pdf"}
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "禁止反斜杠" in str(exc_info.value)


def test_load_manifest_path_field_absolute_batch45(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "/etc/passwd", "source_type": "pdf"}
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "禁止绝对路径" in str(exc_info.value)


def test_load_manifest_accepts_str_path_batch45(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    m = load_manifest(str(p), project_root=str(tmp_path))
    assert m.manifest_version == "1.0"


# ---------- module source 字符串精确 ----------

def test_module_docstring_contains_invariants_batch45():
    src = inspect.getsource(manifest_mod)
    assert "path 字段必须是相对路径" in src
    assert "正斜杠" in src
    assert "拒绝绝对路径与反斜杠" in src


def test_module_source_contains_dataclass_import_batch45():
    src = inspect.getsource(manifest_mod)
    assert "from dataclasses import dataclass" in src


def test_module_source_contains_json_import_batch45():
    src = inspect.getsource(manifest_mod)
    assert "import json" in src


def test_module_source_contains_path_import_batch45():
    src = inspect.getsource(manifest_mod)
    assert "from pathlib import Path" in src


def test_module_source_contains_evaluation_manifest_version_import_batch45():
    src = inspect.getsource(manifest_mod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_contains_evaluation_schema_validate_import_batch45():
    src = inspect.getsource(manifest_mod)
    assert "from evaluation.schema import validate" in src


def test_module_source_contains_manifest_error_class_batch45():
    src = inspect.getsource(manifest_mod)
    assert "class ManifestError(Exception):" in src


def test_module_source_contains_document_entry_class_batch45():
    src = inspect.getsource(manifest_mod)
    assert "@dataclass(frozen=True)" in src
    assert "class DocumentEntry:" in src


def test_module_source_contains_expected_failure_class_batch45():
    src = inspect.getsource(manifest_mod)
    assert "class ExpectedFailure:" in src


def test_module_source_contains_manifest_class_batch45():
    src = inspect.getsource(manifest_mod)
    assert "class Manifest:" in src


def test_module_source_contains_is_absolute_like_function_batch45():
    src = inspect.getsource(manifest_mod)
    assert "def _is_absolute_like(path_str: str) -> bool:" in src


def test_module_source_contains_has_backslash_function_batch45():
    src = inspect.getsource(manifest_mod)
    assert "def _has_backslash(path_str: str) -> bool:" in src


def test_module_source_contains_resolve_relative_path_function_batch45():
    src = inspect.getsource(manifest_mod)
    assert "def _resolve_relative_path(" in src


def test_module_source_contains_load_manifest_function_batch45():
    src = inspect.getsource(manifest_mod)
    assert "def load_manifest(" in src


def test_module_source_contains_detect_project_root_function_batch45():
    src = inspect.getsource(manifest_mod)
    assert "def _detect_project_root(start: Path) -> Path:" in src


def test_module_source_contains_file_count_property_batch45():
    src = inspect.getsource(manifest_mod)
    assert "@property" in src
    assert "def file_count(self) -> int:" in src


def test_module_source_contains_pdf_count_property_batch45():
    src = inspect.getsource(manifest_mod)
    assert "def pdf_count(self) -> int:" in src


def test_module_source_contains_docx_count_property_batch45():
    src = inspect.getsource(manifest_mod)
    assert "def docx_count(self) -> int:" in src


def test_module_source_contains_content_group_count_property_batch45():
    src = inspect.getsource(manifest_mod)
    assert "def content_group_count(self) -> int:" in src


def test_module_source_contains_categories_covered_property_batch45():
    src = inspect.getsource(manifest_mod)
    assert "def categories_covered(self) -> list[str]:" in src


# ---------- __all__ ----------

def test_all_exact_order_batch45():
    assert list(manifest_mod.__all__) == [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ]


def test_all_count_five_batch45():
    assert len(manifest_mod.__all__) == 5


def test_all_entries_importable_batch45():
    for name in manifest_mod.__all__:
        assert hasattr(manifest_mod, name)


def test_all_entries_unique_batch45():
    assert len(set(manifest_mod.__all__)) == len(manifest_mod.__all__)


# ---------- AST 结构 ----------

def test_ast_top_level_classes_count_batch45():
    tree = ast.parse(inspect.getsource(manifest_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 4  # ManifestError, DocumentEntry, ExpectedFailure, Manifest


def test_ast_top_level_class_names_batch45():
    tree = ast.parse(inspect.getsource(manifest_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    assert names == ["ManifestError", "DocumentEntry", "ExpectedFailure", "Manifest"]


def test_ast_top_level_functions_count_batch45():
    tree = ast.parse(inspect.getsource(manifest_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 5  # _is_absolute_like, _has_backslash, _resolve_relative_path, load_manifest, _detect_project_root


def test_ast_top_level_function_names_batch45():
    tree = ast.parse(inspect.getsource(manifest_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == [
        "_is_absolute_like",
        "_has_backslash",
        "_resolve_relative_path",
        "load_manifest",
        "_detect_project_root",
    ]


def test_ast_no_async_in_top_level_batch45():
    tree = ast.parse(inspect.getsource(manifest_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_first_node_docstring_batch45():
    tree = ast.parse(inspect.getsource(manifest_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)


def test_ast_second_node_future_import_batch45():
    tree = ast.parse(inspect.getsource(manifest_mod))
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


def test_ast_manifest_class_has_properties_batch45():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest"][0]
    props = []
    for n in cls.body:
        if isinstance(n, ast.FunctionDef):
            # 检查装饰器
            for d in n.decorator_list:
                if isinstance(d, ast.Name) and d.id == "property":
                    props.append(n.name)
    assert set(props) == {
        "file_count",
        "pdf_count",
        "docx_count",
        "content_group_count",
        "categories_covered",
    }


def test_ast_document_entry_has_no_methods_batch45():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "DocumentEntry"][0]
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert len(methods) == 0  # frozen dataclass 自动生成


def test_ast_expected_failure_has_no_methods_batch45():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ExpectedFailure"][0]
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert len(methods) == 0


def test_ast_manifest_class_has_init_generated_batch45():
    """frozen dataclass 不写 __init__ 但 CPython 自动生成；AST 中看不到。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest"][0]
    init_methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"]
    assert len(init_methods) == 0  # dataclass 装饰器生成


def test_ast_manifest_error_inherits_exception_batch45():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ManifestError"][0]
    assert len(cls.bases) == 1
    assert isinstance(cls.bases[0], ast.Name)
    assert cls.bases[0].id == "Exception"


def test_ast_is_absolute_like_uses_startswith_batch45():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_is_absolute_like"][0]
    has_startswith = False
    for n in ast.walk(func):
        if isinstance(n, ast.Attribute) and n.attr == "startswith":
            has_startswith = True
    assert has_startswith


def test_ast_is_absolute_like_uses_isalpha_batch45():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_is_absolute_like"][0]
    has_isalpha = False
    for n in ast.walk(func):
        if isinstance(n, ast.Attribute) and n.attr == "isalpha":
            has_isalpha = True
    assert has_isalpha


def test_ast_load_manifest_has_try_except_batch45():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest"][0]
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) >= 1


def test_ast_load_manifest_has_for_loops_batch45():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest"][0]
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) >= 2  # documents + expected_failures


# ---------- forbidden tokens 第九十九批 ----------

def test_source_no_eval_batch45():
    src = inspect.getsource(manifest_mod)
    assert "eval(" not in src


def test_source_no_exec_batch45():
    src = inspect.getsource(manifest_mod)
    assert "exec(" not in src


def test_source_no_compile_batch45():
    src = inspect.getsource(manifest_mod)
    assert "compile(" not in src


def test_source_no_globals_batch45():
    src = inspect.getsource(manifest_mod)
    assert "globals(" not in src


def test_source_no_locals_batch45():
    src = inspect.getsource(manifest_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch45():
    src = inspect.getsource(manifest_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch45():
    src = inspect.getsource(manifest_mod)
    assert "popen(" not in src


def test_source_no_yaml_load_batch45():
    src = inspect.getsource(manifest_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch45():
    src = inspect.getsource(manifest_mod)
    assert "pickle.load(" not in src


def test_source_no_async_def_batch45():
    src = inspect.getsource(manifest_mod)
    assert "async def" not in src


def test_source_no_yield_batch45():
    src = inspect.getsource(manifest_mod)
    assert "yield" not in src


def test_source_no_walrus_batch45():
    src = inspect.getsource(manifest_mod)
    assert ":=" not in src


def test_source_no_lambda_batch45():
    src = inspect.getsource(manifest_mod)
    assert "lambda" not in src


def test_source_no_subprocess_batch45():
    src = inspect.getsource(manifest_mod)
    assert "subprocess" not in src
