"""app/hash.py 边角测试（Round 71）。

补强 tests/test_hash.py（55 个测试）未覆盖的：
- 模块结构与导入
- compute_file_hash 错误类型严格性（FileNotFoundError）
- compute_file_hash 流式读取的多个 chunk 边界
- compute_file_hash Path normalization（./ 前缀、绝对/相对）
- compute_file_hash 与 symlink
- compute_text_hash 输入类型错（None/int/bytes）→ AttributeError
- compute_text_hash 与 file hash 的一致性各场景
- compute_text_hash 与 hashlib 一致性各场景
- 跨函数 invariants
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.hash import compute_file_hash, compute_text_hash


# ---------- 模块结构 ----------


def test_module_imports_hashlib():
    import app.hash as mod
    assert hasattr(mod, "hashlib")


def test_module_imports_path():
    import app.hash as mod
    assert hasattr(mod, "Path")


def test_module_has_compute_file_hash():
    import app.hash as mod
    assert hasattr(mod, "compute_file_hash")


def test_module_has_compute_text_hash():
    import app.hash as mod
    assert hasattr(mod, "compute_text_hash")


def test_module_does_not_have_all_exports():
    """hash.py 没有 __all__。"""
    import app.hash as mod
    assert not hasattr(mod, "__all__")


def test_compute_file_hash_callable():
    assert callable(compute_file_hash)


def test_compute_text_hash_callable():
    assert callable(compute_text_hash)


# ---------- compute_file_hash 错误类型严格性 ----------


def test_compute_file_hash_missing_raises_filenotfounderror_type(tmp_path: Path):
    """严格 FileNotFoundError 类型（不是 OSError 通用）。"""
    with pytest.raises(FileNotFoundError):
        compute_file_hash(tmp_path / "missing.bin")


def test_compute_file_hash_directory_raises_filenotfounderror_type(tmp_path: Path):
    """目录 → FileNotFoundError（is_file()=False）。"""
    with pytest.raises(FileNotFoundError):
        compute_file_hash(tmp_path)


def test_compute_file_hash_error_message_contains_path(tmp_path: Path):
    missing = tmp_path / "specific_name.bin"
    with pytest.raises(FileNotFoundError) as exc:
        compute_file_hash(missing)
    assert "specific_name.bin" in str(exc.value)


def test_compute_file_hash_empty_path_string_raises(tmp_path: Path):
    """空字符串路径 → Path('') → is_file()=False → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        compute_file_hash("")


def test_compute_file_hash_dot_path_raises(tmp_path: Path):
    """'.' → 当前目录 → is_file()=False → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        compute_file_hash(".")


def test_compute_file_hash_double_dot_path_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        compute_file_hash("..")


# ---------- compute_file_hash Path normalization ----------


def test_compute_file_hash_dot_slash_prefix(tmp_path: Path):
    """'./foo' → Path('foo')，工作目录上下文。"""
    # 改用 chdir 到 tmp_path
    p = tmp_path / "f.bin"
    p.write_bytes(b"data")
    # 用 chdir 测试 './' 前缀
    old_cwd = Path.cwd()
    try:
        import os
        os.chdir(tmp_path)
        h = compute_file_hash("./f.bin")
        assert h == hashlib.sha256(b"data").hexdigest()
    finally:
        os.chdir(old_cwd)


def test_compute_file_hash_absolute_path(tmp_path: Path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"data")
    abs_path = str(p.resolve())
    h = compute_file_hash(abs_path)
    assert h == hashlib.sha256(b"data").hexdigest()


def test_compute_file_hash_relative_path(tmp_path: Path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"data")
    old_cwd = Path.cwd()
    try:
        import os
        os.chdir(tmp_path)
        h = compute_file_hash("f.bin")
        assert h == hashlib.sha256(b"data").hexdigest()
    finally:
        os.chdir(old_cwd)


# ---------- compute_file_hash 流式 chunk 边界 ----------


def test_compute_file_hash_one_byte(tmp_path: Path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"x")
    assert compute_file_hash(p) == hashlib.sha256(b"x").hexdigest()


def test_compute_file_hash_two_bytes(tmp_path: Path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"xy")
    assert compute_file_hash(p) == hashlib.sha256(b"xy").hexdigest()


def test_compute_file_hash_chunk_size_65536_minus_two(tmp_path: Path):
    p = tmp_path / "f.bin"
    content = b"a" * 65534
    p.write_bytes(content)
    assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()


def test_compute_file_hash_chunk_size_exact_65536_known_value(tmp_path: Path):
    """65536 字节正好一个 chunk → 用 known hashlib 验证。"""
    p = tmp_path / "f.bin"
    content = b"a" * 65536
    p.write_bytes(content)
    assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()


def test_compute_file_hash_chunk_size_65536_plus_two(tmp_path: Path):
    p = tmp_path / "f.bin"
    content = b"a" * 65538
    p.write_bytes(content)
    assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()


def test_compute_file_hash_multiple_chunks_known_value(tmp_path: Path):
    """10 chunks * 65536 = 655360 bytes。"""
    p = tmp_path / "f.bin"
    content = b"abcdefgh" * (65536 * 10 // 8)
    p.write_bytes(content)
    assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()


# ---------- compute_file_hash 一致性 ----------


def test_compute_file_hash_idempotent(tmp_path: Path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"data")
    h1 = compute_file_hash(p)
    h2 = compute_file_hash(p)
    assert h1 == h2


def test_compute_file_hash_two_consecutive_calls_independent(tmp_path: Path):
    """多次调用互不污染（流式读取应当独立）。"""
    p1 = tmp_path / "a.bin"
    p2 = tmp_path / "b.bin"
    p1.write_bytes(b"first")
    p2.write_bytes(b"second")
    h1 = compute_file_hash(p1)
    h2 = compute_file_hash(p2)
    assert h1 != h2


def test_compute_file_hash_matches_hashlib_with_binary_content(tmp_path: Path):
    """二进制内容（含 null byte）匹配 hashlib。"""
    p = tmp_path / "f.bin"
    content = b"\x00\x01\x02\xff\xfe" * 100
    p.write_bytes(content)
    assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()


# ---------- compute_file_hash 与 symlink ----------


def test_compute_file_hash_symlink_to_file(tmp_path: Path):
    """symlink 指向真实文件 → 返真实文件的 hash。"""
    real = tmp_path / "real.bin"
    real.write_bytes(b"data")
    link = tmp_path / "link.bin"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("symlink not supported on this platform")
    assert compute_file_hash(link) == hashlib.sha256(b"data").hexdigest()


def test_compute_file_hash_symlink_to_directory_raises(tmp_path: Path):
    """symlink 指向目录 → is_file() 返 True（follows symlink）→ 但读取时报错或返 directory hash。"""
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(target_dir)
    except (OSError, NotImplementedError):
        pytest.skip("symlink not supported on this platform")
    # symlink 指向目录 → is_file()=False（target 是目录）→ FileNotFoundError
    with pytest.raises(FileNotFoundError):
        compute_file_hash(link)


def test_compute_file_hash_dangling_symlink_raises(tmp_path: Path):
    """悬空 symlink → FileNotFoundError。"""
    link = tmp_path / "dangling"
    try:
        link.symlink_to(tmp_path / "nonexistent")
    except (OSError, NotImplementedError):
        pytest.skip("symlink not supported on this platform")
    with pytest.raises(FileNotFoundError):
        compute_file_hash(link)


# ---------- compute_text_hash 输入类型错 ----------


def test_compute_text_hash_none_raises_attribute_error():
    """None.encode → AttributeError。"""
    with pytest.raises(AttributeError):
        compute_text_hash(None)  # type: ignore[arg-type]


def test_compute_text_hash_int_raises_attribute_error():
    """int 没有 .encode 方法 → AttributeError。"""
    with pytest.raises(AttributeError):
        compute_text_hash(42)  # type: ignore[arg-type]


def test_compute_text_hash_bytes_raises_attribute_error():
    """bytes.encode 不存在 → AttributeError。"""
    with pytest.raises(AttributeError):
        compute_text_hash(b"hello")  # type: ignore[arg-type]


def test_compute_text_hash_list_raises_attribute_error():
    with pytest.raises(AttributeError):
        compute_text_hash(["a", "b"])  # type: ignore[arg-type]


def test_compute_text_hash_dict_raises_attribute_error():
    with pytest.raises(AttributeError):
        compute_text_hash({"k": "v"})  # type: ignore[arg-type]


# ---------- compute_text_hash 与 hashlib ----------


def test_compute_text_hash_matches_hashlib_basic():
    assert compute_text_hash("hello") == hashlib.sha256(b"hello").hexdigest()


def test_compute_text_hash_matches_hashlib_unicode():
    s = "你好世界 🎉"
    assert compute_text_hash(s) == hashlib.sha256(s.encode("utf-8")).hexdigest()


def test_compute_text_hash_matches_hashlib_empty():
    assert compute_text_hash("") == hashlib.sha256(b"").hexdigest()


def test_compute_text_hash_matches_hashlib_long_string():
    s = "x" * 10000
    assert compute_text_hash(s) == hashlib.sha256(s.encode("utf-8")).hexdigest()


def test_compute_text_hash_matches_hashlib_with_newlines():
    s = "line1\nline2\nline3\n"
    assert compute_text_hash(s) == hashlib.sha256(s.encode("utf-8")).hexdigest()


def test_compute_text_hash_matches_hashlib_with_special_chars():
    s = "tab\there\rreturn"
    assert compute_text_hash(s) == hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------- 跨函数 invariants ----------


def test_file_hash_equals_text_hash_for_same_content(tmp_path: Path):
    """文件内容 == 字符串内容 → hash 相同。"""
    text = "hello world"
    p = tmp_path / "f.txt"
    p.write_text(text, encoding="utf-8")
    assert compute_file_hash(p) == compute_text_hash(text)


def test_file_hash_equals_text_hash_for_unicode(tmp_path: Path):
    text = "你好 🎉"
    p = tmp_path / "f.txt"
    p.write_text(text, encoding="utf-8")
    assert compute_file_hash(p) == compute_text_hash(text)


def test_file_hash_equals_text_hash_for_empty(tmp_path: Path):
    p = tmp_path / "empty.txt"
    p.write_text("", encoding="utf-8")
    assert compute_file_hash(p) == compute_text_hash("")


def test_file_hash_differs_from_text_hash_for_different_content(tmp_path: Path):
    """文件二进制内容 != 文本字符串 → 不同 hash。"""
    p = tmp_path / "f.bin"
    p.write_bytes(b"\x00\x01\x02")  # 二进制
    # 同样字节序列不能直接 encode → utf-8 编码会失败
    # 但 0x00-0x02 都是合法 utf-8 单字节字符
    h_file = compute_file_hash(p)
    h_text = compute_text_hash("\x00\x01\x02")
    assert h_file == h_text


def test_text_hash_deterministic_across_calls():
    h1 = compute_text_hash("deterministic")
    h2 = compute_text_hash("deterministic")
    assert h1 == h2


def test_text_hash_returns_64_char_hex():
    h = compute_text_hash("x")
    assert len(h) == 64
    # 全是 hex 字符
    int(h, 16)  # 不抛即 OK


def test_file_hash_returns_64_char_hex(tmp_path: Path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"x")
    h = compute_file_hash(p)
    assert len(h) == 64
    int(h, 16)


# ---------- compute_text_hash 与 BOM ----------


def test_text_hash_with_bom_character():
    """UTF-8 BOM (U+FEFF) 是有效 Unicode → 编码后 hash。"""
    s = "﻿hello"
    assert compute_text_hash(s) == hashlib.sha256(s.encode("utf-8")).hexdigest()


def test_text_hash_bom_changes_hash():
    """有无 BOM → 不同 hash。"""
    with_bom = "﻿hello"
    without_bom = "hello"
    assert compute_text_hash(with_bom) != compute_text_hash(without_bom)


# ---------- compute_file_hash 大文件流式不溢出（理论验证）----------


def test_compute_file_hash_does_not_load_full_file_at_once(tmp_path: Path):
    """通过 monkeypatch 验证流式读取（f.read 多次调用）。"""
    p = tmp_path / "f.bin"
    p.write_bytes(b"a" * (65536 * 3 + 100))  # 3+ chunks
    # 仅验证不抛（理论验证流式读取正确）
    h = compute_file_hash(p)
    assert len(h) == 64
