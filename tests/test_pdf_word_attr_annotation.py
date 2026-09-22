# -*- coding: utf-8 -*-
"""Batch 14（r72 方案 2）：word 属性加富纯度测试。

覆盖 r72 验收 D 要求的合成夹具：单 font 词 / mixed font 词 /
CJK 连续字符 / 相邻不同字号 / 无 chars 命中；另加确定性、
词身份保持（不增不删不改序不改 text/bbox、原 dict 不变异）、
空词流、接线调用证明与 e2e schema。全合成夹具，零真实语料。
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from unittest import mock

from app.parsers.fallback_parser import (
    FallbackParser,
    _annotate_words_with_attrs,
)
from app.pipeline import process_single


def _w(text: str, x0: float, x1: float, top: float = 100.0,
       bottom: float = 110.0) -> dict:
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": bottom}


def _c(x0: float, x1: float, font: str, size: float,
       top: float = 101.0, bottom: float = 109.0) -> dict:
    return {"x0": x0, "x1": x1, "top": top, "bottom": bottom,
            "fontname": font, "size": size}


def test_single_font_word():
    words = [_w("hello", 72.0, 100.0)]
    chars = [_c(72.0, 82.0, "Helvetica", 10.0),
             _c(82.0, 92.0, "Helvetica", 10.0),
             _c(92.0, 100.0, "Helvetica", 10.0)]
    out = _annotate_words_with_attrs(words, chars)
    assert len(out) == 1
    assert out[0]["fontname"] == "Helvetica"
    assert out[0]["font_size"] == 10.0


def test_mixed_font_max_span_wins():
    # A 字符跨度 18 > B 跨度 10 → A 胜（r72：覆盖最大跨度 char）
    words = [_w("AB", 72.0, 100.0)]
    chars = [_c(72.0, 90.0, "FontA", 12.0), _c(90.0, 100.0, "FontB", 8.0)]
    out = _annotate_words_with_attrs(words, chars)
    assert out[0]["fontname"] == "FontA"
    assert out[0]["font_size"] == 12.0


def test_mixed_font_tie_leftmost_wins():
    # 跨度平局（14 vs 14）→ cx 最左者（A cx=79 < B cx=93）胜
    words = [_w("AB", 72.0, 100.0)]
    chars = [_c(72.0, 86.0, "FontA", 12.0), _c(86.0, 100.0, "FontB", 8.0)]
    out = _annotate_words_with_attrs(words, chars)
    assert out[0]["fontname"] == "FontA"


def test_cjk_continuous_chars():
    # CJK 连续字符块：同字体 → 该字体；跨字符不引入不确定性
    words = [_w("中文测试", 72.0, 112.0)]
    chars = [_c(72.0 + 10 * i, 82.0 + 10 * i, "SimSun", 7.9)
             for i in range(4)]
    out = _annotate_words_with_attrs(words, chars)
    assert out[0]["fontname"] == "SimSun"
    assert out[0]["font_size"] == 7.9


def test_adjacent_words_different_sizes_no_cross_bleed():
    # 相邻不同字号词：各得各的 size；缝隙中的 char 不属于任何词
    words = [_w("big", 72.0, 110.0), _w("small", 120.0, 160.0)]
    chars = [_c(72.0, 110.0, "F", 12.0), _c(115.0, 118.0, "X", 9.0),
             _c(120.0, 160.0, "F", 8.0)]
    out = _annotate_words_with_attrs(words, chars)
    assert out[0]["font_size"] == 12.0
    assert out[1]["font_size"] == 8.0


def test_adjacent_line_char_ignored():
    # x 区间重叠但位于相邻行（cy 落词 bbox ±0.5 外）→ 不计包含
    words = [_w("line", 72.0, 100.0, top=100.0, bottom=110.0)]
    chars = [_c(72.0, 100.0, "Other", 9.0, top=80.0, bottom=88.0)]
    out = _annotate_words_with_attrs(words, chars)
    assert out[0]["fontname"] is None
    assert out[0]["font_size"] is None


def test_no_chars_hit_returns_none():
    # 无 chars 命中：两键 None（防御路径，取证证明真实语料不发生）
    words = [_w("island", 300.0, 340.0)]
    chars = [_c(72.0, 100.0, "Helvetica", 10.0)]
    out = _annotate_words_with_attrs(words, chars)
    assert out[0]["fontname"] is None
    assert out[0]["font_size"] is None
    # 空 chars 列表同样全 None
    out2 = _annotate_words_with_attrs(words, [])
    assert out2[0]["fontname"] is None


def test_deterministic_same_input_same_output():
    words = [_w("a", 72.0, 90.0), _w("b", 100.0, 130.0)]
    chars = [_c(72.0, 82.0, "F1", 10.0), _c(82.0, 90.0, "F2", 10.0),
             _c(100.0, 130.0, "F1", 9.0)]
    r1 = _annotate_words_with_attrs(words, chars)
    r2 = _annotate_words_with_attrs(words, chars)
    assert r1 == r2


def test_word_identity_preserved_and_input_not_mutated():
    # 词守恒（r72 验收 B）：不增不删不改序；text/bbox 恒等；
    # 原 dict 不被写入属性（返回浅拷贝新列表）
    words = [_w("first", 72.0, 100.0), _w("second", 110.0, 150.0)]
    chars = [_c(72.0, 100.0, "F", 10.0), _c(110.0, 150.0, "F", 10.0)]
    out = _annotate_words_with_attrs(words, chars)
    assert len(out) == len(words)
    for orig, new in zip(words, out):
        assert new is not orig
        assert "fontname" not in orig  # 原词未被修改
        assert new["text"] == orig["text"]
        assert (new["x0"], new["x1"], new["top"], new["bottom"]) == (
            orig["x0"], orig["x1"], orig["top"], orig["bottom"])


def test_empty_words_returns_empty():
    assert _annotate_words_with_attrs([], [_c(1.0, 2.0, "F", 1.0)]) == []


# ---------- 接线与端到端 ----------

def _escape_pdf_literal(t: str) -> str:
    return t.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _stream(positions: list[tuple[str, float, float]]) -> str:
    ops = [
        f"BT /F1 10 Tf {x} {y} Td ({_escape_pdf_literal(t)}) Tj ET"
        for t, x, y in positions
    ]
    return "\n".join(ops) + "\n"


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


def test_wiring_called_during_pdf_parse(tmp_path: Path):
    """_parse_pdf 词提取后确实调用属性加富（接线存在性证明）。"""
    pdf = _make_pdf(tmp_path / "wire.pdf", [
        _stream([("Hello attribute enrichment world.", 72.0, 700.0)]),
        _stream([("Second page with more words here.", 72.0, 700.0)]),
    ])
    with mock.patch(
        "app.parsers.fallback_parser._annotate_words_with_attrs",
        wraps=_annotate_words_with_attrs,
    ) as spy:
        FallbackParser().parse(
            pdf, source_hash=hashlib.sha256(pdf.read_bytes()).hexdigest())
    assert spy.call_count == 2  # 每页一次


def test_e2e_process_single_schema(tmp_path: Path):
    """加富后全链仍过 schema（属性零外显 → 输出形状不变）。"""
    pdf = _make_pdf(tmp_path / "pipe.pdf", [
        _stream([("Schema guard sentence for batch fourteen.", 72.0, 700.0)]),
    ])
    out = tmp_path / "pipe.json"
    doc, errs = process_single(pdf, out)
    assert errs == []
    assert out.exists()
    assert doc is not None
    # 属性不外显：任何元素 metadata 都不出现新键
    for e in doc.elements:
        assert "fontname" not in (e.metadata or {})
        assert "font_size" not in (e.metadata or {})
        assert "word_attrs" not in (e.metadata or {})
