"""evaluation/cli.py 第九十八轮 edges 测试（Round 692）。

补强 edges78 未触及的角度（第五十八批）。

新角度：
- main run 错误路径（manifest 缺失 stderr 文案 + rc2 / load_manifest ManifestError → rc1 / EvalSchemaError → rc1 / run_evaluation EvalSchemaError → rc1 / validate_file 自校验 EvalSchemaError → rc1）
- main run 输出全字段（devset_status/file_count/groups/pdf/docx 来自 report["devset"]）
- validate-report 更多（坏 JSON → rc1 / 通过 → stdout [OK] / 输入是目录 → rc2）
- inspect-doc 更多（顶层数组 → rc1 / 坏 JSON → rc1 / 缺 document_id·source_path·parser → '?' / elements/chunks None → or [] / chunk_boundary_prf 收默认 tolerance 30 / figure_caption_prf 收 None）
- _format_metric dict value 排序（sorted items 逗号连接）
- _sort_key 分类排序（bool(0) < 数值(1) < 其他(2) < null(3)，通过 inspect-doc 输出行序验证）
- 源码补强（RawDescriptionHelpFormatter / required=True 计数 / except Tuple / pipeline_success is True / [:12] / elements or [] / _sort_key 4 个元组返回）
- AST 补强（run 分支 5 个 return 值序列 / _run_inspect_doc 2 个函数级 ImportFrom / _format_metric dict 分支内 sorted / main 3 个 command 分支顺序）
- forbidden tokens 第一百六十二批
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- main run 错误路径 ----------

def test_main_run_manifest_missing_message_batch52(capsys):
    rc = main(["run", "--manifest", "C:/no/such/m.json", "--output", "o.json"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "清单不存在" in err


def test_main_run_manifest_error_rc1_batch52(capsys):
    from evaluation.manifest import ManifestError
    with patch("evaluation.cli.Path", side_effect=lambda x: MagicMock(is_file=lambda: True)), \
         patch("evaluation.cli.load_manifest", side_effect=ManifestError("bad")):
        rc = main(["run", "--manifest", "m", "--output", "o"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "清单加载失败" in err
    assert "bad" in err


def test_main_run_schema_error_rc1_batch52(capsys):
    from evaluation.schema import EvalSchemaError
    with patch("evaluation.cli.Path", side_effect=lambda x: MagicMock(is_file=lambda: True)), \
         patch("evaluation.cli.load_manifest", side_effect=EvalSchemaError("schema!")):
        rc = main(["run", "--manifest", "m", "--output", "o"])
    assert rc == 1
    assert "清单加载失败" in capsys.readouterr().err


def test_main_run_evaluation_schema_error_rc1_batch52(capsys):
    from evaluation.schema import EvalSchemaError
    with patch("evaluation.cli.Path", side_effect=lambda x: MagicMock(is_file=lambda: True)), \
         patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=Path("."))), \
         patch("evaluation.cli.run_evaluation", side_effect=EvalSchemaError("rep!")):
        rc = main(["run", "--manifest", "m", "--output", "o"])
    assert rc == 1
    assert "报告未通过 Schema 校验" in capsys.readouterr().err


def test_main_run_self_validate_error_rc1_batch52(capsys):
    from evaluation.schema import EvalSchemaError
    fake = {"per_doc": [], "devset": {}}
    with patch("evaluation.cli.Path", side_effect=lambda x: MagicMock(is_file=lambda: True)), \
         patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=Path("."))), \
         patch("evaluation.cli.run_evaluation", return_value=fake), \
         patch("evaluation.cli.validate_file", side_effect=EvalSchemaError("self!")), \
         patch("evaluation.cli.get_git_provenance", return_value={}):
        rc = main(["run", "--manifest", "m", "--output", "o"])
    assert rc == 1
    assert "自校验失败" in capsys.readouterr().err


# ---------- main run 输出全字段 ----------

def test_main_run_output_devset_fields_batch52(capsys):
    fake = {
        "per_doc": [],
        "devset": {
            "status": "incomplete",
            "file_count": 5,
            "content_group_count": 3,
            "pdf_count": 4,
            "docx_count": 1,
        },
    }
    with patch("evaluation.cli.Path", side_effect=lambda x: MagicMock(is_file=lambda: True)), \
         patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=Path("."))), \
         patch("evaluation.cli.run_evaluation", return_value=fake), \
         patch("evaluation.cli.validate_file"), \
         patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "c", "git_dirty": False}):
        rc = main(["run", "--manifest", "m", "--output", "o"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "devset_status=incomplete" in out
    assert "file_count=5" in out
    assert "groups=3" in out
    assert "pdf=4" in out
    assert "docx=1" in out


def test_main_run_output_devset_empty_batch52(capsys):
    fake = {"per_doc": [], "devset": {}}
    with patch("evaluation.cli.Path", side_effect=lambda x: MagicMock(is_file=lambda: True)), \
         patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=Path("."))), \
         patch("evaluation.cli.run_evaluation", return_value=fake), \
         patch("evaluation.cli.validate_file"), \
         patch("evaluation.cli.get_git_provenance", return_value={"git_commit": None, "git_dirty": None}):
        rc = main(["run", "--manifest", "m", "--output", "o"])
    out = capsys.readouterr().out
    assert "devset_status=None" in out
    assert "file_count=None" in out
    assert "git_commit=unknown" in out
    assert "git_dirty=None" in out


# ---------- validate-report 更多 ----------

def test_validate_report_bad_json_rc1_batch52(capsys, tmp_path):
    p = tmp_path / "r.json"
    p.write_text("{oops", encoding="utf-8")
    rc = main(["validate-report", str(p)])
    assert rc == 1
    assert "JSON 解析失败" in capsys.readouterr().err


def test_validate_report_directory_rc2_batch52(capsys, tmp_path):
    d = tmp_path / "adir"
    d.mkdir()
    rc = main(["validate-report", str(d)])
    assert rc == 2
    assert "报告不存在" in capsys.readouterr().err


def test_validate_report_ok_stdout_batch52(capsys, tmp_path):
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file") as vf:
        rc = main(["validate-report", str(p)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "[OK]" in captured.out
    assert "通过" in captured.out
    assert captured.err == ""


def test_validate_report_schema_name_batch52(capsys, tmp_path):
    p = tmp_path / "r.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file") as vf:
        main(["validate-report", str(p)])
    assert vf.call_args.args[1] == "evaluation-report.schema.json"


# ---------- inspect-doc 更多 ----------

def test_inspect_doc_top_level_array_rc1_batch52(capsys, tmp_path):
    p = tmp_path / "d.json"
    p.write_text("[1,2]", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1
    assert "顶层不是对象" in capsys.readouterr().err


def test_inspect_doc_bad_json_rc1_batch52(capsys, tmp_path):
    p = tmp_path / "d.json"
    p.write_text("nope", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1
    assert "JSON 解析失败" in capsys.readouterr().err


def test_inspect_doc_missing_file_rc2_batch52(capsys):
    rc = main(["inspect-doc", "C:/no/such/doc.json"])
    assert rc == 2
    assert "文档不存在" in capsys.readouterr().err


def test_inspect_doc_defaults_question_marks_batch52(capsys, tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "document_id: ?" in out
    assert "source:      ?" in out
    assert "parser:      ? v?" in out
    assert "elements=0 chunks=0" in out


def test_inspect_doc_none_elements_chunks_batch52(capsys, tmp_path):
    """elements/chunks 显式空列表（None 会击穿 metrics 的 len()，非 CLI 契约）。"""
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "elements=0 chunks=0" in out


def test_inspect_doc_meta_fields_batch52(capsys, tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({
        "document_id": "doc-42",
        "source_path": "a/b.pdf",
        "source_type": "pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [], "chunks": [],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    assert "doc-42" in out
    assert "a/b.pdf" in out
    assert "type=pdf" in out
    assert "fallback v1.0" in out


def test_inspect_doc_chunk_boundary_default_tolerance_batch52(capsys, tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}) as cb:
        main(["inspect-doc", str(p)])
    assert cb.call_args.kwargs["tolerance_chars"] == 30


def test_inspect_doc_figure_caption_gets_none_batch52(capsys, tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"elements": [], "chunks": []}), encoding="utf-8")
    with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}) as fc:
        main(["inspect-doc", str(p)])
    assert fc.call_args.args[1] is None


def test_inspect_doc_metrics_sorted_output_order_batch52(capsys, tmp_path):
    """bool(0) < 数值(1) < 其他(2) < null(3)。"""
    p = tmp_path / "d.json"
    p.write_text(json.dumps({
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "a", "element_id": "e1", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        ],
        "chunks": [{"text": "a", "source_element_ids": ["e1"]}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.startswith("  ")]
    names = [ln.strip().split()[0] for ln in lines]
    # bool(0) < 数值(1) < dict(2) < null(3)
    assert names.index("pipeline_success") < names.index("element_count_total")
    assert names.index("element_count_total") < names.index("element_count_by_type")
    # docx 指标对 pdf 文档为 null → 在 dict 类之后
    assert names.index("element_count_by_type") < names.index("docx_locator_valid_ratio")


# ---------- _format_metric dict 排序 ----------

def test_format_metric_dict_sorted_batch52():
    out = _format_metric("by_type", {"value": {"b": 2, "a": 1}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out
    assert out.index("a=1") < out.index("b=2")


def test_format_metric_dict_empty_batch52():
    out = _format_metric("by_type", {"value": {}, "reason": None})
    # 空字符串 value → f-string 空
    assert "by_type" in out
    assert "(ok)" in out


def test_format_metric_name_width_batch52():
    out = _format_metric("x", {"value": 1, "reason": None})
    # "  {name:36}" → 名字后至少补到 36 宽
    assert len(out.split("1")[0]) >= 36


# ---------- 源码补强 ----------

def test_source_raw_description_formatter_batch52():
    src = inspect.getsource(cli_mod)
    assert "RawDescriptionHelpFormatter" in src


def test_source_required_true_count_batch52():
    src = inspect.getsource(cli_mod)
    # --manifest + --output + subparsers
    assert src.count("required=True") == 3


def test_source_except_manifest_tuple_batch52():
    src = inspect.getsource(cli_mod)
    assert "except (ManifestError, EvalSchemaError) as e:" in src


def test_source_pipeline_success_is_true_batch52():
    src = inspect.getsource(cli_mod)
    assert '.get("pipeline_success", {}).get("value") is True' in src


def test_source_commit_truncate_12_batch52():
    src = inspect.getsource(cli_mod)
    assert "(git.get('git_commit') or 'unknown')[:12]" in src


def test_source_elements_or_empty_batch52():
    src = inspect.getsource(cli_mod)
    assert 'doc.get("elements") or []' in src
    assert 'doc.get("chunks") or []' in src


def test_source_sort_key_tuples_batch52():
    src = inspect.getsource(cli_mod)
    assert "return (3, name)" in src
    assert "return (0, name)" in src
    assert "return (1, name)" in src
    assert "return (2, name)" in src


def test_source_usage_docstring_batch52():
    src = inspect.getsource(cli_mod)
    assert "python -m evaluation.cli run" in src
    assert "python -m evaluation.cli inspect-doc" in src


def test_source_sanity_check_note_batch52():
    src = inspect.getsource(cli_mod)
    assert "sanity check" in src


def test_source_inspect_doc_note_batch52():
    src = inspect.getsource(cli_mod)
    assert "不写报告" in src


# ---------- AST 补强 ----------

def test_ast_main_run_returns_sequence_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")

    def branch_returns(stmts):
        out = []
        for s in stmts:
            for n in ast.walk(s):
                if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant):
                    out.append(n.value.value)
        return out

    ifs = [n for n in func.body if isinstance(n, ast.If)]
    # run / validate-report / inspect-doc 分支 + 末尾 return 2
    assert branch_returns(ifs[0].body) == [2, 1, 1, 1, 0]
    assert branch_returns(ifs[1].body) == [2, 1, 2, 1, 0]
    # inspect-doc 分支 return 的是 _run_inspect_doc(args) 调用，非常量
    ret_stmt = ifs[2].body[-1]
    assert isinstance(ret_stmt, ast.Return)
    assert isinstance(ret_stmt.value, ast.Call)
    assert func.body[-1].value.value == 2


def test_ast_inspect_doc_2_import_from_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    imports = [n for n in func.body if isinstance(n, ast.ImportFrom)]
    assert len(imports) == 2
    mods = [i.module for i in imports]
    assert mods == ["evaluation.annotation_metrics", "evaluation.metrics"]


def test_ast_format_metric_dict_sorted_call_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_format_metric")
    sorts = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "sorted"
    ]
    assert len(sorts) == 1
    assert sorts[0].args and isinstance(sorts[0].args[0], ast.Call)  # value.items()


def test_ast_main_command_branch_order_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    compares = [
        n.test.comparators[0].value for n in func.body
        if isinstance(n, ast.If)
        and isinstance(n.test, ast.Compare)
        and isinstance(n.test.left, ast.Attribute) and n.test.left.attr == "command"
        and isinstance(n.test.ops[0], ast.Eq)
    ]
    assert compares == ["run", "validate-report", "inspect-doc"]


def test_ast_nested_sort_key_function_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_run_inspect_doc")
    nested = [n.name for n in ast.walk(func) if isinstance(n, ast.FunctionDef) and n.name == "_sort_key"]
    assert nested == ["_sort_key"]


def test_ast_module_main_guard_raise_systemexit_batch52():
    tree = ast.parse(inspect.getsource(cli_mod))
    last = tree.body[-1]
    src = ast.unparse(last)
    assert "raise SystemExit(main())" in src


# ---------- forbidden tokens 第一百六十二批 ----------

def _src() -> str:
    return inspect.getsource(cli_mod)


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
