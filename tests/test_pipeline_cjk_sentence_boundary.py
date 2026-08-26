r"""pipeline 中文句号不作句界、ASCII ?/!
句界与混合文本 forced_char（Round 1723）。

新角度：R1722 锁边界元数据三态——**'。'
不被切分器当句界（'你好。'*300 仍
forced_char 切 800，对比 '?''!' 被识别成
句界）**零覆盖：

- **'你好。'*300（900 字符）**：800
  forced_char + 100（首块尾部 '好。你好'
  跨句中）
- **'what? yes! '*100（1100 字符）**：
  797 + 301，块尾分别 'hat?'/'yes!'（?/!
  句界切分，无 split_boundary_after 键）
- **'hello世界测试。'*100**：800
  forced_char + 200（中英混合同样无句界）
- **'你好。'*200（600 字符）**：单 chunk
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _chunks(tmp_path, text):
    p = tmp_path / "d.txt"
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    return doc.chunks


def test_cjk_period_not_sentence_boundary(tmp_path):
    chunks = _chunks(tmp_path, "你好。" * 300)
    assert len(chunks) == 2
    assert (len(chunks[0].text),
            chunks[0].metadata["split_boundary_after"]) == \
        (800, "forced_char")
    assert chunks[0].text.endswith("好。你好")
    assert len(chunks[1].text) == 100


def test_ascii_q_excl_sentence_boundaries(tmp_path):
    chunks = _chunks(tmp_path, "what? yes! " * 100)
    assert [len(c.text) for c in chunks] == [797, 301]
    assert chunks[0].text.endswith("hat?")
    assert chunks[1].text.endswith("yes!")
    for c in chunks:
        assert "split_boundary_after" not in c.metadata


def test_mixed_cjk_latin_forced(tmp_path):
    chunks = _chunks(tmp_path, "hello世界测试。" * 100)
    assert [(len(c.text),
             c.metadata.get("split_boundary_after"))
            for c in chunks] == [
        (800, "forced_char"), (200, None)]


def test_cjk_under_limit_single_chunk(tmp_path):
    chunks = _chunks(tmp_path, "你好。" * 200)
    assert len(chunks) == 1
    assert len(chunks[0].text) == 600
