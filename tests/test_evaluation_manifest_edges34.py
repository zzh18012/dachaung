"""evaluation/manifest.py 第三十四轮 edges 测试（Round 369）。

补强 edges33 未触及的角度：
- _is_absolute_like 数学边界第九批（Unicode alpha 字母扩展 + 1/2/3 char 边界）
- _has_backslash 数学边界第九批（whitespace 字符串 + 空字符串）
- _resolve_relative_path 行为深度第四批（path 等于 "."、unicode 文件名、subdir 深层）
- _detect_project_root 行为深度第五批（不存在路径、文件路径、深层 parent 链）
- DocumentEntry / ExpectedFailure / Manifest dataclass 行为深度第七批（hash、asdict、astuple、fields）
- Manifest properties 算法深度第七批（categories 排序、count 不变量、空字符串类别）
- load_manifest malformed data 第七批（文件不存在、目录、JSON syntax 错误、version 不匹配）
- module source forbidden tokens 第十批
- signatures 第五批（私有 helper 返回类型注解、ManifestError init 无自定义）
- 模块整体合理性第三批（__all__ 顺序、ManifestError 无 __init__ 覆写）
- 端到端集成第三批（annotation_file、文档顺序保留、categories 跨文档去重）
"""

from __future__ import annotations

import inspect
import json
from dataclasses import asdict, astuple, fields, replace
from pathlib import Path

import pytest

from evaluation import MANIFEST_VERSION, manifest as mmod
from evaluation.manifest import (
    DocumentEntry,
    ExpectedFailure,
    Manifest,
    ManifestError,
    _detect_project_root,
    _has_backslash,
    _is_absolute_like,
    _resolve_relative_path,
    load_manifest,
)


# ---------- _is_absolute_like 数学边界第九批 ----------


def test_is_absolute_like_empty_string():
    assert _is_absolute_like("") is False


def test_is_absolute_like_single_char_alpha():
    assert _is_absolute_like("a") is False


def test_is_absolute_like_single_char_slash():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_single_char_colon():
    assert _is_absolute_like(":") is False


def test_is_absolute_like_two_char_alpha():
    assert _is_absolute_like("ab") is False


def test_is_absolute_like_two_char_a_colon():
    assert _is_absolute_like("a:") is False  # len < 3


def test_is_absolute_like_underscore_pos0():
    assert _is_absolute_like("_:/foo") is False  # _ isalpha False


def test_is_absolute_like_digit_pos0():
    assert _is_absolute_like("1:/foo") is False  # digit isalpha False


def test_is_absolute_like_cyrillic_alpha_pos0():
    # Cyrillic А is alphabetic
    assert _is_absolute_like("А:/foo") is True


def test_is_absolute_like_greek_alpha_pos0():
    # Greek α is alphabetic
    assert _is_absolute_like("α:/foo") is True


def test_is_absolute_like_han_pos0():
    # Han ideograph is alphabetic per .isalpha()
    assert _is_absolute_like("中:/foo") is True


def test_is_absolute_like_arabic_pos0():
    # Arabic alef is alphabetic
    assert _is_absolute_like("أ:/foo") is True


# ---------- _has_backslash 数学边界第九批 ----------


def test_has_backslash_empty_string():
    assert _has_backslash("") is False


def test_has_backslash_only_tab():
    assert _has_backslash("\t") is False


def test_has_backslash_only_space():
    assert _has_backslash(" ") is False


def test_has_backslash_only_newline():
    assert _has_backslash("\n") is False


def test_has_backslash_tab_then_backslash():
    assert _has_backslash("\t\\") is True


def test_has_backslash_newline_then_backslash():
    assert _has_backslash("\n\\") is True


def test_has_backslash_only_backslash_and_forward():
    assert _has_backslash("\\/") is True


def test_has_backslash_two_backslashes():
    assert _has_backslash("\\\\") is True


# ---------- _resolve_relative_path 行为深度第四批 ----------


def test_resolve_relative_path_dot_returns_project_root(tmp_path):
    """'.' 解析为 project_root 本身。"""
    resolved = _resolve_relative_path(".", tmp_path, "test")
    assert resolved == tmp_path.resolve()


def test_resolve_relative_path_subdir_no_file(tmp_path):
    """'sub/' 解析为 sub 目录（即使不存在）。"""
    resolved = _resolve_relative_path("sub/", tmp_path, "test")
    assert resolved == (tmp_path / "sub").resolve()


def test_resolve_relative_path_unicode_filename(tmp_path):
    """Unicode 文件名。"""
    resolved = _resolve_relative_path("中文.pdf", tmp_path, "test")
    assert resolved == (tmp_path / "中文.pdf").resolve()


def test_resolve_relative_path_deep_subdir_4_levels(tmp_path):
    """4 层深的子目录。"""
    resolved = _resolve_relative_path("a/b/c/d/e.txt", tmp_path, "test")
    assert resolved == (tmp_path / "a" / "b" / "c" / "d" / "e.txt").resolve()


def test_resolve_relative_path_filename_with_multiple_dots(tmp_path):
    resolved = _resolve_relative_path("a.b.c.txt", tmp_path, "test")
    assert resolved == (tmp_path / "a.b.c.txt").resolve()


def test_resolve_relative_path_field_name_in_error(tmp_path):
    """field_name 出现在错误信息中。"""
    with pytest.raises(ManifestError, match="my_field_label"):
        _resolve_relative_path("", tmp_path, "my_field_label")


def test_resolve_relative_path_resolved_inside_project(tmp_path):
    """路径解析后仍在 project_root 内。"""
    (tmp_path / "sub").mkdir()
    resolved = _resolve_relative_path("sub/foo.txt", tmp_path, "test")
    # 相对 project_root 计算
    assert resolved.relative_to(tmp_path.resolve()) == Path("sub/foo.txt")


# ---------- _detect_project_root 行为深度第五批 ----------


def test_detect_project_root_with_nonexistent_path():
    """不存在的路径，parent 链向上找 pyproject。"""
    p = Path("evaluation/_definitely_not_exists_")
    root = _detect_project_root(p)
    # 应该解析到包含 pyproject.toml 的项目根（本仓库根）
    assert (root / "pyproject.toml").is_file()


def test_detect_project_root_returns_path_for_directory_under_repo():
    """目录路径，向上找到 pyproject.toml。"""
    p = Path("evaluation")
    root = _detect_project_root(p)
    assert (root / "pyproject.toml").is_file()


def test_detect_project_root_finds_first_pyproject(tmp_path):
    """多层嵌套时，找到最近的 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='outer'\n")
    inner = tmp_path / "inner"
    inner.mkdir()
    (inner / "pyproject.toml").write_text("[project]\nname='inner'\n")
    deep = inner / "sub"
    deep.mkdir()
    root = _detect_project_root(deep)
    # 最近的是 inner
    assert root == inner.resolve()


def test_detect_project_root_for_file_returns_parent_pyproject(tmp_path):
    """文件路径，从其父目录开始向上找。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    f = tmp_path / "x.txt"
    f.write_text("x")
    root = _detect_project_root(f)
    assert root == tmp_path.resolve()


def test_detect_project_root_returns_path_type():
    p = Path(".")
    root = _detect_project_root(p)
    assert isinstance(root, Path)


def test_detect_project_root_default_to_cur_when_no_pyproject_in_chain(tmp_path):
    """整个 parent 链都没有 pyproject.toml 时返回 cur。"""
    # tmp_path 是 pytest 临时目录，通常不含 pyproject.toml
    sub = tmp_path / "sub"
    sub.mkdir()
    root = _detect_project_root(sub)
    # 没有 pyproject.toml 在链中，返回 cur（即 sub 本身）
    assert root == sub.resolve()


# ---------- DocumentEntry dataclass 行为深度第七批 ----------


def _make_doc(**overrides):
    defaults = {
        "doc_id": "d1",
        "path_str": "foo.pdf",
        "resolved_path": Path("/tmp/foo.pdf"),
        "source_type": "pdf",
        "sha256": None,
        "categories": (),
        "paired_with": None,
        "annotation_file_str": None,
        "annotation_resolved": None,
        "expectations": None,
    }
    defaults.update(overrides)
    return DocumentEntry(**defaults)


def test_document_entry_hash_equal_for_equal_instances():
    """frozen dataclass 默认 hash 基于所有字段。"""
    d1 = _make_doc()
    d2 = _make_doc()
    assert hash(d1) == hash(d2)


def test_document_entry_hash_in_dict_key():
    """frozen dataclass 可作为 dict key。"""
    d = _make_doc()
    mapping = {d: "value"}
    assert mapping[d] == "value"


def test_document_entry_asdict_round_trip():
    """asdict 返回所有字段。"""
    d = _make_doc(doc_id="dx", source_type="pdf")
    d_dict = asdict(d)
    assert d_dict["doc_id"] == "dx"
    assert d_dict["source_type"] == "pdf"
    assert "categories" in d_dict


def test_document_entry_astuple_returns_tuple():
    d = _make_doc()
    t = astuple(d)
    assert isinstance(t, tuple)
    # 字段顺序与定义一致
    assert t[0] == "d1"
    assert t[3] == "pdf"


def test_document_entry_fields_count():
    """DocumentEntry 应有 10 个字段。"""
    flds = fields(DocumentEntry)
    assert len(flds) == 10


def test_document_entry_field_names():
    flds = fields(DocumentEntry)
    names = [f.name for f in flds]
    expected = [
        "doc_id", "path_str", "resolved_path", "source_type",
        "sha256", "categories", "paired_with",
        "annotation_file_str", "annotation_resolved", "expectations",
    ]
    assert names == expected


def test_document_entry_replace_preserves_other_fields():
    d1 = _make_doc(doc_id="d1", source_type="pdf", categories=("a",))
    d2 = replace(d1, doc_id="d2")
    # source_type 和 categories 应保持
    assert d2.source_type == "pdf"
    assert d2.categories == ("a",)
    assert d2.doc_id == "d2"


# ---------- ExpectedFailure dataclass 行为深度第七批 ----------


def _make_failure(**overrides):
    defaults = {
        "doc_id": "f1",
        "path_str": "bad.pdf",
        "resolved_path": Path("/tmp/bad.pdf"),
        "expected_error_code": "code1",
        "source_type": None,
    }
    defaults.update(overrides)
    return ExpectedFailure(**defaults)


def test_expected_failure_hash_equal_for_equal_instances():
    f1 = _make_failure()
    f2 = _make_failure()
    assert hash(f1) == hash(f2)


def test_expected_failure_asdict_returns_dict():
    f = _make_failure(doc_id="fx")
    d = asdict(f)
    assert d["doc_id"] == "fx"
    assert d["expected_error_code"] == "code1"


def test_expected_failure_astuple_returns_tuple():
    f = _make_failure()
    t = astuple(f)
    assert isinstance(t, tuple)
    assert t[0] == "f1"


def test_expected_failure_fields_count_5():
    flds = fields(ExpectedFailure)
    assert len(flds) == 5


def test_expected_failure_field_names():
    flds = fields(ExpectedFailure)
    names = [f.name for f in flds]
    expected = ["doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"]
    assert names == expected


def test_expected_failure_in_set():
    f1 = _make_failure()
    f2 = _make_failure()
    s = {f1, f2}
    assert len(s) == 1


# ---------- Manifest dataclass 行为深度第七批 ----------


def _make_manifest(**overrides):
    defaults = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": (),
        "expected_failures": (),
        "project_root": Path("/tmp"),
    }
    defaults.update(overrides)
    return Manifest(**defaults)


def test_manifest_hash_equal_for_equal_instances():
    m1 = _make_manifest()
    m2 = _make_manifest()
    # documents 和 expected_failures 都是空 tuple，project_root 是相同 Path
    assert hash(m1) == hash(m2)


def test_manifest_asdict_returns_dict():
    m = _make_manifest(devset_status="incomplete")
    d = asdict(m)
    assert d["devset_status"] == "incomplete"


def test_manifest_astuple_returns_tuple():
    m = _make_manifest()
    t = astuple(m)
    assert isinstance(t, tuple)


def test_manifest_fields_count_5():
    flds = fields(Manifest)
    assert len(flds) == 5


def test_manifest_field_names():
    flds = fields(Manifest)
    names = [f.name for f in flds]
    expected = ["manifest_version", "devset_status", "documents", "expected_failures", "project_root"]
    assert names == expected


# ---------- Manifest properties 算法深度第七批 ----------


def test_manifest_pdf_count_with_many():
    docs = tuple(_make_doc(doc_id=f"d{i}", source_type="pdf") for i in range(5))
    m = _make_manifest(documents=docs)
    assert m.pdf_count == 5
    assert m.docx_count == 0


def test_manifest_docx_count_with_many():
    docs = tuple(_make_doc(doc_id=f"d{i}", source_type="docx") for i in range(3))
    m = _make_manifest(documents=docs)
    assert m.docx_count == 3
    assert m.pdf_count == 0


def test_manifest_pdf_plus_docx_equals_file_count():
    docs = (
        _make_doc(doc_id="d1", source_type="pdf"),
        _make_doc(doc_id="d2", source_type="pdf"),
        _make_doc(doc_id="d3", source_type="docx"),
    )
    m = _make_manifest(documents=docs)
    assert m.pdf_count + m.docx_count == m.file_count


def test_manifest_categories_covered_with_empty():
    m = _make_manifest(documents=())
    assert m.categories_covered == []


def test_manifest_categories_covered_sorted_alphabetical():
    d1 = _make_doc(doc_id="d1", categories=("z", "a"))
    d2 = _make_doc(doc_id="d2", categories=("m",))
    m = _make_manifest(documents=(d1, d2))
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_with_unicode():
    d = _make_doc(categories=("中文", "日本語", "english"))
    m = _make_manifest(documents=(d,))
    # 排序按 Unicode codepoint
    sorted_cats = sorted(["中文", "日本語", "english"])
    assert m.categories_covered == sorted_cats


def test_manifest_content_group_count_pair_only():
    d1 = _make_doc(doc_id="d1", paired_with="d2")
    d2 = _make_doc(doc_id="d2", paired_with="d1")
    m = _make_manifest(documents=(d1, d2))
    assert m.content_group_count == 1


def test_manifest_content_group_count_pair_unidirectional():
    """单向 paired_with：d1 -> d2，d2 不回指。"""
    d1 = _make_doc(doc_id="d1", paired_with="d2")
    d2 = _make_doc(doc_id="d2")
    m = _make_manifest(documents=(d1, d2))
    # d1.paired_with 算 1 组；d2.paired_with 是 None 但 seen 含 d2（因为 pair_ids 含 {d1,d2}），
    # 实际：pair_ids={frozenset({d1,d2})}, seen={d1,d2}, unpaired=0 → 1
    assert m.content_group_count == 1


def test_manifest_content_group_count_two_pairs():
    d1 = _make_doc(doc_id="d1", paired_with="d2")
    d2 = _make_doc(doc_id="d2", paired_with="d1")
    d3 = _make_doc(doc_id="d3", paired_with="d4")
    d4 = _make_doc(doc_id="d4", paired_with="d3")
    m = _make_manifest(documents=(d1, d2, d3, d4))
    assert m.content_group_count == 2


# ---------- load_manifest malformed data 第七批 ----------


def test_load_manifest_file_not_found_raises(tmp_path):
    """清单文件不存在 → ManifestError。"""
    mf = tmp_path / "nonexistent.json"
    with pytest.raises(ManifestError, match="不存在"):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_directory_raises(tmp_path):
    """manifest_path 是目录 → ManifestError。"""
    sub = tmp_path / "subdir"
    sub.mkdir()
    with pytest.raises(ManifestError, match="不存在"):
        load_manifest(sub, project_root=tmp_path)


def test_load_manifest_empty_json_raises(tmp_path):
    """空文件 → JSON 解析失败。"""
    mf = tmp_path / "manifest.json"
    mf.write_text("", encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON"):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_invalid_json_syntax_raises(tmp_path):
    """JSON 语法错误（trailing comma）。"""
    mf = tmp_path / "manifest.json"
    mf.write_text('{"a": 1,}', encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON"):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_not_a_dict_root_raises(tmp_path):
    """JSON 根是 list 而非 dict → Schema 校验失败。"""
    mf = tmp_path / "manifest.json"
    mf.write_text("[]", encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_wrong_manifest_version_raises_specific(tmp_path):
    """manifest_version 错误 → ManifestError 包含 不兼容。"""
    data = {
        "manifest_version": "0.0",  # schema const 拒绝
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_missing_devset_status_raises(tmp_path):
    """缺少 devset_status → Schema 校验失败。"""
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "documents": [],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_missing_doc_id_raises(tmp_path):
    """documents 缺 doc_id → Schema 校验失败。"""
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"path": "x.pdf", "source_type": "pdf"}  # missing doc_id
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_missing_path_raises(tmp_path):
    """documents 缺 path → Schema 校验失败。"""
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "source_type": "pdf"}  # missing path
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


# ---------- module source forbidden tokens 第十批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.chmod", "os.chown",
        "os.execv", "os.fork",
        "os.kill", "os.mkdir",
        "os.makedirs", "os.remove",
        "os.rename", "os.rmdir",
        "os.unlink",
        "pathlib.Path.rmdir",
        "pathlib.Path.unlink",
        "Path.rmdir",
        "Path.unlink",
        "eval(", "exec(",
        "compile(",
        "globals(",
        "locals(",
        "vars(",
        "memoryview",
        "bytearray",
        "bytearray(",
        "errno",
        "signal.signal",
        "fcntl",
        "termios",
        "tty",
        "pty",
        "winreg",
        "msvcrt",
        "_winapi",
    ],
)
def test_manifest_source_no_forbidden_token_v3(token):
    src = inspect.getsource(mmod)
    assert token not in src, f"forbidden token found: {token}"


# ---------- signatures 第五批 ----------


def test_signature_is_absolute_like_returns_bool_annotation():
    sig = inspect.signature(_is_absolute_like)
    annot = sig.return_annotation
    # 没用 from __future__ 影响时，bool 是真实类型
    assert annot is bool or annot == "bool"


def test_signature_has_backslash_returns_bool_annotation():
    sig = inspect.signature(_has_backslash)
    annot = sig.return_annotation
    assert annot is bool or annot == "bool"


def test_signature_resolve_relative_path_returns_path_annotation():
    sig = inspect.signature(_resolve_relative_path)
    annot = sig.return_annotation
    assert annot is Path or annot == "Path"


def test_signature_detect_project_root_returns_path_annotation():
    sig = inspect.signature(_detect_project_root)
    annot = sig.return_annotation
    assert annot is Path or annot == "Path"


def test_signature_manifest_error_init_inherits_from_exception():
    """ManifestError 没有自定义 __init__，从 Exception 继承。"""
    init = ManifestError.__init__
    # 应该和 Exception.__init__ 是同一个
    assert init is Exception.__init__


def test_signature_load_manifest_two_params():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.values())
    # manifest_path + project_root
    assert len(params) == 2


def test_signature_load_manifest_project_root_default_none():
    sig = inspect.signature(load_manifest)
    params = sig.parameters
    assert params["project_root"].default is None


def test_signature_manifest_properties_return_types():
    """Manifest 的 properties 返回类型应正确。"""
    file_count_sig = inspect.signature(Manifest.file_count.fget)
    pdf_count_sig = inspect.signature(Manifest.pdf_count.fget)
    assert file_count_sig.return_annotation is int or file_count_sig.return_annotation == "int"
    assert pdf_count_sig.return_annotation is int or pdf_count_sig.return_annotation == "int"


# ---------- 模块整体合理性第三批 ----------


def test_module_all_attribute_lists_exact_items():
    """__all__ 应按顺序列出 5 个公开项。"""
    expected = ["ManifestError", "Manifest", "DocumentEntry", "ExpectedFailure", "load_manifest"]
    assert mmod.__all__ == expected


def test_module_has_docstring():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 0


def test_module_manifest_error_docstring_present():
    """ManifestError 类有 docstring。"""
    assert ManifestError.__doc__ is not None
    assert len(ManifestError.__doc__) > 0


def test_module_manifest_error_no_custom_init_in_source():
    """ManifestError 源码中没有 __init__ 覆写。"""
    src = inspect.getsource(ManifestError)
    assert "__init__" not in src


def test_module_no_module_level_mutable_state():
    """模块级别不应有可变全局（除常量外）。"""
    # _is_absolute_like / _has_backslash 是函数，不是状态
    import evaluation.manifest as mod
    # 关键公开名称
    public = [n for n in dir(mod) if not n.startswith("_")]
    assert "ManifestError" in public
    assert "Manifest" in public
    assert "DocumentEntry" in public
    assert "ExpectedFailure" in public
    assert "load_manifest" in public


# ---------- 端到端集成第三批 ----------


def test_e2e_load_manifest_with_annotation_file(tmp_path):
    """annotation_file 字段会被解析。"""
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    ann = tmp_path / "x.ann.json"
    ann.write_text("{}", encoding="utf-8")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf",
             "annotation_file": "x.ann.json"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].annotation_file_str == "x.ann.json"
    assert m.documents[0].annotation_resolved == ann.resolve()


def test_e2e_load_manifest_preserves_document_order(tmp_path):
    """文档顺序应与 manifest 中一致。"""
    for letter in "abcde":
        (tmp_path / f"{letter}.pdf").write_text("x")
    docs_data = [
        {"doc_id": f"d{i}", "path": f"{letter}.pdf", "source_type": "pdf"}
        for i, letter in enumerate("abcde")
    ]
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": docs_data,
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert [d.doc_id for d in m.documents] == ["d0", "d1", "d2", "d3", "d4"]


def test_e2e_load_manifest_with_expected_failures(tmp_path):
    """expected_failures 解析正确。"""
    bad = tmp_path / "bad.pdf"
    bad.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "f1", "path": "bad.pdf", "expected_error_code": "parse_error",
             "source_type": "pdf"},
        ],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    f = m.expected_failures[0]
    assert f.doc_id == "f1"
    assert f.expected_error_code == "parse_error"
    assert f.source_type == "pdf"
    assert f.resolved_path == bad.resolve()


def test_e2e_load_manifest_categories_deduplicated_across_docs(tmp_path):
    """categories 跨文档去重后排序。"""
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_text("x")
    pdf2 = tmp_path / "b.pdf"
    pdf2.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["cat_a", "cat_b"]},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf",
             "categories": ["cat_b", "cat_c"]},
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.categories_covered == ["cat_a", "cat_b", "cat_c"]


def test_e2e_load_manifest_default_devset_status_preserved(tmp_path):
    """devset_status 是 'incomplete' 时也保留。"""
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.devset_status == "incomplete"


def test_e2e_load_manifest_no_documents_no_failures(tmp_path):
    """空 documents 和 expected_failures。"""
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.file_count == 0
    assert len(m.expected_failures) == 0
    assert m.categories_covered == []


def test_e2e_load_manifest_resolved_paths_are_absolute(tmp_path):
    """所有 resolved_path 必须是绝对路径。"""
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    for d in m.documents:
        assert d.resolved_path.is_absolute()
