"""metrics.py 的测试：自动指标 13 项 + 各种 null 路径。"""

from __future__ import annotations

from pathlib import Path

import pytest

from evaluation.metrics import compute_automatic_metrics


# ---------- helpers ----------


def _docx_document(elements: list[dict], chunks: list[dict]) -> dict:
    return {
        "schema_version": "0.1.0",
        "document_id": "doc-test",
        "source_path": "samples/private/test.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "test=1.0",
        "elements": elements,
        "chunks": chunks,
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def _pdf_document(elements: list[dict], chunks: list[dict]) -> dict:
    d = _docx_document(elements=elements, chunks=chunks)
    d["source_type"] = "pdf"
    d["source_path"] = "samples/private/test.pdf"
    return d


def _heading(eid: str, text: str, *, paragraph_index: int = 0) -> dict:
    return {
        "element_id": eid,
        "type": "heading",
        "content": text,
        "resource_path": None,
        "parent_id": None,
        "source_locator": {"paragraph_index": paragraph_index, "section": 0},
        "confidence": 0.95,
        "metadata": {"level": 1, "style": "Heading 1", "empty": False},
    }


def _paragraph(eid: str, text: str, *, paragraph_index: int = 0) -> dict:
    return {
        "element_id": eid,
        "type": "paragraph",
        "content": text,
        "resource_path": None,
        "parent_id": None,
        "source_locator": {"paragraph_index": paragraph_index, "section": 0},
        "confidence": 0.95,
        "metadata": {"level": 0, "style": "Normal", "empty": False},
    }


def _pdf_text_elem(eid: str, etype: str, text: str, *, page: int = 1, bbox: list | None = None) -> dict:
    loc: dict = {"page": page}
    if bbox is not None:
        loc["bbox"] = bbox
    return {
        "element_id": eid,
        "type": etype,
        "content": text,
        "resource_path": None,
        "parent_id": None,
        "source_locator": loc,
        "confidence": 0.9,
        "metadata": {},
    }


def _table(eid: str, md: str, *, table_index: int = 0) -> dict:
    return {
        "element_id": eid,
        "type": "table",
        "content": md,
        "resource_path": None,
        "parent_id": None,
        "source_locator": {"table_index": table_index, "section": 0},
        "confidence": 0.85,
        "metadata": {"row_count": 2, "col_count": 2},
    }


def _image(eid: str, resource_path: str | None, *, relationship_id: str = "rId1") -> dict:
    return {
        "element_id": eid,
        "type": "image",
        "content": None,
        "resource_path": resource_path,
        "parent_id": None,
        "source_locator": {"relationship_id": relationship_id, "paragraph_index": 0},
        "confidence": 0.6,
        "metadata": {},
    }


def _chunk(cid: str, text: str, src_ids: list[str]) -> dict:
    return {
        "chunk_id": cid,
        "text": text,
        "source_element_ids": src_ids,
        "metadata": {"strategy": "sequential", "max_chars": 800, "char_count": len(text)},
    }


# ---------- pipeline_failed path ----------


def test_pipeline_failed_yields_null_metrics():
    m = compute_automatic_metrics(
        document=None,
        error={"code": "no_extracted_elements", "message": "x"},
        source_type="pdf",
        expectations=None,
    )
    assert m["pipeline_success"]["value"] is False
    assert m["error_code"]["value"] == "no_extracted_elements"
    assert m["schema_valid"]["reason"] == "pipeline_failed"
    assert m["element_count_total"]["reason"] == "pipeline_failed"
    assert m["pdf_locator_valid_ratio"]["reason"] == "pipeline_failed"
    assert m["text_preservation_equal"]["reason"] == "pipeline_failed"


# ---------- basic DOCX ----------


def test_docx_basic_counts_and_ratios():
    elements = [
        _heading("e0", "Chapter 1", paragraph_index=0),
        _paragraph("e1", "Hello world.", paragraph_index=1),
        _table("e2", "| a | b |\n| --- | --- |\n| 1 | 2 |", table_index=0),
        _image("e3", "(unsaved)", relationship_id="rId1"),
    ]
    chunks = [
        _chunk("c0", "Chapter 1 Hello world.", ["e0", "e1"]),
        _chunk("c1", "| a | b |", ["e2"]),
    ]
    doc = _docx_document(elements=elements, chunks=chunks)
    m = compute_automatic_metrics(
        document=doc, error=None, source_type="docx", expectations=None
    )
    assert m["pipeline_success"]["value"] is True
    assert m["error_code"]["value"] is None
    assert m["schema_valid"]["value"] is True
    assert m["element_count_total"]["value"] == 4
    assert m["element_count_by_type"]["value"] == {
        "heading": 1, "paragraph": 1, "table": 1, "image": 1
    }
    # DOCX locator：4 个元素都合规
    assert m["docx_locator_valid_ratio"]["value"] == 1.0
    # PDF locator 不适用
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_docx_no_image_returns_null_image_ratio():
    elements = [_heading("e0", "x"), _paragraph("e1", "y")]
    chunks = [_chunk("c0", "x y", ["e0", "e1"])]
    doc = _docx_document(elements=elements, chunks=chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["image_resource_exists_ratio"]["reason"] == "no_image_elements"


def test_docx_no_chunks_returns_null_chunk_ratio():
    elements = [_heading("e0", "x")]
    doc = _docx_document(elements=elements, chunks=[])
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["chunk_reference_intact_ratio"]["reason"] == "no_chunks"


# ---------- PDF locator ----------


def test_pdf_locator_all_valid_with_bbox():
    elements = [
        _pdf_text_elem("e0", "heading", "H", bbox=[0, 0, 100, 20]),
        _pdf_text_elem("e1", "paragraph", "P", bbox=[0, 30, 100, 50]),
    ]
    chunks = [_chunk("c0", "H P", ["e0", "e1"])]
    doc = _pdf_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pdf_locator_valid_ratio"]["value"] == 1.0
    assert m["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_pdf_locator_invalid_page():
    elements = [
        _pdf_text_elem("e0", "heading", "H", page=0, bbox=[0, 0, 1, 1]),  # page<1
        _pdf_text_elem("e1", "paragraph", "P", page=1, bbox=[0, 0, 1, 1]),
    ]
    chunks = [_chunk("c0", "H P", ["e0", "e1"])]
    doc = _pdf_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pdf_locator_valid_ratio"]["value"] == 0.5


def test_pdf_locator_missing_bbox_for_text_type():
    elements = [
        _pdf_text_elem("e0", "heading", "H", page=1, bbox=None),  # 缺 bbox
        _pdf_text_elem("e1", "paragraph", "P", page=1, bbox=[0, 0, 1, 1]),
    ]
    chunks = [_chunk("c0", "H P", ["e0", "e1"])]
    doc = _pdf_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pdf_locator_valid_ratio"]["value"] == 0.5


def test_pdf_locator_bad_bbox_length():
    elements = [
        _pdf_text_elem("e0", "heading", "H", page=1, bbox=[0, 0, 1]),  # 3 元素
        _pdf_text_elem("e1", "paragraph", "P", page=1, bbox=[0, 0, 1, 1]),
    ]
    chunks = [_chunk("c0", "H P", ["e0", "e1"])]
    doc = _pdf_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pdf_locator_valid_ratio"]["value"] == 0.5


# ---------- image resource ----------


def test_image_resource_exists(tmp_path: Path):
    # 创建两个真实图片文件，一个引用、一个不存在
    real_file = tmp_path / "img1.png"
    real_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    elements = [
        _image("e0", str(real_file)),  # 绝对路径，存在
        _image("e1", "missing.png"),  # 相对路径，不存在
    ]
    chunks = []
    doc = _docx_document(elements=elements, chunks=chunks)
    m = compute_automatic_metrics(doc, None, "docx", None, image_base_dir=tmp_path)
    # 1/2 = 0.5
    assert m["image_resource_exists_ratio"]["value"] == 0.5


def test_image_resource_empty_file(tmp_path: Path):
    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    elements = [_image("e0", str(empty))]
    doc = _docx_document(elements=elements, chunks=[])
    m = compute_automatic_metrics(doc, None, "docx", None, image_base_dir=tmp_path)
    assert m["image_resource_exists_ratio"]["value"] == 0.0


# ---------- chunk reference ----------


def test_chunk_reference_intact():
    elements = [_heading("e0", "x"), _paragraph("e1", "y")]
    chunks = [
        _chunk("c0", "x y", ["e0", "e1"]),  # 完整
        _chunk("c1", "z", ["eZZZ"]),  # 引用不存在的 element
    ]
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["chunk_reference_intact_ratio"]["value"] == 0.5


# ---------- text preservation ----------


def test_text_preservation_equal_match():
    elements = [_heading("e0", "Hello"), _paragraph("e1", "world.")]
    chunks = [_chunk("c0", "Hello world.", ["e0", "e1"])]
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["text_preservation_equal"]["value"] is True
    assert m["text_char_multiset_precision"]["value"] == 1.0
    assert m["text_char_multiset_recall"]["value"] == 1.0


def test_text_preservation_missing_text():
    """chunk 漏掉了部分文本 → equal=False, recall<1, precision=1。"""
    elements = [_paragraph("e0", "alpha beta gamma")]
    chunks = [_chunk("c0", "alpha beta", ["e0"])]  # 漏了 gamma
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["text_preservation_equal"]["value"] is False
    # precision: 所有 actual 都在 expected 中 → 1.0
    assert m["text_char_multiset_precision"]["value"] == 1.0
    # recall: actual 是 expected 的子集 → < 1
    assert m["text_char_multiset_recall"]["value"] < 1.0


def test_text_preservation_duplicate_text():
    """chunk 重复了文本 → equal=False, precision<1, recall=1。"""
    elements = [_paragraph("e0", "alpha")]
    chunks = [_chunk("c0", "alpha alpha", ["e0"])]  # 重复了
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["text_preservation_equal"]["value"] is False
    assert m["text_char_multiset_precision"]["value"] < 1.0
    assert m["text_char_multiset_recall"]["value"] == 1.0


def test_text_preservation_excludes_image():
    elements = [
        _heading("e0", "H"),
        _image("e1", None),  # 图片不参与文本比对
    ]
    chunks = [_chunk("c0", "H", ["e0"])]
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["text_preservation_equal"]["value"] is True


# ---------- text preservation v1.1（口径 D：非空白字符序列）----------


def test_text_preservation_whitespace_only_diff_equal():
    """v1.1：仅空白差异（空格 vs 制表符 vs 换行 vs 全去掉）必须 equal=True。"""
    elements = [_paragraph("e0", "hello world")]
    chunks = [_chunk("c0", "hello\tworld", ["e0"])]
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["text_preservation_equal"]["value"] is True
    assert m["text_char_multiset_precision"]["value"] == 1.0
    assert m["text_char_multiset_recall"]["value"] == 1.0


def test_text_preservation_newline_only_diff_equal():
    """v1.1：换行 vs 空格 vs 无空白必须视为相等。"""
    elements = [_paragraph("e0", "alpha\rbeta\ngamma")]
    chunks = [_chunk("c0", "alphabetagamma", ["e0"])]
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["text_preservation_equal"]["value"] is True


def test_text_preservation_unicode_whitespace_equal():
    """v1.1：Unicode 空白（NBSP U+00A0、表意空格 U+3000）也算空白。"""
    elements = [_paragraph("e0", "a b　c")]
    chunks = [_chunk("c0", "abc", ["e0"])]
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["text_preservation_equal"]["value"] is True


def test_text_preservation_missing_non_whitespace_char_not_equal():
    """v1.1：缺失任意非空白字符必须 equal=False 且 recall<1。"""
    elements = [_paragraph("e0", "hello world")]
    chunks = [_chunk("c0", "hello orld", ["e0"])]  # 漏了 'w'
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["text_preservation_equal"]["value"] is False
    assert m["text_char_multiset_precision"]["value"] == 1.0
    assert m["text_char_multiset_recall"]["value"] < 1.0


def test_text_preservation_duplicate_non_whitespace_char_not_equal():
    """v1.1：重复任意非空白字符必须 equal=False 且 precision<1。"""
    elements = [_paragraph("e0", "abc")]
    chunks = [_chunk("c0", "abcabc", ["e0"])]  # 整段重复
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["text_preservation_equal"]["value"] is False
    assert m["text_char_multiset_precision"]["value"] < 1.0
    assert m["text_char_multiset_recall"]["value"] == 1.0


def test_text_preservation_reorder_non_whitespace_not_equal():
    """v1.1：非空白字符顺序改变必须 equal=False（多集合可能不变）。"""
    elements = [_paragraph("e0", "abc def")]
    chunks = [_chunk("c0", "def abc", ["e0"])]  # 重排
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    # 顺序变了 → equal=False
    assert m["text_preservation_equal"]["value"] is False
    # 但多集合相同 → precision=recall=1.0
    assert m["text_char_multiset_precision"]["value"] == 1.0
    assert m["text_char_multiset_recall"]["value"] == 1.0


def test_text_preservation_mid_token_extra_space_equal():
    """v1.1：chunker 词内硬切引入的额外空格不再误报（长元素按 max_chars 切片落在词中间）。"""
    # element "Havelock" 被 chunker 硬切成 "Have" + "lock"
    # 旧 v1.0：' '.join → "Have lock" 与 "Havelock" 不等，误报
    # 新 v1.1：删空白后两序列都是 "Havelock"，等
    elements = [_paragraph("e0", "Havelock")]
    chunks = [
        _chunk("c0", "Have", ["e0"]),
        _chunk("c1", "lock", ["e0"]),
    ]
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["text_preservation_equal"]["value"] is True
    assert m["text_char_multiset_precision"]["value"] == 1.0
    assert m["text_char_multiset_recall"]["value"] == 1.0


# ---------- heading boundary ----------


def test_heading_boundary_compliance_all_at_chunk_start():
    elements = [
        _heading("e0", "H1"),
        _paragraph("e1", "p1"),
        _heading("e2", "H2"),
        _paragraph("e3", "p2"),
    ]
    chunks = [
        _chunk("c0", "H1 p1", ["e0", "e1"]),  # e0 是首
        _chunk("c1", "H2 p2", ["e2", "e3"]),  # e2 是首
    ]
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["heading_boundary_compliance"]["value"] == 1.0


def test_heading_boundary_compliance_partial():
    elements = [
        _heading("e0", "H1"),
        _heading("e2", "H2"),
        _paragraph("e1", "p1"),  # 故意让 e2 不在 c0 首
    ]
    chunks = [
        _chunk("c0", "H1 H2", ["e0", "e2"]),  # 只有 e0 在首
        _chunk("c1", "p1", ["e1"]),
    ]
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["heading_boundary_compliance"]["value"] == 0.5


def test_heading_boundary_no_headings_returns_null():
    elements = [_paragraph("e0", "p")]
    chunks = [_chunk("c0", "p", ["e0"])]
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["heading_boundary_compliance"]["reason"] == "no_heading_elements"


# ---------- silent drop ----------


def test_silent_drop_no_expectations():
    elements = [_paragraph("e0", "p")]
    chunks = [_chunk("c0", "p", ["e0"])]
    doc = _docx_document(elements, chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["silent_drop_count"]["reason"] == "no_expectations"


def test_silent_drop_with_expectations_no_drop():
    elements = [
        _heading("e0", "h"),
        _table("e1", "md"),
    ]
    doc = _docx_document(elements, [])
    expectations = {"element_count_by_type": {"heading": 1, "table": 1}}
    m = compute_automatic_metrics(doc, None, "docx", expectations)
    assert m["silent_drop_count"]["value"] == 0


def test_silent_drop_missing_one_table():
    elements = [_heading("e0", "h")]  # 缺 table
    doc = _docx_document(elements, [])
    expectations = {"element_count_by_type": {"heading": 1, "table": 1}}
    m = compute_automatic_metrics(doc, None, "docx", expectations)
    assert m["silent_drop_count"]["value"] == 1


def test_silent_drop_extra_actual_not_counted():
    """实际比期望多不算 drop（这是 surplus，不是 silent drop）。"""
    elements = [_heading("e0", "h"), _table("e1", "m1"), _table("e2", "m2")]
    doc = _docx_document(elements, [])
    expectations = {"element_count_by_type": {"heading": 1, "table": 1}}
    m = compute_automatic_metrics(doc, None, "docx", expectations)
    assert m["silent_drop_count"]["value"] == 0


# ---------- 边角与缺漏补强（Round 22） ----------


# 直接测试内部 helper


def test_is_valid_bbox_rejects_non_list():
    from evaluation.metrics import _is_valid_bbox
    assert _is_valid_bbox(None) is False
    assert _is_valid_bbox("0,0,1,1") is False
    assert _is_valid_bbox((0, 0, 1, 1)) is False  # tuple 不接受


def test_is_valid_bbox_rejects_wrong_length():
    from evaluation.metrics import _is_valid_bbox
    assert _is_valid_bbox([]) is False
    assert _is_valid_bbox([0, 0, 1]) is False
    assert _is_valid_bbox([0, 0, 1, 1, 1]) is False


def test_is_valid_bbox_rejects_bool_even_though_int():
    """bool 是 int 的子类，但 bbox 不应接受 True/False。"""
    from evaluation.metrics import _is_valid_bbox
    assert _is_valid_bbox([0, 0, 1, True]) is False
    assert _is_valid_bbox([False, 0, 0, 1]) is False


def test_is_valid_bbox_rejects_nan_and_inf():
    """NaN / Infinity 不是有限数。"""
    from evaluation.metrics import _is_valid_bbox
    assert _is_valid_bbox([0, 0, 1, float("nan")]) is False
    assert _is_valid_bbox([0, 0, 1, float("inf")]) is False
    assert _is_valid_bbox([0, 0, float("-inf"), 1]) is False


def test_is_valid_bbox_accepts_int_and_float():
    from evaluation.metrics import _is_valid_bbox
    assert _is_valid_bbox([0, 0, 100, 200]) is True
    assert _is_valid_bbox([0.5, 1.5, 10.0, 20.0]) is True


def test_strip_unicode_whitespace_removes_all_kinds():
    """NBSP、em space、en space、ideographic space、line/paragraph separator 都应被删除。"""
    from evaluation.metrics import _strip_unicode_whitespace
    # ASCII space + NBSP(U+00A0) + en space(U+2002) + em space(U+2003) + ideographic(U+3000)
    s = "a b c d e　f"
    assert _strip_unicode_whitespace(s) == "abcdef"
    # line separator U+2028, paragraph separator U+2029
    assert _strip_unicode_whitespace("x y z") == "xyz"
    # ASCII tabs/newlines
    assert _strip_unicode_whitespace("\t\r\n h i \n") == "hi"


# 各种 null/边界路径


def test_pdf_locator_no_elements_returns_null():
    """没有 elements 时返回 no_elements。"""
    doc = _pdf_document(elements=[], chunks=[])
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pdf_locator_valid_ratio"]["reason"] == "no_elements"


def test_docx_locator_no_elements_returns_null():
    doc = _docx_document(elements=[], chunks=[])
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["docx_locator_valid_ratio"]["reason"] == "no_elements"


def test_docx_locator_rejects_page_or_bbox_keys():
    """DOCX locator 含 page 或 bbox → 不合规。"""
    elements = [
        # 合规：paragraph_index
        _paragraph("e0", "x", paragraph_index=0),
        # 不合规：含 page
        {
            "element_id": "e1", "type": "paragraph", "content": "y",
            "resource_path": None, "parent_id": None, "confidence": 1.0,
            "source_locator": {"paragraph_index": 1, "page": 1},
            "metadata": {},
        },
        # 不合规：含 bbox
        {
            "element_id": "e2", "type": "paragraph", "content": "z",
            "resource_path": None, "parent_id": None, "confidence": 1.0,
            "source_locator": {"paragraph_index": 2, "bbox": [0, 0, 1, 1]},
            "metadata": {},
        },
    ]
    doc = _docx_document(elements=elements, chunks=[])
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["docx_locator_valid_ratio"]["value"] == 1 / 3


def test_docx_locator_without_structural_keys_invalid():
    """locator 没有任何 structural key → 不合规。"""
    elements = [
        # 合规
        _paragraph("e0", "x", paragraph_index=0),
        # locator 是空 dict → 不合规
        {
            "element_id": "e1", "type": "paragraph", "content": "y",
            "resource_path": None, "parent_id": None, "confidence": 1.0,
            "source_locator": {},
            "metadata": {},
        },
    ]
    doc = _docx_document(elements=elements, chunks=[])
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["docx_locator_valid_ratio"]["value"] == 0.5


def test_pdf_locator_table_type_does_not_require_bbox():
    """table 不在 _PDF_BBOX_REQUIRED_TYPES 中，page≥1 即合规。"""
    elements = [
        # table 有 page 但没 bbox → 仍合规
        {
            "element_id": "e0", "type": "table", "content": "x",
            "resource_path": None, "parent_id": None, "confidence": 1.0,
            "source_locator": {"page": 1},  # 无 bbox
            "metadata": {},
        },
        # heading 缺 bbox → 不合规
        _pdf_text_elem("e1", "heading", "h", page=1, bbox=None),
    ]
    chunks = []
    doc = _pdf_document(elements=elements, chunks=chunks)
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pdf_locator_valid_ratio"]["value"] == 0.5


def test_image_resource_with_none_path_counts_as_invalid():
    """resource_path=None 的 image 不应被认为存在。"""
    elements = [
        _image("e0", None),  # None
        _image("e1", None),  # None
    ]
    doc = _docx_document(elements=elements, chunks=[])
    m = compute_automatic_metrics(doc, None, "docx", None)
    # 2 个 image，0 个有效 → 0.0
    assert m["image_resource_exists_ratio"]["value"] == 0.0


def test_image_resource_with_empty_string_path_invalid():
    """resource_path='' 的 image 不应被认为存在。"""
    elements = [_image("e0", "")]
    doc = _docx_document(elements=elements, chunks=[])
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["image_resource_exists_ratio"]["value"] == 0.0


def test_chunk_reference_empty_source_ids_not_valid():
    """chunk 的 source_element_ids 为空列表 → 该 chunk 不合规。"""
    elements = [_heading("e0", "h")]
    chunks = [
        _chunk("c0", "h", ["e0"]),  # 合规
        _chunk("c1", "", []),  # 空 → 不合规
    ]
    doc = _docx_document(elements=elements, chunks=chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["chunk_reference_intact_ratio"]["value"] == 0.5


def test_chunk_reference_none_source_ids_not_valid():
    """chunk 的 source_element_ids 缺失 → 不合规。"""
    elements = [_heading("e0", "h")]
    chunks = [
        {"chunk_id": "c0", "text": "h", "metadata": {}},  # 没 source_element_ids
    ]
    doc = _docx_document(elements=elements, chunks=chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["chunk_reference_intact_ratio"]["value"] == 0.0


def test_text_preservation_both_empty_returns_null():
    """elements 与 chunks 都没文本 → null + empty_expected_and_actual。"""
    elements = [_image("e0", None)]  # 图片不参与文本
    chunks = []
    doc = _docx_document(elements=elements, chunks=chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["text_preservation_equal"]["value"] is True
    assert m["text_char_multiset_precision"]["reason"] == "empty_expected_and_actual"
    assert m["text_char_multiset_recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_empty_actual_non_empty_expected():
    """expected 非空，actual 空 → precision null(empty_actual)，recall=0.0。"""
    elements = [_paragraph("e0", "hello")]
    chunks = []  # actual 是空
    doc = _docx_document(elements=elements, chunks=chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["text_preservation_equal"]["value"] is False
    assert m["text_char_multiset_precision"]["reason"] == "empty_actual"
    # recall: |expected| > 0, common=0 → 0.0
    assert m["text_char_multiset_recall"]["value"] == 0.0


def test_text_preservation_empty_expected_non_empty_actual():
    """expected 空，actual 非空 → precision=0.0, recall null(empty_expected)。"""
    elements = [_image("e0", None)]  # 没文本
    chunks = [_chunk("c0", "stray", ["e0"])]  # 但 chunk 有文本
    doc = _docx_document(elements=elements, chunks=chunks)
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["text_preservation_equal"]["value"] is False
    assert m["text_char_multiset_precision"]["value"] == 0.0
    assert m["text_char_multiset_recall"]["reason"] == "empty_expected"


def test_heading_boundary_ratio_with_no_chunks_returns_zero():
    """headings 存在但 chunks 为空 → matched=0 → 0.0（不是 null）。"""
    elements = [_heading("e0", "h")]
    doc = _docx_document(elements=elements, chunks=[])
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["heading_boundary_compliance"]["value"] == 0.0
    assert m["heading_boundary_compliance"]["reason"] is None


def test_silent_drop_with_empty_expectations_dict():
    """expectations={}（空 dict）→ no_expectations。"""
    elements = [_heading("e0", "h")]
    doc = _docx_document(elements=elements, chunks=[])
    m = compute_automatic_metrics(doc, None, "docx", expectations={})
    assert m["silent_drop_count"]["reason"] == "no_expectations"


def test_silent_drop_expectations_without_element_count_by_type():
    """expectations 存在但没有 element_count_by_type → no_expectations_element_count。"""
    elements = [_heading("e0", "h")]
    doc = _docx_document(elements=elements, chunks=[])
    m = compute_automatic_metrics(
        doc, None, "docx", expectations={"other_field": "x"}
    )
    assert m["silent_drop_count"]["reason"] == "no_expectations_element_count"


def test_silent_drop_multiple_types_dropped_sums():
    """多种类型同时缺 → 求和。"""
    # actual: 1 heading, 0 table, 0 image
    elements = [_heading("e0", "h")]
    doc = _docx_document(elements=elements, chunks=[])
    # expected: 2 heading, 3 table, 1 image → drops = 1 + 3 + 1 = 5
    expectations = {
        "element_count_by_type": {"heading": 2, "table": 3, "image": 1}
    }
    m = compute_automatic_metrics(doc, None, "docx", expectations)
    assert m["silent_drop_count"]["value"] == 5


def test_schema_valid_false_when_document_invalid():
    """document 字段缺失或类型错 → schema_valid=False。"""
    bad_doc = {
        "schema_version": "0.1.0",
        "document_id": "d-bad",
        # 缺 source_path/source_type/source_hash/parser_name/parser_version
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    m = compute_automatic_metrics(bad_doc, None, "docx", None)
    assert m["schema_valid"]["value"] is False


def test_pipeline_success_false_when_error_present():
    """error 非 None 但 document 非 None → pipeline_success=False。"""
    doc = _docx_document(elements=[], chunks=[])
    m = compute_automatic_metrics(
        document=doc,
        error={"code": "some_error", "message": "x"},
        source_type="docx",
        expectations=None,
    )
    assert m["pipeline_success"]["value"] is False
    assert m["error_code"]["value"] == "some_error"
