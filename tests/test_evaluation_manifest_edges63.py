"""evaluation/manifest.py 第六十三轮 edges 测试（Round 572）。

补强 edges62 未触及的角度（第三十六批）。
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


# ---------- DocumentEntry 第三十六批


def test_document_entry_field_types_batch36():
    """字段类型断言（frozen）。"""
    d = DocumentEntry(
        doc_id="d1",
        path_str="a.pdf",
        resolved_path=Path("/x/a.pdf"),
        source_type="pdf",
        sha256="abc",
        categories=("c1",),
        paired_with="d2",
        annotation_file_str="a.json",
        annotation_resolved=Path("/x/a.json"),
        expectations={"x": 1},
    )
    assert d.doc_id == "d1"
    assert d.path_str == "a.pdf"
    assert d.source_type == "pdf"
    assert d.sha256 == "abc"
    assert d.categories == ("c1",)
    assert d.paired_with == "d2"
    assert d.annotation_file_str == "a.json"
    assert d.annotation_resolved == Path("/x/a.json")
    assert d.expectations == {"x": 1}


def test_document_entry_sha256_none_default_batch36():
    d = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None)
    assert d.sha256 is None


def test_document_entry_categories_default_empty_tuple_batch36():
    d = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None)
    assert d.categories == ()


def test_document_entry_paired_with_default_none_batch36():
    d = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None)
    assert d.paired_with is None


def test_document_entry_annotation_resolved_default_none_batch36():
    d = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None)
    assert d.annotation_resolved is None


def test_document_entry_expectations_default_none_batch36():
    d = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None)
    assert d.expectations is None


def test_document_entry_with_categories_paired_annotation_batch36():
    """完整字段无 None。"""
    d = DocumentEntry("d1", "a/b.pdf", Path("/x/a/b.pdf"), "pdf", "sha",
                     ("essay", "report"), "d2", "a/b.json",
                     Path("/x/a/b.json"), {"k": "v"})
    assert d.categories == ("essay", "report")
    assert d.paired_with == "d2"
    assert d.annotation_file_str == "a/b.json"


def test_document_entry_str_representation_batch36():
    d = DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None)
    s = str(d)
    assert "d1" in s
    assert "DocumentEntry" in s


# ---------- ExpectedFailure 第三十六批


def test_expected_failure_full_construction_batch36():
    ef = ExpectedFailure("bad1", "bad.pdf", Path("/x/bad.pdf"),
                        "E_PARSE", "pdf")
    assert ef.doc_id == "bad1"
    assert ef.path_str == "bad.pdf"
    assert ef.expected_error_code == "E_PARSE"
    assert ef.source_type == "pdf"


def test_expected_failure_repr_batch36():
    ef = ExpectedFailure("bad1", "bad.pdf", Path("/x/bad.pdf"),
                        "E_PARSE", "pdf")
    r = repr(ef)
    assert "ExpectedFailure" in r
    assert "bad1" in r


def test_expected_failure_str_with_unicode_batch36():
    ef = ExpectedFailure("中文", "中文.pdf", Path("/x/中文.pdf"),
                        "E_PARSE", None)
    assert ef.doc_id == "中文"


def test_expected_failure_equality_batch36():
    ef1 = ExpectedFailure("d1", "p", Path("/x/p"), "E1", None)
    ef2 = ExpectedFailure("d1", "p", Path("/x/p"), "E1", None)
    assert ef1 == ef2


def test_expected_failure_inequality_batch36():
    ef1 = ExpectedFailure("d1", "p", Path("/x/p"), "E1", None)
    ef2 = ExpectedFailure("d2", "p", Path("/x/p"), "E1", None)
    assert ef1 != ef2


# ---------- Manifest properties 第三十六批


def test_manifest_pdf_count_only_batch36():
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None),
        DocumentEntry("d2", "b.pdf", Path("/x/b.pdf"), "pdf", None, (),
                     None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.pdf_count == 2
    assert m.docx_count == 0


def test_manifest_docx_count_only_batch36():
    docs = (
        DocumentEntry("d1", "a.docx", Path("/x/a.docx"), "docx", None, (),
                     None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.docx_count == 1
    assert m.pdf_count == 0


def test_manifest_mixed_source_types_batch36():
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None),
        DocumentEntry("d2", "b.docx", Path("/x/b.docx"), "docx", None, (),
                     None, None, None, None),
        DocumentEntry("d3", "c.pdf", Path("/x/c.pdf"), "pdf", None, (),
                     None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.pdf_count == 2
    assert m.docx_count == 1
    assert m.file_count == 3


def test_manifest_content_group_count_unpaired_batch36():
    """3 个未配对的 doc → 3 组。"""
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     None, None, None, None),
        DocumentEntry("d2", "b.pdf", Path("/x/b.pdf"), "pdf", None, (),
                     None, None, None, None),
        DocumentEntry("d3", "c.pdf", Path("/x/c.pdf"), "pdf", None, (),
                     None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.content_group_count == 3


def test_manifest_content_group_count_one_pair_batch36():
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     "d2", None, None, None),
        DocumentEntry("d2", "b.docx", Path("/x/b.docx"), "docx", None, (),
                     "d1", None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.content_group_count == 1


def test_manifest_content_group_count_pair_plus_unpaired_batch36():
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                     "d2", None, None, None),
        DocumentEntry("d2", "b.docx", Path("/x/b.docx"), "docx", None, (),
                     "d1", None, None, None),
        DocumentEntry("d3", "c.pdf", Path("/x/c.pdf"), "pdf", None, (),
                     None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.content_group_count == 2


def test_manifest_categories_covered_sorted_batch36():
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None,
                     ("zeta", "alpha"), None, None, None, None),
        DocumentEntry("d2", "b.pdf", Path("/x/b.pdf"), "pdf", None,
                     ("middle",), None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.categories_covered == ["alpha", "middle", "zeta"]


def test_manifest_categories_covered_dedup_batch36():
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None,
                     ("essay",), None, None, None, None),
        DocumentEntry("d2", "b.pdf", Path("/x/b.pdf"), "pdf", None,
                     ("essay", "report"), None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.categories_covered == ["essay", "report"]


def test_manifest_field_count_5_batch36():
    """重新断言字段数。"""
    flds = fields(Manifest)
    assert len(flds) == 5


def test_manifest_hashable_batch36():
    """frozen=True → Manifest 是 hashable。"""
    m = Manifest("1.0", "incomplete", (), (), Path("/x"))
    assert isinstance(hash(m), int)


def test_manifest_equality_batch36():
    m1 = Manifest("1.0", "incomplete", (), (), Path("/x"))
    m2 = Manifest("1.0", "incomplete", (), (), Path("/x"))
    assert m1 == m2


def test_manifest_inequality_different_status_batch36():
    m1 = Manifest("1.0", "incomplete", (), (), Path("/x"))
    m2 = Manifest("1.0", "complete", (), (), Path("/x"))
    assert m1 != m2


def test_manifest_repr_batch36():
    m = Manifest("1.0", "incomplete", (), (), Path("/x"))
    r = repr(m)
    assert "Manifest" in r
    assert "1.0" in r


# ---------- _is_absolute_like / _has_backslash 第三十六批


def test_is_absolute_like_tilde_path_batch36():
    """~ 不是绝对路径。"""
    assert _is_absolute_like("~/foo") is False


def test_is_absolute_like_just_colon_batch36():
    assert _is_absolute_like(":") is False


def test_is_absolute_like_just_colon_slash_batch36():
    assert _is_absolute_like(":/foo") is False  # 第 0 个字符不是 alpha


def test_is_absolute_like_alpha_colon_no_slash_batch36():
    """X:foo 在 Windows 上是驱动器相对路径，函数判定为非绝对。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_alpha_colon_backslash_batch36():
    assert _is_absolute_like("C:\\") is True


def test_is_absolute_like_alpha_colon_forward_batch36():
    assert _is_absolute_like("D:/") is True


def test_is_absolute_like_lowercase_alpha_colon_backslash_batch36():
    assert _is_absolute_like("c:\\foo") is True


def test_is_absolute_like_digit_colon_batch36():
    """数字 + : + / 不是绝对（数字不是 alpha）。"""
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_underscore_colon_batch36():
    """下划线不是 alpha。"""
    assert _is_absolute_like("_:/foo") is False


def test_has_backslash_normal_relative_batch36():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_single_char_batch36():
    assert _has_backslash("a") is False


def test_has_backslash_double_backslash_batch36():
    assert _has_backslash("\\\\") is True


def test_has_backslash_trailing_backslash_batch36():
    assert _has_backslash("foo/") is False


# ---------- _resolve_relative_path 第三十六批


def test_resolve_path_empty_raises_batch36(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("", tmp_path, "f")
    assert "为空" in str(exc.value)


def test_resolve_path_field_name_in_error_batch36(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("C:\\bar", tmp_path, "field123")
    assert "field123" in str(exc.value)


def test_resolve_path_backslash_message_contains_field_batch36(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("a\\b", tmp_path, "myfield")
    s = str(exc.value)
    assert "myfield" in s
    assert "正斜杠" in s


def test_resolve_path_returns_path_instance_batch36(tmp_path):
    p = _resolve_relative_path("a.pdf", tmp_path, "f")
    assert isinstance(p, Path)


def test_resolve_path_already_resolved_in_root_batch36(tmp_path):
    """绝对路径在 project_root 内（但被拒绝因为是绝对的）。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path(str(tmp_path / "a.pdf"), tmp_path, "f")


def test_resolve_path_dotdot_to_inside_root_batch36(tmp_path):
    """sub/../a.pdf → tmp_path/a.pdf，仍在内。"""
    p = _resolve_relative_path("sub/../a.pdf", tmp_path, "f")
    assert p == (tmp_path / "a.pdf").resolve()


def test_resolve_path_three_levels_up_inside_batch36(tmp_path):
    """tmp_path/a/b/c/../../d.pdf → tmp_path/a/d.pdf，仍在内。"""
    p = _resolve_relative_path("a/b/c/../../d.pdf", tmp_path, "f")
    assert p == (tmp_path / "a" / "d.pdf").resolve()


# ---------- load_manifest 第三十六批


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_default_devset_status_value_batch36(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.devset_status == "incomplete"


def test_load_manifest_complete_devset_status_batch36(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.devset_status == "complete"


def test_load_manifest_returns_manifest_instance_batch36(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)


def test_load_manifest_manifest_version_matches_constant_batch36(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.manifest_version == MANIFEST_VERSION


def test_load_manifest_path_resolve_called_batch36(tmp_path):
    """load_manifest 内部对 manifest_path 做 .resolve()。"""
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_missing_documents_key_batch36(tmp_path):
    """schema 要求 documents 必填 → 缺省时 EvalSchemaError。"""
    from evaluation.schema import EvalSchemaError
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "expected_failures": [],
    })
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_missing_expected_failures_key_batch36(tmp_path):
    """expected_failures 缺省 → 仍可加载（schema 不要求），返回空 tuple。"""
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures == ()


def test_load_manifest_categories_as_list_batch36(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
                       "categories": ["a", "b", "c"]}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ("a", "b", "c")


def test_load_manifest_with_sha256_batch36(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
                       "sha256": "a" * 64}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 == "a" * 64


def test_load_manifest_with_expectations_batch36(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    exp = {"element_count_by_type": {"paragraph": 5}}
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
                       "expectations": exp}],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations == exp


def test_load_manifest_expected_failure_path_resolved_batch36(tmp_path):
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
    assert m.expected_failures[0].resolved_path == bad.resolve()


def test_load_manifest_expected_failure_path_str_batch36(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_text("y", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "bad1", "path": "bad.pdf",
             "expected_error_code": "E_PARSE"},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].path_str == "bad.pdf"


def test_load_manifest_annotation_resolved_inside_root_batch36(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    ann = tmp_path / "sub" / "a.json"
    ann.parent.mkdir(parents=True)
    ann.write_text("{}", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
            "annotation_file": "sub/a.json",
        }],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_resolved == ann.resolve()


def test_load_manifest_annotation_absolute_raises_batch36(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
            "annotation_file": "/etc/passwd",
        }],
        "expected_failures": [],
    })
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "绝对路径" in str(exc.value)


def test_load_manifest_annotation_with_backslash_raises_batch36(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
            "annotation_file": "a\\b.json",
        }],
        "expected_failures": [],
    })
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "正斜杠" in str(exc.value)


def test_load_manifest_annotation_escape_outside_root_batch36(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
            "annotation_file": "../escape.json",
        }],
        "expected_failures": [],
    })
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "之外" in str(exc.value) or "→" in str(exc.value)


def test_load_manifest_expected_failure_escape_outside_root_batch36(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "bad1", "path": "../escape.pdf",
             "expected_error_code": "E_PARSE"},
        ],
    })
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_document_escape_outside_root_batch36(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "../escape.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_json_array_top_level_raises_batch36(tmp_path):
    """JSON 顶层是 array → schema 失败 → EvalSchemaError。"""
    p = tmp_path / "manifest.json"
    p.write_text("[]", encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_json_string_top_level_raises_batch36(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text('"hello"', encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_json_int_top_level_raises_batch36(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("42", encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_json_null_top_level_raises_batch36(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("null", encoding="utf-8")
    from evaluation.schema import EvalSchemaError
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_directory_path_raises_batch36(tmp_path):
    """manifest_path 是目录 → ManifestError。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(ManifestError) as exc:
        load_manifest(sub, project_root=tmp_path)
    assert "不存在" in str(exc.value)


def test_load_manifest_no_project_root_uses_detect_batch36(tmp_path):
    """project_root=None → 使用 _detect_project_root。"""
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
        "expected_failures": [],
    })
    m = load_manifest(p)  # 不传 project_root
    assert m.project_root == tmp_path.resolve()


# ---------- _detect_project_root 第三十六批


def test_detect_project_root_nested_pyproject_batch36(tmp_path):
    """找最近的 pyproject.toml（向上递归）。"""
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert _detect_project_root(sub) == tmp_path.resolve()


def test_detect_project_root_two_pyprojects_batch36(tmp_path):
    """两个 pyproject.toml → 找最近（最深的）那个。"""
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    sub = tmp_path / "a"
    sub.mkdir()
    (sub / "pyproject.toml").write_text("[y]", encoding="utf-8")
    subsub = sub / "b"
    subsub.mkdir()
    assert _detect_project_root(subsub) == sub.resolve()


def test_detect_project_root_no_pyproject_at_all_batch36(tmp_path):
    """完全没有 pyproject.toml → 返回 cur。"""
    sub = tmp_path / "x"
    sub.mkdir()
    assert _detect_project_root(sub) == sub.resolve()


def test_detect_project_root_path_param_only_batch36(tmp_path):
    """签名只有 start 参数（无其他）。"""
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters.keys()) == ["start"]


# ---------- ManifestError 第三十六批


def test_manifest_error_with_cause_batch36():
    try:
        try:
            raise ValueError("inner")
        except ValueError as e:
            raise ManifestError("outer") from e
    except ManifestError as ex:
        assert ex.__cause__ is not None
        assert isinstance(ex.__cause__, ValueError)


def test_manifest_error_is_not_keyerror_batch36():
    assert not issubclass(ManifestError, KeyError)


def test_manifest_error_is_not_valueerror_batch36():
    assert not issubclass(ManifestError, ValueError)


def test_manifest_error_is_not_typeerror_batch36():
    assert not issubclass(ManifestError, TypeError)


def test_manifest_error_can_be_raised_and_caught_batch36():
    with pytest.raises(ManifestError):
        raise ManifestError("test")


def test_manifest_error_caught_as_exception_batch36():
    """被 except Exception 捕获。"""
    with pytest.raises(Exception):
        raise ManifestError("test")


# ---------- module source forbidden tokens 第五十四批


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
def test_module_source_no_forbidden_tokens_batch36(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第五十批


def test_module_source_contains_devset_status_in_docstring_batch36():
    src = inspect.getsource(mmod)
    assert "devset_status" in src


def test_module_source_contains_path_field_docstring_batch36():
    src = inspect.getsource(mmod)
    assert "相对路径" in src


def test_module_source_contains_windows_drive_comment_batch36():
    src = inspect.getsource(mmod)
    assert "Windows 盘符" in src


def test_module_source_contains_path_str_field_batch36():
    src = inspect.getsource(mmod)
    assert "path_str: str" in src


def test_module_source_contains_resolved_path_field_batch36():
    src = inspect.getsource(mmod)
    assert "resolved_path: Path" in src


def test_module_source_contains_source_type_field_batch36():
    src = inspect.getsource(mmod)
    assert "source_type: str" in src


def test_module_source_contains_sha256_optional_field_batch36():
    src = inspect.getsource(mmod)
    assert "sha256: str | None" in src


def test_module_source_contains_categories_tuple_field_batch36():
    src = inspect.getsource(mmod)
    assert "categories: tuple[str, ...]" in src


def test_module_source_contains_paired_with_optional_batch36():
    src = inspect.getsource(mmod)
    assert "paired_with: str | None" in src


def test_module_source_contains_annotation_resolved_optional_batch36():
    src = inspect.getsource(mmod)
    assert "annotation_resolved: Path | None" in src


def test_module_source_contains_expectations_dict_batch36():
    src = inspect.getsource(mmod)
    assert "expectations: dict[str, Any] | None" in src


def test_module_source_contains_expected_error_code_field_batch36():
    src = inspect.getsource(mmod)
    assert "expected_error_code: str" in src


def test_module_source_contains_manifest_version_field_batch36():
    src = inspect.getsource(mmod)
    assert "manifest_version: str" in src


def test_module_source_contains_documents_tuple_batch36():
    src = inspect.getsource(mmod)
    assert "documents: tuple[DocumentEntry, ...]" in src


def test_module_source_contains_expected_failures_tuple_batch36():
    src = inspect.getsource(mmod)
    assert "expected_failures: tuple[ExpectedFailure, ...]" in src


def test_module_source_contains_project_root_field_batch36():
    src = inspect.getsource(mmod)
    assert "project_root: Path" in src


def test_module_source_contains_file_count_property_batch36():
    src = inspect.getsource(mmod)
    assert "def file_count" in src


def test_module_source_contains_pdf_count_property_batch36():
    src = inspect.getsource(mmod)
    assert "def pdf_count" in src


def test_module_source_contains_docx_count_property_batch36():
    src = inspect.getsource(mmod)
    assert "def docx_count" in src


def test_module_source_contains_content_group_count_property_batch36():
    src = inspect.getsource(mmod)
    assert "def content_group_count" in src


def test_module_source_contains_categories_covered_property_batch36():
    src = inspect.getsource(mmod)
    assert "def categories_covered" in src


def test_module_source_contains_manifest_version_check_batch36():
    src = inspect.getsource(mmod)
    assert 'data.get("manifest_version") != MANIFEST_VERSION' in src


def test_module_source_contains_resolve_relative_path_func_batch36():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in src


def test_module_source_contains_detect_project_root_func_batch36():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root(" in src


# ---------- signatures 第五十批


def test_signature_manifest_error_inherits_exception_batch36():
    """ManifestError 没有自定义 __init__，直接继承 Exception。"""
    assert ManifestError.__init__ is Exception.__init__


def test_signature_document_entry_params_batch36():
    sig = inspect.signature(DocumentEntry)
    params = list(sig.parameters.keys())
    assert params == [
        "doc_id", "path_str", "resolved_path", "source_type", "sha256",
        "categories", "paired_with", "annotation_file_str",
        "annotation_resolved", "expectations",
    ]


def test_signature_expected_failure_params_batch36():
    sig = inspect.signature(ExpectedFailure)
    params = list(sig.parameters.keys())
    assert params == ["doc_id", "path_str", "resolved_path",
                      "expected_error_code", "source_type"]


def test_signature_manifest_params_batch36():
    sig = inspect.signature(Manifest)
    params = list(sig.parameters.keys())
    assert params == ["manifest_version", "devset_status", "documents",
                      "expected_failures", "project_root"]


def test_signature_resolve_relative_path_return_annotation_batch36():
    """_resolve_relative_path 的 return annotation。"""
    sig = inspect.signature(_resolve_relative_path)
    # 因为 from __future__ import annotations，annotations 都是字符串
    assert sig.return_annotation == "Path"


def test_signature_load_manifest_manifest_path_no_default_batch36():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["manifest_path"].default is inspect.Parameter.empty


def test_signature_is_absolute_like_param_path_str_batch36():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]


def test_signature_has_backslash_param_path_str_batch36():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]


# ---------- module 合理性第五十批


def test_module_has_manifest_error_attribute_batch36():
    assert hasattr(mmod, "ManifestError")


def test_module_has_document_entry_attribute_batch36():
    assert hasattr(mmod, "DocumentEntry")


def test_module_has_expected_failure_attribute_batch36():
    assert hasattr(mmod, "ExpectedFailure")


def test_module_has_manifest_attribute_batch36():
    assert hasattr(mmod, "Manifest")


def test_module_has_load_manifest_attribute_batch36():
    assert hasattr(mmod, "load_manifest")


def test_module_has_is_absolute_like_attribute_batch36():
    assert hasattr(mmod, "_is_absolute_like")


def test_module_has_has_backslash_attribute_batch36():
    assert hasattr(mmod, "_has_backslash")


def test_module_has_resolve_relative_path_attribute_batch36():
    assert hasattr(mmod, "_resolve_relative_path")


def test_module_has_detect_project_root_attribute_batch36():
    assert hasattr(mmod, "_detect_project_root")


def test_module_manifest_error_is_class_batch36():
    assert isinstance(mmod.ManifestError, type)


def test_module_document_entry_is_class_batch36():
    assert isinstance(mmod.DocumentEntry, type)


# ---------- 端到端集成第五十批


def test_e2e_load_manifest_real_paired_pair_batch36(tmp_path):
    """双向 paired_with → content_group_count=1。"""
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    b = tmp_path / "b.docx"
    b.write_text("y", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "paired_with": "d2"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx",
             "paired_with": "d1"},
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 1
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.file_count == 2


def test_e2e_load_manifest_one_way_paired_batch36(tmp_path):
    """单向 paired_with → 仍算 1 组（避免重复计数）。"""
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    b = tmp_path / "b.docx"
    b.write_text("y", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "paired_with": "d2"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx"},
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    # d1 paired_with d2 → frozenset{d1,d2} → 1 组
    # d2 不在 seen，但 paired_with 在 pair_ids 已建立
    # 实际逻辑：d2.doc_id not in seen 且 d2.paired_with 是 None → unpaired 计数
    # 但 d2.doc_id 已在 seen 中（因为 frozenset 把它加进去了）→ 不计 unpaired
    assert m.content_group_count == 1


def test_e2e_load_manifest_unpaired_three_docs_batch36(tmp_path):
    """3 个独立 doc → content_group_count=3。"""
    paths = []
    for i, name in enumerate(["a.pdf", "b.pdf", "c.pdf"]):
        f = tmp_path / name
        f.write_text(str(i), encoding="utf-8")
        paths.append(name)
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": f"d{i}", "path": name, "source_type": "pdf"}
            for i, name in enumerate(paths, start=1)
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.content_group_count == 3


def test_e2e_load_manifest_with_annotation_full_batch36(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    ann = tmp_path / "a.json"
    ann.write_text(json.dumps({"annotation_version": "1.0", "doc_id": "d1"}), encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
            "annotation_file": "a.json",
            "categories": ["essay"],
            "sha256": "b" * 64,
        }],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    d = m.documents[0]
    assert d.annotation_file_str == "a.json"
    assert d.annotation_resolved == ann.resolve()
    assert d.categories == ("essay",)
    assert d.sha256 == "b" * 64


def test_e2e_load_manifest_full_round_trip_batch36(tmp_path):
    """完整 round-trip：所有字段都填上。"""
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    b = tmp_path / "b.docx"
    b.write_text("y", encoding="utf-8")
    bad = tmp_path / "bad.pdf"
    bad.write_text("z", encoding="utf-8")
    ann = tmp_path / "a.json"
    ann.write_text("{}", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["essay"], "paired_with": "d2",
             "annotation_file": "a.json", "sha256": "c" * 64,
             "expectations": {"element_count_by_type": {"paragraph": 3}}},
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
    assert m.content_group_count == 1
    assert m.categories_covered == ["essay"]
    assert len(m.expected_failures) == 1
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 3}}
    assert m.documents[0].sha256 == "c" * 64
    assert m.documents[0].annotation_file_str == "a.json"
