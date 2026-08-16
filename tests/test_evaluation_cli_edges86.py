"""evaluation/cli.py 第一百零五轮 edges 测试（Round 741）。

补强 edges83-85 未触及的角度（第一百零六批）。

新角度：
- inspect-doc 头部五行精确格式（file: 8 空格 / document_id: /
  source: path + "  type=" / parser: name + " v" + version /
  counts: elements=N chunks=M）
- inspect-doc 指标键集恰 21 个（含 _tolerance_chars，行为级提取）
- 子命令 --help（validate-report / inspect-doc）exit 0
- run 清单不存在 → rc2 + stderr "[ERROR] 清单不存在: <Path>"
- argparse 错误 stderr 以 "usage: evaluation.cli" 开头
- 源码计数：add_argument ×8、add_parser ×3、add_subparsers ×1
- forbidden tokens 第二百一十一批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _build_parser, main

_METRIC_KEYS = sorted([
    "_tolerance_chars", "chunk_boundary_f1", "chunk_boundary_precision",
    "chunk_boundary_recall", "chunk_reference_intact_ratio",
    "docx_locator_valid_ratio", "element_count_by_type",
    "element_count_total", "error_code", "figure_caption_f1",
    "figure_caption_precision", "figure_caption_recall",
    "heading_boundary_compliance", "image_resource_exists_ratio",
    "pdf_locator_valid_ratio", "pipeline_success", "schema_valid",
    "silent_drop_count", "text_char_multiset_precision",
    "text_char_multiset_recall", "text_preservation_equal",
])


def _ok_doc() -> dict:
    return {
        "document_id": "o", "source_type": "docx", "source_path": "o.docx",
        "parser_name": "python-docx", "parser_version": "1.2.0",
        "elements": [{"type": "paragraph", "content": "a"},
                     {"type": "heading", "content": "b"},
                     {"type": "image", "resource_path": "x.png"}],
        "chunks": [{"text": "a b", "source_element_ids": ["e1"]},
                   {"text": "c", "source_element_ids": ["e2"]}],
    }


# ---------- inspect-doc 头部行 ----------

def test_inspect_header_lines_exact_batch54(tmp_path, capsys):
    f = tmp_path / "ok.json"
    f.write_text(json.dumps(_ok_doc()), encoding="utf-8")
    assert main(["inspect-doc", str(f)]) == 0
    lines = [l for l in capsys.readouterr().out.splitlines()
             if l.strip() and not l.startswith("  ")]
    assert lines == [
        f"file:        {f}",
        "document_id: o",
        "source:      o.docx  type=docx",
        "parser:      python-docx v1.2.0",
        "counts:      elements=3 chunks=2",
        "metrics:",
    ]


def test_inspect_metric_key_set_exact_21_batch54(tmp_path, capsys):
    f = tmp_path / "ok.json"
    f.write_text(json.dumps(_ok_doc()), encoding="utf-8")
    assert main(["inspect-doc", str(f)]) == 0
    out = capsys.readouterr().out
    names = [l.strip().split()[0] for l in out.splitlines()
             if l.startswith("  ")]
    assert sorted(names) == _METRIC_KEYS
    assert len(names) == 21


# ---------- 子命令帮助 ----------

@pytest.mark.parametrize("argv,marker", [
    (["validate-report", "--help"], "input"),  # 子帮助只列参数不列 schema 名
    (["inspect-doc", "--help"], "tolerance"),
])
def test_subcommand_help_exits_zero_batch54(argv, marker, capsys):
    with pytest.raises(SystemExit) as e:
        _build_parser().parse_args(argv)
    assert e.value.code == 0
    assert marker in capsys.readouterr().out


# ---------- run 缺清单 ----------

def test_run_missing_manifest_rc2_batch54(tmp_path, capsys):
    ghost = tmp_path / "ghost.json"
    assert main(["run", "--manifest", str(ghost),
                 "--output", str(tmp_path / "r.json")]) == 2
    err = capsys.readouterr().err
    assert err.strip() == f"[ERROR] 清单不存在: {ghost}"


# ---------- argparse usage 行 ----------

def test_argparse_error_usage_line_batch54(capsys):
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["run"])
    err = capsys.readouterr().err
    assert err.startswith("usage: evaluation.cli")


# ---------- 源码计数 ----------

def _src() -> str:
    return inspect.getsource(cli_mod)


def test_source_parser_counts_batch54():
    src = _src()
    assert src.count("add_argument") == 8
    assert src.count("add_parser") == 3
    assert src.count("add_subparsers") == 1


# ---------- forbidden tokens 第二百一十一批 ----------

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
