"""各 package 的 __init__.py 模块导出契约测试。

覆盖：
- app/chunkers/__init__.py：StructuralChunker + normalize_text 导出
- app/parsers/__init__.py：Parser / ParserError / make_document_id 导出
- evaluation/__init__.py：版本常量 + __all__

注：app/__init__.py 当前为空，不导出任何符号。
"""

from __future__ import annotations

import pytest


# ---------- app.chunkers __init__ ----------


def test_chunkers_init_exports_structural_chunker():
    from app.chunkers import StructuralChunker
    assert StructuralChunker is not None
    assert hasattr(StructuralChunker, "__call__") or hasattr(StructuralChunker, "chunk")


def test_chunkers_init_exports_normalize_text():
    from app.chunkers import normalize_text
    assert callable(normalize_text)


def test_chunkers_init_all_listed():
    import app.chunkers as pkg
    assert "StructuralChunker" in pkg.__all__
    assert "normalize_text" in pkg.__all__


def test_chunkers_init_all_only_lists_documented_names():
    import app.chunkers as pkg
    assert set(pkg.__all__) == {"StructuralChunker", "normalize_text"}


def test_chunkers_init_all_is_list():
    import app.chunkers as pkg
    assert isinstance(pkg.__all__, list)


def test_chunkers_init_exports_match_actual_attributes():
    """__all__ 中的每个名字都应是模块属性。"""
    import app.chunkers as pkg
    for name in pkg.__all__:
        assert hasattr(pkg, name), f"{name} in __all__ 但模块无此属性"


def test_chunkers_init_normalize_text_callable_with_string():
    """normalize_text 是函数，接受 str 返 str。"""
    from app.chunkers import normalize_text
    result = normalize_text("  hello   world  ")
    assert isinstance(result, str)


def test_chunkers_init_structural_chunker_can_be_instantiated():
    """StructuralChunker 可实例化（默认参数）。"""
    from app.chunkers import StructuralChunker
    chunker = StructuralChunker(max_chars=800)
    assert chunker is not None


# ---------- app.parsers __init__ ----------


def test_parsers_init_exports_parser():
    from app.parsers import Parser
    assert Parser is not None


def test_parsers_init_exports_parser_error():
    from app.parsers import ParserError
    assert issubclass(ParserError, Exception)


def test_parsers_init_exports_make_document_id():
    from app.parsers import make_document_id
    assert callable(make_document_id)


def test_parsers_init_all_listed():
    import app.parsers as pkg
    assert "Parser" in pkg.__all__
    assert "ParserError" in pkg.__all__
    assert "make_document_id" in pkg.__all__


def test_parsers_init_all_only_lists_documented_names():
    import app.parsers as pkg
    assert set(pkg.__all__) == {"Parser", "ParserError", "make_document_id"}


def test_parsers_init_all_is_list():
    import app.parsers as pkg
    assert isinstance(pkg.__all__, list)


def test_parsers_init_exports_match_actual_attributes():
    import app.parsers as pkg
    for name in pkg.__all__:
        assert hasattr(pkg, name)


def test_parsers_init_parser_is_abc_class():
    """Parser 是 ABC，不能直接实例化。"""
    from app.parsers import Parser
    from abc import ABC
    assert issubclass(Parser, ABC)


def test_parsers_init_make_document_id_accepts_hex():
    """make_document_id 接受 64 字符 hex → 返 doc- 前缀 ID。"""
    from app.parsers import make_document_id
    result = make_document_id("a" * 64)
    assert isinstance(result, str)
    assert result.startswith("doc-")


# ---------- evaluation __init__ ----------


def test_evaluation_init_exports_evaluator_version():
    from evaluation import EVALUATOR_VERSION
    assert isinstance(EVALUATOR_VERSION, str)
    assert EVALUATOR_VERSION == "1.1"


def test_evaluation_init_exports_report_version():
    from evaluation import REPORT_VERSION
    assert isinstance(REPORT_VERSION, str)
    assert REPORT_VERSION == "1.1"


def test_evaluation_init_exports_annotation_version():
    from evaluation import ANNOTATION_VERSION
    assert isinstance(ANNOTATION_VERSION, str)
    assert ANNOTATION_VERSION == "1.0"


def test_evaluation_init_exports_manifest_version():
    from evaluation import MANIFEST_VERSION
    assert isinstance(MANIFEST_VERSION, str)
    assert MANIFEST_VERSION == "1.0"


def test_evaluation_init_all_listed():
    import evaluation as pkg
    assert "EVALUATOR_VERSION" in pkg.__all__
    assert "REPORT_VERSION" in pkg.__all__
    assert "ANNOTATION_VERSION" in pkg.__all__
    assert "MANIFEST_VERSION" in pkg.__all__


def test_evaluation_init_all_only_lists_documented_names():
    import evaluation as pkg
    assert set(pkg.__all__) == {
        "EVALUATOR_VERSION",
        "REPORT_VERSION",
        "ANNOTATION_VERSION",
        "MANIFEST_VERSION",
    }


def test_evaluation_init_all_is_list():
    import evaluation as pkg
    assert isinstance(pkg.__all__, list)


def test_evaluation_init_exports_match_actual_attributes():
    import evaluation as pkg
    for name in pkg.__all__:
        assert hasattr(pkg, name)


def test_evaluation_init_evaluator_version_is_immutable_string():
    """版本号是 str，长度合理（≥3 字符，如 '1.0'）。"""
    from evaluation import EVALUATOR_VERSION
    assert len(EVALUATOR_VERSION) >= 3
    assert "." in EVALUATOR_VERSION


def test_evaluation_init_report_version_matches_evaluator():
    """v1.1 阶段两者应一致（如未来分开发版可改）。"""
    from evaluation import EVALUATOR_VERSION, REPORT_VERSION
    # 当前两者都是 "1.1"，记录此契约
    assert EVALUATOR_VERSION == REPORT_VERSION


def test_evaluation_init_annotation_version_is_one_zero():
    """annotation 版本固定为 1.0（manifest_version 也是 1.0）。"""
    from evaluation import ANNOTATION_VERSION, MANIFEST_VERSION
    assert ANNOTATION_VERSION == "1.0"
    assert MANIFEST_VERSION == "1.0"


# ---------- app __init__（空模块） ----------


def test_app_init_exists_and_is_module():
    import app
    assert app is not None
    assert hasattr(app, "__name__")


def test_app_init_no_required_exports():
    """app/__init__.py 当前为空，没有强制导出。

    此测试记录"app 是包"这一事实，不假设任何 __all__。"""
    import app
    # 没有显式 __all__ 也是合法的
    # 测试本身只验证 app 可被导入
    assert app.__name__ == "app"


# ---------- 子模块 import 路径稳定性 ----------


def test_chunkers_init_submodule_path_stable():
    """从 app.chunkers.StructuralChunker 与 app.chunkers.structural.StructuralChunker
    应得到同一个对象（同一引用）。"""
    from app.chunkers import StructuralChunker as A
    from app.chunkers.structural import StructuralChunker as B
    assert A is B


def test_chunkers_init_normalize_text_submodule_path_stable():
    from app.chunkers import normalize_text as A
    from app.chunkers.structural import normalize_text as B
    assert A is B


def test_parsers_init_parser_submodule_path_stable():
    from app.parsers import Parser as A
    from app.parsers.base import Parser as B
    assert A is B


def test_parsers_init_parser_error_submodule_path_stable():
    from app.parsers import ParserError as A
    from app.parsers.base import ParserError as B
    assert A is B


def test_parsers_init_make_document_id_submodule_path_stable():
    from app.parsers import make_document_id as A
    from app.parsers.base import make_document_id as B
    assert A is B


# ---------- 包元数据 ----------


def test_chunkers_init_has_docstring():
    """每个 __init__.py 都应有 docstring 解释包职责。"""
    import app.chunkers as pkg
    assert pkg.__doc__ is not None
    assert len(pkg.__doc__) > 0


def test_parsers_init_has_docstring():
    import app.parsers as pkg
    assert pkg.__doc__ is not None
    assert len(pkg.__doc__) > 0


def test_evaluation_init_has_docstring():
    import evaluation as pkg
    assert pkg.__doc__ is not None
    assert len(pkg.__doc__) > 0


def test_evaluation_init_docstring_mentions_design_principles():
    """evaluation/__init__.py docstring 应说明设计原则。"""
    import evaluation as pkg
    doc = pkg.__doc__
    # 含至少一个设计原则关键词
    keywords = ["设计", "v1.", "manifest", "annotation", "version"]
    assert any(k in doc for k in keywords)


# ---------- 版本常量全局唯一性 ----------


def test_evaluation_versions_form_consistent_set():
    """四个版本号应符合当前阶段契约：
    - EVALUATOR_VERSION = "1.1"（v1.1 阶段）
    - REPORT_VERSION = "1.1"
    - ANNOTATION_VERSION = "1.0"（手注格式未变）
    - MANIFEST_VERSION = "1.0"（清单格式未变）
    """
    from evaluation import (
        EVALUATOR_VERSION,
        REPORT_VERSION,
        ANNOTATION_VERSION,
        MANIFEST_VERSION,
    )
    assert (EVALUATOR_VERSION, REPORT_VERSION, ANNOTATION_VERSION, MANIFEST_VERSION) == (
        "1.1",
        "1.1",
        "1.0",
        "1.0",
    )


def test_evaluation_versions_tuple_form():
    """版本号能用元组形式整理（便于一次性引用）。"""
    import evaluation as pkg
    versions = (
        pkg.EVALUATOR_VERSION,
        pkg.REPORT_VERSION,
        pkg.ANNOTATION_VERSION,
        pkg.MANIFEST_VERSION,
    )
    assert all(isinstance(v, str) for v in versions)
    assert len(versions) == 4
