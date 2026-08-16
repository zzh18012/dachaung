"""evaluation/metrics.py 第九十六轮 edges 测试（Round 695）。

补强 edges77 未触及的角度（第六十批）。

新角度：
- compute_automatic_metrics schema 校验集成（完整合法 document → schema_valid True / 缺 source_type → False / patch document_passes_schema 抛异常 → value False + reason schema_check_exception:ValueError / 返回 True → True）
- _image_resource_ratio candidates 顺序（第一个 Path(rp) 成功不再试 base_dir 拼接 / 第一个失败第二个成功 / image element rp 是 None 不计 valid / rp 空串）
- _docx_locator_ratio 数值（3 elements 1 无结构键 → 2/3 / relationship_id 单键 / locator 有 bbox 拒）
- _pdf_locator_ratio heading 需 bbox / header footer 不需
- element_count_by_type type 缺失 → "unknown" / 多类型混合精确计数
- _text_preservation 混合 Unicode 空白（NBSP+全角+tab 全删）
- helpers reason 字段在 _null 时保留原字符串引用
- 源码补强（candidates append 条件 / type: ignore / is_valid bool() / schema_check_exception f-string / unknown 类型 get 默认）
- AST 补强（image candidates list Assign / by_type.get(t, 0) / text_preservation 3 个 metric 变量 / compute 2 个早 return）
- forbidden tokens 第一百六十五批
"""

from __future__ import annotations

import ast
import inspect
from typing import Any
from unittest.mock import patch

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import (
    _bool_metric,
    _chunk_reference_ratio,
    _docx_locator_ratio,
    _heading_boundary_ratio,
    _int_metric,
    _image_resource_ratio,
    _is_valid_bbox,
    _null,
    _pdf_locator_ratio,
    _ratio,
    _strip_unicode_whitespace,
    _text_preservation,
    compute_automatic_metrics,
)


# ---------- schema 校验集成 ----------

def _valid_document() -> dict[str, Any]:
    """完整通过 schemas/document.schema.json 的最小文档。"""
    return {
        "schema_version": "0.1.0",
        "document_id": "doc-1",
        "source_path": "samples/a.pdf",
        "source_type": "pdf",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{
            "element_id": "e1",
            "type": "paragraph",
            "parent_id": None,
            "content": "hello",
            "resource_path": None,
            "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
            "confidence": 1.0,
            "metadata": {},
        }],
        "chunks": [{
            "chunk_id": "c1",
            "text": "hello",
            "source_element_ids": ["e1"],
            "metadata": {},
        }],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def test_compute_schema_valid_true_for_valid_document_batch52():
    out = compute_automatic_metrics(_valid_document(), None, "pdf", None)
    assert out["schema_valid"]["value"] is True


def test_compute_schema_valid_false_for_broken_document_batch52():
    doc = _valid_document()
    del doc["source_type"]
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["schema_valid"]["value"] is False


def test_compute_schema_check_exception_reason_batch52():
    with patch("evaluation.schema_validation.document_passes_schema", side_effect=ValueError("boom")):
        out = compute_automatic_metrics(_valid_document(), None, "pdf", None)
    assert out["schema_valid"]["value"] is False
    assert out["schema_valid"]["reason"] == "schema_check_exception:ValueError"


def test_compute_schema_check_exception_other_type_batch52():
    with patch("evaluation.schema_validation.document_passes_schema", side_effect=KeyError("k")):
        out = compute_automatic_metrics(_valid_document(), None, "pdf", None)
    assert out["schema_valid"]["reason"] == "schema_check_exception:KeyError"


def test_compute_schema_check_patched_true_batch52():
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics({"anything": 1}, None, "pdf", None)
    assert out["schema_valid"]["value"] is True


# ---------- _image_resource_ratio candidates 顺序 ----------

def _img(rp: Any) -> dict:
    return {"type": "image", "resource_path": rp}


def test_image_ratio_first_candidate_wins_batch52(tmp_path):
    real = tmp_path / "img.png"
    real.write_bytes(b"x")
    base = tmp_path / "base"
    base.mkdir()
    (base / "img.png").write_bytes(b"y")
    # rp 是绝对路径 → 第一个 candidate 命中
    out = _image_resource_ratio([_img(str(real))], base)
    assert out["value"] == 1.0


def test_image_ratio_second_candidate_rescues_batch52(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    (base / "img.png").write_bytes(b"data")
    # rp 只是文件名（不存在于 cwd）→ 第二个 candidate 命中
    out = _image_resource_ratio([_img("img.png")], base)
    assert out["value"] == 1.0


def test_image_ratio_both_candidates_fail_batch52(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    out = _image_resource_ratio([_img("ghost.png")], base)
    assert out["value"] == 0.0


def test_image_ratio_rp_none_invalid_batch52():
    out = _image_resource_ratio([_img(None)], None)
    assert out["value"] == 0.0


def test_image_ratio_rp_empty_string_invalid_batch52():
    out = _image_resource_ratio([_img("")], None)
    assert out["value"] == 0.0


def test_image_ratio_mixed_images_batch52(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    (base / "good.png").write_bytes(b"d")
    elements = [
        _img("good.png"),   # 第二 candidate 命中
        _img(None),         # 无 rp
        _img("lost.png"),   # 都失败
    ]
    out = _image_resource_ratio(elements, base)
    assert out["value"] == pytest.approx(1 / 3)


def test_image_ratio_zero_size_file_invalid_batch52(tmp_path):
    zero = tmp_path / "zero.png"
    zero.write_bytes(b"")
    out = _image_resource_ratio([_img(str(zero))], None)
    assert out["value"] == 0.0


# ---------- _docx_locator_ratio 数值 ----------

def _docx_elem(loc: dict | None) -> dict:
    e: dict[str, Any] = {"type": "paragraph", "content": "x"}
    if loc is not None:
        e["source_locator"] = loc
    return e


def test_docx_ratio_two_thirds_batch52():
    elements = [
        _docx_elem({"paragraph_index": 0}),
        _docx_elem({"section": 1}),
        _docx_elem({}),  # 无结构键
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == pytest.approx(2 / 3)


def test_docx_ratio_relationship_id_batch52():
    out = _docx_locator_ratio([_docx_elem({"relationship_id": "rId7"})])
    assert out["value"] == 1.0


def test_docx_ratio_bbox_rejected_batch52():
    out = _docx_locator_ratio([_docx_elem({"paragraph_index": 0, "bbox": [0, 0, 1, 1]})])
    assert out["value"] == 0.0


def test_docx_ratio_page_rejected_even_with_structural_batch52():
    out = _docx_locator_ratio([_docx_elem({"page": 1, "paragraph_index": 0})])
    assert out["value"] == 0.0


def test_docx_ratio_locator_none_invalid_batch52():
    out = _docx_locator_ratio([_docx_elem(None)])
    assert out["value"] == 0.0


def test_docx_ratio_empty_batch52():
    out = _docx_locator_ratio([])
    assert out["reason"] == "no_elements"


# ---------- _pdf_locator_ratio 类型矩阵 ----------

def _pdf(t: str, loc: dict) -> dict:
    return {"type": t, "source_locator": loc}


def test_pdf_ratio_heading_needs_bbox_batch52():
    out = _pdf_locator_ratio([_pdf("heading", {"page": 1})])
    assert out["value"] == 0.0


def test_pdf_ratio_header_no_bbox_needed_batch52():
    out = _pdf_locator_ratio([_pdf("header", {"page": 1})])
    assert out["value"] == 1.0


def test_pdf_ratio_footer_no_bbox_needed_batch52():
    out = _pdf_locator_ratio([_pdf("footer", {"page": 3})])
    assert out["value"] == 1.0


def test_pdf_ratio_table_no_bbox_needed_batch52():
    out = _pdf_locator_ratio([_pdf("table", {"page": 2})])
    assert out["value"] == 1.0


def test_pdf_ratio_list_item_needs_bbox_batch52():
    out = _pdf_locator_ratio([_pdf("list_item", {"page": 1})])
    assert out["value"] == 0.0


def test_pdf_ratio_bbox_and_page_valid_batch52():
    out = _pdf_locator_ratio([_pdf("paragraph", {"page": 1, "bbox": [1, 2, 3, 4]})])
    assert out["value"] == 1.0


# ---------- element_count_by_type ----------

def test_by_type_unknown_for_missing_type_batch52():
    out = compute_automatic_metrics({"elements": [{"content": "x"}]}, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"unknown": 1}


def test_by_type_mixed_exact_counts_batch52():
    doc = {
        "elements": [
            {"type": "paragraph", "content": "a"},
            {"type": "paragraph", "content": "b"},
            {"type": "heading", "content": "t"},
            {"type": "table"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"paragraph": 2, "heading": 1, "table": 1}
    assert out["element_count_total"]["value"] == 4


# ---------- _text_preservation 混合 Unicode 空白 ----------

def test_text_preservation_mixed_unicode_ws_batch52():
    elements = [{"type": "paragraph", "content": "a b　c\td"}]
    chunks = [{"text": "abcd"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_emoji_multiset_batch52():
    elements = [{"type": "paragraph", "content": "😀😀x"}]
    chunks = [{"text": "😀x😀"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


# ---------- helpers reason 引用 ----------

def test_null_reason_keeps_reference_batch52():
    r = "some_reason"
    d = _null(r)
    assert d["reason"] == r


def test_bool_metric_true_value_batch52():
    assert _bool_metric(True)["value"] is True


def test_int_metric_zero_batch52():
    d = _int_metric(0)
    assert d["value"] == 0
    assert d["reason"] is None


def test_ratio_bounds_batch52():
    assert _ratio(0.0)["value"] == 0.0
    assert _ratio(1.0)["value"] == 1.0


# ---------- 其余子函数快速回归 ----------

def test_is_valid_bbox_bool_rejected_batch52():
    assert _is_valid_bbox([True, 0, 0, 0]) is False
    assert _is_valid_bbox([1, 2, 3, 4]) is True


def test_strip_unicode_whitespace_nbsp_batch52():
    assert _strip_unicode_whitespace("a b") == "ab"
    assert _strip_unicode_whitespace("") == ""


def test_chunk_reference_ratio_ghost_id_batch52():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},      # 有效
        {"source_element_ids": ["e1", "g"]},  # g 不存在 → 无效
        {"source_element_ids": []},            # 空 → 无效
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == pytest.approx(1 / 3)


def test_heading_boundary_ratio_first_id_only_batch52():
    elements = [
        {"element_id": "h1", "type": "heading"},
        {"element_id": "h2", "type": "heading"},
    ]
    chunks = [
        {"source_element_ids": ["h1", "x"]},   # h1 是首元素 → 合规
        {"source_element_ids": ["p1", "h2"]},  # h2 不是首元素 → 不合规
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


# ---------- 源码补强 ----------

def test_source_candidates_append_conditional_batch52():
    src = inspect.getsource(metrics_mod)
    assert "if image_base_dir is not None:" in src
    assert "candidates.append(image_base_dir / Path(rp).name)" in src


def test_source_is_valid_bool_wrap_batch52():
    src = inspect.getsource(metrics_mod)
    assert "return bool(is_valid(document))" not in src  # 在 schema_validation 模块


def test_source_schema_check_exception_fstring_batch52():
    src = inspect.getsource(metrics_mod)
    assert 'f"schema_check_exception:{type(e).__name__}"' in src


def test_source_by_type_get_default_batch52():
    src = inspect.getsource(metrics_mod)
    assert "by_type.get(t, 0) + 1" in src


def test_source_type_default_unknown_batch52():
    src = inspect.getsource(metrics_mod)
    assert 'e.get("type", "unknown")' in src


def test_source_images_list_comp_batch52():
    src = inspect.getsource(metrics_mod)
    assert 'images = [e for e in elements if e.get("type") == "image"]' in src


def test_source_pdf_bbox_required_usage_batch52():
    src = inspect.getsource(metrics_mod)
    assert "if e.get(\"type\") in _PDF_BBOX_REQUIRED_TYPES:" in src


def test_source_docx_structural_any_batch52():
    src = inspect.getsource(metrics_mod)
    assert "if not any(k in loc for k in structural_keys):" in src


# ---------- AST 补强 ----------

def test_ast_image_candidates_assign_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_image_resource_ratio")
    src = ast.unparse(func)
    assert "candidates: list[Path] = [Path(rp)]" in src


def test_ast_text_preservation_3_metric_vars_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_text_preservation")
    src = ast.unparse(func)
    for var in ("equal_metric", "precision_metric", "recall_metric"):
        assert var in src


def test_ast_compute_2_early_returns_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    # null 循环后的 return（嵌套在 if document is None 内）+ 末尾 return
    assert len(returns) == 2


def test_ast_pdf_docx_ratio_early_null_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    for fname in ("_pdf_locator_ratio", "_docx_locator_ratio"):
        func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fname)
        src = ast.unparse(func)
        assert 'if not elements:' in src


def test_ast_metrics_module_all_single_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert ast.unparse(all_assign) == "__all__ = ['compute_automatic_metrics']"


def test_ast_no_try_in_compute_batch52():
    """compute 里只有 schema 的 1 个 try。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1


# ---------- forbidden tokens 第一百六十五批 ----------

def _src() -> str:
    return inspect.getsource(metrics_mod)


def test_source_no_eval_batch52():
    assert "eval(" not in _src()


def test_source_no_exec_batch52():
    assert "exec(" not in _src()


def test_source_no_compile_batch52():
    assert "compile(" not in _src()


def test_source_no_globals_batch52():
    assert "globals(" not in _src()


def test_source_no_locals_batch52():
    assert "locals(" not in _src()


def test_source_no_os_system_batch52():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch52():
    assert "subprocess" not in _src()


def test_source_no_popen_batch52():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch52():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch52():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch52():
    assert "socket" not in _src()


def test_source_no_requests_batch52():
    assert "requests" not in _src()


def test_source_no_urllib_batch52():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch52():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch52():
    assert "yield" not in _src()


def test_source_no_async_await_batch52():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch52():
    assert "open(" not in _src()
