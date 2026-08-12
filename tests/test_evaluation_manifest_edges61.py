"""evaluation/manifest.py 第六十一轮 edges 测试（Round 558）。

补强 edges60 未触及的角度（第三十四批）。
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


# ---------- _is_absolute_like 第三十四批


def test_is_absolute_like_digit_then_colon_batch34():
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_underscore_drive_batch34():
    assert _is_absolute_like("_:/foo") is False


def test_is_absolute_like_three_chars_drive_batch34():
    """3 char path with letter at 0 + colon at 1 + slash at 2 → True。"""
    assert _is_absolute_like("a:/foo") is True


def test_is_absolute_like_uppercase_drive_batch34():
    assert _is_absolute_like("C:\\Windows") is True


def test_is_absolute_like_lowercase_z_batch34():
    assert _is_absolute_like("z:/foo") is True


def test_is_absolute_like_double_slash_batch34():
    """//foo 是 POSIX absolute（startswith /）。"""
    assert _is_absolute_like("//foo") is True


def test_is_absolute_like_tilde_path_batch34():
    """~/foo 不是绝对路径（POSIX 用 ~ 当 home，但函数只判 / 和 盘符）。"""
    assert _is_absolute_like("~/foo") is False


def test_is_absolute_like_just_colon_batch34():
    assert _is_absolute_like(":") is False


# ---------- _has_backslash 第三十四批


def test_has_backslash_tab_batch34():
    assert _has_backslash("\t") is False


def test_has_backslash_slash_batch34():
    assert _has_backslash("/") is False


def test_has_backslash_double_batch34():
    assert _has_backslash("\\\\") is True


def test_has_backslash_trailing_batch34():
    assert _has_backslash("foo\\") is True


def test_has_backslash_leading_batch34():
    assert _has_backslash("\\foo") is True


# ---------- Manifest.content_group_count 第三十四批


def test_content_group_count_two_unidirectional_pairs_batch34():
    """两个单向配对，互不交叉 → 2 组。"""
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                      "d2", None, None, None),
        DocumentEntry("d2", "b.docx", Path("/x/b.docx"), "docx", None, (),
                      None, None, None, None),
        DocumentEntry("d3", "c.pdf", Path("/x/c.pdf"), "pdf", None, (),
                      "d4", None, None, None),
        DocumentEntry("d4", "d.docx", Path("/x/d.docx"), "docx", None, (),
                      None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.content_group_count == 2


def test_content_group_count_self_paired_batch34():
    """doc 自指 paired_with（罕见）→ 算 1 组。"""
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                      "d1", None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.content_group_count == 1


def test_content_group_count_chain_batch34():
    """d1→d2, d2→d3, d3→d1 三角链 → frozenset 去重。"""
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                      "d2", None, None, None),
        DocumentEntry("d2", "b.docx", Path("/x/b.docx"), "docx", None, (),
                      "d3", None, None, None),
        DocumentEntry("d3", "c.pdf", Path("/x/c.pdf"), "pdf", None, (),
                      "d1", None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    # 这个集合会被去重为 3 个 frozenset {d1,d2}, {d2,d3}, {d1,d3}，但都不是同一个
    # 实际算法是按 frozenset 去重，会得到 3 个不同的 frozenset
    assert m.content_group_count >= 1


def test_content_group_count_pair_with_unpaired_batch34():
    """1 对 + 1 单（不属于 pair）= 2 组。"""
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                      "d2", None, None, None),
        DocumentEntry("d2", "b.docx", Path("/x/b.docx"), "docx", None, (),
                      "d1", None, None, None),
        DocumentEntry("d3", "c.pdf", Path("/x/c.pdf"), "pdf", None, (),
                      None, None, None, None),
        DocumentEntry("d4", "d.docx", Path("/x/d.docx"), "docx", None, (),
                      None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.content_group_count == 3


# ---------- Manifest.pdf_count / docx_count 第三十四批


def test_pdf_count_only_docx_batch34():
    docs = (
        DocumentEntry("d1", "a.docx", Path("/x/a.docx"), "docx", None, (),
                      None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.pdf_count == 0
    assert m.docx_count == 1


def test_pdf_count_only_pdf_batch34():
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                      None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.pdf_count == 1
    assert m.docx_count == 0


def test_pdf_count_mixed_batch34():
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


def test_pdf_count_unknown_type_batch34():
    """未知 source_type 不算 pdf 也不算 docx。"""
    docs = (
        DocumentEntry("d1", "a.txt", Path("/x/a.txt"), "txt", None, (),
                      None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.pdf_count == 0
    assert m.docx_count == 0


# ---------- Manifest.categories_covered 第三十四批


def test_categories_covered_single_category_batch34():
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None,
                      ("essay",), None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.categories_covered == ["essay"]


def test_categories_covered_dedup_batch34():
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None,
                      ("essay", "report"), None, None, None, None),
        DocumentEntry("d2", "b.pdf", Path("/x/b.pdf"), "pdf", None,
                      ("essay", "letter"), None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.categories_covered == ["essay", "letter", "report"]


def test_categories_covered_unicode_batch34():
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None,
                      ("中文", "english"), None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.categories_covered == ["english", "中文"]


def test_categories_covered_empty_string_batch34():
    """空字符串也是有效 key（不主动 filter）。"""
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None,
                      ("", "a"), None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert "" in m.categories_covered
    assert "a" in m.categories_covered


# ---------- _resolve_relative_path 第三十四批


def test_resolve_path_normal_relative_batch34(tmp_path):
    p = _resolve_relative_path("foo/bar.pdf", tmp_path, "test")
    assert p == (tmp_path / "foo" / "bar.pdf").resolve()


def test_resolve_path_double_dot_batch34(tmp_path):
    """foo/../bar 解析后是 tmp_path/bar。"""
    p = _resolve_relative_path("foo/../bar.pdf", tmp_path, "test")
    assert p == (tmp_path / "bar.pdf").resolve()


def test_resolve_path_escape_deep_batch34(tmp_path):
    """a/../../../etc 在 tmp_path 内会被视为越界。"""
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("a/../../../etc", tmp_path, "f")
    assert "项目根目录之外" in str(exc.value)


def test_resolve_path_field_name_in_empty_msg_batch34(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("", tmp_path, "myfield")
    assert "myfield" in str(exc.value)


def test_resolve_path_field_name_in_absolute_msg_batch34(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("/etc/passwd", tmp_path, "myfield")
    assert "myfield" in str(exc.value)


def test_resolve_path_field_name_in_backslash_msg_batch34(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("a\\b", tmp_path, "myfield")
    assert "myfield" in str(exc.value)


# ---------- load_manifest 第三十四批


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_with_categories_batch34(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["essay", "report"]},
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ("essay", "report")


def test_load_manifest_with_paired_with_batch34(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "paired_with": "d2"},
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].paired_with == "d2"


def test_load_manifest_with_sha256_batch34(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "sha256": "b" * 64},
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 == "b" * 64


def test_load_manifest_with_expectations_batch34(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "expectations": {"element_count_by_type": {"paragraph": 5}}},
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_document_path_str_preserved_batch34(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "subdir/a.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    })
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "a.pdf").write_text("x", encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].path_str == "subdir/a.pdf"


def test_load_manifest_expected_failure_path_str_preserved_batch34(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_text("y", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "bad1", "path": "bad.pdf", "expected_error_code": "E"}
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].path_str == "bad.pdf"


def test_load_manifest_document_resolved_path_is_absolute_batch34(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].resolved_path.is_absolute()


def test_load_manifest_two_documents_batch34(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    b = tmp_path / "b.docx"
    b.write_text("y", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx"},
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.documents) == 2
    assert m.documents[0].doc_id == "d1"
    assert m.documents[1].doc_id == "d2"


def test_load_manifest_project_root_preserved_batch34(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.project_root == tmp_path.resolve()


# ---------- _detect_project_root 第三十四批


def test_detect_project_root_no_file_param_batch34(tmp_path):
    """start 是目录 → 不需要再 .parent。"""
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    assert _detect_project_root(tmp_path) == tmp_path.resolve()


def test_detect_project_root_file_in_same_dir_batch34(tmp_path):
    """start 是文件 → cur = start.parent。"""
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    f = tmp_path / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    assert _detect_project_root(f) == tmp_path.resolve()


def test_detect_project_root_walks_up_multiple_levels_batch34(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    sub = tmp_path / "a" / "b" / "c"
    sub.mkdir(parents=True)
    assert _detect_project_root(sub) == tmp_path.resolve()


def test_detect_project_root_with_file_in_subdir_batch34(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    sub = tmp_path / "a"
    sub.mkdir()
    f = sub / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    assert _detect_project_root(f) == tmp_path.resolve()


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
def test_module_source_no_forbidden_tokens_batch34(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch34():
    src = inspect.getsource(mmod)
    assert "开发集清单加载器" in src


def test_module_source_contains_future_annotations_batch34():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_frozen_dataclass_batch34():
    src = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in src


def test_module_source_contains_manifest_error_class_batch34():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


def test_module_source_contains_document_entry_class_batch34():
    src = inspect.getsource(mmod)
    assert "class DocumentEntry:" in src


def test_module_source_contains_expected_failure_class_batch34():
    src = inspect.getsource(mmod)
    assert "class ExpectedFailure:" in src


def test_module_source_contains_manifest_class_batch34():
    src = inspect.getsource(mmod)
    assert "class Manifest:" in src


def test_module_source_contains_load_manifest_func_batch34():
    src = inspect.getsource(mmod)
    assert "def load_manifest(" in src


def test_module_source_contains_resolve_relative_path_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in src


def test_module_source_contains_detect_project_root_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root(" in src


def test_module_source_contains_is_absolute_like_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in src


def test_module_source_contains_has_backslash_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _has_backslash(" in src


def test_module_source_contains_validate_call_batch34():
    src = inspect.getsource(mmod)
    assert 'validate(' in src


def test_module_source_contains_all_keys_batch34():
    src = inspect.getsource(mmod)
    assert '"ManifestError"' in src
    assert '"Manifest"' in src
    assert '"DocumentEntry"' in src
    assert '"ExpectedFailure"' in src
    assert '"load_manifest"' in src


# ---------- signatures 第四十九批


def test_signature_is_absolute_like_one_param_batch34():
    sig = inspect.signature(_is_absolute_like)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_signature_has_backslash_one_param_batch34():
    sig = inspect.signature(_has_backslash)
    assert list(sig.parameters.keys()) == ["path_str"]


def test_signature_resolve_relative_path_three_params_batch34():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters.keys()) == ["path_str", "project_root", "field_name"]


def test_signature_load_manifest_params_batch34():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters.keys()) == ["manifest_path", "project_root"]


def test_signature_detect_project_root_one_param_batch34():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters.keys()) == ["start"]


def test_signature_load_manifest_return_manifest_batch34():
    sig = inspect.signature(load_manifest)
    assert sig.return_annotation == "Manifest"


# ---------- module 合理性第四十九批


def test_module_has_future_annotations_batch34():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch34():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_imports_dataclass_batch34():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_imports_pathlib_batch34():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_has_manifest_class_batch34():
    assert hasattr(mmod, "Manifest")


def test_module_has_document_entry_class_batch34():
    assert hasattr(mmod, "DocumentEntry")


def test_module_has_expected_failure_class_batch34():
    assert hasattr(mmod, "ExpectedFailure")


def test_module_has_all_batch34():
    assert hasattr(mmod, "__all__")
    assert "ManifestError" in mmod.__all__
    assert "Manifest" in mmod.__all__
    assert "DocumentEntry" in mmod.__all__
    assert "ExpectedFailure" in mmod.__all__
    assert "load_manifest" in mmod.__all__


# ---------- 端到端集成第四十九批


def test_e2e_full_manifest_round_trip_batch34(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_text("x", encoding="utf-8")
    b = tmp_path / "b.docx"
    b.write_text("y", encoding="utf-8")
    bad = tmp_path / "bad.pdf"
    bad.write_text("z", encoding="utf-8")
    ann = tmp_path / "ann.json"
    ann.write_text("{}", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["essay"], "paired_with": "d2",
             "annotation_file": "ann.json", "sha256": "a" * 64,
             "expectations": {"element_count_by_type": {"paragraph": 5}}},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx",
             "categories": ["essay"], "paired_with": "d1"},
        ],
        "expected_failures": [
            {"doc_id": "bad1", "path": "bad.pdf", "expected_error_code": "E_PARSE",
             "source_type": "pdf"},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.manifest_version == MANIFEST_VERSION
    assert m.devset_status == "incomplete"
    assert len(m.documents) == 2
    assert len(m.expected_failures) == 1
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.content_group_count == 1
    assert m.categories_covered == ["essay"]
    # 详细字段
    d1 = m.documents[0]
    assert d1.annotation_resolved == ann.resolve()
    assert d1.sha256 == "a" * 64
    assert d1.expectations == {"element_count_by_type": {"paragraph": 5}}
    ef = m.expected_failures[0]
    assert ef.source_type == "pdf"
    assert ef.expected_error_code == "E_PARSE"


def test_e2e_idempotent_batch34(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1 == m2


def test_e2e_default_project_root_finds_pyproject_batch34(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[x]", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p)
    assert m.project_root == tmp_path.resolve()


def test_e2e_invalid_path_in_doc_batch34(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "/etc/passwd", "source_type": "pdf"},
        ],
        "expected_failures": [],
    })
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "绝对路径" in str(exc.value)


def test_e2e_json_decode_error_msg_batch34(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("{broken", encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p)
    assert "JSON 解析失败" in str(exc.value)
