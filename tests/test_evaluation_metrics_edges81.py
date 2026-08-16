"""evaluation/metrics.py 第九十九轮 edges 测试（Round 716）。

补强 edges80 未触及的角度（第八十一批）。

新角度：
- 合法全量 doc 端到端 14 键全值矩阵（count/by_type/pdf 1.0/docx null/image null/chunk_ref 1.0/
  equal True/P=R=1.0/heading null/silent null）
- error 与 document 并存（pipeline_success False + error_code 取 error）
- 空 elements → pdf/docx ratio null no_elements
- image-only + 非空 chunk（precision 0.0 / recall null empty_expected）
- chunk 缺 text（actual "" → precision null empty_actual / recall 0.0）
- element content None + chunk 空（equal True + 双 null empty_expected_and_actual）
- element 缺 type → by_type unknown
- chunk id 类型严格（element_id 1 vs "1" 不匹配）
- expectations None 与 {} 同为 no_expectations
- 源码补强（valid += 1 ×4 / not elements ×2 / not chunks ×1 / ids or [] ×2 / drops 行 / silent 调用行）
- AST 补强（pdf If4·Continue2·Return2 / docx If3·Continue2·Return2·GenExp1 / chunk_ref If2·Return2·GenExp1 /
  silent Return3 / heading ListComp1·GenExp1）
- forbidden tokens 第一百八十六批
"""

from __future__ import annotations

import ast
import inspect
from typing import Any

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import (
    _chunk_reference_ratio,
    _docx_locator_ratio,
    _pdf_locator_ratio,
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


# ---------- 合法全量 doc 14 键全值 ----------

def test_full_valid_doc_metric_matrix_batch53(monkeypatch):
    import evaluation.schema_validation as sv_mod
    monkeypatch.setattr(sv_mod, "document_passes_schema", lambda d: True)
    out = compute_automatic_metrics(_valid_document(), None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["error_code"]["value"] is None
    assert out["schema_valid"]["value"] is True
    assert out["element_count_total"]["value"] == 1
    assert out["element_count_by_type"]["value"] == {"paragraph": 1}
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"
    assert out["image_resource_exists_ratio"]["reason"] == "no_image_elements"
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True
    assert out["text_char_multiset_precision"]["value"] == 1.0
    assert out["text_char_multiset_recall"]["value"] == 1.0
    assert out["heading_boundary_compliance"]["reason"] == "no_heading_elements"
    assert out["silent_drop_count"]["reason"] == "no_expectations"


# ---------- error 与 document 并存 ----------

def test_error_and_document_both_present_batch53(monkeypatch):
    import evaluation.schema_validation as sv_mod
    monkeypatch.setattr(sv_mod, "document_passes_schema", lambda d: True)
    err = {"code": "weird", "message": "m"}
    out = compute_automatic_metrics(_valid_document(), err, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "weird"
    # document 仍在 → 其余指标照算
    assert out["element_count_total"]["value"] == 1


# ---------- 空 elements ----------

def test_pdf_ratio_empty_elements_null_batch53():
    assert _pdf_locator_ratio([])["reason"] == "no_elements"


def test_docx_ratio_empty_elements_null_batch53():
    assert _docx_locator_ratio([])["reason"] == "no_elements"


# ---------- 文本保留变体 ----------

def test_image_only_with_nonempty_chunk_batch53():
    from evaluation.metrics import _text_preservation
    out = _text_preservation([{"type": "image", "resource_path": "x"}],
                             [{"text": "leftover"}])
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.0
    assert out["recall"]["reason"] == "empty_expected"


def test_chunk_missing_text_batch53():
    from evaluation.metrics import _text_preservation
    out = _text_preservation([{"type": "paragraph", "content": "ab"}],
                             [{"no_text": 1}])
    assert out["equal"]["value"] is False
    assert out["precision"]["reason"] == "empty_actual"
    assert out["recall"]["value"] == 0.0


def test_element_content_none_and_empty_chunk_batch53():
    from evaluation.metrics import _text_preservation
    out = _text_preservation([{"type": "paragraph", "content": None}],
                             [{"text": ""}])
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


# ---------- by_type / chunk id 严格性 ----------

def test_by_type_missing_type_unknown_batch53():
    out = compute_automatic_metrics({"elements": [{}], "chunks": []}, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"unknown": 1}


def test_chunk_id_type_strict_batch53():
    els = [{"element_id": 1}]  # int id
    chunks = [{"source_element_ids": ["1"]}]  # str id
    assert _chunk_reference_ratio(els, chunks)["value"] == 0.0


# ---------- expectations None 与 {} ----------

def test_silent_none_and_empty_same_reason_batch53():
    doc = {"elements": [{"type": "paragraph", "content": "x"}], "chunks": []}
    a = compute_automatic_metrics(doc, None, "pdf", None)
    b = compute_automatic_metrics(doc, None, "pdf", {})
    assert a["silent_drop_count"]["reason"] == "no_expectations"
    assert b["silent_drop_count"]["reason"] == "no_expectations"


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(metrics_mod)


def test_source_valid_increment_count_batch53():
    assert _src().count("valid += 1") == 4


def test_source_empty_guards_batch53():
    src = _src()
    assert src.count("if not elements:") == 2
    assert src.count("if not chunks:") == 1


def test_source_ids_or_empty_twice_batch53():
    assert _src().count('ids = c.get("source_element_ids") or []') == 2


def test_source_drops_line_batch53():
    assert "drops += (exp - actual)" in _src()


def test_source_silent_call_line_batch53():
    assert 'metrics["silent_drop_count"] = _silent_drop_count(by_type, expectations)' in _src()


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(metrics_mod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _counts(func) -> dict:
    import collections
    return collections.Counter(type(n).__name__ for n in ast.walk(func))


def test_ast_pdf_ratio_structure_batch53():
    c = _counts(_func("_pdf_locator_ratio"))
    assert (c["If"], c["Continue"], c["Return"]) == (4, 2, 2)


def test_ast_docx_ratio_structure_batch53():
    c = _counts(_func("_docx_locator_ratio"))
    assert (c["If"], c["Continue"], c["Return"], c["GeneratorExp"]) == (3, 2, 2, 1)


def test_ast_chunk_ref_structure_batch53():
    c = _counts(_func("_chunk_reference_ratio"))
    assert (c["If"], c["Return"], c["GeneratorExp"]) == (2, 2, 1)


def test_ast_silent_three_returns_batch53():
    assert _counts(_func("_silent_drop_count"))["Return"] == 3


def test_ast_heading_comprehensions_batch53():
    c = _counts(_func("_heading_boundary_ratio"))
    assert (c["ListComp"], c["GeneratorExp"]) == (1, 1)


# ---------- forbidden tokens 第一百八十六批 ----------

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
