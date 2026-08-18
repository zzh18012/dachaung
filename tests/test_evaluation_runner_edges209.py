"""evaluation/runner.py 第六百四十二轮 edges 测试（Round 1198）。

补强 edges208 未触及的角度（第五百七十批，probe 实证）。

新角度（字号盲合流 / 宽距分离）：
- **近距字号盲合**——20pt 行 + 12pt
  行 y 差 15 → 合单 paragraph（字号
  不参与行聚类，只看 y 间距首锁）；
  合并段以句号结尾 → 段类
- **宽距分离**——y 差 40 → [heading,
  paragraph] 两元素（20pt 大字无
  特判，仍走 short_line）
- **预算切两块**——max_chars 50：
  [23, 44] 各 1 源；"words" after
  → 全 1.0、"title."（流尾）→ 全
  0.0、双锚 → P 1.0 / R 0.5
- forbidden tokens 第六百七十批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _build_pdf(objects, n_obj) -> bytes:
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objects[num] + b"endobj\n")
    xref_pos = len(out)
    out += b"xref\n0 " + str(n_obj).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for num in range(1, n_obj):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size " + str(n_obj).encode()
            + b"/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


def _T(text, x, y, size) -> bytes:
    return ("BT /F1 %d Tf %d %d Td (%s) Tj ET\n"
            % (size, x, y, text)).encode()


def _pdf(y_body) -> bytes:
    s = (_T("Big sized opening words", 10, 700, 20)
         + _T("small body line follows "
              + ("closely under it."
                 if y_body > 670 else
                 "far below the title."),
              10, y_body, 12))
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 500 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 6)


def _board(tmp_path, doc_id, y_body, anchors=None):
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "a").mkdir(exist_ok=True)
    (tmp_path / "s" / f"{doc_id}.pdf").write_bytes(_pdf(y_body))
    docs = [{"doc_id": doc_id, "path": f"s/{doc_id}.pdf",
             "source_type": "pdf"}]
    if anchors is not None:
        (tmp_path / "a" / "a.json").write_text(json.dumps({
            "annotation_version": "1.0", "doc_id": doc_id,
            "chunk_boundary_anchors": anchors}),
            encoding="utf-8")
        docs[0]["annotation_file"] = "a/a.json"
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": docs}), encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 近距字号盲合 ----------

def test_mixed_size_near_merge_batch396(tmp_path):
    _board(tmp_path, "nr", 685)
    doc, errors = process_single(
        tmp_path / "s" / "nr.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == ["paragraph"]
    assert els[0]["content"] == (
        "Big sized opening words small body "
        "line follows closely under it.")


# ---------- 宽距分离 ----------

def test_mixed_size_far_split_batch396(tmp_path):
    _board(tmp_path, "fr", 660)
    doc, errors = process_single(
        tmp_path / "s" / "fr.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == ["heading", "paragraph"]
    assert els[0]["content"] == "Big sized opening words"
    assert els[0]["metadata"] == {
        "level": 0, "heuristic": "short_line"}
    assert els[1]["content"] == (
        "small body line follows far below the title.")


def test_mixed_size_far_chunks_batch396(tmp_path):
    _board(tmp_path, "fr2", 660)
    doc, errors = process_single(
        tmp_path / "s" / "fr2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=50)
    chunks = doc.to_dict()["chunks"]
    assert [c["text"] for c in chunks] == [
        "Big sized opening words",
        "small body line follows far below the title."]
    assert all(len(c["source_element_ids"]) == 1
               for c in chunks)


# ---------- 锚 ----------

def test_words_anchor_batch396(tmp_path):
    r = run_evaluation(_board(tmp_path, "a1", 660, [
        {"marker": "words", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_title_anchor_batch396(tmp_path):
    r = run_evaluation(_board(tmp_path, "a2", 660, [
        {"marker": "title.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.0, "reason": None}


def test_both_anchors_batch396(tmp_path):
    r = run_evaluation(_board(tmp_path, "a3", 660, [
        {"marker": "words", "position": "after"},
        {"marker": "title.", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 0.5, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


# ---------- 指标 ----------

def test_mixed_size_metrics_batch396(tmp_path):
    r = run_evaluation(_board(tmp_path, "mx", 660),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=50)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "paragraph": 1},
        "reason": None}
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["pdf_locator_valid_ratio"] == {"value": 1.0,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch396():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百七十批 ----------

def test_source_no_eval_batch396():
    assert "eval(" not in _src()


def test_source_no_exec_batch396():
    assert "exec(" not in _src()


def test_source_no_compile_batch396():
    assert "compile(" not in _src()


def test_source_no_globals_batch396():
    assert "globals(" not in _src()


def test_source_no_locals_batch396():
    assert "locals(" not in _src()


def test_source_no_os_system_batch396():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch396():
    assert "subprocess" not in _src()


def test_source_no_popen_batch396():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch396():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch396():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch396():
    assert "socket" not in _src()


def test_source_no_requests_batch396():
    assert "requests" not in _src()


def test_source_no_urllib_batch396():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch396():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch396():
    assert "yield" not in _src()


def test_source_no_async_await_batch396():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch396():
    assert _src().count("open(") == 2
