"""evaluation/runner.py 第五百七十八轮 edges 测试（Round 1134）。

补强 edges152 未触及的角度（第五百一十批，probe 实证）。

新角度（括号转义文本 × 标注通道）：
- **括号 marker 精确命中**——PDF 字面串 \\(paren\\) 解出真
  括号，marker "(paren)" after 恰落 30 字符白界劈点 d=0
  → P/R/F1 全 1.0（转义文本进标注匹配通道首锁）
- **单块无边界态**——同板 max_chars 200 合一块 → 无预测
  边界：P null no_predicted_boundaries / R 0.0 /
  F1 null no_predicted_boundaries——marker 存在但无处
  匹配（真 PDF 板首锁）
- forbidden tokens 第六百零七批（open 2）
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


def _paren_pdf() -> bytes:
    return _build_one_page_pdf(
        rb"BT /F1 12 Tf 10 80 Td (Alpha beta gamma delta "
        rb"\(paren\) epsilon zeta eta theta.) Tj ET")


def _board(tmp_path, doc_id):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "anns").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(
        _paren_pdf())
    (tmp_path / "anns" / f"{doc_id}.json").write_text(json.dumps({
        "annotation_version": "1.0", "doc_id": doc_id,
        "chunk_boundary_anchors": [
            {"marker": "(paren)", "position": "after"}]}),
        encoding="utf-8")
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id,
                       "path": f"samples/{doc_id}.pdf",
                       "source_type": "pdf",
                       "annotation_file":
                           f"anns/{doc_id}.json"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 括号 marker 精确命中 ----------

def test_paren_marker_exact_hit_batch333(tmp_path):
    _board(tmp_path, "pm")
    doc, errors = process_single(
        tmp_path / "samples" / "pm.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=32)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert len(chunks) == 2
    assert chunks[0]["text"] == "Alpha beta gamma delta (paren)"
    r = run_evaluation(_board(tmp_path, "pm2"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=32)
    m = r["per_doc"][0]["metrics"]
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert m[k] == {"value": 1.0, "reason": None}


# ---------- 单块无边界态 ----------

def test_single_chunk_no_boundary_batch333(tmp_path):
    r = run_evaluation(_board(tmp_path, "sc"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert m["chunk_boundary_recall"] == {"value": 0.0,
                                          "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": None, "reason": "no_predicted_boundaries"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch333():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("load_annotation") == 2


# ---------- forbidden tokens 第六百零七批 ----------

def test_source_no_eval_batch333():
    assert "eval(" not in _src()


def test_source_no_exec_batch333():
    assert "exec(" not in _src()


def test_source_no_compile_batch333():
    assert "compile(" not in _src()


def test_source_no_globals_batch333():
    assert "globals(" not in _src()


def test_source_no_locals_batch333():
    assert "locals(" not in _src()


def test_source_no_os_system_batch333():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch333():
    assert "subprocess" not in _src()


def test_source_no_popen_batch333():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch333():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch333():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch333():
    assert "socket" not in _src()


def test_source_no_requests_batch333():
    assert "requests" not in _src()


def test_source_no_urllib_batch333():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch333():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch333():
    assert "yield" not in _src()


def test_source_no_async_await_batch333():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch333():
    assert _src().count("open(") == 2
