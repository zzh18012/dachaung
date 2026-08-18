"""evaluation/runner.py 第六百六十轮 edges 测试（Round 1255）。

补强 edges224 未触及的角度（第六百二十七批，probe 实证）。

新角度（双页板 × 行距阈 2D 网格 / 页序）：
- **页内合跨页分**——wg30：每页两
  行 gap 30 → 每页 1 合并元素，页
  序 [1, 2]；wg31：gap 31 → 每页
  2 元素，页序 [1, 1, 2, 2]（阈值
  仅在页内生效 + 页界永不并首锁）
- **同串双元素**——wg30 两元素
  content 完全相同，页号是唯一区
  分位
- **块层全并**——两板均 1 chunk，
  源数 2 / 4（块层无页界）
- **per-doc ect [2, 4]** + sum 6
  ——2D 网格在 runner 指标层显形
- forbidden tokens 第七百一十八批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


def _two_page(y2: int) -> bytes:
    s1 = (("BT /F1 12 Tf 10 700 Td (Top line text here.) Tj ET\n"
           "BT /F1 12 Tf 10 %d Td (Lower line text here.) Tj ET\n"
           % y2).encode())
    s2 = s1
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R 6 0 R]/Count 2>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s1)).encode()
            + b">>stream\n" + s1 + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        6: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 7 0 R>>"),
        7: (b"<</Length " + str(len(s2)).encode()
            + b">>stream\n" + s2 + b"\nendstream "),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xp = len(out)
    out += b"xref\n0 8\n0000000000 65535 f \n"
    for num in range(1, 8):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 8/Root 1 0 R>>\nstartxref\n"
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


def _board(tmp_path):
    for did, y2 in (("wg30", 670), ("wg31", 669)):
        (tmp_path / (did + ".pdf")).write_bytes(_two_page(y2))
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": did, "path": "%s.pdf" % did,
             "source_type": "pdf"}
            for did in ("wg30", "wg31")]}), encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


def _run(tmp_path):
    return run_evaluation(_board(tmp_path), tmp_path / "r.json",
                          parser_name="fallback", max_chars=200)


def _doc(tmp_path, did, y2):
    from app.pipeline import process_single
    (tmp_path / (did + ".pdf")).write_bytes(_two_page(y2))
    d, errors = process_single(tmp_path / (did + ".pdf"),
                               tmp_path / (did + ".json"),
                               parser_name="fallback", max_chars=200)
    assert errors == []
    return d.to_dict()


# ---------- 页内合跨页分 ----------

def test_wg30_two_merged_elements_batch453(tmp_path):
    dd = _doc(tmp_path, "wg30", 670)
    assert [e["content"] for e in dd["elements"]] == [
        "Top line text here. Lower line text here.",
        "Top line text here. Lower line text here."]


def test_wg30_pages_one_two_batch453(tmp_path):
    dd = _doc(tmp_path, "wg30", 670)
    assert [e["source_locator"]["page"] for e in dd["elements"]] == [
        1, 2]


def test_wg31_four_elements_batch453(tmp_path):
    dd = _doc(tmp_path, "wg31", 669)
    assert [e["content"] for e in dd["elements"]] == [
        "Top line text here.", "Lower line text here.",
        "Top line text here.", "Lower line text here."]


def test_wg31_pages_pairwise_batch453(tmp_path):
    dd = _doc(tmp_path, "wg31", 669)
    assert [e["source_locator"]["page"] for e in dd["elements"]] == [
        1, 1, 2, 2]


# ---------- 块层全并 ----------

def test_wg30_chunk_two_sources_batch453(tmp_path):
    dd = _doc(tmp_path, "wg30", 670)
    assert len(dd["chunks"]) == 1
    assert len(dd["chunks"][0]["source_element_ids"]) == 2


def test_wg31_chunk_four_sources_batch453(tmp_path):
    dd = _doc(tmp_path, "wg31", 669)
    assert len(dd["chunks"]) == 1
    assert len(dd["chunks"][0]["source_element_ids"]) == 4


# ---------- runner 指标层 ----------

def test_per_doc_ect_two_four_batch453(tmp_path):
    r = _run(tmp_path)
    assert [p["metrics"]["element_count_total"]["value"]
            for p in r["per_doc"]] == [2, 4]


def test_summary_sum_six_batch453(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["counts"]["element_count_total"] == {
        "sum": 6, "participating_docs": 2}


def test_success_two_of_two_batch453(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["success_rates"]["pipeline_success"] == {
        "success_count": 2, "total": 2, "rate": 1.0}


def test_devset_two_pdfs_batch453(tmp_path):
    r = _run(tmp_path)
    assert r["devset"] == {
        "status": "incomplete", "file_count": 2,
        "content_group_count": 2, "pdf_count": 2, "docx_count": 0,
        "categories_covered": []}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch453():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第七百一十八批 ----------

def test_source_no_eval_batch453():
    assert "eval(" not in _src()


def test_source_no_exec_batch453():
    assert "exec(" not in _src()


def test_source_no_compile_batch453():
    assert "compile(" not in _src()


def test_source_no_globals_batch453():
    assert "globals(" not in _src()


def test_source_no_locals_batch453():
    assert "locals(" not in _src()


def test_source_no_os_system_batch453():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch453():
    assert "subprocess" not in _src()


def test_source_no_popen_batch453():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch453():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch453():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch453():
    assert "socket" not in _src()


def test_source_no_requests_batch453():
    assert "requests" not in _src()


def test_source_no_urllib_batch453():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch453():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch453():
    assert "yield" not in _src()


def test_source_no_async_await_batch453():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch453():
    assert _src().count("open(") == 2
