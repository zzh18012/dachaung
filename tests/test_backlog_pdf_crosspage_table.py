r"""BACKLOG 候选 D（跨页表格拆分）根因合成复现（Round 1888，b 优先级）。

**特征锁定（characterization），不是期望行为规格**——锁定主线
docs/BACKLOG.md §3（候选 D：PDF 跨页表格被按页拆分，table 计数
+300%）在自跑线代码中的确切机制。手写最小双页线框表格 PDF
（xref 偏移程序化计算，不读 real-*、无外部 PDF 库）。

根因定位（app/parsers/fallback_parser.py）：
- :257 `for page_idx, page in enumerate(pdf.pages)` 逐页循环 +
  :291 `page.find_tables()` 逐页检测——**无任何跨页状态**
  （列宽/列 x 对齐/表头相似度信号都不采集），逻辑一张表跨页
  必拆成 N 个 table 元素
- 复合发现（BACKLOG 未记）：:260 `page.extract_words()` 不排除
  表格区域——单元格文本同时进 words 流，被 :184 短行启发式判成
  heading 元素（候选 C 机制在表格场景复现）→ 表格文本双重提取
  （table markdown + heading 元素各一份）
"""

from __future__ import annotations

from pathlib import Path

from app.parsers.fallback_parser import _parse_pdf

_XS = [100.0, 250.0, 400.0, 550.0]


def _grid_page_content(
    texts: list[tuple[float, float, str]],
) -> bytes:
    """一页内容流：2 行 × 3 列网格线 + 单元格文本（PDF 坐标自下而上）。"""
    ys = [700.0, 660.0, 620.0]
    parts = ["1 w 0 0 0 RG"]
    for y in ys:
        parts.append(f"{_XS[0]} {y:.1f} m {_XS[-1]} {y:.1f} l S")
    for x in _XS:
        parts.append(f"{x:.1f} {ys[-1]:.1f} m {x:.1f} {ys[0]:.1f} l S")
    for x, y, text in texts:
        parts.append(f"BT /F1 12 Tf {x:.1f} {y:.1f} Td ({text}) Tj ET")
    return "\n".join(parts).encode("latin-1")


def _build_pdf(contents: list[bytes]) -> bytes:
    n = len(contents)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n))
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode(),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for i, content in enumerate(contents):
        page_num = 4 + 2 * i
        objects[page_num] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> "
            f"/Contents {page_num + 1} 0 R >>"
        ).encode()
        objects[page_num + 1] = (
            b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"
        )
    total = 3 + 2 * n
    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for num in range(1, total + 1):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode() + objects[num] + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {total + 1}\n".encode() + b"0000000000 65535 f \n"
    for num in range(1, total + 1):
        out += f"{offsets[num]:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {total + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    return bytes(out)


def _make_cross_page_pdf(path: Path) -> None:
    """双页同列宽线框表：页 1 = 表头 + alpha 行；页 2 = beta/gamma 行
    （列 x 完全对齐——逻辑上是同一张表）。"""
    page1 = _grid_page_content(
        [
            (110, 668, "Name"), (260, 668, "Value"), (410, 668, "Note"),
            (110, 628, "alpha"), (260, 628, "1"), (410, 628, "first"),
        ]
    )
    page2 = _grid_page_content(
        [
            (110, 668, "beta"), (260, 668, "2"), (410, 668, "second"),
            (110, 628, "gamma"), (260, 628, "3"), (410, 628, "third"),
        ]
    )
    path.write_bytes(_build_pdf([page1, page2]))


def test_backlog_candD_cross_page_table_split_into_two_elements(tmp_path):
    """候选 D 机制：逻辑一张表跨两页（列 x 完全对齐）→ 拆成 2 个
    table 元素，各挂各的 page locator，无合并。"""
    pdf_path = tmp_path / "cross_page.pdf"
    _make_cross_page_pdf(pdf_path)
    elements, warnings = _parse_pdf(pdf_path, "sha" * 21, "doc-x", None)
    assert warnings == []
    tables = [e for e in elements if e.type == "table"]
    assert len(tables) == 2
    pages = [t.source_locator["page"] for t in tables]
    assert pages == [1, 2]
    # 列 x 对齐（同一张逻辑表）在 bbox 上完全一致，仍被拆分
    assert tables[0].source_locator["bbox"] == tables[1].source_locator["bbox"]
    # 内容被切成两半：表头行留在页 1
    assert "Name | Value | Note" in tables[0].content
    assert "alpha" in tables[0].content
    assert "beta" not in tables[0].content
    assert "beta" in tables[1].content and "gamma" in tables[1].content


def test_backlog_candD_page2_fragment_misrenders_header(tmp_path):
    """候选 D 后果：页 2 表片段的首行（beta 数据行）被 markdown
    渲染成表头行——跨页拆分不仅计数 +300%，语义也错位。"""
    pdf_path = tmp_path / "cross_page.pdf"
    _make_cross_page_pdf(pdf_path)
    elements, _ = _parse_pdf(pdf_path, "sha" * 21, "doc-x", None)
    tables = [e for e in elements if e.type == "table"]
    page2 = next(t for t in tables if t.source_locator["page"] == 2)
    lines = page2.content.splitlines()
    # _rows_to_markdown 把首行当 header：beta 数据行成了表头
    assert lines[0] == "| beta | 2 | second |"
    assert lines[1] == "| --- | --- | --- |"
    assert lines[2] == "| gamma | 3 | third |"
    assert page2.metadata["row_count"] == 2  # 逻辑表 4 行 → 每片只记 2


def test_backlog_table_cell_text_double_extracted_as_headings(tmp_path):
    """复合发现：单元格文本同时被 extract_words 抽走 → 每行单元格
    文本聚成一段 → 候选 C 短行启发式判 heading——表格文本双重提取
    （table markdown 一份 + heading 元素一份）。"""
    pdf_path = tmp_path / "cross_page.pdf"
    _make_cross_page_pdf(pdf_path)
    elements, _ = _parse_pdf(pdf_path, "sha" * 21, "doc-x", None)
    headings = [e for e in elements if e.type == "heading"]
    heading_texts = [e.content for e in headings]
    # 每页 2 行单元格文本 × 2 页 = 4 个 heading（全部重复表格内容）
    assert heading_texts == [
        "Name Value Note",
        "alpha 1 first",
        "beta 2 second",
        "gamma 3 third",
    ]
    assert all(e.metadata == {"level": 0, "heuristic": "short_line"}
               for e in headings)
