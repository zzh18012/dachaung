r"""app/parsers/html_parser.py 边角测试 - 第十一轮（Round 1372）。

补强 edges10（表单控件）后继续未触达面（probe 实证，历史 html
测试对媒体/嵌入标签零覆盖）：
- video/canvas/object/iframe 的 fallback 文本保留且不关闭段落缓冲
  （与后续 <p> 拼接 'fallback vidt'）
- picture 透明——内部 <img> 正常产 image 元素（含 alt metadata）
- audio/embed 无文本贡献；<source>/<track> 子标签静默
- svg 不整体跳过：<text> 文本保留（'SVGTEXTt'）；但 <title> 在
  全局 skip 集里——svg 内 title 也被吞（svg+title → 0 元素）
- details/dialog/template/math 文本全保留并拼接
- h2 照常关闭媒体打开的缓冲
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser


def _parse(html):
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "t.html").write_text(html, encoding="utf-8")
        return HtmlParser().parse(
            tp / "t.html",
            compute_file_hash(tp / "t.html"))


# ---------- video ----------

def test_video_fallback_text_kept():
    doc = _parse("<html><body><video src='v.mp4'>"
                 "fallback vid</video><p>t</p>"
                 "</body></html>")
    assert [e.content for e in doc.elements
            ] == ["fallback vidt"]


def test_video_source_child_silent():
    doc = _parse("<html><body><video><source "
                 "src='a.mp4' type='video/mp4'>"
                 "inner</video></body></html>")
    assert [e.content for e in doc.elements
            ] == ["inner"]


def test_video_h2_closes_buffer():
    doc = _parse("<html><body><video>v</video>"
                 "<h2>H</h2></body></html>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "v"),
        ("heading", "H")]


# ---------- audio / embed ----------

def test_audio_no_text_contribution():
    doc = _parse("<html><body><audio controls "
                 "src='a.mp3'></audio><p>t</p>"
                 "</body></html>")
    assert [e.content for e in doc.elements
            ] == ["t"]


def test_audio_track_silent():
    doc = _parse("<html><body><audio><track "
                 "src='t.vtt'>aud</audio>"
                 "</body></html>")
    assert [e.content for e in doc.elements
            ] == ["aud"]


def test_embed_no_text_contribution():
    doc = _parse("<html><body><embed src='e.swf'>"
                 "<p>t</p></body></html>")
    assert [e.content for e in doc.elements
            ] == ["t"]


# ---------- canvas / object / iframe ----------

def test_canvas_fallback_text_kept():
    doc = _parse("<html><body><canvas>noscript "
                 "canvas</canvas><p>t</p>"
                 "</body></html>")
    assert [e.content for e in doc.elements
            ] == ["noscript canvast"]


def test_object_fallback_text_kept():
    doc = _parse("<html><body><object data="
                 "'o.pdf'>obj fallback</object>"
                 "<p>t</p></body></html>")
    assert [e.content for e in doc.elements
            ] == ["obj fallbackt"]


def test_iframe_fallback_text_kept():
    doc = _parse("<html><body><iframe>ifallback"
                 "</iframe></body></html>")
    assert [e.content for e in doc.elements
            ] == ["ifallback"]


def test_iframe_empty_no_element():
    doc = _parse("<html><body><iframe src="
                 "'x.html'></iframe><p>t</p>"
                 "</body></html>")
    assert [e.content for e in doc.elements
            ] == ["t"]


# ---------- picture ----------

def test_picture_transparent_img_emitted():
    doc = _parse("<html><body><picture><img "
                 "src='p.png' alt='PA'></picture>"
                 "<p>t</p></body></html>")
    assert [(e.type, e.resource_path)
            for e in doc.elements] == [
        ("image", "p.png"), ("paragraph", None)]


def test_picture_img_alt_metadata():
    doc = _parse("<html><body><picture><img "
                 "src='p.png' alt='PA'></picture>"
                 "</body></html>")
    img = doc.elements[0]
    assert img.metadata == {"alt": "PA"}


# ---------- svg ----------

def test_svg_text_content_kept():
    doc = _parse("<html><body><svg width='10'>"
                 "<text>SVGTEXT</text></svg>"
                 "<p>t</p></body></html>")
    assert [e.content for e in doc.elements
            ] == ["SVGTEXTt"]


def test_svg_title_swallowed():
    """<title> 在全局 skip 集——svg 内的 title 也被吞。"""
    doc = _parse("<html><body><svg><title>cap"
                 "</title></svg></body></html>")
    assert doc.elements == []


def test_svg_rect_only_empty():
    doc = _parse("<html><body><svg><rect "
                 "width='5'/><title>TT</title>"
                 "</svg></body></html>")
    assert doc.elements == []


# ---------- details / dialog / template / math ----------

def test_details_flattened():
    doc = _parse("<html><body><details>"
                 "<summary>Sum</summary>hidden body"
                 "</details><p>t</p></body></html>")
    assert [e.content for e in doc.elements
            ] == ["Sumhidden bodyt"]


def test_dialog_text_kept():
    doc = _parse("<html><body><dialog open>dlg"
                 "</dialog><p>t</p></body></html>")
    assert [e.content for e in doc.elements
            ] == ["dlgt"]


def test_template_content_kept():
    doc = _parse("<html><body><template>tpl "
                 "content</template><p>t</p>"
                 "</body></html>")
    assert [e.content for e in doc.elements
            ] == ["tpl contentt"]


def test_template_empty_silent():
    doc = _parse("<html><body><template>"
                 "</template><p>only</p>"
                 "</body></html>")
    assert [e.content for e in doc.elements
            ] == ["only"]


def test_math_text_kept():
    doc = _parse("<html><body><math><mi>x</mi>"
                 "</math><p>t</p></body></html>")
    assert [e.content for e in doc.elements
            ] == ["xt"]


# ---------- noscript 全吞 ----------

def test_noscript_swallowed():
    doc = _parse("<html><body><noscript>NS"
                 "</noscript></body></html>")
    assert doc.elements == []


# ---------- 无警告 + schema ----------

def test_media_board_no_warnings():
    doc = _parse("<html><body><video>v</video>"
                 "<canvas>c</canvas><audio></audio>"
                 "</body></html>")
    assert doc.warnings == []


def test_media_doc_passes_schema():
    from app.schema import is_valid
    doc = _parse("<html><body><video src='v'>"
                 "fb</video><picture><img src="
                 "'p.png'></picture></body>"
                 "</html>")
    assert is_valid(doc.to_dict())


def test_media_doc_source_type():
    doc = _parse("<html><body><video>v</video>"
                 "</body></html>")
    assert doc.source_type == "html"
