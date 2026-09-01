"""批次 20 Phase B 测试：schema 0.6.0 开放扩展 source_type。

覆盖设计裁决 D2（版本分支 + pattern + family 驱动 locator 形状）：
- 0.6.0 非内置类型：locator 必须带 family（封闭四值），形状按 family
  路由到对应 locator def（page_geometry→page、structural_index→
  结构键、line_address→line、container_line→cell_index/cell_type）。
- 0.1.0–0.5.0 守卫：source_type 仍限内置六类型，新类型被旧版本拒绝。
- 顶层 pattern：^[a-z][a-z0-9_]{0,31}$（拒大写/数字开头/超长/空白）。
- 内置六类型在 0.5.0 与 0.6.0 下形状一致（升版零回归承诺）。
"""

from __future__ import annotations

import pytest

from app.models import SCHEMA_VERSION_CURRENT, Document, Element
from app.schema import validate as validate_udm

BUILTIN = ["pdf", "docx", "markdown", "html", "text", "ipynb"]


def _udm(source_type: str, schema_version: str, locator: dict) -> dict:
    return {
        "schema_version": schema_version,
        "document_id": "doc1",
        "source_path": "samples/x",
        "source_type": source_type,
        "source_hash": "a" * 64,
        "parser_name": "p",
        "parser_version": "1",
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "parent_id": None,
                "source_locator": locator,
                "content": "x",
                "resource_path": None,
                "confidence": 1.0,
                "metadata": {},
            }
        ],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


# ---------- 0.6.0 扩展类型：正向 ----------

@pytest.mark.parametrize(
    "locator",
    [
        {"family": "line_address", "line": 1},
        {"family": "line_address", "line": 3, "section_path": "intro"},
        {"family": "page_geometry", "page": 1},
        {"family": "page_geometry", "page": 2, "bbox": [0, 0, 1, 1]},
        {"family": "structural_index", "paragraph_index": 0},
        {"family": "container_line", "cell_index": 0, "cell_type": "code"},
    ],
)
def test_060_new_type_valid_by_family(locator):
    validate_udm(_udm("myx", "0.6.0", locator))


def test_060_new_type_extra_locator_keys_allowed():
    # line_address_locator additionalProperties true：family/line 之外可带扩展键
    validate_udm(
        _udm("myx", "0.6.0", {"family": "line_address", "line": 1, "col": 4})
    )


# ---------- 0.6.0 扩展类型：family 契约负面 ----------

def test_060_new_type_missing_family_rejected():
    with pytest.raises(Exception):
        validate_udm(_udm("myx", "0.6.0", {"line": 1}))


def test_060_new_type_bogus_family_rejected():
    with pytest.raises(Exception):
        validate_udm(_udm("myx", "0.6.0", {"family": "byte_offset", "line": 1}))


@pytest.mark.parametrize(
    "locator",
    [
        # page_geometry 形状：缺 page / page<1
        {"family": "page_geometry"},
        {"family": "page_geometry", "page": 0},
        # line_address 形状：缺 line / line<1
        {"family": "line_address"},
        {"family": "line_address", "line": 0},
        # container_line 形状：缺 cell_type / cell_type 非法 / 缺 cell_index
        {"family": "container_line", "cell_index": 0},
        {"family": "container_line", "cell_index": 0, "cell_type": "formula"},
        {"family": "container_line", "cell_type": "code"},
    ],
)
def test_060_new_type_wrong_shape_for_family_rejected(locator):
    with pytest.raises(Exception):
        validate_udm(_udm("myx", "0.6.0", locator))


def test_060_structural_index_minimal_locator_valid():
    # docx_locator 语义为 minProperties:1：family 自身计一个属性（与内置
    # docx 的既有形状检查同语义，不为扩展类型收紧）
    validate_udm(_udm("myx", "0.6.0", {"family": "structural_index"}))


# ---------- 旧版本守卫：0.1.0–0.5.0 拒新类型 ----------

@pytest.mark.parametrize("version", ["0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0"])
def test_old_versions_reject_new_type(version):
    with pytest.raises(Exception):
        validate_udm(_udm("myx", version, {"family": "line_address", "line": 1}))


@pytest.mark.parametrize("version", ["0.5.0", "0.6.0"])
def test_builtin_types_valid_under_both_versions(version):
    locators = {
        "pdf": {"family": "page_geometry", "page": 1},
        "docx": {"family": "structural_index", "paragraph_index": 0},
        "markdown": {"family": "line_address", "line": 1},
        "html": {"family": "line_address", "line": 1},
        "text": {"family": "line_address", "line": 1},
        "ipynb": {"family": "container_line", "cell_index": 0, "cell_type": "code"},
    }
    for st in BUILTIN:
        validate_udm(_udm(st, version, locators[st]))


def test_060_builtin_missing_family_rejected():
    # family 绑定分支已扩到 0.6.0：内置类型在新版本下仍必须带 family
    with pytest.raises(Exception):
        validate_udm(_udm("markdown", "0.6.0", {"line": 1}))


# ---------- 顶层 source_type pattern ----------

@pytest.mark.parametrize(
    "bad_type", ["Myx", "myX", "1abc", "_myx", "my-x", "a b", "myx ", ""]
)
def test_060_pattern_rejects_invalid_source_type(bad_type):
    with pytest.raises(Exception):
        validate_udm(
            _udm(bad_type, "0.6.0", {"family": "line_address", "line": 1})
        )


def test_060_pattern_accepts_32_chars():
    st = "a" + "b" * 31
    validate_udm(_udm(st, "0.6.0", {"family": "line_address", "line": 1}))


def test_060_pattern_rejects_33_chars():
    st = "a" + "b" * 32
    with pytest.raises(Exception):
        validate_udm(_udm(st, "0.6.0", {"family": "line_address", "line": 1}))


# ---------- writer 版本 ----------

def test_current_version_constant_is_060():
    assert SCHEMA_VERSION_CURRENT == "0.6.0"


def test_extension_document_to_dict_validates():
    doc = Document(
        document_id="doc1",
        source_path="samples/x.myx",
        source_type="myx",
        source_hash="a" * 64,
        parser_name="myx_parser",
        parser_version="test/1.0",
        elements=[
            Element(
                element_id="e1",
                type="paragraph",
                content="x",
                source_locator={"family": "line_address", "line": 1},
            )
        ],
    )
    d = doc.to_dict()
    assert d["schema_version"] == "0.6.0"
    assert d["source_type"] == "myx"
    validate_udm(d)
