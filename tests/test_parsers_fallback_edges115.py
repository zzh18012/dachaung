r"""app/parsers_fallback PDF 边角测试 - 第一百一十五轮（Round 1545）。

新角度（probe 实证）对象引用形式家族（此前轮次
/Length、字体、资源全为直接值或常规间接流引用——本
轮锁非常规引用形式）：

- **/Length 间接引用**（指向数字对象 6 0 R）→ 照常
- **/Contents 指向普通 dict（非流）** → 容忍：[] + 仅
  pdf_no_text_extracted（静默无文本）
- **/Font 直接内联字体 dict**（非间接引用）→ 照常
- **多级继承**：MediaBox/Resources 在祖父 /Pages、中
  间节点裸、叶子省略 → 照常（两级向上查找成功）
- **页 dict 缺失 /Type /Page** → 页不被识别：[] + 仅
  pdf_no_text_extracted（静默跳页）
- **⚠ 流 dict 带 /F 100**（文件规格标志）→ [] +
  word_extract_failed + no_text 双警告——未知键无害但
  /F 是保留语义键，触发外部文件路径解析并整体失败
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

_C = "BT /F1 12 Tf 72 700 Td (BODY) Tj ET"
_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")


def _parse(tmp_path, name, objs,
           size):
    pdf = b"%PDF-1.4\n"
    for oid in sorted(objs):
        o = objs[oid]
        if isinstance(o, str):
            o = o.encode("latin-1")
        pdf += (f"{oid} 0 obj\n"
                .encode("latin-1")
                + o + b"\nendobj\n")
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size " + str(size).encode()
            + b" >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return FallbackParser().parse(
        p, compute_file_hash(p))


def _ok(tmp_path, name, objs, size):
    doc = _parse(tmp_path, name, objs,
                 size)
    assert [(e.content,
             e.source_locator["page"])
            for e in doc.elements] == [
        ("BODY", 1)]
    assert doc.warnings == []


def _lost(tmp_path, name, objs, size,
          codes):
    doc = _parse(tmp_path, name, objs,
                 size)
    assert doc.elements == []
    assert [w.code for w in
            doc.warnings] == codes


def test_length_indirect(tmp_path):
    _ok(tmp_path, "lenref.pdf", {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R]"
           " /Count 1 >>",
        3: "<< /Type /Page"
           " /Parent 2 0 R"
           " /MediaBox [0 0 612 792]"
           " /Resources << /Font"
           " << /F1 5 0 R >> >>"
           " /Contents 4 0 R >>",
        4: f"<< /Length 6 0 R >>"
           f"\nstream\n{_C}\n"
           f"endstream",
        5: _FONT,
        6: str(len(_C)),
    }, 7)


def test_contents_nonstream(tmp_path):
    _lost(tmp_path, "dictcont.pdf", {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R]"
           " /Count 1 >>",
        3: "<< /Type /Page"
           " /Parent 2 0 R"
           " /MediaBox [0 0 612 792]"
           " /Resources << /Font"
           " << /F1 5 0 R >> >>"
           " /Contents 4 0 R >>",
        4: "<< /Foo 1 >>",
        5: _FONT,
    }, 6, ["pdf_no_text_extracted"])


def test_inline_font_dict(tmp_path):
    _ok(tmp_path, "inlinefont.pdf", {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R]"
           " /Count 1 >>",
        3: f"<< /Type /Page"
           f" /Parent 2 0 R"
           f" /MediaBox [0 0 612 792]"
           f" /Resources << /Font"
           f" << /F1 {_FONT} >> >>"
           f" /Contents 4 0 R >>",
        4: f"<< /Length"
           f" {len(_C)} >>"
           f"\nstream\n{_C}\n"
           f"endstream",
    }, 5)


def test_multilevel_inheritance(
        tmp_path):
    _ok(tmp_path, "multinh.pdf", {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: ("<< /Type /Pages"
            " /Kids [10 0 R]"
            " /Count 1"
            " /MediaBox [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 5 0 R >> >> >>"),
        10: "<< /Type /Pages"
            " /Parent 2 0 R"
            " /Kids [3 0 R]"
            " /Count 1 >>",
        3: "<< /Type /Page"
           " /Parent 10 0 R"
           " /Contents 4 0 R >>",
        4: f"<< /Length"
           f" {len(_C)} >>"
           f"\nstream\n{_C}\n"
           f"endstream",
        5: _FONT,
    }, 11)


def test_page_missing_type(tmp_path):
    _lost(tmp_path, "notype.pdf", {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R]"
           " /Count 1 >>",
        3: f"<< /Parent 2 0 R"
           f" /MediaBox [0 0 612 792]"
           f" /Resources << /Font"
           f" << /F1 5 0 R >> >>"
           f" /Contents 4 0 R >>",
        4: f"<< /Length"
           f" {len(_C)} >>"
           f"\nstream\n{_C}\n"
           f"endstream",
        5: _FONT,
    }, 6, ["pdf_no_text_extracted"])


def test_stream_F_flag(tmp_path):
    _lost(tmp_path, "streamF.pdf", {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R]"
           " /Count 1 >>",
        3: "<< /Type /Page"
           " /Parent 2 0 R"
           " /MediaBox [0 0 612 792]"
           " /Resources << /Font"
           " << /F1 5 0 R >> >>"
           " /Contents 4 0 R >>",
        4: f"<< /Length"
           f" {len(_C)} /F 100 >>"
           f"\nstream\n{_C}\n"
           f"endstream",
        5: _FONT,
    }, 6, ["pdfplumber_word_extract"
           "_failed",
           "pdf_no_text_extracted"])
