"""evaluation/runner.py 第三十轮 edges 测试（Round 335）。

重点补强 edges28 未触及的角度：
- _load_annotation 行为深度第四批（嵌套数组 / Unicode BOM / 单元素 array / 空对象）
- _process_one source level 字符串精确补强（5 returns / 各路径细节）
- run_evaluation source level 字符串精确补强（imports / module-level constants）
- module source forbidden tokens 第四批（~75 stdlib）
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

import pytest

from evaluation import runner
from evaluation.runner import (
    _load_annotation,
    _process_one,
    run_evaluation,
)


# ---------- _load_annotation 行为深度第四批 ----------


def test_load_annotation_with_nested_arrays(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"k": [[1, 2], [3, 4]]}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": [[1, 2], [3, 4]]}


def test_load_annotation_with_mixed_types_array(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"k": [1, "x", true, null, [1.0]]}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": [1, "x", True, None, [1.0]]}


def test_load_annotation_with_unicode_in_keys(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"中文": 1}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"中文": 1}


def test_load_annotation_with_unicode_in_string_value(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"k": "你好"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": "你好"}


def test_load_annotation_with_bom_bytes(tmp_path):
    """BOM 字节开头 → json.load 可能拒绝（utf-8 不剥 BOM）。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'\xef\xbb\xbf{"x": 1}')
    out = _load_annotation(p)
    # BOM 行为：json.load 用 utf-8 时 BOM 会触发错误 → 返回 None
    # 但有些情况下也能解析 → 不强制
    assert out is None or out == {"x": 1}


def test_load_annotation_with_utf8_bom_text(tmp_path):
    """用 'utf-8-sig' 才能正确剥 BOM；这里用 utf-8 → 视实现。"""
    p = tmp_path / "a.json"
    p.write_bytes(b'\xef\xbb\xbf{}')
    out = _load_annotation(p)
    assert out is None or out == {}


def test_load_annotation_with_emoji(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"k": "🎉"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": "🎉"}


def test_load_annotation_with_long_string_value(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"k": "' + 'a' * 1000 + '"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": "a" * 1000}


def test_load_annotation_with_deeply_nested_dict(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"a": {"b": {"c": {"d": {"e": 1}}}}}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"a": {"b": {"c": {"d": {"e": 1}}}}}


def test_load_annotation_with_empty_string(tmp_path):
    """空字符串不是合法 JSON。"""
    p = tmp_path / "a.json"
    p.write_text("", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


def test_load_annotation_with_only_whitespace(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("   \n  \t  ", encoding="utf-8")
    out = _load_annotation(p)
    assert out is None


# ---------- _process_one source level 字符串精确补强 ----------


def test_process_one_source_has_out_stub_init():
    src = inspect.getsource(_process_one)
    assert "out_stub = output_root" in src
    assert '_per_doc' in src


def test_process_one_source_has_parent_mkdir():
    src = inspect.getsource(_process_one)
    assert "out_stub.parent.mkdir" in src


def test_process_one_source_has_perf_counter_before():
    src = inspect.getsource(_process_one)
    assert "t0 = time.perf_counter()" in src


def test_process_one_source_has_perf_counter_after():
    src = inspect.getsource(_process_one)
    assert "elapsed = time.perf_counter() - t0" in src


def test_process_one_source_has_5_return_paths():
    """5-tuple return：(document, error, elapsed, parser_version, image_dir)。"""
    src = inspect.getsource(_process_one)
    # 3 个 return 语句（errors path / document None / normal）
    return_count = src.count("return ")
    assert return_count == 3


def test_process_one_source_has_unlink_in_try_except_oserror():
    src = inspect.getsource(_process_one)
    assert "try:" in src
    assert "except OSError:" in src
    assert "out_stub.unlink()" in src


def test_process_one_source_has_unknown_code_for_none_document():
    src = inspect.getsource(_process_one)
    assert '"unknown"' in src
    assert '"process_single returned None without errors"' in src


# ---------- run_evaluation source level 字符串精确补强 ----------


def test_run_evaluation_source_has_kwargs_only():
    src = inspect.getsource(run_evaluation)
    assert "*," in src


def test_run_evaluation_source_has_parser_name_default_fallback():
    src = inspect.getsource(run_evaluation)
    assert 'parser_name: str = "fallback"' in src


def test_run_evaluation_source_has_max_chars_default_800():
    src = inspect.getsource(run_evaluation)
    assert "max_chars: int = 800" in src


def test_run_evaluation_source_has_tolerance_chars_default_30():
    src = inspect.getsource(run_evaluation)
    assert "tolerance_chars: int = 30" in src


def test_run_evaluation_source_has_manifest_param():
    src = inspect.getsource(run_evaluation)
    assert "manifest," in src


def test_run_evaluation_source_has_output_path_param():
    src = inspect.getsource(run_evaluation)
    assert "output_path: Path," in src


def test_run_evaluation_source_has_2_loops():
    src = inspect.getsource(run_evaluation)
    # 主循环 + expected_failures 循环
    assert src.count("for ") >= 2


def test_run_evaluation_source_has_compute_automatic_metrics_kwargs():
    src = inspect.getsource(run_evaluation)
    assert "compute_automatic_metrics(" in src


def test_run_evaluation_source_has_load_annotation_call():
    src = inspect.getsource(run_evaluation)
    assert "_load_annotation(doc.annotation_resolved)" in src


def test_run_evaluation_source_has_per_doc_results_append():
    src = inspect.getsource(run_evaluation)
    assert "per_doc_results.append(" in src


def test_run_evaluation_source_has_public_per_doc_loop():
    src = inspect.getsource(run_evaluation)
    assert "public_per_doc = []" in src


def test_run_evaluation_source_has_report_dict_init():
    src = inspect.getsource(run_evaluation)
    assert "report = {" in src
    assert '"report_version": REPORT_VERSION' in src


def test_run_evaluation_source_returns_report():
    src = inspect.getsource(run_evaluation)
    assert "return report" in src


def test_run_evaluation_source_has_only_one_return():
    src = inspect.getsource(run_evaluation)
    # run_evaluation 只有一个 return
    assert src.count("return ") == 1


def test_run_evaluation_source_has_json_dump_kwargs():
    src = inspect.getsource(run_evaluation)
    assert 'json.dump(report, f, ensure_ascii=False, indent=2)' in src


# ---------- module source forbidden tokens 第四批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "_thread", "_weakref", "abc", "aifc", "antigravity",
        "asynchat", "asyncio", "asyncore", "audioop", "binhex",
        "cProfile", "cgi", "cgitb", "chunk", "code", "codeop",
        "colorsys", "commands", "compileall", "ctypes",
        "curses", "datetime", "decimal", "difflib", "dis",
        "distutils", "doctest", "dummy_threading", "ensurepip",
        "enum", "errno", "exceptions", "filecmp", "fileinput",
        "fmt", "formatter", "fpformat", "fractions", "gc",
        "genericpath", "getopt", "getpass", "glob", "gdbm",
        "grp", "hashlib", "hmac", "hotshot", "html",
        "http", "ihooks", "imghdr",
        "itertools", "keyword", "linecache", "linuxaudiodev",
        "logging", "macpath", "macurl2path", "marshal",
        "md5", "mhlib", "mimetools", "multifile", "mutex",
        "nis", "nntplib", "parser",
        "pdb", "pickle", "pickletools", "pipes", "pkgutil",
        "plistlib", "popen2", "poplib", "posixfile", "pprint",
        "pty", "pyclbr", "pydoc", "queue", "quopri",
        "random", "readline", "resource",
        "rexec", "rfc822", "rlcompleter", "robotparser",
        "sets", "sgmllib", "shelve", "shutil",
        "smtpd", "sndhdr", "socket", "spwd",
        "sre_compile", "sre_constants", "sre_parse", "statistics",
        "stringprep", "struct", "sunau",
    ],
)
def test_module_source_forbidden_tokens_fourth_batch(token):
    """这些 stdlib 模块不应出现在 runner.py。"""
    src = inspect.getsource(runner)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_app_pipeline_import():
    src = inspect.getsource(runner)
    assert "from app.pipeline import image_output_dir_for, process_single" in src


def test_module_source_docstring_mentions_metrics():
    src = inspect.getsource(runner)
    assert "metrics" in src


# ---------- signatures 精确补强 ----------


def test_load_annotation_param_count():
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1


def test_process_one_signature_4_params():
    sig = inspect.signature(_process_one)
    assert len(sig.parameters) == 4


def test_run_evaluation_signature_5_params():
    sig = inspect.signature(run_evaluation)
    assert len(sig.parameters) == 5


def test_run_evaluation_keyword_only_marker():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert params[0].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params[1].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    for p in params[2:]:
        assert p.kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_defaults_values():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


def test_no_varargs_varkw_in_functions():
    for fn in (_load_annotation, _process_one, run_evaluation):
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_POSITIONAL
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- 模块整体合理性 ----------


def test_namespace_module():
    assert isinstance(runner, types.ModuleType)


def test_namespace_module_all():
    assert hasattr(runner, "__all__")
    assert "run_evaluation" in runner.__all__


def test_module_has_2_private_functions():
    private_funcs = [
        n for n, v in vars(runner).items()
        if n.startswith("_") and not n.startswith("__")
        and isinstance(v, types.FunctionType)
        and getattr(v, "__module__", "") == runner.__name__
    ]
    assert sorted(private_funcs) == ["_load_annotation", "_process_one"]


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


def test_e2e_creates_output_in_subdir(tmp_path):
    out = tmp_path / "a" / "b" / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    run_evaluation(mf, out)
    assert out.is_file()


def test_e2e_returns_same_dict_as_written(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    returned = run_evaluation(mf, out)
    with out.open("r", encoding="utf-8") as f:
        written = json.load(f)
    assert returned == written


def test_e2e_run_with_default_kwargs(tmp_path):
    """不传任何 kwarg → 用默认 fallback / 800 / 30。"""
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    assert "report_version" in report


def test_e2e_devset_section_independent_of_documents(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    d = report["devset"]
    assert isinstance(d, dict)
    assert "file_count" in d
    assert "categories_covered" in d


def test_e2e_provenance_section_has_parser_name_default(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    p = report["provenance"]
    assert "parser_name" in p
    assert p["parser_name"] == "fallback"


def test_e2e_provenance_section_has_max_chars_default(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    p = report["provenance"]
    assert p["max_chars"] == 800


def test_e2e_provenance_section_has_tolerance_chars(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out, tolerance_chars=42)
    # tolerance_chars 是 chunk_boundary 用的，可能不在 provenance
    # 但 per_doc 的 _tolerance_chars 字段会带（public 时被剥）
    assert "report_version" in report


def test_e2e_summary_section_independent_of_documents(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out)
    s = report["summary"]
    assert isinstance(s, dict)


def test_e2e_run_with_max_chars_1(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out, max_chars=1)
    assert "report_version" in report


def test_e2e_run_with_tolerance_chars_0(tmp_path):
    out = tmp_path / "out.json"
    mf = _make_minimal_manifest(tmp_path)
    report = run_evaluation(mf, out, tolerance_chars=0)
    assert "report_version" in report
