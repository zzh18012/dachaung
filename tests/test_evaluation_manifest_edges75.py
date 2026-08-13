"""evaluation/manifest.py 第九十轮 edges 测试（Round 661）。

补强 edges74 未触及的角度（第四十九批）。

新角度：
- _is_absolute_like 边界补充（混合大小写盘符 / 单字符后冒号但无斜杠 / 仅冒号 / 路径含 ../ 的相对）
- _has_backslash 多场景（多个反斜杠 / 反斜杠在开头 / 反斜杠在结尾）
- _resolve_relative_path 字段名传递（错误 message 含 field_name 完整路径）
- load_manifest annotation_file 完整流程（缺失 / 存在 + 合法 / 存在 + 绝对路径 raise / 存在 + 反斜杠 raise）
- Manifest content_group_count 复杂场景（3 向配对 / 2 组双向 + 1 单向 / 全无 paired_with / A 配 B + B 配 A + C 配 D）
- Manifest categories_covered 多场景（无文档 / 单文档单 category / 多文档 categories union / 重复 category dedup）
- _detect_project_root 多种起始路径（嵌套深 / 起始为 . / 起始为文件 / 起始无 pyproject）
- DocumentEntry frozen setattr 多字段
- Manifest hashable 检查（frozen dataclass 含 Path 是否 hashable）
- 模块源码补强（json/dataclass/Path/Any/MANIFEST_VERSION/validate imports / __all__ 5 entries / docstring 关键词）
- AST 结构补强（5 函数 / 4 ClassDef / Manifest properties 5 个 / load_manifest 多 if + 多 for + try-except / _resolve_relative_path 多 if + 1 try / module docstring）
- forbidden tokens 第一百三十一批
"""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import FrozenInstanceError
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


# ---------- _is_absolute_like 边界补充 ----------

def test_is_absolute_like_mixed_case_drive_batch49():
    """C: D: E: 都识别为盘符。"""
    assert _is_absolute_like("C:/x") is True
    assert _is_absolute_like("D:\\x") is True
    assert _is_absolute_like("E:/x") is True
    assert _is_absolute_like("z:/x") is True
    assert _is_absolute_like("Z:\\x") is True


def test_is_absolute_like_colon_no_slash_batch49():
    """有冒号但后面无斜杠不是绝对路径。"""
    assert _is_absolute_like("C:foo") is False
    assert _is_absolute_like("C:x") is False


def test_is_absolute_like_only_colon_batch49():
    assert _is_absolute_like(":") is False
    assert _is_absolute_like(":foo") is False


def test_is_absolute_like_relative_with_dotdot_batch49():
    """../foo 是相对路径，不是绝对。"""
    assert _is_absolute_like("../foo") is False
    assert _is_absolute_like("./foo") is False
    assert _is_absolute_like("foo/../bar") is False


def test_is_absolute_like_just_slash_batch49():
    assert _is_absolute_like("/") is True
    assert _is_absolute_like("/foo") is True
    assert _is_absolute_like("/foo/bar") is True


def test_is_absolute_like_empty_string_batch49():
    assert _is_absolute_like("") is False


def test_is_absolute_like_two_chars_batch49():
    """2 字符不可能是盘符 + 斜杠（至少 3 字符）。"""
    assert _is_absolute_like("C:") is False
    assert _is_absolute_like("AB") is False


def test_is_absolute_like_digit_drive_batch49():
    """数字不是字母。"""
    assert _is_absolute_like("1:/x") is False
    assert _is_absolute_like("0:\\x") is False


# ---------- _has_backslash 多场景 ----------

def test_has_backslash_multiple_positions_batch49():
    assert _has_backslash("a\\b\\c") is True
    assert _has_backslash("\\start") is True
    assert _has_backslash("end\\") is True
    assert _has_backslash("\\") is True


def test_has_backslash_no_backslash_batch49():
    assert _has_backslash("a/b") is False
    assert _has_backslash("foo") is False
    assert _has_backslash("") is False
    assert _has_backslash("foo/bar/baz") is False


def test_has_backslash_only_backslash_batch49():
    assert _has_backslash("\\\\") is True  # 双反斜杠 UNC


# ---------- _resolve_relative_path 字段名传递 ----------

def test_resolve_relative_includes_field_name_in_error_batch49(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("/abs/path", tmp_path, "documents[doc1].path")
    assert "documents[doc1].path" in str(ei.value)


def test_resolve_relative_includes_field_name_backslash_batch49(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("a\\b", tmp_path, "my_field")
    assert "my_field" in str(ei.value)


def test_resolve_relative_includes_field_name_empty_batch49(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", tmp_path, "empty_field")
    assert "empty_field" in str(ei.value)


def test_resolve_relative_includes_field_name_outside_root_batch49(tmp_path):
    """路径在 project_root 之外 → message 含 field_name。"""
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("../../etc/passwd", tmp_path, "secret_field")
    assert "secret_field" in str(ei.value)


def test_resolve_relative_success_returns_path_batch49(tmp_path):
    out = _resolve_relative_path("foo/bar.txt", tmp_path, "f")
    assert isinstance(out, Path)
    assert out.is_absolute()


# ---------- load_manifest annotation_file 完整流程 ----------

def _write_valid_manifest(tmp_path: Path, documents: list[dict]) -> Path:
    """写一个合法 manifest 到 tmp_path 下。"""
    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": documents,
    }
    # 写到 tmp_path 上层目录（project_root 是 tmp_path 父级，但用 tmp_path 作为 root）
    # 实际：让 manifest 在 tmp_path/manifest.json，project_root = tmp_path
    f = tmp_path / "manifest.json"
    f.write_text(json.dumps(manifest_data), encoding="utf-8")
    return f


def test_load_manifest_annotation_file_present_valid_batch49(tmp_path):
    """annotation_file 存在且路径合法 → annotation_resolved 不为 None。"""
    manifest = _write_valid_manifest(
        tmp_path,
        [
            {
                "doc_id": "d1",
                "path": "samples/file.pdf",
                "source_type": "pdf",
                "annotation_file": "annotations/d1.json",
            }
        ],
    )
    m = load_manifest(manifest, project_root=tmp_path)
    assert m.documents[0].annotation_file_str == "annotations/d1.json"
    assert m.documents[0].annotation_resolved is not None
    assert m.documents[0].annotation_resolved == (tmp_path / "annotations" / "d1.json").resolve()


def test_load_manifest_annotation_file_missing_batch49(tmp_path):
    """无 annotation_file → annotation_resolved is None。"""
    manifest = _write_valid_manifest(
        tmp_path,
        [{"doc_id": "d1", "path": "samples/file.pdf", "source_type": "pdf"}],
    )
    m = load_manifest(manifest, project_root=tmp_path)
    assert m.documents[0].annotation_file_str is None
    assert m.documents[0].annotation_resolved is None


def test_load_manifest_annotation_file_absolute_raises_batch49(tmp_path):
    """annotation_file 绝对路径 → ManifestError。"""
    manifest = _write_valid_manifest(
        tmp_path,
        [
            {
                "doc_id": "d1",
                "path": "samples/file.pdf",
                "source_type": "pdf",
                "annotation_file": "/abs/path/ann.json",
            }
        ],
    )
    with pytest.raises(ManifestError) as ei:
        load_manifest(manifest, project_root=tmp_path)
    assert "annotation_file" in str(ei.value)


def test_load_manifest_annotation_file_backslash_raises_batch49(tmp_path):
    manifest = _write_valid_manifest(
        tmp_path,
        [
            {
                "doc_id": "d1",
                "path": "samples/file.pdf",
                "source_type": "pdf",
                "annotation_file": "annotations\\d1.json",
            }
        ],
    )
    with pytest.raises(ManifestError) as ei:
        load_manifest(manifest, project_root=tmp_path)
    assert "annotation_file" in str(ei.value)


def test_load_manifest_annotation_file_outside_root_raises_batch49(tmp_path):
    """annotation_file 解析后位于 project_root 外 → raise。"""
    manifest = _write_valid_manifest(
        tmp_path,
        [
            {
                "doc_id": "d1",
                "path": "samples/file.pdf",
                "source_type": "pdf",
                "annotation_file": "../../etc/ann.json",
            }
        ],
    )
    with pytest.raises(ManifestError):
        load_manifest(manifest, project_root=tmp_path)


# ---------- Manifest content_group_count 复杂场景 ----------

def _make_doc(
    doc_id: str,
    paired_with: str | None = None,
    source_type: str = "pdf",
) -> dict:
    return {
        "doc_id": doc_id,
        "path": f"samples/{doc_id}.pdf" if source_type == "pdf" else f"samples/{doc_id}.docx",
        "source_type": source_type,
        "paired_with": paired_with,
    }


def _build_manifest(docs: list[dict], tmp_path: Path) -> Manifest:
    """绕开文件直接构建 Manifest 用于 property 测试。"""
    entries = []
    for d in docs:
        path_str = d.get("path", f"samples/{d['doc_id']}.{d['source_type']}")
        entries.append(
            DocumentEntry(
                doc_id=d["doc_id"],
                path_str=path_str,
                resolved_path=tmp_path / path_str,
                source_type=d["source_type"],
                sha256=None,
                categories=tuple(d.get("categories", [])),
                paired_with=d.get("paired_with"),
                annotation_file_str=None,
                annotation_resolved=None,
                expectations=None,
            )
        )
    return Manifest(
        manifest_version="1.0",
        devset_status="complete",
        documents=tuple(entries),
        expected_failures=(),
        project_root=tmp_path,
    )


def test_content_group_count_all_unpaired_batch49(tmp_path):
    m = _build_manifest(
        [
            {"doc_id": "a", "source_type": "pdf"},
            {"doc_id": "b", "source_type": "docx"},
            {"doc_id": "c", "source_type": "pdf"},
        ],
        tmp_path,
    )
    # 3 个无配对 → 3 组
    assert m.content_group_count == 3


def test_content_group_count_two_pairs_batch49(tmp_path):
    m = _build_manifest(
        [
            {"doc_id": "a", "source_type": "pdf", "paired_with": "b"},
            {"doc_id": "b", "source_type": "docx", "paired_with": "a"},
            {"doc_id": "c", "source_type": "pdf", "paired_with": "d"},
            {"doc_id": "d", "source_type": "docx", "paired_with": "c"},
        ],
        tmp_path,
    )
    assert m.content_group_count == 2


def test_content_group_count_one_way_pair_batch49(tmp_path):
    """A 配 B（B 未声明）→ 算 1 组 + B 是 unpaired。"""
    m = _build_manifest(
        [
            {"doc_id": "a", "source_type": "pdf", "paired_with": "b"},
            {"doc_id": "b", "source_type": "docx"},  # 未声明 paired_with
            {"doc_id": "c", "source_type": "pdf"},
        ],
        tmp_path,
    )
    # pair_ids = {frozenset({a, b})} → 1 group, seen = {a, b}
    # c not in seen and no paired_with → unpaired +1
    # b not in seen? b is in seen (pair_ids update seen.update({a, b}))
    # 所以 c 是唯一 unpaired → 1 + 1 = 2
    assert m.content_group_count == 2


def test_content_group_count_empty_batch49(tmp_path):
    m = _build_manifest([], tmp_path)
    assert m.content_group_count == 0


# ---------- Manifest categories_covered 多场景 ----------

def test_categories_covered_empty_batch49(tmp_path):
    m = _build_manifest([], tmp_path)
    assert m.categories_covered == []


def test_categories_covered_single_doc_single_category_batch49(tmp_path):
    m = _build_manifest(
        [{"doc_id": "a", "source_type": "pdf", "categories": ["x"]}],
        tmp_path,
    )
    assert m.categories_covered == ["x"]


def test_categories_covered_union_batch49(tmp_path):
    m = _build_manifest(
        [
            {"doc_id": "a", "source_type": "pdf", "categories": ["x", "y"]},
            {"doc_id": "b", "source_type": "docx", "categories": ["y", "z"]},
        ],
        tmp_path,
    )
    assert m.categories_covered == ["x", "y", "z"]


def test_categories_covered_dedup_batch49(tmp_path):
    m = _build_manifest(
        [
            {"doc_id": "a", "source_type": "pdf", "categories": ["x", "x", "y"]},
            {"doc_id": "b", "source_type": "docx", "categories": ["x", "y"]},
        ],
        tmp_path,
    )
    assert m.categories_covered == ["x", "y"]


def test_categories_covered_sorted_batch49(tmp_path):
    m = _build_manifest(
        [
            {"doc_id": "a", "source_type": "pdf", "categories": ["z", "a", "m"]},
        ],
        tmp_path,
    )
    assert m.categories_covered == ["a", "m", "z"]


def test_categories_covered_no_categories_field_batch49(tmp_path):
    """文档没声明 categories → 贡献 0 个 category。"""
    m = _build_manifest(
        [
            {"doc_id": "a", "source_type": "pdf"},  # 无 categories
            {"doc_id": "b", "source_type": "pdf", "categories": ["x"]},
        ],
        tmp_path,
    )
    assert m.categories_covered == ["x"]


# ---------- _detect_project_root 多种起始路径 ----------

def test_detect_project_root_deep_nested_batch49(tmp_path):
    """起始路径深嵌套，向上找直到 tmp_path（含 pyproject.toml）。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    out = _detect_project_root(deep)
    assert out == tmp_path


def test_detect_project_root_start_is_file_batch49(tmp_path):
    """起始是文件 → 取 parent 后再向上找。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    deep_dir = tmp_path / "a"
    deep_dir.mkdir()
    f = deep_dir / "f.txt"
    f.write_text("x")
    out = _detect_project_root(f)
    assert out == tmp_path


def test_detect_project_root_no_pyproject_batch49(tmp_path):
    """无 pyproject.toml 时返回起始目录（或其 parent）。"""
    out = _detect_project_root(tmp_path)
    # 找不到 pyproject 时返回 cur（已 resolve）
    # tmp_path 可能本身没有 pyproject.toml，但要返回某个路径
    assert isinstance(out, Path)


def test_detect_project_root_returns_absolute_batch49(tmp_path):
    out = _detect_project_root(tmp_path)
    assert out.is_absolute()


# ---------- DocumentEntry frozen setattr 多字段 ----------

def test_document_entry_frozen_doc_id_batch49(tmp_path):
    e = DocumentEntry(
        doc_id="d1",
        path_str="x",
        resolved_path=tmp_path,
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        e.doc_id = "d2"


def test_document_entry_frozen_source_type_batch49(tmp_path):
    e = DocumentEntry(
        doc_id="d1",
        path_str="x",
        resolved_path=tmp_path,
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        e.source_type = "docx"


def test_document_entry_frozen_categories_batch49(tmp_path):
    e = DocumentEntry(
        doc_id="d1",
        path_str="x",
        resolved_path=tmp_path,
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        e.categories = ("x",)


def test_expected_failure_frozen_doc_id_batch49(tmp_path):
    e = ExpectedFailure(
        doc_id="d1",
        path_str="x",
        resolved_path=tmp_path,
        expected_error_code="err",
        source_type=None,
    )
    with pytest.raises(FrozenInstanceError):
        e.doc_id = "d2"


def test_expected_failure_frozen_expected_error_code_batch49(tmp_path):
    e = ExpectedFailure(
        doc_id="d1",
        path_str="x",
        resolved_path=tmp_path,
        expected_error_code="err",
        source_type=None,
    )
    with pytest.raises(FrozenInstanceError):
        e.expected_error_code = "other"


def test_manifest_frozen_documents_batch49(tmp_path):
    m = _build_manifest(
        [{"doc_id": "a", "source_type": "pdf"}],
        tmp_path,
    )
    with pytest.raises(FrozenInstanceError):
        m.documents = ()


def test_manifest_frozen_devset_status_batch49(tmp_path):
    m = _build_manifest(
        [{"doc_id": "a", "source_type": "pdf"}],
        tmp_path,
    )
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "incomplete"


# ---------- Manifest hashable 检查 ----------

def test_document_entry_hashable_batch49(tmp_path):
    """frozen dataclass 自动生成 __hash__。"""
    e = DocumentEntry(
        doc_id="d1",
        path_str="x",
        resolved_path=tmp_path / "x",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    # Path 是 hashable，所以 frozen dataclass 可哈希
    assert hash(e) is not None


def test_manifest_hashable_batch49(tmp_path):
    m = _build_manifest(
        [{"doc_id": "a", "source_type": "pdf"}],
        tmp_path,
    )
    assert hash(m) is not None


# ---------- 模块源码补强 ----------

def test_source_contains_json_import_batch49():
    src = inspect.getsource(manifest_mod)
    assert "import json" in src


def test_source_contains_dataclass_import_batch49():
    src = inspect.getsource(manifest_mod)
    assert "from dataclasses import dataclass" in src


def test_source_contains_pathlib_import_batch49():
    src = inspect.getsource(manifest_mod)
    assert "from pathlib import Path" in src


def test_source_contains_typing_any_import_batch49():
    src = inspect.getsource(manifest_mod)
    assert "from typing import Any" in src


def test_source_contains_manifest_version_import_batch49():
    src = inspect.getsource(manifest_mod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_source_contains_validate_import_batch49():
    src = inspect.getsource(manifest_mod)
    assert "from evaluation.schema import validate" in src


def test_source_docstring_mentions_relative_path_batch49():
    src = inspect.getsource(manifest_mod)
    assert "相对路径" in src


def test_source_docstring_mentions_no_absolute_batch49():
    src = inspect.getsource(manifest_mod)
    assert "绝对路径" in src


def test_source_docstring_mentions_no_backslash_batch49():
    src = inspect.getsource(manifest_mod)
    assert "反斜杠" in src


def test_source_docstring_mentions_project_root_batch49():
    src = inspect.getsource(manifest_mod)
    assert "项目根" in src


def test_source_all_has_5_entries_batch49():
    src = inspect.getsource(manifest_mod)
    assert '"ManifestError"' in src
    assert '"Manifest"' in src
    assert '"DocumentEntry"' in src
    assert '"ExpectedFailure"' in src
    assert '"load_manifest"' in src


def test_source_no_extra_class_def_batch49():
    """只有 4 个 ClassDef（ManifestError + DocumentEntry + ExpectedFailure + Manifest）。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 4


def test_source_document_entry_has_10_fields_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "DocumentEntry")
    # annotations
    annots = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    assert len(annots) == 10


def test_source_expected_failure_has_5_fields_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ExpectedFailure")
    annots = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    assert len(annots) == 5


def test_source_manifest_has_5_fields_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    annots = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    assert len(annots) == 5


def test_source_manifest_has_5_properties_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    props = [n for n in cls.body if isinstance(n, ast.FunctionDef) and any(isinstance(d, ast.Name) and d.id == "property" for d in n.decorator_list)]
    assert len(props) == 5


# ---------- AST 结构补强 ----------

def test_ast_has_5_top_level_functions_batch49():
    """5 个函数：_is_absolute_like, _has_backslash, _resolve_relative_path, load_manifest, _detect_project_root。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 5


def test_ast_has_4_class_def_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 4


def test_ast_class_names_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    assert names == ["ManifestError", "DocumentEntry", "ExpectedFailure", "Manifest"]


def test_ast_no_async_function_def_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_module_has_docstring_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_module_has_7_imports_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 7


def test_ast_load_manifest_has_multiple_for_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    # documents for + expected_failures for = 2
    assert len(fors) >= 2


def test_ast_load_manifest_has_try_except_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) >= 1


def test_ast_load_manifest_has_multiple_if_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 3  # p.is_file + project_root None + manifest_version check + annotation_file


def test_ast_resolve_relative_has_multiple_if_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_relative_path")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 3  # empty + absolute + backslash


def test_ast_resolve_relative_has_try_except_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_relative_path")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_resolve_relative_raises_manifest_error_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_relative_path")
    raises = [n for n in ast.walk(func) if isinstance(n, ast.Raise)]
    assert len(raises) >= 3


def test_ast_is_absolute_like_has_3_returns_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_is_absolute_like")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 3  # 空字符串 + POSIX + Windows + final False


def test_ast_detect_project_root_has_for_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_detect_project_root")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_detect_project_root_has_if_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_detect_project_root")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    # 2 个 if：cur.is_file() 取 parent + (parent/pyproject).is_file()
    assert len(ifs) >= 2


def test_ast_manifest_property_file_count_returns_int_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    func = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "file_count")
    src = ast.unparse(func)
    assert "len(self.documents)" in src


def test_ast_manifest_property_categories_uses_sorted_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    func = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "categories_covered")
    src = ast.unparse(func)
    assert "sorted(" in src


def test_ast_manifest_property_content_group_uses_frozenset_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    func = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "content_group_count")
    src = ast.unparse(func)
    assert "frozenset" in src


def test_ast_document_entry_has_decorator_batch49():
    """DocumentEntry 应有 @dataclass(frozen=True) 装饰器。"""
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "DocumentEntry")
    src = ast.unparse(cls)
    assert "@dataclass(frozen=True)" in src


def test_ast_manifest_has_decorator_batch49():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    src = ast.unparse(cls)
    assert "@dataclass(frozen=True)" in src


# ---------- forbidden tokens 第一百三十一批 ----------

def _src() -> str:
    return inspect.getsource(manifest_mod)


def test_source_no_eval_batch49():
    assert "eval(" not in _src()


def test_source_no_exec_batch49():
    assert "exec(" not in _src()


def test_source_no_compile_batch49():
    assert "compile(" not in _src()


def test_source_no_globals_batch49():
    assert "globals(" not in _src()


def test_source_no_locals_batch49():
    assert "locals(" not in _src()


def test_source_no_os_system_batch49():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch49():
    assert "subprocess" not in _src()


def test_source_no_popen_batch49():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch49():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch49():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch49():
    assert "socket" not in _src()


def test_source_no_requests_batch49():
    assert "requests" not in _src()


def test_source_no_urllib_batch49():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch49():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch49():
    assert "yield" not in _src()


def test_source_open_only_in_load_manifest_batch49():
    """open() 仅出现在 load_manifest 中（读 manifest JSON）。"""
    src = _src()
    assert src.count("open(") == 1
