r"""pipeline fallback 分派：仅 pdf/docx、
unsupported_type 与假 PDF 失败（Round 1754）。

新角度：R1753 锁失败分类学——**fallback
只认 .pdf/.docx（大小写不敏感）：其余扩
展名一律 unsupported_type（details 含
suffix）；缺 .pdf 先 file_not_found；内
容非 PDF 的 .PDF → pdfplumber_open_failed
（details exception_type PdfminerException）**
零覆盖：

- **.md/.txt/.html/.ipynb/.xyz 显式
  fallback**：全 unsupported_type，message
  '仅支持 .pdf / .docx'
- **d.MD + parser markdown**：正常解析
  （source_type 'markdown'，大写扩展归
  一）
- **假内容 .PDF**：pdfplumber_open_failed
  + message 'No /Root object!'
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_fallback_rejects_other_extensions(tmp_path):
    for name in ["d.md", "d.txt", "d.html",
                 "d.ipynb", "d.xyz"]:
        p = tmp_path / name
        p.write_text("x", encoding="utf-8")
        doc, errors = process_single(
            p, write_json=False)
        assert doc is None, name
        e = errors[0]
        assert e.code == "unsupported_type", name
        assert e.message == (
            f"不支持的文件扩展名: {p.suffix}，"
            "仅支持 .pdf / .docx"), name
        assert e.details == {
            "path": str(p), "suffix": p.suffix}, name


def test_uppercase_md_explicit_parser(tmp_path):
    p = tmp_path / "d.MD"
    p.write_text("## T\n\nx\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert doc.source_type == "markdown"
    assert [(e.type, e.content) for e in doc.elements] == [
        ("heading", "T"), ("paragraph", "x")]


def test_fake_pdf_open_failed(tmp_path):
    p = tmp_path / "d.PDF"
    p.write_text("x", encoding="utf-8")
    doc, errors = process_single(p, write_json=False)
    assert doc is None
    e = errors[0]
    assert e.code == "pdfplumber_open_failed"
    assert "No /Root object" in e.message
    assert e.details["exception_type"] == (
        "PdfminerException")
    assert e.details["path"] == str(p)
