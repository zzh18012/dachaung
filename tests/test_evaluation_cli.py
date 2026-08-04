"""评测 CLI 端到端测试：合成 DOCX → manifest → 跑评测 → 校验报告。

合成文档只用于评测代码本身的测试，不计入真实开发集，不会写入 samples/private/devset。
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from evaluation.schema import validate_file

from tests._synthetic_docs import build_minimal_docx


VENV_PYTHON = str(
    Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe"
)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run_cli(args: list[str], cwd: Path) -> tuple[int, str, str]:
    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        # 让子进程能 import evaluation 包（cwd 可能不在项目根）
        "PYTHONPATH": str(PROJECT_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    proc = subprocess.run(
        [VENV_PYTHON, "-m", "evaluation.cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """构造临时项目根，用真实 .git 让 provenance 工作。"""
    import subprocess
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)
    return tmp_path


def _write_manifest(project_root: Path, docx_rel_path: str) -> Path:
    (project_root / "outputs").mkdir(exist_ok=True)
    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "TEST-001",
                "path": docx_rel_path,
                "source_type": "docx",
                "categories": ["report", "synthetic"],
                "expectations": {
                    "element_count_by_type": {"heading": 1, "paragraph": 1}
                },
            }
        ],
    }
    p = project_root / "manifest.json"
    p.write_text(json.dumps(manifest_data), encoding="utf-8")
    return p


def test_cli_run_end_to_end(project_root: Path):
    docx_rel = "samples/test/sample.docx"
    docx_path = project_root / docx_rel
    docx_path.parent.mkdir(parents=True)
    build_minimal_docx(docx_path)

    manifest = _write_manifest(project_root, docx_rel)
    output = project_root / "outputs" / "report.json"

    rc, out, err = _run_cli(
        ["run", "--manifest", str(manifest), "--output", str(output)],
        cwd=project_root,
    )
    assert rc == 0, f"stderr={err}"
    assert "[OK]" in out
    assert output.is_file()

    # 报告通过 Schema 校验
    validate_file(output, "evaluation-report.schema.json")

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["report_version"] == "1.1"
    assert report["devset"]["status"] == "incomplete"
    assert report["devset"]["file_count"] == 1
    assert report["devset"]["docx_count"] == 1
    assert report["devset"]["pdf_count"] == 0
    # 只有 1 个文档（无 paired_with）→ 1 个 content group
    assert report["devset"]["content_group_count"] == 1
    # provenance
    assert report["provenance"]["git_commit"] is not None
    # tmp_path 仓库此时可能有未跟踪文件（synthetic docx / manifest），dirty 可能 True 或 False
    assert isinstance(report["provenance"]["git_dirty"], bool)
    assert report["provenance"]["parser_name"] == "fallback"
    assert report["provenance"]["max_chars"] == 800
    # per_doc
    assert len(report["per_doc"]) == 1
    pd = report["per_doc"][0]
    assert pd["doc_id"] == "TEST-001"
    assert pd["source_type"] == "docx"
    # 自动指标都有
    metrics = pd["metrics"]
    assert metrics["pipeline_success"]["value"] is True
    assert metrics["element_count_total"]["value"] >= 2
    assert metrics["heading_boundary_compliance"]["value"] == 1.0  # 1 heading at chunk start
    # figure_caption 固定 null
    assert metrics["figure_caption_precision"]["reason"] == "parser_does_not_emit_relations"
    # chunk_boundary 无标注 → null
    assert metrics["chunk_boundary_precision"]["reason"] == "no_annotation"
    # wall_time
    wt = pd["wall_time_seconds"]
    assert wt["total"] is not None and wt["total"] > 0
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_cli_run_with_annotation(project_root: Path):
    docx_rel = "samples/test/sample.docx"
    docx_path = project_root / docx_rel
    docx_path.parent.mkdir(parents=True)
    build_minimal_docx(docx_path)

    # 加一个标注文件
    ann_rel = "annotations/TEST-001.json"
    ann_path = project_root / ann_rel
    ann_path.parent.mkdir(parents=True)
    ann_path.write_text(json.dumps({
        "annotation_version": "1.0",
        "doc_id": "TEST-001",
        "annotator": "reviewer_a",
        "date": "2026-08-03",
        "chunk_boundary_anchors": [
            # 用一个不存在的 marker，验证 recall 走 "no_ground_truth_anchors_in_stream"
            {"marker": "ZZZ_NONEXISTENT", "position": "after", "reason": "test"},
        ],
    }), encoding="utf-8")

    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "TEST-001",
                "path": docx_rel,
                "source_type": "docx",
                "annotation_file": ann_rel,
            }
        ],
    }
    manifest = project_root / "manifest.json"
    manifest.write_text(json.dumps(manifest_data), encoding="utf-8")

    output = project_root / "outputs" / "report.json"
    # 用较小的 max_chars 强制产生多个 chunk，让 chunk_boundary 有预测边界
    rc, out, err = _run_cli(
        ["run", "--manifest", str(manifest), "--output", str(output),
         "--max-chars", "32"],
        cwd=project_root,
    )
    assert rc == 0, f"stderr={err}"
    report = json.loads(output.read_text(encoding="utf-8"))
    metrics = report["per_doc"][0]["metrics"]
    # chunk_boundary_recall 因 marker 找不到 → no_ground_truth_anchors_in_stream
    assert metrics["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_cli_validate_report_subcommand(project_root: Path):
    docx_rel = "samples/test/sample.docx"
    docx_path = project_root / docx_rel
    docx_path.parent.mkdir(parents=True)
    build_minimal_docx(docx_path)
    manifest = _write_manifest(project_root, docx_rel)
    output = project_root / "outputs" / "report.json"
    rc, _, _ = _run_cli(
        ["run", "--manifest", str(manifest), "--output", str(output)],
        cwd=project_root,
    )
    assert rc == 0

    # validate-report 子命令
    rc, out, err = _run_cli(["validate-report", str(output)], cwd=project_root)
    assert rc == 0, f"stderr={err}"
    assert "[OK]" in out


def test_cli_validate_report_missing_file(project_root: Path):
    rc, out, err = _run_cli(
        ["validate-report", str(project_root / "nope.json")], cwd=project_root
    )
    assert rc == 2
    assert "不存在" in err


def test_cli_run_missing_manifest(project_root: Path):
    rc, out, err = _run_cli(
        ["run", "--manifest", str(project_root / "nope.json"),
         "--output", str(project_root / "out.json")],
        cwd=project_root,
    )
    assert rc == 2
    assert "清单不存在" in err


def test_cli_run_bad_manifest(project_root: Path):
    bad = project_root / "bad.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    rc, out, err = _run_cli(
        ["run", "--manifest", str(bad),
         "--output", str(project_root / "out.json")],
        cwd=project_root,
    )
    assert rc != 0


def test_cli_run_with_expected_failures(project_root: Path):
    """expected_failures 也应被评测且 matches 字段正确。"""
    bad_rel = "samples/test/bad.pdf"
    bad_path = project_root / bad_rel
    bad_path.parent.mkdir(parents=True)
    bad_path.write_bytes(b"%PDF-1.4\nthis is not valid\n%%EOF")

    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "ERR-1",
                "path": bad_rel,
                "expected_error_code": "pdfplumber_open_failed",
            }
        ],
    }
    manifest = project_root / "manifest.json"
    manifest.write_text(json.dumps(manifest_data), encoding="utf-8")
    output = project_root / "outputs" / "report.json"
    rc, out, err = _run_cli(
        ["run", "--manifest", str(manifest), "--output", str(output)],
        cwd=project_root,
    )
    assert rc == 0, f"stderr={err}"
    report = json.loads(output.read_text(encoding="utf-8"))
    assert len(report["expected_failures"]) == 1
    ef = report["expected_failures"][0]
    assert ef["doc_id"] == "ERR-1"
    assert ef["actual_error_code"] == "pdfplumber_open_failed"
    assert ef["matches"] is True


# ---- inspect-doc 子命令 ----


def _parse_doc_to_json(project_root: Path, doc_id: str = "TEST-INSPECT") -> Path:
    """构造一份合法 doc.json，供 inspect-doc 用。"""
    docx_rel = "samples/test/sample.docx"
    docx_path = project_root / docx_rel
    docx_path.parent.mkdir(parents=True)
    build_minimal_docx(docx_path)
    out_json = project_root / "outputs" / f"{doc_id}.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    # 用 app.cli parse 跑出真实 doc.json（带 source_spans）
    rc, _, err = _run_cli_app(
        ["parse", str(docx_path), "-o", str(out_json)], cwd=project_root,
    )
    assert rc == 0, f"stderr={err}"
    return out_json


def _run_cli_app(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """跑 app.cli（不是 evaluation.cli）。"""
    python = VENV_PYTHON if Path(VENV_PYTHON).is_file() else os.environ.get("PYTHON", "python")
    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(PROJECT_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    proc = subprocess.run(
        [python, "-m", "app.cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_inspect_doc_basic(project_root: Path):
    """inspect-doc 打印文档元信息 + metrics 列表。"""
    doc_json = _parse_doc_to_json(project_root)

    rc, out, err = _run_cli(["inspect-doc", str(doc_json)], cwd=project_root)
    assert rc == 0, f"stderr={err}"
    # 元信息
    assert "file:" in out
    assert "document_id:" in out
    assert "source:" in out
    assert "parser:" in out
    assert "counts:" in out
    # metrics 区块
    assert "metrics:" in out
    # 关键指标出现
    assert "pipeline_success" in out
    assert "schema_valid" in out
    assert "element_count_total" in out
    assert "chunk_reference_intact_ratio" in out
    assert "text_preservation_equal" in out


def test_inspect_doc_null_metrics_rendered_with_reason(project_root: Path):
    """无标注时 chunk_boundary / figure_caption 是 null，应显示 reason。"""
    doc_json = _parse_doc_to_json(project_root)
    rc, out, err = _run_cli(["inspect-doc", str(doc_json)], cwd=project_root)
    assert rc == 0, f"stderr={err}"
    # chunk_boundary 无标注 → reason=no_annotation
    assert "chunk_boundary_precision" in out
    assert "no_annotation" in out
    # figure_caption 固定 null + parser_does_not_emit_relations
    assert "figure_caption_precision" in out
    assert "parser_does_not_emit_relations" in out


def test_inspect_doc_missing_file_returns_2(project_root: Path):
    rc, _, err = _run_cli(
        ["inspect-doc", str(project_root / "nope.json")], cwd=project_root,
    )
    assert rc == 2
    assert "不存在" in err


def test_inspect_doc_bad_json_returns_1(project_root: Path):
    bad = project_root / "bad.json"
    bad.write_text("{not valid", encoding="utf-8")
    rc, _, err = _run_cli(["inspect-doc", str(bad)], cwd=project_root)
    assert rc == 1
    assert "JSON 解析失败" in err


def test_inspect_doc_top_level_not_object(project_root: Path):
    arr = project_root / "arr.json"
    arr.write_text("[1, 2, 3]", encoding="utf-8")
    rc, _, err = _run_cli(["inspect-doc", str(arr)], cwd=project_root)
    assert rc == 1
    assert "顶层不是对象" in err


# ---------- 边角与缺漏补强（Round 34） ----------


# argparse 入口校验


def test_no_subcommand_returns_nonzero(project_root: Path):
    """argparse required=True 时缺子命令 → rc=2。"""
    rc, out, err = _run_cli([], cwd=project_root)
    assert rc != 0


def test_unknown_subcommand_returns_nonzero(project_root: Path):
    rc, _, _ = _run_cli(["bogus"], cwd=project_root)
    assert rc != 0


def test_run_invalid_parser_choice_returns_nonzero(project_root: Path):
    """--parser 不在 choices ('fallback','kreuzberg') 内 → argparse rc!=0。"""
    manifest = project_root / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    rc, out, err = _run_cli([
        "run", "--manifest", str(manifest),
        "--output", str(project_root / "out.json"),
        "--parser", "bogus_parser",
    ], cwd=project_root)
    assert rc != 0
    assert "invalid choice" in err


def test_run_missing_manifest_arg_returns_nonzero(project_root: Path):
    """缺 --manifest 必填项 → argparse rc!=0。"""
    rc, out, err = _run_cli([
        "run", "--output", str(project_root / "out.json"),
    ], cwd=project_root)
    assert rc != 0
    assert "--manifest" in err or "required" in err.lower()


def test_run_missing_output_arg_returns_nonzero(project_root: Path):
    """缺 --output 必填项 → argparse rc!=0。"""
    manifest = project_root / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    rc, out, err = _run_cli([
        "run", "--manifest", str(manifest),
    ], cwd=project_root)
    assert rc != 0
    assert "--output" in err or "required" in err.lower()


def test_run_with_kreuzberg_parser_choice(project_root: Path):
    """--parser kreuzberg 在 choices 内（即便 kreuzberg 不一定能解析）。"""
    docx_rel = "samples/test/sample.docx"
    docx_path = project_root / docx_rel
    docx_path.parent.mkdir(parents=True)
    build_minimal_docx(docx_path)
    manifest = _write_manifest(project_root, docx_rel)
    output = project_root / "outputs" / "report.json"
    rc, _, err = _run_cli([
        "run", "--manifest", str(manifest), "--output", str(output),
        "--parser", "kreuzberg",
    ], cwd=project_root)
    # kreuzberg 适配器存在时 rc=0；如果 import 失败则 rc!=0
    assert rc != 2  # 不应是 argparse 错误


def test_run_with_explicit_max_chars(project_root: Path):
    """--max-chars 32 也应能跑通（生成多 chunk）。"""
    docx_rel = "samples/test/sample.docx"
    docx_path = project_root / docx_rel
    docx_path.parent.mkdir(parents=True)
    build_minimal_docx(docx_path)
    manifest = _write_manifest(project_root, docx_rel)
    output = project_root / "outputs" / "report.json"
    rc, _, err = _run_cli([
        "run", "--manifest", str(manifest), "--output", str(output),
        "--max-chars", "32",
    ], cwd=project_root)
    assert rc == 0, f"stderr={err}"
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["provenance"]["max_chars"] == 32


def test_run_with_explicit_tolerance_chars(project_root: Path):
    """--tolerance-chars 50 应能跑通（runner 内部会传递给 chunk_boundary_prf）。

    注：_tolerance_chars 在 public report 序列化时被剥离（schema additionalProperties:false），
    所以这里只验证 CLI 接受参数 + 报告生成成功。
    """
    docx_rel = "samples/test/sample.docx"
    docx_path = project_root / docx_rel
    docx_path.parent.mkdir(parents=True)
    build_minimal_docx(docx_path)
    manifest = _write_manifest(project_root, docx_rel)
    output = project_root / "outputs" / "report.json"
    rc, _, err = _run_cli([
        "run", "--manifest", str(manifest), "--output", str(output),
        "--tolerance-chars", "50",
    ], cwd=project_root)
    assert rc == 0, f"stderr={err}"
    # 报告通过 schema 校验（含 chunk_boundary 子结构）
    validate_file(output, "evaluation-report.schema.json")


# validate-report 边角


def test_validate_report_bad_json_returns_1(project_root: Path):
    """validate-report 拿到非合法 JSON → rc=1。"""
    bad = project_root / "broken.json"
    bad.write_text("{not json", encoding="utf-8")
    rc, _, err = _run_cli(["validate-report", str(bad)], cwd=project_root)
    assert rc == 1
    assert "JSON 解析失败" in err


def test_validate_report_invalid_content_returns_1(project_root: Path):
    """合法 JSON 但报告不合规 → rc=1。"""
    bad = project_root / "wrong.json"
    bad.write_text(json.dumps({"wrong": "shape"}), encoding="utf-8")
    rc, _, err = _run_cli(["validate-report", str(bad)], cwd=project_root)
    assert rc == 1
    assert "[FAIL]" in err


# inspect-doc 边角


def test_inspect_doc_with_custom_tolerance_chars(project_root: Path):
    """--tolerance-chars 应被接受（虽然无标注时该指标固定 null）。"""
    doc_json = _parse_doc_to_json(project_root)
    rc, _, err = _run_cli([
        "inspect-doc", str(doc_json), "--tolerance-chars", "100",
    ], cwd=project_root)
    assert rc == 0, f"stderr={err}"


def test_inspect_doc_with_empty_doc(project_root: Path):
    """空文档（无 elements/chunks）也能 inspect。"""
    empty = project_root / "empty.json"
    empty.write_text(json.dumps({
        "schema_version": "0.1.0",
        "document_id": "d-empty",
        "source_path": "x",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "test",
        "parser_version": "0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }), encoding="utf-8")
    rc, out, err = _run_cli(["inspect-doc", str(empty)], cwd=project_root)
    assert rc == 0, f"stderr={err}"
    assert "elements=0" in out
    assert "chunks=0" in out


def test_inspect_doc_metrics_sorted_correctly(project_root: Path):
    """metrics 输出应按 (bool, numeric, dict, null) 分组排序。"""
    doc_json = _parse_doc_to_json(project_root)
    rc, out, err = _run_cli(["inspect-doc", str(doc_json)], cwd=project_root)
    assert rc == 0, f"stderr={err}"
    # bool 类（pipeline_success=True）应在 numeric 类之前
    success_line = out.find("pipeline_success")
    element_count_line = out.find("element_count_total")
    assert success_line != -1 and element_count_line != -1
    assert success_line < element_count_line


# _format_metric 直接单测


def test_format_metric_none_value():
    from evaluation.cli import _format_metric
    result = _format_metric("foo", {"value": None, "reason": "no_data"})
    assert "foo" in result
    assert "null" in result
    assert "no_data" in result


def test_format_metric_bool_true():
    from evaluation.cli import _format_metric
    result = _format_metric("ok_metric", {"value": True, "reason": None})
    assert "true" in result
    assert "(ok)" in result


def test_format_metric_bool_false():
    from evaluation.cli import _format_metric
    result = _format_metric("fail_metric", {"value": False, "reason": None})
    assert "false" in result


def test_format_metric_int_value():
    from evaluation.cli import _format_metric
    result = _format_metric("count_metric", {"value": 42, "reason": None})
    assert "42" in result
    assert "(ok)" in result


def test_format_metric_float_value_formatted():
    from evaluation.cli import _format_metric
    result = _format_metric("ratio_metric", {"value": 0.123456, "reason": None})
    assert "0.1235" in result  # 4 位小数


def test_format_metric_dict_value():
    from evaluation.cli import _format_metric
    result = _format_metric("counts", {"value": {"heading": 2, "paragraph": 3}, "reason": None})
    assert "heading=2" in result
    assert "paragraph=3" in result


def test_format_metric_string_value():
    """value 是字符串时走 default 分支。"""
    from evaluation.cli import _format_metric
    result = _format_metric("name", {"value": "fallback", "reason": None})
    assert "fallback" in result


def test_format_metric_with_reason_overrides_default():
    from evaluation.cli import _format_metric
    result = _format_metric("ok_metric", {"value": True, "reason": "custom_reason"})
    # bool 但有自定义 reason → 用 reason 不用默认 'ok'
    assert "custom_reason" in result
    assert "(custom_reason)" in result
    # 默认的 "(ok)" 不应出现
    assert "(ok)" not in result


def test_format_metric_alignment_width():
    """所有 metric 行的 name 列固定 36 字符宽（format spec {name:36}）。"""
    from evaluation.cli import _format_metric
    result = _format_metric("x", {"value": 1, "reason": None})
    # format is "  {name:36} {value}  ({reason})"
    # 总前缀（到 value 之前）= 2 (缩进) + 36 (name 区) + 1 (空格) = 39
    name_part = result.split("1")[0]
    assert len(name_part) == 39


# main() 函数级别


def test_main_unknown_command_raises_system_exit():
    """main(['bogus']) → argparse rc!=0 (SystemExit)。"""
    from evaluation.cli import main
    with pytest.raises(SystemExit) as exc:
        main(["bogus"])
    assert exc.value.code != 0


def test_main_no_command_raises_system_exit():
    """main([]) → argparse rc!=0 (SystemExit)。"""
    from evaluation.cli import main
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code != 0


def test_main_validate_report_returns_2_for_missing_file(tmp_path: Path):
    from evaluation.cli import main
    assert main(["validate-report", str(tmp_path / "nope.json")]) == 2


def test_main_validate_report_returns_1_for_bad_json(tmp_path: Path):
    from evaluation.cli import main
    bad = tmp_path / "broken.json"
    bad.write_text("{not json", encoding="utf-8")
    assert main(["validate-report", str(bad)]) == 1


def test_main_validate_report_returns_1_for_invalid_content(tmp_path: Path):
    from evaluation.cli import main
    bad = tmp_path / "wrong.json"
    bad.write_text(json.dumps({"x": 1}), encoding="utf-8")
    assert main(["validate-report", str(bad)]) == 1


def test_main_inspect_doc_returns_2_for_missing_file(tmp_path: Path):
    from evaluation.cli import main
    assert main(["inspect-doc", str(tmp_path / "nope.json")]) == 2


def test_main_inspect_doc_returns_1_for_bad_json(tmp_path: Path):
    from evaluation.cli import main
    bad = tmp_path / "broken.json"
    bad.write_text("{not json", encoding="utf-8")
    assert main(["inspect-doc", str(bad)]) == 1


def test_main_inspect_doc_returns_1_for_top_level_array(tmp_path: Path):
    from evaluation.cli import main
    bad = tmp_path / "arr.json"
    bad.write_text("[1,2,3]", encoding="utf-8")
    assert main(["inspect-doc", str(bad)]) == 1


def test_main_inspect_doc_returns_0_for_valid_doc(tmp_path: Path):
    from evaluation.cli import main
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({
        "schema_version": "0.1.0",
        "document_id": "d",
        "source_path": "x",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "test",
        "parser_version": "0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }), encoding="utf-8")
    assert main(["inspect-doc", str(p)]) == 0


def test_main_run_returns_2_for_missing_manifest(tmp_path: Path):
    from evaluation.cli import main
    assert main([
        "run", "--manifest", str(tmp_path / "nope.json"),
        "--output", str(tmp_path / "out.json"),
    ]) == 2


def test_main_run_returns_1_for_bad_manifest(tmp_path: Path):
    from evaluation.cli import main
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert main([
        "run", "--manifest", str(bad),
        "--output", str(tmp_path / "out.json"),
    ]) == 1


# _build_parser 直接调用


def test_build_parser_returns_argparse_parser():
    from evaluation.cli import _build_parser
    p = _build_parser()
    # 三个子命令都已注册
    sub_actions = [a for a in p._actions if hasattr(a, "choices") and a.choices]
    # 找到 subparsers action
    sub_action = next((a for a in p._subparsers._group_actions if hasattr(a, "choices")), None)
    assert sub_action is not None
    assert set(sub_action.choices.keys()) == {"run", "validate-report", "inspect-doc"}


# run 子命令的端到端输出格式


def test_run_outputs_summary_includes_devset_status(project_root: Path):
    docx_rel = "samples/test/sample.docx"
    docx_path = project_root / docx_rel
    docx_path.parent.mkdir(parents=True)
    build_minimal_docx(docx_path)
    manifest = _write_manifest(project_root, docx_rel)
    output = project_root / "outputs" / "report.json"
    rc, out, err = _run_cli([
        "run", "--manifest", str(manifest), "--output", str(output),
    ], cwd=project_root)
    assert rc == 0, f"stderr={err}"
    # stdout 应有 devset_status / file_count / groups / pdf / docx
    assert "devset_status=incomplete" in out
    assert "file_count=1" in out
    assert "groups=1" in out
    assert "pdf=0" in out
    assert "docx=1" in out


def test_run_outputs_summary_includes_git_provenance(project_root: Path):
    docx_rel = "samples/test/sample.docx"
    docx_path = project_root / docx_rel
    docx_path.parent.mkdir(parents=True)
    build_minimal_docx(docx_path)
    manifest = _write_manifest(project_root, docx_rel)
    output = project_root / "outputs" / "report.json"
    rc, out, err = _run_cli([
        "run", "--manifest", str(manifest), "--output", str(output),
    ], cwd=project_root)
    assert rc == 0, f"stderr={err}"
    # git_commit 前 12 字符
    assert "git_commit=" in out
    # git_dirty=True 或 False
    assert "git_dirty=" in out
