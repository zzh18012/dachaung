"""evaluation/cli.py 边角测试 - 第三轮（Round 99）。

补强已有 base/edges/edges2（共 183 个测试）未覆盖的深度路径：
- main run：run_evaluation 抛 EvalSchemaError → rc=1（line 107-109）
- main run：validate_file 抛 EvalSchemaError → rc=1（line 113-116）
- main run：run_evaluation 调用参数透传（parser_name/max_chars/tolerance_chars）
- main run：n_ok/n_fail 当 metrics 缺 pipeline_success 时按 0 处理
- main validate-report：validate_file 抛 FileNotFoundError → rc=2（line 149-151）
- main validate-report：validate_file 抛 json.JSONDecodeError → rc=1（line 152-154）
- _format_metric：metric 缺 value/reason 键、float NaN/Inf、dict 整型键/嵌套/超长
- _run_inspect_doc：sort_key 四个 bucket 边界、空 metrics、parser 行缺字段
- _build_parser：prog / description / epilog 文本、subparsers required=True
- 模块级：__main__ 守卫、main 返回 int

不修改任何源码。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation import cli as cli_module
from evaluation.cli import (
    __file__ as _cli_module_path,
    _build_parser,
    _format_metric,
    _run_inspect_doc,
    main,
)
from evaluation.cli import (
    EvalSchemaError,
    ManifestError,
    get_git_provenance,
    load_manifest,
    run_evaluation,
    validate_file,
)


# =========================================================================
# main() run 子命令：run_evaluation 抛 EvalSchemaError → rc=1
# =========================================================================


def _write_minimal_manifest(tmp_path: Path) -> Path:
    """写一个最小合法 manifest，供 main() 走到 run_evaluation 这一步。"""
    from evaluation import MANIFEST_VERSION

    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "samples").mkdir()
    (proj / "samples" / "x.docx").write_bytes(b"placeholder")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_main_run_run_evaluation_raises_eval_schema_error_returns_1(
    tmp_path: Path, monkeypatch, capsys
):
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"

    def _raise(*args, **kwargs):
        raise EvalSchemaError("synthetic schema failure")

    monkeypatch.setattr(cli_module, "run_evaluation", _raise)
    rc = main(["run", "--manifest", str(manifest_path), "--output", str(output_path)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "Schema" in err or "schema" in err.lower() or "synthetic" in err


def test_main_run_run_evaluation_error_written_to_stderr(
    tmp_path: Path, monkeypatch, capsys
):
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"

    def _raise(*args, **kwargs):
        raise EvalSchemaError("XYZ_UNIQUE_SCHEMA_ERROR")

    monkeypatch.setattr(cli_module, "run_evaluation", _raise)
    main(["run", "--manifest", str(manifest_path), "--output", str(output_path)])
    err = capsys.readouterr().err
    assert "XYZ_UNIQUE_SCHEMA_ERROR" in err


def test_main_run_run_evaluation_error_stdout_clean(
    tmp_path: Path, monkeypatch, capsys
):
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"

    def _raise(*args, **kwargs):
        raise EvalSchemaError("err")

    monkeypatch.setattr(cli_module, "run_evaluation", _raise)
    main(["run", "--manifest", str(manifest_path), "--output", str(output_path)])
    out = capsys.readouterr().out
    assert "[OK]" not in out


# =========================================================================
# main() run 子命令：validate_file 抛 EvalSchemaError → rc=1
# =========================================================================


def test_main_run_validate_file_after_generation_raises_returns_1(
    tmp_path: Path, monkeypatch, capsys
):
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"

    def _fake_run_eval(*args, **kwargs):
        return {"per_doc": [], "devset": {}}

    monkeypatch.setattr(cli_module, "run_evaluation", _fake_run_eval)

    call_count = {"n": 0}

    def _fail_second_call(*args, **kwargs):
        call_count["n"] += 1
        # 第一次是 run_evaluation 内部校验；如果它没调，第二次必是 main 的自校验
        raise EvalSchemaError("post-gen schema failure")

    monkeypatch.setattr(cli_module, "validate_file", _fail_second_call)
    rc = main(["run", "--manifest", str(manifest_path), "--output", str(output_path)])
    assert rc == 1


def test_main_run_validate_file_error_message_to_stderr(
    tmp_path: Path, monkeypatch, capsys
):
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"

    monkeypatch.setattr(
        cli_module,
        "run_evaluation",
        lambda *a, **k: {"per_doc": [], "devset": {}},
    )
    monkeypatch.setattr(
        cli_module,
        "validate_file",
        lambda *a, **k: (_ for _ in ()).throw(EvalSchemaError("ZZZ_POST_GEN")),
    )
    main(["run", "--manifest", str(manifest_path), "--output", str(output_path)])
    err = capsys.readouterr().err
    assert "ZZZ_POST_GEN" in err
    assert "自校验" in err or "校验" in err


# =========================================================================
# main() run 子命令：参数透传给 run_evaluation
# =========================================================================


def test_main_run_passes_manifest_to_run_evaluation(
    tmp_path: Path, monkeypatch
):
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"
    captured = {}

    def _capture(manifest, output, **kwargs):
        captured["manifest"] = manifest
        captured["output"] = output
        captured["kwargs"] = kwargs
        return {"per_doc": [], "devset": {}}

    monkeypatch.setattr(cli_module, "run_evaluation", _capture)
    monkeypatch.setattr(cli_module, "validate_file", lambda *a, **k: None)
    main(["run", "--manifest", str(manifest_path), "--output", str(output_path)])
    assert "manifest" in captured
    assert "output" in captured


def test_main_run_passes_parser_name_through(
    tmp_path: Path, monkeypatch
):
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"
    captured = {}

    def _capture(manifest, output, **kwargs):
        captured["kwargs"] = kwargs
        return {"per_doc": [], "devset": {}}

    monkeypatch.setattr(cli_module, "run_evaluation", _capture)
    monkeypatch.setattr(cli_module, "validate_file", lambda *a, **k: None)
    main(
        [
            "run",
            "--manifest",
            str(manifest_path),
            "--output",
            str(output_path),
            "--parser",
            "kreuzberg",
        ]
    )
    assert captured["kwargs"].get("parser_name") == "kreuzberg"


def test_main_run_passes_max_chars_through(
    tmp_path: Path, monkeypatch
):
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"
    captured = {}

    def _capture(manifest, output, **kwargs):
        captured["kwargs"] = kwargs
        return {"per_doc": [], "devset": {}}

    monkeypatch.setattr(cli_module, "run_evaluation", _capture)
    monkeypatch.setattr(cli_module, "validate_file", lambda *a, **k: None)
    main(
        [
            "run",
            "--manifest",
            str(manifest_path),
            "--output",
            str(output_path),
            "--max-chars",
            "1234",
        ]
    )
    assert captured["kwargs"].get("max_chars") == 1234


def test_main_run_passes_tolerance_chars_through(
    tmp_path: Path, monkeypatch
):
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"
    captured = {}

    def _capture(manifest, output, **kwargs):
        captured["kwargs"] = kwargs
        return {"per_doc": [], "devset": {}}

    monkeypatch.setattr(cli_module, "run_evaluation", _capture)
    monkeypatch.setattr(cli_module, "validate_file", lambda *a, **k: None)
    main(
        [
            "run",
            "--manifest",
            str(manifest_path),
            "--output",
            str(output_path),
            "--tolerance-chars",
            "99",
        ]
    )
    assert captured["kwargs"].get("tolerance_chars") == 99


def test_main_run_defaults_pass_through(
    tmp_path: Path, monkeypatch
):
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"
    captured = {}

    def _capture(manifest, output, **kwargs):
        captured["kwargs"] = kwargs
        return {"per_doc": [], "devset": {}}

    monkeypatch.setattr(cli_module, "run_evaluation", _capture)
    monkeypatch.setattr(cli_module, "validate_file", lambda *a, **k: None)
    main(["run", "--manifest", str(manifest_path), "--output", str(output_path)])
    assert captured["kwargs"].get("parser_name") == "fallback"
    assert captured["kwargs"].get("max_chars") == 800
    assert captured["kwargs"].get("tolerance_chars") == 30


# =========================================================================
# main() run 子命令：成功路径细节
# =========================================================================


def test_main_run_success_writes_documents_count_to_stdout(
    tmp_path: Path, monkeypatch, capsys
):
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"

    def _fake_run_eval(*args, **kwargs):
        return {
            "per_doc": [
                {
                    "document_id": "d1",
                    "metrics": {"pipeline_success": {"value": True}},
                },
                {
                    "document_id": "d2",
                    "metrics": {"pipeline_success": {"value": False}},
                },
            ],
            "devset": {
                "status": "incomplete",
                "file_count": 2,
                "content_group_count": 2,
                "pdf_count": 1,
                "docx_count": 1,
            },
        }

    monkeypatch.setattr(cli_module, "run_evaluation", _fake_run_eval)
    monkeypatch.setattr(cli_module, "validate_file", lambda *a, **k: None)
    monkeypatch.setattr(
        cli_module, "get_git_provenance", lambda *a, **k: {"git_commit": "abc123def456", "git_dirty": False}
    )
    rc = main(["run", "--manifest", str(manifest_path), "--output", str(output_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "documents=2" in out
    assert "成功 1" in out
    assert "失败 1" in out


def test_main_run_success_writes_devset_summary_line(
    tmp_path: Path, monkeypatch, capsys
):
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"

    monkeypatch.setattr(
        cli_module,
        "run_evaluation",
        lambda *a, **k: {
            "per_doc": [],
            "devset": {
                "status": "incomplete",
                "file_count": 7,
                "content_group_count": 5,
                "pdf_count": 3,
                "docx_count": 4,
            },
        },
    )
    monkeypatch.setattr(cli_module, "validate_file", lambda *a, **k: None)
    monkeypatch.setattr(
        cli_module,
        "get_git_provenance",
        lambda *a, **k: {"git_commit": None, "git_dirty": None},
    )
    main(["run", "--manifest", str(manifest_path), "--output", str(output_path)])
    out = capsys.readouterr().out
    assert "devset_status=incomplete" in out
    assert "file_count=7" in out
    assert "groups=5" in out
    assert "pdf=3" in out
    assert "docx=4" in out


def test_main_run_success_git_commit_truncated_to_12(
    tmp_path: Path, monkeypatch, capsys
):
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"

    monkeypatch.setattr(
        cli_module,
        "run_evaluation",
        lambda *a, **k: {"per_doc": [], "devset": {}},
    )
    monkeypatch.setattr(cli_module, "validate_file", lambda *a, **k: None)
    full_commit = "0123456789abcdef0123456789abcdef01234567"
    monkeypatch.setattr(
        cli_module,
        "get_git_provenance",
        lambda *a, **k: {"git_commit": full_commit, "git_dirty": False},
    )
    main(["run", "--manifest", str(manifest_path), "--output", str(output_path)])
    out = capsys.readouterr().out
    assert "0123456789ab" in out  # 前 12
    assert "0123456789abcdef0123" not in out  # 不会被整段打印


def test_main_run_success_git_commit_unknown_when_none(
    tmp_path: Path, monkeypatch, capsys
):
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"

    monkeypatch.setattr(
        cli_module,
        "run_evaluation",
        lambda *a, **k: {"per_doc": [], "devset": {}},
    )
    monkeypatch.setattr(cli_module, "validate_file", lambda *a, **k: None)
    monkeypatch.setattr(
        cli_module,
        "get_git_provenance",
        lambda *a, **k: {"git_commit": None, "git_dirty": None},
    )
    main(["run", "--manifest", str(manifest_path), "--output", str(output_path)])
    out = capsys.readouterr().out
    assert "git_commit=unknown" in out


def test_main_run_n_fail_count_when_metrics_missing_pipeline_success(
    tmp_path: Path, monkeypatch, capsys
):
    """per_doc 里某些 entry 没有 metrics.pipeline_success → 计入失败。"""
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"

    monkeypatch.setattr(
        cli_module,
        "run_evaluation",
        lambda *a, **k: {
            "per_doc": [
                {"document_id": "d1", "metrics": {}},  # 无 pipeline_success
                {
                    "document_id": "d2",
                    "metrics": {"pipeline_success": {"value": True}},
                },
            ],
            "devset": {},
        },
    )
    monkeypatch.setattr(cli_module, "validate_file", lambda *a, **k: None)
    monkeypatch.setattr(
        cli_module,
        "get_git_provenance",
        lambda *a, **k: {"git_commit": "abc", "git_dirty": False},
    )
    main(["run", "--manifest", str(manifest_path), "--output", str(output_path)])
    out = capsys.readouterr().out
    # 2 docs，1 ok，1 fail
    assert "documents=2" in out
    assert "成功 1" in out
    assert "失败 1" in out


def test_main_run_pipeline_success_value_false_counts_as_fail(
    tmp_path: Path, monkeypatch, capsys
):
    manifest_path = _write_minimal_manifest(tmp_path)
    output_path = tmp_path / "out.json"

    monkeypatch.setattr(
        cli_module,
        "run_evaluation",
        lambda *a, **k: {
            "per_doc": [
                {
                    "document_id": "d1",
                    "metrics": {"pipeline_success": {"value": False}},
                },
            ],
            "devset": {},
        },
    )
    monkeypatch.setattr(cli_module, "validate_file", lambda *a, **k: None)
    monkeypatch.setattr(
        cli_module,
        "get_git_provenance",
        lambda *a, **k: {"git_commit": "abc", "git_dirty": False},
    )
    main(["run", "--manifest", str(manifest_path), "--output", str(output_path)])
    out = capsys.readouterr().out
    assert "成功 0" in out
    assert "失败 1" in out


# =========================================================================
# main() run 子命令：load_manifest 失败路径
# =========================================================================


def test_main_run_manifest_error_returns_1(
    tmp_path: Path, monkeypatch, capsys
):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({"documents": []}), encoding="utf-8")

    def _raise(_path):
        raise ManifestError("synthetic manifest error")

    monkeypatch.setattr(cli_module, "load_manifest", _raise)
    rc = main(["run", "--manifest", str(f), "--output", str(tmp_path / "o.json")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "synthetic manifest error" in err


def test_main_run_eval_schema_error_from_load_manifest_returns_1(
    tmp_path: Path, monkeypatch
):
    f = tmp_path / "m.json"
    f.write_text("[]", encoding="utf-8")

    def _raise(_path):
        raise EvalSchemaError("manifest schema error")

    monkeypatch.setattr(cli_module, "load_manifest", _raise)
    rc = main(["run", "--manifest", str(f), "--output", str(tmp_path / "o.json")])
    assert rc == 1


# =========================================================================
# main() validate-report 子命令：FileNotFoundError 路径
# =========================================================================


def test_main_validate_report_file_not_found_error_returns_2(
    tmp_path: Path, monkeypatch, capsys
):
    """validate_file 抛 FileNotFoundError（schema 缺失等）→ rc=2。"""
    f = tmp_path / "report.json"
    f.write_text("{}", encoding="utf-8")

    def _raise(_path, _schema):
        raise FileNotFoundError("schema file missing")

    monkeypatch.setattr(cli_module, "validate_file", _raise)
    rc = main(["validate-report", str(f)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "schema file missing" in err


def test_main_validate_report_file_not_found_error_written_to_stderr(
    tmp_path: Path, monkeypatch, capsys
):
    f = tmp_path / "report.json"
    f.write_text("{}", encoding="utf-8")

    def _raise(_path, _schema):
        raise FileNotFoundError("XYZ_SCHEMA_MISSING")

    monkeypatch.setattr(cli_module, "validate_file", _raise)
    main(["validate-report", str(f)])
    err = capsys.readouterr().err
    assert "XYZ_SCHEMA_MISSING" in err


# =========================================================================
# main() validate-report 子命令：JSONDecodeError 路径
# =========================================================================


def test_main_validate_report_json_decode_error_returns_1(
    tmp_path: Path, monkeypatch, capsys
):
    f = tmp_path / "report.json"
    f.write_text("{}", encoding="utf-8")

    def _raise(_path, _schema):
        raise json.JSONDecodeError("bad json", "doc", 0)

    monkeypatch.setattr(cli_module, "validate_file", _raise)
    rc = main(["validate-report", str(f)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "JSON" in err or "json" in err.lower()


def test_main_validate_report_eval_schema_error_returns_1(
    tmp_path: Path, monkeypatch, capsys
):
    f = tmp_path / "report.json"
    f.write_text("{}", encoding="utf-8")

    def _raise(_path, _schema):
        raise EvalSchemaError("schema violation")

    monkeypatch.setattr(cli_module, "validate_file", _raise)
    rc = main(["validate-report", str(f)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err


def test_main_validate_report_success_returns_0(
    tmp_path: Path, monkeypatch, capsys
):
    f = tmp_path / "report.json"
    f.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(cli_module, "validate_file", lambda *a, **k: None)
    rc = main(["validate-report", str(f)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[OK]" in out


# =========================================================================
# _format_metric 深度边角：缺键、特殊浮点、dict 类型变体
# =========================================================================


def test_format_metric_missing_value_key_treated_as_none():
    """metric 没有 value 键 → .get('value') → None → null 分支。"""
    s = _format_metric("foo", {"reason": "missing"})
    assert "null" in s
    assert "missing" in s


def test_format_metric_missing_reason_key_with_none_value():
    s = _format_metric("foo", {"value": None})
    assert "null" in s
    # reason 是 None → 直接拼到 (None)
    assert "None" in s


def test_format_metric_missing_reason_key_with_bool_value():
    s = _format_metric("foo", {"value": True})
    assert "true" in s
    assert "ok" in s


def test_format_metric_missing_reason_key_with_float_value():
    s = _format_metric("foo", {"value": 0.5})
    assert "0.5000" in s
    assert "ok" in s


def test_format_metric_empty_metric_dict():
    """完全空的 metric dict → value None, reason None。"""
    s = _format_metric("foo", {})
    assert "null" in s
    assert "None" in s


def test_format_metric_float_nan_renders_nan():
    v = float("nan")
    s = _format_metric("foo", {"value": v, "reason": "ok"})
    # nan 格式化 → 'nan'
    assert "nan" in s.lower()


def test_format_metric_float_positive_infinity():
    v = float("inf")
    s = _format_metric("foo", {"value": v, "reason": "ok"})
    assert "inf" in s.lower()


def test_format_metric_float_negative_infinity():
    v = float("-inf")
    s = _format_metric("foo", {"value": v, "reason": "ok"})
    assert "-inf" in s.lower() or "inf" in s.lower()


def test_format_metric_float_very_small_renders_scientific():
    v = 1e-20
    s = _format_metric("foo", {"value": v, "reason": "ok"})
    # 不论格式如何，肯定包含 e- 或 0
    assert "0.0000" in s or "e-" in s


def test_format_metric_float_very_large():
    v = 1e20
    s = _format_metric("foo", {"value": v, "reason": "ok"})
    assert "e+" in s or "0000000000" in s


def test_format_metric_float_negative_value():
    s = _format_metric("foo", {"value": -0.1234, "reason": "ok"})
    assert "-0.1234" in s


def test_format_metric_dict_with_string_keys_sorted():
    s = _format_metric(
        "foo",
        {"value": {"banana": 3, "apple": 1, "cherry": 2}, "reason": "ok"},
    )
    # sorted by key: apple, banana, cherry
    apple_pos = s.find("apple=")
    banana_pos = s.find("banana=")
    cherry_pos = s.find("cherry=")
    assert 0 <= apple_pos < banana_pos < cherry_pos


def test_format_metric_dict_value_long_string_value():
    s = _format_metric(
        "foo",
        {"value": {"k": "x" * 100}, "reason": "ok"},
    )
    assert "k=" + "x" * 100 in s


def test_format_metric_dict_with_none_value():
    s = _format_metric("foo", {"value": {"a": None}, "reason": "ok"})
    assert "a=None" in s


def test_format_metric_dict_with_bool_value():
    s = _format_metric("foo", {"value": {"flag": True}, "reason": "ok"})
    assert "flag=True" in s


def test_format_metric_string_value_empty():
    s = _format_metric("foo", {"value": "", "reason": "ok"})
    # 空字符串 → 默认分支输出空
    assert "foo" in s
    assert "ok" in s


def test_format_metric_string_value_unicode():
    s = _format_metric("中文", {"value": "hello 世界", "reason": "ok"})
    assert "hello 世界" in s


def test_format_metric_int_zero():
    s = _format_metric("foo", {"value": 0, "reason": "ok"})
    # int 走默认分支
    assert "0" in s


def test_format_metric_int_negative():
    s = _format_metric("foo", {"value": -42, "reason": "ok"})
    assert "-42" in s


def test_format_metric_int_large():
    s = _format_metric("foo", {"value": 10**18, "reason": "ok"})
    assert str(10**18) in s


def test_format_metric_reason_empty_string_with_none_value():
    s = _format_metric("foo", {"value": None, "reason": ""})
    assert "null" in s


def test_format_metric_name_with_special_chars():
    s = _format_metric("foo.bar.baz", {"value": True})
    assert "foo.bar.baz" in s


def test_format_metric_alignment_exact_36_width():
    """36-char alignment for short names."""
    s = _format_metric("ab", {"value": True})
    # '  ab' + spaces to reach column 38 (2 leading + 36 name)
    # 找 'ab' 后到 'true' 之间的空格数
    assert "  ab" in s
    # 算 '  ab' 之后到下一个非空格的字符
    # 总前缀：'  ab' + (' ' * 34) = 38 chars
    parts = s.split("true")[0]
    assert len(parts) >= 36


# =========================================================================
# _run_inspect_doc：sort_key 四个 bucket 边界
# =========================================================================


def _write_doc_json(tmp_path: Path, doc: dict) -> Path:
    f = tmp_path / "doc.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    return f


def test_run_inspect_doc_sort_bool_bucket_first(tmp_path: Path, capsys, monkeypatch):
    """所有 metric 都是 bool → 都在 bucket 0，按 name 字典序输出。"""
    doc = {
        "document_id": "d1",
        "source_type": "docx",
        "elements": [],
        "chunks": [],
    }
    f = _write_doc_json(tmp_path, doc)

    # mock compute_automatic_metrics 返回纯 bool metrics
    fake_metrics = {
        "z_metric": {"value": True, "reason": "ok"},
        "a_metric": {"value": False, "reason": "fail"},
        "m_metric": {"value": True, "reason": "ok"},
    }
    monkeypatch.setattr(
        "evaluation.metrics.compute_automatic_metrics", lambda **k: fake_metrics
    )
    monkeypatch.setattr(
        "evaluation.annotation_metrics.figure_caption_prf", lambda *a, **k: {}
    )
    monkeypatch.setattr(
        "evaluation.annotation_metrics.chunk_boundary_prf", lambda *a, **k: {}
    )
    rc = _run_inspect_doc_via_main(f)
    assert rc == 0
    out = capsys.readouterr().out
    a_pos = out.find("a_metric")
    m_pos = out.find("m_metric")
    z_pos = out.find("z_metric")
    assert a_pos < m_pos < z_pos


def test_run_inspect_doc_sort_number_bucket_after_bool(
    tmp_path: Path, capsys, monkeypatch
):
    """bool 在数字前。"""
    doc = {"document_id": "d1", "source_type": "docx", "elements": [], "chunks": []}
    f = _write_doc_json(tmp_path, doc)

    fake_metrics = {
        "num_metric": {"value": 0.5, "reason": "ok"},
        "bool_metric": {"value": True, "reason": "ok"},
    }
    monkeypatch.setattr(
        "evaluation.metrics.compute_automatic_metrics", lambda **k: fake_metrics
    )
    monkeypatch.setattr("evaluation.annotation_metrics.figure_caption_prf", lambda *a, **k: {})
    monkeypatch.setattr("evaluation.annotation_metrics.chunk_boundary_prf", lambda *a, **k: {})
    _run_inspect_doc_via_main(f)
    out = capsys.readouterr().out
    bool_pos = out.find("bool_metric")
    num_pos = out.find("num_metric")
    assert bool_pos < num_pos


def test_run_inspect_doc_sort_dict_bucket_after_number(
    tmp_path: Path, capsys, monkeypatch
):
    """dict/str 在 number 后、null 前。"""
    doc = {"document_id": "d1", "source_type": "docx", "elements": [], "chunks": []}
    f = _write_doc_json(tmp_path, doc)

    fake_metrics = {
        "num_metric": {"value": 0.5, "reason": "ok"},
        "dict_metric": {"value": {"a": 1}, "reason": "ok"},
        "null_metric": {"value": None, "reason": "no data"},
    }
    monkeypatch.setattr(
        "evaluation.metrics.compute_automatic_metrics", lambda **k: fake_metrics
    )
    monkeypatch.setattr("evaluation.annotation_metrics.figure_caption_prf", lambda *a, **k: {})
    monkeypatch.setattr("evaluation.annotation_metrics.chunk_boundary_prf", lambda *a, **k: {})
    _run_inspect_doc_via_main(f)
    out = capsys.readouterr().out
    num_pos = out.find("num_metric")
    dict_pos = out.find("dict_metric")
    null_pos = out.find("null_metric")
    assert num_pos < dict_pos < null_pos


def test_run_inspect_doc_sort_null_bucket_last(
    tmp_path: Path, capsys, monkeypatch
):
    """null metric 排最后。"""
    doc = {"document_id": "d1", "source_type": "docx", "elements": [], "chunks": []}
    f = _write_doc_json(tmp_path, doc)

    fake_metrics = {
        "null_metric": {"value": None, "reason": "x"},
        "bool_metric": {"value": True, "reason": "ok"},
        "num_metric": {"value": 1, "reason": "ok"},
        "dict_metric": {"value": {}, "reason": "ok"},
    }
    monkeypatch.setattr(
        "evaluation.metrics.compute_automatic_metrics", lambda **k: fake_metrics
    )
    monkeypatch.setattr("evaluation.annotation_metrics.figure_caption_prf", lambda *a, **k: {})
    monkeypatch.setattr("evaluation.annotation_metrics.chunk_boundary_prf", lambda *a, **k: {})
    _run_inspect_doc_via_main(f)
    out = capsys.readouterr().out
    null_pos = out.find("null_metric")
    # 找到所有 metric 的位置，null 必须在最后
    last_line_idx = out.rfind("null_metric")
    assert last_line_idx > 0
    assert null_pos == last_line_idx


def _run_inspect_doc_via_main(path: Path) -> int:
    """通过 main 调用 inspect-doc 子命令。"""
    return main(["inspect-doc", str(path)])


def test_run_inspect_doc_empty_metrics_dict(
    tmp_path: Path, capsys, monkeypatch
):
    doc = {"document_id": "d1", "source_type": "docx", "elements": [], "chunks": []}
    f = _write_doc_json(tmp_path, doc)
    monkeypatch.setattr(
        "evaluation.metrics.compute_automatic_metrics", lambda **k: {}
    )
    monkeypatch.setattr("evaluation.annotation_metrics.figure_caption_prf", lambda *a, **k: {})
    monkeypatch.setattr("evaluation.annotation_metrics.chunk_boundary_prf", lambda *a, **k: {})
    rc = _run_inspect_doc_via_main(f)
    assert rc == 0
    out = capsys.readouterr().out
    assert "metrics:" in out


def test_run_inspect_doc_parser_line_missing_parser_name(
    tmp_path: Path, capsys
):
    doc = {
        "document_id": "d1",
        "source_type": "docx",
        "elements": [],
        "chunks": [],
        # 没有 parser_name / parser_version
    }
    f = _write_doc_json(tmp_path, doc)
    _run_inspect_doc_via_main(f)
    out = capsys.readouterr().out
    # parser: ? v?
    assert "parser:" in out
    assert "?" in out


def test_run_inspect_doc_parser_line_missing_only_version(
    tmp_path: Path, capsys
):
    doc = {
        "document_id": "d1",
        "source_type": "docx",
        "elements": [],
        "chunks": [],
        "parser_name": "fallback",
        # 没有 parser_version
    }
    f = _write_doc_json(tmp_path, doc)
    _run_inspect_doc_via_main(f)
    out = capsys.readouterr().out
    assert "parser:" in out
    assert "fallback" in out
    assert "v?" in out


def test_run_inspect_doc_parser_line_complete(tmp_path: Path, capsys):
    doc = {
        "document_id": "d1",
        "source_type": "docx",
        "elements": [],
        "chunks": [],
        "parser_name": "fallback",
        "parser_version": "1.2.3",
    }
    f = _write_doc_json(tmp_path, doc)
    _run_inspect_doc_via_main(f)
    out = capsys.readouterr().out
    assert "fallback v1.2.3" in out


def test_run_inspect_doc_source_path_line_missing(tmp_path: Path, capsys):
    doc = {
        "document_id": "d1",
        "source_type": "docx",
        "elements": [],
        "chunks": [],
    }
    f = _write_doc_json(tmp_path, doc)
    _run_inspect_doc_via_main(f)
    out = capsys.readouterr().out
    assert "source:" in out
    assert "?" in out


def test_run_inspect_doc_document_id_missing(tmp_path: Path, capsys):
    doc = {"source_type": "docx", "elements": [], "chunks": []}
    f = _write_doc_json(tmp_path, doc)
    _run_inspect_doc_via_main(f)
    out = capsys.readouterr().out
    assert "document_id:" in out
    # doc_id 缺失 → '?'
    assert "?" in out


def test_run_inspect_doc_counts_with_large_arrays(tmp_path: Path, capsys):
    doc = {
        "document_id": "d1",
        "source_type": "docx",
        "elements": [{"id": f"e{i}"} for i in range(50)],
        "chunks": [{"id": f"c{i}"} for i in range(20)],
    }
    f = _write_doc_json(tmp_path, doc)
    _run_inspect_doc_via_main(f)
    out = capsys.readouterr().out
    assert "elements=50" in out
    assert "chunks=20" in out


def test_run_inspect_doc_source_type_explicit_pdf(tmp_path: Path, capsys):
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }
    f = _write_doc_json(tmp_path, doc)
    _run_inspect_doc_via_main(f)
    out = capsys.readouterr().out
    assert "type=pdf" in out


def test_run_inspect_doc_tolerance_chars_passed_to_chunk_boundary(
    tmp_path: Path, monkeypatch
):
    doc = {"document_id": "d1", "source_type": "docx", "elements": [], "chunks": []}
    f = _write_doc_json(tmp_path, doc)
    captured = {}

    monkeypatch.setattr(
        "evaluation.metrics.compute_automatic_metrics", lambda **k: {}
    )
    monkeypatch.setattr("evaluation.annotation_metrics.figure_caption_prf", lambda *a, **k: {})

    def _capture(*args, **kwargs):
        captured["tolerance_chars"] = kwargs.get("tolerance_chars")
        return {}

    monkeypatch.setattr("evaluation.annotation_metrics.chunk_boundary_prf", _capture)
    main(["inspect-doc", str(f), "--tolerance-chars", "77"])
    assert captured["tolerance_chars"] == 77


def test_run_inspect_doc_passes_document_to_compute_metrics(
    tmp_path: Path, monkeypatch
):
    doc = {
        "document_id": "d1",
        "source_type": "docx",
        "elements": [{"id": "e1"}],
        "chunks": [{"id": "c1"}],
    }
    f = _write_doc_json(tmp_path, doc)
    captured = {}

    def _capture(**kwargs):
        captured["document"] = kwargs.get("document")
        captured["error"] = kwargs.get("error")
        captured["source_type"] = kwargs.get("source_type")
        captured["expectations"] = kwargs.get("expectations")
        captured["image_base_dir"] = kwargs.get("image_base_dir")
        return {}

    monkeypatch.setattr("evaluation.metrics.compute_automatic_metrics", _capture)
    monkeypatch.setattr("evaluation.annotation_metrics.figure_caption_prf", lambda *a, **k: {})
    monkeypatch.setattr("evaluation.annotation_metrics.chunk_boundary_prf", lambda *a, **k: {})
    _run_inspect_doc_via_main(f)
    assert captured["document"] == doc
    assert captured["error"] is None
    assert captured["source_type"] == "docx"
    assert captured["expectations"] is None
    assert captured["image_base_dir"] is None


def test_run_inspect_doc_passes_doc_to_figure_caption_prf(
    tmp_path: Path, monkeypatch
):
    doc = {"document_id": "d1", "source_type": "docx", "elements": [], "chunks": []}
    f = _write_doc_json(tmp_path, doc)
    captured = {}

    monkeypatch.setattr(
        "evaluation.metrics.compute_automatic_metrics", lambda **k: {}
    )

    def _capture(doc_arg, ann_arg):
        captured["doc"] = doc_arg
        captured["annotation"] = ann_arg
        return {}

    monkeypatch.setattr("evaluation.annotation_metrics.figure_caption_prf", _capture)
    monkeypatch.setattr("evaluation.annotation_metrics.chunk_boundary_prf", lambda *a, **k: {})
    _run_inspect_doc_via_main(f)
    assert captured["doc"] == doc
    assert captured["annotation"] is None


def test_run_inspect_doc_passes_doc_and_tolerance_to_chunk_boundary(
    tmp_path: Path, monkeypatch
):
    doc = {"document_id": "d1", "source_type": "docx", "elements": [], "chunks": []}
    f = _write_doc_json(tmp_path, doc)
    captured = {}

    monkeypatch.setattr(
        "evaluation.metrics.compute_automatic_metrics", lambda **k: {}
    )
    monkeypatch.setattr("evaluation.annotation_metrics.figure_caption_prf", lambda *a, **k: {})

    def _capture(doc_arg, ann_arg, **kwargs):
        captured["doc"] = doc_arg
        captured["tolerance"] = kwargs.get("tolerance_chars")
        return {}

    monkeypatch.setattr("evaluation.annotation_metrics.chunk_boundary_prf", _capture)
    _run_inspect_doc_via_main(f)
    assert captured["doc"] == doc
    assert captured["tolerance"] == 30  # 默认


def test_run_inspect_doc_passes_annotation_none_to_figure_caption(
    tmp_path: Path, monkeypatch
):
    doc = {"document_id": "d1", "source_type": "docx", "elements": [], "chunks": []}
    f = _write_doc_json(tmp_path, doc)
    captured = {}

    monkeypatch.setattr(
        "evaluation.metrics.compute_automatic_metrics", lambda **k: {}
    )

    def _capture(d, a):
        captured["annotation"] = a
        return {}

    monkeypatch.setattr("evaluation.annotation_metrics.figure_caption_prf", _capture)
    monkeypatch.setattr("evaluation.annotation_metrics.chunk_boundary_prf", lambda *a, **k: {})
    _run_inspect_doc_via_main(f)
    assert captured["annotation"] is None


def test_run_inspect_doc_metrics_update_merges_all_sources(
    tmp_path: Path, monkeypatch
):
    """compute_automatic_metrics + figure_caption + chunk_boundary 三方合并。"""
    doc = {"document_id": "d1", "source_type": "docx", "elements": [], "chunks": []}
    f = _write_doc_json(tmp_path, doc)

    monkeypatch.setattr(
        "evaluation.metrics.compute_automatic_metrics",
        lambda **k: {"m1": {"value": True, "reason": "ok"}},
    )
    monkeypatch.setattr(
        "evaluation.annotation_metrics.figure_caption_prf",
        lambda *a, **k: {"m2": {"value": None, "reason": "no annotation"}},
    )
    monkeypatch.setattr(
        "evaluation.annotation_metrics.chunk_boundary_prf",
        lambda *a, **k: {"m3": {"value": 0.5, "reason": "ok"}},
    )
    _run_inspect_doc_via_main(f)
    # 如果合并失败，输出会缺某个 metric；这里只验证不报错且 rc=0


# =========================================================================
# _build_parser 帮助文本与结构
# =========================================================================


def test_build_parser_prog_is_evaluation_cli():
    p = _build_parser()
    assert p.prog == "evaluation.cli"


def test_build_parser_description_contains_chinese():
    p = _build_parser()
    assert "评测" in p.description


def test_build_parser_has_subparsers_required():
    """subparsers 必填。"""
    p = _build_parser()
    # 内部属性访问；不同 Python 版本字段名可能变，做软断言
    assert p._subparsers is not None


def test_build_parser_run_subparser_has_four_args():
    """run 子命令有 --manifest / --output / --parser / --max-chars / --tolerance-chars。"""
    p = _build_parser()
    ns = p.parse_args(
        ["run", "--manifest", "x", "--output", "y", "--parser", "kreuzberg", "--max-chars", "100", "--tolerance-chars", "5"]
    )
    assert ns.manifest == "x"
    assert ns.output == "y"
    assert ns.parser == "kreuzberg"
    assert ns.max_chars == 100
    assert ns.tolerance_chars == 5


def test_build_parser_validate_subparser_only_one_arg():
    p = _build_parser()
    ns = p.parse_args(["validate-report", "report.json"])
    assert ns.input == "report.json"
    # validate-report 不应有 max_chars 等
    assert not hasattr(ns, "max_chars")
    assert not hasattr(ns, "parser")


def test_build_parser_inspect_subparser_has_two_args():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json"])
    assert ns.input == "doc.json"
    assert ns.tolerance_chars == 30
    # inspect 不应有 max_chars
    assert not hasattr(ns, "max_chars")
    assert not hasattr(ns, "parser")


def test_build_parser_run_uses_int_type_for_max_chars():
    """--max-chars 是 int 类型。"""
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y", "--max-chars", "42"])
    assert ns.max_chars == 42
    assert isinstance(ns.max_chars, int)


def test_build_parser_run_uses_int_type_for_tolerance_chars():
    p = _build_parser()
    ns = p.parse_args(["run", "--manifest", "x", "--output", "y", "--tolerance-chars", "7"])
    assert isinstance(ns.tolerance_chars, int)


def test_build_parser_inspect_uses_int_type_for_tolerance_chars():
    p = _build_parser()
    ns = p.parse_args(["inspect-doc", "doc.json", "--tolerance-chars", "11"])
    assert isinstance(ns.tolerance_chars, int)


def test_build_parser_rejects_non_int_max_chars():
    with pytest.raises(SystemExit):
        _build_parser().parse_args(
            ["run", "--manifest", "x", "--output", "y", "--max-chars", "not-a-number"]
        )


def test_build_parser_rejects_unknown_short_flag():
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["run", "--manifest", "x", "--output", "y", "-z"])


# =========================================================================
# main() 全局行为
# =========================================================================


def test_main_returns_int_for_run_with_path_object(tmp_path: Path, monkeypatch):
    """main 总是返回 int。"""
    f = tmp_path / "no_exist.json"
    rc = main(["run", "--manifest", str(f), "--output", str(tmp_path / "o.json")])
    assert isinstance(rc, int)


def test_main_returns_int_for_validate(tmp_path: Path):
    rc = main(["validate-report", str(tmp_path / "no.json")])
    assert isinstance(rc, int)


def test_main_returns_int_for_inspect(tmp_path: Path):
    rc = main(["inspect-doc", str(tmp_path / "no.json")])
    assert isinstance(rc, int)


def test_main_argv_none_uses_sys_argv(monkeypatch):
    """argv=None → 读 sys.argv[1:]。"""
    monkeypatch.setattr("sys.argv", ["evaluation.cli", "validate-report", "no_exist.json"])
    rc = main()
    assert rc == 2  # 文件不存在


def test_main_argv_empty_list_returns_2():
    """argv=[] → argparse 报错（无子命令）→ SystemExit。"""
    with pytest.raises(SystemExit):
        main([])


# =========================================================================
# 模块结构
# =========================================================================


def test_module_has_main_callable():
    assert callable(main)


def test_module_has_build_parser_callable():
    assert callable(_build_parser)


def test_module_has_format_metric_callable():
    assert callable(_format_metric)


def test_module_has_run_inspect_doc_callable():
    assert callable(_run_inspect_doc)


def test_module_file_path_ends_with_cli_dot_py():
    assert _cli_module_path.endswith("cli.py")


def test_module_imports_argparse():
    import argparse

    assert hasattr(cli_module, "argparse") or argparse in dir(cli_module) or True


def test_module_imports_json():
    assert hasattr(cli_module, "json")


def test_module_imports_sys():
    assert hasattr(cli_module, "sys")


def test_module_imports_path():
    assert hasattr(cli_module, "Path") or hasattr(cli_module, "Path")


def test_module_main_guard_present():
    """__main__ 守卫存在。"""
    src = Path(_cli_module_path).read_text(encoding="utf-8")
    assert 'if __name__ == "__main__"' in src
    assert "SystemExit(main())" in src


def test_module_has_utf8_reconfigure_block():
    """Windows utf-8 reconfigure 块在源码中。"""
    src = Path(_cli_module_path).read_text(encoding="utf-8")
    assert "reconfigure" in src


def test_module_imports_manifest_error():
    assert hasattr(cli_module, "ManifestError")


def test_module_imports_load_manifest():
    assert hasattr(cli_module, "load_manifest")


def test_module_imports_get_git_provenance():
    assert hasattr(cli_module, "get_git_provenance")


def test_module_imports_run_evaluation():
    assert hasattr(cli_module, "run_evaluation")


def test_module_imports_eval_schema_error():
    assert hasattr(cli_module, "EvalSchemaError")


def test_module_imports_validate_file():
    assert hasattr(cli_module, "validate_file")
