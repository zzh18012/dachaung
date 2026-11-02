# -*- coding: utf-8 -*-
"""W5 text v2 fallback 测试（r99 §十二 15 项实现门）。

冻结契约面：
- 架构 geometry-first / text-fallback-per-page（§八）；
- 唯一 text 配置 tl_xtr1_5 完整 mapping 冻结（§九）；
- text 候选走 r7 门链（gate1/gate2/pathological-oversize override，
  §十二-4/5/6）；
- stacked option B：>=2 题注锚关联 → 拒发射 + 零 ownership（§十二-7/8）；
- 单题注正常发射（§十二-9）；
- 题注保护词 / 缺 provenance 词不吸收（§十二-10/11）；
- gate words-inside = cell-semantic 可归属词计数，bbox-only 词不计入
  （§十 / §十二-12/13）；
- source-char deficit=0 守恒 fixture（§十二-14）；
- text fallback 不活跃时 geometry 路径输出与 r7 面结构逐字节一致
  （无 detection 键，§十二-15）。

纯函数面（helpers）+ 全路径面（monkeypatch pdfplumber.open + TableFinder
stub，走 FallbackParser.parse 真实生产代码路径）。
"""

from __future__ import annotations

import types

import pytest

from app.parsers import fallback_parser as fpm
from app.parsers.fallback_parser import (
    TABLE_TEXT_SETTINGS,
    _is_stacked_ambiguous_table,
    _table_caption_anchors,
)

FROZEN_SETTINGS = {
    "vertical_strategy": "text",
    "horizontal_strategy": "lines",
    "text_x_tolerance": 1.5,
}

PAGE_W, PAGE_H = 612.0, 792.0
PAGE_AREA = PAGE_W * PAGE_H


# ---------- 构造器 ----------

def _word(text: str, x0: float, top: float, x1: float, bottom: float,
          with_chars: bool = True) -> dict:
    w = {"text": text, "x0": float(x0), "x1": float(x1),
         "top": float(top), "bottom": float(bottom)}
    if with_chars:
        n = max(len(text), 1)
        cw = (w["x1"] - w["x0"]) / n
        w["chars"] = [
            {"x0": w["x0"] + i * cw, "x1": w["x0"] + (i + 1) * cw,
             "top": w["top"], "bottom": w["bottom"]}
            for i in range(n)
        ]
    return w


def _tile_cells(x0: float, top: float, x1: float, bottom: float,
                ncols: int, nrows: int) -> list[list[float]]:
    xs = [x0 + (x1 - x0) * i / ncols for i in range(ncols + 1)]
    ys = [top + (bottom - top) * i / nrows for i in range(nrows + 1)]
    return [[xs[c], ys[r], xs[c + 1], ys[r + 1]]
            for r in range(nrows) for c in range(ncols)]


def _tile_rows(prefix: str, ncols: int, nrows: int) -> list[list[str]]:
    return [[f"{prefix}{r * ncols + c}" for c in range(ncols)]
            for r in range(nrows)]


def _tile_body_words(prefix: str, cells: list[list[float]],
                     with_chars: bool = True) -> list[dict]:
    words = []
    for i, cell in enumerate(cells):
        words.append(_word(f"{prefix}{i}", cell[0] + 5, cell[1] + 6,
                           (cell[0] + cell[2]) / 2, cell[1] + 20,
                           with_chars=with_chars))
    return words


def _caption_words(x: float, top: float, text: str = "Table 1: Results",
                   char_w: float = 7.0, h: float = 14.0) -> list[dict]:
    words = []
    cx = x
    for tok in text.split(" "):
        wdt = len(tok) * char_w
        words.append(_word(tok, cx, top, cx + wdt, top + h))
        cx += wdt + char_w
    return words


class _FakeTable:
    def __init__(self, rows: list[list[str]], bbox: list[float],
                 cells: list[list[float]]) -> None:
        self._rows = rows
        self.bbox = list(bbox)
        self.cells = [list(c) for c in cells]

    def extract(self) -> list[list[str]]:
        return [list(r) for r in self._rows]


class _FakePage:
    def __init__(self, words, geometry_tables=(), text_tables=(),
                 images=(), curves=(), rects=(), lines=()) -> None:
        self._words = list(words)
        self._geometry = list(geometry_tables)
        self.text_tables = list(text_tables)
        self.images = list(images)
        self.curves = list(curves)
        self.rects = list(rects)
        self.lines = list(lines)
        self.bbox = [0.0, 0.0, PAGE_W, PAGE_H]

    def extract_words(self, **kwargs):
        return list(self._words)

    def find_tables(self):
        return list(self._geometry)


def _parse(monkeypatch, tmp_path, pages) -> tuple:
    """monkeypatch pdfplumber.open + TableFinder，走真实 parse 全路径。

    返回 (Document, finder_calls)；finder_calls 每项为 TableFinder 收到的
    settings dict（拷贝），长度 = text fallback 实际构造次数。"""
    if fpm.TableFinder is None:
        pytest.skip("pdfplumber.table.TableFinder 不可用")
    calls: list[dict] = []

    class _TF:
        def __init__(self, page, settings):
            calls.append(dict(settings))
            self.tables = list(getattr(page, "text_tables", []))

    monkeypatch.setattr(fpm, "TableFinder", _TF)

    class _Ctx:
        def __init__(self, pgs):
            self.pages = pgs

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        fpm, "pdfplumber",
        types.SimpleNamespace(open=lambda p: _Ctx(pages)))
    pdf_path = tmp_path / "fake.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%%EOF\n")
    doc = fpm.FallbackParser().parse(str(pdf_path), source_hash="0" * 64)
    return doc, calls


def _tables(doc):
    return [e for e in doc.elements if e.type == "table"]


def _nontable_text(doc) -> str:
    return "\n".join(
        (e.content or "") for e in doc.elements
        if e.type not in ("table", "image"))


def _full_tile_page(body_prefix: str = "b", with_chars: bool = True,
                    geometry: bool = False, text: bool = True,
                    extra_words=(), images=()):
    bbox = [100.0, 200.0, 400.0, 400.0]
    cells = _tile_cells(*bbox, ncols=3, nrows=3)
    rows = _tile_rows(body_prefix, ncols=3, nrows=3)
    words = _tile_body_words(body_prefix, cells, with_chars=with_chars)
    words.extend(extra_words)
    tbl = _FakeTable(rows, bbox, cells)
    return _FakePage(
        words,
        geometry_tables=[tbl] if geometry else [],
        text_tables=[tbl] if text else [],
        images=list(images),
    )


# ---------- 纯函数面：锚行 / stacked ----------

def test_anchor_line_regex_and_line_grouping():
    words = (
        _caption_words(100, 300, "Table 2. More")
        + [_word("plain", 100, 400, 140, 414)]
        + _caption_words(100, 500, "Table 1: Results")
    )
    anchors = _table_caption_anchors(words)
    assert anchors == [[100, 300, 191, 314], [100, 500, 212, 514]]


def test_anchor_mega_word_and_non_caption():
    assert len(_table_caption_anchors(
        [_word("Table1:megaword", 100, 500, 260, 514)])) == 1
    assert _table_caption_anchors(
        [_word("hello world", 100, 500, 260, 514)]) == []


def test_stacked_predicate_windows():
    anchors = [[100, 300, 190, 314], [100, 500, 200, 514]]
    bbox = [90, 330, 210, 470]
    # 双向间距 330-314=16 / 500-470=30，均 <=60 且水平重叠 -> stacked
    assert _is_stacked_ambiguous_table(bbox, anchors) is True
    assert _is_stacked_ambiguous_table(bbox, [anchors[0]]) is False
    # 窗口外（300pt 间距）不关联
    assert _is_stacked_ambiguous_table(
        bbox, [[100, 40, 200, 54], [100, 740, 200, 754]]) is False
    # 锚完全在 bbox 内也关联（两个负间距 <=60）
    assert _is_stacked_ambiguous_table(
        bbox, [[110, 350, 180, 364], [110, 430, 180, 444]]) is True
    # 无水平重叠不关联
    assert _is_stacked_ambiguous_table(
        bbox, [[400, 330, 500, 344], [400, 460, 500, 474]]) is False


# ---------- §十二-3：冻结配置身份 ----------

def test_frozen_settings_identity():
    assert TABLE_TEXT_SETTINGS == FROZEN_SETTINGS
    assert set(TABLE_TEXT_SETTINGS) == set(FROZEN_SETTINGS)


def test_finder_receives_frozen_settings_copy(monkeypatch, tmp_path):
    page = _full_tile_page()
    doc, calls = _parse(monkeypatch, tmp_path, [page])
    assert len(calls) == 1
    assert calls[0] == FROZEN_SETTINGS
    # 生产传 dict(TABLE_TEXT_SETTINGS) 拷贝：stub 改写不回写模块常量
    calls[0]["vertical_strategy"] = "mutated"
    assert TABLE_TEXT_SETTINGS["vertical_strategy"] == "text"


# ---------- §十二-1/15：geometry 已接受 -> text 路径跳过 + r7 结构一致 ----------

def test_geometry_accepted_text_path_skipped(monkeypatch, tmp_path):
    page = _full_tile_page(geometry=True, text=True)
    doc, calls = _parse(monkeypatch, tmp_path, [page])
    assert calls == []  # TableFinder 未构造
    tbls = _tables(doc)
    assert len(tbls) == 1
    assert tbls[0].metadata == {
        "row_count": 3, "col_count": 3, "source": "pdfplumber",
    }  # 无 detection 键 = r7 面结构逐字节一致
    assert "b0" not in _nontable_text(doc)
    assert "b4" in tbls[0].content


def test_no_geometry_text_path_enabled(monkeypatch, tmp_path):
    page = _full_tile_page(geometry=False, text=True)
    doc, calls = _parse(monkeypatch, tmp_path, [page])
    assert len(calls) == 1
    tbls = _tables(doc)
    assert len(tbls) == 1
    assert tbls[0].metadata["detection"] == "text_fallback"
    assert "b0" in tbls[0].content
    assert "b0" not in _nontable_text(doc)


# ---------- §十二-4：gate1（栅格重叠 >=0.5 拒） ----------

def test_text_gate1_raster_overlap_rejected(monkeypatch, tmp_path):
    page = _full_tile_page(
        images=[{"x0": 100.0, "top": 200.0, "x1": 400.0, "bottom": 400.0}])
    doc, calls = _parse(monkeypatch, tmp_path, [page])
    assert len(calls) == 1
    assert _tables(doc) == []
    assert "b0" in _nontable_text(doc)  # 零 ownership
    assert any(e.type == "image" for e in doc.elements)


# ---------- §十二-5：gate2（单行拒） ----------

def test_text_gate2_single_row_rejected(monkeypatch, tmp_path):
    bbox = [100.0, 200.0, 400.0, 267.0]
    cells = _tile_cells(*bbox, ncols=3, nrows=1)
    rows = [["a", "b", "c"]]
    words = _tile_body_words("s", cells)  # 3 词
    words.append(_word("s3", 105, 240, 150, 254))
    page = _FakePage(
        words, text_tables=[_FakeTable(rows, bbox, cells)])
    doc, calls = _parse(monkeypatch, tmp_path, [page])
    assert len(calls) == 1
    assert _tables(doc) == []
    assert "s0" in _nontable_text(doc)


# ---------- §十二-6：pathological-oversize override 继承 ----------

def test_text_oversize_override_inherited(monkeypatch, tmp_path):
    # 单曲线簇覆盖 >1.0×page_area（632×812 > 612×792）
    page_curve = {"x0": -10.0, "top": -10.0, "x1": 622.0, "bottom": 802.0}
    bbox = [60.0, 200.0, 560.0, 340.0]
    cells = _tile_cells(*bbox, ncols=6, nrows=2)
    rows = _tile_rows("o", ncols=6, nrows=2)
    words = _tile_body_words("o", cells)  # 12 词
    page = _FakePage(
        words, curves=[page_curve],
        text_tables=[_FakeTable(rows, bbox, cells)])
    # 直接核验 wrapper：无 override 时 gate1 拒、override 解除
    from app.parsers.fallback_parser import _gate_pdf_table_with_override
    vec = [[-10.0, -10.0, 622.0, 802.0]]
    base = fpm._gate_pdf_table(bbox, 2, 6, 12, [], vec)
    assert base[0] is False
    accepted, warn, partial = _gate_pdf_table_with_override(
        bbox, 2, 6, 12, [], vec, PAGE_AREA)
    assert accepted and warn is not None and partial is False
    # 全路径：text 表经 override 接受并携带 detection 标记
    doc, calls = _parse(monkeypatch, tmp_path, [page])
    assert len(calls) == 1
    tbls = _tables(doc)
    assert len(tbls) == 1
    assert tbls[0].metadata["detection"] == "text_fallback"
    assert "o0" in tbls[0].content
    assert "o0" not in _nontable_text(doc)


# ---------- §十二-7/8：stacked option B 拒发射 + 零 ownership ----------

def _stacked_page() -> _FakePage:
    page = _full_tile_page()
    # 上锚（gap 200-144=56<=60）+ 下锚（gap 458-400=58<=60），均水平重叠
    page._words = (
        list(page._words)
        + _caption_words(120, 130, "Table 1: Setup")
        + _caption_words(120, 458, "Table 2: Results")
    )
    return page


def test_stacked_two_anchors_rejected(monkeypatch, tmp_path):
    page = _stacked_page()
    doc, calls = _parse(monkeypatch, tmp_path, [page])
    assert len(calls) == 1  # text 路径运行了（finder 构造）
    assert _tables(doc) == []
    # 两个题注都保留为 caption 元素（未吞并）
    caps = [e.content for e in doc.elements if e.type == "caption"]
    assert any("Table 1: Setup" in c for c in caps)
    assert any("Table 2: Results" in c for c in caps)


def test_stacked_zero_ownership(monkeypatch, tmp_path):
    page = _stacked_page()
    doc, _ = _parse(monkeypatch, tmp_path, [page])
    text = _nontable_text(doc)
    for i in range(9):
        assert f"b{i}" in text  # 表体词全部留在段落轨


# ---------- §十二-9：单题注正常路径 ----------

def test_single_caption_normal_emission(monkeypatch, tmp_path):
    page = _full_tile_page()
    page._words = (
        list(page._words) + _caption_words(120, 170, "Table 1: Setup"))
    doc, calls = _parse(monkeypatch, tmp_path, [page])
    assert len(calls) == 1
    tbls = _tables(doc)
    assert len(tbls) == 1
    assert tbls[0].metadata["detection"] == "text_fallback"
    assert "b0" in tbls[0].content
    assert "b0" not in _nontable_text(doc)
    caps = [e.content for e in doc.elements if e.type == "caption"]
    assert any("Table 1: Setup" in c for c in caps)
    assert "Table 1: Setup" not in tbls[0].content


# ---------- §十二-10：题注保护词不吸收 ----------

def test_caption_protected_words_excluded(monkeypatch, tmp_path):
    page = _full_tile_page()
    # 题注行置于 cell0 内（top 245..259，独立行带），不经保护本会被吸收
    page._words = (
        list(page._words) + _caption_words(102, 245, "Table 1: Results"))
    doc, calls = _parse(monkeypatch, tmp_path, [page])
    assert len(calls) == 1
    tbls = _tables(doc)
    assert len(tbls) == 1  # 单锚不 stacked，正常发射
    caps = [e.content for e in doc.elements if e.type == "caption"]
    assert any(c == "Table 1: Results" for c in caps)
    assert "Table 1: Results" not in tbls[0].content
    assert "b0" not in _nontable_text(doc)


# ---------- §十二-11：provenance 缺失保守不吸收 ----------

def test_missing_provenance_conservative(monkeypatch, tmp_path):
    bbox = [100.0, 200.0, 400.0, 400.0]
    cells = _tile_cells(*bbox, ncols=3, nrows=3)
    rows = _tile_rows("m", ncols=3, nrows=3)
    # 5 词带 chars（可归属，>=4 过 gate2）+ 4 词缺 chars（in-cell 位置）
    with_chars = _tile_body_words("m", cells)[:5]
    no_chars = [
        _word(f"n{i}", cells[i][0] + 5, cells[i][1] + 40,
              (cells[i][0] + cells[i][2]) / 2, cells[i][1] + 54,
              with_chars=False)
        for i in range(4)
    ]
    page = _FakePage(
        with_chars + no_chars,
        text_tables=[_FakeTable(rows, bbox, cells)])
    doc, calls = _parse(monkeypatch, tmp_path, [page])
    assert len(calls) == 1
    tbls = _tables(doc)
    assert len(tbls) == 1  # 5 个可归属词足够过门
    text = _nontable_text(doc)
    for i in range(5):
        assert f"m{i}" not in text  # 带 chars 的被吸收
    for i in range(4):
        assert f"n{i}" in text  # 缺 provenance 的保守留在段落轨


# ---------- §十二-12/13：cell-semantic gate 计数 / bbox-only 不助力 ----------

def _sparse_cells_page(n_emittable: int) -> _FakePage:
    bbox = [100.0, 200.0, 400.0, 400.0]
    # 真实 cell 只有两个（text 表典型稀疏面），大片 bbox 区域无 cell
    cells = [[100.0, 200.0, 200.0, 267.0], [250.0, 200.0, 350.0, 267.0]]
    rows = [["h1", "h2", "h3"], ["x", "y", "z"], ["p", "q", "r"]]
    emittable = [
        _word("e0", 105, 205, 150, 219),
        _word("e1", 105, 240, 150, 254),
        _word("e2", 255, 205, 300, 219),
        _word("e3", 255, 240, 300, 254),
    ][:n_emittable]
    # 5 个 bbox-only 词：中心在 bbox 内但 chars midpoint 不落任何 cell
    bbox_only = [
        _word(f"g{i}", 260 + i * 6, 280 + i * 2, 380, 294 + i * 2)
        for i in range(5)
    ]
    return _FakePage(
        emittable + bbox_only,
        text_tables=[_FakeTable(rows, bbox, cells)])


def test_cell_semantic_gate_count_three_emittable_rejected(
        monkeypatch, tmp_path):
    page = _sparse_cells_page(n_emittable=3)
    doc, calls = _parse(monkeypatch, tmp_path, [page])
    assert len(calls) == 1
    # 3 可归属 + 5 bbox-only：gate2 按可归属计数 = 3 < 4 -> 拒
    assert _tables(doc) == []
    text = _nontable_text(doc)
    assert "e0" in text and "g0" in text


def test_bbox_only_words_do_not_help_gate2(monkeypatch, tmp_path):
    page = _sparse_cells_page(n_emittable=4)
    doc, calls = _parse(monkeypatch, tmp_path, [page])
    assert len(calls) == 1
    tbls = _tables(doc)
    assert len(tbls) == 1  # 4 可归属恰过门（bbox-only 未充数）
    assert tbls[0].metadata["detection"] == "text_fallback"
    text = _nontable_text(doc)
    for i in range(4):
        assert f"e{i}" not in text  # 可归属词被吸收
    for i in range(5):
        assert f"g{i}" in text  # bbox-only 词留在段落轨（零 ownership）


# ---------- §十二-14：source-char deficit=0 守恒 fixture ----------

def test_source_char_deficit_zero_conservation(monkeypatch, tmp_path):
    page = _full_tile_page()
    page._words = (
        list(page._words) + _caption_words(120, 170, "Table 1: Results"))
    doc, calls = _parse(monkeypatch, tmp_path, [page])
    assert len(calls) == 1
    tbls = _tables(doc)
    assert len(tbls) == 1
    table_md = tbls[0].content
    nontable = _nontable_text(doc)
    # 守恒：每个词恰好出现一次（表内 XOR 段落/题注轨），无丢失无双轨
    for i in range(9):
        tok = f"b{i}"
        assert table_md.count(tok) == 1
        assert tok not in nontable
    assert "Table 1: Results" in nontable
    assert "Table 1: Results" not in table_md
    # 无 image / 无第二表（无重复发射）
    assert len([e for e in doc.elements if e.type == "table"]) == 1
