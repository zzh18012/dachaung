"""evaluation/report.py 第三百三十七轮 edges 测试（Round 893）。

补强 edges96 未触及的角度（第二百六十九批，probe 实证）。

新角度：
- get_dependency_versions 键序锁定 + 混合缺失（pypdfium2 None，
  其余有值）
- get_git_provenance 两条命令精确序列 + kwargs（cwd/timeout 10）
- rev-parse rc=1 而 porcelain 干净 → commit None + dirty False
- rev-parse rc=0 但 stdout 空 → commit None（or None 分支）
- counts 浮点求和 3.5 透传
- success 分母 = 全部文档（缺 metric 键也计入 total）
- ratio 值为 bool（True/False 非 None）参与 macro average → 0.5
- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元组常量
- build_devset_section 键序六项
- build_provenance max_chars 字符串 "5" → int 5；
  run_timestamp_iso 可 fromisoformat 回解析且带时区
- forbidden tokens 第三百六十三批（report 变体：subprocess.run 计 2）
"""

from __future__ import annotations

import inspect
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import evaluation.report as report_mod
from evaluation.report import (
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


def _pd(metrics):
    return {"metrics": metrics}


def _m(name, value):
    return {name: {"value": value, "reason": None}}


class _FakeManifest:
    devset_status = "incomplete"
    file_count = 3
    content_group_count = 2
    pdf_count = 2
    docx_count = 1
    categories_covered = ["a", "b"]


# ---------- dependency versions ----------

def test_dependency_versions_key_order_batch91():
    with patch("importlib.metadata.version", return_value="1.2.3"):
        v = get_dependency_versions()
    assert list(v) == ["pdfplumber", "python-docx", "pypdfium2"]
    assert v == {"pdfplumber": "1.2.3", "python-docx": "1.2.3",
                 "pypdfium2": "1.2.3"}


def test_dependency_versions_mixed_none_batch91():
    import importlib.metadata as im

    def fake_version(pkg):
        if pkg == "pypdfium2":
            raise im.PackageNotFoundError("pypdfium2")
        return "9.9"

    with patch("importlib.metadata.version", side_effect=fake_version):
        v = get_dependency_versions()
    assert v["pdfplumber"] == "9.9"
    assert v["python-docx"] == "9.9"
    assert v["pypdfium2"] is None


# ---------- git 命令序列 ----------

def test_git_provenance_command_sequence_batch91(tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((list(cmd), kwargs.get("cwd"),
                      kwargs.get("timeout")))
        if cmd[1] == "rev-parse":
            return SimpleNamespace(returncode=0, stdout="abc" * 13 + "\n")
        return SimpleNamespace(returncode=0, stdout="")

    with patch.object(report_mod.subprocess, "run",
                      side_effect=fake_run):
        out = get_git_provenance(tmp_path)
    assert out == {"git_commit": "abc" * 13, "git_dirty": False}
    assert calls[0][0] == ["git", "rev-parse", "HEAD"]
    assert calls[1][0] == ["git", "status", "--porcelain"]
    assert calls[0][1] == str(tmp_path)
    assert calls[0][2] == 10 and calls[1][2] == 10


def test_git_provenance_revparse_rc1_clean_batch91(tmp_path):
    runs = [SimpleNamespace(returncode=1, stdout=""),
            SimpleNamespace(returncode=0, stdout="")]
    with patch.object(report_mod.subprocess, "run",
                      side_effect=runs):
        out = get_git_provenance(tmp_path)
    assert out == {"git_commit": None, "git_dirty": False}


def test_git_provenance_empty_commit_stdout_batch91(tmp_path):
    runs = [SimpleNamespace(returncode=0, stdout="   \n"),
            SimpleNamespace(returncode=0, stdout=" M t.txt\n")]
    with patch.object(report_mod.subprocess, "run",
                      side_effect=runs):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None  # stdout.strip() 为空 → or None
    assert out["git_dirty"] is True


# ---------- 聚合补强 ----------

def test_counts_float_sum_batch91():
    s = aggregate_summary([
        _pd(_m("element_count_total", 2.5)),
        _pd(_m("element_count_total", 1)),
    ])
    assert s["counts"]["element_count_total"] == {
        "sum": 3.5, "participating_docs": 2}


def test_success_denominator_all_docs_batch91():
    s = aggregate_summary([
        _pd(_m("pipeline_success", True)),
        _pd({}),  # 完全缺 metric 键
    ])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 1, "total": 2, "rate": 0.5}


def test_ratio_bool_values_participate_batch91():
    s = aggregate_summary([
        _pd(_m("schema_valid", True)),
        _pd(_m("schema_valid", False)),
    ])
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 0.5, "participating_docs": 2,
        "not_evaluated": 0}


def test_count_success_metric_tuples_batch91():
    assert report_mod._COUNT_METRICS == ("element_count_total",)
    assert report_mod._SUCCESS_BOOL_METRICS == ("pipeline_success",)


# ---------- devset 段 ----------

def test_devset_section_key_order_batch91():
    d = build_devset_section(_FakeManifest())
    assert list(d) == ["status", "file_count", "content_group_count",
                       "pdf_count", "docx_count", "categories_covered"]
    assert d["status"] == "incomplete"
    assert d["content_group_count"] == 2


# ---------- provenance 补强 ----------

def test_build_provenance_max_chars_str_coerced_batch91(tmp_path):
    with patch.object(report_mod, "get_git_provenance",
                      return_value={"git_commit": None,
                                    "git_dirty": False}), \
         patch.object(report_mod, "get_dependency_versions",
                      return_value={}):
        p = build_provenance(tmp_path, "fallback", "5", None)
    assert p["max_chars"] == 5
    assert isinstance(p["max_chars"], int)


def test_run_timestamp_roundtrip_batch91(tmp_path):
    with patch.object(report_mod, "get_git_provenance",
                      return_value={"git_commit": None,
                                    "git_dirty": False}), \
         patch.object(report_mod, "get_dependency_versions",
                      return_value={}):
        p = build_provenance(tmp_path, "fallback", 800, "7.7")
    ts = datetime.fromisoformat(p["run_timestamp_iso"])
    assert ts.tzinfo is not None
    assert p["parser_version"] == "7.7"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch91():
    src = _src()
    assert "r.stdout.strip() or None" in src
    assert '"max_chars": int(max_chars),' in src
    assert "datetime.now().astimezone().isoformat()" in src
    assert "not_eval = len(per_doc_results) - len(values)" in src


# ---------- forbidden tokens 第三百六十三批（report 变体）----------

def test_source_no_eval_batch91():
    assert "eval(" not in _src()


def test_source_no_exec_batch91():
    assert "exec(" not in _src()


def test_source_no_compile_batch91():
    assert "compile(" not in _src()


def test_source_no_globals_batch91():
    assert "globals(" not in _src()


def test_source_no_locals_batch91():
    assert "locals(" not in _src()


def test_source_no_os_system_batch91():
    assert "os.system" not in _src()


def test_source_subprocess_run_count_is_2_batch91():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch91():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch91():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch91():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch91():
    assert "socket" not in _src()


def test_source_no_requests_batch91():
    assert "requests" not in _src()


def test_source_no_urllib_batch91():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch91():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch91():
    assert "yield" not in _src()


def test_source_no_async_await_batch91():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch91():
    assert "open(" not in _src()
