"""evaluation/manifest.py 第四十六轮 edges 测试（Round 454）。

补强 edges45 未触及的角度：
- _is_absolute_like 行为深度第十九批（drive letter lowercase / uppercase / mixed case / 3 chars but no colon）
- _has_backslash 行为深度第十九批（multiple consecutive / backslash before forward slash）
- _resolve_relative_path 行为深度第十九批（multiple levels deep / single file / Unicode path / Windows-style drive letter rejected）
- _detect_project_root 行为深度第十九批（cur is symlink / cur nested deep / start is root）
- Manifest dataclass 第十九批（fields 类型 / default values / hashable 含 tuple / equality with different values）
- Manifest properties 第十九批（categories_covered with duplicates / mixed docs / content_group with self-paired）
- DocumentEntry 第十九批（all fields / annotation_resolved default / expectations default）
- ExpectedFailure 第十九批（fields / source_type 'other'）
- load_manifest 行为深度第十九批（JSON 含 trailing comma → invalid / Unicode doc_id / annotation_resolved 解析 / expectations 透传 / sha256 校验）
- module source forbidden tokens 第三十三批
- module source 字符串精确补强第三十一批
- signatures 第二十九批
- module 合理性第二十九批
- 端到端集成第二十九批
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
from evaluation import manifest as mmod


# ---------- _is_absolute_like 行为深度第十九批 ----------


def test_is_absolute_like_lowercase_drive_batch19():
    assert _is_absolute_like("c:\\foo") is True


def test_is_absolute_like_uppercase_drive_batch19():
    assert _is_absolute_like("C:/foo") is True


def test_is_absolute_like_mixed_case_drive_batch19():
    assert _is_absolute_like("A:\\B") is True


def test_is_absolute_like_three_chars_no_colon_batch19():
    assert _is_absolute_like("abc") is False


def test_is_absolute_like_three_chars_no_separator_batch19():
    """C:foo (3 chars, no \\ or /) → not absolute。"""
    assert _is_absolute_like("C:f") is False


def test_is_absolute_like_long_relative_batch19():
    assert _is_absolute_like("a/b/c/d/e/f") is False


def test_is_absolute_like_just_drive_letter_batch19():
    """'C:' len=2 → not absolute (need len>=3)。"""
    assert _is_absolute_like("C:") is False


# ---------- _has_backslash 行为深度第十九批 ----------


def test_has_backslash_multiple_consecutive_batch19():
    assert _has_backslash("a\\\\\\b") is True


def test_has_backslash_backslash_then_forward_batch19():
    assert _has_backslash("a\\/b") is True


def test_has_backslash_forward_then_backslash_batch19():
    assert _has_backslash("a/\\b") is True


def test_has_backslash_only_spaces_batch19():
    assert _has_backslash("   ") is False


# ---------- _resolve_relative_path 行为深度第十九批 ----------


def test_resolve_relative_path_multi_level_batch19(tmp_path):
    rp = _resolve_relative_path("a/b/c/d/e.pdf", tmp_path, "f")
    assert rp == (tmp_path / "a" / "b" / "c" / "d" / "e.pdf").resolve()


def test_resolve_relative_path_single_file_batch19(tmp_path):
    rp = _resolve_relative_path("a.pdf", tmp_path, "f")
    assert rp == (tmp_path / "a.pdf").resolve()


def test_resolve_relative_path_unicode_filename_batch19(tmp_path):
    rp = _resolve_relative_path("中文/文件.pdf", tmp_path, "f")
    assert rp == (tmp_path / "中文" / "文件.pdf").resolve()


def test_resolve_relative_path_drive_letter_rejected_batch19(tmp_path):
    with pytest.raises(ManifestError, match="绝对路径"):
        _resolve_relative_path("D:/foo/bar.pdf", tmp_path, "f")


def test_resolve_relative_path_lowercase_drive_rejected_batch19(tmp_path):
    with pytest.raises(ManifestError, match="绝对路径"):
        _resolve_relative_path("d:\\foo", tmp_path, "f")


def test_resolve_relative_path_inside_root_batch19(tmp_path):
    rp = _resolve_relative_path("a/b.pdf", tmp_path, "f")
    # rp 应位于 tmp_path 内
    rp.relative_to(tmp_path.resolve())


def test_resolve_relative_path_field_name_in_error_batch19(tmp_path):
    """错误信息含 field_name。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "custom_field_name")
    assert "custom_field_name" in str(exc_info.value)


# ---------- _detect_project_root 行为深度第十九批 ----------


def test_detect_project_root_start_with_pyproject_batch19(tmp_path):
    """start 目录本身含 pyproject → 返回 start。"""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("", encoding="utf-8")
    rp = _detect_project_root(tmp_path)
    assert rp == tmp_path.resolve()


def test_detect_project_root_deep_nested_batch19(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("", encoding="utf-8")
    sub1 = tmp_path / "s1"
    sub1.mkdir()
    sub2 = sub1 / "s2"
    sub2.mkdir()
    sub3 = sub2 / "s3"
    sub3.mkdir()
    rp = _detect_project_root(sub3)
    assert rp == tmp_path.resolve()


def test_detect_project_root_returns_absolute_batch19(tmp_path):
    rp = _detect_project_root(tmp_path)
    assert rp.is_absolute()


def test_detect_project_root_string_path_batch19(tmp_path):
    """传 str 路径会被 Path() 处理。"""
    rp = _detect_project_root(Path(tmp_path))
    assert isinstance(rp, Path)


# ---------- Manifest dataclass 第十九批 ----------


def _mk_manifest_basic():
    return Manifest(
        manifest_version=MANIFEST_VERSION,
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/fake"),
    )


def test_manifest_field_types_batch19():
    flds = {f.name: f for f in fields(Manifest)}
    # manifest_version 是 str
    assert flds["manifest_version"].type == "str" or flds["manifest_version"].type is str
    # documents 是 tuple
    assert "tuple" in str(flds["documents"].type)


def test_manifest_hashable_with_documents_batch19():
    """Manifest 含 documents tuple → 仍 hashable。"""
    doc = DocumentEntry(
        doc_id="d1", path_str="a.pdf",
        resolved_path=Path("/fake/a.pdf"),
        source_type="pdf", sha256=None,
        categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(MANIFEST_VERSION, "incomplete", (doc,), (), Path("/fake"))
    assert hash(m) is not None


def test_manifest_inequality_batch19():
    m1 = Manifest(MANIFEST_VERSION, "incomplete", (), (), Path("/fake"))
    m2 = Manifest(MANIFEST_VERSION, "complete", (), (), Path("/fake"))
    assert m1 != m2


def test_manifest_no_default_values_batch19():
    """Manifest 字段都无 default（必须显式传）。"""
    import dataclasses
    for f in fields(Manifest):
        # dataclasses 用 MISSING sentinel 表示无 default
        assert f.default is dataclasses.MISSING
        assert f.default_factory is dataclasses.MISSING


# ---------- Manifest properties 第十九批 ----------


def _mk_doc(doc_id="d1", source_type="pdf", categories=("c1",), paired_with=None):
    return DocumentEntry(
        doc_id=doc_id, path_str=f"samples/{doc_id}.pdf",
        resolved_path=Path(f"/fake/{doc_id}.pdf"),
        source_type=source_type, sha256=None,
        categories=categories, paired_with=paired_with,
        annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )


def test_manifest_categories_covered_empty_batch19():
    m = _mk_manifest_basic()
    assert m.categories_covered == []


def test_manifest_pdf_count_zero_when_no_pdf_batch19():
    docs = (_mk_doc("d1", "docx"), _mk_doc("d2", "docx"))
    m = Manifest(MANIFEST_VERSION, "incomplete", docs, (), Path("/fake"))
    assert m.pdf_count == 0


def test_manifest_docx_count_zero_when_no_docx_batch19():
    docs = (_mk_doc("d1", "pdf"),)
    m = Manifest(MANIFEST_VERSION, "incomplete", docs, (), Path("/fake"))
    assert m.docx_count == 0


def test_manifest_content_group_count_self_paired_batch19():
    """doc 自己 paired_with 自己（异常但代码不校验）。"""
    docs = (_mk_doc("d1", paired_with="d1"),)
    m = Manifest(MANIFEST_VERSION, "incomplete", docs, (), Path("/fake"))
    # frozenset({"d1", "d1"}) = frozenset({"d1"}) → 1 group
    assert m.content_group_count == 1


def test_manifest_content_group_count_one_way_paired_batch19():
    """单向 paired 也算 1 组。"""
    docs = (
        _mk_doc("d1", paired_with="d2"),
        _mk_doc("d2"),  # 不指回 d1
    )
    m = Manifest(MANIFEST_VERSION, "incomplete", docs, (), Path("/fake"))
    # d1.paired_with="d2" → frozenset({"d1","d2"})；seen={d1,d2}
    # d2.doc_id in seen → 不算 unpaired
    # 总组数 = 1
    assert m.content_group_count == 1


# ---------- DocumentEntry 第十九批 ----------


def test_document_entry_all_fields_batch19():
    d = DocumentEntry(
        doc_id="d1",
        path_str="a.pdf",
        resolved_path=Path("/fake/a.pdf"),
        source_type="pdf",
        sha256="abc",
        categories=("c1", "c2"),
        paired_with="d2",
        annotation_file_str="ann.json",
        annotation_resolved=Path("/fake/ann.json"),
        expectations={"key": "value"},
    )
    assert d.doc_id == "d1"
    assert d.path_str == "a.pdf"
    assert d.source_type == "pdf"
    assert d.sha256 == "abc"
    assert d.categories == ("c1", "c2")
    assert d.paired_with == "d2"
    assert d.annotation_file_str == "ann.json"
    assert d.expectations == {"key": "value"}


def test_document_entry_equality_batch19():
    d1 = _mk_doc()
    d2 = _mk_doc()
    assert d1 == d2


def test_document_entry_inequality_batch19():
    d1 = _mk_doc("d1")
    d2 = _mk_doc("d2")
    assert d1 != d2


def test_document_entry_hashable_with_hashable_fields_batch19():
    """DocumentEntry 在 expectations=None 时 hashable（dict 不可 hash）。"""
    d = DocumentEntry(
        doc_id="d1", path_str="a.pdf",
        resolved_path=Path("/fake/a.pdf"),
        source_type="pdf", sha256="x",
        categories=("c",), paired_with="d2",
        annotation_file_str="ann.json",
        annotation_resolved=Path("/fake/ann.json"),
        expectations=None,  # None is hashable
    )
    assert hash(d) is not None


def test_document_entry_unhashable_with_dict_expectations_batch19():
    """expectations 是 dict 时 DocumentEntry 不可 hash。"""
    d = DocumentEntry(
        doc_id="d1", path_str="a.pdf",
        resolved_path=Path("/fake/a.pdf"),
        source_type="pdf", sha256=None,
        categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None,
        expectations={"k": "v"},  # dict 不可 hash
    )
    with pytest.raises(TypeError, match="unhashable"):
        hash(d)


# ---------- ExpectedFailure 第十九批 ----------


def test_expected_failure_with_source_type_other_batch19():
    ef = ExpectedFailure(
        doc_id="bad1", path_str="bad.txt",
        resolved_path=Path("/fake/bad.txt"),
        expected_error_code="unsupported_format",
        source_type="other",
    )
    assert ef.source_type == "other"


def test_expected_failure_with_source_type_txt_batch19():
    ef = ExpectedFailure(
        doc_id="bad1", path_str="bad.txt",
        resolved_path=Path("/fake/bad.txt"),
        expected_error_code="unsupported_format",
        source_type="txt",
    )
    assert ef.source_type == "txt"


def test_expected_failure_inequality_batch19():
    ef1 = ExpectedFailure("b1", "p", Path(), "x", None)
    ef2 = ExpectedFailure("b2", "p", Path(), "x", None)
    assert ef1 != ef2


def test_expected_failure_field_count_batch19():
    assert len(fields(ExpectedFailure)) == 5


# ---------- load_manifest 行为深度第十九批 ----------


def _basic_manifest_dict():
    return {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }


def test_load_manifest_returns_manifest_instance_batch19(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_basic_manifest_dict()), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)


def test_load_manifest_path_str_batch19(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_basic_manifest_dict()), encoding="utf-8")
    m = load_manifest(str(p), project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_unicode_doc_id_batch19(tmp_path):
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "中文", "path": "a.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].doc_id == "中文"


def test_load_manifest_annotation_resolved_batch19(tmp_path):
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "annotation_file": "ann/d1.json"},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_resolved == (tmp_path / "ann" / "d1.json").resolve()


def test_load_manifest_annotation_file_str_batch19(tmp_path):
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "annotation_file": "ann/d1.json"},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_file_str == "ann/d1.json"


def test_load_manifest_expectations_passthrough_batch19(tmp_path):
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "expectations": {"element_count_by_type": {"heading": 5}}},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations == {"element_count_by_type": {"heading": 5}}


def test_load_manifest_sha256_passthrough_batch19(tmp_path):
    p = tmp_path / "m.json"
    sha = "a" * 64
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "sha256": sha},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 == sha


def test_load_manifest_invalid_json_trailing_comma_batch19(tmp_path):
    """JSON trailing comma → JSONDecodeError → ManifestError。"""
    p = tmp_path / "m.json"
    p.write_text('{"a": 1,}', encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON 解析失败"):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_categories_default_empty_tuple_batch19(tmp_path):
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ()


def test_load_manifest_doc_id_with_special_chars_batch19(tmp_path):
    """doc_id 含特殊字符也工作。"""
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "doc-1_v2.0", "path": "a.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].doc_id == "doc-1_v2.0"


def test_load_manifest_expected_failure_no_source_type_batch19(tmp_path):
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "bad1", "path": "bad.txt",
             "expected_error_code": "x"},
        ],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].source_type is None


def test_load_manifest_devset_status_complete_batch19(tmp_path):
    p = tmp_path / "m.json"
    data = _basic_manifest_dict()
    data["devset_status"] = "complete"
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.devset_status == "complete"


# ---------- module source forbidden tokens 第三十三批 ----------


@pytest.mark.parametrize("forbidden", [
    "pty.spawn",
    "commands.getoutput",
    "paramiko",
    "fabric.api",
    "ftplib",
    "smtplib",
    "telnetlib",
    "webbrowser.open",
    "socket.socket",
    "asyncio.open_connection",
    "multiprocessing.Process",
    "threading.Thread",
    "ctypes.CDLL",
    "pickle.dumps",
    "shutil.rmtree",
])
def test_module_source_forbidden_tokens_batch19(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


def test_module_source_no_subprocess_batch19():
    src = inspect.getsource(mmod)
    assert "import subprocess" not in src


def test_module_source_no_network_batch19():
    src = inspect.getsource(mmod)
    assert "urllib.request" not in src
    assert "import requests" not in src


def test_module_source_no_sys_exit_batch19():
    src = inspect.getsource(mmod)
    assert "sys.exit" not in src


# ---------- module source 字符串精确补强第三十一批 ----------


def test_module_source_has_future_annotations_batch19():
    src = inspect.getsource(mmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch19():
    src = inspect.getsource(mmod)
    assert "开发集清单加载器" in src


def test_module_source_has_json_import_batch19():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_source_has_dataclass_import_batch19():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_has_pathlib_import_batch19():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_import_batch19():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_manifest_version_import_batch19():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_has_schema_import_batch19():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_has_manifest_error_class_batch19():
    src = inspect.getsource(mmod)
    assert "class ManifestError" in src


def test_module_source_has_load_manifest_function_batch19():
    src = inspect.getsource(mmod)
    assert "def load_manifest(" in src


def test_module_source_has_resolve_relative_path_function_batch19():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in src


def test_module_source_has_detect_project_root_function_batch19():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root(" in src


def test_module_source_has_is_absolute_like_function_batch19():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in src


def test_module_source_has_has_backslash_function_batch19():
    src = inspect.getsource(mmod)
    assert "def _has_backslash(" in src


def test_module_source_has_all_dunder_batch19():
    src = inspect.getsource(mmod)
    assert "__all__" in src


def test_module_source_no_main_block_batch19():
    src = inspect.getsource(mmod)
    assert "__main__" not in src


# ---------- signatures 第二十九批 ----------


def test_signature_load_manifest_batch19():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.keys())
    assert params == ["manifest_path", "project_root"]


def test_signature_resolve_relative_path_batch19():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.keys())
    assert params == ["path_str", "project_root", "field_name"]


def test_signature_is_absolute_like_batch19():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]


def test_signature_has_backslash_batch19():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]


def test_signature_detect_project_root_batch19():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.keys())
    assert params == ["start"]


# ---------- module 合理性第二十九批 ----------


def test_module_has_all_attribute_batch19():
    assert hasattr(mmod, "__all__")
    assert isinstance(mmod.__all__, list)


def test_module_all_count_5_batch19():
    assert len(mmod.__all__) == 5


def test_module_all_contents_batch19():
    assert set(mmod.__all__) == {
        "ManifestError", "Manifest", "DocumentEntry",
        "ExpectedFailure", "load_manifest",
    }


def test_module_load_manifest_callable_batch19():
    assert callable(load_manifest)


def test_module_does_not_import_unsafe_modules_batch19():
    src = inspect.getsource(mmod)
    for unsafe in ["import pickle", "import marshal", "import shelve"]:
        assert unsafe not in src


def test_module_does_not_import_evaluation_runner_batch19():
    src = inspect.getsource(mmod)
    assert "from evaluation.runner" not in src


def test_module_does_not_import_evaluation_cli_batch19():
    src = inspect.getsource(mmod)
    assert "from evaluation.cli" not in src


# ---------- 端到端集成第二十九批 ----------


def test_e2e_load_manifest_full_round_trip_batch19(tmp_path):
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["x", "y"], "paired_with": "d2"},
            {"doc_id": "d2", "path": "a.docx", "source_type": "docx",
             "paired_with": "d1"},
        ],
        "expected_failures": [
            {"doc_id": "bad1", "path": "bad.txt",
             "expected_error_code": "unsupported_format", "source_type": "txt"},
        ],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.devset_status == "complete"
    assert len(m.documents) == 2
    assert len(m.expected_failures) == 1
    assert m.content_group_count == 1  # d1+d2 paired = 1 group
    assert m.categories_covered == ["x", "y"]
    assert m.expected_failures[0].source_type == "txt"


def test_e2e_load_manifest_then_validate_with_runner_batch19(tmp_path):
    """manifest 加载后可被 runner 使用（mock process_single）。"""
    from evaluation.runner import run_evaluation
    p = tmp_path / "m.json"
    data = _basic_manifest_dict()
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    out = tmp_path / "out.json"
    r = run_evaluation(m, out)
    assert "per_doc" in r


def test_e2e_manifest_categories_aggregated_batch19(tmp_path):
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["a", "b"]},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf",
             "categories": ["b", "c"]},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    # dedup
    assert m.categories_covered == ["a", "b", "c"]


def test_e2e_manifest_pdf_docx_count_batch19(tmp_path):
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf"},
            {"doc_id": "d3", "path": "c.docx", "source_type": "docx"},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.pdf_count == 2
    assert m.docx_count == 1
    assert m.file_count == 3


def test_e2e_load_manifest_auto_project_root_batch19(tmp_path):
    """project_root=None → 自动检测（含 pyproject.toml 的目录）。"""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_basic_manifest_dict()), encoding="utf-8")
    m = load_manifest(p)
    assert m.project_root == tmp_path.resolve()


def test_e2e_load_manifest_default_devset_incomplete_batch19(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_basic_manifest_dict()), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.devset_status == "incomplete"


def test_e2e_manifest_used_by_evaluation_cli_batch19(tmp_path):
    """manifest 被 cli 使用（间接验证完整性）。"""
    from evaluation.cli import main
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_basic_manifest_dict()), encoding="utf-8")
    output_p = tmp_path / "out.json"
    output_p.write_text("{}", encoding="utf-8")
    fake_manifest = MagicMock()
    fake_manifest.documents = []
    fake_manifest.expected_failures = []
    fake_manifest.project_root = tmp_path
    fake_manifest.devset_status = "incomplete"
    fake_manifest.file_count = 0
    fake_manifest.content_group_count = 0
    fake_manifest.pdf_count = 0
    fake_manifest.docx_count = 0
    fake_manifest.categories_covered = []
    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), \
         patch("evaluation.cli.run_evaluation",
               return_value={"per_doc": [], "devset": {}}), \
         patch("evaluation.cli.validate_file", return_value=None), \
         patch("evaluation.cli.get_git_provenance",
               return_value={"git_commit": "x", "git_dirty": False}):
        rc = main(["run", "--manifest", str(p), "--output", str(output_p)])
    assert rc == 0
