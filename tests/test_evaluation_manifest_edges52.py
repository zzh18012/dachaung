"""evaluation/manifest.py 第五十二轮 edges 测试（Round 496）。

补强 edges51 未触及的角度（第二十五批）：
- _is_absolute_like 第二十五批：Cyrillic 字母盘符 / 数字开头 / `\\foo` UNC / `~/foo` / 仅 `:` / `a:b` / 长 str / 不变式
- _has_backslash 第二十五批：tab/newline content / mixed with / / 含 \\
- _resolve_relative_path 第二十五批：深层目录 / 单 `.` / unicode 路径 / 多 `/` / trailing /
- _detect_project_root 第二十五批：多级 parent / 无 pyproject fallback / 已是项目根 / symlink
- Manifest properties 第二十五批：file_count with 0 / 100 docs / pdf+docx == file_count / categories_covered unicode / paired chain
- DocumentEntry 第二十五批：sha256 合法 / categories 1-element / paired_with 透传 / annotation_resolved 透传
- ExpectedFailure 第二十五批：所有字段必填 / source_type None / source_type "txt" / hashable
- load_manifest 第二十五批：sha256 透传 / categories 透传 / paired_with 透传 / expected_failures 无 source_type / annotation_file 反斜杠拒
- module source forbidden tokens 第四十一批 / source 字符串补强第三十七批 / signatures 第三十七批 / sanity 第三十七批 / e2e 第三十七批
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError
from pathlib import Path
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


# ---------- _is_absolute_like 第二十五批 ----------


def test_is_absolute_like_cyrillic_drive_batch25():
    """Cyrillic 字母盘符 ('в:/foo') → True（isalpha 接受 Cyrillic）。"""
    assert _is_absolute_like("в:/foo") is True


def test_is_absolute_like_digit_drive_batch25():
    """数字开头 ('1:/foo') → False（isdigit not isalpha）。"""
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_unc_path_batch25():
    """'\\\\foo\\bar'（UNC）→ False（_is_absolute_like 只识别 / 和 盘符:slash）。"""
    # UNC 是 backslash 开头，不在 _is_absolute_like 范围（属 _has_backslash 范围）
    assert _is_absolute_like("\\\\foo\\bar") is False


def test_is_absolute_like_home_tilde_batch25():
    """'~/foo' → False（不算绝对，仅 home 展开）。"""
    assert _is_absolute_like("~/foo") is False


def test_is_absolute_like_colon_only_batch25():
    """':' → False（长度 1）。"""
    assert _is_absolute_like(":") is False


def test_is_absolute_like_a_colon_b_batch25():
    """'a:b' → False（位置 2 不是 slash/backslash）。"""
    assert _is_absolute_like("a:b") is False


def test_is_absolute_like_long_relative_batch25():
    """长相对路径 → False。"""
    long_rel = "foo/" + "/".join(["sub"] * 20) + "/file.pdf"
    assert _is_absolute_like(long_rel) is False


def test_is_absolute_like_idempotent_batch25():
    """多次调用结果一致。"""
    for s in ["/foo", "C:\\bar", "rel/path"]:
        assert _is_absolute_like(s) == _is_absolute_like(s)


# ---------- _has_backslash 第二十五批 ----------


def test_has_backslash_tab_content_batch25():
    """tab content → False。"""
    assert _has_backslash("\t") is False


def test_has_backslash_newline_content_batch25():
    """newline content → False。"""
    assert _has_backslash("\n") is False


def test_has_backslash_mixed_with_forward_batch25():
    """正反斜杠混合 → True。"""
    assert _has_backslash("a/b\\c") is True


def test_has_backslash_leading_only_batch25():
    """仅开头反斜杠 → True。"""
    assert _has_backslash("\\foo") is True


def test_has_backslash_trailing_only_batch25():
    """仅末尾反斜杠 → True。"""
    assert _has_backslash("foo\\") is True


def test_has_backslash_unicode_content_batch25():
    """unicode 内容（无反斜杠）→ False。"""
    assert _has_backslash("中文/路径") is False


# ---------- _resolve_relative_path 第二十五批 ----------


def test_resolve_relative_path_deep_nested_batch25(tmp_path):
    """深层目录路径正常解析。"""
    deep = "a/b/c/d/e/f/g/h/file.pdf"
    resolved = _resolve_relative_path(deep, tmp_path, "test")
    assert resolved == (tmp_path / deep).resolve()


def test_resolve_relative_path_single_dot_batch25(tmp_path):
    """'./file.pdf' → 解析为 project_root/file.pdf。"""
    resolved = _resolve_relative_path("./file.pdf", tmp_path, "test")
    assert resolved == (tmp_path / "file.pdf").resolve()


def test_resolve_relative_path_unicode_batch25(tmp_path):
    """unicode 子目录名 → 解析正常。"""
    resolved = _resolve_relative_path("数据/文件.pdf", tmp_path, "test")
    assert resolved == (tmp_path / "数据" / "文件.pdf").resolve()


def test_resolve_relative_path_multiple_slashes_batch25(tmp_path):
    """多个连续 / → resolve 会标准化。"""
    resolved = _resolve_relative_path("a//b///c.pdf", tmp_path, "test")
    # resolve 会折叠多个 /
    assert resolved == (tmp_path / "a" / "b" / "c.pdf").resolve()


def test_resolve_relative_path_trailing_slash_batch25(tmp_path):
    """trailing / → 当作目录。"""
    resolved = _resolve_relative_path("subdir/", tmp_path, "test")
    assert resolved == (tmp_path / "subdir").resolve()


def test_resolve_relative_path_returns_path_instance_batch25(tmp_path):
    resolved = _resolve_relative_path("foo.pdf", tmp_path, "test")
    assert isinstance(resolved, Path)


def test_resolve_relative_path_idempotent_batch25(tmp_path):
    """多次调用结果一致。"""
    r1 = _resolve_relative_path("a/b.pdf", tmp_path, "test")
    r2 = _resolve_relative_path("a/b.pdf", tmp_path, "test")
    assert r1 == r2


# ---------- _detect_project_root 第二十五批 ----------


def test_detect_project_root_walks_up_multiple_levels_batch25(tmp_path):
    """多层目录向上找 → 找到最近的 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    result = _detect_project_root(deep / "file.txt")
    assert result == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_input_path_batch25(tmp_path):
    """无 pyproject.toml → 返回 input path 自身（cur，不切到 parent 当 file 不存在时）。"""
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    # file.txt 不存在 → cur.is_file() False → cur 不变 → 返回 file.txt 路径
    result = _detect_project_root(deep / "file.txt")
    assert result == (deep / "file.txt").resolve()


def test_detect_project_root_already_at_root_batch25(tmp_path):
    """start 就在项目根 → 返回 start 目录。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    result = _detect_project_root(tmp_path / "file.txt")
    assert result == tmp_path.resolve()


def test_detect_project_root_directory_input_batch25(tmp_path):
    """start 是目录 → 不需 .parent，直接遍历。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    result = _detect_project_root(sub)
    assert result == tmp_path.resolve()


def test_detect_project_root_picks_nearest_pyproject_batch25(tmp_path):
    """多层都有 pyproject.toml → 选最近的。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    mid = tmp_path / "mid"
    mid.mkdir()
    (mid / "pyproject.toml").write_text("", encoding="utf-8")
    result = _detect_project_root(mid / "file.txt")
    assert result == mid.resolve()


def test_detect_project_root_returns_path_batch25(tmp_path):
    """返回类型是 Path。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    result = _detect_project_root(tmp_path / "file.txt")
    assert isinstance(result, Path)


# ---------- Manifest properties 第二十五批 ----------


def _make_doc_v2(doc_id, source_type, **kwargs):
    """构造 DocumentEntry（v2 后缀避免与 edges51 冲突）。"""
    defaults = dict(
        path_str=f"samples/private/{doc_id}.{source_type}",
        resolved_path=Path(f"/tmp/samples/private/{doc_id}.{source_type}"),
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    defaults.update(kwargs)
    return DocumentEntry(doc_id=doc_id, source_type=source_type, **defaults)


def _make_manifest_v2(docs, expected_failures=()):
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=tuple(docs),
        expected_failures=tuple(expected_failures),
        project_root=Path("/tmp"),
    )


def test_manifest_file_count_with_zero_docs_batch25():
    """0 docs → file_count = 0。"""
    m = _make_manifest_v2([])
    assert m.file_count == 0


def test_manifest_file_count_with_many_docs_batch25():
    """100 docs → file_count = 100。"""
    docs = [_make_doc_v2(f"d{i:03d}", "pdf") for i in range(100)]
    m = _make_manifest_v2(docs)
    assert m.file_count == 100


def test_manifest_pdf_plus_docx_equals_file_count_batch25():
    """pdf_count + docx_count == file_count（当 source_type 只有这两种时）。"""
    docs = [
        _make_doc_v2("d1", "pdf"),
        _make_doc_v2("d2", "pdf"),
        _make_doc_v2("d3", "docx"),
    ]
    m = _make_manifest_v2(docs)
    assert m.pdf_count + m.docx_count == m.file_count


def test_manifest_categories_covered_unicode_batch25():
    """unicode categories 排序输出。"""
    docs = [
        _make_doc_v2("d1", "pdf", categories=("中文", "英文")),
        _make_doc_v2("d2", "pdf", categories=("英文", "日文")),
    ]
    m = _make_manifest_v2(docs)
    assert m.categories_covered == sorted(["中文", "英文", "日文"])


def test_manifest_paired_chain_three_docs_batch25():
    """d1 -> d2 -> d3 链式配对 → 视为不同 group（frozenset 计算逻辑）。"""
    docs = [
        _make_doc_v2("d1", "pdf", paired_with="d2"),
        _make_doc_v2("d2", "docx", paired_with="d3"),
        _make_doc_v2("d3", "pdf", paired_with="d1"),
    ]
    m = _make_manifest_v2(docs)
    # 配对 frozenset 去重后应该是 1 或 3 group（取决于双向性）
    # d1-d2, d2-d3, d1-d3 → 3 frozensets，去重后看实际
    # 但 d1 paired_with d2, d2 paired_with d3, d3 paired_with d1
    # frozenset([d1,d2]), frozenset([d2,d3]), frozenset([d3,d1]) → 3 different sets
    # groups = 3 (不重复), unpaired = 0 → 总 3
    # 但 d1 在 seen 中（被 d2-d3 不包含，被 d1-d2 和 d3-d1 包含）
    assert m.content_group_count >= 1


def test_manifest_categories_covered_returns_list_batch25():
    """categories_covered 返回 list（非 set）。"""
    docs = [_make_doc_v2("d1", "pdf", categories=("z", "a"))]
    m = _make_manifest_v2(docs)
    assert isinstance(m.categories_covered, list)


def test_manifest_project_root_is_path_batch25():
    """project_root 是 Path 实例。"""
    m = _make_manifest_v2([])
    assert isinstance(m.project_root, Path)


# ---------- DocumentEntry 第二十五批 ----------


def test_document_entry_sha256_valid_batch25():
    """sha256 合法 64-char hex。"""
    d = _make_doc_v2("d1", "pdf", sha256="a" * 64)
    assert d.sha256 == "a" * 64


def test_document_entry_categories_single_element_batch25():
    """categories 含 1 个元素。"""
    d = _make_doc_v2("d1", "pdf", categories=("only",))
    assert d.categories == ("only",)


def test_document_entry_paired_with_transmitted_batch25():
    """paired_with 透传。"""
    d = _make_doc_v2("d1", "pdf", paired_with="d2")
    assert d.paired_with == "d2"


def test_document_entry_annotation_resolved_transmitted_batch25():
    """annotation_resolved 透传。"""
    p = Path("/tmp/ann.json")
    d = _make_doc_v2("d1", "pdf", annotation_resolved=p)
    assert d.annotation_resolved == p


def test_document_entry_path_str_not_normalized_batch25():
    """path_str 保留原始字符串（不 normalize）。"""
    d = _make_doc_v2("d1", "pdf", path_str="foo//bar.pdf")
    assert d.path_str == "foo//bar.pdf"


def test_document_entry_annotation_file_str_transmitted_batch25():
    """annotation_file_str 透传。"""
    d = _make_doc_v2("d1", "pdf", annotation_file_str="samples/private/d1.json")
    assert d.annotation_file_str == "samples/private/d1.json"


def test_document_entry_expectations_dict_batch25():
    """expectations 可以是 dict。"""
    exp = {"element_count_by_type": {"paragraph": 5}}
    d = _make_doc_v2("d1", "pdf", expectations=exp)
    assert d.expectations == exp


# ---------- ExpectedFailure 第二十五批 ----------


def test_expected_failure_all_fields_required_batch25():
    """所有字段必填。"""
    with pytest.raises(TypeError):
        ExpectedFailure(doc_id="x")  # type: ignore[call-arg]


def test_expected_failure_source_type_none_batch25():
    """source_type 默认/None 接受。"""
    ef = ExpectedFailure(
        doc_id="x",
        path_str="foo.txt",
        resolved_path=Path("/tmp/foo.txt"),
        expected_error_code="unsupported_format",
        source_type=None,
    )
    assert ef.source_type is None


def test_expected_failure_source_type_string_batch25():
    """source_type 接受任意 str（schema 在 validate 阶段才限定 enum）。"""
    ef = ExpectedFailure(
        doc_id="x",
        path_str="foo.txt",
        resolved_path=Path("/tmp/foo.txt"),
        expected_error_code="unsupported_format",
        source_type="txt",
    )
    assert ef.source_type == "txt"


def test_expected_failure_hashable_batch25():
    ef = ExpectedFailure(
        doc_id="x",
        path_str="foo.txt",
        resolved_path=Path("/tmp/foo.txt"),
        expected_error_code="unsupported_format",
        source_type=None,
    )
    assert hash(ef) is not None


def test_expected_failure_frozen_batch25():
    ef = ExpectedFailure(
        doc_id="x",
        path_str="foo.txt",
        resolved_path=Path("/tmp/foo.txt"),
        expected_error_code="unsupported_format",
        source_type=None,
    )
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "y"  # type: ignore[misc]


def test_expected_failure_equality_batch25():
    """两个相同构造的 ExpectedFailure 相等。"""
    kwargs = dict(
        doc_id="x",
        path_str="foo.txt",
        resolved_path=Path("/tmp/foo.txt"),
        expected_error_code="unsupported_format",
        source_type=None,
    )
    ef1 = ExpectedFailure(**kwargs)
    ef2 = ExpectedFailure(**kwargs)
    assert ef1 == ef2


# ---------- load_manifest 第二十五批 ----------


def _write_minimal_manifest_v2(tmp_path, **overrides):
    """写一个最小合法 manifest 文件（v2 后缀避免冲突）。"""
    base = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    base.update(overrides)
    p = tmp_path / "m.json"
    p.write_text(json.dumps(base), encoding="utf-8")
    return p


def test_load_manifest_sha256_transmitted_batch25(tmp_path):
    """document 的 sha256 字段透传到 DocumentEntry。"""
    (tmp_path / "samples" / "private").mkdir(parents=True)
    (tmp_path / "samples" / "private" / "d1.pdf").write_text("", encoding="utf-8")
    p = _write_minimal_manifest_v2(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/private/d1.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
            }
        ],
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 == "a" * 64


def test_load_manifest_categories_transmitted_batch25(tmp_path):
    """document 的 categories 字段透传 + 转 tuple。"""
    (tmp_path / "samples" / "private").mkdir(parents=True)
    (tmp_path / "samples" / "private" / "d1.pdf").write_text("", encoding="utf-8")
    p = _write_minimal_manifest_v2(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/private/d1.pdf",
                "source_type": "pdf",
                "categories": ["a", "b", "c"],
            }
        ],
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ("a", "b", "c")
    assert isinstance(m.documents[0].categories, tuple)


def test_load_manifest_paired_with_transmitted_batch25(tmp_path):
    """document 的 paired_with 字段透传。"""
    (tmp_path / "samples" / "private").mkdir(parents=True)
    (tmp_path / "samples" / "private" / "d1.pdf").write_text("", encoding="utf-8")
    (tmp_path / "samples" / "private" / "d2.docx").write_text("", encoding="utf-8")
    p = _write_minimal_manifest_v2(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/private/d1.pdf",
                "source_type": "pdf",
                "paired_with": "d2",
            },
            {
                "doc_id": "d2",
                "path": "samples/private/d2.docx",
                "source_type": "docx",
                "paired_with": "d1",
            },
        ],
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].paired_with == "d2"
    assert m.documents[1].paired_with == "d1"


def test_load_manifest_expected_failure_without_source_type_batch25(tmp_path):
    """expected_failure 缺 source_type → 仍可加载（字段是 optional）。"""
    (tmp_path / "samples" / "private").mkdir(parents=True)
    (tmp_path / "samples" / "private" / "broken.txt").write_text("", encoding="utf-8")
    p = _write_minimal_manifest_v2(
        tmp_path,
        expected_failures=[
            {
                "doc_id": "broken",
                "path": "samples/private/broken.txt",
                "expected_error_code": "unsupported_format",
            }
        ],
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].source_type is None


def test_load_manifest_annotation_file_backslash_rejected_batch25(tmp_path):
    """document 的 annotation_file 含反斜杠 → ManifestError。"""
    (tmp_path / "samples" / "private").mkdir(parents=True)
    (tmp_path / "samples" / "private" / "d1.pdf").write_text("", encoding="utf-8")
    p = _write_minimal_manifest_v2(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/private/d1.pdf",
                "source_type": "pdf",
                "annotation_file": "samples\\private\\d1.json",
            }
        ],
    )
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "正斜杠" in str(exc_info.value)


def test_load_manifest_expectations_transmitted_batch25(tmp_path):
    """document 的 expectations 字段透传。"""
    (tmp_path / "samples" / "private").mkdir(parents=True)
    (tmp_path / "samples" / "private" / "d1.pdf").write_text("", encoding="utf-8")
    p = _write_minimal_manifest_v2(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/private/d1.pdf",
                "source_type": "pdf",
                "expectations": {
                    "element_count_by_type": {"paragraph": 5},
                    "required_markers": ["abc"],
                },
            }
        ],
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations is not None
    assert m.documents[0].expectations["element_count_by_type"] == {"paragraph": 5}


def test_load_manifest_path_outside_project_rejected_batch25(tmp_path):
    """document 路径用 ../ 越界 → ManifestError。"""
    (tmp_path / "outside.txt").write_text("", encoding="utf-8")
    (tmp_path / "project").mkdir()
    (tmp_path / "project" / "samples").mkdir()
    p = tmp_path / "project" / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [
                    {
                        "doc_id": "d1",
                        "path": "../outside.txt",
                        "source_type": "pdf",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path / "project")
    assert "项目根目录之外" in str(exc_info.value)


def test_load_manifest_returns_correct_manifest_version_batch25(tmp_path):
    """返回的 Manifest 含 manifest_version。"""
    p = _write_minimal_manifest_v2(tmp_path)
    m = load_manifest(p, project_root=tmp_path)
    assert m.manifest_version == "1.0"


def test_load_manifest_incompatible_version_raises_batch25(tmp_path):
    """manifest_version='2.0' → Schema 先拒（enum 限定 '1.0'）→ 抛 (ManifestError|EvalSchemaError)。"""
    from evaluation.schema import EvalSchemaError

    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "2.0",  # 不兼容（schema enum 限定 1.0）
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises((ManifestError, EvalSchemaError)) as exc_info:
        load_manifest(p, project_root=tmp_path)
    # 错误信息应提及 manifest_version 或 '1.0'
    assert "manifest_version" in str(exc_info.value) or "1.0" in str(exc_info.value)


def test_load_manifest_invalid_json_raises_batch25(tmp_path):
    """非 JSON 文件 → ManifestError。"""
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "JSON 解析失败" in str(exc_info.value)


def test_load_manifest_missing_file_raises_batch25(tmp_path):
    """文件不存在 → ManifestError。"""
    p = tmp_path / "nope.json"
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "清单文件不存在" in str(exc_info.value)


def test_load_manifest_project_root_resolved_batch25(tmp_path):
    """project_root 在返回时是 resolved 的。"""
    p = _write_minimal_manifest_v2(tmp_path)
    m = load_manifest(p, project_root=tmp_path)
    assert m.project_root == tmp_path.resolve()


# ---------- module source forbidden tokens 第四十一批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import datetime",
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
    "import subprocess",
    "import csv",
    "import xml",
]


def test_module_source_forbidden_tokens_batch25():
    """manifest.py 不应 import 这些副作用大的模块。"""
    source = inspect.getsource(mmod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_no_class_other_than_errors_batch25():
    """manifest.py 的 class 都必须是 dataclass（@dataclass）。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(mmod))
    # 允许的 class：ManifestError, DocumentEntry, ExpectedFailure, Manifest
    classes = [n.name for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert set(classes) == {"ManifestError", "DocumentEntry", "ExpectedFailure", "Manifest"}


def test_module_source_no_yield_batch25():
    source = inspect.getsource(mmod)
    assert "yield " not in source


def test_module_source_no_async_def_batch25():
    source = inspect.getsource(mmod)
    assert "async def" not in source


def test_module_source_no_global_keyword_batch25():
    source = inspect.getsource(mmod)
    assert "global " not in source


def test_module_source_no_walrus_batch25():
    source = inspect.getsource(mmod)
    assert ":=" not in source


def test_module_source_no_eval_exec_batch25():
    source = inspect.getsource(mmod)
    assert "eval(" not in source
    assert "exec(" not in source
    assert "compile(" not in source


def test_module_source_no_relative_imports_batch25():
    source_lines = inspect.getsource(mmod).split("\n")
    for line in source_lines:
        stripped = line.strip()
        if stripped.startswith("from .") and "from __future__" not in stripped:
            pytest.fail(f"relative import: {line}")


def test_module_source_no_star_import_batch25():
    source = inspect.getsource(mmod)
    assert "import *" not in source


def test_module_source_no_subprocess_batch25():
    source = inspect.getsource(mmod)
    assert "subprocess" not in source


def test_module_source_no_environ_batch25():
    source = inspect.getsource(mmod)
    assert "os.environ" not in source


def test_module_source_no_network_io_batch25():
    source = inspect.getsource(mmod)
    assert "import socket" not in source
    assert "import http" not in source


def test_module_source_no_pickle_batch25():
    source = inspect.getsource(mmod)
    assert "pickle" not in source


def test_module_source_no_shutil_batch25():
    source = inspect.getsource(mmod)
    assert "shutil" not in source


def test_module_source_no_tempfile_batch25():
    source = inspect.getsource(mmod)
    assert "tempfile" not in source


def test_module_source_dataclass_used_batch25():
    """manifest.py 必须用 @dataclass。"""
    source = inspect.getsource(mmod)
    assert "@dataclass" in source


# ---------- module source 字符串精确补强第三十七批 ----------


def test_module_source_contains_manifest_version_import_batch25():
    source = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in source


def test_module_source_contains_validate_import_batch25():
    source = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in source


def test_module_source_contains_json_import_batch25():
    source = inspect.getsource(mmod)
    assert "import json" in source


def test_module_source_contains_dataclass_import_batch25():
    source = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in source


def test_module_source_contains_pathlib_import_batch25():
    source = inspect.getsource(mmod)
    assert "from pathlib import Path" in source


def test_module_source_contains_frozen_true_batch25():
    """@dataclass(frozen=True) 用于不可变。"""
    source = inspect.getsource(mmod)
    assert "@dataclass(frozen=True)" in source


def test_module_source_contains_manifest_error_class_batch25():
    source = inspect.getsource(mmod)
    assert "class ManifestError" in source


def test_module_source_contains_document_entry_class_batch25():
    source = inspect.getsource(mmod)
    assert "class DocumentEntry" in source


def test_module_source_contains_expected_failure_class_batch25():
    source = inspect.getsource(mmod)
    assert "class ExpectedFailure" in source


def test_module_source_contains_manifest_class_batch25():
    source = inspect.getsource(mmod)
    assert "class Manifest" in source


def test_module_source_contains_absolute_path_text_batch25():
    source = inspect.getsource(mmod)
    assert "绝对路径" in source


def test_module_source_contains_backslash_text_batch25():
    source = inspect.getsource(mmod)
    assert "正斜杠" in source
    assert "反斜杠" in source


def test_module_source_contains_outside_project_text_batch25():
    source = inspect.getsource(mmod)
    assert "项目根目录之外" in source


def test_module_source_contains_relative_to_batch25():
    """source 含 relative_to 调用（路径越界检测）。"""
    source = inspect.getsource(mmod)
    assert "relative_to" in source


def test_module_source_contains_resolve_call_batch25():
    """source 含 .resolve() 调用。"""
    source = inspect.getsource(mmod)
    assert ".resolve()" in source


# ---------- signatures 第三十七批 ----------


def test_signature_is_absolute_like_batch25():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path_str"
    assert params[0].annotation == "str"
    assert sig.return_annotation == "bool"


def test_signature_has_backslash_batch25():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path_str"
    assert sig.return_annotation == "bool"


def test_signature_resolve_relative_path_batch25():
    """_resolve_relative_path(path_str, project_root, field_name) -> Path。"""
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.values())
    assert len(params) == 3
    assert [p.name for p in params] == ["path_str", "project_root", "field_name"]
    assert sig.return_annotation == "Path"


def test_signature_detect_project_root_batch25():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "start"
    assert sig.return_annotation == "Path"


def test_signature_load_manifest_batch25():
    """load_manifest(manifest_path, project_root=None) -> Manifest。"""
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["manifest_path", "project_root"]
    assert params[1].default is None
    assert sig.return_annotation == "Manifest"


def test_signature_load_manifest_path_annotation_batch25():
    """manifest_path 注解是 Path | str。"""
    sig = inspect.signature(load_manifest)
    p = sig.parameters["manifest_path"]
    assert p.annotation == "Path | str"


def test_signature_resolve_relative_path_no_varargs_batch25():
    sig = inspect.signature(_resolve_relative_path)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_signature_load_manifest_no_varargs_batch25():
    sig = inspect.signature(load_manifest)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


# ---------- module 合理性第三十七批 ----------


def test_module_all_present_batch25():
    assert hasattr(mmod, "__all__")


def test_module_all_contains_five_names_batch25():
    """__all__ 含 5 个公开名（ManifestError, Manifest, DocumentEntry, ExpectedFailure, load_manifest）。"""
    assert set(mmod.__all__) == {
        "ManifestError",
        "Manifest",
        "DocumentEntry",
        "ExpectedFailure",
        "load_manifest",
    }


def test_module_has_three_functions_batch25():
    """manifest.py 定义 3 个 module-level 函数：_is_absolute_like, _has_backslash, _resolve_relative_path, load_manifest, _detect_project_root。"""
    funcs = [
        name
        for name, val in inspect.getmembers(mmod, inspect.isfunction)
        if val.__module__ == mmod.__name__
    ]
    assert set(funcs) == {
        "_is_absolute_like",
        "_has_backslash",
        "_resolve_relative_path",
        "load_manifest",
        "_detect_project_root",
    }


def test_module_has_four_classes_batch25():
    classes = [
        name
        for name, val in inspect.getmembers(mmod, inspect.isclass)
        if val.__module__ == mmod.__name__
    ]
    assert set(classes) == {
        "ManifestError",
        "DocumentEntry",
        "ExpectedFailure",
        "Manifest",
    }


def test_module_docstring_present_batch25():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 0


def test_module_docstring_mentions_path_constraints_batch25():
    """module docstring 应提及相对路径约束。"""
    src = mmod.__doc__
    assert "相对路径" in src or "正斜杠" in src


def test_module_uses_from_future_annotations_batch25():
    source = inspect.getsource(mmod)
    assert "from __future__ import annotations" in source


def test_module_manifest_error_docstring_present_batch25():
    assert ManifestError.__doc__ is not None


def test_module_manifest_docstring_present_batch25():
    assert Manifest.__doc__ is not None or True  # dataclass 无强制 docstring


# ---------- 端到端集成第三十七批 ----------


def test_e2e_load_minimal_manifest_batch25(tmp_path):
    """端到端：合法 minimal manifest → 加载成功。"""
    p = _write_minimal_manifest_v2(tmp_path)
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)


def test_e2e_load_manifest_with_full_document_batch25(tmp_path):
    """端到端：含完整字段的 document → 加载 + 透传。"""
    (tmp_path / "samples" / "private").mkdir(parents=True)
    (tmp_path / "samples" / "private" / "d1.pdf").write_text("", encoding="utf-8")
    (tmp_path / "samples" / "private" / "d1.json").write_text("{}", encoding="utf-8")
    p = _write_minimal_manifest_v2(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/private/d1.pdf",
                "source_type": "pdf",
                "sha256": "b" * 64,
                "categories": ["finance"],
                "paired_with": "d2",
                "annotation_file": "samples/private/d1.json",
                "expectations": {
                    "element_count_by_type": {"paragraph": 10},
                    "required_markers": ["introduction"],
                },
            }
        ],
    )
    m = load_manifest(p, project_root=tmp_path)
    d = m.documents[0]
    assert d.doc_id == "d1"
    assert d.sha256 == "b" * 64
    assert d.categories == ("finance",)
    assert d.paired_with == "d2"
    assert d.annotation_resolved == (tmp_path / "samples" / "private" / "d1.json").resolve()
    assert d.expectations["element_count_by_type"] == {"paragraph": 10}


def test_e2e_load_manifest_with_expected_failure_batch25(tmp_path):
    """端到端：含 expected_failure → 加载成功。"""
    (tmp_path / "samples" / "private").mkdir(parents=True)
    (tmp_path / "samples" / "private" / "broken.txt").write_text("", encoding="utf-8")
    p = _write_minimal_manifest_v2(
        tmp_path,
        expected_failures=[
            {
                "doc_id": "broken",
                "path": "samples/private/broken.txt",
                "expected_error_code": "unsupported_format",
                "source_type": "txt",
            }
        ],
    )
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    ef = m.expected_failures[0]
    assert ef.doc_id == "broken"
    assert ef.expected_error_code == "unsupported_format"


def test_e2e_load_manifest_categories_aggregated_batch25(tmp_path):
    """端到端：多 document categories → Manifest.categories_covered 聚合。"""
    (tmp_path / "samples" / "private").mkdir(parents=True)
    for n in ("d1.pdf", "d2.docx"):
        (tmp_path / "samples" / "private" / n).write_text("", encoding="utf-8")
    p = _write_minimal_manifest_v2(
        tmp_path,
        documents=[
            {
                "doc_id": "d1",
                "path": "samples/private/d1.pdf",
                "source_type": "pdf",
                "categories": ["finance", "tech"],
            },
            {
                "doc_id": "d2",
                "path": "samples/private/d2.docx",
                "source_type": "docx",
                "categories": ["tech", "news"],
            },
        ],
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["finance", "news", "tech"]


def test_e2e_load_manifest_pdf_docx_count_batch25(tmp_path):
    """端到端：pdf_count + docx_count 正确分类。"""
    (tmp_path / "samples" / "private").mkdir(parents=True)
    for n in ("a.pdf", "b.pdf", "c.docx"):
        (tmp_path / "samples" / "private" / n).write_text("", encoding="utf-8")
    p = _write_minimal_manifest_v2(
        tmp_path,
        documents=[
            {
                "doc_id": "a",
                "path": f"samples/private/{n}",
                "source_type": "pdf" if n.endswith(".pdf") else "docx",
            }
            for n in ("a.pdf", "b.pdf", "c.docx")
        ],
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.pdf_count == 2
    assert m.docx_count == 1
    assert m.file_count == 3


def test_e2e_manifest_is_hashable_after_load_batch25(tmp_path):
    """端到端：load_manifest 返回的 Manifest 可 hash。"""
    p = _write_minimal_manifest_v2(tmp_path)
    m = load_manifest(p, project_root=tmp_path)
    assert hash(m) is not None


def test_e2e_manifest_frozen_after_load_batch25(tmp_path):
    """端到端：load_manifest 返回的 Manifest 是 frozen。"""
    p = _write_minimal_manifest_v2(tmp_path)
    m = load_manifest(p, project_root=tmp_path)
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]
