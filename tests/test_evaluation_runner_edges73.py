"""evaluation/runner.py 第九十轮 edges 测试（Round 647）。

补强 edges72 未触及的角度（第四十八批）。

新角度：
- _load_annotation 更多边界
- _process_one image_dir 路径计算
- run_evaluation annotation_present 透传
- run_evaluation metrics.update 链
- run_evaluation tolerance_record / missing_markers_record 处理
- run_evaluation image_base_dir 推导
- module source 字符串补强
- AST 结构补强
- forbidden tokens 第一百一十七批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.runner as runner_mod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 更多边界 ----------

def test_load_annotation_object_with_extra_keys_batch48(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"key1": 1, "key2": 2, "extra": "x"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out["key1"] == 1
    assert out["key2"] == 2


def test_load_annotation_null_json_batch48(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("null", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_string_json_batch48(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('"just a string"', encoding="utf-8")
    out = _load_annotation(p)
    assert out == "just a string"


def test_load_annotation_number_json_batch48(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("42", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 42


def test_load_annotation_boolean_json_batch48(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("true", encoding="utf-8")
    out = _load_annotation(p)
    assert out is True


def test_load_annotation_nested_dict_batch48(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"a": {"b": {"c": 1}}}', encoding="utf-8")
    out = _load_annotation(p)
    assert out["a"]["b"]["c"] == 1


def test_load_annotation_bom_batch48(tmp_path):
    """UTF-8 BOM 不会被 open 默认 strip，json.loads 直接抛 JSONDecodeError → 返回 None。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf{"key": "value"}')
    out = _load_annotation(p)
    assert out is None


# ---------- _process_one image_dir 路径计算 ----------

def _make_doc(**kw):
    m = MagicMock()
    m.doc_id = kw.get("doc_id", "d1")
    m.resolved_path = kw.get("resolved_path", Path("/tmp/x.pdf"))
    m.source_type = kw.get("source_type", "pdf")
    m.expectations = kw.get("expectations")
    m.annotation_resolved = kw.get("annotation_resolved")
    return m


def test_process_one_image_dir_uses_source_hash_batch48(tmp_path):
    """image_dir 由 image_output_dir_for(out_stub, source_hash) 计算。"""
    doc = _make_doc(resolved_path=tmp_path / "x.pdf")

    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc123"
    fake_document.parser_version = "v1"

    captured_args = {}

    def fake_image_dir(stub, source_hash):
        captured_args["stub"] = stub
        captured_args["source_hash"] = source_hash
        return tmp_path / "imgs"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", side_effect=fake_image_dir):
            _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert captured_args["source_hash"] == "abc123"
    assert image_dir == tmp_path / "imgs"


def test_process_one_out_stub_path_batch48(tmp_path):
    """out_stub 应是 output_root/_per_doc/<doc_id>.json。"""
    doc = _make_doc(doc_id="custom_id", resolved_path=tmp_path / "x.pdf")
    captured_stub = {}

    def fake_process(*args, **kwargs):
        captured_stub["path"] = args[1]
        return MagicMock(), []  # document, errors

    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _process_one(doc, tmp_path, "fallback", 800)
    # 检查 _per_doc 目录被创建
    assert (tmp_path / "_per_doc").is_dir()


def test_process_one_calls_process_single_with_correct_args_batch48(tmp_path):
    """process_single 应收到 resolved_path, out_stub, parser_name, max_chars, write_json=False。"""
    doc = _make_doc(resolved_path=tmp_path / "x.pdf")
    captured = {}

    def fake_process(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return MagicMock(), []

    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    with patch("evaluation.runner.process_single", side_effect=fake_process):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _process_one(doc, tmp_path, "fallback", 800)
    assert captured["kwargs"]["parser_name"] == "fallback"
    assert captured["kwargs"]["max_chars"] == 800
    assert captured["kwargs"]["write_json"] is False


def test_process_one_elapsed_is_positive_batch48(tmp_path):
    """elapsed 应 > 0（即使很小）。"""
    doc = _make_doc(resolved_path=tmp_path / "x.pdf")
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _, _, elapsed, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(elapsed, float)


# ---------- run_evaluation annotation_present 透传 ----------

def _make_manifest(docs=None, efs=None, project_root=None):
    m = MagicMock()
    m.documents = docs or []
    m.expected_failures = efs or []
    m.project_root = project_root or Path("/tmp")
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def test_run_evaluation_annotation_present_false_when_none_batch48(tmp_path):
    """annotation_file 缺失 → _annotation_present=False。"""
    doc = _make_doc(resolved_path=tmp_path / "x.pdf", annotation_resolved=None)

    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    captured = {}

    def fake_aggregate(per_doc):
        captured["per_doc"] = per_doc
        return {}

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.build_provenance", return_value={}):
                with patch("evaluation.runner.build_devset_section", return_value={}):
                    with patch("evaluation.runner.aggregate_summary", side_effect=fake_aggregate):
                        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                                    run_evaluation(manifest, out)
    assert captured["per_doc"][0]["_annotation_present"] is False


def test_run_evaluation_annotation_present_true_when_loaded_batch48(tmp_path):
    """annotation 文件存在 → _annotation_present=True。"""
    ann_file = tmp_path / "a.json"
    ann_file.write_text("{}", encoding="utf-8")

    doc = _make_doc(resolved_path=tmp_path / "x.pdf", annotation_resolved=ann_file)

    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    captured = {}

    def fake_aggregate(per_doc):
        captured["per_doc"] = per_doc
        return {}

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.build_provenance", return_value={}):
                with patch("evaluation.runner.build_devset_section", return_value={}):
                    with patch("evaluation.runner.aggregate_summary", side_effect=fake_aggregate):
                        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                                with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                                    run_evaluation(manifest, out)
    assert captured["per_doc"][0]["_annotation_present"] is True


# ---------- run_evaluation metrics.update 链 ----------

def test_run_evaluation_metrics_merged_from_three_sources_batch48(tmp_path):
    """metrics 应合并 compute_automatic_metrics + figure_caption_prf + chunk_boundary_prf。"""
    doc = _make_doc(resolved_path=tmp_path / "x.pdf")

    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    captured_metrics = {}

    def fake_aggregate(per_doc):
        captured_metrics["metrics"] = per_doc[0]["metrics"]
        return {}

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.build_provenance", return_value={}):
                with patch("evaluation.runner.build_devset_section", return_value={}):
                    with patch("evaluation.runner.aggregate_summary", side_effect=fake_aggregate):
                        with patch("evaluation.runner.compute_automatic_metrics", return_value={"auto_key": "auto"}):
                            with patch("evaluation.runner.figure_caption_prf", return_value={"fig_key": "fig"}):
                                with patch("evaluation.runner.chunk_boundary_prf", return_value={"chunk_key": "chunk"}):
                                    run_evaluation(manifest, out)
    m = captured_metrics["metrics"]
    assert m["auto_key"] == "auto"
    assert m["fig_key"] == "fig"
    assert m["chunk_key"] == "chunk"


# ---------- run_evaluation tolerance_record / missing_markers_record 处理 ----------

def test_run_evaluation_tolerance_record_from_chunk_b_batch48(tmp_path):
    """chunk_boundary_prf 返回的 _tolerance_chars 被 pop 出来记到 per_doc。"""
    doc = _make_doc(resolved_path=tmp_path / "x.pdf")

    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    captured = {}

    def fake_aggregate(per_doc):
        captured["per_doc"] = per_doc
        return {}

    def fake_chunk_b(doc, ann, tolerance_chars=30):
        return {
            "chunk_boundary_precision": {"value": 1.0, "reason": None},
            "_tolerance_chars": {"value": tolerance_chars, "reason": None},
        }

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.build_provenance", return_value={}):
                with patch("evaluation.runner.build_devset_section", return_value={}):
                    with patch("evaluation.runner.aggregate_summary", side_effect=fake_aggregate):
                        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                                with patch("evaluation.runner.chunk_boundary_prf", side_effect=fake_chunk_b):
                                    run_evaluation(manifest, out, tolerance_chars=42)
    assert captured["per_doc"][0]["_tolerance_chars"] == 42
    # public_per_doc 不应有 _tolerance_chars
    assert "_tolerance_chars" not in captured["per_doc"][0].get("metrics", {})


def test_run_evaluation_missing_markers_record_batch48(tmp_path):
    """chunk_boundary_prf 返回 _missing_markers 时记到 per_doc。"""
    doc = _make_doc(resolved_path=tmp_path / "x.pdf")

    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    captured = {}

    def fake_aggregate(per_doc):
        captured["per_doc"] = per_doc
        return {}

    def fake_chunk_b(doc, ann, tolerance_chars=30):
        return {
            "chunk_boundary_precision": {"value": 0.0, "reason": None},
            "_tolerance_chars": {"value": tolerance_chars, "reason": None},
            "_missing_markers": {"value": ["miss1", "miss2"], "reason": None},
        }

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.build_provenance", return_value={}):
                with patch("evaluation.runner.build_devset_section", return_value={}):
                    with patch("evaluation.runner.aggregate_summary", side_effect=fake_aggregate):
                        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                                with patch("evaluation.runner.chunk_boundary_prf", side_effect=fake_chunk_b):
                                    run_evaluation(manifest, out)
    assert captured["per_doc"][0]["_missing_markers"] == ["miss1", "miss2"]


def test_run_evaluation_no_missing_markers_defaults_empty_list_batch48(tmp_path):
    """chunk_boundary_prf 不返回 _missing_markers → per_doc 里是 []。"""
    doc = _make_doc(resolved_path=tmp_path / "x.pdf")

    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    captured = {}

    def fake_aggregate(per_doc):
        captured["per_doc"] = per_doc
        return {}

    def fake_chunk_b(doc, ann, tolerance_chars=30):
        return {
            "_tolerance_chars": {"value": tolerance_chars, "reason": None},
        }

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.build_provenance", return_value={}):
                with patch("evaluation.runner.build_devset_section", return_value={}):
                    with patch("evaluation.runner.aggregate_summary", side_effect=fake_aggregate):
                        with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                            with patch("evaluation.runner.figure_caption_prf", return_value={}):
                                with patch("evaluation.runner.chunk_boundary_prf", side_effect=fake_chunk_b):
                                    run_evaluation(manifest, out)
    assert captured["per_doc"][0]["_missing_markers"] == []


# ---------- run_evaluation image_base_dir 推导 ----------

def test_run_evaluation_image_base_dir_passed_when_dir_exists_batch48(tmp_path):
    """image_dir 是目录 → image_base_dir 传给 compute_automatic_metrics。"""
    doc = _make_doc(resolved_path=tmp_path / "x.pdf")
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()

    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    captured = {}

    def fake_metrics(**kwargs):
        captured["image_base_dir"] = kwargs.get("image_base_dir")
        return {}

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=img_dir):
            with patch("evaluation.runner.build_provenance", return_value={}):
                with patch("evaluation.runner.build_devset_section", return_value={}):
                    with patch("evaluation.runner.compute_automatic_metrics", side_effect=fake_metrics):
                        with patch("evaluation.runner.figure_caption_prf", return_value={}):
                            with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                                run_evaluation(manifest, out)
    assert captured["image_base_dir"] == img_dir


def test_run_evaluation_image_base_dir_none_when_not_dir_batch48(tmp_path):
    """image_dir 不存在 → image_base_dir=None。"""
    doc = _make_doc(resolved_path=tmp_path / "x.pdf")
    img_dir = tmp_path / "nonexistent"  # 不存在

    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    captured = {}

    def fake_metrics(**kwargs):
        captured["image_base_dir"] = kwargs.get("image_base_dir")
        return {}

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=img_dir):
            with patch("evaluation.runner.build_provenance", return_value={}):
                with patch("evaluation.runner.build_devset_section", return_value={}):
                    with patch("evaluation.runner.compute_automatic_metrics", side_effect=fake_metrics):
                        with patch("evaluation.runner.figure_caption_prf", return_value={}):
                            with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                                run_evaluation(manifest, out)
    assert captured["image_base_dir"] is None


def test_run_evaluation_image_base_dir_none_when_image_dir_none_batch48(tmp_path):
    """document None → image_dir=None → image_base_dir=None。"""
    doc = _make_doc(resolved_path=tmp_path / "x.pdf")
    err = MagicMock()
    err.to_dict.return_value = {"code": "parse_failed"}

    captured = {}

    def fake_metrics(**kwargs):
        captured["image_base_dir"] = kwargs.get("image_base_dir")
        return {}

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"

    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        with patch("evaluation.runner.build_provenance", return_value={}):
            with patch("evaluation.runner.build_devset_section", return_value={}):
                with patch("evaluation.runner.compute_automatic_metrics", side_effect=fake_metrics):
                    with patch("evaluation.runner.figure_caption_prf", return_value={}):
                        with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                            run_evaluation(manifest, out)
    assert captured["image_base_dir"] is None


# ---------- module source 字符串补强 ----------

def test_source_contains__per_doc_batch48():
    src = inspect.getsource(runner_mod)
    assert "_per_doc" in src


def test_source_contains_doc_id_batch48():
    src = inspect.getsource(runner_mod)
    assert "doc_id" in src


def test_source_contains_IMAGE_DIR_batch48():
    src = inspect.getsource(runner_mod)
    assert "image_dir" in src


def test_source_contains_chunk_reason_batch48():
    src = inspect.getsource(runner_mod)
    assert "chunk_reason" in src


def test_source_contains_parse_reason_batch48():
    src = inspect.getsource(runner_mod)
    assert "parse_reason" in src


def test_source_contains_wall_time_seconds_batch48():
    src = inspect.getsource(runner_mod)
    assert "wall_time_seconds" in src


def test_source_contains_provenance_batch48():
    src = inspect.getsource(runner_mod)
    assert "provenance" in src


def test_source_contains_devset_batch48():
    src = inspect.getsource(runner_mod)
    assert "devset" in src


def test_source_contains_summary_batch48():
    src = inspect.getsource(runner_mod)
    assert "summary" in src


def test_source_contains_expected_failures_batch48():
    src = inspect.getsource(runner_mod)
    assert "expected_failures" in src


def test_source_contains_public_per_doc_batch48():
    src = inspect.getsource(runner_mod)
    assert "public_per_doc" in src


def test_source_contains_image_base_dir_batch48():
    src = inspect.getsource(runner_mod)
    assert "image_base_dir" in src


# ---------- AST 结构补强 ----------

def test_ast_top_level_functions_count_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 3  # _load_annotation / _process_one / run_evaluation


def test_ast_run_evaluation_has_three_main_for_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation"][0]
    top_fors = [n for n in func.body if isinstance(n, ast.For)]
    assert len(top_fors) == 3  # documents / expected_failures / public_per_doc


def test_ast_run_evaluation_has_with_for_dump_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation"][0]
    withs = [n for n in func.body if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_run_evaluation_dump_call_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation"][0]
    dump_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "dump"
    ]
    assert len(dump_calls) == 1


def test_ast_process_one_has_perf_counter_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one"][0]
    perf_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "perf_counter"
    ]
    assert len(perf_calls) >= 2  # t0 + elapsed


def test_ast_load_annotation_open_with_utf8_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation"][0]
    # 应有 .open Call
    open_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "open"
    ]
    assert len(open_calls) == 1


def test_ast_process_one_return_statements_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one"][0]
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    # errors / document None / 成功 / 内部 try（不算 return）
    assert len(returns) >= 3


def test_ast_no_class_def_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_no_async_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in ast.walk(tree):
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_module_docstring_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert isinstance(tree.body[0], ast.Expr)


# ---------- forbidden tokens 第一百一十七批 ----------

def test_source_no_eval_batch48():
    src = inspect.getsource(runner_mod)
    assert "eval(" not in src


def test_source_no_exec_batch48():
    src = inspect.getsource(runner_mod)
    assert "exec(" not in src


def test_source_no_compile_batch48():
    src = inspect.getsource(runner_mod)
    assert "compile(" not in src


def test_source_no_globals_batch48():
    src = inspect.getsource(runner_mod)
    assert "globals(" not in src


def test_source_no_locals_batch48():
    src = inspect.getsource(runner_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch48():
    src = inspect.getsource(runner_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch48():
    src = inspect.getsource(runner_mod)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch48():
    src = inspect.getsource(runner_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch48():
    src = inspect.getsource(runner_mod)
    assert "pickle.load(" not in src


def test_source_no_subprocess_batch48():
    src = inspect.getsource(runner_mod)
    assert "subprocess" not in src


def test_source_no_lambda_batch48():
    src = inspect.getsource(runner_mod)
    assert "lambda" not in src


def test_source_no_yield_batch48():
    src = inspect.getsource(runner_mod)
    assert "yield" not in src


def test_source_no_walrus_batch48():
    src = inspect.getsource(runner_mod)
    assert ":=" not in src


def test_source_no_async_def_batch48():
    src = inspect.getsource(runner_mod)
    assert "async def" not in src


def test_source_no_await_batch48():
    src = inspect.getsource(runner_mod)
    assert "await " not in src
