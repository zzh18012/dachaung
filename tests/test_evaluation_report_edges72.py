"""evaluation/report.py 第二百轮 edges 测试（Round 718）。

补强 edges71 未触及的角度（第八十三批）。

新角度：
- 真实 compute 输出喂 aggregate（document None ×2 → success rate 0.0 / 12 个 ratio 全 null not_evaluated 2）
- 合法 doc（mock schema 过）→ success_count 1 rate 1.0
- counts 值为 0 时仍参与（sum 0 participating 1，非 None 分支）
- 成功率精确分数（1/3）/ ratio 值 0.0 参与
- participating + not_evaluated == len(docs) 全 12 键不变量
- build_provenance max_chars float 截断（7.9 → 7）/ str "800" → 800
- get_git_provenance 真实仓库运行（commit str 40-hex 或 None / dirty bool）
- 三个指标元组字面 unparse（_RATIO_METRICS 12 / _COUNT 1 / _SUCCESS 1）
- 源码补强（values = [ ×2 / if values: ×2 / macro = None / successes = sum / dependencies·timestamp 行）
- AST 补强（aggregate 8 个下标赋值（4 段 + 4 内层）/ build_devset 6 键字面 / dv AnnAssign）
- forbidden tokens 第一百八十八批
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

import evaluation.report as report_mod
from evaluation.metrics import compute_automatic_metrics
from evaluation.report import (
    _COUNT_METRICS,
    _RATIO_METRICS,
    _SUCCESS_BOOL_METRICS,
    aggregate_summary,
    build_provenance,
    get_git_provenance,
)


# ---------- 真实 compute 输出聚合 ----------

def test_aggregate_real_failed_metrics_batch53():
    m = compute_automatic_metrics(None, None, "pdf", None)
    per_doc = [{"doc_id": f"d{i}", "metrics": m} for i in range(2)]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 2, "rate": 0.0,
    }
    for name in _RATIO_METRICS:
        entry = out["ratio_macro_averages"][name]
        assert entry == {"macro_average": None, "participating_docs": 0,
                         "not_evaluated": 2}, name
    assert out["silent_drop_total"] is None


def test_aggregate_real_success_metrics_batch53(monkeypatch):
    import evaluation.schema_validation as sv_mod
    monkeypatch.setattr(sv_mod, "document_passes_schema", lambda d: True)
    doc = {
        "elements": [{"type": "paragraph", "content": "x",
                      "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    out = aggregate_summary([{"doc_id": "d1", "metrics": m}])
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0
    assert out["counts"]["element_count_total"] == {"sum": 1, "participating_docs": 1}


# ---------- 0 值参与 ----------

def test_counts_zero_value_participates_batch53():
    out = aggregate_summary([{"doc_id": "a", "metrics": {
        "element_count_total": {"value": 0, "reason": None}}}])
    assert out["counts"]["element_count_total"] == {"sum": 0, "participating_docs": 1}


def test_ratio_zero_value_participates_batch53():
    out = aggregate_summary([{"doc_id": "a", "metrics": {
        "pdf_locator_valid_ratio": {"value": 0.0, "reason": None}}}])
    entry = out["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert entry == {"macro_average": 0.0, "participating_docs": 1,
                     "not_evaluated": 0}


# ---------- 精确分数与不变量 ----------

def test_success_rate_exact_third_batch53():
    docs = [
        {"doc_id": "a", "metrics": {"pipeline_success": {"value": True, "reason": None}}},
        {"doc_id": "b", "metrics": {"pipeline_success": {"value": False, "reason": None}}},
        {"doc_id": "c", "metrics": {"pipeline_success": {"value": False, "reason": None}}},
    ]
    assert aggregate_summary(docs)["success_rates"]["pipeline_success"]["rate"] == \
        pytest.approx(1 / 3)


def test_participating_plus_not_evaluated_invariant_batch53():
    docs = [
        {"doc_id": "a", "metrics": {"pdf_locator_valid_ratio": {"value": 0.5, "reason": None},
                                    "schema_valid": {"value": True, "reason": None}}},
        {"doc_id": "b", "metrics": {}},
    ]
    out = aggregate_summary(docs)["ratio_macro_averages"]
    for name in _RATIO_METRICS:
        entry = out[name]
        assert entry["participating_docs"] + entry["not_evaluated"] == 2, name


# ---------- build_provenance 数值强制转换 ----------

def test_provenance_max_chars_float_truncated_batch53(monkeypatch):
    monkeypatch.setattr(report_mod, "get_git_provenance",
                        lambda r: {"git_commit": None, "git_dirty": True})
    monkeypatch.setattr(report_mod, "get_dependency_versions", lambda: {})
    out = build_provenance(Path("."), "fallback", 7.9, None)
    assert out["max_chars"] == 7  # int() 截断（现状记录）


def test_provenance_max_chars_str_coerced_batch53(monkeypatch):
    monkeypatch.setattr(report_mod, "get_git_provenance",
                        lambda r: {"git_commit": None, "git_dirty": True})
    monkeypatch.setattr(report_mod, "get_dependency_versions", lambda: {})
    out = build_provenance(Path("."), "fallback", "800", None)
    assert out["max_chars"] == 800


# ---------- 真实 git 运行 ----------

def test_git_provenance_real_repo_batch53():
    root = Path(report_mod.__file__).resolve().parent.parent
    out = get_git_provenance(root)
    assert set(out.keys()) == {"git_commit", "git_dirty"}
    assert out["git_commit"] is None or re.fullmatch(r"[0-9a-f]{40}", out["git_commit"])
    assert isinstance(out["git_dirty"], bool)


# ---------- 指标元组字面 ----------

def test_metric_tuple_literals_batch53():
    tree = ast.parse(inspect.getsource(report_mod))
    unparsed = {n.targets[0].id: ast.unparse(n) for n in tree.body
                if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id.startswith("_")}
    assert unparsed["_COUNT_METRICS"] == "_COUNT_METRICS = ('element_count_total',)"
    assert unparsed["_SUCCESS_BOOL_METRICS"] == \
        "_SUCCESS_BOOL_METRICS = ('pipeline_success',)"
    assert len(_RATIO_METRICS) == 12


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(report_mod)


def test_source_values_listcount_batch53():
    src = _src()
    assert src.count("values = [") == 2
    assert src.count("if values:") == 2
    assert "macro = None" in src


def test_source_successes_sum_batch53():
    assert "successes = sum(" in _src()


def test_source_provenance_fields_batch53():
    src = _src()
    assert '"dependencies": get_dependency_versions(),' in src
    assert '"run_timestamp_iso": datetime.now().astimezone().isoformat(),' in src


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(report_mod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def test_ast_aggregate_subscript_assigns_batch53():
    subs = [ast.unparse(n.targets[0]) for n in ast.walk(_func("aggregate_summary"))
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Subscript)]
    assert subs[:4] == ["summary['counts']", "summary['success_rates']",
                        "summary['ratio_macro_averages']",
                        "summary['silent_drop_total']"]
    assert sorted(subs[4:]) == ["counts[name]", "counts[name]",
                                "ratio_avgs[name]", "success_rates[name]"]


def test_ast_devset_six_dict_keys_batch53():
    ret = [n for n in ast.walk(_func("build_devset_section"))
           if isinstance(n, ast.Return)][0]
    assert [k.value for k in ret.value.keys] == [
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    ]


def test_ast_versions_annassign_batch53():
    anns = [ast.unparse(n) for n in ast.walk(_func("get_dependency_versions"))
            if isinstance(n, ast.AnnAssign)]
    assert anns == ["versions: dict[str, str | None] = {}"]


# ---------- forbidden tokens 第一百八十八批 ----------

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
