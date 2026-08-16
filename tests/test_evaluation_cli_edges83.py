"""evaluation/cli.py 第一百零二轮 edges 测试（Round 720）。

补强 edges81/edges82 未触及的角度（第八十五批）。

新角度：
- run 成功 stdout 全字段（documents=3（成功 1，失败 2）/ devset 五字段 / git_commit[:12]）
- git_commit None → 'unknown' 截断仍为 'unknown'
- run kwargs 透传（parser kreuzberg / max_chars / tolerance_chars）
- load_manifest 接收 Path；get_git_provenance 接收 manifest.project_root
- load_manifest 抛 ManifestError / EvalSchemaError → rc 1
- run_evaluation 抛 EvalSchemaError / validate_file 自校验抛 EvalSchemaError → rc 1
- manifest 是目录（is_file False）→ rc 2
- validate-report 四分支（FAIL rc1 / FileNotFoundError rc2 / JSONDecode rc1 / OK stdout）
- inspect-doc 元信息缺省（? / v? / type unknown / elements=0 chunks=0）
- inspect-doc 顶层数组 → 顶层不是对象 rc 1
- inspect-doc tolerance-chars 透传到 chunk_boundary_prf（函数内导入 → patch 源模块）
- _format_metric dict 排序 / int / str / bool / null / float 4 位小数
- argparse inspect-doc --tolerance-chars 1.5 → SystemExit 2；run 缺 --manifest → SystemExit 2
- AST（main If5·Try4·Return12 / inspect If5·Try1·Return8·For1 / format If4·Return5 /
  build_parser Return1 / 模块级 If2·Try0）
- 源码补强（[ERROR]×10 / sys.stderr×12 / print×21 / reconfigure×3 / isinstance×6）
- forbidden tokens 第一百九十批
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
from evaluation.schema import EvalSchemaError


# ---------- run 路径 patch 工具 ----------

def _patch_run(monkeypatch, tmp_path, report=None, git=None):
    calls = {}
    manifest = SimpleNamespace(project_root=tmp_path / "root")
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text("{}", encoding="utf-8")

    def fake_load(p):
        calls["manifest_arg"] = p
        return manifest
    monkeypatch.setattr(cli_mod, "load_manifest", fake_load)

    def fake_run(m, out, *, parser_name, max_chars, tolerance_chars):
        calls["run"] = (m, out, parser_name, max_chars, tolerance_chars)
        return report if report is not None else {}
    monkeypatch.setattr(cli_mod, "run_evaluation", fake_run)
    monkeypatch.setattr(cli_mod, "validate_file", lambda *a, **k: None)

    def fake_git(root):
        calls["git_root"] = root
        return git if git is not None else {"git_commit": None, "git_dirty": False}
    monkeypatch.setattr(cli_mod, "get_git_provenance", fake_git)
    return calls, manifest_file


_FULL_REPORT = {
    "per_doc": [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {}},
    ],
    "devset": {"status": "incomplete", "file_count": 3, "content_group_count": 2,
               "pdf_count": 2, "docx_count": 1},
}


def test_run_success_stdout_full_details_batch53(monkeypatch, tmp_path, capsys):
    git = {"git_commit": "0123456789ab" + "c" * 28, "git_dirty": True}
    _patch_run(monkeypatch, tmp_path, report=_FULL_REPORT, git=git)
    out_file = tmp_path / "out" / "r.json"
    rc = main(["run", "--manifest", str(tmp_path / "manifest.json"),
               "--output", str(out_file)])
    assert rc == 0
    stdout = capsys.readouterr().out
    assert "评测完成" in stdout
    assert "documents=3（成功 1，失败 2）" in stdout
    assert "devset_status=incomplete file_count=3 groups=2 pdf=2 docx=1" in stdout
    assert "git_commit=0123456789ab git_dirty=True" in stdout


def test_run_git_commit_none_renders_unknown_batch53(monkeypatch, tmp_path, capsys):
    _patch_run(monkeypatch, tmp_path, report=_FULL_REPORT,
               git={"git_commit": None, "git_dirty": False})
    rc = main(["run", "--manifest", str(tmp_path / "manifest.json"),
               "--output", str(tmp_path / "o.json")])
    assert rc == 0
    assert "git_commit=unknown git_dirty=False" in capsys.readouterr().out


def test_run_kwargs_passthrough_batch53(monkeypatch, tmp_path):
    calls, mf = _patch_run(monkeypatch, tmp_path)
    rc = main(["run", "--manifest", str(mf), "--output", str(tmp_path / "o.json"),
               "--parser", "kreuzberg", "--max-chars", "100",
               "--tolerance-chars", "5"])
    assert rc == 0
    _, out, parser_name, max_chars, tol = calls["run"]
    assert parser_name == "kreuzberg"
    assert max_chars == 100
    assert tol == 5
    assert out == Path(tmp_path / "o.json")
    assert calls["manifest_arg"] == Path(mf)
    assert calls["git_root"] == tmp_path / "root"


def test_run_load_manifesterror_batch53(monkeypatch, tmp_path, capsys):
    from evaluation.manifest import ManifestError
    mf = tmp_path / "manifest.json"
    mf.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli_mod, "load_manifest",
                        lambda p: (_ for _ in ()).throw(ManifestError("坏清单")))
    monkeypatch.setattr(cli_mod, "run_evaluation", lambda *a, **k: {})
    rc = main(["run", "--manifest", str(mf), "--output", str(tmp_path / "o.json")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "[ERROR] 清单加载失败: 坏清单" in err


def test_run_load_evalschemaerror_batch53(monkeypatch, tmp_path, capsys):
    mf = tmp_path / "manifest.json"
    mf.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli_mod, "load_manifest",
                        lambda p: (_ for _ in ()).throw(EvalSchemaError("schema 坏")))
    monkeypatch.setattr(cli_mod, "run_evaluation", lambda *a, **k: {})
    rc = main(["run", "--manifest", str(mf), "--output", str(tmp_path / "o.json")])
    assert rc == 1
    assert "清单加载失败" in capsys.readouterr().err


def test_run_evaluation_schema_error_batch53(monkeypatch, tmp_path, capsys):
    mf = tmp_path / "manifest.json"
    mf.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli_mod, "load_manifest",
                        lambda p: SimpleNamespace(project_root=tmp_path))
    monkeypatch.setattr(cli_mod, "run_evaluation",
                        lambda *a, **k: (_ for _ in ()).throw(EvalSchemaError("报告坏")))
    monkeypatch.setattr(cli_mod, "validate_file", lambda *a, **k: None)
    monkeypatch.setattr(cli_mod, "get_git_provenance",
                        lambda r: {"git_commit": None, "git_dirty": False})
    rc = main(["run", "--manifest", str(mf), "--output", str(tmp_path / "o.json")])
    assert rc == 1
    assert "生成的报告未通过 Schema 校验" in capsys.readouterr().err


def test_run_selfvalidate_fail_batch53(monkeypatch, tmp_path, capsys):
    _patch_run(monkeypatch, tmp_path)

    def boom(*a, **k):
        raise EvalSchemaError("自校验炸了")
    monkeypatch.setattr(cli_mod, "validate_file", boom)
    rc = main(["run", "--manifest", str(tmp_path / "manifest.json"),
               "--output", str(tmp_path / "o.json")])
    assert rc == 1
    assert "报告自校验失败" in capsys.readouterr().err


def test_run_manifest_is_directory_batch53(tmp_path, capsys):
    rc = main(["run", "--manifest", str(tmp_path), "--output", str(tmp_path / "o.json")])
    assert rc == 2
    assert "清单不存在" in capsys.readouterr().err


# ---------- validate-report ----------

def _patch_validate(monkeypatch, exc):
    monkeypatch.setattr(cli_mod, "validate_file",
                        lambda *a, **k: (_ for _ in ()).throw(exc))


def test_val_report_schema_fail_batch53(monkeypatch, tmp_path, capsys):
    f = tmp_path / "r.json"
    f.write_text("{}", encoding="utf-8")
    _patch_validate(monkeypatch, EvalSchemaError("缺字段"))
    rc = main(["validate-report", str(f)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err
    assert "报告校验失败：缺字段" in err


def test_val_report_file_not_found_batch53(monkeypatch, tmp_path, capsys):
    f = tmp_path / "r.json"
    f.write_text("{}", encoding="utf-8")
    _patch_validate(monkeypatch, FileNotFoundError("schema 丢了个"))
    rc = main(["validate-report", str(f)])
    assert rc == 2
    assert "schema 丢了个" in capsys.readouterr().err


def test_val_report_jsondecode_batch53(monkeypatch, tmp_path, capsys):
    f = tmp_path / "r.json"
    f.write_text("{}", encoding="utf-8")
    _patch_validate(monkeypatch, json.JSONDecodeError("Expecting value", "", 0))
    rc = main(["validate-report", str(f)])
    assert rc == 1
    assert "JSON 解析失败" in capsys.readouterr().err


def test_val_report_ok_stdout_batch53(monkeypatch, tmp_path, capsys):
    f = tmp_path / "r.json"
    f.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(cli_mod, "validate_file", lambda *a, **k: None)
    rc = main(["validate-report", str(f)])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("[OK]")
    assert "通过 evaluation-report Schema 校验" in out


def test_val_report_missing_file_real_batch53(tmp_path, capsys):
    rc = main(["validate-report", str(tmp_path / "ghost.json")])
    assert rc == 2
    assert "报告不存在" in capsys.readouterr().err


# ---------- inspect-doc ----------

def test_inspect_doc_defaults_batch53(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text("{}", encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "document_id: ?" in out
    assert "parser:      ? v?" in out
    assert "source:      ?  type=unknown" in out
    assert "counts:      elements=0 chunks=0" in out


def test_inspect_doc_metadata_present_batch53(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text(json.dumps({
        "document_id": "doc-9", "source_path": "a.pdf", "source_type": "pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [{}], "chunks": [{}, {}],
    }), encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "document_id: doc-9" in out
    assert "parser:      fallback v1.0" in out
    assert "source:      a.pdf  type=pdf" in out
    assert "counts:      elements=1 chunks=2" in out


def test_inspect_doc_top_level_list_batch53(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text("[1, 2]", encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 1
    assert "[ERROR] JSON 顶层不是对象" in capsys.readouterr().err


def test_inspect_doc_jsondecode_real_batch53(tmp_path, capsys):
    f = tmp_path / "d.json"
    f.write_text("not json", encoding="utf-8")
    rc = main(["inspect-doc", str(f)])
    assert rc == 1
    assert "JSON 解析失败" in capsys.readouterr().err


def test_inspect_doc_missing_real_batch53(tmp_path, capsys):
    rc = main(["inspect-doc", str(tmp_path / "ghost.json")])
    assert rc == 2
    assert "文档不存在" in capsys.readouterr().err


def test_inspect_doc_tolerance_passthrough_batch53(monkeypatch, tmp_path):
    import evaluation.annotation_metrics as am
    f = tmp_path / "d.json"
    f.write_text("{}", encoding="utf-8")
    captured = {}

    def fake_fig(d, a):
        captured["fig"] = (d, a)
        return {}

    def fake_cb(d, a, *, tolerance_chars):
        captured["cb"] = (a, tolerance_chars)
        return {}
    monkeypatch.setattr(am, "figure_caption_prf", fake_fig)
    monkeypatch.setattr(am, "chunk_boundary_prf", fake_cb)
    rc = main(["inspect-doc", str(f), "--tolerance-chars", "9"])
    assert rc == 0
    assert captured["fig"][1] is None
    assert captured["cb"] == (None, 9)


# ---------- _format_metric ----------

def test_format_metric_dict_sorted_batch53():
    line = _format_metric("x", {"value": {"b": 2, "a": 1}, "reason": None})
    assert line == "  x" + " " * 36 + "a=1, b=2  (ok)"


def test_format_metric_int_batch53():
    assert _format_metric("n", {"value": 5, "reason": None}) == \
        "  n" + " " * 36 + "5  (ok)"


def test_format_metric_str_value_batch53():
    assert _format_metric("s", {"value": "x", "reason": None}) == \
        "  s" + " " * 36 + "x  (ok)"


def test_format_metric_bool_batch53():
    assert _format_metric("p", {"value": True, "reason": None}) == \
        "  p" + " " * 36 + "true  (ok)"
    assert _format_metric("p", {"value": False, "reason": None}) == \
        "  p" + " " * 36 + "false  (ok)"


def test_format_metric_null_reason_batch53():
    assert _format_metric("z", {"value": None, "reason": "r"}) == \
        "  z" + " " * 36 + "null  (r)"


def test_format_metric_float_batch53():
    assert _format_metric("f", {"value": 0.5, "reason": None}) == \
        "  f" + " " * 36 + "0.5000  (ok)"


# ---------- argparse ----------

def test_parser_inspect_tolerance_rejects_float_batch53():
    with pytest.raises(SystemExit) as ei:
        _build_parser().parse_args(["inspect-doc", "x.json",
                                    "--tolerance-chars", "1.5"])
    assert ei.value.code == 2


def test_parser_run_requires_manifest_batch53():
    with pytest.raises(SystemExit) as ei:
        _build_parser().parse_args(["run", "--output", "o.json"])
    assert ei.value.code == 2


def test_parser_run_full_defaults_batch53():
    args = _build_parser().parse_args(
        ["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.command == "run"
    assert args.parser == "fallback"
    assert args.max_chars == 800
    assert args.tolerance_chars == 30


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(cli_mod)


def test_source_error_and_stderr_counts_batch53():
    src = _src()
    assert src.count("[ERROR]") == 10
    assert src.count("sys.stderr") == 12


def test_source_print_reconfigure_counts_batch53():
    src = _src()
    assert src.count("print(") == 21
    assert src.count("reconfigure") == 3
    assert src.count("isinstance(") == 6


def test_source_key_lines_batch53():
    src = _src()
    assert "args.tolerance_chars," in src
    assert "parser_name=args.parser," in src
    assert "max_chars=args.max_chars," in src
    assert "validate_file(output_path, \"evaluation-report.schema.json\")" in src
    assert "if not isinstance(doc, dict):" in src


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(cli_mod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _counts(func) -> dict:
    import collections
    return collections.Counter(type(n).__name__ for n in ast.walk(func))


def test_ast_main_counts_batch53():
    c = _counts(_func("main"))
    assert (c["If"], c["Try"], c["Return"]) == (5, 4, 12)


def test_ast_inspect_doc_counts_batch53():
    c = _counts(_func("_run_inspect_doc"))
    assert (c["If"], c["Try"], c["Return"], c["For"], c["FunctionDef"]) == \
        (5, 1, 8, 1, 2)  # FunctionDef 含自身 + 嵌套 _sort_key


def test_ast_format_metric_counts_batch53():
    c = _counts(_func("_format_metric"))
    assert (c["If"], c["Return"]) == (4, 5)


def test_ast_build_parser_counts_batch53():
    c = _counts(_func("_build_parser"))
    assert (c["If"], c["Try"], c["Return"]) == (0, 0, 1)


def test_ast_module_guards_batch53():
    import collections
    mod = collections.Counter(type(n).__name__ for n in _tree().body)
    # hasattr 守卫 + __main__ 守卫；try 嵌套在 if 内不在顶层
    assert (mod["If"], mod["Try"]) == (2, 0)


# ---------- forbidden tokens 第一百九十批 ----------

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
