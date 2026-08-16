"""evaluation/manifest.py 第九十三轮 edges 测试（Round 682）。

补强 edges77 未触及的角度（第五十三批）。

新角度：
- _is_absolute_like 更深（单字符 / 2 字符 / 盘符后无斜杠 / 盘符小写 / 非字母+冒号 / 只有斜杠 / 空字符串 / 中文盘符）
- _has_backslash 边界（单个 / 多个 / 开头 / 结尾 / 不含）
- _resolve_relative_path 更多异常路径（空字符串 raise / 绝对路径 raise / 反斜杠 raise / ../ 越界 raise / 子目录合法 / ./ 前缀合法）
- _detect_project_root 更深（已是项目根 / 深嵌套子目录 / 文件输入 / 无 pyproject 回退 cur）
- load_manifest 更多场景（manifest 不存在 raise / JSON 解析失败 raise / schema 失败 raise / manifest_version 不匹配 raise / documents 缺省空 / expected_failures 缺省空）
- load_manifest 字段传递（sha256 / categories / paired_with / expectations 完整传递）
- DocumentEntry frozen（赋值 raise / 等值比较 / repr 含字段名）
- ExpectedFailure frozen（赋值 raise / 字段访问）
- Manifest frozen（赋值 raise / properties 不被 freeze 影响）
- 模块源码补强（MANIFEST_VERSION import / validate import / json import / dataclass import / 5 __all__ entries / Manifest properties docstring / load_manifest docstring）
- AST 结构补强（3 dataclass decorator / DocumentEntry 10 AnnAssign / ExpectedFailure 5 AnnAssign / Manifest 5 AnnAssign + 5 property / _resolve_relative_path 3 if + 1 try / load_manifest 2 for + 1 with + 1 try / _detect_project_root 1 for + 2 if）
- forbidden tokens 第一百五十二批
"""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.manifest as manifest_mod
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


# ---------- _is_absolute_like 更深 ----------

def test_is_absolute_like_single_char_batch52():
    assert _is_absolute_like("C") is False


def test_is_absolute_like_two_chars_batch52():
    assert _is_absolute_like("C:") is False  # len < 3


def test_is_absolute_like_drive_no_slash_batch52():
    assert _is_absolute_like("C:foo") is False  # path_str[2] 不是 \ 或 /


def test_is_absolute_like_lowercase_drive_batch52():
    assert _is_absolute_like("c:/foo") is True


def test_is_absolute_like_lowercase_drive_backslash_batch52():
    assert _is_absolute_like("c:\\foo") is True


def test_is_absolute_like_non_alpha_colon_batch52():
    assert _is_absolute_like("1:/foo") is False  # '1' 不是 alpha


def test_is_absolute_like_only_slash_batch52():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_empty_string_batch52():
    assert _is_absolute_like("") is False


def test_is_absolute_like_chinese_drive_batch52():
    """中文'盘符'后跟冒号斜杠 → isalpha() True → 认为绝对路径。"""
    # '中'.isalpha() is True
    assert _is_absolute_like("中:/foo") is True


def test_is_absolute_like_relative_normal_batch52():
    assert _is_absolute_like("samples/foo.pdf") is False


def test_is_absolute_like_relative_dotslash_batch52():
    assert _is_absolute_like("./foo.pdf") is False


# ---------- _has_backslash 边界 ----------

def test_has_backslash_single_batch52():
    assert _has_backslash("a\\b") is True


def test_has_backslash_multiple_batch52():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_at_start_batch52():
    assert _has_backslash("\\foo") is True


def test_has_backslash_at_end_batch52():
    assert _has_backslash("foo\\") is True


def test_has_backslash_none_present_batch52():
    assert _has_backslash("a/b/c") is False


def test_has_backslash_empty_batch52():
    assert _has_backslash("") is False


# ---------- _resolve_relative_path 更多异常路径 ----------

def test_resolve_relative_path_empty_raises_batch52(tmp_path):
    with pytest.raises(ManifestError, match="为空"):
        _resolve_relative_path("", tmp_path, "field")


def test_resolve_relative_path_absolute_raises_batch52(tmp_path):
    with pytest.raises(ManifestError, match="绝对路径"):
        _resolve_relative_path("/etc/passwd", tmp_path, "field")


def test_resolve_relative_path_windows_drive_raises_batch52(tmp_path):
    with pytest.raises(ManifestError, match="绝对路径"):
        _resolve_relative_path("C:/foo/bar.pdf", tmp_path, "field")


def test_resolve_relative_path_backslash_raises_batch52(tmp_path):
    with pytest.raises(ManifestError, match="反斜杠"):
        _resolve_relative_path("a\\b.pdf", tmp_path, "field")


def test_resolve_relative_path_escape_root_raises_batch52(tmp_path):
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("../outside.pdf", tmp_path, "field")


def test_resolve_relative_path_deep_escape_raises_batch52(tmp_path):
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("a/../../outside.pdf", tmp_path, "field")


def test_resolve_relative_path_subdirectory_ok_batch52(tmp_path):
    resolved = _resolve_relative_path("samples/private/x.pdf", tmp_path, "field")
    assert resolved == (tmp_path / "samples/private/x.pdf").resolve()


def test_resolve_relative_path_dotslash_prefix_ok_batch52(tmp_path):
    resolved = _resolve_relative_path("./x.pdf", tmp_path, "field")
    assert resolved == (tmp_path / "x.pdf").resolve()


def test_resolve_relative_path_returns_absolute_path_batch52(tmp_path):
    resolved = _resolve_relative_path("x.pdf", tmp_path, "field")
    assert resolved.is_absolute()


def test_resolve_relative_path_nonexistent_file_ok_batch52(tmp_path):
    """路径不需要真实存在（只校验形式与位置）。"""
    resolved = _resolve_relative_path("no/such/file.pdf", tmp_path, "field")
    assert resolved == (tmp_path / "no/such/file.pdf").resolve()


# ---------- _detect_project_root 更深 ----------

def test_detect_project_root_at_root_batch52():
    """manifest.py 在 evaluation/ 内，向上找 pyproject.toml → 项目根。"""
    start = Path(manifest_mod.__file__).resolve().parent
    root = _detect_project_root(start)
    assert (root / "pyproject.toml").is_file()
    assert (root / "evaluation").is_dir()


def test_detect_project_root_deep_nested_batch52():
    start = Path(manifest_mod.__file__).resolve().parent
    root = _detect_project_root(start)
    # evaluation/ 在 root 下
    assert start == root / "evaluation"


def test_detect_project_root_file_input_batch52(tmp_path):
    """输入是文件 → 取 parent 开始找。"""
    f = tmp_path / "somefile.txt"
    f.write_text("x", encoding="utf-8")
    root = _detect_project_root(f)
    # tmp_path 无 pyproject.toml → 回退 cur = tmp_path
    assert root == tmp_path.resolve()


def test_detect_project_root_no_pyproject_fallback_batch52(tmp_path):
    root = _detect_project_root(tmp_path)
    assert root == tmp_path.resolve()


def test_detect_project_root_with_pyproject_batch52(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    root = _detect_project_root(sub)
    assert root == tmp_path.resolve()


# ---------- load_manifest 更多场景 ----------

def _write_manifest(tmp_path, data):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_load_manifest_not_exist_raises_batch52(tmp_path):
    with pytest.raises(ManifestError, match="清单文件不存在"):
        load_manifest(tmp_path / "nope.json", project_root=tmp_path)


def test_load_manifest_bad_json_raises_batch52(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON 解析失败"):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_schema_failure_raises_batch52(tmp_path):
    from evaluation.schema import EvalSchemaError
    p = _write_manifest(tmp_path, {"invalid": "data"})
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_version_mismatch_raises_batch52(tmp_path):
    """manifest_version 是别的值 → schema const:1.0 先拦。"""
    from evaluation.schema import EvalSchemaError
    p = _write_manifest(tmp_path, {
        "manifest_version": "2.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_empty_documents_ok_batch52(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents == ()
    assert m.file_count == 0


def test_load_manifest_no_expected_failures_key_ok_batch52(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures == ()


def test_load_manifest_full_fields_passed_batch52(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/a.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "categories": ["cat1", "cat2"],
                "paired_with": "d2",
                "expectations": {"element_count_by_type": {"paragraph": 3}},
            },
        ],
        "expected_failures": [
            {
                "doc_id": "ef1",
                "path": "samples/bad.pdf",
                "expected_error_code": "unsupported_format",
                "source_type": "pdf",
            },
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.documents) == 1
    d = m.documents[0]
    assert d.doc_id == "d1"
    assert d.path_str == "samples/a.pdf"
    assert d.sha256 == "a" * 64
    assert d.categories == ("cat1", "cat2")
    assert d.paired_with == "d2"
    assert d.expectations == {"element_count_by_type": {"paragraph": 3}}
    assert d.annotation_file_str is None
    assert d.annotation_resolved is None
    # expected failure
    ef = m.expected_failures[0]
    assert ef.doc_id == "ef1"
    assert ef.expected_error_code == "unsupported_format"
    assert ef.source_type == "pdf"


def test_load_manifest_expected_failure_no_source_type_batch52(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "ef1", "path": "x.txt", "expected_error_code": "unsupported_format"},
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert m.expected_failures[0].source_type is None


def test_load_manifest_annotation_file_resolved_batch52(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/a.pdf",
                "source_type": "pdf",
                "annotation_file": "annotations/d1.json",
            },
        ],
    })
    m = load_manifest(p, project_root=tmp_path)
    d = m.documents[0]
    assert d.annotation_file_str == "annotations/d1.json"
    assert d.annotation_resolved == (tmp_path / "annotations/d1.json").resolve()


def test_load_manifest_returns_manifest_instance_batch52(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)
    assert m.manifest_version == "1.0"
    assert m.devset_status == "incomplete"
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_str_path_ok_batch52(tmp_path):
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    m = load_manifest(str(p), project_root=tmp_path)
    assert isinstance(m, Manifest)


def test_load_manifest_default_project_root_batch52(tmp_path):
    """project_root=None → 自动检测（manifest 在 tmp_path 内，无 pyproject → tmp_path）。"""
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    p = _write_manifest(tmp_path, {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    m = load_manifest(p)
    assert m.project_root == tmp_path.resolve()


# ---------- DocumentEntry frozen ----------

def _doc_entry(**overrides):
    defaults = dict(
        doc_id="d1",
        path_str="a/b.pdf",
        resolved_path=Path("/x/a/b.pdf"),
        source_type="pdf",
        sha256=None,
        categories=("c1",),
        paired_with=None,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )
    defaults.update(overrides)
    return DocumentEntry(**defaults)


def test_document_entry_frozen_assign_raises_batch52():
    d = _doc_entry()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "new"


def test_document_entry_equality_batch52():
    d1 = _doc_entry()
    d2 = _doc_entry()
    assert d1 == d2


def test_document_entry_inequality_batch52():
    d1 = _doc_entry()
    d2 = _doc_entry(doc_id="d2")
    assert d1 != d2


def test_document_entry_repr_contains_doc_id_batch52():
    d = _doc_entry(doc_id="xyz")
    assert "xyz" in repr(d)


def test_document_entry_is_dataclass_batch52():
    assert is_dataclass(DocumentEntry)


def test_document_entry_10_fields_batch52():
    assert len(fields(DocumentEntry)) == 10


# ---------- ExpectedFailure frozen ----------

def _expected_failure(**overrides):
    defaults = dict(
        doc_id="ef1",
        path_str="bad.txt",
        resolved_path=Path("/x/bad.txt"),
        expected_error_code="unsupported_format",
        source_type=None,
    )
    defaults.update(overrides)
    return ExpectedFailure(**defaults)


def test_expected_failure_frozen_assign_raises_batch52():
    ef = _expected_failure()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "new"


def test_expected_failure_equality_batch52():
    assert _expected_failure() == _expected_failure()


def test_expected_failure_is_dataclass_batch52():
    assert is_dataclass(ExpectedFailure)


def test_expected_failure_5_fields_batch52():
    assert len(fields(ExpectedFailure)) == 5


# ---------- Manifest frozen ----------

def _manifest(docs=(), efs=(), project_root=None):
    return Manifest(
        manifest_version="1.0",
        devset_status="incomplete",
        documents=tuple(docs),
        expected_failures=tuple(efs),
        project_root=project_root or Path("."),
    )


def test_manifest_frozen_assign_raises_batch52():
    m = _manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"


def test_manifest_is_dataclass_batch52():
    assert is_dataclass(Manifest)


def test_manifest_5_fields_batch52():
    assert len(fields(Manifest)) == 5


def test_manifest_properties_work_despite_frozen_batch52():
    m = _manifest(docs=[
        _doc_entry(doc_id="d1", source_type="pdf"),
        _doc_entry(doc_id="d2", source_type="docx"),
    ])
    assert m.file_count == 2
    assert m.pdf_count == 1
    assert m.docx_count == 1


# ---------- 模块源码补强 ----------

def test_source_future_annotations_batch52():
    src = inspect.getsource(manifest_mod)
    assert "from __future__ import annotations" in src


def test_source_json_import_batch52():
    src = inspect.getsource(manifest_mod)
    assert "import json" in src


def test_source_dataclass_import_batch52():
    src = inspect.getsource(manifest_mod)
    assert "from dataclasses import dataclass" in src


def test_source_pathlib_path_import_batch52():
    src = inspect.getsource(manifest_mod)
    assert "from pathlib import Path" in src


def test_source_typing_any_import_batch52():
    src = inspect.getsource(manifest_mod)
    assert "from typing import Any" in src


def test_source_manifest_version_import_batch52():
    src = inspect.getsource(manifest_mod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_source_validate_import_batch52():
    src = inspect.getsource(manifest_mod)
    assert "from evaluation.schema import validate" in src


def test_source_manifest_error_docstring_batch52():
    src = inspect.getsource(manifest_mod)
    assert "清单加载或校验失败" in src


def test_source_is_absolute_like_docstring_batch52():
    src = inspect.getsource(manifest_mod)
    assert "识别绝对路径" in src


def test_source_content_group_count_docstring_batch52():
    src = inspect.getsource(manifest_mod)
    assert "配对的 DOCX+PDF 视为同一内容来源" in src


def test_source_resolve_relative_path_docstring_batch52():
    src = inspect.getsource(manifest_mod)
    assert "校验路径形式并解析为绝对路径" in src


def test_source_load_manifest_docstring_batch52():
    src = inspect.getsource(manifest_mod)
    assert "加载清单" in src


def test_source_detect_project_root_docstring_batch52():
    src = inspect.getsource(manifest_mod)
    assert "从 start 向上找包含 pyproject.toml 的目录" in src


def test_source_all_5_entries_batch52():
    src = inspect.getsource(manifest_mod)
    for name in ("ManifestError", "Manifest", "DocumentEntry", "ExpectedFailure", "load_manifest"):
        assert f'"{name}"' in src


def test_source_3_frozen_dataclasses_batch52():
    src = inspect.getsource(manifest_mod)
    assert src.count("@dataclass(frozen=True)") == 3


def test_source_module_docstring_invariants_batch52():
    """模块 docstring 说明 3 条不变量。"""
    src = inspect.getsource(manifest_mod)
    assert "相对路径" in src
    assert "项目根目录内" in src


# ---------- AST 结构补强 ----------

def test_ast_3_dataclass_decorators_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 4  # ManifestError + 3 dataclass
    # @dataclass(frozen=True) 是 Call(func=Name('dataclass'))
    dataclasses = [c for c in classes if any(
        isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass"
        for d in c.decorator_list
    )]
    assert len(dataclasses) == 3
    # 3 个都有 frozen=True keyword
    for c in dataclasses:
        dec = next(d for d in c.decorator_list if isinstance(d, ast.Call))
        kw = next(k for k in dec.keywords if k.arg == "frozen")
        assert isinstance(kw.value, ast.Constant)
        assert kw.value.value is True


def test_ast_document_entry_10_fields_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "DocumentEntry")
    ann_assigns = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    assert len(ann_assigns) == 10


def test_ast_expected_failure_5_fields_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ExpectedFailure")
    ann_assigns = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    assert len(ann_assigns) == 5


def test_ast_manifest_5_fields_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    field_assigns = [n for n in cls.body if isinstance(n, ast.AnnAssign)]
    assert len(field_assigns) == 5


def test_ast_manifest_5_properties_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    props = []
    for n in cls.body:
        if isinstance(n, ast.FunctionDef):
            for d in n.decorator_list:
                if isinstance(d, ast.Name) and d.id == "property":
                    props.append(n.name)
    assert sorted(props) == [
        "categories_covered", "content_group_count",
        "docx_count", "file_count", "pdf_count",
    ]


def test_ast_manifest_error_extends_exception_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ManifestError")
    assert len(cls.bases) == 1
    assert isinstance(cls.bases[0], ast.Name)
    assert cls.bases[0].id == "Exception"


def test_ast_resolve_relative_path_3_if_raise_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_relative_path")
    ifs = [n for n in func.body if isinstance(n, ast.If)]
    assert len(ifs) == 3  # empty + absolute + backslash
    # try/except for relative_to
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_resolve_relative_path_raises_manifest_error_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_relative_path")
    src = ast.unparse(func)
    assert "raise ManifestError" in src


def test_ast_load_manifest_2_for_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 2  # documents + expected_failures


def test_ast_load_manifest_1_with_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    withs = [n for n in ast.walk(func) if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_load_manifest_1_try_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1  # json.load


def test_ast_load_manifest_calls_validate_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    src = ast.unparse(func)
    assert "validate(data, 'manifest.schema.json')" in src or 'validate(data, "manifest.schema.json")' in src


def test_ast_detect_project_root_1_for_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_detect_project_root")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_detect_project_root_2_if_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_detect_project_root")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) == 2  # cur.is_file() + (parent/pyproject).is_file()


def test_ast_top_level_functions_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert funcs == [
        "_is_absolute_like", "_has_backslash",
        "_resolve_relative_path", "load_manifest", "_detect_project_root",
    ]


def test_ast_no_async_function_def_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_no_star_import_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


def test_ast_no_global_nonlocal_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


def test_ast_all_value_is_list_5_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert isinstance(all_assign.value, ast.List)
    assert len(all_assign.value.elts) == 5


# ---------- forbidden tokens 第一百五十二批 ----------

def _src() -> str:
    return inspect.getsource(manifest_mod)


def test_source_no_eval_batch52():
    assert "eval(" not in _src()


def test_source_no_exec_batch52():
    assert "exec(" not in _src()


def test_source_no_compile_batch52():
    assert "compile(" not in _src()


def test_source_no_globals_batch52():
    assert "globals(" not in _src()


def test_source_no_locals_batch52():
    assert "locals(" not in _src()


def test_source_no_os_system_batch52():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch52():
    assert "subprocess" not in _src()


def test_source_no_popen_batch52():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch52():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch52():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch52():
    assert "socket" not in _src()


def test_source_no_requests_batch52():
    assert "requests" not in _src()


def test_source_no_urllib_batch52():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch52():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch52():
    assert "yield" not in _src()


def test_source_no_async_await_batch52():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch52():
    """load_manifest 1 个 with open。"""
    assert _src().count("open(") == 1
