"""evaluation/report.py 第二百零一轮 edges 测试（Round 725）。

补强 edges71/edges72 未触及的角度（第九十批）。

新角度：
- aggregate_summary 空输入全矩阵（rate None / counts sum None / 12 ratio 全 null not_evaluated 0 / silent None）
- 成功判定严格 is True（value=1 不计数）
- 指标键整体缺失 → not_evaluated（participating 2 / not_evaluated 1 / macro 0.75）
- counts 键缺失 → sum None participating 0
- macro 精确分数（[1/3, 2/3] → 0.5）
- silent_drop 0 值保留（sum([0]) → 0 非 None）
- get_dependency_versions 真实运行（3 键精确 / 值 None 或版本样式）
- get_git_provenance rc 分支（rev-parse rc1 → commit None / porcelain 空输出 → dirty False / 有输出 → True）
- build_provenance 9 键 + evaluator_version/report_version 等于锁定常量 "1.1"
- run_timestamp_iso 可 fromisoformat 解析且带时区
- build_devset_section 真实 Manifest 全字段（2 pdf + 1 docx + categories / 空 manifest 全零）
- AST（五函数 If/For/Return/Try/ListComp/Dict/Subscript/AnnAssign）
- 源码补强（subprocess.run×2 / timeout=10×2 / is True×1 / is not None×3 / figure_caption 排除注释）
- forbidden tokens 第一百九十五批（subprocess 是本模块自身合法用法，不在排除列表）
"""

from __future__ import annotations

import ast
import inspect
import re
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

import evaluation
import evaluation.report as report_mod
from evaluation.manifest import DocumentEntry, Manifest
from evaluation.report import (
    _RATIO_METRICS,
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


# ---------- 空输入全矩阵 ----------

def test_aggregate_empty_full_matrix_batch53():
    out = aggregate_summary([])
    assert out["success_rates"]["pipeline_success"] == \
        {"success_count": 0, "total": 0, "rate": None}
    assert out["counts"]["element_count_total"] == \
        {"sum": None, "participating_docs": 0}
    for name in _RATIO_METRICS:
        assert out["ratio_macro_averages"][name] == \
            {"macro_average": None, "participating_docs": 0,
             "not_evaluated": 0}, name
    assert out["silent_drop_total"] is None
    assert list(out.keys()) == ["counts", "success_rates",
                                "ratio_macro_averages", "silent_drop_total"]


# ---------- 严格 True ----------

def test_success_strict_true_only_batch53():
    out = aggregate_summary([{"doc_id": "a", "metrics": {
        "pipeline_success": {"value": 1}}}])  # int 1 非 True
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.0


# ---------- 键缺失 ----------

def test_ratio_missing_key_not_evaluated_batch53():
    out = aggregate_summary([
        {"doc_id": "a", "metrics": {"schema_valid": {"value": 0.5}}},
        {"doc_id": "b", "metrics": {}},
        {"doc_id": "c", "metrics": {"schema_valid": {"value": 1.0}}},
    ])
    assert out["ratio_macro_averages"]["schema_valid"] == \
        {"macro_average": 0.75, "participating_docs": 2, "not_evaluated": 1}


def test_counts_missing_key_sum_none_batch53():
    out = aggregate_summary([{"doc_id": "a", "metrics": {}}])
    assert out["counts"]["element_count_total"] == \
        {"sum": None, "participating_docs": 0}


def test_counts_skips_none_values_batch53():
    out = aggregate_summary([
        {"doc_id": "a", "metrics": {"element_count_total": {"value": 3,
                                                            "reason": None}}},
        {"doc_id": "b", "metrics": {"element_count_total": {"value": None,
                                                            "reason": "x"}}},
    ])
    assert out["counts"]["element_count_total"] == \
        {"sum": 3, "participating_docs": 1}


# ---------- macro 分数 ----------

def test_macro_exact_half_batch53():
    out = aggregate_summary([
        {"doc_id": "a", "metrics": {"schema_valid": {"value": 1 / 3}}},
        {"doc_id": "b", "metrics": {"schema_valid": {"value": 2 / 3}}},
    ])
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == \
        pytest.approx(0.5)


# ---------- silent_drop ----------

def test_silent_zero_value_kept_batch53():
    out = aggregate_summary([{"doc_id": "a", "metrics": {
        "silent_drop_count": {"value": 0}}}])
    assert out["silent_drop_total"] == 0


def test_silent_mixed_sum_batch53():
    out = aggregate_summary([
        {"doc_id": "a", "metrics": {"silent_drop_count": {"value": 2}}},
        {"doc_id": "b", "metrics": {"silent_drop_count": {"value": None}}},
        {"doc_id": "c", "metrics": {"silent_drop_count": {"value": 3}}},
    ])
    assert out["silent_drop_total"] == 5


# ---------- get_dependency_versions 真实运行 ----------

def test_dependency_versions_real_batch53():
    deps = get_dependency_versions()
    assert sorted(deps.keys()) == ["pdfplumber", "pypdfium2", "python-docx"]
    for v in deps.values():
        assert v is None or re.fullmatch(r"[0-9][0-9a-zA-Z.\-]*", v), v


# ---------- get_git_provenance rc 分支 ----------

class _FakeRc:
    def __init__(self, returncode, stdout=""):
        self.returncode = returncode
        self.stdout = stdout


def test_git_revparse_rc1_commit_none_batch53(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd[1])
        if cmd[1] == "rev-parse":
            return _FakeRc(1, "deadbeef\n")
        return _FakeRc(0, "")
    monkeypatch.setattr(report_mod.subprocess, "run", fake_run)
    out = get_git_provenance(Path("."))
    assert out == {"git_commit": None, "git_dirty": False}
    assert calls == ["rev-parse", "status"]


def test_git_porcelain_empty_dirty_false_batch53(monkeypatch):
    def fake_run(cmd, **kwargs):
        return _FakeRc(0, "" if cmd[1] == "status" else "abc\n")
    monkeypatch.setattr(report_mod.subprocess, "run", fake_run)
    assert get_git_provenance(Path("."))["git_dirty"] is False


def test_git_porcelain_nonempty_dirty_true_batch53(monkeypatch):
    def fake_run(cmd, **kwargs):
        return _FakeRc(0, " M file\n" if cmd[1] == "status" else "abc\n")
    monkeypatch.setattr(report_mod.subprocess, "run", fake_run)
    assert get_git_provenance(Path("."))["git_dirty"] is True


def test_git_commit_stdout_strip_batch53(monkeypatch):
    def fake_run(cmd, **kwargs):
        return _FakeRc(0, "  abc123  \n" if cmd[1] == "rev-parse" else "")
    monkeypatch.setattr(report_mod.subprocess, "run", fake_run)
    assert get_git_provenance(Path("."))["git_commit"] == "abc123"


# ---------- build_provenance 锁定常量 ----------

def test_build_provenance_version_constants_locked_batch53(monkeypatch):
    monkeypatch.setattr(report_mod, "get_git_provenance",
                        lambda r: {"git_commit": None, "git_dirty": False})
    monkeypatch.setattr(report_mod, "get_dependency_versions", lambda: {})
    out = build_provenance(Path("."), "fallback", 800, None)
    assert evaluation.EVALUATOR_VERSION == "1.1"
    assert evaluation.REPORT_VERSION == "1.1"
    assert out["evaluator_version"] == "1.1"
    assert out["report_version"] == "1.1"
    assert out["parser_version"] is None
    assert out["max_chars"] == 800


def test_run_timestamp_parseable_tz_aware_batch53(monkeypatch):
    monkeypatch.setattr(report_mod, "get_git_provenance",
                        lambda r: {"git_commit": None, "git_dirty": True})
    monkeypatch.setattr(report_mod, "get_dependency_versions", lambda: {})
    out = build_provenance(Path("."), "fallback", 800, None)
    ts = datetime.fromisoformat(out["run_timestamp_iso"])
    assert ts.utcoffset() is not None


# ---------- build_devset_section 真实 Manifest ----------

def _doc(doc_id, source_type, categories=(), paired=None):
    return DocumentEntry(
        doc_id=doc_id, path_str=f"{doc_id}.pdf", resolved_path=Path("x"),
        source_type=source_type, sha256=None, categories=categories,
        paired_with=paired, annotation_file_str=None, annotation_resolved=None,
        expectations=None,
    )


def test_devset_section_real_manifest_batch53(tmp_path):
    m = Manifest("1.0", "incomplete", (
        _doc("a", "pdf", ("cat1", "cat2")),
        _doc("b", "docx", ("cat2",)),
        _doc("c", "pdf", ()),
    ), (), tmp_path)
    out = build_devset_section(m)
    assert out == {
        "status": "incomplete", "file_count": 3, "content_group_count": 3,
        "pdf_count": 2, "docx_count": 1,
        "categories_covered": ["cat1", "cat2"],
    }


def test_devset_section_empty_manifest_batch53(tmp_path):
    m = Manifest("1.0", "complete", (), (), tmp_path)
    out = build_devset_section(m)
    assert out["file_count"] == 0
    assert out["content_group_count"] == 0
    assert out["categories_covered"] == []
    assert out["status"] == "complete"


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(report_mod)


def test_source_subprocess_counts_batch53():
    src = _src()
    assert src.count("subprocess.run(") == 2
    assert src.count("timeout=10") == 2
    assert src.count("is True") == 1
    assert src.count("is not None") == 3


def test_source_figure_caption_excluded_batch53():
    src = _src()
    assert "figure_caption_* 始终 null" in src  # 排除注释存在
    assert "figure_caption" not in _RATIO_METRICS


def test_source_version_import_batch53():
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in _src()


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(report_mod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _counts(func) -> dict:
    import collections
    return collections.Counter(type(n).__name__ for n in ast.walk(func))


@pytest.mark.parametrize("name,expect", [
    ("get_git_provenance", (1, 0, 1, 1, 0, 1, 1, 2)),
    ("get_dependency_versions", (0, 1, 1, 1, 0, 1, 5, 1)),
    ("build_provenance", (0, 0, 1, 0, 0, 1, 3, 0)),
    ("build_devset_section", (0, 0, 1, 0, 0, 1, 1, 0)),
    ("aggregate_summary", (2, 3, 1, 0, 3, 15, 22, 4)),
])
def test_ast_function_structures_batch53(name, expect):
    c = _counts(_func(name))
    got = (c["If"], c["For"], c["Return"], c["Try"], c["ListComp"],
           c["Dict"], c["Subscript"], c["AnnAssign"])
    assert got == expect, name


# ---------- forbidden tokens 第一百九十五批 ----------

def test_source_no_eval_batch53():
    assert "eval(" not in _src()


def test_source_no_exec_batch53():
    assert "exec(" not in _src()


def test_source_no_compile_batch53():
    assert "compile(" not in _src()


def test_source_no_globals_batch53():
    assert "globals(" not in _src()


def test_source_no_locals_batch53():
    assert "locals(" not in _src()


def test_source_no_os_system_batch53():
    assert "os.system" not in _src()


def test_source_no_popen_batch53():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch53():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch53():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch53():
    assert "socket" not in _src()


def test_source_no_requests_batch53():
    assert "requests" not in _src()


def test_source_no_urllib_batch53():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch53():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch53():
    assert "yield" not in _src()


def test_source_no_async_await_batch53():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch53():
    assert "open(" not in _src()
