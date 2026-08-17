"""evaluation/cli.py 第三百六十轮 edges 测试（Round 916）。

补强 edges110 未触及的角度（第二百九十二批，probe 实证）。

新角度：
- run 成功输出完整 5 行块（含 devset 行五字段与
  git_commit 前 12 字符截断）
- run/validate-report 传目录 → 各自 rc 2 "清单不存在"/
  "报告不存在"；validate-report 传坏 JSON → rc 1
  "JSON 解析失败"
- inspect-doc 顶层 "elements": null → TypeError 未捕获
  （compute_automatic_metrics 的 get(key, []) 只救缺键，
  _run_inspect_doc 的 or [] 只护 counts 行、永远到不了）
- inspect-doc 非 UTF-8 → UnicodeDecodeError 未捕获
- _format_metric float 分支 {:.4f}；string 分支兜底行
- inspect 排序四组：bool→数值（_ 开头先排）→dict→null；
  error_code null 行 reason 原样 "(None)"（null 分支无
  or 'ok' 兜底）
- forbidden tokens 第三百八十六批
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _format_metric, main


# ---------- _format_metric float / string ----------

def test_format_metric_float_four_decimals_batch114():
    assert _format_metric("x", {"value": 2 / 3, "reason": None}) == (
        "  " + "x".ljust(36) + " 0.6667  (ok)")


def test_format_metric_string_fallback_batch114():
    assert _format_metric("error_code",
                          {"value": "E_PARSE", "reason": None}) == (
        "  " + "error_code".ljust(36) + " E_PARSE  (ok)")


# ---------- 目录与坏 JSON 输入 ----------

def test_run_manifest_directory_rc2_batch114(tmp_path, capsys):
    d = tmp_path / "mdir"
    d.mkdir()
    rc = main(["run", "--manifest", str(d),
               "--output", str(tmp_path / "o.json")])
    assert rc == 2
    err = capsys.readouterr().err
    assert err.startswith("[ERROR] 清单不存在: ")


def test_validate_report_directory_rc2_batch114(tmp_path, capsys):
    d = tmp_path / "adir"
    d.mkdir()
    rc = main(["validate-report", str(d)])
    assert rc == 2
    assert capsys.readouterr().err.startswith("[ERROR] 报告不存在: ")


def test_validate_report_bad_json_rc1_batch114(tmp_path, capsys):
    f = tmp_path / "r.json"
    f.write_text("not json", encoding="utf-8")
    rc = main(["validate-report", str(f)])
    assert rc == 1
    assert capsys.readouterr().err.startswith("[ERROR] JSON 解析失败: ")


# ---------- run 成功完整块 ----------

def test_run_success_full_block_batch114(tmp_path, capsys):
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "complete",
        "documents": []}), encoding="utf-8")
    fake = {
        "per_doc": [
            {"metrics": {"pipeline_success": {"value": True}}},
            {"metrics": {"pipeline_success": {"value": False}}},
        ],
        "devset": {"status": "complete", "file_count": 2,
                   "content_group_count": 2, "pdf_count": 1,
                   "docx_count": 1},
    }
    out = tmp_path / "o.json"
    with patch.object(cli_mod, "run_evaluation",
                      return_value=fake), \
         patch.object(cli_mod, "validate_file"), \
         patch.object(cli_mod, "get_git_provenance",
                      return_value={"git_commit": "abcdef1234567890",
                                    "git_dirty": False}):
        rc = main(["run", "--manifest", str(mf), "--output", str(out)])
    assert rc == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines == [
        f"[OK] 评测完成：{out}",
        "      documents=2（成功 1，失败 1）",
        "      devset_status=complete file_count=2 groups=2 "
        "pdf=1 docx=1",
        "      git_commit=abcdef123456 git_dirty=False",
    ]


# ---------- inspect-doc：elements null / 非 UTF-8 ----------

def test_inspect_elements_null_typeerror_batch114(tmp_path):
    f = tmp_path / "d.json"
    f.write_text(json.dumps({
        "document_id": "doc-1", "source_type": "pdf",
        "elements": None, "chunks": None}), encoding="utf-8")
    with pytest.raises(TypeError):
        main(["inspect-doc", str(f)])


def test_inspect_bad_encoding_unicode_error_batch114(tmp_path):
    f = tmp_path / "d.json"
    f.write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(UnicodeDecodeError):
        main(["inspect-doc", str(f)])


# ---------- inspect 排序四组 ----------

def test_inspect_group_order_with_dict_batch114(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(json.dumps({
        "document_id": "doc-1", "source_type": "pdf",
        "elements": [{"element_id": "e1", "type": "heading",
                      "content": "H"}],
        "chunks": [{"text": "H",
                    "source_element_ids": ["e1"]}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 0
    lines = capsys.readouterr().out.splitlines()
    metric = lines[lines.index("metrics:") + 1:]
    assert len(metric) == 21
    # bool 组
    assert [m.split()[0] for m in metric[:3]] == [
        "pipeline_success", "schema_valid", "text_preservation_equal"]
    # 数值组首个是 _tolerance_chars（下划线 95 排在小写前）
    assert metric[3] == "  " + "_tolerance_chars".ljust(36) + \
        " 30  (ok)"
    # dict 组独一行
    assert "  " + "element_count_by_type".ljust(36) + \
        " heading=1  (ok)" in metric
    # null 组：error_code 行 reason 原样 None
    assert "  " + "error_code".ljust(36) + " null  (None)" in metric
    assert "  " + "figure_caption_f1".ljust(36) + \
        " null  (parser_does_not_emit_relations)" in metric


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(cli_mod)


def test_source_key_lines_batch114():
    src = _src()
    assert 'if not isinstance(doc, dict):' in src
    assert 'print("[ERROR] JSON 顶层不是对象", file=sys.stderr)' in src
    assert "f\"      git_commit={(git.get('git_commit') or 'unknown')[:12]} \"" in src


# ---------- forbidden tokens 第三百八十六批 ----------

def test_source_no_eval_batch114():
    assert "eval(" not in _src()


def test_source_no_exec_batch114():
    assert "exec(" not in _src()


def test_source_no_compile_batch114():
    assert "compile(" not in _src()


def test_source_no_globals_batch114():
    assert "globals(" not in _src()


def test_source_no_locals_batch114():
    assert "locals(" not in _src()


def test_source_no_os_system_batch114():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch114():
    assert "subprocess" not in _src()


def test_source_no_popen_batch114():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch114():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch114():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch114():
    assert "socket" not in _src()


def test_source_no_requests_batch114():
    assert "requests" not in _src()


def test_source_no_urllib_batch114():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch114():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch114():
    assert "yield" not in _src()


def test_source_no_async_await_batch114():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch114():
    assert _src().count("open(") == 1
