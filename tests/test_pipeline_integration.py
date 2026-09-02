"""集成测试：端到端跑通 PDF/DOCX → JSON → 校验。

策略：
- 用 stdlib 合成的 PDF/DOCX 必跑（验证管道全程）
- 真实样例（samples/private/sample.pdf 等）如果存在则跑**强断言**；不存在则 SKIPPED（绝不伪造）
- 错误样例（blank/corrupt/unsupported）：明确 SKIPPED 如果不存在
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from app.chunkers import normalize_text
from app.pipeline import process_single, validate_only
from app.schema import is_valid


SAMPLES_PRIVATE = Path(__file__).resolve().parent.parent / "samples" / "private"


# ---------- 共用合成样例 ----------

def _build_minimal_docx(tmp_path: Path) -> Path:
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    doc_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Chapter 1</w:t></w:r></w:p>
    <w:p><w:r><w:t>Hello world. This is paragraph one.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Second paragraph with more content.</w:t></w:r></w:p>
  </w:body>
</w:document>'''
    p = tmp_path / "synthetic.docx"
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc_xml)
    return p


def _build_minimal_pdf(tmp_path: Path, text: str = "Hello Chapter 1 World") -> Path:
    objs = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    ]
    stream = b'BT /F1 24 Tf 100 700 Td (' + text.encode('latin-1') + b') Tj ET'
    objs.append(b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream')
    objs.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    pdf = b'%PDF-1.4\n'
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += f'{i} 0 obj\n'.encode() + body + b'\nendobj\n'
    xref_pos = len(pdf)
    n = len(objs) + 1
    pdf += b'xref\n' + f'0 {n}\n'.encode() + b'0000000000 65535 f \n'
    for off in offsets:
        pdf += f'{off:010d} 00000 n \n'.encode()
    pdf += b'trailer\n<< /Size ' + str(n).encode() + b' /Root 1 0 R >>\nstartxref\n'
    pdf += str(xref_pos).encode() + b'\n%%EOF'
    p = tmp_path / "synthetic.pdf"
    p.write_bytes(pdf)
    return p


# ---------- 合成样例端到端 ----------

def test_end_to_end_synthetic_docx(tmp_path: Path):
    src = _build_minimal_docx(tmp_path)
    out = tmp_path / "out.json"
    document, errors = process_single(src, out, parser_name="fallback", max_chars=200)
    assert errors == [], f"应无错误，但得到: {[e.to_dict() for e in errors]}"
    assert document is not None
    assert out.is_file(), "输出 JSON 未生成"

    data = json.loads(out.read_text(encoding="utf-8"))
    assert is_valid(data)
    assert data["source_type"] == "docx"
    assert data["parser_name"] == "fallback"
    assert len(data["elements"]) >= 2
    assert len(data["chunks"]) >= 1
    for c in data["chunks"]:
        assert len(c["source_element_ids"]) >= 1


def test_end_to_end_synthetic_pdf(tmp_path: Path):
    src = _build_minimal_pdf(tmp_path)
    out = tmp_path / "out.json"
    document, errors = process_single(src, out, parser_name="fallback", max_chars=200)
    assert errors == []
    assert document is not None

    data = json.loads(out.read_text(encoding="utf-8"))
    assert is_valid(data)
    assert data["source_type"] == "pdf"
    for e in data["elements"]:
        assert e["source_locator"].get("page", 0) >= 1


def test_pipeline_validates_before_writing(tmp_path: Path):
    """如果 schema 校验失败，绝不能写盘。"""
    src = _build_minimal_docx(tmp_path)
    out = tmp_path / "out.json"

    import app.pipeline as pl

    original_validate = pl.validate

    def boom(_):
        from app.schema import SchemaValidationError
        raise SchemaValidationError("forced", [{"path": [], "message": "forced"}])

    pl.validate = boom  # type: ignore[assignment]
    try:
        document, errors = process_single(src, out, parser_name="fallback")
    finally:
        pl.validate = original_validate  # type: ignore[assignment]

    assert document is None
    assert errors and errors[0].code == "schema_validation_failed"
    assert not out.exists(), "校验失败时不应写盘"


def test_missing_file_yields_structured_error(tmp_path: Path):
    src = tmp_path / "nope.pdf"
    out = tmp_path / "out.json"
    document, errors = process_single(src, out)
    assert document is None
    assert len(errors) == 1
    assert errors[0].code == "file_not_found"


def test_unsupported_extension_yields_structured_error(tmp_path: Path):
    src = tmp_path / "x.txt"
    src.write_text("hello", encoding="utf-8")
    out = tmp_path / "out.json"
    document, errors = process_single(src, out)
    assert document is None
    assert errors and errors[0].code == "unsupported_type"


def test_kreuzberg_pipeline_also_runs(tmp_path: Path):
    """Kreuzberg 路径也要能跑通（即使它给出的是启发式 elements）。"""
    src = _build_minimal_docx(tmp_path)
    out = tmp_path / "out.json"
    document, errors = process_single(src, out, parser_name="kreuzberg")
    assert errors == []
    assert document is not None
    data = json.loads(out.read_text(encoding="utf-8"))
    assert is_valid(data)
    codes = [w["code"] for w in data["warnings"]]
    assert "kreuzberg_no_structured_elements" in codes


def test_validate_only_on_existing_json(tmp_path: Path):
    src = _build_minimal_docx(tmp_path)
    out = tmp_path / "out.json"
    process_single(src, out)
    ok, msg = validate_only(out)
    assert ok, msg


def test_validate_only_on_bad_json(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"wrong": "shape"}), encoding="utf-8")
    ok, msg = validate_only(p)
    assert not ok
    assert "schema" in msg.lower() or "validation" in msg.lower()


# ---------- CLI subprocess 测试（新 parse/validate 子命令） ----------

def _run_cli(args: list[str]) -> tuple[int, str, str]:
    # Windows venv 布局不存在（如 Linux CI）时回退当前解释器（pytest 即 venv python）
    cand = Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe"
    venv_python = str(cand) if cand.is_file() else sys.executable
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [venv_python, "-m", "app.cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(Path(__file__).resolve().parent.parent),
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_cli_parse_mode_end_to_end(tmp_path: Path):
    src = _build_minimal_docx(tmp_path)
    out = tmp_path / "out.json"
    rc, stdout, stderr = _run_cli(["parse", str(src), "-o", str(out), "--max-chars", "200"])
    assert rc == 0, f"stderr={stderr}"
    assert "[OK]" in stdout
    assert out.is_file()


def test_cli_validate_subcommand(tmp_path: Path):
    """validate 是独立子命令：python -m app.cli validate <json>"""
    src = _build_minimal_docx(tmp_path)
    out = tmp_path / "out.json"
    _run_cli(["parse", str(src), "-o", str(out)])
    rc, stdout, stderr = _run_cli(["validate", str(out)])
    assert rc == 0, f"stderr={stderr}"
    assert "[OK]" in stdout


def test_cli_legacy_positional_no_longer_works():
    """子命令现在是 required=True：直接传文件名应当报错。"""
    rc, stdout, stderr = _run_cli(["some.pdf", "-o", "x.json"])
    assert rc != 0
    assert "invalid choice" in stderr or "required" in stderr.lower()


def test_cli_missing_file_returns_nonzero_no_residual(tmp_path: Path):
    """不存在文件：非零退出 + 结构化错误 + 无残留 JSON"""
    out = tmp_path / "out.json"
    rc, stdout, stderr = _run_cli(["parse", str(tmp_path / "nope.pdf"), "-o", str(out)])
    assert rc != 0
    assert "file_not_found" in stderr
    assert not out.exists(), "失败时不应残留半成品 JSON"


def test_cli_corrupt_pdf_returns_nonzero(tmp_path: Path):
    """损坏 PDF：非零退出 + 结构化错误"""
    bad = tmp_path / "corrupt.pdf"
    bad.write_bytes(b"%PDF-1.4\nthis is not a valid pdf body\n%%EOF")
    out = tmp_path / "out.json"
    rc, stdout, stderr = _run_cli(["parse", str(bad), "-o", str(out)])
    assert rc != 0
    assert "errors" in stderr
    assert not out.exists()


def test_cli_unsupported_extension_returns_nonzero(tmp_path: Path):
    bad = tmp_path / "x.txt"
    bad.write_text("hello")
    out = tmp_path / "out.json"
    rc, stdout, stderr = _run_cli(["parse", str(bad), "-o", str(out)])
    assert rc != 0
    assert "unsupported_type" in stderr
    assert not out.exists()


# ---------- 真实样例：强断言 ----------

@pytest.fixture
def real_pdf() -> Path | None:
    p = SAMPLES_PRIVATE / "sample.pdf"
    return p if p.is_file() else None


@pytest.fixture
def real_docx() -> Path | None:
    p = SAMPLES_PRIVATE / "sample.docx"
    return p if p.is_file() else None


def _assert_strong_pdf_properties(data: dict) -> None:
    """真实 PDF 的强断言：不能只看'没崩溃'。"""
    # 1. 至少有标题或正文
    types = [e["type"] for e in data["elements"]]
    assert "heading" in types or "paragraph" in types, "PDF 必须提取到标题或正文"

    # 2. 每个文本/表格/题注/图片元素的 source_locator 必须有 page ≥ 1
    for e in data["elements"]:
        loc = e.get("source_locator", {})
        pg = loc.get("page", 0)
        assert pg >= 1, f"PDF element {e['element_id']} page 必须 ≥ 1，实际 {pg}"

    # 3. 文本元素必须有 4 个数字的 bbox（heading/paragraph/caption）
    for e in data["elements"]:
        if e["type"] in ("heading", "paragraph", "caption"):
            bbox = e["source_locator"].get("bbox")
            assert bbox is not None, f"PDF 文本 element {e['element_id']} 缺 bbox"
            assert len(bbox) == 4, f"PDF bbox 必须是 4 个数：{bbox}"
            for v in bbox:
                assert isinstance(v, (int, float)) and v == v, f"bbox 数值非法：{bbox}"

    # 4. 至少识别到 1 个 table（manifest 预期 1 张）
    tables = [e for e in data["elements"] if e["type"] == "table"]
    assert len(tables) >= 1, "PDF 应当识别到至少 1 张表格"

    # 5. 至少识别到 1 个 image（manifest 预期 1 张）
    images = [e for e in data["elements"] if e["type"] == "image"]
    assert len(images) >= 1, "PDF 应当识别到至少 1 张图片"

    # 6. 图片必须有实存的 resource_path
    for img in images:
        rp = img.get("resource_path")
        assert rp and rp not in ("(unsaved)", "(unrendered)"), \
            f"PDF 图片 {img['element_id']} resource_path 未指向实存文件"
        assert Path(rp).is_file(), f"PDF 图片资源文件实际不存在：{rp}"
        assert Path(rp).stat().st_size > 0, f"PDF 图片资源文件为空：{rp}"

    # 7. chunk 的 source_element_ids 必须全部指向真实存在的 element
    elem_ids = {e["element_id"] for e in data["elements"]}
    for c in data["chunks"]:
        for sid in c["source_element_ids"]:
            assert sid in elem_ids, f"chunk {c['chunk_id']} 引用了不存在的 element：{sid}"


def _assert_strong_docx_properties(data: dict) -> None:
    """真实 DOCX 的强断言。"""
    types = [e["type"] for e in data["elements"]]
    # 1. 至少有 heading + paragraph + table + caption + image
    assert "heading" in types, "DOCX 应当识别到标题"
    assert "paragraph" in types, "DOCX 应当识别到正文"
    assert "table" in types, "DOCX 应当识别到表格"
    assert "image" in types, "DOCX 应当识别到图片"
    assert "caption" in types, "DOCX 应当识别到题注"

    # 2. locator 用结构路径，绝不能伪造 page/bbox
    for e in data["elements"]:
        loc = e.get("source_locator", {})
        assert "page" not in loc, f"DOCX element {e['element_id']} 不应有 page：{loc}"
        assert "bbox" not in loc, f"DOCX element {e['element_id']} 不应有 bbox：{loc}"
        # 至少要有一种结构标识
        if e["type"] == "table":
            assert "table_index" in loc, f"DOCX table 缺 table_index：{loc}"
        else:
            assert "paragraph_index" in loc or "table_index" in loc, \
                f"DOCX element {e['element_id']} 缺结构定位：{loc}"

    # 3. 图片必须有 relationship_id 和实存的 resource_path
    for img in [e for e in data["elements"] if e["type"] == "image"]:
        loc = img["source_locator"]
        assert "relationship_id" in loc, f"DOCX 图片缺 relationship_id：{loc}"
        rp = img.get("resource_path")
        assert rp and rp != "(unsaved)", f"DOCX 图片 {img['element_id']} 未保存"
        assert Path(rp).is_file(), f"DOCX 图片资源文件实际不存在：{rp}"
        assert Path(rp).stat().st_size > 0, f"DOCX 图片资源文件为空：{rp}"

    # 4. chunk 引用完整性
    elem_ids = {e["element_id"] for e in data["elements"]}
    for c in data["chunks"]:
        for sid in c["source_element_ids"]:
            assert sid in elem_ids, f"chunk {c['chunk_id']} 引用了不存在的 element：{sid}"


def _assert_no_loss_no_duplicate(data: dict) -> None:
    """分块前后正文（统一规范化后）必须不丢不重。

    表格、图片、题注被设计为独立 chunk（caption 单独 isolate，table/caption 也 isolate），
    所以它们也参与拼接。image 不参与（chunker._element_text 返回空）。
    """
    expected = " ".join(
        e["content"] for e in data["elements"]
        if e["type"] != "image" and e.get("content")
    )
    actual = " ".join(c["text"] for c in data["chunks"])
    assert normalize_text(expected) == normalize_text(actual), (
        f"分块前后文本不一致：\n"
        f"  expected ({len(normalize_text(expected))} chars)\n"
        f"  actual   ({len(normalize_text(actual))} chars)\n"
        f"  diff (expected - actual): {set(normalize_text(expected).split()) - set(normalize_text(actual).split())}\n"
        f"  diff (actual - expected): {set(normalize_text(actual).split()) - set(normalize_text(expected).split())}"
    )


@pytest.mark.parametrize("parser_name", ["fallback", "kreuzberg"])
def test_real_sample_pdf_strong(real_pdf, tmp_path: Path, parser_name: str):
    if real_pdf is None:
        pytest.skip("samples/private/sample.pdf 未提供")
    out = tmp_path / "real_pdf_out.json"
    document, errors = process_single(real_pdf, out, parser_name=parser_name, max_chars=800)
    assert errors == [], f"真实 PDF 解析失败：{[e.to_dict() for e in errors]}"
    assert document is not None
    data = json.loads(out.read_text(encoding="utf-8"))
    assert is_valid(data), "真实 PDF 输出未通过 Schema 校验"

    if parser_name == "fallback":
        _assert_strong_pdf_properties(data)
        _assert_no_loss_no_duplicate(data)
    else:
        # Kreuzberg 路径不要求 page/bbox 精确，但要求清晰 warning
        codes = [w["code"] for w in data["warnings"]]
        assert "kreuzberg_no_structured_elements" in codes or \
               "kreuzberg_pdf_no_bbox" in codes, \
               "Kreuzberg 路径必须返回清晰的 no_structured 或 no_bbox warning"


@pytest.mark.parametrize("parser_name", ["fallback", "kreuzberg"])
def test_real_sample_docx_strong(real_docx, tmp_path: Path, parser_name: str):
    if real_docx is None:
        pytest.skip("samples/private/sample.docx 未提供")
    out = tmp_path / "real_docx_out.json"
    document, errors = process_single(real_docx, out, parser_name=parser_name, max_chars=800)
    assert errors == []
    assert document is not None
    data = json.loads(out.read_text(encoding="utf-8"))
    assert is_valid(data), "真实 DOCX 输出未通过 Schema 校验"

    if parser_name == "fallback":
        _assert_strong_docx_properties(data)
        _assert_no_loss_no_duplicate(data)
    else:
        codes = [w["code"] for w in data["warnings"]]
        assert "kreuzberg_no_structured_elements" in codes


def test_real_sample_pdf_cli_end_to_end(real_pdf, tmp_path: Path):
    """通过 CLI 子进程跑真实 PDF + 用 validate 子命令校验。"""
    if real_pdf is None:
        pytest.skip("samples/private/sample.pdf 未提供")
    out = tmp_path / "pdf_cli.json"
    rc, stdout, stderr = _run_cli(["parse", str(real_pdf), "-o", str(out)])
    assert rc == 0, f"PDF CLI 失败：{stderr}"
    assert "[OK]" in stdout
    rc2, stdout2, stderr2 = _run_cli(["validate", str(out)])
    assert rc2 == 0, f"PDF validate 失败：{stderr2}"


def test_real_sample_docx_cli_end_to_end(real_docx, tmp_path: Path):
    if real_docx is None:
        pytest.skip("samples/private/sample.docx 未提供")
    out = tmp_path / "docx_cli.json"
    rc, stdout, stderr = _run_cli(["parse", str(real_docx), "-o", str(out)])
    assert rc == 0, f"DOCX CLI 失败：{stderr}"
    rc2, stdout2, stderr2 = _run_cli(["validate", str(out)])
    assert rc2 == 0, f"DOCX validate 失败：{stderr2}"


# ---------- 错误样例（manifest 中的 blank/corrupt/unsupported） ----------

def test_real_blank_pdf(real_pdf, tmp_path: Path):
    """空白 PDF：非零退出 + 结构化错误 + 不残留 JSON。manifest: 'blank.pdf': explicit warning or structured error"""
    blank = SAMPLES_PRIVATE / "blank.pdf"
    if not blank.is_file():
        pytest.skip("samples/private/blank.pdf 未提供（错误样例可选）")
    out = tmp_path / "blank_out.json"
    rc, stdout, stderr = _run_cli(["parse", str(blank), "-o", str(out)])
    assert rc != 0, "空白 PDF 必须非零退出"
    assert "errors" in stderr
    assert not out.exists(), "空白 PDF 不应残留 JSON"


def test_real_corrupt_pdf(tmp_path: Path):
    corrupt = SAMPLES_PRIVATE / "corrupt.pdf"
    if not corrupt.is_file():
        pytest.skip("samples/private/corrupt.pdf 未提供（错误样例可选）")
    out = tmp_path / "corrupt_out.json"
    rc, stdout, stderr = _run_cli(["parse", str(corrupt), "-o", str(out)])
    assert rc != 0
    assert "errors" in stderr
    assert not out.exists()


def test_real_unsupported_txt(tmp_path: Path):
    txt = SAMPLES_PRIVATE / "unsupported.txt"
    if not txt.is_file():
        pytest.skip("samples/private/unsupported.txt 未提供（错误样例可选）")
    out = tmp_path / "txt_out.json"
    rc, stdout, stderr = _run_cli(["parse", str(txt), "-o", str(out)])
    assert rc != 0
    assert "unsupported_type" in stderr
    assert not out.exists()
