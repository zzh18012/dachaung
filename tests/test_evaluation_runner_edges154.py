"""evaluation/runner.py 第五百七十九轮 edges 测试（Round 1135）。

补强 edges153 未触及的角度（第五百一十一批，probe 实证）。

新角度（真 PDF heading / caption 分类通道）：
- **短行无句读 → heading**——35 字符无句末标点独行 →
  element type heading + metadata {level 0, heuristic
  "short_line"}；runner 级 by_type {heading: 1} +
  heading_boundary_compliance **真值 1.0**（真 PDF 板上
  该指标首次脱离 null no_heading_elements）
- **超长 heading 不劈**——35 字符 heading 配 max_chars
  32 → 恰 1 个整块 strategy sequential——heading 分支
  优先于长文劈块，heading 永不内切（首锁）
- **Figure 前缀 → caption**——"Figure 1: a caption here."
  → element caption + {heuristic: "caption_regex"} +
  isolated_caption 单块——caption 独立成块通道首锁
- **caption 板 heading 指标 null**——caption 不是 heading
  → no_heading_elements 照旧
- forbidden tokens 第六百零八批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _build_one_page_pdf(stream) -> bytes:
    objects = {}
    objects[1] = b"<</Type/Catalog/Pages 2 0 R>>"
    objects[2] = b"<</Type/Pages/Kids[3 0 R]/Count 1>>"
    objects[3] = (
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 500 100]"
        b"/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>")
    objects[4] = b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"
    objects[5] = (
        b"<</Length " + str(len(stream)).encode() + b">>stream\n"
        + stream + b"\nendstream ")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objects[num] + b"endobj\n")
    xref_pos = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


def _board(tmp_path):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / "h.pdf").write_bytes(_build_one_page_pdf(
        b"BT /F1 12 Tf 10 80 Td "
        b"(Alpha beta gamma delta epsilon zeta) Tj ET"))
    (tmp_path / "samples" / "c.pdf").write_bytes(_build_one_page_pdf(
        b"BT /F1 12 Tf 10 80 Td "
        b"(Figure 1: a caption here.) Tj ET"))
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "h", "path": "samples/h.pdf",
             "source_type": "pdf"},
            {"doc_id": "c", "path": "samples/c.pdf",
             "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 短行无句读 → heading ----------

def test_short_line_heading_batch334(tmp_path):
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "h.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert len(els) == 1
    assert els[0]["type"] == "heading"
    assert els[0]["metadata"] == {"level": 0,
                                  "heuristic": "short_line"}


def test_heading_doc_metrics_batch334(tmp_path):
    r = run_evaluation(_board(tmp_path), tmp_path / "r.json",
                       parser_name="fallback", max_chars=200)
    h = r["per_doc"][0]["metrics"]
    assert h["element_count_by_type"] == {
        "value": {"heading": 1}, "reason": None}
    assert h["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


# ---------- 超长 heading 不劈 ----------

def test_oversized_heading_not_split_batch334(tmp_path):
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "h.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=32)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert len(chunks) == 1
    assert chunks[0]["text"] == \
        "Alpha beta gamma delta epsilon zeta"
    assert chunks[0]["metadata"]["strategy"] == "sequential"


# ---------- Figure 前缀 → caption ----------

def test_caption_classification_batch334(tmp_path):
    _board(tmp_path)
    doc, errors = process_single(
        tmp_path / "samples" / "c.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    d = doc.to_dict()
    els = d["elements"]
    assert len(els) == 1
    assert els[0]["type"] == "caption"
    assert els[0]["metadata"] == {"heuristic": "caption_regex"}
    assert len(d["chunks"]) == 1
    assert d["chunks"][0]["metadata"]["strategy"] == \
        "isolated_caption"


def test_caption_doc_metrics_batch334(tmp_path):
    r = run_evaluation(_board(tmp_path), tmp_path / "r.json",
                       parser_name="fallback", max_chars=200)
    c = r["per_doc"][1]["metrics"]
    assert c["element_count_by_type"] == {
        "value": {"caption": 1}, "reason": None}
    assert c["heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch334():
    src = _src()
    assert src.count("metrics") == 13
    assert src.count("manifest") == 5
    assert src.count("process_single") == 6


# ---------- forbidden tokens 第六百零八批 ----------

def test_source_no_eval_batch334():
    assert "eval(" not in _src()


def test_source_no_exec_batch334():
    assert "exec(" not in _src()


def test_source_no_compile_batch334():
    assert "compile(" not in _src()


def test_source_no_globals_batch334():
    assert "globals(" not in _src()


def test_source_no_locals_batch334():
    assert "locals(" not in _src()


def test_source_no_os_system_batch334():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch334():
    assert "subprocess" not in _src()


def test_source_no_popen_batch334():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch334():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch334():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch334():
    assert "socket" not in _src()


def test_source_no_requests_batch334():
    assert "requests" not in _src()


def test_source_no_urllib_batch334():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch334():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch334():
    assert "yield" not in _src()


def test_source_no_async_await_batch334():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch334():
    assert _src().count("open(") == 2
