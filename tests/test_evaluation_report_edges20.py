"""evaluation/report.py 边角测试 - 第二十轮（Round 285）。

edges19 已覆盖：模块 imports / _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS source-level
完整 + value 精确 + tuple 验证 / get_git_provenance source 详尽 / get_dependency_versions source 详尽 /
build_provenance source 详尽 / build_devset_section source 详尽 / aggregate_summary source 详尽 /
__all__ 5 entries / namespace 详细 / 模块 source 不含 print/logging/async/threading 等 / 签名 introspection /
模块 docstring 详细 / aggregate_summary 行为（4 keys / silent_drop_total None when empty / 12 metrics）。

edges20 补强未覆盖的角度：**Schema 交叉验证** + **subprocess.run / importlib.metadata 深度模拟** +
**aggregate_summary 跨多文档混合行为**：
- Schema 交叉验证：
  - build_provenance 输出可通过 evaluation-report.schema.json 中 $defs/provenance 校验
  - build_devset_section 输出可通过 evaluation-report.schema.json 中 $defs/devset 校验
  - aggregate_summary 输出可通过 evaluation-report.schema.json 中 $defs/summary 校验
  - end-to-end 拼装：report_version + provenance + devset + summary + per_doc → 通过 evaluation-report.schema.json
  - get_dependency_versions 输出 keys（pdfplumber/python-docx/pypdfium2）符合 dependencies schema

- get_git_provenance subprocess.run 深度模拟（monkeypatch）：
  - rev-parse returncode=0 + stdout='abc123\n' → commit='abc123'
  - rev-parse returncode=0 + stdout='\n'（空 line） → commit=None
  - rev-parse returncode=0 + stdout='   '（only whitespace） → commit=None（strip 后空）
  - rev-parse returncode=1（git 不可用） → commit=None
  - rev-parse 抛 OSError → commit=None, dirty=True
  - rev-parse 抛 subprocess.SubprocessError（含 TimeoutExpired） → commit=None, dirty=True
  - status returncode=0 + stdout='M file.txt\n' → dirty=True
  - status returncode=0 + stdout='\n' → dirty=False
  - status returncode=0 + stdout='   ' → dirty=False
  - status returncode=1 → dirty=False（returncode != 0 短路）
  - status 抛 OSError → 进入 except，commit=None, dirty=True
  - 两次 subprocess.run 调用，按顺序：先 rev-parse，后 status --porcelain

- get_dependency_versions 深度模拟（monkeypatch importlib.metadata）：
  - 所有 3 包都找到版本 → 返回 dict 含 3 keys，values 都非 None
  - 包不存在（PackageNotFoundError） → 该 key value=None
  - 包抛 Exception（非 PackageNotFoundError） → 该 key value=None
  - 返回 dict 的 keys 顺序精确：['pdfplumber', 'python-docx', 'pypdfium2']

- aggregate_summary 跨多文档混合行为：
  - 多文档都含 element_count_total → sum 累加 + participating_docs=count
  - 多文档部分含 element_count_total，部分缺 → sum 只算 participating，participating_docs=count
  - 多文档部分 metric value=None → 不参与 sum/avg
  - 多文档部分 metric value=0 → 参与 sum（不算 None）
  - 多文档 pipeline_success 部分真部分假 → success_count=count True, total=count, rate=count/total
  - 多文档全部 pipeline_success=True → rate=1.0
  - 多文档全部 pipeline_success=False → rate=0.0
  - 多文档部分 pipeline_success=None → 不算 success，但 total 仍 += 1
  - 多文档 silent_drop_count 部分含值，部分 None → 只 sum 非 None 的
  - 多文档 silent_drop_count 全 None → silent_drop_total=None
  - 多文档 silent_drop_count 都=0 → silent_drop_total=0
  - 多文档 ratio metric macro_average 正确（sum/len，含 0）
  - 多文档 ratio metric 部分 None → not_evaluated=count None
  - 多文档 ratio metric 全 None → macro_average=None, participating_docs=0, not_evaluated=total

- build_provenance 输出深度：
  - run_timestamp_iso 可解析为 datetime（合法 ISO 格式）
  - run_timestamp_iso 含时区偏移（astimezone() 包含 tzinfo）
  - 不同时刻两次调用 run_timestamp_iso 不同（时间前进）
  - dependencies keys 精确顺序：['pdfplumber', 'python-docx', 'pypdfium2']
  - max_chars int 转换：800 → 800（int）；800.0 → 800（int）；800.5 → 800（int truncate）

- build_devset_section duck typing 深度：
  - Manifest dataclass（frozen）作为输入
  - 自定义 namespace 对象作为输入（duck typing）
  - 缺 status 属性 → AttributeError 含 'devset_status'
  - 缺 file_count 属性 → AttributeError 含 'file_count'

- 子进程超时路径：
  - subprocess.TimeoutExpired 是 subprocess.SubprocessError 子类
  - 在 except 中被捕获
"""

from __future__ import annotations

import inspect
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

import evaluation.report as report_module
from evaluation import EVALUATOR_VERSION, REPORT_VERSION
from evaluation.report import (
    _COUNT_METRICS,
    _RATIO_METRICS,
    _SUCCESS_BOOL_METRICS,
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)
from evaluation.schema import validate as schema_validate


# ============================================================================
# Schema 交叉验证
# ============================================================================


def test_build_provenance_output_passes_provenance_schema(tmp_path):
    """build_provenance 输出符合 evaluation-report.schema.json 的 $defs/provenance。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    # 取出 provenance 子 schema，校验
    full_schema = json.loads(
        (Path(__file__).resolve().parent.parent / "schemas" / "evaluation-report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    prov_schema = {
        **full_schema["$defs"]["provenance"],
        "$defs": full_schema.get("$defs", {}),
    }
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(prov_schema)
    errs = list(validator.iter_errors(out))
    assert errs == [], f"provenance schema errors: {errs}"


def test_build_devset_section_output_passes_devset_schema():
    """build_devset_section 输出符合 evaluation-report.schema.json 的 $defs/devset。"""
    class FakeManifest:
        devset_status = "incomplete"
        file_count = 5
        content_group_count = 3
        pdf_count = 2
        docx_count = 3
        categories_covered = ["cat_a", "cat_b"]

    out = build_devset_section(FakeManifest())
    full_schema = json.loads(
        (Path(__file__).resolve().parent.parent / "schemas" / "evaluation-report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    devset_schema = full_schema["$defs"]["devset"]
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(devset_schema)
    errs = list(validator.iter_errors(out))
    assert errs == [], f"devset schema errors: {errs}"


def test_aggregate_summary_output_passes_summary_schema():
    """aggregate_summary 输出符合 evaluation-report.schema.json 的 $defs/summary。"""
    out = aggregate_summary([])
    full_schema = json.loads(
        (Path(__file__).resolve().parent.parent / "schemas" / "evaluation-report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    summary_schema = full_schema["$defs"]["summary"]
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(summary_schema)
    errs = list(validator.iter_errors(out))
    assert errs == [], f"summary schema errors: {errs}"


def test_aggregate_summary_with_filled_data_passes_summary_schema():
    """aggregate_summary 含实际数据时也通过 summary schema。"""
    per_doc = [
        {
            "metrics": {
                "element_count_total": {"value": 10},
                "pipeline_success": {"value": True},
                "text_preservation_equal": {"value": 1.0},
                "silent_drop_count": {"value": 0},
            }
        },
        {
            "metrics": {
                "element_count_total": {"value": 20},
                "pipeline_success": {"value": False},
                "text_preservation_equal": {"value": 0.5},
                "silent_drop_count": {"value": 2},
            }
        }
    ]
    out = aggregate_summary(per_doc)
    full_schema = json.loads(
        (Path(__file__).resolve().parent.parent / "schemas" / "evaluation-report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    summary_schema = full_schema["$defs"]["summary"]
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(summary_schema)
    errs = list(validator.iter_errors(out))
    assert errs == [], f"summary schema errors: {errs}"


def test_get_dependency_versions_output_passes_dependencies_schema():
    """dependencies schema 要 value 是 str 或 null。"""
    out = get_dependency_versions()
    full_schema = json.loads(
        (Path(__file__).resolve().parent.parent / "schemas" / "evaluation-report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    # 用整个 provenance schema（dependencies 是子字段）
    prov_schema = full_schema["$defs"]["provenance"]
    # 包一个 minimal provenance dict 让 dependencies 通过校验
    minimal_prov = {
        "git_commit": "abc",
        "git_dirty": False,
        "evaluator_version": "1.1",
        "report_version": "1.1",
        "parser_name": "fallback",
        "parser_version": None,
        "dependencies": out,
        "max_chars": 800,
        "run_timestamp_iso": "2026-01-01T00:00:00+00:00",
    }
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(prov_schema)
    errs = list(validator.iter_errors(minimal_prov))
    assert errs == [], f"dependencies schema errors: {errs}"


def test_end_to_end_report_assembly_passes_full_schema(tmp_path):
    """拼装完整 evaluation-report 实例，通过完整 schema 校验。"""
    class FakeManifest:
        devset_status = "incomplete"
        file_count = 1
        content_group_count = 1
        pdf_count = 1
        docx_count = 0
        categories_covered = ["cat_a"]

    provenance = build_provenance(tmp_path, "fallback", 800, None)
    devset = build_devset_section(FakeManifest())
    summary = aggregate_summary([])
    per_doc = [
        {
            "doc_id": "doc1",
            "source_type": "pdf",
            "metrics": {},
            "wall_time_seconds": {
                "total": 0.1,
                "parse": None,
                "chunk": None,
                "parse_reason": "not_instrumented",
                "chunk_reason": "not_instrumented",
            },
        }
    ]
    full_report = {
        "report_version": REPORT_VERSION,
        "provenance": provenance,
        "devset": devset,
        "summary": summary,
        "per_doc": per_doc,
    }
    schema_validate(full_report, "evaluation-report.schema.json")  # 不抛


# ============================================================================
# get_git_provenance subprocess.run 深度模拟
# ============================================================================


def _make_completed(returncode: int, stdout: str = "", stderr: str = ""):
    """构造一个简单的 CompletedProcess-like 对象。"""
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_get_git_provenance_revparse_success_with_commit(tmp_path, monkeypatch):
    """rev-parse 成功 + 输出 commit → git_commit='abc123'。"""
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd == ["git", "rev-parse", "HEAD"]:
            return _make_completed(0, stdout="abc123\n")
        if cmd == ["git", "status", "--porcelain"]:
            return _make_completed(0, stdout="")
        return _make_completed(1)

    monkeypatch.setattr(report_module.subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is False


def test_get_git_provenance_revparse_success_with_empty_stdout(tmp_path, monkeypatch):
    """rev-parse returncode=0 + stdout='\n' → commit=None（strip 后空）。"""
    def fake_run(cmd, **kwargs):
        if cmd == ["git", "rev-parse", "HEAD"]:
            return _make_completed(0, stdout="\n")
        if cmd == ["git", "status", "--porcelain"]:
            return _make_completed(0, stdout="")
        return _make_completed(1)

    monkeypatch.setattr(report_module.subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_revparse_success_with_whitespace_stdout(tmp_path, monkeypatch):
    """rev-parse stdout='   ' → strip 后空 → commit=None。"""
    def fake_run(cmd, **kwargs):
        if cmd == ["git", "rev-parse", "HEAD"]:
            return _make_completed(0, stdout="   ")
        if cmd == ["git", "status", "--porcelain"]:
            return _make_completed(0, stdout="")
        return _make_completed(1)

    monkeypatch.setattr(report_module.subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_revparse_returncode_nonzero(tmp_path, monkeypatch):
    """rev-parse returncode=1 → commit=None（git 不可用）。"""
    def fake_run(cmd, **kwargs):
        if cmd == ["git", "rev-parse", "HEAD"]:
            return _make_completed(1)
        if cmd == ["git", "status", "--porcelain"]:
            return _make_completed(0, stdout="")
        return _make_completed(1)

    monkeypatch.setattr(report_module.subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_status_porcelain_with_changes(tmp_path, monkeypatch):
    """status --porcelain 输出 'M file.txt\n' → dirty=True。"""
    def fake_run(cmd, **kwargs):
        if cmd == ["git", "rev-parse", "HEAD"]:
            return _make_completed(0, stdout="abc\n")
        if cmd == ["git", "status", "--porcelain"]:
            return _make_completed(0, stdout="M file.txt\n")
        return _make_completed(1)

    monkeypatch.setattr(report_module.subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


def test_get_git_provenance_status_porcelain_empty_stdout(tmp_path, monkeypatch):
    """status --porcelain stdout='' → dirty=False（returncode=0 and not strip）。"""
    def fake_run(cmd, **kwargs):
        if cmd == ["git", "rev-parse", "HEAD"]:
            return _make_completed(0, stdout="abc\n")
        if cmd == ["git", "status", "--porcelain"]:
            return _make_completed(0, stdout="")
        return _make_completed(1)

    monkeypatch.setattr(report_module.subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_get_git_provenance_status_porcelain_whitespace_only(tmp_path, monkeypatch):
    """status --porcelain stdout='   \n' → strip 后空 → dirty=False。"""
    def fake_run(cmd, **kwargs):
        if cmd == ["git", "rev-parse", "HEAD"]:
            return _make_completed(0, stdout="abc\n")
        if cmd == ["git", "status", "--porcelain"]:
            return _make_completed(0, stdout="   \n")
        return _make_completed(1)

    monkeypatch.setattr(report_module.subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_get_git_provenance_status_porcelain_returncode_nonzero(tmp_path, monkeypatch):
    """status --porcelain returncode=1 → 'r2.returncode == 0' 短路 → dirty=False。"""
    def fake_run(cmd, **kwargs):
        if cmd == ["git", "rev-parse", "HEAD"]:
            return _make_completed(0, stdout="abc\n")
        if cmd == ["git", "status", "--porcelain"]:
            return _make_completed(1, stdout="M file\n")
        return _make_completed(1)

    monkeypatch.setattr(report_module.subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_get_git_provenance_revparse_raises_oserror(tmp_path, monkeypatch):
    """rev-parse 抛 OSError → 进 except → commit=None, dirty=True。"""
    def fake_run(cmd, **kwargs):
        raise OSError("not found")

    monkeypatch.setattr(report_module.subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_revparse_raises_subprocess_error(tmp_path, monkeypatch):
    """rev-parse 抛 subprocess.SubprocessError → 进 except。"""
    def fake_run(cmd, **kwargs):
        raise subprocess.SubprocessError("boom")

    monkeypatch.setattr(report_module.subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_revparse_raises_timeout_expired(tmp_path, monkeypatch):
    """subprocess.TimeoutExpired 是 SubprocessError 子类 → 进 except。"""
    assert issubclass(subprocess.TimeoutExpired, subprocess.SubprocessError)

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=10)

    monkeypatch.setattr(report_module.subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_two_subprocess_calls_in_order(tmp_path, monkeypatch):
    """两次 subprocess.run 调用，按顺序：先 rev-parse，后 status --porcelain。"""
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd == ["git", "rev-parse", "HEAD"]:
            return _make_completed(0, stdout="abc\n")
        if cmd == ["git", "status", "--porcelain"]:
            return _make_completed(0, stdout="")
        return _make_completed(1)

    monkeypatch.setattr(report_module.subprocess, "run", fake_run)
    get_git_provenance(tmp_path)
    assert len(calls) == 2
    assert calls[0] == ["git", "rev-parse", "HEAD"]
    assert calls[1] == ["git", "status", "--porcelain"]


def test_get_git_provenance_returns_dict_with_2_keys(tmp_path):
    out = get_git_provenance(tmp_path)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_default_dirty_is_true(tmp_path, monkeypatch):
    """默认（subprocess 失败）dirty=True。"""
    def fake_run(cmd, **kwargs):
        raise OSError("x")

    monkeypatch.setattr(report_module.subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


def test_get_git_provenance_default_commit_is_none(tmp_path, monkeypatch):
    """默认（subprocess 失败）commit=None。"""
    def fake_run(cmd, **kwargs):
        raise OSError("x")

    monkeypatch.setattr(report_module.subprocess, "run", fake_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


# ============================================================================
# get_dependency_versions 深度模拟
# ============================================================================


def test_get_dependency_versions_keys_exact_order(monkeypatch):
    """返回 dict 的 keys 顺序精确：['pdfplumber', 'python-docx', 'pypdfium2']。"""
    out = get_dependency_versions()
    assert list(out.keys()) == ["pdfplumber", "python-docx", "pypdfium2"]


def test_get_dependency_versions_all_found(monkeypatch):
    """所有 3 包都找到 → values 都非 None。"""
    import importlib.metadata

    real_version = importlib.metadata.version

    def fake_version(pkg):
        if pkg in ("pdfplumber", "python-docx", "pypdfium2"):
            return f"1.0.0-{pkg}"
        return real_version(pkg)

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    out = get_dependency_versions()
    assert out["pdfplumber"] == "1.0.0-pdfplumber"
    assert out["python-docx"] == "1.0.0-python-docx"
    assert out["pypdfium2"] == "1.0.0-pypdfium2"


def test_get_dependency_versions_package_not_found(monkeypatch):
    """包不存在 → 该 key value=None。"""
    import importlib.metadata

    def fake_version(pkg):
        raise importlib.metadata.PackageNotFoundError(pkg)

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    out = get_dependency_versions()
    assert out["pdfplumber"] is None
    assert out["python-docx"] is None
    assert out["pypdfium2"] is None


def test_get_dependency_versions_partial_package_not_found(monkeypatch):
    """部分包不存在 → 不存在 None，存在有版本。"""
    import importlib.metadata

    real_version = importlib.metadata.version

    def fake_version(pkg):
        if pkg == "python-docx":
            raise importlib.metadata.PackageNotFoundError(pkg)
        return real_version(pkg)

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    out = get_dependency_versions()
    # pdfplumber 和 pypdfium2 通过 real_version 取到（环境已安装则非 None）
    assert out["python-docx"] is None


def test_get_dependency_versions_general_exception(monkeypatch):
    """包抛 Exception（非 PackageNotFoundError） → 该 key value=None。"""
    import importlib.metadata

    def fake_version(pkg):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    out = get_dependency_versions()
    assert out["pdfplumber"] is None
    assert out["python-docx"] is None
    assert out["pypdfium2"] is None


def test_get_dependency_versions_partial_general_exception(monkeypatch):
    """部分包抛 Exception → 抛错的 None，正常的有版本。"""
    import importlib.metadata

    real_version = importlib.metadata.version

    def fake_version(pkg):
        if pkg == "pypdfium2":
            raise RuntimeError("unexpected")
        return real_version(pkg)

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    out = get_dependency_versions()
    assert out["pypdfium2"] is None


# ============================================================================
# aggregate_summary 跨多文档混合行为
# ============================================================================


def test_aggregate_summary_count_sum_across_docs():
    """多文档都含 element_count_total → sum 累加 + participating_docs=count。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": 20}}},
        {"metrics": {"element_count_total": {"value": 30}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 60
    assert out["counts"]["element_count_total"]["participating_docs"] == 3


def test_aggregate_summary_count_partial_participation():
    """多文档部分含 element_count_total，部分缺 → sum 只算 participating。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {}},  # 缺该 metric
        {"metrics": {"element_count_total": {"value": 30}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 40
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_count_value_none_not_participating():
    """metric value=None → 不参与。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": 30}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 40
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_count_value_zero_participates():
    """metric value=0 → 参与（不算 None）。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": 0}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 10
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_count_no_values_sum_none():
    """全无 value → sum=None, participating_docs=0。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_pipeline_success_mixed():
    """pipeline_success 部分 True 部分 False → rate=count_true/total。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 3
    assert sr["rate"] == pytest.approx(2 / 3)


def test_aggregate_summary_pipeline_success_all_true_rate_one():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["rate"] == 1.0


def test_aggregate_summary_pipeline_success_all_false_rate_zero():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["rate"] == 0.0


def test_aggregate_summary_pipeline_success_value_none_not_counted():
    """value=None → 不算 success，但 total 仍 += 1。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2
    assert sr["rate"] == 0.5


def test_aggregate_summary_pipeline_success_missing_metric_total_still_increments():
    """缺 pipeline_success 的 doc 仍计入 total（len(per_doc)）。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {}},  # 缺该 metric
    ]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2  # total 用 len(per_doc) 不是 metric 计数
    assert sr["rate"] == 0.5


def test_aggregate_summary_pipeline_success_empty_total_zero():
    """空 per_doc → rate=None, total=0。"""
    out = aggregate_summary([])
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 0
    assert sr["rate"] is None


def test_aggregate_summary_ratio_macro_average():
    """ratio metric macro_average 正确（sum/len）。"""
    per_doc = [
        {"metrics": {"text_preservation_equal": {"value": 1.0}}},
        {"metrics": {"text_preservation_equal": {"value": 0.5}}},
        {"metrics": {"text_preservation_equal": {"value": 0.0}}},
    ]
    out = aggregate_summary(per_doc)
    ra = out["ratio_macro_averages"]["text_preservation_equal"]
    assert ra["macro_average"] == pytest.approx(0.5)
    assert ra["participating_docs"] == 3
    assert ra["not_evaluated"] == 0


def test_aggregate_summary_ratio_partial_participation():
    per_doc = [
        {"metrics": {"text_preservation_equal": {"value": 1.0}}},
        {"metrics": {"text_preservation_equal": {"value": None}}},
        {"metrics": {}},
    ]
    out = aggregate_summary(per_doc)
    ra = out["ratio_macro_averages"]["text_preservation_equal"]
    assert ra["macro_average"] == 1.0
    assert ra["participating_docs"] == 1
    assert ra["not_evaluated"] == 2


def test_aggregate_summary_ratio_zero_value_participates():
    """ratio value=0 → 参与 macro_average。"""
    per_doc = [
        {"metrics": {"text_preservation_equal": {"value": 1.0}}},
        {"metrics": {"text_preservation_equal": {"value": 0.0}}},
    ]
    out = aggregate_summary(per_doc)
    ra = out["ratio_macro_averages"]["text_preservation_equal"]
    assert ra["macro_average"] == 0.5
    assert ra["participating_docs"] == 2


def test_aggregate_summary_ratio_all_none_macro_none():
    """ratio metric 全 None → macro_average=None, participating_docs=0。"""
    per_doc = [
        {"metrics": {"text_preservation_equal": {"value": None}}},
        {"metrics": {}},
    ]
    out = aggregate_summary(per_doc)
    ra = out["ratio_macro_averages"]["text_preservation_equal"]
    assert ra["macro_average"] is None
    assert ra["participating_docs"] == 0
    assert ra["not_evaluated"] == 2


def test_aggregate_summary_silent_drop_partial_participation():
    """silent_drop_count 部分含值，部分 None → 只 sum 非 None 的。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_all_none_returns_none():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_all_zero_returns_zero():
    """全 0 → silent_drop_total=0。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 0}}},
        {"metrics": {"silent_drop_count": {"value": 0}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 0


def test_aggregate_summary_all_metrics_in_ratio_metrics_covered():
    """所有 _RATIO_METRICS 中的 metric 都在 ratio_macro_averages 输出中。"""
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    assert set(out["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


def test_aggregate_summary_count_metrics_in_counts():
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    assert set(out["counts"].keys()) == set(_COUNT_METRICS)


def test_aggregate_summary_success_bool_metrics_in_success_rates():
    per_doc = [{"metrics": {}}]
    out = aggregate_summary(per_doc)
    assert set(out["success_rates"].keys()) == set(_SUCCESS_BOOL_METRICS)


def test_aggregate_summary_no_extra_top_level_keys():
    """summary 只含 4 keys，没有 extras。"""
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_does_not_mutate_input():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 10}}},
    ]
    snapshot = json.loads(json.dumps(per_doc))
    aggregate_summary(per_doc)
    assert per_doc == snapshot


# ============================================================================
# build_provenance 输出深度
# ============================================================================


def test_build_provenance_run_timestamp_iso_is_parseable(tmp_path):
    """run_timestamp_iso 可解析为 datetime。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    dt = datetime.fromisoformat(out["run_timestamp_iso"])
    assert dt is not None


def test_build_provenance_run_timestamp_iso_has_timezone(tmp_path):
    """astimezone() 应包含 tzinfo。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    dt = datetime.fromisoformat(out["run_timestamp_iso"])
    assert dt.tzinfo is not None


def test_build_provenance_two_calls_different_timestamps(tmp_path):
    """两次调用 run_timestamp_iso 不同（时间前进）。"""
    out1 = build_provenance(tmp_path, "fallback", 800, None)
    out2 = build_provenance(tmp_path, "fallback", 800, None)
    assert out1["run_timestamp_iso"] != out2["run_timestamp_iso"]


def test_build_provenance_dependencies_keys_exact(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert list(out["dependencies"].keys()) == ["pdfplumber", "python-docx", "pypdfium2"]


def test_build_provenance_max_chars_int_truncates_float(tmp_path):
    """int(max_chars) 对 float 截断（int(800.9) = 800）。"""
    out = build_provenance(tmp_path, "fallback", 800.99, None)
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_int_from_zero(tmp_path):
    out = build_provenance(tmp_path, "fallback", 0, None)
    assert out["max_chars"] == 0


def test_build_provenance_max_chars_int_from_negative(tmp_path):
    """int(-5) = -5（不会拒绝负数）。"""
    out = build_provenance(tmp_path, "fallback", -5, None)
    assert out["max_chars"] == -5


def test_build_provenance_max_chars_int_from_true(tmp_path):
    """int(True) = 1。"""
    out = build_provenance(tmp_path, "fallback", True, None)
    assert out["max_chars"] == 1


def test_build_provenance_parser_version_none_passes_through(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_parser_version_string_passes_through(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.2.3")
    assert out["parser_version"] == "1.2.3"


def test_build_provenance_evaluator_version_constant(tmp_path):
    """evaluator_version 来自 evaluation.EVALUATOR_VERSION（不能改）。"""
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_constant(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_parser_name_passes_through(tmp_path):
    out = build_provenance(tmp_path, "kreuzberg", 800, None)
    assert out["parser_name"] == "kreuzberg"


# ============================================================================
# build_devset_section duck typing 深度
# ============================================================================


class _FakeManifest:
    """模拟 Manifest dataclass 的最小接口。"""

    def __init__(
        self,
        devset_status="incomplete",
        file_count=0,
        content_group_count=0,
        pdf_count=0,
        docx_count=0,
        categories_covered=None,
    ):
        self.devset_status = devset_status
        self.file_count = file_count
        self.content_group_count = content_group_count
        self.pdf_count = pdf_count
        self.docx_count = docx_count
        self.categories_covered = categories_covered if categories_covered is not None else []


def test_build_devset_section_with_namespace_object():
    """duck typing：任何含 6 属性的对象都行。"""
    out = build_devset_section(_FakeManifest())
    assert set(out.keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_build_devset_section_missing_devset_status_raises():
    class Bad:
        pass

    with pytest.raises(AttributeError) as exc:
        build_devset_section(Bad())
    assert "devset_status" in str(exc.value)


def test_build_devset_section_missing_file_count_raises():
    class Bad:
        devset_status = "incomplete"

    with pytest.raises(AttributeError) as exc:
        build_devset_section(Bad())
    assert "file_count" in str(exc.value)


def test_build_devset_section_missing_content_group_count_raises():
    class Bad:
        devset_status = "incomplete"
        file_count = 1

    with pytest.raises(AttributeError) as exc:
        build_devset_section(Bad())
    assert "content_group_count" in str(exc.value)


def test_build_devset_section_missing_pdf_count_raises():
    class Bad:
        devset_status = "incomplete"
        file_count = 1
        content_group_count = 1

    with pytest.raises(AttributeError) as exc:
        build_devset_section(Bad())
    assert "pdf_count" in str(exc.value)


def test_build_devset_section_missing_docx_count_raises():
    class Bad:
        devset_status = "incomplete"
        file_count = 1
        content_group_count = 1
        pdf_count = 1

    with pytest.raises(AttributeError) as exc:
        build_devset_section(Bad())
    assert "docx_count" in str(exc.value)


def test_build_devset_section_missing_categories_covered_raises():
    class Bad:
        devset_status = "incomplete"
        file_count = 1
        content_group_count = 1
        pdf_count = 1
        docx_count = 1

    with pytest.raises(AttributeError) as exc:
        build_devset_section(Bad())
    assert "categories_covered" in str(exc.value)


def test_build_devset_section_categories_covered_passes_through():
    m = _FakeManifest(categories_covered=["a", "b", "c"])
    out = build_devset_section(m)
    assert out["categories_covered"] == ["a", "b", "c"]


def test_build_devset_section_passes_through_all_values():
    m = _FakeManifest(
        devset_status="complete",
        file_count=10,
        content_group_count=5,
        pdf_count=3,
        docx_count=7,
        categories_covered=["x"],
    )
    out = build_devset_section(m)
    assert out["status"] == "complete"
    assert out["file_count"] == 10
    assert out["content_group_count"] == 5
    assert out["pdf_count"] == 3
    assert out["docx_count"] == 7
    assert out["categories_covered"] == ["x"]


def test_build_devset_section_no_extra_keys():
    """输出只含 6 keys，没有 extras。"""
    out = build_devset_section(_FakeManifest())
    assert len(out) == 6


# ============================================================================
# 模块 source 深度补强
# ============================================================================


def test_module_source_contains_relative_path_imports():
    """report.py 通过 'from evaluation import ...' 取 version。"""
    src = inspect.getsource(report_module)
    assert "from evaluation import" in src


def test_module_source_does_not_contain_star_import():
    src = inspect.getsource(report_module)
    assert "import *" not in src


def test_module_source_does_not_contain_exec_or_eval():
    src = inspect.getsource(report_module)
    assert "exec(" not in src
    assert "eval(" not in src


def test_module_source_does_not_contain_open():
    """不直接 open 文件（subprocess 和 importlib 才读外部）。"""
    src = inspect.getsource(report_module)
    assert ".open(" not in src
    assert "open(" not in src


def test_module_source_does_not_contain_global_keyword():
    src = inspect.getsource(report_module)
    assert "global " not in src


def test_module_source_does_not_contain_nonlocal_keyword():
    src = inspect.getsource(report_module)
    assert "nonlocal " not in src


def test_module_source_does_not_contain_walrus():
    src = inspect.getsource(report_module)
    assert ":=" not in src


def test_module_source_does_not_contain_assert():
    src = inspect.getsource(report_module)
    assert "\n    assert " not in src


def test_module_source_does_not_contain_relative_import_dots():
    """from . 或 from .. 没用。"""
    src = inspect.getsource(report_module)
    assert "from ." not in src


def test_module_source_contains_no_class_definitions():
    """report.py 不定义 class。"""
    src = inspect.getsource(report_module)
    assert "\nclass " not in src
    assert src.startswith('"""')  # 模块以 docstring 开始


def test_module_source_contains_no_dataclasses_decorator():
    src = inspect.getsource(report_module)
    assert "@dataclass" not in src


# ============================================================================
# 常量 _RATIO_METRICS 排他性深度
# ============================================================================


def test_ratio_metrics_does_not_overlap_count_metrics():
    """_RATIO_METRICS 与 _COUNT_METRICS 没交集。"""
    assert set(_RATIO_METRICS).isdisjoint(set(_COUNT_METRICS))


def test_ratio_metrics_does_not_overlap_success_bool_metrics():
    assert set(_RATIO_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))


def test_count_metrics_does_not_overlap_success_bool_metrics():
    assert set(_COUNT_METRICS).isdisjoint(set(_SUCCESS_BOOL_METRICS))


def test_ratio_metrics_no_duplicates():
    assert len(set(_RATIO_METRICS)) == len(_RATIO_METRICS)


def test_count_metrics_no_duplicates():
    assert len(set(_COUNT_METRICS)) == len(_COUNT_METRICS)


def test_success_bool_metrics_no_duplicates():
    assert len(set(_SUCCESS_BOOL_METRICS)) == len(_SUCCESS_BOOL_METRICS)


# ============================================================================
# build_provenance + aggregate_summary 联动
# ============================================================================


def test_build_provenance_then_aggregate_summary_integration(tmp_path):
    """build_provenance + aggregate_summary 联动可以工作（无副作用）。"""
    prov = build_provenance(tmp_path, "fallback", 800, None)
    summary = aggregate_summary([])
    # 验证两者的 key 不冲突
    assert set(prov.keys()).isdisjoint(set(summary.keys()))


def test_build_provenance_no_mutation_of_summary(tmp_path):
    """build_provenance 不会污染 aggregate_summary 输出。"""
    prov = build_provenance(tmp_path, "fallback", 800, None)
    summary = aggregate_summary([])
    # summary 不该有 provenance 的 key
    for key in prov:
        assert key not in summary


# ============================================================================
# 异常路径
# ============================================================================


def test_aggregate_summary_with_per_doc_none_metric_value():
    """per_doc 中 metric value=None 不应导致崩溃。"""
    per_doc = [{"metrics": {"pipeline_success": {"value": None}}}]
    out = aggregate_summary(per_doc)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 1


def test_aggregate_summary_with_per_doc_no_metrics_key():
    """per_doc 完全缺 metrics 键 → 应抛 KeyError。"""
    per_doc = [{}]
    with pytest.raises(KeyError):
        aggregate_summary(per_doc)


def test_aggregate_summary_with_per_doc_metrics_none():
    """per_doc 中 metrics=None → None.get 抛 AttributeError。"""
    per_doc = [{"metrics": None}]
    with pytest.raises(AttributeError):
        aggregate_summary(per_doc)


def test_aggregate_summary_does_not_cache_across_calls():
    """aggregate_summary 不缓存。"""
    per_doc1 = [{"metrics": {"element_count_total": {"value": 10}}}]
    per_doc2 = [{"metrics": {"element_count_total": {"value": 20}}}]
    out1 = aggregate_summary(per_doc1)
    out2 = aggregate_summary(per_doc2)
    assert out1["counts"]["element_count_total"]["sum"] == 10
    assert out2["counts"]["element_count_total"]["sum"] == 20


# ============================================================================
# __all__ 深度
# ============================================================================


def test_module_all_entries_each_a_valid_identifier():
    for name in report_module.__all__:
        assert isinstance(name, str)
        assert name.isidentifier()


def test_module_all_entries_each_exists_in_namespace():
    for name in report_module.__all__:
        assert hasattr(report_module, name)


def test_module_all_entries_each_callable():
    """__all__ 中每个名字都是 function。"""
    import types

    for name in report_module.__all__:
        obj = getattr(report_module, name)
        assert isinstance(obj, types.FunctionType)


# ============================================================================
# datetime 属性
# ============================================================================


def test_module_datetime_attr_is_datetime_class():
    assert report_module.datetime is datetime


def test_module_pathlib_path_attr_is_path_class():
    """report.py 通过 from pathlib import Path 引入 Path。"""
    assert report_module.Path is Path


def test_module_subprocess_attr_is_subprocess_module():
    """report.py 通过 import subprocess 引入 subprocess 模块。"""
    assert report_module.subprocess is subprocess


# ============================================================================
# 模块 __all__ 与 namespace 完整性
# ============================================================================


def test_module_all_in_namespace_diff():
    """__all__ 中所有名字都在 namespace。"""
    for name in report_module.__all__:
        assert name in report_module.__dict__


def test_module_namespace_constants_underscore():
    """_RATIO_METRICS 等带下划线的常量不在 __all__ 但在 namespace。"""
    for name in ["_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"]:
        assert name in report_module.__dict__
        assert name not in report_module.__all__


def test_module_namespace_versions_in_namespace_not_all():
    """EVALUATOR_VERSION 和 REPORT_VERSION 在 namespace 但不在 __all__。"""
    assert "EVALUATOR_VERSION" in report_module.__dict__
    assert "REPORT_VERSION" in report_module.__dict__
    assert "EVALUATOR_VERSION" not in report_module.__all__
    assert "REPORT_VERSION" not in report_module.__all__
