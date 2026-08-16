"""evaluation/report.py 第九十九轮 edges 测试（Round 711）。

补强 edges70 未触及的角度（第七十六批）。

新角度：
- aggregate ratio 细节（mixed None/值 → macro 只算参与 doc + not_evaluated 计 null / schema_valid True+False → macro 0.5 / 全 False → 0.0）
- counts 双 doc 求和精确形状 / silent_drop [2,null,3] → 5 / 全 0 → 0（非 None）
- summary 4 键顺序 / ratio_avgs 恰 12 键 == _RATIO_METRICS 顺序 / counts 恰 1 键 / success_rates 恰 1 键
- get_git_provenance 失败路径（rev-parse rc1 → commit None / status rc1 → dirty False / OSError → 双默认 None+True /
  rev-parse 空 stdout → None / 第二条命令抛异常 → commit 保留 + dirty True）
- build_provenance 全量（mock 双依赖 → 9 键顺序与值 / run_timestamp_iso 可 fromisoformat 解析 / max_chars int 化）
- build_devset_section stub manifest 直测（categories_covered 同一对象透传）
- get_dependency_versions mock importlib.metadata.version（单包 PackageNotFoundError → 该键 None）
- 源码补强（commit or None / dirty bool 表达式 / except 元组 / int(max_chars) / for pkg 三包 / not_eval / macro 公式 / rate 三元 / silent 三元）
- AST 补强（aggregate GeneratorExp 1 / commit 3 赋值 / dirty 3 赋值 / build_provenance 9 键字面 / dv 1 For+1 Try+2 handler）
- forbidden tokens 第一百八十一批
"""

from __future__ import annotations

import ast
import importlib.metadata
import inspect
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import evaluation.report as report_mod
from evaluation.report import (
    _RATIO_METRICS,
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


def _pd(doc_id: str, **metric_values) -> dict:
    return {
        "doc_id": doc_id,
        "metrics": {k: {"value": v, "reason": None} for k, v in metric_values.items()},
    }


# ---------- aggregate ratio 细节 ----------

def test_ratio_mixed_null_macro_participating_only_batch53():
    docs = [
        _pd("a", pdf_locator_valid_ratio=0.5),
        _pd("b", pdf_locator_valid_ratio=None),
        _pd("c", pdf_locator_valid_ratio=1.0),
    ]
    entry = aggregate_summary(docs)["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert entry == {"macro_average": pytest.approx(0.75),
                     "participating_docs": 2, "not_evaluated": 1}


def test_ratio_bool_values_in_macro_batch53():
    docs = [_pd("a", schema_valid=True), _pd("b", schema_valid=False)]
    entry = aggregate_summary(docs)["ratio_macro_averages"]["schema_valid"]
    assert entry["macro_average"] == pytest.approx(0.5)
    assert entry["participating_docs"] == 2
    assert entry["not_evaluated"] == 0


def test_ratio_all_false_macro_zero_batch53():
    docs = [_pd("a", text_preservation_equal=False)]
    entry = aggregate_summary(docs)["ratio_macro_averages"]["text_preservation_equal"]
    assert entry["macro_average"] == 0.0
    assert entry["participating_docs"] == 1


# ---------- counts / silent_drop ----------

def test_counts_two_docs_exact_shape_batch53():
    docs = [_pd("a", element_count_total=3), _pd("b", element_count_total=4)]
    out = aggregate_summary(docs)["counts"]
    assert out == {"element_count_total": {"sum": 7, "participating_docs": 2}}


def test_silent_drop_skips_null_batch53():
    docs = [
        _pd("a", silent_drop_count=2),
        _pd("b", silent_drop_count=None),
        _pd("c", silent_drop_count=3),
    ]
    assert aggregate_summary(docs)["silent_drop_total"] == 5


def test_silent_drop_all_zero_is_zero_batch53():
    docs = [_pd("a", silent_drop_count=0), _pd("b", silent_drop_count=0)]
    assert aggregate_summary(docs)["silent_drop_total"] == 0  # 非 None


# ---------- summary 结构 ----------

def test_summary_four_keys_order_batch53():
    assert list(aggregate_summary([]).keys()) == [
        "counts", "success_rates", "ratio_macro_averages", "silent_drop_total",
    ]


def test_ratio_avgs_twelve_keys_match_tuple_batch53():
    out = aggregate_summary([])
    assert list(out["ratio_macro_averages"].keys()) == list(_RATIO_METRICS)
    assert len(_RATIO_METRICS) == 12


def test_counts_and_success_single_keys_batch53():
    out = aggregate_summary([])
    assert list(out["counts"].keys()) == ["element_count_total"]
    assert list(out["success_rates"].keys()) == ["pipeline_success"]


# ---------- get_git_provenance 失败路径 ----------

def _resp(rc, stdout):
    r = MagicMock()
    r.returncode = rc
    r.stdout = stdout
    return r


def test_git_revparse_rc1_commit_none_batch53():
    def fake_run(cmd, **kw):
        return _resp(1, "") if cmd[1] == "rev-parse" else _resp(0, "")
    with patch.object(report_mod.subprocess, "run", side_effect=fake_run):
        assert get_git_provenance(Path_dot()) == {"git_commit": None, "git_dirty": False}


def Path_dot():
    from pathlib import Path
    return Path(".")


def test_git_status_rc1_dirty_false_batch53():
    def fake_run(cmd, **kw):
        return _resp(0, "abc\n") if cmd[1] == "rev-parse" else _resp(1, "")
    with patch.object(report_mod.subprocess, "run", side_effect=fake_run):
        out = get_git_provenance(Path_dot())
    assert out == {"git_commit": "abc", "git_dirty": False}


def test_git_oserror_defaults_batch53():
    def boom(cmd, **kw):
        raise OSError("no git")
    with patch.object(report_mod.subprocess, "run", side_effect=boom):
        assert get_git_provenance(Path_dot()) == {"git_commit": None, "git_dirty": True}


def test_git_second_command_crash_resets_commit_batch53():
    """except 块包住两条命令：第二条抛 OSError 会把 commit 也重置为 None。"""
    def fake_run(cmd, **kw):
        if cmd[1] == "rev-parse":
            return _resp(0, "dead\n")
        raise OSError("boom")
    with patch.object(report_mod.subprocess, "run", side_effect=fake_run):
        out = get_git_provenance(Path_dot())
    assert out == {"git_commit": None, "git_dirty": True}


def test_git_revparse_empty_stdout_none_batch53():
    def fake_run(cmd, **kw):
        return _resp(0, "\n") if cmd[1] == "rev-parse" else _resp(0, "")
    with patch.object(report_mod.subprocess, "run", side_effect=fake_run):
        out = get_git_provenance(Path_dot())
    assert out == {"git_commit": None, "git_dirty": False}


# ---------- build_provenance 全量 ----------

def test_build_provenance_nine_keys_batch53(monkeypatch):
    monkeypatch.setattr(report_mod, "get_git_provenance",
                        lambda root: {"git_commit": "c1", "git_dirty": False})
    monkeypatch.setattr(report_mod, "get_dependency_versions",
                        lambda: {"pdfplumber": "1.0"})
    out = build_provenance(Path_dot(), "kreuzberg", 800, None)
    assert list(out.keys()) == [
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    ]
    assert out["git_commit"] == "c1"
    assert out["git_dirty"] is False
    assert out["evaluator_version"] == "1.1"
    assert out["report_version"] == "1.1"
    assert out["parser_name"] == "kreuzberg"
    assert out["parser_version"] is None
    assert out["dependencies"] == {"pdfplumber": "1.0"}
    assert out["max_chars"] == 800
    assert out["max_chars"] == int(800)


def test_build_provenance_timestamp_parseable_batch53(monkeypatch):
    monkeypatch.setattr(report_mod, "get_git_provenance",
                        lambda root: {"git_commit": None, "git_dirty": True})
    monkeypatch.setattr(report_mod, "get_dependency_versions", lambda: {})
    out = build_provenance(Path_dot(), "fallback", 500, "2.0")
    ts = datetime.fromisoformat(out["run_timestamp_iso"])
    assert ts.tzinfo is not None
    assert out["parser_version"] == "2.0"
    assert out["max_chars"] == 500


# ---------- build_devset_section stub ----------

def test_devset_section_stub_passthrough_batch53():
    cats = ["contracts"]
    m = SimpleNamespace(devset_status="incomplete", file_count=3,
                        content_group_count=2, pdf_count=2, docx_count=1,
                        categories_covered=cats)
    out = build_devset_section(m)
    assert out == {"status": "incomplete", "file_count": 3,
                   "content_group_count": 2, "pdf_count": 2, "docx_count": 1,
                   "categories_covered": cats}
    assert out["categories_covered"] is cats  # 同一对象透传


# ---------- get_dependency_versions mock ----------

def test_dependency_versions_one_missing_batch53(monkeypatch):
    def fake_version(pkg):
        if pkg == "python-docx":
            raise importlib.metadata.PackageNotFoundError(pkg)
        return "1.2.3"

    monkeypatch.setattr(importlib.metadata, "version", fake_version)
    out = get_dependency_versions()
    assert out == {"pdfplumber": "1.2.3", "python-docx": None, "pypdfium2": "1.2.3"}


def test_dependency_versions_all_same_batch53(monkeypatch):
    monkeypatch.setattr(importlib.metadata, "version", lambda pkg: "9.9")
    assert get_dependency_versions() == {
        "pdfplumber": "9.9", "python-docx": "9.9", "pypdfium2": "9.9",
    }


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(report_mod)


def test_source_commit_or_none_batch53():
    assert "commit = r.stdout.strip() or None" in _src()


def test_source_dirty_bool_expr_batch53():
    assert "dirty = bool(r2.returncode == 0 and r2.stdout.strip())" in _src()


def test_source_except_tuple_batch53():
    assert "except (OSError, subprocess.SubprocessError):" in _src()


def test_source_int_max_chars_batch53():
    assert '"max_chars": int(max_chars),' in _src()


def test_source_for_pkg_three_batch53():
    assert 'for pkg in ("pdfplumber", "python-docx", "pypdfium2"):' in _src()


def test_source_aggregate_formulas_batch53():
    src = _src()
    assert "not_eval = len(per_doc_results) - len(values)" in src
    assert "macro = sum(values) / len(values)" in src
    assert "rate = (successes / total) if total else None" in src
    assert 'summary["silent_drop_total"] = sum(silent_vals) if silent_vals else None' in src


def test_source_timeout_ten_twice_batch53():
    assert _src().count("timeout=10") == 2


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(report_mod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _assigns(func, var: str) -> list[str]:
    out = []
    for n in ast.walk(func):
        if isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == var for t in n.targets):
            out.append(ast.unparse(n))
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) \
                and n.target.id == var:
            out.append(ast.unparse(n))
    return out


def test_ast_aggregate_one_genexp_batch53():
    f = _func("aggregate_summary")
    genexps = [n for n in ast.walk(f) if isinstance(n, ast.GeneratorExp)]
    assert len(genexps) == 1


def test_ast_commit_three_assigns_batch53():
    assert _assigns(_func("get_git_provenance"), "commit") == [
        "commit: str | None = None",
        "commit = r.stdout.strip() or None",
        "commit = None",
    ]


def test_ast_dirty_three_assigns_batch53():
    assert _assigns(_func("get_git_provenance"), "dirty") == [
        "dirty: bool = True",
        "dirty = bool(r2.returncode == 0 and r2.stdout.strip())",
        "dirty = True",
    ]


def test_ast_build_provenance_nine_dict_keys_batch53():
    f = _func("build_provenance")
    ret = [n for n in ast.walk(f) if isinstance(n, ast.Return)][0]
    keys = [k.value for k in ret.value.keys]
    assert keys == ["git_commit", "git_dirty", "evaluator_version",
                    "report_version", "parser_name", "parser_version",
                    "dependencies", "max_chars", "run_timestamp_iso"]


def test_ast_dependency_versions_structure_batch53():
    f = _func("get_dependency_versions")
    import collections
    c = collections.Counter(type(n).__name__ for n in ast.walk(f))
    assert c["For"] == 1
    assert c["Try"] == 1
    assert c["ExceptHandler"] == 2


# ---------- forbidden tokens 第一百八十一批 ----------

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
