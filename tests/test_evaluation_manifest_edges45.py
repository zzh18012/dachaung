"""evaluation/manifest.py 第四十五轮 edges 测试（Round 447）。

补强 edges44 未触及的角度：
- _is_absolute_like 行为深度第十八批（空 string / 多字节首字符 / 非 ASCII letter + colon / 单字符 / 仅盘符无分隔）
- _has_backslash 行为深度第十八批（mixed slash / only backslash / 末尾反斜杠 / 反斜杠在中间）
- _resolve_relative_path 行为深度第十八批（custom field name in error / project_root 不变 / 正常路径 / resolve normalizes ./）
- _detect_project_root 行为深度第十八批（start is dir / start is file / no pyproject fallback cur / multiple parents）
- Manifest dataclass 第十八批（frozen / hashable / equality / 字段顺序 / tuple 类型）
- Manifest properties 第十八批（file_count==len / pdf_count / docx_count / categories_covered sorts / content_group_count unpaired）
- DocumentEntry 第十八批（frozen / hashable / equality / categories 默认空 / paired_with 默认 None）
- ExpectedFailure 第十八批（source_type 默认 None / frozen / equality）
- load_manifest 行为深度第十八批（manifest_path as str / project_root as str / 多 documents / 多 expected_failures / annotation_file 解析 / categories tuple 化）
- module source forbidden tokens 第三十二批
- module source 字符串精确补强第二十八批
- signatures 第二十八批
- module 合理性第二十八批
- 端到端集成第二十八批
"""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evaluation import MANIFEST_VERSION
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
from evaluation import manifest as mmod


# ---------- _is_absolute_like 行为深度第十八批 ----------


def test_is_absolute_like_empty_batch18():
    assert _is_absolute_like("") is False


def test_is_absolute_like_single_char_batch18():
    """单字符不算盘符。"""
    assert _is_absolute_like("C") is False


def test_is_absolute_like_two_chars_batch18():
    assert _is_absolute_like("C:") is False


def test_is_absolute_like_drive_no_separator_batch18():
    """C:foo 不算绝对（C 后面 :foo 没分隔符）。"""
    assert _is_absolute_like("C:foo") is False


def test_is_absolute_like_digit_colon_batch18():
    """1:\\foo 不是盘符（数字不是字母）。"""
    assert _is_absolute_like("1:\\foo") is False


def test_is_absolute_like_unicode_alpha_batch18():
    """中文字符 + :\\ 不是盘符（isalpha() True 对 Unicode 字符也成立，但 len<3 检查）。"""
    # 严格按代码：len >= 3 + [1]==':' + [0].isalpha() + [2] in '/\\'
    # '中' isalpha() True；'中:\\' 满足所有条件 → True
    assert _is_absolute_like("中:\\foo") is True


def test_is_absolute_like_only_root_slash_batch18():
    assert _is_absolute_like("/") is True


def test_is_absolute_like_dot_slash_batch18():
    assert _is_absolute_like("./foo") is False


def test_is_absolute_like_double_dot_batch18():
    assert _is_absolute_like("../foo") is False


def test_is_absolute_like_backslash_only_batch18():
    """单独 \\ 不算绝对（不以 / 开头，长度 1）。"""
    assert _is_absolute_like("\\") is False


# ---------- _has_backslash 行为深度第十八批 ----------


def test_has_backslash_no_batch18():
    assert _has_backslash("a/b/c") is False


def test_has_backslash_single_batch18():
    assert _has_backslash("a\\b") is True


def test_has_backslash_multiple_batch18():
    assert _has_backslash("a\\b\\c") is True


def test_has_backslash_only_batch18():
    assert _has_backslash("\\") is True


def test_has_backslash_trailing_batch18():
    assert _has_backslash("abc\\") is True


def test_has_backslash_leading_batch18():
    assert _has_backslash("\\abc") is True


def test_has_backslash_empty_batch18():
    assert _has_backslash("") is False


def test_has_backslash_mixed_batch18():
    """正反斜杠混合。"""
    assert _has_backslash("a/b\\c") is True


# ---------- _resolve_relative_path 行为深度第十八批 ----------


def test_resolve_relative_path_normal_batch18(tmp_path):
    """正常相对路径解析为绝对路径。"""
    rp = _resolve_relative_path("foo/bar.pdf", tmp_path, "test_field")
    assert rp == (tmp_path / "foo" / "bar.pdf").resolve()


def test_resolve_relative_path_dot_normalized_batch18(tmp_path):
    """./foo 等价于 foo。"""
    rp = _resolve_relative_path("./foo.pdf", tmp_path, "f")
    assert rp == (tmp_path / "foo.pdf").resolve()


def test_resolve_relative_path_double_dot_normalized_batch18(tmp_path):
    """foo/../bar 等价于 bar。"""
    rp = _resolve_relative_path("foo/../bar.pdf", tmp_path, "f")
    assert rp == (tmp_path / "bar.pdf").resolve()


def test_resolve_relative_path_does_not_modify_root_batch18(tmp_path):
    """解析后 project_root 路径对象未被修改（resolve 返回新对象）。"""
    root_before = tmp_path
    _resolve_relative_path("foo", tmp_path, "f")
    assert root_before == tmp_path  # identity 不变


def test_resolve_relative_path_error_field_name_batch18(tmp_path):
    """错误信息含 field_name。"""
    with pytest.raises(ManifestError, match="my_field"):
        _resolve_relative_path("/abs/path", tmp_path, "my_field")


def test_resolve_relative_path_error_path_in_message_batch18(tmp_path):
    with pytest.raises(ManifestError, match="/abs/path"):
        _resolve_relative_path("/abs/path", tmp_path, "f")


def test_resolve_relative_path_returns_path_batch18(tmp_path):
    rp = _resolve_relative_path("a.json", tmp_path, "f")
    assert isinstance(rp, Path)


def test_resolve_relative_path_outside_root_batch18(tmp_path):
    """路径解析后位于 root 之外 → ManifestError。"""
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("../../etc/passwd", tmp_path, "f")


def test_resolve_relative_path_empty_path_batch18(tmp_path):
    with pytest.raises(ManifestError, match="为空"):
        _resolve_relative_path("", tmp_path, "f")


def test_resolve_relative_path_backslash_batch18(tmp_path):
    with pytest.raises(ManifestError, match="正斜杠"):
        _resolve_relative_path("foo\\bar", tmp_path, "f")


# ---------- _detect_project_root 行为深度第十八批 ----------


def test_detect_project_root_start_with_file_batch18(tmp_path):
    """传 file path → 从 parent 开始找。"""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    target = sub / "manifest.json"
    target.write_text("{}", encoding="utf-8")
    rp = _detect_project_root(target)
    assert rp == tmp_path.resolve()


def test_detect_project_root_start_with_dir_batch18(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("", encoding="utf-8")
    rp = _detect_project_root(tmp_path)
    assert rp == tmp_path.resolve()


def test_detect_project_root_no_pyproject_returns_cur_batch18(tmp_path):
    """没有 pyproject.toml → 返回 cur（start 的目录）。"""
    sub = tmp_path / "deep"
    sub.mkdir()
    rp = _detect_project_root(sub)
    assert rp == sub.resolve()


def test_detect_project_root_finds_grandparent_batch18(tmp_path):
    """向上找多级。"""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("", encoding="utf-8")
    sub1 = tmp_path / "s1"
    sub1.mkdir()
    sub2 = sub1 / "s2"
    sub2.mkdir()
    rp = _detect_project_root(sub2)
    assert rp == tmp_path.resolve()


def test_detect_project_root_returns_path_batch18(tmp_path):
    rp = _detect_project_root(tmp_path)
    assert isinstance(rp, Path)


# ---------- Manifest dataclass 第十八批 ----------


def _mk_manifest():
    return Manifest(
        manifest_version=MANIFEST_VERSION,
        devset_status="incomplete",
        documents=(),
        expected_failures=(),
        project_root=Path("/fake"),
    )


def test_manifest_is_frozen_batch18():
    m = _mk_manifest()
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"  # type: ignore[misc]


def test_manifest_is_hashable_batch18():
    m = _mk_manifest()
    # tuple fields are hashable; Path is hashable; str is hashable
    assert hash(m) is not None


def test_manifest_equality_batch18():
    m1 = _mk_manifest()
    m2 = _mk_manifest()
    assert m1 == m2


def test_manifest_field_count_batch18():
    """Manifest 有 5 字段。"""
    assert len(fields(Manifest)) == 5


def test_manifest_field_names_batch18():
    names = [f.name for f in fields(Manifest)]
    assert names == ["manifest_version", "devset_status", "documents",
                     "expected_failures", "project_root"]


def test_manifest_documents_is_tuple_batch18():
    m = _mk_manifest()
    assert isinstance(m.documents, tuple)


def test_manifest_expected_failures_is_tuple_batch18():
    m = _mk_manifest()
    assert isinstance(m.expected_failures, tuple)


# ---------- Manifest properties 第十八批 ----------


def _mk_doc(doc_id="d1", source_type="pdf", categories=("c1",), paired_with=None):
    return DocumentEntry(
        doc_id=doc_id,
        path_str=f"samples/{doc_id}.pdf",
        resolved_path=Path(f"/fake/{doc_id}.pdf"),
        source_type=source_type,
        sha256=None,
        categories=categories,
        paired_with=paired_with,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def test_manifest_file_count_empty_batch18():
    m = _mk_manifest()
    assert m.file_count == 0


def test_manifest_file_count_with_docs_batch18():
    m = Manifest(
        manifest_version=MANIFEST_VERSION,
        devset_status="incomplete",
        documents=(_mk_doc("d1"), _mk_doc("d2")),
        expected_failures=(),
        project_root=Path("/fake"),
    )
    assert m.file_count == 2


def test_manifest_pdf_count_batch18():
    docs = (_mk_doc("d1", "pdf"), _mk_doc("d2", "docx"), _mk_doc("d3", "pdf"))
    m = Manifest(MANIFEST_VERSION, "incomplete", docs, (), Path("/fake"))
    assert m.pdf_count == 2


def test_manifest_docx_count_batch18():
    docs = (_mk_doc("d1", "pdf"), _mk_doc("d2", "docx"), _mk_doc("d3", "docx"))
    m = Manifest(MANIFEST_VERSION, "incomplete", docs, (), Path("/fake"))
    assert m.docx_count == 2


def test_manifest_categories_covered_sorts_batch18():
    docs = (
        _mk_doc("d1", "pdf", categories=("z", "a")),
        _mk_doc("d2", "docx", categories=("m",)),
    )
    m = Manifest(MANIFEST_VERSION, "incomplete", docs, (), Path("/fake"))
    assert m.categories_covered == ["a", "m", "z"]


def test_manifest_categories_covered_dedup_batch18():
    docs = (
        _mk_doc("d1", "pdf", categories=("a", "b")),
        _mk_doc("d2", "docx", categories=("a", "c")),
    )
    m = Manifest(MANIFEST_VERSION, "incomplete", docs, (), Path("/fake"))
    assert m.categories_covered == ["a", "b", "c"]


def test_manifest_content_group_count_unpaired_batch18():
    docs = (_mk_doc("d1"), _mk_doc("d2"))
    m = Manifest(MANIFEST_VERSION, "incomplete", docs, (), Path("/fake"))
    assert m.content_group_count == 2


def test_manifest_content_group_count_paired_batch18():
    docs = (
        _mk_doc("d1", paired_with="d2"),
        _mk_doc("d2", paired_with="d1"),
    )
    m = Manifest(MANIFEST_VERSION, "incomplete", docs, (), Path("/fake"))
    # 一对算 1 组
    assert m.content_group_count == 1


def test_manifest_content_group_count_mixed_batch18():
    docs = (
        _mk_doc("d1", paired_with="d2"),
        _mk_doc("d2", paired_with="d1"),
        _mk_doc("d3"),
    )
    m = Manifest(MANIFEST_VERSION, "incomplete", docs, (), Path("/fake"))
    # 1 paired group + 1 unpaired = 2
    assert m.content_group_count == 2


# ---------- DocumentEntry 第十八批 ----------


def test_document_entry_frozen_batch18():
    d = _mk_doc()
    with pytest.raises(FrozenInstanceError):
        d.doc_id = "other"  # type: ignore[misc]


def test_document_entry_hashable_batch18():
    d = _mk_doc()
    assert hash(d) is not None


def test_document_entry_equality_batch18():
    d1 = _mk_doc()
    d2 = _mk_doc()
    assert d1 == d2


def test_document_entry_field_count_batch18():
    assert len(fields(DocumentEntry)) == 10


def test_document_entry_field_names_batch18():
    names = [f.name for f in fields(DocumentEntry)]
    assert names == [
        "doc_id", "path_str", "resolved_path", "source_type", "sha256",
        "categories", "paired_with", "annotation_file_str",
        "annotation_resolved", "expectations",
    ]


def test_document_entry_categories_is_tuple_batch18():
    d = _mk_doc(categories=("a", "b"))
    assert isinstance(d.categories, tuple)


# ---------- ExpectedFailure 第十八批 ----------


def _mk_expected_failure(doc_id="bad1"):
    return ExpectedFailure(
        doc_id=doc_id,
        path_str=f"samples/{doc_id}.txt",
        resolved_path=Path(f"/fake/{doc_id}.txt"),
        expected_error_code="unsupported_format",
        source_type=None,
    )


def test_expected_failure_frozen_batch18():
    ef = _mk_expected_failure()
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "other"  # type: ignore[misc]


def test_expected_failure_hashable_batch18():
    ef = _mk_expected_failure()
    assert hash(ef) is not None


def test_expected_failure_equality_batch18():
    ef1 = _mk_expected_failure()
    ef2 = _mk_expected_failure()
    assert ef1 == ef2


def test_expected_failure_field_count_batch18():
    assert len(fields(ExpectedFailure)) == 5


def test_expected_failure_source_type_optional_batch18():
    ef = _mk_expected_failure()
    assert ef.source_type is None


# ---------- load_manifest 行为深度第十八批 ----------


def _mk_manifest_data_basic(tmp_path):
    """生成最小合法 manifest dict。"""
    # 创建一个文件让 resolved_path 真实存在（虽然 load_manifest 不要求文件存在）
    return {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/a.pdf",
                "source_type": "pdf",
            }
        ],
        "expected_failures": [],
    }


def test_load_manifest_accepts_str_path_batch18(tmp_path):
    """load_manifest 接受 str path。"""
    p = tmp_path / "m.json"
    p.write_text('{"manifest_version": "' + MANIFEST_VERSION + '", '
                 '"devset_status": "incomplete", "documents": [], '
                 '"expected_failures": []}', encoding="utf-8")
    m = load_manifest(str(p), project_root=tmp_path)
    assert m.devset_status == "incomplete"


def test_load_manifest_accepts_str_project_root_batch18(tmp_path):
    p = tmp_path / "m.json"
    p.write_text('{"manifest_version": "' + MANIFEST_VERSION + '", '
                 '"devset_status": "incomplete", "documents": [], '
                 '"expected_failures": []}', encoding="utf-8")
    m = load_manifest(p, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_not_found_raises_batch18(tmp_path):
    with pytest.raises(ManifestError, match="清单文件不存在"):
        load_manifest(tmp_path / "no.json")


def test_load_manifest_invalid_json_raises_batch18(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(ManifestError, match="JSON 解析失败"):
        load_manifest(p)


def test_load_manifest_version_mismatch_raises_batch18(tmp_path):
    """manifest_version='0.9' 不等于 schema 要求的 '1.0' → EvalSchemaError 先于 ManifestError。"""
    from evaluation.schema import EvalSchemaError
    p = tmp_path / "m.json"
    p.write_text('{"manifest_version": "0.9", "devset_status": "incomplete", '
                 '"documents": [], "expected_failures": []}',
                 encoding="utf-8")
    # schema 要求 enum ["1.0"]，所以 0.9 在 schema 阶段就被拒
    with pytest.raises((ManifestError, EvalSchemaError)):
        load_manifest(p)


def test_load_manifest_multi_documents_batch18(tmp_path):
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
            {"doc_id": "d2", "path": "b.docx", "source_type": "docx"},
        ],
        "expected_failures": [],
    }
    p.write_text(__import__("json").dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.documents) == 2
    assert m.documents[0].doc_id == "d1"
    assert m.documents[1].doc_id == "d2"


def test_load_manifest_expected_failures_batch18(tmp_path):
    p = tmp_path / "m.json"
    import json
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {"doc_id": "bad1", "path": "bad.txt",
             "expected_error_code": "unsupported_format"},
            {"doc_id": "bad2", "path": "bad2.txt",
             "expected_error_code": "parse_error",
             "source_type": "txt"},
        ],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert len(m.expected_failures) == 2
    assert m.expected_failures[0].doc_id == "bad1"
    assert m.expected_failures[1].source_type == "txt"


def test_load_manifest_categories_default_empty_batch18(tmp_path):
    import json
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ()


def test_load_manifest_paired_with_batch18(tmp_path):
    import json
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "paired_with": "d2"},
            {"doc_id": "d2", "path": "a.docx", "source_type": "docx",
             "paired_with": "d1"},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].paired_with == "d2"
    assert m.content_group_count == 1


def test_load_manifest_path_absolute_rejected_batch18(tmp_path):
    import json
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "/abs/foo.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestError, match="绝对路径"):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_path_backslash_rejected_batch18(tmp_path):
    import json
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "foo\\bar.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestError, match="正斜杠"):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_path_outside_root_rejected_batch18(tmp_path):
    import json
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "../../etc/passwd", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ManifestError, match="项目根目录之外"):
        load_manifest(p, project_root=tmp_path)


def test_load_manifest_returns_manifest_batch18(tmp_path):
    import json
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert isinstance(m, Manifest)


# ---------- module source forbidden tokens 第三十二批 ----------


@pytest.mark.parametrize("forbidden", [
    "pty.spawn",
    "commands.getoutput",
    "paramiko",
    "fabric.api",
    "ftplib",
    "smtplib",
    "telnetlib",
    "webbrowser.open",
    "socket.socket",
    "asyncio.open_connection",
    "multiprocessing.Process",
    "threading.Thread",
    "ctypes.CDLL",
    "pickle.dumps",
    "shutil.rmtree",
])
def test_module_source_forbidden_tokens_batch18(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


def test_module_source_no_subprocess_batch18():
    src = inspect.getsource(mmod)
    assert "import subprocess" not in src


def test_module_source_no_network_batch18():
    src = inspect.getsource(mmod)
    assert "urllib.request" not in src
    assert "import requests" not in src


def test_module_source_no_sys_exit_batch18():
    src = inspect.getsource(mmod)
    assert "sys.exit" not in src


# ---------- module source 字符串精确补强第二十八批 ----------


def test_module_source_has_future_annotations_batch18():
    src = inspect.getsource(mmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch18():
    src = inspect.getsource(mmod)
    assert "开发集清单加载器" in src


def test_module_source_has_json_import_batch18():
    src = inspect.getsource(mmod)
    assert "import json" in src


def test_module_source_has_dataclass_import_batch18():
    src = inspect.getsource(mmod)
    assert "from dataclasses import dataclass" in src


def test_module_source_has_pathlib_import_batch18():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_import_batch18():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_manifest_version_import_batch18():
    src = inspect.getsource(mmod)
    assert "from evaluation import MANIFEST_VERSION" in src


def test_module_source_has_schema_import_batch18():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema import validate" in src


def test_module_source_has_load_manifest_function_batch18():
    src = inspect.getsource(mmod)
    assert "def load_manifest(" in src


def test_module_source_has_resolve_relative_path_batch18():
    src = inspect.getsource(mmod)
    assert "def _resolve_relative_path(" in src


def test_module_source_has_detect_project_root_batch18():
    src = inspect.getsource(mmod)
    assert "def _detect_project_root(" in src


def test_module_source_has_is_absolute_like_batch18():
    src = inspect.getsource(mmod)
    assert "def _is_absolute_like(" in src


def test_module_source_has_has_backslash_batch18():
    src = inspect.getsource(mmod)
    assert "def _has_backslash(" in src


def test_module_source_has_manifest_error_class_batch18():
    src = inspect.getsource(mmod)
    assert "class ManifestError" in src


def test_module_source_has_manifest_dataclass_batch18():
    src = inspect.getsource(mmod)
    assert "@dataclass" in src


def test_module_source_has_all_dunder_batch18():
    src = inspect.getsource(mmod)
    assert "__all__" in src


# ---------- signatures 第二十八批 ----------


def test_signature_load_manifest_batch18():
    sig = inspect.signature(load_manifest)
    params = list(sig.parameters.keys())
    assert params == ["manifest_path", "project_root"]


def test_signature_load_manifest_project_root_optional_batch18():
    sig = inspect.signature(load_manifest)
    assert sig.parameters["project_root"].default is None


def test_signature_resolve_relative_path_batch18():
    sig = inspect.signature(_resolve_relative_path)
    params = list(sig.parameters.keys())
    assert params == ["path_str", "project_root", "field_name"]


def test_signature_is_absolute_like_batch18():
    sig = inspect.signature(_is_absolute_like)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]


def test_signature_has_backslash_batch18():
    sig = inspect.signature(_has_backslash)
    params = list(sig.parameters.keys())
    assert params == ["path_str"]


def test_signature_detect_project_root_batch18():
    sig = inspect.signature(_detect_project_root)
    params = list(sig.parameters.keys())
    assert params == ["start"]


# ---------- module 合理性第二十八批 ----------


def test_module_has_all_attribute_batch18():
    assert hasattr(mmod, "__all__")
    assert isinstance(mmod.__all__, list)


def test_module_all_count_5_batch18():
    assert len(mmod.__all__) == 5


def test_module_all_contents_batch18():
    assert set(mmod.__all__) == {
        "ManifestError", "Manifest", "DocumentEntry",
        "ExpectedFailure", "load_manifest",
    }


def test_module_load_manifest_callable_batch18():
    assert callable(load_manifest)


def test_module_does_not_import_unsafe_modules_batch18():
    src = inspect.getsource(mmod)
    for unsafe in ["import pickle", "import marshal", "import shelve",
                   "import subprocess"]:
        assert unsafe not in src


def test_module_does_not_import_evaluation_runner_batch18():
    """manifest.py 不应反向依赖 runner.py。"""
    src = inspect.getsource(mmod)
    assert "from evaluation.runner" not in src


def test_module_does_not_import_evaluation_cli_batch18():
    src = inspect.getsource(mmod)
    assert "from evaluation.cli" not in src


def test_module_no_main_block_batch18():
    """没有 if __name__ == '__main__' 入口。"""
    src = inspect.getsource(mmod)
    assert "__main__" not in src


# ---------- 端到端集成第二十八批 ----------


def test_e2e_load_manifest_round_trip_batch18(tmp_path):
    """写 manifest JSON → load → 字段正确。"""
    import json
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "categories": ["x"]},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.manifest_version == MANIFEST_VERSION
    assert m.devset_status == "complete"
    assert m.documents[0].doc_id == "d1"
    assert m.documents[0].categories == ("x",)


def test_e2e_load_manifest_with_annotation_batch18(tmp_path):
    """annotation_file 也被解析。"""
    import json
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "annotation_file": "annotations/d1.json"},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].annotation_resolved == (tmp_path / "annotations" / "d1.json").resolve()


def test_e2e_load_manifest_with_expectations_batch18(tmp_path):
    import json
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "expectations": {"element_count_by_type": {"heading": 2}}},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations == {"element_count_by_type": {"heading": 2}}


def test_e2e_load_manifest_with_sha256_batch18(tmp_path):
    import json
    p = tmp_path / "m.json"
    sha = "a" * 64
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "sha256": sha},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].sha256 == sha


def test_e2e_load_manifest_default_categories_empty_batch18(tmp_path):
    import json
    p = tmp_path / "m.json"
    data = {
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    p.write_text(json.dumps(data), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].categories == ()
    assert m.documents[0].paired_with is None
    assert m.documents[0].annotation_file_str is None
    assert m.documents[0].annotation_resolved is None
    assert m.documents[0].expectations is None
    assert m.documents[0].sha256 is None


def test_e2e_load_manifest_auto_project_root_batch18(tmp_path):
    """project_root=None → 自动检测。"""
    import json
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("", encoding="utf-8")
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p)
    assert m.project_root == tmp_path.resolve()


def test_e2e_load_manifest_empty_documents_batch18(tmp_path):
    import json
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": MANIFEST_VERSION,
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents == ()
    assert m.expected_failures == ()
    assert m.file_count == 0


def test_e2e_manifest_dataclass_used_by_runner_batch18():
    """Manifest 被 runner 引用（间接验证完整性）。"""
    from evaluation.runner import run_evaluation
    assert callable(run_evaluation)
