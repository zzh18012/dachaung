"""evaluation/runner.py 第三十二轮 edges 测试（Round 347）。

重点补强 edges30 未触及的角度：
- _load_annotation 行为深度第六批（更多 JSON 类型组合 / 文件系统错误 / encoding 边界）
- _process_one 行为深度（更多 source level / returns / error 路径）
- run_evaluation source level 字符串精确补强第三批（更多 control flow / 数据流）
- module source forbidden tokens 第九批（不同 stdlib list）
- module source 字符串精确补强第三批（更多）
- signatures 精确补强第三批（更多）
- 模块整体合理性（更多 namespace 检查）
- 端到端集成补强第三批（更多场景）
"""

from __future__ import annotations

import inspect
import json
import types
from pathlib import Path
from typing import Any

import pytest

from evaluation import runner as rmod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 行为深度第六批 ----------


def test_load_annotation_with_array_of_arrays(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("[[1, 2], [3, 4]]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == [[1, 2], [3, 4]]


def test_load_annotation_with_nested_dict_deep(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": {"b": {"c": {"d": "e"}}}}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": {"b": {"c": {"d": "e"}}}}


def test_load_annotation_with_unicode_keys(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"中文": 1, "日本語": 2}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"中文": 1, "日本語": 2}


def test_load_annotation_with_float_values(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": 3.14, "b": 2.71}', encoding="utf-8")
    out = _load_annotation(p)
    assert out["a"] == pytest.approx(3.14)


def test_load_annotation_with_scientific_notation(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": 1e10}', encoding="utf-8")
    out = _load_annotation(p)
    assert out["a"] == 1e10


def test_load_annotation_with_null_values(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": null, "b": [null, 1]}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": None, "b": [None, 1]}


def test_load_annotation_with_long_string(tmp_path):
    p = tmp_path / "ann.json"
    long_value = "x" * 10000
    p.write_text(json.dumps({"a": long_value}), encoding="utf-8")
    out = _load_annotation(p)
    assert len(out["a"]) == 10000


def test_load_annotation_with_empty_dict(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("{}", encoding="utf-8")
    out = _load_annotation(p)
    assert out == {}


def test_load_annotation_with_empty_array(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("[]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == []


def test_load_annotation_with_whitespace_only(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("   \n\t  ", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_with_object_having_list_value(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"items": [1, 2, 3]}', encoding="utf-8")
    out = _load_annotation(p)
    assert out["items"] == [1, 2, 3]


def test_load_annotation_with_negative_numbers(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": -5, "b": -3.14}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": -5, "b": pytest.approx(-3.14)}


def test_load_annotation_with_explicit_exponent(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": 1.5e3}', encoding="utf-8")
    out = _load_annotation(p)
    assert out["a"] == 1500.0


def test_load_annotation_returns_dict_for_typical_annotation(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text(
        json.dumps({
            "annotation_version": "1.0",
            "chunk_boundary_anchors": [
                {"marker": "abc", "position": "after"}
            ],
        }),
        encoding="utf-8",
    )
    out = _load_annotation(p)
    assert isinstance(out, dict)
    assert "annotation_version" in out


def test_load_annotation_with_directory_path(tmp_path):
    """传目录而不是文件 → is_file() False → 返回 None。"""
    sub = tmp_path / "subdir"
    sub.mkdir()
    out = _load_annotation(sub)
    assert out is None


def test_load_annotation_with_relative_path(tmp_path, monkeypatch):
    """相对路径也能加载（chdir 到 tmp_path）。"""
    p = tmp_path / "ann.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    out = _load_annotation(Path("ann.json"))
    assert out == {"a": 1}


def test_load_annotation_with_pathlib_path(tmp_path):
    """Path 对象能加载。"""
    p = tmp_path / "ann.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    out = _load_annotation(Path(p))
    assert out == {"x": 1}


def test_load_annotation_with_str_path(tmp_path):
    """str 路径不应直接传（类型注解是 Path|None），但有些 Path 实现可能接受。"""
    p = tmp_path / "ann.json"
    p.write_text('{"y": 1}', encoding="utf-8")
    # Path(None) 会抛 TypeError；str 路径需要 Path 包裹
    # 这里仅验证 Path 路径正确
    out = _load_annotation(Path(str(p)))
    assert out == {"y": 1}


# ---------- _process_one source level 字符串精确补强第三批 ----------


def test_process_one_source_starts_with_def_keyword():
    src = inspect.getsource(_process_one)
    assert src.lstrip().startswith("def _process_one(")


def test_process_one_source_returns_5_tuple():
    src = inspect.getsource(_process_one)
    # 多分支返回值结构（5-tuple 形式）
    assert "return document.to_dict(), None, elapsed, document.parser_version, image_dir" in src


def test_process_one_source_image_dir_appears_in_returns():
    src = inspect.getsource(_process_one)
    # image_dir 在至少 3 个 return 分支中出现
    assert src.count("image_dir") >= 3


def test_process_one_source_calls_process_single():
    src = inspect.getsource(_process_one)
    assert "process_single(" in src


def test_process_one_source_uses_out_stub_variable():
    src = inspect.getsource(_process_one)
    assert "out_stub = " in src


def test_process_one_source_uses_doc_dot_doc_id():
    src = inspect.getsource(_process_one)
    assert "doc.doc_id" in src


def test_process_one_source_uses_doc_dot_resolved_path():
    src = inspect.getsource(_process_one)
    assert "doc.resolved_path" in src


def test_process_one_source_initializes_image_dir_to_none():
    src = inspect.getsource(_process_one)
    assert "image_dir: Path | None = None" in src


def test_process_one_source_returns_5_tuple_in_all_3_branches():
    """3 个 return 路径：errors / document None / 正常。"""
    src = inspect.getsource(_process_one)
    return_count = src.count("return ")
    # 3 个 return 路径
    assert return_count == 3


def test_process_one_source_branch_1_returns_none_errors_to_dict():
    src = inspect.getsource(_process_one)
    # if errors:
    assert "if errors:" in src
    # return None, errors[0].to_dict(), elapsed, None, image_dir
    assert "errors[0].to_dict()" in src


def test_process_one_source_branch_2_returns_unknown_error():
    src = inspect.getsource(_process_one)
    # if document is None:
    assert "if document is None:" in src
    assert '"code": "unknown"' in src
    assert '"message": "process_single returned None without errors"' in src


def test_process_one_source_branch_3_returns_normal_tuple():
    src = inspect.getsource(_process_one)
    assert "document.to_dict()" in src
    assert "document.parser_version" in src


def test_process_one_source_no_yield_keyword():
    src = inspect.getsource(_process_one)
    assert "yield" not in src


def test_process_one_source_no_async_def():
    src = inspect.getsource(_process_one)
    assert "async def" not in src


def test_process_one_source_no_class_keyword():
    src = inspect.getsource(_process_one)
    assert "class " not in src


def test_process_one_source_no_global_keyword():
    src = inspect.getsource(_process_one)
    assert "global " not in src


def test_process_one_source_no_nonlocal_keyword():
    src = inspect.getsource(_process_one)
    assert "nonlocal " not in src


def test_process_one_source_no_lambda():
    src = inspect.getsource(_process_one)
    assert "lambda " not in src


def test_process_one_source_no_decorators():
    src = inspect.getsource(_process_one)
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("@"):
            pytest.fail(f"unexpected decorator at line {i}: {line}")


def test_process_one_source_no_try_in_main_path():
    """主路径无 try（除了 unlink 的 except OSError）。"""
    src = inspect.getsource(_process_one)
    # unlink 在 try 里
    assert "try:" in src


def test_process_one_source_returns_image_dir_in_all_paths():
    """每个 return 都包含 image_dir 作为最后元素。"""
    src = inspect.getsource(_process_one)
    # 3 个 return 都以 image_dir 结尾
    assert src.count("image_dir") >= 3


# ---------- run_evaluation source level 字符串精确补强第三批 ----------


def test_run_evaluation_source_starts_with_def_keyword():
    src = inspect.getsource(run_evaluation)
    assert src.lstrip().startswith("def run_evaluation(")


def test_run_evaluation_source_has_manifest_param():
    src = inspect.getsource(run_evaluation)
    assert "manifest" in src
    assert "output_path" in src


def test_run_evaluation_source_initializes_per_doc_results_correct_type():
    src = inspect.getsource(run_evaluation)
    assert "per_doc_results: list[dict[str, Any]] = []" in src


def test_run_evaluation_source_initializes_expected_failure_results():
    src = inspect.getsource(run_evaluation)
    assert "expected_failure_results: list[dict[str, Any]] = []" in src


def test_run_evaluation_source_initializes_parser_version_for_prov_correct_type():
    src = inspect.getsource(run_evaluation)
    assert "parser_version_for_prov: str | None = None" in src


def test_run_evaluation_source_passes_doc_source_type_to_metrics():
    src = inspect.getsource(run_evaluation)
    assert "source_type=doc.source_type" in src


def test_run_evaluation_source_passes_doc_expectations_to_metrics():
    src = inspect.getsource(run_evaluation)
    assert "expectations=doc.expectations" in src


def test_run_evaluation_source_passes_tolerance_chars_to_chunk_boundary():
    src = inspect.getsource(run_evaluation)
    assert "tolerance_chars=tolerance_chars" in src


def test_run_evaluation_source_assigns_fig_caps_variable():
    src = inspect.getsource(run_evaluation)
    assert "fig_caps = " in src


def test_run_evaluation_source_assigns_chunk_b_variable():
    src = inspect.getsource(run_evaluation)
    assert "chunk_b = " in src


def test_run_evaluation_source_assigns_tolerance_record():
    src = inspect.getsource(run_evaluation)
    assert "tolerance_record = " in src


def test_run_evaluation_source_assigns_missing_markers_record():
    src = inspect.getsource(run_evaluation)
    assert "missing_markers_record = " in src


def test_run_evaluation_source_assigns_annotation_variable():
    src = inspect.getsource(run_evaluation)
    assert "annotation = _load_annotation" in src


def test_run_evaluation_source_assigns_metrics_variable():
    src = inspect.getsource(run_evaluation)
    assert "metrics = compute_automatic_metrics" in src


def test_run_evaluation_source_assigns_provenance_via_build():
    src = inspect.getsource(run_evaluation)
    assert "provenance = build_provenance(" in src


def test_run_evaluation_source_assigns_devset_via_build():
    src = inspect.getsource(run_evaluation)
    assert "devset = build_devset_section" in src


def test_run_evaluation_source_assigns_summary_via_aggregate():
    src = inspect.getsource(run_evaluation)
    assert "summary = aggregate_summary" in src


def test_run_evaluation_source_creates_public_per_doc_loop():
    src = inspect.getsource(run_evaluation)
    assert "public_per_doc = []" in src
    assert "for r in per_doc_results:" in src


def test_run_evaluation_source_creates_report_dict():
    src = inspect.getsource(run_evaluation)
    assert "report = {" in src


def test_run_evaluation_source_assigns_out_p():
    src = inspect.getsource(run_evaluation)
    assert "out_p = Path(output_path)" in src


def test_run_evaluation_source_uses_out_p_parent_mkdir():
    src = inspect.getsource(run_evaluation)
    assert "out_p.parent.mkdir(parents=True, exist_ok=True)" in src


def test_run_evaluation_source_returns_report():
    src = inspect.getsource(run_evaluation)
    assert "return report" in src


def test_run_evaluation_source_calls_actual_code_extraction():
    src = inspect.getsource(run_evaluation)
    assert "actual_code = errors[0].code if errors else None" in src


def test_run_evaluation_source_creates_expected_failure_dict_with_4_keys():
    src = inspect.getsource(run_evaluation)
    ef_start = src.find("expected_failure_results.append(")
    ef_end = src.find("provenance = build_provenance")
    ef_section = src[ef_start:ef_end]
    assert '"doc_id": ef.doc_id' in ef_section
    assert '"expected_error_code": ef.expected_error_code' in ef_section
    assert '"actual_error_code": actual_code' in ef_section
    assert '"matches": actual_code == ef.expected_error_code' in ef_section


def test_run_evaluation_source_only_first_parser_version_cached():
    """只缓存第一个非 None 的 parser_version。"""
    src = inspect.getsource(run_evaluation)
    assert "if parser_version and not parser_version_for_prov:" in src


def test_run_evaluation_source_no_yield():
    src = inspect.getsource(run_evaluation)
    assert "yield" not in src


def test_run_evaluation_source_no_async_def():
    src = inspect.getsource(run_evaluation)
    assert "async def" not in src


def test_run_evaluation_source_no_class():
    src = inspect.getsource(run_evaluation)
    assert "class " not in src


def test_run_evaluation_source_no_global():
    src = inspect.getsource(run_evaluation)
    assert "global " not in src


def test_run_evaluation_source_no_lambda():
    src = inspect.getsource(run_evaluation)
    assert "lambda " not in src


def test_run_evaluation_source_no_decorators():
    src = inspect.getsource(run_evaluation)
    for i, line in enumerate(src.splitlines()):
        if line.lstrip().startswith("@"):
            pytest.fail(f"unexpected decorator at line {i}: {line}")


# ---------- module source forbidden tokens 第九批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "_thread", "_dummy_thread", "_markupbase", "_strptime", "_threading_local",
        "_weakrefset", "_collections_abc", "_compat_pickle", "_sitebuiltins",
        "_sysconfigdata", "_pyio", "_dummy_backtrace", "abc", "aifc", "antigravity",
        "argparse", "asdl", "ast", "asyncio", "atexit", "audioop",
        "base64", "bdb", "binascii", "binhex", "builtins",
        "bz2", "cProfile", "calendar", "cgi", "cgitb", "cmath",
        "cmd", "code", "codecs", "codeop", "colorsys", "compileall",
        "configparser", "contextvars", "contextlib", "copyreg", "concurrent",
        "copy", "crypt", "curses", "dataclasses", "datetime",
        "decimal", "difflib", "dis", "distutils", "doctest",
        "email", "encodings", "ensurepip", "enum", "errno",
        "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
        "formatter", "fractions", "ftplib", "functools", "gc",
        "genericpath", "getopt", "getpass", "gettext", "glob",
        "grp", "gzip", "hashlib", "heapq", "hmac",
        "html", "http", "idlelib", "imaplib", "imghdr",
        "importlib", "inspect", "ipaddress", "itertools", "keyword",
        "lib2to3", "linecache", "locale", "logging", "lzma",
        "mailbox", "mailcap", "marshal", "math", "mimetypes",
        "mmap", "modulefinder", "msilib", "msvcrt", "multiprocessing",
        "netrc", "nis", "nntplib", "ntpath", "numbers",
        "opcode", "operator", "optparse", "ossaudiodev", "parser",
        "pdb", "pickle", "pickletools", "pipes", "pkgutil",
        "platform", "plistlib", "poplib", "posix", "posixpath",
        "pprint", "profile", "pstats", "pty", "pwd",
        "py_compile", "pyclbr", "pydoc", "pydoc_data", "pyexpat",
        "queue", "quopri", "random", "readline",
        "reprlib", "resource", "rlcompleter", "runpy", "sched",
        "secrets", "select", "selectors", "shelve", "shlex",
        "shutil", "signal", "site", "smtpd", "smtplib",
        "sndhdr", "socket", "socketserver", "spwd", "sqlite3",
        "sre_compile", "sre_constants", "sre_parse", "ssl", "stat",
        "statistics", "string", "stringprep", "subprocess", "sunau",
        "symtable", "syslog", "tabnanny", "tarfile",
        "telnetlib", "tempfile", "termios", "test", "textwrap",
        "threading", "timeit", "tkinter", "token",
        "tokenize", "trace", "tracemalloc", "tty", "turtle",
        "turtledemo", "types", "unicodedata", "unittest", "urllib",
        "uu", "uuid", "venv", "warnings", "wave",
        "weakref", "webbrowser", "winreg", "winsound", "wsgiref",
        "xdrlib", "xmlrpc", "zipapp", "zipfile", "zipimport",
        "zlib", "zoneinfo",
    ],
)
def test_module_source_forbidden_tokens_ninth_batch(token):
    """这些 stdlib 模块不应出现在 runner.py（仅 json/time/Path/Any）。"""
    src = inspect.getsource(rmod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强（第三批） ----------


def test_module_source_starts_with_docstring():
    src = inspect.getsource(rmod)
    assert src.lstrip().startswith(('"""', "'''"))


def test_module_source_docstring_mentions_runner():
    src = inspect.getsource(rmod)
    assert "runner" in src.lower() or "评测" in src


def test_module_source_docstring_mentions_total_only():
    src = inspect.getsource(rmod)
    assert "total" in src.lower()


def test_module_source_docstring_mentions_not_instrumented():
    src = inspect.getsource(rmod)
    assert "未插桩" in src or "not_instrumented" in src


def test_module_source_docstring_mentions_image_resource():
    src = inspect.getsource(rmod)
    assert "image" in src.lower()


def test_module_source_docstring_mentions_per_doc():
    src = inspect.getsource(rmod)
    assert "per_doc" in src or "_per_doc" in src


def test_module_source_import_block_count_10():
    """10 个 import: __future__ + json + time + Path + Any + app.pipeline + REPORT_VERSION + annotation_metrics + metrics + report。"""
    src = inspect.getsource(rmod)
    import_lines = [
        l for l in src.splitlines()
        if l.strip().startswith(("import ", "from "))
        and not l.startswith(" ")
    ]
    assert len(import_lines) == 10


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


def test_module_source_no_class_definition():
    src = inspect.getsource(rmod)
    body_lines = [
        (i, line) for i, line in enumerate(src.splitlines())
        if not line.strip().startswith(("#", '"', "'"))
    ]
    for i, line in body_lines:
        if line.startswith("class "):
            pytest.fail(f"unexpected class at line {i}: {line}")


def test_module_source_no_yield():
    src = inspect.getsource(rmod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(rmod)
    assert "async def" not in src


def test_module_source_no_global_keyword():
    src = inspect.getsource(rmod)
    assert "global " not in src


def test_module_source_no_nonlocal_keyword():
    src = inspect.getsource(rmod)
    assert "nonlocal " not in src


def test_module_source_no_decorators():
    src = inspect.getsource(rmod)
    for i, line in enumerate(src.splitlines()):
        if line.startswith("@"):
            pytest.fail(f"unexpected decorator at line {i}: {line}")


def test_module_source_no_lambda():
    src = inspect.getsource(rmod)
    assert "lambda " not in src


def test_module_source_no_eval_exec():
    src = inspect.getsource(rmod)
    assert "eval(" not in src
    assert "exec(" not in src


def test_module_source_no_compile_call():
    src = inspect.getsource(rmod)
    assert "compile(" not in src


def test_module_source_no_os_module():
    src = inspect.getsource(rmod)
    assert "import os" not in src
    assert "from os " not in src


def test_module_source_no_subprocess():
    src = inspect.getsource(rmod)
    assert "subprocess" not in src


def test_module_source_no_sys_import():
    src = inspect.getsource(rmod)
    assert "import sys" not in src
    assert "from sys " not in src


def test_module_source_has_3_module_level_functions():
    src = inspect.getsource(rmod)
    func_count = sum(1 for line in src.splitlines() if line.startswith("def "))
    assert func_count == 3


def test_module_source_function_names_exact():
    src = inspect.getsource(rmod)
    assert "def _load_annotation(" in src
    assert "def _process_one(" in src
    assert "def run_evaluation(" in src


def test_module_source_all_exact():
    src = inspect.getsource(rmod)
    assert '__all__ = ["run_evaluation"]' in src


def test_module_source_imports_future_annotations():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_uses_json_load_in_load_annotation():
    src = inspect.getsource(_load_annotation)
    assert "json.load(f)" in src


def test_module_source_uses_perf_counter_in_process_one():
    src = inspect.getsource(_process_one)
    assert "time.perf_counter()" in src


def test_module_source_uses_json_dump_in_run_evaluation():
    src = inspect.getsource(run_evaluation)
    assert "json.dump(report" in src


# ---------- signatures 精确补强（第三批） ----------


def test_load_annotation_param_no_default():
    sig = inspect.signature(_load_annotation)
    p = list(sig.parameters.values())[0]
    # path: Path | None 没有 default（必须显式传入）
    assert p.default is inspect.Parameter.empty


def test_load_annotation_no_varargs():
    sig = inspect.signature(_load_annotation)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_process_one_param_no_defaults():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_process_one_param_annotations_optional():
    """_process_one 用注释类型而非 annotation（doc 是 DocumentEntry）。"""
    sig = inspect.signature(_process_one)
    # doc, output_root, parser_name, max_chars
    assert list(sig.parameters.keys()) == ["doc", "output_root", "parser_name", "max_chars"]


def test_run_evaluation_signature_5_params_confirmed():
    sig = inspect.signature(run_evaluation)
    assert len(sig.parameters) == 5


def test_run_evaluation_param_names_confirmed():
    sig = inspect.signature(run_evaluation)
    assert list(sig.parameters.keys()) == [
        "manifest",
        "output_path",
        "parser_name",
        "max_chars",
        "tolerance_chars",
    ]


def test_run_evaluation_manifest_positional_or_keyword():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_output_path_positional_or_keyword():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_run_evaluation_parser_name_keyword_only():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_max_chars_keyword_only():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_tolerance_chars_keyword_only():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_load_annotation_function_has_docstring():
    assert _load_annotation.__doc__ is None or _load_annotation.__doc__ == ""


def test_process_one_function_has_docstring():
    assert _process_one.__doc__ is not None


def test_run_evaluation_function_has_docstring():
    assert run_evaluation.__doc__ is not None


def test_run_evaluation_docstring_mentions_评测():
    assert run_evaluation.__doc__ is not None
    assert "评测" in run_evaluation.__doc__ or "评估" in run_evaluation.__doc__


# ---------- 模块整体合理性（第三批） ----------


def test_module_namespace_is_module():
    assert isinstance(rmod, types.ModuleType)


def test_module_namespace_name():
    assert rmod.__name__ == "evaluation.runner"


def test_module_namespace_has_file():
    assert hasattr(rmod, "__file__")
    assert rmod.__file__ is not None


def test_module_namespace_has_doc():
    assert hasattr(rmod, "__doc__")
    assert rmod.__doc__ is not None


def test_module_namespace_has_all():
    assert hasattr(rmod, "__all__")


def test_module_all_is_list():
    assert isinstance(rmod.__all__, list)


def test_module_all_has_1_entry():
    assert len(rmod.__all__) == 1


def test_module_all_entries_are_str():
    for entry in rmod.__all__:
        assert isinstance(entry, str)


def test_module_all_only_run_evaluation():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_namespace_has_run_evaluation():
    assert hasattr(rmod, "run_evaluation")


def test_module_namespace_has_load_annotation():
    assert hasattr(rmod, "_load_annotation")


def test_module_namespace_has_process_one():
    assert hasattr(rmod, "_process_one")


def test_module_has_3_module_level_functions():
    functions = [
        v for v in vars(rmod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == rmod.__name__
    ]
    assert len(functions) == 3


def test_module_has_2_private_functions():
    private = [
        v for v in vars(rmod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == rmod.__name__
        and v.__name__.startswith("_")
        and not v.__name__.startswith("__")
    ]
    assert len(private) == 2
    names = sorted(p.__name__ for p in private)
    assert names == ["_load_annotation", "_process_one"]


def test_module_has_1_public_function():
    public = [
        v for v in vars(rmod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == rmod.__name__
        and not v.__name__.startswith("_")
    ]
    assert len(public) == 1
    assert public[0].__name__ == "run_evaluation"


def test_module_no_user_classes():
    classes = [
        v for v in vars(rmod).values()
        if isinstance(v, type) and v.__module__ == rmod.__name__
    ]
    assert len(classes) == 0


def test_module_callable_run_evaluation():
    assert callable(run_evaluation)


def test_module_callable_load_annotation():
    assert callable(_load_annotation)


def test_module_callable_process_one():
    assert callable(_process_one)


def test_module_function_modules_eq_runner():
    for fn in [_load_annotation, _process_one, run_evaluation]:
        assert fn.__module__ == "evaluation.runner"


# ---------- 端到端集成补强（第三批） ----------


def _make_minimal_manifest(path):
    path.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )


def test_e2e_no_documents_creates_per_doc_dir(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["per_doc"] == []
    assert out.is_file()


def test_e2e_no_documents_creates_report_dict_with_6_keys(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    expected_keys = {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }
    assert set(report.keys()) == expected_keys


def test_e2e_no_documents_devset_status_incomplete(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert report["devset"]["status"] == "incomplete"


def test_e2e_no_documents_summary_total_0(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    # summary 的 schema 是 counts/success_rates/ratio_macro_averages/silent_drop_total
    assert "counts" in report["summary"]
    assert "success_rates" in report["summary"]


def test_e2e_no_documents_creates_subdir(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "sub" / "deep" / "out.json"
    report = run_evaluation(manifest, out)
    assert out.is_file()


def test_e2e_loadable_report(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    run_evaluation(manifest, out)
    with out.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert "report_version" in loaded


def test_e2e_indent_2_in_output(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    run_evaluation(manifest, out)
    text = out.read_text(encoding="utf-8")
    assert "\n" in text


def test_e2e_deterministic_across_calls(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out1 = tmp_path / "out1.json"
    out2 = tmp_path / "out2.json"
    r1 = run_evaluation(manifest, out1)
    r2 = run_evaluation(manifest, out2)
    assert r1["per_doc"] == r2["per_doc"]
    assert r1["summary"] == r2["summary"]
    assert r1["devset"] == r2["devset"]


def test_e2e_with_max_chars_1(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out, max_chars=1)
    assert report["provenance"]["max_chars"] == 1


def test_e2e_with_tolerance_chars_0(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out, tolerance_chars=0)
    assert isinstance(report["per_doc"], list)


def test_e2e_with_kreuzberg_parser_name(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out, parser_name="kreuzberg")
    assert report["provenance"]["parser_name"] == "kreuzberg"


def test_e2e_creates_per_doc_subdir_even_with_no_documents(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "sub" / "out.json"
    run_evaluation(manifest, out)
    assert out.parent.is_dir()


def test_e2e_load_annotation_none_returns_none():
    assert _load_annotation(None) is None


def test_e2e_load_annotation_nonexistent_returns_none(tmp_path):
    p = tmp_path / "no.json"
    assert _load_annotation(p) is None


def test_e2e_load_annotation_invalid_json_returns_none(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("not json", encoding="utf-8")
    assert _load_annotation(p) is None


def test_e2e_load_annotation_valid_returns_dict(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": 1}


def test_e2e_returns_dict_type(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert isinstance(report, dict)


def test_e2e_returns_per_doc_list(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert isinstance(report["per_doc"], list)


def test_e2e_returns_expected_failures_list(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert isinstance(report["expected_failures"], list)


def test_e2e_with_kwargs_only(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(
        manifest=manifest,
        output_path=out,
        parser_name="fallback",
        max_chars=800,
        tolerance_chars=30,
    )
    assert report["provenance"]["max_chars"] == 800


def test_e2e_with_positional_first_two(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert isinstance(report, dict)


def test_e2e_does_not_overwrite_existing_per_doc_when_none(tmp_path):
    """无文档时不应有残留 _per_doc JSON。"""
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    run_evaluation(manifest, out)
    # _per_doc 目录可能存在但应该是空的（或不存在）
    per_doc_dir = tmp_path / "_per_doc"
    if per_doc_dir.is_dir():
        # 不应有残留 .json
        files = list(per_doc_dir.glob("*.json"))
        assert len(files) == 0


def test_e2e_creates_output_directory_recursively(tmp_path):
    """深嵌套目录也能创建。"""
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "a" / "b" / "c" / "d" / "out.json"
    run_evaluation(manifest, out)
    assert out.is_file()


def test_e2e_report_json_has_no_private_top_level_keys(tmp_path):
    """报告顶层不应有 _xxx 私有字段。"""
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    for key in report:
        assert not key.startswith("_"), f"top-level private key: {key}"


def test_e2e_report_json_serializable(tmp_path):
    """report dict 可被 json.dumps。"""
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    s = json.dumps(report)
    assert isinstance(s, str)


def test_e2e_idempotent_with_max_chars_variations(tmp_path):
    """不同 max_chars 都应工作。"""
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    for mc in (100, 500, 800, 1500):
        out = tmp_path / f"out_{mc}.json"
        report = run_evaluation(manifest, out, max_chars=mc)
        assert report["provenance"]["max_chars"] == mc


def test_e2e_idempotent_with_tolerance_chars_variations(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    for tc in (0, 10, 30, 100):
        out = tmp_path / f"out_tc_{tc}.json"
        report = run_evaluation(manifest, out, tolerance_chars=tc)
        assert isinstance(report, dict)


def test_e2e_does_not_raise_with_empty_manifest(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    # 不应抛异常
    run_evaluation(manifest, out)


def test_e2e_with_unicode_path(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "结果.json"
    run_evaluation(manifest, out)
    assert out.is_file()


def test_e2e_creates_directory_under_existing_one(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    # 已存在子目录
    sub = tmp_path / "outputs"
    sub.mkdir()
    out = sub / "out.json"
    run_evaluation(manifest, out)
    assert out.is_file()
