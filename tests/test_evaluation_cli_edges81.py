"""evaluation/cli.py 第一百轮 edges 测试（Round 706）。

补强 edges80 未触及的角度（第七十一批）。

新角度：
- main run 全链路成功（真实 load_manifest → mocked run_evaluation → 自校验 → [OK] 输出行细节）
- run 的三处失败路径（清单不存在 rc2 / 清单 schema 不符 rc1 / run_evaluation 抛 EvalSchemaError rc1 / 自校验失败 rc1）
- git_commit None → unknown；负数 --max-chars 透传（现状记录）
- validate-report 成功 rc0 / validate_file 抛 JSONDecodeError rc1
- inspect-doc 错误路径（不存在 rc2 / 坏 JSON rc1 / 顶层非对象 rc1）+ 输出元信息 + 指标排序（bool < 数字 < null）
- argparse 行为（--help exit 0 / 未知子命令 exit 2 / 缺 --output exit 2）
- _format_metric 负浮点 / 空 dict / 多键 dict 排序 / str+reason
- 源码补强（add_subparsers 行 / RawDescriptionHelpFormatter / 三个 command 分支 / or [] 两行 / _sort_key 注解 / value:.4f / sorted items）
- AST 补强（main 11 个 Return 计数 0×2/1×5/2×4 / 三 command 常量顺序 / isinstance 链 bool-float-dict / inspect-doc 函数级双 import / main 默认 None）
- forbidden tokens 第一百七十六批
"""

from __future__ import annotations

import ast
import inspect
import json
from collections import Counter
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _format_metric, main
from evaluation.schema import EvalSchemaError


def _report_stub() -> dict:
    return {
        "per_doc": [
            {"doc_id": "d1", "metrics": {"pipeline_success": {"value": True, "reason": None}}},
            {"doc_id": "d2", "metrics": {"pipeline_success": {"value": False, "reason": "x"}}},
        ],
        "devset": {"status": "incomplete", "file_count": 2, "content_group_count": 2,
                   "pdf_count": 1, "docx_count": 1},
    }


def _patch_run(monkeypatch, tmp_path, report=None, git=None):
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete", "documents": [],
    }), encoding="utf-8")
    monkeypatch.setattr(cli_mod, "run_evaluation",
                        MagicMock(return_value=report or _report_stub()))
    monkeypatch.setattr(cli_mod, "validate_file", MagicMock())
    monkeypatch.setattr(cli_mod, "get_git_provenance",
                        lambda root: git if git is not None
                        else {"git_commit": "a" * 40, "git_dirty": True})
    return m


# ---------- run 成功全链路 ----------

def test_run_success_output_details_batch52(monkeypatch, tmp_path, capsys):
    m = _patch_run(monkeypatch, tmp_path)
    out = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out)])
    assert rc == 0
    o = capsys.readouterr().out
    assert f"[OK] 评测完成：{out}" in o
    assert "documents=2（成功 1，失败 1）" in o
    assert "devset_status=incomplete" in o
    assert "file_count=2" in o
    assert "groups=2" in o
    assert "pdf=1 docx=1" in o
    assert "git_commit=aaaaaaaaaaaa" in o
    assert "git_dirty=True" in o


def test_run_evaluation_called_with_defaults_batch52(monkeypatch, tmp_path):
    m = _patch_run(monkeypatch, tmp_path)
    out = tmp_path / "o.json"
    rc = main(["run", "--manifest", str(m), "--output", str(out)])
    assert rc == 0
    call = cli_mod.run_evaluation.call_args
    assert call.args[1] == out  # Path(args.output)
    assert call.kwargs == {"parser_name": "fallback", "max_chars": 800,
                           "tolerance_chars": 30}


def test_run_negative_max_chars_flows_batch52(monkeypatch, tmp_path):
    """argparse 对 int 不设下界，负数原样透传（现状记录）。"""
    m = _patch_run(monkeypatch, tmp_path)
    rc = main(["run", "--manifest", str(m), "--output", str(tmp_path / "o.json"),
               "--max-chars", "-5"])
    assert rc == 0
    assert cli_mod.run_evaluation.call_args.kwargs["max_chars"] == -5


def test_run_git_commit_none_prints_unknown_batch52(monkeypatch, tmp_path, capsys):
    m = _patch_run(monkeypatch, tmp_path, git={"git_commit": None, "git_dirty": False})
    rc = main(["run", "--manifest", str(m), "--output", str(tmp_path / "o.json")])
    assert rc == 0
    o = capsys.readouterr().out
    assert "git_commit=unknown" in o
    assert "git_dirty=False" in o


# ---------- run 失败路径 ----------

def test_run_missing_manifest_rc2_batch52(monkeypatch, tmp_path, capsys):
    _patch_run(monkeypatch, tmp_path)
    rc = main(["run", "--manifest", str(tmp_path / "nope.json"),
               "--output", str(tmp_path / "o.json")])
    assert rc == 2
    assert "[ERROR] 清单不存在" in capsys.readouterr().err


def test_run_invalid_manifest_schema_rc1_batch52(monkeypatch, tmp_path, capsys):
    m = tmp_path / "bad.json"
    m.write_text(json.dumps({"manifest_version": "9.9", "devset_status": "incomplete",
                             "documents": []}), encoding="utf-8")
    _patch_run(monkeypatch, tmp_path)
    rc = main(["run", "--manifest", str(m), "--output", str(tmp_path / "o.json")])
    assert rc == 1
    assert "[ERROR] 清单加载失败" in capsys.readouterr().err


def test_run_eval_schema_error_rc1_batch52(monkeypatch, tmp_path, capsys):
    m = _patch_run(monkeypatch, tmp_path)
    monkeypatch.setattr(cli_mod, "run_evaluation",
                        MagicMock(side_effect=EvalSchemaError("boom")))
    rc = main(["run", "--manifest", str(m), "--output", str(tmp_path / "o.json")])
    assert rc == 1
    assert "生成的报告未通过 Schema 校验" in capsys.readouterr().err


def test_run_self_validate_failure_rc1_batch52(monkeypatch, tmp_path, capsys):
    m = _patch_run(monkeypatch, tmp_path)
    cli_mod.validate_file.side_effect = EvalSchemaError("bad")
    rc = main(["run", "--manifest", str(m), "--output", str(tmp_path / "o.json")])
    assert rc == 1
    assert "报告自校验失败" in capsys.readouterr().err


# ---------- validate-report 成功与 JSONDecodeError ----------

def test_validate_report_ok_rc0_batch52(monkeypatch, tmp_path, capsys):
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli_mod, "validate_file", MagicMock())
    rc = main(["validate-report", str(p)])
    assert rc == 0
    assert f"[OK] {p} 通过 evaluation-report Schema 校验" in capsys.readouterr().out


def test_validate_report_json_decode_rc1_batch52(monkeypatch, tmp_path, capsys):
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        cli_mod, "validate_file",
        MagicMock(side_effect=json.JSONDecodeError("Expecting value", "doc", 0)))
    rc = main(["validate-report", str(p)])
    assert rc == 1
    assert "JSON 解析失败" in capsys.readouterr().err


# ---------- inspect-doc 错误路径与输出 ----------

def test_inspect_doc_missing_file_rc2_batch52(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "no.json")])
    assert rc == 2
    assert "[ERROR] 文档不存在" in capsys.readouterr().err


def test_inspect_doc_bad_json_rc1_batch52(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("{bad", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1
    assert "JSON 解析失败" in capsys.readouterr().err


def test_inspect_doc_top_level_array_rc1_batch52(tmp_path, capsys):
    p = tmp_path / "d.json"
    p.write_text("[1, 2]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1
    assert "JSON 顶层不是对象" in capsys.readouterr().err


def test_inspect_doc_meta_lines_and_order_batch52(tmp_path, capsys):
    doc = {
        "document_id": "doc-1", "source_path": "a.pdf", "parser_name": "fallback",
        "parser_version": "1.0", "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "ab",
                      "source_locator": {"page": 1}}],
        "chunks": [{"text": "ab", "source_element_ids": ["e1"]}],
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    lines = capsys.readouterr().out.splitlines()
    assert any(l.startswith("file:") and str(p) in l for l in lines)
    assert any("document_id: doc-1" in l for l in lines)
    assert any("type=pdf" in l for l in lines)
    assert any("counts:" in l and "elements=1" in l and "chunks=1" in l for l in lines)
    idx = {l.strip().split(" ")[0]: i for i, l in enumerate(lines) if l.startswith("  ")}
    # 排序：bool 组(0) < 数字组(1) < null 组(3)
    assert idx["pipeline_success"] < idx["text_char_multiset_precision"]
    assert idx["text_char_multiset_precision"] < idx["figure_caption_precision"]


def test_inspect_doc_empty_doc_defaults_batch52(tmp_path, capsys):
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 0
    o = capsys.readouterr().out
    assert "type=unknown" in o
    assert "elements=0 chunks=0" in o


# ---------- argparse 行为 ----------

def test_help_exits_zero_batch52(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["--help"])
    assert ei.value.code == 0
    assert "evaluation.cli" in capsys.readouterr().out


def test_run_help_lists_options_batch52(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["run", "--help"])
    assert ei.value.code == 0
    o = capsys.readouterr().out
    assert "--max-chars" in o
    assert "--tolerance-chars" in o


def test_unknown_subcommand_exit2_batch52(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["bogus"])
    assert ei.value.code == 2


def test_run_missing_output_exit2_batch52(capsys):
    with pytest.raises(SystemExit) as ei:
        main(["run", "--manifest", "x.json"])
    assert ei.value.code == 2


# ---------- _format_metric 补充 ----------

def test_format_metric_negative_float_batch52():
    assert "-0.5000" in _format_metric("r", {"value": -0.5, "reason": None})


def test_format_metric_empty_dict_value_batch52():
    out = _format_metric("e", {"value": {}, "reason": None})
    assert out.strip().endswith("(ok)")
    assert "=" not in out


def test_format_metric_dict_sorted_keys_batch52():
    out = _format_metric("d", {"value": {"b": 2, "a": 1}, "reason": None})
    assert "a=1, b=2" in out


def test_format_metric_str_with_null_reason_batch52():
    out = _format_metric("ec", {"value": "parse_failed", "reason": None})
    assert "parse_failed" in out
    assert "(ok)" in out


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(cli_mod)


def test_source_subparsers_line_batch52():
    assert 'sub = p.add_subparsers(dest="command", required=True)' in _src()


def test_source_formatter_class_batch52():
    assert "formatter_class=argparse.RawDescriptionHelpFormatter" in _src()


def test_source_three_command_branches_batch52():
    src = _src()
    assert 'if args.command == "run":' in src
    assert 'if args.command == "validate-report":' in src
    assert 'if args.command == "inspect-doc":' in src


def test_source_or_empty_defaults_batch52():
    src = _src()
    assert 'elements = doc.get("elements") or []' in src
    assert 'chunks = doc.get("chunks") or []' in src


def test_source_sort_key_annotation_batch52():
    assert "def _sort_key(name: str) -> tuple[int, str]:" in _src()


def test_source_float_format_and_sorted_batch52():
    src = _src()
    assert "{value:.4f}" in src
    assert "sorted(value.items())" in src


def test_source_inspect_updates_batch52():
    src = _src()
    assert "metrics.update(figure_caption_prf(doc, None))" in src
    assert "metrics.update(chunk_boundary_prf(doc, None, tolerance_chars=args.tolerance_chars))" in src


def test_source_source_type_default_batch52():
    assert 'doc.get("source_type", "unknown")' in _src()


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(cli_mod))


def test_ast_main_return_value_counts_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    rets = [n.value.value for n in ast.walk(func)
            if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)]
    assert len(rets) == 11
    assert Counter(rets) == {0: 2, 1: 5, 2: 4}


def test_ast_main_command_constants_order_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    cmds = [n.test.comparators[0].value for n in ast.walk(func)
            if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
            and isinstance(n.test.comparators[0], ast.Constant)]
    assert cmds == ["run", "validate-report", "inspect-doc"]


def test_ast_format_metric_isinstance_chain_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_format_metric")
    isas = [c.args[1].id for c in ast.walk(func)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
            and c.func.id == "isinstance" and isinstance(c.args[1], ast.Name)]
    assert isas == ["bool", "float", "dict"]


def test_ast_inspect_doc_function_imports_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    mods = sorted(n.module for n in ast.walk(func) if isinstance(n, ast.ImportFrom))
    assert mods == ["evaluation.annotation_metrics", "evaluation.metrics"]
    names = [a.name for n in ast.walk(func)
             if isinstance(n, ast.ImportFrom) and n.module == "evaluation.annotation_metrics"
             for a in n.names]
    assert names == ["chunk_boundary_prf", "figure_caption_prf"]


def test_ast_main_default_none_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    assert [ast.unparse(d) for d in func.args.defaults] == ["None"]


def test_ast_module_function_names_batch52():
    tree = _tree()
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_build_parser", "main", "_format_metric", "_run_inspect_doc"]


# ---------- forbidden tokens 第一百七十六批 ----------

def test_source_no_eval_batch52():
    assert "eval(" not in _src()


def test_source_no_exec_batch52():
    assert "exec(" not in _src()


def test_source_no_compile_batch52():
    assert "compile(" not in _src()


def test_source_no_globals_batch52():
    assert "globals(" not in _src()


def test_source_no_locals_batch52():
    assert "locals(" not in _src()


def test_source_no_os_system_batch52():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch52():
    assert "subprocess" not in _src()


def test_source_no_popen_batch52():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch52():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch52():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch52():
    assert "socket" not in _src()


def test_source_no_requests_batch52():
    assert "requests" not in _src()


def test_source_no_urllib_batch52():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch52():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch52():
    assert "yield" not in _src()


def test_source_no_async_await_batch52():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch52():
    assert _src().count("open(") == 1
