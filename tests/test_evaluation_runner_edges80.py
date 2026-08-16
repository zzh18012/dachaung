"""evaluation/runner.py 第九十八轮 edges 测试（Round 698）。

补强 edges79 未触及的角度（第六十三批）。

新角度：
- _load_annotation 深挖（目录输入 → None / JSON 数组原样返回 list / 空文件 → None / BOM 文件 → None）
- _process_one 四分支（errors 非空取 errors[0].to_dict / document+errors 同时存在 → image_dir 仍返回 / 双 None → unknown 错误 dict / 成功 → to_dict+parser_version+image_dir）
- _process_one unlink out_stub（fake process_single 落盘 stub → 调用后已删除）
- run_evaluation doc 循环全链路（mock _process_one → per_doc 公共 4 键 / wall_time_seconds 5 键精确 / _annotation_present·_tolerance·_missing 不进公共 / 输出文件 == 返回 dict）
- parser_version_for_prov 首个非 None 胜（1.0 先于 2.0 / None 先则取后续 9 / 全 None → None）
- image_base_dir 门控（存在的目录透传 / 非目录 → None）
- build_provenance 收 kwargs（parser_name/max_chars/parser_version 透传）
- output_path 传 str 也可
- 空清单端到端（per_doc [] / expected_failures [] / 文件写出）
- 源码补强（image_dir 注解 / if document is not None / image_output_dir_for 调用 / unknown 消息 / errors[0].to_dict / parser_version 首个条件 / _annotation_present / matches 表达式 / actual_code 三元 / public 4 键字面）
- AST 补强（_load_annotation Or 条件 + except 元组 / _process_one 3 个 Return 首个是 5 元 Tuple / 内部 per_doc 7 键顺序 / app.pipeline ImportFrom 双名 / doc 循环先于 ef 循环）
- forbidden tokens 第一百六十八批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import evaluation.runner as runner_mod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


def _doc_stub(doc_id="d1", source_type="pdf", expectations=None, annotation_resolved=None):
    return SimpleNamespace(
        doc_id=doc_id, source_type=source_type,
        expectations=expectations, annotation_resolved=annotation_resolved,
        resolved_path=Path("x.pdf"),
    )


def _manifest_stub(documents=(), expected_failures=(), project_root=None):
    return SimpleNamespace(
        documents=list(documents),
        expected_failures=list(expected_failures),
        project_root=project_root or Path("."),
    )


class _Doc:
    parser_version = "1.2.3"
    source_hash = "h" * 64

    def to_dict(self):
        return {"document_id": "x", "elements": [], "chunks": []}


class _Err:
    def __init__(self, code):
        self.code = code

    def to_dict(self):
        return {"code": self.code}


# ---------- _load_annotation 深挖 ----------

def test_load_annotation_directory_is_none_batch52(tmp_path):
    d = tmp_path / "adir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_json_array_passthrough_batch52(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("[1, 2]", encoding="utf-8")
    assert _load_annotation(p) == [1, 2]


def test_load_annotation_empty_file_none_batch52(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_bom_file_none_batch52(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("﻿{}", encoding="utf-8")
    assert _load_annotation(p) is None


# ---------- _process_one 四分支 ----------

def test_process_one_errors_first_used_batch52(monkeypatch, tmp_path):
    monkeypatch.setattr(
        runner_mod, "process_single",
        lambda *a, **k: (None, [_Err("e1"), _Err("e2")]),
    )
    document, error, elapsed, pv, img = _process_one(_doc_stub(), tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "e1"}
    assert pv is None
    assert img is None
    assert elapsed >= 0


def test_process_one_document_with_errors_keeps_image_dir_batch52(monkeypatch, tmp_path):
    monkeypatch.setattr(
        runner_mod, "process_single",
        lambda *a, **k: (_Doc(), [_Err("boom")]),
    )
    document, error, _, _, img = _process_one(_doc_stub(), tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "boom"}
    assert img is not None


def test_process_one_both_none_unknown_error_batch52(monkeypatch, tmp_path):
    monkeypatch.setattr(runner_mod, "process_single", lambda *a, **k: (None, []))
    document, error, _, pv, img = _process_one(_doc_stub(), tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "unknown", "message": "process_single returned None without errors"}
    assert pv is None
    assert img is None


def test_process_one_success_batch52(monkeypatch, tmp_path):
    from app.pipeline import image_output_dir_for
    monkeypatch.setattr(runner_mod, "process_single", lambda *a, **k: (_Doc(), []))
    document, error, _, pv, img = _process_one(_doc_stub(), tmp_path, "fallback", 800)
    assert document == {"document_id": "x", "elements": [], "chunks": []}
    assert error is None
    assert pv == "1.2.3"
    stub = tmp_path / "_per_doc" / "d1.json"
    assert img == image_output_dir_for(stub, "h" * 64)


def test_process_one_unlinks_stub_file_batch52(monkeypatch, tmp_path):
    def fake_ps(*a, **k):
        stub = a[1]
        stub.write_text("{}", encoding="utf-8")
        return None, []
    monkeypatch.setattr(runner_mod, "process_single", fake_ps)
    _process_one(_doc_stub(), tmp_path, "fallback", 800)
    assert not (tmp_path / "_per_doc" / "d1.json").exists()


def test_process_one_creates_per_doc_dir_batch52(monkeypatch, tmp_path):
    monkeypatch.setattr(runner_mod, "process_single", lambda *a, **k: (None, []))
    _process_one(_doc_stub(), tmp_path / "out", "fallback", 800)
    assert (tmp_path / "out" / "_per_doc").is_dir()


# ---------- run_evaluation doc 循环全链路 ----------

def _patch_light(monkeypatch, captured=None):
    if captured is None:
        captured = {}
    monkeypatch.setattr(
        runner_mod, "build_provenance",
        lambda **kw: (captured.update(kw), {"git_commit": None})[1],
    )
    monkeypatch.setattr(runner_mod, "build_devset_section", lambda m: {"status": "incomplete"})
    return captured


def test_run_evaluation_doc_loop_full_batch52(monkeypatch, tmp_path):
    captured = _patch_light(monkeypatch)
    fake_doc = {"document_id": "x", "elements": [], "chunks": []}
    monkeypatch.setattr(
        runner_mod, "_process_one",
        lambda *a, **k: (fake_doc, None, 1.5, "0.9", None),
    )
    m = _manifest_stub(documents=[_doc_stub()], project_root=tmp_path)
    out = tmp_path / "rep.json"
    report = run_evaluation(m, out)
    entry = report["per_doc"][0]
    assert entry["doc_id"] == "d1"
    assert entry["source_type"] == "pdf"
    assert entry["metrics"]["pipeline_success"]["value"] is True
    assert entry["wall_time_seconds"] == {
        "total": 1.5, "parse": None, "chunk": None,
        "parse_reason": "not_instrumented", "chunk_reason": "not_instrumented",
    }
    # 内部字段不进公共报告
    for k in ("_annotation_present", "_tolerance_chars", "_missing_markers"):
        assert k not in entry
    # provenance kwargs 透传
    assert captured["parser_version"] == "0.9"
    assert captured["parser_name"] == "fallback"
    assert captured["max_chars"] == 800
    # 文件内容 == 返回 dict
    assert json.loads(out.read_text(encoding="utf-8")) == report


def test_run_evaluation_str_output_path_batch52(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    out = run_evaluation(_manifest_stub(), str(tmp_path / "r.json"))
    assert out["per_doc"] == []
    assert out["expected_failures"] == []
    assert (tmp_path / "r.json").is_file()


# ---------- parser_version 首个非 None 胜 ----------

def _run_with_versions(monkeypatch, tmp_path, versions):
    captured = _patch_light(monkeypatch)
    it = iter(versions)
    fake_doc = {"elements": [], "chunks": []}
    monkeypatch.setattr(
        runner_mod, "_process_one",
        lambda *a, **k: (fake_doc, None, 0.1, next(it), None),
    )
    docs = [_doc_stub("d1"), _doc_stub("d2"), _doc_stub("d3")]
    run_evaluation(_manifest_stub(documents=docs, project_root=tmp_path), tmp_path / "r.json")
    return captured["parser_version"]


def test_parser_version_first_wins_batch52(monkeypatch, tmp_path):
    assert _run_with_versions(monkeypatch, tmp_path, ["1.0", "2.0", "3.0"]) == "1.0"


def test_parser_version_none_then_value_batch52(monkeypatch, tmp_path):
    assert _run_with_versions(monkeypatch, tmp_path, [None, "9", None]) == "9"


def test_parser_version_all_none_batch52(monkeypatch, tmp_path):
    assert _run_with_versions(monkeypatch, tmp_path, [None, None, None]) is None


# ---------- image_base_dir 门控 ----------

def test_image_base_dir_dir_passthrough_batch52(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    imgs = tmp_path / "imgs"
    imgs.mkdir()
    captured = {}

    def fake_compute(**kwargs):
        captured.update(kwargs)
        return {}

    monkeypatch.setattr(runner_mod, "compute_automatic_metrics", fake_compute)
    fake_doc = {"elements": [], "chunks": []}
    monkeypatch.setattr(
        runner_mod, "_process_one",
        lambda *a, **k: (fake_doc, None, 0.0, None, imgs),
    )
    run_evaluation(_manifest_stub(documents=[_doc_stub()], project_root=tmp_path), tmp_path / "r.json")
    assert captured["image_base_dir"] == imgs


def test_image_base_dir_non_dir_gated_none_batch52(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    captured = {}

    def fake_compute(**kwargs):
        captured.update(kwargs)
        return {}

    monkeypatch.setattr(runner_mod, "compute_automatic_metrics", fake_compute)
    fake_doc = {"elements": [], "chunks": []}
    ghost = tmp_path / "no-such-dir"
    monkeypatch.setattr(
        runner_mod, "_process_one",
        lambda *a, **k: (fake_doc, None, 0.0, None, ghost),
    )
    run_evaluation(_manifest_stub(documents=[_doc_stub()], project_root=tmp_path), tmp_path / "r.json")
    assert captured["image_base_dir"] is None


def test_image_base_dir_none_passthrough_batch52(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    captured = {}

    def fake_compute(**kwargs):
        captured.update(kwargs)
        return {}

    monkeypatch.setattr(runner_mod, "compute_automatic_metrics", fake_compute)
    fake_doc = {"elements": [], "chunks": []}
    monkeypatch.setattr(
        runner_mod, "_process_one",
        lambda *a, **k: (fake_doc, None, 0.0, None, None),
    )
    run_evaluation(_manifest_stub(documents=[_doc_stub()], project_root=tmp_path), tmp_path / "r.json")
    assert captured["image_base_dir"] is None


# ---------- expected_failures 结果形状 ----------

def test_expected_failures_matches_shape_batch52(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    monkeypatch.setattr(
        runner_mod, "process_single",
        lambda *a, **k: (None, [_Err("unsupported_format")]),
    )
    efs = [SimpleNamespace(doc_id="ef1", resolved_path=Path("b.txt"),
                           expected_error_code="unsupported_format")]
    report = run_evaluation(_manifest_stub(expected_failures=efs, project_root=tmp_path),
                            tmp_path / "r.json")
    assert report["expected_failures"] == [
        {"doc_id": "ef1", "expected_error_code": "unsupported_format",
         "actual_error_code": "unsupported_format", "matches": True},
    ]


def test_expected_failures_mismatch_shape_batch52(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    monkeypatch.setattr(runner_mod, "process_single", lambda *a, **k: (None, []))
    efs = [SimpleNamespace(doc_id="ef1", resolved_path=Path("b.txt"),
                           expected_error_code="boom")]
    report = run_evaluation(_manifest_stub(expected_failures=efs, project_root=tmp_path),
                            tmp_path / "r.json")
    entry = report["expected_failures"][0]
    assert entry["actual_error_code"] is None
    assert entry["matches"] is False


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(runner_mod)


def test_source_image_dir_annotation_batch52():
    assert "image_dir: Path | None = None" in _src()


def test_source_if_document_not_none_batch52():
    assert "if document is not None:" in _src()


def test_source_image_output_dir_call_batch52():
    assert "image_output_dir_for(out_stub, document.source_hash)" in _src()


def test_source_unknown_message_batch52():
    assert "process_single returned None without errors" in _src()


def test_source_errors_first_to_dict_batch52():
    assert "errors[0].to_dict()" in _src()


def test_source_parser_version_first_condition_batch52():
    assert "if parser_version and not parser_version_for_prov:" in _src()


def test_source_annotation_present_key_batch52():
    assert '"_annotation_present": annotation is not None' in _src()


def test_source_matches_expression_batch52():
    assert '"matches": actual_code == ef.expected_error_code' in _src()


def test_source_actual_code_ternary_batch52():
    assert "actual_code = errors[0].code if errors else None" in _src()


def test_source_public_dict_4_keys_batch52():
    src = _src()
    assert '"doc_id": r["doc_id"],' in src
    assert '"source_type": r["source_type"],' in src
    assert '"metrics": r["metrics"],' in src
    assert '"wall_time_seconds": r["wall_time_seconds"],' in src


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(runner_mod))


def test_ast_load_annotation_or_condition_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation")
    first_if = func.body[0]
    assert isinstance(first_if.test, ast.BoolOp) and isinstance(first_if.test.op, ast.Or)
    src = ast.unparse(func)
    assert "if path is None or not path.is_file():" in src
    assert "except (OSError, json.JSONDecodeError):" in src


def test_ast_process_one_3_returns_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 3
    for r in returns:
        assert isinstance(r.value, ast.Tuple) and len(r.value.elts) == 5


def test_ast_internal_per_doc_7_keys_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    appends = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "append"
    ]
    assert len(appends) == 3  # per_doc_results / expected_failure_results / public_per_doc
    internal = appends[0].args[0]
    keys = [k.value for k in internal.keys]
    assert keys == [
        "doc_id", "source_type", "metrics", "wall_time_seconds",
        "_annotation_present", "_tolerance_chars", "_missing_markers",
    ]
    ef = appends[1].args[0]
    assert [k.value for k in ef.keys] == [
        "doc_id", "expected_error_code", "actual_error_code", "matches",
    ]
    public = appends[2].args[0]
    assert [k.value for k in public.keys] == ["doc_id", "source_type", "metrics", "wall_time_seconds"]


def test_ast_app_pipeline_import_batch52():
    tree = _tree()
    imp = next(n for n in tree.body if isinstance(n, ast.ImportFrom) and n.module == "app.pipeline")
    assert sorted(a.name for a in imp.names) == ["image_output_dir_for", "process_single"]


def test_ast_doc_loop_before_ef_loop_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    loops = [n for n in func.body if isinstance(n, ast.For)]
    srcs = [ast.unparse(l.iter) for l in loops[:3]]
    assert srcs[0] == "manifest.documents"
    assert srcs[1] == "manifest.expected_failures"
    assert srcs[2] == "per_doc_results"


# ---------- forbidden tokens 第一百六十八批 ----------

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
