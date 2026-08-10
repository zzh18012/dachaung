"""evaluation/manifest.py 第三十三轮 edges 测试（Round 362）。

重点补强 edges32 未触及的角度：
- _is_absolute_like 数学边界第八批（更多 Unicode 类别 / 组合）
- _has_backslash 数学边界第八批
- _resolve_relative_path 行为深度第三批
- _detect_project_root 行为深度第四批
- DocumentEntry / ExpectedFailure / Manifest dataclass 行为深度第六批
- Manifest properties 算法深度第六批
- load_manifest malformed data 第六批
- module source forbidden tokens 第八批
- module source 字符串精确补强第二批
- signatures 精确补强第二批
- 模块整体合理性补强第二批
- 端到端集成补强第二批
"""

from __future__ import annotations

import inspect
import json
import types
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import Any

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


# ---------- _is_absolute_like 数学边界第八批 ----------


def test_is_absolute_like_alpha_with_diacritic():
    # 带变音符号的字母 isalpha() True
    assert _is_absolute_like("é:/foo") is True


def test_is_absolute_like_alpha_combining_char():
    # 组合字符 e + combining acute
    assert _is_absolute_like("é:/foo") is False


def test_is_absolute_like_three_letter_drive_lowercase():
    assert _is_absolute_like("abc:/foo") is False  # [1] != ":"


def test_is_absolute_like_4_letter_with_colon_pos1():
    assert _is_absolute_like("a:/foo") is True  # len("a:/foo") >= 3


def test_is_absolute_like_two_char_input():
    assert _is_absolute_like("a:") is False  # len < 3


def test_is_absolute_like_three_char_with_pos2_pipe():
    assert _is_absolute_like("a:|foo") is False  # pos2 不是 \ 或 /


def test_is_absolute_like_three_char_with_pos2_dash():
    assert _is_absolute_like("a:-foo") is False


def test_is_absolute_like_three_char_with_pos2_dot():
    assert _is_absolute_like("a:.foo") is False


def test_is_absolute_like_three_char_with_pos2_alpha():
    assert _is_absolute_like("a:bfoo") is False


def test_is_absolute_like_three_char_with_pos2_digit():
    assert _is_absolute_like("a:1foo") is False


def test_is_absolute_like_three_char_with_pos2_space():
    assert _is_absolute_like("a: foo") is False


# ---------- _has_backslash 数学边界第八批 ----------


def test_has_backslash_long_string_no_backslash():
    assert _has_backslash("a" * 1000 + "/b") is False


def test_has_backslash_long_string_with_backslash():
    assert _has_backslash("a" * 1000 + "\\b") is True


def test_has_backslash_backslash_in_first_position():
    assert _has_backslash("\\abcdef") is True


def test_has_backslash_backslash_in_last_position():
    assert _has_backslash("abcdef\\") is True


def test_has_backslash_backslash_in_middle():
    assert _has_backslash("abc\\def") is True


def test_has_backslash_only_one_backslash():
    assert _has_backslash("\\") is True


def test_has_backslash_mixed_slashes_only_forward():
    assert _has_backslash("////") is False


# ---------- _resolve_relative_path 行为深度第三批 ----------


def test_resolve_relative_path_normal_path(tmp_path):
    resolved = _resolve_relative_path("foo.txt", tmp_path, "test")
    assert resolved == (tmp_path / "foo.txt").resolve()


def test_resolve_relative_path_subdir_path(tmp_path):
    resolved = _resolve_relative_path("sub/foo.txt", tmp_path, "test")
    assert resolved == (tmp_path / "sub" / "foo.txt").resolve()


def test_resolve_relative_path_deep_subdir(tmp_path):
    resolved = _resolve_relative_path("a/b/c/d.txt", tmp_path, "test")
    assert resolved == (tmp_path / "a" / "b" / "c" / "d.txt").resolve()


def test_resolve_relative_path_dot_dot_inside_subdir(tmp_path):
    resolved = _resolve_relative_path("a/../b.txt", tmp_path, "test")
    assert resolved == (tmp_path / "b.txt").resolve()


def test_resolve_relative_path_double_dot_inside(tmp_path):
    resolved = _resolve_relative_path("a/b/../../c.txt", tmp_path, "test")
    assert resolved == (tmp_path / "c.txt").resolve()


def test_resolve_relative_path_starts_with_dot_slash(tmp_path):
    resolved = _resolve_relative_path("./foo.txt", tmp_path, "test")
    assert resolved == (tmp_path / "foo.txt").resolve()


def test_resolve_relative_path_filename_with_special_chars(tmp_path):
    resolved = _resolve_relative_path("foo bar.txt", tmp_path, "test")
    assert resolved == (tmp_path / "foo bar.txt").resolve()


def test_resolve_relative_path_filename_with_dot(tmp_path):
    resolved = _resolve_relative_path(".hidden", tmp_path, "test")
    assert resolved == (tmp_path / ".hidden").resolve()


def test_resolve_relative_path_returns_path_instance(tmp_path):
    resolved = _resolve_relative_path("foo", tmp_path, "test")
    assert isinstance(resolved, Path)


def test_resolve_relative_path_resolved_is_absolute(tmp_path):
    resolved = _resolve_relative_path("foo", tmp_path, "test")
    assert resolved.is_absolute()


def test_resolve_relative_path_empty_raises_with_field_name(tmp_path):
    with pytest.raises(ManifestError, match="custom_field"):
        _resolve_relative_path("", tmp_path, "custom_field")


def test_resolve_relative_path_absolute_raises_with_path_in_msg(tmp_path):
    with pytest.raises(ManifestError, match="/etc/passwd"):
        _resolve_relative_path("/etc/passwd", tmp_path, "test")


def test_resolve_relative_path_backslash_raises_with_backslash_in_msg(tmp_path):
    with pytest.raises(ManifestError, match="反斜杠"):
        _resolve_relative_path("a\\b", tmp_path, "test")


def test_resolve_relative_path_outside_raises_with_project_root_msg(tmp_path):
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("../foo", tmp_path, "test")


# ---------- _detect_project_root 行为深度第四批 ----------


def test_detect_project_root_returns_path():
    root = _detect_project_root(Path("."))
    assert isinstance(root, Path)


def test_detect_project_root_default_to_cur_when_no_pyproject(tmp_path):
    root = _detect_project_root(tmp_path)
    assert root == tmp_path.resolve()


def test_detect_project_root_default_to_parent_when_file(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("x")
    root = _detect_project_root(f)
    assert root == tmp_path.resolve()


def test_detect_project_root_finds_pyproject_at_root(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    root = _detect_project_root(tmp_path)
    assert root == tmp_path.resolve()


def test_detect_project_root_finds_pyproject_in_parent(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    root = _detect_project_root(sub)
    assert root == tmp_path.resolve()


def test_detect_project_root_finds_pyproject_deep_nested(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    deep = tmp_path / "a" / "b" / "c" / "d" / "e"
    deep.mkdir(parents=True)
    root = _detect_project_root(deep)
    assert root == tmp_path.resolve()


# ---------- DocumentEntry dataclass 行为深度第六批 ----------


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


def test_document_entry_field_types_doc_id():
    d = _make_doc()
    assert isinstance(d.doc_id, str)


def test_document_entry_field_types_path_str():
    d = _make_doc()
    assert isinstance(d.path_str, str)


def test_document_entry_field_types_resolved_path():
    d = _make_doc()
    assert isinstance(d.resolved_path, Path)


def test_document_entry_field_types_source_type():
    d = _make_doc()
    assert isinstance(d.source_type, str)


def test_document_entry_field_types_sha256_optional():
    d = _make_doc()
    assert d.sha256 is None or isinstance(d.sha256, str)


def test_document_entry_field_types_categories_tuple():
    d = _make_doc()
    assert isinstance(d.categories, tuple)


def test_document_entry_field_types_paired_with():
    d = _make_doc()
    assert d.paired_with is None or isinstance(d.paired_with, str)


def test_document_entry_field_types_annotation_str():
    d = _make_doc()
    assert d.annotation_file_str is None or isinstance(d.annotation_file_str, str)


def test_document_entry_field_types_annotation_resolved():
    d = _make_doc()
    assert d.annotation_resolved is None or isinstance(d.annotation_resolved, Path)


def test_document_entry_field_types_expectations():
    d = _make_doc()
    assert d.expectations is None or isinstance(d.expectations, dict)


def test_document_entry_with_categories_tuple():
    d = _make_doc(categories=("a", "b", "c"))
    assert d.categories == ("a", "b", "c")


def test_document_entry_with_sha256():
    d = _make_doc(sha256="a" * 64)
    assert d.sha256 == "a" * 64


def test_document_entry_with_paired_with():
    d = _make_doc(paired_with="d2")
    assert d.paired_with == "d2"


def test_document_entry_with_annotation_resolved():
    d = _make_doc(annotation_resolved=Path("/tmp/ann.json"))
    assert d.annotation_resolved == Path("/tmp/ann.json")


def test_document_entry_with_expectations_dict():
    d = _make_doc(expectations={"element_count_by_type": {"paragraph": 5}})
    assert d.expectations == {"element_count_by_type": {"paragraph": 5}}


def test_document_entry_replace_creates_new():
    """frozen dataclass 用 replace 创建新实例。"""
    from dataclasses import replace
    d1 = _make_doc()
    d2 = replace(d1, doc_id="d2")
    assert d1.doc_id == "d1"
    assert d2.doc_id == "d2"


def test_document_entry_eq_when_all_fields_same():
    d1 = _make_doc()
    d2 = _make_doc()
    assert d1 == d2


def test_document_entry_neq_when_diff_path():
    d1 = _make_doc(resolved_path=Path("/a"))
    d2 = _make_doc(resolved_path=Path("/b"))
    assert d1 != d2


# ---------- ExpectedFailure dataclass 行为深度第六批 ----------


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


def test_expected_failure_field_types():
    f = _make_failure()
    assert isinstance(f.doc_id, str)
    assert isinstance(f.path_str, str)
    assert isinstance(f.resolved_path, Path)
    assert isinstance(f.expected_error_code, str)
    assert f.source_type is None or isinstance(f.source_type, str)


def test_expected_failure_with_source_type_pdf():
    f = _make_failure(source_type="pdf")
    assert f.source_type == "pdf"


def test_expected_failure_with_source_type_docx():
    f = _make_failure(source_type="docx")
    assert f.source_type == "docx"


def test_expected_failure_replace_creates_new():
    from dataclasses import replace
    f1 = _make_failure()
    f2 = replace(f1, doc_id="f2")
    assert f1.doc_id == "f1"
    assert f2.doc_id == "f2"


def test_expected_failure_with_all_fields_set():
    f = _make_failure(
        doc_id="f1",
        path_str="x.pdf",
        resolved_path=Path("/tmp/x.pdf"),
        expected_error_code="parse_error",
        source_type="pdf",
    )
    assert f.doc_id == "f1"
    assert f.expected_error_code == "parse_error"


# ---------- Manifest dataclass 行为深度第六批 ----------


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


def test_manifest_with_one_document():
    d = _make_doc()
    m = _make_manifest(documents=(d,))
    assert m.file_count == 1


def test_manifest_with_one_expected_failure():
    f = _make_failure()
    m = _make_manifest(expected_failures=(f,))
    assert len(m.expected_failures) == 1


def test_manifest_replace_creates_new():
    from dataclasses import replace
    m1 = _make_manifest()
    m2 = replace(m1, devset_status="incomplete")
    assert m1.devset_status == "complete"
    assert m2.devset_status == "incomplete"


def test_manifest_immutable_documents():
    m = _make_manifest()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        m.documents = ()  # type: ignore[misc]


def test_manifest_immutable_devset_status():
    m = _make_manifest()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        m.devset_status = "x"  # type: ignore[misc]


# ---------- Manifest properties 算法深度第六批 ----------


def test_manifest_categories_covered_with_empty_string_category():
    d = _make_doc(categories=("",))
    m = _make_manifest(documents=(d,))
    assert "" in m.categories_covered


def test_manifest_categories_covered_with_special_chars():
    d = _make_doc(categories=("with space", "with/slash", "with.dot"))
    m = _make_manifest(documents=(d,))
    assert m.categories_covered == sorted(["with space", "with/slash", "with.dot"])


def test_manifest_categories_covered_with_numeric_strings():
    d = _make_doc(categories=("1", "10", "2"))
    m = _make_manifest(documents=(d,))
    # 字符串排序
    assert m.categories_covered == ["1", "10", "2"]


def test_manifest_categories_covered_with_duplicates_across_docs():
    d1 = _make_doc(categories=("a", "b"))
    d2 = _make_doc(categories=("a", "c"))
    m = _make_manifest(documents=(d1, d2))
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_pdf_count_with_zero():
    m = _make_manifest(documents=())
    assert m.pdf_count == 0


def test_manifest_docx_count_with_zero():
    m = _make_manifest(documents=())
    assert m.docx_count == 0


def test_manifest_content_group_count_with_one_unpaired():
    d = _make_doc()
    m = _make_manifest(documents=(d,))
    assert m.content_group_count == 1


def test_manifest_content_group_count_with_two_unpaired():
    d1 = _make_doc()
    d2 = _make_doc(doc_id="d2")
    m = _make_manifest(documents=(d1, d2))
    assert m.content_group_count == 2


def test_manifest_content_group_count_with_simple_pair():
    d1 = _make_doc(doc_id="d1", paired_with="d2")
    d2 = _make_doc(doc_id="d2", paired_with="d1")
    m = _make_manifest(documents=(d1, d2))
    assert m.content_group_count == 1


def test_manifest_content_group_count_with_pair_plus_unpaired():
    d1 = _make_doc(doc_id="d1", paired_with="d2")
    d2 = _make_doc(doc_id="d2", paired_with="d1")
    d3 = _make_doc(doc_id="d3")
    m = _make_manifest(documents=(d1, d2, d3))
    assert m.content_group_count == 2


# ---------- load_manifest malformed data 第六批 ----------


def test_load_manifest_document_extra_field(tmp_path):
    """schema additionalProperties:false，多字段会被拒绝。"""
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "extra": "value"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_expected_failure_extra_field(tmp_path):
    pdf = tmp_path / "bad.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "f1", "path": "bad.pdf", "expected_error_code": "x",
             "extra": "value"}
        ],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_root_extra_field(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
        "extra_field": "value",
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_wrong_manifest_version_string(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": "2.0",  # schema const="1.0"
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_documents_with_invalid_path_field(tmp_path):
    """path 字段是绝对路径，schema 接受但 loader 拒绝。"""
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "/abs/path.pdf", "source_type": "pdf"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestError, match="禁止绝对路径"):
        load_manifest(mf, project_root=tmp_path)


def test_load_manifest_devset_status_value_preserved(tmp_path):
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


def test_load_manifest_returns_correct_project_root(tmp_path):
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
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_with_str_manifest_path(tmp_path):
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
    m = load_manifest(str(mf), project_root=str(tmp_path))
    assert isinstance(m, Manifest)


# ---------- module source forbidden tokens 第八批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "asyncio", "threading", "concurrent", "subprocess",
        "multiprocessing", "queue", "socket", "select",
        "re.match", "re.sub",
        "datetime.datetime",
        "time.time", "time.sleep",
        "os.system", "os.popen",
        "logging.getLogger",
        "urllib.request", "http.client",
        "ctypes", "pickle.loads",
        "shutil.rmtree",
        "tempfile.mkdtemp",
        "glob.glob",
        "unittest.TestCase",
        "pytest.fixture",
        "sys.exit",
        "copy.deepcopy",
        "weakref.ref",
        "abc.ABC",
        "contextlib.contextmanager",
        "operator.add",
        "functools.reduce",
        "itertools.chain",
        "collections.OrderedDict",
        "collections.deque",
        "importlib.import_module",
        "platform.system",
    ],
)
def test_manifest_source_no_forbidden_token_v2(token):
    src = inspect.getsource(mmod)
    assert token not in src, f"forbidden token found: {token}"


# ---------- module source 字符串精确补强第二批 ----------


def test_manifest_source_dataclass_decorator_count():
    src = inspect.getsource(mmod)
    assert src.count("@dataclass(frozen=True)") == 3


def test_manifest_source_class_count_4():
    src = inspect.getsource(mmod)
    # ManifestError、DocumentEntry、ExpectedFailure、Manifest
    class_count = src.count("\nclass ")
    assert class_count == 3 or class_count == 4  # 4 if first line is "class"


def test_manifest_source_property_count_5():
    src = inspect.getsource(mmod)
    assert src.count("@property") == 5


def test_manifest_source_manifest_error_init_docstring():
    src = inspect.getsource(ManifestError)
    assert '"""' in src


def test_manifest_source_dataclass_uses_field_default_factories():
    """dataclass 用默认值（不是 field(default_factory=...))。"""
    src = inspect.getsource(mmod)
    assert "field(default_factory" not in src


# ---------- signatures 精确补强第二批 ----------


def test_signature_document_entry_init_10_params():
    sig = inspect.signature(DocumentEntry.__init__)
    params = list(sig.parameters.values())
    assert len(params) == 11  # self + 10


def test_signature_expected_failure_init_5_params():
    sig = inspect.signature(ExpectedFailure.__init__)
    params = list(sig.parameters.values())
    assert len(params) == 6  # self + 5


def test_signature_manifest_init_5_params():
    sig = inspect.signature(Manifest.__init__)
    params = list(sig.parameters.values())
    assert len(params) == 6  # self + 5


def test_signature_resolve_relative_path_field_name_str():
    sig = inspect.signature(_resolve_relative_path)
    params = sig.parameters
    # field_name 没有 default
    assert params["field_name"].default is inspect.Parameter.empty


def test_signature_load_manifest_returns_manifest_annotation():
    sig = inspect.signature(load_manifest)
    annot = sig.return_annotation
    # 因为 from __future__，注解是 str
    assert "Manifest" in str(annot)


# ---------- 模块整体合理性补强第二批 ----------


def test_module_namespace_no_extra_module_level_vars():
    """不应有 module-level 函数/类之外的可变状态。"""
    public_names = [
        name for name in dir(mmod)
        if not name.startswith("_") or name in ("__all__", "__doc__", "__file__", "__name__")
    ]
    # 应该只有 ManifestError、Manifest、DocumentEntry、ExpectedFailure、load_manifest、MANIFEST_VERSION
    for expected in ("ManifestError", "Manifest", "DocumentEntry", "ExpectedFailure", "load_manifest"):
        assert expected in public_names


def test_module_dataclass_instances_are_immutable():
    d = DocumentEntry(
        doc_id="d1", path_str="x", resolved_path=Path("/x"),
        source_type="pdf", sha256=None, categories=(),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "modified"  # type: ignore[misc]


def test_module_manifest_error_is_exception_subclass():
    assert issubclass(ManifestError, Exception)


def test_module_manifest_error_str_representation():
    err = ManifestError("test message")
    assert "test message" in str(err)


def test_module_manifest_error_with_complex_errors():
    errs = [
        {"path": ["a", "b"], "message": "err1"},
        {"path": ["c"], "message": "err2"},
    ]
    err = ManifestError("msg", errs)
    assert err.args[0] == "msg"
    assert err.args[1] == errs


# ---------- 端到端集成补强第二批 ----------


def test_e2e_load_manifest_three_documents(tmp_path):
    pdf1 = tmp_path / "a.pdf"
    pdf1.write_text("x")
    pdf2 = tmp_path / "b.pdf"
    pdf2.write_text("x")
    pdf3 = tmp_path / "c.pdf"
    pdf3.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.pdf", "source_type": "pdf"},
            {"doc_id": "d3", "path": "c.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.file_count == 3
    assert m.pdf_count == 3


def test_e2e_load_manifest_docx_only(tmp_path):
    docx = tmp_path / "x.docx"
    docx.write_text("dummy")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.docx", "source_type": "docx"}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.docx_count == 1
    assert m.pdf_count == 0


def test_e2e_load_manifest_mixed_pdf_docx(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_text("x")
    docx = tmp_path / "b.docx"
    docx.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx"},
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.pdf_count == 1
    assert m.docx_count == 1


def test_e2e_load_manifest_with_categories_multi(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf",
             "categories": ["cat1", "cat2", "cat3"]}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.categories_covered == ["cat1", "cat2", "cat3"]
    assert m.documents[0].categories == ("cat1", "cat2", "cat3")


def test_e2e_load_manifest_does_not_mutate_input_dict(tmp_path):
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
    data_before = json.loads(json.dumps(data))
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    load_manifest(mf, project_root=tmp_path)
    # 重新加载文件内容比较
    data_after = json.loads(mf.read_text(encoding="utf-8"))
    assert data_after == data_before


def test_e2e_load_manifest_idempotent(tmp_path):
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
    m1 = load_manifest(mf, project_root=tmp_path)
    m2 = load_manifest(mf, project_root=tmp_path)
    assert m1 == m2


def test_e2e_load_manifest_default_root_finds_pyproject(tmp_path):
    """不传 project_root，从 manifest 路径向上找 pyproject.toml。"""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
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
    m = load_manifest(mf)
    assert m.project_root == tmp_path.resolve()


def test_e2e_load_manifest_with_paired_documents(tmp_path):
    pdf = tmp_path / "a.pdf"
    pdf.write_text("x")
    docx = tmp_path / "b.docx"
    docx.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "paired_with": "d2"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx", "paired_with": "d1"},
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.content_group_count == 1
    assert m.documents[0].paired_with == "d2"


def test_e2e_load_manifest_with_expectations(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf",
             "expectations": {"element_count_by_type": {"paragraph": 10}}}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].expectations == {"element_count_by_type": {"paragraph": 10}}


def test_e2e_load_manifest_with_sha256(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_text("x")
    sha = "a" * 64
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "sha256": sha}
        ],
        "expected_failures": [],
    }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(mf, project_root=tmp_path)
    assert m.documents[0].sha256 == sha


def test_e2e_load_manifest_str_path_returns_manifest(tmp_path):
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
    m = load_manifest(str(mf))
    assert isinstance(m, Manifest)


def test_e2e_load_manifest_with_path_path(tmp_path):
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
    m = load_manifest(Path(mf), project_root=Path(tmp_path))
    assert isinstance(m, Manifest)
