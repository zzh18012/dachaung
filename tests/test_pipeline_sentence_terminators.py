r"""pipeline 句末符集：。！？.!? 终结（需后
随空白），; , 不终结（Round 1780）。

新角度：R1779 锁句界优先——**句末符集
{. ! ? 。 ！ ？}后随空白才构成句界：
稀疏全角 6×142=852 切 709（尾 '。'，尾
随空格丢弃）；密集 '好. '×300 落 800 但
boundary None（句界）非 forced_char；
';'/',' 不触发 → 799 whitespace 回退**零
覆盖：

- **('好'*140+'。 ')×6**：709+141，boundary
  全 None、尾 '。'
- **'好. '/'好！ '×300**：800+98，boundary
  None（句界）而非 forced_char
- **'abc; '/'abc, '×200**：799
  'whitespace'+199 回退
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.txt"
    p.write_text(text + "\n", encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="text")


def test_sparse_fullwidth_period_boundary(tmp_path):
    doc, errors = _run(
        tmp_path, ("好" * 140 + "。 ") * 6)
    assert errors == []
    assert [(len(c.text),
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [(709, None),
                                     (141, None)]
    assert doc.chunks[0].text.endswith("。")
    assert doc.chunks[1].text.endswith("。")


def test_dense_terminator_boundary_key(tmp_path):
    for text in ("好. " * 300, "好！ " * 300):
        doc, errors = _run(tmp_path, text)
        assert errors == []
        assert [(len(c.text),
                 c.metadata.get("split_boundary_after"))
                for c in doc.chunks] == [
            (800, None), (98, None)]


def test_semicolon_comma_not_terminators(tmp_path):
    for text in ("abc; " * 200, "abc, " * 200):
        doc, errors = _run(tmp_path, text)
        assert errors == []
        assert [(len(c.text),
                 c.metadata.get("split_boundary_after"))
                for c in doc.chunks] == [
            (799, "whitespace"), (199, None)]
