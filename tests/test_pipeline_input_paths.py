r"""pipeline 输入路径形态错误（Round 1556）。

新角度：`file_not_found`（文件不存在）与
`unsupported_type`（错误扩展名）各自有覆盖，但两个
**输入路径形态**变体零覆盖：

- **输入是目录** → hash 阶段即拒绝：单条
  file_not_found（消息含路径），不进 parser
- **无扩展名文件** → unsupported_type 消息含 '(无)'
  （pipeline 层呈现，此前只在 parser 层断言）
- **未知扩展名** → unsupported_type 消息含该扩展名
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_directory_input(tmp_path):
    doc, errors = process_single(
        tmp_path, write_json=False)
    assert doc is None
    assert len(errors) == 1
    e = errors[0]
    assert e.code == "file_not_found"
    assert str(tmp_path) in e.message


def test_no_extension(tmp_path):
    p = tmp_path / "noext"
    p.write_bytes(b"%PDF-1.4")
    doc, errors = process_single(
        p, write_json=False)
    assert doc is None
    (e,) = errors
    assert e.code == "unsupported_type"
    assert "(无)" in e.message


def test_unknown_extension(tmp_path):
    p = tmp_path / "x.xyz"
    p.write_bytes(b"data")
    doc, errors = process_single(
        p, write_json=False)
    assert doc is None
    (e,) = errors
    assert e.code == "unsupported_type"
    assert ".xyz" in e.message
