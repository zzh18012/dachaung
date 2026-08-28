"""版本语义 PR 验收测试：精确 schema 快照（ChatGPT 5.6 Sol 2026-08-27 指示）。

版本映射与规则：
- UDM 0.1.0：仅旧 PDF/DOCX 形状，不允许 source_spans；0.2.0 才允许新类型/spans
- manifest 1.0：仅旧格式与旧 expectation 键；1.1 才允许 markdown/html/text/ipynb 与新键
- report 1.1：旧结构；含 expectation_checks / per-doc check 键必须标 1.2
- 旧资产（冻结 manifest / 旧结构报告 / 旧 PDF/DOCX pipeline 输出）继续通过
- 【2026-08-28 批次 2 修订（契约 docs/chunker-source-spans-contract.md §1.9）】
  chunker 填充 source_spans 后，新 pipeline 输出一律 0.2.0；
  0.1.0 保持合法读取格式（已落盘旧产物继续可校验）
- 【2026-08-28 裁决追认后的纠正】版本描述 writer 能力而非单文档内容：
  span-aware writer 对全部来源（含无 span 的 pdf/docx）统一输出 0.2.0
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.models import (
    SCHEMA_VERSION_EXTENDED,
    Chunk,
    Document,
    Element,
)
from app.schema import validate as validate_udm
from evaluation.manifest import load_manifest
from evaluation.schema import EvalSchemaError

ROOT = Path(__file__).resolve().parent.parent


# ---------- UDM 精确快照 ----------

def _udm(source_type: str, schema_version: str, locator: dict, spans: bool = False) -> dict:
    chunk = {
        "chunk_id": "d::c0000",
        "text": "t",
        "source_element_ids": ["e1"],
        "metadata": {},
    }
    if spans:
        chunk["source_spans"] = [{"element_id": "e1", "start": 0, "end": 1}]
    return {
        "schema_version": schema_version,
        "document_id": "doc1",
        "source_path": "samples/x",
        "source_type": source_type,
        "source_hash": "a" * 64,
        "parser_name": "p",
        "parser_version": "1",
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "parent_id": None,
                "source_locator": locator,
                "content": "x",
                "resource_path": None,
                "confidence": 1.0,
                "metadata": {},
            }
        ],
        "chunks": [chunk],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def test_udm_010_rejects_markdown():
    doc = _udm("markdown", "0.1.0", {"line": 1})
    with pytest.raises(Exception):
        validate_udm(doc)


def test_udm_020_accepts_markdown():
    doc = _udm("markdown", "0.2.0", {"line": 1}, spans=True)
    validate_udm(doc)


def test_udm_010_rejects_source_spans():
    doc = _udm("docx", "0.1.0", {"paragraph_index": 0}, spans=True)
    with pytest.raises(Exception):
        validate_udm(doc)


def test_udm_old_pdf_docx_shape_still_passes():
    validate_udm(_udm("pdf", "0.1.0", {"page": 1, "bbox": [0, 0, 1, 1]}))
    validate_udm(_udm("docx", "0.1.0", {"paragraph_index": 0}))
    # 0.2.0 是超集：旧形状在 0.2.0 下也合法
    validate_udm(_udm("pdf", "0.2.0", {"page": 1}))


def test_udm_unknown_version_rejected():
    with pytest.raises(Exception):
        validate_udm(_udm("pdf", "0.3.0", {"page": 1}))


# ---------- Document.to_dict 动态版本 ----------

def _model_doc(source_type: str, locator: dict, spans: bool = False) -> Document:
    el = Element(
        element_id="e1", type="paragraph", content="x", source_locator=locator
    )
    chunk = Chunk(
        chunk_id="d::c0000",
        text="t",
        source_element_ids=["e1"],
        source_spans=[{"element_id": "e1", "start": 0, "end": 1}] if spans else [],
    )
    return Document(
        document_id="doc1",
        source_path="samples/x",
        source_type=source_type,
        source_hash="a" * 64,
        parser_name="p",
        parser_version="1",
        elements=[el],
        chunks=[chunk],
    )


def test_all_types_emit_020_writer_capability():
    """2026-08-28 裁决追认后的纠正：版本描述 writer 能力，非内容驱动。

    旧断言（pdf/docx 无 span → 0.1.0）被取代：span-aware writer 对全部
    来源统一输出 0.2.0，即使某文档碰巧没有非空 span；0.1.0 仅为 legacy
    读入格式（见 test_udm_old_pdf_docx_shape_still_passes）。
    """
    d = _model_doc("pdf", {"page": 1}).to_dict()
    assert d["schema_version"] == SCHEMA_VERSION_EXTENDED == "0.2.0"
    validate_udm(d)


def test_new_types_emit_020():
    d = _model_doc("markdown", {"line": 1}).to_dict()
    assert d["schema_version"] == SCHEMA_VERSION_EXTENDED == "0.2.0"
    validate_udm(d)


def test_spans_force_020():
    d = _model_doc("docx", {"paragraph_index": 0}, spans=True).to_dict()
    assert d["schema_version"] == "0.2.0"
    validate_udm(d)


# ---------- manifest 精确快照 ----------

def _manifest(tmp_path: Path, version: str, source_type: str = "markdown",
              expectations: dict | None = None) -> Path:
    (tmp_path / "doc.md").write_text("# x\n", encoding="utf-8")
    doc: dict = {"doc_id": "D1", "path": "doc.md", "source_type": source_type}
    if expectations is not None:
        doc["expectations"] = expectations
    data = {
        "manifest_version": version,
        "devset_status": "incomplete",
        "documents": [doc],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_manifest_10_rejects_new_expectation_keys(tmp_path: Path):
    exp = {"element_count_by_type": {"heading": 1}, "forbidden_markers": ["y"]}
    with pytest.raises(EvalSchemaError):
        load_manifest(_manifest(tmp_path, "1.0", "docx", exp), project_root=tmp_path)


def test_manifest_10_rejects_new_formats(tmp_path: Path):
    (tmp_path / "doc.pdf").write_bytes(b"%PDF-1.4 minimal")
    with pytest.raises(EvalSchemaError):
        load_manifest(
            _manifest(tmp_path, "1.0", "markdown", None), project_root=tmp_path
        )


def test_manifest_11_accepts_same_content(tmp_path: Path):
    exp = {"element_count_by_type": {"heading": 1}, "forbidden_markers": ["y"]}
    m = load_manifest(
        _manifest(tmp_path, "1.1", "markdown", exp), project_root=tmp_path
    )
    assert m.documents[0].source_type == "markdown"


def test_manifest_unknown_version_rejected(tmp_path: Path):
    with pytest.raises(Exception):
        load_manifest(_manifest(tmp_path, "1.2"), project_root=tmp_path)


# ---------- 冻结旧资产继续通过 ----------

def test_frozen_old_manifest_loads():
    p = ROOT / "samples/private/devset/manifest.json"
    if not p.is_file():
        pytest.skip("samples/private 为本机资产，不存在时跳过")
    m = load_manifest(p, project_root=ROOT)
    assert m.manifest_version == "1.0"
    assert all(d.source_type in ("pdf", "docx") for d in m.documents)


def test_pipeline_output_now_020_with_spans(tmp_path: Path):
    """真实 fallback pipeline 的 DOCX 输出为 0.2.0 且全部 chunk 带 span。

    2026-08-28 批次 2 修订（契约 §1.9）：原"输出仍 0.1.0（与冻结基线
    字节一致）"断言被取代——0.1.0 是合法读取格式（旧产物继续可校验，
    见 test_udm_old_pdf_docx_shape_still_passes），新运行一律 0.2.0。
    """
    pytest.importorskip("app.pipeline")
    devset = ROOT / "samples/private/devset/manifest.json"
    if not devset.is_file():
        pytest.skip("samples/private 为本机资产，不存在时跳过")
    m = load_manifest(devset, project_root=ROOT)
    docx_entry = next((d for d in m.documents if d.source_type == "docx"), None)
    if docx_entry is None:
        pytest.skip("devset 无 docx 样本")
    from app.pipeline import process_single

    out_stub = tmp_path / "out.json"
    document, errors = process_single(
        docx_entry.resolved_path, out_stub,
        parser_name="fallback", max_chars=800, write_json=False,
    )
    assert not errors and document is not None
    d = document.to_dict()
    assert d["schema_version"] == "0.2.0"
    assert d["chunks"], "docx 样本应有 chunk"
    for chunk in d["chunks"]:
        assert "source_spans" in chunk
        assert chunk["source_spans"], "批次 2 后所有 chunk 都带非空 span"
    validate_udm(d)
