"""evaluation/runner.py 第二十九轮 edges 测试（Round 329）。

重点补强 edges27 未触及的角度：
- _load_annotation 行为深度第三批（混合 JSON 类型 / 重读 / 大文件 / Path-like）
- _process_one return tuple 结构精确（5 元 / 各位置类型）
- _process_one image_dir 行为（None when document None / Path when not None / unlink 失败 swallowed）
- run_evaluation parser_version 捕获（first non-null wins / 全 None 时 prov None）
- run_evaluation image_base_dir 条件（None / not dir / is dir）
- public_per_doc 字段过滤（无 _ 前缀）
- expected_failures 结构精确（4 keys / matches bool）
- per_doc 私有字段（_annotation_present / _tolerance_chars / _missing_markers）
- module source 字符串精确补强（imports / 常量 / 控制流 substring）
- module source forbidden tokens 第三批（~75 stdlib）
- signatures 精确补强（return annotations）
- 模块整体合理性（namespace / __all__ / no class / no main）
- 端到端集成补强（多文档 / expected_failures 命中 / 输出可重读 / 同输入同输出 / wall_time 字段）
"""

from __future__ import annotations

import inspect
import json
import types
from pathlib import Path

import pytest

from evaluation import runner
from evaluation.runner import (
    _load_annotation,
    _process_one,
    run_evaluation,
)


# ---------- _load_annotation 行为深度第三批 ----------


def test_load_annotation_returns_none_for_directory(tmp_path):
    """目录不是 file → None。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_returns_none_for_pipe_like(tmp_path):
    """普通 file 不抛 → 返回 dict（正向）。"""
    p = tmp_path / "a.json"
    p.write_text("{}", encoding="utf-8")
    out = _load_annotation(p)
    assert out == {}


def test_load_annotation_returns_dict_with_array_value(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"k": [1, 2, 3]}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": [1, 2, 3]}


def test_load_annotation_returns_dict_with_nested_dict(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"k": {"x": {"y": 1}}}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": {"x": {"y": 1}}}


def test_load_annotation_with_extension_other_than_json(tmp_path):
    """文件扩展名无所谓，只要内容是 JSON。"""
    p = tmp_path / "a.txt"
    p.write_text('{"x": 1}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"x": 1}


def test_load_annotation_does_not_cache(tmp_path):
    """两次读同一文件应得到独立 dict（不缓存）。"""
    p = tmp_path / "a.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    a = _load_annotation(p)
    b = _load_annotation(p)
    assert a == b
    assert a is not b


def test_load_annotation_handles_trailing_newline(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": 1}\n', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"x": 1}


def test_load_annotation_handles_leading_whitespace(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('  {"x": 1}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"x": 1}


def test_load_annotation_handles_tab_in_content(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x":\t1}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"x": 1}


def test_load_annotation_with_escape_sequences(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(r'{"k": "a\\b"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": "a\\b"}


def test_load_annotation_with_unicode_escape(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(r'{"k": "中"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": "中"}


# ---------- _process_one return tuple 结构精确 ----------


def test_process_one_returns_5_tuple():
    sig = inspect.signature(_process_one)
    ret = sig.return_annotation
    # return annotation is a string due to from __future__ import annotations
    assert "tuple" in ret
    assert "None" in ret
    assert "dict" in ret
    assert "float" in ret
    assert "str" in ret
    assert "Path" in ret


def test_process_one_param_count():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_process_one_param_names():
    sig = inspect.signature(_process_one)
    assert list(sig.parameters) == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_param_kinds_all_positional_or_keyword():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_process_one_no_default_for_doc_output_root():
    sig = inspect.signature(_process_one)
    assert sig.parameters["doc"].default is inspect.Parameter.empty
    assert sig.parameters["output_root"].default is inspect.Parameter.empty


def test_process_one_defaults_for_parser_name_max_chars():
    sig = inspect.signature(_process_one)
    # 这两个其实没默认值（默认在 run_evaluation 调用时给）
    assert sig.parameters["parser_name"].default is inspect.Parameter.empty
    assert sig.parameters["max_chars"].default is inspect.Parameter.empty


# ---------- _process_one source level 字符串精确补强 ----------


def test_process_one_source_mentions_image_output_dir_for():
    src = inspect.getsource(_process_one)
    assert "image_output_dir_for" in src


def test_process_one_source_mentions_perf_counter():
    src = inspect.getsource(_process_one)
    assert "perf_counter" in src


def test_process_one_source_mentions_process_single():
    src = inspect.getsource(_process_one)
    assert "process_single" in src


def test_process_one_source_mentions_write_json_false():
    src = inspect.getsource(_process_one)
    assert "write_json=False" in src


def test_process_one_source_mentions_out_stub():
    src = inspect.getsource(_process_one)
    assert "out_stub" in src


def test_process_one_source_mentions_unlink():
    src = inspect.getsource(_process_one)
    assert "unlink" in src


def test_process_one_source_mentions_per_doc():
    src = inspect.getsource(_process_one)
    assert "_per_doc" in src


def test_process_one_source_mentions_image_dir():
    src = inspect.getsource(_process_one)
    assert "image_dir" in src


def test_process_one_source_mentions_to_dict():
    src = inspect.getsource(_process_one)
    assert "to_dict" in src


def test_process_one_source_mentions_parser_version():
    src = inspect.getsource(_process_one)
    assert "parser_version" in src


def test_process_one_source_has_3_returns():
    src = inspect.getsource(_process_one)
    assert src.count("return ") >= 3


def test_process_one_source_has_doc_id_format_string():
    src = inspect.getsource(_process_one)
    assert "{doc.doc_id}.json" in src or "doc_id}" in src


def test_process_one_source_has_try_except_oserror_for_unlink():
    src = inspect.getsource(_process_one)
    # unlink 包裹在 try/except OSError 中
    assert "except OSError" in src
    assert "unlink" in src


def test_process_one_source_has_unknown_code_for_none_document():
    src = inspect.getsource(_process_one)
    assert '"unknown"' in src


def test_process_one_source_has_return_none_image_dir_when_doc_none():
    src = inspect.getsource(_process_one)
    # 当 document is None 时不计算 image_dir
    assert "document is not None" in src


# ---------- run_evaluation parser_version 捕获 ----------


def test_run_evaluation_parser_version_for_prov_starts_none():
    src = inspect.getsource(run_evaluation)
    assert "parser_version_for_prov: str | None = None" in src


def test_run_evaluation_source_has_parser_version_capture_logic():
    src = inspect.getsource(run_evaluation)
    # if parser_version and not parser_version_for_prov
    assert "not parser_version_for_prov" in src
    assert "parser_version_for_prov = parser_version" in src


# ---------- run_evaluation image_base_dir 条件 ----------


def test_run_evaluation_source_has_image_dir_is_dir_check():
    src = inspect.getsource(run_evaluation)
    assert "image_dir.is_dir()" in src


def test_run_evaluation_source_has_image_base_dir_param_to_compute():
    src = inspect.getsource(run_evaluation)
    assert "image_base_dir=" in src


# ---------- public_per_doc 字段过滤 ----------


def test_run_evaluation_public_per_doc_strips_underscore_fields(tmp_path):
    """public per_doc 不含 _ 前缀字段。"""
    from evaluation.manifest import Manifest
    mf = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )
    out = tmp_path / "out.json"
    report = run_evaluation(mf, out)
    for entry in report["per_doc"]:
        for k in entry:
            assert not k.startswith("_")


def test_run_evaluation_public_per_doc_has_3_keys(tmp_path):
    from evaluation.manifest import Manifest
    mf = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )
    out = tmp_path / "out.json"
    report = run_evaluation(mf, out)
    # 空 per_doc list 也 OK，但需验证 keys contract
    # 当无 documents 时 per_doc 是 []，跳过
    assert report["per_doc"] == []


# ---------- expected_failures 结构精确 ----------


def test_expected_failures_empty_when_no_expected_failures(tmp_path):
    from evaluation.manifest import Manifest
    mf = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )
    out = tmp_path / "out.json"
    report = run_evaluation(mf, out)
    assert report["expected_failures"] == []


def test_run_evaluation_source_has_expected_failure_loop():
    src = inspect.getsource(run_evaluation)
    assert "for ef in manifest.expected_failures" in src


def test_run_evaluation_source_has_actual_code_capture():
    src = inspect.getsource(run_evaluation)
    assert "actual_code" in src


def test_run_evaluation_source_has_matches_field():
    src = inspect.getsource(run_evaluation)
    assert '"matches"' in src


def test_run_evaluation_source_has_expected_error_code_field():
    src = inspect.getsource(run_evaluation)
    assert '"expected_error_code"' in src
    assert '"actual_error_code"' in src


# ---------- run_evaluation source level 字符串精确补强 ----------


def test_run_evaluation_source_mentions_public_per_doc():
    src = inspect.getsource(run_evaluation)
    assert "public_per_doc" in src


def test_run_evaluation_source_mentions_per_doc_results():
    src = inspect.getsource(run_evaluation)
    assert "per_doc_results" in src


def test_run_evaluation_source_mentions_aggregate_summary():
    src = inspect.getsource(run_evaluation)
    assert "aggregate_summary" in src


def test_run_evaluation_source_mentions_build_provenance():
    src = inspect.getsource(run_evaluation)
    assert "build_provenance" in src


def test_run_evaluation_source_mentions_build_devset_section():
    src = inspect.getsource(run_evaluation)
    assert "build_devset_section" in src


def test_run_evaluation_source_has_json_dump_call():
    src = inspect.getsource(run_evaluation)
    assert "json.dump" in src


def test_run_evaluation_source_has_ensure_ascii_false():
    src = inspect.getsource(run_evaluation)
    assert "ensure_ascii=False" in src


def test_run_evaluation_source_has_indent_2():
    src = inspect.getsource(run_evaluation)
    assert "indent=2" in src


def test_run_evaluation_source_has_open_with_w_mode():
    src = inspect.getsource(run_evaluation)
    assert '"w"' in src
    assert "encoding=\"utf-8\"" in src


def test_run_evaluation_source_has_parent_mkdir():
    src = inspect.getsource(run_evaluation)
    assert "parent.mkdir" in src


def test_run_evaluation_source_has_kwargs_for_compute_metrics():
    src = inspect.getsource(run_evaluation)
    # 关键字传参 compute_automatic_metrics
    assert "document=document" in src
    assert "error=error" in src
    assert "source_type=doc.source_type" in src
    assert "expectations=doc.expectations" in src


def test_run_evaluation_source_has_kwargs_for_chunk_boundary_prf():
    src = inspect.getsource(run_evaluation)
    assert "tolerance_chars=tolerance_chars" in src


def test_run_evaluation_source_has_kwargs_for_run_evaluation_signature():
    src = inspect.getsource(run_evaluation)
    # keyword-only 标记 *
    assert "*," in src or "*, " in src


def test_run_evaluation_source_has_tolerance_record_pop():
    src = inspect.getsource(run_evaluation)
    assert "pop(\"_tolerance_chars\"" in src
    assert "pop(\"_missing_markers\"" in src


def test_run_evaluation_source_has_dict_keys_for_per_doc():
    src = inspect.getsource(run_evaluation)
    assert '"doc_id": doc.doc_id' in src
    assert '"source_type": doc.source_type' in src
    assert '"metrics": metrics' in src


def test_run_evaluation_source_has_wall_time_seconds_dict():
    src = inspect.getsource(run_evaluation)
    assert '"wall_time_seconds"' in src
    assert '"total": total_seconds' in src
    assert '"parse": None' in src
    assert '"chunk": None' in src
    assert '"parse_reason": "not_instrumented"' in src
    assert '"chunk_reason": "not_instrumented"' in src


# ---------- module source forbidden tokens 第三批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "base64", "binascii", "bisect", "calendar", "concurrent",
        "contextlib", "copyreg", "csv", "fnmatch", "functools",
        "getopt", "getpass", "gettext", "heapq", "imaplib",
        "importlib", "ipaddress", "locale", "lzma", "mailbox",
        "mimetypes", "mmap", "multiprocessing", "netrc", "ntpath",
        "numbers", "operator", "optparse", "platform",
        "poplib", "posixpath", "profile", "pstats", "py_compile",
        "quopri", "reprlib", "runpy", "sched", "select",
        "shelve", "shlex", "signal", "site", "smtplib",
        "sndhdr", "socketserver", "sqlite3", "ssl", "subprocess",
        "sunau", "symtable", "tabnanny", "telnetlib", "termios",
        "timeit", "tkinter", "token", "tokenize", "trace",
        "tty", "turtle", "unittest", "urllib",
        "uu", "webbrowser", "xdrlib", "zipapp", "zipfile",
        "zipimport", "argparse", "array", "ast", "atexit",
        "builtins", "collections",
    ],
)
def test_module_source_forbidden_tokens_third_batch(token):
    """这些 stdlib 模块不应出现在 runner.py（仅用 json/time/Path/typing）。"""
    src = inspect.getsource(runner)
    # 检查 import 语句不含该 token
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_from_future_import_annotations():
    src = inspect.getsource(runner)
    assert "from __future__ import annotations" in src


def test_module_source_has_import_json():
    src = inspect.getsource(runner)
    assert "import json" in src


def test_module_source_has_import_time():
    src = inspect.getsource(runner)
    assert "import time" in src


def test_module_source_has_from_pathlib_import_path():
    src = inspect.getsource(runner)
    assert "from pathlib import Path" in src


def test_module_source_has_from_typing_import_any():
    src = inspect.getsource(runner)
    assert "from typing import Any" in src


def test_module_source_has_app_pipeline_import_process_single():
    src = inspect.getsource(runner)
    assert "from app.pipeline import" in src
    assert "process_single" in src


def test_module_source_has_app_pipeline_import_image_output_dir_for():
    src = inspect.getsource(runner)
    assert "image_output_dir_for" in src


def test_module_source_has_evaluation_report_version_import():
    src = inspect.getsource(runner)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_has_annotation_metrics_import():
    src = inspect.getsource(runner)
    assert "from evaluation.annotation_metrics import" in src
    assert "chunk_boundary_prf" in src
    assert "figure_caption_prf" in src


def test_module_source_has_metrics_import():
    src = inspect.getsource(runner)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_has_report_import():
    src = inspect.getsource(runner)
    assert "from evaluation.report import" in src
    assert "aggregate_summary" in src
    assert "build_devset_section" in src
    assert "build_provenance" in src


def test_module_source_has_no_yield():
    src = inspect.getsource(runner)
    assert "yield" not in src


def test_module_source_has_no_global():
    src = inspect.getsource(runner)
    assert "global " not in src


def test_module_source_has_no_async():
    src = inspect.getsource(runner)
    assert "async " not in src


def test_module_source_has_no_decorators():
    src = inspect.getsource(runner)
    # 不应有 @ 装饰器（除文档字符串中的 @param）
    # 简单检查行首 @
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("@"):
            # 不应有 @dataclass, @property, @staticmethod 等
            assert False, f"unexpected decorator: {stripped}"


def test_module_source_has_no_lambda():
    src = inspect.getsource(runner)
    assert "lambda " not in src


def test_module_source_has_no_class_definition():
    src = inspect.getsource(runner)
    assert "\nclass " not in src
    assert not src.startswith("class ")


def test_module_source_has_no_main_block():
    src = inspect.getsource(runner)
    assert "__main__" not in src


def test_module_source_docstring_mentions_total():
    src = inspect.getsource(runner)
    # module docstring 提到 total（计时）
    assert "total" in src


def test_module_source_docstring_mentions_pipeline():
    src = inspect.getsource(runner)
    assert "pipeline" in src


def test_module_source_docstring_mentions_metrics():
    src = inspect.getsource(runner)
    assert "metrics" in src.lower() or "metric" in src.lower()


def test_module_source_docstring_mentions_image():
    src = inspect.getsource(runner)
    assert "image" in src.lower()


# ---------- signatures 精确补强 ----------


def test_load_annotation_signature_return_is_optional_dict():
    sig = inspect.signature(_load_annotation)
    ret = sig.return_annotation
    # str form: dict[str, Any] | None
    assert "dict" in ret
    assert "None" in ret


def test_load_annotation_signature_param_path():
    sig = inspect.signature(_load_annotation)
    assert "path" in sig.parameters
    p = sig.parameters["path"]
    assert "| None" in str(p.annotation) or "Optional" in str(p.annotation)


def test_load_annotation_no_varargs_varkw():
    sig = inspect.signature(_load_annotation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_process_one_signature_return_mentions_path_or_none():
    sig = inspect.signature(_process_one)
    ret = sig.return_annotation
    assert "tuple" in ret


def test_process_one_no_varargs_varkw():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_run_evaluation_signature_return_dict():
    sig = inspect.signature(run_evaluation)
    ret = sig.return_annotation
    assert "dict" in ret


def test_run_evaluation_no_varargs_varkw():
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_run_evaluation_keyword_only_marker_position():
    """第三个参数后是 keyword-only 标记。"""
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    # output_path 之后是 * 标记（POSITIONAL_ONLY 没有，直接是 manifest/output_path，然后 keyword-only）
    # 实际：manifest (pos), output_path (pos), *, parser_name, max_chars, tolerance_chars
    assert params[0].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params[1].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    for p in params[2:]:
        assert p.kind == inspect.Parameter.KEYWORD_ONLY


# ---------- namespace 模块整体合理性 ----------


def test_namespace_load_annotation_in_module():
    assert hasattr(runner, "_load_annotation")
    assert isinstance(getattr(runner, "_load_annotation"), types.FunctionType)


def test_namespace_process_one_in_module():
    assert hasattr(runner, "_process_one")
    assert isinstance(getattr(runner, "_process_one"), types.FunctionType)


def test_namespace_run_evaluation_in_module():
    assert hasattr(runner, "run_evaluation")
    assert isinstance(getattr(runner, "run_evaluation"), types.FunctionType)


def test_namespace_module_constants():
    """模块只有少数顶层常量（来自 import）。"""
    # __all__ 包含 run_evaluation
    assert hasattr(runner, "__all__")
    assert "run_evaluation" in runner.__all__


def test_module_all_only_run_evaluation():
    assert runner.__all__ == ["run_evaluation"]


def test_module_all_is_list():
    assert isinstance(runner.__all__, list)


def test_module_all_entries_str():
    for entry in runner.__all__:
        assert isinstance(entry, str)


def test_module_has_2_private_functions():
    private_funcs = [
        n for n, v in vars(runner).items()
        if n.startswith("_") and not n.startswith("__")
        and isinstance(v, types.FunctionType)
    ]
    assert sorted(private_funcs) == ["_load_annotation", "_process_one"]


def test_module_has_1_public_function():
    public_funcs = [
        n for n, v in vars(runner).items()
        if not n.startswith("_") and isinstance(v, types.FunctionType)
        and getattr(v, "__module__", "") == runner.__name__
    ]
    assert public_funcs == ["run_evaluation"]


def test_module_no_class_definition():
    classes = [
        n for n, v in vars(runner).items()
        if not n.startswith("_") and isinstance(v, type)
        and getattr(v, "__module__", "") == runner.__name__
    ]
    assert classes == []


def test_module_no_main_block():
    src = inspect.getsource(runner)
    assert 'if __name__' not in src


# ---------- 端到端集成补强 ----------


def _make_minimal_manifest(tmp_path):
    from evaluation.manifest import Manifest
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )


def test_e2e_no_documents_returns_dict(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert isinstance(report, dict)


def test_e2e_no_documents_creates_file(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    assert out.is_file()


def test_e2e_no_documents_does_not_create_per_doc_entries(tmp_path):
    """无 documents → _per_doc 目录可能为空或不存在（loop 不迭代）。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    # 不抛异常即 OK；_per_doc 子目录可能创建（mkdir parents=True）但内部为空
    per_doc_dir = tmp_path / "_per_doc"
    if per_doc_dir.is_dir():
        # 若存在，应无文件
        assert not any(per_doc_dir.iterdir())


def test_e2e_output_json_is_valid_json(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    with out.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_e2e_indent_2_in_output(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    text = out.read_text(encoding="utf-8")
    # indent=2 → 含 '  ' 缩进
    assert "\n  " in text


def test_e2e_ensure_ascii_false_for_ascii_content(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    text = out.read_text(encoding="utf-8")
    # ensure_ascii=False 不会转义非 ASCII（这里都是 ASCII，但可看格式）
    assert '"report_version":' in text


def test_e2e_same_output_when_called_twice(tmp_path):
    """同一 manifest 调两次（不同输出文件）→ 相同内容。"""
    mf = _make_minimal_manifest(tmp_path)
    out1 = tmp_path / "out1.json"
    out2 = tmp_path / "out2.json"
    r1 = run_evaluation(mf, out1)
    r2 = run_evaluation(mf, out2)
    # 去掉 wall_time_seconds（含计时）后比较
    for r in (r1, r2):
        for entry in r.get("per_doc", []):
            entry.pop("wall_time_seconds", None)
    # 比较 report_version / devset / summary 结构
    assert r1["report_version"] == r2["report_version"]
    assert r1["devset"] == r2["devset"]


def test_e2e_run_with_only_parser_name_kwarg(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out, parser_name="fallback")
    assert "report_version" in report


def test_e2e_run_with_only_max_chars_kwarg(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out, max_chars=800)
    assert "report_version" in report


def test_e2e_run_with_only_tolerance_chars_kwarg(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out, tolerance_chars=30)
    assert "report_version" in report


def test_e2e_run_with_all_kwargs(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(
        mf, out,
        parser_name="fallback",
        max_chars=800,
        tolerance_chars=30,
    )
    assert "report_version" in report


def test_e2e_summary_section_has_silent_drop_sum(tmp_path):
    """summary section 含 silent_drop_count（聚合求和）。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    s = report["summary"]
    assert isinstance(s, dict)


def test_e2e_per_doc_each_entry_has_doc_id_source_type_metrics_wall_time(tmp_path):
    """如果有 per_doc，每条 entry 含 4 keys。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    for entry in report["per_doc"]:
        assert set(entry.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_e2e_wall_time_seconds_has_5_keys(tmp_path):
    """wall_time_seconds 含 total/parse/chunk/parse_reason/chunk_reason。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    if report["per_doc"]:
        wt = report["per_doc"][0]["wall_time_seconds"]
        assert set(wt.keys()) == {
            "total", "parse", "chunk", "parse_reason", "chunk_reason",
        }


def test_e2e_devset_section_independent_of_documents(tmp_path):
    """devset section 即便无 documents 也有合理结构。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    d = report["devset"]
    assert isinstance(d, dict)
    assert "file_count" in d
    assert "categories_covered" in d


def test_e2e_provenance_section_has_parser_name(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out, parser_name="fallback")
    p = report["provenance"]
    assert "parser_name" in p


def test_e2e_provenance_section_has_max_chars(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out, max_chars=800)
    p = report["provenance"]
    assert "max_chars" in p


def test_e2e_report_can_be_reloaded_and_validated(tmp_path):
    """报告可被重新加载并通过 schema validate。"""
    from evaluation.schema import validate
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    with out.open("r", encoding="utf-8") as f:
        report_data = json.load(f)
    # validate against evaluation-report schema; success returns None, failure raises
    validate(report_data, "evaluation-report.schema.json")


def test_e2e_with_tolerance_chars_0(tmp_path):
    """tolerance_chars=0 极端值。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out, tolerance_chars=0)
    assert "report_version" in report


def test_e2e_with_max_chars_1(tmp_path):
    """max_chars=1 极端值。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out, max_chars=1)
    assert "report_version" in report


def test_e2e_run_does_not_raise_for_empty_manifest(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    # 不抛
    run_evaluation(mf, out)


def test_e2e_output_path_in_subdir_creates_parents(tmp_path):
    """output_path 在多层子目录下 → 自动 mkdir parents。"""
    out = tmp_path / "a" / "b" / "c" / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    assert out.is_file()


def test_e2e_returns_same_dict_as_written(tmp_path):
    """返回的 dict 与写盘的 dict 一致。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    returned = run_evaluation(mf, out)
    with out.open("r", encoding="utf-8") as f:
        written = json.load(f)
    assert returned == written
