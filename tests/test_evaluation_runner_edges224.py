"""evaluation/runner.py 第六百五十九轮 edges 测试（Round 1251）。

补强 edges223 未触及的角度（第六百二十三批，probe 实证）。

新角度（三文档 gap 梯度清单全像）：
- **首块 3 文档板**——all30 + all31 +
  mixed → per-doc ect 恰 [1, 3, 2]
  （行距梯度在 runner 多文档层
  首锁，前史最多 2 文档）
- **summary sum 6**——1+3+2 跨三
  文档求和 / participating 3
- **devset 三行**——file_count 3 /
  groups 3 / pdf 3 / docx 0
- **hbc 三不参评**——{None, 0, 3}
  （零参评 not_evaluated 随文档数
  增长首锁）
- **public per_doc 恰 4 键**——
  doc_id / metrics / source_type /
  wall_time_seconds（无 document 键）
- forbidden tokens 第七百一十五批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation


def _pdf3(ys) -> bytes:
    parts = []
    for y, txt in zip(ys, ["Alpha first line.", "Beta second line.",
                           "Gamma third line."]):
        parts.append("BT /F1 12 Tf 10 %d Td (%s) Tj ET" % (y, txt))
    s = ("\n".join(parts) + "\n").encode()
    objs = {
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 800]"
            b"/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: (b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objs[num] + b"endobj\n")
    xp = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


def _board(tmp_path):
    (tmp_path / "s").mkdir(exist_ok=True)
    for did, ys in (("ga", [700, 670, 640]), ("gb", [700, 669, 638]),
                    ("gc", [700, 670, 639])):
        (tmp_path / "s" / (did + ".pdf")).write_bytes(_pdf3(ys))
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": did, "path": "s/%s.pdf" % did,
             "source_type": "pdf"}
            for did in ("ga", "gb", "gc")]}), encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


def _run(tmp_path):
    return run_evaluation(_board(tmp_path), tmp_path / "r.json",
                          parser_name="fallback", max_chars=200)


# ---------- per-doc 梯度 ----------

def test_three_doc_ect_132_batch449(tmp_path):
    r = _run(tmp_path)
    assert [p["metrics"]["element_count_total"]["value"]
            for p in r["per_doc"]] == [1, 3, 2]


def test_three_doc_doc_ids_batch449(tmp_path):
    r = _run(tmp_path)
    assert [p["doc_id"] for p in r["per_doc"]] == ["ga", "gb", "gc"]


def test_three_doc_source_types_batch449(tmp_path):
    r = _run(tmp_path)
    assert [p["source_type"] for p in r["per_doc"]] == [
        "pdf", "pdf", "pdf"]


def test_per_doc_row_keys_batch449(tmp_path):
    r = _run(tmp_path)
    assert sorted(r["per_doc"][0].keys()) == [
        "doc_id", "metrics", "source_type", "wall_time_seconds"]


# ---------- summary 聚合 ----------

def test_three_doc_sum6_batch449(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["counts"]["element_count_total"] == {
        "sum": 6, "participating_docs": 3}


def test_three_doc_success_batch449(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["success_rates"]["pipeline_success"] == {
        "success_count": 3, "total": 3, "rate": 1.0}


def test_counts_keys_only_ect_batch449(tmp_path):
    r = _run(tmp_path)
    assert list(r["summary"]["counts"].keys()) == [
        "element_count_total"]


# ---------- devset 三行 ----------

def test_three_doc_devset_batch449(tmp_path):
    r = _run(tmp_path)
    assert r["devset"] == {
        "status": "incomplete", "file_count": 3,
        "content_group_count": 3, "pdf_count": 3, "docx_count": 0,
        "categories_covered": []}


# ---------- ratio 参评 ----------

def test_three_doc_hbc_not_evaluated3_batch449(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["ratio_macro_averages"][
        "heading_boundary_compliance"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 3}


def test_three_doc_pdf_locator3_batch449(tmp_path):
    r = _run(tmp_path)
    assert r["summary"]["ratio_macro_averages"][
        "pdf_locator_valid_ratio"] == {
        "macro_average": 1.0, "participating_docs": 3,
        "not_evaluated": 0}


# ---------- 杂项 ----------

def test_expected_failures_empty_batch449(tmp_path):
    r = _run(tmp_path)
    assert r["expected_failures"] == []


def test_wall_time_not_instrumented_batch449(tmp_path):
    r = _run(tmp_path)
    wt = r["per_doc"][2]["wall_time_seconds"]
    assert wt["chunk_reason"] == "not_instrumented"
    assert isinstance(wt["total"], float)
    assert wt["total"] >= 0


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch449():
    src = _src()
    assert src.count("run_evaluation") == 2
    assert src.count("chunk") == 9
    assert src.count("per_doc") == 12


# ---------- forbidden tokens 第七百一十五批 ----------

def test_source_no_eval_batch449():
    assert "eval(" not in _src()


def test_source_no_exec_batch449():
    assert "exec(" not in _src()


def test_source_no_compile_batch449():
    assert "compile(" not in _src()


def test_source_no_globals_batch449():
    assert "globals(" not in _src()


def test_source_no_locals_batch449():
    assert "locals(" not in _src()


def test_source_no_os_system_batch449():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch449():
    assert "subprocess" not in _src()


def test_source_no_popen_batch449():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch449():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch449():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch449():
    assert "socket" not in _src()


def test_source_no_requests_batch449():
    assert "requests" not in _src()


def test_source_no_urllib_batch449():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch449():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch449():
    assert "yield" not in _src()


def test_source_no_async_await_batch449():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch449():
    assert _src().count("open(") == 2
