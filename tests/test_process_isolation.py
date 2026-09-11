"""原生崩溃进程隔离测试（Stage 10 批次 2 首项）。

三层覆盖：
1. run_in_isolated_process 单元契约：ok / exc / crashed（os._exit 硬崩
   替身，exitcode≠0）/ exitcode==0 无结果（EOF 防御路径）
2. batch 接线：.pdf 隔离成功输出与进程内逐字节一致；.md 不进隔离；
   crashed 清理半成品 JSON + 结构化错误（无 traceback）；子进程 Python
   异常结构化回传；真实硬崩插件 parser 端到端（含孙进程插件重放）；
   Pool worker（daemonic）内嵌套隔离的并行批量
3. evaluation 接线：.pdf crashed/exc → doc 级结构化错误（无 traceback
   键）；非 .pdf 直连 _process_one

子进程目标函数必须模块级（pickle 按模块名引用）；父 sys.path 经任务
首段 pickle 传入孙进程，测试模块函数可解析，无样本依赖。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.batch import _parse_core, batch_parse_files, parse_one_file
from app.process_isolation import CRASH_ERROR_CODE, run_in_isolated_process


# ---------- 子进程目标（模块级：pickle 按名引用） ----------

def _child_ok(x: int) -> int:
    return x * 2


def _child_raise(msg: str) -> None:
    raise ValueError(msg)


def _child_hard_crash(code: int) -> None:
    os._exit(code)


def _child_exit0_silent() -> None:
    os._exit(0)


# ---------- 1. 单元契约 ----------

def test_ok_roundtrip():
    status, payload = run_in_isolated_process(_child_ok, (21,))
    assert status == "ok"
    assert payload == 42


def test_exception_structured():
    status, payload = run_in_isolated_process(_child_raise, ("boom-marker",))
    assert status == "exc"
    assert payload["type"] == "ValueError"
    assert "boom-marker" in payload["message"]
    assert "ValueError" in payload["traceback"]


def test_hard_crash_isolated():
    status, payload = run_in_isolated_process(_child_hard_crash, (3,))
    assert status == "crashed"
    assert payload["code"] == CRASH_ERROR_CODE
    assert payload["exitcode"] == 3
    assert "exitcode=3" in payload["message"]


def test_exit0_no_result_eof_defensive():
    status, payload = run_in_isolated_process(_child_exit0_silent, ())
    assert status == "crashed"
    assert payload["code"] == CRASH_ERROR_CODE
    assert payload["exitcode"] == 0
    assert "EOF" in payload["message"]


# ---------- 合成 PDF 夹具（手写最小单页文本 PDF，无第三方生成依赖） ----------

def _make_text_pdf(path: Path) -> None:
    content = b"BT /F1 12 Tf 72 770 Td (Isolated hello) Tj ET"
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    out = b"%PDF-1.4\n"
    offsets: dict[int, int] = {}
    for i in sorted(objs):
        offsets[i] = len(out)
        out += f"{i} 0 obj\n".encode() + objs[i] + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n0000000000 65535 f \n"
    for i in sorted(objs):
        out += f"{offsets[i]:010d} 00000 n \n".encode()
    out += (b"trailer\n<< /Size " + str(len(objs) + 1).encode()
            + b" /Root 1 0 R >>\nstartxref\n" + str(xref_pos).encode()
            + b"\n%%EOF")
    path.write_bytes(out)


def _write_md(directory: Path, name: str, marker: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    p = directory / name
    p.write_text(f"# 标题 {name}\n\n正文 {marker} 标记内容。\n", encoding="utf-8")
    return p


# ---------- 2. batch 接线 ----------

def test_pdf_isolated_success_byte_identical(tmp_path: Path):
    pytest.importorskip("pdfplumber")
    pdf = tmp_path / "iso.pdf"
    _make_text_pdf(pdf)
    out = tmp_path / "out"

    r = parse_one_file((str(pdf), str(out), "fallback", 800))
    assert r["success"] is True, r
    assert r["error_code"] is None
    first = (out / "iso.json").read_bytes()

    # 语义不变证明：同输入进程内直跑解析核心，输出 JSON 逐字节一致
    r2 = _parse_core(str(pdf), str(out), "fallback", 800)
    assert r2["success"] is True
    second = (out / "iso.json").read_bytes()
    assert first == second

    data = json.loads(first)
    assert data["errors"] == []
    assert any(
        e.get("content") and "Isolated hello" in e["content"]
        for e in data["elements"]
    )


def test_md_not_isolated(monkeypatch, tmp_path: Path):
    calls: list[tuple] = []

    def fake_spawn(fn, args):
        calls.append((fn, args))
        return ("ok", {})

    monkeypatch.setattr("app.batch.run_in_isolated_process", fake_spawn)
    md = _write_md(tmp_path / "docs", "plain.md", "MK")
    r = parse_one_file((str(md), str(tmp_path / "out"), "markdown", 800))
    assert r["success"] is True
    assert calls == []


def test_crashed_cleans_partial_json(monkeypatch, tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    pdf = tmp_path / "c.pdf"
    pdf.write_bytes(b"%PDF-1.4")  # 隔离入口被替换，内容不会真被解析
    partial = out / "c.json"
    partial.write_text('{"half": true}', encoding="utf-8")
    monkeypatch.setattr(
        "app.batch.run_in_isolated_process",
        lambda fn, args: (
            "crashed",
            {
                "code": CRASH_ERROR_CODE,
                "exitcode": 3,
                "message": "解析子进程异常终止（exitcode=3，疑似 pdfplumber 底层 C 库原生崩溃），已隔离，批处理继续",
            },
        ),
    )
    r = parse_one_file((str(pdf), str(out), "fallback", 800))
    assert r["success"] is False
    assert r["error_code"] == CRASH_ERROR_CODE
    assert "exitcode=3" in r["error_message"]
    assert r["traceback"] is None  # 原生崩溃无 traceback
    assert not partial.exists()  # 半成品 JSON 被清理


def test_child_python_exception_structured(monkeypatch, tmp_path: Path):
    pdf = tmp_path / "e.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(
        "app.batch.run_in_isolated_process",
        lambda fn, args: (
            "exc",
            {
                "type": "ValueError",
                "message": "bad thing",
                "traceback": "Traceback (most recent call last): ...",
            },
        ),
    )
    r = parse_one_file((str(pdf), str(tmp_path / "out"), "fallback", 800))
    assert r["success"] is False
    assert r["error_code"] == "ValueError"
    assert r["error_message"] == "bad thing"
    assert "Traceback" in r["traceback"]


_CRASHY_PLUGIN = '''
from app.parser_registry import register
from app.parsers.base import Parser


@register
class CrashyParser(Parser):
    name = "crashy_test"
    version = "test/1.0"
    supported_extensions = (".pdf",)
    priority = 30
    source_types = ("pdf",)
    locator_family = "page_geometry"

    def parse(self, path, source_hash):
        import os
        os._exit(1)
'''


def test_real_crash_plugin_parser_end_to_end(monkeypatch, tmp_path: Path):
    """真实硬崩经完整链路：孙进程重放插件 → parser 内 os._exit(1) →
    父侧按退出码捕获 → 结构化 parser_process_crashed，无 traceback。"""
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    (plugins / "crashy_parser.py").write_text(_CRASHY_PLUGIN, encoding="utf-8")
    monkeypatch.syspath_prepend(str(plugins))
    monkeypatch.setattr(
        "app.batch._WORKER_PLUGIN_MODULES", ("crashy_parser",)
    )
    pdf = tmp_path / "real.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    r = parse_one_file((str(pdf), str(tmp_path / "out"), "crashy_test", 800))

    assert r["success"] is False
    assert r["error_code"] == CRASH_ERROR_CODE
    assert "exitcode=1" in r["error_message"]
    assert r["traceback"] is None


def test_parallel_pool_pdf_batch_nested_isolation(tmp_path: Path):
    """Pool worker 是 daemonic 进程：证明 subprocess 隔离在 worker 内
    可用（mp.Process 方案在此路径会 AssertionError），且批量继续。"""
    pytest.importorskip("pdfplumber")
    docs = tmp_path / "docs"
    files = [_write_md(docs, f"m{i}.md", f"MK{i}") for i in range(6)]
    for i in range(3):
        p = docs / f"p{i}.pdf"
        _make_text_pdf(p)
        files.append(p)
    out = tmp_path / "out"
    summary = batch_parse_files(files, out, workers=3)

    assert summary["total"] == 9
    assert summary["success"] == 9
    assert summary["failed"] == 0
    for i in range(3):
        data = json.loads((out / f"p{i}.json").read_text(encoding="utf-8"))
        assert data["errors"] == []


# ---------- 3. evaluation 接线 ----------

class _StubDoc:
    def __init__(self, path: Path):
        self.resolved_path = Path(path)


def test_eval_pdf_crash_structured(monkeypatch, tmp_path: Path):
    pdf = tmp_path / "d.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(
        "evaluation.runner.run_in_isolated_process",
        lambda fn, args: (
            "crashed",
            {
                "code": CRASH_ERROR_CODE,
                "exitcode": 2,
                "message": "解析子进程异常终止（exitcode=2），已隔离，批处理继续",
            },
        ),
    )
    from evaluation.runner import _process_one_task

    doc, err, secs, pv, img = _process_one_task(
        (_StubDoc(pdf), tmp_path, "fallback", 800)
    )
    assert doc is None
    assert err["code"] == CRASH_ERROR_CODE
    assert "traceback" not in err  # eval error dict 与既有同形，无新键
    assert pv is None
    assert img == Path()
    assert secs >= 0.0


def test_eval_pdf_exc_structured(monkeypatch, tmp_path: Path):
    pdf = tmp_path / "e.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(
        "evaluation.runner.run_in_isolated_process",
        lambda fn, args: (
            "exc",
            {"type": "ValueError", "message": "boom",
             "traceback": "Traceback ..."},
        ),
    )
    from evaluation.runner import _process_one_task

    doc, err, secs, pv, img = _process_one_task(
        (_StubDoc(pdf), tmp_path, "fallback", 800)
    )
    assert doc is None
    assert err["code"] == "ValueError"
    assert err["message"] == "boom"


def test_eval_non_pdf_direct(monkeypatch, tmp_path: Path):
    md = _write_md(tmp_path, "direct.md", "MK")
    seen: list[Path] = []

    def fake_process_one(doc, output_root, parser_name, max_chars):
        seen.append(doc.resolved_path)
        return ({"document_id": "doc-x"}, None, 0.5, "1.0", Path())

    monkeypatch.setattr("evaluation.runner._process_one", fake_process_one)

    def no_spawn(fn, args):
        raise AssertionError("非 .pdf 文档不应进入隔离路径")

    monkeypatch.setattr("evaluation.runner.run_in_isolated_process", no_spawn)

    from evaluation.runner import _process_one_task

    result = _process_one_task((_StubDoc(md), tmp_path, "markdown", 800))
    assert result[0] == {"document_id": "doc-x"}
    assert seen == [md]
