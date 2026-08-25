r"""app/parsers/fallback_parser.py 边角测试 - 第六十四轮（Round 1477）。

新角度（probe 实证）兼容段 + 畸形双引号 + 缺省 TL 的 T* +
颜色/合法 gs（edges1-63 未碰过；edges43 已锁 ' 与 " 带显式
TL/操作数、edges23 已锁 T* 带 TL 14、edges44 已锁 Ts/Tz/Tr、
edges63 已锁缺失 gs、edges32 已锁内联图片，避开）：
- **BX/EX 兼容段完全透明**：unknown 运算符被 EX 兼容机制
  吞掉，文本照常提取、无告警
- **畸形 " （操作数不足）→ 全页无文本**："(dq text)\" 只有
  字符串在栈上，" 需 aw ac string 三操作数 → pdfminer 消化
  失败静默 → elements 空 + pdf_no_text_extracted（对照
  edges43 的合法 0 0 (...) " 正常画字）
- **T\* 无 TL（缺省 0）同 y 交织**：'(first) Tj T*
  (second) Tj' → 'fsiresctond'（TL 缺省 0，T* 不降行，
  x 排序交织——对照 edges23 的 TL 14 正常降行）
- **颜色运算符全部忽略**：rg/g 同流，'red text' 照常提取
  无告警
- **合法 /GS1 gs（ca/CA 半透明）文本照常**：ExtGState 资源
  真实在 Resource 字典里，alpha 只影响渲染不影响抽取
  （对照 edges63 的缺失 gs 被忽略）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _pdf(tmp_path, name, content,
         extra_res=""):
    res = (f"/Font << /F1 5 0 R >>"
           f"{extra_res}")
    pdf = (f"%PDF-1.4\n"
           f"1 0 obj\n<< /Type /Catalog"
           f" /Pages 2 0 R >>\nendobj\n"
           f"2 0 obj\n<< /Type /Pages"
           f" /Kids [3 0 R] /Count 1"
           f" >>\nendobj\n"
           f"3 0 obj\n<< /Type /Page"
           f" /Parent 2 0 R"
           f" /MediaBox [0 0 612 792]"
           f" /Resources << {res} >>"
           f" /Contents 4 0 R"
           f" >>\nendobj\n"
           f"4 0 obj\n<< /Length "
           f"{len(content)} >>\nstream\n"
           f"{content}\nendstream"
           f"\nendobj\n"
           f"5 0 obj\n<< /Type /Font"
           f" /Subtype /Type1"
           f" /BaseFont /Helvetica"
           f" /Encoding /WinAnsiEncoding"
           f" >>\nendobj\n"
           f"6 0 obj\n<< /Type /ExtGState"
           f" /ca 0.5 /CA 0.5"
           f" >>\nendobj\n"
           f"trailer\n<< /Root 1 0 R"
           f" /Size 7 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf.encode("latin-1"))
    return p


def _parse(p):
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- 兼容段 ----------

def test_bx_ex_transparent(tmp_path):
    p = _pdf(
        tmp_path, "bx.pdf",
        "BX /F1 12 Tf BT (in bx) Tj"
        " ET EX")
    doc = _parse(p)
    e = doc.elements[0]
    assert e.content == "in bx"
    assert e.type == "heading"
    assert e.metadata == {
        "level": 0,
        "heuristic": "short_line",
    }
    assert doc.warnings == []


# ---------- 畸形双引号 ----------

def test_dq_malformed_no_text(
        tmp_path):
    p = _pdf(
        tmp_path, "dqb.pdf",
        'BT /F1 12 Tf 5 Tw '
        '(dq text)" ET')
    doc = _parse(p)
    assert doc.elements == []
    assert [w.code for w in doc.warnings] \
        == ["pdf_no_text_extracted"]


# ---------- T* 缺省 TL ----------

def test_tstar_default_tl_interleave(
        tmp_path):
    p = _pdf(
        tmp_path, "ts0.pdf",
        "BT /F1 12 Tf (first) Tj"
        " T* (second) Tj ET")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == [
        "fsiresctond",
    ]


# ---------- 颜色运算符 ----------

def test_color_ops_ignored(tmp_path):
    p = _pdf(
        tmp_path, "color.pdf",
        "1 0 0 rg BT /F1 12 Tf"
        " (red text) Tj ET"
        " 0 G 0.5 g")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == [
        "red text",
    ]
    assert doc.warnings == []


# ---------- 合法 gs ----------

def test_gs_valid_alpha_text_kept(
        tmp_path):
    p = _pdf(
        tmp_path, "gsv.pdf",
        "/GS1 gs BT /F1 12 Tf"
        " (alpha text) Tj ET",
        extra_res=(" /ExtGState"
                   " << /GS1 6 0 R >>"))
    doc = _parse(p)
    e = doc.elements[0]
    assert e.content == "alpha text"
    assert e.source_locator["bbox"][2] == \
        52.032
    assert doc.warnings == []
