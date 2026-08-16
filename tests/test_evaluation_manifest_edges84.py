"""evaluation/manifest.py 第二百零一轮 edges 测试（Round 724）。

补强 edges82/edges83 未触及的角度（第八十九批）。

新角度：
- _is_absolute_like 深矩阵（"ä:/x" 非盘符字母也过（isalpha 现状）/ "C:x" 无斜杠拒 /
  "AB:/x" 双字母拒 / "1:/x" 数字拒 / "C:" len2 拒 / ":/x" 拒）
- content_group_count 链式不传递合并（a→b, b→c, c 无 → 2 组，非 1 组）
- paired_with="" 空串视为未配对（falsy）
- 三角配对（a→b, b→a, c→a → frozenset 去重 → 2 组）
- devset_status "complete" 可加载（schema enum 两值）
- annotation_file 空串：过 schema（无 minLength）但 falsy → annotation_resolved None（现状记录）
- expectations 未知键 → EvalSchemaError（additionalProperties false）
- 顶层 null JSON → EvalSchemaError（非 ManifestError）
- 逃逸 field 名精确（documents[d1].path / documents[d1].annotation_file / expected_failures[ef1].path）
- 四类 raise 的行为级消息（空/绝对/反斜杠/越界）
- _detect_project_root 无 pyproject 兜底返回 cur
- 空 documents 的五个 property 全零/空
- load_manifest 接受 str manifest_path 与 str project_root
- AST（五函数 If/For/Return/Raise/Try/Call / Manifest 5 property 名单）
- 源码补强（paired_with×8 / data.get×4 / d.get×6 / ef.get×1）
- forbidden tokens 第一百九十四批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import pytest

import evaluation.manifest as manifest_mod
from evaluation.manifest import (
    ManifestError,
    Manifest,
    DocumentEntry,
    _detect_project_root,
    _has_backslash,
    _is_absolute_like,
    _resolve_relative_path,
    load_manifest,
)
from evaluation.schema import EvalSchemaError


def _base(documents=None, efs=None, status="incomplete", **extra) -> dict:
    payload = {
        "manifest_version": "1.0",
        "devset_status": status,
        "documents": documents or [],
    }
    if efs is not None:
        payload["expected_failures"] = efs
    payload.update(extra)
    return payload


def _write(root: Path, payload: dict) -> Path:
    p = root / "m.json"
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return p


def _doc(**over) -> dict:
    d = {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"}
    d.update(over)
    return d


# ---------- _is_absolute_like 深矩阵 ----------

@pytest.mark.parametrize("s,expected", [
    ("/foo", True),
    ("C:\\foo", True),
    ("C:/foo", True),
    ("ä:/x", True),      # isalpha() 对非 ASCII 也成立（现状记录）
    ("Ω:/x", True),
    ("C:", False),        # len < 3
    ("C:x", False),       # 冒号后无斜杠
    ("AB:/x", False),     # 第二字符非冒号
    ("1:/x", False),      # 数字非字母
    (":/x", False),
    ("foo/bar", False),
    ("", False),
])
def test_is_absolute_like_matrix_batch53(s, expected):
    assert _is_absolute_like(s) is expected


def test_has_backslash_direct_batch53():
    assert _has_backslash("a\\b") is True
    assert _has_backslash("a/b") is False
    assert _has_backslash("") is False


# ---------- content_group_count 语义 ----------

def _entry(doc_id, paired=None):
    return DocumentEntry(
        doc_id=doc_id, path_str=f"{doc_id}.pdf", resolved_path=Path("x"),
        source_type="pdf", sha256=None, categories=(), paired_with=paired,
        annotation_file_str=None, annotation_resolved=None, expectations=None,
    )


def _manifest(*docs) -> Manifest:
    return Manifest("1.0", "incomplete", tuple(docs), (), Path("root"))


def test_chain_pairs_do_not_merge_batch53():
    # a→b, b→c：frozenset {a,b} 与 {b,c} 不合并 → 2 组（非传递闭包）
    m = _manifest(_entry("a", "b"), _entry("b", "c"), _entry("c"))
    assert m.content_group_count == 2


def test_empty_string_paired_with_is_unpaired_batch53():
    m = _manifest(_entry("a", ""), _entry("b"))
    assert m.content_group_count == 2  # 两个都算未配对


def test_triangle_pairing_dedup_batch53():
    # a→b, b→a, c→a：{a,b} 重复去重 + {a,c} → 2 组
    m = _manifest(_entry("a", "b"), _entry("b", "a"), _entry("c", "a"))
    assert m.content_group_count == 2


def test_empty_documents_properties_batch53():
    m = _manifest()
    assert m.file_count == 0
    assert m.pdf_count == 0
    assert m.docx_count == 0
    assert m.content_group_count == 0
    assert m.categories_covered == []


# ---------- devset_status / annotation_file 空串 ----------

def test_devset_status_complete_loads_batch53(tmp_path):
    m = load_manifest(_write(tmp_path, _base(status="complete")),
                      project_root=tmp_path)
    assert m.devset_status == "complete"


def test_annotation_file_empty_string_loads_batch53(tmp_path):
    m = load_manifest(_write(tmp_path, _base([_doc(annotation_file="")])),
                      project_root=tmp_path)
    d = m.documents[0]
    assert d.annotation_file_str == ""       # 原样保留
    assert d.annotation_resolved is None      # falsy → 不解析（现状记录）


# ---------- schema 层拒绝 ----------

def test_expectations_unknown_key_rejected_batch53(tmp_path):
    p = _write(tmp_path, _base([_doc(expectations={"bogus": 1})]))
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_top_level_null_rejected_batch53(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("null", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_documents_missing_rejected_batch53(tmp_path):
    p = _write(tmp_path, {"manifest_version": "1.0", "devset_status": "incomplete"})
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


# ---------- 逃逸 field 名 ----------

def test_escape_field_names_batch53(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(_write(tmp_path, _base([_doc(path="../esc.pdf")])),
                      project_root=tmp_path)
    assert "documents[d1].path" in str(ei.value)
    assert "项目根目录之外" in str(ei.value)


def test_annotation_escape_field_name_batch53(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(_write(tmp_path, _base([_doc(annotation_file="../a.json")])),
                      project_root=tmp_path)
    assert "documents[d1].annotation_file" in str(ei.value)


def test_ef_escape_field_name_batch53(tmp_path):
    p = _write(tmp_path, _base(efs=[
        {"doc_id": "ef1", "path": "../x.bin", "expected_error_code": "x"}]))
    with pytest.raises(ManifestError) as ei:
        load_manifest(p, project_root=tmp_path)
    assert "expected_failures[ef1].path" in str(ei.value)


# ---------- 四类 raise 行为消息 ----------

def test_empty_path_blocked_by_schema_first_batch53(tmp_path):
    # schema 的 minLength 1 先拦住；代码里 "为空" 分支只能被 _resolve_relative_path
    # 直调触达（见 test_resolve_direct_all_four_raises）
    with pytest.raises(EvalSchemaError):
        load_manifest(_write(tmp_path, _base([_doc(path="")])),
                      project_root=tmp_path)


def test_absolute_path_message_batch53(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(_write(tmp_path, _base([_doc(path="/abs/a.pdf")])),
                      project_root=tmp_path)
    assert "禁止绝对路径：/abs/a.pdf" in str(ei.value)


def test_backslash_path_message_batch53(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(_write(tmp_path, _base([_doc(path="sub\\a.pdf")])),
                      project_root=tmp_path)
    assert "禁止反斜杠：sub\\a.pdf" in str(ei.value)


def test_resolve_direct_all_four_raises_batch53(tmp_path):
    with pytest.raises(ManifestError, match="f 为空"):
        _resolve_relative_path("", tmp_path, "f")
    with pytest.raises(ManifestError, match="禁止绝对路径"):
        _resolve_relative_path("/x", tmp_path, "f")
    with pytest.raises(ManifestError, match="禁止反斜杠"):
        _resolve_relative_path("a\\b", tmp_path, "f")
    with pytest.raises(ManifestError, match="项目根目录之外"):
        _resolve_relative_path("../x", tmp_path, "f")


# ---------- _detect_project_root 兜底 ----------

def test_detect_root_fallback_no_pyproject_batch53(tmp_path):
    mfile = tmp_path / "m.json"
    mfile.write_text("{}", encoding="utf-8")
    assert _detect_project_root(mfile) == tmp_path  # 无 pyproject → manifest 所在目录


# ---------- str 入参 ----------

def test_load_manifest_str_args_batch53(tmp_path):
    p = _write(tmp_path, _base())
    m = load_manifest(str(p), project_root=str(tmp_path))
    assert m.project_root == tmp_path.resolve()


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(manifest_mod)


def test_source_get_counts_batch53():
    src = _src()
    assert src.count("paired_with") == 8
    assert src.count("data.get(") == 4
    assert src.count("d.get(") == 6
    assert src.count("ef.get(") == 1


def test_source_key_lines_batch53():
    src = _src()
    assert "from evaluation import MANIFEST_VERSION" in src
    assert 'validate(data, "manifest.schema.json")' in src
    assert 'categories=tuple(d.get("categories", []))' in src
    assert "documents: tuple[DocumentEntry, ...]" in src


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(manifest_mod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _counts(func) -> dict:
    import collections
    return collections.Counter(type(n).__name__ for n in ast.walk(func))


@pytest.mark.parametrize("name,expect", [
    ("_is_absolute_like", (4, 0, 4, 0, 0, 3, 1)),
    ("_has_backslash", (0, 0, 1, 0, 0, 0, 0)),
    ("_detect_project_root", (2, 1, 2, 0, 0, 3, 0)),
    ("_resolve_relative_path", (3, 0, 1, 4, 1, 9, 0)),
    ("load_manifest", (4, 2, 1, 3, 1, 34, 0)),
])
def test_ast_function_structures_batch53(name, expect):
    c = _counts(_func(name))
    got = (c["If"], c["For"], c["Return"], c["Raise"], c["Try"], c["Call"],
           c["BoolOp"])
    assert got == expect, name


def test_ast_manifest_property_names_batch53():
    cls = next(n for n in _tree().body
               if isinstance(n, ast.ClassDef) and n.name == "Manifest")
    methods = [n.name for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert methods == ["file_count", "pdf_count", "docx_count",
                       "content_group_count", "categories_covered"]


# ---------- forbidden tokens 第一百九十四批 ----------

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
