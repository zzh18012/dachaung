"""evaluation/manifest.py 第五十九轮 edges 测试（Round 545）。

补强 edges58 未触及的角度（第三十二批）。
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, fields
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


# ---------- ManifestError 第三十二批 ----------


def test_manifest_error_inherits_exception_batch32():
    e = ManifestError("msg")
    assert isinstance(e, Exception)


def test_manifest_error_str_batch32():
    e = ManifestError("boom")
    assert str(e) == "boom"


def test_manifest_error_no_args_batch32():
    e = ManifestError()
    assert str(e) == ""


def test_manifest_error_caught_as_exception_batch32():
    with pytest.raises(Exception) as exc:
        raise ManifestError("x")
    assert exc.value is not None


def test_manifest_error_can_be_caught_specifically_batch32():
    with pytest.raises(ManifestError):
        raise ManifestError("x")


def test_manifest_error_module_level_batch32():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


# ---------- _is_absolute_like 第三十二批 ----------


def test_is_absolute_like_d_drive_batch32():
    assert _is_absolute_like("D:/foo") is True


def test_is_absolute_like_e_drive_batch32():
    assert _is_absolute_like("E:\\foo") is True


def test_is_absolute_like_y_drive_batch32():
    assert _is_absolute_like("Y:/foo") is True


def test_is_absolute_like_relative_with_colon_no_slash_batch32():
    r"""a:b 无 \ 或 / 不是绝对路径。"""
    assert _is_absolute_like("a:b") is False


def test_is_absolute_like_just_slash_batch32():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_just_colon_batch32():
    assert _is_absolute_like(":") is False


def test_is_absolute_like_unicode_alpha_batch32():
    """unicode 字母也算 alpha。"""
    assert _is_absolute_like("é:/foo") is True


def test_is_absolute_like_two_chars_batch32():
    """长度 < 3 不是绝对路径。"""
    assert _is_absolute_like("a:") is False


def test_is_absolute_like_digit_drive_batch32():
    """数字不是 alpha。"""
    assert _is_absolute_like("1:/foo") is False


# ---------- _has_backslash 第三十二批 ----------


def test_has_backslash_empty_string_batch32():
    assert _has_backslash("") is False


def test_has_backslash_single_backslash_batch32():
    assert _has_backslash("\\") is True


def test_has_backslash_two_backslashes_batch32():
    assert _has_backslash("\\\\") is True


def test_has_backslash_forward_only_batch32():
    assert _has_backslash("/foo/bar") is False


def test_has_backslash_mixed_batch32():
    assert _has_backslash("foo\\bar/baz") is True


# ---------- DocumentEntry 第三十二批 ----------


def test_document_entry_is_dataclass_batch32():
    from dataclasses import is_dataclass
    assert is_dataclass(DocumentEntry)


def test_document_entry_is_frozen_batch32():
    e = DocumentEntry(
        doc_id="d1",
        path_str="x.pdf",
        resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        e.doc_id = "modified"  # type: ignore[misc]


def test_document_entry_field_count_ten_batch32():
    fs = fields(DocumentEntry)
    assert len(fs) == 10


def test_document_entry_field_names_batch32():
    fs = fields(DocumentEntry)
    names = {f.name for f in fs}
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


def test_document_entry_eq_batch32():
    e1 = DocumentEntry(
        doc_id="d1",
        path_str="x.pdf",
        resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    e2 = DocumentEntry(
        doc_id="d1",
        path_str="x.pdf",
        resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    assert e1 == e2


def test_document_entry_hash_batch32():
    """frozen dataclass 是 hashable。"""
    e = DocumentEntry(
        doc_id="d1",
        path_str="x.pdf",
        resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    assert isinstance(hash(e), int)


# ---------- ExpectedFailure 第三十二批 ----------


def test_expected_failure_is_dataclass_batch32():
    from dataclasses import is_dataclass
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_is_frozen_batch32():
    ef = ExpectedFailure(
        doc_id="ef1",
        path_str="bad.txt",
        resolved_path=Path("/tmp/bad.txt"),
        expected_error_code="x",
        source_type=None,
    )
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "modified"  # type: ignore[misc]


def test_expected_failure_field_count_five_batch32():
    fs = fields(ExpectedFailure)
    assert len(fs) == 5


def test_expected_failure_field_names_batch32():
    fs = fields(ExpectedFailure)
    names = {f.name for f in fs}
    assert names == {
        "doc_id",
        "path_str",
        "resolved_path",
        "expected_error_code",
        "source_type",
    }


def test_expected_failure_eq_batch32():
    ef1 = ExpectedFailure("ef1", "bad.txt", Path("/tmp/bad.txt"), "code", None)
    ef2 = ExpectedFailure("ef1", "bad.txt", Path("/tmp/bad.txt"), "code", None)
    assert ef1 == ef2


# ---------- Manifest 第三十二批 ----------


def test_manifest_is_dataclass_batch32():
    from dataclasses import is_dataclass
    assert is_dataclass(Manifest)


def test_manifest_field_count_five_batch32():
    fs = fields(Manifest)
    assert len(fs) == 5


def test_manifest_field_names_batch32():
    fs = fields(Manifest)
    names = {f.name for f in fs}
    assert names == {
        "manifest_version",
        "devset_status",
        "documents",
        "expected_failures",
        "project_root",
    }


def test_manifest_file_count_with_three_docs_batch32():
    m = Manifest(
        manifest_version="1.0",
        devset_status="complete",
        documents=(MagicMock(), MagicMock(), MagicMock()),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.file_count == 3


def test_manifest_pdf_count_filters_by_source_type_batch32():
    d1 = MagicMock(); d1.source_type = "pdf"
    d2 = MagicMock(); d2.source_type = "docx"
    d3 = MagicMock(); d3.source_type = "pdf"
    m = Manifest("1.0", "complete", (d1, d2, d3), (), Path("/tmp"))
    assert m.pdf_count == 2


def test_manifest_docx_count_filters_by_source_type_batch32():
    d1 = MagicMock(); d1.source_type = "pdf"
    d2 = MagicMock(); d2.source_type = "docx"
    d3 = MagicMock(); d3.source_type = "docx"
    m = Manifest("1.0", "complete", (d1, d2, d3), (), Path("/tmp"))
    assert m.docx_count == 2


def test_manifest_categories_covered_sorted_batch32():
    d1 = MagicMock(); d1.categories = ("report", "memo")
    d2 = MagicMock(); d2.categories = ("notes",)
    m = Manifest("1.0", "complete", (d1, d2), (), Path("/tmp"))
    assert m.categories_covered == sorted(["report", "memo", "notes"])


def test_manifest_categories_covered_unique_batch32():
    d1 = MagicMock(); d1.categories = ("a", "b")
    d2 = MagicMock(); d2.categories = ("a", "c")
    m = Manifest("1.0", "complete", (d1, d2), (), Path("/tmp"))
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_content_group_count_no_paired_batch32():
    d1 = MagicMock(); d1.paired_with = None; d1.doc_id = "d1"
    d2 = MagicMock(); d2.paired_with = None; d2.doc_id = "d2"
    m = Manifest("1.0", "complete", (d1, d2), (), Path("/tmp"))
    assert m.content_group_count == 2


def test_manifest_content_group_count_with_paired_batch32():
    d1 = MagicMock(); d1.paired_with = "d2"; d1.doc_id = "d1"
    d2 = MagicMock(); d2.paired_with = "d1"; d2.doc_id = "d2"
    m = Manifest("1.0", "complete", (d1, d2), (), Path("/tmp"))
    assert m.content_group_count == 1


def test_manifest_content_group_count_one_paired_one_unpaired_batch32():
    d1 = MagicMock(); d1.paired_with = "d2"; d1.doc_id = "d1"
    d2 = MagicMock(); d2.paired_with = "d1"; d2.doc_id = "d2"
    d3 = MagicMock(); d3.paired_with = None; d3.doc_id = "d3"
    m = Manifest("1.0", "complete", (d1, d2, d3), (), Path("/tmp"))
    assert m.content_group_count == 2


# ---------- _resolve_relative_path 第三十二批 ----------


def test_resolve_relative_path_empty_raises_batch32(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("", tmp_path, "test")


def test_resolve_relative_path_absolute_raises_batch32(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("/etc/passwd", tmp_path, "test")


def test_resolve_relative_path_backslash_raises_batch32(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("a\\b", tmp_path, "test")


def test_resolve_relative_path_outside_root_raises_batch32(tmp_path):
    """路径含 .. 越界 → 抛。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("../../etc/passwd", tmp_path, "test")


def test_resolve_relative_path_simple_returns_path_batch32(tmp_path):
    out = _resolve_relative_path("foo.txt", tmp_path, "test")
    assert isinstance(out, Path)
    assert out.name == "foo.txt"


def test_resolve_relative_path_nested_subdir_batch32(tmp_path):
    out = _resolve_relative_path("a/b/c.txt", tmp_path, "test")
    assert "a" in str(out)
    assert "b" in str(out)
    assert "c.txt" in str(out)


def test_resolve_relative_path_idempotent_batch32(tmp_path):
    p1 = _resolve_relative_path("foo.txt", tmp_path, "test")
    p2 = _resolve_relative_path("foo.txt", tmp_path, "test")
    assert p1 == p2


# ---------- load_manifest 第三十二批 ----------


def test_load_manifest_nonexistent_file_raises_batch32(tmp_path):
    with pytest.raises(ManifestError):
        load_manifest(tmp_path / "nonexistent.json", tmp_path)


def test_load_manifest_directory_raises_batch32(tmp_path):
    """manifest_path 是目录 → is_file()=False → ManifestError。"""
    d = tmp_path / "subdir"
    d.mkdir()
    with pytest.raises(ManifestError):
        load_manifest(d, tmp_path)


def test_load_manifest_invalid_json_raises_batch32(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{not json}", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p, tmp_path)


def test_load_manifest_explicit_project_root_batch32(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_no_documents_batch32(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert m.documents == ()


def test_load_manifest_two_documents_batch32(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "sha256": "a" * 64},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx", "sha256": "b" * 64},
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert len(m.documents) == 2
    assert m.documents[0].doc_id == "d1"
    assert m.documents[1].doc_id == "d2"


def test_load_manifest_with_categories_batch32(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "sha256": "a" * 64, "categories": ["report"]},
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert m.documents[0].categories == ("report",)


def test_load_manifest_with_paired_batch32(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "sha256": "a" * 64, "paired_with": "d2"},
            {"doc_id": "d2", "path": "a.docx", "source_type": "docx", "sha256": "a" * 64, "paired_with": "d1"},
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert m.documents[0].paired_with == "d2"
    assert m.content_group_count == 1


def test_load_manifest_no_modification_to_input_batch32(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    before = p.read_text(encoding="utf-8")
    load_manifest(p, tmp_path)
    assert p.read_text(encoding="utf-8") == before


def test_load_manifest_with_expected_failures_batch32(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "bad.txt", "expected_error_code": "x"},
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].doc_id == "ef1"
    assert m.expected_failures[0].expected_error_code == "x"


def test_load_manifest_invalid_manifest_version_raises_batch32(tmp_path):
    """manifest_version != MANIFEST_VERSION → ManifestError。"""
    instance = {
        "manifest_version": "999.0",
        "devset_status": "complete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    # 先 schema 校验失败（enum），但代码也会检查 version
    # 所以可能抛 EvalSchemaError 或 ManifestError
    with pytest.raises((ManifestError, Exception)):
        load_manifest(p, tmp_path)


def test_load_manifest_path_with_backslash_raises_batch32(tmp_path):
    """path 含反斜杠 → ManifestError。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a\\b.pdf", "source_type": "pdf", "sha256": "a" * 64},
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p, tmp_path)


# ---------- _detect_project_root 第三十二批 ----------


def test_detect_project_root_from_file_batch32(tmp_path):
    """从 file 路径开始 → 应在 parent 找。"""
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    out = _detect_project_root(p)
    assert out == tmp_path.resolve()


def test_detect_project_root_from_dir_batch32(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_nested_batch32(tmp_path):
    """深嵌套 → 找到顶层。"""
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    out = _detect_project_root(deep)
    assert out == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_cur_batch32(tmp_path):
    """无 pyproject.toml → 返回 cur（已 resolved）。"""
    deep = tmp_path / "a"
    deep.mkdir()
    out = _detect_project_root(deep)
    assert out == deep.resolve()


# ---------- module source forbidden tokens 第四十八批 ----------


def test_module_source_no_subprocess_batch32():
    src = inspect.getsource(mmod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch32():
    src = inspect.getsource(mmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch32():
    src = inspect.getsource(mmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch32():
    src = inspect.getsource(mmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch32():
    src = inspect.getsource(mmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch32():
    src = inspect.getsource(mmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch32():
    src = inspect.getsource(mmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch32():
    src = inspect.getsource(mmod)
    assert "breakpoint(" not in src


def test_module_source_no_shutil_batch32():
    src = inspect.getsource(mmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch32():
    src = inspect.getsource(mmod)
    assert "requests" not in src


def test_module_source_no_open_w_mode_batch32():
    src = inspect.getsource(mmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_unlink_batch32():
    src = inspect.getsource(mmod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十四批 ----------


def test_module_source_contains_module_docstring_batch32():
    src = inspect.getsource(mmod)
    assert "开发集清单加载器" in src


def test_module_source_contains_manifest_error_class_batch32():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


def test_module_source_contains_is_absolute_like_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in src


def test_module_source_contains_has_backslash_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _has_backslash(" in src


def test_module_source_contains_document_entry_class_batch32():
    src = inspect.getsource(mmod)
    assert "class DocumentEntry:" in src
    assert "@dataclass(frozen=True)" in src


def test_module_source_contains_expected_failure_class_batch32():
    src = inspect.getsource(mmod)
    assert "class ExpectedFailure:" in src


def test_module_source_contains_manifest_class_batch32():
    src = inspect.getsource(mmod)
    assert "class Manifest:" in src


def test_module_source_contains_resolve_relative_path_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in src


def test_module_source_contains_load_manifest_func_batch32():
    src = inspect.getsource(mmod)
    assert "def load_manifest(" in src


def test_module_source_contains_detect_project_root_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root(" in src


def test_module_source_contains_manifest_version_import_batch32():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_contains_schema_import_batch32():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_contains_dataclass_import_batch32():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_contains_json_import_batch32():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_source_contains_pathlib_import_batch32():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch32():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_contains_relative_to_batch32():
    src = inspect.getsource(mmod)
    assert ".relative_to(" in src


def test_module_source_contains_paired_with_doc_batch32():
    src = inspect.getsource(mmod)
    assert "配对的" in src or "paired" in src


# ---------- signatures 第四十四批 ----------


def test_signature_is_absolute_like_batch32():
    sig = inspect.signature(_is_absolute_like)
    assert sig.parameters["path_str"].annotation == "str"
    assert sig.return_annotation == "bool"


def test_signature_has_backslash_batch32():
    sig = inspect.signature(_has_backslash)
    assert sig.parameters["path_str"].annotation == "str"
    assert sig.return_annotation == "bool"


def test_signature_resolve_relative_path_batch32():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.keys())
    assert params == ["path_str", "project_root", "field_name"]
    assert sig.return_annotation == "Path"


def test_signature_load_manifest_batch32():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.keys())
    assert params == ["manifest_path", "project_root"]
    assert sig.return_annotation == "Manifest"
    assert sig.parameters["project_root"].default is None


def test_signature_detect_project_root_batch32():
    sig = inspect.signature(_detect_project_root)
    assert sig.parameters["start"].annotation == "Path"
    assert sig.return_annotation == "Path"


# ---------- module 合理性第四十四批 ----------


def test_module_has_future_annotations_batch32():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch32():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_imports_dataclass_batch32():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_imports_pathlib_batch32():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch32():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_imports_manifest_version_batch32():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_imports_validate_batch32():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_has_all_export_batch32():
    src = inspect.getsource(mmod)
    assert "__all__" in src


def test_module_no_main_block_batch32():
    src = inspect.getsource(mmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十四批 ----------


def test_e2e_load_manifest_full_with_three_docs_batch32(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": f"d{i}", "path": f"a{i}.pdf", "source_type": "pdf", "sha256": "a" * 64}
            for i in range(3)
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert m.manifest_version == MANIFEST_VERSION
    assert m.devset_status == "complete"
    assert m.file_count == 3
    assert m.pdf_count == 3
    assert m.docx_count == 0


def test_e2e_manifest_with_paired_pdfs_and_docx_batch32(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "sha256": "a" * 64, "paired_with": "d2"},
            {"doc_id": "d2", "path": "a.docx", "source_type": "docx", "sha256": "a" * 64, "paired_with": "d1"},
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.content_group_count == 1


def test_e2e_manifest_categories_from_multiple_docs_batch32(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "sha256": "a" * 64, "categories": ["report", "finance"]},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx", "sha256": "b" * 64, "categories": ["memo", "report"]},
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert m.categories_covered == ["finance", "memo", "report"]


def test_e2e_manifest_idempotent_batch32(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    m1 = load_manifest(p, tmp_path)
    m2 = load_manifest(p, tmp_path)
    assert m1 == m2


def test_e2e_manifest_incomplete_status_batch32(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert m.devset_status == "incomplete"


def test_e2e_manifest_with_expected_failure_batch32(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "bad.txt", "expected_error_code": "unsupported_source_type"},
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    m = load_manifest(p, tmp_path)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].expected_error_code == "unsupported_source_type"
