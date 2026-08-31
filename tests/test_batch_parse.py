"""批次 16 测试：批量解析与并行化（Stage 8，Option A 裁决）。

覆盖裁决 3.1 六项：合成 10 文档批量 / 顺序并行一致性 / 错误隔离 /
stem 冲突 / 小批次顺序路径 / summary 格式；另含 CLI 冒烟与
evaluation --workers 并行一致性（per_doc wall_time 与时间戳除外相同）。
"""

from __future__ import annotations

import json
from pathlib import Path

from app.batch import (
    batch_parse_files,
    default_workers,
    effective_parser_for,
)
from app.cli import main as app_main
from evaluation.manifest import load_manifest
from evaluation.runner import run_evaluation

SUMMARY_KEYS = {
    "total",
    "success",
    "failed",
    "workers",
    "wall_time_seconds",
    "errors",
}


def _write_md(directory: Path, name: str, marker: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    p = directory / name
    p.write_text(f"# 标题 {name}\n\n正文 {marker} 标记内容。\n", encoding="utf-8")
    return p


# ---------- 1. 合成 10 文档批量（并行路径） ----------

def test_batch_parse_ten_docs_parallel(tmp_path: Path):
    docs = tmp_path / "docs"
    files = [_write_md(docs, f"doc{i:02d}.md", f"MARK{i}") for i in range(10)]
    out = tmp_path / "out"
    summary = batch_parse_files(files, out, workers=3)

    assert summary["total"] == 10
    assert summary["success"] == 10
    assert summary["failed"] == 0
    assert summary["workers"] == 3  # 10 >= 3 → 并行路径
    assert (out / "summary.json").is_file()
    for i in range(10):
        data = json.loads((out / f"doc{i:02d}.json").read_text(encoding="utf-8"))
        assert data["document_id"].startswith("doc-")
        assert data["errors"] == []


# ---------- 2. 顺序 vs 并行结果一致性 ----------

def test_sequential_vs_parallel_identical(tmp_path: Path):
    docs = tmp_path / "docs"
    files = [_write_md(docs, f"same{i}.md", f"MARK{i}") for i in range(6)]
    seq_out = tmp_path / "seq"
    par_out = tmp_path / "par"

    s1 = batch_parse_files(files, seq_out, workers=1)
    s2 = batch_parse_files(files, par_out, workers=3)

    for f in files:
        a = (seq_out / (f.stem + ".json")).read_bytes()
        b = (par_out / (f.stem + ".json")).read_bytes()
        assert a == b, f"顺序/并行输出不一致: {f.name}"
    assert (s1["success"], s1["failed"]) == (s2["success"], s2["failed"])


# ---------- 3. 错误隔离（单文档失败不中断批） ----------

def test_error_isolation_single_failure_continues(tmp_path: Path):
    docs = tmp_path / "docs"
    good1 = _write_md(docs, "good1.md", "OK1")
    missing = docs / "missing.md"
    good2 = _write_md(docs, "good2.md", "OK2")
    good3 = _write_md(docs, "good3.md", "OK3")
    out = tmp_path / "out"

    summary = batch_parse_files([good1, missing, good2, good3], out, workers=2)

    assert summary["total"] == 4
    assert summary["success"] == 3
    assert summary["failed"] == 1
    assert summary["errors"][0]["code"] == "file_not_found"
    assert summary["errors"][0]["file"] == str(missing)
    assert (out / "good1.json").is_file()
    assert (out / "good2.json").is_file()
    assert (out / "good3.json").is_file()


# ---------- 4. stem 冲突：后者记错误不覆盖 ----------

def test_stem_collision_records_error_no_overwrite(tmp_path: Path):
    f1 = _write_md(tmp_path / "a", "one.md", "FIRST")
    f2 = _write_md(tmp_path / "b", "one.md", "SECOND")
    out = tmp_path / "out"

    summary = batch_parse_files([f1, f2], out, workers=1)

    assert summary["total"] == 2
    assert summary["success"] == 1
    assert summary["failed"] == 1
    assert summary["errors"][0]["code"] == "stem_collision"
    data = json.loads((out / "one.json").read_text(encoding="utf-8"))
    assert "FIRST" in json.dumps(data, ensure_ascii=False)


# ---------- 5. 小批次（<3 文档）走顺序路径 ----------

def test_small_batch_takes_sequential_path(tmp_path: Path):
    docs = tmp_path / "docs"
    files = [_write_md(docs, f"small{i}.md", f"M{i}") for i in range(2)]
    summary = batch_parse_files(files, tmp_path / "out", workers=8)

    assert summary["workers"] == 1  # <3 文档：免 spawn 开销，顺序执行
    assert summary["success"] == 2


# ---------- 6. summary 格式 ----------

def test_summary_format(tmp_path: Path):
    docs = tmp_path / "docs"
    good = _write_md(docs, "fmt.md", "FMT")
    missing = docs / "nope.md"
    summary = batch_parse_files([good, missing], tmp_path / "out", workers=1)

    assert set(summary.keys()) == SUMMARY_KEYS
    assert summary["total"] == 2
    assert summary["success"] + summary["failed"] == summary["total"]
    assert summary["wall_time_seconds"] > 0
    assert set(summary["errors"][0].keys()) == {"file", "code", "message"}


# ---------- worker 默认值与 md 路由 ----------

def test_default_workers_bounded():
    assert 1 <= default_workers() <= 8


def test_effective_parser_routes_md_to_markdown(tmp_path: Path):
    assert effective_parser_for("fallback", "x.md") == "markdown"
    assert effective_parser_for("fallback", tmp_path / "x.pdf") == "fallback"
    assert effective_parser_for("fallback", tmp_path / "x.docx") == "fallback"
    assert effective_parser_for("markdown", "x.md") == "markdown"


# ---------- CLI 冒烟 ----------

def test_cli_batch_parse_directory_rc0(tmp_path: Path):
    docs = tmp_path / "docs"
    for i in range(3):
        _write_md(docs, f"cli{i}.md", f"CLI{i}")
    out = tmp_path / "cliout"
    rc = app_main(["batch-parse", str(docs), "-o", str(out)])
    assert rc == 0
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["success"] == 3


def test_cli_batch_parse_missing_single_file_rc2(tmp_path: Path):
    rc = app_main(
        ["batch-parse", str(tmp_path / "no-such.md"), "-o", str(tmp_path / "o2")]
    )
    assert rc == 2


def test_cli_batch_parse_broken_file_rc1(tmp_path: Path):
    docs = tmp_path / "docs"
    _write_md(docs, "fine.md", "FINE")
    bad = docs / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 not a real pdf")
    rc = app_main(["batch-parse", str(docs), "-o", str(tmp_path / "o3")])
    assert rc == 1
    summary = json.loads(
        (tmp_path / "o3" / "summary.json").read_text(encoding="utf-8")
    )
    assert summary["success"] == 1 and summary["failed"] == 1


# ---------- evaluation 并行一致性 ----------

def test_evaluation_parallel_report_consistency(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='test'\n", encoding="utf-8"
    )
    docs = tmp_path / "docs"
    entries = []
    for i in range(4):
        rel = _write_md(docs, f"ev{i}.md", f"EVAL{i}")
        entries.append(
            {
                "doc_id": f"EV-{i}",
                "path": rel.relative_to(tmp_path).as_posix(),
                "source_type": "markdown",
            }
        )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_version": "1.1",
                "devset_status": "incomplete",
                "documents": entries,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    manifest = load_manifest(manifest_path, project_root=tmp_path)

    r1 = run_evaluation(
        manifest, tmp_path / "r-seq.json", parser_name="markdown", workers=1
    )
    r2 = run_evaluation(
        manifest, tmp_path / "r-par.json", parser_name="markdown", workers=2
    )

    assert [d["doc_id"] for d in r1["per_doc"]] == [
        d["doc_id"] for d in r2["per_doc"]
    ]
    for d1, d2 in zip(r1["per_doc"], r2["per_doc"]):
        assert d1["metrics"] == d2["metrics"]
        assert d1["parser_used"] == d2["parser_used"]
    assert r1["summary"] == r2["summary"]
    assert r1["devset"] == r2["devset"]
