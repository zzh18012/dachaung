"""evaluation/cli.py 第四百零九轮 edges 测试（Round 965）。

补强 edges117 未触及的角度（第三百四十一批，probe 实证）。

新角度：
- --parser 非法选项 "kreutzberg" → argparse SystemExit
  rc 2、stderr 含 "kreutzberg"
- inspect-doc 缺 source_type → "unknown"：pdf/docx
  locator 双 null（not_pdf_document /
  not_docx_document）、source 行 "?  type=unknown"
- _format_metric 浮点恒 4 位小数（1/3 → 0.3333、
  1.0 → 1.0000）
- _format_metric dict 值按 items 排序渲染
  （{paragraph:2, heading:1} → "heading=1,
  paragraph=2"）
- forbidden tokens 第四百三十五批（open 1）
"""

from __future__ import annotations

import inspect
import json

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _format_metric, main


# ---------- 非法 parser 选项 ----------

def test_invalid_parser_choice_batch163(tmp_path, capsys):
    with pytest.raises(SystemExit) as ei:
        main(["run", "--manifest", str(tmp_path / "m.json"),
              "--output", str(tmp_path / "o.json"),
              "--parser", "kreutzberg"])
    assert ei.value.code == 2
    assert "kreutzberg" in capsys.readouterr().err


# ---------- 缺 source_type ----------

def test_missing_source_type_unknown_batch163(tmp_path, capsys):
    f = tmp_path / "doc.json"
    f.write_text(json.dumps(
        {"chunks": [{"text": "AB"}]}), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert [ln for ln in lines
            if ln.startswith("source:")][0] == \
        "source:      ?  type=unknown"
    assert "  " + "pdf_locator_valid_ratio".ljust(36) + \
        " null  (not_pdf_document)" in lines
    assert "  " + "docx_locator_valid_ratio".ljust(36) + \
        " null  (not_docx_document)" in lines


# ---------- 浮点 4 位小数 ----------

def test_format_metric_float_four_decimals_batch163():
    assert _format_metric(
        "x", {"value": 1 / 3, "reason": None}) == \
        "  " + "x".ljust(36) + " 0.3333  (ok)"
    assert _format_metric(
        "x", {"value": 1.0, "reason": None}) == \
        "  " + "x".ljust(36) + " 1.0000  (ok)"


# ---------- dict 值排序渲染 ----------

def test_format_metric_dict_sorted_items_batch163():
    assert _format_metric(
        "element_count_by_type",
        {"value": {"paragraph": 2, "heading": 1},
         "reason": None}) == \
        "  " + "element_count_by_type".ljust(36) + \
        " heading=1, paragraph=2  (ok)"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch163():
    src = _src()
    assert 'choices=("fallback", "kreuzberg"),' in src
    assert 'source_type = doc.get("source_type", "unknown")' in src
    assert "return f\"  {name:36} {value:.4f}  ({reason or 'ok'})\"" in src
    assert "items = \", \".join(f\"{k}={v}\" for k, v in sorted(value.items()))" in src


# ---------- forbidden tokens 第四百三十五批 ----------

def test_source_no_eval_batch163():
    assert "eval(" not in _src()


def test_source_no_exec_batch163():
    assert "exec(" not in _src()


def test_source_no_compile_batch163():
    assert "compile(" not in _src()


def test_source_no_globals_batch163():
    assert "globals(" not in _src()


def test_source_no_locals_batch163():
    assert "locals(" not in _src()


def test_source_no_os_system_batch163():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch163():
    assert "subprocess" not in _src()


def test_source_no_popen_batch163():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch163():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch163():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch163():
    assert "socket" not in _src()


def test_source_no_requests_batch163():
    assert "requests" not in _src()


def test_source_no_urllib_batch163():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch163():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch163():
    assert "yield" not in _src()


def test_source_no_async_await_batch163():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch163():
    assert _src().count("open(") == 1
