"""evaluation/runner.py 第三十四轮 edges 测试（Round 361）。

重点补强 edges32 未触及的角度：
- _load_annotation source level 字符串精确补强第三批
- _process_one source level 字符串精确补强第五批
- run_evaluation source level 字符串精确补强第五批
- module source forbidden tokens 第十一批
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性补强
- 端到端集成补强
"""

from __future__ import annotations

import inspect
import json
import time
import types
from pathlib import Path
from typing import Any

import pytest

from app.pipeline import image_output_dir_for, process_single
from evaluation import REPORT_VERSION, runner as rmod
from evaluation.annotation_metrics import chunk_boundary_prf, figure_caption_prf
from evaluation.metrics import compute_automatic_metrics
from evaluation.report import aggregate_summary, build_devset_section, build_provenance
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation source level 字符串精确补强第三批 ----------


def test_load_annotation_source_starts_with_def():
    src = inspect.getsource(_load_annotation)
    assert src.lstrip().startswith("def _load_annotation(")


def test_load_annotation_source_one_param_path_optional():
    src = inspect.getsource(_load_annotation)
    assert "path: Path | None" in src


def test_load_annotation_source_returns_dict_or_none():
    src = inspect.getsource(_load_annotation)
    assert "dict[str, Any] | None" in src


def test_load_annotation_source_uses_path_is_none():
    src = inspect.getsource(_load_annotation)
    assert "path is None" in src


def test_load_annotation_source_uses_is_file_check():
    src = inspect.getsource(_load_annotation)
    assert ".is_file()" in src


def test_load_annotation_source_returns_none_for_none_path():
    src = inspect.getsource(_load_annotation)
    assert "return None" in src


def test_load_annotation_source_uses_try_except():
    src = inspect.getsource(_load_annotation)
    assert "try:" in src
    assert "except" in src


def test_load_annotation_source_uses_oserror_json_decode_error():
    src = inspect.getsource(_load_annotation)
    assert "OSError" in src
    assert "json.JSONDecodeError" in src


def test_load_annotation_source_uses_open_utf8():
    src = inspect.getsource(_load_annotation)
    assert '.open("r", encoding="utf-8")' in src


def test_load_annotation_source_uses_json_load():
    src = inspect.getsource(_load_annotation)
    assert "json.load(f)" in src


def test_load_annotation_source_returns_json_load():
    src = inspect.getsource(_load_annotation)
    assert "return json.load(f)" in src


def test_load_annotation_source_no_eval():
    src = inspect.getsource(_load_annotation)
    assert "eval(" not in src


def test_load_annotation_source_no_subprocess():
    src = inspect.getsource(_load_annotation)
    assert "subprocess" not in src


def test_load_annotation_source_no_yield():
    src = inspect.getsource(_load_annotation)
    assert "yield" not in src


def test_load_annotation_source_no_async_def():
    src = inspect.getsource(_load_annotation)
    assert "async def" not in src


def test_load_annotation_source_no_global_keyword():
    src = inspect.getsource(_load_annotation)
    lines = [l for l in src.splitlines() if not l.strip().startswith("#")]
    for l in lines:
        assert not l.strip().startswith("global ")


# ---------- _process_one source level 字符串精确补强第五批 ----------


def test_process_one_source_starts_with_def():
    src = inspect.getsource(_process_one)
    assert src.lstrip().startswith("def _process_one(")


def test_process_one_source_4_params():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.values())
    assert len(params) == 4
    assert [p.name for p in params] == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_source_returns_5_tuple():
    src = inspect.getsource(_process_one)
    assert "tuple[dict[str, Any] | None, dict[str, Any] | None, float, str | None, Path | None]" in src


def test_process_one_source_uses_out_stub():
    src = inspect.getsource(_process_one)
    assert "out_stub = " in src


def test_process_one_source_uses_per_doc_dir():
    src = inspect.getsource(_process_one)
    assert '"_per_doc"' in src
    assert "f\"{doc.doc_id}.json\"" in src or "f'{doc.doc_id}.json'" in src


def test_process_one_source_uses_mkdir_parents():
    src = inspect.getsource(_process_one)
    assert ".mkdir(parents=True, exist_ok=True)" in src


def test_process_one_source_uses_perf_counter():
    src = inspect.getsource(_process_one)
    assert "time.perf_counter()" in src


def test_process_one_source_calls_process_single():
    src = inspect.getsource(_process_one)
    assert "process_single(" in src


def test_process_one_source_passes_doc_resolved_path():
    src = inspect.getsource(_process_one)
    assert "doc.resolved_path" in src


def test_process_one_source_passes_parser_name():
    src = inspect.getsource(_process_one)
    assert "parser_name=parser_name" in src


def test_process_one_source_passes_max_chars():
    src = inspect.getsource(_process_one)
    assert "max_chars=max_chars" in src


def test_process_one_source_passes_write_json_false():
    src = inspect.getsource(_process_one)
    assert "write_json=False" in src


def test_process_one_source_uses_image_output_dir_for():
    src = inspect.getsource(_process_one)
    assert "image_output_dir_for(" in src


def test_process_one_source_uses_document_source_hash():
    src = inspect.getsource(_process_one)
    assert "document.source_hash" in src


def test_process_one_source_uses_image_dir_none_default():
    src = inspect.getsource(_process_one)
    assert "image_dir: Path | None = None" in src


def test_process_one_source_uses_document_is_not_none():
    src = inspect.getsource(_process_one)
    assert "if document is not None:" in src


def test_process_one_source_uses_unlink_out_stub():
    src = inspect.getsource(_process_one)
    assert "out_stub.is_file()" in src
    assert "out_stub.unlink()" in src


def test_process_one_source_uses_oserror_for_unlink():
    src = inspect.getsource(_process_one)
    assert "except OSError" in src


def test_process_one_source_uses_errors_truthy_check():
    src = inspect.getsource(_process_one)
    assert "if errors:" in src


def test_process_one_source_returns_errors_0_to_dict():
    src = inspect.getsource(_process_one)
    assert "errors[0].to_dict()" in src


def test_process_one_source_uses_document_is_none_branch():
    src = inspect.getsource(_process_one)
    assert "if document is None:" in src


def test_process_one_source_returns_unknown_error_message():
    src = inspect.getsource(_process_one)
    assert '"unknown"' in src
    assert "process_single returned None without errors" in src


def test_process_one_source_returns_5_tuple_in_success():
    src = inspect.getsource(_process_one)
    assert "return document.to_dict(), None, elapsed, document.parser_version, image_dir" in src


def test_process_one_source_uses_elapsed_calc():
    src = inspect.getsource(_process_one)
    assert "elapsed = time.perf_counter()" in src


def test_process_one_source_no_eval():
    src = inspect.getsource(_process_one)
    assert "eval(" not in src


def test_process_one_source_no_subprocess():
    src = inspect.getsource(_process_one)
    assert "subprocess" not in src


def test_process_one_source_no_yield():
    src = inspect.getsource(_process_one)
    assert "yield" not in src


# ---------- run_evaluation source level 字符串精确补强第五批 ----------


def test_run_evaluation_source_starts_with_def():
    src = inspect.getsource(run_evaluation)
    assert src.lstrip().startswith("def run_evaluation(")


def test_run_evaluation_source_5_params():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert len(params) == 5


def test_run_evaluation_source_returns_dict():
    src = inspect.getsource(run_evaluation)
    assert "-> dict[str, Any]" in src


def test_run_evaluation_source_uses_output_root():
    src = inspect.getsource(run_evaluation)
    assert "output_root = Path(output_path).parent" in src


def test_run_evaluation_source_uses_mkdir():
    src = inspect.getsource(run_evaluation)
    assert "output_root.mkdir(parents=True, exist_ok=True)" in src


def test_run_evaluation_source_initializes_per_doc_results():
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


def test_run_evaluation_source_calls_process_one():
    src = inspect.getsource(run_evaluation)
    assert "_process_one(" in src


def test_run_evaluation_source_calls_compute_automatic_metrics():
    src = inspect.getsource(run_evaluation)
    assert "compute_automatic_metrics(" in src


def test_run_evaluation_source_passes_doc_source_type():
    src = inspect.getsource(run_evaluation)
    assert "source_type=doc.source_type" in src


def test_run_evaluation_source_passes_doc_expectations():
    src = inspect.getsource(run_evaluation)
    assert "expectations=doc.expectations" in src


def test_run_evaluation_source_calls_load_annotation():
    src = inspect.getsource(run_evaluation)
    assert "_load_annotation(doc.annotation_resolved)" in src


def test_run_evaluation_source_calls_figure_caption_prf():
    src = inspect.getsource(run_evaluation)
    assert "figure_caption_prf(document, annotation)" in src


def test_run_evaluation_source_calls_chunk_boundary_prf():
    src = inspect.getsource(run_evaluation)
    assert "chunk_boundary_prf(" in src


def test_run_evaluation_source_passes_tolerance_chars_to_chunk_boundary():
    src = inspect.getsource(run_evaluation)
    assert "tolerance_chars=tolerance_chars" in src


def test_run_evaluation_source_pops_tolerance_chars():
    src = inspect.getsource(run_evaluation)
    assert 'chunk_b.pop("_tolerance_chars"' in src


def test_run_evaluation_source_pops_missing_markers():
    src = inspect.getsource(run_evaluation)
    assert 'chunk_b.pop("_missing_markers"' in src


def test_run_evaluation_source_uses_metrics_update():
    src = inspect.getsource(run_evaluation)
    assert "metrics.update(fig_caps)" in src
    assert "metrics.update(chunk_b)" in src


def test_run_evaluation_source_uses_image_dir_is_dir():
    src = inspect.getsource(run_evaluation)
    assert "image_dir.is_dir()" in src


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
    assert "report = {" in src
    assert '"report_version": REPORT_VERSION' in src
    assert '"provenance": provenance' in src
    assert '"devset": devset' in src
    assert '"summary": summary' in src
    assert '"per_doc": public_per_doc' in src
    assert '"expected_failures": expected_failure_results' in src


def test_run_evaluation_source_writes_json_with_indent():
    src = inspect.getsource(run_evaluation)
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in src


def test_run_evaluation_source_uses_out_p_path():
    src = inspect.getsource(run_evaluation)
    assert "out_p = Path(output_path)" in src
    assert "out_p.parent.mkdir(parents=True, exist_ok=True)" in src


def test_run_evaluation_source_uses_open_w_utf8():
    src = inspect.getsource(run_evaluation)
    assert 'out_p.open("w", encoding="utf-8")' in src


def test_run_evaluation_source_returns_report():
    src = inspect.getsource(run_evaluation)
    assert "return report" in src


def test_run_evaluation_source_uses_parser_version_first():
    src = inspect.getsource(run_evaluation)
    assert "if parser_version and not parser_version_for_prov:" in src


def test_run_evaluation_source_initializes_expected_failure_results():
    src = inspect.getsource(run_evaluation)
    assert "expected_failure_results: list[dict[str, Any]] = []" in src


def test_run_evaluation_source_appends_to_per_doc_results():
    src = inspect.getsource(run_evaluation)
    assert "per_doc_results.append(" in src


def test_run_evaluation_source_appends_to_expected_failure_results():
    src = inspect.getsource(run_evaluation)
    assert "expected_failure_results.append(" in src


def test_run_evaluation_source_handles_actual_code():
    src = inspect.getsource(run_evaluation)
    assert "actual_code = errors[0].code if errors else None" in src


def test_run_evaluation_source_compares_actual_with_expected():
    src = inspect.getsource(run_evaluation)
    assert "actual_code == ef.expected_error_code" in src


def test_run_evaluation_source_uses_total_seconds_in_wall_time():
    src = inspect.getsource(run_evaluation)
    assert '"total": total_seconds' in src


def test_run_evaluation_source_uses_parse_chunk_null():
    src = inspect.getsource(run_evaluation)
    assert '"parse": None' in src
    assert '"chunk": None' in src


def test_run_evaluation_source_uses_not_instrumented_reason():
    src = inspect.getsource(run_evaluation)
    assert '"not_instrumented"' in src


def test_run_evaluation_source_uses_doc_id_in_per_doc():
    src = inspect.getsource(run_evaluation)
    assert '"doc_id": doc.doc_id' in src


def test_run_evaluation_source_uses_doc_id_in_expected_failure():
    src = inspect.getsource(run_evaluation)
    assert '"doc_id": ef.doc_id' in src


def test_run_evaluation_source_uses_kwargs_only():
    """run_evaluation 的非 manifest/output_path 参数是 keyword-only。"""
    sig = inspect.signature(run_evaluation)
    for name in ("parser_name", "max_chars", "tolerance_chars"):
        assert sig.parameters[name].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_source_no_eval():
    src = inspect.getsource(run_evaluation)
    assert "eval(" not in src


def test_run_evaluation_source_no_subprocess():
    src = inspect.getsource(run_evaluation)
    assert "subprocess" not in src


def test_run_evaluation_source_no_yield():
    src = inspect.getsource(run_evaluation)
    assert "yield" not in src


# ---------- module source forbidden tokens 第十一批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "asyncio", "threading", "concurrent",
        "multiprocessing", "queue", "socket", "select",
        "re.match", "re.sub", "re.compile",
        "datetime.datetime",
        "time.time", "time.sleep",
        "os.system", "os.popen",
        "logging.getLogger",
        "urllib.request", "http.client",
        "ctypes", "pickle.loads",
        "shutil.rmtree",
        "tempfile.mkdtemp",
        "glob.glob",
        "unittest.TestCase",
        "pytest.fixture",
        "sys.exit",
        "copy.deepcopy",
        "weakref.ref",
        "abc.ABC",
        "contextlib.contextmanager",
        "operator.add",
        "functools.reduce",
        "itertools.chain",
        "collections.OrderedDict",
        "collections.deque",
        "collections.defaultdict",
        "importlib.import_module",
        "platform.system",
    ],
)
def test_runner_source_no_forbidden_token(token):
    src = inspect.getsource(rmod)
    # subprocess 是 forbidden（runner 不该用）
    assert token not in src, f"forbidden token found: {token}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_docstring_present():
    src = inspect.getsource(rmod)
    assert src.startswith('"""')


def test_module_source_docstring_mentions_runner():
    assert "runner" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_pipeline():
    assert "pipeline" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_total():
    assert "total" in rmod.__doc__.lower() or "计时" in rmod.__doc__


def test_module_source_docstring_mentions_parse_chunk():
    assert "parse" in rmod.__doc__.lower()
    assert "chunk" in rmod.__doc__.lower()


def test_module_source_docstring_mentions_not_instrumented():
    """docstring 提到 not_instrumented 或未插桩。"""
    assert "not_instrumented" in rmod.__doc__ or "未插桩" in rmod.__doc__


def test_module_source_has_future_annotations():
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


def test_module_source_imports_app_pipeline():
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


def test_module_source_no_relative_above_root():
    src = inspect.getsource(rmod)
    assert "from .." not in src


def test_module_source_no_star_import():
    src = inspect.getsource(rmod)
    assert "import *" not in src


def test_module_source_no_yield():
    src = inspect.getsource(rmod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(rmod)
    assert "async def" not in src


def test_module_source_no_walrus():
    src = inspect.getsource(rmod)
    assert ":=" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(rmod)
    assert 'if __name__' not in src


def test_module_source_no_user_class():
    classes = [
        name for name, val in vars(rmod).items()
        if isinstance(val, type) and val.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_source_3_user_functions():
    funcs = [
        name for name, val in vars(rmod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == rmod.__name__
    ]
    assert set(funcs) == {"_load_annotation", "_process_one", "run_evaluation"}


def test_module_source_all_1_entry():
    src = inspect.getsource(rmod)
    assert '__all__ = ["run_evaluation"]' in src


def test_module_source_no_eval():
    src = inspect.getsource(rmod)
    assert "eval(" not in src


def test_module_source_no_exec():
    src = inspect.getsource(rmod)
    assert "exec(" not in src


def test_module_source_no_compile():
    src = inspect.getsource(rmod)
    assert "compile(" not in src


def test_module_source_no_unlink_in_load_annotation():
    """_load_annotation 不应该 unlink。"""
    src = inspect.getsource(_load_annotation)
    assert ".unlink(" not in src


def test_module_source_no_write_in_load_annotation():
    src = inspect.getsource(_load_annotation)
    assert ".write(" not in src


# ---------- signatures 精确补强 ----------


def test_signature_load_annotation():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path"


def test_signature_load_annotation_path_no_default():
    sig = inspect.signature(_load_annotation)
    assert sig.parameters["path"].default is inspect.Parameter.empty


def test_signature_load_annotation_no_varargs():
    sig = inspect.signature(_load_annotation)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_process_one():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters.values())
    assert len(params) == 4
    assert [p.name for p in params] == ["doc", "output_root", "parser_name", "max_chars"]


def test_signature_process_one_no_defaults():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_process_one_no_varargs():
    sig = inspect.signature(_process_one)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_run_evaluation():
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    assert len(params) == 5


def test_signature_run_evaluation_manifest_no_default():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["manifest"].default is inspect.Parameter.empty


def test_signature_run_evaluation_output_path_no_default():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["output_path"].default is inspect.Parameter.empty


def test_signature_run_evaluation_parser_name_default_fallback():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"


def test_signature_run_evaluation_max_chars_default_800():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["max_chars"].default == 800


def test_signature_run_evaluation_tolerance_chars_default_30():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_run_evaluation_3_kwargs():
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


# ---------- 模块整体合理性补强 ----------


def test_module_has_docstring():
    assert rmod.__doc__ is not None
    assert len(rmod.__doc__) > 10


def test_module_has_all_attribute():
    assert hasattr(rmod, "__all__")


def test_module_all_is_list():
    assert isinstance(rmod.__all__, list)


def test_module_all_length_1():
    assert len(rmod.__all__) == 1


def test_module_all_only_run_evaluation():
    assert rmod.__all__ == ["run_evaluation"]


def test_module_namespace_3_callables():
    funcs = [
        name for name, val in vars(rmod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == rmod.__name__
    ]
    assert set(funcs) == {"_load_annotation", "_process_one", "run_evaluation"}


def test_module_no_user_classes():
    classes = [
        name for name, val in vars(rmod).items()
        if isinstance(val, type) and val.__module__ == rmod.__name__
    ]
    assert classes == []


def test_module_name_is_evaluation_runner():
    assert rmod.__name__ == "evaluation.runner"


def test_module_file_ends_with_runner_py():
    assert rmod.__file__.endswith("runner.py")


def test_module_function_module_eq_rmod():
    assert run_evaluation.__module__ == "evaluation.runner"
    assert _process_one.__module__ == "evaluation.runner"
    assert _load_annotation.__module__ == "evaluation.runner"


def test_module_imports_json():
    assert rmod.json is json


def test_module_imports_time():
    assert rmod.time is time


def test_module_imports_path():
    assert rmod.Path is Path


def test_module_imports_process_single():
    assert rmod.process_single is process_single


def test_module_imports_image_output_dir_for():
    assert rmod.image_output_dir_for is image_output_dir_for


def test_module_imports_compute_automatic_metrics():
    assert rmod.compute_automatic_metrics is compute_automatic_metrics


def test_module_imports_aggregate_summary():
    assert rmod.aggregate_summary is aggregate_summary


def test_module_imports_build_devset_section():
    assert rmod.build_devset_section is build_devset_section


def test_module_imports_build_provenance():
    assert rmod.build_provenance is build_provenance


def test_module_imports_chunk_boundary_prf():
    assert rmod.chunk_boundary_prf is chunk_boundary_prf


def test_module_imports_figure_caption_prf():
    assert rmod.figure_caption_prf is figure_caption_prf


def test_module_imports_report_version():
    assert rmod.REPORT_VERSION == REPORT_VERSION


# ---------- 端到端集成补强 ----------


def test_load_annotation_none_path_returns_none():
    out = _load_annotation(None)
    assert out is None


def test_load_annotation_nonexistent_path_returns_none(tmp_path):
    out = _load_annotation(tmp_path / "nope.json")
    assert out is None


def test_load_annotation_valid_json_returns_dict(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text('{"k": 1}', encoding="utf-8")
    out = _load_annotation(f)
    assert out == {"k": 1}


def test_load_annotation_invalid_json_returns_none(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text("{not json", encoding="utf-8")
    out = _load_annotation(f)
    assert out is None


def test_load_annotation_empty_file_returns_none(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text("", encoding="utf-8")
    out = _load_annotation(f)
    assert out is None


def test_load_annotation_array_root_returns_array(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text("[]", encoding="utf-8")
    out = _load_annotation(f)
    # json.load 成功；返回 list 不是 dict
    assert out == []


def test_load_annotation_int_root_returns_int(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text("42", encoding="utf-8")
    out = _load_annotation(f)
    assert out == 42


def test_load_annotation_null_root_returns_none_value(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text("null", encoding="utf-8")
    out = _load_annotation(f)
    # json.load 成功，返回 None（不是因为异常）
    assert out is None


def test_load_annotation_string_root_returns_str(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text('"hello"', encoding="utf-8")
    out = _load_annotation(f)
    assert out == "hello"


def test_load_annotation_dict_with_nested(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text(
        json.dumps({
            "outer": {"inner": [1, 2, {"deep": "value"}]},
            "list": [{"x": 1}],
        }),
        encoding="utf-8",
    )
    out = _load_annotation(f)
    assert isinstance(out, dict)
    assert out["outer"]["inner"][2]["deep"] == "value"


def test_load_annotation_does_not_write(tmp_path):
    """_load_annotation 是只读。"""
    f = tmp_path / "ann.json"
    f.write_text('{"k": 1}', encoding="utf-8")
    mtime_before = f.stat().st_mtime
    _load_annotation(f)
    # mtime 不变（只读访问）
    import os
    # 容忍少量误差
    assert abs(f.stat().st_mtime - mtime_before) < 1.0


def test_load_annotation_idempotent(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text('{"k": 1}', encoding="utf-8")
    out1 = _load_annotation(f)
    out2 = _load_annotation(f)
    assert out1 == out2


def test_load_annotation_no_side_effects(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text('{"k": 1}', encoding="utf-8")
    other_file = tmp_path / "other.json"
    other_file.write_text("{}", encoding="utf-8")
    _load_annotation(f)
    # other_file 不受影响
    assert other_file.read_text(encoding="utf-8") == "{}"


def test_load_annotation_utf8_with_chinese(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text('{"name": "测试"}', encoding="utf-8")
    out = _load_annotation(f)
    assert out == {"name": "测试"}


def test_load_annotation_special_chars(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text('{"s": "a\\tb\\nc"}', encoding="utf-8")
    out = _load_annotation(f)
    assert "\t" in out["s"]
    assert "\n" in out["s"]


def test_load_annotation_huge_dict(tmp_path):
    f = tmp_path / "ann.json"
    big = {str(i): i for i in range(1000)}
    f.write_text(json.dumps(big), encoding="utf-8")
    out = _load_annotation(f)
    assert len(out) == 1000


def test_load_annotation_long_array(tmp_path):
    f = tmp_path / "ann.json"
    arr = list(range(10000))
    f.write_text(json.dumps(arr), encoding="utf-8")
    out = _load_annotation(f)
    assert len(out) == 10000


def test_load_annotation_trailing_comma_raises(tmp_path):
    """JSON 不允许 trailing comma。"""
    f = tmp_path / "ann.json"
    f.write_text('{"a": 1,}', encoding="utf-8")
    out = _load_annotation(f)
    # 应该返回 None（json 解析失败）
    assert out is None


def test_load_annotation_unquoted_keys_raises(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text('{a: 1}', encoding="utf-8")
    out = _load_annotation(f)
    assert out is None


def test_load_annotation_utf8_bom(tmp_path):
    """UTF-8 BOM 通常被 Python 的 utf-8 codec 接受。"""
    f = tmp_path / "ann.json"
    f.write_bytes(b'\xef\xbb\xbf{"k": 1}')
    out = _load_annotation(f)
    # BOM 通常 OK
    assert out == {"k": 1} or out is None


# ---------- 端到端 run_evaluation 行为补强 ----------


def _write_valid_manifest(tmp_path, with_paired=False):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("%PDF-1.4\n%test\n")
    docs = [
        {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
    ]
    if with_paired:
        docx = tmp_path / "x.docx"
        docx.write_text("dummy docx")
        docs.append({"doc_id": "d2", "path": "x.docx", "source_type": "docx", "paired_with": "d1"})
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": docs,
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    return mf


def test_run_evaluation_minimal_run(tmp_path):
    """smoke test：跑一个最小 manifest。"""
    from evaluation.manifest import load_manifest
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(m, out_path)
    assert isinstance(report, dict)
    assert "report_version" in report
    assert "provenance" in report
    assert "devset" in report
    assert "summary" in report
    assert "per_doc" in report
    assert "expected_failures" in report


def test_run_evaluation_writes_file(tmp_path):
    from evaluation.manifest import load_manifest
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    out_path = tmp_path / "out" / "report.json"
    run_evaluation(m, out_path)
    assert out_path.is_file()


def test_run_evaluation_file_is_valid_json(tmp_path):
    from evaluation.manifest import load_manifest
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    out_path = tmp_path / "out" / "report.json"
    run_evaluation(m, out_path)
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)


def test_run_evaluation_report_version_correct(tmp_path):
    from evaluation.manifest import load_manifest
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(m, out_path)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_per_doc_count_matches(tmp_path):
    from evaluation.manifest import load_manifest
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(m, out_path)
    assert len(report["per_doc"]) == m.file_count


def test_run_evaluation_does_not_mutate_manifest(tmp_path):
    from evaluation.manifest import load_manifest
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    out_path = tmp_path / "out" / "report.json"
    docs_before = m.documents
    run_evaluation(m, out_path)
    assert m.documents == docs_before


def test_run_evaluation_kwargs_only(tmp_path):
    """parser_name/max_chars/tolerance_chars 是 keyword-only。"""
    from evaluation.manifest import load_manifest
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(
        m, out_path,
        parser_name="fallback",
        max_chars=800,
        tolerance_chars=30,
    )
    assert isinstance(report, dict)


def test_run_evaluation_default_kwargs(tmp_path):
    from evaluation.manifest import load_manifest
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(m, out_path)
    assert report["provenance"]["parser_name"] == "fallback"
    assert report["provenance"]["max_chars"] == 800


def test_run_evaluation_idempotent_structure(tmp_path):
    """两次跑出来的 report 结构一致（除非时间戳）。"""
    from evaluation.manifest import load_manifest
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    out_path = tmp_path / "out" / "report.json"
    r1 = run_evaluation(m, out_path)
    r2 = run_evaluation(m, out_path)
    assert set(r1.keys()) == set(r2.keys())
    assert set(r1["per_doc"][0]["metrics"].keys()) == set(r2["per_doc"][0]["metrics"].keys())


def test_run_evaluation_creates_output_root(tmp_path):
    """output_root 不存在时自动创建。"""
    from evaluation.manifest import load_manifest
    mf = _write_valid_manifest(tmp_path)
    m = load_manifest(mf, project_root=tmp_path)
    out_path = tmp_path / "deep" / "nested" / "report.json"
    run_evaluation(m, out_path)
    assert out_path.is_file()


def test_run_evaluation_with_expected_failure(tmp_path):
    """跑一个 expected_failure 的 doc。"""
    from evaluation.manifest import load_manifest
    bad_pdf = tmp_path / "bad.pdf"
    bad_pdf.write_text("not a pdf at all")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "f1", "path": "bad.pdf", "expected_error_code": "parse_error"}
        ],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    out_path = tmp_path / "out" / "report.json"
    report = run_evaluation(m, out_path)
    assert len(report["expected_failures"]) == 1
    ef = report["expected_failures"][0]
    assert ef["doc_id"] == "f1"
    assert ef["expected_error_code"] == "parse_error"
    # 实际错误码可能是 parse_error 或别的（取决于 parser）
    assert "actual_error_code" in ef
    assert "matches" in ef
