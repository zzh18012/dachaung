"""Stage 10 批次 4 测试：PDF 跨页表格保守合并（r36 授权，全合成夹具）。

裁决边界（登记行 Stage-10-Batch-4 AUTHORIZED）：
- 仅在相邻页对象具备唯一、可解释的连续性证据时合并；证据不足一律
  不合并；
- 证据 = 列网格逐边对齐（|Δ|<=2pt 且边界数相等）且（重复表头 或
  断版位置：前页片段底边在底部区 >=80% 页高、后页片段顶边在顶部
  区 <=20% 页高）；
- 测试只用合成跨页表格夹具（手写最小 PDF，零真实语料）。

坐标系注记：fixture 按 PDF 坐标（原点左下、y 向上）画线；正文断言
用 pdfplumber 顶起坐标换算后的分区阈值。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.parsers.fallback_parser import (
    FallbackParser,
    _plan_cross_page_merges,
    _xpage_continuation,
    _xpage_grid_matches,
)
from app.pipeline import process_single


# ---------- 合成夹具：多页最小 PDF + 线框表格 ----------

def _make_pdf(path: Path, page_streams: list[str]) -> Path:
    n = len(page_streams)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n))
    objs: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for stream in page_streams:
        content = stream.encode("latin-1")
        objs.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
            b" /Contents " + str(len(objs) + 2).encode() + b" 0 R"
            b" /Resources << /Font << /F1 3 0 R >> >> >>"
        )
        objs.append(
            b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"
        )
    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_pos = len(pdf)
    total = len(objs) + 1
    pdf += b"xref\n" + f"0 {total}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += (
        b"trailer\n<< /Size " + str(total).encode() + b" /Root 1 0 R >>\n"
        b"startxref\n" + str(xref_pos).encode() + b"\n%%EOF"
    )
    path.write_bytes(pdf)
    return path


def _table_stream(
    xs: list[float],
    ys: list[float],
    texts: dict[tuple[int, int], str],
) -> str:
    """画线框表格并放文本。

    xs：垂直线 x 坐标（升序）；ys：水平线 y 坐标（降序，ys[0] 为表格
    顶边、ys[-1] 为底边）；texts[(row, col)]：第 row 行第 col 列文本。
    """
    ops: list[str] = ["0.5 w"]
    for y in ys:
        ops.append(f"{xs[0]} {y} m {xs[-1]} {y} l S")
    for x in xs:
        ops.append(f"{x} {ys[-1]} m {x} {ys[0]} l S")
    for (r, c), text in sorted(texts.items()):
        x = xs[c] + 4
        y = ys[r + 1] + 4
        ops.append(f"BT /F1 10 Tf {x} {y} Td ({text}) Tj ET")
    return "\n".join(ops) + "\n"


_XS3 = [100, 200, 300, 400]


def _grid_texts(rows: list[list[str]]) -> dict[tuple[int, int], str]:
    return {
        (r, c): cell for r, row in enumerate(rows) for c, cell in enumerate(row)
    }


def _parse_tables(pdf_path: Path):
    h = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    doc = FallbackParser().parse(pdf_path, source_hash=h)
    return doc, [e for e in doc.elements if e.type == "table"]


# ---------- 合并行为（PDF 端到端） ----------

def test_repeated_header_continuation_merges(tmp_path: Path):
    """p1 中部表 + p2 中部表（均不在断版分区）但 p2 首行与链首表头
    逐字相同 → 唯一证据=重复表头 → 合并且丢弃重复表头。"""
    p1 = _table_stream(
        _XS3, [400, 340, 280, 220],
        _grid_texts([["H1", "H2", "H3"], ["a1", "a2", "a3"], ["b1", "b2", "b3"]]),
    )
    p2 = _table_stream(
        _XS3, [500, 440, 380, 320],
        _grid_texts([["H1", "H2", "H3"], ["c1", "c2", "c3"], ["d1", "d2", "d3"]]),
    )
    pdf = _make_pdf(tmp_path / "hdr.pdf", [p1, p2])
    doc, tables = _parse_tables(pdf)
    assert len(tables) == 1
    t = tables[0]
    assert t.metadata["cross_page_merge"] is True
    assert t.metadata["continuation_pages"] == [2]
    assert t.metadata["dropped_header_rows"] == 1
    assert t.metadata["row_count"] == 5  # 3 + (3-1)
    assert t.source_locator["page"] == 1  # locator 保持首片段起始页
    # 重复表头只出现一次；两页数据行都在
    assert t.content.count("H1") == 1
    assert "b3" in t.content and "d3" in t.content


def test_break_position_merges_without_header(tmp_path: Path):
    """p1 底部区表 + p2 顶部区表（网格一致、首行不同）→ 证据=断版位置
    → 合并、不丢行。"""
    p1 = _table_stream(
        _XS3, [300, 240, 180, 120],
        _grid_texts([["H1", "H2", "H3"], ["a1", "a2", "a3"], ["b1", "b2", "b3"]]),
    )
    p2 = _table_stream(
        _XS3, [740, 660, 580],
        _grid_texts([["c1", "c2", "c3"], ["d1", "d2", "d3"]]),
    )
    pdf = _make_pdf(tmp_path / "pos.pdf", [p1, p2])
    doc, tables = _parse_tables(pdf)
    assert len(tables) == 1
    t = tables[0]
    assert t.metadata["dropped_header_rows"] == 0
    assert t.metadata["continuation_pages"] == [2]
    assert t.metadata["row_count"] == 5  # 3 + 2 全保留
    assert "c1" in t.content and "b1" in t.content


def test_column_grid_mismatch_no_merge(tmp_path: Path):
    """p2 列边界平移 10pt（> 2pt 容差）→ 网格证据不成立 → 不合并，
    即便处于断版分区。"""
    p1 = _table_stream(
        _XS3, [300, 240, 180, 120],
        _grid_texts([["H1", "H2", "H3"], ["a1", "a2", "a3"]]),
    )
    p2 = _table_stream(
        [100, 210, 310, 400], [740, 660, 580],
        _grid_texts([["H1", "H2", "H3"], ["c1", "c2", "c3"]]),
    )
    pdf = _make_pdf(tmp_path / "grid.pdf", [p1, p2])
    doc, tables = _parse_tables(pdf)
    assert len(tables) == 2
    assert all("cross_page_merge" not in t.metadata for t in tables)


def test_mid_page_same_grid_no_merge(tmp_path: Path):
    """两页中部同网格表格、首行不同、均不在断版分区 → 证据不足 →
    不合并（保守默认）。"""
    rows = _grid_texts([["x1", "x2", "x3"], ["y1", "y2", "y3"]])
    p1 = _table_stream(_XS3, [400, 340, 280], rows)
    p2 = _table_stream(_XS3, [500, 440, 380], _grid_texts([["z1", "z2", "z3"], ["w1", "w2", "w3"]]))
    pdf = _make_pdf(tmp_path / "mid.pdf", [p1, p2])
    doc, tables = _parse_tables(pdf)
    assert len(tables) == 2


def test_three_page_chain_merges(tmp_path: Path):
    """跨 3 页链：p1 底部区 → p2 整页片段（顶部+底部区均满足）→
    p3 顶部区；全部网格一致、无重复表头 → 位置证据逐段成立。"""
    p1 = _table_stream(
        _XS3, [260, 190, 120],
        _grid_texts([["H1", "H2", "H3"], ["a1", "a2", "a3"]]),
    )
    p2 = _table_stream(
        _XS3, [740, 420, 100],
        _grid_texts([["b1", "b2", "b3"], ["c1", "c2", "c3"]]),
    )
    p3 = _table_stream(
        _XS3, [740, 660, 580],
        _grid_texts([["d1", "d2", "d3"], ["e1", "e2", "e3"]]),
    )
    pdf = _make_pdf(tmp_path / "chain.pdf", [p1, p2, p3])
    doc, tables = _parse_tables(pdf)
    assert len(tables) == 1
    t = tables[0]
    assert t.metadata["continuation_pages"] == [2, 3]
    assert t.metadata["row_count"] == 6
    assert t.source_locator["page"] == 1


def test_header_only_fragment_not_merged(tmp_path: Path):
    """p2 仅一行与链首表头相同的文本（无数据行）→ 表头证据要求
    len(rows)>=2 → 不合并。"""
    p1 = _table_stream(
        _XS3, [400, 340, 280, 220],
        _grid_texts([["H1", "H2", "H3"], ["a1", "a2", "a3"], ["b1", "b2", "b3"]]),
    )
    p2 = _table_stream(_XS3, [500, 440], _grid_texts([["H1", "H2", "H3"]]))
    pdf = _make_pdf(tmp_path / "hdronly.pdf", [p1, p2])
    doc, tables = _parse_tables(pdf)
    assert len(tables) == 2


def test_page_gap_no_merge(tmp_path: Path):
    """中间隔一页无表格（页号差 2）→ 不合并，即便两端在断版分区。"""
    p1 = _table_stream(
        _XS3, [300, 240, 180, 120],
        _grid_texts([["H1", "H2", "H3"], ["a1", "a2", "a3"]]),
    )
    blank = "BT /F1 10 Tf 100 400 Td (only text) Tj ET\n"
    p3 = _table_stream(
        _XS3, [740, 660, 580],
        _grid_texts([["c1", "c2", "c3"], ["d1", "d2", "d3"]]),
    )
    pdf = _make_pdf(tmp_path / "gap.pdf", [p1, blank, p3])
    doc, tables = _parse_tables(pdf)
    assert len(tables) == 2


def test_second_table_on_continuation_page_no_merge(tmp_path: Path):
    """p2 首个表格在中部（顶部区不成立）→ p1 链关闭；同页其后的
    第二个表格页号不 +1，永不成为续页片段 → 三个表全部保持独立
    （保守）。注：顶区表若为页内首表则可与前页合并，属位置证据的
    正常语义，非误合并。"""
    p1 = _table_stream(
        _XS3, [300, 240, 180, 120],
        _grid_texts([["H1", "H2", "H3"], ["a1", "a2", "a3"]]),
    )
    first_mid = _table_stream(
        _XS3, [500, 440, 380],
        _grid_texts([["m1", "m2", "m3"], ["n1", "n2", "n3"]]),
    )
    second_below = _table_stream(
        _XS3, [360, 280, 200],
        _grid_texts([["c1", "c2", "c3"], ["d1", "d2", "d3"]]),
    )
    pdf = _make_pdf(tmp_path / "second.pdf", [p1, first_mid + second_below])
    doc, tables = _parse_tables(pdf)
    assert len(tables) == 3
    assert all("cross_page_merge" not in t.metadata for t in tables)


def test_merged_document_passes_pipeline_schema(tmp_path: Path):
    """合并产物经完整管线（schema 校验 + 契约检查 + 分块）零错误。"""
    p1 = _table_stream(
        _XS3, [300, 240, 180, 120],
        _grid_texts([["H1", "H2", "H3"], ["a1", "a2", "a3"], ["b1", "b2", "b3"]]),
    )
    p2 = _table_stream(
        _XS3, [740, 660, 580],
        _grid_texts([["H1", "H2", "H3"], ["c1", "c2", "c3"]]),
    )
    pdf = _make_pdf(tmp_path / "pipe.pdf", [p1, p2])
    document, errors = process_single(
        pdf, None, parser_name="fallback", max_chars=800, write_json=False
    )
    assert errors == []
    assert document is not None
    tables = [e for e in document.elements if e.type == "table"]
    assert len(tables) == 1
    assert tables[0].metadata["cross_page_merge"] is True
    # 合并表参与分块且 source_element_ids 非空（关键不变量）
    assert all(c.source_element_ids for c in document.chunks)


# ---------- 判定纯函数单元 ----------

def _rec(page, edges, rows, top, bottom, height=792.0):
    return {
        "page": page,
        "col_edges": tuple(edges),
        "rows": rows,
        "top": top,
        "bottom": bottom,
        "page_height": height,
    }


def test_grid_tolerance_boundary():
    a = (100.0, 200.0, 300.0)
    assert _xpage_grid_matches(a, (102.0, 202.0, 300.0))  # |Δ|=2 恰容差内
    assert not _xpage_grid_matches(a, (102.5, 202.0, 300.0))  # 2.5 超容差
    assert not _xpage_grid_matches(a, (100.0, 200.0))  # 边界数不同


def test_header_normalization_ignores_ws_and_case():
    tail = _rec(1, (100, 200), [["Name", "Qty"], ["a", "1"]], 100.0, 100.0)
    cand = _rec(
        2, (100, 200), [["  NAME  ", "  Qty  "], ["b", "2"]], 50.0, 50.0
    )
    ok, drop = _xpage_continuation(tail, "name|qty", cand)
    assert ok is True and drop is True


def test_planner_gap_page_closes_chain():
    recs = [
        _rec(1, (100, 200), [["h", "h"], ["a", "1"]], 700.0, 100.0),
        _rec(3, (100, 200), [["b", "2"], ["c", "3"]], 60.0, 20.0),
    ]
    assert _plan_cross_page_merges(recs) == []


def test_planner_single_fragment_no_group():
    recs = [_rec(1, (100, 200), [["h", "h"], ["a", "1"]], 400.0, 300.0)]
    assert _plan_cross_page_merges(recs) == []
