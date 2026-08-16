"""evaluation/report.py 第九十七轮 edges 测试（Round 697）。

补强 edges68 未触及的角度（第六十二批）。

新角度：
- aggregate_summary 数值精度（ratio 0.5/None/1.0 → macro 0.75 participating 2 not_eval 1 / True+False → 0.5 / 单值 1.0）
- success_rates 把失败文档计入 total（True/True/False → 2/3，rate=2/3）
- counts 里 value 0 参与（0/5/None → sum 5 participating 2）
- ratio value 0.0 参与（非 None）
- figure_caption_* 不进 ratio_macro_averages（给了 value 也不出现）
- silent_drop_total（None/3/0 → 3 / 全 None → None / [0,0] → 0）
- build_devset_section 用最小 stub 对象（6 键透传）
- build_provenance 完整形状（9 键 / evaluator_version·report_version 绑定 evaluation 常量="1.1" / run_timestamp_iso 可 fromisoformat 且 tz-aware / max_chars int）
- get_git_provenance 真实仓库运行（commit 40 hex 或 None / dirty 是 bool）
- 源码补强（rev-parse/status 两条命令列表 / strip or None / dirty bool 表达式 / dirty 默认 True 注解 / timeout=10 恰 2 / datetime 一行 / int(max_chars) / 两个常量元组精确 / figure_caption 注释 / rate 三元）
- AST 补强（_RATIO_METRICS unparse 精确 12 项 / 3 个模块常量 Assign / build_provenance 返回键序 / get_dependency_versions for 元组 / aggregate_summary total·not_eval 赋值 / build_devset_section 6 键 / get_git_provenance AnnAssign）
- forbidden tokens 第一百六十七批
"""

from __future__ import annotations

import ast
import inspect
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

import evaluation.report as report_mod
from evaluation import EVALUATOR_VERSION, REPORT_VERSION
from evaluation.report import (
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_git_provenance,
)


def _pd(doc_id: str, **metric_values) -> dict:
    return {
        "doc_id": doc_id,
        "metrics": {k: {"value": v, "reason": None} for k, v in metric_values.items()},
    }


# ---------- aggregate_summary 数值精度 ----------

def test_ratio_macro_skips_none_batch52():
    docs = [
        _pd("a", pdf_locator_valid_ratio=0.5),
        _pd("b", pdf_locator_valid_ratio=None),
        _pd("c", pdf_locator_valid_ratio=1.0),
    ]
    out = aggregate_summary(docs)
    entry = out["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert entry["macro_average"] == pytest.approx(0.75)
    assert entry["participating_docs"] == 2
    assert entry["not_evaluated"] == 1


def test_ratio_macro_bool_values_batch52():
    docs = [
        _pd("a", text_preservation_equal=True),
        _pd("b", text_preservation_equal=False),
    ]
    out = aggregate_summary(docs)
    entry = out["ratio_macro_averages"]["text_preservation_equal"]
    assert entry["macro_average"] == pytest.approx(0.5)
    assert entry["not_evaluated"] == 0


def test_ratio_macro_single_value_batch52():
    out = aggregate_summary([_pd("a", chunk_boundary_f1=1.0)])
    entry = out["ratio_macro_averages"]["chunk_boundary_f1"]
    assert entry["macro_average"] == 1.0
    assert entry["participating_docs"] == 1


def test_ratio_zero_participates_batch52():
    docs = [
        _pd("a", image_resource_exists_ratio=0.0),
        _pd("b", image_resource_exists_ratio=None),
    ]
    out = aggregate_summary(docs)
    entry = out["ratio_macro_averages"]["image_resource_exists_ratio"]
    assert entry["macro_average"] == 0.0
    assert entry["participating_docs"] == 1
    assert entry["not_evaluated"] == 1


def test_missing_metric_key_not_evaluated_batch52():
    """metrics 里完全没有该键 → 不参与。"""
    docs = [_pd("a", element_count_total=3), {"doc_id": "b", "metrics": {}}]
    out = aggregate_summary(docs)
    entry = out["ratio_macro_averages"]["schema_valid"]
    assert entry["participating_docs"] == 0
    assert entry["macro_average"] is None
    assert entry["not_evaluated"] == 2


# ---------- success_rates total 计入失败文档 ----------

def test_success_rate_counts_failed_in_total_batch52():
    docs = [
        _pd("a", pipeline_success=True),
        _pd("b", pipeline_success=True),
        _pd("c", pipeline_success=False),
    ]
    out = aggregate_summary(docs)
    entry = out["success_rates"]["pipeline_success"]
    assert entry["success_count"] == 2
    assert entry["total"] == 3
    assert entry["rate"] == pytest.approx(2 / 3)


def test_success_rate_all_true_batch52():
    docs = [_pd("a", pipeline_success=True), _pd("b", pipeline_success=True)]
    entry = aggregate_summary(docs)["success_rates"]["pipeline_success"]
    assert entry == {"success_count": 2, "total": 2, "rate": 1.0}


# ---------- counts 里 0 参与 ----------

def test_counts_zero_participates_batch52():
    docs = [
        _pd("a", element_count_total=0),
        _pd("b", element_count_total=5),
        _pd("c", element_count_total=None),
    ]
    out = aggregate_summary(docs)
    entry = out["counts"]["element_count_total"]
    assert entry["sum"] == 5
    assert entry["participating_docs"] == 2


# ---------- figure_caption 不进 ratio ----------

def test_figure_caption_excluded_from_macro_batch52():
    docs = [_pd("a", figure_caption_precision=0.9, figure_caption_recall=1.0)]
    out = aggregate_summary(docs)
    ratios = out["ratio_macro_averages"]
    assert "figure_caption_precision" not in ratios
    assert "figure_caption_recall" not in ratios
    assert "figure_caption_f1" not in ratios


# ---------- silent_drop_total ----------

def test_silent_drop_mixed_sum_batch52():
    docs = [
        _pd("a", silent_drop_count=None),
        _pd("b", silent_drop_count=3),
        _pd("c", silent_drop_count=0),
    ]
    assert aggregate_summary(docs)["silent_drop_total"] == 3


def test_silent_drop_all_none_is_none_batch52():
    docs = [_pd("a", silent_drop_count=None), _pd("b", silent_drop_count=None)]
    assert aggregate_summary(docs)["silent_drop_total"] is None


def test_silent_drop_all_zero_is_zero_batch52():
    docs = [_pd("a", silent_drop_count=0), _pd("b", silent_drop_count=0)]
    assert aggregate_summary(docs)["silent_drop_total"] == 0


# ---------- build_devset_section stub ----------

def test_build_devset_section_stub_batch52():
    class _M:
        devset_status = "incomplete"
        file_count = 7
        content_group_count = 3
        pdf_count = 5
        docx_count = 2
        categories_covered = ["contracts", "reports"]

    out = build_devset_section(_M())
    assert out == {
        "status": "incomplete",
        "file_count": 7,
        "content_group_count": 3,
        "pdf_count": 5,
        "docx_count": 2,
        "categories_covered": ["contracts", "reports"],
    }


# ---------- build_provenance 完整形状 ----------

def test_build_provenance_full_shape_batch52(monkeypatch):
    monkeypatch.setattr(report_mod, "get_git_provenance",
                        lambda root: {"git_commit": None, "git_dirty": False})
    monkeypatch.setattr(report_mod, "get_dependency_versions",
                        lambda: {"pdfplumber": "1.2.3"})
    out = build_provenance(Path("."), "fallback", "800", "0.9")
    assert set(out.keys()) == {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    }
    assert out["git_commit"] is None
    assert out["git_dirty"] is False
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] == "0.9"
    assert out["dependencies"] == {"pdfplumber": "1.2.3"}
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)
    ts = datetime.fromisoformat(out["run_timestamp_iso"])
    assert ts.tzinfo is not None


def test_build_provenance_version_constants_batch52(monkeypatch):
    monkeypatch.setattr(report_mod, "get_git_provenance",
                        lambda root: {"git_commit": "c", "git_dirty": True})
    monkeypatch.setattr(report_mod, "get_dependency_versions", lambda: {})
    out = build_provenance(Path("."), "fallback", 100, None)
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION
    # 项目不变量：两版本固定 1.1（指示线审计目标，不可动）
    assert EVALUATOR_VERSION == "1.1"
    assert REPORT_VERSION == "1.1"


# ---------- get_git_provenance 真实仓库 ----------

def test_get_git_provenance_real_repo_batch52():
    root = Path(__file__).resolve().parents[1]
    out = get_git_provenance(root)
    assert set(out.keys()) == {"git_commit", "git_dirty"}
    assert out["git_commit"] is None or (
        isinstance(out["git_commit"], str)
        and len(out["git_commit"]) == 40
        and all(c in "0123456789abcdef" for c in out["git_commit"])
    )
    assert isinstance(out["git_dirty"], bool)


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(report_mod)


def test_source_git_command_lists_batch52():
    src = _src()
    assert '["git", "rev-parse", "HEAD"]' in src
    assert '["git", "status", "--porcelain"]' in src


def test_source_commit_strip_or_none_batch52():
    assert "commit = r.stdout.strip() or None" in _src()


def test_source_dirty_bool_expr_batch52():
    assert "dirty = bool(r2.returncode == 0 and r2.stdout.strip())" in _src()


def test_source_dirty_default_annotation_batch52():
    assert "dirty: bool = True" in _src()


def test_source_timeout_count_2_batch52():
    assert _src().count("timeout=10") == 2


def test_source_datetime_one_line_batch52():
    assert "datetime.now().astimezone().isoformat()" in _src()


def test_source_max_chars_int_batch52():
    assert '"max_chars": int(max_chars)' in _src()


def test_source_count_metrics_tuple_batch52():
    assert '_COUNT_METRICS = ("element_count_total",)' in _src()


def test_source_success_bool_tuple_batch52():
    assert '_SUCCESS_BOOL_METRICS = ("pipeline_success",)' in _src()


def test_source_figure_caption_comment_batch52():
    assert "figure_caption_* 始终 null" in _src()


def test_source_rate_ternary_batch52():
    assert "rate = (successes / total) if total else None" in _src()


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(report_mod))


def test_ast_ratio_metrics_unparse_exact_batch52():
    tree = _tree()
    assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "_RATIO_METRICS"
    )
    assert ast.unparse(assign) == (
        "_RATIO_METRICS = ('schema_valid', 'pdf_locator_valid_ratio', "
        "'docx_locator_valid_ratio', 'image_resource_exists_ratio', "
        "'chunk_reference_intact_ratio', 'text_preservation_equal', "
        "'text_char_multiset_precision', 'text_char_multiset_recall', "
        "'heading_boundary_compliance', 'chunk_boundary_precision', "
        "'chunk_boundary_recall', 'chunk_boundary_f1')"
    )


def test_ast_module_constant_names_batch52():
    tree = _tree()
    names = [
        n.targets[0].id for n in tree.body
        if isinstance(n, ast.Assign)
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id.startswith("_")
        and not n.targets[0].id.startswith("__")
    ]
    assert names == ["_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS"]


def test_ast_build_provenance_key_order_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_provenance")
    ret = func.body[-1]
    keys = [k.value for k in ret.value.keys]
    assert keys == [
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    ]


def test_ast_dependency_for_tuple_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_dependency_versions")
    src = ast.unparse(func)
    assert "for pkg in ('pdfplumber', 'python-docx', 'pypdfium2'):" in src


def test_ast_aggregate_assignments_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    src = ast.unparse(func)
    assert "total = len(per_doc_results)" in src
    assert "not_eval = len(per_doc_results) - len(values)" in src
    assert "summary['counts'] = counts" in src
    assert "summary['success_rates'] = success_rates" in src
    assert "summary['ratio_macro_averages'] = ratio_avgs" in src


def test_ast_build_devset_section_keys_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_devset_section")
    src = ast.unparse(func)
    for key in ("status", "file_count", "content_group_count",
                "pdf_count", "docx_count", "categories_covered"):
        assert f"'{key}'" in src


def test_ast_git_provenance_annassign_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance")
    src = ast.unparse(func)
    assert "commit: str | None = None" in src


# ---------- forbidden tokens 第一百六十七批 ----------

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


def test_source_no_subprocess_module_string_batch52():
    """subprocess 是合法 import（get_git_provenance 用），但禁止 subprocess.Popen 直调。"""
    assert "subprocess.Popen" not in _src()
    assert "subprocess.call" not in _src()
    assert "subprocess.check_output" not in _src()


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
