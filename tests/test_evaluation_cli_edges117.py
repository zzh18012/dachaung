"""evaluation/cli.py 第四百零二轮 edges 测试（Round 958）。

补强 edges116 未触及的角度（第三百三十四批，probe 实证）。

新角度：
- run 四条错误出口全矩阵：清单 Schema 失败 → rc 1
  "清单加载失败"；run_evaluation 抛 EvalSchemaError →
  rc 1 "生成的报告未通过 Schema 校验"；validate_file
  抛 → rc 1 "报告自校验失败"
- inspect-doc：文件不存在 → rc 2 "文档不存在"；非法
  JSON → rc 1 "JSON 解析失败"
- validate-report 非法 JSON → rc 1 "JSON 解析失败"
- _format_metric 字符串值（error_code "E_PARSE"）与
  int 值（element_count_total 5）都走通用分支：
  "  {name:36} {value}  (ok)"（reason None → ok）
- forbidden tokens 第四百二十八批（open 1）
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _format_metric, main
from evaluation.schema import EvalSchemaError


def _mk_manifest(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{"doc_id": "d1", "path": "samples/a.pdf",
                       "source_type": "pdf"}]}), encoding="utf-8")
    return f


# ---------- run 错误出口矩阵 ----------

def test_run_manifest_schema_fail_batch156(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"manifest_version": "1.0"}),
                   encoding="utf-8")
    rc = main(["run", "--manifest", str(bad), "--output",
               str(tmp_path / "o.json")])
    assert rc == 1
    err = capsys.readouterr().err
    assert err.startswith("[ERROR] 清单加载失败: Schema "
                          "'manifest.schema.")


def test_run_report_schema_fail_batch156(tmp_path, capsys):
    m = _mk_manifest(tmp_path)
    with patch.object(cli_mod, "run_evaluation",
                      side_effect=EvalSchemaError("boom")):
        rc = main(["run", "--manifest", str(m), "--output",
                   str(tmp_path / "o.json")])
    assert rc == 1
    assert capsys.readouterr().err.strip() == \
        "[ERROR] 生成的报告未通过 Schema 校验: boom"


def test_run_self_validate_fail_batch156(tmp_path, capsys):
    m = _mk_manifest(tmp_path)
    with patch.object(cli_mod, "run_evaluation",
                      return_value={"per_doc": [],
                                    "devset": {}}), \
         patch.object(cli_mod, "validate_file",
                      side_effect=EvalSchemaError("bad report")):
        rc = main(["run", "--manifest", str(m), "--output",
                   str(tmp_path / "o.json")])
    assert rc == 1
    assert capsys.readouterr().err.strip() == \
        "[ERROR] 报告自校验失败: bad report"


# ---------- inspect-doc 出口 ----------

def test_inspect_missing_file_batch156(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "nope.json")])
    assert rc == 2
    assert capsys.readouterr().err.strip() == \
        f"[ERROR] 文档不存在: {tmp_path / 'nope.json'}"


def test_inspect_bad_json_batch156(tmp_path, capsys):
    f = tmp_path / "bj.json"
    f.write_text("{oops", encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 1
    assert capsys.readouterr().err.startswith(
        "[ERROR] JSON 解析失败: ")


# ---------- validate-report 非法 JSON ----------

def test_validate_report_bad_json_batch156(tmp_path, capsys):
    f = tmp_path / "vr.json"
    f.write_text("{oops", encoding="utf-8")
    rc = main(["validate-report", str(f)])
    assert rc == 1
    assert capsys.readouterr().err.startswith(
        "[ERROR] JSON 解析失败: ")


# ---------- _format_metric 字符串/int ----------

def test_format_metric_string_value_batch156():
    assert _format_metric(
        "error_code", {"value": "E_PARSE", "reason": None}
    ) == "  " + "error_code".ljust(36) + " E_PARSE  (ok)"


def test_format_metric_int_value_batch156():
    assert _format_metric(
        "element_count_total", {"value": 5, "reason": None}
    ) == "  " + "element_count_total".ljust(36) + " 5  (ok)"


def test_format_metric_string_with_reason_batch156():
    out = _format_metric(
        "error_code", {"value": None, "reason": "pipeline_failed"})
    assert out == "  " + "error_code".ljust(36) + \
        " null  (pipeline_failed)"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch156():
    src = _src()
    assert 'print(f"[ERROR] 清单加载失败: {e}", file=sys.stderr)' in src
    assert 'print(f"[ERROR] 生成的报告未通过 Schema 校验: {e}", file=sys.stderr)' in src
    assert 'print(f"[ERROR] 报告自校验失败: {e}", file=sys.stderr)' in src
    assert 'print(f"[ERROR] 文档不存在: {input_path}", file=sys.stderr)' in src


# ---------- forbidden tokens 第四百二十八批 ----------

def test_source_no_eval_batch156():
    assert "eval(" not in _src()


def test_source_no_exec_batch156():
    assert "exec(" not in _src()


def test_source_no_compile_batch156():
    assert "compile(" not in _src()


def test_source_no_globals_batch156():
    assert "globals(" not in _src()


def test_source_no_locals_batch156():
    assert "locals(" not in _src()


def test_source_no_os_system_batch156():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch156():
    assert "subprocess" not in _src()


def test_source_no_popen_batch156():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch156():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch156():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch156():
    assert "socket" not in _src()


def test_source_no_requests_batch156():
    assert "requests" not in _src()


def test_source_no_urllib_batch156():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch156():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch156():
    assert "yield" not in _src()


def test_source_no_async_await_batch156():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch156():
    assert _src().count("open(") == 1
