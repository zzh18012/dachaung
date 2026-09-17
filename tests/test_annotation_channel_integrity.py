"""r55 C15/C16/C06：评测标注通道完整性。

- C15：坏标注（不可读 / JSON 无效）必须与缺标注（no_annotation）在降级
  reason 上可区分，且公开 per_doc 落盘 annotation_status
- C16：标注 doc_id 与清单不符时拒绝消费，不得进入评测链
- C06：CLAUDE.md 承诺"容差 tolerance_chars 必须在报告中记录"→ 公开
  per_doc 落盘 tolerance_chars
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from evaluation.runner import _load_annotation
from evaluation.schema import validate_file


VENV_PYTHON = str(
    Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe"
)
_PYTHON = VENV_PYTHON if Path(VENV_PYTHON).is_file() else sys.executable
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run_cli(args: list[str], cwd: Path) -> tuple[int, str, str]:
    env = {
        **os.environ,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(PROJECT_ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    }
    proc = subprocess.run(
        [_PYTHON, "-m", "evaluation.cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _build_synthetic_docx(path: Path) -> Path:
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
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)
    return tmp_path


def _setup_doc_and_manifest(
    project_root: Path,
    annotation_file: str | None,
    annotation_content: str | None,
) -> Path:
    docx_rel = "samples/test/sample.docx"
    docx_path = project_root / docx_rel
    docx_path.parent.mkdir(parents=True)
    _build_synthetic_docx(docx_path)

    doc_entry: dict = {
        "doc_id": "TEST-001",
        "path": docx_rel,
        "source_type": "docx",
    }
    if annotation_file is not None:
        ann_path = project_root / annotation_file
        ann_path.parent.mkdir(parents=True, exist_ok=True)
        assert annotation_content is not None
        ann_path.write_text(annotation_content, encoding="utf-8")
        doc_entry["annotation_file"] = annotation_file

    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [doc_entry],
    }
    manifest = project_root / "manifest.json"
    manifest.write_text(json.dumps(manifest_data), encoding="utf-8")
    return manifest


# ---------- _load_annotation 单元（C15 三态） ----------


def test_load_annotation_missing(tmp_path: Path):
    ann, status = _load_annotation(tmp_path / "nope.json")
    assert ann is None
    assert status == "missing"


def test_load_annotation_none_path():
    ann, status = _load_annotation(None)
    assert ann is None
    assert status == "missing"


def test_load_annotation_invalid_json(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text('{"unclosed": ', encoding="utf-8")
    ann, status = _load_annotation(p)
    assert ann is None
    assert status == "annotation_invalid_json"


def test_load_annotation_unreadable(tmp_path: Path, monkeypatch):
    p = tmp_path / "locked.json"
    p.write_text("{}", encoding="utf-8")

    def _raise_open(self, *a, **k):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "open", _raise_open)
    ann, status = _load_annotation(p)
    assert ann is None
    assert status == "annotation_unreadable"


# ---------- 端到端：坏标注与缺标注可区分（C15） ----------


def test_invalid_json_annotation_distinct_from_missing(project_root: Path):
    manifest = _setup_doc_and_manifest(
        project_root,
        "annotations/TEST-001.json",
        '{"broken json',
    )
    output = project_root / "outputs" / "report.json"
    log_file = project_root / "outputs" / "eval.jsonl"
    rc, out, err = _run_cli(
        [
            "run",
            "--manifest", str(manifest),
            "--output", str(output),
            "--log-file", str(log_file),
        ],
        cwd=project_root,
    )
    assert rc == 0, f"stderr={err}"
    report = json.loads(output.read_text(encoding="utf-8"))
    pd = report["per_doc"][0]
    # 降级 reason 必须是"坏标注"专属，而不是与缺标注混用的 no_annotation
    assert pd["metrics"]["figure_caption_precision"]["reason"] == "annotation_invalid_json"
    assert pd["metrics"]["chunk_boundary_precision"]["reason"] == "annotation_invalid_json"
    assert pd["metrics"]["table_caption_precision"]["reason"] == "annotation_invalid_json"
    assert pd["metrics"]["heading_order_precision"]["reason"] == "annotation_invalid_json"
    # 公开 per_doc 落盘消费状态
    assert pd["annotation_status"] == "annotation_invalid_json"
    # 结构化日志有对应事件
    log_lines = [
        json.loads(line)
        for line in log_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    events = [e.get("event") for e in log_lines]
    assert "annotation_invalid_json" in events


def test_missing_annotation_keeps_no_annotation(project_root: Path):
    """缺标注的既有契约不变：reason 仍是 no_annotation（不被 C15 改写）。"""
    manifest = _setup_doc_and_manifest(project_root, None, None)
    output = project_root / "outputs" / "report.json"
    rc, _, err = _run_cli(
        ["run", "--manifest", str(manifest), "--output", str(output)],
        cwd=project_root,
    )
    assert rc == 0, f"stderr={err}"
    report = json.loads(output.read_text(encoding="utf-8"))
    pd = report["per_doc"][0]
    assert pd["metrics"]["figure_caption_precision"]["reason"] == "no_annotation"
    assert pd["annotation_status"] == "missing"


# ---------- 端到端：doc_id 不匹配拒绝消费（C16） ----------


def test_annotation_doc_id_mismatch_refused(project_root: Path):
    annotation = {
        "annotation_version": "1.0",
        "doc_id": "OTHER-DOC",  # 与清单 TEST-001 不符
        "chunk_boundary_anchors": [
            {"marker": "Hello world", "position": "after", "reason": "test"},
        ],
    }
    manifest = _setup_doc_and_manifest(
        project_root,
        "annotations/TEST-001.json",
        json.dumps(annotation, ensure_ascii=False),
    )
    output = project_root / "outputs" / "report.json"
    log_file = project_root / "outputs" / "eval.jsonl"
    rc, _, err = _run_cli(
        [
            "run",
            "--manifest", str(manifest),
            "--output", str(output),
            "--log-file", str(log_file),
        ],
        cwd=project_root,
    )
    assert rc == 0, f"stderr={err}"
    report = json.loads(output.read_text(encoding="utf-8"))
    pd = report["per_doc"][0]
    # 拒绝消费：指标为 null + 专属 reason，绝不用错误标注算出数值
    assert pd["annotation_status"] == "annotation_doc_id_mismatch"
    for key in (
        "figure_caption_precision",
        "chunk_boundary_precision",
        "table_caption_precision",
        "heading_order_precision",
    ):
        m = pd["metrics"][key]
        assert m["value"] is None, key
        assert m["reason"] == "annotation_doc_id_mismatch", key
    # 日志事件携带双侧 doc_id
    log_lines = [
        json.loads(line)
        for line in log_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    mismatch_events = [
        e for e in log_lines if e.get("event") == "annotation_doc_id_mismatch"
    ]
    assert len(mismatch_events) == 1
    assert mismatch_events[0]["doc_id"] == "TEST-001"
    assert mismatch_events[0]["annotation_doc_id"] == "OTHER-DOC"


def test_annotation_matching_doc_id_consumed(project_root: Path):
    """doc_id 匹配的标注正常消费（回归护栏：C16 不误伤合法标注）。"""
    annotation = {
        "annotation_version": "1.0",
        "doc_id": "TEST-001",
        "chunk_boundary_anchors": [
            {"marker": "ZZZ_NONEXISTENT", "position": "after", "reason": "test"},
        ],
    }
    manifest = _setup_doc_and_manifest(
        project_root,
        "annotations/TEST-001.json",
        json.dumps(annotation, ensure_ascii=False),
    )
    output = project_root / "outputs" / "report.json"
    rc, _, err = _run_cli(
        ["run", "--manifest", str(manifest), "--output", str(output), "--max-chars", "32"],
        cwd=project_root,
    )
    assert rc == 0, f"stderr={err}"
    report = json.loads(output.read_text(encoding="utf-8"))
    pd = report["per_doc"][0]
    assert pd["annotation_status"] == "loaded"
    # 标注被真实消费：marker 找不到 → 专属 reason 而非 no_annotation
    assert (
        pd["metrics"]["chunk_boundary_recall"]["reason"]
        == "no_ground_truth_anchors_in_stream"
    )


# ---------- C06：tolerance_chars 公开落盘 ----------


def test_report_carries_tolerance_chars(project_root: Path):
    manifest = _setup_doc_and_manifest(project_root, None, None)
    output = project_root / "outputs" / "report.json"
    rc, _, err = _run_cli(
        [
            "run",
            "--manifest", str(manifest),
            "--output", str(output),
            "--tolerance-chars", "45",
        ],
        cwd=project_root,
    )
    assert rc == 0, f"stderr={err}"
    report = json.loads(output.read_text(encoding="utf-8"))
    pd = report["per_doc"][0]
    assert pd["tolerance_chars"] == 45
    # 默认 30 同样落盘
    output2 = project_root / "outputs" / "report2.json"
    rc, _, err = _run_cli(
        ["run", "--manifest", str(manifest), "--output", str(output2)],
        cwd=project_root,
    )
    assert rc == 0, f"stderr={err}"
    report2 = json.loads(output2.read_text(encoding="utf-8"))
    assert report2["per_doc"][0]["tolerance_chars"] == 30
    # 新增键不破坏报告 Schema
    validate_file(output, "evaluation-report.schema.json")
    validate_file(output2, "evaluation-report.schema.json")
