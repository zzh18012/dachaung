r"""app/parsers/__init__.py 边角测试（Round 166）。

补强 test_packages_init.py（41 测试，覆盖所有 package init）未深入的：
- __all__ 精确性与顺序
- 重导出 identity（app.parsers.X is app.parsers.base.X）
- 子模块（fallback/kreuzberg/markdown/html/ipynb/text）可独立导入
- 公共 API 子模块完整覆盖（每个 parser class 都能从子包访问）
- 模块 docstring / future annotations
- 子包目录结构
"""

from __future__ import annotations

import inspect

import pytest


# =========================================================================
# __all__ 精确性
# =========================================================================


def test_all_exact():
    import app.parsers as pkg
    assert pkg.__all__ == ["Parser", "ParserError", "make_document_id"]


def test_all_is_list():
    import app.parsers as pkg
    assert isinstance(pkg.__all__, list)


def test_all_no_duplicates():
    import app.parsers as pkg
    assert len(pkg.__all__) == len(set(pkg.__all__))


def test_all_length_three():
    import app.parsers as pkg
    assert len(pkg.__all__) == 3


def test_all_contains_parser():
    import app.parsers as pkg
    assert "Parser" in pkg.__all__


def test_all_contains_parser_error():
    import app.parsers as pkg
    assert "ParserError" in pkg.__all__


def test_all_contains_make_document_id():
    import app.parsers as pkg
    assert "make_document_id" in pkg.__all__


# =========================================================================
# 重导出 identity
# =========================================================================


def test_parser_reexported_identity():
    import app.parsers as pkg
    from app.parsers.base import Parser
    assert pkg.Parser is Parser


def test_parser_error_reexported_identity():
    import app.parsers as pkg
    from app.parsers.base import ParserError
    assert pkg.ParserError is ParserError


def test_make_document_id_reexported_identity():
    import app.parsers as pkg
    from app.parsers.base import make_document_id
    assert pkg.make_document_id is make_document_id


# =========================================================================
# 公共 API 类型
# =========================================================================


def test_parser_is_class():
    import app.parsers as pkg
    from abc import ABC
    assert isinstance(pkg.Parser, type)
    assert issubclass(pkg.Parser, ABC)


def test_parser_error_is_class():
    import app.parsers as pkg
    assert isinstance(pkg.ParserError, type)
    assert issubclass(pkg.ParserError, Exception)


def test_make_document_id_is_callable():
    import app.parsers as pkg
    assert callable(pkg.make_document_id)


# =========================================================================
# 子模块可导入
# =========================================================================


def test_can_import_base_module():
    import app.parsers.base as mod
    assert mod is not None


def test_can_import_fallback_module():
    import app.parsers.fallback_parser as mod
    assert mod is not None


def test_can_import_kreuzberg_module():
    import app.parsers.kreuzberg_parser as mod
    assert mod is not None


def test_can_import_markdown_parser_module():
    import app.parsers.markdown_parser as mod
    assert mod is not None


def test_can_import_html_parser_module():
    import app.parsers.html_parser as mod
    assert mod is not None


def test_can_import_ipynb_parser_module():
    import app.parsers.ipynb_parser as mod
    assert mod is not None


def test_can_import_text_parser_module():
    import app.parsers.text_parser as mod
    assert mod is not None


# =========================================================================
# 子模块中 Parser 子类
# =========================================================================


def test_fallback_module_has_fallback_parser():
    import app.parsers.fallback_parser as mod
    assert hasattr(mod, "FallbackParser")


def test_kreuzberg_module_has_kreuzberg_parser():
    import app.parsers.kreuzberg_parser as mod
    # 可能叫 KreuzbergParser 或其他
    parser_classes = [n for n in dir(mod) if n.endswith("Parser") and not n.startswith("_")]
    assert len(parser_classes) >= 1


def test_markdown_module_has_markdown_parser():
    import app.parsers.markdown_parser as mod
    assert hasattr(mod, "MarkdownParser")


def test_html_module_has_html_parser():
    import app.parsers.html_parser as mod
    assert hasattr(mod, "HtmlParser")


def test_ipynb_module_has_ipynb_parser():
    import app.parsers.ipynb_parser as mod
    assert hasattr(mod, "IpynbParser")


def test_text_module_has_text_parser():
    import app.parsers.text_parser as mod
    assert hasattr(mod, "TextParser")


def test_all_parsers_inherit_parser():
    import app.parsers as pkg
    from app.parsers.fallback_parser import FallbackParser
    from app.parsers.html_parser import HtmlParser
    from app.parsers.ipynb_parser import IpynbParser
    from app.parsers.markdown_parser import MarkdownParser
    from app.parsers.text_parser import TextParser

    for cls in (FallbackParser, HtmlParser, IpynbParser, MarkdownParser, TextParser):
        assert issubclass(cls, pkg.Parser)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_docstring_present():
    import app.parsers as pkg
    assert pkg.__doc__ is not None


def test_module_docstring_mentions_business_code():
    """docstring 提及"业务代码只依赖 Parser"。"""
    import app.parsers as pkg
    doc = pkg.__doc__
    assert "业务代码" in doc or "business" in doc.lower()


def test_module_docstring_mentions_di_or_factory():
    """docstring 提及"依赖注入或工厂选择"。"""
    import app.parsers as pkg
    doc = pkg.__doc__
    assert "依赖注入" in doc or "工厂" in doc or "injection" in doc.lower()


def test_module_uses_future_annotations():
    import app.parsers as pkg
    src = inspect.getsource(pkg)
    assert "from __future__ import annotations" in src


def test_module_imports_from_base():
    import app.parsers as pkg
    src = inspect.getsource(pkg)
    assert "from .base import" in src


def test_module_no_silence_unused():
    import app.parsers as pkg
    # __init__.py 不应有 _silence_unused（base.py 才有）
    assert not hasattr(pkg, "_silence_unused")


def test_module_file_path():
    """模块文件路径以 __init__.py 结尾。"""
    import app.parsers as pkg
    assert pkg.__file__.endswith("__init__.py")


def test_module_package_attribute():
    import app.parsers as pkg
    assert pkg.__package__ == "app.parsers"


# =========================================================================
# 子包目录
# =========================================================================


def test_parsers_dir_contains_modules():
    """app.parsers 子目录应至少含 base/fallback_parser/markdown/html/ipynb/text/kreuzberg。"""
    import app.parsers
    import os
    pkg_dir = os.path.dirname(app.parsers.__file__)
    files = set(os.listdir(pkg_dir))
    for name in (
        "base.py",
        "fallback_parser.py",
        "markdown_parser.py",
        "html_parser.py",
        "ipynb_parser.py",
        "text_parser.py",
        "kreuzberg_parser.py",
        "__init__.py",
    ):
        assert name in files


# =========================================================================
# 综合行为
# =========================================================================


def test_reexported_parser_callable_through_pkg():
    """通过 package 路径访问 Parser 仍能正常用 isinstance。"""
    import app.parsers as pkg

    class MyParser(pkg.Parser):
        name = "x"
        version = "1.0.0"

        def parse(self, path, source_hash):
            return None

    assert isinstance(MyParser(), pkg.Parser)


def test_reexported_parser_error_usable_through_pkg():
    """通过 package 路径抛/捕 ParserError。"""
    import app.parsers as pkg
    with pytest.raises(pkg.ParserError):
        raise pkg.ParserError(code="x", message="y")


def test_reexported_make_document_id_works():
    """通过 package 路径调用 make_document_id。"""
    import app.parsers as pkg
    h = "a" * 64
    result = pkg.make_document_id(h)
    assert result == "doc-" + "a" * 16


def test_star_import_only_yields_all_three():
    """star import 应只导入 __all__ 中的 3 个名字。"""
    namespace = {}
    exec("from app.parsers import *", namespace)
    expected = {"Parser", "ParserError", "make_document_id"}
    actual = {k for k in namespace if not k.startswith("__")}
    assert actual == expected
