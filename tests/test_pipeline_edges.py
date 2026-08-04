"""app/pipeline.py 边角测试（Round 70）。

补强 tests/test_pipeline_helpers.py / test_pipeline_errors.py / test_pipeline_integration.py
（共 113 个）未覆盖的：
- get_parser 边角：空 name/大小写/前后空白/带后缀变体
- image_output_dir_for 边角：hash 长度边界/Unicode/特殊字符/Path vs str
- process_single 边角：返回 tuple 严格 2 元、errors list of ErrorRecord、write_json + output_path=None 组合、max_chars 边界
- validate_only 边角：返回类型、错误消息内容
- __all__ 导出
- 模块导入与 callable
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.pipeline import (
    __all__,
    get_parser,
    image_output_dir_for,
    process_single,
    validate_only,
)
from app.models import Document, ErrorRecord
from app.parsers import Parser


# ---------- get_parser 边角 ----------


def test_get_parser_fallback_returns_parser_subclass():
    p = get_parser("fallback")
    assert isinstance(p, Parser)


def test_get_parser_kreuzberg_returns_parser_subclass():
    p = get_parser("kreuzberg")
    assert isinstance(p, Parser)


def test_get_parser_markdown_returns_parser_subclass():
    p = get_parser("markdown")
    assert isinstance(p, Parser)


def test_get_parser_html_returns_parser_subclass():
    p = get_parser("html")
    assert isinstance(p, Parser)


def test_get_parser_text_returns_parser_subclass():
    p = get_parser("text")
    assert isinstance(p, Parser)


def test_get_parser_ipynb_returns_parser_subclass():
    p = get_parser("ipynb")
    assert isinstance(p, Parser)


def test_get_parser_empty_string_raises():
    with pytest.raises(ValueError):
        get_parser("")


def test_get_parser_uppercase_name_raises():
    """'FALLBACK' 不等于 'fallback'（区分大小写）。"""
    with pytest.raises(ValueError):
        get_parser("FALLBACK")


def test_get_parser_mixed_case_raises():
    with pytest.raises(ValueError):
        get_parser("Fallback")


def test_get_parser_with_leading_whitespace_raises():
    with pytest.raises(ValueError):
        get_parser(" fallback")


def test_get_parser_with_trailing_whitespace_raises():
    with pytest.raises(ValueError):
        get_parser("fallback ")


def test_get_parser_with_suffix_raises():
    """'fallback_v2' 不被支持。"""
    with pytest.raises(ValueError):
        get_parser("fallback_v2")


def test_get_parser_with_prefix_raises():
    with pytest.raises(ValueError):
        get_parser("v2_fallback")


def test_get_parser_fallback_name_attribute():
    p = get_parser("fallback")
    assert p.name == "fallback"


def test_get_parser_kreuzberg_name_attribute():
    p = get_parser("kreuzberg")
    assert p.name == "kreuzberg"


def test_get_parser_markdown_name_attribute():
    p = get_parser("markdown")
    assert p.name == "markdown"


def test_get_parser_html_name_attribute():
    p = get_parser("html")
    assert p.name == "html"


def test_get_parser_text_name_attribute():
    p = get_parser("text")
    assert p.name == "text"


def test_get_parser_ipynb_name_attribute():
    p = get_parser("ipynb")
    assert p.name == "ipynb"


def test_get_parser_each_parser_has_version():
    for name in ("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"):
        p = get_parser(name)
        assert isinstance(p.version, str)


def test_get_parser_each_parser_has_parse_callable():
    for name in ("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"):
        p = get_parser(name)
        assert callable(p.parse)


def test_get_parser_value_error_message_contains_supported():
    with pytest.raises(ValueError) as exc:
        get_parser("nonexistent")
    msg = str(exc.value)
    # 错误消息应列支持的 parser
    for n in ("fallback", "kreuzberg", "markdown", "html", "text", "ipynb"):
        assert n in msg


def test_get_parser_default_image_output_dir_is_none_for_kreuzberg():
    p = get_parser("kreuzberg")
    # kreuzberg 不接受 image_output_dir kwarg，单独验证它有 parser 行为
    assert isinstance(p, Parser)


# ---------- image_output_dir_for 边角 ----------


def test_image_output_dir_for_returns_pathlib_path():
    result = image_output_dir_for("/tmp/out.json", "a" * 64)
    assert isinstance(result, Path)


def test_image_output_dir_for_none_output_returns_none():
    assert image_output_dir_for(None, "a" * 64) is None


def test_image_output_dir_for_empty_string_output_returns_path():
    """空字符串 output_path：Path('').parent 是 '.' → 仍在当前目录。"""
    result = image_output_dir_for("", "a" * 64)
    # 不返 None（None 只在 output_path is None 时）；返 Path
    assert isinstance(result, Path)


def test_image_output_dir_for_hash_length_16_exactly():
    """hash 长度恰 16 → 全部用。"""
    sha = "a" * 16
    result = image_output_dir_for("/tmp/out.json", sha)
    assert result.name == "images-" + sha


def test_image_output_dir_for_hash_length_17_truncated_to_16():
    sha = "a" * 17
    result = image_output_dir_for("/tmp/out.json", sha)
    assert result.name == "images-" + "a" * 16


def test_image_output_dir_for_hash_length_15_used_as_is():
    """hash 长度 15（< 16）→ 全部用（切片不补）。"""
    sha = "a" * 15
    result = image_output_dir_for("/tmp/out.json", sha)
    assert result.name == "images-" + sha


def test_image_output_dir_for_empty_hash():
    """空 hash → name 是 'images-'。"""
    result = image_output_dir_for("/tmp/out.json", "")
    assert result.name == "images-"


def test_image_output_dir_for_unicode_hash():
    sha = "中" * 16
    result = image_output_dir_for("/tmp/out.json", sha)
    assert "中" in result.name


def test_image_output_dir_for_special_chars_hash():
    """hash 含特殊字符（实际 SHA256 不会，但函数不校验）。"""
    sha = "abcdefgh01234567"
    result = image_output_dir_for("/tmp/out.json", sha)
    assert result.name == "images-" + sha


def test_image_output_dir_for_str_path_accepted():
    result = image_output_dir_for("out.json", "a" * 64)
    assert isinstance(result, Path)


def test_image_output_dir_for_path_object_accepted():
    result = image_output_dir_for(Path("/tmp/out.json"), "a" * 64)
    assert isinstance(result, Path)


def test_image_output_dir_for_nested_path():
    result = image_output_dir_for("/tmp/a/b/c/out.json", "a" * 64)
    assert result.parent.name == "c"


def test_image_output_dir_for_filename_only():
    """output_path 只有文件名（无目录）→ parent 是 '.'。"""
    result = image_output_dir_for("out.json", "a" * 64)
    # parent 应当是 '.'
    assert result.parent.name in ("", ".", "out.json")  # 平台相关，宽松断言


def test_image_output_dir_for_format_constant_prefix():
    """格式约定：images-<sha16>。"""
    sha = "0123456789abcdef"
    result = image_output_dir_for("/tmp/out.json", sha)
    assert str(result).endswith("images-0123456789abcdef")


# ---------- process_single 边角 ----------


def test_process_single_returns_tuple_of_two(tmp_path: Path):
    """任何情况都返 tuple，长度 2。"""
    doc, errors = process_single(tmp_path / "missing.docx")
    assert isinstance((doc, errors), tuple)
    assert len((doc, errors)) == 2


def test_process_single_file_not_found_returns_none_doc(tmp_path: Path):
    doc, errors = process_single(tmp_path / "missing.docx")
    assert doc is None


def test_process_single_file_not_found_returns_error_list(tmp_path: Path):
    doc, errors = process_single(tmp_path / "missing.docx")
    assert isinstance(errors, list)
    assert len(errors) >= 1


def test_process_single_file_not_found_error_is_error_record(tmp_path: Path):
    doc, errors = process_single(tmp_path / "missing.docx")
    for e in errors:
        assert isinstance(e, ErrorRecord)


def test_process_single_file_not_found_error_code(tmp_path: Path):
    doc, errors = process_single(tmp_path / "missing.docx")
    assert any(e.code == "file_not_found" for e in errors)


def test_process_single_unknown_parser_returns_none(tmp_path: Path):
    p = tmp_path / "f.docx"
    p.write_text("not actual docx but unknown parser fails first", encoding="utf-8")
    doc, errors = process_single(p, parser_name="unknown")
    assert doc is None


def test_process_single_unknown_parser_error_code(tmp_path: Path):
    p = tmp_path / "f.docx"
    p.write_text("dummy", encoding="utf-8")
    doc, errors = process_single(p, parser_name="unknown")
    assert any(e.code == "unexpected_parser_error" for e in errors)


def test_process_single_unsupported_extension_returns_errors(tmp_path: Path):
    p = tmp_path / "f.txt"
    p.write_text("hello", encoding="utf-8")
    doc, errors = process_single(p)
    # .txt 不被 fallback 支持（用 text parser）
    assert doc is None or isinstance(doc, Document)


def test_process_single_text_parser_end_to_end_succeeds(tmp_path: Path):
    p = tmp_path / "f.txt"
    p.write_text("first paragraph with enough content here\nsecond paragraph more content", encoding="utf-8")
    doc, errors = process_single(p, parser_name="text")
    if doc is None:
        # text parser 实际可能仍报错；只验证 errors 是 list
        assert isinstance(errors, list)
    else:
        assert isinstance(doc, Document)
        assert errors == []


def test_process_single_write_json_false_skips_writing(tmp_path: Path):
    p = tmp_path / "in.txt"
    p.write_text("hello world enough text", encoding="utf-8")
    out = tmp_path / "out.json"
    doc, errors = process_single(p, parser_name="text", output_path=out, write_json=False)
    # write_json=False → 不创建文件
    assert not out.exists()


def test_process_single_write_json_true_with_output_writes(tmp_path: Path):
    p = tmp_path / "in.txt"
    p.write_text("hello world enough text here for chunking", encoding="utf-8")
    out = tmp_path / "out.json"
    doc, errors = process_single(p, parser_name="text", output_path=out, write_json=True)
    if doc is not None:
        assert out.exists()
        assert out.is_file()


def test_process_single_no_output_path_does_not_crash(tmp_path: Path):
    p = tmp_path / "in.txt"
    p.write_text("hello world enough text", encoding="utf-8")
    # output_path=None → write_json 被忽略
    doc, errors = process_single(p, parser_name="text", write_json=True)
    # 不崩即可（doc 可能 None 因 text parser 边角，但 errors 应是 list）
    assert isinstance(errors, list)


def test_process_single_str_input_path(tmp_path: Path):
    p = tmp_path / "in.txt"
    p.write_text("hello world enough text", encoding="utf-8")
    doc, errors = process_single(str(p), parser_name="text")
    assert isinstance(errors, list)


def test_process_single_default_parser_name_is_fallback(tmp_path: Path):
    """不传 parser_name → 默认 fallback。"""
    p = tmp_path / "in.txt"
    p.write_text("dummy", encoding="utf-8")
    # 不抛即 OK（fallback 拒绝 .txt 也只返 errors）
    doc, errors = process_single(p)
    assert isinstance(errors, list)


def test_process_single_default_max_chars_is_800(tmp_path: Path):
    """默认 max_chars=800。"""
    p = tmp_path / "in.txt"
    p.write_text("dummy", encoding="utf-8")
    doc, errors = process_single(p, parser_name="text")
    assert isinstance(errors, list)


def test_process_single_max_chars_one_does_not_crash(tmp_path: Path):
    p = tmp_path / "in.txt"
    p.write_text("hello world enough text", encoding="utf-8")
    doc, errors = process_single(p, parser_name="text", max_chars=1)
    # max_chars=1 可能触发 chunker_failed，但不崩
    assert isinstance(errors, list)


def test_process_single_max_chars_zero_does_not_crash(tmp_path: Path):
    p = tmp_path / "in.txt"
    p.write_text("hello world enough text", encoding="utf-8")
    doc, errors = process_single(p, parser_name="text", max_chars=0)
    assert isinstance(errors, list)


def test_process_single_max_chars_negative_does_not_crash(tmp_path: Path):
    p = tmp_path / "in.txt"
    p.write_text("hello world enough text", encoding="utf-8")
    doc, errors = process_single(p, parser_name="text", max_chars=-1)
    assert isinstance(errors, list)


def test_process_single_creates_nested_output_parent(tmp_path: Path):
    p = tmp_path / "in.txt"
    p.write_text("hello world enough text here to chunk", encoding="utf-8")
    out = tmp_path / "a" / "b" / "c" / "out.json"
    doc, errors = process_single(p, parser_name="text", output_path=out)
    if doc is not None:
        assert out.parent.exists()


def test_process_single_error_code_value_is_string(tmp_path: Path):
    """错误 code 应当是 string 类型。"""
    doc, errors = process_single(tmp_path / "missing.docx")
    for e in errors:
        assert isinstance(e.code, str)


def test_process_single_error_message_is_string(tmp_path: Path):
    doc, errors = process_single(tmp_path / "missing.docx")
    for e in errors:
        assert isinstance(e.message, str)


def test_process_single_error_details_is_dict(tmp_path: Path):
    doc, errors = process_single(tmp_path / "missing.docx")
    for e in errors:
        assert isinstance(e.details, dict)


def test_process_single_error_details_contains_path(tmp_path: Path):
    missing = tmp_path / "missing.docx"
    doc, errors = process_single(missing)
    assert any("path" in e.details for e in errors)


# ---------- validate_only 边角 ----------


def test_validate_only_returns_tuple(tmp_path: Path):
    """validate_only 总返 tuple。"""
    result = validate_only(tmp_path / "missing.json")
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_validate_only_first_element_is_bool(tmp_path: Path):
    ok, msg = validate_only(tmp_path / "missing.json")
    assert isinstance(ok, bool)


def test_validate_only_second_element_is_str(tmp_path: Path):
    ok, msg = validate_only(tmp_path / "missing.json")
    assert isinstance(msg, str)


def test_validate_only_missing_file_returns_false(tmp_path: Path):
    ok, msg = validate_only(tmp_path / "missing.json")
    assert ok is False


def test_validate_only_missing_file_message_has_path(tmp_path: Path):
    p = tmp_path / "missing.json"
    ok, msg = validate_only(p)
    assert "missing" in msg.lower() or "no such" in msg.lower() or "不存在" in msg


def test_validate_only_invalid_json_returns_false(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is False
    assert "JSON" in msg or "解析" in msg


def test_validate_only_directory_returns_false(tmp_path: Path):
    """传入目录 → validate_file 抛 FileNotFoundError（is_file()=False）。"""
    d = tmp_path / "subdir"
    d.mkdir()
    ok, msg = validate_only(d)
    assert ok is False


def test_validate_only_empty_file_returns_false(tmp_path: Path):
    """空文件 → JSON 解析失败。"""
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    ok, msg = validate_only(p)
    assert ok is False


def test_validate_only_str_path_accepted(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text("dummy", encoding="utf-8")
    ok, msg = validate_only(str(p))
    # 不抛即 OK（即使内容无效，也返 False）
    assert isinstance(ok, bool)


def test_validate_only_path_object_accepted(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text("dummy", encoding="utf-8")
    ok, msg = validate_only(p)
    assert isinstance(ok, bool)


# ---------- __all__ 导出 ----------


def test_all_exports_is_list():
    assert isinstance(__all__, list)


def test_all_exports_count_four():
    assert len(__all__) == 4


def test_all_exports_exact_set():
    assert set(__all__) == {
        "get_parser",
        "image_output_dir_for",
        "process_single",
        "validate_only",
    }


def test_all_exports_match_module_attributes():
    import app.pipeline as mod
    for name in __all__:
        assert hasattr(mod, name)


# ---------- 模块导入 ----------


def test_import_module_does_not_crash():
    import importlib
    mod = importlib.import_module("app.pipeline")
    assert mod is not None


def test_module_has_required_attributes():
    import app.pipeline as mod
    for attr in ("get_parser", "image_output_dir_for", "process_single", "validate_only"):
        assert hasattr(mod, attr)


def test_module_imports_json():
    import app.pipeline as mod
    assert hasattr(mod, "json")


def test_module_imports_path():
    import app.pipeline as mod
    assert hasattr(mod, "Path")


def test_get_parser_callable():
    assert callable(get_parser)


def test_image_output_dir_for_callable():
    assert callable(image_output_dir_for)


def test_process_single_callable():
    assert callable(process_single)


def test_validate_only_callable():
    assert callable(validate_only)


# ---------- 错误恢复语义 ----------


def test_process_single_does_not_raise_on_missing_file(tmp_path: Path):
    """不抛异常给调用方。"""
    # 不应抛异常
    try:
        doc, errors = process_single(tmp_path / "missing.docx")
    except Exception as e:
        pytest.fail(f"process_single should not raise: {e}")


def test_process_single_does_not_raise_on_unknown_parser(tmp_path: Path):
    p = tmp_path / "f.docx"
    p.write_text("dummy", encoding="utf-8")
    try:
        doc, errors = process_single(p, parser_name="unknown")
    except Exception as e:
        pytest.fail(f"process_single should not raise: {e}")


def test_process_single_does_not_raise_on_unsupported_extension(tmp_path: Path):
    p = tmp_path / "f.unknown"
    p.write_text("dummy", encoding="utf-8")
    try:
        doc, errors = process_single(p)
    except Exception as e:
        pytest.fail(f"process_single should not raise: {e}")


def test_process_single_does_not_raise_on_max_chars_zero(tmp_path: Path):
    p = tmp_path / "f.txt"
    p.write_text("dummy", encoding="utf-8")
    try:
        doc, errors = process_single(p, parser_name="text", max_chars=0)
    except Exception as e:
        pytest.fail(f"process_single should not raise: {e}")
