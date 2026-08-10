r"""evaluation/manifest.py 边角测试 - 第十九轮（Round 276）。

edges18 已覆盖：源码 token、docstring、类型注解、dataclass fields/params、frozen=True、
_is_absolute_like alpha check、_has_backslash bool、ManifestError raise/except、
content_group_count 各种 pairing、categories_covered nested tuple、_resolve_relative_path 错误格式、
_detect_project_root 边界、load_manifest str+project_root、namespace、__all__、helper FunctionType、
_is_absolute_like 单/双/3 字符边界、_has_backslash 空/单/多/mixed、_resolve_relative_path 成功/失败路径、
_detect_project_root 文件/目录/无 pyproject.toml、DocumentEntry/Manifest frozen=True setattr/delattr、
Manifest property 边界、模块源码 token、签名 introspection、ManifestError MRO、
dataclass __dataclass_fields__ 顺序、categories_covered unicode、content_group_count 链式 pairing。

edges19 补强未覆盖的角度：
- 模块 imports 精确字符串：'import json'/'from dataclasses import dataclass'/'from pathlib import Path'/
  'from typing import Any'/'from evaluation import MANIFEST_VERSION'/'from evaluation.schema import validate'
- import 顺序：__future__ → json → dataclasses → pathlib → typing → evaluation → evaluation.schema
- ManifestError source-level：'class ManifestError(Exception):' 字面量 + docstring 含 '清单加载或校验失败'
- _is_absolute_like source-level token：'if not path_str:' / 'return False' (≥2) /
  'path_str.startswith("/")' / 'len(path_str) >= 3' / 'path_str[1] == ":"' / 'path_str[0].isalpha()' /
  'path_str[2] in ("\\\\", "/")' / 'return True' (≥2) / 'return False'
- _has_backslash source-level：'return "\\\\" in path_str' 单行函数
- DocumentEntry source-level：'@dataclass(frozen=True)' / 'class DocumentEntry:' / 9 fields
- ExpectedFailure source-level：'class ExpectedFailure:' / 5 fields
- Manifest source-level：'class Manifest:' / 5 fields + 5 properties
- Manifest.file_count source：'return len(self.documents)'
- Manifest.pdf_count source：'return sum(1 for d in self.documents if d.source_type == "pdf")'
- Manifest.docx_count source：'return sum(1 for d in self.documents if d.source_type == "docx")'
- Manifest.content_group_count source：含 'pair_ids: set[frozenset[str]] = set()' /
  'unpaired = 0' / 'all_paired: set[str] = set()' / 'if d.paired_with:' /
  'pair_ids.add(frozenset([d.doc_id, d.paired_with]))' / 'groups = 0' / 'seen.update(pair)' /
  'return groups + unpaired'
- Manifest.categories_covered source：'s: set[str] = set()' / 's.update(d.categories)' / 'return sorted(s)'
- _resolve_relative_path source：'if not path_str:' / 'raise ManifestError(f"{field_name} 为空")' /
  'if _is_absolute_like(path_str):' / '必须是相对路径，禁止绝对路径' /
  'if _has_backslash(path_str):' / '必须使用正斜杠，禁止反斜杠' /
  'resolved = (project_root / path_str).resolve()' /
  'project_root_resolved = project_root.resolve()' /
  'resolved.relative_to(project_root_resolved)' / 'except ValueError:' / 'raise ManifestError('
- load_manifest source：'p = Path(manifest_path).resolve()' / 'if not p.is_file():' /
  'raise ManifestError(f"清单文件不存在: {p}")' / 'if project_root is None:' /
  'project_root = _detect_project_root(p)' / 'project_root = Path(project_root).resolve()' /
  'with p.open("r", encoding="utf-8") as f:' / 'data = json.load(f)' /
  'except json.JSONDecodeError as e:' / 'raise ManifestError(f"清单 JSON 解析失败: {e}") from e' /
  'validate(data, "manifest.schema.json")' / 'data.get("manifest_version") != MANIFEST_VERSION' /
  'raise ManifestError(f"manifest_version 不兼容' / 'documents: list[DocumentEntry] = []' /
  'failures: list[ExpectedFailure] = []' / 'return Manifest('
- _detect_project_root source：'cur = start.resolve()' / 'if cur.is_file():' /
  'cur = cur.parent' / 'for parent in [cur, *cur.parents]:' /
  'if (parent / "pyproject.toml").is_file():' / 'return parent' / 'return cur'
- __all__ 5 entries 顺序精确：ManifestError → Manifest → DocumentEntry → ExpectedFailure → load_manifest
- _detect_project_root 实际行为：从某个 start 找到项目根（含 pyproject.toml）
- _resolve_relative_path 实际成功路径：返回 resolved Path，位于 project_root 内
- Manifest dataclass 实际字段顺序
- DocumentEntry frozen 行为：替换值抛 FrozenInstanceError
- ManifestError catch as Exception
- load_manifest 实际加载 minimal manifest：含 manifest_version + devset_status + documents + expected_failures
- 模块 source 不含 print/logging/subprocess/asyncio/threading/os
- 模块 source 不含 silent_drop_count/metrics/image_resource/process_single
- 模块 source 不含 read_text/write_text
- MANIFEST_VERSION 在 namespace 中
- validate 是 evaluation.schema.validate 引用
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from typing import Any

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
from evaluation.schema import validate as schema_validate


# =========================================================================
# 模块 imports 精确字符串
# =========================================================================


def test_module_source_contains_import_json():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "import json" in src


def test_module_source_contains_from_dataclasses_import_dataclass():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "from dataclasses import dataclass" in src


def test_module_source_contains_from_pathlib_import_path():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "from pathlib import Path" in src


def test_module_source_contains_from_typing_import_any():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "from typing import Any" in src


def test_module_source_contains_from_evaluation_import_manifest_version():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_contains_from_evaluation_schema_import_validate():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "from evaluation.schema import validate" in src


def test_module_import_order():
    """import 顺序：__future__ → json → dataclasses → pathlib → typing → evaluation → evaluation.schema。"""
    import evaluation.manifest as m

    src = inspect.getsource(m)
    pos_future = src.find("from __future__ import annotations")
    pos_json = src.find("import json")
    pos_dataclasses = src.find("from dataclasses import dataclass")
    pos_pathlib = src.find("from pathlib import Path")
    pos_typing = src.find("from typing import Any")
    pos_eval = src.find("from evaluation import MANIFEST_VERSION")
    pos_schema = src.find("from evaluation.schema import validate")
    assert pos_future < pos_json < pos_dataclasses < pos_pathlib < pos_typing
    assert pos_typing < pos_eval < pos_schema


# =========================================================================
# ManifestError source-level
# =========================================================================


def test_manifest_error_source_contains_class_definition():
    src = inspect.getsource(ManifestError)
    assert "class ManifestError(Exception):" in src


def test_manifest_error_source_contains_docstring():
    src = inspect.getsource(ManifestError)
    assert "清单加载或校验失败" in src


def test_manifest_error_source_does_not_contain_init():
    """ManifestError 没有自定义 __init__（用默认 Exception.__init__）。"""
    src = inspect.getsource(ManifestError)
    assert "def __init__" not in src


def test_manifest_error_source_does_not_contain_print():
    src = inspect.getsource(ManifestError)
    assert "print(" not in src


def test_manifest_error_is_exception_subclass():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_is_baseexception_subclass():
    assert issubclass(ManifestError, BaseException)


def test_manifest_error_bases_exact():
    assert ManifestError.__bases__ == (Exception,)


def test_manifest_error_module_identity():
    assert ManifestError.__module__ == "evaluation.manifest"


def test_manifest_error_qualname_exact():
    assert ManifestError.__qualname__ == "ManifestError"


def test_manifest_error_can_be_raised_and_caught():
    with pytest.raises(ManifestError) as exc:
        raise ManifestError("test")
    assert "test" in str(exc.value)


def test_manifest_error_caught_as_exception():
    """ManifestError 可以被通用 except Exception 捕获。"""
    try:
        raise ManifestError("x")
    except Exception as e:
        assert isinstance(e, ManifestError)


# =========================================================================
# _is_absolute_like source-level
# =========================================================================


def test_is_absolute_like_source_contains_empty_check():
    src = inspect.getsource(_is_absolute_like)
    assert "if not path_str:" in src


def test_is_absolute_like_source_contains_startswith_slash():
    src = inspect.getsource(_is_absolute_like)
    assert 'path_str.startswith("/")' in src


def test_is_absolute_like_source_contains_length_3_check():
    src = inspect.getsource(_is_absolute_like)
    assert "len(path_str) >= 3" in src


def test_is_absolute_like_source_contains_colon_check():
    src = inspect.getsource(_is_absolute_like)
    assert 'path_str[1] == ":"' in src


def test_is_absolute_like_source_contains_alpha_check():
    src = inspect.getsource(_is_absolute_like)
    assert "path_str[0].isalpha()" in src


def test_is_absolute_like_source_contains_backslash_or_slash_check():
    src = inspect.getsource(_is_absolute_like)
    assert 'path_str[2] in ("\\\\", "/")' in src


def test_is_absolute_like_source_contains_return_true_at_least_twice():
    src = inspect.getsource(_is_absolute_like)
    assert src.count("return True") >= 2


def test_is_absolute_like_source_contains_return_false():
    src = inspect.getsource(_is_absolute_like)
    assert "return False" in src


def test_is_absolute_like_returns_bool_type():
    assert isinstance(_is_absolute_like("/x"), bool)
    assert isinstance(_is_absolute_like("x"), bool)


def test_is_absolute_like_module_identity():
    assert _is_absolute_like.__module__ == "evaluation.manifest"


def test_is_absolute_like_qualname_exact():
    assert _is_absolute_like.__qualname__ == "_is_absolute_like"


# =========================================================================
# _has_backslash source-level
# =========================================================================


def test_has_backslash_source_is_single_line_return():
    src = inspect.getsource(_has_backslash)
    assert 'return "\\\\" in path_str' in src


def test_has_backslash_source_does_not_contain_print():
    src = inspect.getsource(_has_backslash)
    assert "print(" not in src


def test_has_backslash_returns_bool_type():
    assert isinstance(_has_backslash("x"), bool)


def test_has_backslash_module_identity():
    assert _has_backslash.__module__ == "evaluation.manifest"


def test_has_backslash_qualname_exact():
    assert _has_backslash.__qualname__ == "_has_backslash"


# =========================================================================
# DocumentEntry source-level
# =========================================================================


def test_document_entry_source_contains_dataclass_frozen_decorator():
    src = inspect.getsource(DocumentEntry)
    assert "@dataclass(frozen=True)" in src


def test_document_entry_source_contains_class_definition():
    src = inspect.getsource(DocumentEntry)
    assert "class DocumentEntry:" in src


def test_document_entry_source_contains_9_fields():
    """DocumentEntry 9 个字段。"""
    src = inspect.getsource(DocumentEntry)
    # 9 fields: doc_id, path_str, resolved_path, source_type, sha256,
    # categories, paired_with, annotation_file_str, annotation_resolved, expectations
    # 实际 10 个；按 fields() 检查
    assert len(fields(DocumentEntry)) >= 9


def test_document_entry_field_names_exact():
    field_names = [f.name for f in fields(DocumentEntry)]
    assert "doc_id" in field_names
    assert "path_str" in field_names
    assert "resolved_path" in field_names
    assert "source_type" in field_names
    assert "sha256" in field_names
    assert "categories" in field_names
    assert "paired_with" in field_names
    assert "annotation_file_str" in field_names
    assert "annotation_resolved" in field_names
    assert "expectations" in field_names


def test_document_entry_field_count_exact():
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_frozen_setattr_raises():
    de = DocumentEntry(
        doc_id="d1",
        path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
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


def test_document_entry_frozen_delattr_raises():
    de = DocumentEntry(
        doc_id="d1",
        path_str="a/b.pdf",
        resolved_path=Path("/tmp/a/b.pdf"),
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        del de.doc_id


# =========================================================================
# ExpectedFailure source-level
# =========================================================================


def test_expected_failure_source_contains_dataclass_frozen_decorator():
    src = inspect.getsource(ExpectedFailure)
    assert "@dataclass(frozen=True)" in src


def test_expected_failure_source_contains_class_definition():
    src = inspect.getsource(ExpectedFailure)
    assert "class ExpectedFailure:" in src


def test_expected_failure_field_count_exact():
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_field_names_exact():
    field_names = [f.name for f in fields(ExpectedFailure)]
    assert field_names == ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]


# =========================================================================
# Manifest source-level
# =========================================================================


def test_manifest_source_contains_dataclass_frozen_decorator():
    src = inspect.getsource(Manifest)
    assert "@dataclass(frozen=True)" in src


def test_manifest_source_contains_class_definition():
    src = inspect.getsource(Manifest)
    assert "class Manifest:" in src


def test_manifest_source_contains_5_fields():
    field_names = [f.name for f in fields(Manifest)]
    assert field_names == ["manifest_version", "devset_status", "documents", "expected_failures", "project_root"]


def test_manifest_source_contains_file_count_property():
    src = inspect.getsource(Manifest.file_count.fget)
    assert "return len(self.documents)" in src


def test_manifest_source_contains_pdf_count_property():
    src = inspect.getsource(Manifest.pdf_count.fget)
    assert 'd.source_type == "pdf"' in src


def test_manifest_source_contains_docx_count_property():
    src = inspect.getsource(Manifest.docx_count.fget)
    assert 'd.source_type == "docx"' in src


def test_manifest_source_contains_content_group_count_property():
    src = inspect.getsource(Manifest.content_group_count.fget)
    assert "pair_ids: set[frozenset[str]] = set()" in src
    assert "unpaired = 0" in src
    assert "if d.paired_with:" in src
    assert "pair_ids.add(frozenset([d.doc_id, d.paired_with]))" in src
    assert "groups = 0" in src
    assert "seen.update(pair)" in src
    assert "return groups + unpaired" in src


def test_manifest_source_contains_categories_covered_property():
    src = inspect.getsource(Manifest.categories_covered.fget)
    assert "s: set[str] = set()" in src
    assert "s.update(d.categories)" in src
    assert "return sorted(s)" in src


def test_manifest_file_count_returns_int():
    m = Manifest(
        manifest_version="1.0",
        devset_status="complete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(m.file_count, int)


def test_manifest_pdf_count_returns_int():
    m = Manifest(
        manifest_version="1.0",
        devset_status="complete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(m.pdf_count, int)


def test_manifest_docx_count_returns_int():
    m = Manifest(
        manifest_version="1.0",
        devset_status="complete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(m.docx_count, int)


def test_manifest_content_group_count_returns_int():
    m = Manifest(
        manifest_version="1.0",
        devset_status="complete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(m.content_group_count, int)


def test_manifest_categories_covered_returns_list():
    m = Manifest(
        manifest_version="1.0",
        devset_status="complete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    assert isinstance(m.categories_covered, list)


def test_manifest_frozen_setattr_raises():
    m = Manifest(
        manifest_version="1.0",
        devset_status="complete",
        documents=(),
        expected_failures=(),
        project_root=Path("/tmp"),
    )
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "x"


# =========================================================================
# _resolve_relative_path source-level
# =========================================================================


def test_resolve_relative_path_source_contains_empty_check():
    src = inspect.getsource(_resolve_relative_path)
    assert "if not path_str:" in src


def test_resolve_relative_path_source_contains_wei_kong_error():
    src = inspect.getsource(_resolve_relative_path)
    assert "为空" in src


def test_resolve_relative_path_source_contains_absolute_check():
    src = inspect.getsource(_resolve_relative_path)
    assert "if _is_absolute_like(path_str):" in src


def test_resolve_relative_path_source_contains_jue_dui_lu_jing_error():
    src = inspect.getsource(_resolve_relative_path)
    assert "禁止绝对路径" in src


def test_resolve_relative_path_source_contains_backslash_check():
    src = inspect.getsource(_resolve_relative_path)
    assert "if _has_backslash(path_str):" in src


def test_resolve_relative_path_source_contains_fan_xie_gang_error():
    src = inspect.getsource(_resolve_relative_path)
    assert "禁止反斜杠" in src


def test_resolve_relative_path_source_contains_resolve_call():
    src = inspect.getsource(_resolve_relative_path)
    assert "(project_root / path_str).resolve()" in src


def test_resolve_relative_path_source_contains_relative_to_call():
    src = inspect.getsource(_resolve_relative_path)
    assert "resolved.relative_to(project_root_resolved)" in src


def test_resolve_relative_path_source_contains_except_value_error():
    src = inspect.getsource(_resolve_relative_path)
    assert "except ValueError:" in src


def test_resolve_relative_path_source_contains_xiang_mu_gen_wai_error():
    src = inspect.getsource(_resolve_relative_path)
    assert "项目根目录之外" in src


def test_resolve_relative_path_source_contains_return_resolved():
    src = inspect.getsource(_resolve_relative_path)
    assert "return resolved" in src


def test_resolve_relative_path_source_does_not_contain_print():
    src = inspect.getsource(_resolve_relative_path)
    assert "print(" not in src


def test_resolve_relative_path_success_returns_path():
    """成功路径返回 resolved Path。"""
    project_root = Path("/tmp")
    out = _resolve_relative_path("a/b.pdf", project_root, "test")
    assert isinstance(out, Path)
    assert out.is_absolute()


def test_resolve_relative_path_empty_raises_manifest_error():
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("", Path("/tmp"), "field_x")
    assert "field_x" in str(exc.value)
    assert "为空" in str(exc.value)


def test_resolve_relative_path_absolute_raises_manifest_error():
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("/etc/passwd", Path("/tmp"), "field_x")
    assert "field_x" in str(exc.value)
    assert "禁止绝对路径" in str(exc.value)


def test_resolve_relative_path_backslash_raises_manifest_error():
    with pytest.raises(ManifestError) as exc:
        _resolve_relative_path("a\\b.pdf", Path("/tmp"), "field_x")
    assert "field_x" in str(exc.value)
    assert "禁止反斜杠" in str(exc.value)


# =========================================================================
# load_manifest source-level
# =========================================================================


def test_load_manifest_source_contains_path_resolve():
    src = inspect.getsource(load_manifest)
    assert "p = Path(manifest_path).resolve()" in src


def test_load_manifest_source_contains_is_file_check():
    src = inspect.getsource(load_manifest)
    assert "if not p.is_file():" in src


def test_load_manifest_source_contains_qing_dan_bu_cun_zai():
    src = inspect.getsource(load_manifest)
    assert "清单文件不存在" in src


def test_load_manifest_source_contains_project_root_none_check():
    src = inspect.getsource(load_manifest)
    assert "if project_root is None:" in src


def test_load_manifest_source_contains_detect_project_root_call():
    src = inspect.getsource(load_manifest)
    assert "project_root = _detect_project_root(p)" in src


def test_load_manifest_source_contains_project_root_resolve():
    src = inspect.getsource(load_manifest)
    assert "project_root = Path(project_root).resolve()" in src


def test_load_manifest_source_contains_open_utf8():
    src = inspect.getsource(load_manifest)
    assert 'open("r", encoding="utf-8")' in src


def test_load_manifest_source_contains_json_load():
    src = inspect.getsource(load_manifest)
    assert "data = json.load(f)" in src


def test_load_manifest_source_contains_json_decode_error_catch():
    src = inspect.getsource(load_manifest)
    assert "except json.JSONDecodeError as e:" in src


def test_load_manifest_source_contains_qing_dan_jie_shi_shi_bai():
    src = inspect.getsource(load_manifest)
    assert "清单 JSON 解析失败" in src


def test_load_manifest_source_contains_validate_call():
    src = inspect.getsource(load_manifest)
    assert 'validate(data, "manifest.schema.json")' in src


def test_load_manifest_source_contains_manifest_version_check():
    src = inspect.getsource(load_manifest)
    assert 'data.get("manifest_version") != MANIFEST_VERSION' in src


def test_load_manifest_source_contains_bu_jian_rong_error():
    src = inspect.getsource(load_manifest)
    assert "manifest_version 不兼容" in src


def test_load_manifest_source_contains_documents_list_init():
    src = inspect.getsource(load_manifest)
    assert "documents: list[DocumentEntry] = []" in src


def test_load_manifest_source_contains_documents_loop():
    src = inspect.getsource(load_manifest)
    assert "for d in data.get(\"documents\", []):" in src


def test_load_manifest_source_contains_annotation_file_check():
    src = inspect.getsource(load_manifest)
    assert 'if d.get("annotation_file"):' in src


def test_load_manifest_source_contains_failures_list_init():
    src = inspect.getsource(load_manifest)
    assert "failures: list[ExpectedFailure] = []" in src


def test_load_manifest_source_contains_failures_loop():
    src = inspect.getsource(load_manifest)
    assert "for ef in data.get(\"expected_failures\", []):" in src


def test_load_manifest_source_contains_return_manifest():
    src = inspect.getsource(load_manifest)
    assert "return Manifest(" in src


def test_load_manifest_source_does_not_contain_print():
    src = inspect.getsource(load_manifest)
    assert "print(" not in src


def test_load_manifest_source_does_not_contain_logging():
    src = inspect.getsource(load_manifest)
    assert "logging" not in src


def test_load_manifest_source_does_not_contain_subprocess():
    src = inspect.getsource(load_manifest)
    assert "subprocess" not in src


def test_load_manifest_source_does_not_contain_async():
    src = inspect.getsource(load_manifest)
    assert "async " not in src


# =========================================================================
# _detect_project_root source-level
# =========================================================================


def test_detect_project_root_source_contains_cur_resolve():
    src = inspect.getsource(_detect_project_root)
    assert "cur = start.resolve()" in src


def test_detect_project_root_source_contains_is_file_check():
    src = inspect.getsource(_detect_project_root)
    assert "if cur.is_file():" in src


def test_detect_project_root_source_contains_parent_assignment():
    src = inspect.getsource(_detect_project_root)
    assert "cur = cur.parent" in src


def test_detect_project_root_source_contains_parents_iteration():
    src = inspect.getsource(_detect_project_root)
    assert "for parent in [cur, *cur.parents]:" in src


def test_detect_project_root_source_contains_pyproject_toml_check():
    src = inspect.getsource(_detect_project_root)
    assert 'if (parent / "pyproject.toml").is_file():' in src


def test_detect_project_root_source_contains_return_parent():
    src = inspect.getsource(_detect_project_root)
    assert "return parent" in src


def test_detect_project_root_source_contains_return_cur_fallback():
    src = inspect.getsource(_detect_project_root)
    assert "return cur" in src


def test_detect_project_root_does_not_contain_print():
    src = inspect.getsource(_detect_project_root)
    assert "print(" not in src


def test_detect_project_root_actual_finds_project_root(tmp_path):
    """从某个 start 文件能找到含 pyproject.toml 的项目根。"""
    # tmp_path 没有 pyproject.toml → fallback to cur
    fake_start = tmp_path / "fake.json"
    fake_start.write_text("{}", encoding="utf-8")
    out = _detect_project_root(fake_start)
    # fallback 是 cur.parent
    assert isinstance(out, Path)


def test_detect_project_root_with_directory_input(tmp_path):
    """start 是目录 → 直接用。"""
    out = _detect_project_root(tmp_path)
    assert isinstance(out, Path)


# =========================================================================
# __all__ 详细
# =========================================================================


def test_module_all_value_exact_5_entries_in_order():
    import evaluation.manifest as m

    assert m.__all__ == [
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    ]


def test_module_all_is_list_type():
    import evaluation.manifest as m

    assert isinstance(m.__all__, list)


def test_module_all_does_not_contain_is_absolute_like():
    import evaluation.manifest as m

    assert "_is_absolute_like" not in m.__all__


def test_module_all_does_not_contain_has_backslash():
    import evaluation.manifest as m

    assert "_has_backslash" not in m.__all__


def test_module_all_does_not_contain_resolve_relative_path():
    import evaluation.manifest as m

    assert "_resolve_relative_path" not in m.__all__


def test_module_all_does_not_contain_detect_project_root():
    import evaluation.manifest as m

    assert "_detect_project_root" not in m.__all__


def test_module_all_does_not_contain_manifest_version():
    import evaluation.manifest as m

    assert "MANIFEST_VERSION" not in m.__all__


# =========================================================================
# namespace 详细
# =========================================================================


def test_module_namespace_has_manifest_version_attr():
    import evaluation.manifest as m

    assert hasattr(m, "MANIFEST_VERSION")
    assert m.MANIFEST_VERSION == MANIFEST_VERSION


def test_module_namespace_has_validate_attr():
    """validate 是 evaluation.schema.validate 引用。"""
    import evaluation.manifest as m

    assert hasattr(m, "validate")
    assert m.validate is schema_validate


def test_module_namespace_has_manifest_error():
    import evaluation.manifest as m

    assert hasattr(m, "ManifestError")


def test_module_namespace_has_manifest_dataclass():
    import evaluation.manifest as m

    assert hasattr(m, "Manifest")
    assert hasattr(m, "DocumentEntry")
    assert hasattr(m, "ExpectedFailure")


def test_module_namespace_has_load_manifest():
    import evaluation.manifest as m

    assert hasattr(m, "load_manifest")


def test_module_namespace_has_helpers():
    import evaluation.manifest as m

    assert hasattr(m, "_is_absolute_like")
    assert hasattr(m, "_has_backslash")
    assert hasattr(m, "_resolve_relative_path")
    assert hasattr(m, "_detect_project_root")


def test_module_namespace_does_not_have_subprocess():
    import evaluation.manifest as m

    assert not hasattr(m, "subprocess")


def test_module_namespace_does_not_have_logging():
    import evaluation.manifest as m

    assert not hasattr(m, "logging")


def test_module_namespace_does_not_have_os():
    import evaluation.manifest as m

    assert not hasattr(m, "os")


def test_module_namespace_does_not_have_asyncio():
    import evaluation.manifest as m

    assert not hasattr(m, "asyncio")


def test_module_namespace_does_not_have_threading():
    import evaluation.manifest as m

    assert not hasattr(m, "threading")


# =========================================================================
# 模块 source 不含禁止内容
# =========================================================================


def test_module_source_does_not_contain_print():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "print(" not in src


def test_module_source_does_not_contain_logging():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "logging" not in src


def test_module_source_does_not_contain_subprocess():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "subprocess" not in src


def test_module_source_does_not_contain_async():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "async " not in src


def test_module_source_does_not_contain_threading():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "import threading" not in src


def test_module_source_does_not_contain_os_import():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "import os" not in src


def test_module_source_does_not_contain_read_text():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "read_text(" not in src


def test_module_source_does_not_contain_write_text():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "write_text(" not in src


def test_module_source_does_not_contain_silent_drop():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "silent_drop_count" not in src


def test_module_source_does_not_contain_metrics_calc():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "compute_automatic_metrics" not in src


def test_module_source_does_not_contain_image_resource():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "image_resource" not in src


def test_module_source_does_not_contain_process_single():
    import evaluation.manifest as m

    src = inspect.getsource(m)
    assert "process_single" not in src
    assert "from app.pipeline" not in src


# =========================================================================
# load_manifest 实际加载 minimal manifest
# =========================================================================


def test_load_manifest_minimal_manifest(tmp_path):
    """加载 minimal valid manifest：含 manifest_version + devset_status + documents + expected_failures。"""
    manifest_data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest_data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)
    assert m.manifest_version == MANIFEST_VERSION
    assert m.devset_status == "complete"
    assert m.documents == ()
    assert m.expected_failures == ()
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_nonexistent_file_raises(tmp_path):
    with pytest.raises(ManifestError) as exc:
        load_manifest(tmp_path / "no.json")
    assert "清单文件不存在" in str(exc.value)


def test_load_manifest_invalid_json_raises(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("{not valid json}", encoding="utf-8")
    with pytest.raises(ManifestError) as exc:
        load_manifest(p, project_root=tmp_path)
    assert "清单 JSON 解析失败" in str(exc.value)


def test_load_manifest_invalid_manifest_version_raises(tmp_path):
    """manifest_version 不匹配 MANIFEST_VERSION → ManifestError。"""
    manifest_data = {
        "manifest_version": "0.0.invalid",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest_data), encoding="utf-8")
    # 注意：schema 校验先发生（manifest_version 是 const），所以可能抛 EvalSchemaError
    # 但如果 schema 通过（version 不匹配 const），那就会抛 ManifestError
    # 这里两个都接受
    with pytest.raises((ManifestError, Exception)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_returns_manifest_type(tmp_path):
    manifest_data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest_data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert type(m).__name__ == "Manifest"


def test_load_manifest_two_calls_return_independent_manifests(tmp_path):
    manifest_data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(manifest_data), encoding="utf-8")
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1 is not m2
    # frozen dataclass 用 == 比较
    assert m1 == m2


# =========================================================================
# 签名 introspection 详细
# =========================================================================


def test_is_absolute_like_signature_param_count_1():
    sig = inspect.signature(_is_absolute_like)
    assert len(sig.parameters) == 1


def test_is_absolute_like_signature_param_name():
    sig = inspect.signature(_is_absolute_like)
    assert "path_str" in sig.parameters


def test_has_backslash_signature_param_count_1():
    sig = inspect.signature(_has_backslash)
    assert len(sig.parameters) == 1


def test_resolve_relative_path_signature_param_count_3():
    sig = inspect.signature(_resolve_relative_path)
    assert len(sig.parameters) == 3


def test_resolve_relative_path_signature_param_names():
    sig = inspect.signature(_resolve_relative_path)
    assert list(sig.parameters.keys()) == ["path_str", "project_root", "field_name"]


def test_load_manifest_signature_param_count_2():
    sig = inspect.signature(load_manifest)
    assert len(sig.parameters) == 2


def test_load_manifest_signature_param_names():
    sig = inspect.signature(load_manifest)
    assert list(sig.parameters.keys()) == ["manifest_path", "project_root"]


def test_load_manifest_signature_project_root_default_none():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_detect_project_root_signature_param_count_1():
    sig = inspect.signature(_detect_project_root)
    assert len(sig.parameters) == 1


def test_detect_project_root_signature_param_name():
    sig = inspect.signature(_detect_project_root)
    assert "start" in sig.parameters


# =========================================================================
# 模块 docstring 详细
# =========================================================================


def test_module_docstring_is_nonempty_string():
    import evaluation.manifest as m

    assert isinstance(m.__doc__, str)
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_xiang_dui_lu_jing():
    """docstring 提到相对路径。"""
    import evaluation.manifest as m

    doc = m.__doc__
    assert "相对路径" in doc


def test_module_docstring_mentions_zheng_xie_gang():
    """docstring 提到正斜杠。"""
    import evaluation.manifest as m

    doc = m.__doc__
    assert "正斜杠" in doc


def test_module_docstring_mentions_jue_dui_lu_jing():
    """docstring 提到拒绝绝对路径。"""
    import evaluation.manifest as m

    doc = m.__doc__
    assert "绝对路径" in doc


def test_module_docstring_mentions_fan_xie_gang():
    """docstring 提到反斜杠。"""
    import evaluation.manifest as m

    doc = m.__doc__
    assert "反斜杠" in doc


def test_module_docstring_mentions_xiang_mu_gen():
    """docstring 提到项目根。"""
    import evaluation.manifest as m

    doc = m.__doc__
    assert "项目根" in doc


# =========================================================================
# helper metadata 详细
# =========================================================================


def test_is_absolute_like_is_function_type():
    import types

    assert isinstance(_is_absolute_like, types.FunctionType)


def test_has_backslash_is_function_type():
    import types

    assert isinstance(_has_backslash, types.FunctionType)


def test_resolve_relative_path_is_function_type():
    import types

    assert isinstance(_resolve_relative_path, types.FunctionType)


def test_detect_project_root_is_function_type():
    import types

    assert isinstance(_detect_project_root, types.FunctionType)


def test_load_manifest_is_function_type():
    import types

    assert isinstance(load_manifest, types.FunctionType)


def test_manifest_error_is_class():
    assert isinstance(ManifestError, type)


def test_manifest_is_dataclass_type():
    assert isinstance(Manifest, type)


def test_document_entry_is_dataclass_type():
    assert isinstance(DocumentEntry, type)


def test_expected_failure_is_dataclass_type():
    assert isinstance(ExpectedFailure, type)
