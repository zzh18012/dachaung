"""evaluation/manifest.py 第九十五轮 edges 测试（Round 689）。

补强 edges78 未触及的角度（第五十六批）。

新角度：
- content_group_count 语义矩阵（双向配对 1 组 / 单向配对也 1 组 / A→B+B→C 传递不合并 2 组 / 自配对 frozenset 单元素 1 组 / paired_with 空串算未配对 / 混合 1 对+2 未配对=3 / 空清单 0）
- load_manifest 错误消息细节（path 逃逸 message 含 documents[doc].path / annotation_file 字段名 / expected_failures[doc].path / 版本不匹配含双版本号 / 不存在含 resolve 路径 / JSON 解析失败前缀）
- load_manifest 端到端更多（categories tuple 化 / expectations dict 原样 / sha256 默认 None / project_root 传 str / devset_status complete / 注释路径 a/../b 收敛后仍在根内）
- _is_absolute_like 更多（单字母盘符 a:\\\\b / 两字母 AB:/x 非盘符 / 数字 1:/x 非盘符 / 空格 :/x 非盘符 / UNC //server / ~/x 相对）
- _resolve_relative_path 更多（a/../b.py 收敛 / a/./b.py / a//b.py 双斜杠 / 相对 project_root 传入仍正确）
- Manifest properties 数值（file/pdf/docx count 混合）
- AST/源码补强（content_group_count 内 frozenset+seen.update / categories_covered sorted / data.get 默认空 / detect_project_root [cur, *cur.parents] / relative_to try ValueError）
- forbidden tokens 第一百五十九批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import (
    DocumentEntry,
    ExpectedFailure,
    Manifest,
    ManifestError,
    _detect_project_root,
    _is_absolute_like,
    _resolve_relative_path,
    load_manifest,
)


# ---------- 构造工具 ----------

def _doc_entry(doc_id="d1", paired=None, cats=()) -> DocumentEntry:
    return DocumentEntry(
        doc_id=doc_id,
        path_str=f"samples/{doc_id}.pdf",
        resolved_path=Path(f"samples/{doc_id}.pdf"),
        source_type="pdf",
        sha256=None,
        categories=cats,
        paired_with=paired,
        annotation_file_str=None,
        annotation_resolved=None,
        expectations=None,
    )


def _mk_manifest(tmp_path, docs, efs=(), status="incomplete") -> Manifest:
    data = {
        "manifest_version": "1.0",
        "devset_status": status,
        "documents": docs,
        "expected_failures": efs,
    }
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return load_manifest(p, project_root=tmp_path)


# ---------- content_group_count 语义矩阵 ----------

def test_group_count_bidirectional_pair_batch52():
    m = Manifest("1.0", "incomplete", (_doc_entry("a", paired="b"), _doc_entry("b", paired="a")), (), Path("."))
    assert m.content_group_count == 1


def test_group_count_unidirectional_pair_batch52():
    """只有 A→B 单向引用：frozenset 仍只有一组。"""
    m = Manifest("1.0", "incomplete", (_doc_entry("a", paired="b"), _doc_entry("b")), (), Path("."))
    assert m.content_group_count == 1


def test_group_count_chain_not_merged_batch52():
    """A→B + B→C：两个不同 frozenset → 2 组（不合并传递闭包）。"""
    m = Manifest(
        "1.0", "incomplete",
        (_doc_entry("a", paired="b"), _doc_entry("b", paired="c"), _doc_entry("c")),
        (), Path("."),
    )
    assert m.content_group_count == 2


def test_group_count_self_pair_batch52():
    """paired_with=self → frozenset 单元素 1 组，doc 在 seen 不再算未配对。"""
    m = Manifest("1.0", "incomplete", (_doc_entry("a", paired="a"),), (), Path("."))
    assert m.content_group_count == 1


def test_group_count_empty_string_paired_batch52():
    m = Manifest("1.0", "incomplete", (_doc_entry("a", paired=""), _doc_entry("b")), (), Path("."))
    assert m.content_group_count == 2


def test_group_count_mixed_pair_plus_unpaired_batch52():
    m = Manifest(
        "1.0", "incomplete",
        (_doc_entry("a", paired="b"), _doc_entry("b", paired="a"), _doc_entry("x"), _doc_entry("y")),
        (), Path("."),
    )
    assert m.content_group_count == 3


def test_group_count_empty_manifest_batch52():
    m = Manifest("1.0", "incomplete", (), (), Path("."))
    assert m.content_group_count == 0


def test_group_count_all_unpaired_batch52():
    m = Manifest("1.0", "incomplete", (_doc_entry("a"), _doc_entry("b"), _doc_entry("c")), (), Path("."))
    assert m.content_group_count == 3


# ---------- load_manifest 错误消息细节 ----------

def test_load_manifest_escape_message_contains_field_batch52(tmp_path):
    docs = [{"doc_id": "d1", "path": "../escape.pdf", "source_type": "pdf"}]
    with pytest.raises(ManifestError) as ei:
        _mk_manifest(tmp_path, docs)
    assert "documents[d1].path" in str(ei.value)


def test_load_manifest_annotation_escape_message_batch52(tmp_path):
    docs = [{
        "doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
        "annotation_file": "../ann.json",
    }]
    with pytest.raises(ManifestError) as ei:
        _mk_manifest(tmp_path, docs)
    assert "annotation_file" in str(ei.value)


def test_load_manifest_ef_escape_message_batch52(tmp_path):
    efs = [{"doc_id": "ef1", "path": "../../x.pdf", "expected_error_code": "unsupported_format"}]
    with pytest.raises(ManifestError) as ei:
        _mk_manifest(tmp_path, [], efs=efs)
    assert "expected_failures[ef1].path" in str(ei.value)


def test_load_manifest_version_message_both_versions_batch52(tmp_path):
    """schema const=1.0 先拦截 9.9；改 patch 代码侧版本触发不匹配分支。"""
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    from unittest.mock import patch
    with patch("evaluation.manifest.MANIFEST_VERSION", "2.0"):
        with pytest.raises(ManifestError) as ei:
            load_manifest(p, project_root=tmp_path)
    msg = str(ei.value)
    assert "1.0" in msg  # 清单版本
    assert "2.0" in msg  # 代码版本


def test_load_manifest_missing_message_contains_resolved_batch52(tmp_path):
    missing = tmp_path / "nope" / "m.json"
    with pytest.raises(ManifestError) as ei:
        load_manifest(missing, project_root=tmp_path)
    assert str(missing.resolve()) in str(ei.value)


def test_load_manifest_bad_json_prefix_batch52(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text("{oops", encoding="utf-8")
    with pytest.raises(ManifestError) as ei:
        load_manifest(p, project_root=tmp_path)
    assert "清单 JSON 解析失败" in str(ei.value)


def test_load_manifest_backslash_message_batch52(tmp_path):
    docs = [{"doc_id": "d1", "path": "a\\b.pdf", "source_type": "pdf"}]
    with pytest.raises(ManifestError) as ei:
        _mk_manifest(tmp_path, docs)
    assert "正斜杠" in str(ei.value)


def test_load_manifest_absolute_message_batch52(tmp_path):
    docs = [{"doc_id": "d1", "path": "C:/x/b.pdf", "source_type": "pdf"}]
    with pytest.raises(ManifestError) as ei:
        _mk_manifest(tmp_path, docs)
    assert "绝对路径" in str(ei.value)


# ---------- load_manifest 端到端更多 ----------

def test_load_manifest_categories_become_tuple_batch52(tmp_path):
    docs = [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "categories": ["x", "y"]}]
    m = _mk_manifest(tmp_path, docs)
    assert m.documents[0].categories == ("x", "y")
    assert isinstance(m.documents[0].categories, tuple)


def test_load_manifest_expectations_passed_through_batch52(tmp_path):
    exp = {"element_count_by_type": {"paragraph": 3}}
    docs = [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "expectations": exp}]
    m = _mk_manifest(tmp_path, docs)
    assert m.documents[0].expectations == exp


def test_load_manifest_sha256_default_none_batch52(tmp_path):
    m = _mk_manifest(tmp_path, [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}])
    assert m.documents[0].sha256 is None
    assert m.documents[0].paired_with is None
    assert m.documents[0].annotation_file_str is None
    assert m.documents[0].annotation_resolved is None


def test_load_manifest_project_root_str_batch52(tmp_path):
    docs = [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}]
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete", "documents": docs,
    }), encoding="utf-8")
    m = load_manifest(p, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


def test_load_manifest_status_complete_batch52(tmp_path):
    m = _mk_manifest(tmp_path, [], status="complete")
    assert m.devset_status == "complete"


def test_load_manifest_dotdot_collapse_inside_root_batch52(tmp_path):
    """a/../b.pdf resolve 后仍在根内 → OK。"""
    docs = [{"doc_id": "d1", "path": "a/../b.pdf", "source_type": "pdf"}]
    m = _mk_manifest(tmp_path, docs)
    assert m.documents[0].resolved_path == (tmp_path / "b.pdf").resolve()


def test_load_manifest_annotation_resolved_path_batch52(tmp_path):
    docs = [{
        "doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
        "annotation_file": "ann/d1.json",
    }]
    m = _mk_manifest(tmp_path, docs)
    assert m.documents[0].annotation_resolved == (tmp_path / "ann" / "d1.json").resolve()


# ---------- _is_absolute_like 更多 ----------

def test_is_absolute_single_letter_drive_batch52():
    assert _is_absolute_like("a:\\b") is True


def test_is_absolute_two_letters_not_drive_batch52():
    assert _is_absolute_like("AB:/x") is False


def test_is_absolute_digit_colon_not_drive_batch52():
    assert _is_absolute_like("1:/x") is False


def test_is_absolute_space_colon_not_drive_batch52():
    assert _is_absolute_like(" :/x") is False


def test_is_absolute_unc_double_slash_batch52():
    assert _is_absolute_like("//server/share") is True


def test_is_absolute_tilde_relative_batch52():
    assert _is_absolute_like("~/docs") is False


def test_is_absolute_colon_only_third_char_batch52():
    """'a:b' 第三字符非斜杠 → 相对。"""
    assert _is_absolute_like("a:b") is False


# ---------- _resolve_relative_path 更多 ----------

def test_resolve_dot_in_middle_batch52(tmp_path):
    out = _resolve_relative_path("a/./b.pdf", tmp_path, "f")
    assert out == (tmp_path / "a" / "b.pdf").resolve()


def test_resolve_double_slash_batch52(tmp_path):
    out = _resolve_relative_path("a//b.pdf", tmp_path, "f")
    assert out == (tmp_path / "a" / "b.pdf").resolve()


def test_resolve_relative_project_root_batch52():
    """project_root 传相对路径（未 resolve）也正确。"""
    out = _resolve_relative_path("x.pdf", Path("some/rel"), "f")
    assert out.is_absolute()


def test_resolve_custom_field_name_in_message_batch52(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("../x", tmp_path, "custom_field")
    assert "custom_field" in str(ei.value)


# ---------- Manifest properties 数值 ----------

def test_manifest_counts_mixed_batch52(tmp_path):
    docs = [
        {"doc_id": "a", "path": "a.pdf", "source_type": "pdf"},
        {"doc_id": "b", "path": "b.pdf", "source_type": "pdf"},
        {"doc_id": "c", "path": "c.docx", "source_type": "docx"},
    ]
    m = _mk_manifest(tmp_path, docs)
    assert m.file_count == 3
    assert m.pdf_count == 2
    assert m.docx_count == 1


def test_manifest_categories_covered_sorted_dedupe_batch52(tmp_path):
    docs = [
        {"doc_id": "a", "path": "a.pdf", "source_type": "pdf", "categories": ["z", "m"]},
        {"doc_id": "b", "path": "b.pdf", "source_type": "pdf", "categories": ["m", "a"]},
    ]
    m = _mk_manifest(tmp_path, docs)
    assert m.categories_covered == ["a", "m", "z"]


# ---------- AST / 源码补强 ----------

def test_source_group_count_frozenset_batch52():
    src = inspect.getsource(manifest_mod)
    assert "frozenset([d.doc_id, d.paired_with])" in src


def test_source_group_count_seen_update_batch52():
    src = inspect.getsource(manifest_mod)
    assert "seen.update(pair)" in src


def test_source_categories_sorted_batch52():
    src = inspect.getsource(manifest_mod)
    assert "return sorted(s)" in src


def test_source_documents_get_default_batch52():
    src = inspect.getsource(manifest_mod)
    assert 'data.get("documents", [])' in src
    assert 'data.get("expected_failures", [])' in src


def test_source_detect_parents_splat_batch52():
    src = inspect.getsource(manifest_mod)
    assert "[cur, *cur.parents]" in src


def test_source_relative_to_try_valueerror_batch52():
    src = inspect.getsource(manifest_mod)
    assert "except ValueError:" in src
    assert "relative_to(project_root_resolved)" in src


def test_source_unidirectional_note_batch52():
    src = inspect.getsource(manifest_mod)
    assert "单向也算一组" in src


def test_source_annotation_field_label_batch52():
    src = inspect.getsource(manifest_mod)
    assert "annotation_file" in src


def test_ast_group_count_2_set_literals_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    prop = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "content_group_count")
    src = ast.unparse(prop)
    assert "pair_ids: set[frozenset[str]] = set()" in src
    assert "all_paired: set[str] = set()" in src


def test_ast_group_count_2_for_loops_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    prop = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "content_group_count")
    fors = [n for n in prop.body if isinstance(n, ast.For)]
    assert len(fors) == 3  # 收集 paired / 遍历 pair_ids / 遍历 documents 计未配对


def test_ast_load_manifest_document_for_has_annotation_if_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    src = ast.unparse(func)
    assert "if d.get('annotation_file'):" in src


def test_ast_load_manifest_manifest_version_compare_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    src = ast.unparse(func)
    assert "data.get('manifest_version') != MANIFEST_VERSION" in src


def test_ast_properties_are_property_decorated_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    props = [
        n.name for n in cls.body
        if isinstance(n, ast.FunctionDef)
        and any(
            isinstance(d, ast.Name) and d.id == "property"
            for d in n.decorator_list
        )
    ]
    assert props == ["file_count", "pdf_count", "docx_count", "content_group_count", "categories_covered"]


def test_ast_dataclass_decorator_call_not_attribute_batch52():
    tree = ast.parse(inspect.getsource(manifest_mod))
    decs = []
    for n in tree.body:
        if isinstance(n, ast.ClassDef):
            for d in n.decorator_list:
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass":
                    decs.append(n.name)
    assert decs == ["DocumentEntry", "ExpectedFailure", "Manifest"]


# ---------- forbidden tokens 第一百五十九批 ----------

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
    assert _src().count("open(") == 1
