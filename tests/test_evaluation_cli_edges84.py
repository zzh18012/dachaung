"""evaluation/cli.py 第一百零三轮 edges 测试（Round 727）。

补强 edges81/edges82/edges83 未触及的角度（第九十二批）。

新角度：
- validate_file 收到 (output_path, "evaluation-report.schema.json") 行为级捕获
- load_manifest 收到 Path 类型（字符串参数被 Path() 转换）
- inspect-doc 真实运行 21 行指标：首行 bool（pipeline_success true）、末行 null
  （silent_drop_count）、metrics: 头部位置、file: 行精确 8 空格
- _format_metric 空 metric（{}）→ "null  (None)"（reason 缺省 None 被插值成字符串）
- main(argv=None) 走 sys.argv（monkeypatch sys.argv）
- argparse：run 缺 --output / validate-report 缺参数 / 未知子命令 → 全 SystemExit 2
- stdout reconfigure 守卫（AttributeError, OSError）+ __main__ 守卫 raise SystemExit
- AST（main Compare4·BoolOp1·Call37 / inspect Tuple6 / format JoinedStr12）
- 源码补强（Path(×4 / args.×11）
- forbidden tokens 第一百九十七批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import evaluation.cli as cli_mod
from evaluation.cli import _build_parser, _format_metric, main


def _patch_run(monkeypatch, tmp_path, report=None):
    calls = {}
    mf = tmp_path / "manifest.json"
    mf.write_text("{}", encoding="utf-8")

    def fake_load(p):
        calls["manifest_arg"] = p
        return SimpleNamespace(project_root=tmp_path)
    monkeypatch.setattr(cli_mod, "load_manifest", fake_load)

    def fake_val(path, schema_name, *a, **k):
        calls["validate_args"] = (path, schema_name)
    monkeypatch.setattr(cli_mod, "validate_file", fake_val)

    def fake_run(m, out, **kwargs):
        calls["output_path"] = out
        return report if report is not None else {"per_doc": [], "devset": {}}
    monkeypatch.setattr(cli_mod, "run_evaluation", fake_run)
    monkeypatch.setattr(cli_mod, "get_git_provenance",
                        lambda r: {"git_commit": None, "git_dirty": False})
    return calls, mf


# ---------- validate_file 行为级捕获 ----------

def test_validate_file_receives_output_and_schema_batch53(monkeypatch, tmp_path):
    calls, mf = _patch_run(monkeypatch, tmp_path)
    out = tmp_path / "out" / "r.json"
    assert main(["run", "--manifest", str(mf), "--output", str(out)]) == 0
    assert calls["validate_args"] == (out, "evaluation-report.schema.json")
    assert isinstance(calls["manifest_arg"], Path)
    assert calls["output_path"] == out


# ---------- inspect-doc 真实全量运行 ----------

def _real_doc() -> dict:
    return {
        "document_id": "d1", "source_type": "pdf",
        "source_path": "a.pdf", "parser_name": "fallback", "parser_version": "1",
        "elements": [{"type": "paragraph", "content": "hello",
                      "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
    }


def test_inspect_real_run_ordering_batch53(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(json.dumps(_real_doc()), encoding="utf-8")
    assert main(["inspect-doc", str(f)]) == 0
    lines = [l for l in capsys.readouterr().out.splitlines() if l.strip()]
    assert lines[0] == f"file:        {f}"
    header_idx = [i for i, l in enumerate(lines) if l == "metrics:"]
    assert len(header_idx) == 1
    metric_lines = [l for l in lines if l.startswith("  ")]
    assert len(metric_lines) == 21
    assert metric_lines[0].strip().startswith("pipeline_success")
    assert "true" in metric_lines[0]
    assert metric_lines[-1].strip().startswith("silent_drop_count")
    assert "null" in metric_lines[-1]


# ---------- _format_metric 缺省 ----------

def test_format_metric_empty_dict_batch53():
    assert _format_metric("x", {}) == "  x" + " " * 36 + "null  (None)"


def test_format_metric_reason_only_batch53():
    assert _format_metric("x", {"reason": "r"}) == \
        "  x" + " " * 36 + "null  (r)"


# ---------- argv=None 走 sys.argv ----------

def test_main_none_argv_reads_sys_argv_batch53(monkeypatch, tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["evaluation.cli", "inspect-doc", str(f)])
    assert main() == 0
    assert "document_id: ?" in capsys.readouterr().out


# ---------- argparse 拒绝 ----------

def test_parser_run_missing_output_batch53():
    with pytest.raises(SystemExit) as ei:
        _build_parser().parse_args(["run", "--manifest", "m.json"])
    assert ei.value.code == 2


def test_parser_validate_report_missing_input_batch53():
    with pytest.raises(SystemExit) as ei:
        _build_parser().parse_args(["validate-report"])
    assert ei.value.code == 2


def test_parser_unknown_subcommand_batch53():
    with pytest.raises(SystemExit) as ei:
        _build_parser().parse_args(["bogus-command"])
    assert ei.value.code == 2


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(cli_mod)


def test_source_guards_batch53():
    src = _src()
    assert 'if __name__ == "__main__":' in src
    assert "raise SystemExit(main())" in src
    assert "(AttributeError, OSError):" in src
    assert 'f"file:        {input_path}"' in src


def test_source_path_and_args_counts_batch53():
    src = _src()
    assert src.count("Path(") == 4
    assert src.count("args.") == 11


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(cli_mod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _counts(func) -> dict:
    import collections
    return collections.Counter(type(n).__name__ for n in ast.walk(func))


def test_ast_main_structure_batch53():
    c = _counts(_func("main"))
    assert (c["If"], c["Try"], c["Return"], c["GenExp"], c["BoolOp"],
            c["Compare"], c["Call"]) == (5, 4, 12, 0, 1, 4, 37)


def test_ast_inspect_structure_batch53():
    c = _counts(_func("_run_inspect_doc"))
    assert (c["If"], c["Try"], c["Return"], c["For"], c["FunctionDef"],
            c["Tuple"]) == (5, 1, 8, 1, 2, 6)


def test_ast_format_joinedstr_batch53():
    c = _counts(_func("_format_metric"))
    assert (c["If"], c["Return"], c["JoinedStr"]) == (4, 5, 12)


# ---------- forbidden tokens 第一百九十七批 ----------

def test_source_no_eval_batch53():
    assert "eval(" not in _src()


def test_source_no_exec_batch53():
    assert "exec(" not in _src()


def test_source_no_compile_batch53():
    assert "compile(" not in _src()


def test_source_no_globals_batch53():
    assert "globals(" not in _src()


def test_source_no_locals_batch53():
    assert "locals(" not in _src()


def test_source_no_os_system_batch53():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch53():
    assert "subprocess" not in _src()


def test_source_no_popen_batch53():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch53():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch53():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch53():
    assert "socket" not in _src()


def test_source_no_requests_batch53():
    assert "requests" not in _src()


def test_source_no_urllib_batch53():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch53():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch53():
    assert "yield" not in _src()


def test_source_no_async_await_batch53():
    assert "async " not in _src()
    assert "await " not in _src()
