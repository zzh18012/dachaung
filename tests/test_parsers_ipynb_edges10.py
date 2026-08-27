r"""app/parsers/ipynb_parser.py 边角测试 - 第十轮（Round 1374）。

补强 edges9 未触达面（probe 实证）：
- image 提取规则：整行单图 → image 元素；图 + 文本同行 → 字面
  paragraph（'before ![pic](img.png)' 不提取）；两行两图 → 两个
  image 元素；无 alt → alt ''；title 拼进 resource_path
  （'img.png "title"'）；纯链接 [text](url) 不提取
- attachments 字段对提取无影响（attachment: 前缀只是 URL 字面值）
- code cell 的 outputs 三种类型（stream/execute_result/error）全
  部丢弃，只留 source
- cells 为空 dict {} 时被容忍（cell_count 0 + ipynb_no_content）；
  非空 dict → ipynb_bad_structure
- source 为 int 42 → ipynb_empty_code_cell + ipynb_no_content
  双告警，不崩溃
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.base import ParserError
from app.parsers.ipynb_parser import IpynbParser


def _parse(nb):
    # adoption 契约 §2 注记（2026-08-27）：版本字段必填——fixture 缺省时补默认。
    if isinstance(nb, dict):
        nb.setdefault("nbformat", 4)
        nb.setdefault("nbformat_minor", 5)
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "t.ipynb").write_text(
            json.dumps(nb), encoding="utf-8")
        return IpynbParser().parse(
            tp / "t.ipynb",
            compute_file_hash(tp / "t.ipynb"))


def _nb(source):
    # adoption 契约 §2 注记（2026-08-27）：补 nbformat_minor（版本字段必填）。
    return {"cells": [{"cell_type": "markdown",
                       "source": source}],
            "metadata": {}, "nbformat": 4, "nbformat_minor": 5}


# ---------- image 提取规则 ----------

def test_single_image_whole_line():
    doc = _parse(_nb("![pic](img.png)"))
    assert [(e.type, e.resource_path, e.metadata)
            for e in doc.elements] == [
        ("image", "img.png", {"alt": "pic"})]


def test_attachment_prefix_is_literal_url():
    doc = _parse(_nb("![pic](attachment:p.png)"))
    img = doc.elements[0]
    assert img.type == "image"
    assert img.resource_path == "attachment:p.png"


def test_image_with_text_same_line_not_extracted():
    doc = _parse(_nb("before ![pic](img.png)"))
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "before ![pic](img.png)")]


def test_two_images_two_lines_extracted():
    doc = _parse(_nb("![a](1.png)\n![b](2.png)"))
    assert [(e.type, e.resource_path)
            for e in doc.elements] == [
        ("image", "1.png"), ("image", "2.png")]


def test_two_images_same_line_not_extracted():
    doc = _parse(_nb("![a](1.png)![b](2.png)"))
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "paragraph"


def test_image_empty_alt():
    doc = _parse(_nb("![](img.png)"))
    assert doc.elements[0].metadata == {"alt": ""}


def test_image_title_glued_to_resource():
    doc = _parse(_nb('![alt](img.png "title")'))
    img = doc.elements[0]
    assert img.resource_path == 'img.png "title"'
    assert img.metadata == {"alt": "alt"}


def test_plain_link_not_extracted():
    doc = _parse(_nb("[text](url)"))
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "[text](url)")]


# ---------- attachments 无影响 ----------

def test_attachments_irrelevant_to_extraction():
    nb = {"cells": [{"cell_type": "markdown",
                     "source": "no images",
                     "attachments": {"x.png": {
                         "image/png": "AA"}}}],
          "metadata": {}, "nbformat": 4}
    doc = _parse(nb)
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "no images")]


def test_attachments_alone_no_element():
    nb = {"cells": [{"cell_type": "markdown",
                     "source": "",
                     "attachments": {"x.png": {
                         "image/png": "AA"}}}],
          "metadata": {}, "nbformat": 4}
    doc = _parse(nb)
    assert doc.elements == []
    assert "ipynb_no_content" in [
        w.code for w in doc.warnings]


# ---------- outputs 全丢 ----------

def _code_nb(outputs):
    return {"cells": [{"cell_type": "code",
                       "source": "x",
                       "outputs": outputs}],
            "metadata": {}, "nbformat": 4}


def test_stream_output_dropped():
    doc = _parse(_code_nb([
        {"output_type": "stream",
         "text": "out1\n"}]))
    code = doc.elements[0]
    assert code.content == "x"
    assert "out1" not in code.content


def test_execute_result_dropped():
    doc = _parse(_code_nb([
        {"output_type": "execute_result",
         "data": {"text/plain": "2"}}]))
    assert doc.elements[0].content == "x"


def test_error_output_dropped():
    doc = _parse(_code_nb([
        {"output_type": "error",
         "ename": "E"}]))
    assert doc.elements[0].content == "x"


def test_image_output_dropped():
    doc = _parse(_code_nb([
        {"output_type": "display_data",
         "data": {"image/png": "AAAA"}}]))
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "paragraph"
    assert "AAAA" not in str(
        doc.elements[0].to_dict())


# ---------- cells 类型 ----------

def test_cells_empty_dict_tolerated():
    nb = {"cells": {}, "metadata": {},
          "nbformat": 4}
    doc = _parse(nb)
    assert doc.elements == []
    assert doc.metadata["cell_count"] == 0
    assert "ipynb_no_content" in [
        w.code for w in doc.warnings]


def test_cells_nonempty_dict_rejected():
    nb = {"cells": {"a": 1}, "metadata": {},
          "nbformat": 4}
    try:
        _parse(nb)
        raise AssertionError("should raise")
    except ParserError as e:
        assert e.code == "ipynb_bad_structure"


def test_cells_string_rejected():
    nb = {"cells": "nope", "metadata": {},
          "nbformat": 4}
    try:
        _parse(nb)
        raise AssertionError("should raise")
    except ParserError as e:
        assert e.code == "ipynb_bad_structure"


def test_cells_none_tolerated():
    nb = {"cells": None, "metadata": {},
          "nbformat": 4}
    doc = _parse(nb)
    assert doc.metadata["cell_count"] == 0


# ---------- source 非字符串 ----------

# adoption 契约 §5 注记（2026-08-27）：source 非法（非 str / 非 str-list）→ 跳过 cell + ipynb_bad_cell。
def test_source_int_double_warning():
    nb = {"cells": [{"cell_type": "code",
                     "source": 42}],
          "metadata": {}, "nbformat": 4}
    doc = _parse(nb)
    codes = [w.code for w in doc.warnings]
    assert codes == ["ipynb_bad_cell",
                     "ipynb_no_content"]
    assert doc.warnings[0].details == {
        "cell_index": 0, "field": "source"}


def test_source_int_no_elements():
    nb = {"cells": [{"cell_type": "code",
                     "source": 42}],
          "metadata": {}, "nbformat": 4}
    assert _parse(nb).elements == []


# ---------- schema ----------

def test_image_doc_passes_schema():
    from app.schema import is_valid
    doc = _parse(_nb("![pic](img.png)"))
    assert is_valid(doc.to_dict())


def test_image_doc_identity():
    doc = _parse(_nb("![pic](img.png)"))
    assert doc.source_type == "ipynb"
    assert doc.parser_version == "stdlib/0.1.0"
