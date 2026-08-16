"""evaluation/manifest.py 第九十九轮 edges 测试（Round 717）。

补强 edges82 未触及的角度（第八十二批）。

新角度：
- 版本不兼容死分支激活（monkeypatch MANIFEST_VERSION="2.0" → schema 过但代码比对抛不兼容）
- _detect_project_root 嵌套向上查找（c 下清单 → 找到 b 的 pyproject）
- 清单 BOM 字节 → JSON 解析失败 ManifestError / 顶层数组 → EvalSchemaError（非 ManifestError）
- ghost 路径不查存在性（不存在文件照常加载，记录现状）
- 重复 doc_id 允许（两份同 id 都加载）
- doc 全可选字段一次回读（sha256+categories+paired_with+annotation_file+expectations）
- ef 完整回读（source_type txt / other 枚举边界）
- _resolve_relative_path 点段（./a.pdf 与 a//b.pdf 均可解析）
- 源码补强（不存在/解析失败 raise / validate 调用行 / 版本比对行 / 双 resolve / cur=cur.parent / parents 展开 / 双 return）
- AST 补强（三类字段数 10/5/5 精确名单 / load_manifest 3 Raise+1 With+1 Try+4 If）
- forbidden tokens 第一百八十七批
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
    _detect_project_root,
    _resolve_relative_path,
    load_manifest,
)
from evaluation.schema import EvalSchemaError


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


# ---------- 版本不兼容死分支 ----------

def test_version_mismatch_branch_activated_batch53(tmp_path, monkeypatch):
    monkeypatch.setattr(manifest_mod, "MANIFEST_VERSION", "2.0")
    p = _write(tmp_path, _base())
    with pytest.raises(ManifestError) as ei:
        load_manifest(p, project_root=tmp_path)
    msg = str(ei.value)
    assert "manifest_version 不兼容" in msg
    assert "清单=1.0" in msg
    assert "代码=2.0" in msg


# ---------- _detect_project_root 嵌套 ----------

def test_detect_root_nested_walkup_batch53(tmp_path):
    b = tmp_path / "a" / "b"
    c = b / "c"
    c.mkdir(parents=True)
    (b / "pyproject.toml").write_text("", encoding="utf-8")
    assert _detect_project_root(c / "m.json") == b


def test_detect_root_file_start_uses_parent_batch53(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    f = tmp_path / "m.json"
    f.write_text("{}", encoding="utf-8")
    assert _detect_project_root(f) == tmp_path


# ---------- 解析失败形态 ----------

def test_manifest_bom_bytes_rejected_batch53(tmp_path):
    p = tmp_path / "m.json"
    p.write_bytes(b"\xef\xbb\xbf" + json.dumps(_base()).encode("utf-8"))
    with pytest.raises(ManifestError) as ei:
        load_manifest(p, project_root=tmp_path)
    assert "清单 JSON 解析失败" in str(ei.value)


def test_manifest_top_level_array_eval_error_batch53(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        load_manifest(p, project_root=tmp_path)


def test_manifest_missing_file_batch53(tmp_path):
    with pytest.raises(ManifestError) as ei:
        load_manifest(tmp_path / "ghost.json", project_root=tmp_path)
    assert "清单文件不存在" in str(ei.value)


# ---------- 现状记录 ----------

def test_ghost_path_loads_without_existence_check_batch53(tmp_path):
    p = _write(tmp_path, _base([_doc(path="ghost/deep/no.pdf")]))
    m = load_manifest(p, project_root=tmp_path)
    assert m.documents[0].resolved_path.name == "no.pdf"


def test_duplicate_doc_ids_allowed_batch53(tmp_path):
    p = _write(tmp_path, _base([_doc(doc_id="same"), _doc(doc_id="same", path="b.pdf")]))
    m = load_manifest(p, project_root=tmp_path)
    assert [d.doc_id for d in m.documents] == ["same", "same"]
    assert m.file_count == 2


# ---------- 全字段回读 ----------

def test_doc_all_optional_fields_roundtrip_batch53(tmp_path):
    ann = tmp_path / "a.json"
    ann.write_text("{}", encoding="utf-8")
    sha = "0123456789abcdef" * 4
    p = _write(tmp_path, _base([_doc(
        sha256=sha, categories=["c1", "c2"], paired_with="d0",
        annotation_file="a.json",
        expectations={"element_count_by_type": {"paragraph": 1}},
    )]))
    m = load_manifest(p, project_root=tmp_path)
    d = m.documents[0]
    assert d.sha256 == sha
    assert d.categories == ("c1", "c2")
    assert d.paired_with == "d0"
    assert d.annotation_file_str == "a.json"
    assert d.annotation_resolved == ann.resolve()
    assert d.expectations == {"element_count_by_type": {"paragraph": 1}}


def test_ef_full_roundtrip_txt_batch53(tmp_path):
    payload = _base(expected_failures=[
        {"doc_id": "ef1", "path": "bad.txt", "expected_error_code": "unsupported",
         "source_type": "txt"},
        {"doc_id": "ef2", "path": "bad2.bin", "expected_error_code": "x",
         "source_type": "other"},
    ])
    m = load_manifest(_write(tmp_path, payload), project_root=tmp_path)
    ef1, ef2 = m.expected_failures
    assert ef1.source_type == "txt"
    assert ef1.expected_error_code == "unsupported"
    assert ef2.source_type == "other"
    assert m.expected_failures[0].path_str == "bad.txt"


# ---------- 点段路径 ----------

def test_resolve_dot_segment_batch53(tmp_path):
    out = _resolve_relative_path("./a.pdf", tmp_path, "f")
    assert out == (tmp_path / "a.pdf").resolve()


def test_resolve_double_slash_batch53(tmp_path):
    out = _resolve_relative_path("sub//x.pdf", tmp_path, "f")
    assert out == (tmp_path / "sub" / "x.pdf").resolve()


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(manifest_mod)


def test_source_raise_messages_batch53():
    src = _src()
    assert 'raise ManifestError(f"清单文件不存在: {p}")' in src
    assert 'raise ManifestError(f"清单 JSON 解析失败: {e}") from e' in src


def test_source_validate_call_line_batch53():
    assert 'validate(data, "manifest.schema.json")' in _src()


def test_source_version_compare_line_batch53():
    assert 'if data.get("manifest_version") != MANIFEST_VERSION:' in _src()


def test_source_double_resolve_batch53():
    src = _src()
    assert "p = Path(manifest_path).resolve()" in src
    assert "project_root = Path(project_root).resolve()" in src


def test_source_detect_root_lines_batch53():
    src = _src()
    assert "cur = cur.parent" in src
    assert "for parent in [cur, *cur.parents]:" in src
    assert src.count("return parent") == 1
    assert src.count("return cur") == 1


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(manifest_mod))


def test_ast_class_field_names_batch53():
    fields = {}
    for cls in [n for n in _tree().body if isinstance(n, ast.ClassDef)]:
        fields[cls.name] = [a.target.id for a in cls.body if isinstance(a, ast.AnnAssign)]
    assert fields["DocumentEntry"] == [
        "doc_id", "path_str", "resolved_path", "source_type", "sha256",
        "categories", "paired_with", "annotation_file_str",
        "annotation_resolved", "expectations",
    ]
    assert fields["ExpectedFailure"] == [
        "doc_id", "path_str", "resolved_path", "expected_error_code", "source_type",
    ]
    assert fields["Manifest"] == [
        "manifest_version", "devset_status", "documents",
        "expected_failures", "project_root",
    ]


def test_ast_load_manifest_structure_batch53():
    import collections
    lm = next(n for n in _tree().body
              if isinstance(n, ast.FunctionDef) and n.name == "load_manifest")
    c = collections.Counter(type(n).__name__ for n in ast.walk(lm))
    assert (c["Raise"], c["With"], c["Try"], c["If"]) == (3, 1, 1, 4)


# ---------- forbidden tokens 第一百八十七批 ----------

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
