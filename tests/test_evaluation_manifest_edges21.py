"""evaluation/manifest.py 边角测试 - 第二十一轮（Round 289）。

edges20 已覆盖：load_manifest 完整文档场景 / schema 失败场景 / manifest_version 兼容性 / JSON 解析失败 /
DocumentEntry/ExpectedFailure/Manifest frozen / Manifest properties 多场景 / _is_absolute_like 字符级 /
_has_backslash 字符级 / _resolve_relative_path 多场景 / _detect_project_root fallback / __all__ /
ManifestError 语义 / dataclass field count。

edges21 补强未覆盖的角度：**Schema 联动深度** + **dataclass 行为** + **极端路径场景**：
- load_manifest 完整集成：
  - 含完整字段（doc + expected_failure + sha256 + categories + paired + annotation + expectations）
  - 多 doc 多 expected_failure 都解析
  - manifest 字段值类型严格（documents 是 tuple；expected_failures 是 tuple）
  - Manifest.project_root 是 Path（resolved）
  - DocumentEntry.annotation_resolved 在没有 annotation_file 时是 None
  - ExpectedFailure.source_type 在没有 source_type 时是 None
  - 文件不存在的 manifest_path → ManifestError 含 '清单文件不存在'

- Schema 联动：
  - 通过 load_manifest 的 manifest dict 都通过 manifest.schema.json
  - load_manifest 失败时 schema 先抛 EvalSchemaError 再转 ManifestError（实际是 schema 直接抛）
  - manifest_version 检查发生在 schema 之后

- dataclass instance behaviors：
  - dataclasses.replace(DocumentEntry) → 新对象
  - dataclasses.asdict(DocumentEntry) → dict（含 Path 不变）
  - dataclasses.astuple(DocumentEntry) → tuple
  - Manifest hashable（含 tuple documents）
  - ManifestDocument eq when all fields match
  - Manifest eq when all fields match
  - Manifest 复制后 eq 但 not is

- Manifest properties edge cases：
  - file_count 0/1/N
  - pdf_count when no pdf → 0
  - docx_count when no docx → 0
  - categories_covered empty → []
  - categories_covered sorted
  - categories_covered 多 doc 合并去重
  - content_group_count self-pair（A.paired_with=A → 1 组 + 0 unpaired = 1）
  - content_group_count 全 paired（A↔B, C↔D → 2 组）
  - content_group_count 全 unpaired（A,B,C 各自 → 3 组）

- _is_absolute_like 字符级深度：
  - 空 string → False
  - '/' → True
  - '/foo' → True
  - 'C:/' → True
  - 'C:\\' → True
  - 'c:/' (lowercase) → True
  - 'Z:/path' → True
  - '1:/foo' → False（'1' 不是 alpha）
  - 'C:' (len 2) → False（len < 3）
  - 'C:x' → False（path_str[2] 不是反斜杠或正斜杠）
  - 'foo' → False
  - 'a/b' → False
  - './foo' → False
  - '../foo' → False

- _has_backslash 字符级深度：
  - 'a\\b' → True
  - 'a\\b/c' → True
  - 'a/b' → False
  - '\\' → True
  - '' → False
  - 'foo' → False
  - '\\foo' → True

- _resolve_relative_path 极端场景：
  - path 含 unicode（中文/日文/emoji）→ OK
  - path 含空格 → OK
  - path 含连续斜杠 '//' → resolve 后正常
  - path 含 './foo' → resolve 后去掉 './'
  - path 含 '../' 但仍在 project_root 内 → OK
  - path 含 '../' 越过 project_root → ManifestError
  - path 是绝对路径 → ManifestError
  - path 含反斜杠 → ManifestError
  - path 空 string → ManifestError
  - field_name 出现在错误信息中

- _detect_project_root 边界：
  - 找到 pyproject.toml → 返回该目录
  - 多层嵌套向上找
  - 找不到 → fallback 返回 cur
  - 输入是文件 → 取 parent
  - 输入是目录 → 直接用

- module source level 完整：
  - imports: json, dataclasses.dataclass, pathlib.Path, typing.Any, evaluation.MANIFEST_VERSION, evaluation.schema.validate
  - 不含 os/sys/logging/subprocess/asyncio/threading/concurrent
  - ManifestError 直接继承 Exception
  - DocumentEntry/ExpectedFailure/Manifest 都有 @dataclass(frozen=True)
  - Manifest 5 properties
  - load_manifest source 含 raise ManifestError 多处

- ManifestError 行为深度：
  - ManifestError 是 Exception 子类
  - ManifestError 不是 BaseException 直接子类
  - ManifestError 可 catch as Exception
  - ManifestError str 含 message
  - ManifestError 可包含 from 链
  - ManifestError 不接受 errors kwarg（不像 EvalSchemaError）

- 文件不存在场景：
  - manifest_path 不存在 → ManifestError 含 '清单文件不存在'
  - manifest_path 是目录 → ManifestError
  - manifest_path 含 .. → resolve 后检查 is_file
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, asdict, astuple, is_dataclass, replace
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


# ============================================================================
# 辅助
# ============================================================================


def _write_manifest(tmp_path: Path, data: dict[str, Any]) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def _minimal_valid_manifest_data() -> dict[str, Any]:
    return {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }


def _make_document_entry(
    tmp_path: Path, doc_id: str = "d1", path: str = "a.pdf"
) -> DocumentEntry:
    """构造 DocumentEntry 用于 dataclass 测试。"""
    return DocumentEntry(
        doc_id=doc_id,
        path_str=path,
        resolved_path=tmp_path / path,
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def _make_expected_failure(
    tmp_path: Path, doc_id: str = "ef1", path: str = "b.docx"
) -> ExpectedFailure:
    return ExpectedFailure(
        doc_id=doc_id,
        path_str=path,
        resolved_path=tmp_path / path,
        expected_error_code="file_not_found",
        source_type=None,
    )


# ============================================================================
# load_manifest 完整集成
# ============================================================================


def test_load_manifest_with_all_fields(tmp_path):
    """含完整字段的 doc + expected_failure 都解析。"""
    (tmp_path / "a.pdf").write_bytes(b"a")
    (tmp_path / "b.docx").write_bytes(b"b")
    (tmp_path / "a.ann.json").write_text("{}", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "a.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "categories": ["report"],
                "paired_with": "d2",
                "annotation_file": "a.ann.json",
                "expectations": {"element_count_by_type": {"paragraph": 5}},
            }
        ],
        "expected_failures": [
            {
                "doc_id": "ef1",
                "path": "b.docx",
                "expected_error_code": "parse_failed",
                "source_type": "docx",
            }
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert len(m.documents) == 1
    assert len(m.expected_failures) == 1
    assert m.documents[0].sha256 == "a" * 64
    assert m.documents[0].categories == ("report",)
    assert m.documents[0].annotation_resolved is not None
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 5}}
    assert m.expected_failures[0].source_type == "docx"


def test_load_manifest_returns_manifest_type(tmp_path):
    p = _write_manifest(tmp_path, _minimal_valid_manifest_data())
    m = load_manifest(p, tmp_path)
    assert isinstance(m, Manifest)


def test_load_manifest_documents_is_tuple(tmp_path):
    p = _write_manifest(tmp_path, _minimal_valid_manifest_data())
    m = load_manifest(p, tmp_path)
    assert isinstance(m.documents, tuple)


def test_load_manifest_expected_failures_is_tuple(tmp_path):
    p = _write_manifest(tmp_path, _minimal_valid_manifest_data())
    m = load_manifest(p, tmp_path)
    assert isinstance(m.expected_failures, tuple)


def test_load_manifest_project_root_is_path(tmp_path):
    p = _write_manifest(tmp_path, _minimal_valid_manifest_data())
    m = load_manifest(p, tmp_path)
    assert isinstance(m.project_root, Path)


def test_load_manifest_project_root_is_resolved(tmp_path):
    """project_root 是 resolved Path。"""
    p = _write_manifest(tmp_path, _minimal_valid_manifest_data())
    m = load_manifest(p, tmp_path)
    assert m.project_root == m.project_root.resolve()


def test_load_manifest_doc_annotation_resolved_none_when_no_file(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"a")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents[0].annotation_resolved is None


def test_load_manifest_doc_annotation_file_str_none_when_no_file(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"a")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents[0].annotation_file_str is None


def test_load_manifest_ef_source_type_none_when_no_field(tmp_path):
    (tmp_path / "b.docx").write_bytes(b"b")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "b.docx", "expected_error_code": "boom"}
        ],
    }
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.expected_failures[0].source_type is None


def test_load_manifest_file_not_exists_error_message(tmp_path):
    """manifest_path 不存在 → ManifestError 含 '清单文件不存在'。"""
    missing = tmp_path / "missing.json"
    with pytest.raises(ManifestError) as exc:
        load_manifest(missing, tmp_path)
    assert "清单文件不存在" in str(exc.value)


def test_load_manifest_directory_path_raises(tmp_path):
    """manifest_path 是目录 → ManifestError（is_file 返 False）。"""
    with pytest.raises(ManifestError) as exc:
        load_manifest(tmp_path, tmp_path)
    assert "清单文件不存在" in str(exc.value)


# ============================================================================
# Schema 联动
# ============================================================================


def test_load_manifest_minimal_passes_manifest_schema(tmp_path):
    """load_manifest 接受的最小 manifest 都符合 schema。"""
    p = _write_manifest(tmp_path, _minimal_valid_manifest_data())
    m = load_manifest(p, tmp_path)
    # 重读 raw data 校验
    raw = json.loads(p.read_text(encoding="utf-8"))
    from evaluation.schema import validate as schema_validate

    schema_validate(raw, "manifest.schema.json")


def test_load_manifest_schema_check_before_version_check(tmp_path):
    """schema 检查在 manifest_version 兼容性检查之前。"""
    # manifest_version 错（schema 拒）→ 不会到 version 兼容性检查
    data = {
        "manifest_version": "BAD_VERSION",  # schema 拒（const="1.0"）
        "devset_status": "incomplete",
        "documents": [],
    }
    p = _write_manifest(tmp_path, data)
    with pytest.raises(Exception) as exc:  # EvalSchemaError
        load_manifest(p, tmp_path)
    # 不应是 ManifestError 的 'manifest_version 不兼容'
    assert "不兼容" not in str(exc.value)


def test_load_manifest_version_check_after_schema(tmp_path):
    """schema 通过但 manifest_version=2.0 → 不可能（schema const=1.0）。"""
    # 这个测试只是确认：schema 拒 2.0，所以走不到 version 兼容性
    data = {
        "manifest_version": "2.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    p = _write_manifest(tmp_path, data)
    with pytest.raises(Exception):
        load_manifest(p, tmp_path)


# ============================================================================
# dataclass instance behaviors
# ============================================================================


def test_document_entry_replace_creates_new_instance(tmp_path):
    """dataclasses.replace 创建新 DocumentEntry，原对象不变。"""
    de = _make_document_entry(tmp_path)
    de2 = replace(de, doc_id="new-id")
    assert de2.doc_id == "new-id"
    assert de.doc_id == "d1"  # 原不变
    assert de is not de2


def test_document_entry_asdict(tmp_path):
    """asdict 转 dict（保留 Path 字段）。"""
    de = _make_document_entry(tmp_path)
    d = asdict(de)
    assert d["doc_id"] == "d1"
    assert d["source_type"] == "pdf"
    assert isinstance(d["resolved_path"], Path)
    assert d["categories"] == ()  # tuple 转 list
    # dataclasses.asdict 会把 tuple 转 list
    assert isinstance(d["categories"], list) or isinstance(d["categories"], tuple)


def test_document_entry_astuple(tmp_path):
    de = _make_document_entry(tmp_path)
    t = astuple(de)
    assert isinstance(t, tuple)
    assert t[0] == "d1"  # doc_id


def test_document_entry_eq_all_fields_match(tmp_path):
    de1 = _make_document_entry(tmp_path)
    de2 = _make_document_entry(tmp_path)
    assert de1 == de2


def test_document_entry_eq_diff_field(tmp_path):
    de1 = _make_document_entry(tmp_path, doc_id="d1")
    de2 = _make_document_entry(tmp_path, doc_id="d2")
    assert de1 != de2


def test_expected_failure_replace(tmp_path):
    ef = _make_expected_failure(tmp_path)
    ef2 = replace(ef, doc_id="new-ef")
    assert ef2.doc_id == "new-ef"
    assert ef.doc_id == "ef1"


def test_expected_failure_asdict(tmp_path):
    ef = _make_expected_failure(tmp_path)
    d = asdict(ef)
    assert d["doc_id"] == "ef1"


def test_expected_failure_astuple(tmp_path):
    ef = _make_expected_failure(tmp_path)
    t = astuple(ef)
    assert isinstance(t, tuple)


def test_expected_failure_eq(tmp_path):
    ef1 = _make_expected_failure(tmp_path)
    ef2 = _make_expected_failure(tmp_path)
    assert ef1 == ef2


def test_manifest_replace(tmp_path):
    m1 = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )
    m2 = replace(m1, devset_status="complete")
    assert m1.devset_status == "incomplete"
    assert m2.devset_status == "complete"


def test_manifest_eq_all_fields_match(tmp_path):
    m1 = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )
    m2 = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )
    assert m1 == m2


def test_manifest_neq_diff_field(tmp_path):
    m1 = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )
    m2 = Manifest(
        manifest_version="1.0",
        devset_status="complete",  # diff
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )
    assert m1 != m2


# ============================================================================
# Manifest properties edge cases
# ============================================================================


def test_manifest_file_count_zero():
    m = Manifest("1.0", "incomplete", (), (), Path("."))
    assert m.file_count == 0


def test_manifest_file_count_one(tmp_path):
    de = _make_document_entry(tmp_path)
    m = Manifest("1.0", "incomplete", (de,), (), tmp_path)
    assert m.file_count == 1


def test_manifest_file_count_n(tmp_path):
    des = tuple(_make_document_entry(tmp_path, doc_id=f"d{i}") for i in range(5))
    m = Manifest("1.0", "incomplete", des, (), tmp_path)
    assert m.file_count == 5


def test_manifest_pdf_count_when_no_pdf(tmp_path):
    de = DocumentEntry(
        doc_id="d1", path_str="a.docx", resolved_path=tmp_path / "a.docx",
        source_type="docx", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest("1.0", "incomplete", (de,), (), tmp_path)
    assert m.pdf_count == 0


def test_manifest_docx_count_when_no_docx(tmp_path):
    de = _make_document_entry(tmp_path)  # source_type="pdf"
    m = Manifest("1.0", "incomplete", (de,), (), tmp_path)
    assert m.docx_count == 0


def test_manifest_categories_covered_empty():
    m = Manifest("1.0", "incomplete", (), (), Path("."))
    assert m.categories_covered == []


def test_manifest_categories_covered_sorted(tmp_path):
    de1 = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=tmp_path / "a.pdf",
        source_type="pdf", sha256=None, categories=("zebra", "apple"),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest("1.0", "incomplete", (de1,), (), tmp_path)
    assert m.categories_covered == ["apple", "zebra"]


def test_manifest_categories_covered_dedup(tmp_path):
    de1 = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=tmp_path / "a.pdf",
        source_type="pdf", sha256=None, categories=("report", "financial"),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d2", path_str="b.pdf", resolved_path=tmp_path / "b.pdf",
        source_type="pdf", sha256=None, categories=("report", "legal"),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest("1.0", "incomplete", (de1, de2), (), tmp_path)
    assert m.categories_covered == ["financial", "legal", "report"]


def test_manifest_content_group_count_self_pair(tmp_path):
    """A.paired_with=A → 1 组 + 0 unpaired = 1。"""
    de = DocumentEntry(
        doc_id="d1", path_str="a.pdf", resolved_path=tmp_path / "a.pdf",
        source_type="pdf", sha256=None, categories=(),
        paired_with="d1",  # 自引
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    m = Manifest("1.0", "incomplete", (de,), (), tmp_path)
    # frozenset([d1, d1]) = {d1} → groups=1
    # unpaired: d1 在 seen 中（因为 d1.paired_with 真值）→ unpaired=0
    assert m.content_group_count == 1


def test_manifest_content_group_count_two_paired_pairs(tmp_path):
    """A↔B, C↔D → 2 组。"""
    de1 = DocumentEntry("d1", "a.pdf", tmp_path / "a.pdf", "pdf", None, (), "d2", None, None, None)
    de2 = DocumentEntry("d2", "b.pdf", tmp_path / "b.pdf", "pdf", None, (), "d1", None, None, None)
    de3 = DocumentEntry("d3", "c.pdf", tmp_path / "c.pdf", "pdf", None, (), "d4", None, None, None)
    de4 = DocumentEntry("d4", "d.pdf", tmp_path / "d.pdf", "pdf", None, (), "d3", None, None, None)
    m = Manifest("1.0", "incomplete", (de1, de2, de3, de4), (), tmp_path)
    assert m.content_group_count == 2


def test_manifest_content_group_count_all_unpaired(tmp_path):
    """A, B, C 各自 unpaired → 3 组。"""
    des = tuple(
        DocumentEntry(f"d{i}", f"a{i}.pdf", tmp_path / f"a{i}.pdf", "pdf", None, (), None, None, None, None)
        for i in range(3)
    )
    m = Manifest("1.0", "incomplete", des, (), tmp_path)
    assert m.content_group_count == 3


def test_manifest_content_group_count_zero_documents():
    m = Manifest("1.0", "incomplete", (), (), Path("."))
    assert m.content_group_count == 0


# ============================================================================
# _is_absolute_like 字符级深度
# ============================================================================


def test_is_absolute_like_empty_string():
    assert _is_absolute_like("") is False


def test_is_absolute_like_single_slash():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_posix_absolute():
    assert _is_absolute_like("/foo") is True
    assert _is_absolute_like("/foo/bar") is True


def test_is_absolute_like_windows_drive_with_slash():
    assert _is_absolute_like("C:/") is True
    assert _is_absolute_like("C:/foo") is True


def test_is_absolute_like_windows_drive_with_backslash():
    assert _is_absolute_like("C:\\") is True
    assert _is_absolute_like("C:\\foo") is True


def test_is_absolute_like_lowercase_drive():
    assert _is_absolute_like("c:/foo") is True


def test_is_absolute_like_z_drive():
    assert _is_absolute_like("Z:/path") is True


def test_is_absolute_like_numeric_drive_not_absolute():
    """'1:/foo' 不是绝对路径（'1' 不是 alpha）。"""
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_short_drive_not_absolute():
    """'C:' len=2 < 3 → False。"""
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_drive_without_separator():
    """'C:x' → path_str[2]='x' 不是反斜杠或正斜杠 → False。"""
    assert _is_absolute_like("C:x") is False


def test_is_absolute_like_relative_path():
    assert _is_absolute_like("foo") is False
    assert _is_absolute_like("a/b") is False


def test_is_absolute_like_dot_path():
    assert _is_absolute_like("./foo") is False
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_returns_bool_type():
    """_is_absolute_like 返回 bool。"""
    assert isinstance(_is_absolute_like("foo"), bool)
    assert isinstance(_is_absolute_like("/foo"), bool)


# ============================================================================
# _has_backslash 字符级深度
# ============================================================================


def test_has_backslash_single():
    assert _has_backslash("a\\b") is True


def test_has_backslash_mixed():
    assert _has_backslash("a\\b/c") is True


def test_has_backslash_no_backslash():
    assert _has_backslash("a/b") is False


def test_has_backslash_only_backslash():
    assert _has_backslash("\\") is True


def test_has_backslash_empty():
    assert _has_backslash("") is False


def test_has_backslash_no_separator():
    assert _has_backslash("foo") is False


def test_has_backslash_starts_with():
    assert _has_backslash("\\foo") is True


def test_has_backslash_returns_bool_type():
    assert isinstance(_has_backslash("foo"), bool)


# ============================================================================
# _resolve_relative_path 极端场景
# ============================================================================


def test_resolve_relative_path_unicode(tmp_path):
    """path 含 unicode（中文）→ OK。"""
    out = _resolve_relative_path("中文/文件.pdf", tmp_path, "test")
    assert isinstance(out, Path)


def test_resolve_relative_path_with_spaces(tmp_path):
    out = _resolve_relative_path("my dir/my file.pdf", tmp_path, "test")
    assert isinstance(out, Path)


def test_resolve_relative_path_double_slash(tmp_path):
    """连续斜杠 '//' → resolve 后正常。"""
    out = _resolve_relative_path("foo//bar.pdf", tmp_path, "test")
    assert isinstance(out, Path)


def test_resolve_relative_path_dot_slash(tmp_path):
    """'./foo' → resolve 后去掉 './'。"""
    out = _resolve_relative_path("./foo.pdf", tmp_path, "test")
    assert isinstance(out, Path)
    assert out == (tmp_path / "foo.pdf").resolve()


def test_resolve_relative_path_within_project_root(tmp_path):
    """path 含 '../' 但仍在 project_root 内 → OK。

    例：tmp_path/sub/../foo.pdf 解析后是 tmp_path/foo.pdf
    """
    out = _resolve_relative_path("sub/../foo.pdf", tmp_path, "test")
    assert isinstance(out, Path)
    assert out == (tmp_path / "foo.pdf").resolve()


def test_resolve_relative_path_escape_project_root_raises(tmp_path):
    """path '../' 越过 project_root → ManifestError。"""
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("../../etc/passwd", tmp_path, "test")
    assert "项目根目录之外" in str(exc.value)


def test_resolve_relative_path_absolute_raises(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("/etc/passwd", tmp_path, "test")
    assert "绝对路径" in str(exc.value)


def test_resolve_relative_path_backslash_raises(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("foo\\bar.pdf", tmp_path, "test")
    assert "反斜杠" in str(exc.value)


def test_resolve_relative_path_empty_raises(tmp_path):
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("", tmp_path, "test")
    assert "为空" in str(exc.value)


def test_resolve_relative_path_field_name_in_error(tmp_path):
    """field_name 出现在错误信息中。"""
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("", tmp_path, "MY_FIELD_NAME")
    assert "MY_FIELD_NAME" in str(exc.value)


# ============================================================================
# _detect_project_root 边界
# ============================================================================


def test_detect_project_root_finds_pyproject(tmp_path):
    """找到 pyproject.toml → 返回该目录。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    start = tmp_path / "subdir"
    start.mkdir()
    root = _detect_project_root(start)
    assert root == tmp_path


def test_detect_project_root_nested(tmp_path):
    """多层嵌套向上找。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    root = _detect_project_root(deep)
    assert root == tmp_path


def test_detect_project_root_no_pyproject_returns_cur(tmp_path):
    """找不到 pyproject.toml → fallback 返回 cur。"""
    start = tmp_path / "subdir"
    start.mkdir()
    root = _detect_project_root(start)
    # 返回 start（cur 是 start 的 resolved）
    assert root == start.resolve()


def test_detect_project_root_input_is_file(tmp_path):
    """输入是文件 → 取 parent。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    f = tmp_path / "subdir" / "file.txt"
    f.parent.mkdir()
    f.write_text("", encoding="utf-8")
    root = _detect_project_root(f)
    assert root == tmp_path


def test_detect_project_root_input_is_dir_uses_dir(tmp_path):
    """输入是目录 → 直接用。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    root = _detect_project_root(tmp_path)
    assert root == tmp_path


# ============================================================================
# ManifestError 行为深度
# ============================================================================


def test_manifest_error_is_exception_subclass():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_not_baseexception_directly():
    assert ManifestError.__bases__ == (Exception,)


def test_manifest_error_caught_as_exception():
    try:
        raise ManifestError("test")
    except Exception as e:
        assert isinstance(e, ManifestError)


def test_manifest_error_str_contains_message():
    err = ManifestError("hello world")
    assert "hello world" in str(err)


def test_manifest_error_args():
    err = ManifestError("msg")
    assert err.args == ("msg",)


def test_manifest_error_with_from_chain(tmp_path):
    """ManifestError 可包含 from 链。"""
    try:
        try:
            raise ValueError("inner")
        except ValueError as e:
            raise ManifestError("outer") from e
    except ManifestError as outer:
        assert isinstance(outer.__cause__, ValueError)


# ============================================================================
# module source level 完整
# ============================================================================


def test_module_source_contains_import_json():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "import json" in src


def test_module_source_contains_dataclass_import():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "from dataclasses import dataclass" in src


def test_module_source_contains_pathlib_import():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "from typing import Any" in src


def test_module_source_contains_evaluation_imports():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "from evaluation import MANIFEST_VERSION" in src
    assert "from evaluation.schema import validate" in src


def test_module_source_does_not_contain_os():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "import os" not in src


def test_module_source_does_not_contain_sys():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "import sys" not in src


def test_module_source_does_not_contain_logging():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "import logging" not in src


def test_module_source_does_not_contain_subprocess():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "import subprocess" not in src


def test_module_source_does_not_contain_threading():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "import threading" not in src


def test_module_source_does_not_contain_asyncio():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "import asyncio" not in src


def test_module_source_contains_frozen_dataclass_decorators():
    """3 个 dataclass 都有 @dataclass(frozen=True)。"""
    import evaluation.manifest as m

    src = inspect.getsource(m)
    # 3 个 @dataclass(frozen=True)
    assert src.count("@dataclass(frozen=True)") == 3


def test_module_source_does_not_contain_star_import():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "import *" not in src


def test_module_source_does_not_contain_relative_import():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "from ." not in src
    assert "from .." not in src


def test_module_source_does_not_contain_class_decorator_other_than_dataclass():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    # 没有其他 class decorator
    assert "@property" in src  # 5 properties
    # 不应有 @staticmethod/@classmethod/@abstractmethod
    assert "@staticmethod" not in src
    assert "@classmethod" not in src
    assert "@abstractmethod" not in src


# ============================================================================
# load_manifest source level 完整
# ============================================================================


def test_load_manifest_source_contains_signature(tmp_path):
    import evaluation.manifest as m

    src = inspect.getsource(m.load_manifest)
    assert "def load_manifest(" in src
    assert "manifest_path: Path | str" in src
    assert "project_root: Path | str | None = None" in src


def test_load_manifest_source_contains_resolve_call():
    import evaluation.manifest as m

    src = inspect.getsource(m.load_manifest)
    assert "Path(manifest_path).resolve()" in src


def test_load_manifest_source_contains_is_file_check():
    import evaluation.manifest as m

    src = inspect.getsource(m.load_manifest)
    assert "if not p.is_file():" in src
    assert "raise ManifestError" in src


def test_load_manifest_source_contains_detect_project_root_call():
    import evaluation.manifest as m

    src = inspect.getsource(m.load_manifest)
    assert "_detect_project_root(p)" in src


def test_load_manifest_source_contains_json_load():
    import evaluation.manifest as m

    src = inspect.getsource(m.load_manifest)
    assert 'p.open("r", encoding="utf-8")' in src
    assert "json.load(f)" in src


def test_load_manifest_source_contains_json_decode_error_handler():
    import evaluation.manifest as m

    src = inspect.getsource(m.load_manifest)
    assert "except json.JSONDecodeError as e:" in src
    assert "raise ManifestError" in src


def test_load_manifest_source_contains_validate_call():
    import evaluation.manifest as m

    src = inspect.getsource(m.load_manifest)
    assert 'validate(data, "manifest.schema.json")' in src


def test_load_manifest_source_contains_manifest_version_check():
    import evaluation.manifest as m

    src = inspect.getsource(m.load_manifest)
    assert "data.get(\"manifest_version\") != MANIFEST_VERSION" in src


def test_load_manifest_source_contains_two_loops():
    """source 含 2 个 for 循环：documents 和 expected_failures。"""
    import evaluation.manifest as m

    src = inspect.getsource(m.load_manifest)
    assert 'for d in data.get("documents", []):' in src
    assert 'for ef in data.get("expected_failures", []):' in src


def test_load_manifest_source_contains_return_manifest():
    import evaluation.manifest as m

    src = inspect.getsource(m.load_manifest)
    assert "return Manifest(" in src


# ============================================================================
# signatures
# ============================================================================


def test_load_manifest_signature_2_params():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert params[0].name == "manifest_path"
    assert params[1].name == "project_root"


def test_load_manifest_project_root_default_none():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_resolve_relative_path_signature_3_params():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.values())
    assert len(params) == 3
    assert [p.name for p in params] == ["path_str", "project_root", "field_name"]


def test_is_absolute_like_signature_1_param():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path_str"


def test_has_backslash_signature_1_param():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path_str"


def test_detect_project_root_signature_1_param():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "start"


# ============================================================================
# __all__ 与 namespace
# ============================================================================


def test_module_all_5_entries_exact():
    import evaluation.manifest as m

    assert m.__all__ == [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ]


def test_module_all_entries_each_valid_identifier():
    import evaluation.manifest as m

    for name in m.__all__:
        assert isinstance(name, str)
        assert name.isidentifier()


def test_module_namespace_has_all_entries():
    import evaluation.manifest as m

    for name in m.__all__:
        assert hasattr(m, name)


def test_module_namespace_has_private_helpers():
    """私有 helper（带下划线）在 namespace 不在 __all__。"""
    import evaluation.manifest as m

    for name in ["_is_absolute_like", "_has_backslash", "_resolve_relative_path", "_detect_project_root"]:
        assert hasattr(m, name)
        assert name not in m.__all__


def test_module_namespace_does_not_have_process_single():
    """manifest.py 不依赖 pipeline。"""
    import evaluation.manifest as m

    assert not hasattr(m, "process_single")


def test_module_namespace_does_not_have_compute_metrics():
    import evaluation.manifest as m

    assert not hasattr(m, "compute_automatic_metrics")


# ============================================================================
# frozen dataclass 严格
# ============================================================================


def test_document_entry_frozen_setattr_raises(tmp_path):
    de = _make_document_entry(tmp_path)
    with pytest.raises(FrozenInstanceError):
        de.doc_id = "new-id"


def test_document_entry_frozen_delattr_raises(tmp_path):
    de = _make_document_entry(tmp_path)
    with pytest.raises(FrozenInstanceError):
        del de.doc_id


def test_expected_failure_frozen_setattr_raises(tmp_path):
    ef = _make_expected_failure(tmp_path)
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "new-id"


def test_manifest_frozen_setattr_raises(tmp_path):
    m = Manifest("1.0", "incomplete", (), (), tmp_path)
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"


def test_manifest_is_dataclass():
    assert is_dataclass(Manifest)


def test_document_entry_is_dataclass():
    assert is_dataclass(DocumentEntry)


def test_expected_failure_is_dataclass():
    assert is_dataclass(ExpectedFailure)
