r"""app/pipeline 生成式坏 PDF 错误路径测试（Round 1548）。

新角度：'pdfplumber_open_failed' 错误码此前只在
evaluation 层断言过；pipeline 层的坏 PDF 路径测试依赖
samples/private（常年 SKIPPED）——本轮用**生成字节**在
pipeline 层真实锁定（不依赖私有样例）：

- **纯文本垃圾字节** → doc=None + 单条
  pdfplumber_open_failed（message 含 'No /Root
  object!'、details.exception_type='PdfminerException'、
  details.path 为输入路径）
- **空文件** → 同上
- **仅头+EOF** → 同上
- **有效 PDF 中途截断** → 同码但 message 含
  'Unexpected EOF'（与无 Root 可区分）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _err(tmp_path, name, data,
         needle):
    p = tmp_path / name
    p.write_bytes(data)
    doc, errors = process_single(
        p, write_json=False)
    assert doc is None
    assert len(errors) == 1
    e = errors[0]
    assert e.code == \
        "pdfplumber_open_failed"
    assert needle in e.message
    assert e.details[
        "exception_type"] == \
        "PdfminerException"
    assert str(p) in str(
        e.details["path"])


def test_garbage_bytes(tmp_path):
    _err(
        tmp_path, "garbage.pdf",
        b"this is not a pdf at"
        b" all, just plain text",
        "No /Root object!")


def test_empty_file(tmp_path):
    _err(tmp_path, "empty.pdf",
         b"", "No /Root object!")


def test_header_only(tmp_path):
    _err(tmp_path, "headeronly.pdf",
         b"%PDF-1.4\n%%EOF",
         "No /Root object!")


def test_truncated(tmp_path):
    full = (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog"
        b" /Pages 2 0 R >>\n"
        b"endobj\n"
        b"2 0 obj\n"
        b"<< /Type /Pages"
        b" /Kids [3 0 R]"
        b" /Count 1 >>\n"
        b"endobj\n"
        b"3 0 obj\n"
        b"<< /Type /Page"
        b" /Parent 2 0 R"
        b" /Contents 4 0 R >>\n"
        b"endobj\n"
        b"4 0 obj\n"
        b"<< /Length 50 >>\n"
        b"stream\nBT /F1 12 Tf"
        b" 72 700 Td (BODY) Tj ET"
        b"\nendstream\n"
        b"endobj\n"
        b"trailer << /Root 1 0 R"
        b" /Size 5 >>\n%%EOF")
    _err(tmp_path, "trunc.pdf",
         full[:len(full) // 2],
         "Unexpected EOF")
