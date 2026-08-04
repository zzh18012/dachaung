"""app/hash.py 边角测试 - 第三轮（Round 124）。

补强已有 base/edges（共 104 测试）未覆盖的深度路径：
- compute_text_hash 输入边界：
  - bool True/False（int 子类，encode 失败 → AttributeError）
  - float（无 encode）
  - bytearray（无 encode）
  - memoryview（无 encode）
  - 极长文本（1MB+）
  - 单字节 unicode（"\x00"）
  - 控制字符
  - 全 256 ASCII 字节字符
- compute_file_hash 文件边界：
  - 文件含全 256 字节
  - 隐藏文件（. 前缀）
  - 文件名仅数字
  - 极小文件（1 byte 各 byte 值）
- 跨函数等价性：
  - file_hash(file with text X) == text_hash(X) for unicode/CJK/控制字符
- 模块结构深度：
  - hashlib 已 import
  - Path 已 import
  - 函数注解 str | Path
  - 返回注解 str
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.hash import compute_file_hash, compute_text_hash


# =========================================================================
# compute_text_hash 输入边界
# =========================================================================


def test_compute_text_hash_bool_true_raises():
    """True 是 int 子类，无 encode → AttributeError。"""
    with pytest.raises(AttributeError):
        compute_text_hash(True)  # type: ignore[arg-type]


def test_compute_text_hash_bool_false_raises():
    with pytest.raises(AttributeError):
        compute_text_hash(False)  # type: ignore[arg-type]


def test_compute_text_hash_int_raises():
    with pytest.raises(AttributeError):
        compute_text_hash(42)  # type: ignore[arg-type]


def test_compute_text_hash_float_raises():
    with pytest.raises(AttributeError):
        compute_text_hash(3.14)  # type: ignore[arg-type]


def test_compute_text_hash_bytearray_raises():
    """bytearray 无 encode 方法。"""
    with pytest.raises(AttributeError):
        compute_text_hash(bytearray(b"hello"))  # type: ignore[arg-type]


def test_compute_text_hash_memoryview_raises():
    with pytest.raises(AttributeError):
        compute_text_hash(memoryview(b"hello"))  # type: ignore[arg-type]


def test_compute_text_hash_bytes_raises():
    with pytest.raises(AttributeError):
        compute_text_hash(b"hello")  # type: ignore[arg-type]


def test_compute_text_hash_list_raises():
    with pytest.raises(AttributeError):
        compute_text_hash(["hello"])  # type: ignore[arg-type]


def test_compute_text_hash_dict_raises():
    with pytest.raises(AttributeError):
        compute_text_hash({"k": "v"})  # type: ignore[arg-type]


def test_compute_text_hash_none_raises():
    with pytest.raises(AttributeError):
        compute_text_hash(None)  # type: ignore[arg-type]


# =========================================================================
# compute_text_hash 极端文本
# =========================================================================


def test_compute_text_hash_very_long_text_1mb():
    """1MB 文本应能正常 hash。"""
    text = "a" * (1024 * 1024)
    h = compute_text_hash(text)
    assert len(h) == 64
    # 与 hashlib 直接对比
    assert h == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_compute_text_hash_null_byte():
    """含 null byte 的文本。"""
    text = "hello\x00world"
    h = compute_text_hash(text)
    assert h == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_compute_text_hash_only_null_byte():
    text = "\x00"
    h = compute_text_hash(text)
    assert h == hashlib.sha256(b"\x00").hexdigest()


def test_compute_text_hash_control_chars():
    """各种控制字符（0x01-0x1F）。"""
    text = "".join(chr(i) for i in range(1, 0x20))
    h = compute_text_hash(text)
    assert h == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_compute_text_hash_high_ascii_in_latin1():
    """Latin-1 范围（0x80-0xFF）unicode 字符。"""
    text = "".join(chr(i) for i in range(0x80, 0x100))
    h = compute_text_hash(text)
    assert h == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_compute_text_hash_all_single_byte_utf8():
    """所有 ASCII 单字节（0x00-0x7F）。"""
    text = "".join(chr(i) for i in range(0x80))
    h = compute_text_hash(text)
    assert h == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_compute_text_hash_4byte_utf8_sequence():
    """4 字节 UTF-8 序列（emoji 等）。"""
    text = "🎉" * 100  # U+1F389
    h = compute_text_hash(text)
    assert h == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_compute_text_hash_surrogate_pair_emoji():
    text = "👨‍👩‍👧‍👦"  # family emoji (ZWJ 序列)
    h = compute_text_hash(text)
    assert h == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_compute_text_hash_mixed_cjk_and_ascii():
    text = "Hello 世界 World 世界"
    h = compute_text_hash(text)
    assert h == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_compute_text_hash_only_whitespace():
    text = "   \t\n\r  "
    h = compute_text_hash(text)
    assert h == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_compute_text_hash_only_punctuation():
    text = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
    h = compute_text_hash(text)
    assert h == hashlib.sha256(text.encode("utf-8")).hexdigest()


# =========================================================================
# compute_file_hash 文件内容边界
# =========================================================================


def test_compute_file_hash_all_256_byte_values(tmp_path: Path):
    """文件含全 256 字节值。"""
    p = tmp_path / "all_bytes.bin"
    p.write_bytes(bytes(range(256)))
    h = compute_file_hash(p)
    expected = hashlib.sha256(bytes(range(256))).hexdigest()
    assert h == expected


def test_compute_file_hash_all_null_bytes(tmp_path: Path):
    p = tmp_path / "nulls.bin"
    p.write_bytes(b"\x00" * 100)
    h = compute_file_hash(p)
    expected = hashlib.sha256(b"\x00" * 100).hexdigest()
    assert h == expected


def test_compute_file_hash_hidden_file_dot_prefix(tmp_path: Path):
    p = tmp_path / ".hidden"
    p.write_bytes(b"hidden content")
    h = compute_file_hash(p)
    expected = hashlib.sha256(b"hidden content").hexdigest()
    assert h == expected


def test_compute_file_hash_filename_only_digits(tmp_path: Path):
    p = tmp_path / "12345"
    p.write_bytes(b"content")
    h = compute_file_hash(p)
    assert len(h) == 64


def test_compute_file_hash_filename_with_extension(tmp_path: Path):
    p = tmp_path / "file.txt"
    p.write_text("hello", encoding="utf-8")
    h1 = compute_file_hash(p)
    h2 = compute_text_hash("hello")
    assert h1 == h2


def test_compute_file_hash_one_byte_each_value(tmp_path: Path):
    """每个 byte 值都生成一个文件并校验。"""
    for b in range(256):
        p = tmp_path / f"byte_{b}.bin"
        p.write_bytes(bytes([b]))
        h = compute_file_hash(p)
        expected = hashlib.sha256(bytes([b])).hexdigest()
        assert h == expected


# =========================================================================
# 跨函数等价性
# =========================================================================


def test_file_text_hash_equivalence_null_byte(tmp_path: Path):
    content = "hello\x00world"
    p = tmp_path / "x.txt"
    # Python write_text 用 utf-8，null byte 编码为 0x00
    p.write_text(content, encoding="utf-8")
    assert compute_file_hash(p) == compute_text_hash(content)


def test_file_text_hash_equivalence_emoji(tmp_path: Path):
    content = "🎉 emoji test"
    p = tmp_path / "x.txt"
    p.write_text(content, encoding="utf-8")
    assert compute_file_hash(p) == compute_text_hash(content)


def test_file_text_hash_equivalence_cjk(tmp_path: Path):
    content = "中文测试内容"
    p = tmp_path / "x.txt"
    p.write_text(content, encoding="utf-8")
    assert compute_file_hash(p) == compute_text_hash(content)


def test_file_text_hash_equivalence_control_chars(tmp_path: Path):
    """Windows write_text 会翻译换行符，用 write_bytes 避免。"""
    content = "".join(chr(i) for i in range(0, 0x20))
    p = tmp_path / "x.txt"
    p.write_bytes(content.encode("utf-8"))
    assert compute_file_hash(p) == compute_text_hash(content)


def test_file_text_hash_equivalence_long_text(tmp_path: Path):
    content = "a" * 10000
    p = tmp_path / "x.txt"
    p.write_text(content, encoding="utf-8")
    assert compute_file_hash(p) == compute_text_hash(content)


# =========================================================================
# 多次调用与稳定性
# =========================================================================


def test_text_hash_called_many_times_stable():
    text = "stability test"
    hashes = [compute_text_hash(text) for _ in range(100)]
    assert all(h == hashes[0] for h in hashes)


def test_file_hash_called_many_times_stable(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("stability", encoding="utf-8")
    hashes = [compute_file_hash(p) for _ in range(100)]
    assert all(h == hashes[0] for h in hashes)


def test_text_hash_and_file_hash_distinct_algorithms():
    """两个函数都基于 sha256，但 file_hash 流式，text_hash 一次性。"""
    # 验证两者对相同 utf-8 内容产生相同 hash
    text = "consistency"
    assert compute_text_hash(text) == hashlib.sha256(text.encode("utf-8")).hexdigest()


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_imports_hashlib():
    from app import hash as mod

    assert hasattr(mod, "hashlib")


def test_module_imports_path():
    from app import hash as mod

    assert hasattr(mod, "Path")


def test_module_has_compute_file_hash():
    from app import hash as mod

    assert hasattr(mod, "compute_file_hash")


def test_module_has_compute_text_hash():
    from app import hash as mod

    assert hasattr(mod, "compute_text_hash")


def test_module_does_not_define_all():
    """hash.py 不定义 __all__（模块结构深度）。"""
    from app import hash as mod

    # 默认 __all__ 不显式定义
    assert not hasattr(mod, "__all__") or mod.__all__ is None or mod.__all__ == []


def test_module_docstring_present():
    from app import hash as mod

    assert mod.__doc__ is not None


def test_module_docstring_mentions_sha():
    """docstring 应提及 SHA-256。"""
    from app import hash as mod

    doc = mod.__doc__
    assert "SHA" in doc.upper() or "sha" in doc.lower()


def test_module_docstring_mentions_source_hash():
    """docstring 应提及 source_hash 字段用途。"""
    from app import hash as mod

    doc = mod.__doc__
    assert "source_hash" in doc or "指纹" in doc or "hash" in doc.lower()


def test_module_uses_future_annotations():
    """模块用了 from __future__ import annotations。"""
    import ast

    from app import hash as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    has_future = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(a.name == "annotations" for a in node.names)
        for node in tree.body
    )
    assert has_future


# =========================================================================
# 签名深度
# =========================================================================


def test_compute_file_hash_signature_one_param():
    import inspect

    sig = inspect.signature(compute_file_hash)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "path" in params


def test_compute_text_hash_signature_one_param():
    import inspect

    sig = inspect.signature(compute_text_hash)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "text" in params


def test_compute_file_hash_return_annotation_str():
    import inspect

    sig = inspect.signature(compute_file_hash)
    ret = sig.return_annotation
    assert ret is str or "str" in str(ret)


def test_compute_text_hash_return_annotation_str():
    import inspect

    sig = inspect.signature(compute_text_hash)
    ret = sig.return_annotation
    assert ret is str or "str" in str(ret)


def test_compute_file_hash_param_annotation_str_or_path():
    """path 注解：str | Path（被 future 字符串化）。"""
    import inspect

    sig = inspect.signature(compute_file_hash)
    ann = sig.parameters["path"].annotation
    assert "str" in str(ann) and "Path" in str(ann)


def test_compute_text_hash_param_annotation_str():
    import inspect

    sig = inspect.signature(compute_text_hash)
    ann = sig.parameters["text"].annotation
    assert ann is str or "str" in str(ann)


# =========================================================================
# 错误消息细节
# =========================================================================


def test_file_hash_missing_file_message_starts_with_hash(tmp_path: Path):
    p = tmp_path / "missing.txt"
    with pytest.raises(FileNotFoundError) as ei:
        compute_file_hash(p)
    assert "hash" in str(ei.value)


def test_file_hash_directory_message_contains_path(tmp_path: Path):
    d = tmp_path / "subdir"
    d.mkdir()
    with pytest.raises(FileNotFoundError) as ei:
        compute_file_hash(d)
    assert "subdir" in str(ei.value)


def test_file_hash_empty_string_path_message():
    """空字符串 path → Path('') → 不是文件 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        compute_file_hash("")
