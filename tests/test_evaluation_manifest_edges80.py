"""evaluation/manifest.py 第九十六轮 edges 测试（Round 696）。

补强 edges79 未触及的角度（第六十一批）。

新角度：
- Schema 拒绝矩阵经 load_manifest（顶层多余键 / 缺 documents / devset_status 坏值 / doc 缺 doc_id·doc_id 空串 / source_type txt 不在 document 枚举 / sha256 非 64hex / doc 多余键 / expectations 多余键 / element_count_by_type 负数 / required_markers 空串项 / ef 缺 expected_error_code / ef source_type 坏值 / documents 非数组）
- ExpectedFailure 往返（source_type "txt" 合法保留 / 缺省 None / expected_error_code 透传 / 多 ef 保序）
- load_manifest 不检查文件实存（ghost 路径照常加载）
- frozen dataclass（FrozenInstanceError / fields 精确名单 10-5-5 / 可 hash）
- _detect_project_root（嵌套文件起点 / 深层目录 / 找不到 pyproject 返回起点目录）
- _is_absolute_like 更多（é:/x Unicode 盘符 True / "C:" 两字符 False / "/" 与 "//" / 恰 3 字符 C:\\）
- _resolve_relative_path "." 解析为根本身
- 最小空清单全属性零值 / 全 docx 时 pdf_count=0 / 全字段文档往返（categories tuple / expectations dict 原样）
- 源码补强（import 两行 / 为空消息 / relative_to / get 默认 / frozenset / sorted / 反斜杠一行 / open encoding / validate 调用 / 版本不兼容双段）
- AST 补强（3 个 dataclass Call frozen=True / detect root 的 [cur, *cur.parents] / load_manifest Try 1 个 handler / __all__ 精确 / _resolve_relative_path 3 参数无默认 / Manifest 5 property 顺序 / _is_absolute_like 4 个 Return）
- forbidden tokens 第一百六十六批
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

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
from evaluation.schema import EvalSchemaError


def _base(documents: list | None = None, **extra) -> dict:
    payload = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": documents or [],
    }
    payload.update(extra)
    return payload


def _write(tmp_path: Path, payload: dict) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


# ---------- Schema 拒绝矩阵（经 load_manifest） ----------

def test_load_rejects_top_level_extra_key_batch52(tmp_path):
    with pytest.raises(EvalSchemaError):
        load_manifest(_write(tmp_path, _base(extra=1)), project_root=tmp_path)


def test_load_rejects_missing_documents_batch52(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"manifest_version": "1.0", "devset_status": "complete"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_load_rejects_bad_devset_status_batch52(tmp_path):
    with pytest.raises(EvalSchemaError):
        load_manifest(_write(tmp_path, _base(devset_status="maybe")), project_root=tmp_path)


def test_load_rejects_doc_missing_doc_id_batch52(tmp_path):
    docs = [{"path": "a.pdf", "source_type": "pdf"}]
    with pytest.raises(EvalSchemaError):
        load_manifest(_write(tmp_path, _base(docs)), project_root=tmp_path)


def test_load_rejects_empty_doc_id_batch52(tmp_path):
    docs = [{"doc_id": "", "path": "a.pdf", "source_type": "pdf"}]
    with pytest.raises(EvalSchemaError):
        load_manifest(_write(tmp_path, _base(docs)), project_root=tmp_path)


def test_load_rejects_doc_source_type_txt_batch52(tmp_path):
    """document 的 source_type 枚举只有 pdf/docx（ef 才有 txt/other）。"""
    docs = [{"doc_id": "d1", "path": "a.txt", "source_type": "txt"}]
    with pytest.raises(EvalSchemaError):
        load_manifest(_write(tmp_path, _base(docs)), project_root=tmp_path)


def test_load_rejects_bad_sha256_batch52(tmp_path):
    docs = [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "sha256": "xyz"}]
    with pytest.raises(EvalSchemaError):
        load_manifest(_write(tmp_path, _base(docs)), project_root=tmp_path)


def test_load_rejects_doc_extra_key_batch52(tmp_path):
    docs = [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf", "foo": 1}]
    with pytest.raises(EvalSchemaError):
        load_manifest(_write(tmp_path, _base(docs)), project_root=tmp_path)


def test_load_rejects_expectations_extra_key_batch52(tmp_path):
    docs = [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "expectations": {"surprise": 1}}]
    with pytest.raises(EvalSchemaError):
        load_manifest(_write(tmp_path, _base(docs)), project_root=tmp_path)


def test_load_rejects_negative_expected_count_batch52(tmp_path):
    docs = [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "expectations": {"element_count_by_type": {"paragraph": -1}}}]
    with pytest.raises(EvalSchemaError):
        load_manifest(_write(tmp_path, _base(docs)), project_root=tmp_path)


def test_load_rejects_empty_marker_string_batch52(tmp_path):
    docs = [{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf",
             "expectations": {"required_markers": [""]}}]
    with pytest.raises(EvalSchemaError):
        load_manifest(_write(tmp_path, _base(docs)), project_root=tmp_path)


def test_load_rejects_ef_missing_error_code_batch52(tmp_path):
    payload = _base([{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}])
    payload["expected_failures"] = [{"doc_id": "ef1", "path": "bad.pdf"}]
    with pytest.raises(EvalSchemaError):
        load_manifest(_write(tmp_path, payload), project_root=tmp_path)


def test_load_rejects_ef_bad_source_type_batch52(tmp_path):
    payload = _base([{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}])
    payload["expected_failures"] = [
        {"doc_id": "ef1", "path": "bad.pdf", "expected_error_code": "x", "source_type": "pdf2"},
    ]
    with pytest.raises(EvalSchemaError):
        load_manifest(_write(tmp_path, payload), project_root=tmp_path)


def test_load_rejects_documents_string_batch52(tmp_path):
    with pytest.raises(EvalSchemaError):
        load_manifest(_write(tmp_path, _base("not-a-list")), project_root=tmp_path)


def test_load_schema_error_is_not_manifest_error_batch52(tmp_path):
    """Schema 错误透传 EvalSchemaError，不包装成 ManifestError。"""
    with pytest.raises(EvalSchemaError) as ei:
        load_manifest(_write(tmp_path, _base(bad="x")), project_root=tmp_path)
    assert not isinstance(ei.value, ManifestError)


# ---------- ExpectedFailure 往返 ----------

def _ef_manifest(*efs: dict) -> dict:
    payload = _base([{"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}])
    payload["expected_failures"] = list(efs)
    return payload


def test_ef_source_type_txt_allowed_batch52(tmp_path):
    payload = _ef_manifest({"doc_id": "ef1", "path": "b.txt",
                            "expected_error_code": "unsupported", "source_type": "txt"})
    m = load_manifest(_write(tmp_path, payload), project_root=tmp_path)
    assert m.expected_failures[0].source_type == "txt"


def test_ef_source_type_other_allowed_batch52(tmp_path):
    payload = _ef_manifest({"doc_id": "ef1", "path": "b.bin",
                            "expected_error_code": "unsupported", "source_type": "other"})
    m = load_manifest(_write(tmp_path, payload), project_root=tmp_path)
    assert m.expected_failures[0].source_type == "other"


def test_ef_source_type_defaults_none_batch52(tmp_path):
    payload = _ef_manifest({"doc_id": "ef1", "path": "b.pdf", "expected_error_code": "boom"})
    m = load_manifest(_write(tmp_path, payload), project_root=tmp_path)
    ef = m.expected_failures[0]
    assert ef.source_type is None
    assert ef.expected_error_code == "boom"
    assert ef.path_str == "b.pdf"
    assert ef.resolved_path == (tmp_path / "b.pdf").resolve()


def test_ef_multiple_preserve_order_batch52(tmp_path):
    payload = _ef_manifest(
        {"doc_id": "efA", "path": "a.pdf", "expected_error_code": "e1"},
        {"doc_id": "efB", "path": "b.pdf", "expected_error_code": "e2"},
        {"doc_id": "efC", "path": "c.pdf", "expected_error_code": "e3"},
    )
    m = load_manifest(_write(tmp_path, payload), project_root=tmp_path)
    assert [ef.doc_id for ef in m.expected_failures] == ["efA", "efB", "efC"]
    assert isinstance(m.expected_failures, tuple)


# ---------- 文件实存不检查 ----------

def test_ghost_document_path_loads_batch52(tmp_path):
    docs = [{"doc_id": "d1", "path": "ghost/no-such.pdf", "source_type": "pdf"}]
    m = load_manifest(_write(tmp_path, _base(docs)), project_root=tmp_path)
    assert m.documents[0].resolved_path == (tmp_path / "ghost" / "no-such.pdf").resolve()
    assert not m.documents[0].resolved_path.exists()


def test_ghost_ef_path_loads_batch52(tmp_path):
    payload = _ef_manifest({"doc_id": "ef1", "path": "ghost/bad.pdf", "expected_error_code": "x"})
    m = load_manifest(_write(tmp_path, payload), project_root=tmp_path)
    assert not m.expected_failures[0].resolved_path.exists()


# ---------- frozen dataclass ----------

def _entry(**over) -> DocumentEntry:
    kw = dict(
        doc_id="d", path_str="a/b.pdf", resolved_path=Path("x"),
        source_type="pdf", sha256=None, categories=("c",),
        paired_with=None, annotation_file_str=None,
        annotation_resolved=None, expectations=None,
    )
    kw.update(over)
    return DocumentEntry(**kw)


def test_document_entry_frozen_batch52():
    with pytest.raises(FrozenInstanceError):
        _entry().doc_id = "z"


def test_manifest_frozen_batch52(tmp_path):
    m = load_manifest(_write(tmp_path, _base()), project_root=tmp_path)
    with pytest.raises(FrozenInstanceError):
        m.devset_status = "complete"


def test_expected_failure_frozen_batch52():
    ef = ExpectedFailure("e", "p", Path("x"), "code", None)
    with pytest.raises(FrozenInstanceError):
        ef.doc_id = "z"


def test_fields_names_exact_batch52():
    assert [f.name for f in dataclasses.fields(DocumentEntry)] == [
        "doc_id", "path_str", "resolved_path", "source_type", "sha256",
        "categories", "paired_with", "annotation_file_str",
        "annotation_resolved", "expectations",
    ]
    assert [f.name for f in dataclasses.fields(ExpectedFailure)] == [
        "doc_id", "path_str", "resolved_path", "expected_error_code", "source_type",
    ]
    assert [f.name for f in dataclasses.fields(Manifest)] == [
        "manifest_version", "devset_status", "documents",
        "expected_failures", "project_root",
    ]


def test_entries_hashable_batch52():
    s = {_entry(doc_id="a"), _entry(doc_id="a"), _entry(doc_id="b")}
    assert len(s) == 2


# ---------- _detect_project_root ----------

def test_detect_root_from_nested_file_batch52(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    deep = tmp_path / "sub" / "deep"
    deep.mkdir(parents=True)
    f = deep / "x.txt"
    f.write_text("", encoding="utf-8")
    assert _detect_project_root(f) == tmp_path


def test_detect_root_deep_dir_batch52(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    assert _detect_project_root(deep) == tmp_path


def test_detect_root_missing_pyproject_returns_start_batch52(tmp_path):
    nested = tmp_path / "x" / "y"
    nested.mkdir(parents=True)
    res = _detect_project_root(nested)
    assert res == nested or res in nested.parents


# ---------- _is_absolute_like 更多 ----------

def test_abs_like_unicode_drive_batch52():
    assert _is_absolute_like("é:/x") is True


def test_abs_like_two_char_drive_batch52():
    assert _is_absolute_like("C:") is False


def test_abs_like_single_slash_batch52():
    assert _is_absolute_like("/") is True
    assert _is_absolute_like("//") is True


def test_abs_like_exact_three_chars_batch52():
    assert _is_absolute_like("C:\\") is True
    assert _is_absolute_like("C:/") is True


# ---------- _resolve_relative_path "." ----------

def test_resolve_dot_is_root_batch52(tmp_path):
    assert _resolve_relative_path(".", tmp_path, "f") == tmp_path.resolve()


# ---------- 最小空清单 / 计数 ----------

def test_minimal_empty_manifest_all_zero_batch52(tmp_path):
    m = load_manifest(_write(tmp_path, _base()), project_root=tmp_path)
    assert m.file_count == 0
    assert m.pdf_count == 0
    assert m.docx_count == 0
    assert m.content_group_count == 0
    assert m.categories_covered == []
    assert m.expected_failures == ()
    assert m.manifest_version == "1.0"
    assert m.devset_status == "complete"


def test_all_docx_pdf_count_zero_batch52(tmp_path):
    docs = [
        {"doc_id": "d1", "path": "a.docx", "source_type": "docx"},
        {"doc_id": "d2", "path": "b.docx", "source_type": "docx"},
    ]
    m = load_manifest(_write(tmp_path, _base(docs)), project_root=tmp_path)
    assert m.pdf_count == 0
    assert m.docx_count == 2
    assert m.file_count == 2


def test_full_optional_fields_roundtrip_batch52(tmp_path):
    exp = {
        "element_count_by_type": {"paragraph": 3, "heading": 1},
        "required_markers": ["第一章"],
    }
    docs = [{
        "doc_id": "d1", "path": "a/b.pdf", "source_type": "pdf",
        "sha256": "a" * 64, "categories": ["c1", "c2"],
        "paired_with": "d2", "annotation_file": "ann/a.json",
        "expectations": exp,
    }, {
        "doc_id": "d2", "path": "a/b.docx", "source_type": "docx",
        "paired_with": "d1",
    }]
    m = load_manifest(_write(tmp_path, _base(docs)), project_root=tmp_path)
    d = m.documents[0]
    assert d.sha256 == "a" * 64
    assert d.categories == ("c1", "c2")
    assert isinstance(d.categories, tuple)
    assert d.paired_with == "d2"
    assert d.annotation_file_str == "ann/a.json"
    assert d.annotation_resolved == (tmp_path / "ann" / "a.json").resolve()
    assert d.expectations == exp
    # 双向配对 → 1 组 + 0 未配对
    assert m.content_group_count == 1


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(manifest_mod)


def test_source_imports_batch52():
    src = _src()
    assert "from evaluation import MANIFEST_VERSION" in src
    assert "from evaluation.schema import validate" in src


def test_source_empty_field_message_batch52():
    assert 'raise ManifestError(f"{field_name} 为空")' in _src()


def test_source_relative_to_call_batch52():
    assert "resolved.relative_to(project_root_resolved)" in _src()


def test_source_get_defaults_batch52():
    src = _src()
    assert 'data.get("documents", [])' in src
    assert 'data.get("expected_failures", [])' in src


def test_source_frozenset_add_batch52():
    assert "pair_ids.add(frozenset([d.doc_id, d.paired_with]))" in _src()


def test_source_sorted_categories_batch52():
    assert "return sorted(s)" in _src()


def test_source_backslash_one_liner_batch52():
    assert 'return "\\\\" in path_str' in _src()


def test_source_open_encoding_batch52():
    assert 'with p.open("r", encoding="utf-8") as f:' in _src()


def test_source_validate_call_batch52():
    assert 'validate(data, "manifest.schema.json")' in _src()


def test_source_version_mismatch_two_parts_batch52():
    src = _src()
    assert "manifest_version 不兼容" in src
    assert "代码={MANIFEST_VERSION}" in src


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(manifest_mod))


def test_ast_3_dataclasses_frozen_batch52():
    tree = _tree()
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    # ManifestError 无装饰器；其余 3 个是 @dataclass(frozen=True)
    assert [c.name for c in classes] == ["ManifestError", "DocumentEntry", "ExpectedFailure", "Manifest"]
    assert classes[0].decorator_list == []
    for c in classes[1:]:
        dec = c.decorator_list[0]
        assert isinstance(dec, ast.Call)
        assert isinstance(dec.func, ast.Name) and dec.func.id == "dataclass"
        kw = {k.arg: k.value.value for k in dec.keywords}
        assert kw == {"frozen": True}


def test_ast_detect_root_starred_parents_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_detect_project_root")
    assert "for parent in [cur, *cur.parents]:" in ast.unparse(func)


def test_ast_load_manifest_try_one_handler_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1
    handler = trys[0].handlers[0]
    assert ast.unparse(handler.type) == "json.JSONDecodeError"
    assert "raise ManifestError" in ast.unparse(handler.body[0])
    assert handler.body[0].cause is not None  # from e


def test_ast_all_exact_batch52():
    tree = _tree()
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert ast.unparse(all_assign) == (
        "__all__ = ['ManifestError', 'Manifest', 'DocumentEntry', "
        "'ExpectedFailure', 'load_manifest']"
    )


def test_ast_resolve_relative_path_3_args_no_default_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_resolve_relative_path")
    assert len(func.args.args) == 3
    assert len(func.args.defaults) == 0


def test_ast_manifest_5_properties_order_batch52():
    tree = _tree()
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    props = [n.name for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert props == ["file_count", "pdf_count", "docx_count", "content_group_count", "categories_covered"]


def test_ast_is_absolute_like_4_returns_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_is_absolute_like")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 4


def test_ast_manifest_error_is_class_batch52():
    tree = _tree()
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ManifestError")
    assert [ast.unparse(b) for b in cls.bases] == ["Exception"]


# ---------- forbidden tokens 第一百六十六批 ----------

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
