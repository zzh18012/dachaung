"""evaluation/runner.py 第九十七轮 edges 测试（Round 691）。

补强 edges78 未触及的角度（第五十七批）。

新角度：
- run_evaluation annotation 流向（annotation_resolved 真文件 → figure/chunk prf 收 dict / None 时收 None / chunk_boundary_prf 收 tolerance_chars=77 与默认 30）
- metrics.update 覆盖顺序（fig_caps 先 / chunk_b 后 → 同名 key 由 chunk_b 覆盖）
- error 路径 compute_automatic_metrics kwargs（error dict 透传 / expectations 透传）
- expected_failures 流程细节（process_single 收 ef.resolved_path + _per_doc/{doc_id}.json + write_json=False / unlink 容错 / 多 ef 依序）
- _process_one 计时（patch perf_counter 序列 1.0→2.5 elapsed 1.5）
- _process_one image_dir 推导（image_output_dir_for 收 out_stub + document.source_hash）
- 源码补强（out_p.open("w") / json.dump 一行 3 kwargs / mkdir 出现 2 次 / image_base_dir 三元 / tolerance_record 条件 / unlink 分支 2 处）
- AST 补强（_process_one perf_counter 2 调用 / pop 顺序 / report Dict 6 keys 顺序 / kwonly 默认值 fallback-800-30 / public Dict 4 keys / 无 Assert）
- forbidden tokens 第一百六十一批
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


# ---------- 构造工具 ----------

def _doc_entry(doc_id="d1", annotation=None, expectations=None):
    d = MagicMock()
    d.doc_id = doc_id
    d.resolved_path = Path(f"{doc_id}.pdf")
    d.source_type = "pdf"
    d.annotation_resolved = annotation
    d.expectations = expectations
    return d


def _manifest(docs=(), efs=()):
    m = MagicMock()
    m.project_root = Path(".")
    m.documents = list(docs)
    m.expected_failures = list(efs)
    return m


def _ctx(cam_ret=None, fig_ret=None, cb_ret=None):
    cam = patch("evaluation.runner.compute_automatic_metrics", return_value=cam_ret if cam_ret is not None else {})
    fig = patch("evaluation.runner.figure_caption_prf", return_value=fig_ret if fig_ret is not None else {})
    cb = patch("evaluation.runner.chunk_boundary_prf", return_value=cb_ret if cb_ret is not None else {})
    bp = patch("evaluation.runner.build_provenance", return_value={})
    bd = patch("evaluation.runner.build_devset_section", return_value={})
    ag = patch("evaluation.runner.aggregate_summary", return_value={})
    po = patch("evaluation.runner._process_one", return_value=({"a": 1}, None, 0.1, "1.0", None))
    return [po, cam, fig, cb, bp, bd, ag]


def _run_with_ctx(m, out, **kw):
    ctx = _ctx()
    with ctx[0], ctx[1], ctx[2], ctx[3], ctx[4], ctx[5], ctx[6]:
        return run_evaluation(m, out, **kw), ctx


# ---------- run_evaluation annotation 流向 ----------

def test_annotation_file_loaded_and_passed_batch52(tmp_path):
    ann_file = tmp_path / "d1.ann.json"
    ann_file.write_text(json.dumps({"chunk_boundary_anchors": []}), encoding="utf-8")
    m = _manifest(docs=[_doc_entry(annotation=ann_file)])
    with patch("evaluation.runner._process_one", return_value=({"a": 1}, None, 0.1, "1.0", None)), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}) as cam, \
         patch("evaluation.runner.figure_caption_prf", return_value={}) as fig, \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}) as cb, \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        run_evaluation(m, tmp_path / "out.json")
    passed_ann = fig.call_args.args[1]
    assert passed_ann == {"chunk_boundary_anchors": []}
    assert cb.call_args.args[1] == {"chunk_boundary_anchors": []}
    assert cam.call_args.kwargs["document"] == {"a": 1}


def test_annotation_none_passed_through_batch52(tmp_path):
    m = _manifest(docs=[_doc_entry(annotation=None)])
    with patch("evaluation.runner._process_one", return_value=({"a": 1}, None, 0.1, "1.0", None)), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}) as fig, \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}) as cb, \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        run_evaluation(m, tmp_path / "out.json")
    assert fig.call_args.args[1] is None
    assert cb.call_args.args[1] is None


def test_annotation_bad_file_becomes_none_batch52(tmp_path):
    """annotation 文件损坏 → _load_annotation None → 传 None。"""
    ann_file = tmp_path / "bad.json"
    ann_file.write_text("not json", encoding="utf-8")
    m = _manifest(docs=[_doc_entry(annotation=ann_file)])
    with patch("evaluation.runner._process_one", return_value=({"a": 1}, None, 0.1, "1.0", None)), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}) as fig, \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        run_evaluation(m, tmp_path / "out.json")
    assert fig.call_args.args[1] is None


def test_chunk_boundary_receives_tolerance_batch52(tmp_path):
    m = _manifest(docs=[_doc_entry()])
    with patch("evaluation.runner._process_one", return_value=({"a": 1}, None, 0.1, "1.0", None)), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}) as cb, \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        run_evaluation(m, tmp_path / "out.json", tolerance_chars=77)
    assert cb.call_args.kwargs["tolerance_chars"] == 77


def test_chunk_boundary_default_tolerance_30_batch52(tmp_path):
    m = _manifest(docs=[_doc_entry()])
    with patch("evaluation.runner._process_one", return_value=({"a": 1}, None, 0.1, "1.0", None)), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}) as cb, \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        run_evaluation(m, tmp_path / "out.json")
    assert cb.call_args.kwargs["tolerance_chars"] == 30


# ---------- metrics.update 覆盖顺序 ----------

def test_metrics_update_chunk_b_overrides_batch52(tmp_path):
    m = _manifest(docs=[_doc_entry()])
    fig_ret = {"shared": {"value": "from_fig"}}
    cb_ret = {"shared": {"value": "from_cb", "reason": None}}
    with patch("evaluation.runner._process_one", return_value=({"a": 1}, None, 0.1, "1.0", None)), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}), \
         patch("evaluation.runner.figure_caption_prf", return_value=fig_ret), \
         patch("evaluation.runner.chunk_boundary_prf", return_value=cb_ret), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        report = run_evaluation(m, tmp_path / "out.json")
    assert report["per_doc"][0]["metrics"]["shared"]["value"] == "from_cb"


def test_metrics_merge_three_sources_batch52(tmp_path):
    m = _manifest(docs=[_doc_entry()])
    with patch("evaluation.runner._process_one", return_value=({"a": 1}, None, 0.1, "1.0", None)), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={"m1": 1}) as cam, \
         patch("evaluation.runner.figure_caption_prf", return_value={"m2": 2}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={"m3": 3}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        report = run_evaluation(m, tmp_path / "out.json")
    keys = set(report["per_doc"][0]["metrics"].keys())
    assert keys == {"m1", "m2", "m3"}


# ---------- compute_automatic_metrics kwargs ----------

def test_compute_metrics_receives_error_dict_batch52(tmp_path):
    err = {"code": "unsupported_format", "message": "x"}
    m = _manifest(docs=[_doc_entry(expectations={"e": 1})])
    with patch("evaluation.runner._process_one", return_value=(None, err, 0.1, None, None)), \
         patch("evaluation.runner.compute_automatic_metrics", return_value={}) as cam, \
         patch("evaluation.runner.figure_caption_prf", return_value={}), \
         patch("evaluation.runner.chunk_boundary_prf", return_value={}), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        run_evaluation(m, tmp_path / "out.json")
    kw = cam.call_args.kwargs
    assert kw["document"] is None
    assert kw["error"] == err
    assert kw["expectations"] == {"e": 1}
    assert kw["source_type"] == "pdf"


# ---------- expected_failures 流程细节 ----------

def test_ef_process_single_call_args_batch52(tmp_path):
    ef = MagicMock()
    ef.doc_id = "efx"
    ef.resolved_path = Path("bad.pdf")
    ef.expected_error_code = "unsupported_format"
    m = _manifest(efs=[ef])
    err = MagicMock()
    err.code = "unsupported_format"
    with patch("evaluation.runner.process_single", return_value=(None, [err])) as ps, \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        run_evaluation(m, tmp_path / "out.json")
    call = ps.call_args
    assert call.args[0] == Path("bad.pdf")
    assert call.args[1] == tmp_path / "_per_doc" / "efx.json"
    assert call.kwargs == {"parser_name": "fallback", "max_chars": 800, "write_json": False}


def test_ef_unlink_oserror_tolerated_batch52(tmp_path):
    ef = MagicMock()
    ef.doc_id = "efx"
    ef.resolved_path = Path("bad.pdf")
    ef.expected_error_code = "x"
    m = _manifest(efs=[ef])
    err = MagicMock()
    err.code = "x"
    with patch("evaluation.runner.process_single", return_value=(None, [err])), \
         patch("evaluation.runner.Path.is_file", return_value=True), \
         patch("evaluation.runner.Path.unlink", side_effect=OSError("locked")), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        report = run_evaluation(m, tmp_path / "out.json")
    assert report["expected_failures"][0]["matches"] is True


def test_ef_multiple_sequential_batch52(tmp_path):
    efs = []
    for i in range(3):
        ef = MagicMock()
        ef.doc_id = f"ef{i}"
        ef.resolved_path = Path(f"bad{i}.pdf")
        ef.expected_error_code = "code_a"
        efs.append(ef)
    m = _manifest(efs=efs)
    err = MagicMock()
    err.code = "code_b"
    with patch("evaluation.runner.process_single", return_value=(None, [err])) as ps, \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        report = run_evaluation(m, tmp_path / "out.json")
    assert ps.call_count == 3
    assert [r["doc_id"] for r in report["expected_failures"]] == ["ef0", "ef1", "ef2"]
    assert all(r["matches"] is False for r in report["expected_failures"])


def test_ef_creates_per_doc_dir_batch52(tmp_path):
    ef = MagicMock()
    ef.doc_id = "efx"
    ef.resolved_path = Path("bad.pdf")
    ef.expected_error_code = "x"
    m = _manifest(efs=[ef])
    with patch("evaluation.runner.process_single", return_value=(None, [])), \
         patch("evaluation.runner.build_provenance", return_value={}), \
         patch("evaluation.runner.build_devset_section", return_value={}), \
         patch("evaluation.runner.aggregate_summary", return_value={}):
        run_evaluation(m, tmp_path / "out.json")
    assert (tmp_path / "_per_doc").is_dir()


# ---------- _process_one 计时 ----------

def test_process_one_elapsed_from_perf_counter_batch52(tmp_path):
    with patch("evaluation.runner.process_single", return_value=(None, [])), \
         patch("evaluation.runner.time.perf_counter", side_effect=[1.0, 2.5]):
        doc, err, elapsed, pv, img = _process_one(_doc_entry(), tmp_path, "fallback", 800)
    assert elapsed == pytest.approx(1.5)


def test_process_one_perf_counter_called_twice_batch52(tmp_path):
    with patch("evaluation.runner.process_single", return_value=(None, [])), \
         patch("evaluation.runner.time.perf_counter", side_effect=[0, 0]) as pc:
        _process_one(_doc_entry(), tmp_path, "fallback", 800)
    assert pc.call_count == 2


# ---------- _process_one image_dir 推导 ----------

def test_process_one_image_dir_args_batch52(tmp_path):
    document = MagicMock()
    document.to_dict.return_value = {"a": 1}
    document.parser_version = "v"
    document.source_hash = "sha123"
    with patch("evaluation.runner.process_single", return_value=(document, [])), \
         patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "i") as iodf:
        _process_one(_doc_entry(doc_id="mydoc"), tmp_path, "fallback", 800)
    args = iodf.call_args.args
    assert args[0] == tmp_path / "_per_doc" / "mydoc.json"
    assert args[1] == "sha123"


# ---------- 源码补强 ----------

def test_source_out_p_open_write_batch52():
    src = inspect.getsource(runner_mod)
    assert 'out_p.open("w", encoding="utf-8")' in src


def test_source_json_dump_one_line_batch52():
    src = inspect.getsource(runner_mod)
    assert "json.dump(report, f, ensure_ascii=False, indent=2)" in src


def test_source_mkdir_4_sites_batch52():
    """_process_one 1 + ef 循环 1 + output_root 1 + out_p.parent 1 = 4。"""
    src = inspect.getsource(runner_mod)
    assert src.count(".mkdir(parents=True, exist_ok=True)") == 4


def test_source_image_base_dir_conditional_batch52():
    src = inspect.getsource(runner_mod)
    assert "image_dir if (image_dir is not None and image_dir.is_dir()) else None" in src


def test_source_tolerance_record_conditional_batch52():
    src = inspect.getsource(runner_mod)
    assert 'tolerance_record["value"] if tolerance_record else None' in src


def test_source_missing_markers_conditional_batch52():
    src = inspect.getsource(runner_mod)
    assert "missing_markers_record[\"value\"]" in src
    assert "if missing_markers_record" in src


def test_source_unlink_branches_batch52():
    src = inspect.getsource(runner_mod)
    assert src.count("out_stub.unlink()") == 2


def test_source_doc_annotation_flow_batch52():
    src = inspect.getsource(runner_mod)
    assert "annotation = _load_annotation(doc.annotation_resolved)" in src


def test_source_fig_caps_before_chunk_b_batch52():
    src = inspect.getsource(runner_mod)
    assert src.index("fig_caps = figure_caption_prf") < src.index("chunk_b = chunk_boundary_prf")


# ---------- AST 补强 ----------

def test_ast_process_one_2_perf_counter_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "perf_counter"
    ]
    assert len(calls) == 2


def test_ast_pop_order_tolerance_first_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    src = ast.unparse(func)
    assert src.index("pop('_tolerance_chars'") < src.index("pop('_missing_markers'")


def test_ast_report_dict_key_order_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    report_assign = next(
        n for n in func.body
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict)
        and any(isinstance(k, ast.Constant) and k.value == "report_version" for k in n.value.keys)
    )
    keys = [k.value for k in report_assign.value.keys]
    assert keys == ["report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"]


def test_ast_kwonly_defaults_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    defaults = [d.value for d in func.args.kw_defaults if d is not None]
    assert defaults == ["fallback", 800, 30]


def test_ast_public_per_doc_4_keys_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    dicts = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Dict) and n.keys
        and all(isinstance(k, ast.Constant) for k in n.keys)
        and any(k.value == "wall_time_seconds" for k in n.keys)
        and len(n.keys) == 4
    ]
    assert len(dicts) >= 1


def test_ast_no_assert_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.Assert) for n in ast.walk(tree))


def test_ast_ef_loop_before_provenance_batch52():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    src = ast.unparse(func)
    assert src.index("for ef in manifest.expected_failures") < src.index("provenance = build_provenance")


# ---------- forbidden tokens 第一百六十一批 ----------

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
    assert _src().count("open(") == 2
