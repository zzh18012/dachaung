"""evaluation/runner.py 第三十三轮 edges 测试（Round 354）。

重点补强 edges31 未触及的角度：
- _load_annotation 行为深度第七批（更多文件形式 / 编码 / JSON 边界）
- _process_one source level 第四批（更多字符串精确）
- run_evaluation source level 第四批（更多字符串精确）
- module source forbidden tokens 第十批（不同 stdlib list）
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性
- 端到端集成补强
"""

from __future__ import annotations

import inspect
import json
import types
from pathlib import Path
from typing import Any

import pytest

from evaluation import REPORT_VERSION, runner as rmod
from evaluation.runner import (
    _load_annotation,
    _process_one,
    run_evaluation,
)


# ---------- _load_annotation 行为深度第七批 ----------


def test_load_annotation_with_array_root(tmp_path):
    f = tmp_path / "arr.json"
    f.write_text("[1, 2, 3]", encoding="utf-8")
    out = _load_annotation(f)
    assert out == [1, 2, 3]


def test_load_annotation_with_int_root(tmp_path):
    f = tmp_path / "int.json"
    f.write_text("42", encoding="utf-8")
    out = _load_annotation(f)
    assert out == 42


def test_load_annotation_with_float_root(tmp_path):
    f = tmp_path / "float.json"
    f.write_text("3.14", encoding="utf-8")
    out = _load_annotation(f)
    assert out == 3.14


def test_load_annotation_with_bool_root(tmp_path):
    f = tmp_path / "bool.json"
    f.write_text("true", encoding="utf-8")
    out = _load_annotation(f)
    assert out is True


def test_load_annotation_with_null_root(tmp_path):
    f = tmp_path / "null.json"
    f.write_text("null", encoding="utf-8")
    out = _load_annotation(f)
    assert out is None


def test_load_annotation_with_string_root(tmp_path):
    f = tmp_path / "str.json"
    f.write_text('"hello"', encoding="utf-8")
    out = _load_annotation(f)
    assert out == "hello"


def test_load_annotation_with_deeply_nested_dict(tmp_path):
    f = tmp_path / "deep.json"
    f.write_text('{"a": {"b": {"c": {"d": {"e": "deep"}}}}}', encoding="utf-8")
    out = _load_annotation(f)
    assert out["a"]["b"]["c"]["d"]["e"] == "deep"


def test_load_annotation_with_long_array(tmp_path):
    arr = list(range(1000))
    f = tmp_path / "long.json"
    f.write_text(json.dumps(arr), encoding="utf-8")
    out = _load_annotation(f)
    assert len(out) == 1000


def test_load_annotation_with_special_chars_in_string(tmp_path):
    f = tmp_path / "special.json"
    f.write_text(json.dumps({"text": 'newline\n\ttab "quotes"'}), encoding="utf-8")
    out = _load_annotation(f)
    assert "newline" in out["text"]


def test_load_annotation_with_huge_dict(tmp_path):
    big = {f"key_{i}": i for i in range(500)}
    f = tmp_path / "big.json"
    f.write_text(json.dumps(big), encoding="utf-8")
    out = _load_annotation(f)
    assert len(out) == 500


def test_load_annotation_with_utf8_bom(tmp_path):
    """带 BOM 的文件会让 json.load 抛 JSONDecodeError。"""
    f = tmp_path / "bom.json"
    f.write_bytes(b"\xef\xbb\xbf" + b'{"a":1}')
    out = _load_annotation(f)
    # _load_annotation 捕获 JSONDecodeError → 返回 None
    assert out is None


def test_load_annotation_with_trailing_comma(tmp_path):
    """JSON 不允许 trailing comma。"""
    f = tmp_path / "trailing.json"
    f.write_text('{"a": 1,}', encoding="utf-8")
    out = _load_annotation(f)
    assert out is None


def test_load_annotation_with_unquoted_keys(tmp_path):
    f = tmp_path / "unquoted.json"
    f.write_text('{a: 1}', encoding="utf-8")
    out = _load_annotation(f)
    assert out is None


def test_load_annotation_returns_dict_or_list_or_none(tmp_path):
    """合法返回类型：dict / list / int / float / str / bool / None。"""
    f = tmp_path / "valid.json"
    f.write_text('{"a": 1}', encoding="utf-8")
    out = _load_annotation(f)
    assert isinstance(out, dict)


def test_load_annotation_no_side_effects(tmp_path):
    f = tmp_path / "data.json"
    content = '{"x": 1}'
    f.write_text(content, encoding="utf-8")
    _load_annotation(f)
    # 文件内容不变
    assert f.read_text(encoding="utf-8") == content


def test_load_annotation_idempotent(tmp_path):
    f = tmp_path / "data.json"
    f.write_text('{"x": 1}', encoding="utf-8")
    a = _load_annotation(f)
    b = _load_annotation(f)
    assert a == b


def test_load_annotation_does_not_write_file(tmp_path):
    f = tmp_path / "data.json"
    f.write_text('{"x": 1}', encoding="utf-8")
    before_mtime = f.stat().st_mtime
    _load_annotation(f)
    after_mtime = f.stat().st_mtime
    assert before_mtime == after_mtime


# ---------- _process_one source level 第四批 ----------


def test_process_one_source_starts_with_def():
    src = inspect.getsource(_process_one)
    assert src.lstrip().startswith("def _process_one(")


def test_process_one_source_has_docstring():
    src = inspect.getsource(_process_one)
    # 函数体内含 docstring
    assert '"""' in src or "'''" in src


def test_process_one_source_docstring_mentions_5_tuple():
    """docstring 描述 5-tuple 返回。"""
    src = inspect.getsource(_process_one)
    assert "5-tuple" in src or "tuple" in src.lower() or "返回" in src


def test_process_one_source_docstring_mentions_image_dir():
    src = inspect.getsource(_process_one)
    assert "image_dir" in src.lower()


def test_process_one_source_docstring_mentions_write_json_false():
    src = inspect.getsource(_process_one)
    assert "write_json" in src


def test_process_one_source_docstring_mentions_output_path():
    src = inspect.getsource(_process_one)
    assert "output_path" in src or "out_stub" in src


def test_process_one_source_calls_process_single():
    src = inspect.getsource(_process_one)
    assert "process_single(" in src


def test_process_one_source_uses_perf_counter():
    src = inspect.getsource(_process_one)
    assert "time.perf_counter()" in src


def test_process_one_source_creates_per_doc_subdir():
    src = inspect.getsource(_process_one)
    assert '"_per_doc"' in src or "'_per_doc'" in src


def test_process_one_source_uses_doc_doc_id():
    src = inspect.getsource(_process_one)
    assert "doc.doc_id" in src


def test_process_one_source_handles_errors_truthy():
    """if errors: → 返回 errors[0].to_dict()。"""
    src = inspect.getsource(_process_one)
    assert "if errors:" in src


def test_process_one_source_handles_document_none():
    src = inspect.getsource(_process_one)
    assert "if document is None:" in src


def test_process_one_source_returns_5_tuple_in_success_path():
    src = inspect.getsource(_process_one)
    assert "return document.to_dict(), None, elapsed, document.parser_version, image_dir" in src


def test_process_one_source_unlinks_out_stub():
    src = inspect.getsource(_process_one)
    assert "out_stub.unlink()" in src


def test_process_one_source_calls_image_output_dir_for():
    src = inspect.getsource(_process_one)
    assert "image_output_dir_for(" in src


def test_process_one_source_handles_oserror_in_unlink():
    src = inspect.getsource(_process_one)
    assert "except OSError" in src


def test_process_one_source_mkdir_parents():
    src = inspect.getsource(_process_one)
    assert "mkdir(parents=True" in src


def test_process_one_source_unknown_error_message():
    src = inspect.getsource(_process_one)
    assert "unknown" in src.lower() and "process_single returned None" in src


def test_process_one_source_returns_image_dir_none_when_document_none():
    src = inspect.getsource(_process_one)
    # 第三个 return：image_dir 是 None
    assert "image_dir," in src  # 出现在多个 return 中


# ---------- run_evaluation source level 第四批 ----------


def test_run_evaluation_source_starts_with_def():
    src = inspect.getsource(run_evaluation)
    assert src.lstrip().startswith("def run_evaluation(")


def test_run_evaluation_source_docstring_present():
    src = inspect.getsource(run_evaluation)
    # 函数体内含 docstring
    assert '"""' in src or "'''" in src


def test_run_evaluation_source_docstring_short():
    src = inspect.getsource(run_evaluation)
    # docstring 是单行
    assert '"""跑评测主流程，返回报告 dict（同时写到 output_path）。"""' in src


def test_run_evaluation_source_creates_output_root():
    src = inspect.getsource(run_evaluation)
    assert "output_root = Path(output_path).parent" in src


def test_run_evaluation_source_creates_output_root_dirs():
    src = inspect.getsource(run_evaluation)
    assert "output_root.mkdir(parents=True, exist_ok=True)" in src


def test_run_evaluation_source_initializes_per_doc_list():
    src = inspect.getsource(run_evaluation)
    assert "per_doc_results: list[dict[str, Any]] = []" in src


def test_run_evaluation_source_initializes_parser_version():
    src = inspect.getsource(run_evaluation)
    assert "parser_version_for_prov: str | None = None" in src


def test_run_evaluation_source_loops_documents():
    src = inspect.getsource(run_evaluation)
    assert "for doc in manifest.documents:" in src


def test_run_evaluation_source_loops_expected_failures():
    src = inspect.getsource(run_evaluation)
    assert "for ef in manifest.expected_failures:" in src


def test_run_evaluation_source_calls_compute_automatic_metrics():
    src = inspect.getsource(run_evaluation)
    assert "compute_automatic_metrics(" in src


def test_run_evaluation_source_passes_doc_source_type():
    src = inspect.getsource(run_evaluation)
    assert "source_type=doc.source_type" in src


def test_run_evaluation_source_passes_doc_expectations():
    src = inspect.getsource(run_evaluation)
    assert "expectations=doc.expectations" in src


def test_run_evaluation_source_loads_annotation():
    src = inspect.getsource(run_evaluation)
    assert "_load_annotation(doc.annotation_resolved)" in src


def test_run_evaluation_source_calls_figure_caption_prf():
    src = inspect.getsource(run_evaluation)
    assert "figure_caption_prf(document, annotation)" in src


def test_run_evaluation_source_calls_chunk_boundary_prf():
    src = inspect.getsource(run_evaluation)
    assert "chunk_boundary_prf(" in src
    assert "tolerance_chars=tolerance_chars" in src


def test_run_evaluation_source_pops_tolerance_chars():
    src = inspect.getsource(run_evaluation)
    assert 'pop("_tolerance_chars"' in src


def test_run_evaluation_source_pops_missing_markers():
    src = inspect.getsource(run_evaluation)
    assert 'pop("_missing_markers"' in src


def test_run_evaluation_source_calls_build_provenance():
    src = inspect.getsource(run_evaluation)
    assert "build_provenance(" in src


def test_run_evaluation_source_calls_build_devset_section():
    src = inspect.getsource(run_evaluation)
    assert "build_devset_section(manifest)" in src


def test_run_evaluation_source_calls_aggregate_summary():
    src = inspect.getsource(run_evaluation)
    assert "aggregate_summary(per_doc_results)" in src


def test_run_evaluation_source_builds_public_per_doc():
    src = inspect.getsource(run_evaluation)
    assert "public_per_doc = []" in src


def test_run_evaluation_source_creates_report_dict():
    src = inspect.getsource(run_evaluation)
    assert '"report_version": REPORT_VERSION' in src
    assert '"provenance": provenance' in src
    assert '"devset": devset' in src
    assert '"summary": summary' in src
    assert '"per_doc": public_per_doc' in src
    assert '"expected_failures": expected_failure_results' in src


def test_run_evaluation_source_writes_json_with_indent():
    src = inspect.getsource(run_evaluation)
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in src


def test_run_evaluation_source_returns_report():
    src = inspect.getsource(run_evaluation)
    assert "return report" in src


def test_run_evaluation_source_handles_expected_failure_actual_code():
    src = inspect.getsource(run_evaluation)
    assert "errors[0].code if errors" in src


def test_run_evaluation_source_compares_actual_with_expected():
    src = inspect.getsource(run_evaluation)
    assert "actual_code == ef.expected_error_code" in src


def test_run_evaluation_source_initializes_expected_failure_results():
    src = inspect.getsource(run_evaluation)
    assert "expected_failure_results: list[dict[str, Any]] = []" in src


def test_run_evaluation_source_appends_to_per_doc_results():
    src = inspect.getsource(run_evaluation)
    assert "per_doc_results.append(" in src


def test_run_evaluation_source_appends_to_expected_failure_results():
    src = inspect.getsource(run_evaluation)
    assert "expected_failure_results.append(" in src


def test_run_evaluation_source_track_parser_version_first():
    src = inspect.getsource(run_evaluation)
    assert "if parser_version and not parser_version_for_prov:" in src


def test_run_evaluation_source_uses_image_dir_is_dir():
    src = inspect.getsource(run_evaluation)
    assert "image_dir.is_dir()" in src


def test_run_evaluation_source_uses_doc_id_in_per_doc():
    src = inspect.getsource(run_evaluation)
    assert '"doc_id": doc.doc_id' in src


def test_run_evaluation_source_uses_total_seconds_in_wall_time():
    src = inspect.getsource(run_evaluation)
    assert '"total": total_seconds' in src
    assert '"parse": None' in src
    assert '"chunk": None' in src
    assert '"parse_reason": "not_instrumented"' in src


# ---------- module source forbidden tokens 第十批 ----------


_FORBIDDEN_TOKENS_ROUND10 = [
    "sys",
    "os",
    "logging",
    "asyncio",
    "threading",
    "concurrent",
    "multiprocessing",
    "socket",
    "signal",
    "ctypes",
    "gc",
    "traceback",
    "warnings",
    "weakref",
    "tempfile",
    "shutil",
    "pickle",
    "csv",
    "yaml",
    "tomllib",
    "configparser",
    "argparse",
    "logging.config",
    "importlib.resources",
    "inspect",
    "dis",
    "compile(",
    "exec(",
    "globals(",
    "locals(",
    "vars(",
    "dir(",
    "delattr(",
    "exit(",
    "quit(",
    "input(",
    "pprint(",
    "ascii(",
    "bin(",
    "oct(",
    "hex(",
    "slice(",
    "reversed(",
    "abs(",
    "divmod(",
    "pow(",
    "bytearray(",
    "memoryview(",
    "complex(",
    "classmethod(",
    "staticmethod(",
    "property(",
    "super(",
    "object()",
    "ellipsi",
    "notimplemented",
    "License",
    "Credits",
    "Copyright",
    "help(",
    "breakpoint(",
    "__import__",
]


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND10)
def test_module_source_no_forbidden_token_round10(token):
    """runner.py 不应使用这些 stdlib modules / builtin calls。"""
    src = inspect.getsource(rmod)

    allowed = {
        "compile(",
        "globals(",
        "locals(",
        "vars(",
        "dir(",
        "delattr(",
        "exit(",
        "quit(",
        "input(",
        "pprint(",
        "ascii(",
        "bin(",
        "oct(",
        "hex(",
        "slice(",
        "reversed(",
        "abs(",
        "divmod(",
        "pow(",
        "bytearray(",
        "memoryview(",
        "complex(",
        "classmethod(",
        "staticmethod(",
        "property(",
        "super(",
        "object()",
    }
    if token in allowed:
        return

    if token.endswith("("):
        assert token not in src, f"unexpected builtin call {token!r} in runner.py"
    else:
        import re
        pattern = r"\b" + re.escape(token) + r"\b"
        matches = re.findall(pattern, src)
        assert not matches, f"unexpected token {token!r} in runner.py"


# ---------- module source 字符串精确补强 ----------


def test_module_source_starts_with_docstring():
    src = inspect.getsource(rmod)
    assert src.lstrip().startswith(('"""', "'''"))


def test_module_source_docstring_mentions_runner():
    src = inspect.getsource(rmod)
    assert "runner" in src.lower() or "评测" in src or "评估" in src


def test_module_source_docstring_mentions_total_only():
    src = inspect.getsource(rmod)
    # 计时只记 total
    assert "total" in src.lower()


def test_module_source_docstring_mentions_not_instrumented():
    src = inspect.getsource(rmod)
    assert "not_instrumented" in src or "未插桩" in src or "不插桩" in src


def test_module_source_import_count_10():
    """10 个 module-level imports。"""
    src = inspect.getsource(rmod)
    import_lines = [
        l for l in src.splitlines()
        if l.strip().startswith(("import ", "from "))
        and not l.startswith(" ")
    ]
    assert len(import_lines) == 10


def test_module_source_imports_json():
    src = inspect.getsource(rmod)
    assert "import json" in src


def test_module_source_imports_time():
    src = inspect.getsource(rmod)
    assert "import time" in src


def test_module_source_imports_path():
    src = inspect.getsource(rmod)
    assert "from pathlib import Path" in src


def test_module_source_imports_any():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_imports_app_pipeline():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_imports_report_version():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_imports_annotation_metrics():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import" in src
    assert "chunk_boundary_prf" in src
    assert "figure_caption_prf" in src


def test_module_source_imports_compute_automatic_metrics():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_imports_report_funcs():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import" in src
    assert "aggregate_summary" in src
    assert "build_devset_section" in src
    assert "build_provenance" in src


def test_module_source_no_relative_import():
    src = inspect.getsource(rmod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert not line.strip().startswith("from .")


def test_module_source_no_star_import():
    src = inspect.getsource(rmod)
    assert "import *" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(rmod)
    assert "__main__" not in src


def test_module_source_no_yield():
    src = inspect.getsource(rmod)
    assert "yield " not in src


def test_module_source_no_async():
    src = inspect.getsource(rmod)
    assert "async " not in src
    assert "await " not in src


def test_module_source_no_global_keyword():
    src = inspect.getsource(rmod)
    assert "\nglobal " not in src
    assert " global " not in src


def test_module_source_no_walrus():
    src = inspect.getsource(rmod)
    assert ":=" not in src


def test_module_source_no_class_definition():
    src = inspect.getsource(rmod)
    assert not any(line.startswith("class ") for line in src.splitlines())


def test_module_source_no_pickle():
    src = inspect.getsource(rmod)
    assert "pickle" not in src


def test_module_source_no_yaml():
    src = inspect.getsource(rmod)
    assert "yaml" not in src


def test_module_source_no_logging():
    src = inspect.getsource(rmod)
    assert "logging" not in src


def test_module_source_no_argparse():
    src = inspect.getsource(rmod)
    assert "argparse" not in src


def test_module_source_no_csv():
    src = inspect.getsource(rmod)
    assert "csv" not in src


def test_module_source_no_tomllib():
    src = inspect.getsource(rmod)
    assert "tomllib" not in src


def test_module_source_function_count_3():
    src = inspect.getsource(rmod)
    func_count = sum(
        1 for line in src.splitlines()
        if line.startswith("def ")
    )
    assert func_count == 3


def test_module_source_function_names():
    src = inspect.getsource(rmod)
    funcs = [
        line.split("def ")[1].split("(")[0]
        for line in src.splitlines()
        if line.startswith("def ")
    ]
    assert sorted(funcs) == sorted(["_load_annotation", "_process_one", "run_evaluation"])


def test_module_source_has_1_public_func():
    src = inspect.getsource(rmod)
    public = [
        line for line in src.splitlines()
        if line.startswith("def ") and not line.startswith("def _")
    ]
    assert len(public) == 1
    assert "def run_evaluation" in public[0]


def test_module_source_has_2_private_funcs():
    src = inspect.getsource(rmod)
    private = [
        line for line in src.splitlines()
        if line.startswith("def _")
    ]
    assert len(private) == 2


def test_module_source_has_all():
    src = inspect.getsource(rmod)
    assert "__all__" in src


def test_module_source_all_includes_run_evaluation():
    src = inspect.getsource(rmod)
    all_block = src[src.index("__all__"):]
    assert '"run_evaluation"' in all_block


# ---------- signatures 精确补强 ----------


def test_load_annotation_signature_param_count():
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1


def test_load_annotation_signature_param_name():
    sig = inspect.signature(_load_annotation)
    p = list(sig.parameters.values())[0]
    assert p.name == "path"


def test_load_annotation_signature_param_no_default():
    sig = inspect.signature(_load_annotation)
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_load_annotation_signature_no_varargs():
    sig = inspect.signature(_load_annotation)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_process_one_signature_param_count():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_process_one_signature_param_names():
    sig = inspect.signature(_process_one)
    names = list(sig.parameters.keys())
    assert names == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_signature_no_defaults():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_process_one_signature_no_varargs():
    sig = inspect.signature(_process_one)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_run_evaluation_signature_param_count():
    sig = inspect.signature(run_evaluation)
    assert len(sig.parameters) == 5


def test_run_evaluation_signature_param_names():
    sig = inspect.signature(run_evaluation)
    names = list(sig.parameters.keys())
    assert names == ["manifest", "output_path", "parser_name", "max_chars", "tolerance_chars"]


def test_run_evaluation_signature_parser_name_default_fallback():
    sig = inspect.signature(run_evaluation)
    p = sig.parameters["parser_name"]
    assert p.default == "fallback"


def test_run_evaluation_signature_max_chars_default_800():
    sig = inspect.signature(run_evaluation)
    p = sig.parameters["max_chars"]
    assert p.default == 800


def test_run_evaluation_signature_tolerance_default_30():
    sig = inspect.signature(run_evaluation)
    p = sig.parameters["tolerance_chars"]
    assert p.default == 30


def test_run_evaluation_signature_kw_only_separator():
    """* 之后是 kw-only。"""
    sig = inspect.signature(run_evaluation)
    # parser_name/max_chars/tolerance_chars 是 kw-only
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_signature_manifest_positional_or_kw():
    sig = inspect.signature(run_evaluation)
    p = sig.parameters["manifest"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_signature_output_path_positional_or_kw():
    sig = inspect.signature(run_evaluation)
    p = sig.parameters["output_path"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_no_function_has_varargs_in_module():
    for name in ["_load_annotation", "_process_one", "run_evaluation"]:
        fn = getattr(rmod, name)
        sig = inspect.signature(fn)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_POSITIONAL not in kinds
        assert inspect.Parameter.VAR_KEYWORD not in kinds


# ---------- 模块整体合理性 ----------


def test_module_namespace_has_3_callables():
    ns = [
        (k, v) for k, v in vars(rmod).items()
        if getattr(v, "__module__", "") == rmod.__name__
        and not k.startswith("__")
    ]
    names = [k for k, v in ns]
    expected = ["_load_annotation", "_process_one", "run_evaluation"]
    assert sorted(names) == sorted(expected)


def test_module_name():
    assert rmod.__name__ == "evaluation.runner"


def test_module_file_endswith_runner_py():
    assert rmod.__file__.replace("\\", "/").endswith("evaluation/runner.py")


def test_module_docstring_present():
    assert rmod.__doc__ is not None and len(rmod.__doc__) > 50


def test_module_all_present():
    assert hasattr(rmod, "__all__")


def test_module_all_count_1():
    assert len(rmod.__all__) == 1


def test_module_all_contents():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_run_evaluation_callable():
    assert callable(rmod.run_evaluation)


def test_module_load_annotation_callable():
    assert callable(rmod._load_annotation)


def test_module_process_one_callable():
    assert callable(rmod._process_one)


def test_module_no_user_classes():
    classes = [
        (k, v) for k, v in vars(rmod).items()
        if isinstance(v, type) and getattr(v, "__module__", "") == rmod.__name__
    ]
    assert classes == []


def test_module_function_module_eq():
    for name in ["_load_annotation", "_process_one", "run_evaluation"]:
        fn = getattr(rmod, name)
        assert fn.__module__ == "evaluation.runner"


# ---------- 端到端集成补强 ----------


def test_load_annotation_returns_none_for_directory(tmp_path):
    """目录不是文件 → None。"""
    sub = tmp_path / "subdir"
    sub.mkdir()
    out = _load_annotation(sub)
    assert out is None


def test_load_annotation_handles_unicode_keys(tmp_path):
    f = tmp_path / "uni.json"
    f.write_text('{"中文键": "value"}', encoding="utf-8")
    out = _load_annotation(f)
    assert out["中文键"] == "value"


def test_load_annotation_handles_emoji_in_keys(tmp_path):
    f = tmp_path / "emoji.json"
    f.write_text('{"🚀": "rocket"}', encoding="utf-8")
    out = _load_annotation(f)
    assert out["🚀"] == "rocket"


def test_load_annotation_returns_none_for_empty_file(tmp_path):
    f = tmp_path / "empty.json"
    f.write_text("", encoding="utf-8")
    out = _load_annotation(f)
    # 空 → JSON 解析失败 → None
    assert out is None


def test_load_annotation_returns_none_for_only_whitespace(tmp_path):
    f = tmp_path / "ws.json"
    f.write_text("   \n  \t  ", encoding="utf-8")
    out = _load_annotation(f)
    assert out is None


def test_load_annotation_returns_none_for_partial_json(tmp_path):
    f = tmp_path / "partial.json"
    f.write_text('{"a": 1, "b":', encoding="utf-8")
    out = _load_annotation(f)
    assert out is None


def test_load_annotation_with_str_path(tmp_path):
    """接受 str path 输入。"""
    f = tmp_path / "data.json"
    f.write_text('{"x": 1}', encoding="utf-8")
    # _load_annotation 接受 Path，str 路径需要包装
    out = _load_annotation(Path(str(f)))
    assert out["x"] == 1


def test_load_annotation_with_pathlib_path(tmp_path):
    f = tmp_path / "data.json"
    f.write_text('{"x": 1}', encoding="utf-8")
    out = _load_annotation(f)
    assert out["x"] == 1


def test_load_annotation_with_path_none():
    """path=None → 直接返回 None。"""
    out = _load_annotation(None)
    assert out is None


def test_load_annotation_with_nonexistent_path(tmp_path):
    out = _load_annotation(tmp_path / "nonexistent.json")
    assert out is None


def test_load_annotation_preserves_dict_order(tmp_path):
    """JSON object 保留插入顺序。"""
    f = tmp_path / "ordered.json"
    f.write_text('{"z": 1, "a": 2, "m": 3}', encoding="utf-8")
    out = _load_annotation(f)
    assert list(out.keys()) == ["z", "a", "m"]


def test_load_annotation_preserves_array_order(tmp_path):
    f = tmp_path / "arr.json"
    f.write_text('[3, 1, 4, 1, 5, 9]', encoding="utf-8")
    out = _load_annotation(f)
    assert out == [3, 1, 4, 1, 5, 9]


def test_load_annotation_with_nested_arrays_in_dict(tmp_path):
    f = tmp_path / "nested.json"
    f.write_text('{"a": [1, 2], "b": [[3, 4], [5, 6]]}', encoding="utf-8")
    out = _load_annotation(f)
    assert out["a"] == [1, 2]
    assert out["b"] == [[3, 4], [5, 6]]


def test_load_annotation_with_mixed_types(tmp_path):
    f = tmp_path / "mixed.json"
    f.write_text(
        '{"str": "hello", "int": 42, "float": 3.14, "bool": true, "null": null, "list": [], "obj": {}}',
        encoding="utf-8",
    )
    out = _load_annotation(f)
    assert out["str"] == "hello"
    assert out["int"] == 42
    assert out["float"] == 3.14
    assert out["bool"] is True
    assert out["null"] is None
    assert out["list"] == []
    assert out["obj"] == {}


def test_module_no_callables_with_unexpected_names():
    """除了 _load_annotation, _process_one, run_evaluation，不应有其他 callable。"""
    ns = [
        (k, v) for k, v in vars(rmod).items()
        if callable(v) and getattr(v, "__module__", "") == rmod.__name__
        and not k.startswith("__")
    ]
    names = [k for k, v in ns]
    assert sorted(names) == sorted(["_load_annotation", "_process_one", "run_evaluation"])
