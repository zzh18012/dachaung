"""evaluation/manifest.py 第九十二轮 edges 测试（Round 675）。

补强 edges76 未触及的角度（第五十二批）。

新角度：
- Manifest properties 更深（content_group_count 多对一 pair / 多组同时配 / frozenset 去重）
- Manifest categories_covered 大小写敏感 / 数字 category / 多 doc 同 category
- _resolve_relative_path 路径混合（含 ../ 的相对合法路径 / 含 ./ 的相对合法路径 / 含 ./ 的绝对路径）
- _is_absolute_like 更多 Unicode（拉丁字母 / 西里尔字母 / 韩文字母）
- _detect_project_root 起始路径是当前工作目录的文件
- load_manifest 完整成功路径（含 documents + expected_failures + annotation_file）
- load_manifest annotation_file 解析（合法 / 不存在 raise / 绝对路径 raise / 反斜杠 raise）
- DocumentEntry annotation_resolved 字段（None 默认 / Path 对象）
- 模块源码补强（frozen=True / ManifestError 文档字符串 / dataclass 字段顺序）
- AST 结构补强（Manifest 5 property 函数 + decorator / DocumentEntry 10 fields / ExpectedFailure 5 fields / load_manifest 完整 AST 检查）
- forbidden tokens 第一百四十五批
"""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
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


# ---------- Manifest properties 更深 ----------

def _make_doc(doc_id, paired_with=None, categories=(), source_type="pdf", tmp_path=None):
    return DocumentEntry(
        doc_id=doc_id,
        path_str=f"a/{doc_id}.pdf",
        resolved_path=(tmp_path or Path(".")) / "a" / f"{doc_id}.pdf",
        source_type=source_type,
        sha256=None,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def test_content_group_count_pair_one_direction_batch52(tmp_path):
    """A 配 B，B 不配 A → frozenset([A,B]) 算 1 组。"""
    dA = _make_doc("A", paired_with="B", tmp_path=tmp_path)
    dB = _make_doc("B", paired_with=None, tmp_path=tmp_path)
    m = Manifest("1.0", "complete", (dA, dB), (), tmp_path)
    # pair_ids = {frozenset(A, B)}, all_paired = {A}
    # 验证：B 不在 all_paired 也不在 seen，但 dA 已 seen
    # 实际：A.paired_with=B → frozenset([A,B])；B.paired_with=None → 不算
    # groups=1; seen={A, B}; unpaired: A 在 seen, B 在 seen → unpaired=0
    assert m.content_group_count == 1


def test_content_group_count_pair_one_direction_reversed_batch52(tmp_path):
    """A 不配 B，B 配 A → frozenset([B,A]) 算 1 组。"""
    dA = _make_doc("A", paired_with=None, tmp_path=tmp_path)
    dB = _make_doc("B", paired_with="A", tmp_path=tmp_path)
    m = Manifest("1.0", "complete", (dA, dB), (), tmp_path)
    assert m.content_group_count == 1


def test_content_group_count_unpaired_with_paired_with_set_to_other_batch52(tmp_path):
    """A 配 B，C 配 D（不存在的 doc） → 2 组。"""
    dA = _make_doc("A", paired_with="B", tmp_path=tmp_path)
    dC = _make_doc("C", paired_with="D", tmp_path=tmp_path)  # D 不在 manifest
    m = Manifest("1.0", "complete", (dA, dC), (), tmp_path)
    # 2 frozensets: {A,B}, {C,D}
    # groups=2; seen={A,B,C,D}; unpaired=0
    assert m.content_group_count == 2


def test_content_group_count_pair_chain_AB_BC_batch52(tmp_path):
    """A 配 B + B 配 C → frozenset([A,B]) + frozenset([B,C]) → 2 组。"""
    dA = _make_doc("A", paired_with="B", tmp_path=tmp_path)
    dB = _make_doc("B", paired_with="C", tmp_path=tmp_path)
    m = Manifest("1.0", "complete", (dA, dB), (), tmp_path)
    assert m.content_group_count == 2


def test_content_group_count_only_unpaired_batch52(tmp_path):
    """所有 doc 都 unpaired → unpaired 数 = doc 数。"""
    docs = tuple(_make_doc(f"d{i}", tmp_path=tmp_path) for i in range(5))
    m = Manifest("1.0", "complete", docs, (), tmp_path)
    assert m.content_group_count == 5


def test_content_group_count_pair_makes_2_seen_excludes_unpaired_batch52(tmp_path):
    """A↔B + C unpaired → 1 组（pair） + 1 单 = 2。"""
    dA = _make_doc("A", paired_with="B", tmp_path=tmp_path)
    dB = _make_doc("B", paired_with="A", tmp_path=tmp_path)
    dC = _make_doc("C", tmp_path=tmp_path)
    m = Manifest("1.0", "complete", (dA, dB, dC), (), tmp_path)
    assert m.content_group_count == 2


def test_categories_covered_case_sensitive_batch52(tmp_path):
    """大小写不同视为不同 category。"""
    d = _make_doc("d1", categories=("Foo", "foo"), tmp_path=tmp_path)
    m = Manifest("1.0", "complete", (d,), (), tmp_path)
    assert m.categories_covered == ["Foo", "foo"]


def test_categories_covered_numeric_string_batch52(tmp_path):
    """数字字符串也算 category。"""
    d = _make_doc("d1", categories=("1", "2", "3"), tmp_path=tmp_path)
    m = Manifest("1.0", "complete", (d,), (), tmp_path)
    assert m.categories_covered == ["1", "2", "3"]


def test_categories_covered_multi_doc_same_category_batch52(tmp_path):
    """多 doc 共享 category → sorted unique。"""
    d1 = _make_doc("d1", categories=("a", "b"), tmp_path=tmp_path)
    d2 = _make_doc("d2", categories=("b", "c"), tmp_path=tmp_path)
    d3 = _make_doc("d3", categories=("c", "a"), tmp_path=tmp_path)
    m = Manifest("1.0", "complete", (d1, d2, d3), (), tmp_path)
    assert m.categories_covered == ["a", "b", "c"]


# ---------- _resolve_relative_path 路径混合 ----------

def test_resolve_relative_path_with_dot_slash_batch52(tmp_path):
    """./foo 合法（不以 / 开头）。"""
    out = _resolve_relative_path("./foo", tmp_path, "f")
    assert out == (tmp_path / "foo").resolve()


def test_resolve_relative_path_double_dot_subdir_batch52(tmp_path):
    """foo/../bar → 解析后还在 tmp_path 内。"""
    out = _resolve_relative_path("foo/../bar", tmp_path, "f")
    assert out == (tmp_path / "bar").resolve()


def test_resolve_relative_path_double_dot_escape_batch52(tmp_path):
    """../foo → 解析后位于 tmp_path 之外 → raise。"""
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("../foo", tmp_path, "f")
    assert "项目根目录之外" in str(ei.value)


def test_resolve_relative_path_multi_level_subdir_batch52(tmp_path):
    out = _resolve_relative_path("a/b/c/d.txt", tmp_path, "f")
    assert out == (tmp_path / "a" / "b" / "c" / "d.txt").resolve()


def test_resolve_relative_path_filename_only_batch52(tmp_path):
    out = _resolve_relative_path("foo.txt", tmp_path, "f")
    assert out == (tmp_path / "foo.txt").resolve()


# ---------- _is_absolute_like 更多 Unicode ----------

def test_is_absolute_like_latin_extended_batch51():
    """Latin Extended 字母也算 alpha。"""
    assert _is_absolute_like("Å:/x") is True


def test_is_absolute_like_cyrillic_batch51():
    """西里尔字母也算 alpha。"""
    assert _is_absolute_like("Я:/x") is True


def test_is_absolute_like_korean_batch51():
    """韩文字母也算 alpha。"""
    assert _is_absolute_like("가:/x") is True


def test_is_absolute_like_japanese_kana_batch51():
    """日文假名也算 alpha。"""
    assert _is_absolute_like("あ:/x") is True


# ---------- _detect_project_root 起始路径 ----------

def test_detect_project_root_file_in_nested_dir_batch52(tmp_path):
    """从深嵌套文件路径向上找。"""
    pyproj = tmp_path / "pyproject.toml"
    pyproj.write_text("[project]\nname='x'\n", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c" / "d.json"
    deep.parent.mkdir(parents=True)
    deep.write_text("{}", encoding="utf-8")
    out = _detect_project_root(deep)
    assert out == tmp_path.resolve()


def test_detect_project_root_returns_path_type_batch52(tmp_path):
    out = _detect_project_root(tmp_path / "nonexistent.json")
    assert isinstance(out, Path)


def test_detect_project_root_handles_directory_input_batch52(tmp_path):
    pyproj = tmp_path / "pyproject.toml"
    pyproj.write_text("[project]\nname='x'\n", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


# ---------- load_manifest 完整成功路径 ----------

def test_load_manifest_full_success_batch52(tmp_path):
    """完整 manifest with documents + expected_failures + annotation_file。"""
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"fake pdf")
    annotation = tmp_path / "ann.json"
    annotation.write_text("{}", encoding="utf-8")
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "x.pdf",
                "source_type": "pdf",
                "categories": ["report"],
                "annotation_file": "ann.json",
                "expectations": {"element_count_by_type": {"paragraph": 5}},
            },
        ],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(m_path, project_root=tmp_path)
    assert m.manifest_version == "1.0"
    assert m.devset_status == "complete"
    assert len(m.documents) == 1
    d = m.documents[0]
    assert d.doc_id == "d1"
    assert d.source_type == "pdf"
    assert d.categories == ("report",)
    assert d.annotation_file_str == "ann.json"
    assert d.annotation_resolved == annotation.resolve()
    assert d.expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_annotation_file_missing_batch52(tmp_path):
    """annotation_file 指向不存在文件 → resolved 指向不存在的 Path（load_manifest 不校验存在）。"""
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"fake pdf")
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "x.pdf",
                "source_type": "pdf",
                "annotation_file": "missing.json",
            },
        ],
    }), encoding="utf-8")
    # 不抛异常（_resolve_relative_path 只校验路径形式）
    m = load_manifest(m_path, project_root=tmp_path)
    assert m.documents[0].annotation_resolved == (tmp_path / "missing.json").resolve()
    assert not m.documents[0].annotation_resolved.is_file()


def test_load_manifest_annotation_file_absolute_path_batch52(tmp_path):
    """annotation_file 是绝对路径 → raise。"""
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"fake pdf")
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "x.pdf",
                "source_type": "pdf",
                "annotation_file": "/absolute/path.json",
            },
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(m_path, project_root=tmp_path)
    assert "绝对路径" in str(ei.value)


def test_load_manifest_annotation_file_backslash_batch52(tmp_path):
    """annotation_file 含反斜杠 → raise。"""
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"fake pdf")
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "x.pdf",
                "source_type": "pdf",
                "annotation_file": "sub\\ann.json",
            },
        ],
    }), encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(m_path, project_root=tmp_path)
    assert "反斜杠" in str(ei.value)


def test_load_manifest_no_annotation_file_batch52(tmp_path):
    """无 annotation_file → DocumentEntry.annotation_resolved is None。"""
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"fake pdf")
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"},
        ],
    }), encoding="utf-8")
    m = load_manifest(m_path, project_root=tmp_path)
    assert m.documents[0].annotation_resolved is None


def test_load_manifest_expected_failures_full_batch52(tmp_path):
    """expected_failures 完整字段。"""
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"fake")
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "ef1",
                "path": "x.pdf",
                "expected_error_code": "parse_failed",
                "source_type": "pdf",
            },
        ],
    }), encoding="utf-8")
    m = load_manifest(m_path, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    ef = m.expected_failures[0]
    assert ef.doc_id == "ef1"
    assert ef.expected_error_code == "parse_failed"
    assert ef.source_type == "pdf"


def test_load_manifest_expected_failures_no_source_type_batch52(tmp_path):
    """expected_failure 无 source_type → 默认 None。"""
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"fake")
    m_path = tmp_path / "m.json"
    m_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "x.pdf", "expected_error_code": "x"},
        ],
    }), encoding="utf-8")
    m = load_manifest(m_path, project_root=tmp_path)
    assert m.expected_failures[0].source_type is None


# ---------- DocumentEntry annotation_resolved 字段 ----------

def test_document_entry_annotation_resolved_default_none_batch52(tmp_path):
    d = _make_doc("d1", tmp_path=tmp_path)
    assert d.annotation_resolved is None


def test_document_entry_annotation_resolved_set_to_path_batch52(tmp_path):
    ann_path = tmp_path / "ann.json"
    d = DocumentEntry(
        doc_id="d1",
        path_str="x.pdf",
        resolved_path=tmp_path / "x.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str="ann.json",
        annotation_resolved=ann_path,
        expectations=None,
    )
    assert d.annotation_resolved == ann_path


# ---------- dataclass 字段 ----------

def test_document_entry_has_10_fields_batch52():
    flds = [f.name for f in fields(DocumentEntry)]
    assert set(flds) == {
        "doc_id", "path_str", "resolved_path", "source_type", "sha256",
        "categories", "paired_with", "annotation_file_str",
        "annotation_resolved", "expectations",
    }


def test_expected_failure_has_5_fields_batch52():
    flds = [f.name for f in fields(ExpectedFailure)]
    assert set(flds) == {
        "doc_id", "path_str", "resolved_path",
        "expected_error_code", "source_type",
    }


def test_manifest_has_5_fields_batch52():
    flds = [f.name for f in fields(Manifest)]
    assert set(flds) == {
        "manifest_version", "devset_status", "documents",
        "expected_failures", "project_root",
    }


# ---------- 模块源码补强 ----------

def test_source_imports_dataclass_batch52():
    src = inspect.getsource(manifest_mod)
    assert "from dataclasses import dataclass" in src


def test_source_has_3_frozen_dataclass_batch52():
    """DocumentEntry / ExpectedFailure / Manifest 都是 frozen=True。"""
    src = inspect.getsource(manifest_mod)
    # @dataclass(frozen=True) 出现 3 次
    assert src.count("@dataclass(frozen=True)") == 3


def test_source_has_manifest_error_docstring_batch52():
    src = inspect.getsource(manifest_mod)
    assert "清单加载或校验失败" in src


def test_source_has_no_mutation_methods_batch52():
    """frozen dataclass 没有显式 __setattr__。"""
    src = inspect.getsource(manifest_mod)
    assert "__setattr__" not in src


def test_source_contains_path_form_rules_docstring_batch52():
    src = inspect.getsource(manifest_mod)
    assert "相对路径" in src
    assert "正斜杠" in src


def test_source_contains_no_secret_paths_note_batch52():
    src = inspect.getsource(manifest_mod)
    assert "不把本机绝对路径" in src or "项目根" in src


# ---------- AST 结构补强 ----------

def test_ast_3_dataclass_decorators_with_frozen_true_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    decorated = [
        n for n in tree.body
        if isinstance(n, ast.ClassDef) and n.decorator_list
    ]
    assert len(decorated) == 3
    for d in decorated:
        dec = d.decorator_list[0]
        assert isinstance(dec, ast.Call)
        assert isinstance(dec.func, ast.Name)
        assert dec.func.id == "dataclass"
        assert len(dec.keywords) == 1
        assert dec.keywords[0].arg == "frozen"
        assert dec.keywords[0].value.value is True


def test_ast_manifest_error_extends_exception_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ManifestError")
    assert len(cls.bases) == 1
    assert isinstance(cls.bases[0], ast.Name)
    assert cls.bases[0].id == "Exception"


def test_ast_document_entry_10_fields_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "DocumentEntry")
    # 字段是 AnnAssign（带 annotation）
    annots = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    assert len(annots) == 10


def test_ast_expected_failure_5_fields_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ExpectedFailure")
    annots = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    assert len(annots) == 5


def test_ast_manifest_5_fields_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    annots = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    assert len(annots) == 5


def test_ast_manifest_5_property_functions_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    properties = [
        n for n in cls.body
        if isinstance(n, ast.FunctionDef)
        and any(isinstance(d, ast.Name) and d.id == "property" for d in n.decorator_list)
    ]
    assert len(properties) == 5
    names = {p.name for p in properties}
    assert names == {"file_count", "pdf_count", "docx_count", "content_group_count", "categories_covered"}


def test_ast_load_manifest_signature_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    args = func.args
    # 2 positional args: manifest_path, project_root（默认 None）
    assert len(args.args) == 2
    # project_root 有默认值
    assert len(args.defaults) == 1


def test_ast_resolve_relative_path_signature_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_relative_path")
    args = func.args
    assert len(args.args) == 3  # path_str, project_root, field_name


def test_ast_module_no_async_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_module_no_star_import_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


def test_ast_no_with_at_module_level_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    for n in tree.body:
        assert not isinstance(n, ast.With)


def test_ast_no_global_nonlocal_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


# ---------- forbidden tokens 第一百四十五批 ----------

def _src() -> str:
    return inspect.getsource(manifest_mod)


def test_source_no_eval_batch52():
    assert "eval(" not in _src()


def test_source_no_exec_batch52():
    assert "exec(" not in _src()


def test_source_no_compile_batch52():
    assert "compile(" not in _src()


def test_source_no_globals_batch52():
    assert "globals(" not in _src()


def test_source_no_locals_batch52():
    assert "locals(" not in _src()


def test_source_no_os_system_batch52():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch52():
    assert "subprocess" not in _src()


def test_source_no_popen_batch52():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch52():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch52():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch52():
    assert "socket" not in _src()


def test_source_no_requests_batch52():
    assert "requests" not in _src()


def test_source_no_urllib_batch52():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch52():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch52():
    assert "yield" not in _src()


def test_source_no_async_await_batch52():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch52():
    """load_manifest 1 个 with open。"""
    assert _src().count("open(") == 1
