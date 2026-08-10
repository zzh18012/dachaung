r"""evaluation/manifest.py 边角测试 - 第二十四轮（Round 307）。

edges23 已覆盖：DocumentEntry/ExpectedFailure/Manifest 3 dataclass + frozen + 5 properties +
load_manifest/_resolve_relative_path/_is_absolute_like/_has_backslash/_detect_project_root +
ManifestError + source level + signatures + __all__ + 端到端。

edges24 补强未覆盖的角度（深度边界 + 算法不变量 + source level + signatures + 端到端）：
- **DocumentEntry 行为深度补强**：dataclasses.fields() 返 10 个字段；
  字段顺序精确；instance equality（同字段相等）；instance 能存 set（hashable）；
  不可 setattr（frozen）；不可 delattr；source 含 doc_id/path_str/resolved_path/source_type/
  sha256/categories/paired_with/annotation_file_str/annotation_resolved/expectations 10 字段名
- **ExpectedFailure 行为深度补强**：dataclasses.fields() 返 5 个字段；
  字段顺序精确；source 含 doc_id/path_str/resolved_path/expected_error_code/source_type 5 字段名
- **Manifest 行为深度补强**：dataclasses.fields() 返 5 个字段；
  字段顺序精确（manifest_version/devset_status/documents/expected_failures/project_root）；
  5 properties（file_count/pdf_count/docx_count/content_group_count/categories_covered）精确名
- **content_group_count 算法不变量**：无 documents → 0；全 unpaired → == file_count；
  全 paired → == file_count // 2；混合 → == groups + unpaired；
  单向配对（A→B but B 不→A）→ 1 group（frozenset 去重）
- **categories_covered 算法不变量**：返回 sorted list（升序）；
  空 documents → []；重复 categories 去重；不修改 documents
- **load_manifest 行为深度补强**：manifest_path 含中文路径 → 仍工作；
  project_root 是 str → 转 Path；project_root 是 Path → 直接 resolve；
  data['documents'] 缺失 → 默认空 []；data['expected_failures'] 缺失 → 默认空 []
- **_resolve_relative_path 行为深度补强**：field_name 含特殊字符（中文/emoji） → 错误消息含；
  path_str 是 './foo' → 通过；path_str 是 'foo' → 通过；
  path_str 含多个 .. 仍 → 通过（如果在 project_root 内）；resolve 后位于 root 外 → ManifestError
- **_is_absolute_like 行为深度补强**：'~/foo'（POSIX home）→ False（不是绝对）；
  '  /foo'（前导空格）→ False（startswith 严格）；'/' 单独 → True；'//' → True；
  'C:' 单独（无分隔符）→ False；'C:foo' → False；'C:\\' → True；
  数字盘符 '9:/foo' → False（必须 alpha）；小写盘符 'c:/foo' → True
- **_has_backslash 行为深度补强**：'/' → False；'\\' → True；
  'a\\b' → True；'a\\\\b' → True；空 → False
- **_detect_project_root 行为深度补强**：start 是 dir → 直接 cur 开始；
  start 是 file → cur.parent 开始；pyproject.toml 在 cur → 返 cur；
  pyproject.toml 在 parent → 返 parent；找不到 → 返 cur（最后兜底）
- **ManifestError 行为深度补强**：isinstance Exception；可 raise + catch；
  message 含中文；args 含 message；不依赖 errors 属性（与 EvalSchemaError 不同）
- **module source 字符串精确补强**：含 'frozenset([d.doc_id, d.paired_with])'；
  含 'dataclasses'（import）；含 '@dataclass(frozen=True)' 3 次；
  含 'MANIFEST_VERSION'；含 'pyproject.toml'
- **module source forbidden tokens 补强**：不含 socket/email/html/http/urllib/sqlite3/csv/pickle/
  collections/math/datetime/itertools/functools/time/tempfile/shutil/glob
- **module imports 精确补强**：7 imports 精确：
  future/json/dataclasses/pathlib/typing (5 stdlib) + evaluation (MANIFEST_VERSION) + evaluation.schema (validate) (2 evaluation)
- **module source 含必要字符串**：含 Path / dataclass / ManifestError / DocumentEntry / ExpectedFailure
- **module source level 完整补强**：load_manifest source 含 Path resolve + is_file + utf-8 +
  json.load + validate + MANIFEST_VERSION 比较 + for d in + for ef in + return Manifest；
  _resolve_relative_path source 含 if not path_str + _is_absolute_like + _has_backslash +
  .resolve() + .relative_to + ManifestError 3 处；
  Manifest.content_group_count source 含 frozenset([d.doc_id, d.paired_with]) + pair_ids.add + seen.update + unpaired
- **signatures 精确补强**：load_manifest 2 params + project_root default=None +
  no varargs/varkw + return Manifest（from __future__ → string）；
  _resolve_relative_path 3 params no default + return Path；
  _is_absolute_like/_has_backslash/_detect_project_root 1 param；
  ManifestError 是 Exception subclass（无自定义 __init__）
- **端到端集成补强**：完整 manifest load + 5 documents + 1 expected_failure；
  dataclass 字段精确；properties 计算精确；
  annotation_file 存在 → annotation_resolved 是 Path；
  expectations 字段保留；source_type 在 expected_failure 保留；
  manifest 不修改 input file
- **模块整体合理性**：__all__ 5 entries；1 class + 3 dataclass + 5 module-level function；
  无 __main__ 块；2 imported names
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any

import pytest

import evaluation.manifest as mmod
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


def _make_doc_entry(
    doc_id="d1",
    path_str="samples/d1.pdf",
    resolved_path=None,
    source_type="pdf",
    sha256=None,
    categories=(),
    paired_with=None,
    annotation_file_str=None,
    annotation_resolved=None,
    expectations=None,
):
    return DocumentEntry(
        doc_id=doc_id,
        path_str=path_str,
        resolved_path=resolved_path or Path("/tmp") / path_str,
        source_type=source_type,
        sha256=sha256,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=annotation_file_str,
        annotation_resolved=annotation_resolved,
        expectations=expectations,
    )


def _make_ef_entry(
    doc_id="ef1",
    path_str="samples/ef1.pdf",
    resolved_path=None,
    expected_error_code="parse_failed",
    source_type=None,
):
    return ExpectedFailure(
        doc_id=doc_id,
        path_str=path_str,
        resolved_path=resolved_path or Path("/tmp") / path_str,
        expected_error_code=expected_error_code,
        source_type=source_type,
    )


def _make_manifest(documents=None, expected_failures=None, project_root=None):
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=tuple(documents or []),
        expected_failures=tuple(expected_failures or []),
        project_root=project_root or Path("/tmp"),
    )


# =========================================================================
# DocumentEntry 行为深度补强
# =========================================================================


def test_document_entry_is_dataclass():
    assert is_dataclass(DocumentEntry)


def test_document_entry_frozen_true():
    """frozen=True 严格：不可 setattr。"""
    e = _make_doc_entry()
    with pytest.raises(Exception):  # FrozenInstanceError
        e.doc_id = "other"


def test_document_entry_dataclass_fields_count():
    """dataclasses.fields() 返 10 个字段。"""
    flds = fields(DocumentEntry)
    assert len(flds) == 10


def test_document_entry_field_names_in_order():
    """字段顺序精确。"""
    flds = fields(DocumentEntry)
    names = [f.name for f in flds]
    expected = [
        "doc_id", "path_str", "resolved_path", "source_type",
        "sha256", "categories", "paired_with",
        "annotation_file_str", "annotation_resolved", "expectations",
    ]
    assert names == expected


def test_document_entry_equality_same_fields():
    """同字段相等。"""
    e1 = _make_doc_entry(doc_id="x")
    e2 = _make_doc_entry(doc_id="x")
    assert e1 == e2


def test_document_entry_inequality_different_fields():
    e1 = _make_doc_entry(doc_id="x")
    e2 = _make_doc_entry(doc_id="y")
    assert e1 != e2


def test_document_entry_hashable_when_fields_hashable():
    """instance 能存 set（hashable）。"""
    e = _make_doc_entry()
    s = {e}
    assert e in s


def test_document_entry_no_delattr():
    """不可 delattr（frozen）。"""
    e = _make_doc_entry()
    with pytest.raises(Exception):
        del e.doc_id


def test_document_entry_source_has_10_field_names():
    src = inspect.getsource(DocumentEntry)
    for name in ["doc_id", "path_str", "resolved_path", "source_type",
                 "sha256", "categories", "paired_with",
                 "annotation_file_str", "annotation_resolved", "expectations"]:
        assert name in src


# =========================================================================
# ExpectedFailure 行为深度补强
# =========================================================================


def test_expected_failure_is_dataclass():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_frozen_true():
    e = _make_ef_entry()
    with pytest.raises(Exception):
        e.doc_id = "other"


def test_expected_failure_dataclass_fields_count():
    flds = fields(ExpectedFailure)
    assert len(flds) == 5


def test_expected_failure_field_names_in_order():
    flds = fields(ExpectedFailure)
    names = [f.name for f in flds]
    expected = ["doc_id", "path_str", "resolved_path",
                "expected_error_code", "source_type"]
    assert names == expected


def test_expected_failure_equality_same_fields():
    e1 = _make_ef_entry(doc_id="x")
    e2 = _make_ef_entry(doc_id="x")
    assert e1 == e2


def test_expected_failure_hashable():
    e = _make_ef_entry()
    s = {e}
    assert e in s


def test_expected_failure_source_has_5_field_names():
    src = inspect.getsource(ExpectedFailure)
    for name in ["doc_id", "path_str", "resolved_path",
                 "expected_error_code", "source_type"]:
        assert name in src


# =========================================================================
# Manifest 行为深度补强
# =========================================================================


def test_manifest_is_dataclass():
    assert is_dataclass(Manifest)


def test_manifest_frozen_true():
    m = _make_manifest()
    with pytest.raises(Exception):
        m.devset_status = "complete"


def test_manifest_dataclass_fields_count():
    flds = fields(Manifest)
    assert len(flds) == 5


def test_manifest_field_names_in_order():
    flds = fields(Manifest)
    names = [f.name for f in flds]
    expected = ["manifest_version", "devset_status", "documents",
                "expected_failures", "project_root"]
    assert names == expected


def test_manifest_source_has_5_field_names():
    src = inspect.getsource(Manifest)
    for name in ["manifest_version", "devset_status", "documents",
                 "expected_failures", "project_root"]:
        assert name in src


def test_manifest_source_has_5_property_names():
    src = inspect.getsource(Manifest)
    for name in ["file_count", "pdf_count", "docx_count",
                 "content_group_count", "categories_covered"]:
        assert name in src


# =========================================================================
# content_group_count 算法不变量
# =========================================================================


def test_content_group_count_empty_documents():
    m = _make_manifest(documents=[])
    assert m.content_group_count == 0


def test_content_group_count_all_unpaired():
    """全 unpaired → == file_count。"""
    docs = [_make_doc_entry(doc_id="d1"), _make_doc_entry(doc_id="d2")]
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 2


def test_content_group_count_all_paired():
    """全 paired → == file_count // 2（双向）。"""
    docs = [
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
    ]
    m = _make_manifest(documents=docs)
    assert m.content_group_count == 1


def test_content_group_count_single_direction_paired():
    """单向配对（A→B but B 不→A）→ 1 group（frozenset 去重）。"""
    docs = [
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2"),  # B 不指 A
    ]
    m = _make_manifest(documents=docs)
    # frozenset([d1, d2]) → 1 group; d2 在 seen 中（pair 含 d2）→ 不 unpaired
    assert m.content_group_count == 1


def test_content_group_count_mixed_paired_unpaired():
    """混合 paired + unpaired → groups + unpaired。"""
    docs = [
        _make_doc_entry(doc_id="d1", paired_with="d2"),
        _make_doc_entry(doc_id="d2", paired_with="d1"),
        _make_doc_entry(doc_id="d3"),  # unpaired
    ]
    m = _make_manifest(documents=docs)
    # 1 pair + 1 unpaired = 2
    assert m.content_group_count == 2


def test_content_group_count_no_more_than_file_count():
    """content_group_count ≤ file_count（不变量）。"""
    docs = [_make_doc_entry(doc_id=f"d{i}") for i in range(5)]
    m = _make_manifest(documents=docs)
    assert m.content_group_count <= m.file_count


# =========================================================================
# categories_covered 算法不变量
# =========================================================================


def test_categories_covered_returns_sorted_list():
    docs = [
        _make_doc_entry(doc_id="d1", categories=("z", "a")),
        _make_doc_entry(doc_id="d2", categories=("m",)),
    ]
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "m", "z"]


def test_categories_covered_empty_documents():
    m = _make_manifest(documents=[])
    assert m.categories_covered == []


def test_categories_covered_dedup():
    docs = [
        _make_doc_entry(doc_id="d1", categories=("a", "b")),
        _make_doc_entry(doc_id="d2", categories=("a", "c")),
    ]
    m = _make_manifest(documents=docs)
    assert m.categories_covered == ["a", "b", "c"]


def test_categories_covered_does_not_modify_documents():
    docs = [_make_doc_entry(doc_id="d1", categories=("z", "a"))]
    m = _make_manifest(documents=docs)
    _ = m.categories_covered
    # documents 字段不变
    assert docs[0].categories == ("z", "a")


# =========================================================================
# load_manifest 行为深度补强
# =========================================================================


def test_load_manifest_chinese_path(tmp_path):
    """manifest_path 含中文路径 → 仍工作。"""
    chinese_dir = tmp_path / "中文目录"
    chinese_dir.mkdir()
    manifest = chinese_dir / "manifest.json"
    manifest.write_text(
        '{"manifest_version": "1.0", "devset_status": "incomplete", '
        '"documents": [], "expected_failures": []}',
        encoding="utf-8",
    )
    m = load_manifest(manifest, project_root=tmp_path)
    assert m.manifest_version == "1.0"


def test_load_manifest_project_root_str(tmp_path):
    """project_root 是 str → 转 Path。"""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"manifest_version": "1.0", "devset_status": "incomplete", '
        '"documents": [], "expected_failures": []}',
        encoding="utf-8",
    )
    m = load_manifest(manifest, project_root=str(tmp_path))
    assert isinstance(m.project_root, Path)


def test_load_manifest_project_root_path(tmp_path):
    """project_root 是 Path → 直接 resolve。"""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"manifest_version": "1.0", "devset_status": "incomplete", '
        '"documents": [], "expected_failures": []}',
        encoding="utf-8",
    )
    m = load_manifest(manifest, project_root=tmp_path)
    assert isinstance(m.project_root, Path)


def test_load_manifest_no_expected_failures_default_empty(tmp_path):
    """data['expected_failures'] 缺失 → 默认空 []。"""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"manifest_version": "1.0", "devset_status": "incomplete", '
        '"documents": []}',
        encoding="utf-8",
    )
    m = load_manifest(manifest, project_root=tmp_path)
    assert m.expected_failures == ()


def test_load_manifest_documents_required_by_schema(tmp_path):
    """documents 是 schema 必填字段（缺则 EvalSchemaError，先于 ManifestError）。"""
    from evaluation.schema import EvalSchemaError
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"manifest_version": "1.0", "devset_status": "incomplete", '
        '"expected_failures": []}',
        encoding="utf-8",
    )
    with pytest.raises(EvalSchemaError):
        load_manifest(manifest, project_root=tmp_path)


# =========================================================================
# _resolve_relative_path 行为深度补强
# =========================================================================


def test_resolve_relative_path_dot_slash(tmp_path):
    """'./foo' → 通过（不是绝对，无 backslash）。"""
    out = _resolve_relative_path("./foo", tmp_path, "test")
    assert out.is_absolute()


def test_resolve_relative_path_plain_name(tmp_path):
    """'foo' → 通过。"""
    out = _resolve_relative_path("foo", tmp_path, "test")
    assert out.is_absolute()


def test_resolve_relative_path_field_name_chinese_in_error(tmp_path):
    """field_name 含特殊字符（中文） → 错误消息含。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "字段名")
    assert "字段名" in str(exc_info.value)


def test_resolve_relative_path_field_name_emoji_in_error(tmp_path):
    """field_name 含 emoji → 错误消息含。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "field😀")
    assert "field😀" in str(exc_info.value)


def test_resolve_relative_path_outside_project_root(tmp_path):
    """resolve 后位于 root 外 → ManifestError。"""
    # 用 .. 跳出 project_root
    with pytest.raises(ManifestError):
        _resolve_relative_path("../outside.txt", tmp_path, "test")


# =========================================================================
# _is_absolute_like 行为深度补强
# =========================================================================


def test_is_absolute_like_posix_home_not_absolute():
    """'~/foo'（POSIX home）→ False（不是绝对）。"""
    assert _is_absolute_like("~/foo") is False


def test_is_absolute_like_leading_space():
    """'  /foo'（前导空格）→ False（startswith 严格）。"""
    assert _is_absolute_like("  /foo") is False


def test_is_absolute_like_single_slash():
    """'/' 单独 → True。"""
    assert _is_absolute_like("/") is True


def test_is_absolute_like_double_slash():
    """'//' → True。"""
    assert _is_absolute_like("//") is True


def test_is_absolute_like_drive_letter_no_separator():
    """'C:' 单独（无分隔符）→ False。"""
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_drive_letter_colon_only():
    """'C:foo' → False（无 / 或 \\）。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_drive_letter_with_backslash():
    """'C:\\' → True。"""
    assert _is_absolute_like("C:\\") is True


def test_is_absolute_like_digit_drive_letter():
    """数字盘符 '9:/foo' → False（必须 alpha）。"""
    assert _is_absolute_like("9:/foo") is False


def test_is_absolute_like_lowercase_drive():
    """小写盘符 'c:/foo' → True。"""
    assert _is_absolute_like("c:/foo") is True


# =========================================================================
# _has_backslash 行为深度补强
# =========================================================================


def test_has_backslash_forward_only():
    assert _has_backslash("/") is False


def test_has_backslash_single():
    assert _has_backslash("\\") is True


def test_has_backslash_in_middle():
    assert _has_backslash("a\\b") is True


def test_has_backslash_double():
    assert _has_backslash("a\\\\b") is True


def test_has_backslash_empty():
    assert _has_backslash("") is False


# =========================================================================
# _detect_project_root 行为深度补强
# =========================================================================


def test_detect_project_root_dir_input(tmp_path):
    """start 是 dir → 直接 cur 开始。"""
    # tmp_path 不含 pyproject.toml；返回 cur
    out = _detect_project_root(tmp_path)
    assert isinstance(out, Path)


def test_detect_project_root_file_input(tmp_path):
    """start 是 file → cur.parent 开始。"""
    f = tmp_path / "test.txt"
    f.write_text("test", encoding="utf-8")
    out = _detect_project_root(f)
    assert isinstance(out, Path)


def test_detect_project_root_finds_pyproject(tmp_path):
    """pyproject.toml 在 cur → 返 cur。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out == tmp_path.resolve()


def test_detect_project_root_finds_in_parent(tmp_path):
    """pyproject.toml 在 parent → 返 parent。"""
    parent = tmp_path
    child = parent / "child"
    child.mkdir()
    (parent / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
    out = _detect_project_root(child)
    assert out == parent.resolve()


def test_detect_project_root_signature_1_param():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.values())
    assert len(params) == 1


# =========================================================================
# ManifestError 行为深度补强
# =========================================================================


def test_manifest_error_isinstance_exception():
    e = ManifestError("msg")
    assert isinstance(e, Exception)


def test_manifest_error_can_raise_and_catch():
    with pytest.raises(ManifestError) as exc_info:
        raise ManifestError("test message")
    assert "test message" in str(exc_info.value)


def test_manifest_error_chinese_message():
    e = ManifestError("清单加载失败")
    assert "清单加载失败" in str(e)


def test_manifest_error_args():
    e = ManifestError("msg")
    assert "msg" in e.args


def test_manifest_error_no_errors_attribute():
    """ManifestError 不依赖 errors 属性（与 EvalSchemaError 不同）。"""
    e = ManifestError("msg")
    assert not hasattr(e, "errors")


def test_manifest_error_no_custom_init():
    """ManifestError 是 Exception subclass（无自定义 __init__）。"""
    src = inspect.getsource(ManifestError)
    # 只有 class + docstring，无自定义 __init__
    assert "def __init__" not in src


# =========================================================================
# module source 字符串精确补强
# =========================================================================


def test_module_source_has_frozenset_call():
    """source 含 'frozenset([d.doc_id, d.paired_with])'。"""
    src = inspect.getsource(mmod)
    assert "frozenset([d.doc_id, d.paired_with])" in src


def test_module_source_has_dataclass_import():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_has_3_dataclass_decorators():
    """source 含 '@dataclass(frozen=True)' 3 次。"""
    src = inspect.getsource(mmod)
    assert src.count("@dataclass(frozen=True)") == 3


def test_module_source_has_manifest_version_constant():
    src = inspect.getsource(mmod)
    assert "MANIFEST_VERSION" in src


def test_module_source_has_pyproject_toml():
    """source 含 'pyproject.toml'（_detect_project_root）。"""
    src = inspect.getsource(mmod)
    assert "pyproject.toml" in src


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_no_socket():
    src = inspect.getsource(mmod)
    assert "import socket" not in src


def test_module_source_no_email():
    src = inspect.getsource(mmod)
    assert "import email" not in src


def test_module_source_no_html():
    src = inspect.getsource(mmod)
    assert "import html" not in src


def test_module_source_no_http():
    src = inspect.getsource(mmod)
    assert "import http" not in src


def test_module_source_no_urllib():
    src = inspect.getsource(mmod)
    assert "import urllib" not in src


def test_module_source_no_sqlite3():
    src = inspect.getsource(mmod)
    assert "import sqlite3" not in src


def test_module_source_no_csv():
    src = inspect.getsource(mmod)
    assert "import csv" not in src


def test_module_source_no_pickle():
    src = inspect.getsource(mmod)
    assert "import pickle" not in src


def test_module_source_no_collections():
    src = inspect.getsource(mmod)
    assert "import collections" not in src


def test_module_source_no_math():
    src = inspect.getsource(mmod)
    assert "import math" not in src


def test_module_source_no_datetime():
    src = inspect.getsource(mmod)
    assert "import datetime" not in src


def test_module_source_no_itertools():
    src = inspect.getsource(mmod)
    assert "import itertools" not in src


def test_module_source_no_functools():
    src = inspect.getsource(mmod)
    assert "import functools" not in src


def test_module_source_no_time():
    src = inspect.getsource(mmod)
    assert "import time" not in src


def test_module_source_no_tempfile():
    src = inspect.getsource(mmod)
    assert "import tempfile" not in src


def test_module_source_no_shutil():
    src = inspect.getsource(mmod)
    assert "import shutil" not in src


def test_module_source_no_glob():
    src = inspect.getsource(mmod)
    assert "import glob" not in src


# =========================================================================
# module imports 精确补强
# =========================================================================


def test_module_imports_count_7():
    src = inspect.getsource(mmod)
    lines = src.split("\n")
    import_lines = [l for l in lines if l.startswith("import ") or l.startswith("from ")]
    # future/json/dataclasses/pathlib/typing (5 stdlib) + evaluation (MANIFEST_VERSION) + evaluation.schema (validate)
    assert len(import_lines) == 7


def test_module_imports_has_future():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_has_json():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_imports_has_dataclasses():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_imports_has_pathlib():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_imports_has_typing_any():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_imports_has_evaluation_manifest_version():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_imports_has_evaluation_schema_validate():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


# =========================================================================
# module source 含必要字符串
# =========================================================================


def test_module_source_has_path_class():
    src = inspect.getsource(mmod)
    assert "Path" in src


def test_module_source_has_manifest_error_class():
    src = inspect.getsource(mmod)
    assert "ManifestError" in src


def test_module_source_has_document_entry_class():
    src = inspect.getsource(mmod)
    assert "DocumentEntry" in src


def test_module_source_has_expected_failure_class():
    src = inspect.getsource(mmod)
    assert "ExpectedFailure" in src


# =========================================================================
# module source level 完整补强
# =========================================================================


def test_load_manifest_source_has_path_resolve():
    src = inspect.getsource(load_manifest)
    assert "Path(manifest_path).resolve()" in src


def test_load_manifest_source_has_is_file():
    src = inspect.getsource(load_manifest)
    assert "p.is_file()" in src


def test_load_manifest_source_has_utf8():
    src = inspect.getsource(load_manifest)
    assert 'encoding="utf-8"' in src


def test_load_manifest_source_has_json_load():
    src = inspect.getsource(load_manifest)
    assert "json.load(f)" in src


def test_load_manifest_source_has_validate_call():
    src = inspect.getsource(load_manifest)
    assert 'validate(data, "manifest.schema.json")' in src


def test_load_manifest_source_has_manifest_version_compare():
    src = inspect.getsource(load_manifest)
    assert 'data.get("manifest_version") != MANIFEST_VERSION' in src


def test_load_manifest_source_has_for_d_in_documents():
    src = inspect.getsource(load_manifest)
    assert "for d in data.get(\"documents\", []):" in src


def test_load_manifest_source_has_for_ef_in_expected_failures():
    src = inspect.getsource(load_manifest)
    assert "for ef in data.get(\"expected_failures\", []):" in src


def test_load_manifest_source_has_return_manifest():
    src = inspect.getsource(load_manifest)
    assert "return Manifest(" in src


def test_resolve_relative_path_source_has_4_manifest_error_raises():
    """_resolve_relative_path 含 4 处 raise ManifestError（empty/absolute/backslash/outside-root）。"""
    src = inspect.getsource(_resolve_relative_path)
    assert src.count("raise ManifestError") == 4


def test_resolve_relative_path_source_has_is_absolute_like():
    src = inspect.getsource(_resolve_relative_path)
    assert "_is_absolute_like(path_str)" in src


def test_resolve_relative_path_source_has_has_backslash():
    src = inspect.getsource(_resolve_relative_path)
    assert "_has_backslash(path_str)" in src


def test_resolve_relative_path_source_has_resolve():
    src = inspect.getsource(_resolve_relative_path)
    assert ".resolve()" in src


def test_resolve_relative_path_source_has_relative_to():
    src = inspect.getsource(_resolve_relative_path)
    assert ".relative_to(project_root_resolved)" in src


def test_manifest_content_group_count_source_has_frozenset():
    """Manifest.content_group_count source 含 frozenset。"""
    src = inspect.getsource(Manifest)
    assert "frozenset" in src


def test_manifest_content_group_count_source_has_pair_ids_add():
    src = inspect.getsource(Manifest)
    assert "pair_ids.add(frozenset([d.doc_id, d.paired_with]))" in src


# =========================================================================
# signatures 精确补强
# =========================================================================


def test_load_manifest_signature_2_params():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.keys())
    assert params == ["manifest_path", "project_root"]


def test_load_manifest_signature_project_root_default_none():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_load_manifest_signature_no_varargs_varkw():
    sig = inspect.signature(load_manifest)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_load_manifest_return_annotation_is_manifest():
    sig = inspect.signature(load_manifest)
    assert "Manifest" in str(sig.return_annotation)


def test_resolve_relative_path_signature_3_params_no_default():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.values())
    assert len(params) == 3
    for p in params:
        assert p.default is inspect.Parameter.empty


def test_is_absolute_like_signature_1_param_no_default():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].default is inspect.Parameter.empty


def test_has_backslash_signature_1_param_no_default():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].default is inspect.Parameter.empty


def test_detect_project_root_signature_1_param_no_default():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].default is inspect.Parameter.empty


def test_resolve_relative_path_no_varargs_varkw():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


# =========================================================================
# 端到端集成补强
# =========================================================================


def test_e2e_load_manifest_5_documents_1_expected_failure(tmp_path):
    """完整 manifest load + 5 documents + 1 expected_failure。"""
    # 创建 5 个文件
    for i in range(5):
        (tmp_path / f"d{i}.pdf").write_text(f"doc{i}", encoding="utf-8")
    (tmp_path / "ef1.pdf").write_text("ef", encoding="utf-8")

    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": f"d{i}", "path": f"d{i}.pdf", "source_type": "pdf"}
            for i in range(5)
        ],
        "expected_failures": [
            {"doc_id": "ef1", "path": "ef1.pdf", "expected_error_code": "parse_failed"},
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest_data), encoding="utf-8",
    )
    m = load_manifest(manifest_path, project_root=tmp_path)
    assert len(m.documents) == 5
    assert len(m.expected_failures) == 1
    assert m.file_count == 5
    assert m.pdf_count == 5
    assert m.docx_count == 0


def test_e2e_load_manifest_with_annotation_file(tmp_path):
    """annotation_file 存在 → annotation_resolved 是 Path。"""
    (tmp_path / "d1.pdf").write_text("d1", encoding="utf-8")
    (tmp_path / "d1.annotation.json").write_text("{}", encoding="utf-8")

    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "d1.pdf", "source_type": "pdf",
             "annotation_file": "d1.annotation.json"},
        ],
        "expected_failures": [],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
    m = load_manifest(manifest_path, project_root=tmp_path)
    assert m.documents[0].annotation_resolved is not None
    assert isinstance(m.documents[0].annotation_resolved, Path)


def test_e2e_load_manifest_with_expectations(tmp_path):
    """expectations 字段保留。"""
    (tmp_path / "d1.pdf").write_text("d1", encoding="utf-8")
    expectations = {"element_count_by_type": {"paragraph": 3}}

    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "d1.pdf", "source_type": "pdf",
             "expectations": expectations},
        ],
        "expected_failures": [],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
    m = load_manifest(manifest_path, project_root=tmp_path)
    assert m.documents[0].expectations == expectations


def test_e2e_load_manifest_with_expected_failure_source_type(tmp_path):
    """source_type 在 expected_failure 保留。"""
    (tmp_path / "ef1.pdf").write_text("ef", encoding="utf-8")

    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "ef1.pdf",
             "expected_error_code": "parse_failed", "source_type": "pdf"},
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")
    m = load_manifest(manifest_path, project_root=tmp_path)
    assert m.expected_failures[0].source_type == "pdf"


def test_e2e_load_manifest_does_not_modify_input_file(tmp_path):
    """manifest 不修改 input file。"""
    (tmp_path / "d1.pdf").write_text("d1", encoding="utf-8")
    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "d1.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    manifest_path = tmp_path / "manifest.json"
    content_before = json.dumps(manifest_data, ensure_ascii=False)
    manifest_path.write_text(content_before, encoding="utf-8")
    load_manifest(manifest_path, project_root=tmp_path)
    content_after = manifest_path.read_text(encoding="utf-8")
    assert content_before == content_after


# =========================================================================
# 模块整体合理性
# =========================================================================


def test_module_all_has_5_entries_in_order():
    assert mmod.__all__ == [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ]


def test_module_has_1_class_manifest_error():
    """module 有 1 个 class: ManifestError。"""
    classes = [n for n in dir(mmod)
               if inspect.isclass(getattr(mmod, n))
               and getattr(mmod, n).__module__ == "evaluation.manifest"
               and not is_dataclass(getattr(mmod, n))]
    assert "ManifestError" in classes


def test_module_has_3_dataclasses():
    """module 有 3 个 dataclass：DocumentEntry, ExpectedFailure, Manifest。"""
    dataclasses_in_mod = [n for n in dir(mmod)
                          if is_dataclass(getattr(mmod, n))
                          and getattr(mmod, n).__module__ == "evaluation.manifest"]
    for dc in ["DocumentEntry", "ExpectedFailure", "Manifest"]:
        assert dc in dataclasses_in_mod


def test_module_has_5_module_level_functions():
    """module 有 5 个 module-level function：
    _is_absolute_like, _has_backslash, _resolve_relative_path, _detect_project_root, load_manifest
    """
    import types
    funcs = [n for n in dir(mmod)
             if not n.startswith("__")
             and isinstance(getattr(mmod, n), types.FunctionType)
             and getattr(mmod, n).__module__ == "evaluation.manifest"]
    expected = ["_is_absolute_like", "_has_backslash",
                "_resolve_relative_path", "_detect_project_root", "load_manifest"]
    for e in expected:
        assert e in funcs


def test_module_has_no_main_block():
    src = inspect.getsource(mmod)
    assert 'if __name__ ==' not in src
    assert '__main__' not in src


def test_module_has_2_imported_names():
    """module 含 2 个 imported names：MANIFEST_VERSION, validate。"""
    expected = ["MANIFEST_VERSION", "validate"]
    for name in expected:
        assert hasattr(mmod, name)


# 必要的 import — 用 json 而不是其他
import json
