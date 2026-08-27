"""评测 CLI 端到端测试：合成 DOCX → manifest → 跑评测 → 校验报告。

合成文档只用于评测代码本身的测试，不计入真实开发集，不会写入 samples/private/devset。
"""

from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path

import pytest

from evaluation.schema import validate_file


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


def _build_synthetic_docx(path: Path) -> Path:
    """合成最小 DOCX，含 1 个标题 + 1 个段落（含 styles.xml 让 heading 识别生效）。"""
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    doc_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style>
</w:styles>'''
    doc_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Chapter 1</w:t></w:r></w:p>
    <w:p><w:r><w:t>Hello world. This is paragraph one.</w:t></w:r></w:p>
  </w:body>
</w:document>'''
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/document.xml", doc_xml)
    return path


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
    _build_synthetic_docx(docx_path)

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
    assert report["report_version"] == "1.3"
    # v1.3：per_doc 必须带 parser_used
    assert report["per_doc"][0]["parser_used"] == "fallback"
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
    _build_synthetic_docx(docx_path)

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
    _build_synthetic_docx(docx_path)
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
