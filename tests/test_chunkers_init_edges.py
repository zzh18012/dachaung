r"""app/chunkers/__init__.py 边角测试（Round 171）。

补强 test_packages_init.py（41 测试覆盖所有 package init）未深入的：
- __all__ 精确性与顺序
- 重导出 identity（app.chunkers.X is app.chunkers.structural.X）
- 子模块可导入
- 公共 API 类型（class、callable）
- 模块 docstring / future annotations
- 子包目录结构
- star import 行为
"""

from __future__ import annotations

import inspect

import pytest


# =========================================================================
# __all__ 精确性
# =========================================================================


def test_all_exact():
    import app.chunkers as pkg
    assert pkg.__all__ == ["StructuralChunker", "normalize_text"]


def test_all_is_list():
    import app.chunkers as pkg
    assert isinstance(pkg.__all__, list)


def test_all_no_duplicates():
    import app.chunkers as pkg
    assert len(pkg.__all__) == len(set(pkg.__all__))


def test_all_length_two():
    import app.chunkers as pkg
    assert len(pkg.__all__) == 2


def test_all_contains_structural_chunker():
    import app.chunkers as pkg
    assert "StructuralChunker" in pkg.__all__


def test_all_contains_normalize_text():
    import app.chunkers as pkg
    assert "normalize_text" in pkg.__all__


# =========================================================================
# 重导出 identity
# =========================================================================


def test_structural_chunker_reexported_identity():
    import app.chunkers as pkg
    from app.chunkers.structural import StructuralChunker
    assert pkg.StructuralChunker is StructuralChunker


def test_normalize_text_reexported_identity():
    import app.chunkers as pkg
    from app.chunkers.structural import normalize_text
    assert pkg.normalize_text is normalize_text


# =========================================================================
# 公共 API 类型
# =========================================================================


def test_structural_chunker_is_class():
    import app.chunkers as pkg
    assert isinstance(pkg.StructuralChunker, type)


def test_normalize_text_is_callable():
    import app.chunkers as pkg
    assert callable(pkg.normalize_text)


def test_structural_chunker_init_takes_max_chars():
    """StructuralChunker(max_chars=...) 构造。"""
    import app.chunkers as pkg
    c = pkg.StructuralChunker(max_chars=800)
    assert c is not None


def test_normalize_text_returns_str():
    import app.chunkers as pkg
    assert isinstance(pkg.normalize_text("hello"), str)


# =========================================================================
# 子模块可导入
# =========================================================================


def test_can_import_structural_module():
    import app.chunkers.structural as mod
    assert mod is not None


def test_structural_module_has_structural_chunker():
    import app.chunkers.structural as mod
    assert hasattr(mod, "StructuralChunker")


def test_structural_module_has_normalize_text():
    import app.chunkers.structural as mod
    assert hasattr(mod, "normalize_text")


# =========================================================================
# 模块结构
# =========================================================================


def test_module_docstring_present():
    import app.chunkers as pkg
    assert pkg.__doc__ is not None


def test_module_uses_future_annotations():
    import app.chunkers as pkg
    src = inspect.getsource(pkg)
    assert "from __future__ import annotations" in src


def test_module_imports_from_structural():
    import app.chunkers as pkg
    src = inspect.getsource(pkg)
    assert "from .structural import" in src


def test_module_no_silence_unused():
    import app.chunkers as pkg
    assert not hasattr(pkg, "_silence_unused")


def test_module_file_ends_with_init_py():
    import app.chunkers as pkg
    assert pkg.__file__.endswith("__init__.py")


def test_module_package_attribute():
    import app.chunkers as pkg
    assert pkg.__package__ == "app.chunkers"


# =========================================================================
# 子包目录
# =========================================================================


def test_chunkers_dir_contains_modules():
    """app.chunkers 子目录应至少含 __init__.py 和 structural.py。"""
    import app.chunkers
    import os
    pkg_dir = os.path.dirname(app.chunkers.__file__)
    files = set(os.listdir(pkg_dir))
    for name in ("__init__.py", "structural.py"):
        assert name in files


# =========================================================================
# 综合行为
# =========================================================================


def test_reexported_chunker_usable_through_pkg():
    """通过 package 路径访问 StructuralChunker 仍能正常用。"""
    import app.chunkers as pkg
    c = pkg.StructuralChunker(max_chars=800)
    assert hasattr(c, "chunk")


def test_reexported_normalize_text_works():
    """通过 package 路径调用 normalize_text。"""
    import app.chunkers as pkg
    result = pkg.normalize_text("  hello   world  ")
    assert result == "hello world"


def test_star_import_only_yields_all_two():
    """star import 应只导入 __all__ 中的 2 个名字。"""
    namespace = {}
    exec("from app.chunkers import *", namespace)
    expected = {"StructuralChunker", "normalize_text"}
    actual = {k for k in namespace if not k.startswith("__")}
    assert actual == expected


def test_normalize_text_idempotent():
    import app.chunkers as pkg
    text = "hello   world"
    assert pkg.normalize_text(text) == pkg.normalize_text(text)


def test_structural_chunker_chunk_callable():
    import app.chunkers as pkg
    c = pkg.StructuralChunker()
    assert callable(c.chunk)


def test_normalize_text_empty_string():
    import app.chunkers as pkg
    assert pkg.normalize_text("") == ""


def test_normalize_text_no_whitespace():
    import app.chunkers as pkg
    assert pkg.normalize_text("hello") == "hello"
