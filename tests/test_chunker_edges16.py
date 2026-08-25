r"""app/chunkers/structural.py 边角测试 - 第十六轮（Round 1507）。

新角度（strategy 值审计发现：f-string isolated_{type} 的
三个理论值中 isolated_image **零测试命中**；probe 实证比
预期更极端）：

- **⚠ image 的 content 被 chunker 静默丢弃**：
  _element_text_with_span 对 type='image' **按类型硬返
  空**（与是否有 content 无关）→ 带内容 'alt text here'
  的 image 产 **0 chunk**（若未来 parser 给 image 填
  content，将在此静默丢失）
- **段跨 image 合并**：para + image(有 content) + para
  → 'one two three four' 单 chunk 双 ids（image 完全
  不可见）
- **超长 image content 同样 0 chunk**（isolated 分支根
  本到不了）
- 结论：isolated_image 策略值在当前实现中**不可达**
  （isolated_table / isolated_caption 可达且已锁）
"""

from __future__ import annotations

from app.chunkers.structural import \
    StructuralChunker

from tests.test_chunker_edges14 \
    import _doc, _el


def _chunks(els, max_chars=100):
    return StructuralChunker(
        max_chars=max_chars).chunk(
        _doc(els))


def test_image_with_content_no_chunks():
    chunks = _chunks(
        [_el(0, "image",
             "alt text here")])
    assert chunks == []


def test_image_with_content_and_resource_no_chunks():
    chunks = _chunks(
        [_el(0, "image", "both",
             resource_path="x.png")])
    assert chunks == []


def test_paras_merge_across_content_image():
    els = [
        _el(0, "paragraph", "one two"),
        _el(1, "image", "the alt"),
        _el(2, "paragraph", "three four"),
    ]
    chunks = _chunks(els)
    assert len(chunks) == 1
    c = chunks[0]
    assert c.text == "one two three four"
    assert c.source_element_ids == [
        e.element_id
        for e in (els[0], els[2])]
    assert c.metadata["strategy"] == \
        "sequential"


def test_oversized_image_content_no_chunks():
    chunks = _chunks(
        [_el(0, "image", "A" * 250)])
    assert chunks == []
