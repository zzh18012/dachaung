"""evaluation/runner.py 第二百轮 edges 测试（Round 712）。

补强 edges81 未触及的角度（第七十七批）。

新角度：
- 标注指标键剥离端到端（chunk_b 的 _tolerance_chars/_missing_markers 被 pop → metrics 与公共条目都不含下划线键）
- 公共 per_doc 恰 4 键（无 _annotation_present/_tolerance_chars/_missing_markers）
- tolerance_chars=77 透传（chunk_boundary 正常计算）
- 报告顶层 6 键顺序 + report_version == REPORT_VERSION == "1.1"
- ef 循环 actual=None（无 errors → matches False）/ actual 与 expected 相等 → matches True
- 源码补强（两次 metrics.update / 两个 pop 行 / _annotation_present 行 / image_base_dir 三元 / actual_code 三元 / matches 表达式 / 两次 unlink·mkdir）
- AST 补强（run_evaluation 仅关键字参数名单+默认值 / _process_one 位置参数名单 / 模块 2 次 unlink·mkdir / 两函数各 1 Try / run_evaluation 2 个 pop）
- forbidden tokens 第一百八十二批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import evaluation.runner as runner_mod
import evaluation
from evaluation.runner import run_evaluation


def _doc_stub(doc_id="d1", source_type="pdf", annotation_resolved=None):
    return SimpleNamespace(
        doc_id=doc_id, source_type=source_type, expectations=None,
        annotation_resolved=annotation_resolved, resolved_path=Path(f"{doc_id}.pdf"),
    )


def _manifest_stub(documents=(), expected_failures=(), project_root=None):
    return SimpleNamespace(
        documents=list(documents),
        expected_failures=list(expected_failures),
        project_root=project_root or Path("."),
    )


def _patch_light(monkeypatch):
    monkeypatch.setattr(runner_mod, "build_provenance",
                        lambda **kw: {"git_commit": None})
    monkeypatch.setattr(runner_mod, "build_devset_section", lambda m: {"status": "incomplete"})


# ---------- 标注键剥离端到端 ----------

def test_annotation_underscore_keys_popped_batch53(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    ann = tmp_path / "ann.json"
    ann.write_text(json.dumps({
        "chunk_boundary_anchors": [
            {"marker": "AAA", "position": "after"},
            {"marker": "ZZZ", "position": "after"},  # 找不到 → missing
        ],
    }), encoding="utf-8")
    doc_dict = {"elements": [], "chunks": [{"text": "AAA"}, {"text": "BBB"}]}
    doc = _doc_stub(annotation_resolved=ann)
    monkeypatch.setattr(runner_mod, "_process_one",
                        lambda *a, **k: (doc_dict, None, 0.1, None, None))
    report = run_evaluation(_manifest_stub(documents=[doc], project_root=tmp_path),
                            tmp_path / "r.json", tolerance_chars=77)
    entry = report["per_doc"][0]
    metrics = entry["metrics"]
    assert "_tolerance_chars" not in metrics
    assert "_missing_markers" not in metrics
    # AAA after → gt=3；pred=3；d=0 ≤ 77；ZZZ missing 不计入分母
    assert metrics["chunk_boundary_precision"]["value"] == 1.0
    assert metrics["chunk_boundary_recall"]["value"] == 1.0
    assert set(entry.keys()) == {"doc_id", "source_type", "metrics",
                                 "wall_time_seconds"}


def test_report_top_keys_order_batch53(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    report = run_evaluation(_manifest_stub(project_root=tmp_path), tmp_path / "r.json")
    assert list(report.keys()) == [
        "report_version", "provenance", "devset", "summary",
        "per_doc", "expected_failures",
    ]
    assert report["report_version"] == "1.1"
    assert report["report_version"] == evaluation.REPORT_VERSION


# ---------- ef 循环 actual_code ----------

def test_ef_no_errors_actual_none_batch53(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    monkeypatch.setattr(runner_mod, "process_single",
                        lambda *a, **k: (SimpleNamespace(doc=1), []))
    efs = [SimpleNamespace(doc_id="ef1", resolved_path=Path("b.txt"),
                           expected_error_code="x")]
    report = run_evaluation(_manifest_stub(expected_failures=efs, project_root=tmp_path),
                            tmp_path / "r.json")
    entry = report["expected_failures"][0]
    assert entry == {
        "doc_id": "ef1", "expected_error_code": "x",
        "actual_error_code": None, "matches": False,
    }


def test_ef_matching_code_batch53(monkeypatch, tmp_path):
    _patch_light(monkeypatch)
    err = SimpleNamespace(code="parse_failed")
    monkeypatch.setattr(runner_mod, "process_single",
                        lambda *a, **k: (None, [err]))
    efs = [SimpleNamespace(doc_id="ef1", resolved_path=Path("b.txt"),
                           expected_error_code="parse_failed")]
    report = run_evaluation(_manifest_stub(expected_failures=efs, project_root=tmp_path),
                            tmp_path / "r.json")
    entry = report["expected_failures"][0]
    assert entry["actual_error_code"] == "parse_failed"
    assert entry["matches"] is True


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(runner_mod)


def test_source_two_metric_updates_batch53():
    src = _src()
    assert "metrics.update(fig_caps)" in src
    assert "metrics.update(chunk_b)" in src


def test_source_two_pops_batch53():
    src = _src()
    assert 'tolerance_record = chunk_b.pop("_tolerance_chars", None)' in src
    assert 'missing_markers_record = chunk_b.pop("_missing_markers", None)' in src


def test_source_annotation_present_line_batch53():
    assert '"_annotation_present": annotation is not None,' in _src()


def test_source_image_base_dir_ternary_batch53():
    assert ("image_base_dir=image_dir if (image_dir is not None and image_dir.is_dir()) "
            "else None,") in _src()


def test_source_actual_code_and_matches_batch53():
    src = _src()
    assert "actual_code = errors[0].code if errors else None" in src
    assert '"matches": actual_code == ef.expected_error_code,' in src


def test_source_unlink_and_mkdir_twice_batch53():
    src = _src()
    assert src.count("out_stub.unlink()") == 2
    assert src.count("out_stub.parent.mkdir(parents=True, exist_ok=True)") == 2


def test_source_out_p_line_batch53():
    assert "out_p = Path(output_path)" in _src()


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(runner_mod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def test_ast_run_evaluation_kwonly_params_batch53():
    f = _func("run_evaluation")
    assert [a.arg for a in f.args.kwonlyargs] == [
        "parser_name", "max_chars", "tolerance_chars",
    ]
    assert [ast.unparse(d) for d in f.args.kw_defaults] == [
        "'fallback'", "800", "30",
    ]
    assert f.args.vararg is None  # 裸 * 分隔符（非 *args）


def test_ast_process_one_positional_params_batch53():
    f = _func("_process_one")
    assert [a.arg for a in f.args.args] == [
        "doc", "output_root", "parser_name", "max_chars",
    ]
    assert f.args.kwonlyargs == []


def test_ast_run_evaluation_two_pops_batch53():
    f = _func("run_evaluation")
    pops = [n for n in ast.walk(f)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "pop"]
    assert len(pops) == 2


def test_ast_try_one_each_function_batch53():
    assert len([n for n in ast.walk(_func("_process_one")) if isinstance(n, ast.Try)]) == 1
    assert len([n for n in ast.walk(_func("run_evaluation")) if isinstance(n, ast.Try)]) == 1


def test_ast_module_return_single_batch53():
    # __all__ 之外模块无多余顶层结构；run_evaluation 唯一 Return 在末尾
    f = _func("run_evaluation")
    rets = [n for n in ast.walk(f) if isinstance(n, ast.Return)]
    assert len(rets) == 1


# ---------- forbidden tokens 第一百八十二批 ----------

def test_source_no_eval_batch53():
    assert "eval(" not in _src()


def test_source_no_exec_batch53():
    assert "exec(" not in _src()


def test_source_no_compile_batch53():
    assert "compile(" not in _src()


def test_source_no_globals_batch53():
    assert "globals(" not in _src()


def test_source_no_locals_batch53():
    assert "locals(" not in _src()


def test_source_no_os_system_batch53():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch53():
    assert "subprocess" not in _src()


def test_source_no_popen_batch53():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch53():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch53():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch53():
    assert "socket" not in _src()


def test_source_no_requests_batch53():
    assert "requests" not in _src()


def test_source_no_urllib_batch53():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch53():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch53():
    assert "yield" not in _src()


def test_source_no_async_await_batch53():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch53():
    assert _src().count("open(") == 2
