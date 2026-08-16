"""evaluation/manifest.py 第九十八轮 edges 测试（Round 710）。

补强 edges81 未触及的角度（第七十五批）。

新角度：
- _is_absolute_like 矩阵（"" / "/foo" / C:\\ / C:/ / c:/ 小写 / "C:x" 无斜杠 / "CC/x" / "1:/x" / 纯反斜杠）
- _resolve_relative_path 直测（空串 / 绝对 / 反斜杠 / ../ 越根 / 合法相对）
- content_group_count 配对语义直测（无配对=N / 双向=1 / 单向=1 / 配对+落单=2 / 自配对=1 / 指向不存在 doc=1）
- Manifest 属性直测（file_count / pdf_count / docx_count / categories_covered 排序去重）
- dataclass 冻结（DocumentEntry/Manifest setattr → FrozenInstanceError）
- annotation_file 反斜杠 / ef 路径越根（字段名带 expected_failures 前缀）
- project_root 传 str / expectations 双键完整回读 / paired_with 回读
- manifest_version schema const 1.0（代码里的不兼容分支被 schema 前置拦截）
- 源码补强（空串分支 / relative_to / 越根消息 / pair_ids.add / groups+unpaired / 两个默认 get / 两个 list 注解 / categories tuple 化）
- AST 补强（Manifest 5 个 property / content_group_count 3 个 For / _resolve_relative_path 3 Raise+1 Try / load_manifest 2 For+2 append / _detect_project_root 2 If+2 Return）
- forbidden tokens 第一百八十批
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
from pathlib import Path

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import (
    DocumentEntry,
    Manifest,
    ManifestError,
    ExpectedFailure,
    _detect_project_root,
    _is_absolute_like,
    _resolve_relative_path,
    load_manifest,
)


def _base(documents=None, **extra) -> dict:
    payload = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": documents or [],
    }
    payload.update(extra)
    return payload


def _write(root: Path, payload: dict, name: str = "manifest.json") -> Path:
    p = root / name
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return p


def _doc(**over) -> dict:
    d = {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}
    d.update(over)
    return d


def _entry(i, **kw) -> DocumentEntry:
    base = dict(
        doc_id=f"d{i}", path_str=f"{i}.pdf", resolved_path=Path(f"{i}.pdf"),
        source_type="pdf", sha256=None, categories=(), paired_with=None,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )
    base.update(kw)
    return DocumentEntry(**base)


def _man(*ds) -> Manifest:
    return Manifest(manifest_version="1.0", devset_status="incomplete",
                    documents=tuple(ds), expected_failures=(), project_root=Path("."))


# ---------- _is_absolute_like 矩阵 ----------

def test_absolute_like_matrix_batch53():
    assert _is_absolute_like("") is False
    assert _is_absolute_like("/foo") is True
    assert _is_absolute_like("C:\\foo") is True
    assert _is_absolute_like("C:/foo") is True
    assert _is_absolute_like("c:/x") is True  # 小写盘符
    assert _is_absolute_like("C:x") is False  # 冒号后无斜杠 → 相对
    assert _is_absolute_like("CC/x") is False  # 第二字符非冒号
    assert _is_absolute_like("1:/x") is False  # 首字符非字母
    assert _is_absolute_like("a\\b") is False  # 反斜杠由 _has_backslash 另行拒绝


# ---------- _resolve_relative_path 直测 ----------

def test_resolve_empty_string_batch53(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("", tmp_path, "f")
    assert "为空" in str(ei.value)


def test_resolve_absolute_rejected_batch53(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("C:/abs/x.pdf", tmp_path, "f")
    assert "禁止绝对路径" in str(ei.value)


def test_resolve_backslash_rejected_batch53(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("a\\b.pdf", tmp_path, "f")
    assert "禁止反斜杠" in str(ei.value)


def test_resolve_escape_outside_root_batch53(tmp_path):
    with pytest.raises(ManifestError) as ei:
        _resolve_relative_path("../escape.pdf", tmp_path, "f")
    assert "项目根目录之外" in str(ei.value)


def test_resolve_valid_returns_absolute_batch53(tmp_path):
    out = _resolve_relative_path("sub/x.pdf", tmp_path, "f")
    assert out.is_absolute()
    assert out == (tmp_path / "sub" / "x.pdf").resolve()


# ---------- content_group_count 配对语义 ----------

def test_group_count_no_pair_batch53():
    assert _man(_entry(1), _entry(2)).content_group_count == 2


def test_group_count_bidirectional_batch53():
    m = _man(_entry(1, paired_with="d2"), _entry(2, paired_with="d1"))
    assert m.content_group_count == 1


def test_group_count_one_directional_batch53():
    m = _man(_entry(1, paired_with="d2"), _entry(2))
    assert m.content_group_count == 1


def test_group_count_pair_plus_unpaired_batch53():
    m = _man(_entry(1, paired_with="d2"), _entry(2, paired_with="d1"), _entry(3))
    assert m.content_group_count == 2


def test_group_count_self_pair_batch53():
    assert _man(_entry(1, paired_with="d1")).content_group_count == 1


def test_group_count_ghost_pair_batch53():
    assert _man(_entry(1, paired_with="ghost")).content_group_count == 1


# ---------- Manifest 属性直测 ----------

def test_counts_properties_batch53():
    m = _man(_entry(1), _entry(2, source_type="docx"), _entry(3, source_type="docx"))
    assert m.file_count == 3
    assert m.pdf_count == 1
    assert m.docx_count == 2


def test_categories_covered_sorted_union_batch53():
    m = _man(_entry(1, categories=("z", "a")), _entry(2, categories=("a", "m")))
    assert m.categories_covered == ["a", "m", "z"]


def test_empty_manifest_counts_zero_batch53():
    m = _man()
    assert m.file_count == 0
    assert m.content_group_count == 0
    assert m.categories_covered == []


# ---------- dataclass 冻结 ----------

def test_document_entry_frozen_batch53():
    with pytest.raises(dataclasses.FrozenInstanceError):
        _entry(1).doc_id = "x"


def test_manifest_frozen_batch53():
    with pytest.raises(dataclasses.FrozenInstanceError):
        _man().devset_status = "complete"


def test_document_entry_equality_batch53():
    assert _entry(1) == _entry(1)
    assert _entry(1) != _entry(2)


# ---------- load_manifest 细节 ----------

def test_annotation_file_backslash_field_name_batch53(tmp_path):
    p = _write(tmp_path, _base([_doc(annotation_file="ann\\a.json")]))
    with pytest.raises(ManifestError) as ei:
        load_manifest(p, project_root=tmp_path)
    assert "documents[d1].annotation_file" in str(ei.value)


def test_ef_path_escape_field_name_batch53(tmp_path):
    payload = _base(expected_failures=[
        {"doc_id": "ef1", "path": "../bad.pdf", "expected_error_code": "x"}])
    p = _write(tmp_path, payload)
    with pytest.raises(ManifestError) as ei:
        load_manifest(p, project_root=tmp_path)
    assert "expected_failures[ef1].path" in str(ei.value)


def test_project_root_str_accepted_batch53(tmp_path):
    p = _write(tmp_path, _base([_doc()]))
    m = load_manifest(p, project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


def test_expectations_both_keys_roundtrip_batch53(tmp_path):
    exp = {"element_count_by_type": {"paragraph": 2}, "required_markers": ["结论"]}
    p = _write(tmp_path, _base([_doc(expectations=exp)]))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].expectations == exp


def test_paired_with_roundtrip_batch53(tmp_path):
    p = _write(tmp_path, _base([_doc(paired_with="d2"), _doc(doc_id="d2", path="b.pdf")]))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].paired_with == "d2"
    assert m.documents[1].paired_with is None


def test_manifest_version_schema_const_batch53():
    """schema 把 manifest_version 锁成 const 1.0，代码里的不兼容分支被前置拦截。"""
    from evaluation.schema import load_schema
    s = load_schema("manifest.schema.json")
    assert s["properties"]["manifest_version"]["const"] == "1.0"
    assert "manifest_version 不兼容" in inspect.getsource(manifest_mod)


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(manifest_mod)


def test_source_empty_string_branch_batch53():
    src = _src()
    assert "if not path_str:" in src
    assert 'raise ManifestError(f"{field_name} 为空")' in src


def test_source_relative_to_call_batch53():
    assert "resolved.relative_to(project_root_resolved)" in _src()


def test_source_escape_message_batch53():
    assert "解析后位于项目根目录之外：{path_str} → {resolved}" in _src()


def test_source_pair_ids_add_batch53():
    assert "pair_ids.add(frozenset([d.doc_id, d.paired_with]))" in _src()
    assert "return groups + unpaired" in _src()


def test_source_default_gets_batch53():
    src = _src()
    assert 'data.get("documents", [])' in src
    assert 'data.get("expected_failures", [])' in src


def test_source_list_annotations_batch53():
    src = _src()
    assert "documents: list[DocumentEntry] = []" in src
    assert "failures: list[ExpectedFailure] = []" in src


def test_source_categories_tuple_batch53():
    assert "tuple(d.get(\"categories\", []))" in _src()


def test_source_ef_source_type_get_batch53():
    assert "source_type=ef.get(\"source_type\")" in _src()


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(manifest_mod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in ast.walk(_tree())
                if isinstance(n, ast.FunctionDef) and n.name == name)


def test_ast_manifest_five_properties_batch53():
    tree = _tree()
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    props = [f.name for f in cls.body
             if isinstance(f, ast.FunctionDef)
             and any(isinstance(d, ast.Name) and d.id == "property"
                     for d in f.decorator_list)]
    assert props == ["file_count", "pdf_count", "docx_count",
                     "content_group_count", "categories_covered"]


def test_ast_group_count_three_fors_batch53():
    f = _func("content_group_count")
    assert len([n for n in ast.walk(f) if isinstance(n, ast.For)]) == 3


def test_ast_resolve_four_raises_one_try_batch53():
    """4 个 raise：空串 / 绝对 / 反斜杠 / 越根。"""
    f = _func("_resolve_relative_path")
    raises = [n for n in ast.walk(f) if isinstance(n, ast.Raise)]
    trys = [n for n in ast.walk(f) if isinstance(n, ast.Try)]
    assert len(raises) == 4
    assert len(trys) == 1


def test_ast_load_manifest_two_fors_two_appends_batch53():
    f = _func("load_manifest")
    assert len([n for n in ast.walk(f) if isinstance(n, ast.For)]) == 2
    appends = [n for n in ast.walk(f)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == "append"]
    assert len(appends) == 2


def test_ast_detect_root_two_ifs_two_returns_batch53():
    f = _func("_detect_project_root")
    assert len([n for n in ast.walk(f) if isinstance(n, ast.If)]) == 2
    assert len([n for n in ast.walk(f) if isinstance(n, ast.Return)]) == 2


# ---------- forbidden tokens 第一百八十批 ----------

def test_source_no_eval_batch53():
    assert "eval(" not in _src()


def test_source_no_exec_batch53():
    assert "exec(" not in _src()


def test_source_no_compile_batch53():
    assert "compile(" not in _src()


def test_source_no_globals_batch53():
    assert "globals(" not in _src()


def test_source_no_locals_batch53():
    assert "locals(" not in _src()


def test_source_no_os_system_batch53():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch53():
    assert "subprocess" not in _src()


def test_source_no_popen_batch53():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch53():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch53():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch53():
    assert "socket" not in _src()


def test_source_no_requests_batch53():
    assert "requests" not in _src()


def test_source_no_urllib_batch53():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch53():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch53():
    assert "yield" not in _src()


def test_source_no_async_await_batch53():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_1_batch53():
    assert _src().count("open(") == 1
