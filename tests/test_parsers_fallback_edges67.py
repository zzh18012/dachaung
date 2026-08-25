r"""app/parsers/fallback_parser.py DOCX 边角测试 - 第六十七轮（Round 1490）。

新角度（probe 实证）修订/内容控件 XML 家族（edges1-66 未
碰过；与评测 silent_drop 高度相关的静默丢文本面）：

- **⚠ w:ins 修订插入文本被静默丢弃**：'<w:ins>' 包裹的
  w:r 在 Word 中是**可见文本**，但 paragraph.text 只读
  直接子 w:r → 'keep inserted' 只得 'keep'（真实修订
  文档会丢插入内容）
- **w:del/delText 丢弃（正确）**：delText 非 w:t，删除
  文本不入 content
- **⚠ w:sdt 内容控件整段丢弃**：sdtContent 内 w:p 不在
  body 直接子层 → 'outside'/'inside' 只剩 'outside'
  （Word 表单模板常态结构）
- **全 sdt 文档 → docx_no_content**：整份文档包在内容控
  件里解析为空
- **仅 ins+del 段 → '(空段落)' 占位**：empty=True 元数
  据占位 element（非跳过）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

from tests.test_parsers_fallback_edges65 \
    import _build_docx


def _parse(tmp_path, name, px):
    p = tmp_path / name
    p.write_bytes(_build_docx(px))
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- 修订（tracked changes） ----------

def test_ins_wrapped_run_dropped(
        tmp_path):
    doc = _parse(
        tmp_path, "ins.docx",
        "<w:p><w:r><w:t>keep </w:t></w:r>"
        '<w:ins w:id="1" w:author="a">'
        "<w:r><w:t>inserted</w:t></w:r>"
        "</w:ins></w:p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "keep"),
    ]
    assert doc.warnings == []


def test_del_wrapped_deltext_dropped(
        tmp_path):
    doc = _parse(
        tmp_path, "del.docx",
        "<w:p><w:r><w:t>keep</w:t></w:r>"
        '<w:del w:id="2" w:author="a">'
        "<w:r><w:delText>gone"
        "</w:delText></w:r>"
        "</w:del></w:p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "keep"),
    ]
    assert doc.warnings == []


def test_ins_then_del_only_empty_para(
        tmp_path):
    doc = _parse(
        tmp_path, "ind.docx",
        "<w:p>"
        '<w:ins w:id="1"><w:r><w:t>new'
        "</w:t></w:r></w:ins>"
        '<w:del w:id="2"><w:r>'
        "<w:delText>old</w:delText></w:r>"
        "</w:del></w:p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "(空段落)"),
    ]
    assert doc.elements[0].metadata == {
        "level": 0, "style": None,
        "empty": True,
    }
    assert doc.warnings == []


# ---------- 内容控件（sdt） ----------

def test_sdt_paragraph_dropped(
        tmp_path):
    doc = _parse(
        tmp_path, "sdt.docx",
        "<w:p><w:r><w:t>outside</w:t>"
        "</w:r></w:p>"
        "<w:sdt><w:sdtPr>"
        '<w:alias w:val="ctl"/></w:sdtPr>'
        "<w:sdtContent><w:p><w:r>"
        "<w:t>inside</w:t></w:r></w:p>"
        "</w:sdtContent></w:sdt>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "outside"),
    ]
    assert doc.warnings == []


def test_all_sdt_document_no_content(
        tmp_path):
    doc = _parse(
        tmp_path, "allsdt.docx",
        "<w:sdt><w:sdtContent>"
        "<w:p><w:pPr><w:pStyle "
        'w:val="Heading1"/></w:pPr>'
        "<w:r><w:t>in sdt</w:t></w:r>"
        "</w:p></w:sdtContent></w:sdt>")
    assert doc.elements == []
    assert [w.code for w in
            doc.warnings] == \
        ["docx_no_content"]
