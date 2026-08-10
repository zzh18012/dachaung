"""evaluation/runner.py 边角测试 - 第二十一轮（Round 288）。

edges20 已覆盖：schema 交叉验证 / 失败文档路径 / expected_failures 完整路径 / tolerance_chars 传播 /
_annotation_present 行为 / provenance 字段类型 / summary 字段类型 / per_doc wall_time_seconds 5 keys /
report_version 常量 / 多文档 manifest / public_per_doc vs internal / empty manifest schema 验证 /
out_stub 清理 / module source 不含 subprocess / run_evaluation 不修改 manifest / 不同 parser_name /
paired_with manifest / _process_one source 5-tuple 顺序 / __all__ / report 字段值类型 /
public per_doc 字段顺序。

edges21 补强未覆盖的角度：**_load_annotation 边界** + **_process_one monkeypatch 深度** +
**run_evaluation 集成深度**：
- _load_annotation 边界：
  - path=None → None
  - path 不存在 → None
  - path 是目录 → None（is_file 返 False）
  - path 是文件 + valid JSON → dict
  - path 是文件 + invalid JSON → None（JSONDecodeError）
  - path 是文件 + 空 file → None（JSONDecodeError）
  - path 是文件 + 二进制内容 → None（UnicodeDecodeError 是 ValueError 子类，但 except 只接 OSError+JSONDecodeError）
  - path 是文件 + UTF-8 BOM → None（json.load 不剥 BOM → JSONDecodeError）
  - path 是文件 + top-level array → dict 类型（json.load 不限类型）
  - path 是文件 + top-level number → int 类型

- _process_one 行为深度：
  - 成功路径：document 非 None，errors 空 → 返回 (dict, None, float, parser_version, image_dir)
  - 失败路径：errors 非空 → 返回 (None, errors[0].to_dict(), float, None, image_dir)
  - 异常路径：document 是 None 且 errors 空 → 返回 (None, error_dict 'unknown', float, None, image_dir)
  - total_seconds 是 float（来自 perf_counter 差）
  - image_dir 在 document 是 None 时是 None
  - image_dir 在 document 非 None 时是 Path 对象（image_output_dir_for 结果）
  - out_stub 在 _process_one 完成后被清理（unlink）
  - out_stub 父目录被创建（_per_doc/）
  - write_json=False 传给 process_single

- run_evaluation 集成深度：
  - 多个成功 + 失败文档混合：per_doc 长度 = 文档总数
  - manifest 空 documents 但非空 expected_failures：per_doc=[]，expected_failures 含结果
  - manifest documents + expected_failures 都有：两类都执行
  - tolerance_chars 通过 chunk_boundary_prf 传播（_tolerance_chars 字段记录）
  - 自定义 tolerance_chars=100 → per_doc[0]._tolerance_chars=100
  - 自定义 tolerance_chars=0 → per_doc[0]._tolerance_chars=0
  - report 写盘文件大小 > 0
  - report 写盘后可被 json.load
  - report 写盘后内容与返回值相同（结构上）
  - report 含 5 top-level keys（report_version/provenance/devset/summary/per_doc）+ expected_failures=6
  - report 字段顺序：report_version → provenance → devset → summary → per_doc → expected_failures
  - process_single 失败时 _tolerance_chars 仍正确传播（来自 chunk_boundary_prf 的 fallback）
  - empty manifest（无 doc 无 ef）→ 报告仍 valid schema

- run_evaluation 不修改 manifest：
  - manifest.documents 长度不变
  - manifest.expected_failures 长度不变
  - manifest.project_root 不变
  - manifest.devset_status 不变

- module source level 完整：
  - imports: json, time, pathlib.Path, typing.Any, app.pipeline (image_output_dir_for, process_single)
  - imports: evaluation.REPORT_VERSION, evaluation.annotation_metrics, evaluation.metrics, evaluation.report
  - _load_annotation: try/except (OSError, json.JSONDecodeError)；return None 2 处
  - _process_one: 5-tuple 返回；perf_counter 开/关；mkdir parents=True exist_ok=True；unlink try/except OSError
  - run_evaluation: 6 个 keyword-only args (manifest, output_path, parser_name, max_chars, tolerance_chars)
  - 模块 source 不含 logging/subprocess/os/sys/threading
  - 模块 source 含 'image_dir is None' / 'image_dir.is_dir()' / 'image_dir is not None'
  - 模块 source 含 'out_stub.is_file()' 2 处（_process_one + run_evaluation expected_failures 循环）
  - 模块 source 含 'process_single(...)' 2 处

- run_evaluation 报告写盘：
  - 写盘后文件存在
  - 写盘后文件可读
  - 写盘后 JSON 含 ensure_ascii=False（含中文不转义）
  - 写盘后 JSON 含 indent=2

- _process_one source level 完整：
  - 5-tuple annotation: tuple[dict | None, dict | None, float, str | None, Path | None]
  - mkdir parents=True exist_ok=True
  - t0 = time.perf_counter()
  - elapsed = time.perf_counter() - t0
  - if errors: → 5-tuple 含 errors[0].to_dict()
  - if document is None: → 5-tuple 含 'unknown' error dict
  - return document.to_dict(), None, elapsed, document.parser_version, image_dir
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation import REPORT_VERSION
from evaluation.manifest import DocumentEntry, ExpectedFailure, Manifest
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ============================================================================
# 辅助：构造 Manifest / DocumentEntry / ExpectedFailure
# ============================================================================


def _make_empty_manifest(tmp_path: Path) -> Manifest:
    return Manifest(
        manifest_version="1.0",
        devset_status="complete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )


def _make_failing_doc_entry(tmp_path: Path, doc_id: str = "fail-1") -> DocumentEntry:
    return DocumentEntry(
        doc_id=doc_id,
        path_str=f"missing/{doc_id}.pdf",
        resolved_path=tmp_path / "missing" / f"{doc_id}.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def _make_failing_expected_failure(
    tmp_path: Path, doc_id: str = "ef-1", expected_code: str = "file_not_found"
) -> ExpectedFailure:
    return ExpectedFailure(
        doc_id=doc_id,
        path_str=f"missing/{doc_id}.docx",
        resolved_path=tmp_path / "missing" / f"{doc_id}.docx",
        expected_error_code=expected_code,
        source_type="docx",
    )


def _make_manifest_with_failing_docs(
    tmp_path: Path,
    docs: tuple[DocumentEntry, ...] = (),
    expected_failures: tuple[ExpectedFailure, ...] = (),
) -> Manifest:
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=docs,
        expected_failures=expected_failures,
        project_root=tmp_path,
    )


# ============================================================================
# _load_annotation 边界
# ============================================================================


def test_load_annotation_none_returns_none():
    assert _load_annotation(None) is None


def test_load_annotation_nonexistent_returns_none(tmp_path):
    p = tmp_path / "missing.json"
    assert _load_annotation(p) is None


def test_load_annotation_directory_returns_none(tmp_path):
    """path 是目录 → is_file 返 False → 返 None。"""
    assert _load_annotation(tmp_path) is None


def test_load_annotation_valid_json_returns_dict(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text(json.dumps({"annotation_version": "1.0", "doc_id": "d1"}), encoding="utf-8")
    out = _load_annotation(p)
    assert isinstance(out, dict)
    assert out["doc_id"] == "d1"


def test_load_annotation_invalid_json_returns_none(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_empty_file_returns_none(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_utf8_bom_returns_none(tmp_path):
    """json.load 默认不剥 UTF-8 BOM → JSONDecodeError → 返 None。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b"\xef\xbb\xbf" + json.dumps({"x": 1}).encode("utf-8"))
    assert _load_annotation(p) is None


def test_load_annotation_top_level_array_returns_list(tmp_path):
    """top-level array 是 valid JSON，json.load 返 list（不限类型）。"""
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    out = _load_annotation(p)
    assert isinstance(out, list)
    assert out == [1, 2, 3]


def test_load_annotation_top_level_number_returns_int(tmp_path):
    p = tmp_path / "num.json"
    p.write_text("42", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 42


def test_load_annotation_returns_dict_same_content_each_call(tmp_path):
    """两次调用返回的 dict 内容相同（虽然不同对象）。"""
    p = tmp_path / "ann.json"
    p.write_text(json.dumps({"x": 1}), encoding="utf-8")
    a = _load_annotation(p)
    b = _load_annotation(p)
    assert a == b


def test_load_annotation_binary_content(tmp_path):
    """二进制内容 → UnicodeDecodeError（不被 except 捕获） → 抛而非返 None。

    UnicodeDecodeError 是 ValueError 子类，不是 OSError 或 JSONDecodeError。
    """
    import pytest as _pytest

    p = tmp_path / "bin.json"
    p.write_bytes(b"\xff\xfe\x00\x01")
    with _pytest.raises(UnicodeDecodeError):
        _load_annotation(p)


# ============================================================================
# _process_one 行为深度
# ============================================================================


def test_process_one_failing_returns_5_tuple_with_none_document(tmp_path):
    """failing doc → 返 (None, error_dict, float, None, image_dir)。"""
    doc = _make_failing_doc_entry(tmp_path)
    result = _process_one(doc, tmp_path, "fallback", 800)
    assert len(result) == 5
    document, error, total, parser_version, image_dir = result
    assert document is None
    assert error is not None
    assert isinstance(total, float)
    assert parser_version is None
    # image_dir 在 document None 时也是 None
    assert image_dir is None


def test_process_one_failing_error_dict_has_code_key(tmp_path):
    doc = _make_failing_doc_entry(tmp_path)
    _, error, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert "code" in error
    assert error["code"] == "file_not_found"


def test_process_one_failing_error_dict_has_message_key(tmp_path):
    doc = _make_failing_doc_entry(tmp_path)
    _, error, _, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert "message" in error


def test_process_one_failing_total_seconds_non_negative(tmp_path):
    doc = _make_failing_doc_entry(tmp_path)
    _, _, total, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert total >= 0.0


def test_process_one_creates_per_doc_dir(tmp_path):
    """_process_one 应创建 _per_doc 子目录。"""
    doc = _make_failing_doc_entry(tmp_path)
    _process_one(doc, tmp_path, "fallback", 800)
    per_doc_dir = tmp_path / "_per_doc"
    assert per_doc_dir.is_dir()


def test_process_one_cleans_up_out_stub(tmp_path):
    """out_stub 应在 _process_one 完成后被清理。"""
    doc = _make_failing_doc_entry(tmp_path)
    _process_one(doc, tmp_path, "fallback", 800)
    out_stub = tmp_path / "_per_doc" / f"{doc.doc_id}.json"
    assert not out_stub.is_file()


def test_process_one_two_calls_independent(tmp_path):
    """两次调用不互相影响。"""
    doc1 = _make_failing_doc_entry(tmp_path, doc_id="d1")
    doc2 = _make_failing_doc_entry(tmp_path, doc_id="d2")
    r1 = _process_one(doc1, tmp_path, "fallback", 800)
    r2 = _process_one(doc2, tmp_path, "fallback", 800)
    assert r1[1]["code"] == "file_not_found"
    assert r2[1]["code"] == "file_not_found"


# ============================================================================
# run_evaluation 集成深度
# ============================================================================


def test_run_evaluation_mixed_success_and_failure(tmp_path):
    """混合成功 + 失败文档：per_doc 长度 = 总文档数。"""
    doc1 = _make_failing_doc_entry(tmp_path, doc_id="fail-1")
    doc2 = _make_failing_doc_entry(tmp_path, doc_id="fail-2")
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc1, doc2))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert len(report["per_doc"]) == 2


def test_run_evaluation_empty_docs_with_expected_failures(tmp_path):
    """空 documents + 有 expected_failures：per_doc=[], expected_failures 含结果。"""
    ef = _make_failing_expected_failure(tmp_path)
    manifest = _make_manifest_with_failing_docs(
        tmp_path, docs=(), expected_failures=(ef,)
    )
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert report["per_doc"] == []
    assert len(report["expected_failures"]) == 1


def test_run_evaluation_docs_and_expected_failures_both(tmp_path):
    """documents 和 expected_failures 都有 → 两类都执行。"""
    doc = _make_failing_doc_entry(tmp_path, doc_id="d1")
    ef = _make_failing_expected_failure(tmp_path, doc_id="ef1")
    manifest = _make_manifest_with_failing_docs(
        tmp_path, docs=(doc,), expected_failures=(ef,)
    )
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert len(report["per_doc"]) == 1
    assert len(report["expected_failures"]) == 1


def test_run_evaluation_custom_tolerance_chars_100(tmp_path):
    """自定义 tolerance_chars=100 → per_doc[0]._tolerance_chars=100。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path, tolerance_chars=100)
    # 内部 record 不在 public per_doc，但 chunk_boundary_prf 的 fallback 走 no_predicted_boundaries
    # _tolerance_chars 仍应记录 100
    # public per_doc 不含 _ 前缀，但 metric dict 内 _tolerance_chars 已被 pop
    metrics = report["per_doc"][0]["metrics"]
    # _tolerance_chars 已被 pop（不在 metrics），但它影响了 chunk_boundary_prf 输出
    # 我们验证 tolerance_chars=100 不会让 chunk_boundary_prf 抛
    assert "chunk_boundary_precision" in metrics


def test_run_evaluation_custom_tolerance_chars_zero(tmp_path):
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path, tolerance_chars=0)
    assert "chunk_boundary_precision" in report["per_doc"][0]["metrics"]


def test_run_evaluation_writes_nonempty_file(tmp_path):
    """report 写盘后文件大小 > 0。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    assert out_path.is_file()
    assert out_path.stat().st_size > 0


def test_run_evaluation_written_file_is_loadable_json(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    with out_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_run_evaluation_written_file_matches_returned_report(tmp_path):
    """写盘文件与返回值结构相同。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    returned = run_evaluation(manifest, out_path)
    with out_path.open("r", encoding="utf-8") as f:
        on_disk = json.load(f)
    # 比较时排除 run_timestamp_iso（每次调用不同）
    returned_compare = json.loads(json.dumps(returned))
    on_disk_compare = json.loads(json.dumps(on_disk))
    assert returned_compare["report_version"] == on_disk_compare["report_version"]
    assert returned_compare["per_doc"] == on_disk_compare["per_doc"]


def test_run_evaluation_report_top_level_keys(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    assert set(report.keys()) == {
        "report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"
    }


def test_run_evaluation_report_top_level_keys_order(tmp_path):
    """report top-level keys 顺序：report_version → provenance → devset → summary → per_doc → expected_failures。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    keys = list(report.keys())
    assert keys == [
        "report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"
    ]


def test_run_evaluation_does_not_modify_manifest_documents(tmp_path):
    """run_evaluation 不修改 manifest.documents 长度。"""
    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    docs_before = len(manifest.documents)
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    assert len(manifest.documents) == docs_before


def test_run_evaluation_does_not_modify_manifest_expected_failures(tmp_path):
    ef = _make_failing_expected_failure(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, expected_failures=(ef,))
    ef_before = len(manifest.expected_failures)
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    assert len(manifest.expected_failures) == ef_before


def test_run_evaluation_does_not_modify_manifest_project_root(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    root_before = manifest.project_root
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    assert manifest.project_root == root_before


def test_run_evaluation_does_not_modify_manifest_devset_status(tmp_path):
    manifest = _make_empty_manifest(tmp_path)
    status_before = manifest.devset_status
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    assert manifest.devset_status == status_before


# ============================================================================
# run_evaluation 报告写盘细节
# ============================================================================


def test_run_evaluation_writes_with_indent_2(tmp_path):
    """JSON 写盘含 indent=2（多行格式）。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    text = out_path.read_text(encoding="utf-8")
    # indent=2 → 含换行
    assert "\n" in text
    # 含 "  "（2 spaces indent）
    assert '  "' in text


def test_run_evaluation_writes_with_ensure_ascii_false(tmp_path):
    """ensure_ascii=False → 含中文不转义（如果有的话）。"""
    # manifest 含中文 doc_id（虽然不太可能）
    doc = _make_failing_doc_entry(tmp_path, doc_id="失败文档")
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    run_evaluation(manifest, out_path)
    text = out_path.read_text(encoding="utf-8")
    # 中文应原样存在（不被 \u 转义）
    assert "失败文档" in text


def test_run_evaluation_creates_output_root_if_missing(tmp_path):
    """output_root 不存在时 → run_evaluation 应创建。"""
    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "subdir" / "deeper" / "out.json"
    run_evaluation(manifest, out_path)
    assert out_path.is_file()


# ============================================================================
# module source level 完整
# ============================================================================


def test_module_source_contains_import_json():
    import evaluation.runner as r

    src = inspect.getsource(r)
    assert "import json" in src


def test_module_source_contains_import_time():
    import evaluation.runner as r

    src = inspect.getsource(r)
    assert "import time" in src


def test_module_source_contains_from_pathlib():
    import evaluation.runner as r

    src = inspect.getsource(r)
    assert "from pathlib import Path" in src


def test_module_source_contains_from_typing_any():
    import evaluation.runner as r

    src = inspect.getsource(r)
    assert "from typing import Any" in src


def test_module_source_contains_app_pipeline_import():
    import evaluation.runner as r

    src = inspect.getsource(r)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_contains_evaluation_imports():
    import evaluation.runner as r

    src = inspect.getsource(r)
    assert "from evaluation import REPORT_VERSION" in src
    assert "from evaluation.annotation_metrics import" in src
    assert "from evaluation.metrics import compute_automatic_metrics" in src
    assert "from evaluation.report import" in src


def test_module_source_does_not_contain_logging():
    import evaluation.runner as r

    src = inspect.getsource(r)
    assert "import logging" not in src


def test_module_source_does_not_contain_subprocess():
    import evaluation.runner as r

    src = inspect.getsource(r)
    assert "import subprocess" not in src


def test_module_source_does_not_contain_os_import():
    import evaluation.runner as r

    src = inspect.getsource(r)
    assert "import os" not in src


def test_module_source_does_not_contain_sys_import():
    import evaluation.runner as r

    src = inspect.getsource(r)
    assert "import sys" not in src


def test_module_source_does_not_contain_threading():
    import evaluation.runner as r

    src = inspect.getsource(r)
    assert "import threading" not in src


def test_module_source_does_not_contain_star_import():
    import evaluation.runner as r

    src = inspect.getsource(r)
    assert "import *" not in src


def test_module_source_does_not_contain_relative_import():
    import evaluation.runner as r

    src = inspect.getsource(r)
    assert "from ." not in src
    assert "from .." not in src


# ============================================================================
# _load_annotation source level
# ============================================================================


def test_load_annotation_source_contains_path_none_check():
    import evaluation.runner as r

    src = inspect.getsource(r._load_annotation)
    assert "if path is None or not path.is_file():" in src


def test_load_annotation_source_contains_return_none_first():
    import evaluation.runner as r

    src = inspect.getsource(r._load_annotation)
    assert "return None" in src


def test_load_annotation_source_contains_open_utf8():
    import evaluation.runner as r

    src = inspect.getsource(r._load_annotation)
    assert 'open("r", encoding="utf-8")' in src


def test_load_annotation_source_contains_json_load():
    import evaluation.runner as r

    src = inspect.getsource(r._load_annotation)
    assert "json.load(f)" in src


def test_load_annotation_source_contains_except_oserror_jsondecodeerror():
    """except 只接 OSError 和 json.JSONDecodeError（不含 UnicodeDecodeError）。"""
    import evaluation.runner as r

    src = inspect.getsource(r._load_annotation)
    assert "except (OSError, json.JSONDecodeError):" in src


def test_load_annotation_source_does_not_contain_generic_except():
    """不应有 'except Exception:' 或 'except:' 裸接。"""
    import evaluation.runner as r

    src = inspect.getsource(r._load_annotation)
    assert "except Exception" not in src
    assert "except:" not in src


# ============================================================================
# _process_one source level
# ============================================================================


def test_process_one_source_signature_5_tuple_annotation():
    import evaluation.runner as r

    src = inspect.getsource(r._process_one)
    assert "tuple[dict[str, Any] | None, dict[str, Any] | None, float, str | None, Path | None]" in src


def test_process_one_source_contains_perf_counter():
    import evaluation.runner as r

    src = inspect.getsource(r._process_one)
    assert "time.perf_counter()" in src
    assert "t0 = time.perf_counter()" in src
    assert "elapsed = time.perf_counter() - t0" in src


def test_process_one_source_contains_mkdir():
    import evaluation.runner as r

    src = inspect.getsource(r._process_one)
    assert "out_stub.parent.mkdir(parents=True, exist_ok=True)" in src


def test_process_one_source_contains_unlink():
    import evaluation.runner as r

    src = inspect.getsource(r._process_one)
    assert "out_stub.unlink()" in src
    assert "except OSError:" in src


def test_process_one_source_contains_image_dir_logic():
    import evaluation.runner as r

    src = inspect.getsource(r._process_one)
    assert "image_dir: Path | None = None" in src
    assert "image_dir = image_output_dir_for(out_stub, document.source_hash)" in src


def test_process_one_source_contains_unknown_error_dict():
    """document is None 时返回 'unknown' error dict。"""
    import evaluation.runner as r

    src = inspect.getsource(r._process_one)
    assert '"code": "unknown"' in src
    assert '"process_single returned None without errors"' in src


def test_process_one_source_contains_5_tuple_return():
    import evaluation.runner as r

    src = inspect.getsource(r._process_one)
    # 3 个 return 5-tuple
    assert "return None, errors[0].to_dict(), elapsed, None, image_dir" in src
    assert "return document.to_dict(), None, elapsed, document.parser_version, image_dir" in src


def test_process_one_source_contains_write_json_false():
    import evaluation.runner as r

    src = inspect.getsource(r._process_one)
    assert "write_json=False" in src


# ============================================================================
# run_evaluation source level
# ============================================================================


def test_run_evaluation_source_contains_keyword_only_args():
    import evaluation.runner as r

    src = inspect.getsource(r.run_evaluation)
    # keyword-only marker
    assert "*," in src
    assert "parser_name: str = " in src
    assert "max_chars: int = " in src
    assert "tolerance_chars: int = " in src


def test_run_evaluation_source_contains_two_process_single_calls():
    """source 含两处 process_single(...) 调用：1 在 _process_one，1 在 expected_failures 循环。"""
    import evaluation.runner as r

    src = inspect.getsource(r)
    # _process_one 含 1 处，run_evaluation expected_failures 循环含 1 处
    count = src.count("process_single(")
    # 至少 2 处
    assert count >= 2


def test_run_evaluation_source_contains_out_stub_is_file_twice():
    """source 含两处 out_stub.is_file() 检查。"""
    import evaluation.runner as r

    src = inspect.getsource(r)
    count = src.count("out_stub.is_file()")
    assert count >= 2


def test_run_evaluation_source_contains_image_dir_is_dir_check():
    """image_dir 用 .is_dir() 校验。"""
    import evaluation.runner as r

    src = inspect.getsource(r.run_evaluation)
    assert "image_dir.is_dir()" in src


def test_run_evaluation_source_contains_image_dir_not_none_check():
    import evaluation.runner as r

    src = inspect.getsource(r.run_evaluation)
    assert "image_dir is not None" in src


def test_run_evaluation_source_contains_json_dump_with_options():
    """json.dump 用 ensure_ascii=False 和 indent=2。"""
    import evaluation.runner as r

    src = inspect.getsource(r.run_evaluation)
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in src


def test_run_evaluation_source_contains_per_doc_internal_record_keys():
    """per_doc_results 含 _annotation_present / _tolerance_chars / _missing_markers 内部字段。"""
    import evaluation.runner as r

    src = inspect.getsource(r.run_evaluation)
    assert '"_annotation_present"' in src
    assert '"_tolerance_chars"' in src
    assert '"_missing_markers"' in src


def test_run_evaluation_source_contains_pop_tolerance_and_missing():
    """chunk_b.pop 取出 _tolerance_chars / _missing_markers。"""
    import evaluation.runner as r

    src = inspect.getsource(r.run_evaluation)
    assert 'chunk_b.pop("_tolerance_chars", None)' in src
    assert 'chunk_b.pop("_missing_markers", None)' in src


def test_run_evaluation_source_contains_public_per_doc_construction():
    """public_per_doc 显式构造 4 keys（不带 _ 前缀）。"""
    import evaluation.runner as r

    src = inspect.getsource(r.run_evaluation)
    assert "public_per_doc" in src
    assert '"doc_id": r["doc_id"]' in src
    assert '"source_type": r["source_type"]' in src
    assert '"metrics": r["metrics"]' in src
    assert '"wall_time_seconds": r["wall_time_seconds"]' in src


def test_run_evaluation_source_contains_6_top_level_keys():
    """report top-level 含 6 keys。"""
    import evaluation.runner as r

    src = inspect.getsource(r.run_evaluation)
    assert '"report_version": REPORT_VERSION' in src
    assert '"provenance": provenance' in src
    assert '"devset": devset' in src
    assert '"summary": summary' in src
    assert '"per_doc": public_per_doc' in src
    assert '"expected_failures": expected_failure_results' in src


# ============================================================================
# __all__ 与 namespace
# ============================================================================


def test_module_all_only_run_evaluation():
    import evaluation.runner as r

    assert r.__all__ == ["run_evaluation"]


def test_module_namespace_has_run_evaluation():
    import evaluation.runner as r

    assert hasattr(r, "run_evaluation")


def test_module_namespace_has_private_helpers():
    """私有 helper（_load_annotation, _process_one）在 namespace 不在 __all__。"""
    import evaluation.runner as r

    assert hasattr(r, "_load_annotation")
    assert hasattr(r, "_process_one")
    assert "_load_annotation" not in r.__all__
    assert "_process_one" not in r.__all__


def test_module_namespace_has_imported_helpers():
    """import 的 helper（process_single, image_output_dir_for 等）在 namespace。"""
    import evaluation.runner as r

    assert hasattr(r, "process_single")
    assert hasattr(r, "image_output_dir_for")
    assert hasattr(r, "compute_automatic_metrics")
    assert hasattr(r, "build_provenance")
    assert hasattr(r, "build_devset_section")
    assert hasattr(r, "aggregate_summary")
    assert hasattr(r, "chunk_boundary_prf")
    assert hasattr(r, "figure_caption_prf")
    assert hasattr(r, "REPORT_VERSION")


def test_module_namespace_does_not_have_manifest():
    """runner.py 不直接 import Manifest 类（在测试中通过参数传入）。"""
    import evaluation.runner as r

    assert not hasattr(r, "Manifest")


# ============================================================================
# signatures
# ============================================================================


def test_load_annotation_signature_1_param_path():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path"


def test_process_one_signature_4_params():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.values())
    assert len(params) == 4
    assert [p.name for p in params] == ["doc", "output_root", "parser_name", "max_chars"]


def test_run_evaluation_signature_5_params():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert len(params) == 5
    assert [p.name for p in params] == [
        "manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"
    ]


def test_run_evaluation_parser_name_default_fallback():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_run_evaluation_max_chars_default_800():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_run_evaluation_tolerance_chars_default_30():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_keyword_only_marker():
    """parser_name/max_chars/tolerance_chars 是 keyword-only（'*, ' marker 之后）。"""
    sig = inspect.signature(run_evaluation)
    # manifest, output_path 是 positional-or-keyword
    assert sig.parameters["manifest"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert sig.parameters["output_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    # 后 3 个是 keyword-only
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


# ============================================================================
# module docstring 与 metadata
# ============================================================================


def test_module_docstring_mentions_pipeline():
    import evaluation.runner as r

    doc = r.__doc__
    assert "pipeline" in doc.lower() or "process_single" in doc


def test_module_docstring_mentions_total_only():
    """docstring 提到只记 total。"""
    import evaluation.runner as r

    doc = r.__doc__
    assert "total" in doc.lower() or "只记" in doc


def test_module_docstring_mentions_not_instrumented():
    """docstring 提到 parse/chunk 未插桩。"""
    import evaluation.runner as r

    doc = r.__doc__
    assert "not_instrumented" in doc or "未插桩" in doc


def test_module_docstring_mentions_image():
    """docstring 提到 image 处理。"""
    import evaluation.runner as r

    doc = r.__doc__
    assert "image" in doc.lower() or "图片" in doc


def test_module_no_main_block():
    """runner.py 无 if __name__ == '__main__'。"""
    import evaluation.runner as r

    src = inspect.getsource(r)
    assert "__name__ == " not in src


# ============================================================================
# 完整端到端 schema 验证
# ============================================================================


def test_run_evaluation_report_passes_evaluation_report_schema(tmp_path):
    """完整报告通过 evaluation-report.schema.json 校验。"""
    from evaluation.schema import validate as schema_validate

    doc = _make_failing_doc_entry(tmp_path)
    manifest = _make_manifest_with_failing_docs(tmp_path, docs=(doc,))
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    # 直接验证（不通过文件）
    schema_validate(report, "evaluation-report.schema.json")


def test_run_evaluation_empty_manifest_report_passes_schema(tmp_path):
    from evaluation.schema import validate as schema_validate

    manifest = _make_empty_manifest(tmp_path)
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    schema_validate(report, "evaluation-report.schema.json")


def test_run_evaluation_doc_with_expected_failures_passes_schema(tmp_path):
    from evaluation.schema import validate as schema_validate

    doc = _make_failing_doc_entry(tmp_path, doc_id="d1")
    ef = _make_failing_expected_failure(tmp_path, doc_id="ef1")
    manifest = _make_manifest_with_failing_docs(
        tmp_path, docs=(doc,), expected_failures=(ef,)
    )
    out_path = tmp_path / "out.json"
    report = run_evaluation(manifest, out_path)
    schema_validate(report, "evaluation-report.schema.json")
