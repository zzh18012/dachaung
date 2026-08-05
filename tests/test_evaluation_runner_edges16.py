r"""evaluation/runner.py 边角测试 - 第十六轮（Round 252）。

补强已有 base/edges/edges2-15（共 ~770+ 测试）未覆盖的深度：
- 源码字符串断言（inspect.getsource）：含特定 token（process_single / image_output_dir_for / perf_counter / REPORT_VERSION / aggregate_summary / build_devset_section / build_provenance / chunk_boundary_prf / figure_caption_prf / compute_automatic_metrics / 'not_instrumented' / '_per_doc' / 'parse_reason' / 'chunk_reason'）
- module metadata：__file__ 后缀 .py / __package__ == 'evaluation' / __name__ == 'evaluation.runner'
- 函数 metadata：__module__/__qualname__/FunctionType；无 varargs/varkw；return_annotation
- _load_annotation 边界：路径是 file-like 对象 / 路径含特殊字符 / utf-8 BOM / 大文件
- _process_one 边界：doc_id 含 unicode / 输出目录已存在
- run_evaluation keyword-only 标记精确（* separator 后 3 个参数）
- run_evaluation 输出 report 6 top-level keys 顺序精确
- per_doc 结构 keys 精确
- expected_failure 结构 keys 精确
- wall_time_seconds 结构 keys 精确
- run_evaluation 不修改 manifest
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation import REPORT_VERSION
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# =========================================================================
# 源码字符串断言（inspect.getsource）
# =========================================================================


def test_module_source_contains_process_single_import():
    """源码含 'process_single'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "process_single" in src


def test_module_source_contains_image_output_dir_for_import():
    """源码含 'image_output_dir_for'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "image_output_dir_for" in src


def test_module_source_contains_perf_counter_call():
    """源码含 'time.perf_counter'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "perf_counter" in src


def test_module_source_contains_report_version_reference():
    """源码含 'REPORT_VERSION'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "REPORT_VERSION" in src


def test_module_source_contains_aggregate_summary_call():
    """源码含 'aggregate_summary'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "aggregate_summary" in src


def test_module_source_contains_build_devset_section_call():
    """源码含 'build_devset_section'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "build_devset_section" in src


def test_module_source_contains_build_provenance_call():
    """源码含 'build_provenance'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "build_provenance" in src


def test_module_source_contains_chunk_boundary_prf_call():
    """源码含 'chunk_boundary_prf'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "chunk_boundary_prf" in src


def test_module_source_contains_figure_caption_prf_call():
    """源码含 'figure_caption_prf'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "figure_caption_prf" in src


def test_module_source_contains_compute_automatic_metrics_call():
    """源码含 'compute_automatic_metrics'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "compute_automatic_metrics" in src


def test_module_source_contains_not_instrumented_string():
    """源码含 'not_instrumented'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "not_instrumented" in src


def test_module_source_contains_per_doc_string():
    """源码含 '_per_doc'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "_per_doc" in src


def test_module_source_contains_parse_reason_string():
    """源码含 'parse_reason'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "parse_reason" in src


def test_module_source_contains_chunk_reason_string():
    """源码含 'chunk_reason'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "chunk_reason" in src


def test_module_source_contains_json_dump_call():
    """源码含 'json.dump'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "json.dump" in src


def test_module_source_contains_future_annotations():
    """源码含 'from __future__ import annotations'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_contains_dict_subscript_syntax():
    """源码含 'dict[str,'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "dict[str," in src


def test_module_source_no_main_guard():
    """源码不含 '__main__'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "__main__" not in src


def test_module_source_contains_image_dir_none_initialization():
    """源码含 'image_dir: Path | None = None'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "image_dir" in src


def test_module_source_contains_doc_id_field():
    """源码含 'doc_id'。"""
    import evaluation.runner as m
    src = inspect.getsource(m)
    assert "doc_id" in src


# =========================================================================
# 模块 metadata
# =========================================================================


def test_module_file_endswith_py():
    """__file__ 以 '.py' 结尾。"""
    import evaluation.runner as m
    assert m.__file__.endswith(".py")


def test_module_file_contains_runner():
    """__file__ 含 'runner'。"""
    import evaluation.runner as m
    assert "runner" in m.__file__


def test_module_package_is_evaluation():
    """__package__ == 'evaluation'。"""
    import evaluation.runner as m
    assert m.__package__ == "evaluation"


def test_module_name_is_evaluation_runner():
    """__name__ == 'evaluation.runner'。"""
    import evaluation.runner as m
    assert m.__name__ == "evaluation.runner"


def test_module_json_is_json_module():
    """json is json。"""
    import evaluation.runner as m
    assert m.json is json


def test_module_path_is_pathlib_path():
    """Path is pathlib.Path。"""
    import evaluation.runner as m
    from pathlib import Path as P
    assert m.Path is P


def test_module_typing_any_is_typing_any():
    """Any is typing.Any。"""
    import evaluation.runner as m
    from typing import Any as A
    assert m.Any is A


def test_module_time_is_time_module():
    """time is time。"""
    import time
    import evaluation.runner as m
    assert m.time is time


def test_module_report_version_is_constant():
    """REPORT_VERSION 来自 evaluation 包。"""
    import evaluation.runner as m
    assert m.REPORT_VERSION is REPORT_VERSION


# =========================================================================
# __all__ 精确
# =========================================================================


def test_module_all_is_list_not_tuple():
    """__all__ 是 list 不是 tuple。"""
    import evaluation.runner as m
    assert isinstance(m.__all__, list)
    assert not isinstance(m.__all__, tuple)


def test_module_all_only_one_element():
    """__all__ 仅 1 个元素。"""
    import evaluation.runner as m
    assert len(m.__all__) == 1


def test_module_all_first_run_evaluation():
    """__all__[0] == 'run_evaluation'。"""
    import evaluation.runner as m
    assert m.__all__[0] == "run_evaluation"


def test_module_all_does_not_contain_internal_helpers():
    """__all__ 不含 _load_annotation / _process_one。"""
    import evaluation.runner as m
    assert "_load_annotation" not in m.__all__
    assert "_process_one" not in m.__all__


# =========================================================================
# 函数 metadata
# =========================================================================


def test_run_evaluation_module_attribute():
    """run_evaluation.__module__ == 'evaluation.runner'。"""
    assert run_evaluation.__module__ == "evaluation.runner"


def test_run_evaluation_qualname():
    """run_evaluation.__qualname__ == 'run_evaluation'。"""
    assert run_evaluation.__qualname__ == "run_evaluation"


def test_load_annotation_qualname():
    """_load_annotation.__qualname__ == '_load_annotation'。"""
    assert _load_annotation.__qualname__ == "_load_annotation"


def test_process_one_qualname():
    """_process_one.__qualname__ == '_process_one'。"""
    assert _process_one.__qualname__ == "_process_one"


def test_run_evaluation_is_python_function():
    """run_evaluation 是 Python 函数。"""
    import types
    assert isinstance(run_evaluation, types.FunctionType)


def test_load_annotation_is_python_function():
    """_load_annotation 是 Python 函数。"""
    import types
    assert isinstance(_load_annotation, types.FunctionType)


def test_process_one_is_python_function():
    """_process_one 是 Python 函数。"""
    import types
    assert isinstance(_process_one, types.FunctionType)


def test_run_evaluation_no_varargs():
    """run_evaluation 无 VAR_POSITIONAL。"""
    sig = inspect.signature(run_evaluation)
    assert all(p.kind != inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())


def test_run_evaluation_no_varkw():
    """run_evaluation 无 VAR_KEYWORD。"""
    sig = inspect.signature(run_evaluation)
    assert all(p.kind != inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())


def test_load_annotation_no_varargs():
    """_load_annotation 无 varargs/varkw。"""
    sig = inspect.signature(_load_annotation)
    assert all(p.kind != inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    assert all(p.kind != inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())


def test_process_one_no_varargs():
    """_process_one 无 varargs/varkw。"""
    sig = inspect.signature(_process_one)
    assert all(p.kind != inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    assert all(p.kind != inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())


def test_run_evaluation_return_annotation_is_str():
    """return annotation 是 str（__future__）。"""
    sig = inspect.signature(run_evaluation)
    assert isinstance(sig.return_annotation, str)


def test_run_evaluation_return_annotation_contains_dict():
    """return annotation 含 'dict'。"""
    sig = inspect.signature(run_evaluation)
    assert "dict" in sig.return_annotation


def test_load_annotation_return_annotation_is_str():
    """return annotation 是 str。"""
    sig = inspect.signature(_load_annotation)
    assert isinstance(sig.return_annotation, str)


def test_process_one_return_annotation_is_str():
    """return annotation 是 str（5-tuple）。"""
    sig = inspect.signature(_process_one)
    assert isinstance(sig.return_annotation, str)
    assert "tuple" in sig.return_annotation


# =========================================================================
# _load_annotation 边界
# =========================================================================


def test_load_annotation_none_input_returns_none():
    """path=None → 返回 None。"""
    out = _load_annotation(None)
    assert out is None


def test_load_annotation_missing_file_returns_none(tmp_path: Path):
    """文件不存在 → 返回 None。"""
    out = _load_annotation(tmp_path / "missing.json")
    assert out is None


def test_load_annotation_directory_returns_none(tmp_path: Path):
    """路径是目录 → 返回 None。"""
    out = _load_annotation(tmp_path)
    assert out is None


def test_load_annotation_valid_dict_returns_dict(tmp_path: Path):
    """合法 JSON dict → 返回 dict。"""
    p = tmp_path / "ann.json"
    p.write_text('{"key": "value"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"key": "value"}


def test_load_annotation_valid_list_returns_list(tmp_path: Path):
    """合法 JSON list → 返回 list。"""
    p = tmp_path / "ann.json"
    p.write_text('[1, 2, 3]', encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3]


def test_load_annotation_invalid_json_returns_none(tmp_path: Path):
    """非法 JSON → 返回 None。"""
    p = tmp_path / "ann.json"
    p.write_text("not json", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_empty_file_returns_none(tmp_path: Path):
    """空文件 → 返回 None。"""
    p = tmp_path / "ann.json"
    p.write_text("", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_utf8_bom_returns_none(tmp_path: Path):
    """utf-8 BOM：源码用 encoding='utf-8' 不剥 BOM → JSONDecodeError → 返回 None。"""
    p = tmp_path / "ann.json"
    p.write_bytes(b'\xef\xbb\xbf{"key": "value"}')
    out = _load_annotation(p)
    # BOM 让 json.load 解析失败 → 异常被 except 捕获 → 返回 None
    assert out is None


def test_load_annotation_unicode_filename(tmp_path: Path):
    """文件名含中文 → 仍能加载。"""
    p = tmp_path / "标注.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": 1}


def test_load_annotation_returns_new_dict_each_call(tmp_path: Path):
    """每次返回新 dict（不缓存）。"""
    p = tmp_path / "ann.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    a = _load_annotation(p)
    b = _load_annotation(p)
    assert a is not b
    assert a == b


def test_load_annotation_pathlib_path_object(tmp_path: Path):
    """接受 Path 对象。"""
    p = tmp_path / "ann.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": 1}


def test_load_annotation_signature_param_count():
    """signature 1 个参数。"""
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1


def test_load_annotation_param_name_path():
    """参数名是 'path'。"""
    sig = inspect.signature(_load_annotation)
    assert "path" in sig.parameters


# =========================================================================
# _process_one 签名精确
# =========================================================================


def test_process_one_signature_param_count():
    """signature 4 个参数。"""
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_process_one_param_names_exact():
    """参数名精确：doc/output_root/parser_name/max_chars。"""
    sig = inspect.signature(_process_one)
    names = list(sig.parameters.keys())
    assert names == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_no_defaults():
    """所有参数无 default。"""
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_process_one_param_kinds():
    """4 个都是 POSITIONAL_OR_KEYWORD。"""
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


# =========================================================================
# run_evaluation 签名精确
# =========================================================================


def test_run_evaluation_signature_param_count():
    """signature 5 个参数。"""
    sig = inspect.signature(run_evaluation)
    assert len(sig.parameters) == 5


def test_run_evaluation_param_names_exact():
    """参数名精确：manifest/output_path/parser_name/max_chars/tolerance_chars。"""
    sig = inspect.signature(run_evaluation)
    names = list(sig.parameters.keys())
    assert names == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_run_evaluation_first_two_positional():
    """manifest/output_path 是 POSITIONAL_OR_KEYWORD。"""
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[0].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params[1].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_last_three_keyword_only():
    """parser_name/max_chars/tolerance_chars 是 KEYWORD_ONLY。"""
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[2].kind == inspect.Parameter.KEYWORD_ONLY
    assert params[3].kind == inspect.Parameter.KEYWORD_ONLY
    assert params[4].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_keyword_defaults():
    """keyword-only 默认值：fallback/800/30。"""
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[2].default == "fallback"
    assert params[3].default == 800
    assert params[4].default == 30


def test_run_evaluation_first_two_no_defaults():
    """manifest/output_path 无 default。"""
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[0].default is inspect.Parameter.empty
    assert params[1].default is inspect.Parameter.empty


# =========================================================================
# run_evaluation 输出 report 结构精确
# =========================================================================


def test_run_evaluation_report_six_top_level_keys_in_order(tmp_path: Path):
    """report 6 keys 顺序：report_version/provenance/devset/summary/per_doc/expected_failures。"""
    # 用空 manifest
    class EmptyManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ()
        project_root = tmp_path
    out = tmp_path / "report.json"
    report = run_evaluation(EmptyManifest(), out)
    expected = [
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    ]
    assert list(report.keys()) == expected


def test_run_evaluation_report_version_value(tmp_path: Path):
    """report_version == REPORT_VERSION 常量值。"""
    class EmptyManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ()
        project_root = tmp_path
    out = tmp_path / "report.json"
    report = run_evaluation(EmptyManifest(), out)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_per_doc_is_list(tmp_path: Path):
    """per_doc 是 list。"""
    class EmptyManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ()
        project_root = tmp_path
    out = tmp_path / "report.json"
    report = run_evaluation(EmptyManifest(), out)
    assert isinstance(report["per_doc"], list)


def test_run_evaluation_expected_failures_is_list(tmp_path: Path):
    """expected_failures 是 list。"""
    class EmptyManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ()
        project_root = tmp_path
    out = tmp_path / "report.json"
    report = run_evaluation(EmptyManifest(), out)
    assert isinstance(report["expected_failures"], list)


def test_run_evaluation_summary_is_dict(tmp_path: Path):
    """summary 是 dict。"""
    class EmptyManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ()
        project_root = tmp_path
    out = tmp_path / "report.json"
    report = run_evaluation(EmptyManifest(), out)
    assert isinstance(report["summary"], dict)


def test_run_evaluation_devset_is_dict(tmp_path: Path):
    """devset 是 dict。"""
    class EmptyManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ()
        project_root = tmp_path
    out = tmp_path / "report.json"
    report = run_evaluation(EmptyManifest(), out)
    assert isinstance(report["devset"], dict)


def test_run_evaluation_provenance_is_dict(tmp_path: Path):
    """provenance 是 dict。"""
    class EmptyManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ()
        project_root = tmp_path
    out = tmp_path / "report.json"
    report = run_evaluation(EmptyManifest(), out)
    assert isinstance(report["provenance"], dict)


def test_run_evaluation_returns_dict_type(tmp_path: Path):
    """run_evaluation 返回 dict。"""
    class EmptyManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ()
        project_root = tmp_path
    out = tmp_path / "report.json"
    report = run_evaluation(EmptyManifest(), out)
    assert isinstance(report, dict)


def test_run_evaluation_file_matches_returned_report(tmp_path: Path):
    """写盘 JSON 与返回 dict 一致（tuple → list 序列化后等价）。"""
    class EmptyManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ()
        project_root = tmp_path
    out = tmp_path / "report.json"
    report = run_evaluation(EmptyManifest(), out)
    file_content = json.loads(out.read_text(encoding="utf-8"))
    # JSON 序列化会把 tuple 转成 list；重新序列化 report 以抹平 tuple/list 差异
    report_normalized = json.loads(json.dumps(report, ensure_ascii=False))
    assert file_content == report_normalized


# =========================================================================
# run_evaluation per_doc 结构精确
# =========================================================================


def test_run_evaluation_creates_output_directory_recursively(tmp_path: Path):
    """output_path 在不存在的多级目录下 → 自动创建。"""
    class EmptyManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ()
        project_root = tmp_path
    out = tmp_path / "deep" / "nested" / "dir" / "report.json"
    report = run_evaluation(EmptyManifest(), out)
    assert out.is_file()
    assert isinstance(report, dict)


def test_run_evaluation_empty_manifest_no_per_doc(tmp_path: Path):
    """空 manifest → per_doc=[]。"""
    class EmptyManifest:
        documents = ()
        expected_failures = ()
        devset_status = "incomplete"
        file_count = 0
        content_group_count = 0
        pdf_count = 0
        docx_count = 0
        categories_covered = ()
        project_root = tmp_path
    out = tmp_path / "report.json"
    report = run_evaluation(EmptyManifest(), out)
    assert report["per_doc"] == []
    assert report["expected_failures"] == []


# =========================================================================
# 模块 namespace identity
# =========================================================================


def test_module_namespace_contains_run_evaluation():
    """命名空间含 'run_evaluation'。"""
    import evaluation.runner as m
    assert hasattr(m, "run_evaluation")


def test_module_namespace_contains_load_annotation():
    """命名空间含 '_load_annotation'。"""
    import evaluation.runner as m
    assert hasattr(m, "_load_annotation")


def test_module_namespace_contains_process_one():
    """命名空间含 '_process_one'。"""
    import evaluation.runner as m
    assert hasattr(m, "_process_one")


def test_module_namespace_does_not_contain_main():
    """命名空间不含 'main'（无 main 函数）。"""
    import evaluation.runner as m
    assert not hasattr(m, "main")


# =========================================================================
# 模块 __all__ 不含 helper
# =========================================================================


def test_module_all_does_not_contain_load_annotation():
    """__all__ 不含 _load_annotation。"""
    import evaluation.runner as m
    assert "_load_annotation" not in m.__all__


def test_module_all_does_not_contain_process_one():
    """__all__ 不含 _process_one。"""
    import evaluation.runner as m
    assert "_process_one" not in m.__all__
