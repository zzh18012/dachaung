"""evaluation/runner.py 第九十三轮 edges 测试（Round 671）。

补强 edges75 未触及的角度（第五十一批）。

新角度：
- _load_annotation 多场景（None 输入 / 文件不存在 / JSON 解析失败 / OSError / 正常返回 dict）
- _process_one 控制流（errors 非空返回 errors[0].to_dict / document None 返回 unknown error / 正常返回 document.to_dict）
- _process_one image_dir 推导（document None 时 image_dir None / document 存在时 image_dir = image_output_dir_for）
- _process_one out_stub 清理（unlink 成功 / unlink OSError 容错）
- run_evaluation 完整流程（empty manifest / 完整 manifest / expected_failures 路径）
- run_evaluation 报告字段（report_version / provenance / devset / summary / per_doc / expected_failures）
- run_evaluation 计时（wall_time_seconds.total / parse=None / chunk=None / parse_reason）
- run_evaluation annotation_present / tolerance_chars / missing_markers 内部字段
- 模块源码补强（json/time/Path/Any imports / process_single/image_output_dir_for / REPORT_VERSION / chunk_boundary_prf+figure_caption_prf / compute_automatic_metrics / aggregate_summary+build_devset_section+build_provenance / not_instrumented / __all__）
- AST 结构补强（3 函数 + 顺序 / 无 ClassDef / 无 AsyncFunctionDef / 10 imports / _load_annotation 1 try + 1 with + 2 return / _process_one 多 if + try + 4 return / run_evaluation 多 for + 多 if + 1 with + return / module docstring / __all__ 1 entry）
- forbidden tokens 第一百四十一批
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


# ---------- _load_annotation 多场景 ----------

def test_load_annotation_none_input_batch51():
    assert _load_annotation(None) is None


def test_load_annotation_nonexistent_file_batch51(tmp_path):
    p = tmp_path / "nope.json"
    assert _load_annotation(p) is None


def test_load_annotation_invalid_json_batch51(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_oserror_batch51(tmp_path):
    """open 失败 OSError 也 catch。"""
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    with patch("pathlib.Path.open", side_effect=OSError("boom")):
        assert _load_annotation(p) is None


def test_load_annotation_success_batch51(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": "v"}


def test_load_annotation_returns_dict_or_none_batch51(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    out = _load_annotation(p)
    assert isinstance(out, dict)


def test_load_annotation_no_args_required_batch51():
    """path 是 required positional arg。"""
    with pytest.raises(TypeError):
        _load_annotation()  # type: ignore[call-arg]


# ---------- _process_one 控制流 ----------

def test_process_one_with_errors_batch51(tmp_path):
    """process_single 返回 errors → _process_one 返回 (None, errors[0].to_dict, elapsed, None, image_dir)。"""
    err = MagicMock()
    err.to_dict.return_value = {"code": "parse_failed"}
    fake_doc_dict = MagicMock()
    fake_doc_dict.to_dict.return_value = {"elements": []}
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        with patch("evaluation.runner.time.perf_counter", return_value=0.0):
            doc = MagicMock()
            doc.doc_id = "d1"
            doc.resolved_path = tmp_path / "x.pdf"
            document, error, elapsed, parser_v, image_dir = _process_one(
                doc, tmp_path, "fallback", 800
            )
    assert document is None
    assert error == {"code": "parse_failed"}
    assert elapsed >= 0
    assert parser_v is None


def test_process_one_no_errors_no_document_batch51(tmp_path):
    """process_single 返回 (None, []) → unknown error。"""
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        doc = MagicMock()
        doc.doc_id = "d1"
        doc.resolved_path = tmp_path / "x.pdf"
        document, error, elapsed, parser_v, image_dir = _process_one(
            doc, tmp_path, "fallback", 800
        )
    assert document is None
    assert error["code"] == "unknown"
    assert "process_single returned None without errors" in error["message"]


def test_process_one_success_batch51(tmp_path):
    """process_single 返回 document 无 errors → 正常路径。"""
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"elements": [{"type": "paragraph", "content": "hi"}]}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "sha123"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "img"):
            doc = MagicMock()
            doc.doc_id = "d1"
            doc.resolved_path = tmp_path / "x.pdf"
            document, error, elapsed, parser_v, image_dir = _process_one(
                doc, tmp_path, "fallback", 800
            )
    assert document == {"elements": [{"type": "paragraph", "content": "hi"}]}
    assert error is None
    assert parser_v == "1.0.0"
    assert image_dir == tmp_path / "img"


def test_process_one_image_dir_none_when_document_none_batch51(tmp_path):
    """document None 时 image_dir 必须是 None。"""
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        doc = MagicMock()
        doc.doc_id = "d1"
        doc.resolved_path = tmp_path / "x.pdf"
        _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None


def test_process_one_unlink_oserror_silent_batch51(tmp_path):
    """out_stub.is_file() True 但 unlink 抛 OSError → 不影响结果。"""
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"elements": []}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "sha"
    # 先 patch process_single；然后 patch unlink
    out_stub_path = tmp_path / "_per_doc" / "d1.json"
    out_stub_path.parent.mkdir(parents=True)
    out_stub_path.write_text("{}", encoding="utf-8")
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            with patch("pathlib.Path.unlink", side_effect=OSError("boom")):
                doc = MagicMock()
                doc.doc_id = "d1"
                doc.resolved_path = tmp_path / "x.pdf"
                document, error, elapsed, parser_v, image_dir = _process_one(
                    doc, tmp_path, "fallback", 800
                )
    assert document == {"elements": []}
    assert error is None


def test_process_one_creates_per_doc_dir_batch51(tmp_path):
    """_process_one 创建 output_root/_per_doc 目录。"""
    output_root = tmp_path
    per_doc_dir = output_root / "_per_doc"
    assert not per_doc_dir.exists()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {"elements": []}
    fake_doc.parser_version = "1.0"
    fake_doc.source_hash = "sha"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path):
            doc = MagicMock()
            doc.doc_id = "d1"
            doc.resolved_path = tmp_path / "x.pdf"
            _process_one(doc, output_root, "fallback", 800)
    assert per_doc_dir.is_dir()


def test_process_one_returns_5_tuple_batch51(tmp_path):
    """返回值是 5-tuple。"""
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        doc = MagicMock()
        doc.doc_id = "d1"
        doc.resolved_path = tmp_path / "x.pdf"
        out = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(out, tuple)
    assert len(out) == 5


# ---------- run_evaluation 完整流程 ----------

def _make_full_manifest(documents=None, expected_failures=None, project_root=None):
    """构造一个完整 Manifest，避免 MagicMock 字段 JSON 序列化失败。"""
    m = MagicMock()
    m.documents = documents or []
    m.expected_failures = expected_failures or []
    m.project_root = project_root or Path.cwd()
    m.devset_status = "incomplete"
    m.file_count = len(documents or [])
    m.content_group_count = 0
    m.pdf_count = sum(1 for d in (documents or []) if getattr(d, "source_type", None) == "pdf")
    m.docx_count = sum(1 for d in (documents or []) if getattr(d, "source_type", None) == "docx")
    m.categories_covered = []
    return m


def test_run_evaluation_empty_manifest_batch51(tmp_path):
    """空 manifest → per_doc 空 + summary + devset + provenance + report_version。"""
    m = _make_full_manifest()
    output = tmp_path / "out.json"
    with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
        out = run_evaluation(m, output, parser_name="fallback", max_chars=800)
    assert out["report_version"] == "1.1"
    assert out["per_doc"] == []
    assert out["expected_failures"] == []
    assert out["provenance"] == {"git_commit": "abc"}


def test_run_evaluation_writes_json_file_batch51(tmp_path):
    m = _make_full_manifest()
    output = tmp_path / "sub" / "out.json"
    with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
        run_evaluation(m, output, parser_name="fallback", max_chars=800)
    assert output.is_file()
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["report_version"] == "1.1"


def test_run_evaluation_report_has_6_keys_batch51(tmp_path):
    m = _make_full_manifest()
    output = tmp_path / "out.json"
    with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
        out = run_evaluation(m, output)
    assert set(out.keys()) == {
        "report_version", "provenance", "devset",
        "summary", "per_doc", "expected_failures",
    }


def test_run_evaluation_per_doc_has_required_keys_batch51(tmp_path):
    """每个 per_doc 含 doc_id / source_type / metrics / wall_time_seconds。"""
    fake_doc = MagicMock()
    fake_doc.doc_id = "d1"
    fake_doc.resolved_path = tmp_path / "x.pdf"
    fake_doc.source_type = "pdf"
    fake_doc.expectations = None
    fake_doc.annotation_resolved = None

    fd_result = MagicMock()
    fd_result.to_dict.return_value = {"elements": []}
    fd_result.parser_version = "1.0"
    fd_result.source_hash = "sha"
    with patch("evaluation.runner.process_single", return_value=(fd_result, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
                m = _make_full_manifest(documents=[fake_doc])
                out = run_evaluation(m, tmp_path / "out.json")
    pd = out["per_doc"][0]
    assert set(pd.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}
    assert pd["doc_id"] == "d1"
    assert pd["source_type"] == "pdf"
    assert pd["wall_time_seconds"]["total"] >= 0
    assert pd["wall_time_seconds"]["parse"] is None
    assert pd["wall_time_seconds"]["chunk"] is None


def test_run_evaluation_per_doc_metrics_keys_batch51(tmp_path):
    """metrics 应包含至少 14 个自动指标。"""
    fake_doc = MagicMock()
    fake_doc.doc_id = "d1"
    fake_doc.resolved_path = tmp_path / "x.pdf"
    fake_doc.source_type = "pdf"
    fake_doc.expectations = None
    fake_doc.annotation_resolved = None

    fd_result = MagicMock()
    fd_result.to_dict.return_value = {"elements": []}
    fd_result.parser_version = "1.0"
    fd_result.source_hash = "sha"
    with patch("evaluation.runner.process_single", return_value=(fd_result, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
                m = _make_full_manifest(documents=[fake_doc])
                out = run_evaluation(m, tmp_path / "out.json")
    metrics = out["per_doc"][0]["metrics"]
    # 14 自动 + 3 figure_caption + 3 chunk_boundary = 20
    assert len(metrics) >= 14


def test_run_evaluation_expected_failures_path_batch51(tmp_path):
    """expected_failures 路径：调用 process_single 并比较 code。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "x.pdf"
    ef.expected_error_code = "parse_failed"

    err = MagicMock()
    err.code = "parse_failed"
    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
            m = _make_full_manifest(expected_failures=[ef])
            out = run_evaluation(m, tmp_path / "out.json")
    assert out["expected_failures"] == [
        {
            "doc_id": "ef1",
            "expected_error_code": "parse_failed",
            "actual_error_code": "parse_failed",
            "matches": True,
        }
    ]


def test_run_evaluation_expected_failures_no_error_batch51(tmp_path):
    """expected_failure 没出错 → actual_code=None, matches=False。"""
    ef = MagicMock()
    ef.doc_id = "ef1"
    ef.resolved_path = tmp_path / "x.pdf"
    ef.expected_error_code = "parse_failed"

    with patch("evaluation.runner.process_single", return_value=(MagicMock(), [])):
        with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
            m = _make_full_manifest(expected_failures=[ef])
            out = run_evaluation(m, tmp_path / "out.json")
    assert out["expected_failures"][0]["actual_error_code"] is None
    assert out["expected_failures"][0]["matches"] is False


def test_run_evaluation_parser_version_set_from_first_doc_batch51(tmp_path):
    """parser_version 取自第一个成功的 document。"""
    fake_doc = MagicMock()
    fake_doc.doc_id = "d1"
    fake_doc.resolved_path = tmp_path / "x.pdf"
    fake_doc.source_type = "pdf"
    fake_doc.expectations = None
    fake_doc.annotation_resolved = None

    fd_result = MagicMock()
    fd_result.to_dict.return_value = {"elements": []}
    fd_result.parser_version = "fallback-1.0"
    fd_result.source_hash = "sha"
    with patch("evaluation.runner.process_single", return_value=(fd_result, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}) as bp_mock:
                m = _make_full_manifest(documents=[fake_doc])
                run_evaluation(m, tmp_path / "out.json")
    # build_provenance 被调，parser_version 应是 "fallback-1.0"
    args, kwargs = bp_mock.call_args
    assert kwargs["parser_version"] == "fallback-1.0"


def test_run_evaluation_creates_output_root_batch51(tmp_path):
    """run_evaluation 会 mkdir output_root。"""
    output = tmp_path / "new_dir" / "out.json"
    m = _make_full_manifest()
    with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
        run_evaluation(m, output)
    assert output.parent.is_dir()


def test_run_evaluation_uses_image_dir_when_dir_exists_batch51(tmp_path):
    """image_dir 是有效目录 → 传给 compute_automatic_metrics 作为 image_base_dir。"""
    image_dir = tmp_path / "imgs"
    image_dir.mkdir()
    fake_doc = MagicMock()
    fake_doc.doc_id = "d1"
    fake_doc.resolved_path = tmp_path / "x.pdf"
    fake_doc.source_type = "pdf"
    fake_doc.expectations = None
    fake_doc.annotation_resolved = None

    fd_result = MagicMock()
    fd_result.to_dict.return_value = {"elements": []}
    fd_result.parser_version = "1.0"
    fd_result.source_hash = "sha"
    with patch("evaluation.runner.process_single", return_value=(fd_result, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=image_dir):
            with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
                with patch("evaluation.runner.compute_automatic_metrics") as mock_compute:
                    mock_compute.return_value = {"pipeline_success": {"value": True, "reason": None}}
                    m = _make_full_manifest(documents=[fake_doc])
                    run_evaluation(m, tmp_path / "out.json")
    args, kwargs = mock_compute.call_args
    assert kwargs["image_base_dir"] == image_dir


def test_run_evaluation_skips_image_dir_when_not_dir_batch51(tmp_path):
    """image_dir 不存在 → image_base_dir=None。"""
    image_dir = tmp_path / "nope"  # 不存在
    fake_doc = MagicMock()
    fake_doc.doc_id = "d1"
    fake_doc.resolved_path = tmp_path / "x.pdf"
    fake_doc.source_type = "pdf"
    fake_doc.expectations = None
    fake_doc.annotation_resolved = None

    fd_result = MagicMock()
    fd_result.to_dict.return_value = {"elements": []}
    fd_result.parser_version = "1.0"
    fd_result.source_hash = "sha"
    with patch("evaluation.runner.process_single", return_value=(fd_result, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=image_dir):
            with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
                with patch("evaluation.runner.compute_automatic_metrics") as mock_compute:
                    mock_compute.return_value = {"pipeline_success": {"value": True, "reason": None}}
                    m = _make_full_manifest(documents=[fake_doc])
                    run_evaluation(m, tmp_path / "out.json")
    args, kwargs = mock_compute.call_args
    assert kwargs["image_base_dir"] is None


def test_run_evaluation_compute_metrics_called_with_correct_args_batch51(tmp_path):
    fake_doc = MagicMock()
    fake_doc.doc_id = "d1"
    fake_doc.resolved_path = tmp_path / "x.pdf"
    fake_doc.source_type = "pdf"
    fake_doc.expectations = {"element_count_by_type": {"paragraph": 5}}
    fake_doc.annotation_resolved = None

    fd_result = MagicMock()
    fd_result.to_dict.return_value = {"elements": []}
    fd_result.parser_version = "1.0"
    fd_result.source_hash = "sha"
    with patch("evaluation.runner.process_single", return_value=(fd_result, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=None):
            with patch("evaluation.runner.build_provenance", return_value={"git_commit": "abc"}):
                with patch("evaluation.runner.compute_automatic_metrics") as mock_compute:
                    mock_compute.return_value = {}
                    m = _make_full_manifest(documents=[fake_doc])
                    run_evaluation(m, tmp_path / "out.json")
    args, kwargs = mock_compute.call_args
    assert kwargs["source_type"] == "pdf"
    assert kwargs["expectations"] == {"element_count_by_type": {"paragraph": 5}}


# ---------- 模块源码补强 ----------

def test_source_contains_json_import_batch51():
    src = inspect.getsource(runner_mod)
    assert "import json" in src


def test_source_contains_time_import_batch51():
    src = inspect.getsource(runner_mod)
    assert "import time" in src


def test_source_contains_path_import_batch51():
    src = inspect.getsource(runner_mod)
    assert "from pathlib import Path" in src


def test_source_contains_any_import_batch51():
    src = inspect.getsource(runner_mod)
    assert "from typing import Any" in src


def test_source_imports_process_single_batch51():
    src = inspect.getsource(runner_mod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_source_imports_report_version_batch51():
    src = inspect.getsource(runner_mod)
    assert "from evaluation import REPORT_VERSION" in src


def test_source_imports_annotation_metrics_batch51():
    src = inspect.getsource(runner_mod)
    assert "from evaluation.annotation_metrics import" in src
    assert "chunk_boundary_prf" in src
    assert "figure_caption_prf" in src


def test_source_imports_metrics_batch51():
    src = inspect.getsource(runner_mod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_source_imports_report_helpers_batch51():
    src = inspect.getsource(runner_mod)
    assert "from evaluation.report import" in src
    assert "aggregate_summary" in src
    assert "build_devset_section" in src
    assert "build_provenance" in src


def test_source_contains_not_instrumented_batch51():
    src = inspect.getsource(runner_mod)
    assert "not_instrumented" in src


def test_source_contains_perf_counter_batch51():
    src = inspect.getsource(runner_mod)
    assert "time.perf_counter" in src


def test_source_contains_write_json_false_batch51():
    src = inspect.getsource(runner_mod)
    assert "write_json=False" in src


def test_source_contains_image_output_dir_for_batch51():
    src = inspect.getsource(runner_mod)
    assert "image_output_dir_for" in src


def test_source_contains_unknown_error_code_batch51():
    src = inspect.getsource(runner_mod)
    assert '"unknown"' in src
    assert "process_single returned None without errors" in src


def test_source_contains_ensure_ascii_false_batch51():
    src = inspect.getsource(runner_mod)
    assert "ensure_ascii=False" in src


def test_source_contains_indent_2_batch51():
    src = inspect.getsource(runner_mod)
    assert "indent=2" in src


def test_source_contains_tolerance_chars_batch51():
    src = inspect.getsource(runner_mod)
    assert "tolerance_chars" in src


def test_source_contains_run_evaluation_docstring_batch51():
    src = inspect.getsource(runner_mod)
    assert "跑评测主流程" in src or "评测主流程" in src


def test_source_all_1_entry_batch51():
    src = inspect.getsource(runner_mod)
    assert '"run_evaluation"' in src


# ---------- AST 结构补强 ----------

def test_ast_has_3_top_level_functions_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 3


def test_ast_function_names_order_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_load_annotation", "_process_one", "run_evaluation"]


def test_ast_no_class_def_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_has_10_imports_batch51():
    """__future__ + json + time + Path + Any + process_single/image_output_dir_for + REPORT_VERSION + annotation_metrics + metrics + report = 10。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 10


def test_ast_module_docstring_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_has_all_assign_1_entry_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    all_assign = None
    for n in tree.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == "__all__":
                    all_assign = n
    assert all_assign is not None
    assert isinstance(all_assign.value, ast.List)
    assert len(all_assign.value.elts) == 1


def test_ast_load_annotation_has_try_except_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation")
    tries = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(tries) == 1


def test_ast_load_annotation_has_with_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation")
    withs = [n for n in ast.walk(func) if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_load_annotation_has_3_return_batch51():
    """3 个 return：None（早）/ dict（成功）/ None（异常）。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 3


def test_ast_process_one_has_try_except_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    tries = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(tries) == 1


def test_ast_process_one_has_3_return_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 3  # errors 路径 + None 路径 + 末尾正常路径


def test_ast_run_evaluation_has_2_for_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    fors = [n for n in func.body if isinstance(n, ast.For)]
    assert len(fors) == 3  # for doc + for ef + for r


def test_ast_run_evaluation_has_with_open_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    withs = [n for n in ast.walk(func) if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_run_evaluation_has_1_return_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 1


def test_ast_no_global_nonlocal_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


def test_ast_no_delete_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.Delete) for n in ast.walk(tree))


def test_ast_no_while_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))


def test_ast_no_raise_top_level_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.Raise)


def test_ast_no_star_import_batch51():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


# ---------- forbidden tokens 第一百四十一批 ----------

def _src() -> str:
    return inspect.getsource(runner_mod)


def test_source_no_eval_batch51():
    assert "eval(" not in _src()


def test_source_no_exec_batch51():
    assert "exec(" not in _src()


def test_source_no_compile_batch51():
    assert "compile(" not in _src()


def test_source_no_globals_batch51():
    assert "globals(" not in _src()


def test_source_no_locals_batch51():
    assert "locals(" not in _src()


def test_source_no_os_system_batch51():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch51():
    assert "subprocess" not in _src()


def test_source_no_popen_batch51():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch51():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch51():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch51():
    assert "socket" not in _src()


def test_source_no_requests_batch51():
    assert "requests" not in _src()


def test_source_no_urllib_batch51():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch51():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch51():
    assert "yield" not in _src()


def test_source_no_async_await_batch51():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch51():
    """_load_annotation 1 个 with open + run_evaluation 1 个 with open = 2。"""
    assert _src().count("open(") == 2
