"""evaluation/report.py 第四百一十四轮 edges 测试（Round 970）。

补强 edges107 未触及的角度（第三百四十六批，probe 实证）。

新角度：
- _RATIO_METRICS 全量 12 项精确有序清单（第一次整表
  锁定）：schema_valid → pdf/docx locator → image →
  chunk_ref → text_equal → text P/R → heading →
  chunk_boundary P/R/F1
- 依赖版本号格式：三包均为 x.y.z 数字点分（正则
  fullmatch 通过）
- forbidden tokens 第四百四十批（open 0 +
  subprocess.run 恰 2）
"""

from __future__ import annotations

import inspect
import re

import evaluation.report as rpt
from evaluation.report import get_dependency_versions


# ---------- 全量 ratio 清单 ----------

def test_ratio_metrics_full_tuple_batch168():
    assert rpt._RATIO_METRICS == (
        "schema_valid",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        "heading_boundary_compliance",
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    )


# ---------- 依赖版本格式 ----------

def test_dependency_version_format_batch168():
    d = get_dependency_versions()
    assert list(d) == ["pdfplumber", "python-docx",
                       "pypdfium2"]
    for pkg, ver in d.items():
        assert isinstance(ver, str), pkg
        assert re.fullmatch(r"[0-9]+(\.[0-9]+)+", ver), \
            (pkg, ver)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(rpt)


def test_source_key_lines_batch168():
    src = _src()
    assert "_RATIO_METRICS = (" in src
    assert 'if commit = r.stdout.strip() or None:' not in src
    assert 'commit = r.stdout.strip() or None' in src
    assert "import importlib.metadata" in src


# ---------- forbidden tokens 第四百四十批 ----------

def test_source_no_eval_batch168():
    assert "eval(" not in _src()


def test_source_no_exec_batch168():
    assert "exec(" not in _src()


def test_source_no_compile_batch168():
    assert "compile(" not in _src()


def test_source_no_globals_batch168():
    assert "globals(" not in _src()


def test_source_no_locals_batch168():
    assert "locals(" not in _src()


def test_source_no_os_system_batch168():
    assert "os.system" not in _src()


def test_source_no_popen_batch168():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch168():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch168():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch168():
    assert "socket" not in _src()


def test_source_no_requests_batch168():
    assert "requests" not in _src()


def test_source_no_urllib_batch168():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch168():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch168():
    assert "yield" not in _src()


def test_source_no_async_await_batch168():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch168():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch168():
    assert _src().count("subprocess.run") == 2
