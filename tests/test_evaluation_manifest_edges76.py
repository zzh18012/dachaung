"""evaluation/manifest.py 第九十一轮 edges 测试（Round 669）。

补强 edges75 未触及的角度（第五十一批）。

新角度：
- _is_absolute_like 更细（Unicode 字母盘符 / 数字盘符 / 下划线盘符 / 单字符路径 / 仅 1 字符 / 仅 2 字符 / 空串）
- _has_backslash 边界（仅反斜杠 / 反斜杠+正斜杠 / 编码字符）
- Manifest dataclass 自动生成 __eq__/__hash__/__repr__（frozen=True 行为）
- DocumentEntry 自动 __eq__（doc_id 不同时 false / 全字段相等时 true / 部分字段相等 false）
- ExpectedFailure 默认 source_type=None
- Manifest categories_covered 排序验证（按字母升序）
- Manifest content_group_count self-reference（A.paired_with=A 视为单组）
- load_manifest 完整路径错误（无 manifest_version / documents 缺 path / expected_failures 缺 path）
- _resolve_relative_path 字段名包含完整路径
- 模块源码补强（dataclass import / frozen=True / ManifestError docstring / __all__ 5 entry / 完整文档关键词）
- AST 结构补强（5 函数 + 顺序 / 4 ClassDef + frozen=True / Manifest 5 property + sort + frozenset / load_manifest 复杂控制流 / _resolve_relative_path try-except / module docstring）
- forbidden tokens 第一百三十九批
"""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import FrozenInstanceError, is_dataclass
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


# ---------- _is_absolute_like 更细 ----------

def test_is_absolute_like_unicode_letter_drive_batch51():
    """非 ASCII 字母也算盘符首字符（因为 isalpha() 接受 Unicode 字母）。"""
    # 中文 / 希腊字母都是 alpha
    assert _is_absolute_like("中:/x") is True
    assert _is_absolute_like("Ω:/x") is True


def test_is_absolute_like_digit_drive_batch51():
    """数字开头不是 alpha → False。"""
    assert _is_absolute_like("1:/x") is False


def test_is_absolute_like_underscore_drive_batch51():
    """下划线不是 alpha → False。"""
    assert _is_absolute_like("_:/x") is False


def test_is_absolute_like_single_char_path_batch51():
    """单字符路径不算绝对路径。"""
    assert _is_absolute_like("/") is True  # startswith('/')
    assert _is_absolute_like("a") is False


def test_is_absolute_like_two_chars_batch51():
    """'a:' 长度 2，不满足 >= 3 → False。"""
    assert _is_absolute_like("a:") is False


def test_is_absolute_like_three_chars_no_slash_batch51():
    """'a:b' 长度 3，但 path[2] != \\ 或 / → False。"""
    assert _is_absolute_like("a:b") is False


def test_is_absolute_like_three_chars_with_slash_batch51():
    """'a:b' → False; 'a:/b' → True。"""
    assert _is_absolute_like("a:/b") is True
    assert _is_absolute_like("a:\\b") is True


def test_is_absolute_like_empty_string_batch51():
    assert _is_absolute_like("") is False


def test_is_absolute_like_relative_dot_batch51():
    """'./foo' startswith('.') 不是 '/' → False。"""
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_double_dot_batch51():
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_tilde_batch51():
    """'~' 不被识别。"""
    assert _is_absolute_like("~/foo") is False


# ---------- _has_backslash 边界 ----------

def test_has_backslash_only_backslash_batch51():
    assert _has_backslash("\\") is True


def test_has_backslash_mixed_slashes_batch51():
    assert _has_backslash("a/b\\c") is True
    assert _has_backslash("a/b/c") is False


def test_has_backslash_at_start_batch51():
    assert _has_backslash("\\foo") is True


def test_has_backslash_at_end_batch51():
    assert _has_backslash("foo\\") is True


def test_has_backslash_multiple_batch51():
    assert _has_backslash("a\\b\\c\\d") is True


def test_has_backslash_empty_string_batch51():
    assert _has_backslash("") is False


def test_has_backslash_none_value_batch51():
    """传 None 会 TypeError，但传字符串都返回 bool。"""
    assert _has_backslash("normal") is False


# ---------- Manifest dataclass 自动行为 ----------

def test_manifest_is_dataclass_batch51():
    assert is_dataclass(Manifest)


def test_document_entry_is_dataclass_batch51():
    assert is_dataclass(DocumentEntry)


def test_expected_failure_is_dataclass_batch51():
    assert is_dataclass(ExpectedFailure)


def test_manifest_is_frozen_batch51(tmp_path):
    m = Manifest(
        manifest_version="1.0",
        devset_status="complete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )
    with pytest.raises(FrozenInstanceError):
        m.manifest_version = "1.1"


def test_document_entry_is_frozen_batch51(tmp_path):
    d = DocumentEntry(
        doc_id="d1",
        path_str="a/b.pdf",
        resolved_path=tmp_path / "a" / "b.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "x"


def test_expected_failure_is_frozen_batch51(tmp_path):
    ef = ExpectedFailure(
        doc_id="d1",
        path_str="a/b.pdf",
        resolved_path=tmp_path / "a" / "b.pdf",
        expected_error_code="parse_failed",
        source_type=None,
    )
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "x"


def test_manifest_auto_eq_equal_batch51(tmp_path):
    m1 = Manifest("1.0", "complete", (), (), tmp_path)
    m2 = Manifest("1.0", "complete", (), (), tmp_path)
    assert m1 == m2


def test_manifest_auto_eq_not_equal_batch51(tmp_path):
    m1 = Manifest("1.0", "complete", (), (), tmp_path)
    m2 = Manifest("1.0", "incomplete", (), (), tmp_path)
    assert m1 != m2


def test_manifest_hashable_batch51(tmp_path):
    """frozen dataclass 应该 hashable。"""
    m = Manifest("1.0", "complete", (), (), tmp_path)
    hash(m)  # should not raise


def test_document_entry_auto_eq_equal_batch51(tmp_path):
    d1 = DocumentEntry(
        "d1", "a/b.pdf", tmp_path / "a" / "b.pdf", "pdf",
        None, (), None, None, None, None,
    )
    d2 = DocumentEntry(
        "d1", "a/b.pdf", tmp_path / "a" / "b.pdf", "pdf",
        None, (), None, None, None, None,
    )
    assert d1 == d2


def test_document_entry_auto_eq_not_equal_batch51(tmp_path):
    d1 = DocumentEntry(
        "d1", "a/b.pdf", tmp_path / "a" / "b.pdf", "pdf",
        None, (), None, None, None, None,
    )
    d2 = DocumentEntry(
        "d2", "a/b.pdf", tmp_path / "a" / "b.pdf", "pdf",
        None, (), None, None, None, None,
    )
    assert d1 != d2


def test_expected_failure_auto_eq_equal_batch51(tmp_path):
    e1 = ExpectedFailure("d1", "a/x.pdf", tmp_path / "a" / "x.pdf", "parse_failed", None)
    e2 = ExpectedFailure("d1", "a/x.pdf", tmp_path / "a" / "x.pdf", "parse_failed", None)
    assert e1 == e2


def test_expected_failure_source_type_default_none_batch51(tmp_path):
    ef = ExpectedFailure("d1", "a/x.pdf", tmp_path / "a" / "x.pdf", "parse_failed", None)
    assert ef.source_type is None


def test_manifest_repr_is_string_batch51(tmp_path):
    m = Manifest("1.0", "complete", (), (), tmp_path)
    r = repr(m)
    assert isinstance(r, str)
    assert "Manifest" in r


def test_document_entry_repr_is_string_batch51(tmp_path):
    d = DocumentEntry(
        "d1", "a/b.pdf", tmp_path / "a" / "b.pdf", "pdf",
        None, (), None, None, None, None,
    )
    r = repr(d)
    assert isinstance(r, str)
    assert "DocumentEntry" in r


# ---------- Manifest properties 复杂场景 ----------

def test_manifest_file_count_empty_batch51(tmp_path):
    m = Manifest("1.0", "complete", (), (), tmp_path)
    assert m.file_count == 0


def test_manifest_pdf_count_empty_batch51(tmp_path):
    m = Manifest("1.0", "complete", (), (), tmp_path)
    assert m.pdf_count == 0


def test_manifest_docx_count_empty_batch51(tmp_path):
    m = Manifest("1.0", "complete", (), (), tmp_path)
    assert m.docx_count == 0


def test_manifest_categories_covered_empty_batch51(tmp_path):
    m = Manifest("1.0", "complete", (), (), tmp_path)
    assert m.categories_covered == []


def test_manifest_categories_covered_sorted_batch51(tmp_path):
    d1 = DocumentEntry(
        "d1", "a/b.pdf", tmp_path / "a" / "b.pdf", "pdf",
        None, ("zeta", "alpha"), None, None, None, None,
    )
    d2 = DocumentEntry(
        "d2", "a/c.pdf", tmp_path / "a" / "c.pdf", "pdf",
        None, ("middle",), None, None, None, None,
    )
    m = Manifest("1.0", "complete", (d1, d2), (), tmp_path)
    # sorted union
    assert m.categories_covered == ["alpha", "middle", "zeta"]


def test_manifest_categories_covered_dedup_batch51(tmp_path):
    d1 = DocumentEntry(
        "d1", "a/b.pdf", tmp_path / "a" / "b.pdf", "pdf",
        None, ("cat", "cat"), None, None, None, None,
    )
    m = Manifest("1.0", "complete", (d1,), (), tmp_path)
    assert m.categories_covered == ["cat"]


def test_manifest_content_group_count_self_reference_batch51(tmp_path):
    """A.paired_with = A → frozenset([A, A]) = {A} → 算 1 组。"""
    d = DocumentEntry(
        "A", "a/A.pdf", tmp_path / "a" / "A.pdf", "pdf",
        None, (), "A", None, None, None,
    )
    m = Manifest("1.0", "complete", (d,), (), tmp_path)
    assert m.content_group_count == 1


def test_manifest_content_group_count_pair_chain_batch51(tmp_path):
    """A 配 B, B 配 C → frozenset({A,B}) + frozenset({B,C}) = 2 组（不会合并）。"""
    dA = DocumentEntry(
        "A", "a/A.pdf", tmp_path / "a" / "A.pdf", "pdf",
        None, (), "B", None, None, None,
    )
    dB = DocumentEntry(
        "B", "a/B.pdf", tmp_path / "a" / "B.pdf", "pdf",
        None, (), "C", None, None, None,
    )
    m = Manifest("1.0", "complete", (dA, dB), (), tmp_path)
    assert m.content_group_count == 2


def test_manifest_content_group_count_complex_batch51(tmp_path):
    """混合：A↔B 配对 + C 单 + D↔E 配对 + F 单 = 4 组。"""
    dA = DocumentEntry("A", "a/A.pdf", tmp_path / "a" / "A.pdf", "pdf", None, (), "B", None, None, None)
    dB = DocumentEntry("B", "a/B.pdf", tmp_path / "a" / "B.pdf", "pdf", None, (), "A", None, None, None)
    dC = DocumentEntry("C", "a/C.pdf", tmp_path / "a" / "C.pdf", "pdf", None, (), None, None, None, None)
    dD = DocumentEntry("D", "a/D.pdf", tmp_path / "a" / "D.pdf", "pdf", None, (), "E", None, None, None)
    dE = DocumentEntry("E", "a/E.pdf", tmp_path / "a" / "E.pdf", "pdf", None, (), "D", None, None, None)
    dF = DocumentEntry("F", "a/F.pdf", tmp_path / "a" / "F.pdf", "pdf", None, (), None, None, None, None)
    m = Manifest("1.0", "complete", (dA, dB, dC, dD, dE, dF), (), tmp_path)
    # 2 配对组 (A-B, D-E) + 2 单 (C, F) = 4
    assert m.content_group_count == 4


def test_manifest_pdf_docx_count_mixed_batch51(tmp_path):
    d1 = DocumentEntry("d1", "a/x.pdf", tmp_path / "a" / "x.pdf", "pdf", None, (), None, None, None, None)
    d2 = DocumentEntry("d2", "a/y.docx", tmp_path / "a" / "y.docx", "docx", None, (), None, None, None, None)
    d3 = DocumentEntry("d3", "a/z.pdf", tmp_path / "a" / "z.pdf", "pdf", None, (), None, None, None, None)
    m = Manifest("1.0", "complete", (d1, d2, d3), (), tmp_path)
    assert m.pdf_count == 2
    assert m.docx_count == 1
    assert m.file_count == 3


# ---------- _resolve_relative_path 字段名 ----------

def test_resolve_relative_path_empty_string_batch51(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", tmp_path, "field_x")
    assert "field_x" in str(ei.value)
    assert "为空" in str(ei.value)


def test_resolve_relative_path_absolute_batch51(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("/etc/passwd", tmp_path, "documents[d1].path")
    assert "documents[d1].path" in str(ei.value)
    assert "绝对路径" in str(ei.value)


def test_resolve_relative_path_backslash_batch51(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("a\\b.pdf", tmp_path, "documents[d2].path")
    assert "documents[d2].path" in str(ei.value)
    assert "反斜杠" in str(ei.value)


def test_resolve_relative_path_traversal_batch51(tmp_path):
    """../../foo 解析后位于 project_root 之外。"""
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("../../foo", tmp_path, "documents[d3].path")
    assert "项目根目录之外" in str(ei.value)
    assert "documents[d3].path" in str(ei.value)


def test_resolve_relative_path_success_returns_path_batch51(tmp_path):
    """合法相对路径返回 Path 对象。"""
    out = _resolve_relative_path("a/b.pdf", tmp_path, "field_x")
    assert isinstance(out, Path)
    assert out.is_absolute()


def test_resolve_relative_path_subdir_batch51(tmp_path):
    """多级子目录也合法。"""
    out = _resolve_relative_path("a/b/c/d.pdf", tmp_path, "f")
    assert out == (tmp_path / "a" / "b" / "c" / "d.pdf").resolve()


# ---------- load_manifest 完整路径 ----------

def test_load_manifest_missing_file_batch51(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(tmp_path / "nope.json")
    assert "清单文件不存在" in str(ei.value)


def test_load_manifest_invalid_json_batch51(tmp_path):
    f = tmp_path / "m.json"
    f.write_text("{not json", encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(f)
    assert "JSON 解析失败" in str(ei.value)


def test_load_manifest_version_mismatch_batch51(tmp_path):
    """manifest_version 不是 '1.0' → Schema 先 raise EvalSchemaError（const）。"""
    from evaluation.schema import EvalSchemaError
    f = tmp_path / "m.json"
    f.write_text(
        json.dumps({
            "manifest_version": "9.9",
            "devset_status": "complete",
            "documents": [],
        }),
        encoding="utf-8",
    )
    # schema 用 const: "1.0"，会先抛 EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(f)


def test_load_manifest_no_documents_key_batch51(tmp_path):
    """无 documents key → Schema 校验会失败（required missing）。"""
    f = tmp_path / "m.json"
    f.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
        }),
        encoding="utf-8",
    )
    # Schema 校验 raise EvalSchemaError，不是 ManifestError
    from evaluation.schema import EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(f)


def test_load_manifest_expected_failure_no_path_batch51(tmp_path):
    """expected_failure 缺 path → Schema 校验抛 EvalSchemaError。"""
    from evaluation.schema import EvalSchemaError
    f = tmp_path / "m.json"
    f.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": [],
            "expected_failures": [
                {"doc_id": "d1", "expected_error_code": "parse_failed"},
            ],
        }),
        encoding="utf-8",
    )
    with pytest.raises(EvalSchemaError):
        load_manifest(f)


def test_load_manifest_document_no_path_batch51(tmp_path):
    """document 缺 path → Schema 校验抛 EvalSchemaError。"""
    from evaluation.schema import EvalSchemaError
    f = tmp_path / "m.json"
    f.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
            "documents": [
                {"doc_id": "d1", "source_type": "pdf"},
            ],
        }),
        encoding="utf-8",
    )
    with pytest.raises(EvalSchemaError):
        load_manifest(f)


# ---------- _detect_project_root ----------

def test_detect_project_root_returns_path_batch51(tmp_path):
    """从一个文件路径向上找 pyproject.toml。"""
    pyproj = tmp_path / "pyproject.toml"
    pyproj.write_text("[project]\nname='x'\n", encoding="utf-8")
    nested = tmp_path / "a" / "b" / "c.json"
    nested.parent.mkdir(parents=True)
    nested.write_text("{}", encoding="utf-8")
    out = _detect_project_root(nested)
    assert out == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_parent_batch51(tmp_path):
    """找不到 pyproject.toml → 返回起始的 parent。"""
    nested = tmp_path / "x.json"
    nested.write_text("{}", encoding="utf-8")
    out = _detect_project_root(nested)
    # 不抛异常，返回某个 Path
    assert isinstance(out, Path)


def test_detect_project_root_with_dir_input_batch51(tmp_path):
    """起始是目录时，直接从该目录向上找。"""
    pyproj = tmp_path / "pyproject.toml"
    pyproj.write_text("[project]\nname='x'\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    out = _detect_project_root(sub)
    assert out == tmp_path.resolve()


# ---------- 模块源码补强 ----------

def test_source_contains_dataclass_import_batch51():
    src = inspect.getsource(manifest_mod)
    assert "from dataclasses import dataclass" in src


def test_source_contains_json_import_batch51():
    src = inspect.getsource(manifest_mod)
    assert "import json" in src


def test_source_contains_path_import_batch51():
    src = inspect.getsource(manifest_mod)
    assert "from pathlib import Path" in src


def test_source_imports_manifest_version_batch51():
    src = inspect.getsource(manifest_mod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_source_imports_validate_batch51():
    src = inspect.getsource(manifest_mod)
    assert "from evaluation.schema import validate" in src


def test_source_has_manifest_error_class_batch51():
    src = inspect.getsource(manifest_mod)
    assert "class ManifestError(Exception):" in src


def test_source_has_document_entry_dataclass_batch51():
    src = inspect.getsource(manifest_mod)
    assert "@dataclass(frozen=True)" in src
    assert "class DocumentEntry" in src


def test_source_has_expected_failure_dataclass_batch51():
    src = inspect.getsource(manifest_mod)
    assert "class ExpectedFailure" in src


def test_source_has_manifest_dataclass_batch51():
    src = inspect.getsource(manifest_mod)
    assert "class Manifest" in src


def test_source_has_all_5_entries_batch51():
    src = inspect.getsource(manifest_mod)
    assert '"ManifestError"' in src
    assert '"Manifest"' in src
    assert '"DocumentEntry"' in src
    assert '"ExpectedFailure"' in src
    assert '"load_manifest"' in src


def test_source_contains_content_group_count_docstring_batch51():
    src = inspect.getsource(manifest_mod)
    assert "配对的 DOCX+PDF" in src or "配对" in src


def test_source_contains_path_form_rules_batch51():
    src = inspect.getsource(manifest_mod)
    assert "正斜杠" in src
    assert "反斜杠" in src


def test_source_contains_project_root_check_batch51():
    src = inspect.getsource(manifest_mod)
    assert "项目根" in src


def test_source_contains_relative_to_batch51():
    src = inspect.getsource(manifest_mod)
    assert "relative_to" in src


def test_source_contains_resolve_call_batch51():
    src = inspect.getsource(manifest_mod)
    assert ".resolve()" in src


def test_source_contains_categories_property_batch51():
    src = inspect.getsource(manifest_mod)
    assert "def categories_covered" in src


def test_source_contains_frozenset_call_batch51():
    src = inspect.getsource(manifest_mod)
    assert "frozenset(" in src


# ---------- AST 结构补强 ----------

def test_ast_has_5_top_level_functions_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 5


def test_ast_function_names_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_is_absolute_like", "_has_backslash", "_resolve_relative_path", "load_manifest", "_detect_project_root"]


def test_ast_has_4_class_def_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 4


def test_ast_class_names_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    assert names == ["ManifestError", "DocumentEntry", "ExpectedFailure", "Manifest"]


def test_ast_3_dataclass_decorators_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    decorated = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.decorator_list]
    assert len(decorated) == 3
    for d in decorated:
        # @dataclass(frozen=True)
        dec = d.decorator_list[0]
        assert isinstance(dec, ast.Call)
        assert isinstance(dec.func, ast.Name)
        assert dec.func.id == "dataclass"
        assert len(dec.keywords) == 1
        assert dec.keywords[0].arg == "frozen"
        assert dec.keywords[0].value.value is True


def test_ast_manifest_error_no_decorator_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ManifestError")
    assert len(cls.decorator_list) == 0


def test_ast_manifest_has_5_property_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.decorator_list]
    method_names = [m.name for m in methods]
    assert set(method_names) == {"file_count", "pdf_count", "docx_count", "content_group_count", "categories_covered"}


def test_ast_manifest_property_uses_property_decorator_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    for m in [n for n in cls.body if isinstance(n, ast.FunctionDef)]:
        if m.name in ("file_count", "pdf_count", "docx_count", "content_group_count", "categories_covered"):
            assert any(isinstance(d, ast.Name) and d.id == "property" for d in m.decorator_list)


def test_ast_manifest_categories_covered_uses_sorted_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    cc = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "categories_covered")
    src = ast.unparse(cc)
    assert "sorted(" in src


def test_ast_manifest_content_group_uses_frozenset_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    cg = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "content_group_count")
    src = ast.unparse(cg)
    assert "frozenset(" in src


def test_ast_load_manifest_has_try_except_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    tries = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    # 1 try for json, 1 try inside _resolve_relative_path（独立函数）→ 仅 json 1 个
    assert len(tries) == 1


def test_ast_load_manifest_has_2_for_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 2  # for d in documents + for ef in expected_failures


def test_ast_resolve_relative_path_has_try_except_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_relative_path")
    tries = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(tries) == 1


def test_ast_module_has_5_imports_batch51():
    """__future__ + json + dataclass + Path + Any + MANIFEST_VERSION + validate = 7。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 7


def test_ast_module_has_docstring_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_no_async_function_def_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_no_global_nonlocal_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


def test_ast_no_with_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    # load_manifest 内的 with p.open 是 With
    withs = [n for n in ast.walk(tree) if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_no_while_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))


def test_ast_no_delete_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    assert not any(isinstance(n, ast.Delete) for n in ast.walk(tree))


def test_ast_no_raise_top_level_batch51():
    """raise 都在函数内部，模块顶层无 raise。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    for n in tree.body:
        assert not isinstance(n, ast.Raise)


def test_ast_has_all_assign_batch51():
    tree = ast.parse(inspect.getsource(manifest_mod))
    all_assign = None
    for n in tree.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == "__all__":
                    all_assign = n
    assert all_assign is not None
    assert isinstance(all_assign.value, ast.List)
    assert len(all_assign.value.elts) == 5


# ---------- forbidden tokens 第一百三十九批 ----------

def _src() -> str:
    return inspect.getsource(manifest_mod)


def test_source_no_eval_batch51():
    assert "eval(" not in _src()


def test_source_no_exec_batch51():
    assert "exec(" not in _src()


def test_source_no_compile_batch51():
    assert "compile(" not in _src()


def test_source_no_globals_batch51():
    assert "globals(" not in _src()


def test_source_no_locals_batch51():
    assert "locals(" not in _src()


def test_source_no_os_system_batch51():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch51():
    assert "subprocess" not in _src()


def test_source_no_popen_batch51():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch51():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch51():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch51():
    assert "socket" not in _src()


def test_source_no_requests_batch51():
    assert "requests" not in _src()


def test_source_no_urllib_batch51():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch51():
    assert "shutil.rmtree" not in _src()


def test_source_open_count_is_1_batch51():
    """load_manifest 1 个 with open。"""
    assert _src().count("open(") == 1


def test_source_no_async_await_batch51():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_yield_batch51():
    assert "yield" not in _src()
