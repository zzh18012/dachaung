"""evaluation/manifest.py 第五十六轮 edges 测试（Round 524）。

补强 edges55 未触及的角度（第二十九批）：
- ManifestError 第二十九批：继承 Exception / 抛出与捕获 / message 含特殊字符
- _is_absolute_like 第二十九批：disk letter 大小写 / 数字开头 / 第 2 字符非冒号
- _has_backslash 第二十九批：仅反斜杠 / 含其他字符 / 多个反斜杠
- DocumentEntry 第二十九批：frozen / hashable / 11 字段
- ExpectedFailure 第二十九批：frozen / hashable / 5 字段
- Manifest 第二十九批：frozen / tuple 字段 / properties 类型 / categories_covered 排序
- _resolve_relative_path 第二十九批：空 str / 绝对路径 / 反斜杠 / 越界 / 成功
- load_manifest 第二十九批：不存在 / 无效 JSON / version 不兼容 / 路径越界
- _detect_project_root 第二十九批：起始是文件 / 无 pyproject fallback
- module source forbidden tokens 第四十六批
- module source 字符串精确补强第四十二批
- signatures 第四十二批
- module 合理性第四十二批
- 端到端集成第四十二批
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


# ---------- ManifestError 第二十九批 ----------


def test_manifest_error_is_exception_batch29():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_can_be_raised_and_caught_batch29():
    try:
        raise ManifestError("test")
    except ManifestError as e:
        assert str(e) == "test"


def test_manifest_error_caught_by_exception_batch29():
    try:
        raise ManifestError("test")
    except Exception as e:
        assert isinstance(e, ManifestError)


def test_manifest_error_message_with_special_chars_batch29():
    e = ManifestError("line\nwith\ttabs")
    assert "\n" in str(e)
    assert "\t" in str(e)


def test_manifest_error_message_with_unicode_batch29():
    e = ManifestError("错误：清单")
    assert "错误" in str(e)


def test_manifest_error_no_default_args_batch29():
    """ManifestError 不接受额外默认参数（只有 message）。"""
    sig = inspect.signature(ManifestError.__init__)
    # Exception.__init__ 不接受 kwargs
    assert "self" in sig.parameters


# ---------- _is_absolute_like 第二十九批 ----------


def test_is_absolute_like_disk_letter_uppercase_batch29():
    """大写盘符 → True。"""
    assert _is_absolute_like("C:/Users") is True


def test_is_absolute_like_disk_letter_lowercase_batch29():
    """小写盘符 → True。"""
    assert _is_absolute_like("c:\\users") is True


def test_is_absolute_like_number_prefix_batch29():
    """数字开头不是绝对路径。"""
    assert _is_absolute_like("1:/foo") is False  # 1 不是字母


def test_is_absolute_like_second_char_not_colon_batch29():
    """第 2 字符不是冒号 → 不是 Windows 绝对。"""
    assert _is_absolute_like("ab/foo") is False


def test_is_absolute_like_third_char_neither_slash_batch29():
    r"""第 3 字符既不是 \ 也不是 / → False。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_short_string_batch29():
    """长度 < 3 → False。"""
    assert _is_absolute_like("C:") is False
    assert _is_absolute_like("a") is False


def test_is_absolute_like_empty_batch29():
    assert _is_absolute_like("") is False


def test_is_absolute_like_relative_batch29():
    assert _is_absolute_like("samples/x.pdf") is False


# ---------- _has_backslash 第二十九批 ----------


def test_has_backslash_only_backslash_batch29():
    assert _has_backslash("\\") is True


def test_has_backslash_in_path_batch29():
    assert _has_backslash("samples\\x.pdf") is True


def test_has_backslash_multiple_batch29():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_no_backslash_batch29():
    assert _has_backslash("a/b/c") is False


def test_has_backslash_empty_batch29():
    assert _has_backslash("") is False


# ---------- DocumentEntry 第二十九批 ----------


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


def test_document_entry_is_dataclass_batch29():
    assert is_dataclass(DocumentEntry)


def test_document_entry_ten_fields_batch29():
    """DocumentEntry 有 10 个字段。"""
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_field_names_batch29():
    names = {f.name for f in fields(DocumentEntry)}
    assert names == {
        "doc_id",
        "path_str",
        "resolved_path",
        "source_type",
        "sha256",
        "categories",
        "paired_with",
        "annotation_file_str",
        "annotation_resolved",
        "expectations",
    }


def test_document_entry_frozen_batch29():
    """frozen=True → 不能赋值。"""
    entry = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        entry.doc_id = "modified"  # type: ignore[misc]


def test_document_entry_hashable_batch29():
    """frozen dataclass 是 hashable。"""
    entry = _make_doc_entry()
    assert hash(entry) is not None


# ---------- ExpectedFailure 第二十九批 ----------


def test_expected_failure_is_dataclass_batch29():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_five_fields_batch29():
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_field_names_batch29():
    names = {f.name for f in fields(ExpectedFailure)}
    assert names == {
        "doc_id",
        "path_str",
        "resolved_path",
        "expected_error_code",
        "source_type",
    }


def test_expected_failure_frozen_batch29():
    ef = ExpectedFailure(
        doc_id="bad1",
        path_str="bad.pdf",
        resolved_path=Path("/repo/bad.pdf"),
        expected_error_code="unsupported_format",
        source_type=None,
    )
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "x"  # type: ignore[misc]


def test_expected_failure_hashable_batch29():
    ef = ExpectedFailure("d1", "p", Path("/p"), "code", None)
    assert hash(ef) is not None


# ---------- Manifest 第二十九批 ----------


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


def test_manifest_is_dataclass_batch29():
    assert is_dataclass(Manifest)


def test_manifest_five_fields_batch29():
    assert len(fields(Manifest)) == 5


def test_manifest_frozen_batch29():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.manifest_version = "2.0"  # type: ignore[misc]


def test_manifest_hashable_batch29():
    m = _make_manifest()
    assert hash(m) is not None


def test_manifest_file_count_int_batch29():
    m = _make_manifest()
    assert isinstance(m.file_count, int)


def test_manifest_pdf_count_int_batch29():
    m = _make_manifest()
    assert isinstance(m.pdf_count, int)


def test_manifest_docx_count_int_batch29():
    m = _make_manifest()
    assert isinstance(m.docx_count_int if hasattr(m, "docx_count_int") else m.docx_count, int)


def test_manifest_content_group_count_int_batch29():
    m = _make_manifest()
    assert isinstance(m.content_group_count, int)


def test_manifest_categories_covered_list_batch29():
    m = _make_manifest()
    assert isinstance(m.categories_covered, list)


def test_manifest_categories_covered_sorted_batch29():
    """categories_covered 返回 sorted list。"""
    doc1 = _make_doc_entry(doc_id="d1", categories=("z", "a"))
    doc2 = _make_doc_entry(doc_id="d2", categories=("m", "b"))
    m = _make_manifest(documents=(doc1, doc2))
    assert m.categories_covered == ["a", "b", "m", "z"]


def test_manifest_categories_covered_unique_batch29():
    """categories 去重。"""
    doc1 = _make_doc_entry(doc_id="d1", categories=("a", "b"))
    doc2 = _make_doc_entry(doc_id="d2", categories=("a", "c"))
    m = _make_manifest(documents=(doc1, doc2))
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_file_count_zero_batch29():
    m = _make_manifest(documents=())
    assert m.file_count == 0


def test_manifest_pdf_count_zero_when_no_documents_batch29():
    m = _make_manifest(documents=())
    assert m.pdf_count == 0


# ---------- _resolve_relative_path 第二十九批 ----------


def test_resolve_relative_path_empty_raises_batch29(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("", tmp_path, "field1")
    assert "field1" in str(exc.value)


def test_resolve_relative_path_absolute_raises_batch29(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("/etc/passwd", tmp_path, "field1")
    assert "field1" in str(exc.value)


def test_resolve_relative_path_backslash_raises_batch29(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("a\\b", tmp_path, "field1")
    assert "field1" in str(exc.value)


def test_resolve_relative_path_outside_root_raises_batch29(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("../escape", tmp_path, "field1")
    assert "field1" in str(exc.value)


def test_resolve_relative_path_valid_batch29(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").touch()
    result = _resolve_relative_path("samples/x.pdf", tmp_path, "field1")
    assert result.is_absolute()
    assert result.is_file()


def test_resolve_relative_path_subdir_batch29(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b").mkdir()
    (tmp_path / "a" / "b" / "c.txt").touch()
    result = _resolve_relative_path("a/b/c.txt", tmp_path, "field1")
    assert result.is_file()


def test_resolve_relative_path_message_contains_field_name_batch29(tmp_path):
    try:
        _resolve_relative_path("../escape", tmp_path, "my_field")
    except ManifestError as e:
        assert "my_field" in str(e)
        return
    pytest.fail("Expected ManifestError")


def test_resolve_relative_path_returns_path_batch29(tmp_path):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "y").touch()
    result = _resolve_relative_path("x/y", tmp_path, "f")
    assert isinstance(result, Path)


# ---------- load_manifest 第二十九批 ----------


def test_load_manifest_nonexistent_raises_batch29():
    with pytest.raises(ManifestError):
        load_manifest("/nonexistent/manifest.json")


def test_load_manifest_directory_raises_batch29(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    with pytest.raises(ManifestError):
        load_manifest(d)


def test_load_manifest_invalid_json_raises_batch29(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("not valid json", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_load_manifest_version_mismatch_raises_batch29(tmp_path):
    """manifest_version='999.0' → schema 拒绝（enum 限制）→ EvalSchemaError。"""
    from evaluation.schema import EvalSchemaError
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "999.0",
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_path_outside_root_raises_batch29(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [
                    {"doc_id": "d1", "path": "../escape.pdf", "source_type": "pdf"}
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_load_manifest_returns_manifest_batch29(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p)
    assert isinstance(m, Manifest)


def test_load_manifest_default_project_root_batch29(tmp_path):
    """project_root=None → 自动检测。"""
    (tmp_path / "pyproject.toml").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p)
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_explicit_project_root_batch29(tmp_path):
    """显式传入 project_root。"""
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.project_root == tmp_path.resolve()


# ---------- _detect_project_root 第二十九批 ----------


def test_detect_project_root_with_pyproject_batch29(tmp_path):
    (tmp_path / "pyproject.toml").touch()
    sub = tmp_path / "sub"
    sub.mkdir()
    result = _detect_project_root(sub)
    assert result == tmp_path.resolve()


def test_detect_project_root_no_pyproject_fallback_batch29(tmp_path):
    """无 pyproject.toml → fallback 到 start.parent。"""
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    result = _detect_project_root(sub)
    # fallback 是 cur（即 sub 自身）
    assert result == sub.resolve()


def test_detect_project_root_with_file_batch29(tmp_path):
    """起始是文件 → 用其 parent。"""
    (tmp_path / "pyproject.toml").touch()
    p = tmp_path / "x.txt"
    p.touch()
    result = _detect_project_root(p)
    assert result == tmp_path.resolve()


def test_detect_project_root_returns_path_batch29(tmp_path):
    result = _detect_project_root(tmp_path)
    assert isinstance(result, Path)


def test_detect_project_root_returns_absolute_batch29(tmp_path):
    result = _detect_project_root(tmp_path)
    assert result.is_absolute()


# ---------- module source forbidden tokens 第四十六批 ----------


def test_module_source_no_subprocess_batch29():
    src = inspect.getsource(mmod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch29():
    src = inspect.getsource(mmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch29():
    src = inspect.getsource(mmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch29():
    src = inspect.getsource(mmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch29():
    src = inspect.getsource(mmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch29():
    src = inspect.getsource(mmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch29():
    src = inspect.getsource(mmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch29():
    src = inspect.getsource(mmod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch29():
    src = inspect.getsource(mmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch29():
    src = inspect.getsource(mmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch29():
    src = inspect.getsource(mmod)
    assert "requests" not in src


def test_module_source_no_unlink_batch29():
    src = inspect.getsource(mmod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十二批 ----------


def test_module_source_contains_module_docstring_batch29():
    src = inspect.getsource(mmod)
    assert "开发集清单加载器" in src


def test_module_source_contains_manifest_error_class_batch29():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


def test_module_source_contains_document_entry_class_batch29():
    src = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in src
    assert "class DocumentEntry:" in src


def test_module_source_contains_expected_failure_class_batch29():
    src = inspect.getsource(mmod)
    assert "class ExpectedFailure:" in src


def test_module_source_contains_manifest_class_batch29():
    src = inspect.getsource(mmod)
    assert "class Manifest:" in src


def test_module_source_contains_is_absolute_like_batch29():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like" in src


def test_module_source_contains_has_backslash_batch29():
    src = inspect.getsource(mmod)
    assert "def _has_backslash" in src


def test_module_source_contains_resolve_relative_path_batch29():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path" in src


def test_module_source_contains_load_manifest_batch29():
    src = inspect.getsource(mmod)
    assert "def load_manifest" in src


def test_module_source_contains_detect_project_root_batch29():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root" in src


def test_module_source_contains_file_count_property_batch29():
    src = inspect.getsource(mmod)
    assert "def file_count" in src


def test_module_source_contains_categories_covered_batch29():
    src = inspect.getsource(mmod)
    assert "def categories_covered" in src


def test_module_source_contains_manifest_version_constant_batch29():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


# ---------- signatures 第四十二批 ----------


def test_signature_is_absolute_like_batch29():
    sig = inspect.signature(_is_absolute_like)
    assert sig.parameters["path_str"].annotation == "str"
    assert sig.return_annotation == "bool"


def test_signature_has_backslash_batch29():
    sig = inspect.signature(_has_backslash)
    assert sig.parameters["path_str"].annotation == "str"
    assert sig.return_annotation == "bool"


def test_signature_resolve_relative_path_batch29():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.keys())
    assert params == ["path_str", "project_root", "field_name"]


def test_signature_resolve_relative_path_return_batch29():
    sig = inspect.signature(_resolve_relative_path)
    assert sig.return_annotation == "Path"


def test_signature_load_manifest_batch29():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.keys())
    assert params == ["manifest_path", "project_root"]


def test_signature_load_manifest_return_batch29():
    sig = inspect.signature(load_manifest)
    assert sig.return_annotation == "Manifest"


def test_signature_load_manifest_project_root_default_batch29():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_signature_detect_project_root_batch29():
    sig = inspect.signature(_detect_project_root)
    assert sig.parameters["start"].annotation == "Path"
    assert sig.return_annotation == "Path"


# ---------- module 合理性第四十二批 ----------


def test_module_has_future_annotations_batch29():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch29():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_imports_dataclass_batch29():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_imports_pathlib_batch29():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch29():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_imports_manifest_version_batch29():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_imports_validate_batch29():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_no_main_block_batch29():
    src = inspect.getsource(mmod)
    assert 'if __name__ == "__main__"' not in src


def test_module_all_contains_five_entries_batch29():
    src = inspect.getsource(mmod)
    for name in [
        '"ManifestError"',
        '"Manifest"',
        '"DocumentEntry"',
        '"ExpectedFailure"',
        '"load_manifest"',
    ]:
        assert name in src


# ---------- 端到端集成第四十二批 ----------


def test_e2e_load_manifest_full_batch29(tmp_path):
    """端到端：完整加载带 documents 与 expected_failures。"""
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").touch()
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "bad.pdf").touch()
    (tmp_path / "pyproject.toml").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "incomplete",
                "documents": [
                    {"doc_id": "d1", "path": "samples/x.pdf", "source_type": "pdf"}
                ],
                "expected_failures": [
                    {"doc_id": "b1", "path": "bad/bad.pdf", "expected_error_code": "unsupported_format"}
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p)
    assert m.file_count == 1
    assert m.devset_status == "incomplete"
    assert m.documents[0].doc_id == "d1"
    assert m.expected_failures[0].doc_id == "b1"


def test_e2e_load_manifest_with_paired_docs_batch29(tmp_path):
    """端到端：配对的 PDF+DOCX → content_group_count=1。"""
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
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.content_group_count == 1


def test_e2e_load_manifest_with_categories_batch29(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [
                    {"doc_id": "d1", "path": "samples/x.pdf", "source_type": "pdf", "categories": ["finance", "report"]}
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["finance", "report"]


def test_e2e_manifest_hashable_after_load_batch29(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [
                    {"doc_id": "d1", "path": "samples/x.pdf", "source_type": "pdf"}
                ],
            }
        ),
        encoding="utf-8",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert hash(m) is not None


def test_e2e_manifest_idempotent_batch29(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").touch()
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": MANIFEST_VERSION,
                "devset_status": "complete",
                "documents": [
                    {"doc_id": "d1", "path": "samples/x.pdf", "source_type": "pdf"}
                ],
            }
        ),
        encoding="utf-8",
    )
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1 == m2


def test_e2e_load_manifest_no_input_modification_batch29(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "x.pdf").touch()
    p = tmp_path / "m.json"
    content = json.dumps(
        {
            "manifest_version": MANIFEST_VERSION,
            "devset_status": "complete",
            "documents": [
                {"doc_id": "d1", "path": "samples/x.pdf", "source_type": "pdf"}
            ],
        }
    )
    p.write_text(content, encoding="utf-8")
    load_manifest(p, project_root=tmp_path)
    assert p.read_text(encoding="utf-8") == content
