# -*- coding: utf-8 -*-
"""Stage 9 批次 26：标注校验器测试（契约五项检查逐失败码覆盖）。"""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from stage9.validation import validate_annotation, validate_split_constraints

ROOT = Path(__file__).resolve().parents[1]

STREAM = "Alpha beta gamma. Delta epsilon. Zeta eta theta."


def _sha(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _base_annotation():
    """合法样例：三个 text unit 精确平铺字符流 + 一个 nontext unit。

    平铺规则：unit 间分隔符（单空格）归入前一 unit 的 span 末尾，
    故 [0,18) [18,33) [33,48) 连续无重叠全覆盖（流长 48）。
    """
    return {
        "doc_id": "acad-01-sentencebert",
        "annotation_schema": "v1.1",
        "sentence_splitter": "v1",
        "normalization": "fold-ws-v1",
        "annotator": "claude-draft + user-review",
        "stream": STREAM,
        "units": [
            {"unit_id": "u0001", "kind": "heading", "page": 1,
             "body_index": None,
             "char_span": [0, 18], "norm_text_hash": _sha(STREAM[0:18]),
             "text_preview": STREAM[0:18], "gold_segment_id": "g01",
             "hard_boundary_before": True},
            {"unit_id": "u0002", "kind": "sentence", "page": 1,
             "body_index": None,
             "char_span": [18, 33], "norm_text_hash": _sha(STREAM[18:33]),
             "text_preview": STREAM[18:33], "gold_segment_id": "g02",
             "hard_boundary_before": False,
             "linked_nontext": ["img:figure1"]},
            {"unit_id": "u0003", "kind": "sentence", "page": 2,
             "body_index": None,
             "char_span": [33, 48], "norm_text_hash": _sha(STREAM[33:48]),
             "text_preview": STREAM[33:48], "gold_segment_id": "g02",
             "hard_boundary_before": True},
            {"unit_id": "u0004", "kind": "nontext", "page": 1,
             "body_index": None,
             "char_span": None, "norm_text_hash": None,
             "nontext_ref": "img:figure1", "gold_segment_id": "g02",
             "hard_boundary_before": False},
        ],
        "segments": [
            {"gold_segment_id": "g01", "hint": "标题", "kind": "frontmatter"},
            {"gold_segment_id": "g02", "hint": "正文", "kind": "body"},
        ],
    }


def _manifest_index():
    return {"acad-01-sentencebert": {"doc_id": "acad-01-sentencebert",
                                     "split": "dev", "format": "pdf"}}


def _validate(data):
    return validate_annotation(data, _manifest_index())[1]


def test_valid_annotation_passes():
    doc_id, fails = validate_annotation(_base_annotation(), _manifest_index())
    assert doc_id == "acad-01-sentencebert"
    assert fails == []


def test_frozen_value_splitter():
    data = _base_annotation()
    data["sentence_splitter"] = "v2"
    assert "frozen_value" in [f.code for f in _validate(data)]


def test_frozen_value_annotation_schema():
    data = _base_annotation()
    del data["annotation_schema"]
    assert "frozen_value" in [f.code for f in _validate(data)]
    data = _base_annotation()
    data["annotation_schema"] = "v1.0"
    assert "frozen_value" in [f.code for f in _validate(data)]


def test_docx_page_null_body_index_ok():
    data = _base_annotation()
    for u in data["units"]:
        u["page"] = None
        u["body_index"] = 7
    idx = {"acad-01-sentencebert": {"doc_id": "acad-01-sentencebert",
                                    "split": "dev", "format": "docx"}}
    doc_id, fails = validate_annotation(data, idx)
    assert fails == [], [f.to_json() for f in fails]


def test_dual_locator_rejected():
    data = _base_annotation()
    data["units"][0]["body_index"] = 3
    assert "dual_locator" in [f.code for f in _validate(data)]


def test_locator_format_mismatch():
    docx_in_manifest = {"acad-01-sentencebert":
                        {"doc_id": "acad-01-sentencebert",
                         "split": "dev", "format": "docx"}}
    data = _base_annotation()  # page 有值 → DOCX 篇违规
    fails = validate_annotation(data, docx_in_manifest)[1]
    assert "locator_format_mismatch" in [f.code for f in fails]
    pdf_in_manifest = _manifest_index()  # body_index 有值 → PDF 篇违规
    data = _base_annotation()
    data["units"][0]["page"] = None
    data["units"][0]["body_index"] = 3
    fails = validate_annotation(data, pdf_in_manifest)[1]
    assert "locator_format_mismatch" in [f.code for f in fails]


def test_bad_page_zero_and_body_index_zero():
    data = _base_annotation()
    data["units"][0]["page"] = 0
    codes = [f.code for f in _validate(data)]
    assert "bad_type" in codes


def test_unit_order_violation():
    data = _base_annotation()  # units 列表序 u1[0,18) u2[18,33) u3[33,48)
    data["units"][0], data["units"][2] = data["units"][2], data["units"][0]
    assert "unit_order" in [f.code for f in _validate(data)]


def test_stream_not_folded():
    data = _base_annotation()
    data["stream"] = "Alpha beta.  Delta."
    assert "stream_not_folded" in [f.code for f in _validate(data)]


def test_bad_unit_id_format():
    data = _base_annotation()
    data["units"][0]["unit_id"] = "x1"
    assert "bad_unit_id_format" in [f.code for f in _validate(data)]


def test_duplicate_unit_id():
    data = _base_annotation()
    data["units"][1]["unit_id"] = "u0001"
    assert "duplicate_unit_id" in [f.code for f in _validate(data)]


def test_bad_kind():
    data = _base_annotation()
    data["units"][0]["kind"] = "paragraph"
    assert "bad_type" in [f.code for f in _validate(data)]


def test_span_out_of_range():
    data = _base_annotation()
    data["units"][0]["char_span"] = [0, 999]
    codes = [f.code for f in _validate(data)]
    assert "span_out_of_range" in codes


def test_hash_mismatch():
    data = _base_annotation()
    data["units"][1]["norm_text_hash"] = _sha("篡改后的文本")
    assert "hash_mismatch" in [f.code for f in _validate(data)]


def test_preview_mismatch():
    data = _base_annotation()
    data["units"][2]["text_preview"] = "不在流中的前缀"
    assert "preview_mismatch" in [f.code for f in _validate(data)]


def test_nontext_span_must_be_null():
    data = _base_annotation()
    data["units"][3]["char_span"] = [0, 5]
    assert "span_not_null_nontext" in [f.code for f in _validate(data)]


def test_bad_nontext_ref():
    data = _base_annotation()
    data["units"][3]["nontext_ref"] = "figure1"
    codes = [f.code for f in _validate(data)]
    assert "bad_nontext_ref" in codes
    assert "unknown_nontext_ref" in codes  # linked_nontext 闭合失败


def test_duplicate_nontext_ref():
    data = _base_annotation()
    dup = copy.deepcopy(data["units"][3])
    dup["unit_id"] = "u0005"
    dup["nontext_ref"] = "img:figure1"
    data["units"].append(dup)
    assert "duplicate_nontext_ref" in [f.code for f in _validate(data)]


def test_unknown_segment_reference():
    data = _base_annotation()
    data["units"][1]["gold_segment_id"] = "g99"
    assert "unknown_segment" in [f.code for f in _validate(data)]


def test_unreferenced_segment():
    data = _base_annotation()
    data["segments"].append({"gold_segment_id": "g03"})
    assert "unreferenced_segment" in [f.code for f in _validate(data)]


def test_duplicate_segment_id():
    data = _base_annotation()
    data["segments"].append({"gold_segment_id": "g01"})
    assert "duplicate_segment_id" in [f.code for f in _validate(data)]


def test_span_overlap():
    data = _base_annotation()
    data["units"][1]["char_span"] = [10, 33]
    data["units"][1]["norm_text_hash"] = _sha(STREAM[10:33])
    data["units"][1]["text_preview"] = STREAM[10:33]
    assert "span_overlap" in [f.code for f in _validate(data)]


def test_span_gap():
    data = _base_annotation()
    data["units"][1]["char_span"] = [20, 33]
    data["units"][1]["norm_text_hash"] = _sha(STREAM[20:33])
    data["units"][1]["text_preview"] = STREAM[20:33]
    codes = [f.code for f in _validate(data)]
    assert "span_gap" in codes


def test_missing_units():
    data = _base_annotation()
    data["units"] = []
    assert "missing_field" in [f.code for f in _validate(data)]


def test_doc_not_in_manifest():
    data = _base_annotation()
    data["doc_id"] = "unknown-doc"
    assert "doc_not_in_manifest" in [f.code for f in _validate(data)]


def _manifest_data():
    docs = []
    plan = {"dev": ["academic"] * 5 + ["tech_report"] * 5
            + ["product_manual"] * 4,
            "comparison": ["academic", "academic", "tech_report",
                           "product_manual"],
            "holdout": ["academic"] * 2 + ["tech_report"] * 2
            + ["product_manual"] * 2}
    for split, domains in plan.items():
        for i, dom in enumerate(domains):
            docs.append({"doc_id": "%s-%02d" % (split, i), "domain": dom,
                         "split": split})
    docs.append({"doc_id": "spare-01", "domain": "tech_report",
                 "split": None})
    return {"docs": docs}


def test_split_constraints_pass():
    manifest = _manifest_data()
    annotated = {d["doc_id"] for d in manifest["docs"] if d["split"]}
    fails, summary = validate_split_constraints(manifest, annotated)
    assert fails == []
    assert summary["split_counts"] == {"comparison": 4, "dev": 14,
                                       "holdout": 6}


def test_split_constraints_count_mismatch():
    manifest = _manifest_data()
    manifest["docs"] = manifest["docs"][:-3]  # 挖掉 spare+两个 holdout 产品域
    annotated = {d["doc_id"] for d in manifest["docs"] if d["split"]}
    fails, _ = validate_split_constraints(manifest, annotated)
    assert "split_count_mismatch" in [f.code for f in fails]
    assert "split_domain_coverage" in [f.code for f in fails]


def test_split_constraints_missing_annotation():
    manifest = _manifest_data()
    annotated = {d["doc_id"] for d in manifest["docs"] if d["split"]}
    annotated.discard("dev-00")
    fails, _ = validate_split_constraints(manifest, annotated)
    assert "missing_annotation" in [f.code for f in fails]


def test_cli_exit_codes(tmp_path):
    script = ROOT / "scripts" / "stage9_validate_annotations.py"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_manifest_data_with_annotation_doc()),
                        encoding="utf-8")
    good = tmp_path / "good.json"
    good.write_text(json.dumps(_base_annotation(), ensure_ascii=False),
                    encoding="utf-8")
    bad = tmp_path / "bad.json"
    data = _base_annotation()
    data["units"][1]["norm_text_hash"] = _sha("wrong")
    bad.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def run(*args):
        return subprocess.run(
            [sys.executable, str(script), "--manifest", str(manifest),
             *args], capture_output=True, text=True, cwd=str(ROOT))

    ok = run("--annotations", str(good))
    assert ok.returncode == 0, ok.stdout + ok.stderr
    nok = run("--annotations", str(bad))
    assert nok.returncode == 1
    assert "hash_mismatch" in nok.stdout
    missing = run("--annotations", str(tmp_path / "nope.json"))
    assert missing.returncode == 2
    report = tmp_path / "report.json"
    run("--annotations", str(bad), "--report", str(report))
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["summary"]["failures"] >= 1


def _manifest_data_with_annotation_doc():
    return {"docs": [{"doc_id": "acad-01-sentencebert",
                      "domain": "academic", "split": "dev"}]}
