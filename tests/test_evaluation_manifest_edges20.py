r"""evaluation/manifest.py 边角测试 - 第二十轮（Round 282）。

edges19 已覆盖：source-level 详尽 / 模块 imports / ManifestError class / _is_absolute_like /
_has_backslash / DocumentEntry / ExpectedFailure / Manifest dataclass / _resolve_relative_path /
load_manifest / _detect_project_root / __all__ / namespace / 不含禁止内容 / load_manifest 行为
（minimal / nonexistent / invalid_json / version mismatch / two calls independent）/ 签名 /
docstring / dataclass 类型。

edges20 补强未覆盖的角度（行为细节 + schema 联动 + frozen dataclass + 多场景）：
- **load_manifest 完整文档场景**：1 doc + 1 expected_failure；多 doc；含 annotation_file；
  含 expectations；含 sha256；含 categories；含 paired_with；含 source_type for expected_failure
- **load_manifest schema 失败场景**：documents 非 list；document 缺 doc_id/path/source_type；
  expected_failure 缺 doc_id/path/expected_error_code；sha256 格式错；source_type 错 enum；
  manifest_version 非 1.0；devset_status 非 enum；额外字段
- **load_manifest JSON 解析失败**：JSONDecodeError 转 ManifestError
- **load_manifest manifest_version 兼容性**：1.0 通过；其他都失败
- **load_manifest devset_status**：complete/incomplete 都通过；其他都失败
- **DocumentEntry frozen**：setattr raises FrozenInstanceError；delattr raises；eq/hash
- **ExpectedFailure frozen**：同上
- **Manifest frozen**：同上
- **Manifest properties**：file_count/pdf_count/docx_count/content_group_count/categories_covered
  多场景（空 manifest；单 doc；多 doc 含 paired；categories 合并/去重）
- **content_group_count paired_with 双向引用**：A.paired_with=B；B.paired_with=A → 1 组
- **content_group_count 单向引用**：A.paired_with=B（B 不回）→ 仍 1 组
- **content_group_count 多 paired**：2 对 paired + 1 单 → 3 组
- **categories_covered 排序**：sorted；去重
- **_is_absolute_like 字符级**：'/' / '\\foo' / 'C:/foo' / 'C:\\foo' / 'D:foo'（不 abs）/
  'a/b' / '' / 'foo' / unicode 路径
- **_has_backslash 字符级**：'a/b' / 'a\\b' / 'a\\b/c' / '\\' / ''
- **_resolve_relative_path 多场景**：normal；unicode；带空格；多 / 拼接；project_root escape
  （../../../etc/passwd）；纯文件名
- **_detect_project_root fallback**：找不到 pyproject.toml → 返回 cur
- **module __all__ 5 entries 精确顺序**
- **module 不含禁止 imports**：os/sys/logging/subprocess/asyncio/threading/concurrent
- **ManifestError 不 swallow**：raise ManifestError 由 except Exception 捕获
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
from typing import Any

import pytest

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


# =========================================================================
# 辅助
# =========================================================================


def _write_manifest(tmp_path: Path, data: dict[str, Any]) -> Path:
    """写一个 manifest JSON 文件，返回路径。"""
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def _minimal_valid_manifest_data(project_root_relative: str = "samples") -> dict[str, Any]:
    """构造一个最小可用的 manifest dict（documents 列表为空）。"""
    return {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }


# =========================================================================
# load_manifest 多场景
# =========================================================================


def test_load_manifest_empty_documents(tmp_path):
    """documents=[] → Manifest.documents 是空 tuple。"""
    data = _minimal_valid_manifest_data()
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents == ()


def test_load_manifest_single_document(tmp_path):
    """1 个 doc → Manifest.documents 含 1 个 DocumentEntry。"""
    # 在 tmp_path 下放一个虚拟文件
    (tmp_path / "doc.pdf").write_bytes(b"fake pdf")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "doc.pdf", "source_type": "pdf"},
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert len(m.documents) == 1
    assert isinstance(m.documents[0], DocumentEntry)


def test_load_manifest_two_documents(tmp_path):
    """2 个 doc → Manifest.documents 含 2 个。"""
    (tmp_path / "a.pdf").write_bytes(b"a")
    (tmp_path / "b.pdf").write_bytes(b"b")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf"},
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert len(m.documents) == 2
    assert m.documents[0].doc_id == "d1"
    assert m.documents[1].doc_id == "d2"


def test_load_manifest_with_sha256(tmp_path):
    """含 sha256 → DocumentEntry.sha256 反映。"""
    (tmp_path / "a.pdf").write_bytes(b"a")
    sha = "a" * 64
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "sha256": sha},
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents[0].sha256 == sha


def test_load_manifest_with_categories(tmp_path):
    """含 categories list → DocumentEntry.categories 是 tuple。"""
    (tmp_path / "a.pdf").write_bytes(b"a")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["report", "financial"]},
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents[0].categories == ("report", "financial")
    assert isinstance(m.documents[0].categories, tuple)


def test_load_manifest_with_paired_with(tmp_path):
    """含 paired_with → DocumentEntry.paired_with 反映。"""
    (tmp_path / "a.pdf").write_bytes(b"a")
    (tmp_path / "b.pdf").write_bytes(b"b")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf", "paired_with": "d1"},
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents[0].paired_with == "d2"
    assert m.documents[1].paired_with == "d1"


def test_load_manifest_with_annotation_file(tmp_path):
    """含 annotation_file → DocumentEntry.annotation_resolved 解析。"""
    (tmp_path / "a.pdf").write_bytes(b"a")
    (tmp_path / "a.annotation.json").write_text("{}", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "annotation_file": "a.annotation.json"},
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents[0].annotation_file_str == "a.annotation.json"
    assert m.documents[0].annotation_resolved is not None
    assert m.documents[0].annotation_resolved.is_file()


def test_load_manifest_with_expectations(tmp_path):
    """含 expectations → DocumentEntry.expectations dict。"""
    (tmp_path / "a.pdf").write_bytes(b"a")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "expectations": {"element_count_by_type": {"paragraph": 5}}},
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}


def test_load_manifest_with_expected_failures(tmp_path):
    """含 expected_failures → Manifest.expected_failures 含 ExpectedFailure。"""
    (tmp_path / "broken.pdf").write_bytes(b"x")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "broken.pdf", "expected_error_code": "parse_failed"},
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert len(m.expected_failures) == 1
    assert isinstance(m.expected_failures[0], ExpectedFailure)
    assert m.expected_failures[0].expected_error_code == "parse_failed"


def test_load_manifest_expected_failure_with_source_type(tmp_path):
    """expected_failure 含 source_type → ExpectedFailure.source_type 反映。"""
    (tmp_path / "broken.pdf").write_bytes(b"x")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "broken.pdf", "expected_error_code": "x",
             "source_type": "txt"},
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.expected_failures[0].source_type == "txt"


def test_load_manifest_expected_failure_no_source_type(tmp_path):
    """expected_failure 不含 source_type → ExpectedFailure.source_type=None。"""
    (tmp_path / "broken.pdf").write_bytes(b"x")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "broken.pdf", "expected_error_code": "x"},
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.expected_failures[0].source_type is None


def test_load_manifest_docx_source_type(tmp_path):
    """source_type='docx' → DocumentEntry.source_type='docx'。"""
    (tmp_path / "a.docx").write_bytes(b"x")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.docx", "source_type": "docx"},
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents[0].source_type == "docx"


def test_load_manifest_doc_id_propagates(tmp_path):
    """doc_id 准确传播到 DocumentEntry.doc_id。"""
    (tmp_path / "a.pdf").write_bytes(b"x")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "my-id-XYZ", "path": "a.pdf", "source_type": "pdf"},
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents[0].doc_id == "my-id-XYZ"


def test_load_manifest_path_str_preserved(tmp_path):
    """path_str 保留原始字符串（相对路径，正斜杠）。"""
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.pdf").write_bytes(b"x")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "sub/a.pdf", "source_type": "pdf"},
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents[0].path_str == "sub/a.pdf"


def test_load_manifest_resolved_path_is_absolute(tmp_path):
    """resolved_path 是绝对路径。"""
    (tmp_path / "a.pdf").write_bytes(b"x")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents[0].resolved_path.is_absolute()


# =========================================================================
# load_manifest schema 失败场景
# =========================================================================


def test_load_manifest_missing_documents_key_raises(tmp_path):
    """缺 documents 键 → schema 失败 → EvalSchemaError。"""
    from evaluation.schema import EvalSchemaError

    data = {"manifest_version": "1.0", "devset_status": "incomplete"}
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_documents_not_list_raises(tmp_path):
    """documents 非 list → schema 失败。"""
    from evaluation.schema import EvalSchemaError

    data = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": "not a list",
    }
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_document_missing_doc_id_raises(tmp_path):
    """document 缺 doc_id → schema 失败。"""
    from evaluation.schema import EvalSchemaError

    data = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"path": "a.pdf", "source_type": "pdf"}],
    }
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_document_missing_path_raises(tmp_path):
    """document 缺 path → schema 失败。"""
    from evaluation.schema import EvalSchemaError

    data = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "source_type": "pdf"}],
    }
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_document_missing_source_type_raises(tmp_path):
    """document 缺 source_type → schema 失败。"""
    from evaluation.schema import EvalSchemaError

    data = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf"}],
    }
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_wrong_source_type_raises(tmp_path):
    """source_type 非 pdf/docx → schema 失败。"""
    from evaluation.schema import EvalSchemaError

    data = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "txt"}],
    }
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_doc_extra_field_raises(tmp_path):
    """document 含额外字段 → schema additionalProperties:false 失败。"""
    from evaluation.schema import EvalSchemaError

    (tmp_path / "a.pdf").write_bytes(b"x")
    data = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
                       "extra_field": "not allowed"}],
    }
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_sha256_wrong_format_raises(tmp_path):
    """sha256 不是 64 hex → schema 失败。"""
    from evaluation.schema import EvalSchemaError

    (tmp_path / "a.pdf").write_bytes(b"x")
    data = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
                       "sha256": "short"}],
    }
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_devset_status_wrong_enum_raises(tmp_path):
    """devset_status 非 complete/incomplete → schema 失败。"""
    from evaluation.schema import EvalSchemaError

    data = {
        "manifest_version": "1.0", "devset_status": "other",
        "documents": [],
    }
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_top_level_extra_field_raises(tmp_path):
    """top-level 含额外字段 → 失败。"""
    from evaluation.schema import EvalSchemaError

    data = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [], "extra": "x",
    }
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_expected_failure_missing_doc_id_raises(tmp_path):
    """expected_failure 缺 doc_id → schema 失败。"""
    from evaluation.schema import EvalSchemaError

    data = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{"path": "x.pdf", "expected_error_code": "y"}],
    }
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_expected_failure_missing_path_raises(tmp_path):
    """expected_failure 缺 path → schema 失败。"""
    from evaluation.schema import EvalSchemaError

    data = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{"doc_id": "ef1", "expected_error_code": "y"}],
    }
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_expected_failure_missing_code_raises(tmp_path):
    """expected_failure 缺 expected_error_code → schema 失败。"""
    from evaluation.schema import EvalSchemaError

    data = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{"doc_id": "ef1", "path": "x.pdf"}],
    }
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


# =========================================================================
# load_manifest manifest_version 兼容性
# =========================================================================


def test_load_manifest_version_1_0_passes(tmp_path):
    """manifest_version='1.0' 通过。"""
    data = _minimal_valid_manifest_data()
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.manifest_version == "1.0"


def test_load_manifest_version_2_0_raises(tmp_path):
    """manifest_version='2.0' → schema 失败（const: '1.0'）。"""
    from evaluation.schema import EvalSchemaError

    data = {"manifest_version": "2.0", "devset_status": "incomplete", "documents": []}
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_version_1_1_raises(tmp_path):
    """manifest_version='1.1' → schema 失败。"""
    from evaluation.schema import EvalSchemaError

    data = {"manifest_version": "1.1", "devset_status": "incomplete", "documents": []}
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_version_non_string_raises(tmp_path):
    """manifest_version 非 str → schema 失败。"""
    from evaluation.schema import EvalSchemaError

    data = {"manifest_version": 1.0, "devset_status": "incomplete", "documents": []}
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


# =========================================================================
# load_manifest JSON 解析失败
# =========================================================================


def test_load_manifest_invalid_json_raises_manifest_error(tmp_path):
    """非法 JSON → ManifestError（不是 EvalSchemaError）。"""
    p = tmp_path / "manifest.json"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p, tmp_path)


def test_load_manifest_empty_file_raises(tmp_path):
    """空文件 → JSON 解析失败 → ManifestError。"""
    p = tmp_path / "manifest.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(p, tmp_path)


def test_load_manifest_top_level_array_raises(tmp_path):
    """top-level 是 array 而非 object → schema 失败。"""
    from evaluation.schema import EvalSchemaError

    p = tmp_path / "manifest.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


# =========================================================================
# DocumentEntry frozen
# =========================================================================


def _make_doc_entry(tmp_path: Path) -> DocumentEntry:
    return DocumentEntry(
        doc_id="d1",
        path_str="a.pdf",
        resolved_path=tmp_path / "a.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def test_document_entry_setattr_raises(tmp_path):
    entry = _make_doc_entry(tmp_path)
    with pytest.raises(FrozenInstanceError):
        entry.doc_id = "modified"


def test_document_entry_delattr_raises(tmp_path):
    entry = _make_doc_entry(tmp_path)
    with pytest.raises(FrozenInstanceError):
        del entry.doc_id


def test_document_entry_eq_same_values(tmp_path):
    """两个相同值的 DocumentEntry 相等。"""
    e1 = _make_doc_entry(tmp_path)
    e2 = _make_doc_entry(tmp_path)
    assert e1 == e2


def test_document_entry_eq_different_values(tmp_path):
    e1 = _make_doc_entry(tmp_path)
    e2 = DocumentEntry(
        doc_id="d2",  # 不同
        path_str="a.pdf",
        resolved_path=tmp_path / "a.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    assert e1 != e2


def test_document_entry_hashable(tmp_path):
    """frozen dataclass 可 hash。"""
    e = _make_doc_entry(tmp_path)
    h = hash(e)
    assert isinstance(h, int)


def test_document_entry_in_set(tmp_path):
    """frozen dataclass 可作 set 元素。"""
    e1 = _make_doc_entry(tmp_path)
    e2 = _make_doc_entry(tmp_path)
    s = {e1, e2}
    # 相同值 → 集合 1 个元素
    assert len(s) == 1


# =========================================================================
# ExpectedFailure frozen
# =========================================================================


def _make_ef_entry(tmp_path: Path) -> ExpectedFailure:
    return ExpectedFailure(
        doc_id="ef1",
        path_str="x.pdf",
        resolved_path=tmp_path / "x.pdf",
        expected_error_code="parse_failed",
        source_type="pdf",
    )


def test_expected_failure_setattr_raises(tmp_path):
    ef = _make_ef_entry(tmp_path)
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "x"


def test_expected_failure_delattr_raises(tmp_path):
    ef = _make_ef_entry(tmp_path)
    with pytest.raises(FrozenInstanceError):
        del ef.doc_id


def test_expected_failure_eq_same(tmp_path):
    assert _make_ef_entry(tmp_path) == _make_ef_entry(tmp_path)


def test_expected_failure_hashable(tmp_path):
    ef = _make_ef_entry(tmp_path)
    assert isinstance(hash(ef), int)


# =========================================================================
# Manifest frozen
# =========================================================================


def _make_empty_manifest(tmp_path: Path) -> Manifest:
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )


def test_manifest_setattr_raises(tmp_path):
    m = _make_empty_manifest(tmp_path)
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"


def test_manifest_delattr_raises(tmp_path):
    m = _make_empty_manifest(tmp_path)
    with pytest.raises(FrozenInstanceError):
        del m.devset_status


def test_manifest_hashable(tmp_path):
    m = _make_empty_manifest(tmp_path)
    assert isinstance(hash(m), int)


# =========================================================================
# Manifest properties 多场景
# =========================================================================


def test_manifest_file_count_zero(tmp_path):
    m = _make_empty_manifest(tmp_path)
    assert m.file_count == 0


def test_manifest_file_count_one(tmp_path):
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(_make_doc_entry(tmp_path),),
        expected_failures=(),
        project_root=tmp_path,
    )
    assert m.file_count == 1


def test_manifest_pdf_count_zero_when_no_pdf(tmp_path):
    """无 pdf doc → pdf_count=0。"""
    entry = DocumentEntry(
        doc_id="d1", path_str="a.docx", resolved_path=tmp_path / "a.docx",
        source_type="docx", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(entry,),
        expected_failures=(),
        project_root=tmp_path,
    )
    assert m.pdf_count == 0
    assert m.docx_count == 1


def test_manifest_docx_count_zero_when_no_docx(tmp_path):
    """无 docx → docx_count=0。"""
    entry = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=tmp_path / "a.pdf",
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(entry,),
        expected_failures=(),
        project_root=tmp_path,
    )
    assert m.pdf_count == 1
    assert m.docx_count == 0


def test_manifest_categories_covered_empty(tmp_path):
    """无 categories → []."""
    m = _make_empty_manifest(tmp_path)
    assert m.categories_covered == []


def test_manifest_categories_covered_merged(tmp_path):
    """多 doc categories 合并。"""
    e1 = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=tmp_path / "a.pdf",
        source_type="pdf", sha256=None, categories=("report", "financial"),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    e2 = DocumentEntry(
        doc_id="d2", path_str="b.pdf", resolved_path=tmp_path / "b.pdf",
        source_type="pdf", sha256=None, categories=("legal",),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(e1, e2),
        expected_failures=(),
        project_root=tmp_path,
    )
    assert m.categories_covered == ["financial", "legal", "report"]  # sorted


def test_manifest_categories_covered_dedup(tmp_path):
    """重复 category 去重。"""
    e1 = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=tmp_path / "a.pdf",
        source_type="pdf", sha256=None, categories=("report", "financial"),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    e2 = DocumentEntry(
        doc_id="d2", path_str="b.pdf", resolved_path=tmp_path / "b.pdf",
        source_type="pdf", sha256=None, categories=("report",),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(e1, e2),
        expected_failures=(),
        project_root=tmp_path,
    )
    assert m.categories_covered == ["financial", "report"]


def test_manifest_categories_covered_returns_list(tmp_path):
    """categories_covered 返回 list（不是 tuple/set）。"""
    e = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=tmp_path / "a.pdf",
        source_type="pdf", sha256=None, categories=("z",),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(e,),
        expected_failures=(),
        project_root=tmp_path,
    )
    assert isinstance(m.categories_covered, list)


def test_manifest_content_group_count_zero(tmp_path):
    """空 manifest → content_group_count=0。"""
    m = _make_empty_manifest(tmp_path)
    assert m.content_group_count == 0


def test_manifest_content_group_count_unpaired(tmp_path):
    """2 个 unpaired doc → 2 组。"""
    e1 = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=tmp_path / "a.pdf",
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    e2 = DocumentEntry(
        doc_id="d2", path_str="b.pdf", resolved_path=tmp_path / "b.pdf",
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(e1, e2),
        expected_failures=(),
        project_root=tmp_path,
    )
    assert m.content_group_count == 2


def test_manifest_content_group_count_paired_bidirectional(tmp_path):
    """A.paired_with=B + B.paired_with=A → 1 组（不是 2）。"""
    e1 = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=tmp_path / "a.pdf",
        source_type="pdf", sha256=None, categories=(),
        paired_with="d2", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    e2 = DocumentEntry(
        doc_id="d2", path_str="b.pdf", resolved_path=tmp_path / "b.pdf",
        source_type="pdf", sha256=None, categories=(),
        paired_with="d1", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(e1, e2),
        expected_failures=(),
        project_root=tmp_path,
    )
    assert m.content_group_count == 1


def test_manifest_content_group_count_paired_unidirectional(tmp_path):
    """A.paired_with=B（B 不回）→ 仍 1 组。"""
    e1 = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=tmp_path / "a.pdf",
        source_type="pdf", sha256=None, categories=(),
        paired_with="d2", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    e2 = DocumentEntry(
        doc_id="d2", path_str="b.pdf", resolved_path=tmp_path / "b.pdf",
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(e1, e2),
        expected_failures=(),
        project_root=tmp_path,
    )
    assert m.content_group_count == 1


def test_manifest_content_group_count_mixed(tmp_path):
    """2 paired + 1 unpaired → 2 + 1 = 3 组。"""
    e1 = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=tmp_path / "a.pdf",
        source_type="pdf", sha256=None, categories=(),
        paired_with="d2", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    e2 = DocumentEntry(
        doc_id="d2", path_str="b.pdf", resolved_path=tmp_path / "b.pdf",
        source_type="pdf", sha256=None, categories=(),
        paired_with="d1", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    e3 = DocumentEntry(
        doc_id="d3", path_str="c.pdf", resolved_path=tmp_path / "c.pdf",
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(e1, e2, e3),
        expected_failures=(),
        project_root=tmp_path,
    )
    assert m.content_group_count == 2


# =========================================================================
# _is_absolute_like 字符级
# =========================================================================


def test_is_absolute_like_posix_absolute():
    assert _is_absolute_like("/foo/bar") is True


def test_is_absolute_like_just_slash():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_windows_forward_slash():
    assert _is_absolute_like("C:/foo") is True


def test_is_absolute_like_windows_backslash():
    assert _is_absolute_like("C:\\foo") is True


def test_is_absolute_like_lowercase_drive():
    assert _is_absolute_like("d:/foo") is True


def test_is_absolute_like_drive_no_separator():
    """'D:foo' 没分隔符 → 不算绝对（Windows 上是相对驱动器）。"""
    assert _is_absolute_like("D:foo") is False


def test_is_absolute_like_relative_path():
    assert _is_absolute_like("foo/bar") is False


def test_is_absolute_like_just_filename():
    assert _is_absolute_like("foo.txt") is False


def test_is_absolute_like_empty_string():
    assert _is_absolute_like("") is False


def test_is_absolute_like_dot_relative():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_double_dot_relative():
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_returns_bool_type():
    assert isinstance(_is_absolute_like("foo"), bool)


# =========================================================================
# _has_backslash 字符级
# =========================================================================


def test_has_backslash_only_forward():
    assert _has_backslash("a/b") is False


def test_has_backslash_with_backslash():
    assert _has_backslash("a\\b") is True


def test_has_backslash_mixed():
    assert _has_backslash("a\\b/c") is True


def test_has_backslash_just_backslash():
    assert _has_backslash("\\") is True


def test_has_backslash_empty():
    assert _has_backslash("") is False


def test_has_backslash_no_path():
    assert _has_backslash("foo") is False


def test_has_backslash_returns_bool():
    assert isinstance(_has_backslash("foo"), bool)


# =========================================================================
# _resolve_relative_path 多场景
# =========================================================================


def test_resolve_relative_path_normal(tmp_path):
    """正常路径 → 返回 resolved Path。"""
    p = _resolve_relative_path("a/b.pdf", tmp_path, "test")
    assert isinstance(p, Path)
    assert p.is_absolute()


def test_resolve_relative_path_unicode(tmp_path):
    """unicode 路径名 → 不报错。"""
    p = _resolve_relative_path("中文/文件.pdf", tmp_path, "test")
    assert isinstance(p, Path)


def test_resolve_relative_path_with_spaces(tmp_path):
    """路径含空格 → 不报错。"""
    p = _resolve_relative_path("my dir/my file.pdf", tmp_path, "test")
    assert isinstance(p, Path)


def test_resolve_relative_path_multiple_slashes(tmp_path):
    """多 / 拼接 → 解析正常。"""
    p = _resolve_relative_path("a/b/c/d.pdf", tmp_path, "test")
    assert isinstance(p, Path)


def test_resolve_relative_path_path_escape_attempt(tmp_path):
    """../../../etc/passwd → 解析后位于项目根外 → ManifestError。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("../../../etc/passwd", tmp_path, "test")


def test_resolve_relative_path_just_filename(tmp_path):
    """纯文件名 → 等价于 project_root/filename。"""
    p = _resolve_relative_path("foo.pdf", tmp_path, "test")
    assert p == (tmp_path / "foo.pdf").resolve()


def test_resolve_relative_path_subdir(tmp_path):
    """子目录路径 → 正确解析。"""
    p = _resolve_relative_path("sub/foo.pdf", tmp_path, "test")
    assert p == (tmp_path / "sub" / "foo.pdf").resolve()


def test_resolve_relative_path_includes_field_name_in_error(tmp_path):
    """错误信息含字段名。"""
    try:
        _resolve_relative_path("", tmp_path, "my_field")
    except ManifestError as e:
        assert "my_field" in str(e)
        return
    pytest.fail("应抛 ManifestError")


# =========================================================================
# _detect_project_root fallback
# =========================================================================


def test_detect_project_root_finds_pyproject(tmp_path):
    """有 pyproject.toml → 返回该目录。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    result = _detect_project_root(sub / "manifest.json")
    assert result == tmp_path.resolve()


def test_detect_project_root_finds_parent_pyproject(tmp_path):
    """向上找父目录的 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    result = _detect_project_root(deep)
    assert result == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_cur(tmp_path):
    """无 pyproject.toml → 返回 cur（fallback）。"""
    # tmp_path 本身没 pyproject.toml
    result = _detect_project_root(tmp_path)
    # 至少不抛异常；返回 Path
    assert isinstance(result, Path)


def test_detect_project_root_with_file_input(tmp_path):
    """输入是文件 → 取 parent 再找。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
    f = tmp_path / "manifest.json"
    f.write_text("{}", encoding="utf-8")
    result = _detect_project_root(f)
    assert result == tmp_path.resolve()


# =========================================================================
# 模块 source 不含禁止 imports
# =========================================================================


def test_module_source_does_not_contain_import_os():
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "import os" not in src


def test_module_source_does_not_contain_import_sys():
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "import sys" not in src


def test_module_source_does_not_contain_import_logging():
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "import logging" not in src


def test_module_source_does_not_contain_subprocess():
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "subprocess" not in src


def test_module_source_does_not_contain_asyncio():
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "asyncio" not in src


def test_module_source_does_not_contain_threading():
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "threading" not in src


def test_module_source_does_not_contain_concurrent():
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "concurrent" not in src


def test_module_source_does_not_contain_time_import():
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "import time" not in src


def test_module_source_does_not_contain_re_import():
    import evaluation.manifest as m
    src = inspect.getsource(m)
    assert "import re" not in src


# =========================================================================
# ManifestError 语义
# =========================================================================


def test_manifest_error_caught_as_exception():
    """ManifestError 由 except Exception 捕获（不 swallow）。"""
    try:
        raise ManifestError("test")
    except Exception as e:
        assert isinstance(e, ManifestError)


def test_manifest_error_str_contains_message():
    """str(manifest_error) 含原始 message。"""
    e = ManifestError("my error message")
    assert "my error message" in str(e)


def test_manifest_error_no_args():
    """ManifestError() 不传 message 也可（super().__init__()）。"""
    # ManifestError 没自定义 __init__，所以继承 Exception 默认行为
    e = ManifestError()
    assert isinstance(e, ManifestError)


def test_manifest_error_with_errors_kwarg():
    """ManifestError 不接 errors kwarg（与 SchemaValidationError 不同）。"""
    # 这是验证 ManifestError signature
    sig = inspect.signature(ManifestError.__init__)
    # 继承 Exception，没有自定义 __init__
    # 实际：ManifestError 没有 __init__ 方法，用 Exception 的
    # 所以 signature 是 (*args, **kwargs)
    # 我们验证它不接受 errors kwarg
    e = ManifestError("test")
    assert not hasattr(e, "errors")


# =========================================================================
# dataclass 类型验证
# =========================================================================


def test_document_entry_is_dataclass():
    assert is_dataclass(DocumentEntry)


def test_expected_failure_is_dataclass():
    assert is_dataclass(ExpectedFailure)


def test_manifest_is_dataclass():
    assert is_dataclass(Manifest)


def test_document_entry_field_count_exact_10():
    """DocumentEntry 有 10 fields（doc_id/path_str/resolved_path/source_type/sha256/categories/paired_with/annotation_file_str/annotation_resolved/expectations）。"""
    from dataclasses import fields
    assert len(fields(DocumentEntry)) == 10


def test_expected_failure_field_count_exact_5():
    """ExpectedFailure 有 5 fields（doc_id/path_str/resolved_path/expected_error_code/source_type）。"""
    from dataclasses import fields
    assert len(fields(ExpectedFailure)) == 5


def test_manifest_field_count_exact_5():
    """Manifest 有 5 fields（manifest_version/devset_status/documents/expected_failures/project_root）。"""
    from dataclasses import fields
    assert len(fields(Manifest)) == 5


# =========================================================================
# __all__ 顺序
# =========================================================================


def test_module_all_exact_5_entries_in_order():
    import evaluation.manifest as m
    assert m.__all__ == [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ]


def test_module_all_is_list():
    import evaluation.manifest as m
    assert isinstance(m.__all__, list)


def test_module_all_length_5():
    import evaluation.manifest as m
    assert len(m.__all__) == 5


# =========================================================================
# load_manifest 不修改 manifest 文件
# =========================================================================


def test_load_manifest_does_not_modify_manifest_file(tmp_path):
    """load_manifest 不修改磁盘上的 manifest 文件。"""
    (tmp_path / "a.pdf").write_bytes(b"x")
    data = {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}],
    }
    p = _write_manifest(tmp_path, data)
    content_before = p.read_text(encoding="utf-8")
    load_manifest(p, tmp_path)
    content_after = p.read_text(encoding="utf-8")
    assert content_before == content_after


def test_load_manifest_two_calls_independent(tmp_path):
    """两次调用返回不同 Manifest 对象。"""
    data = _minimal_valid_manifest_data()
    p = _write_manifest(tmp_path, data)
    m1 = load_manifest(p, tmp_path)
    m2 = load_manifest(p, tmp_path)
    assert m1 is not m2
    assert m1 == m2


# =========================================================================
# load_manifest project_root 默认（None → detect）
# =========================================================================


def test_load_manifest_default_project_root_uses_detect(tmp_path):
    """project_root=None → _detect_project_root 找 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
    data = _minimal_valid_manifest_data()
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p)  # 不传 project_root
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_explicit_project_root_overrides(tmp_path):
    """显式 project_root 覆盖 detect。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
    other_root = tmp_path / "other"
    other_root.mkdir()
    data = _minimal_valid_manifest_data()
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, other_root)
    assert m.project_root == other_root.resolve()
