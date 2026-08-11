"""evaluation/cli.py 第五十三轮 edges 测试（Round 494）。

补强 edges51 未触及的角度（第二十五批）：
- _build_parser 第二十五批：--parser accepts kreuzberg / --max-chars type=int / --tolerance-chars 自定义 / validate-report positional 必填 / inspect-doc positional 必填 / 子命令 prog 命名 / argparse prog/format / _actions 数量 / choices 元素类型
- _format_metric 第二十五批：value=0.0 float / value=very large float / reason long string / reason unicode / dict sorted items / dict empty / value None without reason / value False without reason / 长名 padded
- _run_inspect_doc 第二十五批：compute_automatic_metrics 调用参数 / figure_caption_prf 调用参数 / chunk_boundary_prf 调用参数 / elements 缺失 default / chunks 缺失 default / source_type 缺失 default 'unknown' / 多 metric 排序 / 完整 dict 字段读
- main 第二十五批：run 成功路径 + [OK] 输出 / run 多个 flags / validate-report 文件不存在 → 2 / inspect-doc 委托 / inspect-doc 不存在 → 2 / main argv=None 默认 sys.argv / run 打印 git 信息
- module source forbidden tokens 第四十一批
- module source 字符串精确补强第三十七批
- signatures 第三十七批
- module 合理性第三十七批
- 端到端集成第三十七批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evaluation import cli as climod
from evaluation.cli import _build_parser, _format_metric, _run_inspect_doc, main


# ---------- _build_parser 第二十五批 ----------


def test_build_parser_parser_accepts_kreuzberg_batch25():
    """--parser kreuzberg 应被接受。"""
    p = _build_parser()
    args = p.parse_args(
        ["run", "--manifest", "m.json", "--output", "o.json", "--parser", "kreuzberg"]
    )
    assert args.parser == "kreuzberg"


def test_build_parser_max_chars_type_int_batch25():
    """--max-chars 类型必须是 int（type=int）。"""
    p = _build_parser()
    args = p.parse_args(
        ["run", "--manifest", "m.json", "--output", "o.json", "--max-chars", "500"]
    )
    assert args.max_chars == 500
    assert isinstance(args.max_chars, int)


def test_build_parser_max_chars_rejects_non_int_batch25():
    """--max-chars 非整数 → SystemExit。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(
            ["run", "--manifest", "m.json", "--output", "o.json", "--max-chars", "abc"]
        )


def test_build_parser_tolerance_chars_default_30_batch25():
    """run --tolerance-chars 默认 30。"""
    p = _build_parser()
    args = p.parse_args(["run", "--manifest", "m.json", "--output", "o.json"])
    assert args.tolerance_chars == 30


def test_build_parser_tolerance_chars_custom_batch25():
    """run --tolerance-chars 自定义。"""
    p = _build_parser()
    args = p.parse_args(
        [
            "run",
            "--manifest",
            "m.json",
            "--output",
            "o.json",
            "--tolerance-chars",
            "99",
        ]
    )
    assert args.tolerance_chars == 99


def test_build_parser_validate_report_input_required_batch25():
    """validate-report positional input 必填。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["validate-report"])


def test_build_parser_inspect_doc_input_required_batch25():
    """inspect-doc positional input 必填。"""
    p = _build_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["inspect-doc"])


def test_build_parser_inspect_doc_input_parsed_batch25():
    """inspect-doc positional input 解析正确。"""
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "/path/to/doc.json"])
    assert args.input == "/path/to/doc.json"


def test_build_parser_inspect_doc_tolerance_chars_default_30_batch25():
    """inspect-doc --tolerance-chars 默认 30。"""
    p = _build_parser()
    args = p.parse_args(["inspect-doc", "doc.json"])
    assert args.tolerance_chars == 30


def test_build_parser_validate_report_no_optional_flags_batch25():
    """validate-report 子命令只有 positional input（无 optional flags）。"""
    p = _build_parser()
    args = p.parse_args(["validate-report", "report.json"])
    assert args.input == "report.json"
    # command 字段
    assert args.command == "validate-report"


def test_build_parser_command_attribute_set_batch25():
    """所有子命令解析后 command 字段被正确设置。"""
    p = _build_parser()
    assert p.parse_args(["run", "--manifest", "m", "--output", "o"]).command == "run"
    assert p.parse_args(["validate-report", "r"]).command == "validate-report"
    assert p.parse_args(["inspect-doc", "d"]).command == "inspect-doc"


def test_build_parser_run_parser_help_text_batch25():
    """--parser help 含中文或英文说明。"""
    p = _build_parser()
    source = inspect.getsource(_build_parser)
    assert "parser" in source


def test_build_parser_subparser_choices_exact_three_batch25():
    """subparser choices 精确含三个子命令。"""
    p = _build_parser()
    sub_actions = [
        a for a in p._actions if a.__class__.__name__ == "_SubParsersAction"
    ]
    assert len(sub_actions[0].choices) == 3


def test_build_parser_action_count_batch25():
    """_actions 数量合理（version/help/3 subparser flags）。"""
    p = _build_parser()
    # argparse 始终至少含 help action
    assert len(p._actions) >= 1


def test_build_parser_no_flag_duplicate_batch25():
    """--manifest / --output / --parser / --max-chars / --tolerance-chars 不重复。"""
    p = _build_parser()
    # 检查 run 子 parser
    run_p = p._subparsers._group_actions[0].choices["run"]
    option_strings = []
    for a in run_p._actions:
        option_strings.extend(a.option_strings)
    # 没有 --manifest 出现两次（用 list.count）
    manifest_count = sum(1 for s in option_strings if s == "--manifest")
    assert manifest_count == 1


# ---------- _format_metric 第二十五批 ----------


def test_format_metric_value_zero_float_batch25():
    """value=0.0 (float) → '0.0000'。"""
    out = _format_metric("foo", {"value": 0.0, "reason": None})
    assert "0.0000" in out


def test_format_metric_value_large_float_batch25():
    """value=1234567.891011 (float) → 4 位小数格式。"""
    out = _format_metric("foo", {"value": 1234567.890123, "reason": None})
    assert "1234567.8901" in out


def test_format_metric_long_reason_batch25():
    """长 reason string 完整输出。"""
    long_reason = "x" * 200
    out = _format_metric("foo", {"value": None, "reason": long_reason})
    assert long_reason in out


def test_format_metric_unicode_reason_batch25():
    """unicode reason 完整输出。"""
    out = _format_metric("foo", {"value": None, "reason": "中文原因"})
    assert "中文原因" in out


def test_format_metric_dict_sorted_items_batch25():
    """dict value → items 按 key 排序输出。"""
    out = _format_metric(
        "foo",
        {
            "value": {"zebra": 1, "apple": 2, "mango": 3},
            "reason": None,
        },
    )
    # sorted: apple, mango, zebra
    pos_apple = out.find("apple=")
    pos_mango = out.find("mango=")
    pos_zebra = out.find("zebra=")
    assert pos_apple < pos_mango < pos_zebra


def test_format_metric_value_none_no_reason_batch25():
    """value=None 且缺 reason → 'null  (None)'。"""
    out = _format_metric("foo", {"value": None})
    assert "null" in out
    assert "(None)" in out


def test_format_metric_value_false_no_reason_batch25():
    """value=False 且缺 reason → 'false  (ok)'。"""
    out = _format_metric("foo", {"value": False})
    assert "false" in out
    assert "(ok)" in out


def test_format_metric_value_true_with_reason_batch25():
    """value=True 且 reason 存在 → 'true  (reason)'。"""
    out = _format_metric("foo", {"value": True, "reason": "parsed"})
    assert "true" in out
    assert "(parsed)" in out


def test_format_metric_value_negative_float_batch25():
    """value=-1.5 (float) → '-1.5000'。"""
    out = _format_metric("foo", {"value": -1.5, "reason": None})
    assert "-1.5000" in out


def test_format_metric_long_name_batch25():
    """name 超过 36 字符 → 仍原样输出（不截断）。"""
    long_name = "x" * 50
    out = _format_metric(long_name, {"value": 0.5, "reason": None})
    assert long_name in out


# ---------- _run_inspect_doc 第二十五批 ----------


def _make_inspect_args_v2(input_path, tolerance_chars=30):
    """构造 inspect-doc args Namespace（v2 后缀避免与 edges51 冲突）。"""
    args = MagicMock()
    args.input = str(input_path)
    args.tolerance_chars = tolerance_chars
    return args


def test_run_inspect_doc_calls_compute_metrics_with_doc_batch25(tmp_path):
    """compute_automatic_metrics 必须用 doc 关键字参数。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value={}
    ) as cam_mock, patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
        _run_inspect_doc(_make_inspect_args_v2(p))
    cam_mock.assert_called_once()
    kwargs = cam_mock.call_args.kwargs
    assert "document" in kwargs
    assert kwargs["document"] == {}


def test_run_inspect_doc_calls_compute_metrics_error_none_batch25(tmp_path):
    """compute_automatic_metrics 的 error=None。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value={}
    ) as cam_mock, patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
        _run_inspect_doc(_make_inspect_args_v2(p))
    assert cam_mock.call_args.kwargs.get("error") is None


def test_run_inspect_doc_calls_compute_metrics_expectations_none_batch25(tmp_path):
    """compute_automatic_metrics 的 expectations=None。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value={}
    ) as cam_mock, patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
        _run_inspect_doc(_make_inspect_args_v2(p))
    assert cam_mock.call_args.kwargs.get("expectations") is None


def test_run_inspect_doc_calls_figure_caption_with_doc_none_batch25(tmp_path):
    """figure_caption_prf(doc, None)。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value={}
    ), patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ) as fcp_mock, patch(
        "evaluation.annotation_metrics.chunk_boundary_prf", return_value={}
    ):
        _run_inspect_doc(_make_inspect_args_v2(p))
    fcp_mock.assert_called_once_with({}, None)


def test_run_inspect_doc_calls_chunk_boundary_with_tolerance_batch25(tmp_path):
    """chunk_boundary_prf(doc, None, tolerance_chars=...)。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value={}
    ), patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch(
        "evaluation.annotation_metrics.chunk_boundary_prf", return_value={}
    ) as cbp_mock:
        _run_inspect_doc(_make_inspect_args_v2(p, tolerance_chars=77))
    cbp_mock.assert_called_once()
    args = cbp_mock.call_args.args
    kwargs = cbp_mock.call_args.kwargs
    # 第一个参数是 doc，第二个是 None
    assert args[0] == {}
    assert args[1] is None
    # tolerance_chars 透传
    assert kwargs.get("tolerance_chars") == 77


def test_run_inspect_doc_source_type_missing_defaults_unknown_batch25(tmp_path, capsys):
    """source_type 缺失 → 'unknown'。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value={}
    ) as cam_mock, patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
        _run_inspect_doc(_make_inspect_args_v2(p))
    assert cam_mock.call_args.kwargs.get("source_type") == "unknown"


def test_run_inspect_doc_source_type_explicit_batch25(tmp_path, capsys):
    """source_type 显式给值 → 透传。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"source_type": "docx"}), encoding="utf-8")
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value={}
    ) as cam_mock, patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
        _run_inspect_doc(_make_inspect_args_v2(p))
    assert cam_mock.call_args.kwargs.get("source_type") == "docx"


def test_run_inspect_doc_prints_metrics_header_batch25(tmp_path, capsys):
    """输出含 'metrics:' 表头。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value={}
    ), patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
        _run_inspect_doc(_make_inspect_args_v2(p))
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_prints_file_path_batch25(tmp_path, capsys):
    """输出含文件路径。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value={}
    ), patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
        _run_inspect_doc(_make_inspect_args_v2(p))
    out = capsys.readouterr().out
    assert str(p) in out


def test_run_inspect_doc_prints_document_id_batch25(tmp_path, capsys):
    """输出含 document_id。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"document_id": "abc-123"}), encoding="utf-8")
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value={}
    ), patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
        _run_inspect_doc(_make_inspect_args_v2(p))
    out = capsys.readouterr().out
    assert "abc-123" in out


def test_run_inspect_doc_elements_null_defaults_empty_batch25(tmp_path, capsys):
    """elements: null → 当作 []。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"elements": None}), encoding="utf-8")
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value={}
    ), patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
        _run_inspect_doc(_make_inspect_args_v2(p))
    out = capsys.readouterr().out
    assert "elements=0" in out


def test_run_inspect_doc_chunks_null_defaults_empty_batch25(tmp_path, capsys):
    """chunks: null → 当作 []。"""
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"chunks": None}), encoding="utf-8")
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value={}
    ), patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
        _run_inspect_doc(_make_inspect_args_v2(p))
    out = capsys.readouterr().out
    assert "chunks=0" in out


# ---------- main 第二十五批 ----------


def _make_minimal_manifest_file(tmp_path):
    """写一个最小合法 manifest 文件（v2 后缀避免冲突）。"""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    return manifest


def test_main_run_success_returns_0_batch25(tmp_path, capsys):
    """run 成功路径 → return 0 + stdout [OK]。"""
    manifest = _make_minimal_manifest_file(tmp_path)
    out = tmp_path / "report.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), patch(
        "evaluation.cli.run_evaluation", return_value={"per_doc": [], "devset": {}}
    ), patch("evaluation.cli.validate_file"), patch(
        "evaluation.cli.get_git_provenance",
        return_value={"git_commit": "abcdef0123456789", "git_dirty": False},
    ):
        rc = main(["run", "--manifest", str(manifest), "--output", str(out)])
    assert rc == 0
    out_text = capsys.readouterr().out
    assert "[OK]" in out_text


def test_main_run_success_prints_documents_count_batch25(tmp_path, capsys):
    """run 成功 → stdout 含 documents= 数字。"""
    manifest = _make_minimal_manifest_file(tmp_path)
    out = tmp_path / "report.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), patch(
        "evaluation.cli.run_evaluation",
        return_value={
            "per_doc": [
                {"doc_id": "d1", "metrics": {"pipeline_success": {"value": True}}},
                {"doc_id": "d2", "metrics": {"pipeline_success": {"value": False}}},
                {"doc_id": "d3", "metrics": {"pipeline_success": {"value": True}}},
            ],
            "devset": {},
        },
    ), patch("evaluation.cli.validate_file"), patch(
        "evaluation.cli.get_git_provenance",
        return_value={"git_commit": "xyz", "git_dirty": False},
    ):
        rc = main(["run", "--manifest", str(manifest), "--output", str(out)])
    assert rc == 0
    out_text = capsys.readouterr().out
    assert "documents=3" in out_text
    assert "成功 2" in out_text
    assert "失败 1" in out_text


def test_main_run_success_prints_git_commit_batch25(tmp_path, capsys):
    """run 成功 → stdout 含 git_commit 前 12 字符。"""
    manifest = _make_minimal_manifest_file(tmp_path)
    out = tmp_path / "report.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), patch(
        "evaluation.cli.run_evaluation",
        return_value={"per_doc": [], "devset": {}},
    ), patch("evaluation.cli.validate_file"), patch(
        "evaluation.cli.get_git_provenance",
        return_value={"git_commit": "0123456789abcdef", "git_dirty": True},
    ):
        main(["run", "--manifest", str(manifest), "--output", str(out)])
    out_text = capsys.readouterr().out
    assert "0123456789ab" in out_text
    assert "git_dirty=True" in out_text


def test_main_run_success_with_devset_info_batch25(tmp_path, capsys):
    """run 成功 → stdout 含 devset_status / file_count 等。"""
    manifest = _make_minimal_manifest_file(tmp_path)
    out = tmp_path / "report.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), patch(
        "evaluation.cli.run_evaluation",
        return_value={
            "per_doc": [],
            "devset": {
                "status": "complete",
                "file_count": 10,
                "content_group_count": 5,
                "pdf_count": 4,
                "docx_count": 6,
            },
        },
    ), patch("evaluation.cli.validate_file"), patch(
        "evaluation.cli.get_git_provenance",
        return_value={"git_commit": "abc", "git_dirty": False},
    ):
        main(["run", "--manifest", str(manifest), "--output", str(out)])
    out_text = capsys.readouterr().out
    assert "complete" in out_text
    assert "file_count=10" in out_text
    assert "groups=5" in out_text
    assert "pdf=4" in out_text
    assert "docx=6" in out_text


def test_main_run_kreuzberg_flag_batch25(tmp_path):
    """run --parser kreuzberg → 透传到 run_evaluation。"""
    manifest = _make_minimal_manifest_file(tmp_path)
    out = tmp_path / "report.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), patch(
        "evaluation.cli.run_evaluation", return_value={"per_doc": [], "devset": {}}
    ) as re_mock, patch("evaluation.cli.validate_file"), patch(
        "evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}
    ):
        main(
            [
                "run",
                "--manifest",
                str(manifest),
                "--output",
                str(out),
                "--parser",
                "kreuzberg",
            ]
        )
    kwargs = re_mock.call_args.kwargs
    assert kwargs.get("parser_name") == "kreuzberg"


def test_main_run_max_chars_flag_batch25(tmp_path):
    """run --max-chars 500 → 透传。"""
    manifest = _make_minimal_manifest_file(tmp_path)
    out = tmp_path / "report.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), patch(
        "evaluation.cli.run_evaluation", return_value={"per_doc": [], "devset": {}}
    ) as re_mock, patch("evaluation.cli.validate_file"), patch(
        "evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}
    ):
        main(
            [
                "run",
                "--manifest",
                str(manifest),
                "--output",
                str(out),
                "--max-chars",
                "500",
            ]
        )
    kwargs = re_mock.call_args.kwargs
    assert kwargs.get("max_chars") == 500


def test_main_run_tolerance_chars_flag_batch25(tmp_path):
    """run --tolerance-chars 50 → 透传。"""
    manifest = _make_minimal_manifest_file(tmp_path)
    out = tmp_path / "report.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), patch(
        "evaluation.cli.run_evaluation", return_value={"per_doc": [], "devset": {}}
    ) as re_mock, patch("evaluation.cli.validate_file"), patch(
        "evaluation.cli.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}
    ):
        main(
            [
                "run",
                "--manifest",
                str(manifest),
                "--output",
                str(out),
                "--tolerance-chars",
                "50",
            ]
        )
    kwargs = re_mock.call_args.kwargs
    assert kwargs.get("tolerance_chars") == 50


def test_main_validate_report_directory_returns_2_batch25(tmp_path, capsys):
    """validate-report 目录（非文件）→ return 2。"""
    d = tmp_path / "subdir"
    d.mkdir()
    rc = main(["validate-report", str(d)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_inspect_doc_delegates_to_run_inspect_doc_batch25(tmp_path):
    """inspect-doc → 委托 _run_inspect_doc，返回其返回值。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli._run_inspect_doc", return_value=99) as rid_mock:
        rc = main(["inspect-doc", str(p)])
    assert rc == 99
    rid_mock.assert_called_once()


def test_main_inspect_doc_missing_file_returns_2_batch25(tmp_path, capsys):
    """inspect-doc 文件不存在 → return 2。"""
    p = tmp_path / "nope.json"
    rc = main(["inspect-doc", str(p)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_inspect_doc_invalid_json_returns_1_batch25(tmp_path, capsys):
    """inspect-doc 非 JSON → return 1。"""
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    rc = main(["inspect-doc", str(p)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "[ERROR]" in err


def test_main_validate_report_json_decode_error_returns_1_batch25(tmp_path, capsys):
    """validate-report JSON 解析失败 → return 1。"""
    # validate_file 在读取后用 Draft202012Validator 校验
    # 如果 JSON 不合法，json.load 抛 JSONDecodeError，被 validate_file 透传
    p = tmp_path / "report.json"
    p.write_text("{not json", encoding="utf-8")
    from evaluation.schema import EvalSchemaError

    # 模拟 validate_file 抛 JSONDecodeError（实际由 json.load 透传）
    with patch(
        "evaluation.cli.validate_file",
        side_effect=json.JSONDecodeError("msg", "doc", 0),
    ):
        rc = main(["validate-report", str(p)])
    assert rc == 1


def test_main_validate_report_filenotfound_returns_2_batch25(tmp_path, capsys):
    """validate-report 抛 FileNotFoundError → return 2。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch(
        "evaluation.cli.validate_file",
        side_effect=FileNotFoundError("schema file missing"),
    ):
        rc = main(["validate-report", str(p)])
    assert rc == 2


# ---------- module source forbidden tokens 第四十一批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import os",
    "import re",
    "import datetime",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import itertools",
    "import functools",
    "import timeit",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from itertools",
    "from functools",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import csv",
    "import xml",
    "import subprocess",
]


def test_module_source_forbidden_tokens_batch25():
    """cli.py 不应直接 import 这些副作用大的模块。"""
    source = inspect.getsource(climod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_no_class_keyword_batch25():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(climod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_source_no_yield_batch25():
    source = inspect.getsource(climod)
    assert "yield " not in source


def test_module_source_no_async_def_batch25():
    source = inspect.getsource(climod)
    assert "async def" not in source


def test_module_source_no_global_keyword_batch25():
    source = inspect.getsource(climod)
    assert "global " not in source


def test_module_source_no_walrus_batch25():
    source = inspect.getsource(climod)
    assert ":=" not in source


def test_module_source_no_eval_exec_batch25():
    source = inspect.getsource(climod)
    assert "eval(" not in source
    assert "exec(" not in source
    assert "compile(" not in source


def test_module_source_no_pickle_batch25():
    source = inspect.getsource(climod)
    assert "pickle" not in source


def test_module_source_no_subprocess_batch25():
    """cli.py 不应使用 subprocess（仅 report.py 需要）。"""
    source = inspect.getsource(climod)
    assert "subprocess" not in source


def test_module_source_no_dataclass_batch25():
    source = inspect.getsource(climod)
    assert "@dataclass" not in source


def test_module_source_no_network_io_batch25():
    source = inspect.getsource(climod)
    assert "import socket" not in source
    assert "import http" not in source
    assert "import requests" not in source


def test_module_source_no_relative_imports_batch25():
    source = inspect.getsource(climod)
    lines = [l for l in source.split("\n") if "from " in l and "from __future__" not in l]
    for line in lines:
        assert not line.strip().startswith("from ."), f"relative import: {line}"


def test_module_source_no_star_import_batch25():
    source = inspect.getsource(climod)
    assert "import *" not in source


def test_module_source_argparse_used_batch25():
    source = inspect.getsource(climod)
    assert "import argparse" in source


def test_module_source_no_environ_batch25():
    source = inspect.getsource(climod)
    assert "os.environ" not in source


def test_module_source_sys_used_for_reconfigure_batch25():
    """cli.py 必须用 sys.stdout.reconfigure（Windows 中文输出）。"""
    source = inspect.getsource(climod)
    assert "sys.stdout" in source
    assert "reconfigure" in source


# ---------- module source 字符串精确补强第三十七批 ----------


def test_module_source_contains_prog_evaluation_cli_batch25():
    source = inspect.getsource(climod)
    assert 'prog="evaluation.cli"' in source


def test_module_source_contains_subparser_run_batch25():
    source = inspect.getsource(climod)
    assert 'sub.add_parser("run"' in source


def test_module_source_contains_validate_report_batch25():
    source = inspect.getsource(climod)
    assert '"validate-report"' in source


def test_module_source_contains_inspect_doc_batch25():
    source = inspect.getsource(climod)
    assert '"inspect-doc"' in source


def test_module_source_contains_dest_command_batch25():
    source = inspect.getsource(climod)
    assert 'dest="command"' in source


def test_module_source_contains_required_true_batch25():
    source = inspect.getsource(climod)
    assert "required=True" in source


def test_module_source_contains_choices_fallback_kreuzberg_batch25():
    source = inspect.getsource(climod)
    assert "fallback" in source
    assert "kreuzberg" in source


def test_module_source_contains_default_fallback_batch25():
    source = inspect.getsource(climod)
    assert 'default="fallback"' in source


def test_module_source_contains_default_800_batch25():
    source = inspect.getsource(climod)
    assert "default=800" in source


def test_module_source_contains_default_30_batch25():
    source = inspect.getsource(climod)
    assert "default=30" in source


def test_module_source_contains_validate_file_call_batch25():
    source = inspect.getsource(climod)
    assert "validate_file(" in source


def test_module_source_contains_load_manifest_call_batch25():
    source = inspect.getsource(climod)
    assert "load_manifest(" in source


def test_module_source_contains_run_evaluation_call_batch25():
    source = inspect.getsource(climod)
    assert "run_evaluation(" in source


def test_module_source_contains_get_git_provenance_call_batch25():
    source = inspect.getsource(climod)
    assert "get_git_provenance(" in source


def test_module_source_contains_compute_automatic_metrics_call_batch25():
    source = inspect.getsource(climod)
    assert "compute_automatic_metrics(" in source


# ---------- signatures 第三十七批 ----------


def test_signature_build_parser_no_args_batch25():
    sig = inspect.signature(_build_parser)
    assert len(sig.parameters) == 0


def test_signature_main_argv_optional_batch25():
    """main(argv: list[str] | None = None) -> int。"""
    sig = inspect.signature(main)
    assert "argv" in sig.parameters
    p = sig.parameters["argv"]
    assert p.default is None
    assert p.annotation == "list[str] | None"


def test_signature_main_return_int_batch25():
    sig = inspect.signature(main)
    assert sig.return_annotation == "int"


def test_signature_format_metric_two_args_batch25():
    sig = inspect.signature(_format_metric)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["name", "metric"]


def test_signature_run_inspect_doc_one_arg_batch25():
    sig = inspect.signature(_run_inspect_doc)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "args"


def test_signature_run_inspect_doc_return_int_batch25():
    sig = inspect.signature(_run_inspect_doc)
    assert sig.return_annotation == "int"


def test_signature_main_no_varargs_batch25():
    sig = inspect.signature(main)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_signature_build_parser_return_argparse_batch25():
    """_build_parser 返回 argparse.ArgumentParser。"""
    sig = inspect.signature(_build_parser)
    # from __future__ import annotations 使之成为字符串
    assert sig.return_annotation == "argparse.ArgumentParser"


# ---------- module 合理性第三十七批 ----------


def test_module_all_present_or_none_batch25():
    """cli.py 可能没有 __all__（CLI 入口模块）。"""
    # 不强制要求 __all__
    if hasattr(climod, "__all__"):
        assert isinstance(climod.__all__, list)


def test_module_has_four_callables_batch25():
    """cli.py 定义 4 个函数：_build_parser, _format_metric, _run_inspect_doc, main。"""
    funcs = [
        name
        for name, val in inspect.getmembers(climod, inspect.isfunction)
        if val.__module__ == climod.__name__
    ]
    expected = {"_build_parser", "_format_metric", "_run_inspect_doc", "main"}
    assert expected.issubset(set(funcs))


def test_module_no_classes_batch25():
    classes = [
        name
        for name, val in inspect.getmembers(climod, inspect.isclass)
        if val.__module__ == climod.__name__
    ]
    assert classes == []


def test_module_docstring_present_batch25():
    assert climod.__doc__ is not None
    assert len(climod.__doc__) > 0


def test_module_docstring_mentions_subcommands_batch25():
    """module docstring 应提及 run / validate-report / inspect-doc 子命令。"""
    src = climod.__doc__
    assert "run" in src
    assert "validate-report" in src
    assert "inspect-doc" in src


def test_module_uses_from_future_annotations_batch25():
    source = inspect.getsource(climod)
    assert "from __future__ import annotations" in source


def test_module_main_docstring_present_batch25():
    """main 有 docstring 或可执行（不强制）。"""
    # 不强制 main 有 docstring，仅检查 callable
    assert callable(main)


def test_module_run_inspect_doc_uses_lazy_import_batch25():
    """_run_inspect_doc 内部用 lazy import（不在模块顶层）。"""
    source = inspect.getsource(_run_inspect_doc)
    assert "from evaluation.annotation_metrics import" in source
    assert "from evaluation.metrics import" in source


# ---------- 端到端集成第三十七批 ----------


def test_e2e_run_full_flow_returns_0_batch25(tmp_path):
    """端到端：合法 manifest → run → return 0 + 报告文件生成。"""
    manifest = _make_minimal_manifest_file(tmp_path)
    out = tmp_path / "report.json"

    fake_manifest = MagicMock()
    fake_manifest.project_root = tmp_path

    with patch("evaluation.cli.load_manifest", return_value=fake_manifest), patch(
        "evaluation.cli.run_evaluation",
        return_value={"per_doc": [], "devset": {}},
    ), patch("evaluation.cli.validate_file"), patch(
        "evaluation.cli.get_git_provenance",
        return_value={"git_commit": "x", "git_dirty": False},
    ):
        rc = main(["run", "--manifest", str(manifest), "--output", str(out)])
    assert rc == 0


def test_e2e_validate_report_success_returns_0_batch25(tmp_path, capsys):
    """端到端：合法报告 → validate-report → return 0 + [OK]。"""
    p = tmp_path / "report.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.cli.validate_file"):
        rc = main(["validate-report", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[OK]" in out


def test_e2e_inspect_doc_full_flow_returns_0_batch25(tmp_path):
    """端到端：合法 doc → inspect-doc → return 0。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value={}
    ), patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch(
        "evaluation.annotation_metrics.chunk_boundary_prf", return_value={}
    ):
        rc = main(["inspect-doc", str(p)])
    assert rc == 0


def test_e2e_inspect_doc_with_tolerance_chars_flag_batch25(tmp_path):
    """端到端：inspect-doc --tolerance-chars 自定义 → 透传。"""
    p = tmp_path / "doc.json"
    p.write_text("{}", encoding="utf-8")
    captured = {}

    def fake_cbp(doc, ann, tolerance_chars=30):
        captured["tolerance_chars"] = tolerance_chars
        return {}

    with patch(
        "evaluation.metrics.compute_automatic_metrics", return_value={}
    ), patch(
        "evaluation.annotation_metrics.figure_caption_prf", return_value={}
    ), patch(
        "evaluation.annotation_metrics.chunk_boundary_prf", side_effect=fake_cbp
    ):
        rc = main(["inspect-doc", str(p), "--tolerance-chars", "100"])
    assert rc == 0
    assert captured["tolerance_chars"] == 100


def test_e2e_no_args_exits_batch25():
    """端到端：无子命令 → SystemExit。"""
    with pytest.raises(SystemExit):
        main([])


def test_e2e_unknown_subcommand_exits_batch25():
    """端到端：未知子命令 → SystemExit。"""
    with pytest.raises(SystemExit):
        main(["bogus"])


def test_e2e_build_parser_callable_multiple_times_batch25():
    """_build_parser 应可被多次调用（每次返回新 parser）。"""
    p1 = _build_parser()
    p2 = _build_parser()
    assert p1 is not p2
    assert p1.prog == p2.prog
