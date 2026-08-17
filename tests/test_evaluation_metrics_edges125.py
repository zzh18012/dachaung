"""evaluation/metrics.py 第四百七十五轮 edges 测试（Round 1031）。

补强 edges124 未触及的角度（第四百零七批，probe 实证）。

新角度（五类型异构单调用合流）：
- 一份 doc 五类型元素（heading/paragraph/table/image/
  list_item）+ 单 chunk 全引用 + 三类型混合
  expectations（paragraph 恰好、heading 超配 4、
  table 零期望超额供给）：schema_valid True（委托
  document.schema.json 通过）、pdf_locator 0.8
  （paragraph page-only 唯一失分）、silent_drop 3
  （超额供给类型贡献 0——不是 4）、ecbt 全 5 键
  dict、heading 合规 1.0（ids[0] 规则）、intact 1.0、
  image 0.0（rp 相对路径无 base_dir 全落空）
- page-only 五类型横扫：list_item/heading/paragraph
  0.0 vs image/table 1.0（bbox 豁免类含 image，
  与 R1017 七文本类型矩阵互补）
- forbidden tokens 第五百零二批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.metrics as metrics_mod
from evaluation.metrics import compute_automatic_metrics


def _e(t, eid, loc={"page": 1, "bbox": [0, 0, 1, 1]}, rp=None):
    e = {"type": t, "element_id": eid, "content": "x",
         "parent_id": None, "confidence": 0.9, "metadata": {},
         "source_locator": loc}
    if rp:
        e["resource_path"] = rp
    return e


def _doc(elements, chunks):
    return {"elements": elements, "chunks": chunks,
            "source_type": "pdf", "document_id": "x",
            "schema_version": "0.1.0", "source_path": "a.pdf",
            "source_hash": "a" * 64, "parser_name": "fallback",
            "parser_version": "1", "relations": [],
            "warnings": [], "errors": [], "metadata": {}}


_HET = _doc([
    _e("heading", "h1"),
    _e("paragraph", "p1", loc={"page": 2}),
    _e("table", "t1"),
    _e("image", "i1", rp="img.png"),
    _e("list_item", "l1")],
    [{"chunk_id": "c1", "text": "x",
      "source_element_ids": ["h1", "p1", "t1", "i1", "l1"],
      "metadata": {}}])

_EXP = {"element_count_by_type": {"paragraph": 1, "heading": 4,
                                  "table": 0}}


# ---------- 五类型异构合流 ----------

def test_heterogeneous_five_types_batch229():
    m = compute_automatic_metrics(_HET, None, "pdf", _EXP)
    assert m["schema_valid"] == {"value": True,
                                 "reason": None}
    assert m["element_count_total"] == {"value": 5,
                                        "reason": None}
    assert m["element_count_by_type"] == {
        "value": {"heading": 1, "paragraph": 1, "table": 1,
                  "image": 1, "list_item": 1}, "reason": None}


def test_heterogeneous_ratios_batch229():
    m = compute_automatic_metrics(_HET, None, "pdf", _EXP)
    assert m["pdf_locator_valid_ratio"] == {"value": 0.8,
                                            "reason": None}
    assert m["image_resource_exists_ratio"] == {
        "value": 0.0, "reason": None}
    assert m["heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}
    assert m["chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}
    assert m["text_preservation_equal"] == {"value": False,
                                            "reason": None}


def test_oversupply_type_contributes_zero_batch229():
    m = compute_automatic_metrics(_HET, None, "pdf", _EXP)
    assert m["silent_drop_count"] == {"value": 3,
                                      "reason": None}


# ---------- page-only 五类型横扫 ----------

def test_page_only_five_type_sweep_batch229():
    for t, expect in (("list_item", 0.0), ("heading", 0.0),
                      ("paragraph", 0.0), ("image", 1.0),
                      ("table", 1.0)):
        m = compute_automatic_metrics(
            _doc([_e(t, "l1", loc={"page": 3})],
                 [{"chunk_id": "c1", "text": "x",
                   "source_element_ids": ["l1"],
                   "metadata": {}}]),
            None, "pdf", None)
        assert m["pdf_locator_valid_ratio"] == {
            "value": expect, "reason": None}, t


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(metrics_mod)


def test_source_key_lines_batch229():
    src = _src()
    assert ("from evaluation.schema_validation import"
            " document_passes_schema") in src
    assert "ok = document_passes_schema(document)" in src
    assert ('_PDF_BBOX_REQUIRED_TYPES = ("heading",'
            ' "paragraph", "caption", "list_item")') in src


# ---------- forbidden tokens 第五百零二批 ----------

def test_source_no_eval_batch229():
    assert "eval(" not in _src()


def test_source_no_exec_batch229():
    assert "exec(" not in _src()


def test_source_no_compile_batch229():
    assert "compile(" not in _src()


def test_source_no_globals_batch229():
    assert "globals(" not in _src()


def test_source_no_locals_batch229():
    assert "locals(" not in _src()


def test_source_no_os_system_batch229():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch229():
    assert "subprocess" not in _src()


def test_source_no_popen_batch229():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch229():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch229():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch229():
    assert "socket" not in _src()


def test_source_no_requests_batch229():
    assert "requests" not in _src()


def test_source_no_urllib_batch229():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch229():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch229():
    assert "yield" not in _src()


def test_source_no_async_await_batch229():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch229():
    assert "open(" not in _src()
