r"""PDF 图片 Do 在 BT/ET 文本对象内（Round 1953，a 优先级）。

PDF 规范允许 Do 出现在内容流任何位置（含 BT/ET 之间）——
朴素实现会假设图片只在文本对象外；既有测试的 Do 全部在
BT/ET 外（广扫 BT.*Do 零匹配）。探针 R1953 实证——pdfminer
顺序处理算子、文本/图片互不干扰，三形态全提取：

- **B1 交错**：BEFORE Tj → q Do Q → Td → AFTER Tj（同一
  BT/ET）→ 两 heading（行距 150pt 拆段）+ 图，元素序
  **文本先、图最后**（组装序非位置交错）
- **B2 Do 紧跟 BT**：任何文本算子之前 → heading SOLO + 图
- **B3 同基线续排**：HEAD Tj → q Do Q → TAIL Tj（无 Td）
  → 单 heading 'HEADTAIL'（pen 续位连字）

判别式：若实现引入"Do 只在文本对象外"假设则图消失/告警
翻红；若元素组装改位置序则 B1 序断言翻红。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf


def _parse(tmp_path: Path, content: bytes):
    p = tmp_path / "b.pdf"
    p.write_bytes(_pdf([content]))
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    d = FallbackParser(image_output_dir=str(img_dir)).parse(
        p, compute_file_hash(p))
    return d, img_dir


def test_interleaved_do_and_text(tmp_path):
    """B1：同一 BT/ET 内文-图-文 → 两 heading + 图（文本先）。"""
    d, img_dir = _parse(tmp_path, (
        "BT /F1 12 Tf 100 700 Td (BEFORE) Tj\n"
        "q 100 0 0 100 300 550 cm /Im1 Do Q\n"
        "0 -150 Td (AFTER) Tj ET").encode())
    assert [e.type for e in d.elements] == ["heading", "heading", "image"]
    assert [e.content for e in d.elements[:2]] == ["BEFORE", "AFTER"]
    img = d.elements[2]
    assert Path(img.resource_path).name.endswith("_p1_00.png")
    assert img.metadata["extracted_to_disk"]
    assert list(img_dir.glob("*.png"))
    assert d.warnings == []


def test_do_before_text_operators(tmp_path):
    """B2：Do 紧跟 BT（任何文本算子之前）→ 图文双全。"""
    d, _ = _parse(tmp_path, (
        "BT q 100 0 0 100 300 550 cm /Im1 Do Q\n"
        "/F1 12 Tf 100 700 Td (SOLO) Tj ET").encode())
    assert [e.type for e in d.elements] == ["heading", "image"]
    assert d.elements[0].content == "SOLO"
    assert d.warnings == []


def test_same_baseline_continuation(tmp_path):
    """B3：Tj → Do → Tj 无 Td → 单 heading 'HEADTAIL' 连字。"""
    d, _ = _parse(tmp_path, (
        "BT /F1 12 Tf 100 700 Td (HEAD) Tj\n"
        "q 100 0 0 100 300 550 cm /Im1 Do Q\n"
        "(TAIL) Tj ET").encode())
    assert [e.type for e in d.elements] == ["heading", "image"]
    assert d.elements[0].content == "HEADTAIL"
    assert d.warnings == []
