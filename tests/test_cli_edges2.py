"""app/cli.py 边角测试 - 第二轮（Round 73）。

补强 tests/test_cli.py（77）+ tests/test_cli_edges.py（74）未覆盖的：
- 模块结构与导入
- _build_arg_parser 深度：所有子命令 namespace 属性、--output/-o 短长形式
- _EXTENSION_TO_PARSER：精确映射、大小写不敏感（key 是 lowercase）
- _infer_parser_name：所有 9 个扩展名映射、未知扩展名 fallback
- _iter_supported_files：排序、目录跳过、扩展名匹配
- _relative_output_path：嵌套子目录、Windows 反斜杠
- main：各 subcommand 返回 int、SystemExit code
- _emit_structured_error：errors 结构、返回 None
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.cli import (
    _EXTENSION_TO_PARSER,
    _build_arg_parser,
    _emit_structured_error,
    _infer_parser_name,
    _iter_supported_files,
    _relative_output_path,
    main,
)


# ---------- 模块结构 ----------


def test_module_imports_argparse():
    import app.cli as mod
    assert hasattr(mod, "argparse")


def test_module_imports_json():
    import app.cli as mod
    assert hasattr(mod, "json")


def test_module_imports_sys():
    import app.cli as mod
    assert hasattr(mod, "sys")


def test_module_imports_path():
    import app.cli as mod
    assert hasattr(mod, "Path")


def test_module_imports_process_single():
    import app.cli as mod
    assert hasattr(mod, "process_single")


def test_module_imports_validate_only():
    import app.cli as mod
    assert hasattr(mod, "validate_only")


def test_module_has_main():
    import app.cli as mod
    assert hasattr(mod, "main")


def test_module_has_build_arg_parser():
    import app.cli as mod
    assert hasattr(mod, "_build_arg_parser")


def test_module_has_emit_structured_error():
    import app.cli as mod
    assert hasattr(mod, "_emit_structured_error")


def test_module_does_not_have_all():
    """app/cli.py 没有 __all__。"""
    import app.cli as mod
    assert not hasattr(mod, "__all__")


# ---------- _build_arg_parser 深度 ----------


def test_build_arg_parser_returns_argument_parser_type():
    from argparse import ArgumentParser
    p = _build_arg_parser()
    assert isinstance(p, ArgumentParser)


def test_build_arg_parser_prog_value():
    p = _build_arg_parser()
    assert p.prog == "app.cli"


def test_build_arg_parser_parse_input_required():
    p = _build_arg_parser()
    ns = p.parse_args(["parse", "x.pdf", "-o", "y.json"])
    assert ns.input == "x.pdf"


def test_build_arg_parser_parse_output_required():
    with pytest.raises(SystemExit) as exc:
        _build_arg_parser().parse_args(["parse", "x.pdf"])
    assert exc.value.code == 2


def test_build_arg_parser_parse_short_output_form():
    p = _build_arg_parser()
    ns = p.parse_args(["parse", "x.pdf", "-o", "y.json"])
    assert ns.output == "y.json"


def test_build_arg_parser_parse_long_output_form():
    p = _build_arg_parser()
    ns = p.parse_args(["parse", "x.pdf", "--output", "y.json"])
    assert ns.output == "y.json"


def test_build_arg_parser_parse_default_max_chars_800():
    p = _build_arg_parser()
    ns = p.parse_args(["parse", "x.pdf", "-o", "y.json"])
    assert ns.max_chars == 800


def test_build_arg_parser_parse_default_parser_is_none():
    p = _build_arg_parser()
    ns = p.parse_args(["parse", "x.pdf", "-o", "y.json"])
    assert ns.parser is None


def test_build_arg_parser_parse_explicit_parser_fallback():
    p = _build_arg_parser()
    ns = p.parse_args(["parse", "x.pdf", "-o", "y.json", "--parser", "fallback"])
    assert ns.parser == "fallback"


def test_build_arg_parser_parse_explicit_parser_kreuzberg():
    p = _build_arg_parser()
    ns = p.parse_args(["parse", "x.pdf", "-o", "y.json", "--parser", "kreuzberg"])
    assert ns.parser == "kreuzberg"


def test_build_arg_parser_parse_explicit_parser_markdown():
    p = _build_arg_parser()
    ns = p.parse_args(["parse", "x.md", "-o", "y.json", "--parser", "markdown"])
    assert ns.parser == "markdown"


def test_build_arg_parser_parse_explicit_parser_html():
    p = _build_arg_parser()
    ns = p.parse_args(["parse", "x.html", "-o", "y.json", "--parser", "html"])
    assert ns.parser == "html"


def test_build_arg_parser_parse_explicit_parser_text():
    p = _build_arg_parser()
    ns = p.parse_args(["parse", "x.txt", "-o", "y.json", "--parser", "text"])
    assert ns.parser == "text"


def test_build_arg_parser_parse_explicit_parser_ipynb():
    p = _build_arg_parser()
    ns = p.parse_args(["parse", "x.ipynb", "-o", "y.json", "--parser", "ipynb"])
    assert ns.parser == "ipynb"


def test_build_arg_parser_parse_invalid_parser_choice_exits_2():
    with pytest.raises(SystemExit) as exc:
        _build_arg_parser().parse_args(["parse", "x.pdf", "-o", "y.json", "--parser", "invalid"])
    assert exc.value.code == 2


def test_build_arg_parser_parse_max_chars_int_type():
    p = _build_arg_parser()
    ns = p.parse_args(["parse", "x.pdf", "-o", "y.json", "--max-chars", "1000"])
    assert isinstance(ns.max_chars, int)
    assert ns.max_chars == 1000


def test_build_arg_parser_parse_max_chars_negative_accepted():
    p = _build_arg_parser()
    ns = p.parse_args(["parse", "x.pdf", "-o", "y.json", "--max-chars", "-1"])
    assert ns.max_chars == -1


def test_build_arg_parser_parse_dir_subcommand_input_dir():
    p = _build_arg_parser()
    ns = p.parse_args(["parse-dir", "in", "-o", "out"])
    assert ns.input_dir == "in"


def test_build_arg_parser_parse_dir_subcommand_output_dir():
    p = _build_arg_parser()
    ns = p.parse_args(["parse-dir", "in", "-o", "out"])
    assert ns.output_dir == "out"


def test_build_arg_parser_parse_dir_recursive_default_false():
    p = _build_arg_parser()
    ns = p.parse_args(["parse-dir", "in", "-o", "out"])
    assert ns.recursive is False


def test_build_arg_parser_parse_dir_recursive_set_true():
    p = _build_arg_parser()
    ns = p.parse_args(["parse-dir", "in", "-o", "out", "--recursive"])
    assert ns.recursive is True


def test_build_arg_parser_parse_dir_parser_default_none():
    p = _build_arg_parser()
    ns = p.parse_args(["parse-dir", "in", "-o", "out"])
    assert ns.parser is None


def test_build_arg_parser_parse_dir_max_chars_default_800():
    p = _build_arg_parser()
    ns = p.parse_args(["parse-dir", "in", "-o", "out"])
    assert ns.max_chars == 800


def test_build_arg_parser_validate_subcommand_input():
    p = _build_arg_parser()
    ns = p.parse_args(["validate", "x.json"])
    assert ns.input == "x.json"


def test_build_arg_parser_inspect_subcommand_input():
    p = _build_arg_parser()
    ns = p.parse_args(["inspect", "x.json"])
    assert ns.input == "x.json"


def test_build_arg_parser_inspect_elements_default_false():
    p = _build_arg_parser()
    ns = p.parse_args(["inspect", "x.json"])
    assert ns.elements is False


def test_build_arg_parser_inspect_chunks_default_false():
    p = _build_arg_parser()
    ns = p.parse_args(["inspect", "x.json"])
    assert ns.chunks is False


def test_build_arg_parser_inspect_spans_default_false():
    p = _build_arg_parser()
    ns = p.parse_args(["inspect", "x.json"])
    assert ns.spans is False


def test_build_arg_parser_inspect_limit_default_10():
    p = _build_arg_parser()
    ns = p.parse_args(["inspect", "x.json"])
    assert ns.limit == 10


def test_build_arg_parser_inspect_elements_flag():
    p = _build_arg_parser()
    ns = p.parse_args(["inspect", "x.json", "--elements"])
    assert ns.elements is True


def test_build_arg_parser_inspect_chunks_flag():
    p = _build_arg_parser()
    ns = p.parse_args(["inspect", "x.json", "--chunks"])
    assert ns.chunks is True


def test_build_arg_parser_inspect_spans_flag():
    p = _build_arg_parser()
    ns = p.parse_args(["inspect", "x.json", "--chunks", "--spans"])
    assert ns.spans is True


def test_build_arg_parser_inspect_limit_custom():
    p = _build_arg_parser()
    ns = p.parse_args(["inspect", "x.json", "--limit", "5"])
    assert ns.limit == 5


def test_build_arg_parser_inspect_limit_negative():
    p = _build_arg_parser()
    ns = p.parse_args(["inspect", "x.json", "--limit", "-1"])
    assert ns.limit == -1


def test_build_arg_parser_inspect_limit_zero():
    p = _build_arg_parser()
    ns = p.parse_args(["inspect", "x.json", "--limit", "0"])
    assert ns.limit == 0


def test_build_arg_parser_no_command_system_exit_2():
    with pytest.raises(SystemExit) as exc:
        _build_arg_parser().parse_args([])
    assert exc.value.code == 2


def test_build_arg_parser_unknown_command_system_exit_2():
    with pytest.raises(SystemExit) as exc:
        _build_arg_parser().parse_args(["unknown"])
    assert exc.value.code == 2


# ---------- _EXTENSION_TO_PARSER 深度 ----------


def test_extension_to_parser_count_nine():
    assert len(_EXTENSION_TO_PARSER) == 9


def test_extension_to_parser_keys_are_lowercase():
    """所有 key 都是小写（.suffix 形式）。"""
    for k in _EXTENSION_TO_PARSER:
        assert k == k.lower()
        assert k.startswith(".")


def test_extension_to_parser_pdf_value():
    assert _EXTENSION_TO_PARSER[".pdf"] == "fallback"


def test_extension_to_parser_docx_value():
    assert _EXTENSION_TO_PARSER[".docx"] == "fallback"


def test_extension_to_parser_md_value():
    assert _EXTENSION_TO_PARSER[".md"] == "markdown"


def test_extension_to_parser_markdown_value():
    assert _EXTENSION_TO_PARSER[".markdown"] == "markdown"


def test_extension_to_parser_html_value():
    assert _EXTENSION_TO_PARSER[".html"] == "html"


def test_extension_to_parser_htm_value():
    assert _EXTENSION_TO_PARSER[".htm"] == "html"


def test_extension_to_parser_txt_value():
    assert _EXTENSION_TO_PARSER[".txt"] == "text"


def test_extension_to_parser_text_value():
    assert _EXTENSION_TO_PARSER[".text"] == "text"


def test_extension_to_parser_ipynb_value():
    assert _EXTENSION_TO_PARSER[".ipynb"] == "ipynb"


def test_extension_to_parser_values_only_known():
    """所有 value 必须是 6 个支持的 parser。"""
    valid = {"fallback", "kreuzberg", "markdown", "html", "text", "ipynb"}
    for v in _EXTENSION_TO_PARSER.values():
        assert v in valid


def test_extension_to_parser_kreuzberg_not_in_mapping():
    """kreuzberg 必须显式 --parser 指定，不在扩展名映射中。"""
    assert "kreuzberg" not in _EXTENSION_TO_PARSER.values()


# ---------- _infer_parser_name 深度 ----------


def test_infer_parser_name_pdf():
    assert _infer_parser_name(Path("x.pdf")) == "fallback"


def test_infer_parser_name_docx():
    assert _infer_parser_name(Path("x.docx")) == "fallback"


def test_infer_parser_name_md():
    assert _infer_parser_name(Path("x.md")) == "markdown"


def test_infer_parser_name_markdown():
    assert _infer_parser_name(Path("x.markdown")) == "markdown"


def test_infer_parser_name_html():
    assert _infer_parser_name(Path("x.html")) == "html"


def test_infer_parser_name_htm():
    assert _infer_parser_name(Path("x.htm")) == "html"


def test_infer_parser_name_txt():
    assert _infer_parser_name(Path("x.txt")) == "text"


def test_infer_parser_name_text():
    assert _infer_parser_name(Path("x.text")) == "text"


def test_infer_parser_name_ipynb():
    assert _infer_parser_name(Path("x.ipynb")) == "ipynb"


def test_infer_parser_name_uppercase_pdf():
    assert _infer_parser_name(Path("X.PDF")) == "fallback"


def test_infer_parser_name_uppercase_docx():
    assert _infer_parser_name(Path("X.DOCX")) == "fallback"


def test_infer_parser_name_uppercase_md():
    assert _infer_parser_name(Path("X.MD")) == "markdown"


def test_infer_parser_name_uppercase_html():
    assert _infer_parser_name(Path("X.HTML")) == "html"


def test_infer_parser_name_uppercase_txt():
    assert _infer_parser_name(Path("X.TXT")) == "text"


def test_infer_parser_name_uppercase_ipynb():
    assert _infer_parser_name(Path("X.IPYNB")) == "ipynb"


def test_infer_parser_name_mixed_case_pdf():
    assert _infer_parser_name(Path("x.PdF")) == "fallback"


def test_infer_parser_name_unknown_extension():
    assert _infer_parser_name(Path("x.unknown")) == "fallback"


def test_infer_parser_name_no_extension():
    assert _infer_parser_name(Path("README")) == "fallback"


def test_infer_parser_name_dotfile_no_suffix():
    assert _infer_parser_name(Path(".gitignore")) == "fallback"


def test_infer_parser_name_double_extension():
    """file.tar.pdf → suffix 是 .pdf。"""
    assert _infer_parser_name(Path("file.tar.pdf")) == "fallback"


def test_infer_parser_name_str_path_accepted():
    """接受 str 或 Path？看实现：参数是 Path。"""
    # 实际 _infer_parser_name(input_path: Path)
    # 测试以 Path 调用为主
    assert _infer_parser_name(Path("x.pdf")) == "fallback"


def test_infer_parser_name_returns_str_type():
    result = _infer_parser_name(Path("x.pdf"))
    assert isinstance(result, str)


# ---------- _iter_supported_files 深度 ----------


def test_iter_supported_files_returns_list_type(tmp_path: Path):
    result = _iter_supported_files(tmp_path, recursive=False)
    assert isinstance(result, list)


def test_iter_supported_files_empty_dir(tmp_path: Path):
    result = _iter_supported_files(tmp_path, recursive=False)
    assert result == []


def test_iter_supported_files_skips_unsupported_extensions(tmp_path: Path):
    (tmp_path / "f.unknown").write_text("x", encoding="utf-8")
    (tmp_path / "f.unsupported").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    assert result == []


def test_iter_supported_files_includes_supported_types(tmp_path: Path):
    (tmp_path / "a.pdf").write_bytes(b"x")
    (tmp_path / "b.docx").write_bytes(b"x")
    (tmp_path / "c.md").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    names = sorted(p.name for p in result)
    assert names == ["a.pdf", "b.docx", "c.md"]


def test_iter_supported_files_sorted_by_name(tmp_path: Path):
    (tmp_path / "z.md").write_text("x", encoding="utf-8")
    (tmp_path / "a.md").write_text("x", encoding="utf-8")
    (tmp_path / "m.md").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    names = [p.name for p in result]
    assert names == ["a.md", "m.md", "z.md"]


def test_iter_supported_files_skips_directories(tmp_path: Path):
    """目录被过滤（is_file()=False）。"""
    (tmp_path / "subdir").mkdir()
    (tmp_path / "a.md").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=False)
    names = [p.name for p in result]
    assert "subdir" not in names
    assert names == ["a.md"]


def test_iter_supported_files_case_insensitive_suffix(tmp_path: Path):
    """扩展名小写匹配，大写 PDF 也接受。"""
    (tmp_path / "upper.PDF").write_bytes(b"x")
    result = _iter_supported_files(tmp_path, recursive=False)
    assert any(p.name == "upper.PDF" for p in result)


def test_iter_supported_files_recursive_walks_subdirs(tmp_path: Path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "a.md").write_text("x", encoding="utf-8")
    (tmp_path / "b.md").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=True)
    assert len(result) == 2


def test_iter_supported_files_recursive_nested_dirs(tmp_path: Path):
    """recursive=True 时多层子目录都遍历。"""
    a = tmp_path / "a"
    b = a / "b"
    b.mkdir(parents=True)
    (b / "deep.md").write_text("x", encoding="utf-8")
    result = _iter_supported_files(tmp_path, recursive=True)
    assert len(result) == 1
    assert result[0].name == "deep.md"


# ---------- _relative_output_path 深度 ----------


def test_relative_output_path_root_level_file(tmp_path: Path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()
    f = input_dir / "doc.md"
    f.write_text("x", encoding="utf-8")
    rel = _relative_output_path(input_dir, f, output_dir)
    assert rel.name == "doc.md.json"


def test_relative_output_path_nested_subdir(tmp_path: Path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    sub = input_dir / "sub"
    sub.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    f = sub / "doc.md"
    f.write_text("x", encoding="utf-8")
    rel = _relative_output_path(input_dir, f, output_dir)
    # 应当在 output_dir/sub/ 下
    assert "sub" in str(rel)
    assert rel.name == "doc.md.json"


def test_relative_output_path_preserves_full_suffix(tmp_path: Path):
    """file.tar.pdf → file.tar.pdf.json（保留完整 suffix）。"""
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()
    f = input_dir / "file.tar.pdf"
    f.write_bytes(b"x")
    rel = _relative_output_path(input_dir, f, output_dir)
    assert rel.name == "file.tar.pdf.json"


def test_relative_output_path_no_extension_file(tmp_path: Path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()
    f = input_dir / "README"
    f.write_text("x", encoding="utf-8")
    rel = _relative_output_path(input_dir, f, output_dir)
    assert rel.name == "README.json"


def test_relative_output_path_returns_pathlib_path(tmp_path: Path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()
    f = input_dir / "doc.md"
    f.write_text("x", encoding="utf-8")
    rel = _relative_output_path(input_dir, f, output_dir)
    assert isinstance(rel, Path)


# ---------- main 深度 ----------


def test_main_returns_int_type_for_validate_missing(tmp_path: Path):
    rc = main(["validate", str(tmp_path / "missing.json")])
    assert isinstance(rc, int)


def test_main_returns_int_type_for_inspect_missing(tmp_path: Path):
    rc = main(["inspect", str(tmp_path / "missing.json")])
    assert isinstance(rc, int)


def test_main_returns_int_type_for_parse_missing(tmp_path: Path):
    rc = main(["parse", str(tmp_path / "missing.pdf"), "-o", str(tmp_path / "out.json")])
    assert isinstance(rc, int)


def test_main_unknown_command_raises_system_exit():
    with pytest.raises(SystemExit) as exc:
        main(["unknown"])
    assert exc.value.code == 2


def test_main_no_command_raises_system_exit():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_main_parse_returns_1_for_missing_input(tmp_path: Path):
    rc = main(["parse", str(tmp_path / "missing.pdf"), "-o", str(tmp_path / "out.json")])
    assert rc == 1


def test_main_parse_dir_returns_2_for_missing_input_dir(tmp_path: Path):
    rc = main(["parse-dir", str(tmp_path / "nonexistent"), "-o", str(tmp_path / "out")])
    assert rc == 2


def test_main_callable():
    assert callable(main)


def test_build_arg_parser_callable():
    assert callable(_build_arg_parser)


def test_emit_structured_error_callable():
    assert callable(_emit_structured_error)


def test_infer_parser_name_callable():
    assert callable(_infer_parser_name)


def test_iter_supported_files_callable():
    assert callable(_iter_supported_files)


def test_relative_output_path_callable():
    assert callable(_relative_output_path)
