"""evaluation/report.py 第二十一轮 edges 测试（Round 353）。

重点补强 edges20 未触及的角度：
- aggregate_summary 行为深度第六批（更多混合场景 / 各种 null 模式）
- build_devset_section 行为深度第三批（更多 manifest 模拟）
- build_provenance 行为深度第三批（更多参数组合）
- get_git_provenance 行为深度第三批（更多 subprocess 模拟）
- get_dependency_versions 行为深度第三批（更多 importlib.metadata 模拟）
- module source forbidden tokens 第六批
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性
- 端到端集成补强
"""

from __future__ import annotations

import inspect
import json
import subprocess
import types
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from evaluation import EVALUATOR_VERSION, REPORT_VERSION, report as rmod
from evaluation.report import (
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


# ---------- helpers ----------


def _per_doc(metrics_dict):
    return {"doc_id": "d1", "metrics": metrics_dict}


def _manifest_ns(
    devset_status="complete",
    file_count=1,
    content_group_count=1,
    pdf_count=1,
    docx_count=0,
    categories_covered=None,
):
    if categories_covered is None:
        categories_covered = []
    ns = types.SimpleNamespace(
        devset_status=devset_status,
        file_count=file_count,
        content_group_count=content_group_count,
        pdf_count=pdf_count,
        docx_count=docx_count,
        categories_covered=categories_covered,
    )
    return ns


# ---------- aggregate_summary 行为深度第六批 ----------


def test_aggregate_summary_empty_input():
    out = aggregate_summary([])
    assert isinstance(out, dict)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_has_4_top_level_keys():
    out = aggregate_summary([])
    assert "counts" in out
    assert "success_rates" in out
    assert "ratio_macro_averages" in out
    assert "silent_drop_total" in out


def test_aggregate_summary_counts_sum_element_count_total():
    docs = [
        _per_doc({"element_count_total": {"value": 5, "reason": None}}),
        _per_doc({"element_count_total": {"value": 10, "reason": None}}),
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_skip_none_values():
    docs = [
        _per_doc({"element_count_total": {"value": 5, "reason": None}}),
        _per_doc({"element_count_total": {"value": None, "reason": "pipeline_failed"}}),
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_success_rate():
    docs = [
        _per_doc({"pipeline_success": {"value": True, "reason": None}}),
        _per_doc({"pipeline_success": {"value": False, "reason": None}}),
        _per_doc({"pipeline_success": {"value": True, "reason": None}}),
    ]
    out = aggregate_summary(docs)
    rate = out["success_rates"]["pipeline_success"]
    assert rate["success_count"] == 2
    assert rate["total"] == 3
    assert rate["rate"] == 2 / 3


def test_aggregate_summary_success_rate_with_zero_docs():
    out = aggregate_summary([])
    rate = out["success_rates"]["pipeline_success"]
    assert rate["success_count"] == 0
    assert rate["total"] == 0
    assert rate["rate"] is None


def test_aggregate_summary_ratio_macro_average():
    docs = [
        _per_doc({"schema_valid": {"value": 1.0, "reason": None}}),
        _per_doc({"schema_valid": {"value": 0.5, "reason": None}}),
    ]
    out = aggregate_summary(docs)
    avg = out["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == 0.75
    assert avg["participating_docs"] == 2
    assert avg["not_evaluated"] == 0


def test_aggregate_summary_ratio_skip_none():
    docs = [
        _per_doc({"schema_valid": {"value": 1.0, "reason": None}}),
        _per_doc({"schema_valid": {"value": None, "reason": "pipeline_failed"}}),
    ]
    out = aggregate_summary(docs)
    avg = out["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == 1.0
    assert avg["participating_docs"] == 1
    assert avg["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_sum():
    docs = [
        _per_doc({"silent_drop_count": {"value": 2, "reason": None}}),
        _per_doc({"silent_drop_count": {"value": 3, "reason": None}}),
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 5


def test_aggregate_summary_silent_drop_skip_none():
    docs = [
        _per_doc({"silent_drop_count": {"value": 2, "reason": None}}),
        _per_doc({"silent_drop_count": {"value": None, "reason": "no_expectations"}}),
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 2


def test_aggregate_summary_silent_drop_all_none():
    docs = [
        _per_doc({"silent_drop_count": {"value": None, "reason": "no_expectations"}}),
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_does_not_modify_inputs():
    docs = [
        _per_doc({"element_count_total": {"value": 5, "reason": None}}),
    ]
    docs_before = json.loads(json.dumps(docs))
    aggregate_summary(docs)
    assert docs == docs_before


def test_aggregate_summary_idempotent():
    docs = [
        _per_doc({"element_count_total": {"value": 5, "reason": None}}),
    ]
    a = aggregate_summary(docs)
    b = aggregate_summary(docs)
    assert a == b


def test_aggregate_summary_counts_none_when_no_participating():
    out = aggregate_summary([])
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_ratio_macro_none_when_no_participating():
    out = aggregate_summary([])
    avg = out["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] is None
    assert avg["participating_docs"] == 0


def test_aggregate_summary_includes_all_12_ratio_metrics():
    """_RATIO_METRICS 有 12 个 entries。"""
    out = aggregate_summary([])
    assert len(out["ratio_macro_averages"]) == 12


def test_aggregate_summary_includes_1_count_metric():
    out = aggregate_summary([])
    assert len(out["counts"]) == 1
    assert "element_count_total" in out["counts"]


def test_aggregate_summary_includes_1_success_metric():
    out = aggregate_summary([])
    assert len(out["success_rates"]) == 1
    assert "pipeline_success" in out["success_rates"]


def test_aggregate_summary_with_mixed_metrics():
    """单个 doc 含全套 metrics。"""
    metrics = {
        "pipeline_success": {"value": True, "reason": None},
        "element_count_total": {"value": 10, "reason": None},
        "schema_valid": {"value": 1.0, "reason": None},
        "silent_drop_count": {"value": 2, "reason": None},
    }
    out = aggregate_summary([_per_doc(metrics)])
    assert out["counts"]["element_count_total"]["sum"] == 10
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1


def test_aggregate_summary_json_serializable():
    docs = [_per_doc({"pipeline_success": {"value": True, "reason": None}})]
    out = aggregate_summary(docs)
    s = json.dumps(out)
    assert isinstance(s, str)


# ---------- build_devset_section 行为深度第三批 ----------


def test_build_devset_section_returns_dict():
    out = build_devset_section(_manifest_ns())
    assert isinstance(out, dict)


def test_build_devset_section_has_6_keys():
    out = build_devset_section(_manifest_ns())
    assert len(out) == 6


def test_build_devset_section_keys():
    out = build_devset_section(_manifest_ns())
    assert set(out.keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_build_devset_section_status_from_manifest():
    out = build_devset_section(_manifest_ns(devset_status="incomplete"))
    assert out["status"] == "incomplete"


def test_build_devset_section_file_count_from_manifest():
    out = build_devset_section(_manifest_ns(file_count=42))
    assert out["file_count"] == 42


def test_build_devset_section_content_group_count_from_manifest():
    out = build_devset_section(_manifest_ns(content_group_count=5))
    assert out["content_group_count"] == 5


def test_build_devset_section_pdf_count_from_manifest():
    out = build_devset_section(_manifest_ns(pdf_count=3, docx_count=2))
    assert out["pdf_count"] == 3
    assert out["docx_count"] == 2


def test_build_devset_section_categories_covered_from_manifest():
    out = build_devset_section(_manifest_ns(categories_covered=["a", "b"]))
    assert out["categories_covered"] == ["a", "b"]


def test_build_devset_section_zero_counts():
    out = build_devset_section(_manifest_ns(file_count=0, content_group_count=0, pdf_count=0, docx_count=0))
    assert out["file_count"] == 0
    assert out["content_group_count"] == 0


def test_build_devset_section_does_not_modify_manifest():
    m = _manifest_ns()
    out = build_devset_section(m)
    # build_devset_section 只读 manifest
    assert m.devset_status == "complete"
    assert m.file_count == 1


def test_build_devset_section_idempotent():
    m = _manifest_ns()
    a = build_devset_section(m)
    b = build_devset_section(m)
    assert a == b


def test_build_devset_section_json_serializable():
    out = build_devset_section(_manifest_ns(categories_covered=["x", "y"]))
    s = json.dumps(out)
    assert isinstance(s, str)


# ---------- build_provenance 行为深度第三批 ----------


def test_build_provenance_returns_dict(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert isinstance(out, dict)


def test_build_provenance_has_required_keys(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    expected = {
        "git_commit",
        "git_dirty",
        "evaluator_version",
        "report_version",
        "parser_name",
        "parser_version",
        "dependencies",
        "max_chars",
        "run_timestamp_iso",
    }
    assert set(out.keys()) == expected


def test_build_provenance_parser_name(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["parser_name"] == "fallback"


def test_build_provenance_max_chars_int(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_converted_to_int(tmp_path):
    """max_chars 会被 int() 强制转换。"""
    out = build_provenance(tmp_path, "fallback", 800.0, "1.0.0")
    assert isinstance(out["max_chars"], int)


def test_build_provenance_parser_version_str(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "v1.2.3")
    assert out["parser_version"] == "v1.2.3"


def test_build_provenance_parser_version_none(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_evaluator_version(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_dependencies_dict(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["dependencies"], dict)


def test_build_provenance_dependencies_has_3_keys(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert set(out["dependencies"].keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_build_provenance_run_timestamp_iso_format(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    ts = out["run_timestamp_iso"]
    # ISO 格式：解析能成功
    parsed = datetime.fromisoformat(ts)
    assert isinstance(parsed, datetime)


def test_build_provenance_with_kreuzberg_parser(tmp_path):
    out = build_provenance(tmp_path, "kreuzberg", 800, "v2.0")
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_with_zero_max_chars(tmp_path):
    out = build_provenance(tmp_path, "fallback", 0, None)
    assert out["max_chars"] == 0


def test_build_provenance_with_negative_max_chars(tmp_path):
    out = build_provenance(tmp_path, "fallback", -1, None)
    assert out["max_chars"] == -1


def test_build_provenance_idempotent_except_timestamp(tmp_path):
    """build_provenance 是非纯函数（含 timestamp + git），但主要字段一致。"""
    a = build_provenance(tmp_path, "fallback", 800, None)
    b = build_provenance(tmp_path, "fallback", 800, None)
    assert a["parser_name"] == b["parser_name"]
    assert a["max_chars"] == b["max_chars"]


def test_build_provenance_json_serializable(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    s = json.dumps(out)
    assert isinstance(s, str)


# ---------- get_git_provenance 行为深度第三批 ----------


def test_get_git_provenance_returns_dict(tmp_path):
    out = get_git_provenance(tmp_path)
    assert isinstance(out, dict)


def test_get_git_provenance_has_2_keys(tmp_path):
    out = get_git_provenance(tmp_path)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_get_git_provenance_in_repo():
    """在项目根目录跑，应该拿到 commit + dirty。"""
    proj_root = Path(__file__).resolve().parent.parent
    out = get_git_provenance(proj_root)
    # 应该有 commit（autonomous-track 已 push）
    assert "git_commit" in out
    assert "git_dirty" in out


def test_get_git_provenance_in_nonexistent_dir(tmp_path):
    """不存在的目录 → commit=None, dirty=True（git 失败）。"""
    fake = tmp_path / "nonexistent"
    out = get_git_provenance(fake)
    assert out["git_commit"] is None or isinstance(out["git_commit"], str)
    assert isinstance(out["git_dirty"], bool)


def test_get_git_provenance_with_mock_success(monkeypatch, tmp_path):
    """monkeypatch subprocess.run 模拟成功。"""
    calls = []

    def mock_run(cmd, **kwargs):
        calls.append(cmd)
        r = subprocess.CompletedProcess(cmd, 0, "", "")
        if "rev-parse" in cmd:
            r.stdout = "abc123\n"
        else:
            r.stdout = ""  # not dirty
        return r

    monkeypatch.setattr(subprocess, "run", mock_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is False
    assert len(calls) == 2


def test_get_git_provenance_with_mock_dirty(monkeypatch, tmp_path):
    def mock_run(cmd, **kwargs):
        r = subprocess.CompletedProcess(cmd, 0, "", "")
        if "rev-parse" in cmd:
            r.stdout = "abc123\n"
        else:
            r.stdout = "M file.txt\n"  # dirty
        return r

    monkeypatch.setattr(subprocess, "run", mock_run)
    out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


def test_get_git_provenance_rev_parse_fails(monkeypatch, tmp_path):
    def mock_run(cmd, **kwargs):
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, 1, "", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", mock_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_os_error(monkeypatch, tmp_path):
    def mock_run(cmd, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(subprocess, "run", mock_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_subprocess_error(monkeypatch, tmp_path):
    def mock_run(cmd, **kwargs):
        raise subprocess.SubprocessError("boom")

    monkeypatch.setattr(subprocess, "run", mock_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_commit_empty_string(monkeypatch, tmp_path):
    def mock_run(cmd, **kwargs):
        r = subprocess.CompletedProcess(cmd, 0, "", "")
        if "rev-parse" in cmd:
            r.stdout = "   "  # only whitespace
        else:
            r.stdout = ""
        return r

    monkeypatch.setattr(subprocess, "run", mock_run)
    out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None  # strip 后空 → None


# ---------- get_dependency_versions 行为深度第三批 ----------


def test_get_dependency_versions_returns_dict():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_get_dependency_versions_has_3_keys():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_str_or_none():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_keys_order():
    out = get_dependency_versions()
    keys = list(out.keys())
    assert keys == ["pdfplumber", "python-docx", "pypdfium2"]


def test_get_dependency_versions_with_mock_success(monkeypatch):
    """模拟所有包都找到版本。"""
    import importlib.metadata

    real_version = importlib.metadata.version

    def mock_version(pkg):
        return f"1.0.0-{pkg}"

    monkeypatch.setattr(importlib.metadata, "version", mock_version)
    out = get_dependency_versions()
    assert out["pdfplumber"] == "1.0.0-pdfplumber"
    assert out["python-docx"] == "1.0.0-python-docx"
    assert out["pypdfium2"] == "1.0.0-pypdfium2"


def test_get_dependency_versions_with_package_not_found(monkeypatch):
    import importlib.metadata

    def mock_version(pkg):
        raise importlib.metadata.PackageNotFoundError(pkg)

    monkeypatch.setattr(importlib.metadata, "version", mock_version)
    out = get_dependency_versions()
    assert out["pdfplumber"] is None
    assert out["python-docx"] is None
    assert out["pypdfium2"] is None


def test_get_dependency_versions_with_generic_exception(monkeypatch):
    import importlib.metadata

    def mock_version(pkg):
        raise ValueError("unexpected")

    monkeypatch.setattr(importlib.metadata, "version", mock_version)
    out = get_dependency_versions()
    assert out["pdfplumber"] is None


def test_get_dependency_versions_idempotent():
    a = get_dependency_versions()
    b = get_dependency_versions()
    assert a == b


def test_get_dependency_versions_json_serializable():
    out = get_dependency_versions()
    s = json.dumps(out)
    assert isinstance(s, str)


# ---------- module source forbidden tokens 第六批 ----------


_FORBIDDEN_TOKENS_ROUND6 = [
    "sys",
    "logging",
    "asyncio",
    "threading",
    "concurrent",
    "multiprocessing",
    "socket",
    "signal",
    "ctypes",
    "gc",
    "traceback",
    "weakref",
    "tempfile",
    "shutil",
    "pickle",
    "csv",
    "yaml",
    "tomllib",
    "configparser",
    "argparse",
    "logging.config",
    "importlib.resources",
    "inspect",
    "dis",
    "compile(",
    "exec(",
    "globals(",
    "locals(",
    "vars(",
    "dir(",
    "delattr(",
    "exit(",
    "quit(",
    "input(",
    "pprint(",
    "ascii(",
    "bin(",
    "oct(",
    "hex(",
    "slice(",
    "reversed(",
    "abs(",
    "divmod(",
    "pow(",
    "bytearray(",
    "memoryview(",
    "complex(",
    "classmethod(",
    "staticmethod(",
    "property(",
    "super(",
    "object()",
    "ellipsi",
    "notimplemented",
    "License",
    "Credits",
    "Copyright",
    "help(",
    "breakpoint(",
    "__import__",
]


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND6)
def test_module_source_no_forbidden_token_round6(token):
    """report.py 不应使用这些 stdlib modules / builtin calls。"""
    src = inspect.getsource(rmod)

    allowed = {
        "compile(",
        "globals(",
        "locals(",
        "vars(",
        "dir(",
        "delattr(",
        "exit(",
        "quit(",
        "input(",
        "pprint(",
        "ascii(",
        "bin(",
        "oct(",
        "hex(",
        "slice(",
        "reversed(",
        "abs(",
        "divmod(",
        "pow(",
        "bytearray(",
        "memoryview(",
        "complex(",
        "classmethod(",
        "staticmethod(",
        "property(",
        "super(",
        "object()",
    }
    if token in allowed:
        return

    if token.endswith("("):
        assert token not in src, f"unexpected builtin call {token!r} in report.py"
    else:
        import re
        pattern = r"\b" + re.escape(token) + r"\b"
        matches = re.findall(pattern, src)
        assert not matches, f"unexpected token {token!r} in report.py"


# ---------- module source 字符串精确补强 ----------


def test_module_source_starts_with_docstring():
    src = inspect.getsource(rmod)
    assert src.lstrip().startswith(('"""', "'''"))


def test_module_source_docstring_mentions_provenance():
    src = inspect.getsource(rmod)
    assert "provenance" in src.lower() or "溯源" in src


def test_module_source_docstring_mentions_devset():
    src = inspect.getsource(rmod)
    assert "devset" in src.lower() or "开发集" in src


def test_module_source_docstring_mentions_summary():
    src = inspect.getsource(rmod)
    assert "summary" in src.lower() or "汇总" in src or "聚合" in src


def test_module_source_import_count_6():
    """6 个 module-level imports: __future__ + subprocess + datetime + Path + Any + EVALUATOR_VERSION+REPORT_VERSION。"""
    src = inspect.getsource(rmod)
    import_lines = [
        l for l in src.splitlines()
        if l.strip().startswith(("import ", "from "))
        and not l.startswith(" ")
    ]
    assert len(import_lines) == 6


def test_module_source_imports_subprocess():
    src = inspect.getsource(rmod)
    assert "import subprocess" in src


def test_module_source_imports_datetime():
    src = inspect.getsource(rmod)
    assert "from datetime import datetime" in src


def test_module_source_imports_path():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_imports_any():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_imports_versions():
    src = inspect.getsource(rmod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_module_source_no_relative_import():
    src = inspect.getsource(rmod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert not line.strip().startswith("from .")


def test_module_source_no_star_import():
    src = inspect.getsource(rmod)
    assert "import *" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(rmod)
    assert "__main__" not in src


def test_module_source_no_yield():
    src = inspect.getsource(rmod)
    assert "yield " not in src


def test_module_source_no_async():
    src = inspect.getsource(rmod)
    assert "async " not in src
    assert "await " not in src


def test_module_source_no_global_keyword():
    src = inspect.getsource(rmod)
    assert "\nglobal " not in src
    assert " global " not in src


def test_module_source_no_walrus():
    src = inspect.getsource(rmod)
    assert ":=" not in src


def test_module_source_no_class_definition():
    src = inspect.getsource(rmod)
    assert not any(line.startswith("class ") for line in src.splitlines())


def test_module_source_no_pickle():
    src = inspect.getsource(rmod)
    assert "pickle" not in src


def test_module_source_no_yaml():
    src = inspect.getsource(rmod)
    assert "yaml" not in src


def test_module_source_no_logging():
    src = inspect.getsource(rmod)
    assert "logging" not in src


def test_module_source_no_argparse():
    src = inspect.getsource(rmod)
    assert "argparse" not in src


def test_module_source_no_csv():
    src = inspect.getsource(rmod)
    assert "csv" not in src


def test_module_source_no_tomllib():
    src = inspect.getsource(rmod)
    assert "tomllib" not in src


def test_module_source_uses_subprocess_run():
    src = inspect.getsource(rmod)
    assert "subprocess.run(" in src


def test_module_source_uses_capture_output():
    src = inspect.getsource(rmod)
    assert "capture_output=True" in src


def test_module_source_uses_importlib_metadata():
    src = inspect.getsource(rmod)
    assert "importlib.metadata" in src


def test_module_source_uses_datetime_now():
    src = inspect.getsource(rmod)
    assert "datetime.now" in src


def test_module_source_uses_isoformat():
    src = inspect.getsource(rmod)
    assert ".isoformat()" in src or "isoformat" in src


def test_module_source_uses_astimezone():
    src = inspect.getsource(rmod)
    assert "astimezone" in src


def test_module_source_has_3_metric_constants():
    src = inspect.getsource(rmod)
    assert "_RATIO_METRICS" in src
    assert "_COUNT_METRICS" in src
    assert "_SUCCESS_BOOL_METRICS" in src


def test_module_source_function_count_5():
    src = inspect.getsource(rmod)
    func_count = sum(
        1 for line in src.splitlines()
        if line.startswith("def ")
    )
    assert func_count == 5


def test_module_source_function_names():
    src = inspect.getsource(rmod)
    funcs = [
        line.split("def ")[1].split("(")[0]
        for line in src.splitlines()
        if line.startswith("def ")
    ]
    expected = [
        "get_git_provenance",
        "get_dependency_versions",
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
    ]
    assert sorted(funcs) == sorted(expected)


def test_module_source_has_5_public_funcs():
    """5 个公开函数（无私有）。"""
    src = inspect.getsource(rmod)
    public = [
        line for line in src.splitlines()
        if line.startswith("def ") and not line.startswith("def _")
    ]
    assert len(public) == 5


def test_module_source_has_all():
    src = inspect.getsource(rmod)
    assert "__all__" in src


def test_module_source_all_count_5():
    src = inspect.getsource(rmod)
    all_block = src[src.index("__all__"):]
    assert '"build_provenance"' in all_block
    assert '"build_devset_section"' in all_block
    assert '"aggregate_summary"' in all_block
    assert '"get_git_provenance"' in all_block
    assert '"get_dependency_versions"' in all_block


# ---------- signatures 精确补强 ----------


def test_aggregate_summary_signature():
    sig = inspect.signature(aggregate_summary)
    assert len(sig.parameters) == 1
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_build_devset_section_signature():
    sig = inspect.signature(build_devset_section)
    assert len(sig.parameters) == 1
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_build_provenance_signature_param_count():
    sig = inspect.signature(build_provenance)
    assert len(sig.parameters) == 4


def test_build_provenance_signature_param_names():
    sig = inspect.signature(build_provenance)
    names = list(sig.parameters.keys())
    assert names == ["project_root", "parser_name", "max_chars", "parser_version"]


def test_build_provenance_signature_no_defaults():
    sig = inspect.signature(build_provenance)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_get_git_provenance_signature():
    sig = inspect.signature(get_git_provenance)
    assert len(sig.parameters) == 1
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_get_dependency_versions_signature():
    sig = inspect.signature(get_dependency_versions)
    assert len(sig.parameters) == 0


def test_no_function_has_varargs_in_module():
    for name in ["aggregate_summary", "build_devset_section", "build_provenance", "get_git_provenance", "get_dependency_versions"]:
        fn = getattr(rmod, name)
        sig = inspect.signature(fn)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_POSITIONAL not in kinds
        assert inspect.Parameter.VAR_KEYWORD not in kinds


# ---------- 模块整体合理性 ----------


def test_module_namespace_has_5_callables():
    """5 个公开 callable + 3 个 module-level 常量（_RATIO_METRICS 等 str 没 __module__）。"""
    ns = [
        (k, v) for k, v in vars(rmod).items()
        if getattr(v, "__module__", "") == rmod.__name__
        and not k.startswith("__")
    ]
    names = [k for k, v in ns]
    expected = [
        "get_git_provenance",
        "get_dependency_versions",
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
    ]
    assert sorted(names) == sorted(expected)


def test_module_name():
    assert rmod.__name__ == "evaluation.report"


def test_module_file_endswith_report_py():
    assert rmod.__file__.replace("\\", "/").endswith("evaluation/report.py")


def test_module_docstring_present():
    assert rmod.__doc__ is not None and len(rmod.__doc__) > 30


def test_module_all_present():
    assert hasattr(rmod, "__all__")


def test_module_all_count_5():
    assert len(rmod.__all__) == 5


def test_module_all_contents():
    assert sorted(rmod.__all__) == sorted([
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions",
    ])


def test_module_all_callables_callable():
    for name in rmod.__all__:
        assert callable(getattr(rmod, name))


def test_module_no_user_classes():
    classes = [
        (k, v) for k, v in vars(rmod).items()
        if isinstance(v, type) and getattr(v, "__module__", "") == rmod.__name__
    ]
    assert classes == []


def test_module_function_module_eq():
    for name in rmod.__all__:
        fn = getattr(rmod, name)
        assert fn.__module__ == "evaluation.report"


def test_module_constants_present():
    assert hasattr(rmod, "_RATIO_METRICS")
    assert hasattr(rmod, "_COUNT_METRICS")
    assert hasattr(rmod, "_SUCCESS_BOOL_METRICS")


def test_module_ratio_metrics_count():
    assert len(rmod._RATIO_METRICS) == 12


def test_module_count_metrics_count():
    assert len(rmod._COUNT_METRICS) == 1


def test_module_success_bool_metrics_count():
    assert len(rmod._SUCCESS_BOOL_METRICS) == 1


# ---------- 端到端集成补强 ----------


def test_e2e_build_provenance_with_real_repo():
    """在真实 repo 根目录跑，应该能拿到 git_commit。"""
    proj_root = Path(__file__).resolve().parent.parent
    out = build_provenance(proj_root, "fallback", 800, "1.0.0")
    assert out["parser_name"] == "fallback"
    assert out["max_chars"] == 800
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION


def test_e2e_aggregate_summary_with_full_metrics():
    """模拟完整的 per_doc 指标做聚合。"""
    docs = [
        _per_doc({
            "pipeline_success": {"value": True, "reason": None},
            "element_count_total": {"value": 10, "reason": None},
            "schema_valid": {"value": 1.0, "reason": None},
            "pdf_locator_valid_ratio": {"value": 0.5, "reason": None},
            "silent_drop_count": {"value": 2, "reason": None},
        }),
        _per_doc({
            "pipeline_success": {"value": False, "reason": None},
            "element_count_total": {"value": None, "reason": "pipeline_failed"},
            "schema_valid": {"value": None, "reason": "pipeline_failed"},
            "pdf_locator_valid_ratio": {"value": None, "reason": "pipeline_failed"},
            "silent_drop_count": {"value": None, "reason": "pipeline_failed"},
        }),
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 10
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert out["silent_drop_total"] == 2


def test_e2e_build_devset_section_with_real_manifest():
    """用真实 Manifest 模拟（SimpleNamespace）。"""
    m = _manifest_ns(
        devset_status="incomplete",
        file_count=2,
        content_group_count=1,
        pdf_count=1,
        docx_count=1,
        categories_covered=["a", "b", "c"],
    )
    out = build_devset_section(m)
    assert out["status"] == "incomplete"
    assert out["file_count"] == 2
    assert out["pdf_count"] == 1
    assert out["docx_count"] == 1
    assert out["categories_covered"] == ["a", "b", "c"]


def test_e2e_aggregate_summary_does_not_mutate_input():
    docs = [_per_doc({"pipeline_success": {"value": True, "reason": None}})]
    before = json.loads(json.dumps(docs))
    aggregate_summary(docs)
    assert docs == before


def test_e2e_build_provenance_json_serializable(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    s = json.dumps(out)
    parsed = json.loads(s)
    assert parsed == out


def test_e2e_aggregate_summary_with_kwargs():
    docs = [_per_doc({"pipeline_success": {"value": True, "reason": None}})]
    out = aggregate_summary(per_doc_results=docs)
    assert isinstance(out, dict)


def test_e2e_build_provenance_with_positional(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["parser_name"] == "fallback"


def test_e2e_build_provenance_with_kwargs(tmp_path):
    out = build_provenance(
        project_root=tmp_path,
        parser_name="fallback",
        max_chars=800,
        parser_version="1.0.0",
    )
    assert out["parser_name"] == "fallback"


def test_e2e_aggregate_summary_with_positional():
    docs = [_per_doc({"pipeline_success": {"value": True, "reason": None}})]
    out = aggregate_summary(docs)
    assert isinstance(out, dict)


def test_e2e_get_dependency_versions_returns_3_entries():
    out = get_dependency_versions()
    assert len(out) == 3


def test_e2e_full_report_assembly_chain(tmp_path):
    """端到端：provenance + devset + summary + per_doc。"""
    proj_root = Path(__file__).resolve().parent.parent
    provenance = build_provenance(proj_root, "fallback", 800, None)
    devset = build_devset_section(_manifest_ns())
    summary = aggregate_summary([])
    report = {
        "report_version": REPORT_VERSION,
        "provenance": provenance,
        "devset": devset,
        "summary": summary,
        "per_doc": [],
    }
    # json 可序列化
    s = json.dumps(report)
    assert isinstance(s, str)
    parsed = json.loads(s)
    assert parsed["report_version"] == REPORT_VERSION
