"""evaluation/runner.py 第六百二十轮 edges 测试（Round 1176）。

补强 edges188 未触及的角度（第五百四十八批，probe 实证）。

新角度（预算溢出元素界冲刷 / 重复锚有序配对）：
- **溢出冲刷在元素界**——142+139 两段（和 282 >
  200）→ 2 chunks 各 1 源、长度恰 142/139——
  顺序缓冲超预算时在**元素边界**冲刷，不切句中
  （与 edges161 单元素超长 forced_char 成对照：
  预算冲刷 vs 文本硬切两级机制首锁）
- **三段 103/102/103**——每段独立成块：加入下
  一段将超 200 即冲刷（accumulate-overflow 规
  则，元素级）
- **重复锚有序配对**——两个 "sixteen." after 锚
  （"sixteen." 在流中三现）：顺序搜索第 1 锚取
  首现=界 1、第 2 锚续取次现=界 2 → P/R/F1 全
  1.0（与 edges185 单锚首现落空成镜像：双锚吃
  下前两现）
- forbidden tokens 第六百四十八批（open 2）
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


def _T(text: str, y: int) -> bytes:
    return ("BT /F1 12 Tf 10 %d Td (%s) Tj ET\n"
            % (y, text)).encode()


_P1 = ("Alpha sentence one is fairly long and wordy here. "
       "Alpha sentence two continues the flow onward. "
       "Alpha sentence three wraps the first page now.")
_P2 = ("Beta sentence one starts the second page fresh. "
       "Beta sentence two keeps the second page going. "
       "Beta sentence three ends the whole document.")

_A = ("Alpha one two three four five six seven eight nine ten "
      "eleven twelve thirteen fourteen fifteen sixteen.")
_B = ("Beta one two three four five six seven eight nine ten "
      "eleven twelve thirteen fourteen fifteen sixteen.")
_C = ("Gamma one two three four five six seven eight nine ten "
      "eleven twelve thirteen fourteen fifteen sixteen.")


def _two_page_overflow_pdf() -> bytes:
    s1 = _T(_P1, 750)
    s2 = _T(_P2, 750)
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 5 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 900 800]"
            b"/Resources<</Font<</F1 7 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
        5: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 900 800]"
            b"/Resources<</Font<</F1 7 0 R>>>>/Contents 6 0 R>>"),
        6: (b"<</Length " + str(len(s2)).encode()
            + b">>stream\n" + s2 + b"\nendstream "),
        7: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 8)


def _triple_pdf() -> bytes:
    s = _T(_A, 750) + _T(_B, 700) + _T(_C, 650)
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 900 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 6)


def _board(tmp_path, doc_id, anchors=None, triple=False):
    (tmp_path / "s").mkdir(exist_ok=True)
    (tmp_path / "a").mkdir(exist_ok=True)
    (tmp_path / "s" / f"{doc_id}.pdf").write_bytes(
        _triple_pdf() if triple else _two_page_overflow_pdf())
    docs = [{"doc_id": doc_id, "path": f"s/{doc_id}.pdf",
             "source_type": "pdf"}]
    if anchors is not None:
        (tmp_path / "a" / "a.json").write_text(json.dumps({
            "annotation_version": "1.0", "doc_id": doc_id,
            "chunk_boundary_anchors": anchors}), encoding="utf-8")
        docs[0]["annotation_file"] = "a/a.json"
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({"manifest_version": "1.0",
                              "devset_status": "incomplete",
                              "documents": docs}), encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 溢出冲刷在元素界 ----------

def test_overflow_two_page_chunks_batch374(tmp_path):
    _board(tmp_path, "ov")
    doc, errors = process_single(
        tmp_path / "s" / "ov.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    chunks = doc.to_dict()["chunks"]
    assert [c["metadata"]["strategy"] for c in chunks] == [
        "sequential", "sequential"]
    assert [len(c["source_element_ids"]) for c in chunks] == [1, 1]
    assert [len(c["text"]) for c in chunks] == [142, 139]
    assert chunks[0]["text"].startswith("Alpha sentence one")
    assert chunks[1]["text"].startswith("Beta sentence one")


def test_overflow_element_boundary_batch374(tmp_path):
    _board(tmp_path, "ov2", triple=True)
    doc, errors = process_single(
        tmp_path / "s" / "ov2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert [c["metadata"]["strategy"] for c in chunks] == [
        "sequential"] * 3
    assert all(len(c["source_element_ids"]) == 1
               for c in chunks)
    assert [c["text"][:5] for c in chunks] == [
        "Alpha", "Beta ", "Gamma"]
    assert all(c["text"].endswith("sixteen.")
               for c in chunks)


# ---------- 重复锚有序配对 ----------

def test_duplicate_anchor_pairing_batch374(tmp_path):
    r = run_evaluation(_board(tmp_path, "ov3", [
        {"marker": "sixteen.", "position": "after"},
        {"marker": "sixteen.", "position": "after"}],
        triple=True),
        tmp_path / "r.json", parser_name="fallback",
        max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


# ---------- 指标 ----------

def test_overflow_metrics_batch374(tmp_path):
    r = run_evaluation(_board(tmp_path, "ov4", triple=True),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["element_count_by_type"] == {
        "value": {"paragraph": 3}, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch374():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("metrics") == 13
    assert src.count("manifest") == 5


# ---------- forbidden tokens 第六百四十八批 ----------

def test_source_no_eval_batch374():
    assert "eval(" not in _src()


def test_source_no_exec_batch374():
    assert "exec(" not in _src()


def test_source_no_compile_batch374():
    assert "compile(" not in _src()


def test_source_no_globals_batch374():
    assert "globals(" not in _src()


def test_source_no_locals_batch374():
    assert "locals(" not in _src()


def test_source_no_os_system_batch374():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch374():
    assert "subprocess" not in _src()


def test_source_no_popen_batch374():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch374():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch374():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch374():
    assert "socket" not in _src()


def test_source_no_requests_batch374():
    assert "requests" not in _src()


def test_source_no_urllib_batch374():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch374():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch374():
    assert "yield" not in _src()


def test_source_no_async_await_batch374():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch374():
    assert _src().count("open(") == 2
