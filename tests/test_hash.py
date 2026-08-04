"""app/hash.py 的单元测试：compute_file_hash / compute_text_hash。"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.hash import compute_file_hash, compute_text_hash


# 已知的 SHA256 空值（用于一致性检查）
SHA256_EMPTY = hashlib.sha256(b"").hexdigest()


# ---------- compute_text_hash ----------


def test_text_hash_empty_string():
    assert compute_text_hash("") == SHA256_EMPTY


def test_text_hash_basic_string_matches_hashlib():
    s = "hello world"
    assert compute_text_hash(s) == hashlib.sha256(s.encode("utf-8")).hexdigest()


def test_text_hash_unicode_utf8_encoded():
    """非 ASCII 字符串应按 UTF-8 编码后 hash。"""
    s = "你好，世界"
    assert compute_text_hash(s) == hashlib.sha256("你好，世界".encode("utf-8")).hexdigest()


def test_text_hash_returns_lowercase_hex_64_chars():
    h = compute_text_hash("x")
    assert len(h) == 64
    assert h == h.lower()
    assert all(c in "0123456789abcdef" for c in h)


def test_text_hash_deterministic_same_input():
    assert compute_text_hash("abc") == compute_text_hash("abc")


def test_text_hash_different_inputs_different_output():
    assert compute_text_hash("abc") != compute_text_hash("abd")


def test_text_hash_whitespace_significant():
    """空白字符也要进入 hash。"""
    assert compute_text_hash("a b") != compute_text_hash("a  b")
    assert compute_text_hash("a") != compute_text_hash("a\n")


def test_text_hash_handles_emoji():
    """4-byte UTF-8 字符（emoji）也不应崩溃。"""
    s = "test🎉emoji"
    assert compute_text_hash(s) == hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------- compute_file_hash ----------


def test_file_hash_empty_file(tmp_path: Path):
    p = tmp_path / "empty.bin"
    p.write_bytes(b"")
    assert compute_file_hash(p) == SHA256_EMPTY


def test_file_hash_small_file_matches_hashlib(tmp_path: Path):
    content = b"hello world"
    p = tmp_path / "small.bin"
    p.write_bytes(content)
    assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()


def test_file_hash_large_file_streaming(tmp_path: Path):
    """超过 64KB 的文件也要正确 hash（验证流式分块拼接）。"""
    # 200 KB = 3+ chunks
    content = b"A" * (200 * 1024)
    p = tmp_path / "large.bin"
    p.write_bytes(content)
    assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()


def test_file_hash_binary_with_null_and_high_bytes(tmp_path: Path):
    """任意二进制内容（含 \\x00、高位字节）也应正确。"""
    content = bytes(range(256)) * 4
    p = tmp_path / "binary.bin"
    p.write_bytes(content)
    assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()


def test_file_hash_str_path_accepted(tmp_path: Path):
    """str 路径也可以。"""
    p = tmp_path / "str.bin"
    p.write_bytes(b"x")
    h = compute_file_hash(str(p))
    assert h == hashlib.sha256(b"x").hexdigest()


def test_file_hash_path_object_accepted(tmp_path: Path):
    p = tmp_path / "obj.bin"
    p.write_bytes(b"y")
    h = compute_file_hash(p)
    assert h == hashlib.sha256(b"y").hexdigest()


def test_file_hash_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError) as exc:
        compute_file_hash(tmp_path / "nope.bin")
    assert "hash" in str(exc.value).lower() or "文件" in str(exc.value)


def test_file_hash_directory_raises(tmp_path: Path):
    """传目录 → 不是 is_file → FileNotFoundError。"""
    sub = tmp_path / "subdir"
    sub.mkdir()
    with pytest.raises(FileNotFoundError):
        compute_file_hash(sub)


def test_file_hash_returns_lowercase_hex_64_chars(tmp_path: Path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"data")
    h = compute_file_hash(p)
    assert len(h) == 64
    assert h == h.lower()
    assert all(c in "0123456789abcdef" for c in h)


def test_file_hash_deterministic(tmp_path: Path):
    """同一文件两次 hash 应相等。"""
    p = tmp_path / "x.bin"
    p.write_bytes(b"same content")
    assert compute_file_hash(p) == compute_file_hash(p)


def test_file_hash_different_files_different_hash(tmp_path: Path):
    p1 = tmp_path / "a.bin"
    p1.write_bytes(b"aaa")
    p2 = tmp_path / "b.bin"
    p2.write_bytes(b"bbb")
    assert compute_file_hash(p1) != compute_file_hash(p2)


def test_file_hash_chunk_boundary_exact_64kb(tmp_path: Path):
    """恰好 64KB（chunk size 边界）也应正确。"""
    content = b"\xff" * 65536
    p = tmp_path / "exactly_64k.bin"
    p.write_bytes(content)
    assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()


def test_file_hash_chunk_boundary_64kb_plus_one(tmp_path: Path):
    """64KB + 1 byte（跨 chunk）也应正确。"""
    content = b"\xff" * 65537
    p = tmp_path / "64k_plus_1.bin"
    p.write_bytes(content)
    assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()
