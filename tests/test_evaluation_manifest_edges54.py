"""evaluation/manifest.py 第五十四轮 edges 测试（Round 510）。

补强 edges53 未触及的角度（第二十七批）：
- _is_absolute_like 第二十七批：空 / 单字符 / 双字符 / 盘符小写 / 盘符大写 / Windows UNC / 多斜杠 / 数字盘符
- _has_backslash 第二十七批：纯反斜杠 / 混合 / 双反斜杠 / 末尾反斜杠
- DocumentEntry 第二十七批：frozen / hashable / 字段顺序 / 默认值 None / tuple 字段
- ExpectedFailure 第二十七批：frozen / hashable / source_type 默认 None
- Manifest 第二十七批：file_count 等于 0 / pdf_count == file_count / docx_count == 0 / categories_covered 排序 / content_group_count 含 paired_with 链
- _resolve_relative_path 第二十七批：空 / 绝对 / 反斜杠 / 项目根外 / 子目录合法 / ./ 前缀
- load_manifest 第二十七批：str path / Path / project_root 显式 / project_root 自动检测
- _detect_project_root 第二十七批：从文件起 / 从目录起 / 无 pyproject fallback
- module source forbidden tokens 第四十四批
- module source 字符串精确补强第四十批
- signatures 第四十批
- module 合理性第四十批
- 端到端集成第四十批
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError
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


# ---------- _is_absolute_like 第二十七批 ----------


def test_is_absolute_like_empty_string_batch27():
    assert _is_absolute_like("") is False


def test_is_absolute_like_single_char_batch27():
    assert _is_absolute_like("a") is False


def test_is_absolute_like_two_chars_batch27():
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_posix_absolute_batch27():
    assert _is_absolute_like("/etc/passwd") is True


def test_is_absolute_like_windows_drive_upper_batch27():
    assert _is_absolute_like("C:\\foo") is True


def test_is_absolute_like_windows_drive_lower_batch27():
    assert _is_absolute_like("c:/foo") is True


def test_is_absolute_like_windows_drive_forward_slash_batch27():
    assert _is_absolute_like("D:/bar") is True


def test_is_absolute_like_windows_drive_no_slash_batch27():
    """C:foo 不算绝对（没有分隔符）。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_number_drive_batch27():
    """数字开头的盘符不算（要求字母）。"""
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_relative_path_batch27():
    assert _is_absolute_like("samples/foo.pdf") is False


def test_is_absolute_like_double_slash_batch27():
    assert _is_absolute_like("//server/share") is True


def test_is_absolute_like_dot_slash_batch27():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_underscore_drive_batch27():
    """下划线不是字母（isalpha() False）。"""
    assert _is_absolute_like("_:/foo") is False


# ---------- _has_backslash 第二十七批 ----------


def test_has_backslash_empty_batch27():
    assert _has_backslash("") is False


def test_has_backslash_single_batch27():
    assert _has_backslash("foo\\bar") is True


def test_has_backslash_double_batch27():
    assert _has_backslash("foo\\\\bar") is True


def test_has_backslash_trailing_batch27():
    assert _has_backslash("foo\\") is True


def test_has_backslash_only_batch27():
    assert _has_backslash("\\") is True


def test_has_backslash_none_batch27():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_no_slash_batch27():
    assert _has_backslash("foo") is False


# ---------- DocumentEntry 第二十七批 ----------


def _make_doc(**overrides) -> DocumentEntry:
    defaults = dict(
        doc_id="d1",
        path_str="samples/x.pdf",
        resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf",
        sha256="a" * 64,
        categories=("cat1",),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    defaults.update(overrides)
    return DocumentEntry(**defaults)


def test_document_entry_frozen_batch27():
    """DocumentEntry 是 frozen dataclass。"""
    d = _make_doc()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "modified"  # type: ignore[misc]


def test_document_entry_hashable_batch27():
    d = _make_doc()
    h = hash(d)
    assert isinstance(h, int)


def test_document_entry_field_order_batch27():
    """字段顺序固定（与 dataclass 定义一致）。"""
    import dataclasses
    fields = [f.name for f in dataclasses.fields(DocumentEntry)]
    assert fields == [
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
    ]


def test_document_entry_sha256_default_none_batch27():
    """sha256 默认可以是 None。"""
    d = _make_doc(sha256=None)
    assert d.sha256 is None


def test_document_entry_categories_tuple_batch27():
    d = _make_doc(categories=("a", "b", "c"))
    assert isinstance(d.categories, tuple)
    assert d.categories == ("a", "b", "c")


def test_document_entry_categories_empty_tuple_batch27():
    d = _make_doc(categories=())
    assert d.categories == ()


def test_document_entry_equality_batch27():
    d1 = _make_doc()
    d2 = _make_doc()
    assert d1 == d2


def test_document_entry_inequality_batch27():
    d1 = _make_doc(doc_id="d1")
    d2 = _make_doc(doc_id="d2")
    assert d1 != d2


def test_document_entry_repr_has_class_name_batch27():
    d = _make_doc()
    assert "DocumentEntry" in repr(d)


# ---------- ExpectedFailure 第二十七批 ----------


def _make_ef(**overrides) -> ExpectedFailure:
    defaults = dict(
        doc_id="ef1",
        path_str="bad/corrupt.pdf",
        resolved_path=Path("/tmp/corrupt.pdf"),
        expected_error_code="unsupported_format",
        source_type="pdf",
    )
    defaults.update(overrides)
    return ExpectedFailure(**defaults)


def test_expected_failure_frozen_batch27():
    ef = _make_ef()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "modified"  # type: ignore[misc]


def test_expected_failure_hashable_batch27():
    ef = _make_ef()
    h = hash(ef)
    assert isinstance(h, int)


def test_expected_failure_source_type_none_batch27():
    ef = _make_ef(source_type=None)
    assert ef.source_type is None


def test_expected_failure_equality_batch27():
    ef1 = _make_ef()
    ef2 = _make_ef()
    assert ef1 == ef2


def test_expected_failure_field_order_batch27():
    import dataclasses
    fields = [f.name for f in dataclasses.fields(ExpectedFailure)]
    assert fields == [
        "doc_id",
        "path_str",
        "resolved_path",
        "expected_error_code",
        "source_type",
    ]


# ---------- Manifest 第二十七批 ----------


def _make_manifest(**overrides) -> Manifest:
    defaults = dict(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    defaults.update(overrides)
    return Manifest(**defaults)


def test_manifest_file_count_zero_batch27():
    m = _make_manifest(documents=())
    assert m.file_count == 0


def test_manifest_file_count_multiple_batch27():
    docs = (_make_doc(doc_id="d1"), _make_doc(doc_id="d2"), _make_doc(doc_id="d3"))
    m = _make_manifest(documents=docs)
    assert m.file_count == 3


def test_manifest_pdf_count_zero_when_all_docx_batch27():
    docs = (_make_doc(source_type="docx"),)
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 0


def test_manifest_pdf_count_all_batch27():
    docs = (_make_doc(source_type="pdf"), _make_doc(source_type="pdf"))
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 2


def test_manifest_docx_count_zero_when_all_pdf_batch27():
    docs = (_make_doc(source_type="pdf"),)
    m = _make_manifest(documents=docs)
    assert m.docx_count == 0


def test_manifest_docx_count_all_batch27():
    docs = (_make_doc(source_type="docx"), _make_doc(source_type="docx"))
    m = _make_manifest(documents=docs)
    assert m.docx_count == 2


def test_manifest_categories_covered_sorted_batch27():
    docs = (
        _make_doc(categories=("zoo",)),
        _make_doc(categories=("alpha",)),
        _make_doc(categories=("mid",)),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["alpha", "mid", "zoo"]


def test_manifest_categories_covered_dedupe_batch27():
    docs = (
        _make_doc(categories=("a", "b")),
        _make_doc(categories=("b", "c")),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_categories_covered_empty_batch27():
    m = _make_manifest(documents=())
    assert m.categories_covered == []


def test_manifest_content_group_count_unpaired_batch27():
    docs = (_make_doc(doc_id="d1"), _make_doc(doc_id="d2"))
    m = _make_manifest(documents=docs)
    # 两个独立文档，2 组
    assert m.content_group_count == 2


def test_manifest_content_group_count_one_pair_batch27():
    docs = (
        _make_doc(doc_id="d1", paired_with="d2"),
        _make_doc(doc_id="d2", paired_with="d1"),
    )
    m = _make_manifest(documents=docs)
    # 一对算 1 组
    assert m.content_group_count == 1


def test_manifest_frozen_batch27():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


# ---------- _resolve_relative_path 第二十七批 ----------


def test_resolve_relative_path_empty_batch27(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("", tmp_path, "test")


def test_resolve_relative_path_absolute_posix_batch27(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("/etc/passwd", tmp_path, "test")


def test_resolve_relative_path_absolute_windows_batch27(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("C:\\foo", tmp_path, "test")


def test_resolve_relative_path_backslash_batch27(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("foo\\bar", tmp_path, "test")


def test_resolve_relative_path_outside_root_batch27(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("../outside", tmp_path, "test")


def test_resolve_relative_path_valid_batch27(tmp_path):
    """合法相对路径 → 返回 resolved Path。"""
    result = _resolve_relative_path("subdir/file.pdf", tmp_path, "test")
    assert isinstance(result, Path)
    assert result.is_absolute()


def test_resolve_relative_path_nested_batch27(tmp_path):
    """多层嵌套子目录合法。"""
    result = _resolve_relative_path("a/b/c/d.pdf", tmp_path, "test")
    assert isinstance(result, Path)


def test_resolve_relative_path_dot_slash_batch27(tmp_path):
    """./ 前缀合法（不视为绝对）。"""
    result = _resolve_relative_path("./file.pdf", tmp_path, "test")
    assert isinstance(result, Path)


def test_resolve_relative_path_error_message_contains_field_name_batch27(tmp_path):
    """错误消息含 field_name。"""
    try:
        _resolve_relative_path("/etc/passwd", tmp_path, "MY_FIELD")
    except ManifestError as e:
        assert "MY_FIELD" in str(e)
        return
    pytest.fail("Expected ManifestError")


def test_resolve_relative_path_error_message_contains_path_str_batch27(tmp_path):
    """错误消息含 path_str。"""
    try:
        _resolve_relative_path("/etc/passwd", tmp_path, "f")
    except ManifestError as e:
        assert "/etc/passwd" in str(e)
        return
    pytest.fail("Expected ManifestError")


# ---------- load_manifest 第二十七批 ----------


def _make_manifest_file(tmp_path: Path, documents=None, expected_failures=None) -> Path:
    """生成合法 manifest 文件。"""
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": documents if documents is not None else [],
        "expected_failures": expected_failures if expected_failures is not None else [],
    }
    # 确保项目根
    (tmp_path / "pyproject.toml").write_text("# test", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_str_path_batch27(tmp_path):
    """str path 接受。"""
    p = _make_manifest_file(tmp_path)
    m = load_manifest(str(p))
    assert m.manifest_version == MANIFEST_VERSION


def test_load_manifest_path_obj_batch27(tmp_path):
    p = _make_manifest_file(tmp_path)
    m = load_manifest(p)
    assert m.manifest_version == MANIFEST_VERSION


def test_load_manifest_project_root_explicit_batch27(tmp_path):
    p = _make_manifest_file(tmp_path)
    m = load_manifest(p, project_root=tmp_path)
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_auto_detect_project_root_batch27(tmp_path):
    p = _make_manifest_file(tmp_path)
    m = load_manifest(p)
    # 自动检测：找到 pyproject.toml
    assert (m.project_root / "pyproject.toml").is_file()


def test_load_manifest_nonexistent_raises_batch27(tmp_path):
    with pytest.raises(ManifestError):
        load_manifest(tmp_path / "nope.json")


def test_load_manifest_bad_json_raises_batch27(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_load_manifest_with_one_document_batch27(tmp_path):
    p = _make_manifest_file(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
            }
        ],
    )
    m = load_manifest(p)
    assert m.file_count == 1
    assert m.documents[0].doc_id == "d1"


def test_load_manifest_with_categories_batch27(tmp_path):
    p = _make_manifest_file(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "categories": ["c1", "c2"],
            }
        ],
    )
    m = load_manifest(p)
    assert m.documents[0].categories == ("c1", "c2")


def test_load_manifest_with_expected_failure_batch27(tmp_path):
    p = _make_manifest_file(
        tmp_path,
        expected_failures=[
            {
                "doc_id": "bad1",
                "path": "bad/corrupt.pdf",
                "expected_error_code": "unsupported_format",
                "source_type": "pdf",
            }
        ],
    )
    m = load_manifest(p)
    assert len(m.expected_failures) == 1
    assert m.expected_failures[0].doc_id == "bad1"


# ---------- _detect_project_root 第二十七批 ----------


def test_detect_project_root_from_file_batch27(tmp_path):
    """从文件 path 起向上找。"""
    (tmp_path / "pyproject.toml").write_text("#", encoding="utf-8")
    nested = tmp_path / "sub" / "deep"
    nested.mkdir(parents=True)
    f = nested / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    result = _detect_project_root(f)
    assert result == tmp_path.resolve()


def test_detect_project_root_from_dir_batch27(tmp_path):
    """从目录 path 起向上找。"""
    (tmp_path / "pyproject.toml").write_text("#", encoding="utf-8")
    nested = tmp_path / "sub"
    nested.mkdir()
    result = _detect_project_root(nested)
    assert result == tmp_path.resolve()


def test_detect_project_root_no_pyproject_fallback_batch27(tmp_path):
    """无 pyproject.toml → 返回 start（resolve 后）。"""
    nested = tmp_path / "sub"
    nested.mkdir()
    result = _detect_project_root(nested)
    assert result == nested.resolve()


def test_detect_project_root_finds_nearest_batch27(tmp_path):
    """找最近的 pyproject.toml（多级嵌套）。"""
    (tmp_path / "pyproject.toml").write_text("# outer", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "pyproject.toml").write_text("# inner", encoding="utf-8")
    deeper = nested / "c"
    deeper.mkdir()
    result = _detect_project_root(deeper)
    assert result == nested.resolve()


def test_detect_project_root_returns_path_batch27(tmp_path):
    (tmp_path / "pyproject.toml").write_text("#", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert isinstance(result, Path)


# ---------- module source forbidden tokens 第四十四批 ----------


def test_module_source_no_subprocess_batch27():
    src = inspect.getsource(mmod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch27():
    src = inspect.getsource(mmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch27():
    src = inspect.getsource(mmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch27():
    src = inspect.getsource(mmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch27():
    src = inspect.getsource(mmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch27():
    src = inspect.getsource(mmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch27():
    src = inspect.getsource(mmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch27():
    src = inspect.getsource(mmod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch27():
    """manifest 模块只读 JSON，不写。"""
    src = inspect.getsource(mmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch27():
    src = inspect.getsource(mmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch27():
    src = inspect.getsource(mmod)
    assert "requests" not in src


def test_module_source_no_unlink_batch27():
    src = inspect.getsource(mmod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十批 ----------


def test_module_source_contains_manifest_error_class_batch27():
    src = inspect.getsource(mmod)
    assert "class ManifestError" in src


def test_module_source_contains_is_absolute_like_batch27():
    src = inspect.getsource(mmod)
    assert "_is_absolute_like" in src


def test_module_source_contains_has_backslash_batch27():
    src = inspect.getsource(mmod)
    assert "_has_backslash" in src


def test_module_source_contains_resolve_relative_path_batch27():
    src = inspect.getsource(mmod)
    assert "_resolve_relative_path" in src


def test_module_source_contains_load_manifest_batch27():
    src = inspect.getsource(mmod)
    assert "def load_manifest" in src


def test_module_source_contains_detect_project_root_batch27():
    src = inspect.getsource(mmod)
    assert "_detect_project_root" in src


def test_module_source_contains_frozen_dataclass_batch27():
    src = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in src


def test_module_source_contains_manifest_version_check_batch27():
    """load_manifest 校验 manifest_version == MANIFEST_VERSION。"""
    src = inspect.getsource(mmod)
    assert "MANIFEST_VERSION" in src


def test_module_source_contains_no_absolute_path_constraint_batch27():
    src = inspect.getsource(mmod)
    assert "禁止绝对路径" in src


def test_module_source_contains_no_backslash_constraint_batch27():
    src = inspect.getsource(mmod)
    assert "禁止反斜杠" in src


def test_module_source_contains_validate_call_batch27():
    src = inspect.getsource(mmod)
    assert "validate(" in src
    assert "manifest.schema.json" in src


def test_module_source_contains_pyproject_toml_batch27():
    """project root 通过 pyproject.toml 检测。"""
    src = inspect.getsource(mmod)
    assert "pyproject.toml" in src


# ---------- signatures 第四十批 ----------


def test_signature_load_manifest_batch27():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.keys())
    assert params == ["manifest_path", "project_root"]


def test_signature_load_manifest_project_root_default_none_batch27():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_signature_resolve_relative_path_batch27():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.keys())
    assert params == ["path_str", "project_root", "field_name"]


def test_signature_is_absolute_like_batch27():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]


def test_signature_has_backslash_batch27():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]


def test_signature_detect_project_root_batch27():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.keys())
    assert params == ["start"]


def test_signature_manifest_file_count_property_batch27():
    """file_count 是 property。"""
    assert isinstance(Manifest.file_count, property)


def test_signature_manifest_pdf_count_property_batch27():
    assert isinstance(Manifest.pdf_count, property)


def test_signature_manifest_docx_count_property_batch27():
    assert isinstance(Manifest.docx_count, property)


def test_signature_manifest_content_group_count_property_batch27():
    assert isinstance(Manifest.content_group_count, property)


# ---------- module 合理性第四十批 ----------


def test_module_has_future_annotations_batch27():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch27():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_imports_dataclass_batch27():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_imports_pathlib_batch27():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_imports_manifest_version_batch27():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_imports_validate_batch27():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_all_export_six_entries_batch27():
    src = inspect.getsource(mmod)
    for name in [
        '"ManifestError"',
        '"Manifest"',
        '"DocumentEntry"',
        '"ExpectedFailure"',
        '"load_manifest"',
    ]:
        assert name in src


def test_module_manifest_error_inherits_exception_batch27():
    assert issubclass(ManifestError, Exception)


def test_module_manifest_error_not_value_error_batch27():
    """ManifestError 不继承 ValueError（独立异常类型）。"""
    assert not issubclass(ManifestError, ValueError)


# ---------- 端到端集成第四十批 ----------


def test_e2e_load_manifest_full_valid_batch27(tmp_path):
    """端到端：完整 manifest 加载并提取字段。"""
    p = _make_manifest_file(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "categories": ["tech"],
            },
            {
                "doc_id": "d2",
                "path": "samples/y.docx",
                "source_type": "docx",
                "sha256": "b" * 64,
                "categories": ["tech"],
                "paired_with": "d1",
            },
        ],
    )
    m = load_manifest(p)
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.categories_covered == ["tech"]
    assert m.content_group_count == 1


def test_e2e_load_manifest_with_annotation_batch27(tmp_path):
    """端到端：含 annotation_file。"""
    # 创建 annotation 文件让 resolved 路径合法
    (tmp_path / "annotations").mkdir()
    (tmp_path / "annotations" / "d1.json").write_text("{}", encoding="utf-8")
    p = _make_manifest_file(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "annotation_file": "annotations/d1.json",
            }
        ],
    )
    m = load_manifest(p)
    assert m.documents[0].annotation_resolved is not None
    assert m.documents[0].annotation_file_str == "annotations/d1.json"


def test_e2e_load_manifest_round_trip_batch27(tmp_path):
    """端到端：两次加载得到等价 Manifest。"""
    p = _make_manifest_file(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
            }
        ],
    )
    m1 = load_manifest(p)
    m2 = load_manifest(p)
    assert m1 == m2


def test_e2e_load_manifest_no_expected_failures_key_batch27(tmp_path):
    """端到端：manifest 不含 expected_failures key 也能加载（schema 不要求）。"""
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
    }
    (tmp_path / "pyproject.toml").write_text("#", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p)
    assert m.expected_failures == ()


def test_e2e_load_manifest_documents_field_optional_batch27(tmp_path):
    """端到端：schema 允许 documents 缺省吗？schema required 包含 documents。"""
    # 实际：schema required: ["manifest_version", "devset_status", "documents"]
    # 所以 documents 缺省会失败
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
    }
    (tmp_path / "pyproject.toml").write_text("#", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(p)


def test_e2e_load_manifest_wrong_version_raises_batch27(tmp_path):
    """端到端：manifest_version 不匹配抛 ManifestError。"""
    data = {
        "manifest_version": "2.0",  # 不兼容
        "devset_status": "incomplete",
        "documents": [],
    }
    (tmp_path / "pyproject.toml").write_text("#", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    # schema const 1.0 → EvalSchemaError；否则 ManifestError
    with pytest.raises(Exception):
        load_manifest(p)


def test_e2e_load_manifest_path_inside_root_batch27(tmp_path):
    """端到端：resolved_path 必须在 project_root 内。"""
    p = _make_manifest_file(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "subdir/x.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
            }
        ],
    )
    m = load_manifest(p, project_root=tmp_path)
    resolved = m.documents[0].resolved_path
    assert tmp_path.resolve() in resolved.parents or resolved == tmp_path.resolve()


def test_e2e_load_manifest_path_outside_root_raises_batch27(tmp_path):
    """端到端：路径在 project_root 外抛 ManifestError。"""
    p = _make_manifest_file(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "../../etc/passwd",
                "source_type": "pdf",
                "sha256": "a" * 64,
            }
        ],
    )
    with pytest.raises(ManifestError):
        load_manifest(p, project_root=tmp_path)
