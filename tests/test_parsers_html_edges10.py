r"""app/parsers/html_parser.py 边角测试 - 第十轮（Round 1371）。

补强 edges9 未覆盖的深度（probe 实证，历史 html 测试对表单控件
零覆盖）：
- form 是透明容器：整块文本坍缩进一个 paragraph，且不关闭段落
  缓冲——后续 <p> 的文本直接拼进来（'Fafter'）
- select 的 option 文本无分隔符拼接（'AB' / 'OneTwo'）
- input 无文本贡献（placeholder 属性丢弃）；datalist 无文本
  option 同样无痕
- textarea 文本保留；button/label 各成一个段落（独立出现时）
- fieldset/legend 文本摊平（'Groupinside fieldset'）
- progress/meter 保留内部文本（'70%' / 'half'），value 属性丢弃
- 已知块（h2/table）照常关闭 form 打开的缓冲
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser


FULL = """<html><body>
<form>
<label for="n">Name</label>
<input type="text" placeholder="enter name">
<select><option value="1">One</option>
<option value="2">Two</option></select>
<textarea rows="3">default text</textarea>
<fieldset><legend>Group</legend>
inside fieldset</fieldset>
<datalist><option value="x"></datalist>
<output>result</output>
<progress value="70" max="100">70%</progress>
<meter value="0.5">half</meter>
</form>
<p>after form</p>
</body></html>"""


def _parse(html):
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "t.html").write_text(html, encoding="utf-8")
        return HtmlParser().parse(
            tp / "t.html",
            compute_file_hash(tp / "t.html"))


# ---------- 整板坍缩 ----------

def test_full_form_single_paragraph():
    doc = _parse(FULL)
    assert [(e.type, e.content) for e in doc.elements
            ] == [(
        "paragraph",
        "Name\n\nOne\nTwo\ndefault text\n"
        "Group\ninside fieldset\n\nresult\n70%\n"
        "half\n\nafter form")]


def test_full_form_element_count():
    assert len(_parse(FULL).elements) == 1


def test_full_form_no_warnings():
    assert _parse(FULL).warnings == []


def test_after_form_p_merged():
    doc = _parse(FULL)
    assert doc.elements[0].content.endswith(
        "\nafter form")


# ---------- 单控件独立出现 ----------

def test_form_only_text():
    assert [(e.type, e.content)
            for e in _parse(
        "<html><body><form>Only</form>"
        "</body></html>").elements
            ] == [("paragraph", "Only")]


def test_select_options_no_separator():
    doc = _parse("<html><body><select><option>A"
                 "</option><option>B</option>"
                 "</select></body></html>")
    assert doc.elements[0].content == "AB"


def test_button_text():
    doc = _parse("<html><body><button>Click"
                 "</button></body></html>")
    assert doc.elements[0].content == "Click"


def test_label_text():
    doc = _parse("<html><body><label>Name"
                 "</label></body></html>")
    assert doc.elements[0].content == "Name"


def test_textarea_text():
    doc = _parse("<html><body><textarea>ta"
                 "</textarea></body></html>")
    assert doc.elements[0].content == "ta"


# ---------- input / datalist 无痕 ----------

def test_input_no_text_contribution():
    doc = _parse("<html><body><input type='text' "
                 "placeholder='ph'><p>real</p>"
                 "</body></html>")
    assert [e.content for e in doc.elements
            ] == ["real"]


def test_datalist_valueless_option_silent():
    doc = _parse("<html><body><datalist><option "
                 "value='x'></datalist><p>real</p>"
                 "</body></html>")
    assert [e.content for e in doc.elements
            ] == ["real"]


# ---------- progress / meter / output ----------

def test_progress_inner_text_kept():
    doc = _parse("<html><body><progress value='70' "
                 "max='100'>70%</progress>"
                 "</body></html>")
    assert doc.elements[0].content == "70%"


def test_meter_inner_text_kept():
    doc = _parse("<html><body><meter value='0.5'>"
                 "half</meter></body></html>")
    assert doc.elements[0].content == "half"


def test_output_text_kept():
    doc = _parse("<html><body><output>result"
                 "</output></body></html>")
    assert doc.elements[0].content == "result"


def test_value_attrs_dropped():
    doc = _parse("<html><body><progress value='70'"
                 ">t</progress></body></html>")
    assert doc.elements[0].metadata == {}


# ---------- fieldset / legend ----------

def test_fieldset_flattened():
    doc = _parse("<html><body><fieldset>"
                 "<legend>Group</legend>inside"
                 "</fieldset></body></html>")
    assert doc.elements[0].content == \
        "Groupinside"


def test_fieldset_legend_newline_source():
    doc = _parse("<html><body><fieldset>"
                 "<legend>Group</legend>\ninside"
                 "</fieldset></body></html>")
    assert doc.elements[0].content == \
        "Group\ninside"


# ---------- 缓冲不关闭（透明容器语义） ----------

def test_form_p_merge():
    doc = _parse("<html><body><form>F</form>"
                 "<p>after</p></body></html>")
    assert [e.content for e in doc.elements
            ] == ["Fafter"]


def test_form_h2_closes_buffer():
    doc = _parse("<html><body><form>F</form>"
                 "<h2>Head</h2></body></html>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "F"), ("heading", "Head")]


def test_form_table_closes_buffer():
    doc = _parse("<html><body><form>F</form>"
                 "<table><tr><td>1</td></tr>"
                 "</table></body></html>")
    assert [e.type for e in doc.elements
            ] == ["paragraph", "table"]


def test_form_form_merge():
    doc = _parse("<html><body><form>A</form>"
                 "<form>B</form></body></html>")
    assert [e.content for e in doc.elements
            ] == ["AB"]


def test_p_form_separate():
    doc = _parse("<html><body><p>before</p>"
                 "<form>F</form></body></html>")
    assert [e.content for e in doc.elements
            ] == ["before", "F"]


def test_label_p_merge():
    doc = _parse("<html><body><label>L</label>"
                 "<p>after</p></body></html>")
    assert [e.content for e in doc.elements
            ] == ["Lafter"]


# ---------- 定位 ----------

def test_form_paragraph_locator_line():
    doc = _parse(FULL)
    assert doc.elements[0].source_locator[
        "line"] == 3


def test_form_doc_identity():
    doc = _parse(FULL)
    assert doc.source_type == "html"
    assert doc.parser_name == "html"
    assert doc.parser_version == "stdlib/0.1.0"


def test_form_doc_passes_schema():
    from app.schema import is_valid
    assert is_valid(_parse(FULL).to_dict())
