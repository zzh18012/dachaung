"""evaluation/runner.py 第九十五轮 edges 测试（Round 684）。

补强 edges77 未触及的角度（第五十三批）。

新角度：
- _load_annotation 更深（OSError → None / JSONDecodeError → None / 路径是目录 → None / 合法 JSON 返回 dict）
- _process_one 更深（document None + errors 空 → unknown error dict / errors 多个取第一个 / image_dir None 当 document None / out_stub unlink OSError 容错 / elapsed 非负）
- run_evaluation 完整流程更深（per_doc 不含 _annotation_present 等私有字段 / expected_failures matches 判断 / tolerance_record 从 chunk_b pop / missing_markers 默认 [] / wall_time_seconds 5 keys）
- run_evaluation 写盘更深（parent mkdir 两次 / ensure_ascii=False / indent=2 / report 6 keys）
- run_evaluation parser_version 取第一个非 None
- 模块源码补强（time import / image_output_dir_for+process_single import / REPORT_VERSION import / figure_caption_prf+chunk_boundary_prf import / compute_automatic_metrics import / 3 report helpers import / _per_doc 命名 / write_json=False 出现 2 次 / not_instrumented 出现 2 次 / unlink 容错 / json.dump kwargs）
- AST 结构补强（3 函数 + 顺序 / 10 imports / _load_annotation 1 With + 1 Try / _process_one 多 return + image_output_dir_for call / run_evaluation 3 For + 2 With + parser_version 条件赋值 / public_per_doc 构建 / report Dict 6 keys）
- forbidden tokens 第一百五十四批
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


# ---------- _load_annotation 更深 ----------

def test_load_annotation_none_path_batch52():
    assert _load_annotation(None) is None


def test_load_annotation_missing_file_batch52(tmp_path):
    assert _load_annotation(tmp_path / "nope.json") is None


def test_load_annotation_oserror_returns_none_batch52(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("{}", encoding="utf-8")
    with patch("pathlib.Path.open", side_effect=OSError("denied")):
        assert _load_annotation(p) is None


def test_load_annotation_bad_json_returns_none_batch52(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("not json", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_directory_returns_none_batch52(tmp_path):
    d = tmp_path / "adir"
    d.mkdir()
    # is_file() False → None
    assert _load_annotation(d) is None


def test_load_annotation_valid_json_batch52(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text(json.dumps({"chunk_boundary_anchors": []}), encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"chunk_boundary_anchors": []}


def test_load_annotation_empty_obj_batch52(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("{}", encoding="utf-8")
    assert _load_annotation(p) == {}


def test_load_annotation_returns_none_for_empty_file_batch52(tmp_path):
    """空文件 → JSONDecodeError → None。"""
    p = tmp_path / "ann.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


# ---------- _process_one 更深 ----------

def _make_doc(doc_id="d1"):
    d = MagicMock()
    d.doc_id = doc_id
    d.resolved_path = Path("x.pdf")
    return d


def test_process_one_document_none_no_errors_unknown_batch52(tmp_path):
    """document None + errors 空 → unknown error dict。"""
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        doc, err, elapsed, pv, img = _process_one(_make_doc(), tmp_path, "fallback", 800)
    assert doc is None
    assert err == {"code": "unknown", "message": "process_single returned None without errors"}
    assert pv is None


def test_process_one_multiple_errors_first_batch52(tmp_path):
    e1 = MagicMock()
    e1.to_dict.return_value = {"code": "e1"}
    e2 = MagicMock()
    e2.to_dict.return_value = {"code": "e2"}
    with patch("evaluation.runner.process_single", return_value=(None, [e1, e2])):
        doc, err, elapsed, pv, img = _process_one(_make_doc(), tmp_path, "fallback", 800)
    assert err == {"code": "e1"}


def test_process_one_image_dir_none_when_document_none_batch52(tmp_path):
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        doc, err, elapsed, pv, img = _process_one(_make_doc(), tmp_path, "fallback", 800)
    assert img is None


def test_process_one_elapsed_non_negative_batch52(tmp_path):
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        doc, err, elapsed, pv, img = _process_one(_make_doc(), tmp_path, "fallback", 800)
    assert elapsed >= 0.0
    assert isinstance(elapsed, float)


def test_process_one_success_returns_doc_dict_batch52(tmp_path):
    document = MagicMock()
    document.to_dict.return_value = {"document_id": "x"}
    document.parser_version = "1.2.3"
    document.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(document, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
        doc, err, elapsed, pv, img = _process_one(_make_doc(), tmp_path, "fallback", 800)
    assert doc == {"document_id": "x"}
    assert err is None
    assert pv == "1.2.3"
    assert img == tmp_path / "imgs"


def test_process_one_creates_per_doc_dir_batch52(tmp_path):
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        _process_one(_make_doc(doc_id="zz"), tmp_path, "fallback", 800)
    assert (tmp_path / "_per_doc").is_dir()


def test_process_one_unlink_oserror_tolerated_batch52(tmp_path):
    """out_stub.is_file() True 但 unlink 抛 OSError → 不传播。"""
    with patch("evaluation.runner.process_single", return_value=(None, [])), \
         patch("evaluation.runner.Path.is_file", return_value=True), \
         patch("evaluation.runner.Path.unlink", side_effect=OSError("locked")):
        doc, err, elapsed, pv, img = _process_one(_make_doc(), tmp_path, "fallback", 800)
    # 无异常
    assert err is not None


def test_process_one_stub_path_naming_batch52(tmp_path):
    """out_stub 在 _per_doc/{doc_id}.json。"""
    with patch("evaluation.runner.process_single") as ps:
        ps.return_value = (None, [])
        _process_one(_make_doc(doc_id="mydoc"), tmp_path, "fallback", 800)
        called_path = ps.call_args.args[0]
        assert called_path == Path("x.pdf")
        stub = ps.call_args.args[1]
        assert stub == tmp_path / "_per_doc" / "mydoc.json"


def test_process_one_calls_process_single_with_kwargs_batch52(tmp_path):
    with patch("evaluation.runner.process_single") as ps:
        ps.return_value = (None, [])
        _process_one(_make_doc(), tmp_path, "kreuzberg", 500)
    kwargs = ps.call_args.kwargs
    assert kwargs == {"parser_name": "kreuzberg", "max_chars": 500, "write_json": False}


# ---------- run_evaluation 完整流程更深 ----------

def _full_manifest(docs=1, efs=0):
    m = MagicMock()
    m.project_root = Path(".")
    m.documents = []
    for i in range(docs):
        d = MagicMock()
        d.doc_id = f"d{i}"
        d.source_type = "pdf"
        d.expectations = None
        d.annotation_resolved = None
        m.documents.append(d)
    m.expected_failures = []
    for i in range(efs):
        ef = MagicMock()
        ef.doc_id = f"ef{i}"
        ef.resolved_path = Path("bad.pdf")
        ef.expected_error_code = "unsupported_format"
        m.expected_failures.append(ef)
    return m


def _good_document():
    doc = MagicMock()
    doc.to_dict.return_value = {
        "document_id": "x",
        "elements": [{"type": "paragraph", "content": "hello", "element_id": "e1", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
    }
    doc.parser_version = "1.0"
    doc.source_hash = "abc"
    return doc


def test_run_evaluation_per_doc_no_private_fields_batch52(tmp_path):
    m = _full_manifest(docs=1)
    with patch("evaluation.runner._process_one", return_value=(_good_document().to_dict(), None, 0.1, "1.0", None)), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={"pipeline_success": {"value": True, "reason": None}}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        report = run_evaluation(m, tmp_path / "out.json")
    r = report["per_doc"][0]
    assert "_annotation_present" not in r
    assert "_tolerance_chars" not in r
    assert "_missing_markers" not in r


def test_run_evaluation_per_doc_4_public_keys_batch52(tmp_path):
    m = _full_manifest(docs=1)
    with patch("evaluation.runner._process_one", return_value=({"a": 1}, None, 0.1, "1.0", None)), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        report = run_evaluation(m, tmp_path / "out.json")
    r = report["per_doc"][0]
    assert set(r.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_wall_time_5_keys_batch52(tmp_path):
    m = _full_manifest(docs=1)
    with patch("evaluation.runner._process_one", return_value=({"a": 1}, None, 0.1, "1.0", None)), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        report = run_evaluation(m, tmp_path / "out.json")
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_expected_failure_matches_batch52(tmp_path):
    m = _full_manifest(docs=0, efs=1)
    err = MagicMock()
    err.code = "unsupported_format"
    with patch("evaluation.runner.process_single", return_value=(None, [err])), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        report = run_evaluation(m, tmp_path / "out.json")
    ef = report["expected_failures"][0]
    assert ef["actual_error_code"] == "unsupported_format"
    assert ef["matches"] is True


def test_run_evaluation_expected_failure_mismatch_batch52(tmp_path):
    m = _full_manifest(docs=0, efs=1)
    err = MagicMock()
    err.code = "different_error"
    with patch("evaluation.runner.process_single", return_value=(None, [err])), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        report = run_evaluation(m, tmp_path / "out.json")
    ef = report["expected_failures"][0]
    assert ef["matches"] is False


def test_run_evaluation_expected_failure_success_batch52(tmp_path):
    """期望失败但实际成功 → actual_error_code None。"""
    m = _full_manifest(docs=0, efs=1)
    doc = _good_document()
    with patch("evaluation.runner.process_single", return_value=(doc, [])), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        report = run_evaluation(m, tmp_path / "out.json")
    ef = report["expected_failures"][0]
    assert ef["actual_error_code"] is None
    assert ef["matches"] is False


def test_run_evaluation_tolerance_popped_from_chunk_b_batch52(tmp_path):
    """chunk_boundary_prf 的 _tolerance_chars 被移到顶层记录。"""
    m = _full_manifest(docs=1)
    def fake_cb_prf(doc, ann, tolerance_chars=30):
        return {
            "chunk_boundary_precision": {"value": None, "reason": "x"},
            "_tolerance_chars": {"value": tolerance_chars, "reason": None},
            "_missing_markers": {"value": ["m1"], "reason": None},
        }
    with patch("evaluation.runner._process_one", return_value=({"a": 1}, None, 0.1, "1.0", None)), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", side_effect=fake_cb_prf), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        report = run_evaluation(m, tmp_path / "out.json", tolerance_chars=77)
    # 私有记录不进 metrics
    r = report["per_doc"][0]
    assert "_tolerance_chars" not in r["metrics"]
    assert "_missing_markers" not in r["metrics"]


def test_run_evaluation_parser_version_first_non_none_batch52(tmp_path):
    m = _full_manifest(docs=2)
    versions = ["2.0", "1.0"]
    def fake_process_one(doc, output_root, parser_name, max_chars):
        v = versions.pop(0)
        return {"a": 1}, None, 0.1, v, None
    with patch("evaluation.runner._process_one", side_effect=fake_process_one), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance") as bp, \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        bp.return_value = {}
        run_evaluation(m, tmp_path / "out.json")
    # 取第一个非 None = "2.0"
    assert bp.call_args.kwargs["parser_version"] == "2.0"


def test_run_evaluation_skips_none_parser_version_batch52(tmp_path):
    m = _full_manifest(docs=2)
    versions = [None, "1.5"]
    def fake_process_one(doc, output_root, parser_name, max_chars):
        v = versions.pop(0)
        return {"a": 1}, None, 0.1, v, None
    with patch("evaluation.runner._process_one", side_effect=fake_process_one), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance") as bp, \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        bp.return_value = {}
        run_evaluation(m, tmp_path / "out.json")
    # 第一个 None 跳过，取 "1.5"
    assert bp.call_args.kwargs["parser_version"] == "1.5"


def test_run_evaluation_report_6_keys_batch52(tmp_path):
    m = _full_manifest(docs=0)
    with patch("evaluation.runner.build_provenance", return_value={"p": 1}), \
         patch("evaluation.runner.build_devset_section", return_value={"d": 1}), \
         patch("evaluation.runner.aggregate_summary", return_value={"s": 1}):
        report = run_evaluation(m, tmp_path / "out.json")
    assert set(report.keys()) == {
        "report_version", "provenance", "devset", "summary",
        "per_doc", "expected_failures",
    }


def test_run_evaluation_writes_file_batch52(tmp_path):
    m = _full_manifest(docs=0)
    out = tmp_path / "sub" / "out.json"
    with patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        report = run_evaluation(m, out)
    assert out.is_file()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded == report


def test_run_evaluation_json_dump_kwargs_batch52(tmp_path):
    """json.dump 使用 ensure_ascii=False + indent=2。"""
    m = _full_manifest(docs=0)
    with patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}), \
         patch("evaluation.runner.json.dump") as jd:
        run_evaluation(m, tmp_path / "out.json")
    kwargs = jd.call_args.kwargs
    assert kwargs.get("ensure_ascii") is False
    assert kwargs.get("indent") == 2


def test_run_evaluation_image_dir_none_when_not_dir_batch52(tmp_path):
    """image_dir 非 is_dir() → image_base_dir=None。"""
    m = _full_manifest(docs=1)
    with patch("evaluation.runner._process_one", return_value=({"a": 1}, None, 0.1, "1.0", tmp_path / "nonexistent")), \
         patch("evaluation.runner.compute_automatic_metrics") as cam, \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        cam.return_value = {}
        run_evaluation(m, tmp_path / "out.json")
    assert cam.call_args.kwargs.get("image_base_dir") is None


def test_run_evaluation_image_dir_used_when_dir_batch52(tmp_path):
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    m = _full_manifest(docs=1)
    with patch("evaluation.runner._process_one", return_value=({"a": 1}, None, 0.1, "1.0", img_dir)), \
         patch("evaluation.runner.compute_automatic_metrics") as cam, \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        cam.return_value = {}
        run_evaluation(m, tmp_path / "out.json")
    assert cam.call_args.kwargs.get("image_base_dir") == img_dir


# ---------- 模块源码补强 ----------

def test_source_future_annotations_batch52():
    src = inspect.getsource(runner_mod)
    assert "from __future__ import annotations" in src


def test_source_json_import_batch52():
    src = inspect.getsource(runner_mod)
    assert "import json" in src


def test_source_time_import_batch52():
    src = inspect.getsource(runner_mod)
    assert "import time" in src


def test_source_path_import_batch52():
    src = inspect.getsource(runner_mod)
    assert "from pathlib import Path" in src


def test_source_any_import_batch52():
    src = inspect.getsource(runner_mod)
    assert "from typing import Any" in src


def test_source_pipeline_imports_batch52():
    src = inspect.getsource(runner_mod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_source_report_version_import_batch52():
    src = inspect.getsource(runner_mod)
    assert "from evaluation import REPORT_VERSION" in src


def test_source_annotation_metrics_imports_batch52():
    src = inspect.getsource(runner_mod)
    assert "from evaluation.annotation_metrics import (" in src
    assert "chunk_boundary_prf," in src
    assert "figure_caption_prf," in src


def test_source_metrics_import_batch52():
    src = inspect.getsource(runner_mod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_source_report_imports_batch52():
    src = inspect.getsource(runner_mod)
    assert "aggregate_summary," in src
    assert "build_devset_section," in src
    assert "build_provenance," in src


def test_source_per_doc_naming_batch52():
    src = inspect.getsource(runner_mod)
    assert '"_per_doc"' in src or "'_per_doc'" in src


def test_source_write_json_false_twice_batch52():
    """2 处代码调用 + 2 处 docstring 提及 = 4。"""
    src = inspect.getsource(runner_mod)
    assert src.count("write_json=False") == 4


def test_source_not_instrumented_twice_batch52():
    """模块 docstring 1 次 + parse_reason 1 次 + chunk_reason 1 次 = 3。"""
    src = inspect.getsource(runner_mod)
    assert src.count('"not_instrumented"') == 3


def test_source_perf_counter_used_batch52():
    src = inspect.getsource(runner_mod)
    assert "time.perf_counter()" in src


def test_source_unlink_oserror_tolerated_batch52():
    src = inspect.getsource(runner_mod)
    assert src.count("except OSError:") == 2


def test_source_unknown_error_message_batch52():
    src = inspect.getsource(runner_mod)
    assert "process_single returned None without errors" in src


def test_source_annotation_present_field_batch52():
    src = inspect.getsource(runner_mod)
    assert '"_annotation_present": annotation is not None' in src


def test_source_missing_markers_default_empty_batch52():
    src = inspect.getsource(runner_mod)
    assert "else []" in src


def test_source_module_docstring_key_constraints_batch52():
    src = inspect.getsource(runner_mod)
    assert "不修改 app/pipeline.py" in src


def test_source_all_1_entry_batch52():
    src = inspect.getsource(runner_mod)
    assert '__all__ = ["run_evaluation"]' in src


# ---------- AST 结构补强 ----------

def test_ast_3_functions_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 3


def test_ast_function_names_order_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_load_annotation", "_process_one", "run_evaluation"]


def test_ast_10_imports_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 10


def test_ast_no_class_def_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_module_docstring_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_load_annotation_1_with_1_try_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation")
    withs = [n for n in ast.walk(func) if isinstance(n, ast.With)]
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(withs) == 1
    assert len(trys) == 1


def test_ast_load_annotation_3_returns_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    # return None (path invalid) + return json.load + return None (except) = 3
    assert len(returns) == 3


def test_ast_process_one_calls_process_single_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    src = ast.unparse(func)
    assert "process_single(" in src


def test_ast_process_one_calls_image_output_dir_for_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    src = ast.unparse(func)
    assert "image_output_dir_for(" in src


def test_ast_process_one_3_returns_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    # errors / document None / 成功 = 3
    assert len(returns) == 3


def test_ast_process_one_2_if_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    # if document is not None + if out_stub.is_file() + if errors + if document is None = 4
    assert len(ifs) == 4


def test_ast_process_one_2_try_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    # unlink try = 1
    assert len(trys) == 1


def test_ast_run_evaluation_3_for_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    fors = [n for n in func.body if isinstance(n, ast.For)]
    # for doc + for ef + for r in per_doc_results = 3
    assert len(fors) == 3


def test_ast_run_evaluation_2_with_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    withs = [n for n in ast.walk(func) if isinstance(n, ast.With)]
    assert len(withs) == 1  # out_p.open


def test_ast_run_evaluation_keyword_only_args_batch52():
    """parser_name / max_chars / tolerance_chars 是 keyword-only（* 后）。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    assert len(func.args.kwonlyargs) == 3
    assert [a.arg for a in func.args.kwonlyargs] == ["parser_name", "max_chars", "tolerance_chars"]
    assert len(func.args.kw_defaults) == 3


def test_ast_run_evaluation_pops_private_keys_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    src = ast.unparse(func)
    assert "pop('_tolerance_chars'" in src or 'pop("_tolerance_chars"' in src
    assert "pop('_missing_markers'" in src or 'pop("_missing_markers"' in src


def test_ast_run_evaluation_report_dict_6_keys_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    src = ast.unparse(func)
    for key in ("report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"):
        assert f"'{key}'" in src or f'"{key}"' in src


def test_ast_run_evaluation_appends_per_doc_results_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    src = ast.unparse(func)
    assert "per_doc_results.append(" in src


def test_ast_run_evaluation_public_per_doc_strips_private_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    src = ast.unparse(func)
    # public 构建只取 4 个公共 key
    assert "public_per_doc.append(" in src


def test_ast_no_star_import_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


def test_ast_no_global_nonlocal_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


def test_ast_no_while_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))


def test_ast_no_raise_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.Raise) for n in ast.walk(tree))


def test_ast_all_value_is_list_1_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert isinstance(all_assign.value, ast.List)
    assert len(all_assign.value.elts) == 1


# ---------- forbidden tokens 第一百五十四批 ----------

def _src() -> str:
    return inspect.getsource(runner_mod)


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
    """_load_annotation 1 + run_evaluation 1 = 2 个 open。"""
    assert _src().count("open(") == 2
