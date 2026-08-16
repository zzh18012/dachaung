"""evaluation/report.py 第二百零五轮 edges 测试（Round 753）。

补强 edges74-76 未触及的角度（第一百一十八批）。

新角度：
- porcelain stdout 仅空白（"   \\n"）→ strip 后空 → dirty False
- rev-parse rc!=0 但 porcelain rc0 干净 → commit None + dirty False
  （commit 与 dirty 两路独立）
- subprocess 两次调用参数精确：["git","rev-parse","HEAD"] 与
  ["git","status","--porcelain"]、cwd=str(project_root) 透传
- ratio 值 True（bool）参与求和 → macro 1.0（与 jsonschema boolean
  严格性对照：聚合层不拦 bool）
- success 值 1（int）→ `is True` 不成立 → success_count 0 rate 0.0
  （与 counts 的 bool 求和对照，三层 bool 语义各不相同）
- 空 per_doc 列表：summary 恰 4 键、counts sum None、rate None、
  ratio macro None 且 not_evaluated 0（分母 0）
- 未知指标名完全被忽略（zzz 不出现在任何聚合里）
- metrics[name] 为 None → AttributeError；行缺 metrics 键 → KeyError
- build_devset_section 与 stub manifest 六键精确映射
- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 精确元组
- forbidden tokens 第二百二十三批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.report as report_mod
from evaluation.report import (
    aggregate_summary,
    build_devset_section,
    get_git_provenance,
)


class _R:
    def __init__(self, rc, out):
        self.returncode = rc
        self.stdout = out


# ---------- git 两路独立 ----------

def test_porcelain_whitespace_only_not_dirty_batch54(monkeypatch):
    monkeypatch.setattr(report_mod.subprocess, "run",
                        lambda cmd, **k: (_R(0, "abc\n")
                                          if cmd[1] == "rev-parse"
                                          else _R(0, "   \n")))
    assert get_git_provenance(".") == {"git_commit": "abc",
                                       "git_dirty": False}


def test_revparse_fail_porcelain_clean_batch54(monkeypatch):
    monkeypatch.setattr(report_mod.subprocess, "run",
                        lambda cmd, **k: (_R(128, "")
                                          if cmd[1] == "rev-parse"
                                          else _R(0, "")))
    assert get_git_provenance(".") == {"git_commit": None,
                                       "git_dirty": False}


def test_subprocess_call_args_exact_batch54(monkeypatch):
    calls = []

    def fake(cmd, **k):
        calls.append((tuple(cmd), k.get("cwd")))
        return _R(0, "abc\n") if cmd[1] == "rev-parse" else _R(0, "")

    monkeypatch.setattr(report_mod.subprocess, "run", fake)
    get_git_provenance("ROOTX")
    assert calls == [
        (("git", "rev-parse", "HEAD"), "ROOTX"),
        (("git", "status", "--porcelain"), "ROOTX"),
    ]


# ---------- bool 三层语义 ----------

def test_ratio_bool_value_sums_batch54():
    s = aggregate_summary([{"metrics": {"schema_valid": {"value": True}}}])
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 1.0, "participating_docs": 1, "not_evaluated": 0}


def test_success_int_one_not_counted_batch54():
    s = aggregate_summary([{"metrics": {"pipeline_success": {"value": 1}}}])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 1, "rate": 0.0}


def test_success_bool_true_counted_batch54():
    s = aggregate_summary([{"metrics": {"pipeline_success": {"value": True}}}])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 1, "total": 1, "rate": 1.0}


# ---------- 空输入 ----------

def test_empty_per_doc_summary_shape_batch54():
    s = aggregate_summary([])
    assert list(s) == ["counts", "success_rates", "ratio_macro_averages",
                       "silent_drop_total"]
    assert s["counts"] == {"element_count_total": {"sum": None,
                                                   "participating_docs": 0}}
    assert s["silent_drop_total"] is None


def test_empty_per_doc_rate_none_and_ratio_none_batch54():
    s = aggregate_summary([])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 0, "rate": None}
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": None, "participating_docs": 0, "not_evaluated": 0}


# ---------- 未知指标忽略 ----------

def test_unknown_metric_fully_ignored_batch54():
    s = aggregate_summary([{"metrics": {"zzz": {"value": 1}}}])
    assert "zzz" not in str(s)
    assert list(s) == ["counts", "success_rates", "ratio_macro_averages",
                       "silent_drop_total"]


# ---------- 未守卫输入 ----------

def test_metric_entry_none_attributeerror_batch54():
    with pytest.raises(AttributeError):
        aggregate_summary([{"metrics": {"element_count_total": None}}])


def test_row_missing_metrics_key_keyerror_batch54():
    with pytest.raises(KeyError):
        aggregate_summary([{"no_metrics": 1}])


# ---------- devset stub 映射 ----------

class _Manifest:
    devset_status = "incomplete"
    file_count = 2
    content_group_count = 1
    pdf_count = 1
    docx_count = 1
    categories_covered = ["a"]


def test_devset_section_six_keys_batch54():
    assert build_devset_section(_Manifest()) == {
        "status": "incomplete", "file_count": 2, "content_group_count": 1,
        "pdf_count": 1, "docx_count": 1, "categories_covered": ["a"]}


# ---------- 常量精确 ----------

def test_count_and_success_metric_tuples_batch54():
    assert report_mod._COUNT_METRICS == ("element_count_total",)
    assert report_mod._SUCCESS_BOOL_METRICS == ("pipeline_success",)


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(report_mod)


def test_source_is_true_identity_check_batch54():
    src = _src()
    assert ".get(\"value\") is True" in src
    assert "r2.stdout.strip())" in src
    assert 'cwd=str(project_root)' in src


# ---------- forbidden tokens 第二百二十三批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_subprocess_only_in_git_batch54():
    # subprocess 仅出现在 git provenance；无其他外部调用面
    src = _src()
    assert src.count("subprocess.run") == 2
