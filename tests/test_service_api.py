"""Stage 11 批次 1 测试：本地 HTTP API 服务（W1 裁决边界逐条验证）。

覆盖（对应 W1 裁定原文）：
- API 与 CLI 的成功结果结构等价（合成 .md 夹具，auto 路由，除
  source_path 与 metadata.image_output_dir 外逐键相等）；
- 各已知错误码：unknown_parser 400 / unsupported_type 400（发现层）、
  no_extracted_elements 422（业务失败）、upload_too_large 413、
  invalid_request 422（缺 file 字段）、服务端缺陷码 500（无 traceback、
  临时路径被净化）；
- 上传上限：流式实际计量超限 413；恰好等于上限放行（边界）；
- 临时文件清理：成功 / 业务失败 / 超限 / 缺陷码全路径 temp_dir 为空；
- 响应不泄露服务器临时路径（成功 source_path 用净化名；错误
  message/details 中的临时路径被替换）；
- 上传文件名净化：路径穿越 / 反斜杠 / 空值 / 超长封顶；
- 插件预加载：create_app(plugins=[...]) 一次性加载 + 显式/auto 两条
  解析路径 + 加载失败 fail-fast（PluginLoadError）；
- 前端基本流程：GET /（含无鉴权警示）、/docs、/openapi.json、
  /api/v1/health、/api/v1/parsers 均不被静态根遮蔽；
- CLI 守卫：非 loopback --host 无 --unsafe-expose → rc 2；
  --max-upload-mb 非正 → rc 2（不启动 uvicorn）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.cli import main as app_main
from app.models import ErrorRecord
from app.plugin_loader import PluginLoadError
from app.service import create_app, sanitize_filename

# ---------- 合成夹具与插件模板 ----------

_MD_CONTENT = (
    "# 结构等价标题\n\n"
    "第一段正文，用于 API 与 CLI 的结构等价验证。\n\n"
    "- [x] 已完成任务\n- [ ] 未完成任务\n\n"
    "## 小节\n\n结尾段落。\n"
)

_LONG_MD_CONTENT = "# 长文\n\n" + "很长的段落内容。" * 200 + "\n"

_PLUGIN_MYX = r'''
from pathlib import Path

from app.models import Document, Element, WarningRecord
from app.parser_registry import register
from app.parsers.base import Parser, make_document_id


@register
class MyxParser(Parser):
    name = "myx_test"
    version = "test/1.0"
    supported_extensions = (".myx",)
    priority = 1
    source_types = ("text",)
    locator_family = "line_address"

    def parse(self, path, source_hash):
        p = Path(path)
        text = p.read_text(encoding="utf-8")
        document_id = make_document_id(source_hash)
        elements = []
        for i, seg in enumerate(s for s in text.split("\n\n") if s.strip()):
            elements.append(
                Element(
                    element_id=f"{document_id}::e{i:04d}",
                    type="paragraph",
                    content=seg.strip(),
                    parent_id=None,
                    source_locator={"family": "line_address", "line": 1},
                    confidence=0.95,
                    metadata={},
                )
            )
        warnings = [] if elements else [
            WarningRecord(code="myx_no_content", reason="空文档")
        ]
        return Document(
            document_id=document_id,
            source_path=str(p),
            source_type="text",
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
'''


@pytest.fixture
def temp_scan_dir(tmp_path: Path) -> Path:
    """注入 service 的临时目录：请求结束后必须为空（W1 清理断言）。"""
    d = tmp_path / "srv-tmp"
    d.mkdir()
    return d


@pytest.fixture
def client(temp_scan_dir: Path) -> TestClient:
    app = create_app(temp_dir=temp_scan_dir)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def plugin_env(tmp_path: Path, monkeypatch):
    """sys.path 注入 + 注册表三表副本隔离（_registry/_capabilities/
    _source_type_families）+ 首载备忘重置 + 模块 sys.modules 清理。"""
    monkeypatch.syspath_prepend(str(tmp_path))
    import app.parser_registry as pr
    from app import plugin_loader as pl

    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_capabilities", dict(pr._capabilities))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    monkeypatch.setattr(pl, "_FIRST_LOAD", {})
    yield tmp_path
    for key, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if f and str(tmp_path) in str(f):
            del sys.modules[key]


def _write_plugin(directory: Path, mod_name: str, source: str) -> str:
    (directory / f"{mod_name}.py").write_text(source, encoding="utf-8")
    return mod_name


def _post(
    client: TestClient,
    filename: str,
    content: bytes,
    parser: str = "auto",
    max_chars: int = 800,
):
    return client.post(
        "/api/v1/parse",
        files={"file": (filename, content)},
        data={"parser": parser, "max_chars": str(max_chars)},
    )


def _assert_no_temp_leak(resp, temp_dir: Path) -> None:
    text = resp.text
    assert str(temp_dir) not in text
    assert str(temp_dir).replace("\\", "/") not in text


# ---------- sanitize_filename 单元 ----------

def test_sanitize_filename_traversal_and_backslash():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("a\\b\\c.txt") == "c.txt"


def test_sanitize_filename_empty_and_none():
    assert sanitize_filename(None) == "upload"
    assert sanitize_filename("") == "upload"
    assert sanitize_filename("...") == "upload"  # strip 后空 → 兜底


def test_sanitize_filename_control_chars_removed():
    assert sanitize_filename("bad\x00name.txt") == "badname.txt"


def test_sanitize_filename_length_cap_keeps_suffix():
    long = "x" * 150 + ".txt"
    out = sanitize_filename(long)
    assert len(out) == 100
    assert out.endswith(".txt")


# ---------- 前端与遮蔽（W1：静态根不得遮蔽 /api/*、/docs、/openapi.json） ----------

def test_index_served_with_warning_and_form(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "无鉴权" in resp.text  # W1：页面须含警示
    assert "parse-form" in resp.text
    assert "kvfs-doc-parser" in resp.text


def test_docs_and_openapi_not_shadowed(client: TestClient):
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    assert "/api/v1/parse" in spec.json()["paths"]


def test_health_and_parsers_not_shadowed(client: TestClient):
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert body["parser_count"] >= 1

    parsers = client.get("/api/v1/parsers")
    assert parsers.status_code == 200
    rows = parsers.json()
    names = {r["name"] for r in rows}
    assert "fallback" in names
    assert "markdown_enhanced" in names


# ---------- 成功路径：API 与 CLI 结构等价（W1 核心断言） ----------

def test_parse_success_equivalent_to_cli(tmp_path: Path, client: TestClient, temp_scan_dir: Path):
    md = tmp_path / "equiv.md"
    md.write_text(_MD_CONTENT, encoding="utf-8")
    out = tmp_path / "equiv.json"
    rc = app_main(["parse", str(md), "-o", str(out), "--parser", "auto"])
    assert rc == 0
    cli_doc = json.loads(out.read_text(encoding="utf-8"))

    resp = _post(client, "equiv.md", md.read_bytes(), parser="auto")
    assert resp.status_code == 200
    api_doc = resp.json()

    # 同构键集（与 CLI parse -o 输出完全一致，另无多余键）
    assert set(api_doc) == set(cli_doc)
    # 已知差异仅两处：source_path（净化名）；CLI 侧可能有 image_output_dir
    for key in (
        "schema_version", "document_id", "source_type", "source_hash",
        "parser_name", "parser_version", "elements", "chunks", "relations",
        "warnings", "errors",
    ):
        assert api_doc[key] == cli_doc[key], key
    cli_meta = {k: v for k, v in cli_doc["metadata"].items() if k != "image_output_dir"}
    assert api_doc["metadata"] == cli_meta
    assert api_doc["source_path"] == "equiv.md"  # 净化名，非临时路径
    _assert_no_temp_leak(resp, temp_scan_dir)
    assert list(temp_scan_dir.iterdir()) == []  # 成功路径清理


def test_parse_max_chars_form_honored(tmp_path: Path, client: TestClient):
    md = tmp_path / "long.md"
    md.write_text(_LONG_MD_CONTENT, encoding="utf-8")
    out = tmp_path / "long.json"
    rc = app_main(["parse", str(md), "-o", str(out), "--parser", "auto", "--max-chars", "100"])
    assert rc == 0
    cli_doc = json.loads(out.read_text(encoding="utf-8"))

    resp = _post(client, "long.md", md.read_bytes(), max_chars=100)
    assert resp.status_code == 200
    api_doc = resp.json()
    assert api_doc["chunks"] == cli_doc["chunks"]
    assert len(api_doc["chunks"]) > 1  # 小上限确实切出多块


def test_parse_sanitized_upload_name_as_source_path(client: TestClient):
    resp = _post(client, "../../evil/../../travel.md", _MD_CONTENT.encode("utf-8"))
    assert resp.status_code == 200
    assert resp.json()["source_path"] == "travel.md"
    assert ".." not in resp.json()["source_path"]


def test_parse_exact_upload_limit_passes(tmp_path: Path):
    app = create_app(max_upload_bytes=8, temp_dir=tmp_path)
    with TestClient(app) as c:
        resp = _post(c, "b.txt", b"12345678")  # 恰好 8 字节 = 上限
        assert resp.status_code == 200
        assert resp.json()["source_type"] == "text"


# ---------- 错误码与 HTTP 映射（W4 表的行为验证） ----------

def test_unknown_parser_400(client: TestClient, temp_scan_dir: Path):
    resp = _post(client, "a.md", _MD_CONTENT.encode("utf-8"), parser="definitely_not")
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "unknown_parser"
    assert "fallback" in err["message"]  # 提示已知名单
    assert list(temp_scan_dir.iterdir()) == []  # 校验前已落盘 → 仍须清理


def test_unsupported_type_discovery_400(client: TestClient, temp_scan_dir: Path):
    resp = _post(client, "x.zzz9", b"data")
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "unsupported_type"
    assert ".zzz9" in err["message"]
    _assert_no_temp_leak(resp, temp_scan_dir)
    assert list(temp_scan_dir.iterdir()) == []


def test_no_extracted_elements_422(client: TestClient, temp_scan_dir: Path):
    resp = _post(client, "empty.md", b"")  # 空文件 → 0 element 业务失败
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["code"] == "no_extracted_elements"
    _assert_no_temp_leak(resp, temp_scan_dir)
    assert list(temp_scan_dir.iterdir()) == []  # 失败路径清理


def test_upload_too_large_413_and_cleanup(tmp_path: Path):
    temp_dir = tmp_path / "srv-tmp"
    temp_dir.mkdir()
    app = create_app(max_upload_bytes=8, temp_dir=temp_dir)
    with TestClient(app) as c:
        resp = _post(c, "big.md", b"x" * 20)
        assert resp.status_code == 413
        err = resp.json()["error"]
        assert err["code"] == "upload_too_large"
        assert err["details"]["limit_bytes"] == 8
        _assert_no_temp_leak(resp, temp_dir)
        assert list(temp_dir.iterdir()) == []  # 超限路径清理（流式中断后）


def test_missing_file_field_invalid_request_422(client: TestClient):
    resp = client.post("/api/v1/parse", data={"parser": "fallback"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_request"


def test_server_defect_500_scrubbed_no_traceback(
    client: TestClient, temp_scan_dir: Path, monkeypatch
):
    """服务端缺陷码 → 500；message/details 中临时路径被净化；无 traceback。"""
    import app.service as service_mod

    captured: dict[str, str] = {}

    def fake_process_single(input_path, output_path, *, parser_name, max_chars, write_json):
        captured["path"] = str(Path(input_path))
        return None, [
            ErrorRecord(
                code="unexpected_parser_error",
                message=f"解析器在 {captured['path']} 崩溃",
                details={"path": captured["path"], "parser_name": parser_name},
            )
        ]

    monkeypatch.setattr(service_mod, "process_single", fake_process_single)
    resp = _post(client, "boom.md", _MD_CONTENT.encode("utf-8"))
    assert resp.status_code == 500
    err = resp.json()["error"]
    assert err["code"] == "unexpected_parser_error"
    assert err["details"]["path"] == "boom.md"  # 临时路径 → 净化名
    assert "boom.md" in err["message"]
    assert captured["path"] not in err["message"]
    assert "Traceback" not in resp.text and "traceback" not in resp.text
    assert list(temp_scan_dir.iterdir()) == []  # 缺陷路径清理


# ---------- 插件预加载（W1：与 CLI 同语义的一次性加载） ----------

def test_create_app_plugin_preload_explicit(plugin_env: Path, tmp_path: Path):
    _write_plugin(plugin_env, "myx_mod", _PLUGIN_MYX)
    temp_dir = tmp_path / "t1"
    temp_dir.mkdir()
    app = create_app(plugins=["myx_mod"], temp_dir=temp_dir)
    with TestClient(app) as c:
        resp = _post(
            c, "a.myx", "第一段\n\n第二段 STAGE11\n".encode("utf-8"),
            parser="myx_test",
        )
        assert resp.status_code == 200
        doc = resp.json()
        assert doc["parser_name"] == "myx_test"
        assert doc["metadata"]["myx"] is True
        assert any("STAGE11" in e["content"] for e in doc["elements"])
        assert list(temp_dir.iterdir()) == []


def test_create_app_plugin_preload_auto_route(plugin_env: Path, tmp_path: Path):
    _write_plugin(plugin_env, "myx_mod", _PLUGIN_MYX)
    temp_dir = tmp_path / "t2"
    temp_dir.mkdir()
    app = create_app(plugins=["myx_mod"], temp_dir=temp_dir)
    with TestClient(app) as c:
        resp = _post(c, "b.myx", "auto 路由\n".encode("utf-8"), parser="auto")
        assert resp.status_code == 200
        assert resp.json()["parser_name"] == "myx_test"


def test_create_app_plugin_preload_health_lists_plugin(plugin_env: Path):
    _write_plugin(plugin_env, "myx_mod", _PLUGIN_MYX)
    app = create_app(plugins=["myx_mod"])
    with TestClient(app) as c:
        rows = c.get("/api/v1/parsers").json()
        assert "myx_test" in {r["name"] for r in rows}


def test_create_app_plugin_load_failure_fail_fast(plugin_env: Path):
    with pytest.raises(PluginLoadError):
        create_app(plugins=["definitely_missing_module_zzz9"])


# ---------- CLI serve 守卫（W1：loopback-only 默认） ----------

def test_cli_serve_non_loopback_requires_unsafe_expose(capfd):
    rc = app_main(["serve", "--host", "0.0.0.0"])
    assert rc == 2
    assert "--unsafe-expose" in capfd.readouterr().err


def test_cli_serve_max_upload_mb_positive(capfd):
    rc = app_main(["serve", "--host", "0.0.0.0", "--unsafe-expose", "--max-upload-mb", "0"])
    assert rc == 2
    assert "--max-upload-mb" in capfd.readouterr().err
