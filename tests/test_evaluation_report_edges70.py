"""evaluation/report.py 第九十八轮 edges 测试（Round 704）。

补强 edges69 未触及的角度（第六十九批）。

新角度：
- aggregate_summary 重复 doc_id 不去重 / 未知指标忽略 / 部分 doc 缺 pipeline_success 键 → success 不计但 total 计
- counts 浮点值参与（现状记录）/ ratio 超 1 不截断（现状记录）
- _RATIO_METRICS 跨模块不变量（去掉 compute 产出键后恰剩 3 个 chunk_boundary_*；figure_caption_* 不在）
- success_rates 空清单精确形状 {"success_count": 0, "total": 0, "rate": None}
- get_dependency_versions 真实运行（3 包名单 / pdfplumber 必有版本 / 每次新 dict）
- get_git_provenance subprocess.run 两次调用命令序列（rev-parse → status --porcelain）
- build_devset_section 端到端（真实 load_manifest → 6 键）
- 源码补强（from evaluation import 双常量 / subprocess.run kwargs / summary 4 段 key 顺序 / counts values 双分支）
- AST 补强（aggregate 3 个 ListComp / get_git_provenance 2 个 subprocess.Call / build_provenance 调 get_git_provenance 在首位）
- forbidden tokens 第一百七十四批
"""

from __future__ import annotations

import ast
import inspect
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import evaluation.report as report_mod
from evaluation.manifest import load_manifest
from evaluation.report import (
    _RATIO_METRICS,
    aggregate_summary,
    build_devset_section,
    get_dependency_versions,
    get_git_provenance,
)
from evaluation.metrics import compute_automatic_metrics


def _pd(doc_id: str, **metric_values) -> dict:
    return {
        "doc_id": doc_id,
        "metrics": {k: {"value": v, "reason": None} for k, v in metric_values.items()},
    }


# ---------- 重复 doc_id 不去重 ----------

def test_duplicate_doc_ids_counted_twice_batch52():
    docs = [
        _pd("same", pipeline_success=True),
        _pd("same", pipeline_success=True),
    ]
    out = aggregate_summary(docs)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 2
    assert out["success_rates"]["pipeline_success"]["total"] == 2


def test_unknown_metrics_ignored_batch52():
    docs = [_pd("a", custom_metric=0.9, another=1)]
    out = aggregate_summary(docs)
    flat = str(out)
    assert "custom_metric" not in flat
    assert "another" not in flat


def test_missing_pipeline_success_counts_in_total_batch52():
    docs = [
        _pd("a", pipeline_success=True),
        {"doc_id": "b", "metrics": {"schema_valid": {"value": True, "reason": None}}},
    ]
    entry = aggregate_summary(docs)["success_rates"]["pipeline_success"]
    assert entry["success_count"] == 1
    assert entry["total"] == 2
    assert entry["rate"] == pytest.approx(0.5)


# ---------- 现状记录：浮点 count / 超 1 ratio ----------

def test_counts_float_value_participates_batch52():
    docs = [_pd("a", element_count_total=2.5)]
    entry = aggregate_summary(docs)["counts"]["element_count_total"]
    assert entry["sum"] == 2.5
    assert entry["participating_docs"] == 1


def test_ratio_above_one_not_clamped_batch52():
    docs = [_pd("a", pdf_locator_valid_ratio=1.5)]
    entry = aggregate_summary(docs)["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert entry["macro_average"] == 1.5


# ---------- _RATIO_METRICS 跨模块不变量 ----------

def test_ratio_metrics_minus_compute_keys_batch52():
    compute_keys = set(compute_automatic_metrics(None, None, "pdf", None))
    assert set(_RATIO_METRICS) - compute_keys == {
        "chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1",
    }


def test_ratio_metrics_excludes_figure_caption_batch52():
    assert not any(name.startswith("figure_caption") for name in _RATIO_METRICS)


def test_ratio_metrics_all_compute_names_present_batch52():
    compute_keys = set(compute_automatic_metrics(None, None, "pdf", None))
    assert {"schema_valid", "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
            "image_resource_exists_ratio", "chunk_reference_intact_ratio",
            "text_preservation_equal", "text_char_multiset_precision",
            "text_char_multiset_recall", "heading_boundary_compliance"} <= set(_RATIO_METRICS)


# ---------- 空清单精确形状 ----------

def test_success_rates_empty_exact_batch52():
    out = aggregate_summary([])
    assert out["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 0, "rate": None,
    }
    assert out["silent_drop_total"] is None


# ---------- get_dependency_versions 真实运行 ----------

def test_dependency_versions_real_names_batch52():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}
    for v in out.values():
        assert v is None or isinstance(v, str)


def test_dependency_versions_pdfplumber_installed_batch52():
    assert get_dependency_versions()["pdfplumber"] is not None


def test_dependency_versions_fresh_dict_batch52():
    a = get_dependency_versions()
    b = get_dependency_versions()
    assert a == b
    assert a is not b


# ---------- get_git_provenance 命令序列 ----------

def test_git_provenance_command_sequence_batch52():
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        r = MagicMock()
        if cmd[1] == "rev-parse":
            r.returncode = 0
            r.stdout = "abc123\n"
        else:
            r.returncode = 0
            r.stdout = ""
        return r

    with patch.object(report_mod.subprocess, "run", side_effect=fake_run):
        out = get_git_provenance(Path("."))
    assert calls == [["git", "rev-parse", "HEAD"], ["git", "status", "--porcelain"]]
    assert out == {"git_commit": "abc123", "git_dirty": False}


def test_git_provenance_dirty_output_batch52():
    def fake_run(cmd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        r.stdout = " M file.py\n" if cmd[1] == "status" else "abc\n"
        return r

    with patch.object(report_mod.subprocess, "run", side_effect=fake_run):
        out = get_git_provenance(Path("."))
    assert out["git_dirty"] is True


# ---------- build_devset_section 端到端 ----------

def test_build_devset_section_from_real_manifest_batch52(tmp_path):
    payload = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["contracts"]},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf"},
            {"doc_id": "d3", "path": "c.docx", "source_type": "docx"},
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    out = build_devset_section(m)
    assert out == {
        "status": "incomplete",
        "file_count": 3,
        "content_group_count": 3,
        "pdf_count": 2,
        "docx_count": 1,
        "categories_covered": ["contracts"],
    }


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(report_mod)


def test_source_evaluation_import_batch52():
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in _src()


def test_source_subprocess_run_kwargs_batch52():
    src = _src()
    assert "capture_output=True" in src
    assert "text=True" in src
    assert 'encoding="utf-8"' in src
    assert 'errors="replace"' in src


def test_source_summary_4_sections_batch52():
    src = _src()
    assert 'summary["counts"] = counts' in src
    assert 'summary["success_rates"] = success_rates' in src
    assert 'summary["ratio_macro_averages"] = ratio_avgs' in src
    assert 'summary["silent_drop_total"]' in src


def test_source_counts_two_branches_batch52():
    src = _src()
    assert 'counts[name] = {' in src
    assert '{"sum": None, "participating_docs": 0}' in src


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(report_mod))


def test_ast_aggregate_listcomps_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    comps = [n for n in ast.walk(func) if isinstance(n, ast.ListComp)]
    # counts 1 + ratios 1 + silent 1（success 用生成器）
    assert len(comps) == 3


def test_ast_git_provenance_2_subprocess_calls_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance")
    calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and isinstance(n.func.value, ast.Name) and n.func.value.id == "subprocess"
    ]
    assert len(calls) == 2
    assert all(n.func.attr == "run" for n in calls)


def test_ast_build_provenance_git_first_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_provenance")
    src = ast.unparse(func)
    assert src.index("get_git_provenance") < src.index("get_dependency_versions")


# ---------- forbidden tokens 第一百七十四批 ----------

def test_source_no_eval_batch52():
    assert "eval(" not in _src()


def test_source_no_exec_batch52():
    assert "exec(" not in _src()


def test_source_no_compile_batch52():
    assert "compile(" not in _src()


def test_source_no_globals_batch52():
    assert "globals(" not in _src()


def test_source_no_locals_batch52():
    assert "locals(" not in _src()


def test_source_no_os_system_batch52():
    assert "os.system" not in _src()


def test_source_no_popen_batch52():
    assert "popen(" not in _src()


def test_source_no_yaml_load_batch52():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch52():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch52():
    assert "socket" not in _src()


def test_source_no_requests_batch52():
    assert "requests" not in _src()


def test_source_no_urllib_batch52():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch52():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch52():
    assert "yield" not in _src()


def test_source_no_async_await_batch52():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch52():
    assert "open(" not in _src()
