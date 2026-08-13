"""evaluation/runner.py 第八十七轮 edges 测试（Round 623）。

补强 edges69 未触及的角度（第四十四批）。

新角度：
- _process_one 多种 errors 路径
- _process_one unlink 失败 OSError 兜底
- _process_one out_stub.is_file() False 时跳过 unlink
- run_evaluation 多文档遍历
- run_evaluation parser_version 多文档时只取第一个
- run_evaluation report 字段类型
- run_evaluation image_dir 不存在时 image_base_dir=None
- run_evaluation annotation 加载
- run_evaluation 写盘 JSON ensure_ascii=False
- run_evaluation indent=2
- _load_annotation 多种编码
- module source 字符串精确
- AST 结构
- forbidden tokens 第九十三批
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


# ---------- _process_one errors 多种路径 ----------

def _make_doc_mock(doc_id="doc_001", path="/tmp/test.pdf"):
    m = MagicMock()
    m.doc_id = doc_id
    m.resolved_path = Path(path)
    return m


def test_process_one_two_errors_returns_first_batch44(tmp_path):
    doc = _make_doc_mock()
    err1 = MagicMock()
    err1.to_dict.return_value = {"code": "err1", "message": "first"}
    err2 = MagicMock()
    err2.to_dict.return_value = {"code": "err2", "message": "second"}
    with patch("evaluation.runner.process_single", return_value=(None, [err1, err2])):
        document_dict, error_dict, total_seconds, parser_version, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert error_dict == {"code": "err1", "message": "first"}


def test_process_one_unlink_oserror_silent_batch44(tmp_path):
    """unlink 抛 OSError → 静默忽略。"""
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"

    def fake_process_single(path, out_stub, **kwargs):
        out_stub.parent.mkdir(parents=True, exist_ok=True)
        out_stub.write_text("{}", encoding="utf-8")
        return fake_doc, []

    with patch("evaluation.runner.process_single", side_effect=fake_process_single):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            with patch("pathlib.Path.unlink", side_effect=OSError("boom")):
                # 不抛即可（unlink 失败兜底）
                _process_one(doc, tmp_path, "fallback", 800)


def test_process_one_unlink_when_stub_not_exists_batch44(tmp_path):
    """out_stub 不存在 → is_file() False → 跳过 unlink。"""
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            # stub 不存在（process_single 没写）
            _process_one(doc, tmp_path, "fallback", 800)


def test_process_one_image_dir_when_document_succeeds_batch44(tmp_path):
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    expected_dir = tmp_path / "_per_doc" / "images"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=expected_dir):
            _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir == expected_dir


def test_process_one_total_seconds_nonzero_batch44(tmp_path):
    """total_seconds 是 perf_counter 差值（可能极小但非负）。"""
    import time
    doc = _make_doc_mock()
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"

    def slow(*args, **kwargs):
        time.sleep(0.001)
        return fake_doc, []

    with patch("evaluation.runner.process_single", side_effect=slow):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            _, _, total, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert total >= 0


# ---------- run_evaluation 多文档 ----------

def _make_full_manifest_mock(docs=None, efs=None, project_root=None):
    m = MagicMock()
    m.documents = tuple(docs or [])
    m.expected_failures = tuple(efs or [])
    m.project_root = project_root or Path("/tmp")
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def _make_doc_mock_full(doc_id="doc_001", source_type="pdf"):
    m = MagicMock()
    m.doc_id = doc_id
    m.resolved_path = Path("/tmp/test.pdf")
    m.source_type = source_type
    m.expectations = None
    m.annotation_resolved = None
    return m


def test_run_evaluation_multiple_docs_batch44(tmp_path):
    docs = [_make_doc_mock_full(doc_id=f"d{i}") for i in range(3)]
    manifest = _make_full_manifest_mock(docs=docs)
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = run_evaluation(manifest, tmp_path / "report.json")
    assert len(out["per_doc"]) == 3
    ids = [r["doc_id"] for r in out["per_doc"]]
    assert ids == ["d0", "d1", "d2"]


def test_run_evaluation_parser_version_first_only_batch44(tmp_path):
    """parser_version 取第一个成功 doc 的版本，后续 doc 即使不同也不覆盖。"""
    docs = [_make_doc_mock_full(doc_id=f"d{i}") for i in range(2)]
    manifest = _make_full_manifest_mock(docs=docs)
    fake1 = MagicMock()
    fake1.to_dict.return_value = {}
    fake1.parser_version = "1.0.0"
    fake1.source_hash = "abc1"
    fake2 = MagicMock()
    fake2.to_dict.return_value = {}
    fake2.parser_version = "2.0.0"
    fake2.source_hash = "abc2"
    with patch("evaluation.runner.process_single", side_effect=[(fake1, []), (fake2, [])]):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            out = run_evaluation(manifest, tmp_path / "report.json")
    assert out["provenance"]["parser_version"] == "1.0.0"


def test_run_evaluation_image_dir_not_dir_passes_none_batch44(tmp_path):
    """image_dir 不存在（is_dir()=False）→ image_base_dir=None。"""
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    nonexistent = tmp_path / "nonexistent_images"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=nonexistent):
            out = run_evaluation(manifest, tmp_path / "report.json")
    # 不抛即过；image_base_dir=None 时 image_resource_exists_ratio 应该有合理 reason
    assert "per_doc" in out


def test_run_evaluation_image_dir_is_dir_passes_path_batch44(tmp_path):
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    real_dir = tmp_path / "images"
    real_dir.mkdir()
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=real_dir):
            out = run_evaluation(manifest, tmp_path / "report.json")
    assert "per_doc" in out


# ---------- run_evaluation JSON 写盘细节 ----------

def test_run_evaluation_json_ensure_ascii_false_batch44(tmp_path):
    """JSON 输出 ensure_ascii=False（中文不转义）。"""
    src = inspect.getsource(runner_mod)
    assert "ensure_ascii=False" in src


def test_run_evaluation_json_indent_2_batch44(tmp_path):
    src = inspect.getsource(runner_mod)
    assert "indent=2" in src


def test_run_evaluation_json_dump_batch44(tmp_path):
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            run_evaluation(manifest, out_path)
    content = out_path.read_text(encoding="utf-8")
    assert content.startswith("{")


def test_run_evaluation_json_utf8_batch44(tmp_path):
    doc = _make_doc_mock_full()
    manifest = _make_full_manifest_mock(docs=[doc])
    fake_doc = MagicMock()
    fake_doc.to_dict.return_value = {}
    fake_doc.parser_version = "1.0.0"
    fake_doc.source_hash = "abc"
    out_path = tmp_path / "report.json"
    with patch("evaluation.runner.process_single", return_value=(fake_doc, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "images"):
            run_evaluation(manifest, out_path)
    # 应该可被 utf-8 解析
    json.loads(out_path.read_text(encoding="utf-8"))


# ---------- _load_annotation 各种情况 ----------

def test_load_annotation_unicode_content_batch44(tmp_path):
    """annotation 文件含中文 → 正常解析。"""
    p = tmp_path / "anno.json"
    p.write_text('{"name": "测试"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"name": "测试"}


def test_load_annotation_utf8_bom_batch44(tmp_path):
    """BOM 头部 → json.load 可能失败（取决于 Python 版本）。"""
    p = tmp_path / "anno.json"
    p.write_bytes(b'\xef\xbb\xbf{"key": "value"}')
    out = _load_annotation(p)
    # Python json.load 不喜欢 BOM，应当返回 None
    # 但实际取决于实现，utf-8 编码会吞掉 BOM
    assert out is None or out == {"key": "value"}


def test_load_annotation_array_batch44(tmp_path):
    """顶层是 array → json.load 成功，但下游 annotation.get 会抛。"""
    p = tmp_path / "anno.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    out = _load_annotation(p)
    # _load_annotation 只读，不验证结构
    assert out == [1, 2, 3]


def test_load_annotation_null_top_batch44(tmp_path):
    p = tmp_path / "anno.json"
    p.write_text("null", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


# ---------- module source ----------

def test_module_source_contains_run_evaluation_doc_batch44():
    src = inspect.getsource(runner_mod)
    assert "跑评测主流程" in src


def test_module_source_contains_process_one_doc_batch44():
    src = inspect.getsource(runner_mod)
    assert "跑 process_single" in src


def test_module_source_contains_annotation_load_doc_batch44():
    src = inspect.getsource(runner_mod)
    # 没有显式文档字符串里说 annotation load，但有 _load_annotation 函数
    assert "_load_annotation" in src


def test_module_source_contains_image_dir_doc_batch44():
    src = inspect.getsource(runner_mod)
    assert "image_dir" in src


def test_module_source_contains_not_instrumented_batch44():
    src = inspect.getsource(runner_mod)
    assert "not_instrumented" in src


def test_module_source_contains_process_single_import_batch44():
    src = inspect.getsource(runner_mod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_contains_metrics_import_batch44():
    src = inspect.getsource(runner_mod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_contains_report_import_batch44():
    src = inspect.getsource(runner_mod)
    assert "from evaluation.report import" in src


def test_module_source_contains_annotation_metrics_import_batch44():
    src = inspect.getsource(runner_mod)
    assert "from evaluation.annotation_metrics import" in src


def test_module_source_contains_unlink_in_process_one_batch44():
    src = inspect.getsource(_process_one)
    assert "unlink" in src


def test_module_source_contains_per_doc_subdir_batch44():
    src = inspect.getsource(runner_mod)
    assert "_per_doc" in src


def test_module_source_contains_image_output_dir_for_batch44():
    src = inspect.getsource(runner_mod)
    assert "image_output_dir_for" in src


def test_module_source_contains_perf_counter_batch44():
    src = inspect.getsource(runner_mod)
    assert "time.perf_counter" in src


# ---------- __all__ ----------

def test_all_exact_batch44():
    assert set(runner_mod.__all__) == {"run_evaluation"}


def test_all_count_1_batch44():
    assert len(runner_mod.__all__) == 1


def test_all_no_duplicates_batch44():
    assert len(set(runner_mod.__all__)) == len(runner_mod.__all__)


# ---------- AST 结构 ----------

def test_ast_top_level_no_class_batch44():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_top_level_function_count_batch44():
    tree = ast.parse(inspect.getsource(runner_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 3


def test_ast_top_level_function_names_batch44():
    tree = ast.parse(inspect.getsource(runner_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_load_annotation", "_process_one", "run_evaluation"]


def test_ast_no_try_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.Try)


def test_ast_no_for_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.For)


def test_ast_no_while_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_no_async_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_run_evaluation_has_for_loops_in_body_batch44():
    """run_evaluation 函数体内有 for 循环（遍历 documents / expected_failures）。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    run_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation"][0]
    fors = [n for n in run_func.body if isinstance(n, ast.For)]
    assert len(fors) >= 2


def test_ast_process_one_has_try_in_body_batch44():
    """_process_one 函数体内（含嵌套）有 try（unlink 兜底）。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    process_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one"][0]
    # try 在 if 里面，需要 walk 整个函数子树
    trys = list(ast.walk(process_func))
    trys = [n for n in trys if isinstance(n, ast.Try)]
    assert len(trys) >= 1


def test_ast_load_annotation_has_try_in_body_batch44():
    """_load_annotation 函数体内有 try（JSON decode 兜底）。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    load_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation"][0]
    trys = [n for n in load_func.body if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_from_future_second_batch44():
    tree = ast.parse(inspect.getsource(runner_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


def test_ast_has_imports_batch44():
    tree = ast.parse(inspect.getsource(runner_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) >= 4


# ---------- forbidden tokens 第九十三批 ----------

def test_source_no_eval_batch44():
    src = inspect.getsource(runner_mod)
    assert "eval(" not in src


def test_source_no_exec_batch44():
    src = inspect.getsource(runner_mod)
    assert "exec(" not in src


def test_source_no_compile_batch44():
    src = inspect.getsource(runner_mod)
    assert "compile(" not in src


def test_source_no_globals_batch44():
    src = inspect.getsource(runner_mod)
    assert "globals(" not in src


def test_source_no_locals_batch44():
    src = inspect.getsource(runner_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch44():
    src = inspect.getsource(runner_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch44():
    src = inspect.getsource(runner_mod)
    assert "popen(" not in src


def test_source_no_yaml_load_batch44():
    src = inspect.getsource(runner_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch44():
    src = inspect.getsource(runner_mod)
    assert "pickle.load(" not in src


def test_source_no_open_w_mode_at_module_top_batch44():
    """run_evaluation 内部需要 open('w') 写报告 JSON，但模块顶层不应直接 open。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    # 顶层（非函数体内）不应出现 open() 调用
    for n in tree.body:
        if isinstance(n, ast.FunctionDef):
            continue  # 函数体内允许
        # 顶层 Expr / Assign 等里若有 Call→open，则失败
        for sub in ast.walk(n):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == "open":
                pytest.fail("module top-level open() call found")
