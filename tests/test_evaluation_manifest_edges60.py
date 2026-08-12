"""evaluation/manifest.py 第六十轮 edges 测试（Round 551）。

补强 edges59 未触及的角度（第三十三批）。
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


# ---------- _is_absolute_like 第三十三批


def test_is_absolute_like_single_letter_no_colon_batch33():
    assert _is_absolute_like("a") is False


def test_is_absolute_like_digit_drive_batch33():
    """1:\\ 不是有效盘符（必须 alpha）。"""
    assert _is_absolute_like("1:\\foo") is False


def test_is_absolute_like_colon_no_slash_batch33():
    """'C:foo' 没有 \\ 或 / 不算绝对路径。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_just_slash_batch33():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_just_backslash_batch33():
    """单独反斜杠不算（POSIX 才用 / 作绝对路径前缀）。"""
    assert _is_absolute_like("\\") is False


def test_is_absolute_like_lowercase_drive_batch33():
    assert _is_absolute_like("c:/foo") is True


def test_is_absolute_like_lowercase_drive_backslash_batch33():
    assert _is_absolute_like("c:\\foo") is True


def test_is_absolute_like_z_drive_batch33():
    assert _is_absolute_like("Z:/bar") is True


def test_is_absolute_like_relative_posix_batch33():
    assert _is_absolute_like("foo/bar") is False


def test_is_absolute_like_relative_with_dot_batch33():
    assert _is_absolute_like("./foo") is False


# ---------- _has_backslash 第三十三批


def test_has_backslash_empty_batch33():
    assert _has_backslash("") is False


def test_has_backslash_no_backslash_batch33():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_single_batch33():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_only_batch33():
    assert _has_backslash("\\") is True


def test_has_backslash_multiple_batch33():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_mixed_batch33():
    assert _has_backslash("a/b\\c") is True


# ---------- DocumentEntry 第三十三批


def test_document_entry_field_count_batch33():
    """DocumentEntry 共 10 个字段。"""
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_field_names_batch33():
    names = [f.name for f in fields(DocumentEntry)]
    assert "doc_id" in names
    assert "path_str" in names
    assert "resolved_path" in names
    assert "source_type" in names
    assert "sha256" in names
    assert "categories" in names
    assert "paired_with" in names
    assert "annotation_file_str" in names
    assert "annotation_resolved" in names
    assert "expectations" in names


def test_document_entry_frozen_batch33():
    de = DocumentEntry(
        doc_id="d1",
        path_str="a.pdf",
        resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        de.doc_id = "x"


def test_document_entry_categories_default_empty_batch33():
    de = DocumentEntry(
        doc_id="d1",
        path_str="a.pdf",
        resolved_path=Path("/tmp/a.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    assert de.categories == ()


def test_document_entry_equality_batch33():
    """frozen dataclass 默认生成 __eq__。"""
    de1 = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/x/a.pdf"),
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=Path("/x/a.pdf"),
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    assert de1 == de2


# ---------- ExpectedFailure 第三十三批


def test_expected_failure_field_count_batch33():
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_field_names_batch33():
    names = [f.name for f in fields(ExpectedFailure)]
    assert names == ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]


def test_expected_failure_frozen_batch33():
    ef = ExpectedFailure(
        doc_id="d1",
        path_str="bad.pdf",
        resolved_path=Path("/x/bad.pdf"),
        expected_error_code="E_PARSE",
        source_type=None,
    )
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "x"


def test_expected_failure_source_type_optional_batch33():
    ef = ExpectedFailure(
        doc_id="d1",
        path_str="bad.pdf",
        resolved_path=Path("/x/bad.pdf"),
        expected_error_code="E_PARSE",
        source_type=None,
    )
    assert ef.source_type is None


def test_expected_failure_equality_batch33():
    ef1 = ExpectedFailure("d1", "p", Path("/x/p"), "E", None)
    ef2 = ExpectedFailure("d1", "p", Path("/x/p"), "E", None)
    assert ef1 == ef2


# ---------- Manifest 第三十三批


def test_manifest_field_count_batch33():
    assert len(fields(Manifest)) == 5


def test_manifest_field_names_batch33():
    names = [f.name for f in fields(Manifest)]
    assert names == ["manifest_version", "devset_status", "documents", "expected_failures", "project_root"]


def test_manifest_frozen_batch33():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/x"),
    )
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"


def test_manifest_file_count_zero_batch33():
    m = Manifest("1.0", "incomplete", (), (), Path("/x"))
    assert m.file_count == 0


def test_manifest_file_count_three_batch33():
    docs = tuple(
        DocumentEntry(
            doc_id=f"d{i}", path_str=f"a{i}.pdf",
            resolved_path=Path(f"/x/a{i}.pdf"),
            source_type="pdf", sha256=None, categories=(),
            paired_with=None, annotation_file_str=None,
            annotation_resolved=None, expectations=None,
        )
        for i in range(3)
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.file_count == 3


def test_manifest_pdf_count_zero_when_no_pdf_batch33():
    docs = (
        DocumentEntry("d1", "a.docx", Path("/x/a.docx"), "docx", None, (),
                      None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.pdf_count == 0
    assert m.docx_count == 1


def test_manifest_categories_covered_sorted_batch33():
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None,
                      ("zeta", "alpha"), None, None, None, None),
        DocumentEntry("d2", "b.pdf", Path("/x/b.pdf"), "pdf", None,
                      ("alpha", "beta"), None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.categories_covered == ["alpha", "beta", "zeta"]


def test_manifest_categories_covered_empty_batch33():
    m = Manifest("1.0", "incomplete", (), (), Path("/x"))
    assert m.categories_covered == []


def test_manifest_content_group_count_unpaired_batch33():
    """两个未配对的文档 = 2 组。"""
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                      None, None, None, None),
        DocumentEntry("d2", "b.pdf", Path("/x/b.pdf"), "pdf", None, (),
                      None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.content_group_count == 2


def test_manifest_content_group_count_one_pair_batch33():
    """一对配对文档 = 1 组。"""
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                      "d2", None, None, None),
        DocumentEntry("d2", "b.docx", Path("/x/b.docx"), "docx", None, (),
                      "d1", None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.content_group_count == 1


def test_manifest_content_group_count_mixed_batch33():
    """1 对 + 1 单 = 2 组。"""
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


def test_manifest_content_group_count_unidirectional_batch33():
    """单向 paired 也算 1 组。"""
    docs = (
        DocumentEntry("d1", "a.pdf", Path("/x/a.pdf"), "pdf", None, (),
                      "d2", None, None, None),
        DocumentEntry("d2", "b.docx", Path("/x/b.docx"), "docx", None, (),
                      None, None, None, None),
    )
    m = Manifest("1.0", "incomplete", docs, (), Path("/x"))
    assert m.content_group_count == 1


# ---------- _resolve_relative_path 第三十三批


def test_resolve_relative_path_normal_batch33(tmp_path):
    p = _resolve_relative_path("a/b.pdf", tmp_path, "test")
    assert p == (tmp_path / "a" / "b.pdf").resolve()


def test_resolve_relative_path_empty_raises_batch33(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("", tmp_path, "field_x")
    assert "field_x" in str(exc.value)
    assert "为空" in str(exc.value)


def test_resolve_relative_path_absolute_posix_raises_batch33(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("/etc/passwd", tmp_path, "f")
    assert "绝对路径" in str(exc.value)


def test_resolve_relative_path_absolute_windows_raises_batch33(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("C:/foo", tmp_path, "f")
    assert "绝对路径" in str(exc.value)


def test_resolve_relative_path_backslash_raises_batch33(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("a\\b.pdf", tmp_path, "f")
    assert "反斜杠" in str(exc.value)


def test_resolve_relative_path_escape_raises_batch33(tmp_path):
    """../../../etc/passwd 越界 → 失败。"""
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("../../etc/passwd", tmp_path, "f")
    assert "项目根目录之外" in str(exc.value)


def test_resolve_relative_path_nested_inside_batch33(tmp_path):
    p = _resolve_relative_path("samples/private/x.pdf", tmp_path, "f")
    assert p == (tmp_path / "samples" / "private" / "x.pdf").resolve()


def test_resolve_relative_path_dot_relative_batch33(tmp_path):
    """./foo 解析为 tmp_path/foo。"""
    p = _resolve_relative_path("./foo", tmp_path, "f")
    assert p == (tmp_path / "foo").resolve()


# ---------- load_manifest 第三十三批


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_nonexistent_raises_batch33(tmp_path):
    with pytest.raises(ManifestError) as exc:
        load_manifest(tmp_path / "missing.json")
    assert "不存在" in str(exc.value)


def test_load_manifest_invalid_json_raises_batch33(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("not json {", encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p)
    assert "JSON 解析失败" in str(exc.value)


def test_load_manifest_schema_invalid_raises_batch33(tmp_path):
    """schema 不通过 → EvalSchemaError（不是 ManifestError）。"""
    from evaluation.schema import EvalSchemaError
    p = _write_manifest(tmp_path, {"manifest_version": "1.0"})  # 缺 devset_status
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_version_mismatch_raises_batch33(tmp_path):
    """schema 通过但 version 不对 → ManifestError。"""
    p = _write_manifest(tmp_path, {
        "manifest_version": "999.0",  # enum 不允许，所以会 EvalSchemaError
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    from evaluation.schema import EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(p)


def test_load_manifest_empty_documents_batch33(tmp_path):
    """合法 manifest，空 documents 列表。"""
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents == ()
    assert m.expected_failures == ()
    assert m.file_count == 0


def test_load_manifest_one_document_no_optionals_batch33(tmp_path):
    """documents 至少需要 path/doc_id/source_type；其他可选。"""
    target = tmp_path / "a.pdf"
    target.write_text("x", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.documents) == 1
    d = m.documents[0]
    assert d.doc_id == "d1"
    assert d.sha256 is None
    assert d.categories == ()
    assert d.paired_with is None
    assert d.annotation_file_str is None
    assert d.annotation_resolved is None
    assert d.expectations is None


def test_load_manifest_with_annotation_file_batch33(tmp_path):
    target = tmp_path / "a.pdf"
    target.write_text("x", encoding="utf-8")
    ann = tmp_path / "ann.json"
    ann.write_text("{}", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
                "annotation_file": "ann.json",
            }
        ],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_resolved is not None
    assert m.documents[0].annotation_resolved == ann.resolve()


def test_load_manifest_expected_failure_no_source_type_batch33(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_text("y", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "bad1", "path": "bad.pdf", "expected_error_code": "E_PARSE"}
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    ef = m.expected_failures[0]
    assert ef.source_type is None
    assert ef.expected_error_code == "E_PARSE"


def test_load_manifest_expected_failure_with_source_type_batch33(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_text("y", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "bad1", "path": "bad.pdf",
                "expected_error_code": "E_PARSE", "source_type": "pdf",
            }
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].source_type == "pdf"


def test_load_manifest_returns_manifest_instance_batch33(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)
    assert m.manifest_version == MANIFEST_VERSION
    assert m.devset_status == "incomplete"


def test_load_manifest_str_path_batch33(tmp_path):
    """manifest_path 接受 str。"""
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(str(p), project_root=str(tmp_path))
    assert isinstance(m, Manifest)


def test_load_manifest_str_project_root_batch33(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


# ---------- _detect_project_root 第三十三批


def test_detect_project_root_from_file_batch33(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    f = tmp_path / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    assert _detect_project_root(f) == tmp_path.resolve()


def test_detect_project_root_from_dir_batch33(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    assert _detect_project_root(tmp_path) == tmp_path.resolve()


def test_detect_project_root_walks_up_batch33(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert _detect_project_root(sub) == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_cur_batch33(tmp_path):
    """找不到 pyproject.toml → 返回 cur（向上到 root 都没找到）。"""
    # tmp_path 是 pytest 提供的，没有 pyproject.toml
    sub = tmp_path / "deep"
    sub.mkdir()
    result = _detect_project_root(sub)
    # 应该返回某个祖先目录（具体到哪一级取决于文件系统）
    # 至少不是 None
    assert result is not None
    assert isinstance(result, Path)


# ---------- module source forbidden tokens 第五十一批


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
    "pty",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch33(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第四十七批


def test_module_source_contains_docstring_batch33():
    src = inspect.getsource(mmod)
    assert "开发集清单加载器" in src


def test_module_source_contains_future_annotations_batch33():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_json_import_batch33():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_source_contains_dataclass_import_batch33():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_contains_pathlib_import_batch33():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_import_batch33():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_contains_manifest_version_import_batch33():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_contains_schema_import_batch33():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_contains_manifest_error_class_batch33():
    src = inspect.getsource(mmod)
    assert "class ManifestError(Exception):" in src


def test_module_source_contains_document_entry_class_batch33():
    src = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in src
    assert "class DocumentEntry:" in src


def test_module_source_contains_expected_failure_class_batch33():
    src = inspect.getsource(mmod)
    assert "class ExpectedFailure:" in src


def test_module_source_contains_manifest_class_batch33():
    src = inspect.getsource(mmod)
    assert "class Manifest:" in src


def test_module_source_contains_load_manifest_func_batch33():
    src = inspect.getsource(mmod)
    assert "def load_manifest(" in src


def test_module_source_contains_resolve_relative_path_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in src


def test_module_source_contains_detect_project_root_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root(" in src


def test_module_source_contains_is_absolute_like_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in src


def test_module_source_contains_has_backslash_func_batch33():
    src = inspect.getsource(mmod)
    assert "def _has_backslash(" in src


def test_module_source_contains_file_count_property_batch33():
    src = inspect.getsource(mmod)
    assert "def file_count(" in src


def test_module_source_contains_pdf_count_property_batch33():
    src = inspect.getsource(mmod)
    assert "def pdf_count(" in src


def test_module_source_contains_docx_count_property_batch33():
    src = inspect.getsource(mmod)
    assert "def docx_count(" in src


def test_module_source_contains_content_group_count_property_batch33():
    src = inspect.getsource(mmod)
    assert "def content_group_count(" in src


def test_module_source_contains_categories_covered_property_batch33():
    src = inspect.getsource(mmod)
    assert "def categories_covered(" in src


def test_module_source_contains_validate_call_batch33():
    src = inspect.getsource(mmod)
    assert 'validate(' in src


def test_module_source_contains_all_exports_batch33():
    src = inspect.getsource(mmod)
    assert "__all__" in src
    assert '"ManifestError"' in src
    assert '"Manifest"' in src
    assert '"DocumentEntry"' in src
    assert '"ExpectedFailure"' in src
    assert '"load_manifest"' in src


# ---------- signatures 第四十七批


def test_signature_manifest_error_no_params_batch33():
    """ManifestError 继承自 Exception，构造时接受可选 message。"""
    e = ManifestError("msg")
    assert str(e) == "msg"
    e2 = ManifestError()
    assert str(e2) == ""


def test_signature_is_absolute_like_one_param_batch33():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]


def test_signature_has_backslash_one_param_batch33():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]


def test_signature_resolve_relative_path_three_params_batch33():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.keys())
    assert params == ["path_str", "project_root", "field_name"]


def test_signature_load_manifest_params_batch33():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.keys())
    assert params == ["manifest_path", "project_root"]
    assert sig.parameters["project_root"].default is None


def test_signature_detect_project_root_one_param_batch33():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.keys())
    assert params == ["start"]


def test_signature_load_manifest_return_annotation_batch33():
    sig = inspect.signature(load_manifest)
    assert sig.return_annotation == "Manifest"


# ---------- module 合理性第四十七批


def test_module_has_future_annotations_batch33():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch33():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_has_manifest_error_class_batch33():
    assert hasattr(mmod, "ManifestError")
    assert issubclass(mmod.ManifestError, Exception)


def test_module_has_load_manifest_func_batch33():
    assert callable(mmod.load_manifest)


def test_module_has_document_entry_class_batch33():
    assert hasattr(mmod, "DocumentEntry")


def test_module_has_expected_failure_class_batch33():
    assert hasattr(mmod, "ExpectedFailure")


def test_module_has_manifest_class_batch33():
    assert hasattr(mmod, "Manifest")


def test_module_has_all_batch33():
    assert hasattr(mmod, "__all__")
    assert "ManifestError" in mmod.__all__
    assert "Manifest" in mmod.__all__
    assert "DocumentEntry" in mmod.__all__
    assert "ExpectedFailure" in mmod.__all__
    assert "load_manifest" in mmod.__all__


# ---------- 端到端集成第四十七批


def test_e2e_manifest_full_documents_batch33(tmp_path):
    """完整 manifest：多个 documents + expected_failures + categories + paired。"""
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
            {
                "doc_id": "d_pdf", "path": "a.pdf", "source_type": "pdf",
                "categories": ["essay"], "paired_with": "d_docx",
                "annotation_file": "ann.json",
                "sha256": "a" * 64,
                "expectations": {"element_count_by_type": {"paragraph": 5}},
            },
            {
                "doc_id": "d_docx", "path": "b.docx", "source_type": "docx",
                "categories": ["essay"], "paired_with": "d_pdf",
            },
        ],
        "expected_failures": [
            {"doc_id": "bad1", "path": "bad.pdf", "expected_error_code": "E_PARSE"},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.content_group_count == 1
    assert m.categories_covered == ["essay"]
    assert len(m.expected_failures) == 1
    assert m.documents[0].sha256 == "a" * 64
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}
    assert m.documents[0].annotation_resolved == ann.resolve()


def test_e2e_manifest_idempotent_batch33(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1 == m2


def test_e2e_manifest_default_project_root_batch33(tmp_path):
    """project_root=None → 从 manifest_path 向上找 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    })
    m = load_manifest(p)  # 不传 project_root
    assert m.project_root == tmp_path.resolve()


def test_e2e_manifest_invalid_path_in_documents_batch33(tmp_path):
    """document path 是绝对路径 → ManifestError。"""
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "/etc/passwd", "source_type": "pdf"}
        ],
        "expected_failures": [],
    })
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "绝对路径" in str(exc.value)


def test_e2e_manifest_invalid_path_in_expected_failures_batch33(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "bad1", "path": "/etc/passwd", "expected_error_code": "E"}
        ],
    })
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)


def test_e2e_manifest_field_name_in_error_batch33(tmp_path):
    """错误信息中包含 field_name。"""
    p = _write_manifest(tmp_path, {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "doc_xyz", "path": "/etc/passwd", "source_type": "pdf"}
        ],
        "expected_failures": [],
    })
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    msg = str(exc.value)
    assert "doc_xyz" in msg


def test_e2e_manifest_json_decode_error_message_batch33(tmp_path):
    """JSON 解析错误信息可读。"""
    p = tmp_path / "manifest.json"
    p.write_text("{broken", encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p)
    assert "JSON 解析失败" in str(exc.value)
