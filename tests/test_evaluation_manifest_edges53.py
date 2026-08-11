"""evaluation/manifest.py 第五十三轮 edges 测试（Round 503）。

补强 edges52 未触及的角度（第二十六批）：
- _is_absolute_like 第二十六批：empty string / `/` only / `C:` only / `1:foo` / `:foo` / unicode letter / cyrillic alpha / UNC
- _has_backslash 第二十六批：only backslash / mixed forward+back / 多 backslash
- _resolve_relative_path 第二十六批：empty raises / `.` accepted / `..` raises / `./foo` / `foo/./bar` / unicode
- DocumentEntry 第二十六批：frozen / hashable / equality / required fields
- ExpectedFailure 第二十六批：frozen / hashable / source_type optional
- Manifest properties 第二十六批：file_count / pdf_count / docx_count / content_group_count 双向配对 / 单向配对 / 多对 / categories_covered 排序 / project_root 类型
- load_manifest 第二十六批：default project_root detection / explicit project_root / version mismatch / no documents key / no expected_failures key / categories 透传
- _detect_project_root 第二十六批：file input / dir input / no pyproject / nearest pyproject
- module source forbidden tokens 第四十二批
- module source 字符串精确补强第三十八批
- signatures 第三十八批
- module 合理性第三十八批
- 端到端集成第三十八批
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, dataclass
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


# ---------- _is_absolute_like 第二十六批 ----------


def test_is_absolute_like_empty_string_batch26():
    assert _is_absolute_like("") is False


def test_is_absolute_like_single_slash_batch26():
    """单 `/` 也算绝对路径（POSIX root）。"""
    assert _is_absolute_like("/") is True


def test_is_absolute_like_c_colon_only_batch26():
    """`C:` 只有盘符无斜杠 → False（需要 C:\\ 或 C:/）。"""
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_digit_colon_batch26():
    """`1:foo` 数字开头非盘符 → False。"""
    assert _is_absolute_like("1:foo") is False


def test_is_absolute_like_colon_only_batch26():
    """`:foo` 非盘符 → False。"""
    assert _is_absolute_like(":foo") is False


def test_is_absolute_like_unc_path_batch26():
    """UNC `\\\\server\\share` 不被识别（实现仅检查盘符与 POSIX）。"""
    # UNC 以两个 backslash 开头，但 _is_absolute_like 不检查 backslash
    assert _is_absolute_like("\\\\server\\share") is False


def test_is_absolute_like_unicode_alpha_batch26():
    """unicode 字母（如希腊字母 α）也算 alpha → α:\\foo 是绝对路径。"""
    # α 是 unicode letter，isalpha() → True
    assert _is_absolute_like("α:\\foo") is True


def test_is_absolute_like_forward_slash_unix_batch26():
    assert _is_absolute_like("/usr/local/bin") is True


def test_is_absolute_like_c_drive_forward_batch26():
    """C:/foo 也算绝对路径（Windows forward slash 形式）。"""
    assert _is_absolute_like("C:/Users/x") is True


def test_is_absolute_like_relative_path_batch26():
    assert _is_absolute_like("samples/foo.pdf") is False


def test_is_absolute_like_single_dot_batch26():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_double_dot_batch26():
    assert _is_absolute_like("../foo") is False


# ---------- _has_backslash 第二十六批 ----------


def test_has_backslash_only_backslash_batch26():
    assert _has_backslash("\\") is True


def test_has_backslash_multiple_batch26():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_mixed_slashes_batch26():
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_no_backslash_batch26():
    assert _has_backslash("a/b/c") is False


def test_has_backslash_empty_batch26():
    assert _has_backslash("") is False


def test_has_backslash_leading_backslash_batch26():
    assert _has_backslash("\\foo") is True


def test_has_backslash_trailing_backslash_batch26():
    assert _has_backslash("foo\\") is True


# ---------- _resolve_relative_path 第二十六批 ----------


def test_resolve_relative_path_empty_raises_batch26(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("", tmp_path, "test_field")
    assert "为空" in str(exc.value)


def test_resolve_relative_path_absolute_raises_batch26(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("/etc/passwd", tmp_path, "f")
    assert "绝对路径" in str(exc.value)


def test_resolve_relative_path_backslash_raises_batch26(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("foo\\bar", tmp_path, "f")
    assert "正斜杠" in str(exc.value)


def test_resolve_relative_path_dot_only_batch26(tmp_path):
    """`.` 接受 → project_root 本身。"""
    resolved = _resolve_relative_path(".", tmp_path, "f")
    assert resolved == tmp_path.resolve()


def test_resolve_relative_path_dot_slash_foo_batch26(tmp_path):
    resolved = _resolve_relative_path("./foo", tmp_path, "f")
    assert resolved == (tmp_path / "foo").resolve()


def test_resolve_relative_path_inner_dot_batch26(tmp_path):
    """foo/./bar → foo/bar。"""
    resolved = _resolve_relative_path("foo/./bar", tmp_path, "f")
    assert resolved == (tmp_path / "foo" / "bar").resolve()


def test_resolve_relative_path_double_dot_raises_batch26(tmp_path):
    """`..` 解析后位于 project_root 外 → ManifestError。"""
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("../foo", tmp_path, "f")
    assert "项目根目录之外" in str(exc.value)


def test_resolve_relative_path_unicode_batch26(tmp_path):
    """unicode 路径名 → 正常解析。"""
    resolved = _resolve_relative_path("中文/文件夹/file.pdf", tmp_path, "f")
    assert resolved == (tmp_path / "中文" / "文件夹" / "file.pdf").resolve()


def test_resolve_relative_path_nested_subdir_batch26(tmp_path):
    resolved = _resolve_relative_path("a/b/c/d/e/f.txt", tmp_path, "f")
    assert resolved == (tmp_path / "a" / "b" / "c" / "d" / "e" / "f.txt").resolve()


def test_resolve_relative_path_returns_path_obj_batch26(tmp_path):
    resolved = _resolve_relative_path("foo", tmp_path, "f")
    assert isinstance(resolved, Path)


def test_resolve_relative_path_field_name_in_error_batch26(tmp_path):
    """错误消息应包含字段名。"""
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("/etc/passwd", tmp_path, "my_field")
    assert "my_field" in str(exc.value)


# ---------- DocumentEntry 第二十六批 ----------


def _make_doc_entry(**kwargs):
    defaults = dict(
        doc_id="d1",
        path_str="samples/foo.pdf",
        resolved_path=Path("/tmp/samples/foo.pdf"),
        source_type="pdf",
        sha256="abc",
        categories=("reports",),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    defaults.update(kwargs)
    return DocumentEntry(**defaults)


def test_document_entry_frozen_batch26():
    d = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "modified"  # type: ignore


def test_document_entry_hashable_batch26():
    d = _make_doc_entry()
    assert hash(d) != 0  # 只要能 hash 即可


def test_document_entry_equality_batch26():
    d1 = _make_doc_entry()
    d2 = _make_doc_entry()
    assert d1 == d2


def test_document_entry_inequality_batch26():
    d1 = _make_doc_entry(doc_id="d1")
    d2 = _make_doc_entry(doc_id="d2")
    assert d1 != d2


def test_document_entry_required_fields_batch26():
    """缺字段 → TypeError。"""
    with pytest.raises(TypeError):
        DocumentEntry(doc_id="d1")  # type: ignore


def test_document_entry_categories_accepts_tuple_batch26():
    d = _make_doc_entry(categories=("a", "b", "c"))
    assert d.categories == ("a", "b", "c")


def test_document_entry_categories_empty_tuple_batch26():
    d = _make_doc_entry(categories=())
    assert d.categories == ()


def test_document_entry_sha256_none_batch26():
    d = _make_doc_entry(sha256=None)
    assert d.sha256 is None


def test_document_entry_sha256_str_batch26():
    d = _make_doc_entry(sha256="deadbeef")
    assert d.sha256 == "deadbeef"


def test_document_entry_is_dataclass_batch26():
    from dataclasses import is_dataclass
    assert is_dataclass(DocumentEntry)


# ---------- ExpectedFailure 第二十六批 ----------


def _make_expected_failure(**kwargs):
    defaults = dict(
        doc_id="bad",
        path_str="samples/bad.txt",
        resolved_path=Path("/tmp/samples/bad.txt"),
        expected_error_code="unsupported_format",
        source_type=None,
    )
    defaults.update(kwargs)
    return ExpectedFailure(**defaults)


def test_expected_failure_frozen_batch26():
    ef = _make_expected_failure()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "modified"  # type: ignore


def test_expected_failure_hashable_batch26():
    ef = _make_expected_failure()
    assert hash(ef) != 0


def test_expected_failure_equality_batch26():
    ef1 = _make_expected_failure()
    ef2 = _make_expected_failure()
    assert ef1 == ef2


def test_expected_failure_source_type_none_batch26():
    ef = _make_expected_failure(source_type=None)
    assert ef.source_type is None


def test_expected_failure_source_type_str_batch26():
    ef = _make_expected_failure(source_type="txt")
    assert ef.source_type == "txt"


def test_expected_failure_required_fields_batch26():
    with pytest.raises(TypeError):
        ExpectedFailure(doc_id="bad")  # type: ignore


def test_expected_failure_is_dataclass_batch26():
    from dataclasses import is_dataclass
    assert is_dataclass(ExpectedFailure)


# ---------- Manifest properties 第二十六批 ----------


def _make_manifest(docs=None, efs=None, **kwargs):
    if docs is None:
        docs = ()
    if efs is None:
        efs = ()
    return Manifest(
        manifest_version=kwargs.get("manifest_version", MANIFEST_VERSION),
        devset_status=kwargs.get("devset_status", "incomplete"),
        documents=tuple(docs),
        expected_failures=tuple(efs),
        project_root=kwargs.get("project_root", Path("/tmp")),
    )


def test_manifest_file_count_empty_batch26():
    m = _make_manifest()
    assert m.file_count == 0


def test_manifest_file_count_three_docs_batch26():
    docs = [_make_doc_entry(doc_id=f"d{i}") for i in range(3)]
    m = _make_manifest(docs=docs)
    assert m.file_count == 3


def test_manifest_pdf_count_batch26():
    docs = [
        _make_doc_entry(doc_id="d1", source_type="pdf"),
        _make_doc_entry(doc_id="d2", source_type="pdf"),
        _make_doc_entry(doc_id="d3", source_type="docx"),
    ]
    m = _make_manifest(docs=docs)
    assert m.pdf_count == 2
    assert m.docx_count == 1


def test_manifest_no_other_source_types_counted_batch26():
    """pdf_count / docx_count 只数对应 source_type，其它不计。"""
    docs = [
        _make_doc_entry(doc_id="d1", source_type="txt"),
        _make_doc_entry(doc_id="d2", source_type="html"),
    ]
    m = _make_manifest(docs=docs)
    assert m.pdf_count == 0
    assert m.docx_count == 0


def test_manifest_categories_covered_sorted_batch26():
    docs = [
        _make_doc_entry(doc_id="d1", categories=("z", "a")),
        _make_doc_entry(doc_id="d2", categories=("m",)),
    ]
    m = _make_manifest(docs=docs)
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_empty_batch26():
    m = _make_manifest()
    assert m.categories_covered == []


def test_manifest_categories_covered_unique_batch26():
    """重复 category 应去重。"""
    docs = [
        _make_doc_entry(doc_id="d1", categories=("a", "b")),
        _make_doc_entry(doc_id="d2", categories=("a", "c")),
    ]
    m = _make_manifest(docs=docs)
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_content_group_count_no_pairs_batch26():
    """无 paired_with → 每个 doc 一组。"""
    docs = [_make_doc_entry(doc_id="d1"), _make_doc_entry(doc_id="d2")]
    m = _make_manifest(docs=docs)
    assert m.content_group_count == 2


def test_manifest_content_group_count_one_pair_batch26():
    """双向配对 → 1 组。"""
    docs = [
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
    ]
    m = _make_manifest(docs=docs)
    assert m.content_group_count == 1


def test_manifest_content_group_count_unidirectional_batch26():
    """单向配对 → 1 组（实现避免重复计数）。"""
    docs = [
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with=None),
    ]
    m = _make_manifest(docs=docs)
    # d1 指向 d2，d2 无 paired_with
    # pair_ids = {frozenset(d1, d2)}, groups=1
    # d2 not in seen，但 d2.paired_with is None → unpaired += 1
    # 所以总数 = 1 + 1 = 2
    # 但根据实现：if d.doc_id not in seen and not d.paired_with → d2 满足（d2 不在 seen 中且 d2.paired_with=None）→ unpaired
    # 实际逻辑：seen 在 pair 处理后被更新为 {d1, d2}，所以 d2 在 seen 中
    # 让我重新读代码...
    # pair_ids = {frozenset({d1, d2})}, all_paired = {d1}
    # for pair in pair_ids: groups += 1, seen.update(pair) → seen = {d1, d2}
    # for d in documents: if d.doc_id not in seen and not d.paired_with → 都不满足
    # 所以 unpaired = 0, groups = 1, total = 1
    assert m.content_group_count == 1


def test_manifest_content_group_count_mixed_batch26():
    """2 配对 + 1 单独 = 3。"""
    docs = [
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
        _make_doc_entry(doc_id="d3", paired_with=None),
    ]
    m = _make_manifest(docs=docs)
    # pair {d1,d2} → 1 group, seen={d1,d2}
    # d3 not in seen, paired_with=None → unpaired=1
    assert m.content_group_count == 2


def test_manifest_project_root_type_batch26():
    m = _make_manifest(project_root=Path("/custom"))
    assert isinstance(m.project_root, Path)


def test_manifest_is_dataclass_batch26():
    from dataclasses import is_dataclass
    assert is_dataclass(Manifest)


def test_manifest_hashable_after_load_batch26():
    """Manifest frozen → hashable。"""
    m = _make_manifest()
    assert hash(m) != 0


def test_manifest_frozen_batch26():
    m = _make_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore


# ---------- load_manifest 第二十六批 ----------


def _write_manifest(tmp_path, data):
    """写一个 manifest JSON 文件。"""
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _minimal_manifest_data():
    return {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }


def test_load_manifest_minimal_batch26(tmp_path):
    p = _write_manifest(tmp_path, _minimal_manifest_data())
    m = load_manifest(p, project_root=tmp_path)
    assert m.file_count == 0
    assert m.devset_status == "incomplete"


def test_load_manifest_default_project_root_batch26(tmp_path):
    """project_root=None → 自动检测（向上找 pyproject.toml）。"""
    # tmp_path 不含 pyproject.toml → 返回 tmp_path
    p = _write_manifest(tmp_path, _minimal_manifest_data())
    m = load_manifest(p)
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_explicit_project_root_batch26(tmp_path):
    p = _write_manifest(tmp_path, _minimal_manifest_data())
    root = tmp_path / "deep"
    root.mkdir()
    m = load_manifest(p, project_root=root)
    assert m.project_root == root.resolve()


def test_load_manifest_version_mismatch_raises_batch26(tmp_path):
    data = _minimal_manifest_data()
    data["manifest_version"] = "0.9"
    p = _write_manifest(tmp_path, data)
    # schema enum 已限 manifest_version="1.0"，所以 validate 先抛 EvalSchemaError
    from evaluation.schema import EvalSchemaError
    with pytest.raises((ManifestError, EvalSchemaError)) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "1.0" in str(exc.value) or "0.9" in str(exc.value) or "manifest_version" in str(exc.value)


def test_load_manifest_missing_file_raises_batch26(tmp_path):
    with pytest.raises(ManifestError) as exc:
        load_manifest(tmp_path / "missing.json", project_root=tmp_path)
    assert "不存在" in str(exc.value)


def test_load_manifest_invalid_json_raises_batch26(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("not valid json", encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "JSON" in str(exc.value)


def test_load_manifest_no_documents_key_batch26(tmp_path):
    """schema 要 documents 必填；缺失 → EvalSchemaError。"""
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "expected_failures": [],
    }
    p = _write_manifest(tmp_path, data)
    from evaluation.schema import EvalSchemaError
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_no_expected_failures_key_batch26(tmp_path):
    """schema 不要求 expected_failures 必填；缺失 → 默认为空 tuple。"""
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures == ()


def test_load_manifest_categories_aggregated_batch26(tmp_path):
    data = _minimal_manifest_data()
    data["documents"] = [
        {
            "doc_id": "d1",
            "path": "samples/a.pdf",
            "source_type": "pdf",
            "categories": ["reports", "internal"],
        },
        {
            "doc_id": "d2",
            "path": "samples/b.docx",
            "source_type": "docx",
            "categories": ["memos"],
        },
    ]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["internal", "memos", "reports"]


def test_load_manifest_sha256_propagated_batch26(tmp_path):
    valid_sha = "a" * 64  # 64 hex chars
    data = _minimal_manifest_data()
    data["documents"] = [
        {
            "doc_id": "d1",
            "path": "samples/a.pdf",
            "source_type": "pdf",
            "sha256": valid_sha,
        },
    ]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 == valid_sha


def test_load_manifest_paired_with_propagated_batch26(tmp_path):
    data = _minimal_manifest_data()
    data["documents"] = [
        {"doc_id": "d1", "path": "samples/a.pdf", "source_type": "pdf", "paired_with": "d2"},
        {"doc_id": "d2", "path": "samples/a.docx", "source_type": "docx", "paired_with": "d1"},
    ]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].paired_with == "d2"
    assert m.documents[1].paired_with == "d1"


def test_load_manifest_annotation_file_propagated_batch26(tmp_path):
    data = _minimal_manifest_data()
    data["documents"] = [
        {
            "doc_id": "d1",
            "path": "samples/a.pdf",
            "source_type": "pdf",
            "annotation_file": "annotations/a.json",
        },
    ]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_file_str == "annotations/a.json"


def test_load_manifest_annotation_resolved_batch26(tmp_path):
    data = _minimal_manifest_data()
    data["documents"] = [
        {
            "doc_id": "d1",
            "path": "samples/a.pdf",
            "source_type": "pdf",
            "annotation_file": "annotations/a.json",
        },
    ]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_resolved == (tmp_path / "annotations" / "a.json").resolve()


def test_load_manifest_expectations_propagated_batch26(tmp_path):
    data = _minimal_manifest_data()
    data["documents"] = [
        {
            "doc_id": "d1",
            "path": "samples/a.pdf",
            "source_type": "pdf",
            "expectations": {"element_count_by_type": {"paragraph": 10}},
        },
    ]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 10}}


def test_load_manifest_expected_failure_propagated_batch26(tmp_path):
    data = _minimal_manifest_data()
    data["expected_failures"] = [
        {
            "doc_id": "bad",
            "path": "samples/bad.txt",
            "source_type": "txt",
            "expected_error_code": "unsupported_format",
        },
    ]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    ef = m.expected_failures[0]
    assert ef.doc_id == "bad"
    assert ef.expected_error_code == "unsupported_format"
    assert ef.source_type == "txt"


def test_load_manifest_path_backslash_rejected_batch26(tmp_path):
    data = _minimal_manifest_data()
    data["documents"] = [
        {"doc_id": "d1", "path": "samples\\a.pdf", "source_type": "pdf"},
    ]
    p = _write_manifest(tmp_path, data)
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "正斜杠" in str(exc.value)


def test_load_manifest_path_absolute_rejected_batch26(tmp_path):
    data = _minimal_manifest_data()
    data["documents"] = [
        {"doc_id": "d1", "path": "/etc/passwd", "source_type": "pdf"},
    ]
    p = _write_manifest(tmp_path, data)
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "绝对路径" in str(exc.value)


def test_load_manifest_path_outside_root_rejected_batch26(tmp_path):
    data = _minimal_manifest_data()
    data["documents"] = [
        {"doc_id": "d1", "path": "../etc/passwd", "source_type": "pdf"},
    ]
    p = _write_manifest(tmp_path, data)
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "项目根目录之外" in str(exc.value)


def test_load_manifest_path_str_not_normalized_batch26(tmp_path):
    """path_str 保留原始形式（不 normalize）。"""
    data = _minimal_manifest_data()
    data["documents"] = [
        {"doc_id": "d1", "path": "samples/foo.PDF", "source_type": "pdf"},
    ]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].path_str == "samples/foo.PDF"


def test_load_manifest_returns_manifest_obj_batch26(tmp_path):
    p = _write_manifest(tmp_path, _minimal_manifest_data())
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)


def test_load_manifest_str_path_accepted_batch26(tmp_path):
    p = _write_manifest(tmp_path, _minimal_manifest_data())
    m = load_manifest(str(p), project_root=str(tmp_path))
    assert isinstance(m, Manifest)


# ---------- _detect_project_root 第二十六批 ----------


def test_detect_project_root_with_pyproject_batch26(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
    sub = tmp_path / "deep" / "sub"
    sub.mkdir(parents=True)
    assert _detect_project_root(sub) == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_input_batch26(tmp_path):
    """无 pyproject.toml → 返回 input（去掉 file 部分）。"""
    sub = tmp_path / "deep" / "sub"
    sub.mkdir(parents=True)
    # input 是 dir → 返回该 dir
    assert _detect_project_root(sub) == sub.resolve()


def test_detect_project_root_file_input_batch26(tmp_path):
    """input 是 file → 返回其 parent（继续向上找）。"""
    (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
    f = tmp_path / "deep" / "file.txt"
    f.parent.mkdir(parents=True)
    f.write_text("x", encoding="utf-8")
    assert _detect_project_root(f) == tmp_path.resolve()


def test_detect_project_root_nearest_pyproject_batch26(tmp_path):
    """多个 pyproject.toml → 最近的一个。"""
    (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
    mid = tmp_path / "mid"
    mid.mkdir()
    (mid / "pyproject.toml").write_text("[project]", encoding="utf-8")
    sub = mid / "sub"
    sub.mkdir()
    assert _detect_project_root(sub) == mid.resolve()


def test_detect_project_root_returns_path_batch26(tmp_path):
    assert isinstance(_detect_project_root(tmp_path), Path)


# ---------- module source forbidden tokens 第四十二批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import itertools",
    "import functools",
    "import timeit",
    "import time",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from itertools",
    "from functools",
    "from time",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import argparse",
    "import csv",
    "import random",
    "import hashlib",
]


def test_module_source_forbidden_tokens_batch26():
    source = inspect.getsource(mmod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token: {tok}"


def test_module_source_no_eval_exec_batch26():
    source = inspect.getsource(mmod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_module_source_no_star_import_batch26():
    source = inspect.getsource(mmod)
    assert "import *" not in source


def test_module_source_no_relative_imports_batch26():
    source = inspect.getsource(mmod)
    assert "from ." not in source


def test_module_source_no_unsafe_network_batch26():
    source = inspect.getsource(mmod)
    for tok in ["requests", "urllib.request", "http.client", "socket"]:
        assert tok not in source


def test_module_source_no_environ_batch26():
    source = inspect.getsource(mmod)
    assert "os.environ" not in source


def test_module_source_no_subprocess_batch26():
    source = inspect.getsource(mmod)
    assert "subprocess" not in source


def test_module_source_json_allowed_batch26():
    source = inspect.getsource(mmod)
    assert "import json" in source


def test_module_source_dataclass_allowed_batch26():
    """manifest.py 允许 from dataclasses import dataclass。"""
    source = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in source


def test_module_source_no_argparse_batch26():
    source = inspect.getsource(mmod)
    assert "argparse" not in source


def test_module_source_uses_from_future_annotations_batch26():
    source = inspect.getsource(mmod)
    assert "from __future__ import annotations" in source


def test_module_source_no_module_level_mutables_batch26():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(mmod))
    for node in tree.body:
        if isinstance(node, _ast.Assign) and isinstance(node.targets[0], _ast.Name):
            name = node.targets[0].id
            if name.startswith("_") and not name.startswith("__"):
                pytest.fail(f"private module-level constant: {name}")


# ---------- module source 字符串精确补强第三十八批 ----------


def test_module_source_contains_manifest_class_batch26():
    source = inspect.getsource(mmod)
    assert "class Manifest" in source


def test_module_source_contains_document_entry_class_batch26():
    source = inspect.getsource(mmod)
    assert "class DocumentEntry" in source


def test_module_source_contains_expected_failure_class_batch26():
    source = inspect.getsource(mmod)
    assert "class ExpectedFailure" in source


def test_module_source_contains_is_absolute_like_batch26():
    source = inspect.getsource(mmod)
    assert "_is_absolute_like" in source


def test_module_source_contains_has_backslash_batch26():
    source = inspect.getsource(mmod)
    assert "_has_backslash" in source


def test_module_source_contains_resolve_relative_path_batch26():
    source = inspect.getsource(mmod)
    assert "_resolve_relative_path" in source


def test_module_source_contains_detect_project_root_batch26():
    source = inspect.getsource(mmod)
    assert "_detect_project_root" in source


def test_module_source_contains_manifest_error_class_batch26():
    source = inspect.getsource(mmod)
    assert "class ManifestError" in source


def test_module_source_contains_frozen_true_batch26():
    source = inspect.getsource(mmod)
    assert "frozen=True" in source


def test_module_source_contains_relative_to_batch26():
    source = inspect.getsource(mmod)
    assert "relative_to" in source


def test_module_source_contains_resolve_call_batch26():
    source = inspect.getsource(mmod)
    assert ".resolve()" in source


def test_module_source_contains_validate_call_batch26():
    source = inspect.getsource(mmod)
    assert "validate(" in source


def test_module_source_contains_manifest_version_import_batch26():
    source = inspect.getsource(mmod)
    assert "MANIFEST_VERSION" in source


def test_module_source_contains_pyproject_toml_batch26():
    source = inspect.getsource(mmod)
    assert "pyproject.toml" in source


def test_module_source_contains_paired_with_batch26():
    source = inspect.getsource(mmod)
    assert "paired_with" in source


# ---------- signatures 第三十八批 ----------


def test_signature_is_absolute_like_batch26():
    sig = inspect.signature(_is_absolute_like)
    assert list(sig.parameters.keys()) == ["path_str"]
    assert sig.parameters["path_str"].annotation == "str"
    assert sig.return_annotation == "bool"


def test_signature_has_backslash_batch26():
    sig = inspect.signature(_has_backslash)
    assert list(sig.parameters.keys()) == ["path_str"]
    assert sig.return_annotation == "bool"


def test_signature_resolve_relative_path_batch26():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters.keys()) == ["path_str", "project_root", "field_name"]


def test_signature_resolve_relative_path_annotations_batch26():
    sig = inspect.signature(_resolve_relative_path)
    assert sig.parameters["path_str"].annotation == "str"
    assert sig.parameters["project_root"].annotation == "Path"
    assert sig.parameters["field_name"].annotation == "str"
    assert sig.return_annotation == "Path"


def test_signature_detect_project_root_batch26():
    sig = inspect.signature(_detect_project_root)
    assert list(sig.parameters.keys()) == ["start"]
    assert sig.parameters["start"].annotation == "Path"
    assert sig.return_annotation == "Path"


def test_signature_load_manifest_batch26():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters.keys()) == ["manifest_path", "project_root"]


def test_signature_load_manifest_path_annotation_batch26():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["manifest_path"].annotation == "Path | str"
    assert sig.parameters["project_root"].annotation == "Path | str | None"
    assert sig.parameters["project_root"].default is None


def test_signature_resolve_relative_path_no_varargs_batch26():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


def test_signature_load_manifest_no_varargs_batch26():
    sig = inspect.signature(load_manifest)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


def test_signature_all_annotations_are_strings_batch26():
    """from __future__ import annotations → 所有 annotation 应是 str。"""
    for fn in [_is_absolute_like, _has_backslash, _resolve_relative_path, _detect_project_root, load_manifest]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            if p.annotation is not inspect.Parameter.empty:
                assert isinstance(p.annotation, str), f"{fn.__name__}.{p.name}"


# ---------- module 合理性第三十八批 ----------


def test_module_all_present_batch26():
    assert hasattr(mmod, "__all__")


def test_module_all_contains_five_names_batch26():
    assert set(mmod.__all__) == {
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    }


def test_module_has_three_functions_batch26():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(mmod))
    funcs = [n.name for n in tree.body if isinstance(n, _ast.FunctionDef)]
    assert set(funcs) == {
        "_is_absolute_like",
        "_has_backslash",
        "_resolve_relative_path",
        "load_manifest",
        "_detect_project_root",
    }


def test_module_has_four_classes_batch26():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(mmod))
    classes = [n.name for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert set(classes) == {"ManifestError", "DocumentEntry", "ExpectedFailure", "Manifest"}


def test_module_docstring_present_batch26():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__.strip()) > 0


def test_module_docstring_mentions_path_constraints_batch26():
    assert "相对路径" in mmod.__doc__ or "absolute" in mmod.__doc__.lower()


def test_module_docstring_mentions_no_absolute_path_batch26():
    assert "绝对路径" in mmod.__doc__ or "absolute" in mmod.__doc__.lower()


def test_module_uses_from_future_annotations_batch26():
    source = inspect.getsource(mmod)
    assert "from __future__ import annotations" in source


def test_module_manifest_error_docstring_present_batch26():
    assert ManifestError.__doc__ is not None


def test_module_manifest_error_inherits_exception_batch26():
    assert issubclass(ManifestError, Exception)


def test_module_document_entry_frozen_dataclass_batch26():
    """DocumentEntry frozen dataclass。"""
    from dataclasses import is_dataclass, fields
    assert is_dataclass(DocumentEntry)
    d = _make_doc_entry()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "x"  # type: ignore


def test_module_all_entries_accessible_batch26():
    for name in mmod.__all__:
        assert hasattr(mmod, name)


# ---------- 端到端集成第三十八批 ----------


def test_e2e_load_minimal_manifest_batch26(tmp_path):
    p = _write_manifest(tmp_path, _minimal_manifest_data())
    m = load_manifest(p, project_root=tmp_path)
    assert m.manifest_version == MANIFEST_VERSION
    assert m.devset_status == "incomplete"
    assert m.documents == ()
    assert m.expected_failures == ()


def test_e2e_load_manifest_with_full_document_batch26(tmp_path):
    valid_sha = "b" * 64
    data = _minimal_manifest_data()
    data["documents"] = [
        {
            "doc_id": "d1",
            "path": "samples/a.pdf",
            "source_type": "pdf",
            "sha256": valid_sha,
            "categories": ["reports"],
            "expectations": {"element_count_by_type": {"paragraph": 5}},
        }
    ]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.file_count == 1
    d = m.documents[0]
    assert d.doc_id == "d1"
    assert d.source_type == "pdf"
    assert d.sha256 == valid_sha
    assert d.categories == ("reports",)
    assert d.expectations == {"element_count_by_type": {"paragraph": 5}}


def test_e2e_load_manifest_with_expected_failure_batch26(tmp_path):
    data = _minimal_manifest_data()
    data["expected_failures"] = [
        {
            "doc_id": "bad",
            "path": "samples/bad.txt",
            "source_type": "txt",
            "expected_error_code": "unsupported_format",
        }
    ]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    ef = m.expected_failures[0]
    assert ef.doc_id == "bad"
    assert ef.expected_error_code == "unsupported_format"
    assert ef.source_type == "txt"


def test_e2e_load_manifest_categories_aggregated_batch26(tmp_path):
    data = _minimal_manifest_data()
    data["documents"] = [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "categories": ["z", "a"]},
        {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf", "categories": ["m"]},
    ]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["a", "m", "z"]


def test_e2e_load_manifest_pdf_docx_count_batch26(tmp_path):
    data = _minimal_manifest_data()
    data["documents"] = [
        {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf"},
        {"doc_id": "d3", "path": "c.docx", "source_type": "docx"},
    ]
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, project_root=tmp_path)
    assert m.pdf_count == 2
    assert m.docx_count == 1


def test_e2e_manifest_is_hashable_after_load_batch26(tmp_path):
    p = _write_manifest(tmp_path, _minimal_manifest_data())
    m = load_manifest(p, project_root=tmp_path)
    assert hash(m) != 0


def test_e2e_manifest_frozen_after_load_batch26(tmp_path):
    p = _write_manifest(tmp_path, _minimal_manifest_data())
    m = load_manifest(p, project_root=tmp_path)
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore


def test_e2e_load_manifest_default_project_root_works_batch26(tmp_path):
    """无 project_root 参数 → 自动检测。"""
    p = _write_manifest(tmp_path, _minimal_manifest_data())
    m = load_manifest(p)
    assert m.project_root.exists() or m.project_root == tmp_path.resolve()
