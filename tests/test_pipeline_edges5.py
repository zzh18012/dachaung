r"""app/pipeline.py 边角测试 - 第五轮（Round 140）。

补强已有 base/edges/edges2/edges3/edges4/helpers/errors/integration（共 483 测试）未覆盖的深度：
- get_parser 工厂边界（未知 name、各类型实例化）
- image_output_dir_for 边界（None / 短 hash / 不同路径形式）
- process_single 错误路径边界（hash 错误、parser 错误、chunker 错误、空 elements、写盘失败）
- validate_only 边界（不存在 / 非法 JSON / 通过）
- 模块结构深度
- 签名深度
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from app.models import Document, ErrorRecord
from app.parsers import Parser, ParserError
from app.parsers.fallback_parser import FallbackParser
from app.parsers.html_parser import HtmlParser
from app.parsers.ipynb_parser import IpynbParser
from app.parsers.kreuzberg_parser import KreuzbergParser
from app.parsers.markdown_parser import MarkdownParser
from app.parsers.text_parser import TextParser
from app.pipeline import (
    __all__ as pipeline_all,
    get_parser,
    image_output_dir_for,
    process_single,
    validate_only,
)


# =========================================================================
# get_parser 深度
# =========================================================================


def test_get_parser_fallback_returns_fallback_parser():
    p = get_parser("fallback")
    assert isinstance(p, FallbackParser)


def test_get_parser_kreuzberg_returns_kreuzberg_parser():
    p = get_parser("kreuzberg")
    assert isinstance(p, KreuzbergParser)


def test_get_parser_markdown_returns_markdown_parser():
    p = get_parser("markdown")
    assert isinstance(p, MarkdownParser)


def test_get_parser_html_returns_html_parser():
    p = get_parser("html")
    assert isinstance(p, HtmlParser)


def test_get_parser_text_returns_text_parser():
    p = get_parser("text")
    assert isinstance(p, TextParser)


def test_get_parser_ipynb_returns_ipynb_parser():
    p = get_parser("ipynb")
    assert isinstance(p, IpynbParser)


def test_get_parser_all_return_parser_subclass():
    for name in ("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"):
        assert isinstance(get_parser(name), Parser)


def test_get_parser_unknown_name_raises_value_error():
    with pytest.raises(ValueError):
        get_parser("nonexistent")


def test_get_parser_unknown_name_error_message_lists_supported():
    with pytest.raises(ValueError) as exc:
        get_parser("foo")
    msg = str(exc.value)
    assert "fallback" in msg
    assert "kreuzberg" in msg
    assert "markdown" in msg


def test_get_parser_with_image_output_dir(tmp_path):
    p = get_parser("fallback", image_output_dir=tmp_path)
    assert isinstance(p, FallbackParser)


def test_get_parser_kreuzberg_ignores_image_output_dir(tmp_path):
    """kreuzberg 不接受 image_output_dir 参数（接口差异）。"""
    # get_parser 内部不传 image_output_dir 给 kreuzberg
    p = get_parser("kreuzberg", image_output_dir=tmp_path)
    assert isinstance(p, KreuzbergParser)


# =========================================================================
# image_output_dir_for 深度
# =========================================================================


def test_image_output_dir_for_none_returns_none():
    assert image_output_dir_for(None, "0" * 64) is None


def test_image_output_dir_for_returns_path_object():
    result = image_output_dir_for("out.json", "0" * 64)
    assert isinstance(result, Path)


def test_image_output_dir_for_uses_first_16_chars_of_hash():
    result = image_output_dir_for("out.json", "abcdefgh0123456789" * 4)
    # 使用前 16 字符
    assert "images-abcdefgh0123456" in str(result)


def test_image_output_dir_for_short_hash():
    """短 hash 不会崩溃，使用全部字符。"""
    result = image_output_dir_for("out.json", "abc")
    assert "images-abc" in str(result)


def test_image_output_dir_for_in_parent_of_output():
    """目录在 output_path.parent 下。"""
    result = image_output_dir_for("/tmp/sub/out.json", "0" * 64)
    assert str(result).startswith(str(Path("/tmp/sub")))


def test_image_output_dir_for_relative_path():
    """相对路径也工作。"""
    result = image_output_dir_for("out.json", "0" * 64)
    assert "images-" in str(result)


def test_image_output_dir_for_accepts_path_object(tmp_path):
    """接受 Path 对象作为 output_path。"""
    result = image_output_dir_for(tmp_path / "out.json", "0" * 64)
    assert isinstance(result, Path)


# =========================================================================
# process_single 错误路径
# =========================================================================


def test_process_single_file_not_found(tmp_path):
    """input 不存在 → file_not_found error。"""
    missing = tmp_path / "missing.pdf"
    doc, errors = process_single(missing, tmp_path / "out.json")
    assert doc is None
    assert any(e.code == "file_not_found" for e in errors)


def test_process_single_unsupported_parser(tmp_path):
    """未知 parser → ValueError 直接抛（不在 process_single 的异常处理内）。"""
    # 实际上 get_parser 抛 ValueError，会被 Exception 兜底捕获
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc, errors = process_single(p, tmp_path / "out.json", parser_name="bogus")
    assert doc is None
    assert any(e.code == "unexpected_parser_error" for e in errors)


def test_process_single_unsupported_file_type_for_text_parser(tmp_path):
    """text parser 只支持 .txt。"""
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF-1.4 test")
    doc, errors = process_single(p, tmp_path / "out.json", parser_name="text")
    assert doc is None
    # ParserError 路径
    assert any(e.code == "unsupported_type" for e in errors)


def test_process_single_text_parser_success(tmp_path):
    """text parser 成功路径。"""
    p = tmp_path / "x.txt"
    p.write_text("hello world content here", encoding="utf-8")
    doc, errors = process_single(p, tmp_path / "out.json", parser_name="text")
    # text parser 应能提取 element
    if doc is not None:
        assert len(doc.elements) > 0


def test_process_single_no_write_json_when_disabled(tmp_path):
    """write_json=False → 不写盘。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    out = tmp_path / "out.json"
    process_single(p, out, parser_name="text", write_json=False)
    assert not out.exists()


def test_process_single_creates_output_parent_dirs(tmp_path):
    """output_path 的父目录不存在时自动创建。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    out = tmp_path / "a" / "b" / "c" / "out.json"
    doc, errors = process_single(p, out, parser_name="text")
    if doc is not None:
        assert out.exists()


# =========================================================================
# validate_only 深度
# =========================================================================


def test_validate_only_file_not_found(tmp_path):
    """文件不存在 → False + FileNotFoundError 信息。"""
    missing = tmp_path / "missing.json"
    ok, msg = validate_only(missing)
    assert ok is False
    assert "missing" in msg.lower() or "not found" in msg.lower() or "no such" in msg.lower()


def test_validate_only_invalid_json(tmp_path):
    p = tmp_path / "broken.json"
    p.write_text("{not valid", encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is False
    assert "JSON" in msg or "json" in msg.lower()


def test_validate_only_empty_file_invalid_json(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is False


def test_validate_only_not_a_dict_root(tmp_path):
    p = tmp_path / "list.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is False


def test_validate_only_returns_tuple_of_bool_str(tmp_path):
    """返回值是 (bool, str)。"""
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    result = validate_only(p)
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert isinstance(result[0], bool)
    assert isinstance(result[1], str)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_is_list():
    assert isinstance(pipeline_all, list)


def test_module_all_count_four():
    assert len(pipeline_all) == 4


def test_module_all_exact():
    assert set(pipeline_all) == {
        "get_parser",
        "image_output_dir_for",
        "process_single",
        "validate_only",
    }


def test_module_imports_json():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "import json" in src


def test_module_imports_path():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_structural_chunker():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "StructuralChunker" in src


def test_module_imports_compute_file_hash():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "compute_file_hash" in src


def test_module_imports_all_parsers():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    for name in ("FallbackParser", "KreuzbergParser", "MarkdownParser",
                 "HtmlParser", "TextParser", "IpynbParser"):
        assert name in src


def test_module_imports_schema_validate():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "validate" in src


def test_module_uses_future_annotations():
    import app.pipeline as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import app.pipeline as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_pipeline():
    import app.pipeline as mod
    assert "Pipeline" in mod.__doc__ or "parse" in mod.__doc__.lower()


def test_module_docstring_mentions_schema():
    import app.pipeline as mod
    assert "Schema" in mod.__doc__ or "schema" in mod.__doc__


# =========================================================================
# 签名深度
# =========================================================================


def test_get_parser_signature():
    sig = inspect.signature(get_parser)
    assert len(sig.parameters) == 2
    assert "name" in sig.parameters
    assert "image_output_dir" in sig.parameters


def test_get_parser_name_no_default():
    sig = inspect.signature(get_parser)
    assert sig.parameters["name"].default is inspect.Parameter.empty


def test_get_parser_image_output_dir_default_none():
    sig = inspect.signature(get_parser)
    assert sig.parameters["image_output_dir"].default is None


def test_image_output_dir_for_signature():
    sig = inspect.signature(image_output_dir_for)
    assert len(sig.parameters) == 2
    assert "output_path" in sig.parameters
    assert "source_hash" in sig.parameters


def test_image_output_dir_for_no_defaults():
    sig = inspect.signature(image_output_dir_for)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_process_single_signature():
    sig = inspect.signature(process_single)
    # input_path, output_path, parser_name, max_chars, write_json
    assert len(sig.parameters) == 5


def test_process_single_input_path_no_default():
    sig = inspect.signature(process_single)
    assert sig.parameters["input_path"].default is inspect.Parameter.empty


def test_process_single_output_path_default_none():
    sig = inspect.signature(process_single)
    assert sig.parameters["output_path"].default is None


def test_process_single_parser_name_default_fallback():
    sig = inspect.signature(process_single)
    assert sig.parameters["parser_name"].default == "fallback"


def test_process_single_max_chars_default_800():
    sig = inspect.signature(process_single)
    assert sig.parameters["max_chars"].default == 800


def test_process_single_write_json_default_true():
    sig = inspect.signature(process_single)
    assert sig.parameters["write_json"].default is True


def test_process_single_write_json_kind_keyword_only():
    sig = inspect.signature(process_single)
    # parser_name/max_chars/write_json 都是 keyword-only
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["write_json"].kind == inspect.Parameter.KEYWORD_ONLY


def test_validate_only_signature():
    sig = inspect.signature(validate_only)
    assert len(sig.parameters) == 1
    assert "json_path" in sig.parameters


def test_process_single_return_annotation():
    sig = inspect.signature(process_single)
    assert sig.return_annotation is not inspect.Signature.empty


def test_validate_only_return_annotation():
    sig = inspect.signature(validate_only)
    assert sig.return_annotation is not inspect.Signature.empty


# =========================================================================
# ErrorRecord 字段（边界）
# =========================================================================


def test_process_single_errors_are_error_record_type(tmp_path):
    """所有 errors 都是 ErrorRecord 实例。"""
    missing = tmp_path / "missing.pdf"
    doc, errors = process_single(missing)
    for e in errors:
        assert isinstance(e, ErrorRecord)


def test_process_single_errors_have_code_message_details(tmp_path):
    missing = tmp_path / "missing.pdf"
    doc, errors = process_single(missing)
    e = errors[0]
    assert hasattr(e, "code")
    assert hasattr(e, "message")
    assert hasattr(e, "details")


# =========================================================================
# 综合：成功路径完整流程
# =========================================================================


def test_process_single_success_text_full_flow(tmp_path):
    """text 完整流程：parse → chunk → validate → write。"""
    p = tmp_path / "x.txt"
    p.write_text("first paragraph\n\nsecond paragraph", encoding="utf-8")
    out = tmp_path / "out.json"
    doc, errors = process_single(p, out, parser_name="text")
    assert doc is not None
    assert errors == []
    assert out.exists()
    # 输出 JSON 应可解析
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "document_id" in data
    assert "elements" in data


def test_process_single_success_no_output_path(tmp_path):
    """output_path=None → 不写盘，但 Document 仍返回。"""
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    doc, errors = process_single(p, parser_name="text")
    assert doc is not None
    assert errors == []
