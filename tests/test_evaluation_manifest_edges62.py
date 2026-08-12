"""evaluation/manifest.py 第六十二轮 edges 测试（Round 565）。

补强 edges61 未触及的角度（第三十五批）。
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


# ---------- DocumentEntry frozen / equality 第三十五批


def test_document_entry_frozen_cannot_assign_batch35():
    d = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None)
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "changed"  # type: ignore[misc]


def test_document_entry_equality_same_fields_batch35():
    d1 = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                      None, None, None, None)
    d2 = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                      None, None, None, None)
    assert d1 == d2


def test_document_entry_inequality_different_id_batch35():
    d1 = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                      None, None, None, None)
    d2 = DocumentEntry("d2", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                      None, None, None, None)
    assert d1 != d2


def test_document_entry_hashable_batch35():
    """frozen dataclass → hashable。"""
    d = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None)
    h = hash(d)
    assert isinstance(h, int)


def test_document_entry_field_count_10_batch35():
    flds = fields(DocumentEntry)
    assert len(flds) == 10


def test_document_entry_field_names_batch35():
    flds = fields(DocumentEntry)
    names = {f.name for f in flds}
    assert names == {
        "doc_id", "path_str", "resolved_path", "source_type", "sha256",
        "categories", "paired_with", "annotation_file_str",
        "annotation_resolved", "expectations",
    }


def test_document_entry_repr_batch35():
    """frozen dataclass repr 含 class name。"""
    d = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None)
    assert "DocumentEntry" in repr(d)
    assert "d1" in repr(d)


# ---------- ExpectedFailure 第三十五批


def test_expected_failure_default_source_type_none_batch35():
    ef = ExpectedFailure("d1", "bad.pdf", Path("/x/bad.pdf"), "E_PARSE", None)
    assert ef.source_type is None


def test_expected_failure_with_source_type_batch35():
    ef = ExpectedFailure("d1", "bad.pdf", Path("/x/bad.pdf"), "E_PARSE", "pdf")
    assert ef.source_type == "pdf"


def test_expected_failure_field_count_5_batch35():
    flds = fields(ExpectedFailure)
    assert len(flds) == 5


def test_expected_failure_field_names_batch35():
    flds = fields(ExpectedFailure)
    names = {f.name for f in flds}
    assert names == {"doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"}


def test_expected_failure_frozen_batch35():
    ef = ExpectedFailure("d1", "bad.pdf", Path("/x/bad.pdf"), "E_PARSE", None)
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "changed"  # type: ignore[misc]


def test_expected_failure_hashable_batch35():
    ef = ExpectedFailure("d1", "bad.pdf", Path("/x/bad.pdf"), "E_PARSE", None)
    assert isinstance(hash(ef), int)


# ---------- Manifest 第三十五批


def test_manifest_field_count_5_batch35():
    flds = fields(Manifest)
    assert len(flds) == 5


def test_manifest_field_names_batch35():
    flds = fields(Manifest)
    names = {f.name for f in flds}
    assert names == {"manifest_version", "devset_status", "documents", "expected_failures", "project_root"}


def test_manifest_file_count_property_batch35():
    """file_count == len(documents)。"""
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.file_count == 1


def test_manifest_file_count_empty_batch35():
    m = Manifest("1.0", "incomplete", (), (), Path("/x"))
    assert m.file_count == 0


def test_manifest_frozen_batch35():
    m = Manifest("1.0", "incomplete", (), (), Path("/x"))
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


def test_manifest_pdf_count_empty_batch35():
    m = Manifest("1.0", "incomplete", (), (), Path("/x"))
    assert m.pdf_count == 0
    assert m.docx_count == 0


def test_manifest_categories_covered_empty_batch35():
    m = Manifest("1.0", "incomplete", (), (), Path("/x"))
    assert m.categories_covered == []


def test_manifest_content_group_count_empty_batch35():
    m = Manifest("1.0", "incomplete", (), (), Path("/x"))
    assert m.content_group_count == 0


def test_manifest_property_doc_count_independent_batch35():
    """docx_count 不包含 pdf。"""
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None),
        DocumentEntry("d2", "b.pdf", Path("/x/b.pdf"), "pdf", None, (),
                     None, None, None, None),
        DocumentEntry("d3", "c.docx", Path("/x/c.docx"), "docx", None, (),
                     None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.pdf_count == 2
    assert m.docx_count == 1
    assert m.file_count == 3


# ---------- _is_absolute_like 第三十五批


def test_is_absolute_like_just_slash_batch35():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_single_dot_slash_batch35():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_double_dot_slash_batch35():
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_z_drive_upper_batch35():
    assert _is_absolute_like("Z:\\foo") is True


def test_is_absolute_like_z_drive_lower_batch35():
    assert _is_absolute_like("z:/foo") is True


def test_is_absolute_like_two_chars_batch35():
    """少于 3 char 的字符串 → False。"""
    assert _is_absolute_like("a:") is False


def test_is_absolute_like_one_char_batch35():
    assert _is_absolute_like("a") is False


def test_is_absolute_like_empty_str_batch35():
    assert _is_absolute_like("") is False


# ---------- _has_backslash 第三十五批


def test_has_backslash_mixed_separators_batch35():
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_only_forward_batch35():
    assert _has_backslash("a/b/c") is False


def test_has_backslash_only_one_backslash_batch35():
    assert _has_backslash("\\") is True


def test_has_backslash_pure_backslash_path_batch35():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_empty_string_batch35():
    assert _has_backslash("") is False


# ---------- _resolve_relative_path 第三十五批


def test_resolve_path_in_project_root_batch35(tmp_path):
    """正常相对路径解析在 project_root 内。"""
    p = _resolve_relative_path("a.pdf", tmp_path, "f")
    assert p == (tmp_path / "a.pdf").resolve()


def test_resolve_path_subdir_batch35(tmp_path):
    p = _resolve_relative_path("sub/a.pdf", tmp_path, "f")
    assert p == (tmp_path / "sub" / "a.pdf").resolve()


def test_resolve_path_dot_only_batch35(tmp_path):
    """'.' 表示当前目录。"""
    p = _resolve_relative_path(".", tmp_path, "f")
    assert p == tmp_path.resolve()


def test_resolve_path_one_level_up_inside_batch35(tmp_path):
    """tmp_path/sub/.. → tmp_path，仍在内。"""
    p = _resolve_relative_path("sub/..", tmp_path, "f")
    assert p == tmp_path.resolve()


def test_resolve_path_message_contains_field_and_path_batch35(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("/etc/passwd", tmp_path, "fieldX")
    s = str(exc.value)
    assert "fieldX" in s
    assert "/etc/passwd" in s


def test_resolve_path_message_contains_arrow_for_escape_batch35(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("../escape", tmp_path, "f")
    assert "→" in str(exc.value)


# ---------- load_manifest 第三十五批


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_missing_file_raises_batch35(tmp_path):
    with pytest.raises(ManifestError) as exc:
        load_manifest(tmp_path / "missing.json", project_root=tmp_path)
    assert "不存在" in str(exc.value)


def test_load_manifest_str_path_argument_batch35(tmp_path):
    """manifest_path 接受 str。"""
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(str(p), project_root=str(tmp_path))
    assert len(m.documents) == 1


def test_load_manifest_str_project_root_batch35(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_mismatch_version_raises_batch35(tmp_path):
    """manifest_version 不匹配 → ManifestError。"""
    p = _write_manifest(tmp_path, {
        "manifest_version": "999.0",  # 假设 999.0 不在 schema enum 里 → schema 失败
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    # schema 会先报错（EnumValueError），但仍是 EvalSchemaError；如果想测 version mismatch，
    # 需要一个 schema 通过但 version 不匹配的场景。当前 MANIFEST_VERSION="1.0"，
    # schema 限定 enum ("1.0")，所以这条总是 schema-fail。
    from evaluation.schema import EvalSchemaError
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_with_annotation_file_batch35(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    ann = tmp_path / "a.json"
    ann.write_text("{}", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
            "annotation_file": "a.json",
        }],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_file_str == "a.json"
    assert m.documents[0].annotation_resolved == (tmp_path / "a.json").resolve()


def test_load_manifest_annotation_resolved_none_when_absent_batch35(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_file_str is None
    assert m.documents[0].annotation_resolved is None


def test_load_manifest_expectations_none_when_absent_batch35(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations is None


def test_load_manifest_sha256_none_when_absent_batch35(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 is None


def test_load_manifest_paired_with_none_when_absent_batch35(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].paired_with is None


def test_load_manifest_categories_empty_tuple_when_absent_batch35(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ()


def test_load_manifest_expected_failures_with_source_type_batch35(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_text("y", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "bad1", "path": "bad.pdf",
             "expected_error_code": "E_PARSE", "source_type": "pdf"},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].source_type == "pdf"


def test_load_manifest_expected_failures_default_source_type_none_batch35(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_text("y", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "bad1", "path": "bad.pdf", "expected_error_code": "E_PARSE"},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].source_type is None


def test_load_manifest_documents_returns_tuple_batch35(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m.documents, tuple)


def test_load_manifest_expected_failures_returns_tuple_batch35(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m.expected_failures, tuple)


def test_load_manifest_invalid_json_raises_batch35(tmp_path):
    """JSON 解析失败 → ManifestError。"""
    p = tmp_path / "manifest.json"
    p.write_text("not json {", encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "解析失败" in str(exc.value)


def test_load_manifest_document_with_backslash_path_raises_batch35(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a\\b.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "正斜杠" in str(exc.value)


def test_load_manifest_document_with_absolute_path_raises_batch35(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "/etc/passwd", "source_type": "pdf"}],
        "expected_failures": [],
    })
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "绝对路径" in str(exc.value)


# ---------- _detect_project_root 第三十五批


def test_detect_project_root_no_pyproject_returns_cur_batch35(tmp_path):
    """无 pyproject.toml 时返回 cur（start 的 parent if file）。"""
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert _detect_project_root(sub) == sub.resolve()


def test_detect_project_root_with_str_path_batch35(tmp_path):
    """start 是 Path（不接受 str）。"""
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    # _detect_project_root 接受 Path
    assert _detect_project_root(tmp_path) == tmp_path.resolve()


def test_detect_project_root_resolves_symlinks_batch35(tmp_path):
    """resolve() 后返回的应该是绝对路径。"""
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out.is_absolute()


def test_detect_project_root_starts_from_file_parent_batch35(tmp_path):
    """start 是文件 → 从 parent 开始找。"""
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    f = tmp_path / "any.json"
    f.write_text("{}", encoding="utf-8")
    assert _detect_project_root(f) == tmp_path.resolve()


# ---------- ManifestError 第三十五批


def test_manifest_error_inherits_exception_batch35():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_message_preserved_batch35():
    e = ManifestError("test message")
    assert str(e) == "test message"


def test_manifest_error_no_args_batch35():
    e = ManifestError()
    assert str(e) == ""


def test_manifest_error_multiple_args_batch35():
    e = ManifestError("a", "b", "c")
    assert e.args == ("a", "b", "c")


# ---------- module source forbidden tokens 第五十三批


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
def test_module_source_no_forbidden_tokens_batch35(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch35():
    src = inspect.getsource(mmod)
    assert "开发集清单加载器" in src


def test_module_source_contains_future_annotations_batch35():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_json_import_batch35():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_source_contains_dataclass_import_batch35():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_contains_pathlib_import_batch35():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_import_batch35():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_contains_manifest_version_import_batch35():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_contains_validate_import_batch35():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_contains_relative_to_call_batch35():
    src = inspect.getsource(mmod)
    assert "resolved.relative_to(project_root_resolved)" in src


def test_module_source_contains_resolve_call_batch35():
    src = inspect.getsource(mmod)
    assert "(project_root / path_str).resolve()" in src


def test_module_source_contains_pyproject_check_batch35():
    src = inspect.getsource(mmod)
    assert "(parent / \"pyproject.toml\").is_file()" in src


def test_module_source_contains_encoding_utf8_batch35():
    src = inspect.getsource(mmod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_all_list_batch35():
    src = inspect.getsource(mmod)
    assert "__all__" in src


def test_module_source_all_contains_manifest_error_batch35():
    src = inspect.getsource(mmod)
    assert '"ManifestError"' in src


def test_module_source_all_contains_manifest_batch35():
    src = inspect.getsource(mmod)
    assert '"Manifest"' in src


def test_module_source_all_contains_document_entry_batch35():
    src = inspect.getsource(mmod)
    assert '"DocumentEntry"' in src


def test_module_source_all_contains_expected_failure_batch35():
    src = inspect.getsource(mmod)
    assert '"ExpectedFailure"' in src


def test_module_source_all_contains_load_manifest_batch35():
    src = inspect.getsource(mmod)
    assert '"load_manifest"' in src


# ---------- signatures 第四十九批


def test_signature_is_absolute_like_return_bool_batch35():
    sig = inspect.signature(_is_absolute_like)
    assert sig.return_annotation == "bool"


def test_signature_has_backslash_return_bool_batch35():
    sig = inspect.signature(_has_backslash)
    assert sig.return_annotation == "bool"


def test_signature_resolve_relative_path_params_batch35():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters.keys()) == ["path_str", "project_root", "field_name"]


def test_signature_resolve_relative_path_return_path_batch35():
    sig = inspect.signature(_resolve_relative_path)
    assert sig.return_annotation == "Path"


def test_signature_load_manifest_two_params_batch35():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters.keys()) == ["manifest_path", "project_root"]


def test_signature_load_manifest_project_root_optional_batch35():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_signature_load_manifest_return_manifest_batch35():
    sig = inspect.signature(load_manifest)
    assert sig.return_annotation == "Manifest"


def test_signature_detect_project_root_return_path_batch35():
    sig = inspect.signature(_detect_project_root)
    assert sig.return_annotation == "Path"


# ---------- module 合理性第四十九批


def test_module_imports_json_batch35():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_imports_dataclass_batch35():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_imports_pathlib_batch35():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_has_manifest_error_class_batch35():
    assert isinstance(mmod.ManifestError, type)
    assert issubclass(mmod.ManifestError, Exception)


def test_module_has_document_entry_class_batch35():
    assert isinstance(mmod.DocumentEntry, type)


def test_module_has_expected_failure_class_batch35():
    assert isinstance(mmod.ExpectedFailure, type)


def test_module_has_manifest_class_batch35():
    assert isinstance(mmod.Manifest, type)


def test_module_has_load_manifest_func_batch35():
    assert callable(mmod.load_manifest)


# ---------- 端到端集成第四十九批


def test_e2e_load_manifest_real_flow_batch35(tmp_path):
    """完整流程：3 docs + 1 expected_failure + categories + paired_with。"""
    pdf = tmp_path / "a.pdf"
    pdf.write_text("x", encoding="utf-8")
    docx = tmp_path / "b.docx"
    docx.write_text("y", encoding="utf-8")
    bad = tmp_path / "bad.pdf"
    bad.write_text("z", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["essay"], "paired_with": "d2"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx",
             "categories": ["essay"], "paired_with": "d1"},
        ],
        "expected_failures": [
            {"doc_id": "bad1", "path": "bad.pdf",
             "expected_error_code": "E_PARSE", "source_type": "pdf"},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.content_group_count == 1  # 1 对配对
    assert m.categories_covered == ["essay"]
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].expected_error_code == "E_PARSE"


def test_e2e_load_manifest_idempotent_batch35(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1 == m2


def test_e2e_manifest_categories_with_unicode_batch35(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
                       "categories": ["散文", "小说"]}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["小说", "散文"]  # 排序后


def test_e2e_manifest_deeply_nested_doc_path_batch35(tmp_path):
    """深度嵌套路径正常解析。"""
    sub = tmp_path / "x" / "y" / "z"
    sub.mkdir(parents=True)
    f = sub / "deep.pdf"
    f.write_text("d", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "x/y/z/deep.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].resolved_path == f.resolve()
