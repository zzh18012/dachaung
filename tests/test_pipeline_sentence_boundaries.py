r"""pipeline 句界字符集：?;! 边界、小数点豁免、
中文句号非边界（Round 1615）。

新角度：R1614 锁小 max_chars——**句界字符集本身**
零覆盖（R1591 只对比 '.' 与 ','）：

- **ASCII ?/;/! 均为句界**：按句贪心累积，
  超限即 flush
- **小数点不拆**：'3.14'/'2.71' 完整保留（首句
  恰 40 = max）
- **中文全角句号 '。' 不是句界**：无空格文本在
  max 处硬切（32/9，句子中间切断）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _chunks(tmp_path, name, text, mc):
    p = tmp_path / name
    p.write_text(text + "\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False,
        parser_name="text", max_chars=mc)
    assert errors == []
    return [c.text for c in doc.chunks]


def test_ascii_boundaries(tmp_path):
    got = _chunks(
        tmp_path, "q.txt",
        "Really done? Yes it is; quite so! "
        "Final part here ok.", 32)
    assert got == [
        "Really done?",
        "Yes it is; quite so!",
        "Final part here ok."]


def test_decimals_not_split(tmp_path):
    got = _chunks(
        tmp_path, "d.txt",
        "The value 3.14 is pi and 2.71 is e "
        "here. Second sentence follows now ok.",
        40)
    assert got == [
        "The value 3.14 is pi and 2.71 is "
        "e here.",
        "Second sentence follows now ok."]
    assert len(got[0]) == 40


def test_cjk_fullstop_not_boundary(tmp_path):
    text = ("第一句话的内容在这里结束了呀。"
            "第二句话的内容在这里也结束了呀。"
            "第三句话内容结束了。")
    assert len(text) == 41
    got = _chunks(
        tmp_path, "c.txt", text, 32)
    assert got == [
        "第一句话的内容在这里结束了呀。"
        "第二句话的内容在这里也结束了呀。第",
        "三句话内容结束了。"]
    assert [len(g) for g in got] == [32, 9]
