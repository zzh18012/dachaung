r"""app/chunkers/structural.py 边角测试 - 第十二轮（Round 1454）。

新角度（probe 实证）精确贴合边界 + 句子正则盲区（edges1-11
未打过的等号两侧与 lookbehind 缺口）：
- 双 element 累积：40+1+59 = **恰好** max_chars=100 → 同
  chunk（len 100，双 source ids，joiner 空格不入 span）；
  +1 超限 → 劈两 chunk
- 句子累积同界：49+1+50 = 100 → 单 piece span [0,100)；
  101 → 两 piece span [0,49)/[50,101)（索引 49 的空格在
  两 span 之外）
- _SENTENCE_SPLIT_RE 盲区：'." '（引号夹在句点与空白间）
  lookbehind 不命中 → **不切句**，超长走 hard split
  （59 + 25 两 piece，whitespace/None 边界）；
  CJK 无空格 '第一。第二。' 同样不切；'。 ' 带空格才切
- 前导空白 + forced_char CJK：content '   ' + 中*100 的
  span 依次 [3,43)/[43,83)/[83,103)，切片重建精确
- CJK 带空格句子累积：15+1+7 > 20 → 两 piece
  [0,15)/[16,23)
"""

from __future__ import annotations

from app.chunkers.structural import (
    StructuralChunker, _SENTENCE_SPLIT_RE,
    _split_long_text, normalize_text,
)
from app.models import Document, Element


def _doc(elems):
    return Document(
        document_id="doc-x", source_path="x",
        source_type="pdf", source_hash="h",
        parser_name="p", parser_version="1",
        elements=elems, chunks=[], relations=[],
        warnings=[], errors=[], metadata={},
    )


def _para(eid, text):
    return Element(
        element_id=eid, type="paragraph",
        content=text, parent_id=None,
        source_locator={"page": 1}, confidence=1.0,
        metadata={},
    )


# ---------- 句子正则盲区 ----------

def test_sentence_regex_quote_blocks():
    assert _SENTENCE_SPLIT_RE.split(
        'He said." Next sentence.'
    ) == ['He said." Next sentence.']
    assert _SENTENCE_SPLIT_RE.split(
        'A." B'
    ) == ['A." B']


def test_sentence_regex_cjk_no_space():
    assert _SENTENCE_SPLIT_RE.split(
        '第一。第二。'
    ) == ['第一。第二。']


def test_sentence_regex_cjk_with_space():
    assert _SENTENCE_SPLIT_RE.split(
        '第一。 第二。'
    ) == ['第一。', '第二。']


def test_sentence_regex_multi_space():
    assert _SENTENCE_SPLIT_RE.split(
        'One.  Two.  Three.'
    ) == ['One.', 'Two.', 'Three.']


# ---------- 双 element 精确贴合 ----------

def test_join_exact_fit_single_chunk():
    els = [_para("e1", "A" * 40),
           _para("e2", "B" * 59)]
    chunks = StructuralChunker(
        max_chars=100).chunk(_doc(els))
    assert len(chunks) == 1
    c = chunks[0]
    assert len(c.text) == 100
    assert c.source_element_ids == ["e1", "e2"]
    assert c.metadata["char_count"] == 100
    assert c.source_spans == [
        {"element_id": "e1",
         "start": 0, "end": 40},
        {"element_id": "e2",
         "start": 0, "end": 59},
    ]


def test_join_one_over_splits():
    els = [_para("e1", "A" * 40),
           _para("e2", "B" * 60)]
    chunks = StructuralChunker(
        max_chars=100).chunk(_doc(els))
    assert len(chunks) == 2
    assert [len(c.text) for c in chunks] \
        == [40, 60]
    assert chunks[0].source_element_ids == ["e1"]
    assert chunks[1].source_element_ids == ["e2"]


def test_joiner_not_in_span():
    els = [_para("e1", "A" * 40),
           _para("e2", "B" * 59)]
    chunks = StructuralChunker(
        max_chars=100).chunk(_doc(els))
    c = chunks[0]
    assert c.text == "A" * 40 + " " + "B" * 59
    content = {"e1": "A" * 40, "e2": "B" * 59}
    parts = [content[s["element_id"]]
             [s["start"]:s["end"]]
             for s in c.source_spans]
    assert parts == ["A" * 40, "B" * 59]
    assert normalize_text(" ".join(parts)) \
        == normalize_text(c.text)


# ---------- 句子累积精确贴合 ----------

def test_sentence_accum_exact_fit():
    text = "S" * 48 + "." + " " + "T" * 49 + "."
    pieces = _split_long_text(text, 100)
    assert len(pieces) == 1
    assert len(pieces[0].text) == 100
    assert (pieces[0].start,
            pieces[0].end) == (0, 100)
    assert pieces[0].boundary_after is None


def test_sentence_accum_one_over():
    text = "S" * 48 + "." + " " + "T" * 50 + "."
    pieces = _split_long_text(text, 100)
    assert len(pieces) == 2
    assert [(p.start, p.end)
            for p in pieces] == [
        (0, 49), (50, 101)]
    assert pieces[0].text == "S" * 48 + "."
    assert pieces[1].text == "T" * 50 + "."


# ---------- 引号盲区走 hard split ----------

def test_quote_text_hard_split():
    text = 'He said." ' * 8 + "tail."
    pieces = _split_long_text(text, 60)
    assert len(pieces) == 2
    assert [len(p.text) for p in pieces] \
        == [59, 25]
    assert [(p.start, p.end)
            for p in pieces] == [
        (0, 59), (60, 85)]
    assert pieces[0].boundary_after \
        == "whitespace"
    assert pieces[1].boundary_after is None


def test_quote_text_no_loss():
    text = 'He said." ' * 8 + "tail."
    pieces = _split_long_text(text, 60)
    joined = " ".join(p.text for p in pieces)
    assert normalize_text(joined) \
        == normalize_text(text)


# ---------- 前导空白 + forced_char span ----------

def test_leading_ws_forced_spans():
    content = "   " + "中" * 100 + "   "
    chunks = StructuralChunker(
        max_chars=40).chunk(
        _doc([_para("e9", content)]))
    assert [len(c.text) for c in chunks] \
        == [40, 40, 20]
    assert [(c.source_spans[0]["start"],
             c.source_spans[0]["end"])
            for c in chunks] == [
        (3, 43), (43, 83), (83, 103)]
    for c in chunks:
        s = c.source_spans[0]
        assert content[s["start"]:s["end"]] \
            == c.text


# ---------- CJK 带空格累积 ----------

def test_cjk_spaced_accum():
    text = "这是第一句话。 这是第二句话。 这是第三句话。"
    pieces = _split_long_text(text, 20)
    assert [(p.text, p.start, p.end)
            for p in pieces] == [
        ("这是第一句话。 这是第二句话。",
         0, 15),
        ("这是第三句话。", 16, 23),
    ]
