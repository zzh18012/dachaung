"""evaluation/report.py 第四百轮 edges 测试（Round 956）。

补强 edges105 未触及的角度（第三百三十二批，probe 实证）。

新角度：
- counts 跳过 null：[5, None, 3] → {sum 8,
  participating_docs 2}
- 指标键整个缺失 = 等价 null：[无键, 7] → {sum 7,
  participating 1}
- bool True 参与 ratio macro 且按 1 计：[True, 0.5] →
  macro 0.75（schema_valid 真/假混浮点）
- 非 git 目录怪癖：rev-parse rc≠0 → commit None；status
  rc≠0 → dirty = bool(rc==0 and …) = False——非 git 目录
  反而自称"干净"（构造缺陷，锁定现状）
- build_devset_section 六键有序（接受任意带属性对象）
- run_timestamp_iso 可 fromisoformat 解析且带 tzinfo；
  evaluator_version/report_version 锁 1.1/1.1
- forbidden tokens 第四百二十六批（open 0 +
  subprocess.run 恰 2）
"""

from __future__ import annotations

import inspect
import tempfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import evaluation.report as rpt
from evaluation.report import (
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_git_provenance,
)


# ---------- counts 跳过 null ----------

def test_counts_skip_null_batch154():
    per = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {
            "value": None, "reason": "pf"}}},
        {"metrics": {"element_count_total": {"value": 3}}},
    ]
    assert aggregate_summary(per)["counts"][
        "element_count_total"] == {"sum": 8,
                                   "participating_docs": 2}


def test_counts_missing_key_equals_null_batch154():
    per = [
        {"metrics": {}},
        {"metrics": {"element_count_total": {"value": 7}}},
    ]
    assert aggregate_summary(per)["counts"][
        "element_count_total"] == {"sum": 7,
                                   "participating_docs": 1}


# ---------- bool True 按 1 计 ----------

def test_bool_true_counts_as_one_batch154():
    per = [
        {"metrics": {"schema_valid": {"value": True}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
    ]
    assert aggregate_summary(per)["ratio_macro_averages"][
        "schema_valid"] == {"macro_average": 0.75,
                            "participating_docs": 2,
                            "not_evaluated": 0}


# ---------- 非 git 目录怪癖 ----------

def test_non_git_dir_dirty_false_quirk_batch154():
    tmp = Path(tempfile.mkdtemp())
    assert get_git_provenance(tmp) == {"git_commit": None,
                                       "git_dirty": False}


# ---------- devset 六键有序 ----------

def test_devset_section_key_order_batch154():
    fake = SimpleNamespace(
        devset_status="incomplete", file_count=2,
        content_group_count=1, pdf_count=1, docx_count=1,
        categories_covered=["c1", "c2"])
    d = build_devset_section(fake)
    assert list(d) == ["status", "file_count",
                       "content_group_count", "pdf_count",
                       "docx_count", "categories_covered"]
    assert d == {"status": "incomplete", "file_count": 2,
                 "content_group_count": 1, "pdf_count": 1,
                 "docx_count": 1,
                 "categories_covered": ["c1", "c2"]}


# ---------- 时间戳与版本 ----------

def test_provenance_timestamp_and_versions_batch154():
    with patch.object(rpt, "get_git_provenance",
                      return_value={"git_commit": None,
                                    "git_dirty": True}):
        p = build_provenance(Path("."), "fallback", 800, None)
    dt = datetime.fromisoformat(p["run_timestamp_iso"])
    assert dt.tzinfo is not None
    assert p["evaluator_version"] == "1.1"
    assert p["report_version"] == "1.1"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(rpt)


def test_source_key_lines_batch154():
    src = _src()
    assert "dirty = bool(r2.returncode == 0 and r2.stdout.strip())" in src
    assert "r\"metrics\".get" not in src  # 防误写
    assert 'summary["counts"] = counts' in src
    assert "macro = sum(values) / len(values)" in src


# ---------- forbidden tokens 第四百二十六批 ----------

def test_source_no_eval_batch154():
    assert "eval(" not in _src()


def test_source_no_exec_batch154():
    assert "exec(" not in _src()


def test_source_no_compile_batch154():
    assert "compile(" not in _src()


def test_source_no_globals_batch154():
    assert "globals(" not in _src()


def test_source_no_locals_batch154():
    assert "locals(" not in _src()


def test_source_no_os_system_batch154():
    assert "os.system" not in _src()


def test_source_no_popen_batch154():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch154():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch154():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch154():
    assert "socket" not in _src()


def test_source_no_requests_batch154():
    assert "requests" not in _src()


def test_source_no_urllib_batch154():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch154():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch154():
    assert "yield" not in _src()


def test_source_no_async_await_batch154():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch154():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch154():
    assert _src().count("subprocess.run") == 2
