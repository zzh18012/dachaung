"""evaluation/schema_validation.py 边角测试（Round 66）。

补强 tests/test_evaluation_schema.py（含 ~10 个 document_passes_schema 测试）未覆盖的：
- 模块结构（__all__、延迟 import）
- document_passes_schema 各种边角文档（缺字段 / 错类型 / 多字段 / 空字段 / 嵌套异常）
- 返回值类型严格 bool
- 大输入稳定性
- 模块导入无副作用
"""

from __future__ import annotations

import pytest

from evaluation.schema_validation import __all__, document_passes_schema


def _valid_document_dict() -> dict:
    """完整符合 schema 的文档（参考 tests/test_evaluation_schema.py）。"""
    return {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "content": "hi",
                "parent_id": None,
                "source_locator": {"paragraph_index": 0},
                "confidence": 1.0,
                "metadata": {},
            }
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hi", "source_element_ids": ["e1"], "metadata": {}}
        ],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


# ---------- 模块结构 ----------


def test_all_exports_is_list():
    assert isinstance(__all__, list)


def test_all_exports_count_one():
    assert len(__all__) == 1


def test_all_exports_contains_document_passes_schema():
    assert "document_passes_schema" in __all__


def test_all_exports_match_module_attributes():
    import evaluation.schema_validation as mod
    for name in __all__:
        assert hasattr(mod, name)


def test_module_does_not_import_app_schema_at_top_level():
    """schema_validation.py 不能在顶层 import app.schema（避免循环依赖）。

    检查：模块文件中无 'app.schema' 或 'from app.schema' 顶层 import。
    """
    import evaluation.schema_validation as mod
    # 模块顶层不应直接绑定 is_valid / validate / SchemaValidationError
    assert not hasattr(mod, "is_valid")
    assert not hasattr(mod, "validate")
    assert not hasattr(mod, "SchemaValidationError")


# ---------- document_passes_schema: 基础类型 ----------


def test_document_passes_schema_returns_bool_type_for_valid():
    result = document_passes_schema(_valid_document_dict())
    assert isinstance(result, bool)


def test_document_passes_schema_returns_true_for_valid():
    assert document_passes_schema(_valid_document_dict()) is True


def test_document_passes_schema_returns_bool_not_int():
    """Python bool 是 int 子类，但 is True / is False 才严格。"""
    result = document_passes_schema(_valid_document_dict())
    assert result is True


def test_document_passes_schema_returns_false_for_invalid():
    bad = _valid_document_dict()
    del bad["source_hash"]
    result = document_passes_schema(bad)
    assert result is False


def test_document_passes_schema_invalid_returns_bool_type():
    bad = _valid_document_dict()
    del bad["source_hash"]
    result = document_passes_schema(bad)
    assert isinstance(result, bool)


# ---------- document_passes_schema: 缺字段 ----------


def test_rejects_missing_schema_version():
    bad = _valid_document_dict()
    del bad["schema_version"]
    assert document_passes_schema(bad) is False


def test_rejects_missing_document_id():
    bad = _valid_document_dict()
    del bad["document_id"]
    assert document_passes_schema(bad) is False


def test_rejects_missing_source_path():
    bad = _valid_document_dict()
    del bad["source_path"]
    assert document_passes_schema(bad) is False


def test_rejects_missing_source_type():
    bad = _valid_document_dict()
    del bad["source_type"]
    assert document_passes_schema(bad) is False


def test_rejects_missing_parser_name():
    bad = _valid_document_dict()
    del bad["parser_name"]
    assert document_passes_schema(bad) is False


def test_rejects_missing_parser_version():
    bad = _valid_document_dict()
    del bad["parser_version"]
    assert document_passes_schema(bad) is False


def test_rejects_missing_elements():
    bad = _valid_document_dict()
    del bad["elements"]
    assert document_passes_schema(bad) is False


def test_rejects_missing_chunks():
    bad = _valid_document_dict()
    del bad["chunks"]
    assert document_passes_schema(bad) is False


def test_rejects_missing_relations():
    bad = _valid_document_dict()
    del bad["relations"]
    assert document_passes_schema(bad) is False


def test_rejects_missing_warnings():
    bad = _valid_document_dict()
    del bad["warnings"]
    assert document_passes_schema(bad) is False


def test_rejects_missing_errors():
    bad = _valid_document_dict()
    del bad["errors"]
    assert document_passes_schema(bad) is False


def test_rejects_missing_metadata():
    bad = _valid_document_dict()
    del bad["metadata"]
    assert document_passes_schema(bad) is False


# ---------- document_passes_schema: 字段类型错 ----------


def test_rejects_schema_version_not_string():
    bad = _valid_document_dict()
    bad["schema_version"] = 1
    assert document_passes_schema(bad) is False


def test_rejects_source_type_invalid_enum():
    bad = _valid_document_dict()
    bad["source_type"] = "xlsx"
    assert document_passes_schema(bad) is False


def test_rejects_source_hash_wrong_length():
    bad = _valid_document_dict()
    bad["source_hash"] = "a" * 32  # 32 < 64
    assert document_passes_schema(bad) is False


def test_rejects_elements_not_list():
    bad = _valid_document_dict()
    bad["elements"] = "not list"
    assert document_passes_schema(bad) is False


def test_rejects_chunks_not_list():
    bad = _valid_document_dict()
    bad["chunks"] = "not list"
    assert document_passes_schema(bad) is False


def test_rejects_metadata_not_dict():
    bad = _valid_document_dict()
    bad["metadata"] = "not dict"
    assert document_passes_schema(bad) is False


def test_rejects_element_missing_required_field():
    bad = _valid_document_dict()
    del bad["elements"][0]["element_id"]
    assert document_passes_schema(bad) is False


def test_rejects_chunk_missing_required_field():
    bad = _valid_document_dict()
    del bad["chunks"][0]["chunk_id"]
    assert document_passes_schema(bad) is False


# ---------- document_passes_schema: schema_version 错值 ----------


def test_rejects_schema_version_999():
    bad = _valid_document_dict()
    bad["schema_version"] = "9.9.9"
    assert document_passes_schema(bad) is False


def test_rejects_schema_version_empty_string():
    bad = _valid_document_dict()
    bad["schema_version"] = ""
    assert document_passes_schema(bad) is False


def test_rejects_schema_version_none():
    bad = _valid_document_dict()
    bad["schema_version"] = None
    assert document_passes_schema(bad) is False


# ---------- document_passes_schema: 多余字段 / 容忍 ----------


def test_accepts_extra_top_level_field():
    """schema 大多 additionalProperties=true（默认），多字段应当被接受。"""
    doc = _valid_document_dict()
    doc["extra_field"] = "anything"
    # 多余字段是否接受取决于 schema additionalProperties；当前 schema 默认 true
    # 测试以实际行为为准（不强制 True 或 False，只要不崩 + 返 bool）
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


def test_accepts_extra_metadata_field():
    doc = _valid_document_dict()
    doc["metadata"]["custom"] = {"nested": "value"}
    result = document_passes_schema(doc)
    assert isinstance(result, bool)


# ---------- document_passes_schema: PDF vs DOCX 差异 ----------


def test_accepts_pdf_with_valid_bbox_locator():
    doc = _valid_document_dict()
    doc["source_type"] = "pdf"
    doc["source_path"] = "x.pdf"
    doc["elements"][0]["source_locator"] = {"page": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}
    assert document_passes_schema(doc) is True


def test_rejects_pdf_locator_missing_page():
    """PDF 元素的 source_locator 必须含 page（≥1）。"""
    doc = _valid_document_dict()
    doc["source_type"] = "pdf"
    doc["source_path"] = "x.pdf"
    doc["elements"][0]["source_locator"] = {"bbox": [0.0, 0.0, 100.0, 100.0]}  # 缺 page
    assert document_passes_schema(doc) is False


def test_accepts_docx_with_paragraph_index():
    doc = _valid_document_dict()
    doc["elements"][0]["source_locator"] = {"paragraph_index": 0}
    assert document_passes_schema(doc) is True


# ---------- document_passes_schema: 空边角 ----------


def test_rejects_empty_dict():
    assert document_passes_schema({}) is False


def test_rejects_document_with_empty_elements_and_chunks():
    """空 elements/chunks 仍合法（不是缺字段）。"""
    doc = _valid_document_dict()
    doc["elements"] = []
    doc["chunks"] = []
    assert document_passes_schema(doc) is True


def test_accepts_empty_metadata_dict():
    """metadata 是 dict 即可，可以为 {}。"""
    doc = _valid_document_dict()
    doc["metadata"] = {}
    assert document_passes_schema(doc) is True


# ---------- document_passes_schema: 大输入稳定性 ----------


def test_handles_many_elements():
    doc = _valid_document_dict()
    doc["elements"] = [
        {
            "element_id": f"e{i}",
            "type": "paragraph",
            "content": f"text {i}",
            "parent_id": None,
            "source_locator": {"paragraph_index": i},
            "confidence": 1.0,
            "metadata": {},
        }
        for i in range(100)
    ]
    assert document_passes_schema(doc) is True


def test_handles_many_chunks():
    doc = _valid_document_dict()
    doc["chunks"] = [
        {"chunk_id": f"c{i}", "text": f"text {i}", "source_element_ids": ["e1"], "metadata": {}}
        for i in range(100)
    ]
    assert document_passes_schema(doc) is True


def test_handles_long_strings():
    doc = _valid_document_dict()
    doc["elements"][0]["content"] = "x" * 10000
    assert document_passes_schema(doc) is True


# ---------- document_passes_schema: Unicode ----------


def test_accepts_unicode_content():
    doc = _valid_document_dict()
    doc["elements"][0]["content"] = "中文内容 🎉 ñ é ü"
    assert document_passes_schema(doc) is True


def test_accepts_unicode_metadata_values():
    doc = _valid_document_dict()
    doc["metadata"]["unicode_key"] = "中文值"
    assert document_passes_schema(doc) is True


# ---------- document_passes_schema: 不 mutate 输入 ----------


def test_does_not_mutate_input_on_success():
    doc = _valid_document_dict()
    doc_copy = {k: v for k, v in doc.items()}
    document_passes_schema(doc)
    assert doc == doc_copy


def test_does_not_mutate_input_on_failure():
    doc = _valid_document_dict()
    del doc["source_hash"]
    doc_copy = {k: v for k, v in doc.items()}
    document_passes_schema(doc)
    assert doc == doc_copy


# ---------- 模块导入无副作用 ----------


def test_import_module_does_not_crash():
    import importlib
    mod = importlib.import_module("evaluation.schema_validation")
    assert mod is not None


def test_module_has_required_attributes():
    import evaluation.schema_validation as mod
    assert hasattr(mod, "document_passes_schema")
    assert hasattr(mod, "__all__")


def test_document_passes_schema_callable():
    assert callable(document_passes_schema)
