"""evaluation/cli.py 第五十一轮 edges 测试（Round 480）。

补强 edges49 未触及的角度：
- _build_parser 第二十三批（formatter_class / run 子 parser add_argument 类型 / inspect-doc 默认 / 缺 --manifest 错误 / 缺 --output 错误 / --parser choices / prog / run_p 与 val_p 与 ins_p 帮助字符串 / inspect-doc 子 parser type=int）
- _format_metric 第二十三批（None 值 / bool True / bool False + reason / float + reason None / dict 多 key 排序 / dict 单 key / int 0 / 负数 / str value）
- _run_inspect_doc 第二十三批（带 chunks 字段 / 自定义 tolerance / chunk_boundary_prf 透传 / figure_caption_prf 调用 / compute_automatic_metrics 调用 / metrics 排序输出 / 元信息行）
- main 第二十三批（run 成功路径打印 OK / validate-report 成功路径 / run FileNotFoundError 处理 / inspect-doc 整合 main / run 无 per_doc / --tolerance-chars 透传 / --max-chars 透传）
- module source forbidden tokens 第三十九批
- module source 字符串精确补强第三十五批
- signatures 第三十五批
- module 合理性第三十五批
- 端到端集成第三十五批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main
from evaluation import cli as climod


# ---------- _build_parser 第二十三批 ----------


def _get_subparsers(parser):
    """从主 parser 找到 subparsers action。"""
    for action in parser._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            return action
    return None


def test_build_parser_main_formatter_class_batch23():
    """主 parser formatter_class=RawDescriptionHelpFormatter。"""
    p = _build_parser()
    assert p.formatter_class is __import__("argparse").RawDescriptionHelpFormatter


def test_build_parser_run_parser_choices_fallback_kreuzberg_batch23():
    """--parser choices 严格 (fallback, kreuzberg)。"""
    p = _build_parser()
    args_ok = p.parse_args(["run", "--manifest", "a", "--output", "b", "--parser", "fallback"])
    args_ok2 = p.parse_args(["run", "--manifest", "a", "--output", "b", "--parser", "kreuzberg"])
    assert args_ok.parser == "fallback"
    assert args_ok2.parser == "kreuzberg"


def test_build_parser_max_chars_type_int_batch23():
    """--max-chars type=int（字符串 → int 转换）。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a", "--output", "b", "--max-chars", "1234"])
    assert args.max_chars == 1234
    assert isinstance(args.max_chars, int)


def test_build_parser_tolerance_chars_type_int_batch23():
    """--tolerance-chars type=int。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "a", "--output", "b", "--tolerance-chars", "55"])
    assert args.tolerance_chars == 55
    assert isinstance(args.tolerance_chars, int)


def test_build_parser_run_manifest_required_batch23():
    """run 缺 --manifest → SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--output", "b"])


def test_build_parser_run_output_required_batch23():
    """run 缺 --output → SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["run", "--manifest", "a"])


def test_build_parser_validate_report_takes_one_positional_batch23():
    """validate-report 接 1 个 positional。"""
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"
    assert args.command == "validate-report"


def test_build_parser_inspect_doc_takes_one_positional_batch23():
    """inspect-doc 接 1 个 positional。"""
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.input == "doc.json"
    assert args.command == "inspect-doc"


def test_build_parser_inspect_doc_tolerance_chars_type_int_batch23():
    """inspect-doc --tolerance-chars type=int。"""
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "100"])
    assert args.tolerance_chars == 100


def test_build_parser_run_has_description_batch23():
    """主 parser 有 description。"""
    p = _build_parser()
    assert p.description is not None
    assert len(p.description) > 0


def test_build_parser_subparser_run_help_text_batch23():
    """run 子 parser 有 description 或 help。"""
    p = _build_parser()
    sub = _get_subparsers(p)
    run_p = sub.choices["run"]
    # run 子 parser 描述（add_parser 第一个位置参数会进 prog，描述从 description 字段取）
    assert run_p.description is not None or run_p.prog.endswith("run")


def test_build_parser_run_parser_add_argument_count_batch23():
    """run 子 parser 严格 5 个 non-help actions：manifest, output, parser, max_chars, tolerance_chars。"""
    p = _build_parser()
    sub = _get_subparsers(p)
    run_p = sub.choices["run"]
    real_actions = [a for a in run_p._actions if a.dest != "help"]
    dests = {a.dest for a in real_actions}
    assert dests == {"manifest", "output", "parser", "max_chars", "tolerance_chars"}


# ---------- _format_metric 第二十三批 ----------


def test_format_metric_value_none_renders_null_batch23():
    """value=None → null 字面。"""
    out = _format_metric("x", {"value": None, "reason": "missing"})
    assert "null" in out
    assert "(missing)" in out


def test_format_metric_value_true_bool_batch23():
    """value=True → 'true'。"""
    out = _format_metric("flag", {"value": True, "reason": None})
    assert "true" in out


def test_format_metric_value_false_no_reason_batch23():
    """value=False + reason=None → 'false' + (ok)。"""
    out = _format_metric("flag", {"value": False, "reason": None})
    assert "false" in out
    assert "(ok)" in out


def test_format_metric_value_negative_float_batch23():
    """value=-0.5 → '-0.5000'。"""
    out = _format_metric("delta", {"value": -0.5, "reason": None})
    assert "-0.5000" in out


def test_format_metric_value_int_zero_batch23():
    """value=0 (int) → 走 default 分支，输出 0。"""
    out = _format_metric("count", {"value": 0, "reason": None})
    # int 0 走 default 分支，不被识别为 bool
    assert "0" in out
    assert "(ok)" in out


def test_format_metric_value_dict_multi_key_sorted_batch23():
    """value=dict 多 key → 按 key 排序。"""
    out = _format_metric("counts", {"value": {"b": 2, "a": 1, "c": 3}, "reason": None})
    assert "a=1" in out
    assert "b=2" in out
    assert "c=3" in out
    # a 在 b 之前
    assert out.find("a=1") < out.find("b=2") < out.find("c=3")


def test_format_metric_value_string_batch23():
    """value 是 str。"""
    out = _format_metric("msg", {"value": "hello", "reason": None})
    assert "hello" in out


def test_format_metric_value_negative_int_batch23():
    """value 负 int。"""
    out = _format_metric("delta", {"value": -42, "reason": None})
    assert "-42" in out


def test_format_metric_value_dict_with_none_value_batch23():
    """value 是 dict 含 None value。"""
    out = _format_metric("x", {"value": {"a": None}, "reason": None})
    assert "a=None" in out


def test_format_metric_value_dict_with_bool_value_batch23():
    """value 是 dict 含 bool。"""
    out = _format_metric("x", {"value": {"a": True}, "reason": None})
    assert "a=True" in out


# ---------- _run_inspect_doc 第二十三批 ----------


def _write_doc(tmp_path, doc=None, name="d.json"):
    p = tmp_path / name
    if doc is None:
        doc = {
            "document_id": "d1",
            "source_type": "pdf",
            "elements": [],
            "chunks": [],
        }
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def test_run_inspect_doc_with_chunks_batch23(tmp_path, capsys):
    """有 chunks → counts 行 chunks=N。"""
    p = _write_doc(tmp_path, doc={
        "document_id": "d",
        "source_type": "pdf",
        "elements": [{"id": "e1"}],
        "chunks": [{"chunk_id": "c1"}, {"chunk_id": "c2"}, {"chunk_id": "c3"}, {"chunk_id": "c4"}],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "elements=1" in captured
    assert "chunks=4" in captured


def test_run_inspect_doc_file_path_in_output_batch23(tmp_path, capsys):
    """打印输入文件路径。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert str(p) in captured


def test_run_inspect_doc_document_id_in_output_batch23(tmp_path, capsys):
    """打印 document_id。"""
    p = _write_doc(tmp_path, doc={
        "document_id": "abc-123",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "abc-123" in captured


def test_run_inspect_doc_source_type_in_output_batch23(tmp_path, capsys):
    """打印 source_type。"""
    p = _write_doc(tmp_path, doc={
        "document_id": "d",
        "source_type": "docx",
        "elements": [],
        "chunks": [],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "type=docx" in captured


def test_run_inspect_doc_parser_info_in_output_batch23(tmp_path, capsys):
    """打印 parser name + version。"""
    p = _write_doc(tmp_path, doc={
        "document_id": "d",
        "source_type": "pdf",
        "parser_name": "fallback",
        "parser_version": "1.2.3",
        "elements": [],
        "chunks": [],
    })
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert "fallback" in captured
    assert "1.2.3" in captured


def test_run_inspect_doc_calls_compute_automatic_metrics_batch23(tmp_path):
    """compute_automatic_metrics 被调用。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}) as mock_metrics:
        _run_inspect_doc(args)
    assert mock_metrics.called


def test_run_inspect_doc_calls_figure_caption_prf_batch23(tmp_path):
    """figure_caption_prf 被调用。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}):
        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}) as mock_fig:
            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
                _run_inspect_doc(args)
    assert mock_fig.called


def test_run_inspect_doc_metrics_sorted_bool_first_batch23(tmp_path, capsys):
    """bool metrics 排在 numbers 之前。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    fake_metrics = {"z_num": {"value": 1.0, "reason": None}, "a_bool": {"value": True, "reason": None}}
    with patch("evaluation.metrics.compute_automatic_metrics", return_value=fake_metrics):
        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
                _run_inspect_doc(args)
    captured = capsys.readouterr().out
    # a_bool 应在 z_num 之前
    assert captured.find("a_bool") < captured.find("z_num")


def test_run_inspect_doc_metrics_null_last_batch23(tmp_path, capsys):
    """null metrics 排在最后。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    fake_metrics = {
        "z_null": {"value": None, "reason": "x"},
        "a_num": {"value": 1.0, "reason": None},
    }
    with patch("evaluation.metrics.compute_automatic_metrics", return_value=fake_metrics):
        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
                _run_inspect_doc(args)
    captured = capsys.readouterr().out
    # a_num 在 z_null 之前
    assert captured.find("a_num") < captured.find("z_null")


def test_run_inspect_doc_metrics_str_middle_batch23(tmp_path, capsys):
    """str value metrics 排在 numbers 之后 nulls 之前。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    fake_metrics = {
        "z_null": {"value": None, "reason": "x"},
        "m_str": {"value": "abc", "reason": None},
        "a_num": {"value": 1.0, "reason": None},
    }
    with patch("evaluation.metrics.compute_automatic_metrics", return_value=fake_metrics):
        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
                _run_inspect_doc(args)
    captured = capsys.readouterr().out
    assert captured.find("a_num") < captured.find("m_str") < captured.find("z_null")


def test_run_inspect_doc_returns_zero_on_success_batch23(tmp_path):
    """成功跑 → rc=0。"""
    p = _write_doc(tmp_path)
    args = MagicMock()
    args.input = str(p)
    args.tolerance_chars = 30
    rc = _run_inspect_doc(args)
    assert rc == 0


# ---------- main 第二十三批 ----------


def _make_manifest_file(tmp_path, docs=None):
    p = tmp_path / "manifest.json"
    payload = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": docs or [],
    }
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_main_run_success_prints_ok_batch23(tmp_path, capsys):
    """成功 run 打印 [OK]。"""
    manifest_p = _make_manifest_file(tmp_path)
    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }
    with patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=tmp_path)):
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    rc = main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    captured = capsys.readouterr().out
    assert rc == 0
    assert "[OK]" in captured


def test_main_run_prints_devset_info_batch23(tmp_path, capsys):
    """成功 run 打印 devset_status / file_count / 等。"""
    manifest_p = _make_manifest_file(tmp_path)
    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {"status": "incomplete", "file_count": 5, "content_group_count": 2, "pdf_count": 3, "docx_count": 2, "categories_covered": []},
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }
    with patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=tmp_path)):
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": True}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    captured = capsys.readouterr().out
    assert "devset_status=incomplete" in captured
    assert "file_count=5" in captured
    assert "groups=2" in captured
    assert "pdf=3" in captured
    assert "docx=2" in captured
    assert "git_dirty=True" in captured


def test_main_validate_report_success_prints_ok_batch23(tmp_path, capsys):
    """validate-report 成功 → [OK]。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", return_value=None):
        rc = main(["validate-report", str(p)])
    captured = capsys.readouterr().out
    assert rc == 0
    assert "[OK]" in captured
    assert str(p) in captured


def test_main_validate_report_file_not_found_returns_2_batch23(tmp_path, capsys):
    """validate-report 抛 FileNotFoundError → rc=2。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file", side_effect=FileNotFoundError("schema not found")):
        rc = main(["validate-report", str(p)])
    err = capsys.readouterr().err
    assert rc == 2
    assert "[ERROR]" in err


def test_main_run_max_chars_passed_to_run_evaluation_batch23(tmp_path):
    """--max-chars 透传。"""
    manifest_p = _make_manifest_file(tmp_path)
    captured = {}

    def fake_run(manifest, output_path, **kwargs):
        captured.update(kwargs)
        return {
            "report_version": "1.1", "provenance": {},
            "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
            "summary": {}, "per_doc": [], "expected_failures": [],
        }

    with patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=tmp_path)):
        with patch("evaluation.cli.run_evaluation", side_effect=fake_run):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    main(["run", "--manifest", str(manifest_p), "--output", str(out_p),
                          "--max-chars", "1500"])
    assert captured["max_chars"] == 1500


def test_main_run_tolerance_chars_passed_to_run_evaluation_batch23(tmp_path):
    """--tolerance-chars 透传。"""
    manifest_p = _make_manifest_file(tmp_path)
    captured = {}

    def fake_run(manifest, output_path, **kwargs):
        captured.update(kwargs)
        return {
            "report_version": "1.1", "provenance": {},
            "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
            "summary": {}, "per_doc": [], "expected_failures": [],
        }

    with patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=tmp_path)):
        with patch("evaluation.cli.run_evaluation", side_effect=fake_run):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    main(["run", "--manifest", str(manifest_p), "--output", str(out_p),
                          "--tolerance-chars", "99"])
    assert captured["tolerance_chars"] == 99


def test_main_run_manifest_load_manifest_error_returns_1_batch23(tmp_path, capsys):
    """load_manifest 抛 ManifestError → rc=1。"""
    from evaluation.manifest import ManifestError

    manifest_p = _make_manifest_file(tmp_path)
    with patch("evaluation.cli.load_manifest", side_effect=ManifestError("bad manifest")):
        rc = main(["run", "--manifest", str(manifest_p), "--output", str(tmp_path / "o.json")])
    err = capsys.readouterr().err
    assert rc == 1
    assert "[ERROR]" in err
    assert "清单加载失败" in err


def test_main_run_manifest_eval_schema_error_returns_1_batch23(tmp_path, capsys):
    """load_manifest 抛 EvalSchemaError → rc=1。"""
    from evaluation.schema import EvalSchemaError

    manifest_p = _make_manifest_file(tmp_path)
    with patch("evaluation.cli.load_manifest", side_effect=EvalSchemaError("schema bad")):
        rc = main(["run", "--manifest", str(manifest_p), "--output", str(tmp_path / "o.json")])
    err = capsys.readouterr().err
    assert rc == 1


def test_main_run_zero_documents_batch23(tmp_path, capsys):
    """0 documents 也能跑通。"""
    manifest_p = _make_manifest_file(tmp_path)
    fake_report = {
        "report_version": "1.1", "provenance": {},
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
        "summary": {}, "per_doc": [], "expected_failures": [],
    }
    with patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=tmp_path)):
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    captured = capsys.readouterr().out
    assert "documents=0" in captured
    assert "成功 0" in captured
    assert "失败 0" in captured


def test_main_run_inspect_doc_via_main_batch23(tmp_path, capsys):
    """main(['inspect-doc', x]) 路由到 _run_inspect_doc。"""
    p = _write_doc(tmp_path)
    rc = main(["inspect-doc", str(p)])
    captured = capsys.readouterr().out
    assert rc == 0
    assert "metrics:" in captured


def test_main_run_inspect_doc_with_tolerance_via_main_batch23(tmp_path, capsys):
    """main inspect-doc --tolerance-chars 透传。"""
    p = _write_doc(tmp_path)
    captured = {}

    def fake_chunk_b(document, annotation, tolerance_chars=30):
        captured["tolerance_chars"] = tolerance_chars
        return {}

    with patch("evaluation.annotation_metrics.chunk_boundary_prf", side_effect=fake_chunk_b):
        rc = main(["inspect-doc", str(p), "--tolerance-chars", "200"])
    assert rc == 0
    assert captured["tolerance_chars"] == 200


def test_main_run_unknown_command_returns_2_batch23():
    """未知 command（应该不会发生因 argparse 拒）—— 跳过测试用 argparse 拦截。"""
    # argparse 在 _build_parser 阶段就拒绝未知 command → SystemExit
    # main 函数末尾的 return 2 是 unreachable
    # 这里只验证未知 subcommand → SystemExit
    with pytest.raises(SystemExit):
        main(["unknown"])


def test_main_validate_report_json_decode_via_real_file_batch23(tmp_path, capsys):
    """validate-report 真实非法 JSON 文件（不 mock）→ rc=1。"""
    p = tmp_path / "report.json"
    p.write_text("not json at all", encoding="utf-8")
    # 不 patch validate_file，让它真实跑
    rc = main(["validate-report", str(p)])
    err = capsys.readouterr().err
    # 真实 validate_file 会抛 JSONDecodeError 或 EvalSchemaError
    assert rc in (1, 2)


# ---------- module source forbidden tokens 第三十九批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.check_output",
    "subprocess.check_call",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    'open("/etc/passwd',
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch23(forbidden):
    src = inspect.getsource(climod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch23():
    src = inspect.getsource(climod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch23():
    src = inspect.getsource(climod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch23():
    src = inspect.getsource(climod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch23():
    src = inspect.getsource(climod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch23():
    src = inspect.getsource(climod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch23():
    src = inspect.getsource(climod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch23():
    src = inspect.getsource(climod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch23():
    src = inspect.getsource(climod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch23():
    src = inspect.getsource(climod)
    assert "import tempfile" not in src


def test_module_source_no_logging_import_batch23():
    src = inspect.getsource(climod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch23():
    src = inspect.getsource(climod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch23():
    src = inspect.getsource(climod)
    assert "import datetime" not in src


def test_module_source_no_collections_import_batch23():
    src = inspect.getsource(climod)
    assert "import collections" not in src


def test_module_source_no_pandas_import_batch23():
    src = inspect.getsource(climod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch23():
    src = inspect.getsource(climod)
    assert "import numpy" not in src


def test_module_source_no_csv_import_batch23():
    src = inspect.getsource(climod)
    assert "import csv" not in src


# ---------- module source 字符串精确补强第三十五批 ----------


def test_module_source_has_future_annotations_batch23():
    src = inspect.getsource(climod)
    assert "from __future__ import annotations" in src


def test_module_source_has_argparse_import_batch23():
    src = inspect.getsource(climod)
    assert "import argparse" in src


def test_module_source_has_json_import_batch23():
    src = inspect.getsource(climod)
    assert "import json" in src


def test_module_source_has_sys_import_batch23():
    src = inspect.getsource(climod)
    assert "import sys" in src


def test_module_source_has_pathlib_path_import_batch23():
    src = inspect.getsource(climod)
    assert "from pathlib import Path" in src


def test_module_source_has_manifest_import_batch23():
    src = inspect.getsource(climod)
    assert "from evaluation.manifest import ManifestError, load_manifest" in src


def test_module_source_has_report_import_batch23():
    src = inspect.getsource(climod)
    assert "from evaluation.report import get_git_provenance" in src


def test_module_source_has_runner_import_batch23():
    src = inspect.getsource(climod)
    assert "from evaluation.runner import run_evaluation" in src


def test_module_source_has_schema_import_batch23():
    src = inspect.getsource(climod)
    assert "from evaluation.schema import EvalSchemaError, validate_file" in src


def test_module_source_has_main_function_batch23():
    src = inspect.getsource(climod)
    assert "def main(argv:" in src


def test_module_source_has_build_parser_function_batch23():
    src = inspect.getsource(climod)
    assert "def _build_parser()" in src


def test_module_source_has_format_metric_function_batch23():
    src = inspect.getsource(climod)
    assert "def _format_metric(" in src


def test_module_source_has_run_inspect_doc_function_batch23():
    src = inspect.getsource(climod)
    assert "def _run_inspect_doc(" in src


def test_module_source_has_main_guard_batch23():
    src = inspect.getsource(climod)
    assert 'if __name__ ==' in src
    assert "__main__" in src


def test_module_source_has_raw_description_help_formatter_batch23():
    src = inspect.getsource(climod)
    assert "RawDescriptionHelpFormatter" in src


# ---------- signatures 第三十五批 ----------


def test_signature_build_parser_no_args_batch23():
    sig = inspect.signature(_build_parser)
    params = list(sig.parameters.values())
    assert len(params) == 0


def test_signature_main_argv_default_none_batch23():
    sig = inspect.signature(main)
    p = sig.parameters["argv"]
    assert p.default is None


def test_signature_main_returns_int_annotation_batch23():
    sig = inspect.signature(main)
    assert "int" in str(sig.return_annotation)


def test_signature_format_metric_params_batch23():
    sig = inspect.signature(_format_metric)
    names = list(sig.parameters.keys())
    assert names == ["name", "metric"]


def test_signature_format_metric_returns_str_batch23():
    sig = inspect.signature(_format_metric)
    assert "str" in str(sig.return_annotation)


def test_signature_run_inspect_doc_params_batch23():
    sig = inspect.signature(_run_inspect_doc)
    names = list(sig.parameters.keys())
    assert names == ["args"]


def test_signature_run_inspect_doc_returns_int_annotation_batch23():
    sig = inspect.signature(_run_inspect_doc)
    assert "int" in str(sig.return_annotation)


def test_signature_main_argv_annotation_is_list_str_or_none_batch23():
    sig = inspect.signature(main)
    ann = sig.parameters["argv"].annotation
    assert "list" in ann or "None" in ann


# ---------- module 合理性第三十五批 ----------


def test_module_does_not_import_evaluation_runner_top_level_side_effect_batch23():
    """import evaluation.runner 在顶层。"""
    src = inspect.getsource(climod)
    lines = src.splitlines()
    found_top_level = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("from evaluation.runner import") and line[0] != " ":
            found_top_level = True
            break
    assert found_top_level


def test_module_does_not_import_evaluation_metrics_top_level_batch23():
    """evaluation.metrics 仅在 _run_inspect_doc 内部 import。"""
    src = inspect.getsource(climod)
    lines = src.splitlines()
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("from evaluation.metrics import") and line[0] != " ":
            pytest.fail("evaluation.metrics 不应在顶层 import")
        if stripped.startswith("from evaluation.metrics import") and line[0] == " ":
            return  # OK: 在函数内
    # 也允许完全没有这个 import


def test_module_does_not_import_evaluation_annotation_metrics_top_level_batch23():
    """evaluation.annotation_metrics 仅在 _run_inspect_doc 内部 import。"""
    src = inspect.getsource(climod)
    lines = src.splitlines()
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("from evaluation.annotation_metrics import") and line[0] != " ":
            pytest.fail("evaluation.annotation_metrics 不应在顶层 import")


def test_module_does_not_import_app_pipeline_batch23():
    src = inspect.getsource(climod)
    assert "from app.pipeline" not in src
    assert "from app import pipeline" not in src


def test_module_does_not_import_app_chunkers_batch23():
    src = inspect.getsource(climod)
    assert "from app.chunkers" not in src
    assert "from app import chunkers" not in src


def test_module_does_not_import_app_parsers_batch23():
    src = inspect.getsource(climod)
    assert "from app.parsers" not in src
    assert "from app import parsers" not in src


def test_module_constants_not_exposed_batch23():
    """FORBIDDEN / private 常量不应被 export。"""
    assert not hasattr(climod, "FORBIDDEN_TOKENS")


def test_module_has_module_docstring_batch23():
    assert climod.__doc__ is not None
    assert len(climod.__doc__) > 0


def test_module_run_inspect_doc_is_private_batch23():
    assert _run_inspect_doc.__name__.startswith("_")


def test_module_build_parser_is_private_batch23():
    assert _build_parser.__name__.startswith("_")


def test_module_format_metric_is_private_batch23():
    assert _format_metric.__name__.startswith("_")


def test_module_main_is_public_batch23():
    assert not main.__name__.startswith("_")


# ---------- 端到端集成第三十五批 ----------


def test_e2e_main_validate_report_round_trip_batch23(tmp_path, capsys):
    """真实跑 validate-report 在合法 schema 文件上。"""
    # 用一个真实的最小有效报告（schema 是 evaluation-report.schema.json）
    # 由于 schema 校验依赖整个 evaluation-report schema，这里仅测试 main 的路由
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    # Mock validate_file 让它通过
    with patch("evaluation.cli.validate_file", return_value=None):
        rc = main(["validate-report", str(p)])
    captured = capsys.readouterr().out
    assert rc == 0
    assert "[OK]" in captured


def test_e2e_main_run_full_path_mocked_batch23(tmp_path, capsys):
    """main run 全路径（mock 所有外部依赖）。"""
    manifest_p = _make_manifest_file(tmp_path)
    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {"status": "incomplete", "file_count": 1, "content_group_count": 1, "pdf_count": 1, "docx_count": 0, "categories_covered": []},
        "summary": {},
        "per_doc": [
            {"doc_id": "d1", "metrics": {"pipeline_success": {"value": True}}, "wall_time_seconds": {"total": 0.1, "parse": None, "chunk": None, "parse_reason": "not_instrumented", "chunk_reason": "not_instrumented"}},
        ],
        "expected_failures": [],
    }
    with patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=tmp_path)):
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "abcdef1234567890", "git_dirty": False}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    rc = main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    captured = capsys.readouterr().out
    assert rc == 0
    assert "documents=1" in captured
    assert "成功 1" in captured
    assert "git_commit=abcdef123456" in captured


def test_e2e_main_run_pipeline_success_false_counts_as_fail_batch23(tmp_path, capsys):
    """pipeline_success=False 计入失败。"""
    manifest_p = _make_manifest_file(tmp_path)
    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
        "summary": {},
        "per_doc": [
            {"doc_id": "d1", "metrics": {"pipeline_success": {"value": False}}, "wall_time_seconds": {"total": 0.1, "parse": None, "chunk": None, "parse_reason": "not_instrumented", "chunk_reason": "not_instrumented"}},
            {"doc_id": "d2", "metrics": {"pipeline_success": {"value": None}}, "wall_time_seconds": {"total": 0.1, "parse": None, "chunk": None, "parse_reason": "not_instrumented", "chunk_reason": "not_instrumented"}},
        ],
        "expected_failures": [],
    }
    with patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=tmp_path)):
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    captured = capsys.readouterr().out
    assert "documents=2" in captured
    assert "成功 0" in captured
    assert "失败 2" in captured


def test_e2e_main_inspect_doc_full_path_batch23(tmp_path, capsys):
    """main inspect-doc 完整路径。"""
    p = _write_doc(tmp_path, doc={
        "document_id": "doc42",
        "source_type": "docx",
        "parser_name": "fallback",
        "parser_version": "0.1.0",
        "elements": [{"id": "e1"}, {"id": "e2"}],
        "chunks": [{"chunk_id": "c1"}],
    })
    rc = main(["inspect-doc", str(p)])
    captured = capsys.readouterr().out
    assert rc == 0
    assert "doc42" in captured
    assert "fallback" in captured
    assert "0.1.0" in captured
    assert "elements=2" in captured
    assert "chunks=1" in captured


def test_e2e_main_run_no_per_doc_still_works_batch23(tmp_path, capsys):
    """report 缺 per_doc 字段时 n_docs=0。"""
    manifest_p = _make_manifest_file(tmp_path)
    fake_report = {
        "report_version": "1.1",
        "provenance": {},
        "devset": {"status": "incomplete", "file_count": 0, "content_group_count": 0, "pdf_count": 0, "docx_count": 0, "categories_covered": []},
        "summary": {},
        # 故意缺 per_doc
        "expected_failures": [],
    }
    with patch("evaluation.cli.load_manifest", return_value=MagicMock(project_root=tmp_path)):
        with patch("evaluation.cli.run_evaluation", return_value=fake_report):
            with patch("evaluation.cli.validate_file", return_value=None):
                with patch("evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
                    out_p = tmp_path / "out.json"
                    out_p.write_text("{}", encoding="utf-8")
                    rc = main(["run", "--manifest", str(manifest_p), "--output", str(out_p)])
    captured = capsys.readouterr().out
    assert rc == 0
    assert "documents=0" in captured
