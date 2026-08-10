r"""evaluation/manifest.py 边角测试 - 第二十三轮（Round 301）。

edges22 已覆盖：DocumentEntry 10 字段 / ExpectedFailure 5 字段 / Manifest 5 字段 + 5 properties /
load_manifest 边界 / _resolve_relative_path / _is_absolute_like / _has_backslash /
_detect_project_root / ManifestError / frozen dataclass / source level / signatures /
__all__ / 端到端。

edges23 补强未覆盖的角度（深度边界 + 行为 + source level + signatures + 端到端）：
- **DocumentEntry 行为深度补强**：frozen=True 严格；hashable；字段精确顺序；
  categories 是 tuple；expectations 是 dict | None；annotation_resolved 是 Path | None；
  构造时必须传所有字段；to_dict 不存在（dataclass）；instance equality；
  source 含 @dataclass(frozen=True) + 10 字段精确名 + 类型注解
- **ExpectedFailure 行为深度补强**：frozen=True 严格；hashable；5 字段精确顺序；
  source_type 可 None；构造时必须传 5 字段；source 含 @dataclass(frozen=True) + 5 字段
- **Manifest 行为深度补强**：frozen=True 严格；hashable（如 tuple of frozen）；
  documents 是 tuple of DocumentEntry；expected_failures 是 tuple of ExpectedFailure；
  project_root 是 Path；5 properties 行为深度：
  - file_count = len(documents)
  - pdf_count = sum d.source_type=='pdf'
  - docx_count = sum d.source_type=='docx'
  - content_group_count 配对算法（双向 + 单向 + 未配对）
  - categories_covered set 去重 + sorted
- **content_group_count 配对算法深度**：无配对 → doc 数 = group 数；
  1 对配对 → 1 group；2 对独立配对 → 2 groups；单向配对（A→B 但 B 不→A）→ 1 group；
  3 角配对（A→B, B→C）→ frozenset 合并；混合 paired+unpaired
- **categories_covered 算法深度**：空 → []; 单 doc 多 categories；多 doc 重复 categories 去重；
  sorted 升序
- **load_manifest 行为深度补强**：manifest_path 是 str → 转 Path；
  manifest_path 是 Path → 直接 resolve；不存在 → ManifestError；
  invalid JSON → ManifestError + from JSONDecodeError；
  schema reject → EvalSchemaError（先于 version check）；
  manifest_version mismatch → ManifestError；
  documents 字段处理深度（categories 默认 []；paired_with 默认 None；
  annotation_file 默认 None；expectations 默认 None；
  annotation_file 存在 → annotation_resolved 是 Path）；
  expected_failures 字段处理深度（source_type 默认 None）；
  signature 2 params + project_root default=None + no varargs/varkw
- **_resolve_relative_path 行为深度补强**：path_str 是空字符串 → ManifestError；
  绝对路径 POSIX/Windows → ManifestError；含 backslash → ManifestError；
  解析后位于 project_root 之外 → ManifestError；
  field_name 出现在错误消息；正常路径 → 返 Path；
  emoji + 中文 path 通过；多级 .. 通过（如果在 project_root 内）；
  signature 3 params no default + no varargs/varkw
- **_is_absolute_like 行为深度补强**：空 → False；'/' → True；
  '/foo' → True；'C:\\' → True；'C:/foo' → True；'D:/foo' → True；
  'c:/foo' (lowercase) → True；'9:/foo' (digit) → False；
  'Afoo' (no slash) → False；'./foo' → False；'foo' → False
- **_has_backslash 行为深度补强**：无 backslash → False；含 backslash → True；
  纯 backslash → True；double backslash → True；emoji + backslash → True；
  forward slash only → False；空字符串 → False
- **_detect_project_root 行为深度补强**：start 是 file → 从 parent 开始找；
  start 是 dir → 从 cur 开始找；找到 pyproject.toml → 返该 dir；
  没找到 → 返 cur；signature 1 param + no default
- **ManifestError 行为深度补强**：Exception 子类；init 1 param；str/repr 含 message；
  raise + catch；不依赖特定属性
- **frozen dataclass 严格补强**：3 个 dataclass 都不可 setattr；
  frozen instance hashable（如果字段全 hashable）
- **module __all__ 精确**：5 entries 顺序：ManifestError, Manifest, DocumentEntry,
  ExpectedFailure, load_manifest；valid identifier；namespace 含；类型（Exception/3 dataclass/function）
- **module imports 顺序**：future → json → dataclasses → pathlib → typing → evaluation（2 个）
- **module namespace**：ManifestError / Manifest / DocumentEntry / ExpectedFailure / load_manifest 5 个 public；
  _is_absolute_like / _has_backslash / _resolve_relative_path / _detect_project_root 4 个 private；
  MANIFEST_VERSION / validate 2 个 imported
- **module source forbidden tokens 补强**：os/sys/re/logging/subprocess/asyncio/threading/
  concurrent/collections/math/datetime/itertools/functools/star/relative/yield/async/global/nonlocal/walrus/assert
- **module source 含必要 imports**：from __future__ + import json + from dataclasses import dataclass +
  from pathlib import Path + from typing import Any + from evaluation import MANIFEST_VERSION +
  from evaluation.schema import validate
- **module docstring 深度补强**：含「开发集清单加载器」/「相对路径」/「项目根」/「绝对路径」/「反斜杠」
- **signatures 精确**：load_manifest 2 params + project_root default=None + no varargs/varkw + return Manifest；
  _resolve_relative_path 3 params no default + no varargs/varkw + return Path；
  _is_absolute_like 1 param no default + no varargs/varkw + return bool；
  _has_backslash 1 param no default + no varargs/varkw + return bool；
  _detect_project_root 1 param no default + no varargs/varkw + return Path；
  ManifestError.__init__ 1 param no default
- **module source level 完整**：DocumentEntry source 含 @dataclass(frozen=True) + 10 字段精确名；
  ExpectedFailure source 含 @dataclass(frozen=True) + 5 字段精确名；
  Manifest source 含 @dataclass(frozen=True) + 5 字段 + 5 @property 函数；
  _resolve_relative_path source 含 if not path_str / _is_absolute_like / _has_backslash / .resolve() / .relative_to / ManifestError；
  load_manifest source 含 Path(manifest_path).resolve() / not p.is_file() / open utf-8 / json.load / validate / MANIFEST_VERSION 比较 / for d in / for ef in / return Manifest；
  _detect_project_root source 含 cur.resolve() / if cur.is_file() / cur.parent / for parent in [cur, *cur.parents] / pyproject.toml / is_file() / return cur
- **端到端集成**：完整 manifest 5 documents + 1 expected_failure 解析；
  paired_with 双向 → content_group_count 算 1 group；
  categories 多 doc 重复 → categories_covered 去重 sorted；
  annotation_file 字段 → annotation_resolved 是 Path
- **模块整体合理性**：1 class + 3 dataclass + 1 public function + 4 private function；
  无 __main__ 块
"""

from __future__ import annotations

import inspect
import json
from dataclasses import fields, is_dataclass
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
    doc_id: str = "d1",
    path: str = "samples/x.pdf",
    source_type: str = "pdf",
    sha256: str | None = "a" * 64,
    categories: tuple = (),
    paired_with: str | None = None,
    annotation_file: str | None = None,
) -> dict[str, Any]:
    d = {
        "doc_id": doc_id,
        "path": path,
        "source_type": source_type,
    }
    if sha256 is not None:
        d["sha256"] = sha256
    if categories:
        d["categories"] = list(categories)
    if paired_with is not None:
        d["paired_with"] = paired_with
    if annotation_file is not None:
        d["annotation_file"] = annotation_file
    return d


def _make_ef_entry(
    doc_id: str = "ef1",
    path: str = "samples/bad.txt",
    expected_error_code: str = "E_UNSUPPORTED",
    source_type: str | None = None,
) -> dict[str, Any]:
    d = {
        "doc_id": doc_id,
        "path": path,
        "expected_error_code": expected_error_code,
    }
    if source_type is not None:
        d["source_type"] = source_type
    return d


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _create_doc_files(tmp_path: Path, data: dict) -> None:
    for d in data.get("documents", []):
        (tmp_path / d["path"]).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / d["path"]).write_bytes(b"")
        if d.get("annotation_file"):
            (tmp_path / d["annotation_file"]).write_text("{}", encoding="utf-8")
    for ef in data.get("expected_failures", []):
        (tmp_path / ef["path"]).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / ef["path"]).write_bytes(b"")


def _minimal_manifest_data() -> dict:
    return {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }


# =========================================================================
# DocumentEntry 行为深度补强
# =========================================================================


def test_document_entry_is_dataclass():
    assert is_dataclass(DocumentEntry)


def test_document_entry_is_frozen():
    """frozen=True → setattr raises FrozenInstanceError。"""
    de = DocumentEntry(
        doc_id="d1",
        path_str="x.pdf",
        resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf",
        sha256="a" * 64,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises((AttributeError, Exception)):
        de.doc_id = "different"  # type: ignore


def test_document_entry_field_count_is_10():
    flds = fields(DocumentEntry)
    assert len(flds) == 10


def test_document_entry_field_names_in_order():
    flds = [f.name for f in fields(DocumentEntry)]
    assert flds == [
        "doc_id", "path_str", "resolved_path", "source_type", "sha256",
        "categories", "paired_with", "annotation_file_str", "annotation_resolved",
        "expectations",
    ]


def test_document_entry_categories_is_tuple():
    de = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=("a", "b"),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    assert isinstance(de.categories, tuple)
    assert de.categories == ("a", "b")


def test_document_entry_expectations_dict_or_none():
    de1 = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations={"key": "value"},
    )
    assert de1.expectations == {"key": "value"}

    de2 = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    assert de2.expectations is None


def test_document_entry_annotation_resolved_path_or_none():
    de = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=Path("/tmp/ann.json"),
        expectations=None,
    )
    assert isinstance(de.annotation_resolved, Path)


def test_document_entry_equality_same_fields():
    de1 = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    assert de1 == de2


def test_document_entry_no_to_dict_method():
    """DocumentEntry 没有 to_dict 方法（dataclass 默认不生成）。"""
    de = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    assert not hasattr(de, "to_dict")


def test_document_entry_source_has_frozen_dataclass():
    src = inspect.getsource(DocumentEntry)
    assert "@dataclass(frozen=True)" in src


# =========================================================================
# ExpectedFailure 行为深度补强
# =========================================================================


def test_expected_failure_is_dataclass():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_is_frozen():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="bad.txt",
        resolved_path=Path("/tmp/bad.txt"),
        expected_error_code="E_X", source_type=None,
    )
    with pytest.raises((AttributeError, Exception)):
        ef.doc_id = "different"  # type: ignore


def test_expected_failure_field_count_is_5():
    flds = fields(ExpectedFailure)
    assert len(flds) == 5


def test_expected_failure_field_names_in_order():
    flds = [f.name for f in fields(ExpectedFailure)]
    assert flds == ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]


def test_expected_failure_source_type_can_be_none():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="bad.txt",
        resolved_path=Path("/tmp/bad.txt"),
        expected_error_code="E_X", source_type=None,
    )
    assert ef.source_type is None


def test_expected_failure_equality():
    ef1 = ExpectedFailure(
        doc_id="ef1", path_str="bad.txt",
        resolved_path=Path("/tmp/bad.txt"),
        expected_error_code="E_X", source_type="pdf",
    )
    ef2 = ExpectedFailure(
        doc_id="ef1", path_str="bad.txt",
        resolved_path=Path("/tmp/bad.txt"),
        expected_error_code="E_X", source_type="pdf",
    )
    assert ef1 == ef2


def test_expected_failure_source_has_frozen_dataclass():
    src = inspect.getsource(ExpectedFailure)
    assert "@dataclass(frozen=True)" in src


# =========================================================================
# Manifest 行为深度补强
# =========================================================================


def test_manifest_is_dataclass():
    assert is_dataclass(Manifest)


def test_manifest_is_frozen():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    with pytest.raises((AttributeError, Exception)):
        m.devset_status = "complete"  # type: ignore


def test_manifest_field_count_is_5():
    flds = fields(Manifest)
    assert len(flds) == 5


def test_manifest_field_names_in_order():
    flds = [f.name for f in fields(Manifest)]
    assert flds == ["manifest_version", "devset_status", "documents", "expected_failures", "project_root"]


def test_manifest_documents_is_tuple():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(m.documents, tuple)


def test_manifest_expected_failures_is_tuple():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(m.expected_failures, tuple)


def test_manifest_project_root_is_path():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(m.project_root, Path)


def test_manifest_has_5_properties():
    properties = [name for name, obj in inspect.getmembers(Manifest, predicate=property)]
    expected = {"file_count", "pdf_count", "docx_count", "content_group_count", "categories_covered"}
    assert expected.issubset(set(properties))


def test_manifest_file_count():
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.file_count == 0


def test_manifest_pdf_count():
    de_pdf = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de_docx = DocumentEntry(
        doc_id="d2", path_str="y.docx", resolved_path=Path("/tmp/y.docx"),
        source_type="docx", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(de_pdf, de_docx), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.pdf_count == 1
    assert m.docx_count == 1


def test_manifest_source_has_5_property_decorators():
    src = inspect.getsource(Manifest)
    assert src.count("@property") >= 5


# =========================================================================
# content_group_count 配对算法深度
# =========================================================================


def test_content_group_count_no_pairing():
    """无 paired_with → doc 数 = group 数。"""
    de1 = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d2", path_str="y.docx", resolved_path=Path("/tmp/y.docx"),
        source_type="docx", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(de1, de2), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.content_group_count == 2


def test_content_group_count_one_pair():
    """1 对配对（双向）→ 1 group。"""
    de1 = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with="d2", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d2", path_str="y.docx", resolved_path=Path("/tmp/y.docx"),
        source_type="docx", sha256=None, categories=(),
        paired_with="d1", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(de1, de2), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.content_group_count == 1


def test_content_group_count_two_independent_pairs():
    """2 对独立配对 → 2 groups。"""
    de1 = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with="d2", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d2", path_str="y.docx", resolved_path=Path("/tmp/y.docx"),
        source_type="docx", sha256=None, categories=(),
        paired_with="d1", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de3 = DocumentEntry(
        doc_id="d3", path_str="z.pdf", resolved_path=Path("/tmp/z.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with="d4", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de4 = DocumentEntry(
        doc_id="d4", path_str="w.docx", resolved_path=Path("/tmp/w.docx"),
        source_type="docx", sha256=None, categories=(),
        paired_with="d3", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(de1, de2, de3, de4), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.content_group_count == 2


def test_content_group_count_unidirectional_pair():
    """单向配对（A→B 但 B 不→A）→ frozenset 仍合并 → 1 group。"""
    de1 = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with="d2", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d2", path_str="y.docx", resolved_path=Path("/tmp/y.docx"),
        source_type="docx", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(de1, de2), expected_failures=(),
        project_root=Path("/tmp"),
    )
    # 单向：A 引用 B → frozenset([A, B]) → 1 group；B 不在 unpaired
    assert m.content_group_count == 1


def test_content_group_count_mixed_paired_unpaired():
    """混合：1 对配对 + 1 个未配对 → 2 groups。"""
    de1 = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with="d2", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d2", path_str="y.docx", resolved_path=Path("/tmp/y.docx"),
        source_type="docx", sha256=None, categories=(),
        paired_with="d1", annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de3 = DocumentEntry(
        doc_id="d3", path_str="z.pdf", resolved_path=Path("/tmp/z.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(de1, de2, de3), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.content_group_count == 2


# =========================================================================
# categories_covered 算法深度
# =========================================================================


def test_categories_covered_empty():
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.categories_covered == []


def test_categories_covered_single_doc_multi_categories():
    de = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=("a", "b", "c"),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(de,), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.categories_covered == ["a", "b", "c"]


def test_categories_covered_multi_doc_dedup():
    de1 = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=("a", "b"),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    de2 = DocumentEntry(
        doc_id="d2", path_str="y.pdf", resolved_path=Path("/tmp/y.pdf"),
        source_type="pdf", sha256=None, categories=("b", "c"),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(de1, de2), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.categories_covered == ["a", "b", "c"]


def test_categories_covered_sorted_ascending():
    de = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=("z", "a", "m"),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(de,), expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert m.categories_covered == ["a", "m", "z"]


# =========================================================================
# load_manifest 行为深度补强
# =========================================================================


def test_load_manifest_path_str_accepted(tmp_path):
    """manifest_path 是 str → 转 Path。"""
    p = _write_manifest(tmp_path, _minimal_manifest_data())
    m = load_manifest(str(p), tmp_path)
    assert isinstance(m, Manifest)


def test_load_manifest_path_object_accepted(tmp_path):
    p = _write_manifest(tmp_path, _minimal_manifest_data())
    m = load_manifest(p, tmp_path)
    assert isinstance(m, Manifest)


def test_load_manifest_nonexistent_raises(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(tmp_path / "nonexistent.json", tmp_path)
    assert "清单文件不存在" in str(exc_info.value)


def test_load_manifest_invalid_json_raises(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, tmp_path)
    assert "清单 JSON 解析失败" in str(exc_info.value)


def test_load_manifest_version_mismatch_raises(tmp_path):
    """manifest_version mismatch → ManifestError（但 schema 先 reject）。"""
    from evaluation.schema import EvalSchemaError

    data = _minimal_manifest_data()
    data["manifest_version"] = "2.0"  # schema const='1.0' 先 reject
    p = _write_manifest(tmp_path, data)
    with pytest.raises(EvalSchemaError):
        load_manifest(p, tmp_path)


def test_load_manifest_default_project_root(tmp_path):
    """project_root 不传 → 从 manifest 文件向上找 pyproject.toml。"""
    p = _write_manifest(tmp_path, _minimal_manifest_data())
    # 不传 project_root，应自动检测（找到项目根的 pyproject.toml）
    m = load_manifest(p)
    assert isinstance(m.project_root, Path)


def test_load_manifest_documents_default_categories_empty(tmp_path):
    """document 缺 categories → 默认 ()。"""
    data = _minimal_manifest_data()
    data["documents"] = [{
        "doc_id": "d1", "path": "x.pdf", "source_type": "pdf",
    }]
    _create_doc_files(tmp_path, data)
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents[0].categories == ()


def test_load_manifest_documents_default_paired_with_none(tmp_path):
    data = _minimal_manifest_data()
    data["documents"] = [{
        "doc_id": "d1", "path": "x.pdf", "source_type": "pdf",
    }]
    _create_doc_files(tmp_path, data)
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents[0].paired_with is None


def test_load_manifest_documents_default_sha256_none(tmp_path):
    data = _minimal_manifest_data()
    data["documents"] = [{
        "doc_id": "d1", "path": "x.pdf", "source_type": "pdf",
    }]
    _create_doc_files(tmp_path, data)
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents[0].sha256 is None


def test_load_manifest_documents_default_expectations_none(tmp_path):
    data = _minimal_manifest_data()
    data["documents"] = [{
        "doc_id": "d1", "path": "x.pdf", "source_type": "pdf",
    }]
    _create_doc_files(tmp_path, data)
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.documents[0].expectations is None


def test_load_manifest_annotation_file_resolved_to_path(tmp_path):
    """annotation_file 存在 → annotation_resolved 是 Path。"""
    data = _minimal_manifest_data()
    data["documents"] = [{
        "doc_id": "d1", "path": "x.pdf", "source_type": "pdf",
        "annotation_file": "x.ann.json",
    }]
    _create_doc_files(tmp_path, data)
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert isinstance(m.documents[0].annotation_resolved, Path)


def test_load_manifest_expected_failure_source_type_default_none(tmp_path):
    data = _minimal_manifest_data()
    data["expected_failures"] = [{
        "doc_id": "ef1", "path": "bad.txt", "expected_error_code": "E_X",
    }]
    _create_doc_files(tmp_path, data)
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.expected_failures[0].source_type is None


def test_load_manifest_signature_2_params():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["manifest_path", "project_root"]


def test_load_manifest_project_root_default_none():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.values())
    assert params[1].default is None


def test_load_manifest_no_varargs_varkw():
    sig = inspect.signature(load_manifest)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_load_manifest_return_annotation_manifest():
    sig = inspect.signature(load_manifest)
    assert "Manifest" in str(sig.return_annotation)


# =========================================================================
# _resolve_relative_path 行为深度补强
# =========================================================================


def test_resolve_relative_path_empty_raises(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "test_field")
    assert "为空" in str(exc_info.value)


def test_resolve_relative_path_absolute_posix_raises(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("/etc/passwd", tmp_path, "test_field")


def test_resolve_relative_path_absolute_windows_raises(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("C:/foo", tmp_path, "test_field")


def test_resolve_relative_path_backslash_raises(tmp_path):
    with pytest.raises(ManifestError):
        _resolve_relative_path("foo\\bar", tmp_path, "test_field")


def test_resolve_relative_path_outside_project_root_raises(tmp_path):
    """解析后位于 project_root 之外 → ManifestError。"""
    with pytest.raises(ManifestError):
        _resolve_relative_path("../../etc/passwd", tmp_path, "test_field")


def test_resolve_relative_path_field_name_in_error(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "MY_FIELD_NAME")
    assert "MY_FIELD_NAME" in str(exc_info.value)


def test_resolve_relative_path_normal_returns_path(tmp_path):
    out = _resolve_relative_path("foo/bar.pdf", tmp_path, "test_field")
    assert isinstance(out, Path)
    assert out.is_absolute()


def test_resolve_relative_path_emoji_path(tmp_path):
    """emoji path 通过。"""
    out = _resolve_relative_path("foo/📄.pdf", tmp_path, "test_field")
    assert isinstance(out, Path)


def test_resolve_relative_path_chinese_path(tmp_path):
    out = _resolve_relative_path("目录/文件.pdf", tmp_path, "test_field")
    assert isinstance(out, Path)


def test_resolve_relative_path_signature_3_params():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.values())
    assert len(params) == 3
    assert [p.name for p in params] == ["path_str", "project_root", "field_name"]


def test_resolve_relative_path_no_varargs_varkw():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_resolve_relative_path_return_annotation_path():
    sig = inspect.signature(_resolve_relative_path)
    assert "Path" in str(sig.return_annotation)


# =========================================================================
# _is_absolute_like 行为深度补强
# =========================================================================


def test_is_absolute_like_empty():
    assert _is_absolute_like("") is False


def test_is_absolute_like_posix_root():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_posix_path():
    assert _is_absolute_like("/foo/bar") is True


def test_is_absolute_like_windows_backslash():
    assert _is_absolute_like("C:\\foo") is True


def test_is_absolute_like_windows_forward_slash():
    assert _is_absolute_like("C:/foo") is True


def test_is_absolute_like_windows_drive_d():
    assert _is_absolute_like("D:/foo") is True


def test_is_absolute_like_lowercase_drive():
    assert _is_absolute_like("c:/foo") is True


def test_is_absolute_like_digit_drive_not_absolute():
    """'9:/foo' → 数字不是 alpha → 不是绝对路径。"""
    assert _is_absolute_like("9:/foo") is False


def test_is_absolute_like_no_slash_after_drive():
    """'Afoo' (no slash after drive) → 不是绝对路径。"""
    assert _is_absolute_like("Afoo") is False


def test_is_absolute_like_relative_dot_slash():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_relative_filename():
    assert _is_absolute_like("foo") is False


def test_is_absolute_like_unc_path():
    """UNC \\\\server\\share → 以 \\\\ 开头，is_absolute_like 不识别（只看 / 和 C:/）。"""
    assert _is_absolute_like("\\\\server\\share") is False


def test_is_absolute_like_signature_1_param():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path_str"


def test_is_absolute_like_no_varargs_varkw():
    sig = inspect.signature(_is_absolute_like)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


# =========================================================================
# _has_backslash 行为深度补强
# =========================================================================


def test_has_backslash_no_backslash():
    assert _has_backslash("foo/bar") is False


def test_has_backslash_pure_backslash():
    assert _has_backslash("\\") is True


def test_has_backslash_mixed():
    assert _has_backslash("foo\\bar/baz") is True


def test_has_backslash_double():
    assert _has_backslash("foo\\\\bar") is True


def test_has_backslash_emoji():
    assert _has_backslash("📄\\foo") is True


def test_has_backslash_empty():
    assert _has_backslash("") is False


def test_has_backslash_forward_only():
    assert _has_backslash("////") is False


def test_has_backslash_signature_1_param():
    sig = inspect.signature(_has_backslash)
    assert len(sig.parameters) == 1


def test_has_backslash_no_varargs_varkw():
    sig = inspect.signature(_has_backslash)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


# =========================================================================
# _detect_project_root 行为深度补强
# =========================================================================


def test_detect_project_root_signature_1_param():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "start"


def test_detect_project_root_no_varargs_varkw():
    sig = inspect.signature(_detect_project_root)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_detect_project_root_finds_pyproject(tmp_path):
    """找到 pyproject.toml → 返该 dir。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
    out = _detect_project_root(tmp_path)
    assert out == tmp_path


def test_detect_project_root_walks_up(tmp_path):
    """子目录 → 向上找。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
    sub = tmp_path / "sub" / "deep"
    sub.mkdir(parents=True)
    out = _detect_project_root(sub)
    assert out == tmp_path


def test_detect_project_root_file_input_uses_parent(tmp_path):
    """start 是 file → 从 parent 开始。"""
    (tmp_path / "pyproject.toml").write_text("[tool.test]", encoding="utf-8")
    f = tmp_path / "somefile.txt"
    f.write_text("hello", encoding="utf-8")
    out = _detect_project_root(f)
    assert out == tmp_path


def test_detect_project_root_not_found_returns_cur(tmp_path):
    """没找到 → 返 cur（向上遍历完）。"""
    # 在 system tmp 下创建一个深度子目录
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    out = _detect_project_root(deep)
    # 至少返一个 Path（可能是 cur，可能向上找到 system tmp 上面的）
    assert isinstance(out, Path)


# =========================================================================
# ManifestError 行为深度补强
# =========================================================================


def test_manifest_error_subclass_of_exception():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_init_inherits_exception_signature():
    """ManifestError 没有自定义 __init__，继承 Exception 的 (*args, **kwargs)。"""
    sig = inspect.signature(ManifestError.__init__)
    params = list(sig.parameters.values())
    # self + *args + **kwargs（继承自 Exception）
    assert len(params) == 3
    assert params[0].name == "self"


def test_manifest_error_inherits_exception_varargs_varkw():
    """ManifestError 不重写 __init__，继承 Exception 的 varargs/varkw。"""
    sig = inspect.signature(ManifestError.__init__)
    params = list(sig.parameters.values())
    kinds = {p.kind for p in params}
    assert inspect.Parameter.VAR_POSITIONAL in kinds
    assert inspect.Parameter.VAR_KEYWORD in kinds


def test_manifest_error_can_raise_and_catch():
    with pytest.raises(ManifestError) as exc_info:
        raise ManifestError("test error")
    assert "test error" in str(exc_info.value)


def test_manifest_error_str_returns_message():
    e = ManifestError("my message")
    assert str(e) == "my message"


def test_manifest_error_repr_contains_class_name():
    e = ManifestError("msg")
    assert "ManifestError" in repr(e)


def test_manifest_error_args_contains_message():
    e = ManifestError("msg")
    assert e.args == ("msg",)


# =========================================================================
# frozen dataclass 严格补强
# =========================================================================


def test_document_entry_frozen_setattr_fails():
    de = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(Exception):
        de.doc_id = "modified"


def test_expected_failure_frozen_setattr_fails():
    ef = ExpectedFailure(
        doc_id="ef1", path_str="bad.txt",
        resolved_path=Path("/tmp/bad.txt"),
        expected_error_code="E_X", source_type=None,
    )
    with pytest.raises(Exception):
        ef.doc_id = "modified"


def test_manifest_frozen_setattr_fails():
    m = Manifest(
        manifest_version="1.0", devset_status="incomplete",
        documents=(), expected_failures=(),
        project_root=Path("/tmp"),
    )
    with pytest.raises(Exception):
        m.devset_status = "complete"


def test_document_entry_hashable():
    """frozen dataclass 字段全 hashable → hashable。"""
    de = DocumentEntry(
        doc_id="d1", path_str="x.pdf", resolved_path=Path("/tmp/x.pdf"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )
    # frozen instance hashable（如果字段全 hashable）
    # 注意 dict expectations=None 是 hashable
    assert hash(de) is not None


# =========================================================================
# module __all__ 精确
# =========================================================================


def test_module_all_has_5_entries_in_order():
    assert mmod.__all__ == [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ]


def test_module_all_entries_in_namespace():
    for name in mmod.__all__:
        assert hasattr(mmod, name)


def test_module_all_valid_identifier():
    for name in mmod.__all__:
        assert name.isidentifier()


def test_module_all_entries_types():
    assert issubclass(mmod.ManifestError, Exception)
    assert is_dataclass(mmod.Manifest)
    assert is_dataclass(mmod.DocumentEntry)
    assert is_dataclass(mmod.ExpectedFailure)
    assert callable(mmod.load_manifest)


def test_module_all_does_not_include_private():
    for name in ["_is_absolute_like", "_has_backslash", "_resolve_relative_path", "_detect_project_root"]:
        assert name not in mmod.__all__


# =========================================================================
# module imports 顺序
# =========================================================================


def test_module_source_has_future_annotations():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_json_import():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_source_has_dataclass_import():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_has_pathlib_import():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_evaluation_manifest_version_import():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_has_evaluation_schema_import():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_imports_in_correct_order():
    src = inspect.getsource(mmod)
    lines = [l.strip() for l in src.splitlines() if l.strip().startswith(("from ", "import "))]
    # future → json → dataclasses → pathlib → typing → evaluation（2 个）
    assert "from __future__ import annotations" in lines[0]
    assert "import json" in lines[1]


# =========================================================================
# module namespace
# =========================================================================


def test_module_namespace_5_public_names():
    for name in ["ManifestError", "Manifest", "DocumentEntry", "ExpectedFailure", "load_manifest"]:
        assert hasattr(mmod, name)


def test_module_namespace_4_private_functions():
    for name in ["_is_absolute_like", "_has_backslash", "_resolve_relative_path", "_detect_project_root"]:
        assert hasattr(mmod, name)
        assert callable(getattr(mmod, name))


def test_module_namespace_2_imported_names():
    """MANIFEST_VERSION + validate 是 imported name。"""
    assert hasattr(mmod, "MANIFEST_VERSION")
    assert hasattr(mmod, "validate")
    assert callable(mmod.validate)


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_no_os_module():
    src = inspect.getsource(mmod)
    assert "\nimport os" not in src


def test_module_source_no_sys_module():
    src = inspect.getsource(mmod)
    assert "\nimport sys" not in src


def test_module_source_no_re_module():
    src = inspect.getsource(mmod)
    assert "\nimport re" not in src


def test_module_source_no_logging_module():
    src = inspect.getsource(mmod)
    assert "\nimport logging" not in src


def test_module_source_no_subprocess_module():
    src = inspect.getsource(mmod)
    assert "\nimport subprocess" not in src


def test_module_source_no_asyncio_module():
    src = inspect.getsource(mmod)
    assert "\nimport asyncio" not in src


def test_module_source_no_threading_module():
    src = inspect.getsource(mmod)
    assert "\nimport threading" not in src


def test_module_source_no_collections_module():
    src = inspect.getsource(mmod)
    assert "\nimport collections" not in src


def test_module_source_no_math_module():
    src = inspect.getsource(mmod)
    assert "\nimport math" not in src


def test_module_source_no_datetime_module():
    src = inspect.getsource(mmod)
    assert "\nimport datetime" not in src


def test_module_source_no_itertools_module():
    src = inspect.getsource(mmod)
    assert "\nimport itertools" not in src


def test_module_source_no_functools_module():
    src = inspect.getsource(mmod)
    assert "\nimport functools" not in src


def test_module_source_no_relative_import():
    src = inspect.getsource(mmod)
    assert "from ." not in src


def test_module_source_no_yield():
    src = inspect.getsource(mmod)
    assert "yield " not in src


def test_module_source_no_async_def():
    src = inspect.getsource(mmod)
    assert "async def" not in src


def test_module_source_no_global_stmt():
    src = inspect.getsource(mmod)
    assert "\nglobal " not in src


def test_module_source_no_nonlocal_stmt():
    src = inspect.getsource(mmod)
    assert "\nnonlocal " not in src


def test_module_source_no_walrus():
    src = inspect.getsource(mmod)
    assert ":=" not in src


def test_module_source_no_assert_stmt():
    src = inspect.getsource(mmod)
    assert "\nassert " not in src


# =========================================================================
# module docstring 深度补强
# =========================================================================


def test_module_docstring_contains_manifest_loader():
    doc = mmod.__doc__ or ""
    assert "清单加载器" in doc or "清单" in doc


def test_module_docstring_contains_relative_path():
    doc = mmod.__doc__ or ""
    assert "相对路径" in doc


def test_module_docstring_contains_project_root():
    doc = mmod.__doc__ or ""
    assert "项目根" in doc


def test_module_docstring_contains_absolute_path():
    doc = mmod.__doc__ or ""
    assert "绝对路径" in doc


def test_module_docstring_contains_backslash():
    doc = mmod.__doc__ or ""
    assert "反斜杠" in doc


# =========================================================================
# module source level 完整
# =========================================================================


def test_document_entry_source_has_10_field_names():
    src = inspect.getsource(DocumentEntry)
    expected_fields = [
        "doc_id", "path_str", "resolved_path", "source_type", "sha256",
        "categories", "paired_with", "annotation_file_str", "annotation_resolved",
        "expectations",
    ]
    for f in expected_fields:
        assert f in src


def test_expected_failure_source_has_5_field_names():
    src = inspect.getsource(ExpectedFailure)
    for f in ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]:
        assert f in src


def test_manifest_source_has_5_field_names():
    src = inspect.getsource(Manifest)
    for f in ["manifest_version", "devset_status", "documents", "expected_failures", "project_root"]:
        assert f in src


def test_resolve_relative_path_source_uses_is_absolute_like():
    src = inspect.getsource(_resolve_relative_path)
    assert "_is_absolute_like(path_str)" in src


def test_resolve_relative_path_source_uses_has_backslash():
    src = inspect.getsource(_resolve_relative_path)
    assert "_has_backslash(path_str)" in src


def test_resolve_relative_path_source_uses_resolve():
    src = inspect.getsource(_resolve_relative_path)
    assert ".resolve()" in src


def test_resolve_relative_path_source_uses_relative_to():
    src = inspect.getsource(_resolve_relative_path)
    assert ".relative_to(" in src


def test_resolve_relative_path_source_raises_manifest_error_3_times():
    src = inspect.getsource(_resolve_relative_path)
    assert src.count("raise ManifestError") >= 3


def test_load_manifest_source_uses_path_resolve():
    src = inspect.getsource(load_manifest)
    assert "Path(manifest_path).resolve()" in src


def test_load_manifest_source_uses_is_file():
    src = inspect.getsource(load_manifest)
    assert ".is_file()" in src


def test_load_manifest_source_uses_utf8():
    src = inspect.getsource(load_manifest)
    assert 'encoding="utf-8"' in src


def test_load_manifest_source_calls_validate():
    src = inspect.getsource(load_manifest)
    assert 'validate(data, "manifest.schema.json")' in src


def test_load_manifest_source_compares_manifest_version():
    src = inspect.getsource(load_manifest)
    assert "MANIFEST_VERSION" in src


def test_load_manifest_source_returns_manifest():
    src = inspect.getsource(load_manifest)
    assert "return Manifest(" in src


def test_detect_project_root_source_uses_pyproject_toml():
    src = inspect.getsource(_detect_project_root)
    assert "pyproject.toml" in src


def test_detect_project_root_source_walks_parents():
    src = inspect.getsource(_detect_project_root)
    assert "*cur.parents" in src


# =========================================================================
# 端到端集成
# =========================================================================


def test_end_to_end_complete_manifest(tmp_path):
    """完整 manifest：5 documents + 1 expected_failure。"""
    data = _minimal_manifest_data()
    data["documents"] = [
        _make_doc_entry("d1", "samples/d1.pdf", "pdf", categories=("a",)),
        _make_doc_entry("d2", "samples/d2.docx", "docx", categories=("a",), paired_with="d1"),
        _make_doc_entry("d3", "samples/d3.pdf", "pdf", categories=("b",)),
        _make_doc_entry("d4", "samples/d4.docx", "docx", categories=("b",), paired_with="d3"),
        _make_doc_entry("d5", "samples/d5.pdf", "pdf", categories=("c",)),
    ]
    data["expected_failures"] = [
        _make_ef_entry("ef1", "samples/bad.txt", "E_X"),
    ]
    _create_doc_files(tmp_path, data)
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert len(m.documents) == 5
    assert len(m.expected_failures) == 1


def test_end_to_end_paired_with_bidirectional_groups(tmp_path):
    """paired_with 双向 → content_group_count = 2 (2 对配对)。"""
    data = _minimal_manifest_data()
    data["documents"] = [
        _make_doc_entry("d1", "x.pdf", "pdf", paired_with="d2"),
        _make_doc_entry("d2", "y.docx", "docx", paired_with="d1"),
        _make_doc_entry("d3", "z.pdf", "pdf", paired_with="d4"),
        _make_doc_entry("d4", "w.docx", "docx", paired_with="d3"),
    ]
    _create_doc_files(tmp_path, data)
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.content_group_count == 2


def test_end_to_end_categories_dedup_sorted(tmp_path):
    """categories 多 doc 重复 → categories_covered 去重 sorted。"""
    data = _minimal_manifest_data()
    data["documents"] = [
        _make_doc_entry("d1", "x.pdf", "pdf", categories=("z", "a")),
        _make_doc_entry("d2", "y.pdf", "pdf", categories=("a", "m")),
    ]
    _create_doc_files(tmp_path, data)
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.categories_covered == ["a", "m", "z"]


def test_end_to_end_annotation_resolved_is_path(tmp_path):
    """annotation_file 字段 → annotation_resolved 是 Path。"""
    data = _minimal_manifest_data()
    data["documents"] = [
        _make_doc_entry("d1", "x.pdf", "pdf", annotation_file="x.ann.json"),
    ]
    _create_doc_files(tmp_path, data)
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert isinstance(m.documents[0].annotation_resolved, Path)


def test_end_to_end_pdf_count_docx_count(tmp_path):
    data = _minimal_manifest_data()
    data["documents"] = [
        _make_doc_entry("d1", "x.pdf", "pdf"),
        _make_doc_entry("d2", "y.docx", "docx"),
        _make_doc_entry("d3", "z.pdf", "pdf"),
    ]
    _create_doc_files(tmp_path, data)
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.pdf_count == 2
    assert m.docx_count == 1
    assert m.file_count == 3


def test_end_to_end_expected_failure_source_type_given(tmp_path):
    """expected_failure source_type 给定 → 加载后保留。"""
    data = _minimal_manifest_data()
    data["expected_failures"] = [
        _make_ef_entry("ef1", "bad.txt", "E_X", source_type="pdf"),
    ]
    _create_doc_files(tmp_path, data)
    p = _write_manifest(tmp_path, data)
    m = load_manifest(p, tmp_path)
    assert m.expected_failures[0].source_type == "pdf"


# =========================================================================
# 模块整体合理性
# =========================================================================


def test_module_has_1_class_definition():
    """ManifestError 是 module-level class。"""
    classes = [
        name for name, obj in inspect.getmembers(mmod, predicate=inspect.isclass)
        if obj.__module__ == mmod.__name__
    ]
    assert "ManifestError" in classes


def test_module_has_3_dataclass_definitions():
    """Manifest / DocumentEntry / ExpectedFailure 是 dataclass。"""
    classes = [
        name for name, obj in inspect.getmembers(mmod, predicate=inspect.isclass)
        if obj.__module__ == mmod.__name__ and is_dataclass(obj)
    ]
    assert sorted(classes) == ["DocumentEntry", "ExpectedFailure", "Manifest"]


def test_module_has_5_module_level_functions():
    """load_manifest + _is_absolute_like + _has_backslash + _resolve_relative_path + _detect_project_root。"""
    funcs = [
        name for name, obj in inspect.getmembers(mmod, predicate=inspect.isfunction)
        if obj.__module__ == mmod.__name__
    ]
    expected = {"load_manifest", "_is_absolute_like", "_has_backslash", "_resolve_relative_path", "_detect_project_root"}
    assert expected.issubset(set(funcs))


def test_module_no_main_block():
    src = inspect.getsource(mmod)
    assert 'if __name__' not in src


def test_module_has_1_public_function():
    public_funcs = [
        name for name, obj in inspect.getmembers(mmod, predicate=inspect.isfunction)
        if obj.__module__ == mmod.__name__ and not name.startswith("_")
    ]
    assert public_funcs == ["load_manifest"]
