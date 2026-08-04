r"""app/pipeline.py 边角测试 - 第五轮（Round 125）。

补强已有 base/edges/edges2/edges4/errors/helpers/integration
（共 400 测试）未覆盖的深度路径：
- get_parser 深度：
  - "fallback" 返回 FallbackParser 实例
  - "kreuzberg" 返回 KreuzbergParser 实例
  - "markdown" 返回 MarkdownParser 实例
  - "html" 返回 HtmlParser 实例
  - "text" 返回 TextParser 实例
  - "ipynb" 返回 IpynbParser 实例
  - 各种未知 name → ValueError 含支持列表
  - 返回的对象是 Parser 子类
- image_output_dir_for 深度：
  - output_path 为 None → None
  - output_path 为 str → 返回 Path
  - source_hash 不足 16 字符 → 截断不抛
  - 返回 Path 的 parent 与 output_path.parent 一致
  - 返回 Path 的 name 形如 "images-<16 hex>"
- process_single 签名深度：
  - 4 个 keyword-only 参数
  - 默认值精确
- validate_only 深度：
  - SchemaValidationError → (False, str(e))
  - FileNotFoundError → (False, str(e))
  - JSONDecodeError → (False, "JSON 解析失败: ...")
  - 其他异常传播（不被捕获）
- 模块结构深度：
  - imports 完整
  - __all__ 4 项精确
  - 各函数 callable
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.pipeline import (
    get_parser,
    image_output_dir_for,
    process_single,
    validate_only,
)


SHA = "a" * 64


# =========================================================================
# get_parser 深度（类型断言）
# =========================================================================


def test_get_parser_fallback_returns_fallback_parser():
    from app.parsers.fallback_parser import FallbackParser

    p = get_parser("fallback")
    assert isinstance(p, FallbackParser)


def test_get_parser_kreuzberg_returns_kreuzberg_parser():
    from app.parsers.kreuzberg_parser import KreuzbergParser

    p = get_parser("kreuzberg")
    assert isinstance(p, KreuzbergParser)


def test_get_parser_markdown_returns_markdown_parser():
    from app.parsers.markdown_parser import MarkdownParser

    p = get_parser("markdown")
    assert isinstance(p, MarkdownParser)


def test_get_parser_html_returns_html_parser():
    from app.parsers.html_parser import HtmlParser

    p = get_parser("html")
    assert isinstance(p, HtmlParser)


def test_get_parser_text_returns_text_parser():
    from app.parsers.text_parser import TextParser

    p = get_parser("text")
    assert isinstance(p, TextParser)


def test_get_parser_ipynb_returns_ipynb_parser():
    from app.parsers.ipynb_parser import IpynbParser

    p = get_parser("ipynb")
    assert isinstance(p, IpynbParser)


def test_get_parser_all_return_parser_subclass():
    from app.parsers.base import Parser

    for name in ("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"):
        p = get_parser(name)
        assert isinstance(p, Parser)


def test_get_parser_unknown_name_raises_value_error():
    with pytest.raises(ValueError):
        get_parser("unknown")


def test_get_parser_unknown_name_message_lists_supported():
    with pytest.raises(ValueError) as ei:
        get_parser("xyz")
    msg = str(ei.value)
    # 应列出所有支持的 parser 名字
    assert "fallback" in msg
    assert "kreuzberg" in msg
    assert "markdown" in msg
    assert "html" in msg
    assert "text" in msg
    assert "ipynb" in msg


def test_get_parser_unknown_name_message_contains_input():
    with pytest.raises(ValueError) as ei:
        get_parser("my-bad-name")
    assert "my-bad-name" in str(ei.value)


def test_get_parser_empty_string_raises():
    with pytest.raises(ValueError):
        get_parser("")


def test_get_parser_case_sensitive():
    """'Fallback' 大小写敏感 → ValueError。"""
    with pytest.raises(ValueError):
        get_parser("Fallback")


def test_get_parser_with_whitespace_raises():
    with pytest.raises(ValueError):
        get_parser(" fallback ")


def test_get_parser_two_calls_return_independent_instances():
    p1 = get_parser("text")
    p2 = get_parser("text")
    assert p1 is not p2


def test_get_parser_fallback_accepts_image_output_dir(tmp_path: Path):
    """fallback parser 接受 image_output_dir 参数。"""
    p = get_parser("fallback", image_output_dir=tmp_path)
    assert p is not None


def test_get_parser_kreuzberg_ignores_image_output_dir(tmp_path: Path):
    """kreuzberg parser 不接受 image_output_dir（不被 KeywordArg 报错）。"""
    # 注意：get_parser 内部对 kreuzberg 不传 image_output_dir
    p = get_parser("kreuzberg", image_output_dir=tmp_path)
    assert p is not None


# =========================================================================
# image_output_dir_for 深度
# =========================================================================


def test_image_output_dir_for_none_returns_none():
    assert image_output_dir_for(None, SHA) is None


def test_image_output_dir_for_str_returns_path():
    result = image_output_dir_for("/tmp/out.json", SHA)
    assert isinstance(result, Path)


def test_image_output_dir_for_path_returns_path(tmp_path: Path):
    result = image_output_dir_for(tmp_path / "out.json", SHA)
    assert isinstance(result, Path)


def test_image_output_dir_for_short_hash_truncated_safe():
    """source_hash < 16 字符 → 截断（不抛）。"""
    result = image_output_dir_for("/tmp/out.json", "abc")
    # name 应为 "images-abc"
    assert result is not None
    assert result.name == "images-abc"


def test_image_output_dir_for_empty_hash():
    """source_hash 空串 → name 为 'images-'。"""
    result = image_output_dir_for("/tmp/out.json", "")
    assert result is not None
    assert result.name == "images-"


def test_image_output_dir_for_name_format():
    """name 形如 'images-<16 hex>'。"""
    sha = "abcdef1234567890" * 4  # 64 chars
    result = image_output_dir_for("/tmp/out.json", sha)
    assert result is not None
    assert result.name == "images-" + sha[:16]


def test_image_output_dir_for_parent_matches_output_parent(tmp_path: Path):
    out = tmp_path / "sub" / "out.json"
    result = image_output_dir_for(out, SHA)
    assert result is not None
    assert result.parent == out.parent


def test_image_output_dir_for_returns_absolute_when_input_absolute(tmp_path: Path):
    out = tmp_path / "out.json"
    result = image_output_dir_for(out, SHA)
    assert result is not None
    assert result.is_absolute()


def test_image_output_dir_for_returns_relative_when_input_relative():
    """相对路径 input → 相对路径 output（保留输入特性）。"""
    result = image_output_dir_for("out.json", SHA)
    # Path("out.json").parent = Path(".") → images-<sha> 在当前目录下
    assert result is not None
    assert not result.is_absolute()


def test_image_output_dir_for_consistent_with_two_calls():
    """同输入两次调用结果一致。"""
    r1 = image_output_dir_for("/tmp/out.json", SHA)
    r2 = image_output_dir_for("/tmp/out.json", SHA)
    assert r1 == r2


# =========================================================================
# process_single 签名深度
# =========================================================================


def test_process_single_signature_param_count():
    import inspect

    sig = inspect.signature(process_single)
    params = list(sig.parameters.keys())
    # input_path, output_path, parser_name, max_chars, write_json
    assert len(params) == 5


def test_process_single_input_path_required():
    import inspect

    sig = inspect.signature(process_single)
    assert sig.parameters["input_path"].default is inspect.Parameter.empty


def test_process_single_output_path_default_none():
    import inspect

    sig = inspect.signature(process_single)
    assert sig.parameters["output_path"].default is None


def test_process_single_parser_name_keyword_only():
    import inspect

    sig = inspect.signature(process_single)
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY


def test_process_single_max_chars_keyword_only():
    import inspect

    sig = inspect.signature(process_single)
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_process_single_write_json_keyword_only():
    import inspect

    sig = inspect.signature(process_single)
    assert sig.parameters["write_json"].kind == inspect.Parameter.KEYWORD_ONLY


def test_process_single_default_parser_name_fallback():
    import inspect

    sig = inspect.signature(process_single)
    assert sig.parameters["parser_name"].default == "fallback"


def test_process_single_default_max_chars_800():
    import inspect

    sig = inspect.signature(process_single)
    assert sig.parameters["max_chars"].default == 800


def test_process_single_default_write_json_true():
    import inspect

    sig = inspect.signature(process_single)
    assert sig.parameters["write_json"].default is True


def test_process_single_return_annotation_is_tuple():
    import inspect

    sig = inspect.signature(process_single)
    ret = sig.return_annotation
    assert "tuple" in str(ret).lower()


# =========================================================================
# validate_only 深度
# =========================================================================


def test_validate_only_returns_tuple(tmp_path: Path):
    """返回 (bool, str) 元组。"""
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    result = validate_only(p)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_validate_only_first_element_is_bool(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    result = validate_only(p)
    assert isinstance(result[0], bool)


def test_validate_only_second_element_is_str(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    result = validate_only(p)
    assert isinstance(result[1], str)


def test_validate_only_missing_file_returns_false_with_message(tmp_path: Path):
    p = tmp_path / "missing.json"
    ok, msg = validate_only(p)
    assert ok is False
    assert "missing" in msg or "不存在" in msg


def test_validate_only_invalid_json_returns_false_with_json_keyword(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is False
    assert "JSON" in msg or "json" in msg.lower()


def test_validate_only_invalid_content_returns_false(tmp_path: Path):
    """内容不符合 schema → False。"""
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is False


def test_validate_only_str_path(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    ok, msg = validate_only(str(p))
    assert ok is False  # 空 dict 不符合 schema


def test_validate_only_returns_ok_for_valid(tmp_path: Path):
    """合法 document → True。"""
    doc = {
        "schema_version": "0.1.0",
        "document_id": "doc-1",
        "source_path": "/tmp/x.pdf",
        "source_type": "pdf",
        "source_hash": SHA,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "parent_id": None,
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
                "content": "hello",
                "confidence": 1.0,
                "metadata": {},
            }
        ],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    p = tmp_path / "ok.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is True
    assert msg == "OK"


# =========================================================================
# validate_only 签名深度
# =========================================================================


def test_validate_only_signature_one_param():
    import inspect

    sig = inspect.signature(validate_only)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "json_path" in params


def test_validate_only_return_annotation_tuple():
    import inspect

    sig = inspect.signature(validate_only)
    ret = sig.return_annotation
    assert "tuple" in str(ret).lower()


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_imports_json():
    from app import pipeline as mod

    assert hasattr(mod, "json")


def test_module_imports_path():
    from app import pipeline as mod

    assert hasattr(mod, "Path")


def test_module_imports_any():
    from app import pipeline as mod

    assert hasattr(mod, "Any")


def test_module_imports_structural_chunker():
    from app import pipeline as mod

    assert hasattr(mod, "StructuralChunker")


def test_module_imports_compute_file_hash():
    from app import pipeline as mod

    assert hasattr(mod, "compute_file_hash")


def test_module_imports_document():
    from app import pipeline as mod

    assert hasattr(mod, "Document")


def test_module_imports_error_record():
    from app import pipeline as mod

    assert hasattr(mod, "ErrorRecord")


def test_module_imports_parser():
    from app import pipeline as mod

    assert hasattr(mod, "Parser")


def test_module_imports_parser_error():
    from app import pipeline as mod

    assert hasattr(mod, "ParserError")


def test_module_imports_fallback_parser():
    from app import pipeline as mod

    assert hasattr(mod, "FallbackParser")


def test_module_imports_html_parser():
    from app import pipeline as mod

    assert hasattr(mod, "HtmlParser")


def test_module_imports_ipynb_parser():
    from app import pipeline as mod

    assert hasattr(mod, "IpynbParser")


def test_module_imports_kreuzberg_parser():
    from app import pipeline as mod

    assert hasattr(mod, "KreuzbergParser")


def test_module_imports_markdown_parser():
    from app import pipeline as mod

    assert hasattr(mod, "MarkdownParser")


def test_module_imports_text_parser():
    from app import pipeline as mod

    assert hasattr(mod, "TextParser")


def test_module_imports_schema_validation_error():
    from app import pipeline as mod

    assert hasattr(mod, "SchemaValidationError")


def test_module_imports_validate():
    from app import pipeline as mod

    assert hasattr(mod, "validate")


def test_module_has_get_parser():
    from app import pipeline as mod

    assert hasattr(mod, "get_parser")


def test_module_has_image_output_dir_for():
    from app import pipeline as mod

    assert hasattr(mod, "image_output_dir_for")


def test_module_has_process_single():
    from app import pipeline as mod

    assert hasattr(mod, "process_single")


def test_module_has_validate_only():
    from app import pipeline as mod

    assert hasattr(mod, "validate_only")


def test_module_all_is_list():
    from app import pipeline as mod

    assert isinstance(mod.__all__, list)


def test_module_all_length_four():
    from app import pipeline as mod

    assert len(mod.__all__) == 4


def test_module_all_exact_set():
    from app import pipeline as mod

    assert set(mod.__all__) == {
        "get_parser",
        "image_output_dir_for",
        "process_single",
        "validate_only",
    }


def test_module_all_excludes_internal():
    from app import pipeline as mod

    # 没有内部 helper（全 public）
    for item in mod.__all__:
        assert not item.startswith("_")


def test_module_callables():
    from app import pipeline as mod

    assert callable(mod.get_parser)
    assert callable(mod.image_output_dir_for)
    assert callable(mod.process_single)
    assert callable(mod.validate_only)


def test_module_docstring_present():
    from app import pipeline as mod

    assert mod.__doc__ is not None


def test_module_docstring_mentions_pipeline():
    from app import pipeline as mod

    doc = mod.__doc__
    assert "Pipeline" in doc or "pipeline" in doc.lower()


def test_module_docstring_mentions_validate():
    """docstring 应提及 Schema 校验。"""
    from app import pipeline as mod

    doc = mod.__doc__
    assert "校验" in doc or "validate" in doc.lower() or "Schema" in doc


def test_module_uses_future_annotations():
    import ast

    from app import pipeline as mod

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
# get_parser 签名深度
# =========================================================================


def test_get_parser_signature_two_params():
    import inspect

    sig = inspect.signature(get_parser)
    params = list(sig.parameters.keys())
    assert "name" in params
    assert "image_output_dir" in params


def test_get_parser_name_no_default():
    import inspect

    sig = inspect.signature(get_parser)
    assert sig.parameters["name"].default is inspect.Parameter.empty


def test_get_parser_image_output_dir_default_none():
    import inspect

    sig = inspect.signature(get_parser)
    assert sig.parameters["image_output_dir"].default is None


# =========================================================================
# image_output_dir_for 签名深度
# =========================================================================


def test_image_output_dir_for_signature_two_params():
    import inspect

    sig = inspect.signature(image_output_dir_for)
    params = list(sig.parameters.keys())
    assert "output_path" in params
    assert "source_hash" in params


def test_image_output_dir_for_output_path_no_default():
    """output_path 是必需参数（无默认值）。"""
    import inspect

    sig = inspect.signature(image_output_dir_for)
    assert sig.parameters["output_path"].default is inspect.Parameter.empty


def test_image_output_dir_for_source_hash_no_default():
    import inspect

    sig = inspect.signature(image_output_dir_for)
    assert sig.parameters["source_hash"].default is inspect.Parameter.empty


def test_image_output_dir_for_return_annotation_path_or_none():
    import inspect

    sig = inspect.signature(image_output_dir_for)
    ret = sig.return_annotation
    assert "Path" in str(ret) and "None" in str(ret)
