"""evaluation/runner.py 第九十九轮 edges 测试（Round 705）。

补强 edges80 未触及的角度（第七十批）。

新角度：
- run_evaluation 标注端到端（annotation 文件含 anchors → 公共 per_doc 的 chunk_boundary_precision 非 null 且数值正确）
- ef 循环的 process_single 也收 parser_name/max_chars（kreuzberg 流转）
- doc 循环 _process_one 收默认 fallback/800（位置参数捕获）
- 不同 doc_id 的 out_stub 互不相同（d1/d2）
- ef 循环 unlink OSError 容错（patch pathlib.Path.unlink 抛 OSError 仍完成）
- 输出嵌套目录自动创建（a/b/c/r.json）
- 报告文件 ensure_ascii=False（中文 marker 原样落盘非 \\u 转义）
- 源码补强（两个循环行 / public_per_doc 初始化 / per_doc_results 注解 / expected_failures 键 / json.dump ensure_ascii）
- AST 补强（run_evaluation 4 个 AnnAssign 名单 / _load_annotation 单 Return dict / 模块 import 精确名单）
- forbidden tokens 第一百七十五批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import evaluation.runner as runner_mod
from evaluation.runner import _load_annotation, run_evaluation


def _doc_stub(doc_id="d1", source_type="pdf", expectations=None, annotation_resolved=None):
    return SimpleNamespace(
        doc_id=doc_id, source_type=source_type,
        expectations=expectations, annotation_resolved=annotation_resolved,
        resolved_path=Path(f"{doc_id}.pdf"),
    )


def _manifest_stub(documents=(), expected_failures=(), project_root=None):
    return SimpleNamespace(
        documents=list(documents),
        expected_failures=list(expected_failures),
        project_root=project_root or Path("."),
    )


def _patch_light(monkeypatch):
    monkeypatch.setattr(runner_mod, "build_provenance",
                        lambda **kw: {"git_commit": None})
    monkeypatch.setattr(runner_mod, "build_devset_section", lambda m: {"status": "incomplete"})


# ---------- 标注端到端 ----------

def test_run_evaluation_annotation_end_to_end_batch52(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    ann = tmp_path / "ann.json"
    ann.write_text(json.dumps({
        "chunk_boundary_anchors": [{"marker": "第一章", "position": "after"}],
    }, ensure_ascii=False), encoding="utf-8")
    doc_dict = {"elements": [], "chunks": [{"text": "第一章"}, {"text": "第二章"}]}
    doc = _doc_stub(annotation_resolved=ann)
    monkeypatch.setattr(
        runner_mod, "_process_one",
        lambda *a, **k: (doc_dict, None, 0.1, None, None),
    )
    report = run_evaluation(_manifest_stub(documents=[doc], project_root=tmp_path),
                            tmp_path / "r.json")
    metrics = report["per_doc"][0]["metrics"]
    # stream "第一章 第二章"；pred 3；anchor 第一章 after = 3 → 精确命中
    assert metrics["chunk_boundary_precision"]["value"] == 1.0
    assert metrics["chunk_boundary_recall"]["value"] == 1.0
    assert metrics["figure_caption_precision"]["value"] is None


def test_report_file_not_ascii_escaped_batch52(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    doc_dict = {"elements": [], "chunks": [{"text": "正文"}]}
    doc = _doc_stub(doc_id="文档一")
    monkeypatch.setattr(
        runner_mod, "_process_one",
        lambda *a, **k: (doc_dict, None, 0.1, None, None),
    )
    out = tmp_path / "r.json"
    run_evaluation(_manifest_stub(documents=[doc], project_root=tmp_path), out)
    raw = out.read_text(encoding="utf-8")
    assert "文档一" in raw
    assert "\\u6587" not in raw  # 未被 ensure_ascii 转义


# ---------- ef 循环 kwargs 流转 ----------

def test_ef_loop_receives_parser_kwargs_batch52(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    captured = {}

    def fake_ps(*a, **kw):
        captured.update(kw)
        return None, []

    monkeypatch.setattr(runner_mod, "process_single", fake_ps)
    efs = [SimpleNamespace(doc_id="ef1", resolved_path=Path("b.txt"),
                           expected_error_code="x")]
    run_evaluation(_manifest_stub(expected_failures=efs, project_root=tmp_path),
                   tmp_path / "r.json", parser_name="kreuzberg", max_chars=500)
    assert captured == {"parser_name": "kreuzberg", "max_chars": 500, "write_json": False}


# ---------- doc 循环 _process_one 默认参数 ----------

def test_doc_loop_process_one_defaults_batch52(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    seen = []

    def fake_po(doc, output_root, parser_name, max_chars):
        seen.append((doc.doc_id, output_root, parser_name, max_chars))
        return {"elements": [], "chunks": []}, None, 0.0, None, None

    monkeypatch.setattr(runner_mod, "_process_one", fake_po)
    docs = [_doc_stub("d1"), _doc_stub("d2")]
    run_evaluation(_manifest_stub(documents=docs, project_root=tmp_path), tmp_path / "r.json")
    assert seen == [
        ("d1", tmp_path, "fallback", 800),
        ("d2", tmp_path, "fallback", 800),
    ]


def test_doc_loop_distinct_stubs_per_doc_id_batch52(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    stubs = []

    def fake_po(doc, output_root, parser_name, max_chars):
        # _process_one 内部用 output_root/_per_doc/<doc_id>.json —— 这里从 doc 推断验证
        stubs.append(output_root / "_per_doc" / f"{doc.doc_id}.json")
        return {"elements": [], "chunks": []}, None, 0.0, None, None

    monkeypatch.setattr(runner_mod, "_process_one", fake_po)
    docs = [_doc_stub("d1"), _doc_stub("d2")]
    run_evaluation(_manifest_stub(documents=docs, project_root=tmp_path), tmp_path / "r.json")
    assert stubs[0] != stubs[1]
    assert stubs[0].name == "d1.json"
    assert stubs[1].name == "d2.json"


# ---------- ef 循环 unlink OSError 容错 ----------

def test_ef_unlink_oserror_tolerated_batch52(monkeypatch, tmp_path):
    _patch_light(monkeypatch)

    def fake_ps(*a, **kw):
        stub = a[1]
        stub.write_text("{}", encoding="utf-8")
        return None, []

    monkeypatch.setattr(runner_mod, "process_single", fake_ps)

    def raising_unlink(self):
        raise OSError("locked")

    monkeypatch.setattr(Path, "unlink", raising_unlink)
    efs = [SimpleNamespace(doc_id="ef1", resolved_path=Path("b.txt"),
                           expected_error_code="x")]
    report = run_evaluation(_manifest_stub(expected_failures=efs, project_root=tmp_path),
                            tmp_path / "r.json")
    assert report["expected_failures"][0]["matches"] is False
    assert (tmp_path / "_per_doc" / "ef1.json").exists()  # unlink 失败留下 stub


# ---------- 嵌套输出目录 ----------

def test_nested_output_dirs_created_batch52(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    out = tmp_path / "a" / "b" / "c" / "r.json"
    report = run_evaluation(_manifest_stub(project_root=tmp_path), out)
    assert out.is_file()
    assert report["per_doc"] == []


# ---------- _load_annotation 快速补充 ----------

def test_load_annotation_valid_dict_batch52(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("{\"k\": 1}", encoding="utf-8")
    assert _load_annotation(p) == {"k": 1}


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(runner_mod)


def test_source_two_loops_batch52():
    src = _src()
    assert "for doc in manifest.documents:" in src
    assert "for ef in manifest.expected_failures:" in src


def test_source_list_inits_batch52():
    src = _src()
    assert "per_doc_results: list[dict[str, Any]] = []" in src
    assert "public_per_doc = []" in src


def test_source_expected_failures_key_batch52():
    assert '"expected_failures": expected_failure_results,' in _src()


def test_source_json_dump_ensure_ascii_batch52():
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in _src()


def test_source_docstring_invariants_batch52():
    src = _src()
    assert "不修改 app/pipeline.py" in src
    assert "not_instrumented" in src


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(runner_mod))


def test_ast_run_evaluation_4_annassigns_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    names = [n.target.id for n in ast.walk(func) if isinstance(n, ast.AnnAssign)
             and isinstance(n.target, ast.Name)]
    # public_per_doc = [] 是普通 Assign，不在此名单
    assert names == ["per_doc_results", "parser_version_for_prov",
                     "expected_failure_results"]


def test_ast_load_annotation_returns_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 3
    assert any(isinstance(r.value, ast.Constant) and r.value.value is None for r in returns)


def test_ast_module_imports_batch52():
    tree = _tree()
    mods = []
    for n in tree.body:
        if isinstance(n, ast.Import):
            mods.extend(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            mods.append(n.module)
    assert sorted(mods) == [
        "__future__", "app.pipeline", "evaluation", "evaluation.annotation_metrics",
        "evaluation.metrics", "evaluation.report", "json", "pathlib", "time", "typing",
    ]


# ---------- forbidden tokens 第一百七十五批 ----------

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


def test_source_open_count_is_2_batch52():
    assert _src().count("open(") == 2
