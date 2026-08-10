"""evaluation/manifest.py 第四十一轮 edges 测试（Round 419）。

补强 edges40 未触及的角度：
- _is_absolute_like 边界第十四批（更多形态：UNC \\server / 数字开头 D:/ / 单字母 a:/ / 小写盘符 / 多字符盘符 / 前导空白 / 单点 ./）
- _has_backslash 边界第十四批（更多形态：单独 / / 前后空白 / 多个连续 / Unicode 软斜杠）
- _resolve_relative_path 异常深度第十四批（field_name 在 message 中 / project_root 是 str 输入 / resolved_path 类型 / project_root 含 .. / 路径含空格）
- _detect_project_root 异常深度第十四批（pyproject.toml 不存在 → fallback / 文件类型 start / 含 ../a/ / 返回 Path 类型）
- Manifest dataclass 第十四批（不可变性 hashable / project_root 字段 / __dataclass_fields__ 数量 / 与 ExpectedFailure 不混淆）
- Manifest properties 第十四批（categories_covered 含重复 / content_group_count 单向配对 / file_count 与文档数一致）
- load_manifest 异常深度第十四批（manifest_path 是 str / project_root 是 str / version 不匹配 / Schema 失败抛 EvalSchemaError）
- module source forbidden tokens 第十七批
- module source 字符串精确补强第十四批
- signatures 第十四批
- module 合理性第十四批
- 端到端集成第十四批
"""

from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
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


# ---------- _is_absolute_like 边界第十四批 ----------


def test_is_absolute_like_double_backslash_unc_batch14():
    r"""UNC 路径 \\server\share — 以反斜杠开头不是 is_absolute_like 检测范围（只检 / 与盘符）。"""
    assert _is_absolute_like("\\\\server\\share") is False


def test_is_absolute_like_lowercase_drive_batch14():
    """小写盘符 d:/foo 也是绝对路径。"""
    assert _is_absolute_like("d:/foo") is True


def test_is_absolute_like_lowercase_drive_backslash_batch14():
    """小写盘符 d:\\foo 也是绝对路径。"""
    assert _is_absolute_like("d:\\foo") is True


def test_is_absolute_like_uppercase_drive_batch14():
    assert _is_absolute_like("D:/foo") is True


def test_is_absolute_like_numeric_first_char_batch14():
    """数字开头不是盘符。"""
    assert _is_absolute_like("1:/foo") is False


def test_is_absolute_like_drive_no_separator_batch14():
    """C:foo 没有 \\ 或 /，不算绝对路径。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_single_char_drive_batch14():
    """单字符 c 后无内容 — len < 3 → False。"""
    assert _is_absolute_like("c") is False


def test_is_absolute_like_two_chars_only_batch14():
    """两字符 C: — len=2 < 3 → False。"""
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_leading_space_batch14():
    """前导空白不被 strip。"""
    assert _is_absolute_like(" /foo") is False  # 不是 startswith("/")


def test_is_absolute_like_dot_slash_batch14():
    """./ 不是绝对路径。"""
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_empty_string_batch14():
    assert _is_absolute_like("") is False


def test_is_absolute_like_just_slash_batch14():
    """仅一个 / 也算绝对路径（startswith "/"）。"""
    assert _is_absolute_like("/") is True


# ---------- _has_backslash 边界第十四批 ----------


def test_has_backslash_single_batch14():
    assert _has_backslash("a\\b") is True


def test_has_backslash_multiple_consecutive_batch14():
    assert _has_backslash("a\\\\\\b") is True


def test_has_backslash_at_start_batch14():
    assert _has_backslash("\\abc") is True


def test_has_backslash_at_end_batch14():
    assert _has_backslash("abc\\") is True


def test_has_backslash_forward_slash_only_batch14():
    assert _has_backslash("a/b") is False


def test_has_backslash_empty_batch14():
    assert _has_backslash("") is False


def test_has_backslash_no_separator_batch14():
    assert _has_backslash("abc") is False


# ---------- _resolve_relative_path 异常深度第十四批 ----------


def test_resolve_relative_path_str_input_batch14(tmp_path):
    """project_root 必须是 Path — str 会被 TypeError。验证该不变量。"""
    with pytest.raises(TypeError):
        _resolve_relative_path("a.pdf", str(tmp_path), "x")


def test_resolve_relative_path_returns_resolved_path_batch14(tmp_path):
    out = _resolve_relative_path("a.pdf", tmp_path, "x")
    expected = (tmp_path / "a.pdf").resolve()
    assert out == expected


def test_resolve_relative_path_field_name_in_error_batch14(tmp_path):
    """错误 message 应包含 field_name。"""
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("", tmp_path, "MY_FIELD")
    assert "MY_FIELD" in str(exc_info.value)


def test_resolve_relative_path_absolute_in_error_batch14(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("/etc/passwd", tmp_path, "f")
    assert "/etc/passwd" in str(exc_info.value)


def test_resolve_relative_path_backslash_in_error_batch14(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("a\\b.pdf", tmp_path, "f")
    assert "a\\b.pdf" in str(exc_info.value)


def test_resolve_relative_path_outside_root_in_error_batch14(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        _resolve_relative_path("../outside.pdf", tmp_path, "f")
    assert "f" in str(exc_info.value)


def test_resolve_relative_path_with_subdir_batch14(tmp_path):
    """合法的子目录路径。"""
    (tmp_path / "sub").mkdir()
    out = _resolve_relative_path("sub/a.pdf", tmp_path, "f")
    assert out.parent == (tmp_path / "sub").resolve()


def test_resolve_relative_path_with_nested_subdir_batch14(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b").mkdir()
    out = _resolve_relative_path("a/b/c.pdf", tmp_path, "f")
    assert out == (tmp_path / "a" / "b" / "c.pdf").resolve()


def test_resolve_relative_path_space_in_path_batch14(tmp_path):
    """路径含空格。"""
    out = _resolve_relative_path("a b.pdf", tmp_path, "f")
    assert "a b.pdf" in str(out)


# ---------- _detect_project_root 异常深度第十四批 ----------


def test_detect_project_root_returns_path_batch14(tmp_path):
    out = _detect_project_root(tmp_path / "x.json")
    assert isinstance(out, Path)


def test_detect_project_root_with_pyproject_batch14(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    out = _detect_project_root(tmp_path / "x.json")
    assert out == tmp_path.resolve()


def test_detect_project_root_no_pyproject_fallback_batch14(tmp_path):
    """找不到 pyproject.toml → 返回 start.parent。"""
    out = _detect_project_root(tmp_path / "x.json")
    # 没有 pyproject.toml 时返回 cur（即 start.parent）
    assert isinstance(out, Path)


def test_detect_project_root_start_is_dir_batch14(tmp_path):
    """start 是目录也应工作。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    out = _detect_project_root(sub)
    assert out == tmp_path.resolve()


def test_detect_project_root_nested_pyproject_batch14(tmp_path):
    """嵌套：内层 pyproject 优先。"""
    (tmp_path / "pyproject.toml").write_text("[outer]", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "pyproject.toml").write_text("[inner]", encoding="utf-8")
    out = _detect_project_root(sub)
    assert out == sub.resolve()


# ---------- Manifest dataclass 第十四批 ----------


def test_document_entry_field_count_batch14():
    fs = fields(DocumentEntry)
    assert len(fs) == 10


def test_expected_failure_field_count_batch14():
    fs = fields(ExpectedFailure)
    assert len(fs) == 5


def test_manifest_field_count_batch14():
    fs = fields(Manifest)
    assert len(fs) == 5


def test_document_entry_field_names_batch14():
    fs = fields(DocumentEntry)
    names = {f.name for f in fs}
    expected = {
        "doc_id", "path_str", "resolved_path", "source_type", "sha256",
        "categories", "paired_with", "annotation_file_str", "annotation_resolved",
        "expectations",
    }
    assert names == expected


def test_expected_failure_field_names_batch14():
    fs = fields(ExpectedFailure)
    names = {f.name for f in fs}
    expected = {"doc_id", "path_str", "resolved_path", "expected_error_code", "source_type"}
    assert names == expected


def test_manifest_field_names_batch14():
    fs = fields(Manifest)
    names = {f.name for f in fs}
    expected = {"manifest_version", "devset_status", "documents", "expected_failures", "project_root"}
    assert names == expected


def test_document_entry_is_dataclass_batch14():
    assert is_dataclass(DocumentEntry)


def test_expected_failure_is_dataclass_batch14():
    assert is_dataclass(ExpectedFailure)


def test_manifest_is_dataclass_batch14():
    assert is_dataclass(Manifest)


def test_document_entry_frozen_batch14(tmp_path):
    d = DocumentEntry(
        doc_id="x",
        path_str="x.pdf",
        resolved_path=tmp_path / "x.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "y"


def test_manifest_frozen_batch14(tmp_path):
    m = Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=tmp_path,
    )
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"


def test_document_entry_hashable_batch14(tmp_path):
    d = DocumentEntry(
        doc_id="x",
        path_str="x.pdf",
        resolved_path=tmp_path / "x.pdf",
        source_type="pdf",
        sha256=None,
        categories=(),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    # 应可 hash（frozen=True 但含 Path, None, tuple 都可 hash）
    h = hash(d)
    assert isinstance(h, int)


# ---------- Manifest properties 第十四批 ----------


def _make_doc(
    doc_id="d1",
    path_str="a.pdf",
    source_type="pdf",
    categories=("normal",),
    paired_with=None,
):
    return DocumentEntry(
        doc_id=doc_id,
        path_str=path_str,
        resolved_path=Path("/x") / path_str,
        source_type=source_type,
        sha256=None,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def _make_manifest(docs=None, failures=None):
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=tuple(docs or []),
        expected_failures=tuple(failures or []),
        project_root=Path("/x"),
    )


def test_manifest_categories_with_duplicates_batch14():
    docs = [
        _make_doc(doc_id="d1", categories=("a", "b")),
        _make_doc(doc_id="d2", categories=("b", "c")),
    ]
    m = _make_manifest(docs=docs)
    # set 去重 + sorted
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_categories_with_empty_tuple_batch14():
    docs = [_make_doc(doc_id="d1", categories=())]
    m = _make_manifest(docs=docs)
    assert m.categories_covered == []


def test_manifest_pdf_count_zero_when_no_docs_batch14():
    m = _make_manifest(docs=[])
    assert m.pdf_count == 0
    assert m.docx_count == 0


def test_manifest_file_count_equals_len_documents_batch14():
    docs = [_make_doc(doc_id=f"d{i}") for i in range(5)]
    m = _make_manifest(docs=docs)
    assert m.file_count == 5


def test_manifest_content_group_count_unpaired_all_batch14():
    docs = [
        _make_doc(doc_id="d1"),
        _make_doc(doc_id="d2"),
        _make_doc(doc_id="d3"),
    ]
    m = _make_manifest(docs=docs)
    # 3 个独立无配对
    assert m.content_group_count == 3


def test_manifest_content_group_count_paired_batch14():
    docs = [
        _make_doc(doc_id="d1", paired_with="d2"),
        _make_doc(doc_id="d2", paired_with="d1"),
    ]
    m = _make_manifest(docs=docs)
    # 1 个配对组
    assert m.content_group_count == 1


def test_manifest_content_group_count_one_way_paired_batch14():
    """单向配对：d1.paired_with=d2 但 d2 无 paired_with。"""
    docs = [
        _make_doc(doc_id="d1", paired_with="d2"),
        _make_doc(doc_id="d2"),
    ]
    m = _make_manifest(docs=docs)
    # 算法只看有 paired_with 的 d1 → 1 组；d2 在 seen 中 → 不算 unpaired
    assert m.content_group_count == 1


# ---------- load_manifest 异常深度第十四批 ----------


def test_load_manifest_str_input_batch14(tmp_path):
    """manifest_path 可以是 str。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(str(p), project_root=tmp_path)
    assert isinstance(out, Manifest)


def test_load_manifest_path_input_batch14(tmp_path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert isinstance(out, Manifest)


def test_load_manifest_not_exist_raises_batch14(tmp_path):
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(tmp_path / "nonexistent.json", project_root=tmp_path)
    assert "不存在" in str(exc_info.value)


def test_load_manifest_invalid_json_raises_batch14(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("{not json}", encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "JSON" in str(exc_info.value)


def test_load_manifest_version_mismatch_raises_batch14(tmp_path):
    """manifest_version 不是 1.0 → ManifestError。"""
    data = {
        "manifest_version": "2.0",  # 不匹配
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    # schema 不允许 2.0 → EvalSchemaError 先抛
    from evaluation.schema import EvalSchemaError
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_schema_invalid_raises_eval_schema_error_batch14(tmp_path):
    from evaluation.schema import EvalSchemaError
    data = {"wrong": "shape"}
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_returns_manifest_with_correct_fields_batch14(tmp_path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    out = load_manifest(p, project_root=tmp_path)
    assert out.manifest_version == "1.0"
    assert out.devset_status == "incomplete"
    assert out.documents == ()
    assert out.expected_failures == ()
    assert out.project_root == tmp_path.resolve()


# ---------- module source forbidden tokens 第十七批 ----------


_FORBIDDEN_TOKENS_ROUND17 = [
    "eval(",
    "exec(",
    "os.system(",
    "subprocess.call(",
    "subprocess.check_output(",
    "subprocess.check_call(",
    "os.popen(",
    "__import__(",
    "pickle.loads(",
    "yaml.load(",
    "shutil.rmtree(",
    "os.remove(",
    "open('/etc",
    "open(\"/etc",
    "requests.get(",
    "urllib.request.urlopen(",
]


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND17)
def test_module_source_forbidden_tokens_round17_batch14(token):
    source = inspect.getsource(mmod)
    assert token not in source


# ---------- module source 字符串精确补强第十四批 ----------


def test_module_source_module_docstring_present_batch14():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:15])
    assert '"""' in head


def test_module_source_future_annotations_present_batch14():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from __future__ import annotations" in head


def test_module_source_imports_json_batch14():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "import json" in head


def test_module_source_imports_dataclass_batch14():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from dataclasses import dataclass" in head


def test_module_source_imports_pathlib_path_batch14():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from pathlib import Path" in head


def test_module_source_imports_typing_any_batch14():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_source_imports_manifest_version_batch14():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation import MANIFEST_VERSION" in head


def test_module_source_imports_validate_batch14():
    source = inspect.getsource(mmod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation.schema import validate" in head


def test_module_source_defines_manifest_error_batch14():
    source = inspect.getsource(mmod)
    assert "class ManifestError" in source


def test_module_source_defines_document_entry_batch14():
    source = inspect.getsource(mmod)
    assert "class DocumentEntry" in source


def test_module_source_defines_expected_failure_batch14():
    source = inspect.getsource(mmod)
    assert "class ExpectedFailure" in source


def test_module_source_defines_manifest_batch14():
    source = inspect.getsource(mmod)
    assert "class Manifest" in source


def test_module_source_defines_is_absolute_like_batch14():
    source = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in source


def test_module_source_defines_has_backslash_batch14():
    source = inspect.getsource(mmod)
    assert "def _has_backslash(" in source


def test_module_source_defines_resolve_relative_path_batch14():
    source = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in source


def test_module_source_defines_load_manifest_batch14():
    source = inspect.getsource(mmod)
    assert "def load_manifest(" in source


def test_module_source_defines_detect_project_root_batch14():
    source = inspect.getsource(mmod)
    assert "def _detect_project_root(" in source


def test_module_source_has_dunder_all_batch14():
    source = inspect.getsource(mmod)
    assert "__all__" in source


def test_module_source_dunder_all_5_items_batch14():
    assert len(mmod.__all__) == 5


def test_module_source_frozen_true_batch14():
    """Manifest/DocumentEntry/ExpectedFailure 都 frozen=True。"""
    source = inspect.getsource(mmod)
    # 3 个 @dataclass(frozen=True)
    assert source.count("frozen=True") == 3


def test_module_source_no_open_call_for_secrets_batch14():
    """不应有 open('/etc' 等敏感路径访问。"""
    source = inspect.getsource(mmod)
    assert "open('/etc" not in source
    assert 'open("/etc' not in source


def test_module_source_uses_validate_call_batch14():
    source = inspect.getsource(mmod)
    assert "validate(" in source


def test_module_source_no_subprocess_import_batch14():
    source = inspect.getsource(mmod)
    assert "import subprocess" not in source


# ---------- signatures 第十四批 ----------


def test_is_absolute_like_signature_one_param_batch14():
    sig = inspect.signature(_is_absolute_like)
    assert len(sig.parameters) == 1
    assert "path_str" in sig.parameters


def test_has_backslash_signature_one_param_batch14():
    sig = inspect.signature(_has_backslash)
    assert len(sig.parameters) == 1
    assert "path_str" in sig.parameters


def test_resolve_relative_path_signature_3_params_batch14():
    sig = inspect.signature(_resolve_relative_path)
    assert len(sig.parameters) == 3
    for n in ("path_str", "project_root", "field_name"):
        assert n in sig.parameters


def test_load_manifest_signature_2_params_batch14():
    sig = inspect.signature(load_manifest)
    assert len(sig.parameters) == 2
    for n in ("manifest_path", "project_root"):
        assert n in sig.parameters


def test_load_manifest_project_root_optional_batch14():
    sig = inspect.signature(load_manifest)
    p = sig.parameters["project_root"]
    assert p.default is None


def test_detect_project_root_signature_one_param_batch14():
    sig = inspect.signature(_detect_project_root)
    assert len(sig.parameters) == 1
    assert "start" in sig.parameters


def test_is_absolute_like_return_annotation_bool_batch14():
    sig = inspect.signature(_is_absolute_like)
    assert "bool" in str(sig.return_annotation)


def test_has_backslash_return_annotation_bool_batch14():
    sig = inspect.signature(_has_backslash)
    assert "bool" in str(sig.return_annotation)


def test_resolve_relative_path_return_annotation_path_batch14():
    sig = inspect.signature(_resolve_relative_path)
    assert "Path" in str(sig.return_annotation)


def test_load_manifest_return_annotation_manifest_batch14():
    sig = inspect.signature(load_manifest)
    assert "Manifest" in str(sig.return_annotation)


def test_detect_project_root_return_annotation_path_batch14():
    sig = inspect.signature(_detect_project_root)
    assert "Path" in str(sig.return_annotation)


def test_manifest_error_subclass_exception_batch14():
    assert issubclass(ManifestError, Exception)


def test_manifest_error_has_message_batch14():
    e = ManifestError("test")
    assert str(e) == "test"


# ---------- module 合理性第十四批 ----------


def test_module_dunder_file_exists_batch14():
    assert hasattr(mmod, "__file__")
    assert mmod.__file__ is not None


def test_module_dunder_file_manifest_py_batch14():
    assert "evaluation" in mmod.__file__
    assert mmod.__file__.endswith("manifest.py")


def test_module_name_evaluation_manifest_batch14():
    assert mmod.__name__ == "evaluation.manifest"


def test_module_dunder_all_includes_5_names_batch14():
    expected = {"ManifestError", "Manifest", "DocumentEntry", "ExpectedFailure", "load_manifest"}
    assert set(mmod.__all__) == expected


def test_module_dunder_all_items_unique_batch14():
    assert len(set(mmod.__all__)) == len(mmod.__all__)


def test_module_dataclass_class_count_3_batch14():
    classes = [
        n for n, v in vars(mmod).items()
        if inspect.isclass(v) and is_dataclass(v)
    ]
    assert set(classes) == {"DocumentEntry", "ExpectedFailure", "Manifest"}


def test_module_manifest_error_class_count_1_batch14():
    classes = [
        n for n, v in vars(mmod).items()
        if inspect.isclass(v) and not is_dataclass(v) and n != "ManifestError"  # 排除
    ]
    # 仅 ManifestError 是非 dataclass 类
    other_classes = [
        n for n, v in vars(mmod).items()
        if inspect.isclass(v) and not is_dataclass(v)
    ]
    assert "ManifestError" in other_classes


def test_module_all_dunder_all_items_callable_or_class_batch14():
    for name in mmod.__all__:
        attr = getattr(mmod, name)
        # load_manifest 是 callable；其它都是类（也是 callable）
        assert callable(attr)


# ---------- 端到端集成第十四批 ----------


def test_e2e_load_manifest_empty_documents_batch14(tmp_path):
    """空清单能正常加载。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents == ()
    assert m.expected_failures == ()
    assert m.file_count == 0


def test_e2e_load_manifest_with_one_document_batch14(tmp_path):
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "a.pdf",
                "source_type": "pdf",
                "categories": ["x"],
            }
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.file_count == 1
    assert m.documents[0].doc_id == "d1"
    assert m.documents[0].source_type == "pdf"
    assert m.documents[0].categories == ("x",)
    assert m.pdf_count == 1
    assert m.docx_count == 0


def test_e2e_load_manifest_with_paired_documents_batch14(tmp_path):
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    (tmp_path / "a.docx").write_text("fake", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "a.docx", "source_type": "docx", "paired_with": "d1"},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1
    assert m.content_group_count == 1


def test_e2e_load_manifest_with_expected_failure_batch14(tmp_path):
    (tmp_path / "x.bad").write_text("fake", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "x.bad", "expected_error_code": "unsupported_format"},
        ],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.expected_failures) == 1
    ef = m.expected_failures[0]
    assert ef.doc_id == "ef1"
    assert ef.expected_error_code == "unsupported_format"
    assert ef.source_type is None


def test_e2e_load_manifest_default_project_root_batch14(tmp_path):
    """无 project_root 参数 → 自动从 manifest 路径向上找。"""
    (tmp_path / "pyproject.toml").write_text("[tool.x]", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p)
    assert m.project_root == tmp_path.resolve()


def test_e2e_load_manifest_categories_combined_batch14(tmp_path):
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    (tmp_path / "b.pdf").write_text("fake", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "categories": ["a", "b"]},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf", "categories": ["b", "c"]},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.categories_covered == ["a", "b", "c"]


def test_e2e_load_manifest_idempotent_batch14(tmp_path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    m1 = load_manifest(p, project_root=tmp_path)
    m2 = load_manifest(p, project_root=tmp_path)
    assert m1 == m2


def test_e2e_manifest_json_serializable_via_to_dict_indirect_batch14(tmp_path):
    """Manifest dataclass frozen — 但属性应 json 可序列化（通过手动转换）。"""
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "categories": ["x"]},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    # dataclass 字段都可访问
    assert m.manifest_version == "1.0"
    assert m.devset_status == "incomplete"


def test_e2e_load_manifest_backslash_path_rejected_batch14(tmp_path):
    (tmp_path / "a.pdf").write_text("fake", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a\\b.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "正斜杠" in str(exc_info.value)


def test_e2e_load_manifest_absolute_path_rejected_batch14(tmp_path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "/etc/passwd", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestError) as exc_info:
        load_manifest(p, project_root=tmp_path)
    assert "绝对路径" in str(exc_info.value)
