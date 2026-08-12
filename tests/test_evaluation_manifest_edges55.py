"""evaluation/manifest.py 第五十五轮 edges 测试（Round 517）。

补强 edges54 未触及的角度（第二十八批）：
- _is_absolute_like 第二十八批：tab 开头 / newline 开头 / 多字符盘符（带 :）
- _has_backslash 第二十八批：含 tab 与 backslash
- Manifest 第二十八批：categories_covered 多类别 / content_group_count 链式 / 配对单向 / 多对
- _resolve_relative_path 第二十八批：field_name 含特殊字符 / 多层 ../
- load_manifest 第二十八批：含 annotation_resolved / categories 含 unicode / sha256 大写字母
- _detect_project_root 第二十八批：从根起 / 含多个 pyproject
- module source forbidden tokens 第四十五批
- module source 字符串精确补强第四十一批
- signatures 第四十一批
- module 合理性第四十一批
- 端到端集成第四十一批
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


# ---------- _is_absolute_like 第二十八批 ----------


def test_is_absolute_like_tab_prefix_batch28():
    """tab 开头不算绝对路径。"""
    assert _is_absolute_like("\tfoo") is False


def test_is_absolute_like_newline_prefix_batch28():
    assert _is_absolute_like("\nfoo") is False


def test_is_absolute_like_single_letter_no_colon_batch28():
    """'a/foo' 不算绝对（无冒号）。"""
    assert _is_absolute_like("a/foo") is False


def test_is_absolute_like_two_letter_drive_no_slash_batch28():
    """'ab:foo' 不算绝对（'a' 是字母，'b' 是第二个字符，但 path_str[1]==':' 且 path_str[2]=='f' 不在 (\\, /)）."""
    assert _is_absolute_like("ab:foo") is False


def test_is_absolute_like_long_relative_path_batch28():
    assert _is_absolute_like("a/b/c/d/e/f") is False


def test_is_absolute_like_just_colon_batch28():
    assert _is_absolute_like(":") is False


def test_is_absolute_like_just_drive_letter_batch28():
    assert _is_absolute_like("C") is False


def test_is_absolute_like_drive_letter_colon_only_batch28():
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_two_letter_drive_with_slash_batch28():
    """'AB:/foo' → path_str[0]='A' alpha, path_str[1]=':' → wait, B comes first."""
    # path_str[0]='A' alpha, path_str[1]='B', not ':' → False
    # 重新："AB:/foo"，path_str[1]='B'，不是 ':'，不算绝对
    assert _is_absolute_like("AB:/foo") is False


# ---------- _has_backslash 第二十八批 ----------


def test_has_backslash_with_tab_batch28():
    assert _has_backslash("\\\t") is True


def test_has_backslash_long_path_batch28():
    assert _has_backslash("a\\b\\c\\d\\e") is True


def test_has_backslash_only_spaces_batch28():
    assert _has_backslash("   ") is False


def test_has_backslash_unicode_batch28():
    """unicode 字符不含 backslash。"""
    assert _has_backslash("中文/路径") is False


# ---------- Manifest 第二十八批 ----------


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


def test_manifest_categories_covered_many_batch28():
    docs = (
        _make_doc(categories=("a", "b", "c")),
        _make_doc(categories=("d", "e")),
    )
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "b", "c", "d", "e"]


def test_manifest_content_group_one_way_pair_batch28():
    """配对单向（d1 → d2 但 d2 不 → d1）。"""
    docs = (
        _make_doc(doc_id="d1", paired_with="d2"),
        _make_doc(doc_id="d2"),  # d2 没有 paired_with
    )
    m = _make_manifest(documents=docs)
    # d1 配对 → 1 group；d2 未配对但被 d1 引用 → 不算 unpaired
    # 实现里：seen = {d1, d2}（pair frozenset）→ 1 group；d2 not in seen 是 False（d2 in seen），d2 has no paired_with 但 in seen → 不算 unpaired
    # 实际逻辑：先 groups=1（pair_ids），然后 for d in documents: if d.doc_id not in seen and not d.paired_with: unpaired += 1
    # d1 in seen → 不加；d2 in seen → 不加
    assert m.content_group_count == 1


def test_manifest_content_group_two_pairs_batch28():
    """两对独立配对。"""
    docs = (
        _make_doc(doc_id="d1", paired_with="d2"),
        _make_doc(doc_id="d2", paired_with="d1"),
        _make_doc(doc_id="d3", paired_with="d4"),
        _make_doc(doc_id="d4", paired_with="d3"),
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 2


def test_manifest_content_group_mixed_batch28():
    """两对 + 1 单。"""
    docs = (
        _make_doc(doc_id="d1", paired_with="d2"),
        _make_doc(doc_id="d2", paired_with="d1"),
        _make_doc(doc_id="d3"),  # unpaired
    )
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 2  # 1 pair + 1 unpaired


def test_manifest_file_count_with_expected_failures_batch28():
    """file_count 只算 documents，不含 expected_failures。"""
    m = _make_manifest(
        documents=(_make_doc(doc_id="d1"),),
        expected_failures=(MagicMock(), MagicMock()),
    )
    assert m.file_count == 1


def test_manifest_hashable_batch28():
    """frozen dataclass 是 hashable（tuple 字段都可 hash）。"""
    m = _make_manifest()
    h = hash(m)
    assert isinstance(h, int)


def test_manifest_properties_int_type_batch28():
    """property 返回 int 类型。"""
    m = _make_manifest(documents=(_make_doc(), _make_doc()))
    assert isinstance(m.file_count, int)
    assert isinstance(m.pdf_count, int)
    assert isinstance(m.docx_count, int)
    assert isinstance(m.content_group_count, int)


def test_manifest_categories_covered_returns_list_batch28():
    m = _make_manifest()
    assert isinstance(m.categories_covered, list)


# ---------- _resolve_relative_path 第二十八批 ----------


def test_resolve_relative_path_field_name_with_special_chars_batch28(tmp_path):
    """field_name 含特殊字符也透传到消息。"""
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("/etc/passwd", tmp_path, "documents[doc<id>].path")
    assert "documents[doc<id>].path" in str(exc.value)


def test_resolve_relative_path_multi_level_dotdot_batch28(tmp_path):
    """多层 ../ 退出 project_root → 抛错。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("../../../../etc/passwd", tmp_path, "test")


def test_resolve_relative_path_subdir_batch28(tmp_path):
    """子目录合法。"""
    result = _resolve_relative_path("subdir/x.pdf", tmp_path, "test")
    assert result.parent == (tmp_path / "subdir").resolve()


def test_resolve_relative_path_returns_resolved_batch28(tmp_path):
    """返回 resolve 后的路径。"""
    result = _resolve_relative_path("x.pdf", tmp_path, "test")
    assert result == (tmp_path / "x.pdf").resolve()


def test_resolve_relative_path_field_name_in_error_batch28(tmp_path):
    """错误消息含 field_name。"""
    try:
        _resolve_relative_path("/etc", tmp_path, "FIELD_X")
    except ManifestError as e:
        assert "FIELD_X" in str(e)
        return
    pytest.fail("Expected ManifestError")


# ---------- load_manifest 第二十八批 ----------


def _make_manifest_file(tmp_path: Path, documents=None, expected_failures=None) -> Path:
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": documents if documents is not None else [],
        "expected_failures": expected_failures if expected_failures is not None else [],
    }
    (tmp_path / "pyproject.toml").write_text("# test", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_with_categories_unicode_batch28(tmp_path):
    """categories 含 unicode。"""
    p = _make_manifest_file(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "categories": ["技术文档", "中文"],
            }
        ],
    )
    m = load_manifest(p)
    assert m.documents[0].categories == ("技术文档", "中文")


def test_load_manifest_sha256_uppercase_fails_batch28(tmp_path):
    """sha256 大写字母 → 不匹配 pattern `^[0-9a-f]{64}$`。"""
    p = _make_manifest_file(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "sha256": "A" * 64,  # 大写
            }
        ],
    )
    with pytest.raises(Exception):  # EvalSchemaError
        load_manifest(p)


def test_load_manifest_with_required_markers_batch28(tmp_path):
    """expectations 含 required_markers。"""
    p = _make_manifest_file(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "expectations": {
                    "element_count_by_type": {"paragraph": 1},
                    "required_markers": ["必须存在的标记"],
                },
            }
        ],
    )
    m = load_manifest(p)
    assert m.documents[0].expectations["required_markers"] == ["必须存在的标记"]


def test_load_manifest_returns_manifest_instance_batch28(tmp_path):
    p = _make_manifest_file(tmp_path)
    m = load_manifest(p)
    assert isinstance(m, Manifest)


def test_load_manifest_with_annotation_file_batch28(tmp_path):
    """annotation_file 字段。"""
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
    assert m.documents[0].annotation_file_str == "annotations/d1.json"


def test_load_manifest_path_with_subdir_batch28(tmp_path):
    """path 含子目录合法。"""
    p = _make_manifest_file(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/sub/deep/x.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
            }
        ],
    )
    m = load_manifest(p)
    # path_str 保留原相对路径（正斜杠）
    assert m.documents[0].path_str == "samples/sub/deep/x.pdf"
    # resolved_path 应在 project_root 内
    assert m.documents[0].resolved_path.is_absolute()


def test_load_manifest_devset_status_complete_batch28(tmp_path):
    """devset_status='complete' 也接受。"""
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
    }
    (tmp_path / "pyproject.toml").write_text("#", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p)
    assert m.devset_status == "complete"


# ---------- _detect_project_root 第二十八批 ----------


def test_detect_project_root_from_top_level_batch28(tmp_path):
    """从顶层目录起。"""
    (tmp_path / "pyproject.toml").write_text("#", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert result == tmp_path.resolve()


def test_detect_project_root_multi_level_pyproject_batch28(tmp_path):
    """多层 pyproject 都存在时取最近。"""
    (tmp_path / "pyproject.toml").write_text("# outer", encoding="utf-8")
    nested = tmp_path / "a"
    nested.mkdir()
    (nested / "pyproject.toml").write_text("# inner", encoding="utf-8")
    result = _detect_project_root(nested)
    assert result == nested.resolve()


def test_detect_project_root_from_deep_nested_file_batch28(tmp_path):
    """从深层嵌套文件起。"""
    (tmp_path / "pyproject.toml").write_text("#", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    f = deep / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    result = _detect_project_root(f)
    assert result == tmp_path.resolve()


def test_detect_project_root_returns_resolved_batch28(tmp_path):
    """返回 resolve 后的路径。"""
    (tmp_path / "pyproject.toml").write_text("#", encoding="utf-8")
    result = _detect_project_root(tmp_path)
    assert result == tmp_path.resolve()


def test_detect_project_root_with_no_pyproject_anywhere_batch28(tmp_path):
    """完全没有 pyproject.toml → 返回 start。"""
    # tmp_path 通常在 /tmp/pytest-of-USER/... 下，那里可能没有 pyproject
    # 用更深的子目录确保
    nested = tmp_path / "deep" / "nested"
    nested.mkdir(parents=True)
    result = _detect_project_root(nested)
    # 应该返回 nested 自己（fallback）
    assert result == nested.resolve()


# ---------- module source forbidden tokens 第四十五批 ----------


def test_module_source_no_subprocess_batch28():
    src = inspect.getsource(mmod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch28():
    src = inspect.getsource(mmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch28():
    src = inspect.getsource(mmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch28():
    src = inspect.getsource(mmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch28():
    src = inspect.getsource(mmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch28():
    src = inspect.getsource(mmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch28():
    src = inspect.getsource(mmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch28():
    src = inspect.getsource(mmod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch28():
    src = inspect.getsource(mmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch28():
    src = inspect.getsource(mmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch28():
    src = inspect.getsource(mmod)
    assert "requests" not in src


def test_module_source_no_unlink_batch28():
    src = inspect.getsource(mmod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十一批 ----------


def test_module_source_contains_is_absolute_like_docstring_batch28():
    src = inspect.getsource(mmod)
    assert "识别绝对路径" in src


def test_module_source_contains_resolve_relative_path_docstring_batch28():
    src = inspect.getsource(mmod)
    assert "校验路径形式并解析为绝对路径" in src


def test_module_source_contains_relative_to_batch28():
    src = inspect.getsource(mmod)
    assert "relative_to" in src


def test_module_source_contains_manifest_error_class_docstring_batch28():
    src = inspect.getsource(mmod)
    assert "清单加载或校验失败" in src


def test_module_source_contains_frozen_true_batch28():
    src = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in src


def test_module_source_contains_document_entry_class_batch28():
    src = inspect.getsource(mmod)
    assert "class DocumentEntry" in src


def test_module_source_contains_expected_failure_class_batch28():
    src = inspect.getsource(mmod)
    assert "class ExpectedFailure" in src


def test_module_source_contains_manifest_class_batch28():
    src = inspect.getsource(mmod)
    assert "class Manifest" in src


def test_module_source_contains_load_manifest_function_batch28():
    src = inspect.getsource(mmod)
    assert "def load_manifest" in src


def test_module_source_contains_detect_project_root_function_batch28():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root" in src


def test_module_source_contains_categories_property_batch28():
    src = inspect.getsource(mmod)
    assert "categories_covered" in src


def test_module_source_contains_content_group_count_property_batch28():
    src = inspect.getsource(mmod)
    assert "content_group_count" in src


# ---------- signatures 第四十一批 ----------


def test_signature_load_manifest_path_annotation_batch28():
    sig = inspect.signature(load_manifest)
    annotation = sig.parameters["manifest_path"].annotation
    assert "Path" in str(annotation)
    assert "str" in str(annotation)


def test_signature_load_manifest_return_annotation_batch28():
    sig = inspect.signature(load_manifest)
    assert sig.return_annotation == "Manifest"


def test_signature_resolve_relative_path_return_batch28():
    sig = inspect.signature(_resolve_relative_path)
    assert sig.return_annotation == "Path"


def test_signature_detect_project_root_return_batch28():
    sig = inspect.signature(_detect_project_root)
    assert sig.return_annotation == "Path"


def test_signature_is_absolute_like_return_batch28():
    sig = inspect.signature(_is_absolute_like)
    assert sig.return_annotation == "bool"


def test_signature_has_backslash_return_batch28():
    sig = inspect.signature(_has_backslash)
    assert sig.return_annotation == "bool"


def test_document_entry_init_has_10_params_batch28():
    import dataclasses
    fields = dataclasses.fields(DocumentEntry)
    assert len(fields) == 10


def test_expected_failure_init_has_5_params_batch28():
    import dataclasses
    fields = dataclasses.fields(ExpectedFailure)
    assert len(fields) == 5


# ---------- module 合理性第四十一批 ----------


def test_module_has_future_annotations_batch28():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch28():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_imports_dataclass_batch28():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_imports_pathlib_batch28():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch28():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_imports_manifest_version_batch28():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_imports_schema_validate_batch28():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_all_export_count_batch28():
    src = inspect.getsource(mmod)
    for name in ['"ManifestError"', '"Manifest"', '"DocumentEntry"', '"ExpectedFailure"', '"load_manifest"']:
        assert name in src


def test_module_no_main_block_batch28():
    src = inspect.getsource(mmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十一批 ----------


def test_e2e_load_manifest_full_doc_with_all_fields_batch28(tmp_path):
    """端到端：document 含全部可选字段。"""
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
                "categories": ["tech", "docs"],
                "paired_with": "d2",
                "annotation_file": "annotations/d1.json",
                "expectations": {
                    "element_count_by_type": {"paragraph": 5},
                    "required_markers": ["m1", "m2"],
                },
            }
        ],
    )
    m = load_manifest(p)
    d = m.documents[0]
    assert d.doc_id == "d1"
    assert d.categories == ("tech", "docs")
    assert d.paired_with == "d2"
    assert d.annotation_file_str == "annotations/d1.json"
    assert d.annotation_resolved is not None
    assert d.expectations["element_count_by_type"] == {"paragraph": 5}


def test_e2e_load_manifest_round_trip_stable_batch28(tmp_path):
    """端到端：连续两次加载结果相等。"""
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


def test_e2e_load_manifest_mixed_documents_batch28(tmp_path):
    """端到端：pdf + docx 混合。"""
    p = _make_manifest_file(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
            },
            {
                "doc_id": "d2",
                "path": "samples/y.docx",
                "source_type": "docx",
                "sha256": "b" * 64,
            },
        ],
    )
    m = load_manifest(p)
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.file_count == 2


def test_e2e_load_manifest_with_expected_failure_batch28(tmp_path):
    """端到端：含 expected_failure。"""
    p = _make_manifest_file(
        tmp_path,
        expected_failures=[
            {
                "doc_id": "bad1",
                "path": "bad/corrupt.pdf",
                "expected_error_code": "unsupported_format",
                "source_type": "pdf",
            },
            {
                "doc_id": "bad2",
                "path": "bad/empty.docx",
                "expected_error_code": "empty_document",
                "source_type": "docx",
            },
        ],
    )
    m = load_manifest(p)
    assert len(m.expected_failures) == 2
    assert m.expected_failures[0].doc_id == "bad1"
    assert m.expected_failures[1].doc_id == "bad2"


def test_e2e_load_manifest_invalid_version_raises_batch28(tmp_path):
    """端到端：manifest_version 不匹配抛 EvalSchemaError（schema const）。"""
    data = {
        "manifest_version": "0.9",  # 非 1.0
        "devset_status": "incomplete",
        "documents": [],
    }
    (tmp_path / "pyproject.toml").write_text("#", encoding="utf-8")
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(p)


def test_e2e_load_manifest_path_with_backslash_raises_batch28(tmp_path):
    """端到端：path 含反斜杠 → ManifestError。"""
    p = _make_manifest_file(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples\\x.pdf",  # 反斜杠
                "source_type": "pdf",
                "sha256": "a" * 64,
            }
        ],
    )
    with pytest.raises(ManifestError):
        load_manifest(p)


def test_e2e_load_manifest_path_absolute_raises_batch28(tmp_path):
    """端到端：path 是绝对路径 → ManifestError。"""
    p = _make_manifest_file(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "/etc/passwd",  # 绝对
                "source_type": "pdf",
                "sha256": "a" * 64,
            }
        ],
    )
    with pytest.raises(ManifestError):
        load_manifest(p)
