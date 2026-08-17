"""evaluation/cli.py 第二百二十轮 edges 测试（Round 776）。

补强 edges88-90 未触及的角度（第一百四十批）。

新角度：
- inspect-doc metrics 四组排序端到端：bool 组 → 数值组 → dict 组 →
  null 组（null 组内按字母序，error_code 的 reason None 渲染
  "(None)"）
- _tolerance_chars 内部记录泄漏进 inspect-doc 数值组
  （underscore 前缀键照样打印，chunk_boundary_prf update 进
  metrics 后未剥离，现状记录）
- counts 行非零变体："counts:      elements=2 chunks=1"
- parser 行取 doc 字段："parser:      kreuzberg v4.10.2"
- 相对路径原样打印：chdir 后传 "rel.json" → "file:        rel.json"
- run --max-chars -5 / --tolerance-chars 0 原样透传
  （argparse type=int 不做范围校验）
- inspect-doc BOM → rc 1 "[ERROR] JSON 解析失败: Unexpected UTF-8
  BOM"（与 R762 的 validate-report BOM 对照）
- inspect-doc 传目录 → rc 2 "文档不存在"（is_file False）
- forbidden tokens 第二百四十六批
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import main


def _cap():
    out, err = io.StringIO(), io.StringIO()
    return out, err, contextlib.redirect_stdout(out), \
        contextlib.redirect_stderr(err)


def _full_doc(tmp):
    df = tmp / "full.json"
    df.write_text(json.dumps({
        "document_id": "d", "source_type": "pdf",
        "parser_name": "fallback", "parser_version": "1.2",
        "source_path": "samples/a.pdf",
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "A"},
            {"element_id": "e2", "type": "heading", "content": "B"},
        ],
        "chunks": [{"text": "A B",
                    "source_element_ids": ["e1", "e2"]}],
    }), encoding="utf-8")
    return df


# ---------- metrics 四组排序 ----------

def test_inspect_metric_group_ordering_batch54(tmp_path):
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(_full_doc(tmp_path))])
    assert rc == 0
    lines = out.getvalue().splitlines()

    def idx(substr):
        return next(i for i, ln in enumerate(lines) if substr in ln)

    i_bool = idx("pipeline_success ")
    i_num = idx("_tolerance_chars ")
    i_dict = idx("element_count_by_type ")
    i_null = idx("docx_locator_valid_ratio ")
    assert i_bool < i_num < i_dict < i_null
    # null 组内 docx_locator_valid_ratio 排在 error_code 之前（字母序）
    assert i_null < idx("error_code ")
    assert "null  (None)" in lines[idx("error_code ")]


def test_inspect_internal_tolerance_leaks_batch54(tmp_path):
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(_full_doc(tmp_path))])
    assert rc == 0
    lines = out.getvalue().splitlines()
    assert ("  _tolerance_chars                     30  (ok)") in lines


# ---------- header 行 ----------

def test_inspect_counts_nonzero_batch54(tmp_path):
    out, err, co, ce = _cap()
    with co, ce:
        main(["inspect-doc", str(_full_doc(tmp_path))])
    assert "counts:      elements=2 chunks=1" \
        in out.getvalue().splitlines()


def test_inspect_parser_line_from_doc_batch54(tmp_path):
    df = tmp_path / "d.json"
    df.write_text(json.dumps({
        "document_id": "d", "source_type": "docx",
        "parser_name": "kreuzberg", "parser_version": "4.10.2",
        "elements": [], "chunks": []}), encoding="utf-8")
    out, err, co, ce = _cap()
    with co, ce:
        main(["inspect-doc", str(df)])
    assert "parser:      kreuzberg v4.10.2" \
        in out.getvalue().splitlines()


def test_inspect_relative_path_printed_as_is_batch54(tmp_path,
                                                     monkeypatch):
    df = tmp_path / "rel.json"
    df.write_text(json.dumps({"elements": [], "chunks": []}),
                  encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", "rel.json"])
    assert rc == 0
    assert out.getvalue().splitlines()[0] == "file:        rel.json"


# ---------- run 参数原样透传 ----------

def test_run_negative_values_passthrough_batch54(tmp_path):
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": []}), encoding="utf-8")
    capd = {}
    with patch.object(cli_mod, "run_evaluation",
                      lambda man, out, **k: capd.update(k)
                      or {"per_doc": [], "devset": {}}), \
            patch.object(cli_mod, "validate_file",
                         lambda p, s: None), \
            patch.object(cli_mod, "get_git_provenance",
                         lambda r: {"git_commit": None,
                                    "git_dirty": True}):
        out, err, co, ce = _cap()
        with co, ce:
            rc = main(["run", "--manifest", str(mf),
                       "--output", str(tmp_path / "r.json"),
                       "--max-chars", "-5",
                       "--tolerance-chars", "0"])
    assert rc == 0
    assert capd == {"parser_name": "fallback", "max_chars": -5,
                    "tolerance_chars": 0}


# ---------- inspect-doc 异常输入 ----------

def test_inspect_bom_rc1_batch54(tmp_path):
    bf = tmp_path / "bom.json"
    bf.write_bytes(b"\xef\xbb\xbf{}")
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(bf)])
    assert rc == 1
    assert err.getvalue().startswith(
        "[ERROR] JSON 解析失败: Unexpected UTF-8 BOM")


def test_inspect_directory_rc2_batch54(tmp_path):
    out, err, co, ce = _cap()
    with co, ce:
        rc = main(["inspect-doc", str(tmp_path)])
    assert rc == 2
    assert err.getvalue().startswith("[ERROR] 文档不存在: ")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_sort_key_and_print_batch54():
    src = _src()
    assert "return (3, name)" in src
    assert "sorted(metrics.keys(), key=_sort_key)" in src
    assert 'f"  {name:36} null  ({reason})"' in src


# ---------- forbidden tokens 第二百四十六批 ----------

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


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


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


def test_source_open_count_is_1_batch54():
    assert _src().count("open(") == 1
