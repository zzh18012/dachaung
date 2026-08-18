"""evaluation/runner.py 第六百五十三轮 edges 测试（Round 1226）。

补强 edges217 未触及的角度（第五百九十八批，probe 实证）。

新角度（单长行劈三块 / 空白边界 / 一源多块）：
- **单长行劈三块**——159 字符
  段落（40 个 w 词）mc60 → 3 块
  [59, 59, 39]，全部同源 e0000
  （一元素多块首锁）
- **空白边界**——切点落 w14|
  w15 与 w29|w30 词间（不切词
  中）
- **roundtrip 不丢**——join
  (chunks) == 元素 content
- **贴界双锚全中**——"w14"
  after 末 59 恰界 1、"w29"
  after 末 118 恰界 2 → P/R/F1
  全 1.0（块内文本拼接定位首锁）
- forbidden tokens 第六百九十五批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _pdf() -> bytes:
    words = " ".join("w%02d" % i for i in range(40))
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n"
         % words).encode()
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xref_pos = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF\n")
    return bytes(out)


def _pdf_path(tmp_path, doc_id):
    (tmp_path / "s").mkdir(exist_ok=True)
    p = tmp_path / "s" / f"{doc_id}.pdf"
    p.write_bytes(_pdf())
    return p


def _board(tmp_path, doc_id, anchors=None):
    _pdf_path(tmp_path, doc_id)
    docs = [{"doc_id": doc_id, "path": f"s/{doc_id}.pdf",
             "source_type": "pdf"}]
    if anchors is not None:
        (tmp_path / "a").mkdir(exist_ok=True)
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


# ---------- 单长行劈三块 ----------

def test_long_line_three_chunks_batch424(tmp_path):
    doc, errors = process_single(
        _pdf_path(tmp_path, "ll"), tmp_path / "o.json",
        parser_name="fallback", max_chars=60)
    assert errors == []
    d = doc.to_dict()
    els = d["elements"]
    assert len(els) == 1
    assert els[0]["type"] == "paragraph"
    assert len(els[0]["content"]) == 159
    chunks = d["chunks"]
    assert [len(c["text"]) for c in chunks] == [59, 59, 39]


def test_one_element_many_chunks_batch424(tmp_path):
    doc, errors = process_single(
        _pdf_path(tmp_path, "om"), tmp_path / "o.json",
        parser_name="fallback", max_chars=60)
    assert errors == []
    d = doc.to_dict()
    eid = d["elements"][0]["element_id"]
    for c in d["chunks"]:
        assert c["source_element_ids"] == [eid]


def test_whitespace_split_points_batch424(tmp_path):
    doc, errors = process_single(
        _pdf_path(tmp_path, "ws"), tmp_path / "o.json",
        parser_name="fallback", max_chars=60)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert chunks[0]["text"].endswith("w14")
    assert chunks[1]["text"].startswith("w15")
    assert chunks[1]["text"].endswith("w29")
    assert chunks[2]["text"].startswith("w30")


def test_roundtrip_no_loss_batch424(tmp_path):
    doc, errors = process_single(
        _pdf_path(tmp_path, "rt"), tmp_path / "o.json",
        parser_name="fallback", max_chars=60)
    assert errors == []
    d = doc.to_dict()
    joined = " ".join(c["text"] for c in d["chunks"])
    assert joined == d["elements"][0]["content"]


# ---------- 贴界双锚全中 ----------

def test_boundary_anchors_full_hit_batch424(tmp_path):
    r = run_evaluation(_board(tmp_path, "a1", [
        {"marker": "w14", "position": "after"},
        {"marker": "w29", "position": "after"}]),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=60)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_split_board_metrics_batch424(tmp_path):
    r = run_evaluation(_board(tmp_path, "mx"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=60)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["element_count_total"] == {"value": 1,
                                        "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch424():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第六百九十五批 ----------

def test_source_no_eval_batch424():
    assert "eval(" not in _src()


def test_source_no_exec_batch424():
    assert "exec(" not in _src()


def test_source_no_compile_batch424():
    assert "compile(" not in _src()


def test_source_no_globals_batch424():
    assert "globals(" not in _src()


def test_source_no_locals_batch424():
    assert "locals(" not in _src()


def test_source_no_os_system_batch424():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch424():
    assert "subprocess" not in _src()


def test_source_no_popen_batch424():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch424():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch424():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch424():
    assert "socket" not in _src()


def test_source_no_requests_batch424():
    assert "requests" not in _src()


def test_source_no_urllib_batch424():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch424():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch424():
    assert "yield" not in _src()


def test_source_no_async_await_batch424():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch424():
    assert _src().count("open(") == 2
