"""Runner PR 验收测试：expectation 契约键可执行（evaluator v1.2）。

覆盖：
1. required_markers / forbidden_markers / must_not_error_codes /
   max_silent_drop_count 四键逐键 pass/fail 语义（含 pipeline 失败分支）
2. marker 匹配基于 normalize_text 投影：元素内空白差异不影响命中
3. manifest 严格校验：未知键 / 类型错误 / max_silent_drop_count 缺
   element_count_by_type / markdown source_type 接受
4. summary.expectation_checks 聚合：evaluated/passed/failed 分开计数
5. 报告 schema：report_version 1.1 与 1.2 均有效；expectation_checks 通过校验
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.manifest import ManifestError, load_manifest
from evaluation.metrics import compute_automatic_metrics
from evaluation.report import aggregate_summary
from evaluation.schema import EvalSchemaError, validate


def _el(i: int, type_: str, content: str) -> dict:
    return {
        "element_id": f"e{i}",
        "type": type_,
        "source_locator": {"line": i + 1},
        "parent_id": None,
        "content": content,
        "resource_path": None,
        "confidence": 1.0,
        "metadata": {},
    }


def _doc(elements: list[dict]) -> dict:
    return {
        "schema_version": "0.2.0",
        "document_id": "doc-test",
        "source_path": "samples/private/x.md",
        "source_type": "markdown",
        "source_hash": "a" * 64,
        "parser_name": "p",
        "parser_version": "1",
        "elements": elements,
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


# ---------- required_markers ----------

def test_required_markers_all_present():
    doc = _doc([_el(0, "heading", "# 标题 REG_ONE"), _el(1, "paragraph", "正文 REG_TWO 内容")])
    m = compute_automatic_metrics(
        doc, None, "markdown", {"required_markers": ["REG_ONE", "REG_TWO"]}
    )
    c = m["required_markers_check"]
    assert c["value"]["passed"] is True
    assert c["value"]["missing"] == []
    assert c["value"]["expected"] == ["REG_ONE", "REG_TWO"]


def test_required_markers_missing():
    doc = _doc([_el(0, "paragraph", "只有 REG_ONE")])
    m = compute_automatic_metrics(
        doc, None, "markdown", {"required_markers": ["REG_ONE", "REG_TWO"]}
    )
    c = m["required_markers_check"]
    assert c["value"]["passed"] is False
    assert c["value"]["missing"] == ["REG_TWO"]


def test_required_markers_whitespace_insensitive():
    # 元素内多余空白在投影中被压成单空格 → 带空格的 marker 仍命中
    doc = _doc([_el(0, "paragraph", "任务\t清单\n项目\t清单")])
    m = compute_automatic_metrics(
        doc, None, "markdown", {"required_markers": ["任务 清单", "项目 清单"]}
    )
    assert m["required_markers_check"]["value"]["passed"] is True


def test_required_markers_absent_key_is_null():
    doc = _doc([_el(0, "paragraph", "x")])
    for exp in (None, {}, {"required_markers": []}, {"element_count_by_type": {"paragraph": 1}}):
        m = compute_automatic_metrics(doc, None, "markdown", exp)
        c = m["required_markers_check"]
        assert c["value"] is None
        assert c["reason"] == "no_expectation_key:required_markers"


def test_required_markers_pipeline_failed():
    m = compute_automatic_metrics(
        None,
        {"code": "unexpected_parser_error", "message": "x"},
        "markdown",
        {"required_markers": ["REG_ONE"]},
    )
    c = m["required_markers_check"]
    assert c["value"] is None
    assert c["reason"] == "pipeline_failed"


# ---------- forbidden_markers ----------

def test_forbidden_markers_found():
    doc = _doc([_el(0, "paragraph", "前缀 REG_BAD 后缀"), _el(1, "paragraph", "干净")])
    m = compute_automatic_metrics(
        doc, None, "markdown", {"forbidden_markers": ["REG_BAD", "REG_WORSE"]}
    )
    c = m["forbidden_markers_check"]
    assert c["value"]["passed"] is False
    assert c["value"]["found"] == ["REG_BAD"]


def test_forbidden_markers_absent_passes():
    doc = _doc([_el(0, "paragraph", "正常内容")])
    m = compute_automatic_metrics(
        doc, None, "markdown", {"forbidden_markers": ["REG_BAD"]}
    )
    c = m["forbidden_markers_check"]
    assert c["value"]["passed"] is True
    assert c["value"]["found"] == []


def test_forbidden_markers_substring_semantics():
    # 精确子串语义：短 forbidden marker 命中包含它的更长文本
    doc = _doc([_el(0, "paragraph", "javascript 泄漏")])
    m = compute_automatic_metrics(
        doc, None, "markdown", {"forbidden_markers": ["script"]}
    )
    assert m["forbidden_markers_check"]["value"]["passed"] is False


# ---------- must_not_error_codes ----------

def test_must_not_error_codes_occurred():
    m = compute_automatic_metrics(
        None,
        {"code": "unexpected_parser_error", "message": "x"},
        "markdown",
        {"must_not_error_codes": ["unexpected_parser_error", "other_code"]},
    )
    c = m["must_not_error_codes_check"]
    assert c["value"]["passed"] is False
    assert c["value"]["occurred"] == ["unexpected_parser_error"]


def test_must_not_error_codes_success_is_vacuous_pass():
    doc = _doc([_el(0, "paragraph", "x")])
    m = compute_automatic_metrics(
        doc, None, "markdown", {"must_not_error_codes": ["unexpected_parser_error"]}
    )
    c = m["must_not_error_codes_check"]
    assert c["value"]["passed"] is True
    assert c["value"]["occurred"] == []


def test_must_not_error_codes_other_code_passes():
    m = compute_automatic_metrics(
        None,
        {"code": "unsupported_format", "message": "x"},
        "markdown",
        {"must_not_error_codes": ["unexpected_parser_error"]},
    )
    assert m["must_not_error_codes_check"]["value"]["passed"] is True


# ---------- max_silent_drop_count ----------

def test_max_silent_drop_within_max():
    doc = _doc([_el(0, "heading", "h"), _el(1, "paragraph", "p")])
    m = compute_automatic_metrics(
        doc,
        None,
        "markdown",
        {"element_count_by_type": {"heading": 2, "paragraph": 1},
         "max_silent_drop_count": 1},
    )
    c = m["max_silent_drop_check"]
    assert m["silent_drop_count"]["value"] == 1
    assert c["value"] == {"max": 1, "actual": 1, "passed": True}


def test_max_silent_drop_exceeded():
    doc = _doc([_el(0, "heading", "h")])
    m = compute_automatic_metrics(
        doc,
        None,
        "markdown",
        {"element_count_by_type": {"heading": 2, "paragraph": 1},
         "max_silent_drop_count": 0},
    )
    c = m["max_silent_drop_check"]
    assert c["value"]["passed"] is False
    assert c["value"]["actual"] == 2


def test_max_silent_drop_absent_key_is_null():
    doc = _doc([_el(0, "paragraph", "p")])
    m = compute_automatic_metrics(
        doc, None, "markdown", {"element_count_by_type": {"paragraph": 1}}
    )
    c = m["max_silent_drop_check"]
    assert c["value"] is None
    assert c["reason"] == "no_expectation_key:max_silent_drop_count"


# ---------- manifest 严格校验 ----------

def _write_manifest(
    tmp_path: Path,
    expectations: dict,
    source_type: str = "markdown",
    version: str = "1.1",
) -> Path:
    (tmp_path / "doc.md").write_text("# x\n", encoding="utf-8")
    data = {
        "manifest_version": version,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "D1",
                "path": "doc.md",
                "source_type": source_type,
                "expectations": expectations,
            }
        ],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def test_manifest_accepts_new_source_types_and_keys(tmp_path: Path):
    p = _write_manifest(
        tmp_path,
        {
            "element_count_by_type": {"heading": 1},
            "required_markers": ["x"],
            "forbidden_markers": ["y"],
            "must_not_error_codes": ["unexpected_parser_error"],
            "max_silent_drop_count": 0,
        },
        source_type="html",
    )
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].source_type == "html"


def test_manifest_rejects_unknown_expectation_key(tmp_path: Path):
    p = _write_manifest(tmp_path, {"forbidden_silent_drop": ["image"]})
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_manifest_rejects_bad_types(tmp_path: Path):
    p = _write_manifest(tmp_path, {"max_silent_drop_count": -1})
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)
    p = _write_manifest(tmp_path, {"required_markers": [123]})
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_manifest_max_silent_drop_needs_counts(tmp_path: Path):
    p = _write_manifest(tmp_path, {"max_silent_drop_count": 0})
    with pytest.raises(ManifestError, match="element_count_by_type"):
        load_manifest(p, project_root=tmp_path)


def test_drafted_manifests_load(tmp_path: Path):
    """三份起草 manifest 在扩展后的 loader 下应能通过（文件本身不跑 pipeline）。"""
    root = Path(__file__).resolve().parent.parent
    for rel in (
        "samples/private/devset-md/manifest.json",
        "samples/private/devset-html/manifest.json",
        "samples/private/devset-regressions/manifest.json",
    ):
        p = root / rel
        if not p.is_file():
            continue  # samples/private 是 gitignored 的本机资产
        m = load_manifest(p, project_root=root)
        assert m.file_count >= 1


# ---------- summary 聚合 ----------

def _pd(check_name: str, passed: bool | None) -> dict:
    metrics: dict = {"pipeline_success": {"value": passed is not None}}
    if passed is not None:
        metrics[check_name] = {"value": {"passed": passed}, "reason": None}
    return {"metrics": metrics}


def test_summary_expectation_checks_aggregation():
    per_doc = [
        _pd("required_markers_check", True),
        _pd("required_markers_check", False),
        _pd("required_markers_check", None),  # 未声明键
    ]
    s = aggregate_summary(per_doc)
    c = s["expectation_checks"]["required_markers_check"]
    assert c == {"evaluated_docs": 2, "passed_docs": 1, "failed_docs": 1}
    # 其余三键无人声明 → 全 0
    for name in (
        "forbidden_markers_check",
        "must_not_error_codes_check",
        "max_silent_drop_check",
    ):
        assert s["expectation_checks"][name]["evaluated_docs"] == 0


# ---------- 报告 schema 兼容 ----------

def _report(report_version: str) -> dict:
    is_old = report_version == "1.1"
    summary: dict = {
        "counts": {},
        "success_rates": {},
        "ratio_macro_averages": {},
        "silent_drop_total": None,
    }
    if not is_old:
        summary["expectation_checks"] = {
            "required_markers_check": {
                "evaluated_docs": 1,
                "passed_docs": 1,
                "failed_docs": 0,
            }
        }
    return {
        "report_version": report_version,
        "provenance": {
            "git_commit": None,
            "git_dirty": True,
            "evaluator_version": "1.2",
            "report_version": report_version,
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {},
            "max_chars": 800,
            "run_timestamp_iso": "2026-08-27T00:00:00+08:00",
        },
        "devset": {
            "status": "incomplete",
            "file_count": 1,
            "content_group_count": 1,
            "pdf_count": 0,
            "docx_count": 0 if not is_old else 1,
            "categories_covered": ["x"],
        },
        "summary": summary,
        "per_doc": [
            {
                "doc_id": "D1",
                "source_type": "docx" if is_old else "markdown",
                "metrics": {},
                "wall_time_seconds": {
                    "total": 0.1,
                    "parse": None,
                    "chunk": None,
                    "parse_reason": "not_instrumented",
                    "chunk_reason": "not_instrumented",
                },
            }
        ],
    }


def test_report_schema_accepts_v11_and_v12():
    validate(_report("1.1"), "evaluation-report.schema.json")
    validate(_report("1.2"), "evaluation-report.schema.json")


def test_report_v11_rejects_new_sections():
    # 精确快照：1.1 报告不得包含 expectation_checks
    r = _report("1.1")
    r["summary"]["expectation_checks"] = {
        "required_markers_check": {
            "evaluated_docs": 0,
            "passed_docs": 0,
            "failed_docs": 0,
        }
    }
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")
    # 1.1 报告的 per_doc 也不得含 check 键
    r2 = _report("1.1")
    r2["per_doc"][0]["metrics"]["required_markers_check"] = {
        "value": None,
        "reason": "no_expectation_key:required_markers",
    }
    with pytest.raises(EvalSchemaError):
        validate(r2, "evaluation-report.schema.json")


def test_report_schema_rejects_unknown_version():
    with pytest.raises(EvalSchemaError):
        validate(_report("1.3"), "evaluation-report.schema.json")
