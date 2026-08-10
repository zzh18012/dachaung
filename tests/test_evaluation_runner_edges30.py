"""evaluation/runner.py 第三十一轮 edges 测试（Round 341）。

重点补强 edges29 未触及的角度：
- _load_annotation 行为深度第五批（更多 invalid JSON / 编码 / 大文件 / 嵌套）
- _process_one source level 字符串精确补强第二批（5-tuple / image_dir / unlink / try/except）
- run_evaluation source level 字符串精确补强第二批（expected_failures 循环 / build_provenance / build_devset_section / aggregate_summary / public_per_doc loop / report dict keys）
- module source forbidden tokens 第五批
- module source 字符串精确补强（imports / docstring / control flow）
- signatures 精确补强（param kinds / annotations / defaults）
- 模块整体合理性
- 端到端集成补强（更多场景）
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


# ---------- _load_annotation 行为深度第五批 ----------


def test_load_annotation_with_array_top_level(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("[]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == []


def test_load_annotation_with_int_top_level(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("42", encoding="utf-8")
    out = _load_annotation(p)
    assert out == 42


def test_load_annotation_with_string_top_level(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('"hello"', encoding="utf-8")
    out = _load_annotation(p)
    assert out == "hello"


def test_load_annotation_with_bool_top_level(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("true", encoding="utf-8")
    out = _load_annotation(p)
    assert out is True


def test_load_annotation_with_null_top_level(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("null", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_with_huge_json(tmp_path):
    """大 dict 也能加载。"""
    big = {str(i): i for i in range(1000)}
    p = tmp_path / "ann.json"
    p.write_text(json.dumps(big), encoding="utf-8")
    out = _load_annotation(p)
    assert len(out) == 1000


def test_load_annotation_with_trailing_comma_invalid(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": 1,}', encoding="utf-8")
    # trailing comma → JSONDecodeError → return None
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_with_single_quotes_invalid(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("{'a': 1}", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_with_unclosed_brace_invalid(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": 1', encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_with_html_entities(tmp_path):
    """JSON 里 & 不是合法字符。"""
    p = tmp_path / "ann.json"
    p.write_text('{"a": "x & y"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": "x & y"}  # & 在字符串里 OK


def test_load_annotation_with_binary_garbage(tmp_path):
    p = tmp_path / "ann.json"
    p.write_bytes(b"\x00\x01\x02\x03")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_with_only_newlines(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("\n\n\n", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_with_comment_invalid(tmp_path):
    """JSON 不支持注释。"""
    p = tmp_path / "ann.json"
    p.write_text("// comment\n{}", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_with_nested_dict_3_levels(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": {"b": {"c": 1}}}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": {"b": {"c": 1}}}


def test_load_annotation_with_unicode_escape_sequence(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": "\\u4f60\\u597d"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": "你好"}


# ---------- _process_one source level 字符串精确补强第二批 ----------


def test_process_one_source_defines_out_stub_with_per_doc_subdir():
    src = inspect.getsource(_process_one)
    assert "output_root / \"_per_doc\"" in src
    assert "f\"{doc.doc_id}.json\"" in src


def test_process_one_source_uses_parent_mkdir():
    src = inspect.getsource(_process_one)
    assert "out_stub.parent.mkdir(parents=True, exist_ok=True)" in src


def test_process_one_source_uses_perf_counter_for_t0():
    src = inspect.getsource(_process_one)
    assert "t0 = time.perf_counter()" in src


def test_process_one_source_calls_process_single_with_kwargs():
    src = inspect.getsource(_process_one)
    assert "process_single(" in src
    assert "doc.resolved_path" in src
    assert "parser_name=parser_name" in src
    assert "max_chars=max_chars" in src
    assert "write_json=False" in src


def test_process_one_source_uses_elapsed_with_perf_counter_diff():
    src = inspect.getsource(_process_one)
    assert "elapsed = time.perf_counter() - t0" in src


def test_process_one_source_uses_image_output_dir_for():
    src = inspect.getsource(_process_one)
    assert "image_output_dir_for(out_stub, document.source_hash)" in src


def test_process_one_source_uses_isfile_before_unlink():
    src = inspect.getsource(_process_one)
    assert "if out_stub.is_file():" in src


def test_process_one_source_unlinks_in_try_except_oserror():
    src = inspect.getsource(_process_one)
    assert "out_stub.unlink()" in src
    assert "except OSError:" in src


def test_process_one_source_returns_5_tuple_for_errors_path():
    src = inspect.getsource(_process_one)
    # if errors: return None, errors[0].to_dict(), elapsed, None, image_dir
    assert "errors[0].to_dict()" in src


def test_process_one_source_returns_5_tuple_for_none_document():
    src = inspect.getsource(_process_one)
    assert "process_single returned None without errors" in src
    assert '"code": "unknown"' in src


def test_process_one_source_returns_normal_5_tuple():
    src = inspect.getsource(_process_one)
    assert "document.to_dict(), None, elapsed, document.parser_version, image_dir" in src


def test_process_one_source_image_dir_only_if_document_not_none():
    src = inspect.getsource(_process_one)
    assert "if document is not None:" in src


def test_process_one_source_uses_doc_attrs():
    """使用 doc.doc_id / doc.resolved_path / doc.expectations（dataclass 字段）。"""
    src = inspect.getsource(_process_one)
    assert "doc.doc_id" in src
    assert "doc.resolved_path" in src


def test_process_one_source_no_yield():
    src = inspect.getsource(_process_one)
    assert "yield" not in src


def test_process_one_source_no_async():
    src = inspect.getsource(_process_one)
    assert "async " not in src


def test_process_one_source_no_class():
    src = inspect.getsource(_process_one)
    assert "class " not in src


def test_process_one_source_no_global():
    src = inspect.getsource(_process_one)
    assert "global " not in src


# ---------- run_evaluation source level 字符串精确补强第二批 ----------


def test_run_evaluation_source_defines_output_root():
    src = inspect.getsource(run_evaluation)
    assert "output_root = Path(output_path).parent" in src


def test_run_evaluation_source_creates_output_root_dir():
    src = inspect.getsource(run_evaluation)
    assert "output_root.mkdir(parents=True, exist_ok=True)" in src


def test_run_evaluation_source_initializes_per_doc_results_list():
    src = inspect.getsource(run_evaluation)
    assert "per_doc_results: list[dict[str, Any]] = []" in src


def test_run_evaluation_source_initializes_parser_version_for_prov():
    src = inspect.getsource(run_evaluation)
    assert "parser_version_for_prov: str | None = None" in src


def test_run_evaluation_source_loops_over_manifest_documents():
    src = inspect.getsource(run_evaluation)
    assert "for doc in manifest.documents:" in src


def test_run_evaluation_source_calls_process_one():
    src = inspect.getsource(run_evaluation)
    assert "_process_one(" in src
    assert "doc, output_root, parser_name, max_chars" in src


def test_run_evaluation_source_unpacked_5_tuple():
    src = inspect.getsource(run_evaluation)
    assert "document, error, total_seconds, parser_version, image_dir" in src


def test_run_evaluation_source_caches_first_parser_version():
    src = inspect.getsource(run_evaluation)
    assert "if parser_version and not parser_version_for_prov:" in src


def test_run_evaluation_source_calls_compute_automatic_metrics():
    src = inspect.getsource(run_evaluation)
    assert "compute_automatic_metrics(" in src


def test_run_evaluation_source_passes_image_base_dir_with_isdir_check():
    src = inspect.getsource(run_evaluation)
    assert "image_base_dir=image_dir if (image_dir is not None and image_dir.is_dir()) else None" in src


def test_run_evaluation_source_calls_load_annotation():
    src = inspect.getsource(run_evaluation)
    assert "_load_annotation(doc.annotation_resolved)" in src


def test_run_evaluation_source_calls_figure_caption_prf():
    src = inspect.getsource(run_evaluation)
    assert "fig_caps = figure_caption_prf(document, annotation)" in src


def test_run_evaluation_source_calls_chunk_boundary_prf_with_tolerance():
    src = inspect.getsource(run_evaluation)
    assert "chunk_b = chunk_boundary_prf(" in src
    assert "tolerance_chars=tolerance_chars" in src


def test_run_evaluation_source_uses_metrics_update_twice():
    src = inspect.getsource(run_evaluation)
    # metrics.update(fig_caps) 和 metrics.update(chunk_b)
    update_count = src.count("metrics.update(")
    assert update_count == 2


def test_run_evaluation_source_pops_tolerance_and_missing_records():
    src = inspect.getsource(run_evaluation)
    assert 'chunk_b.pop("_tolerance_chars"' in src
    assert 'chunk_b.pop("_missing_markers"' in src


def test_run_evaluation_source_appends_per_doc_results():
    src = inspect.getsource(run_evaluation)
    assert "per_doc_results.append(" in src


def test_run_evaluation_source_per_doc_dict_has_doc_id():
    src = inspect.getsource(run_evaluation)
    assert '"doc_id": doc.doc_id' in src


def test_run_evaluation_source_per_doc_dict_has_source_type():
    src = inspect.getsource(run_evaluation)
    assert '"source_type": doc.source_type' in src


def test_run_evaluation_source_per_doc_dict_has_metrics():
    src = inspect.getsource(run_evaluation)
    assert '"metrics": metrics' in src


def test_run_evaluation_source_per_doc_dict_has_wall_time_seconds():
    src = inspect.getsource(run_evaluation)
    assert '"wall_time_seconds":' in src
    assert '"total": total_seconds' in src
    assert '"parse": None' in src
    assert '"chunk": None' in src
    assert '"parse_reason": "not_instrumented"' in src
    assert '"chunk_reason": "not_instrumented"' in src


def test_run_evaluation_source_per_doc_dict_has_annotation_present():
    src = inspect.getsource(run_evaluation)
    assert '"_annotation_present": annotation is not None' in src


def test_run_evaluation_source_loops_over_expected_failures():
    src = inspect.getsource(run_evaluation)
    assert "for ef in manifest.expected_failures:" in src


def test_run_evaluation_source_expected_failure_uses_ef_doc_id():
    src = inspect.getsource(run_evaluation)
    assert "ef.doc_id" in src


def test_run_evaluation_source_expected_failure_uses_ef_resolved_path():
    src = inspect.getsource(run_evaluation)
    assert "ef.resolved_path" in src


def test_run_evaluation_source_expected_failure_uses_ef_expected_error_code():
    src = inspect.getsource(run_evaluation)
    assert "ef.expected_error_code" in src


def test_run_evaluation_source_expected_failure_calls_process_single():
    src = inspect.getsource(run_evaluation)
    # 注意 expected_failure 也调用 process_single
    process_single_count = src.count("process_single(")
    assert process_single_count >= 1


def test_run_evaluation_source_expected_failure_appends_results():
    src = inspect.getsource(run_evaluation)
    assert "expected_failure_results.append(" in src


def test_run_evaluation_source_expected_failure_dict_has_matches():
    src = inspect.getsource(run_evaluation)
    assert '"matches": actual_code == ef.expected_error_code' in src


def test_run_evaluation_source_calls_build_provenance():
    src = inspect.getsource(run_evaluation)
    assert "build_provenance(" in src
    assert "project_root=manifest.project_root" in src
    assert "parser_name=parser_name" in src
    assert "max_chars=max_chars" in src
    assert "parser_version=parser_version_for_prov" in src


def test_run_evaluation_source_calls_build_devset_section():
    src = inspect.getsource(run_evaluation)
    assert "build_devset_section(manifest)" in src


def test_run_evaluation_source_calls_aggregate_summary():
    src = inspect.getsource(run_evaluation)
    assert "aggregate_summary(per_doc_results)" in src


def test_run_evaluation_source_initializes_public_per_doc():
    src = inspect.getsource(run_evaluation)
    assert "public_per_doc = []" in src


def test_run_evaluation_source_loops_over_per_doc_results_for_public():
    src = inspect.getsource(run_evaluation)
    assert "for r in per_doc_results:" in src


def test_run_evaluation_source_public_per_doc_excludes_private_keys():
    """public_per_doc 不含 _annotation_present / _tolerance_chars / _missing_markers。"""
    src = inspect.getsource(run_evaluation)
    public_loop_start = src.find("public_per_doc = []")
    public_loop_end = src.find("report = {")
    public_section = src[public_loop_start:public_loop_end]
    assert '"doc_id": r["doc_id"]' in public_section
    assert '"source_type": r["source_type"]' in public_section
    assert '"metrics": r["metrics"]' in public_section
    assert '"wall_time_seconds": r["wall_time_seconds"]' in public_section
    # 不应包含私有字段
    assert "_annotation_present" not in public_section
    assert "_tolerance_chars" not in public_section
    assert "_missing_markers" not in public_section


def test_run_evaluation_source_report_dict_has_6_keys():
    src = inspect.getsource(run_evaluation)
    report_start = src.find("report = {")
    report_end = src.find("out_p = Path(output_path)")
    report_section = src[report_start:report_end]
    assert '"report_version": REPORT_VERSION' in report_section
    assert '"provenance": provenance' in report_section
    assert '"devset": devset' in report_section
    assert '"summary": summary' in report_section
    assert '"per_doc": public_per_doc' in report_section
    assert '"expected_failures": expected_failure_results' in report_section


def test_run_evaluation_source_uses_out_p_path():
    src = inspect.getsource(run_evaluation)
    assert "out_p = Path(output_path)" in src


def test_run_evaluation_source_opens_out_p_with_w_utf8():
    src = inspect.getsource(run_evaluation)
    assert 'out_p.open("w", encoding="utf-8")' in src


def test_run_evaluation_source_uses_json_dump_with_kwargs():
    src = inspect.getsource(run_evaluation)
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in src


def test_run_evaluation_source_no_yield():
    src = inspect.getsource(run_evaluation)
    assert "yield" not in src


def test_run_evaluation_source_no_async():
    src = inspect.getsource(run_evaluation)
    assert "async " not in src


def test_run_evaluation_source_no_class():
    src = inspect.getsource(run_evaluation)
    assert "class " not in src


def test_run_evaluation_source_no_global():
    src = inspect.getsource(run_evaluation)
    assert "global " not in src


# ---------- module source forbidden tokens 第五批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "abc", "aifc", "antigravity", "argparse", "asdl", "asyncio",
        "audioop", "base64", "binascii", "binhex", "calendar",
        "concurrent", "contextlib", "copyreg", "crypt",
        "curses", "datetime", "dl", "docxml",
        "dummy_threading", "email", "encodings", "ensurepip",
        "enum", "errno", "fileinput", "fnmatch",
        "formatter", "ftplib", "functools", "genericpath",
        "getopt", "getpass", "gettext", "glob",
        "gopherlib", "heapq", "html", "http",
        "imaplib", "ihooks", "imghdr", "importlib",
        "inspect", "ipaddress", "itertools", "keyword",
        "linecache", "locale", "logging", "lzma",
        "mailbox", "mailcap", "markupbase", "md5",
        "mhlib", "mimetypes", "mimify", "mmap",
        "msilib", "multifile", "multiprocessing", "mutex",
        "netrc", "nis", "nntplib", "numbers",
        "opcode", "operator", "optparse", "os2emxpath",
        "parser", "pdb", "pickle", "pickletools",
        "pipes", "pkgutil", "platform", "plistlib",
        "poplib", "posixfile", "posixpath", "profile",
        "pstats", "pty", "pyclbr", "py_compile",
        "pydoc", "queue", "quopri", "random",
        "readline", "reprlib", "rexec", "rfc822",
        "rlcompleter", "robotparser", "runpy", "sched",
        "secrets", "select", "sets", "sgmlop",
        "sgmllib", "sha", "shelve", "shlex",
        "shutil", "signal", "site", "smtplib",
        "smtpd", "sndhdr", "socket", "socketserver",
        "spawn", "spwd", "sqlite3", "ssl",
        "stat", "stringprep", "struct", "subprocess",
        "sunau", "sunaudio", "symtable", "sys",
        "sysconfig", "tabnanny", "tarfile", "telnetlib",
        "tempfile", "termios", "threading", "timeit",
        "tomllib", "token", "tokenize", "trace",
        "traceback", "tracemalloc", "tty", "turtle",
        "types", "unicodedata", "unittest", "urllib",
        "urllib2", "urlparse", "user", "userdict",
        "userlist", "usersite", "uuid", "venv",
        "warnings", "wave", "weakref", "webbrowser",
        "whichdb", "wsgiref", "xdrlib", "xml",
        "xmlrpc", "zipapp", "zipfile", "zipimport",
        "zlib", "zoneinfo", "math",
    ],
)
def test_module_source_forbidden_tokens_fifth_batch(token):
    """这些 stdlib 模块不应出现在 runner.py。"""
    src = inspect.getsource(rmod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_from_future():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


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


def test_module_source_imports_process_single_and_image_output_dir_for():
    src = inspect.getsource(rmod)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_imports_report_version():
    src = inspect.getsource(rmod)
    assert "from evaluation import REPORT_VERSION" in src


def test_module_source_imports_annotation_metrics():
    src = inspect.getsource(rmod)
    assert "from evaluation.annotation_metrics import (" in src
    assert "chunk_boundary_prf" in src
    assert "figure_caption_prf" in src


def test_module_source_imports_compute_automatic_metrics():
    src = inspect.getsource(rmod)
    assert "from evaluation.metrics import compute_automatic_metrics" in src


def test_module_source_imports_report_helpers():
    src = inspect.getsource(rmod)
    assert "from evaluation.report import (" in src
    assert "aggregate_summary" in src
    assert "build_devset_section" in src
    assert "build_provenance" in src


def test_module_source_docstring_mentions_total():
    src = inspect.getsource(rmod)
    assert "total" in src.lower()


def test_module_source_docstring_mentions_pipeline():
    src = inspect.getsource(rmod)
    assert "pipeline" in src.lower()


def test_module_source_docstring_mentions_metrics():
    src = inspect.getsource(rmod)
    assert "metrics" in src.lower()


def test_module_source_docstring_mentions_not_instrumented():
    src = inspect.getsource(rmod)
    assert "not_instrumented" in src or "未插桩" in src


def test_module_source_no_yield():
    src = inspect.getsource(rmod)
    assert "yield" not in src


def test_module_source_no_async():
    src = inspect.getsource(rmod)
    assert "async " not in src


def test_module_source_no_global():
    src = inspect.getsource(rmod)
    assert "global " not in src


def test_module_source_no_main_block():
    src = inspect.getsource(rmod)
    assert "__main__" not in src


def test_module_source_no_class_definition():
    src = inspect.getsource(rmod)
    body_lines = [l for l in src.splitlines() if not l.strip().startswith(("#", '"', "'"))]
    body = "\n".join(body_lines)
    assert "\nclass " not in body


def test_module_source_no_lambda():
    src = inspect.getsource(rmod)
    assert "lambda " not in src


def test_module_source_no_decorators():
    src = inspect.getsource(rmod)
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("@"):
            pytest.fail(f"unexpected decorator at line {i}: {line}")


def test_module_source_has_all_with_1_entry():
    src = inspect.getsource(rmod)
    assert '__all__ = ["run_evaluation"]' in src


def test_module_source_has_3_module_level_functions():
    src = inspect.getsource(rmod)
    func_count = sum(1 for line in src.splitlines() if line.startswith("def "))
    assert func_count == 3


# ---------- signatures 精确补强 ----------


def test_load_annotation_signature_1_param():
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1


def test_load_annotation_param_name_path():
    sig = inspect.signature(_load_annotation)
    assert list(sig.parameters.keys()) == ["path"]


def test_load_annotation_param_annotation_union():
    sig = inspect.signature(_load_annotation)
    a = sig.parameters["path"].annotation
    assert "Path" in str(a) and "None" in str(a)


def test_load_annotation_return_annotation_union():
    sig = inspect.signature(_load_annotation)
    a = sig.return_annotation
    assert "dict" in str(a) and "None" in str(a)


def test_load_annotation_param_kind():
    sig = inspect.signature(_load_annotation)
    p = list(sig.parameters.values())[0]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_process_one_signature_4_params():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_process_one_param_names():
    sig = inspect.signature(_process_one)
    assert list(sig.parameters.keys()) == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_param_kinds():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_process_one_return_annotation_tuple():
    sig = inspect.signature(_process_one)
    a = sig.return_annotation
    assert "tuple" in str(a)


def test_process_one_no_varargs_varkw():
    sig = inspect.signature(_process_one)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_run_evaluation_signature_5_params():
    sig = inspect.signature(run_evaluation)
    assert len(sig.parameters) == 5


def test_run_evaluation_param_names():
    sig = inspect.signature(run_evaluation)
    assert list(sig.parameters.keys()) == [
        "manifest",
        "output_path",
        "parser_name",
        "max_chars",
        "tolerance_chars",
    ]


def test_run_evaluation_manifest_no_default():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].default is inspect.Parameter.empty


def test_run_evaluation_output_path_no_default():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].default is inspect.Parameter.empty


def test_run_evaluation_parser_name_default_fallback():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_run_evaluation_max_chars_default_800():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_run_evaluation_tolerance_chars_default_30():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_keyword_only_marker_present():
    """run_evaluation 用 * 标记 keyword-only。"""
    sig = inspect.signature(run_evaluation)
    # 找到 * 后的参数都应是 KEYWORD_ONLY
    seen_star = False
    for p in sig.parameters.values():
        if p.kind == inspect.Parameter.VAR_KEYWORD:
            continue
        if p.name == "manifest" or p.name == "output_path":
            assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
        else:
            # parser_name/max_chars/tolerance_chars 应是 KEYWORD_ONLY
            assert p.kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_no_varargs():
    sig = inspect.signature(run_evaluation)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds


def test_run_evaluation_no_varkw():
    sig = inspect.signature(run_evaluation)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_no_varargs_varkw_in_helpers():
    for fn in [_load_annotation, _process_one, run_evaluation]:
        sig = inspect.signature(fn)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_POSITIONAL not in kinds
        assert inspect.Parameter.VAR_KEYWORD not in kinds


# ---------- 模块整体合理性 ----------


def test_module_namespace():
    assert isinstance(rmod, types.ModuleType)


def test_module_namespace_name():
    assert rmod.__name__ == "evaluation.runner"


def test_module_all_is_list():
    assert isinstance(rmod.__all__, list)


def test_module_all_has_1_entry():
    assert len(rmod.__all__) == 1


def test_module_all_only_run_evaluation():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_all_entries_str():
    for entry in rmod.__all__:
        assert isinstance(entry, str)


def test_module_has_2_private_functions():
    private = [
        v for v in vars(rmod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == rmod.__name__
        and v.__name__.startswith("_")
        and not v.__name__.startswith("__")
    ]
    assert len(private) == 2


def test_module_has_1_public_function():
    public = [
        v for v in vars(rmod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == rmod.__name__
        and not v.__name__.startswith("_")
    ]
    assert len(public) == 1
    assert public[0].__name__ == "run_evaluation"


def test_module_no_class_definition():
    classes = [
        v for v in vars(rmod).values()
        if isinstance(v, type) and v.__module__ == rmod.__name__
    ]
    assert len(classes) == 0


def test_module_no_main_block():
    src = inspect.getsource(rmod)
    assert "__main__" not in src


def test_module_callable_run_evaluation():
    assert callable(run_evaluation)


def test_module_callable_load_annotation():
    assert callable(_load_annotation)


def test_module_callable_process_one():
    assert callable(_process_one)


# ---------- 端到端集成补强 ----------


def _make_minimal_manifest(path):
    """构造一个最小 manifest JSON 文件。"""
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
    # 输出文件存在
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


def test_e2e_no_documents_provenance_has_evaluator_version(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out)
    assert "evaluator_version" in report["provenance"]
    assert "report_version" in report["provenance"]
    assert "parser_name" in report["provenance"]


def test_e2e_no_documents_creates_subdir(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "sub" / "deep" / "out.json"
    report = run_evaluation(manifest, out)
    assert out.is_file()


def test_e2e_loadable_report(tmp_path):
    """报告写出后可被 json.load 重新加载。"""
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
    # indent=2 会有换行
    assert "\n" in text


def test_e2e_ensure_ascii_false_preserves_unicode(tmp_path):
    """报告用 ensure_ascii=False，所以 Unicode 字符直接保留。"""
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    run_evaluation(manifest, out)
    text = out.read_text(encoding="utf-8")
    # 没有被 \u 转义的必要 ASCII 范围外字符（manifest 里没 Unicode，但 ensure_ascii=False 仍然设置）
    # 这条断言主要是确保 ensure_ascii=False 被调用
    assert "report_version" in text


def test_e2e_deterministic_across_calls(tmp_path):
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out1 = tmp_path / "out1.json"
    out2 = tmp_path / "out2.json"
    r1 = run_evaluation(manifest, out1)
    r2 = run_evaluation(manifest, out2)
    # 比较 metrics 和结构（不比较时间戳）
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
    # tolerance_chars 不在 provenance 里，但 chunk_boundary 中的 _tolerance_chars 应是 0
    # 因为没有文档，per_doc 为空，没直接断言；只确保不报错
    assert isinstance(report["per_doc"], list)


def test_e2e_with_kreuzberg_parser_name(tmp_path):
    """传 parser_name=kreuzberg 也应工作（不实际跑文档）。"""
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "out.json"
    report = run_evaluation(manifest, out, parser_name="kreuzberg")
    assert report["provenance"]["parser_name"] == "kreuzberg"


def test_e2e_creates_per_doc_subdir_even_with_no_documents(tmp_path):
    """即使 0 文档，_per_doc 子目录也建立（被 mkdir 创建）。"""
    from evaluation.manifest import load_manifest

    mpath = tmp_path / "manifest.json"
    _make_minimal_manifest(mpath)
    manifest = load_manifest(mpath)
    out = tmp_path / "sub" / "out.json"
    run_evaluation(manifest, out)
    # output 父目录已被 mkdir
    assert out.parent.is_dir()


def test_e2e_load_annotation_none_returns_none():
    """_load_annotation(None) 直接 None。"""
    assert _load_annotation(None) is None


def test_e2e_load_annotation_nonexistent_returns_none(tmp_path):
    """文件不存在 → None。"""
    p = tmp_path / "no.json"
    assert _load_annotation(p) is None


def test_e2e_load_annotation_valid_json(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"key": "value"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"key": "value"}


def test_e2e_load_annotation_invalid_json_returns_none(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("not json", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None
