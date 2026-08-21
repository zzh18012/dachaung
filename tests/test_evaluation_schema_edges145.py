"""evaluation/schema.py 第五百八十轮 edges 测试（Round 1299）。

补强 edges144 未触及的角度（第六百七十一批，probe 实证）。

新角度（跨元素 span 合并 / span 宽容面）：
- **mc10000 双 span 合块**——
  heading + 段落 → 1 块 550
  字恰两 span [(::e0000,
  0, 80), (::e0001, 0,
  469)]（跨元素合并的真值
  span 形首锁；edges144 仅
  mc32 单 span）
- **前缀一致**——两 span
  element_id 同 doc-<hash>
  前缀（同文档命名空间首锁）
- **mc100 span 晶格**——6 块
  span 数 [1]×6（mc100 无跨
  元素块）；块 1 span 恰
  (::e0001, 0, 93)
- **语义界**——所有 span
  end ≤ 所引元素 content 长
  （双 mc 均真；计算性不变
  量首锁）
- **宽容面**——倒序 span /
  重复 span / end=999 全
  VALID（Schema 不排序、不
  去重、不设上界；区别于
  edges142 的 pop/[] 可选面）
- forbidden tokens 第七百五十二批（open 2）
"""

from __future__ import annotations

import copy
import inspect

import evaluation.schema as schema_mod
from app.pipeline import process_single
from evaluation.schema import validate


def _wrap(s: bytes) -> bytes:
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
    xp = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += ("%010d 00000 n \n" % offsets[num]).encode()
    out += (b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n"
            + str(xp).encode() + b"\n%%EOF\n")
    return bytes(out)


LONG = " ".join("Word%d." % i for i in range(60))
HEAD = "A" * 80


def _doc(tmp_path, mc):
    s = ("BT /F1 12 Tf 10 700 Td (%s) Tj ET\n" % HEAD
         + "BT /F1 12 Tf 10 660 Td (%s) Tj ET\n"
         % LONG).encode()
    p = tmp_path / ("c%d.pdf" % mc)
    p.write_bytes(_wrap(s))
    doc, errors = process_single(p, tmp_path / "o.json",
                                 parser_name="fallback",
                                 max_chars=mc)
    assert errors == []
    return doc.to_dict()


# ---------- mc10000 双 span 合块 ----------

def test_10k_single_chunk_batch497(tmp_path):
    dd = _doc(tmp_path, 10000)
    assert len(dd["chunks"]) == 1
    assert len(dd["chunks"][0]["text"]) == 550


def test_10k_two_spans_batch497(tmp_path):
    dd = _doc(tmp_path, 10000)
    sp = dd["chunks"][0]["source_spans"]
    assert len(sp) == 2
    assert sp[0]["start"] == 0 and sp[0]["end"] == 80
    assert sp[0]["element_id"].endswith("::e0000")
    assert sp[1]["start"] == 0 and sp[1]["end"] == 469
    assert sp[1]["element_id"].endswith("::e0001")


def test_10k_span_keys_batch497(tmp_path):
    dd = _doc(tmp_path, 10000)
    for sp in dd["chunks"][0]["source_spans"]:
        assert tuple(sorted(sp)) == ("element_id", "end",
                                     "start")


def test_10k_prefix_consistent_batch497(tmp_path):
    dd = _doc(tmp_path, 10000)
    ids = [sp["element_id"]
           for sp in dd["chunks"][0]["source_spans"]]
    prefix = ids[0].rsplit("::", 1)[0]
    assert all(i.startswith(prefix) for i in ids)
    assert prefix.startswith("doc-")


# ---------- mc100 span 晶格 ----------

def test_100_span_lattice_batch497(tmp_path):
    dd = _doc(tmp_path, 100)
    counts = [len(c["source_spans"])
              for c in dd["chunks"]]
    assert counts == [1] * 6


def test_100_chunk1_span_batch497(tmp_path):
    dd = _doc(tmp_path, 100)
    sp = dd["chunks"][1]["source_spans"][0]
    assert sp["element_id"].endswith("::e0001")
    assert (sp["start"], sp["end"]) == (0, 93)


def test_100_chunk0_span_batch497(tmp_path):
    dd = _doc(tmp_path, 100)
    sp = dd["chunks"][0]["source_spans"][0]
    assert sp["element_id"].endswith("::e0000")
    assert (sp["start"], sp["end"]) == (0, 80)


# ---------- 语义界 ----------

def _within_content(dd):
    lens = {e["element_id"]: len(e["content"] or "")
            for e in dd["elements"]}
    return all(sp["end"] <= lens[sp["element_id"]]
               for c in dd["chunks"]
               for sp in c["source_spans"])


def test_spans_within_content_100_batch497(tmp_path):
    assert _within_content(_doc(tmp_path, 100))


def test_spans_within_content_10k_batch497(tmp_path):
    assert _within_content(_doc(tmp_path, 10000))


def test_base_valid_both_mc_batch497(tmp_path):
    validate(_doc(tmp_path, 100), "document.schema.json")
    validate(_doc(tmp_path, 10000),
             "document.schema.json")


# ---------- 宽容面 ----------

def test_swapped_spans_valid_batch497(tmp_path):
    dd = copy.deepcopy(_doc(tmp_path, 10000))
    dd["chunks"][0]["source_spans"] = list(
        reversed(dd["chunks"][0]["source_spans"]))
    validate(dd, "document.schema.json")


def test_duplicate_spans_valid_batch497(tmp_path):
    dd = copy.deepcopy(_doc(tmp_path, 10000))
    sp = dd["chunks"][0]["source_spans"]
    dd["chunks"][0]["source_spans"] = [sp[0]] * 2
    validate(dd, "document.schema.json")


def test_end_beyond_content_valid_batch497(tmp_path):
    dd = copy.deepcopy(_doc(tmp_path, 10000))
    dd["chunks"][0]["source_spans"][1]["end"] = 999
    validate(dd, "document.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(schema_mod)


def test_source_key_lines_batch497():
    src = _src()
    assert "class EvalSchemaError(Exception):" in src
    assert "def validate(instance" in src


# ---------- forbidden tokens 第七百五十二批 ----------

def test_source_no_eval_batch497():
    assert "eval(" not in _src()


def test_source_no_exec_batch497():
    assert "exec(" not in _src()


def test_source_no_compile_batch497():
    assert "compile(" not in _src()


def test_source_no_globals_batch497():
    assert "globals(" not in _src()


def test_source_no_locals_batch497():
    assert "locals(" not in _src()


def test_source_no_os_system_batch497():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch497():
    assert "subprocess" not in _src()


def test_source_no_popen_batch497():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch497():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch497():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch497():
    assert "socket" not in _src()


def test_source_no_requests_batch497():
    assert "requests" not in _src()


def test_source_no_urllib_batch497():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch497():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch497():
    assert "yield" not in _src()


def test_source_no_async_await_batch497():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch497():
    assert _src().count("open(") == 2
