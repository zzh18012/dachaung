r"""app/hash.py 边角测试 - 第三轮（Round 143）。

补强已有 base/edges/edges2（共 157 测试）未覆盖的深度：
- compute_file_hash: 大文件流式读取、空文件、二进制、Unicode 文件
- compute_file_hash: 文件不存在错误细节
- compute_text_hash: 不同输入产生不同 hash、相同输入产生相同 hash
- SHA-256 标准向量（NIST 测试向量）
- hexdigest 格式（64 字符小写 hex）
- 模块结构与签名
"""

from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

import pytest

from app.hash import compute_file_hash, compute_text_hash


# =========================================================================
# SHA-256 NIST 标准测试向量
# =========================================================================


def test_text_hash_empty_string_nist():
    """SHA-256("") = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"""
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert compute_text_hash("") == expected


def test_text_hash_single_char_nist():
    """SHA-256("a") = ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb"""
    expected = "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb"
    assert compute_text_hash("a") == expected


def test_text_hash_abc_nist():
    """SHA-256("abc") = ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"""
    expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert compute_text_hash("abc") == expected


def test_text_hash_longer_test_vector():
    """NIST 长测试向量。"""
    msg = "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"
    expected = "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"
    assert compute_text_hash(msg) == expected


def test_text_hash_matches_hashlib_directly():
    """compute_text_hash 与 hashlib.sha256().hexdigest() 完全一致。"""
    text = "any text content"
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert compute_text_hash(text) == expected


# =========================================================================
# hexdigest 格式
# =========================================================================


def test_text_hash_returns_str():
    assert isinstance(compute_text_hash("x"), str)


def test_text_hash_length_64():
    assert len(compute_text_hash("x")) == 64


def test_text_hash_lowercase_hex():
    """返回小写 hex。"""
    h = compute_text_hash("x")
    assert h == h.lower()
    assert all(c in "0123456789abcdef" for c in h)


# =========================================================================
# compute_text_hash 不变量
# =========================================================================


def test_text_hash_same_input_same_output():
    assert compute_text_hash("hello") == compute_text_hash("hello")


def test_text_hash_different_input_different_output():
    assert compute_text_hash("hello") != compute_text_hash("world")


def test_text_hash_unicode_input():
    """Unicode 字符按 UTF-8 编码后 hash。"""
    direct = hashlib.sha256("中文".encode("utf-8")).hexdigest()
    assert compute_text_hash("中文") == direct


def test_text_hash_whitespace_only():
    h = compute_text_hash("   ")
    assert isinstance(h, str)
    assert len(h) == 64


def test_text_hash_long_text():
    """长文本不崩溃。"""
    text = "x" * 100000
    h = compute_text_hash(text)
    assert len(h) == 64


def test_text_hash_newline_text():
    h = compute_text_hash("line1\nline2\n")
    direct = hashlib.sha256("line1\nline2\n".encode("utf-8")).hexdigest()
    assert h == direct


# =========================================================================
# compute_file_hash 深度
# =========================================================================


def test_file_hash_str_path(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    h = compute_file_hash(str(p))
    assert isinstance(h, str)
    assert len(h) == 64


def test_file_hash_path_object(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    h = compute_file_hash(p)
    assert isinstance(h, str)


def test_file_hash_matches_text_hash(tmp_path: Path):
    """文件内容 = compute_text_hash(文件内容)。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    assert compute_file_hash(p) == compute_text_hash("hello")


def test_file_hash_empty_file(tmp_path: Path):
    p = tmp_path / "empty.bin"
    p.write_bytes(b"")
    # SHA-256("") 标准
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert compute_file_hash(p) == expected


def test_file_hash_single_byte(tmp_path: Path):
    p = tmp_path / "x.bin"
    p.write_bytes(b"a")
    expected = "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb"
    assert compute_file_hash(p) == expected


def test_file_hash_binary_content(tmp_path: Path):
    """二进制内容也能 hash。"""
    p = tmp_path / "x.bin"
    p.write_bytes(bytes(range(256)))
    direct = hashlib.sha256(bytes(range(256))).hexdigest()
    assert compute_file_hash(p) == direct


def test_file_hash_unicode_content(tmp_path: Path):
    """UTF-8 编码的 Unicode 内容。"""
    p = tmp_path / "x.txt"
    p.write_text("中文测试", encoding="utf-8")
    direct = hashlib.sha256("中文测试".encode("utf-8")).hexdigest()
    assert compute_file_hash(p) == direct


def test_file_hash_large_file_streaming(tmp_path: Path):
    """大文件流式读取（超过 65536 buffer）。"""
    p = tmp_path / "big.bin"
    p.write_bytes(b"x" * 200000)  # 200KB > 64KB buffer
    h = compute_file_hash(p)
    direct = hashlib.sha256(b"x" * 200000).hexdigest()
    assert h == direct


def test_file_hash_same_content_same_hash(tmp_path: Path):
    p1 = tmp_path / "a.txt"
    p2 = tmp_path / "b.txt"
    p1.write_text("same", encoding="utf-8")
    p2.write_text("same", encoding="utf-8")
    assert compute_file_hash(p1) == compute_file_hash(p2)


def test_file_hash_different_content_different_hash(tmp_path: Path):
    p1 = tmp_path / "a.txt"
    p2 = tmp_path / "b.txt"
    p1.write_text("foo", encoding="utf-8")
    p2.write_text("bar", encoding="utf-8")
    assert compute_file_hash(p1) != compute_file_hash(p2)


def test_file_hash_returns_lowercase_hex(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    h = compute_file_hash(p)
    assert h == h.lower()


# =========================================================================
# compute_file_hash 错误路径
# =========================================================================


def test_file_hash_missing_file_raises(tmp_path: Path):
    missing = tmp_path / "missing"
    with pytest.raises(FileNotFoundError):
        compute_file_hash(missing)


def test_file_hash_missing_file_error_message(tmp_path: Path):
    missing = tmp_path / "missing"
    with pytest.raises(FileNotFoundError) as exc:
        compute_file_hash(missing)
    assert "不是文件" in str(exc.value) or "not a file" in str(exc.value).lower()


def test_file_hash_directory_not_file(tmp_path: Path):
    """传入目录 → 不是文件 → FileNotFoundError。"""
    sub = tmp_path / "subdir"
    sub.mkdir()
    with pytest.raises(FileNotFoundError):
        compute_file_hash(sub)


def test_file_hash_missing_str_path_raises(tmp_path: Path):
    missing = str(tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        compute_file_hash(missing)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_imports_hashlib():
    import app.hash as mod
    src = inspect.getsource(mod)
    assert "import hashlib" in src


def test_module_imports_path():
    import app.hash as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_uses_future_annotations():
    import app.hash as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import app.hash as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_sha():
    import app.hash as mod
    assert "SHA-256" in mod.__doc__ or "sha256" in mod.__doc__.lower()


# =========================================================================
# 签名
# =========================================================================


def test_compute_file_hash_signature_one_param():
    sig = inspect.signature(compute_file_hash)
    assert len(sig.parameters) == 1


def test_compute_file_hash_path_param_name():
    sig = inspect.signature(compute_file_hash)
    assert "path" in sig.parameters


def test_compute_file_hash_no_default():
    sig = inspect.signature(compute_file_hash)
    assert sig.parameters["path"].default is inspect.Parameter.empty


def test_compute_file_hash_return_annotation_str():
    sig = inspect.signature(compute_file_hash)
    assert sig.return_annotation in (str, "str")


def test_compute_text_hash_signature_one_param():
    sig = inspect.signature(compute_text_hash)
    assert len(sig.parameters) == 1


def test_compute_text_hash_text_param_name():
    sig = inspect.signature(compute_text_hash)
    assert "text" in sig.parameters


def test_compute_text_hash_no_default():
    sig = inspect.signature(compute_text_hash)
    assert sig.parameters["text"].default is inspect.Parameter.empty


def test_compute_text_hash_return_annotation_str():
    sig = inspect.signature(compute_text_hash)
    assert sig.return_annotation in (str, "str")


# =========================================================================
# 综合：跨函数一致性
# =========================================================================


def test_file_hash_equals_hashlib_sha256_file(tmp_path: Path):
    """compute_file_hash == hashlib.sha256(file_content).hexdigest()。"""
    p = tmp_path / "x.txt"
    content = b"hello world"
    p.write_bytes(content)
    direct = hashlib.sha256(content).hexdigest()
    assert compute_file_hash(p) == direct


def test_file_hash_stable_across_calls(tmp_path: Path):
    """多次调用结果一致。"""
    p = tmp_path / "x.txt"
    p.write_text("stable", encoding="utf-8")
    h1 = compute_file_hash(p)
    h2 = compute_file_hash(p)
    h3 = compute_file_hash(p)
    assert h1 == h2 == h3


def test_text_hash_stable_across_calls():
    h1 = compute_text_hash("stable")
    h2 = compute_text_hash("stable")
    h3 = compute_text_hash("stable")
    assert h1 == h2 == h3
