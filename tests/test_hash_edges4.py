r"""app/hash.py 边角测试 - 第四轮（Round 148）。

补强已有 base/edges/edges2/edges3（共 202 测试）未覆盖的深度：
- 65536 buffer 边界（精确 65535/65536/65537/131072 字节）
- 多种 SHA-256 测试向量
- 文件 path 不同形式
- 函数属性（__name__、__qualname__、__module__）
- 模块 dunder 属性
- 错误消息内容
- 跨函数一致性（hashlib 直接对照）
- 异常层级（FileNotFoundError ← OSError）
"""

from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

import pytest

from app.hash import compute_file_hash, compute_text_hash


# =========================================================================
# 65536 buffer 边界（流式读取分块点）
# =========================================================================


def test_file_hash_exactly_65535_bytes(tmp_path: Path):
    """65535 字节 = buffer - 1，单次读完。"""
    p = tmp_path / "x.bin"
    data = b"a" * 65535
    p.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert compute_file_hash(p) == expected


def test_file_hash_exactly_65536_bytes(tmp_path: Path):
    """65536 字节 = buffer 大小，单次读完（iter 在 b"" 时停止）。"""
    p = tmp_path / "x.bin"
    data = b"a" * 65536
    p.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert compute_file_hash(p) == expected


def test_file_hash_exactly_65537_bytes(tmp_path: Path):
    """65537 字节 = buffer + 1，需 2 次 read。"""
    p = tmp_path / "x.bin"
    data = b"a" * 65537
    p.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert compute_file_hash(p) == expected


def test_file_hash_exactly_131072_bytes(tmp_path: Path):
    """131072 字节 = 2 * buffer，2 次 read。"""
    p = tmp_path / "x.bin"
    data = b"a" * 131072
    p.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert compute_file_hash(p) == expected


def test_file_hash_3_buffer_minus_1(tmp_path: Path):
    """3 * 65536 - 1 = 196607 字节。"""
    p = tmp_path / "x.bin"
    data = b"a" * (3 * 65536 - 1)
    p.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert compute_file_hash(p) == expected


def test_file_hash_10_buffers(tmp_path: Path):
    """10 * 65536 = 655360 字节。"""
    p = tmp_path / "x.bin"
    data = b"a" * (10 * 65536)
    p.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert compute_file_hash(p) == expected


def test_file_hash_buffer_boundary_mixed_bytes(tmp_path: Path):
    """边界上字节序列含 0x00/0xff。"""
    p = tmp_path / "x.bin"
    data = bytes(range(256)) * 257  # 256 * 257 = 65792 bytes
    p.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert compute_file_hash(p) == expected


# =========================================================================
# 更多 SHA-256 测试向量
# =========================================================================


def test_text_hash_long_repeating_pattern():
    """长重复模式。"""
    text = "abc" * 1000
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert compute_text_hash(text) == expected


def test_text_hash_4_spaces():
    """4 个空格。"""
    expected = hashlib.sha256(b"    ").hexdigest()
    assert compute_text_hash("    ") == expected


def test_text_hash_single_newline():
    expected = hashlib.sha256(b"\n").hexdigest()
    assert compute_text_hash("\n") == expected


def test_text_hash_multiple_newlines():
    text = "\n" * 10
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert compute_text_hash(text) == expected


def test_text_hash_mixed_whitespace():
    text = " \t\n\r "
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert compute_text_hash(text) == expected


def test_text_hash_emoji():
    text = "😀🎉"
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert compute_text_hash(text) == expected


def test_text_hash_4_byte_utf8_char():
    """4-byte UTF-8 字符（emoji 是其中一种）。"""
    text = "𝕏"  # U+1D54F, 4 bytes in UTF-8
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert compute_text_hash(text) == expected


def test_text_hash_null_byte_in_string():
    """字符串含 \x00。"""
    text = "abc\x00def"
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert compute_text_hash(text) == expected


def test_text_hash_only_null_byte():
    expected = hashlib.sha256(b"\x00").hexdigest()
    assert compute_text_hash("\x00") == expected


def test_text_hash_bom_prefix():
    """BOM 字符（U+FEFF）。"""
    text = "﻿hello"
    expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert compute_text_hash(text) == expected


def test_text_hash_long_text_1mb():
    """1MB 文本。"""
    text = "x" * (1024 * 1024)
    h = compute_text_hash(text)
    assert len(h) == 64


# =========================================================================
# 函数属性
# =========================================================================


def test_compute_file_hash_name():
    assert compute_file_hash.__name__ == "compute_file_hash"


def test_compute_text_hash_name():
    assert compute_text_hash.__name__ == "compute_text_hash"


def test_compute_file_hash_qualname():
    assert compute_file_hash.__qualname__ == "compute_file_hash"


def test_compute_text_hash_qualname():
    assert compute_text_hash.__qualname__ == "compute_text_hash"


def test_compute_file_hash_module():
    assert compute_file_hash.__module__ == "app.hash"


def test_compute_text_hash_module():
    assert compute_text_hash.__module__ == "app.hash"


def test_compute_file_hash_is_callable():
    assert callable(compute_file_hash)


def test_compute_text_hash_is_callable():
    assert callable(compute_text_hash)


def test_compute_file_hash_has_docstring():
    assert compute_file_hash.__doc__ is not None


def test_compute_text_hash_has_docstring():
    assert compute_text_hash.__doc__ is not None


def test_compute_file_hash_docstring_mentions_streaming_or_hash():
    """docstring 应提及流式读取或 hash 概念。"""
    doc = compute_file_hash.__doc__
    assert "流式" in doc or "hash" in doc.lower() or "摘要" in doc


def test_compute_text_hash_docstring_mentions_hash():
    doc = compute_text_hash.__doc__
    assert "hash" in doc.lower() or "指纹" in doc


# =========================================================================
# 模块 dunder 属性
# =========================================================================


def test_module_docstring_present():
    import app.hash as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_sha256():
    import app.hash as mod
    assert "SHA-256" in mod.__doc__ or "sha256" in mod.__doc__.lower()


def test_module_docstring_mentions_source_hash():
    import app.hash as mod
    assert "source_hash" in mod.__doc__


def test_module_name():
    import app.hash as mod
    assert mod.__name__ == "app.hash"


def test_module_file_ends_with_hash_py():
    import app.hash as mod
    assert mod.__file__.endswith("hash.py")


def test_module_no_all_attribute():
    """app/hash.py 不定义 __all__。"""
    import app.hash as mod
    assert not hasattr(mod, "__all__")


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


def test_module_no_other_functions():
    """只导出 compute_file_hash 和 compute_text_hash 两个函数。"""
    import app.hash as mod
    src = inspect.getsource(mod)
    # 数顶层 def
    import re
    defs = re.findall(r"^def\s+(\w+)", src, re.MULTILINE)
    assert set(defs) == {"compute_file_hash", "compute_text_hash"}


# =========================================================================
# 签名深度（已有但更细）
# =========================================================================


def test_compute_file_hash_signature_params():
    sig = inspect.signature(compute_file_hash)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "path"


def test_compute_file_hash_path_param_kind():
    sig = inspect.signature(compute_file_hash)
    param = sig.parameters["path"]
    assert param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_compute_text_hash_signature_params():
    sig = inspect.signature(compute_text_hash)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "text"


def test_compute_text_hash_text_param_kind():
    sig = inspect.signature(compute_text_hash)
    param = sig.parameters["text"]
    assert param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_compute_file_hash_no_varargs():
    sig = inspect.signature(compute_file_hash)
    assert not any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())


def test_compute_text_hash_no_varargs():
    sig = inspect.signature(compute_text_hash)
    assert not any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())


# =========================================================================
# 文件路径形式
# =========================================================================


def test_file_hash_relative_path(tmp_path: Path, monkeypatch):
    """相对路径（cwd 切到 tmp_path）。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    h = compute_file_hash("x.txt")
    assert h == compute_text_hash("hello")


def test_file_hash_path_with_dots(tmp_path: Path):
    """路径含 . 段。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    # 用 ./x.txt 形式
    h = compute_file_hash(tmp_path / "." / "x.txt")
    assert h == compute_text_hash("hello")


def test_file_hash_double_dot_parent(tmp_path: Path):
    """路径含 .. 段。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    p = sub / "x.txt"
    p.write_text("hello", encoding="utf-8")
    # sub/.. 退回 tmp_path，但 x.txt 在 sub 里
    # 这里测 sub/../sub/x.txt
    h = compute_file_hash(tmp_path / "sub" / ".." / "sub" / "x.txt")
    assert h == compute_text_hash("hello")


def test_file_hash_path_with_posix_sep(tmp_path: Path):
    """Path 用 forward slash。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    h = compute_file_hash(str(p).replace("\\", "/"))
    assert h == compute_text_hash("hello")


# =========================================================================
# 错误消息内容
# =========================================================================


def test_file_hash_missing_file_message_contains_path(tmp_path: Path):
    missing = tmp_path / "no_such_file.bin"
    with pytest.raises(FileNotFoundError) as exc:
        compute_file_hash(missing)
    assert "no_such_file.bin" in str(exc.value)


def test_file_hash_directory_message_contains_path(tmp_path: Path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    with pytest.raises(FileNotFoundError) as exc:
        compute_file_hash(sub)
    assert "subdir" in str(exc.value)


def test_file_hash_missing_file_error_is_oserror_subclass():
    """FileNotFoundError 是 OSError 子类。"""
    missing = Path("/no/such/path/here")
    try:
        compute_file_hash(missing)
    except FileNotFoundError as e:
        assert isinstance(e, OSError)


# =========================================================================
# 跨函数一致性
# =========================================================================


def test_file_hash_equals_text_hash_for_arbitrary_content(tmp_path: Path):
    """对任意二进制内容（UTF-8 编码后），file_hash == text_hash。"""
    p = tmp_path / "x.bin"
    content_text = "arbitrary 中文 content 🎉"
    p.write_text(content_text, encoding="utf-8")
    assert compute_file_hash(p) == compute_text_hash(content_text)


def test_file_hash_consistent_with_hashlib_multiple_files(tmp_path: Path):
    """多个不同内容文件都和 hashlib 一致。"""
    for i, content in enumerate([b"", b"a", b"ab", b"abc", b"abcd", b"abcde"]):
        p = tmp_path / f"f{i}.bin"
        p.write_bytes(content)
        assert compute_file_hash(p) == hashlib.sha256(content).hexdigest()


def test_text_hash_consistent_with_hashlib_strings():
    """对多种字符串，compute_text_hash 与 hashlib 一致。"""
    texts = ["", "a", "abc", "hello world", "中文测试", "🎉", "\x00\x01\x02"]
    for text in texts:
        assert compute_text_hash(text) == hashlib.sha256(text.encode("utf-8")).hexdigest()


# =========================================================================
# 不变量
# =========================================================================


def test_text_hash_idempotent():
    """对同一字符串多次调用结果一致。"""
    text = "test text"
    h1 = compute_text_hash(text)
    h2 = compute_text_hash(text)
    h3 = compute_text_hash(text)
    assert h1 == h2 == h3


def test_file_hash_idempotent(tmp_path: Path):
    """对同一文件多次调用结果一致。"""
    p = tmp_path / "x.txt"
    p.write_text("test text", encoding="utf-8")
    h1 = compute_file_hash(p)
    h2 = compute_file_hash(p)
    h3 = compute_file_hash(p)
    assert h1 == h2 == h3


def test_text_hash_no_side_effects():
    """compute_text_hash 不修改输入（str 是 immutable，但验证）。"""
    text = "hello"
    compute_text_hash(text)
    assert text == "hello"


def test_file_hash_does_not_consume_file(tmp_path: Path):
    """file_hash 后文件仍可读。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    compute_file_hash(p)
    assert p.read_text(encoding="utf-8") == "hello"


def test_file_hash_does_not_modify_file_mtime(tmp_path: Path):
    """hash 不修改文件（mtime 不变）。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    mtime_before = p.stat().st_mtime
    compute_file_hash(p)
    mtime_after = p.stat().st_mtime
    assert mtime_before == mtime_after


# =========================================================================
# 综合：file_hash 与 text_hash 输出格式相同
# =========================================================================


def test_file_hash_and_text_hash_same_length(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    assert len(compute_file_hash(p)) == len(compute_text_hash("hello"))


def test_file_hash_and_text_hash_same_charset(tmp_path: Path):
    """都是小写 hex。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    fh = compute_file_hash(p)
    th = compute_text_hash("hello")
    valid = set("0123456789abcdef")
    assert set(fh) <= valid
    assert set(th) <= valid


def test_file_hash_and_text_hash_no_uppercase(tmp_path: Path):
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    fh = compute_file_hash(p)
    th = compute_text_hash("hello")
    assert fh == fh.lower()
    assert th == th.lower()
