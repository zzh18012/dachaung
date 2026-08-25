r"""app/parsers/fallback_parser.py DOCX 边角测试 - 第六十八轮（Round 1491）。

新角度（probe 实证）真实手造 w:tbl + sdt/smartTag/move
家族扩展（R1490 开的静默丢文本面）：

- **真实 w:tbl 完整提取**：前后段落顺序保留，表格成
  markdown 管道格式 '| a1 | b1 |\\n| --- | --- |\\n
  | a2 | b2 |'，metadata row_count/col_count/
  source='python-docx'（edges4 只用 FakeTable mock，本
  轮首个真实手造 XML 表锁定）
- **⚠ sdt 内 w:tbl 整表丢弃**：docx_no_content（R1490
  的 sdt 丢段扩展到表）
- **⚠ smartTag 包裹 run 丢弃**：legacy 智能标签内文本
  丢（与 w:ins 同一"只读直接子 w:r"根因）
- **moveFrom/moveTo 全丢**：仅剩 '(空段落)' 占位
  （moveTo 虽包 w:t 同样不在直接子层）
- **w:tblHeader 不区分**：表头行标识不产生特殊元数
  据，首行照常作数据行（2x1）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

from tests.test_parsers_fallback_edges65 \
    import _build_docx

_TBL = (
    "<w:tbl><w:tr>"
    "<w:tc><w:p><w:r><w:t>a1</w:t>"
    "</w:r></w:p></w:tc>"
    "<w:tc><w:p><w:r><w:t>b1</w:t>"
    "</w:r></w:p></w:tc>"
    "</w:tr><w:tr>"
    "<w:tc><w:p><w:r><w:t>a2</w:t>"
    "</w:r></w:p></w:tc>"
    "<w:tc><w:p><w:r><w:t>b2</w:t>"
    "</w:r></w:p></w:tc>"
    "</w:tr></w:tbl>")


def _parse(tmp_path, name, px):
    p = tmp_path / name
    p.write_bytes(_build_docx(px))
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- 真实表格 ----------

def test_real_tbl_with_surroundings(
        tmp_path):
    doc = _parse(
        tmp_path, "tbl.docx",
        "<w:p><w:r><w:t>before</w:t>"
        "</w:r></w:p>" + _TBL
        + "<w:p><w:r><w:t>after</w:t>"
          "</w:r></w:p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "before"),
        ("table",
         "| a1 | b1 |\n| --- | --- |\n"
         "| a2 | b2 |"),
        ("paragraph", "after"),
    ]
    assert doc.elements[1].metadata == {
        "row_count": 2,
        "col_count": 2,
        "source": "python-docx",
    }
    assert doc.warnings == []


def test_tbl_header_row_not_special(
        tmp_path):
    doc = _parse(
        tmp_path, "th.docx",
        "<w:tbl><w:tr><w:trPr>"
        "<w:tblHeader/></w:trPr>"
        "<w:tc><w:p><w:r><w:t>hdr"
        "</w:t></w:r></w:p></w:tc>"
        "</w:tr><w:tr><w:tc><w:p>"
        "<w:r><w:t>data</w:t></w:r>"
        "</w:p></w:tc></w:tr></w:tbl>")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "table"
    assert e.metadata == {
        "row_count": 2,
        "col_count": 1,
        "source": "python-docx",
    }
    assert e.content == \
        "| hdr |\n| --- |\n| data |"


# ---------- sdt 扩展 ----------

def test_tbl_in_sdt_dropped(tmp_path):
    doc = _parse(
        tmp_path, "tsdt.docx",
        "<w:sdt><w:sdtContent>"
        + _TBL
        + "</w:sdtContent></w:sdt>")
    assert doc.elements == []
    assert [w.code for w in
            doc.warnings] == \
        ["docx_no_content"]


# ---------- 包裹标签家族 ----------

def test_smarttag_run_dropped(
        tmp_path):
    doc = _parse(
        tmp_path, "st.docx",
        "<w:p><w:r><w:t>keep </w:t>"
        "</w:r>"
        '<w:smartTag w:element="city">'
        "<w:r><w:t>tagged</w:t>"
        "</w:r></w:smartTag></w:p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "keep"),
    ]
    assert doc.warnings == []


def test_movefrom_moveto_all_dropped(
        tmp_path):
    doc = _parse(
        tmp_path, "mv.docx",
        "<w:p>"
        '<w:moveFrom w:id="1"><w:r>'
        "<w:delText>old</w:delText>"
        "</w:r></w:moveFrom>"
        '<w:moveTo w:id="2"><w:r>'
        "<w:t>new</w:t></w:r>"
        "</w:moveTo></w:p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "(空段落)"),
    ]
    assert doc.elements[0].metadata[
        "empty"] is True
    assert doc.warnings == []
