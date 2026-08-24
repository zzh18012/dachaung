r"""evaluation/annotation_metrics.py 边角测试 - 第一百六十八轮（Round 1369）。

新角度（probe 实证，历史 annotation 板只用 fallback/pdf/docx 产物，
从未覆盖 markdown/ipynb 真实管线产物）：
- chunk_boundary_prf 直接吃 process_single 的 markdown/ipynb 产物
- "before 标题" 锚点在 tol0 全 miss——规范化流以空格 join 各 chunk，
  标题起始位置比 chunk 末尾恰晚 1 字符（off-by-one 阶梯）
- "after 块尾词" 锚点 tol0 精确命中（锚点位置 == 边界位置）
- ipynb 单锚点对双边界：tol1 P=0.5/R=1.0/F=0.6667
- 单 chunk 文档：P null no_predicted_boundaries、R 0.0
- 缺失 marker：R null no_ground_truth_anchors_in_stream +
  _missing_markers 记录
- document None：全 null pipeline_failed
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.pipeline import process_single
from evaluation.annotation_metrics import chunk_boundary_prf


MD = ("# H\n\npara one two three\n\n"
      "## Sub\n\ntail text here\n\n"
      "## Third\n\nmore text\n")

NB = {
    "cells": [
        {"cell_type": "markdown",
         "source": ["# H\n", "para one two\n"]},
        {"cell_type": "markdown",
         "source": "## Sub\n\ntail"},
        {"cell_type": "markdown",
         "source": "## T3\n\nmore"}],
    "metadata": {}, "nbformat": 4,
}


def _md_doc(tmp_path, md=MD, mc=200):
    (tmp_path / "d.md").write_text(md, encoding="utf-8")
    doc, errors = process_single(
        tmp_path / "d.md", None,
        parser_name="markdown", max_chars=mc)
    assert errors == []
    return doc.to_dict()


def _nb_doc(tmp_path, nb=NB, mc=50):
    (tmp_path / "n.ipynb").write_text(
        json.dumps(nb, ensure_ascii=False),
        encoding="utf-8")
    doc, errors = process_single(
        tmp_path / "n.ipynb", None,
        parser_name="ipynb", max_chars=mc)
    assert errors == []
    return doc.to_dict()


def _ann(*pairs):
    return {"chunk_boundary_anchors": [
        {"marker": m, "position": p} for m, p in pairs]}


BEFORE_TITLES = _ann(
    ("Sub", "before"), ("Third", "before"))

AFTER_TAILS = _ann(
    ("three", "after"), ("here", "after"))


# ---------- markdown 真实产物几何 ----------

def test_md_three_chunks(tmp_path):
    d = _md_doc(tmp_path)
    assert [c["text"] for c in d["chunks"]] == [
        "H para one two three",
        "Sub tail text here",
        "Third more text"]


def test_md_before_anchors_tol0_all_miss(tmp_path):
    r = chunk_boundary_prf(
        _md_doc(tmp_path), BEFORE_TITLES, 0)
    assert r["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}


def test_md_before_anchors_tol1_all_hit(tmp_path):
    r = chunk_boundary_prf(
        _md_doc(tmp_path), BEFORE_TITLES, 1)
    assert r["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_md_before_anchors_tol2_still_hit(tmp_path):
    r = chunk_boundary_prf(
        _md_doc(tmp_path), BEFORE_TITLES, 2)
    assert r["chunk_boundary_f1"]["value"] == 1.0


def test_md_after_tail_anchors_tol0_exact(tmp_path):
    r = chunk_boundary_prf(
        _md_doc(tmp_path), AFTER_TAILS, 0)
    assert r["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_f1"]["value"] == 1.0


def test_md_mixed_anchor_kinds_tol0(tmp_path):
    ann = _ann(("three", "after"), ("Third", "before"))
    r = chunk_boundary_prf(
        _md_doc(tmp_path), ann, 0)
    assert r["chunk_boundary_precision"]["value"] == 0.5
    assert r["chunk_boundary_recall"]["value"] == 0.5


def test_md_tolerance_recorded(tmp_path):
    r = chunk_boundary_prf(
        _md_doc(tmp_path), BEFORE_TITLES, 7)
    assert r["_tolerance_chars"] == {"value": 7,
                                     "reason": None}


# ---------- ipynb 真实产物几何 ----------

def test_ipynb_three_chunks(tmp_path):
    d = _nb_doc(tmp_path)
    assert [c["text"] for c in d["chunks"]] == [
        "H para one two", "Sub tail", "T3 more"]


def test_ipynb_single_anchor_tol0(tmp_path):
    r = chunk_boundary_prf(
        _nb_doc(tmp_path),
        _ann(("Sub", "before")), 0)
    assert r["chunk_boundary_precision"]["value"] == 0.0
    assert r["chunk_boundary_recall"]["value"] == 0.0


def test_ipynb_single_anchor_partial(tmp_path):
    r = chunk_boundary_prf(
        _nb_doc(tmp_path),
        _ann(("Sub", "before")), 1)
    assert r["chunk_boundary_precision"][
        "value"] == 0.5
    assert r["chunk_boundary_recall"]["value"] == 1.0
    assert r["chunk_boundary_f1"][
        "value"] == 0.6666666666666666


def test_ipynb_two_anchors_tol1_full(tmp_path):
    r = chunk_boundary_prf(
        _nb_doc(tmp_path),
        _ann(("Sub", "before"), ("T3", "before")), 1)
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 1.0
    assert r["chunk_boundary_f1"]["value"] == 1.0


def test_ipynb_after_tail_tol0(tmp_path):
    r = chunk_boundary_prf(
        _nb_doc(tmp_path),
        _ann(("two", "after"), ("tail", "after")), 0)
    assert r["chunk_boundary_f1"]["value"] == 1.0


# ---------- 单 chunk / 缺失 marker / None ----------

def test_single_chunk_precision_null(tmp_path):
    d = _md_doc(tmp_path, md="# H\n\none short para\n",
                mc=400)
    assert len(d["chunks"]) == 1
    r = chunk_boundary_prf(
        d, _ann(("H", "before")), 30)
    assert r["chunk_boundary_precision"] == {
        "value": None,
        "reason": "no_predicted_boundaries"}


def test_single_chunk_recall_zero(tmp_path):
    d = _md_doc(tmp_path, md="# H\n\none short para\n",
                mc=400)
    r = chunk_boundary_prf(
        d, _ann(("H", "before")), 30)
    assert r["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}


def test_single_chunk_f1_null(tmp_path):
    d = _md_doc(tmp_path, md="# H\n\none short para\n",
                mc=400)
    r = chunk_boundary_prf(
        d, _ann(("H", "before")), 30)
    assert r["chunk_boundary_f1"] == {
        "value": None,
        "reason": "no_predicted_boundaries"}


def test_missing_marker_precision_zero(tmp_path):
    d = _md_doc(tmp_path, md="# H\n\na\n\n## S\n\nb\n")
    r = chunk_boundary_prf(
        d, _ann(("ZZZNOTTHERE", "before")), 30)
    assert r["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}


def test_missing_marker_recall_null(tmp_path):
    d = _md_doc(tmp_path, md="# H\n\na\n\n## S\n\nb\n")
    r = chunk_boundary_prf(
        d, _ann(("ZZZNOTTHERE", "before")), 30)
    assert r["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}


def test_missing_marker_f1_null(tmp_path):
    d = _md_doc(tmp_path, md="# H\n\na\n\n## S\n\nb\n")
    r = chunk_boundary_prf(
        d, _ann(("ZZZNOTTHERE", "before")), 30)
    assert r["chunk_boundary_f1"] == {
        "value": None,
        "reason": "precision_or_recall_not_evaluated"}


def test_missing_marker_recorded(tmp_path):
    d = _md_doc(tmp_path, md="# H\n\na\n\n## S\n\nb\n")
    r = chunk_boundary_prf(
        d, _ann(("ZZZNOTTHERE", "before")), 30)
    assert r["_missing_markers"] == {
        "value": ["ZZZNOTTHERE"], "reason": None}


# ---------- document None ----------

def test_doc_none_all_pipeline_failed():
    r = chunk_boundary_prf(
        None, _ann(("x", "before")), 30)
    for name in ("chunk_boundary_precision",
                 "chunk_boundary_recall",
                 "chunk_boundary_f1"):
        assert r[name] == {
            "value": None,
            "reason": "pipeline_failed"}, name


# ---------- figure_caption 恒 null ----------

def test_figure_caption_null_on_real_md(tmp_path):
    from evaluation.annotation_metrics import (
        figure_caption_prf)
    r = figure_caption_prf(_md_doc(tmp_path), None)
    for name in r:
        assert r[name]["value"] is None, name
        assert r[name]["reason"] == \
            "parser_does_not_emit_relations"
