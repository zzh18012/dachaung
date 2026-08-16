"""evaluation/metrics.py 第九十八轮 edges 测试（Round 709）。

补强 edges79 未触及的角度（第七十四批）。

新角度：
- schema_valid 三路径（合法全量 doc → True / 非法 doc → False / document_passes_schema 抛异常 → False + schema_check_exception:ValueError）
- source_type 交叉（docx → pdf ratio null not_pdf_document / pdf → docx null / txt → 双 null）
- pdf bbox 必备类型参数化（heading/paragraph/caption/list_item 缺 bbox → 0；header/footer/table 不需要 → 1）
- docx locator 含 page 或 bbox 直接无效（即使结构键也在）
- _image_resource_ratio 文件实存（非空文件 1.0 / 空文件 0（st_size>0）/ 一半有效 0.5 / 相对文件名+base_dir 命中 / 绝对路径不存在但 base_dir 同名命中 / rp None/空串无效 / 无 image → null）
- _text_preservation 多集合语义（"ab"/"ba" → equal False 但 P=R=1.0 / "aab"/"abb" → P=R=2/3 / 空白删除后 equal True）
- _heading_boundary_ratio 无 heading → null / 有 heading 无 chunk → 0.0
- helpers 类型转换（_ratio(1) → float 1.0 / _bool_metric("x") True / _int_metric(2.7) → 2）
- 源码补强（schema_check_exception 模板 / 延迟 import 行 / page-or-bbox 拒绝 / candidates.append / st_size / Counter 交集 / by_type 计数行）
- AST 补强（Try 2 / GeneratorExp 6 / compute 20 个下标赋值 / compute 函数级 import / _is_valid_bbox 5 Return（1 True+4 False）/ _text_preservation 2 Counter）
- forbidden tokens 第一百七十九批
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

import pytest

import evaluation.metrics as metrics_mod
import evaluation.schema_validation as sv_mod
from evaluation.metrics import (
    _bool_metric,
    _chunk_reference_ratio,
    _docx_locator_ratio,
    _heading_boundary_ratio,
    _image_resource_ratio,
    _int_metric,
    _pdf_locator_ratio,
    _ratio,
    _text_preservation,
    compute_automatic_metrics,
)


def _valid_document() -> dict[str, Any]:
    return {
        "schema_version": "0.1.0", "document_id": "doc-1",
        "source_path": "samples/a.pdf", "source_type": "pdf",
        "source_hash": "a" * 64, "parser_name": "fallback", "parser_version": "1.0",
        "elements": [{"element_id": "e1", "type": "paragraph", "parent_id": None,
                      "content": "hello", "resource_path": None,
                      "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
                      "confidence": 1.0, "metadata": {}}],
        "chunks": [{"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"],
                    "metadata": {}}],
        "relations": [], "warnings": [], "errors": [], "metadata": {},
    }


# ---------- schema_valid 三路径 ----------

def test_schema_valid_true_for_full_doc_batch53():
    out = compute_automatic_metrics(_valid_document(), None, "pdf", None)
    assert out["schema_valid"] == {"value": True, "reason": None}


def test_schema_valid_false_for_bad_hash_batch53(monkeypatch):
    monkeypatch.setattr(sv_mod, "document_passes_schema", lambda d: False)
    doc = _valid_document()
    doc["source_hash"] = "short"
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["schema_valid"]["value"] is False
    assert out["schema_valid"]["reason"] is None


def test_schema_valid_exception_reason_batch53(monkeypatch):
    def boom(doc):
        raise ValueError("nope")

    monkeypatch.setattr(sv_mod, "document_passes_schema", boom)
    out = compute_automatic_metrics(_valid_document(), None, "pdf", None)
    assert out["schema_valid"] == {
        "value": False, "reason": "schema_check_exception:ValueError",
    }


# ---------- source_type 交叉 ----------

def test_source_type_docx_pdf_ratio_null_batch53():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "no_elements"


def test_source_type_txt_both_null_batch53():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "txt", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


# ---------- pdf bbox 必备类型 ----------

@pytest.mark.parametrize("t", ["heading", "paragraph", "caption", "list_item"])
def test_pdf_bbox_required_missing_bbox_batch53(t):
    els = [{"type": t, "source_locator": {"page": 1}}]
    assert _pdf_locator_ratio(els)["value"] == 0.0


@pytest.mark.parametrize("t", ["header", "footer", "table"])
def test_pdf_non_required_no_bbox_ok_batch53(t):
    els = [{"type": t, "source_locator": {"page": 1}}]
    assert _pdf_locator_ratio(els)["value"] == 1.0


# ---------- docx locator page/bbox 拒绝 ----------

def test_docx_page_plus_structural_rejected_batch53():
    els = [{"source_locator": {"page": 1, "paragraph_index": 0}}]
    assert _docx_locator_ratio(els)["value"] == 0.0


def test_docx_bbox_plus_structural_rejected_batch53():
    els = [{"source_locator": {"bbox": [0, 0, 1, 1], "paragraph_index": 0}}]
    assert _docx_locator_ratio(els)["value"] == 0.0


# ---------- image_resource_ratio ----------

def _img(rp) -> dict:
    return {"type": "image", "resource_path": rp}


def test_image_no_image_elements_null_batch53():
    out = _image_resource_ratio([{"type": "paragraph", "content": "x"}], None)
    assert out["reason"] == "no_image_elements"


def test_image_none_and_empty_rp_invalid_batch53():
    els = [_img(None), _img("")]
    assert _image_resource_ratio(els, None)["value"] == 0.0


def test_image_real_nonempty_file_valid_batch53(tmp_path):
    f = tmp_path / "img.png"
    f.write_bytes(b"\x89PNG")
    out = _image_resource_ratio([_img(str(f))], None)
    assert out["value"] == 1.0


def test_image_empty_file_invalid_batch53(tmp_path):
    f = tmp_path / "empty.png"
    f.write_bytes(b"")
    assert _image_resource_ratio([_img(str(f))], None)["value"] == 0.0


def test_image_half_valid_batch53(tmp_path):
    good = tmp_path / "good.png"
    good.write_bytes(b"x")
    els = [_img(str(good)), _img(str(tmp_path / "missing.png"))]
    assert _image_resource_ratio(els, None)["value"] == 0.5


def test_image_relative_name_with_base_dir_batch53(tmp_path):
    f = tmp_path / "img.png"
    f.write_bytes(b"x")
    assert _image_resource_ratio([_img("img.png")], None)["value"] == 0.0
    assert _image_resource_ratio([_img("img.png")], tmp_path)["value"] == 1.0


def test_image_abs_missing_base_dir_same_name_batch53(tmp_path):
    f = tmp_path / "img.png"
    f.write_bytes(b"x")
    els = [_img("C:/no/such/dir/img.png")]
    assert _image_resource_ratio(els, tmp_path)["value"] == 1.0  # candidates[1] 命中


# ---------- chunk_reference 补充 ----------

def test_chunk_ref_half_valid_batch53():
    els = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}, {"source_element_ids": ["ghost"]}]
    assert _chunk_reference_ratio(els, chunks)["value"] == 0.5


# ---------- text_preservation 多集合语义 ----------

def test_text_reorder_equal_false_pr_one_batch53():
    out = _text_preservation(
        [{"type": "paragraph", "content": "ab"}], [{"text": "ba"}])
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_duplicate_char_multiset_batch53():
    out = _text_preservation(
        [{"type": "paragraph", "content": "aab"}], [{"text": "abb"}])
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == pytest.approx(2 / 3)
    assert out["recall"]["value"] == pytest.approx(2 / 3)


def test_text_whitespace_deleted_equal_true_batch53():
    out = _text_preservation(
        [{"type": "paragraph", "content": "a b\tc"}], [{"text": "abc"}])
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


# ---------- heading_boundary ----------

def test_heading_none_null_batch53():
    out = _heading_boundary_ratio([{"type": "paragraph"}], [{"source_element_ids": ["x"]}])
    assert out["reason"] == "no_heading_elements"


def test_heading_no_chunks_zero_batch53():
    els = [{"type": "heading", "element_id": "h1"}]
    assert _heading_boundary_ratio(els, [])["value"] == 0.0


# ---------- helpers 类型转换 ----------

def test_ratio_int_to_float_batch53():
    v = _ratio(1)
    assert v == {"value": 1.0, "reason": None}
    assert type(v["value"]) is float


def test_bool_metric_truthy_string_batch53():
    assert _bool_metric("x") == {"value": True, "reason": None}


def test_int_metric_truncates_batch53():
    assert _int_metric(2.7) == {"value": 2, "reason": None}


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(metrics_mod)


def test_source_schema_exception_template_batch53():
    assert 'f"schema_check_exception:{type(e).__name__}"' in _src()


def test_source_delayed_import_batch53():
    assert "from evaluation.schema_validation import document_passes_schema" in _src()


def test_source_docx_page_bbox_rejection_batch53():
    assert 'if "page" in loc or "bbox" in loc:' in _src()


def test_source_image_candidates_batch53():
    src = _src()
    assert "candidates.append(image_base_dir / Path(rp).name)" in src
    assert "p.stat().st_size > 0" in src


def test_source_counter_intersection_batch53():
    assert "common = sum((c_expected & c_actual).values())" in _src()


def test_source_by_type_counting_batch53():
    src = _src()
    assert 'by_type[t] = by_type.get(t, 0) + 1' in src
    assert 'e.get("type", "unknown")' in src


def test_source_chunk_first_ids_batch53():
    assert "chunk_first_ids.add(ids[0])" in _src()


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(metrics_mod))


def test_ast_try_and_genexp_counts_batch53():
    tree = _tree()
    kinds: dict[str, int] = {}
    for n in ast.walk(tree):
        kinds[type(n).__name__] = kinds.get(type(n).__name__, 0) + 1
    assert kinds["Try"] == 2  # schema_valid + image candidates
    assert kinds["GeneratorExp"] == 6
    assert kinds["IfExp"] == 1


def test_ast_compute_subscript_assigns_20_batch53():
    tree = _tree()
    func = next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics")
    subs = [n for n in ast.walk(func)
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Subscript)]
    assert len(subs) == 20


def test_ast_compute_function_level_import_batch53():
    tree = _tree()
    func = next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics")
    imps = [n.module for n in ast.walk(func) if isinstance(n, ast.ImportFrom)]
    assert imps == ["evaluation.schema_validation"]


def test_ast_bbox_five_returns_batch53():
    tree = _tree()
    func = next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "_is_valid_bbox")
    vals = [r.value.value for r in ast.walk(func)
            if isinstance(r, ast.Return) and isinstance(r.value, ast.Constant)]
    assert vals.count(False) == 4
    assert vals.count(True) == 1


def test_ast_text_preservation_two_counters_batch53():
    tree = _tree()
    func = next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == "_text_preservation")
    counters = [n for n in ast.walk(func)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "Counter"]
    assert len(counters) == 2


# ---------- forbidden tokens 第一百七十九批 ----------

def test_source_no_eval_batch53():
    assert "eval(" not in _src()


def test_source_no_exec_batch53():
    assert "exec(" not in _src()


def test_source_no_compile_batch53():
    assert "compile(" not in _src()


def test_source_no_globals_batch53():
    assert "globals(" not in _src()


def test_source_no_locals_batch53():
    assert "locals(" not in _src()


def test_source_no_os_system_batch53():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch53():
    assert "subprocess" not in _src()


def test_source_no_popen_batch53():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch53():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch53():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch53():
    assert "socket" not in _src()


def test_source_no_requests_batch53():
    assert "requests" not in _src()


def test_source_no_urllib_batch53():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch53():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch53():
    assert "yield" not in _src()


def test_source_no_async_await_batch53():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch53():
    assert "open(" not in _src()
