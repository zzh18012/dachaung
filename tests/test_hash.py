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


# ---------- 边角补强（Round 48） ----------


# compute_text_hash 类型契约 & 边角


def test_text_hash_returns_str_type():
    """返回值类型是 str。"""
    h = compute_text_hash("x")
    assert isinstance(h, str)


def test_text_hash_returns_non_empty_string():
    """至少返回非空字符串。"""
    h = compute_text_hash("")
    assert len(h) > 0


def test_text_hash_known_value_for_known_input():
    """已知输入 → 已知 SHA256，防止 hash 算法被悄悄换掉。"""
    # "abc" 的 SHA256 是固定的（公开已知值）
    expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert compute_text_hash("abc") == expected


def test_text_hash_empty_string_known_value():
    """空字符串 SHA256 已知值。"""
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert compute_text_hash("") == expected


def test_text_hash_order_matters():
    """字符顺序敏感："abc" != "bca"。"""
    assert compute_text_hash("abc") != compute_text_hash("bca")


def test_text_hash_case_sensitive():
    """大小写敏感："ABC" != "abc"。"""
    assert compute_text_hash("ABC") != compute_text_hash("abc")


def test_text_hash_handles_long_string():
    """1MB 字符串也应稳定（不崩）。"""
    s = "x" * (1024 * 1024)
    h1 = compute_text_hash(s)
    h2 = compute_text_hash(s)
    assert h1 == h2
    assert len(h1) == 64


def test_text_hash_newline_variants_distinct():
    """不同换行符应得到不同 hash。"""
    assert compute_text_hash("a\nb") != compute_text_hash("a\r\nb")
    assert compute_text_hash("a\nb") != compute_text_hash("a\rb")


def test_text_hash_handles_4byte_utf8_sequence():
    """4-byte UTF-8（emoji）正确编码。"""
    s = "🎉" * 100
    h = compute_text_hash(s)
    assert h == hashlib.sha256(s.encode("utf-8")).hexdigest()


def test_text_hash_pure_ascii_matches_bytes():
    """纯 ASCII 时，text_hash == sha256(str.encode('utf-8')) == sha256(bytes)。"""
    s = "Hello, World!"
    h = compute_text_hash(s)
    direct = hashlib.sha256(s.encode("ascii")).hexdigest()
    assert h == direct


# compute_file_hash 类型契约 & 边角


def test_file_hash_returns_str_type(tmp_path: Path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"data")
    assert isinstance(compute_file_hash(p), str)


def test_file_hash_returns_non_empty_string(tmp_path: Path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"data")
    h = compute_file_hash(p)
    assert len(h) > 0


def test_file_hash_no_underscores_or_dashes(tmp_path: Path):
    """hex 摘要应仅含 0-9a-f，无 _ 或 -。"""
    p = tmp_path / "x.bin"
    p.write_bytes(b"check-format")
    h = compute_file_hash(p)
    for c in h:
        assert c in "0123456789abcdef"


def test_file_hash_32kb_half_chunk(tmp_path: Path):
    """32KB（半个 chunk）边界。"""
    content = b"B" * (32 * 1024)
    p = tmp_path / "32k.bin"
    p.write_bytes(content)
    assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()


def test_file_hash_128kb_two_full_chunks(tmp_path: Path):
    """128KB = 2 个完整 64KB chunk。"""
    content = b"C" * (128 * 1024)
    p = tmp_path / "128k.bin"
    p.write_bytes(content)
    assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()


def test_file_hash_192kb_three_full_chunks(tmp_path: Path):
    """192KB = 3 个完整 chunk，验证 chunk 拼接。"""
    content = b"D" * (192 * 1024)
    p = tmp_path / "192k.bin"
    p.write_bytes(content)
    assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()


def test_file_hash_random_bytes(tmp_path: Path):
    """随机二进制内容（非重复模式）。"""
    import os
    content = os.urandom(70000)  # 略超过一个 chunk
    p = tmp_path / "random.bin"
    p.write_bytes(content)
    assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()


def test_file_hash_filename_with_spaces(tmp_path: Path):
    """文件名含空格也应能读。"""
    p = tmp_path / "my file.bin"
    p.write_bytes(b"content with spaces file")
    assert compute_file_hash(p) == hashlib.sha256(b"content with spaces file").hexdigest()


def test_file_hash_filename_with_unicode(tmp_path: Path):
    """文件名含 Unicode（CJK）也应能读。"""
    p = tmp_path / "数据.bin"
    p.write_bytes(b"unicode name")
    assert compute_file_hash(p) == hashlib.sha256(b"unicode name").hexdigest()


def test_file_hash_content_with_only_whitespace(tmp_path: Path):
    """内容全是空白字节也应正确。"""
    p = tmp_path / "ws.bin"
    p.write_bytes(b"   \t\n  \r\n ")
    expected = hashlib.sha256(b"   \t\n  \r\n ").hexdigest()
    assert compute_file_hash(p) == expected


def test_file_hash_content_modified_changes_hash(tmp_path: Path):
    """文件被修改后 hash 必须改变。"""
    p = tmp_path / "mutable.bin"
    p.write_bytes(b"original")
    h1 = compute_file_hash(p)
    p.write_bytes(b"modified")
    h2 = compute_file_hash(p)
    assert h1 != h2


def test_file_hash_cross_function_consistency_with_text_hash(tmp_path: Path):
    """同字节内容：file_hash(bytes) == text_hash(decoded as latin-1 不一定等)。
    但 file_hash(bytes) == hashlib.sha256(bytes).hexdigest() 这条不变。
    另外，对于纯 ASCII 文件内容（用 binary 写避免 CRLF 转换），file_hash == text_hash(ascii_content)。"""
    ascii_content = "Hello, World!\nThis is a test.\n"
    p = tmp_path / "text.txt"
    # 用 binary 写避免 Windows text mode 的 \n → \r\n 转换
    p.write_bytes(ascii_content.encode("utf-8"))
    # 文件 hash 应与等价文本 hash 一致（UTF-8 编码下 ASCII == 字节）
    assert compute_file_hash(p) == compute_text_hash(ascii_content)


def test_file_hash_error_message_contains_path(tmp_path: Path):
    """FileNotFoundError 消息含路径字符串。"""
    missing = tmp_path / "nope.bin"
    with pytest.raises(FileNotFoundError) as exc:
        compute_file_hash(missing)
    assert "nope.bin" in str(exc.value)


def test_file_hash_empty_path_string_raises():
    """空字符串路径 → FileNotFoundError（'.' 不是文件）。"""
    with pytest.raises(FileNotFoundError):
        compute_file_hash("")


def test_file_hash_current_directory_raises(tmp_path: Path):
    """传 '.' （当前目录）→ 不是文件 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        compute_file_hash(tmp_path)
    with pytest.raises(FileNotFoundError):
        compute_file_hash(".")


def test_file_hash_stable_across_multiple_runs(tmp_path: Path):
    """同一文件多次读取结果一致（无随机性）。"""
    p = tmp_path / "x.bin"
    p.write_bytes(b"stability-check")
    results = [compute_file_hash(p) for _ in range(5)]
    assert all(r == results[0] for r in results)


def test_file_hash_no_leading_trailing_whitespace(tmp_path: Path):
    """hex 输出无前后空白。"""
    p = tmp_path / "x.bin"
    p.write_bytes(b"data")
    h = compute_file_hash(p)
    assert h == h.strip()
    assert not h.startswith("\n") and not h.endswith("\n")


def test_file_hash_path_with_trailing_slash_normalization(tmp_path: Path):
    """Path 自动规范化：path/child vs path/child/ 应等价。"""
    p = tmp_path / "file.bin"
    p.write_bytes(b"x")
    # 直接路径
    h1 = compute_file_hash(p)
    # str 路径
    h2 = compute_file_hash(str(p))
    assert h1 == h2


def test_text_hash_zero_length_returns_known_value():
    """零长度文本与已知空 SHA256 一致（与空文件 hash 也一致）。"""
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert compute_text_hash("") == expected


def test_text_hash_single_char_returns_known_value():
    """单字符 "a" 的 SHA256 已知值（公开标准）。"""
    expected = "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb"
    assert compute_text_hash("a") == expected


def test_text_hash_two_chars_distinct_from_one():
    """追加字符后 hash 必须改变。"""
    one = compute_text_hash("a")
    two = compute_text_hash("aa")
    assert one != two


def test_text_hash_concat_invariant():
    """hash(a) != hash(a+b)，hash 不满足 concat 不变量（验证不是xor 之类）。"""
    a = compute_text_hash("hello")
    b = compute_text_hash("world")
    c = compute_text_hash("helloworld")
    # SHA-256 不是 concat 可组合的
    assert c != a
    assert c != b


def test_file_hash_64kb_minus_one(tmp_path: Path):
    """64KB - 1 字节边界。"""
    content = b"E" * (65536 - 1)
    p = tmp_path / "64k_minus_1.bin"
    p.write_bytes(content)
    assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()


def test_file_hash_two_consecutive_files_independent(tmp_path: Path):
    """连续 hash 两个不同文件，结果应独立（无状态泄漏）。"""
    p1 = tmp_path / "a.bin"
    p1.write_bytes(b"first-file-content")
    p2 = tmp_path / "b.bin"
    p2.write_bytes(b"second-file-content")
    h1 = compute_file_hash(p1)
    h2 = compute_file_hash(p2)
    h1_again = compute_file_hash(p1)
    assert h1 == h1_again
    assert h1 != h2
