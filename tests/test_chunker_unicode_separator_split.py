r"""chunker 对 unicode 分隔符的切分行为：惰性保留 + 家族对照（Round 1851）。

新角度（probe 实证；edges9/10 只锁 _WHITESPACE_RE 与 normalize_text
的 RE 层，pipeline_line_separators 只锁 parser 层惰性——**chunk 实际
切分位置/逐字保留/尾分隔符剥除/家族对照**零覆盖）：
- **分隔符惰性 + 普通空格切分**：html U+2028 / text FF 段在
  max_chars=40 下按普通空格贪心切（39+7），分隔符逐字留在 chunk 内
  且计入长度（非优先切点、非句界）
- **纯分隔符白空间硬切**：('ab'+FF)\\*20 @32 → 恰 32/26 两 chunk，
  FF 作为词界生效、行尾 FF 剥除，两 chunk 同一 element id
- **家族对照（同内容 .md vs .txt）**：md 把 U+2028 归一成 \\n 后
  切分位置与 text 完全一致（32/26），仅分隔符字符不同
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single

U2028 = chr(0x2028)
FF = chr(12)


def _run(tmp_path: Path, name: str, text: str, parser: str, max_chars: int):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8", newline="")
    out = tmp_path / (name + ".json")
    _, errs = process_single(p, out, parser_name=parser, max_chars=max_chars)
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_separator_preserved_split_at_spaces(tmp_path: Path):
    words = "w00 w01 w02 w03" + U2028 + "w04 w05 w06 w07" + U2028 + "w08 w09 w10 w11"
    data = _run(tmp_path, "a.html", f"<p>{words}</p>", "html", 40)
    texts = [c["text"] for c in data["chunks"]]
    assert texts == [words[:39], "w10 w11"]
    assert U2028 in texts[0]
    assert len(texts[0]) == 39

    t = _run(tmp_path, "b.txt", "w00 w01 w02 w03" + FF + "w04 w05 w06 w07" + FF
             + "w08 w09 w10 w11\n", "text", 40)
    assert [c["text"] for c in t["chunks"]] == [
        "w00 w01 w02 w03" + FF + "w04 w05 w06 w07" + FF + "w08 w09",
        "w10 w11"]


def test_ff_only_whitespace_boundary(tmp_path: Path):
    data = _run(tmp_path, "c.txt", ("ab" + FF) * 20, "text", 32)
    chunks = data["chunks"]
    assert len(chunks) == 2
    assert chunks[0]["text"] == ("ab" + FF) * 10 + "ab"
    assert len(chunks[0]["text"]) == 32
    assert not chunks[0]["text"].endswith(FF)
    assert chunks[1]["text"] == ("ab" + FF) * 8 + "ab"
    assert chunks[0]["source_element_ids"] == chunks[1]["source_element_ids"]


def test_md_text_family_normalization_contrast(tmp_path: Path):
    content = ("ab" + U2028) * 20
    md = _run(tmp_path, "d.md", content, "markdown", 32)
    txt = _run(tmp_path, "e.txt", content, "text", 32)
    md_texts = [c["text"] for c in md["chunks"]]
    txt_texts = [c["text"] for c in txt["chunks"]]
    assert md_texts == [("ab\n") * 10 + "ab", ("ab\n") * 8 + "ab"]
    assert txt_texts == [("ab" + U2028) * 10 + "ab", ("ab" + U2028) * 8 + "ab"]
    assert [len(t) for t in md_texts] == [len(t) for t in txt_texts]
