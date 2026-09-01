"""批次 20 Phase D：.myx 外部插件全链验证（测试专用，永不内置）。

正向链（subprocess 走真实 CLI，不绕过任何一层）：
    外部模块文件 → --plugin 加载 → registry 注册 → --parser auto
    扩展名发现 → parse → chunk → schema 0.6.0 校验 → JSON 落盘
    → validate 子命令复检。

负面五类（裁决 D3）：
1. 契约不一致插件 → parser_contract_mismatch / rc=1 / 不写盘
2. 0.5.0 schema 拒新类型（守卫分支）
3. 0.6.0 扩展类型缺 family → schema 拒
4. 未加载插件时 .myx auto 发现失败（unsupported_type）
5. 声明 pattern 非法（大写）→ plugin_register_failed
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.schema import validate as validate_udm

ROOT = Path(__file__).resolve().parent.parent

_MYX_SAMPLE = """# 标题一

正文段落，说明 .myx 的行式语义。

- 列表项甲
- 列表项乙

# 标题二

结尾段落。
"""

_PLUGIN = '''"""批次 20 Phase D 测试插件（tests 专用，永不内置/进 AUTO 映射）。"""
from __future__ import annotations

from pathlib import Path

from app.models import Document, Element, WarningRecord
from app.parser_registry import register
from app.parsers.base import Parser, ParserError, make_document_id

_EXTENSIONS = (".myx",)


@register
class MyxParser(Parser):
    name = "myx_test"
    version = "test/1.0"
    supported_extensions = _EXTENSIONS
    priority = 10
    source_types = ("myx",)
    locator_family = "line_address"

    def parse(self, path, source_hash):
        p = Path(path)
        if not p.is_file():
            raise ParserError(
                code="file_not_found",
                message=f"输入文件不存在: {p}",
                details={"path": str(p)},
            )
        if p.suffix.lower() not in _EXTENSIONS:
            raise ParserError(
                code="unsupported_type",
                message=f"仅支持 .myx，得到 {p.suffix or '(无)'}",
                details={"suffix": p.suffix},
            )
        document_id = make_document_id(source_hash)
        try:
            text = p.read_text(encoding="utf-8")
        except OSError as e:
            raise ParserError(
                code="myx_read_failed",
                message=f"读取 .myx 失败: {e}",
                details={"exception_type": type(e).__name__},
            ) from e

        elements: list[Element] = []
        for i, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if not s:
                continue
            if s.startswith("# "):
                etype, content = "heading", s[2:].strip()
            elif s.startswith("- "):
                etype, content = "list_item", s[2:].strip()
            else:
                etype, content = "paragraph", s
            if not content:
                continue
            elements.append(
                Element(
                    element_id=f"{document_id}::e{i:04d}",
                    type=etype,
                    content=content,
                    source_locator={"family": "line_address", "line": i},
                )
            )

        warnings = (
            []
            if elements
            else [
                WarningRecord(
                    code="myx_no_content",
                    reason=".myx 文件未提取到任何 element（空文件）",
                )
            ]
        )
        return Document(
            document_id=document_id,
            source_path=str(p),
            source_type="myx",
            source_hash=source_hash,
            parser_name=self.name,
            parser_version=self.version,
            elements=elements,
            chunks=[],
            relations=[],
            warnings=warnings,
            errors=[],
            metadata={"myx": True},
        )


__all__ = ["MyxParser"]
'''

_LIAR_PLUGIN = _PLUGIN.replace(
    'name = "myx_test"', 'name = "myx_liar"'
).replace(
    'source_type="myx",', 'source_type="html",  # 声明 myx，产出 html（契约不一致）'
)

_BAD_PATTERN_PLUGIN = _PLUGIN.replace(
    'name = "myx_test"', 'name = "myx_badpat"'
).replace(
    'source_types = ("myx",)', 'source_types = ("MyX",)  # 大写：pattern 非法'
)


def _write(tmp_path: Path, name: str, source: str, sample: str = _MYX_SAMPLE):
    (tmp_path / f"{name}.py").write_text(source, encoding="utf-8")
    src = tmp_path / "doc.myx"
    src.write_text(sample, encoding="utf-8")
    return src


def _cli(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(tmp_path) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "app.cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=ROOT,
        env=env,
        timeout=120,
    )


# ---------- 正向全链（subprocess，真实 CLI） ----------

def test_full_chain_plugin_to_json_060(tmp_path: Path):
    src = _write(tmp_path, "myx_plugin_a", _PLUGIN)
    out = tmp_path / "out.json"
    r = _cli(
        tmp_path, "parse", str(src), "-o", str(out),
        "--plugin", "myx_plugin_a", "--parser", "auto",
    )
    assert r.returncode == 0, r.stderr
    assert out.is_file()

    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["schema_version"] == "0.6.0"
    assert d["source_type"] == "myx"
    assert d["parser_name"] == "myx_test"
    # 扩展名发现选中插件（唯一声明 .myx 的 parser）
    types = [e["type"] for e in d["elements"]]
    assert types.count("heading") == 2
    assert types.count("list_item") == 2
    for e in d["elements"]:
        assert e["source_locator"]["family"] == "line_address"
        assert e["source_locator"]["line"] >= 1
    assert d["chunks"], "chunker 应产出 chunk"
    for c in d["chunks"]:
        assert c["source_element_ids"]
    validate_udm(d)


def test_cli_validate_subcommand_on_plugin_output(tmp_path: Path):
    src = _write(tmp_path, "myx_plugin_b", _PLUGIN)
    out = tmp_path / "out.json"
    r = _cli(
        tmp_path, "parse", str(src), "-o", str(out),
        "--plugin", "myx_plugin_b", "--parser", "auto",
    )
    assert r.returncode == 0, r.stderr
    r2 = _cli(tmp_path, "validate", str(out))
    assert r2.returncode == 0, r2.stderr
    assert "[OK]" in r2.stdout


def test_list_parsers_shows_plugin(tmp_path: Path):
    _write(tmp_path, "myx_plugin_c", _PLUGIN)
    r = _cli(tmp_path, "list-parsers", "--plugin", "myx_plugin_c")
    assert r.returncode == 0, r.stderr
    assert "myx_test" in r.stdout
    assert ".myx" in r.stdout


# ---------- 负面 1：契约不一致 → parser_contract_mismatch ----------

def test_liar_plugin_contract_mismatch_rc1_no_artifact(tmp_path: Path):
    src = _write(tmp_path, "myx_liar_mod", _LIAR_PLUGIN)
    out = tmp_path / "out.json"
    r = _cli(
        tmp_path, "parse", str(src), "-o", str(out),
        "--plugin", "myx_liar_mod", "--parser", "auto",
    )
    assert r.returncode == 1
    assert not out.exists(), "契约违规产物不得落盘"
    payload = json.loads(r.stderr)
    assert payload["errors"][0]["code"] == "parser_contract_mismatch"
    details = payload["errors"][0]["details"]
    assert details["actual_source_type"] == "html"
    assert details["declared_source_types"] == ["myx"]


# ---------- 负面 2/3：schema 层拒绝（守卫与 family） ----------

def _udm(source_type: str, version: str, locator: dict) -> dict:
    return {
        "schema_version": version,
        "document_id": "doc1",
        "source_path": "samples/x.myx",
        "source_type": source_type,
        "source_hash": "a" * 64,
        "parser_name": "myx_test",
        "parser_version": "test/1.0",
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "parent_id": None,
                "source_locator": locator,
                "content": "x",
                "resource_path": None,
                "confidence": 1.0,
                "metadata": {},
            }
        ],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def test_050_schema_rejects_myx():
    with pytest.raises(Exception):
        validate_udm(
            _udm("myx", "0.5.0", {"family": "line_address", "line": 1})
        )


def test_060_missing_family_rejected():
    with pytest.raises(Exception):
        validate_udm(_udm("myx", "0.6.0", {"line": 1}))


# ---------- 负面 4：未加载插件 → .myx auto 发现失败 ----------

def test_auto_discovery_fails_without_plugin(tmp_path: Path):
    src = _write(tmp_path, "unused_mod", _PLUGIN)  # 写入但不 --plugin 加载
    out = tmp_path / "out.json"
    r = _cli(tmp_path, "parse", str(src), "-o", str(out), "--parser", "auto")
    assert r.returncode == 1
    assert not out.exists()
    payload = json.loads(r.stderr)
    assert payload["errors"][0]["code"] == "unsupported_type"
    assert ".myx" in payload["errors"][0]["message"]


# ---------- 负面 5：声明 pattern 非法 → plugin_register_failed ----------

def test_bad_pattern_declaration_rejected_at_load(tmp_path: Path):
    src = _write(tmp_path, "myx_badpat_mod", _BAD_PATTERN_PLUGIN)
    out = tmp_path / "out.json"
    r = _cli(
        tmp_path, "parse", str(src), "-o", str(out),
        "--plugin", "myx_badpat_mod", "--parser", "auto",
    )
    assert r.returncode == 1
    assert not out.exists()
    payload = json.loads(r.stderr)
    assert payload["errors"][0]["code"] == "plugin_register_failed"
    assert "MyX" in payload["errors"][0]["message"]
