"""evaluation/runner.py 第五百七十三轮 edges 测试（Round 1129）。

补强 edges147 未触及的角度（第五百零五批，probe 实证）。

新角度（空白页跳过保号 / 三页归属 / 小上限崩）：
- **空白首页跳过保号**——第 1 页无文字、2/3 页有 → 元素
  pages 恰 [2, 3]——空白页不产元素但页码不重排（首锁）
- **三页归属**——三页各一句 → 3 个 paragraph、pages
  [1, 2, 3]、max_chars 200 合 1 chunk
- **三页小上限崩**——同一板 max_chars 12 → chunker_failed
  （两页板 33 可劈，三页小板 12 全灭——chunker 对短页
  拼流无白界可劈，probe 实证 5/8/10/12 全崩）
- **空白首板指标全胜**——runner 真跑：success True + ect 2
  + pdf_locator 1.0（真 page 2/3 过 page≥1 校验）
- forbidden tokens 第六百零二批（open 2）
"""

from __future__ import annotations

import inspect
import json

import evaluation.runner as runner_mod
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation
from app.pipeline import process_single


def _build_pdf(texts) -> bytes:
    n_pages = len(texts)
    font_no = 3 + 2 * n_pages
    objects = {}
    kids = b" ".join(str(3 + 2 * i).encode() + b" 0 R"
                     for i in range(n_pages))
    objects[1] = b"<</Type/Catalog/Pages 2 0 R>>"
    objects[2] = (b"<</Type/Pages/Kids[" + kids + b"]/Count "
                  + str(n_pages).encode() + b">>")
    for i, t in enumerate(texts):
        page_no = 3 + 2 * i
        cont_no = page_no + 1
        objects[page_no] = (
            b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
            b"/Resources<</Font<</F1 " + str(font_no).encode()
            + b" 0 R>>>>/Contents "
            + str(cont_no).encode() + b" 0 R>>")
        s = b"BT /F1 12 Tf 10 80 Td (" + t + b") Tj ET"
        objects[cont_no] = (
            b"<</Length " + str(len(s)).encode() + b">>stream\n"
            + s + b"\nendstream ")
    objects[font_no] = (
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += (str(num).encode() + b" 0 obj"
                + objects[num] + b"endobj\n")
    xref_pos = len(out)
    max_obj = max(objects)
    out += b"xref\n0 " + str(max_obj + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for num in range(1, max_obj + 1):
        if num in offsets:
            out += ("%010d 00000 n \n" % offsets[num]).encode()
        else:
            out += b"0000000000 65535 f \n"
    out += (b"trailer<</Size " + str(max_obj + 1).encode()
            + b"/Root 1 0 R>>\nstartxref\n" + str(xref_pos).encode()
            + b"\n%%EOF\n")
    return bytes(out)


def _write_board(tmp_path, texts, doc_id):
    (tmp_path / "samples").mkdir(exist_ok=True)
    (tmp_path / "samples" / f"{doc_id}.pdf").write_bytes(
        _build_pdf(texts))
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{"doc_id": doc_id,
                       "path": f"samples/{doc_id}.pdf",
                       "source_type": "pdf"}]}),
        encoding="utf-8")
    return load_manifest(mf, project_root=tmp_path)


# ---------- 空白首页跳过保号 ----------

def test_blank_first_page_skipped_batch328(tmp_path):
    man = _write_board(tmp_path,
                       [b"", b"Page two body.", b"Page three body."],
                       "bf")
    doc, errors = process_single(
        man.documents[0].resolved_path, tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    d = doc.to_dict()
    pages = [e["source_locator"]["page"] for e in d["elements"]]
    assert pages == [2, 3]


# ---------- 三页归属 ----------

def test_three_pages_attribution_batch328(tmp_path):
    man = _write_board(tmp_path, [b"One.", b"Two.", b"Three."],
                       "tp")
    doc, errors = process_single(
        man.documents[0].resolved_path, tmp_path / "o.json",
        parser_name="fallback", max_chars=200)
    assert errors == []
    d = doc.to_dict()
    els = d["elements"]
    assert len(els) == 3
    assert [e["source_locator"]["page"] for e in els] == [1, 2, 3]
    assert len(d["chunks"]) == 1


# ---------- 三页小上限崩 ----------

def test_three_page_small_max_chars_fails_batch328(tmp_path):
    man = _write_board(tmp_path, [b"One.", b"Two.", b"Three."],
                       "tp2")
    r = run_evaluation(man, tmp_path / "r.json",
                       parser_name="fallback", max_chars=12)
    m = r["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": False, "reason": None}
    assert m["error_code"] == {"value": "chunker_failed",
                               "reason": None}


# ---------- 空白首板指标全胜 ----------

def test_blank_first_metrics_batch328(tmp_path):
    man = _write_board(tmp_path,
                       [b"", b"Page two body.", b"Page three body."],
                       "bf2")
    r = run_evaluation(man, tmp_path / "r.json",
                       parser_name="fallback", max_chars=200)
    m = r["per_doc"][0]["metrics"]
    assert m["pipeline_success"] == {"value": True, "reason": None}
    assert m["element_count_total"] == {"value": 2, "reason": None}
    assert m["pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(runner_mod)


def test_source_def_count_batch328():
    src = _src()
    assert src.count("def ") == 3
    for name in ("_load_annotation", "_process_one",
                 "run_evaluation"):
        assert f"def {name}(" in src


# ---------- forbidden tokens 第六百零二批 ----------

def test_source_no_eval_batch328():
    assert "eval(" not in _src()


def test_source_no_exec_batch328():
    assert "exec(" not in _src()


def test_source_no_compile_batch328():
    assert "compile(" not in _src()


def test_source_no_globals_batch328():
    assert "globals(" not in _src()


def test_source_no_locals_batch328():
    assert "locals(" not in _src()


def test_source_no_os_system_batch328():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch328():
    assert "subprocess" not in _src()


def test_source_no_popen_batch328():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch328():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch328():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch328():
    assert "socket" not in _src()


def test_source_no_requests_batch328():
    assert "requests" not in _src()


def test_source_no_urllib_batch328():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch328():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch328():
    assert "yield" not in _src()


def test_source_no_async_await_batch328():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch328():
    assert _src().count("open(") == 2
