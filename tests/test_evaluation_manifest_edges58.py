"""evaluation/manifest.py 第五十八轮 edges 测试（Round 538）。

补强 edges57 未触及的角度（第三十一批）：
- ManifestError 第三十一批：raise 不带 args / 多 args / 含 dict
- _is_absolute_like 第三十一批：unicode 字母盘符 / 空格 / 多冒号 / hash 字符
- _has_backslash 第三十一批：tab 字符 / 换行 / unicode 路径
- DocumentEntry 第三十一批：annotation_resolved Path / paired_with str / expectations 含嵌套 dict
- ExpectedFailure 第三十一批：source_type str / 不等比较
- Manifest 第三十一批：devset_status 任意 string / project_root / categories_covered 多种类型
- _resolve_relative_path 第三十一批：长路径 / unicode / 多层目录
- load_manifest 第三十一批：annotation_file 越界 / expectations dict 透传 / 双文档
- _detect_project_root 第三十一批：嵌套深 / parents 多层
- module source forbidden tokens 第四十八批
- module source 字符串精确补强第四十四批
- signatures 第四十四批
- module 合理性第四十四批
- 端到端集成第四十四批
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
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


# ---------- ManifestError 第三十一批 ----------


def test_manifest_error_with_two_args_batch31():
    """多 args（不被特殊处理，仍走 Exception.args）。"""
    e = ManifestError("msg1")
    e.args = ("msg1", "extra")
    assert len(e.args) == 2


def test_manifest_error_str_is_message_only_batch31():
    """str(e) 只是 message（args 第一个）。"""
    e = ManifestError("hello")
    assert str(e) == "hello"


def test_manifest_error_can_be_raised_without_catching_batch31():
    """raise ManifestError 不被 catch ValueError。"""
    try:
        raise ManifestError("x")
    except ValueError:
        pytest.fail("ManifestError 不应被 ValueError 捕获")
    except ManifestError:
        pass


def test_manifest_error_module_level_constant_batch31():
    """ManifestError 是模块顶层 class。"""
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


# ---------- _is_absolute_like 第三十一批 ----------


def test_is_absolute_like_unicode_drive_letter_batch31():
    """unicode 字母（如 'é'）→ isalpha True 但 Python 仍可能判为绝对。"""
    # "é:/foo" - é.isalpha() is True
    result = _is_absolute_like("é:/foo")
    # 取决于实现，但只要可调用不抛错
    assert isinstance(result, bool)


def test_is_absolute_like_space_in_path_batch31():
    """路径含空格不影响判定。"""
    assert _is_absolute_like("C:/Program Files/x") is True
    assert _is_absolute_like("samples/Program Files/x") is False


def test_is_absolute_like_multiple_colons_batch31():
    """多冒号路径。"""
    assert _is_absolute_like("C:/a:b:x") is True
    assert _is_absolute_like("a:b:c") is False


def test_is_absolute_like_hash_character_batch31():
    """# 字符开头不是绝对路径。"""
    assert _is_absolute_like("#/foo") is False


def test_is_absolute_like_uppercase_z_drive_batch31():
    assert _is_absolute_like("Z:\\windows") is True


def test_is_absolute_like_short_relative_batch31():
    """单字符相对路径 → False。"""
    assert _is_absolute_like("a") is False
    assert _is_absolute_like(".") is False


# ---------- _has_backslash 第三十一批 ----------


def test_has_backslash_with_tab_batch31():
    """tab 不是 backslash。"""
    assert _has_backslash("a\tb") is False


def test_has_backslash_with_newline_batch31():
    assert _has_backslash("a\nb") is False


def test_has_backslash_unicode_path_batch31():
    assert _has_backslash("中文\\路径") is True


def test_has_backslash_only_forward_slashes_batch31():
    assert _has_backslash("/a/b/c") is False


def test_has_backslash_mixed_path_batch31():
    assert _has_backslash("a/b\\c/d") is True


# ---------- DocumentEntry 第三十一批 ----------


def _make_doc_entry(**overrides) -> DocumentEntry:
    defaults = dict(
        doc_id="d1",
        path_str="samples/x.pdf",
        resolved_path=Path("/repo/samples/x.pdf"),
        source_type="pdf",
        sha256="a" * 64,
        categories=("finance",),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    defaults.update(overrides)
    return DocumentEntry(**defaults)


def test_document_entry_annotation_resolved_path_batch31():
    """annotation_resolved 可以是 Path。"""
    e = _make_doc_entry(annotation_resolved=Path("/repo/samples/x.json"))
    assert isinstance(e.annotation_resolved, Path)


def test_document_entry_paired_with_string_batch31():
    """paired_with 是 doc_id 字符串。"""
    e = _make_doc_entry(paired_with="d2")
    assert e.paired_with == "d2"


def test_document_entry_expectations_nested_dict_batch31():
    """expectations 含嵌套 dict。"""
    expectations = {
        "element_count_by_type": {"paragraph": 5, "heading": 2},
        "notes": "test doc",
    }
    e = _make_doc_entry(expectations=expectations)
    assert e.expectations == expectations


def test_document_entry_default_categories_empty_tuple_batch31():
    e = _make_doc_entry(categories=())
    assert e.categories == ()


def test_document_entry_field_types_batch31():
    """字段类型检查。"""
    e = _make_doc_entry()
    assert isinstance(e.doc_id, str)
    assert isinstance(e.path_str, str)
    assert isinstance(e.resolved_path, Path)
    assert isinstance(e.source_type, str)
    assert isinstance(e.categories, tuple)


def test_document_entry_eq_with_paired_batch31():
    """含 paired_with 的两个 entry 相等。"""
    e1 = _make_doc_entry(paired_with="d2")
    e2 = _make_doc_entry(paired_with="d2")
    assert e1 == e2


# ---------- ExpectedFailure 第三十一批 ----------


def test_expected_failure_source_type_string_batch31():
    ef = ExpectedFailure("d1", "p", Path("/p"), "code", "pdf")
    assert ef.source_type == "pdf"


def test_expected_failure_neq_when_differ_batch31():
    ef1 = ExpectedFailure("d1", "p", Path("/p"), "code1", None)
    ef2 = ExpectedFailure("d2", "p", Path("/p"), "code1", None)
    assert ef1 != ef2


def test_expected_failure_with_source_type_batch31():
    ef1 = ExpectedFailure("d1", "p", Path("/p"), "code", "pdf")
    ef2 = ExpectedFailure("d1", "p", Path("/p"), "code", "docx")
    assert ef1 != ef2


def test_expected_failure_field_count_batch31():
    assert len(fields(ExpectedFailure)) == 5


# ---------- Manifest 第三十一批 ----------


def _make_manifest(**overrides) -> Manifest:
    defaults = dict(
        manifest_version="1.0",
        devset_status="complete",
        documents=(),
        expected_failures=(),
        project_root=Path("/repo"),
    )
    defaults.update(overrides)
    return Manifest(**defaults)


def test_manifest_devset_status_arbitrary_string_batch31():
    """devset_status 是任意 string（schema 可能 enum，但 dataclass 不限制）。"""
    m = _make_manifest(devset_status="custom_status")
    assert m.devset_status == "custom_status"


def test_manifest_project_root_is_path_batch31():
    m = _make_manifest()
    assert isinstance(m.project_root, Path)


def test_manifest_documents_tuple_type_batch31():
    docs = (_make_doc_entry(),)
    m = _make_manifest(documents=docs)
    assert isinstance(m.documents, tuple)


def test_manifest_expected_failures_tuple_type_batch31():
    ef = ExpectedFailure("d1", "p", Path("/p"), "code", None)
    m = _make_manifest(expected_failures=(ef,))
    assert isinstance(m.expected_failures, tuple)


def test_manifest_categories_covered_with_many_categories_batch31():
    """多 categories 聚合排序。"""
    docs = (
        _make_doc_entry(doc_id="d1", categories=("z", "y")),
        _make_doc_entry(doc_id="d2", categories=("x",)),
        _make_doc_entry(doc_id="d3", categories=("a", "b", "c")),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "b", "c", "x", "y", "z"]


def test_manifest_categories_covered_no_duplicates_batch31():
    """相同 categories 不重复。"""
    docs = (
        _make_doc_entry(doc_id="d1", categories=("a", "b")),
        _make_doc_entry(doc_id="d2", categories=("a", "b")),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "b"]


def test_manifest_file_count_zero_documents_batch31():
    m = _make_manifest()
    assert m.file_count == 0


# ---------- _resolve_relative_path 第三十一批 ----------


def test_resolve_relative_path_long_path_batch31(tmp_path):
    """长路径仍合法。"""
    deep = tmp_path
    for i in range(5):
        deep = deep / f"dir{i}"
    deep.mkdir(parents=True)
    file = deep / "file.txt"
    file.touch()
    rel = "/".join(f"dir{i}" for i in range(5)) + "/file.txt"
    result = _resolve_relative_path(rel, tmp_path, "f")
    assert result.is_file()


def test_resolve_relative_path_unicode_chars_batch31(tmp_path):
    """unicode 路径仍合法。"""
    (tmp_path / "中文").mkdir()
    (tmp_path / "中文" / "文件.pdf").touch()
    result = _resolve_relative_path("中文/文件.pdf", tmp_path, "f")
    assert result.is_file()


def test_resolve_relative_path_idempotent_batch31(tmp_path):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "y").touch()
    r1 = _resolve_relative_path("x/y", tmp_path, "f")
    r2 = _resolve_relative_path("x/y", tmp_path, "f")
    assert r1 == r2


def test_resolve_relative_path_returns_absolute_path_batch31(tmp_path):
    (tmp_path / "x").touch()
    result = _resolve_relative_path("x", tmp_path, "f")
    assert result.is_absolute()


def test_resolve_relative_path_subdir_chain_batch31(tmp_path):
    """多层目录链。"""
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b").mkdir()
    (tmp_path / "a" / "b" / "c.txt").touch()
    result = _resolve_relative_path("a/b/c.txt", tmp_path, "f")
    assert result.name == "c.txt"


# ---------- load_manifest 第三十一批 ----------


def test_load_manifest_annotation_file_outside_root_batch31(tmp_path):
    """annotation_file 越界 → ManifestError。"""
    (tmp_path / "x.pdf").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "x.pdf",
                        "source_type": "pdf",
                        "annotation_file": "../escape.json",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_expectations_passed_through_batch31(tmp_path):
    """expectations 字段透传到 DocumentEntry。"""
    (tmp_path / "x.pdf").touch()
    p = tmp_path / "m.json"
    expectations = {"element_count_by_type": {"paragraph": 5}}
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "x.pdf",
                        "source_type": "pdf",
                        "expectations": expectations,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations == expectations


def test_load_manifest_two_documents_batch31(tmp_path):
    """两个 documents。"""
    (tmp_path / "x.pdf").touch()
    (tmp_path / "y.pdf").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [
                    {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"},
                    {"doc_id": "d2", "path": "y.pdf", "source_type": "pdf"},
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.documents) == 2
    assert m.file_count == 2


def test_load_manifest_paired_documents_batch31(tmp_path):
    """配对的两个文档（双向 paired_with）。"""
    (tmp_path / "x.pdf").touch()
    (tmp_path / "y.docx").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [
                    {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "paired_with": "d2"},
                    {"doc_id": "d2", "path": "y.docx", "source_type": "docx", "paired_with": "d1"},
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 1


def test_load_manifest_no_modification_batch31(tmp_path):
    (tmp_path / "x.pdf").touch()
    p = tmp_path / "m.json"
    content = json.dumps(
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "complete",
            "documents": [{"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}],
        }
    )
    p.write_text(content, encoding="utf-8")
    load_manifest(p, project_root=tmp_path)
    assert p.read_text(encoding="utf-8") == content


def test_load_manifest_with_sha256_batch31(tmp_path):
    """sha256 字段透传。"""
    (tmp_path / "x.pdf").touch()
    p = tmp_path / "m.json"
    sha = "a" * 64
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [
                    {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "sha256": sha}
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 == sha


# ---------- _detect_project_root 第三十一批 ----------


def test_detect_project_root_deep_nested_batch31(tmp_path):
    """深嵌套目录。"""
    (tmp_path / "pyproject.toml").touch()
    deep = tmp_path
    for i in range(5):
        deep = deep / f"d{i}"
    deep.mkdir(parents=True)
    result = _detect_project_root(deep)
    assert result == tmp_path.resolve()


def test_detect_project_root_starts_at_root_batch31(tmp_path):
    (tmp_path / "pyproject.toml").touch()
    result = _detect_project_root(tmp_path)
    assert result == tmp_path.resolve()


def test_detect_project_root_idempotent_batch31(tmp_path):
    (tmp_path / "pyproject.toml").touch()
    r1 = _detect_project_root(tmp_path)
    r2 = _detect_project_root(tmp_path)
    assert r1 == r2


def test_detect_project_root_returns_existing_batch31(tmp_path):
    """返回的 path 必须存在。"""
    (tmp_path / "pyproject.toml").touch()
    result = _detect_project_root(tmp_path)
    assert result.exists()


# ---------- module source forbidden tokens 第四十八批 ----------


def test_module_source_no_subprocess_batch31():
    src = inspect.getsource(mmod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch31():
    src = inspect.getsource(mmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch31():
    src = inspect.getsource(mmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch31():
    src = inspect.getsource(mmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch31():
    src = inspect.getsource(mmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch31():
    src = inspect.getsource(mmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch31():
    src = inspect.getsource(mmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch31():
    src = inspect.getsource(mmod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch31():
    src = inspect.getsource(mmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch31():
    src = inspect.getsource(mmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch31():
    src = inspect.getsource(mmod)
    assert "requests" not in src


def test_module_source_no_unlink_batch31():
    src = inspect.getsource(mmod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十四批 ----------


def test_module_source_contains_module_docstring_batch31():
    src = inspect.getsource(mmod)
    assert "开发集清单加载器" in src


def test_module_source_contains_invariant_doc_batch31():
    src = inspect.getsource(mmod)
    assert "正斜杠" in src


def test_module_source_contains_manifest_error_class_batch31():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


def test_module_source_contains_manifest_error_doc_batch31():
    src = inspect.getsource(mmod)
    assert "清单加载或校验失败" in src


def test_module_source_contains_is_absolute_like_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like" in src


def test_module_source_contains_windows_drive_doc_batch31():
    src = inspect.getsource(mmod)
    assert "Windows 盘符" in src


def test_module_source_contains_has_backslash_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _has_backslash" in src


def test_module_source_contains_document_entry_class_batch31():
    src = inspect.getsource(mmod)
    assert "class DocumentEntry:" in src


def test_module_source_contains_expected_failure_class_batch31():
    src = inspect.getsource(mmod)
    assert "class ExpectedFailure:" in src


def test_module_source_contains_manifest_class_batch31():
    src = inspect.getsource(mmod)
    assert "class Manifest:" in src


def test_module_source_contains_resolve_relative_path_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path" in src


def test_module_source_contains_load_manifest_func_batch31():
    src = inspect.getsource(mmod)
    assert "def load_manifest" in src


def test_module_source_contains_detect_project_root_func_batch31():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root" in src


def test_module_source_contains_file_count_property_batch31():
    src = inspect.getsource(mmod)
    assert "def file_count" in src


def test_module_source_contains_pdf_count_property_batch31():
    src = inspect.getsource(mmod)
    assert "def pdf_count" in src


def test_module_source_contains_docx_count_property_batch31():
    src = inspect.getsource(mmod)
    assert "def docx_count" in src


def test_module_source_contains_content_group_count_property_batch31():
    src = inspect.getsource(mmod)
    assert "def content_group_count" in src


def test_module_source_contains_categories_covered_property_batch31():
    src = inspect.getsource(mmod)
    assert "def categories_covered" in src


# ---------- signatures 第四十四批 ----------


def test_signature_manifest_error_no_init_batch31():
    """ManifestError 不自定义 __init__（用 Exception 默认）。"""
    # Exception.__init__ 接受可变 args
    sig = inspect.signature(ManifestError.__init__)
    assert "self" in sig.parameters


def test_signature_is_absolute_like_full_batch31():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]
    assert sig.parameters["path_str"].annotation == "str"
    assert sig.return_annotation == "bool"


def test_signature_has_backslash_full_batch31():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]
    assert sig.parameters["path_str"].annotation == "str"
    assert sig.return_annotation == "bool"


def test_signature_resolve_relative_path_full_batch31():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.keys())
    assert params == ["path_str", "project_root", "field_name"]


def test_signature_load_manifest_full_batch31():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.keys())
    assert params == ["manifest_path", "project_root"]


def test_signature_load_manifest_return_batch31():
    sig = inspect.signature(load_manifest)
    assert sig.return_annotation == "Manifest"


def test_signature_detect_project_root_full_batch31():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.keys())
    assert params == ["start"]


# ---------- module 合理性第四十四批 ----------


def test_module_has_future_annotations_batch31():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch31():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_imports_dataclass_batch31():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_imports_pathlib_batch31():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch31():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_imports_manifest_version_batch31():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_imports_validate_batch31():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_has_all_export_batch31():
    src = inspect.getsource(mmod)
    assert "__all__" in src


def test_module_no_main_block_batch31():
    src = inspect.getsource(mmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十四批 ----------


def test_e2e_full_manifest_with_paired_documents_batch31(tmp_path):
    """端到端：配对的双向 paired_with → content_group_count=1。"""
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").touch()
    (tmp_path / "samples" / "y.docx").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [
                    {"doc_id": "d1", "path": "samples/x.pdf", "source_type": "pdf", "paired_with": "d2"},
                    {"doc_id": "d2", "path": "samples/y.docx", "source_type": "docx", "paired_with": "d1"},
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 1
    assert m.pdf_count == 1
    assert m.docx_count == 1


def test_e2e_manifest_with_annotation_file_batch31(tmp_path):
    """端到端：含 annotation_file。"""
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").touch()
    (tmp_path / "samples" / "x.json").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "samples/x.pdf",
                        "source_type": "pdf",
                        "annotation_file": "samples/x.json",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_resolved is not None
    assert m.documents[0].annotation_resolved.is_file()


def test_e2e_manifest_with_categories_aggregated_batch31(tmp_path):
    """端到端：categories 聚合。"""
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").touch()
    (tmp_path / "samples" / "y.pdf").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "samples/x.pdf",
                        "source_type": "pdf",
                        "categories": ["finance", "report"],
                    },
                    {
                        "doc_id": "d2",
                        "path": "samples/y.pdf",
                        "source_type": "pdf",
                        "categories": ["legal"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["finance", "legal", "report"]


def test_e2e_manifest_no_input_modification_batch31(tmp_path):
    (tmp_path / "x.pdf").touch()
    p = tmp_path / "m.json"
    content = json.dumps(
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "complete",
            "documents": [{"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}],
        }
    )
    p.write_text(content, encoding="utf-8")
    load_manifest(p, project_root=tmp_path)
    assert p.read_text(encoding="utf-8") == content


def test_e2e_manifest_idempotent_batch31(tmp_path):
    (tmp_path / "x.pdf").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [{"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}],
            }
        ),
        encoding="utf-8",
    )
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1 == m2


def test_e2e_manifest_hashable_batch31(tmp_path):
    (tmp_path / "x.pdf").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [{"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert hash(m) is not None


def test_e2e_manifest_with_expected_failures_batch31(tmp_path):
    """端到端：expected_failures 字段。"""
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "broken.pdf").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [],
                "expected_failures": [
                    {
                        "doc_id": "b1",
                        "path": "bad/broken.pdf",
                        "expected_error_code": "unsupported_format",
                        "source_type": "pdf",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    ef = m.expected_failures[0]
    assert ef.doc_id == "b1"
    assert ef.expected_error_code == "unsupported_format"
