"""evaluation/runner.py 第五百九十二轮 edges 测试（Round 1149）。

补强 edges166 未触及的角度（第五百二十二批，probe 实证）。

新角度（双表格 / 旋转页）：
- **双网格双表**——同页两个独立网格 → 2 个 table 元素
  + 2 个 isolated_table 块——表格检测各自独立（首锁）
- **跨网格格字同流**——两格内 a/b 纵向同高 → 合并单
  heading "a b"——文本合并无视网格归属（首锁）
- **旋转页照常抽取**——/Rotate 90 页上文本照出
  paragraph "Rotated page body text." page 1——旋转
  不破坏抽取（首锁）
- forbidden tokens 第六百二十一批（open 2）
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


def _two_grids_pdf() -> bytes:
    s = (b"1 w 0 G\n"
         b"10 10 40 30 re S\n30 10 0 30 re S\n"
         b"10 25 40 0 re S\n"
         b"110 10 40 30 re S\n130 10 0 30 re S\n"
         b"110 25 40 0 re S\n"
         b"BT /F1 8 Tf 12 28 Td (a) Tj ET\n"
         b"BT /F1 8 Tf 112 28 Td (b) Tj ET")
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</Font<</F1 5 0 R>>>>"
            b"/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 6)


def _rotated_pdf() -> bytes:
    s = b"BT /F1 12 Tf 10 80 Td (Rotated page body text.) Tj ET"
    return _build_pdf({
        1: b"<</Type/Catalog/Pages 2 0 R>>",
        2: b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        3: (b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Rotate 90"
            b"/Resources<</Font<</F1 5 0 R>>>>"
            b"/Contents 4 0 R>>"),
        4: (b"<</Length " + str(len(s)).encode()
            + b">>stream\n" + s + b"\nendstream "),
        5: b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    }, 6)


def _board(tmp_path, pdf_bytes, doc_id):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(pdf_bytes)
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id,
                       "path": f"samples/{doc_id}.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 双网格双表 ----------

def test_two_grids_two_tables_batch347(tmp_path):
    _board(tmp_path, _two_grids_pdf(), "tg")
    doc, errors = process_single(
        tmp_path / "samples" / "tg.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    d = doc.to_dict()
    assert [e["type"] for e in d["elements"]] == \
        ["heading", "table", "table"]
    assert [c["metadata"]["strategy"] for c in d["chunks"]] == \
        ["sequential", "isolated_table", "isolated_table"]


# ---------- 跨网格格字同流 ----------

def test_cross_grid_text_merge_batch347(tmp_path):
    _board(tmp_path, _two_grids_pdf(), "tg2")
    doc, errors = process_single(
        tmp_path / "samples" / "tg2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    els = doc.to_dict()["elements"]
    assert els[0]["content"] == "a b"


def test_two_grids_metrics_batch347(tmp_path):
    r = run_evaluation(_board(tmp_path, _two_grids_pdf(), "tg3"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "table": 2}, "reason": None}
    assert m["pipeline_success"] == {"value": True, "reason": None}


# ---------- 旋转页照常抽取 ----------

def test_rotated_page_extraction_batch347(tmp_path):
    _board(tmp_path, _rotated_pdf(), "rot")
    doc, errors = process_single(
        tmp_path / "samples" / "rot.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert len(els) == 1
    assert els[0]["type"] == "paragraph"
    assert els[0]["content"] == "Rotated page body text."
    assert els[0]["source_locator"]["page"] == 1


def test_rotated_runner_metrics_batch347(tmp_path):
    r = run_evaluation(_board(tmp_path, _rotated_pdf(), "rot2"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch347():
    src = _src()
    assert src.count("error_code") == 4
    assert src.count("annotation") == 10
    assert src.count("run_evaluation") == 2


# ---------- forbidden tokens 第六百二十一批 ----------

def test_source_no_eval_batch347():
    assert "eval(" not in _src()


def test_source_no_exec_batch347():
    assert "exec(" not in _src()


def test_source_no_compile_batch347():
    assert "compile(" not in _src()


def test_source_no_globals_batch347():
    assert "globals(" not in _src()


def test_source_no_locals_batch347():
    assert "locals(" not in _src()


def test_source_no_os_system_batch347():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch347():
    assert "subprocess" not in _src()


def test_source_no_popen_batch347():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch347():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch347():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch347():
    assert "socket" not in _src()


def test_source_no_requests_batch347():
    assert "requests" not in _src()


def test_source_no_urllib_batch347():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch347():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch347():
    assert "yield" not in _src()


def test_source_no_async_await_batch347():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch347():
    assert _src().count("open(") == 2
