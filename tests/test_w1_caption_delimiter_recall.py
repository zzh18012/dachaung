r"""W1 题注分隔符测试（r85 Q1 扩展 + r89 W4-C 收紧）。

历史：r85 Q1 把分隔符类扩为 [\.、:：\s]（修 pdfplumber 无空格抽取
"Figure3:The…" 零题注边）。r89 W4-C 删去 `_CAPTION_RE`（typing 通道）
的 `\s`——数字后必须可见分隔符，排除 "Figure 3 gives…" 句首叙述句；
dev-14 穷举审计门通过（flip=1 全 FP、TP=0，13,457 被测文本）后生效。
`_FIGURE_CAPTION_RE` / `_TABLE_CAPTION_RE` 是关系侧消费者（r89 未点
名、未审计），分隔符类保持 [\.、:：\s] 不变。

契约：docs/caption-relation-contract.md §1（W1 修正案，含 accepted
forms 表；r89 收紧为 W1 修正案的后续裁决）。

裁决约束：
- r85 Q1：不加 OCR/fuzzy/probabilistic；
- r89 W4-C：typing 通道收紧，"Figure 3 shows…" 不再定型 caption
  （test_sentence_start_reference_no_longer_typed）；
- 负向回归 sentence_start_figure_reference：句首引用形无题注几何
  （上方/超距）不得自动生成 relation。
"""

from __future__ import annotations

import pytest

from app.parsers.fallback_parser import (
    _CAPTION_RE,
    _FIGURE_CAPTION_RE,
    _TABLE_CAPTION_RE,
    _classify_pdf_paragraph,
    match_caption_relations_docx,
    match_caption_relations_pdf,
    match_table_caption_relations_docx,
    match_table_caption_relations_pdf,
)
from tests.test_caption_relation_contract import _cap, _el, _img, _rels


# ---------- 类型层：W1 目标形制（冒号 + 无空格）----------

@pytest.mark.parametrize("text", [
    # acad-03 实测形制（pdfplumber 无空格抽取）
    "Figure3:Thearchitectureandpre-trainingobjectivesofLayoutLMv3",
    "Table1:Comparisonwithexistingpublishedmodelsoninformationextraction",
    # 常规冒号形
    "Figure 3: Overview of the framework",
    "Table 1: Test results",
    # 全角冒号
    "图 3：系统架构示意",
    "表 1：测试结果汇总",
])
def test_colon_forms_typed_caption(text):
    assert _classify_pdf_paragraph(text) == ("caption", {"heuristic": "caption_regex"})


@pytest.mark.parametrize("text", [
    "The model is shown in Figure 3.",
    "我们在图 3 中展示了系统架构。",
    "实验结果见表 3，其中各项指标均有提升。",
    "Figure3Thearchitecturewithoutanyseparator",
])
def test_non_caption_forms_not_typed_caption(text):
    # W1 边界 = 不定型 caption；heading/paragraph 之分属短行启发式，
    # 不在本案范围（无分隔符形 "Figure3The…" 落 heading 分支）
    etype, _ = _classify_pdf_paragraph(text)
    assert etype != "caption"


def test_sentence_start_reference_no_longer_typed():
    # r89 W4-C 收紧（原 r85 钉住测试翻转）："Figure 3 shows…" 数字后
    # 为纯空白，不再定型 caption——dev-14 穷举审计 TP=0（唯一 flip
    # = tech-06 "Figure 42 represents…"，FP）。
    etype, _ = _classify_pdf_paragraph(
        "Figure 3 shows the architecture of the system.")
    assert etype != "caption"


# ---------- 正则层：typing 收紧 + 关系侧不变 ----------

@pytest.mark.parametrize("sep", [".", ":", "：", "、"])
def test_typing_regex_accepts_visible_separators(sep):
    assert _CAPTION_RE.match(f"Figure 3{sep}title")
    assert _CAPTION_RE.match(f"图 3{sep}标题")
    assert _CAPTION_RE.match(f"Table 1{sep}title")


@pytest.mark.parametrize("sep", [" "])
def test_typing_regex_rejects_whitespace_delimiter(sep):
    # r89 W4-C：`\s` 自 typing 通道删除（u0038 "Figure 3 gives…" 类）
    assert not _CAPTION_RE.match(f"Figure 3{sep}title")
    assert not _CAPTION_RE.match(f"表 1{sep}标题")


@pytest.mark.parametrize("rx", [_FIGURE_CAPTION_RE])
@pytest.mark.parametrize("sep", [".", ":", "：", "、", " "])
def test_figure_relation_regex_unchanged(rx, sep):
    # 关系侧消费者未被 r89 点名：分隔符类保持 [\.、:：\s]
    assert rx.match(f"Figure 3{sep}title")
    assert rx.match(f"图 3{sep}标题")


@pytest.mark.parametrize("rx", [_TABLE_CAPTION_RE])
@pytest.mark.parametrize("sep", [".", ":", "：", "、", " "])
def test_table_relation_regex_unchanged(rx, sep):
    assert rx.match(f"Table 1{sep}title")
    assert rx.match(f"表 1{sep}标题")


# ---------- 口径分工 ----------

def test_prefix_disambiguation_unchanged():
    assert not _FIGURE_CAPTION_RE.match("Table 1: matrix")
    assert not _TABLE_CAPTION_RE.match("Figure 1: flow")
    assert _CAPTION_RE.match("表１：全角数字")  # 分类层含全角数字，分工不变


# ---------- 匹配器层：W1 端到端 + 负向回归 ----------

def test_pdf_colon_caption_end_to_end():
    els = [
        _img("i1", {"family": "page_geometry", "page": 1,
                    "bbox": [100, 100, 300, 200]}),
        _cap("c1", "Figure3:Thearchitectureandpre-trainingobjectives",
             {"family": "page_geometry", "page": 1,
              "bbox": [100, 210, 300, 230]}),
    ]
    rels = _rels(match_caption_relations_pdf(els))
    assert rels == [{
        "type": "has_caption", "from_id": "i1", "to_id": "c1",
        "metadata": {"rule": "pdf_geometry_below", "gap_pt": 10.0},
    }]


def test_pdf_colon_table_caption_end_to_end():
    els = [
        _cap("c1", "Table1:Comparisonwithexistingpublishedmodels",
             {"family": "page_geometry", "page": 1,
              "bbox": [100, 100, 300, 120]}),
        _el("t1", "table", "", {"family": "page_geometry", "page": 1,
                                "bbox": [100, 130, 300, 300]}),
    ]
    rels = _rels(match_table_caption_relations_pdf(els))
    assert rels == [{
        "type": "table_has_caption", "from_id": "t1", "to_id": "c1",
        "metadata": {"rule": "pdf_geometry_above", "gap_pt": 10.0},
    }]


def test_docx_colon_caption_adjacent():
    els = [
        _img("i1", {"family": "structural_index", "paragraph_index": 3}),
        _cap("c1", "图 3：系统架构示意",
             {"family": "structural_index", "paragraph_index": 4}),
    ]
    assert _rels(match_caption_relations_docx(els)) == [{
        "type": "has_caption", "from_id": "i1", "to_id": "c1",
        "metadata": {"rule": "docx_adjacent_paragraph"},
    }]


def test_sentence_start_figure_reference_no_relation_without_geometry():
    # r85 Q1 负向回归（sentence_start_figure_reference）：句首引用形
    # （保留风险下被定型 caption）不满足题注几何时不得自动生成 relation。
    sent = "Figure 3 shows the architecture of the system."
    img_loc = {"family": "page_geometry", "page": 1,
               "bbox": [100, 100, 300, 200]}
    # 引用文本在图上方（gap ≤ 0）
    above = _cap("c1", sent, {"family": "page_geometry", "page": 1,
                              "bbox": [100, 40, 300, 90]})
    # 引用文本在图下方但超出 CAPTION_MAX_GAP_PT
    far = _cap("c2", sent, {"family": "page_geometry", "page": 1,
                            "bbox": [100, 260, 300, 280]})
    els = [_img("i1", img_loc), above, far]
    assert match_caption_relations_pdf(els) == []
    # 不邻接的 docx 段落同理（paragraph_index 距离 > 1）
    els_docx = [
        _img("i1", {"family": "structural_index", "paragraph_index": 3}),
        _cap("c1", sent,
             {"family": "structural_index", "paragraph_index": 8}),
    ]
    assert match_caption_relations_docx(els_docx) == []


def test_table_colon_caption_above_only():
    # 表题注规则是上方紧邻：下方不生成（镜像负向）
    els = [
        _el("t1", "table", "", {"family": "page_geometry", "page": 1,
                                "bbox": [100, 100, 300, 300]}),
        _cap("c1", "表 1：测试结果",
             {"family": "page_geometry", "page": 1,
              "bbox": [100, 310, 300, 330]}),
    ]
    assert match_table_caption_relations_pdf(els) == []
    assert match_table_caption_relations_docx(els) == []
