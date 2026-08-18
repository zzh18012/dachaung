"""evaluation/runner.py 第五百九十一轮 edges 测试（Round 1148）。

补强 edges165 未触及的角度（第五百二十一批，probe 实证）。

新角度（表格分隔不切文本流）：
- **表格上下文本合块**——表上方句子与表下方句子跨表
  合并进同一 chunk（表格只隔离自身，不切周围文本流，
  首锁）——恰 2 chunks [sequential 双源, isolated_table]
- **近距格字并入上句**——格内 E1/F1 与上方句子纵向近
  距 → 同一 heading 'Sentence above the table. E1 F1'
  （文本-格字同流合并，首锁）
- **空行表格 markdown**——仅首行有字的网格 → 第二行
  空串单元格 '|  |  |' 收尾
- forbidden tokens 第六百二十批（open 2）
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


def _around_pdf() -> bytes:
    s = (b"1 w 0 G\n"
         b"10 30 100 40 re S\n"
         b"60 30 0 40 re S\n"
         b"10 50 100 0 re S\n"
         b"BT /F1 10 Tf 15 60 Td (E1) Tj ET\n"
         b"BT /F1 10 Tf 65 60 Td (F1) Tj ET\n"
         b"BT /F1 12 Tf 10 85 Td "
         b"(Sentence above the table.) Tj ET\n"
         b"BT /F1 12 Tf 10 10 Td "
         b"(Sentence below the table.) Tj ET")
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


def _board(tmp_path, doc_id):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(
        _around_pdf())
    mf = tmp_path / f"m{doc_id}.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id,
                       "path": f"samples/{doc_id}.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 近距格字并入上句 ----------

def test_cell_text_merges_above_batch346(tmp_path):
    _board(tmp_path, "ar")
    doc, errors = process_single(
        tmp_path / "samples" / "ar.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    els = doc.to_dict()["elements"]
    assert [e["type"] for e in els] == ["heading", "paragraph",
                                        "table"]
    assert els[0]["content"] == \
        "Sentence above the table. E1 F1"
    assert els[1]["content"] == "Sentence below the table."


# ---------- 空行表格 markdown ----------

def test_table_empty_second_row_batch346(tmp_path):
    _board(tmp_path, "ar2")
    doc, errors = process_single(
        tmp_path / "samples" / "ar2.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    tables = [e for e in doc.to_dict()["elements"]
              if e["type"] == "table"]
    assert tables[0]["content"] == \
        "| E1 | F1 |\n| --- | --- |\n|  |  |"


# ---------- 表格上下文本合块 ----------

def test_text_spans_table_batch346(tmp_path):
    _board(tmp_path, "ar3")
    doc, errors = process_single(
        tmp_path / "samples" / "ar3.pdf", tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    chunks = doc.to_dict()["chunks"]
    assert len(chunks) == 2
    assert chunks[0]["text"] == (
        "Sentence above the table. E1 F1 "
        "Sentence below the table.")
    assert len(chunks[0]["source_element_ids"]) == 2
    assert chunks[1]["metadata"]["strategy"] == "isolated_table"


def test_around_board_metrics_batch346(tmp_path):
    r = run_evaluation(_board(tmp_path, "ar4"),
                       tmp_path / "r.json", parser_name="fallback",
                       max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "paragraph": 1, "table": 1},
        "reason": None}
    assert m["text_preservation_equal"] == {"value": True,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_identifier_counts_batch346():
    src = _src()
    assert src.count("metrics") == 13
    assert src.count("manifest") == 5
    assert src.count("process_single") == 6


# ---------- forbidden tokens 第六百二十批 ----------

def test_source_no_eval_batch346():
    assert "eval(" not in _src()


def test_source_no_exec_batch346():
    assert "exec(" not in _src()


def test_source_no_compile_batch346():
    assert "compile(" not in _src()


def test_source_no_globals_batch346():
    assert "globals(" not in _src()


def test_source_no_locals_batch346():
    assert "locals(" not in _src()


def test_source_no_os_system_batch346():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch346():
    assert "subprocess" not in _src()


def test_source_no_popen_batch346():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch346():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch346():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch346():
    assert "socket" not in _src()


def test_source_no_requests_batch346():
    assert "requests" not in _src()


def test_source_no_urllib_batch346():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch346():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch346():
    assert "yield" not in _src()


def test_source_no_async_await_batch346():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch346():
    assert _src().count("open(") == 2
