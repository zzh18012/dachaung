"""pipeline 错误路径测试。

聚焦 `process_single` / `validate_only` / `get_parser` 的错误返回与异常分支。
happy path 测试在 test_pipeline_integration.py；helper 测试在 test_pipeline_helpers.py。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.pipeline import get_parser, process_single, validate_only
from tests._synthetic_docs import build_minimal_docx, build_minimal_pdf


# ---------- get_parser ----------


def test_get_parser_unknown_name_raises_value_error():
    with pytest.raises(ValueError) as exc:
        get_parser("unknown_parser")
    assert "未知 parser" in str(exc.value)


def test_get_parser_all_known_names_return_parser_instances():
    """6 个已知 parser 名称都应返回不同类型的实例（不带 image_output_dir）。"""
    from app.parsers.fallback_parser import FallbackParser
    from app.parsers.html_parser import HtmlParser
    from app.parsers.ipynb_parser import IpynbParser
    from app.parsers.kreuzberg_parser import KreuzbergParser
    from app.parsers.markdown_parser import MarkdownParser
    from app.parsers.text_parser import TextParser

    cases = {
        "fallback": FallbackParser,
        "kreuzberg": KreuzbergParser,
        "markdown": MarkdownParser,
        "html": HtmlParser,
        "text": TextParser,
        "ipynb": IpynbParser,
    }
    for name, cls in cases.items():
        p = get_parser(name)
        assert isinstance(p, cls), f"parser {name} 应是 {cls.__name__}"


def test_get_parser_fallback_accepts_image_output_dir(tmp_path: Path):
    """fallback parser 接收 image_output_dir 参数。"""
    p = get_parser("fallback", image_output_dir=tmp_path / "imgs")
    assert p is not None
    # 内部应记录了 image_output_dir（不是 None）
    # 不直接 assert 内部字段，避免脆性；只要构造不报错就行


# ---------- validate_only 错误路径 ----------


def test_validate_only_missing_file(tmp_path: Path):
    """缺文件 → (False, 错误信息)。"""
    ok, msg = validate_only(tmp_path / "nope.json")
    assert ok is False
    assert "nope" in msg or "不存在" in msg or "找不到" in msg or "Not found" in msg.lower()


def test_validate_only_invalid_json(tmp_path: Path):
    """非 JSON 文件 → (False, "JSON 解析失败")。"""
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    ok, msg = validate_only(bad)
    assert ok is False
    assert "JSON" in msg or "解析" in msg


def test_validate_only_wrong_shape_json(tmp_path: Path):
    """合法 JSON 但 schema 不对 → (False, schema 错误信息)。"""
    bad = tmp_path / "wrong.json"
    bad.write_text(json.dumps({"wrong": "shape"}), encoding="utf-8")
    ok, msg = validate_only(bad)
    assert ok is False
    # 消息应包含 schema 或 validation 字样
    assert "schema" in msg.lower() or "validation" in msg.lower() or "required" in msg.lower()


# ---------- process_single: no_extracted_elements ----------


def _build_blank_pdf(tmp_path: Path) -> Path:
    """构造一个无 content stream 的最小 PDF（pdfplumber 能打开但提取不到任何东西）。"""
    objs = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        # 无 /Contents 字段 → pdfplumber 提取不到文本
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>',
    ]
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
    p = tmp_path / "blank.pdf"
    p.write_bytes(pdf)
    return p


def test_process_single_no_extracted_elements_blank_pdf(tmp_path: Path):
    """无 content 的 PDF → no_extracted_elements 错误。"""
    src = _build_blank_pdf(tmp_path)
    out = tmp_path / "out.json"
    document, errors = process_single(src, out, parser_name="fallback")
    assert document is None
    assert errors  # 至少一条
    codes = [e.code for e in errors]
    assert "no_extracted_elements" in codes
    # details 应记录 warnings 和 source_type
    err = next(e for e in errors if e.code == "no_extracted_elements")
    assert err.details is not None
    assert err.details.get("source_type") == "pdf"
    assert "warnings" in err.details


# ---------- process_single: chunker_failed（monkeypatch）----------


def test_process_single_chunker_failure_yields_structured_error(tmp_path: Path):
    """分块器抛异常 → chunker_failed 错误，不崩溃。"""
    src = build_minimal_docx(tmp_path / "synthetic.docx")
    out = tmp_path / "out.json"

    import app.chunkers.structural as structural_mod

    original_chunk = structural_mod.StructuralChunker.chunk

    def boom(self, document):
        raise RuntimeError("forced chunker failure")

    structural_mod.StructuralChunker.chunk = boom  # type: ignore[assignment]
    try:
        document, errors = process_single(src, out, parser_name="fallback")
    finally:
        structural_mod.StructuralChunker.chunk = original_chunk  # type: ignore[assignment]

    assert document is None
    assert errors
    assert errors[0].code == "chunker_failed"
    assert "forced chunker failure" in errors[0].message
    # details 应有 exception_type
    assert errors[0].details.get("exception_type") == "RuntimeError"
    # 不应残留半成品
    assert not out.exists()


# ---------- process_single: unexpected_parser_error（monkeypatch）----------


def test_process_single_unexpected_parser_exception_yields_structured_error(tmp_path: Path):
    """parser 抛非 ParserError 异常 → unexpected_parser_error，不崩溃。"""
    src = build_minimal_docx(tmp_path / "synthetic.docx")
    out = tmp_path / "out.json"

    import app.pipeline as pl

    original_get_parser = pl.get_parser

    class _BoomParser:
        name = "boom"
        version = "0"

        def parse(self, path, source_hash):
            raise ValueError("forced unexpected parser error")

    def fake_get_parser(name, image_output_dir=None):
        if name == "fallback":
            return _BoomParser()
        return original_get_parser(name, image_output_dir=image_output_dir)

    pl.get_parser = fake_get_parser  # type: ignore[assignment]
    try:
        document, errors = process_single(src, out, parser_name="fallback")
    finally:
        pl.get_parser = original_get_parser  # type: ignore[assignment]

    assert document is None
    assert errors
    assert errors[0].code == "unexpected_parser_error"
    assert "ValueError" in errors[0].message
    assert "forced unexpected parser error" in errors[0].message
    # details 应有 parser_name
    assert errors[0].details.get("parser_name") == "fallback"


# ---------- process_single: write_failed（monkeypatch）----------


def test_process_single_write_failure_yields_structured_error(tmp_path: Path):
    """写盘失败（OSError）→ write_failed 错误，document 仍可返回。

    注：process_single 在写盘失败时返回 (None, errors)，document 被丢弃。
    用 pathlib.Path.open 的 monkeypatch 触发（process_single 走的是 Path.open，
    不是 builtins.open）。
    """
    src = build_minimal_docx(tmp_path / "synthetic.docx")
    out = tmp_path / "out.json"

    original_path_open = Path.open

    def fake_path_open(self, *args, **kwargs):
        mode = args[0] if args else kwargs.get("mode", "r")
        if "out.json" in str(self) and "w" in str(mode):
            raise OSError("forced write failure")
        return original_path_open(self, *args, **kwargs)

    Path.open = fake_path_open  # type: ignore[assignment]
    try:
        document, errors = process_single(src, out, parser_name="fallback")
    finally:
        Path.open = original_path_open  # type: ignore[assignment]

    assert document is None
    assert errors
    assert errors[0].code == "write_failed"
    assert "forced write failure" in errors[0].message
    assert errors[0].details.get("path") == str(out)


# ---------- process_single: 不写盘（write_json=False）----------


def test_process_single_no_write_returns_document_without_creating_file(tmp_path: Path):
    """write_json=False 时不应创建 output_path 文件。"""
    src = build_minimal_docx(tmp_path / "synthetic.docx")
    out = tmp_path / "out.json"
    document, errors = process_single(src, out, parser_name="fallback", write_json=False)
    assert errors == []
    assert document is not None
    assert not out.exists()


def test_process_single_no_output_path_does_not_write(tmp_path: Path):
    """output_path=None 时也不写盘。"""
    src = build_minimal_docx(tmp_path / "synthetic.docx")
    document, errors = process_single(src, None, parser_name="fallback")
    assert errors == []
    assert document is not None


# ---------- process_single: kreuzberg parser 路径不出 chunker_failed ----------


def test_process_single_kreuzberg_on_pdf_works(tmp_path: Path):
    """kreuzberg 走 PDF 路径不应崩溃（即使给不出 bbox）。"""
    src = build_minimal_pdf(tmp_path / "synthetic.pdf", text="(Hello)")
    out = tmp_path / "out.json"
    document, errors = process_single(src, out, parser_name="kreuzberg")
    assert document is not None
    assert errors == []
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source_type"] == "pdf"
