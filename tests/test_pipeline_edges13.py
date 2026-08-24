r"""app/pipeline.py 边角测试 - 第十三轮（Round 1370）。

补强 edges10-12（markdown/ipynb/html 走全管线）后唯一缺的
parser：text 走全管线分块几何（probe 实证）：
- 无 heading → 唯一分块力是 max_chars：mc800 单块 sequential
- mc100 → 每段 2 块 long_paragraph_sentence_split（4 块）
- mc60 → 每段 4 块（8 块），句子从不跨块
- element locator 只有 line（1 / 3），无 section_path
- metrics：heading_boundary_compliance null
  no_heading_elements；tpe True；crir 1.0
- chunk_boundary_prf 段内锚点 tol1 不命中（边界只在句号后）
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.pipeline import process_single

TXT = (
    "".join("Sentence %d ends here. " % i
            for i in range(8))
    + "\n\n"
    + "".join("Second %d block text. " % i
              for i in range(8))
    + "\n")


def _run(tmp_path, mc=800, txt=TXT):
    (tmp_path / "d.txt").write_text(txt,
                                    encoding="utf-8")
    return process_single(
        tmp_path / "d.txt", tmp_path / "o.json",
        parser_name="text", max_chars=mc)


# ---------- 无 heading 的分块力 ----------

def test_mc800_single_sequential_chunk(tmp_path):
    doc, errors = _run(tmp_path, mc=800)
    assert errors == []
    assert len(doc.chunks) == 1
    assert doc.chunks[0].metadata["strategy"] == \
        "sequential"


def test_two_paragraph_elements(tmp_path):
    doc, errors = _run(tmp_path, mc=800)
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "paragraph", "paragraph"]


def test_element_locators_line_only(tmp_path):
    doc, _ = _run(tmp_path, mc=800)
    assert [e.source_locator for e in doc.elements] == [
        {"line": 1}, {"line": 3}]


def test_single_chunk_both_paragraphs(tmp_path):
    doc, _ = _run(tmp_path, mc=800)
    assert len(doc.chunks[0].source_element_ids) == 2


# ---------- mc100 句子切分几何 ----------

def test_mc100_four_chunks(tmp_path):
    doc, errors = _run(tmp_path, mc=100)
    assert errors == []
    assert len(doc.chunks) == 4


def test_mc100_all_sentence_split(tmp_path):
    doc, _ = _run(tmp_path, mc=100)
    assert all(c.metadata["strategy"] ==
               "long_paragraph_sentence_split"
               for c in doc.chunks)


def test_mc100_two_chunks_per_paragraph(tmp_path):
    doc, _ = _run(tmp_path, mc=100)
    srcs = [len(c.source_element_ids) for c
            in doc.chunks]
    assert srcs == [1, 1, 1, 1]
    assert {c.source_element_ids[0]
            for c in doc.chunks[:2]} == {
        doc.elements[0].element_id}
    assert {c.source_element_ids[0]
            for c in doc.chunks[2:]} == {
        doc.elements[1].element_id}


def test_mc100_first_chunk_text(tmp_path):
    doc, _ = _run(tmp_path, mc=100)
    assert doc.chunks[0].text == (
        "Sentence 0 ends here. Sentence 1 ends "
        "here. Sentence 2 ends here. Sentence 3 "
        "ends here.")


def test_mc100_second_chunk_text(tmp_path):
    doc, _ = _run(tmp_path, mc=100)
    assert doc.chunks[1].text == (
        "Sentence 4 ends here. Sentence 5 ends "
        "here. Sentence 6 ends here. Sentence 7 "
        "ends here.")


def test_mc100_paragraph_two_starts_new_chunk(
        tmp_path):
    doc, _ = _run(tmp_path, mc=100)
    assert doc.chunks[2].text.startswith(
        "Second 0 block text.")


# ---------- mc60 更细几何 ----------

def test_mc60_eight_chunks(tmp_path):
    doc, errors = _run(tmp_path, mc=60)
    assert errors == []
    assert len(doc.chunks) == 8


def test_mc60_two_sentences_per_chunk(tmp_path):
    doc, _ = _run(tmp_path, mc=60)
    for c in doc.chunks:
        assert c.text.count(".") == 2


def test_mc60_sentence_never_split(tmp_path):
    doc, _ = _run(tmp_path, mc=60)
    for c in doc.chunks:
        for part in c.text.split(". "):
            assert not part.startswith(" ")


def test_mc60_all_same_strategy(tmp_path):
    doc, _ = _run(tmp_path, mc=60)
    assert {c.metadata["strategy"] for c
            in doc.chunks} == {
        "long_paragraph_sentence_split"}


# ---------- 不丢不重 ----------

def test_no_loss_mc100(tmp_path):
    from app.chunkers import normalize_text
    doc, _ = _run(tmp_path, mc=100)
    orig = " ".join(e.content or ""
                    for e in doc.elements)
    joined = " ".join(c.text for c in doc.chunks)
    assert normalize_text(orig) == \
        normalize_text(joined)


def test_no_loss_mc60(tmp_path):
    from app.chunkers import normalize_text
    doc, _ = _run(tmp_path, mc=60)
    orig = " ".join(e.content or ""
                    for e in doc.elements)
    joined = " ".join(c.text for c in doc.chunks)
    assert normalize_text(orig) == \
        normalize_text(joined)


# ---------- schema + 落盘 ----------

def test_txt_doc_passes_schema(tmp_path):
    doc, errors = _run(tmp_path, mc=100)
    assert errors == []
    from app.schema import validate
    validate(doc.to_dict())


def test_written_json_source_type(tmp_path):
    import json
    _run(tmp_path, mc=100)
    on_disk = json.loads(
        (tmp_path / "o.json").read_text(
            encoding="utf-8"))
    assert on_disk["source_type"] == "text"
    assert len(on_disk["chunks"]) == 4


# ---------- metrics 关联 ----------

def test_hbc_no_heading_elements(tmp_path):
    from evaluation.metrics import (
        compute_automatic_metrics)
    doc, _ = _run(tmp_path, mc=100)
    m = compute_automatic_metrics(
        doc.to_dict(), None, "text", None)
    assert m["heading_boundary_compliance"] == {
        "value": None,
        "reason": "no_heading_elements"}


def test_tpe_and_crir(tmp_path):
    from evaluation.metrics import (
        compute_automatic_metrics)
    doc, _ = _run(tmp_path, mc=100)
    m = compute_automatic_metrics(
        doc.to_dict(), None, "text", None)
    assert m["text_preservation_equal"] == {
        "value": True, "reason": None}
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}


def test_boundary_anchor_mid_sentence_miss(
        tmp_path):
    from evaluation.annotation_metrics import (
        chunk_boundary_prf)
    doc, _ = _run(tmp_path, mc=100)
    r = chunk_boundary_prf(
        doc.to_dict(),
        {"chunk_boundary_anchors": [
            {"marker": "ends", "position": "before"}]},
        1)
    assert r["chunk_boundary_precision"][
        "value"] == 0.0
    assert r["chunk_boundary_recall"][
        "value"] == 0.0


def test_boundary_anchor_unique_suffix_hit(
        tmp_path):
    from evaluation.annotation_metrics import (
        chunk_boundary_prf)
    doc, _ = _run(tmp_path, mc=100)
    d = doc.to_dict()
    marker = "Sentence 3 ends here."
    assert d["chunks"][0]["text"].endswith(
        marker)
    r = chunk_boundary_prf(
        d,
        {"chunk_boundary_anchors": [
            {"marker": marker,
             "position": "after"}]},
        0)
    assert r["chunk_boundary_recall"][
        "value"] == 1.0
    assert r["chunk_boundary_precision"][
        "value"] == 0.3333333333333333
