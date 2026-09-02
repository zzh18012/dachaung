"""Stage 8 封口评估基准：N 文档批量解析计时（封口标准见 ADOPTION §五十）。

口径：100 文档 <10min（600s，8 核单机，workers=8）；语料为确定性合成
混合格式（40 md / 30 docx / 30 pdf，按 count 等比分配）；计时取
batch-parse 自身 summary.json 的 wall_time_seconds（不含语料生成）。

用法（项目 venv 下运行）：
    .venv/Scripts/python.exe scripts/benchmark_stage8_closure.py \
        [--count 100] [--workers 8] [--keep]

产出（outputs/stage8-closure-bench/，gitignored，--keep 保留供复查）：
- corpus/     合成语料；out/ 每文档 JSON + summary.json
- bench.jsonl 结构化 JSONL 日志（batch_start/file_complete/.../batch_complete）
- bench-report.json 本脚本汇总（含 CPU/worker/耗时/事件计数/判定）

语料合成零第三方依赖（stdlib zipfile + 手写最小 PDF，手法与
tests/test_parsers.py 同源）。退出码：0 = 全成功且 <600s；1 = 失败或
超时；2 = 用法/执行错误。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH_DIR = ROOT / "outputs" / "stage8-closure-bench"
TIME_LIMIT_SECONDS = 600.0

if hasattr(sys.stdout, "reconfigure"):  # Windows 控制台 utf-8
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass


def _write_md(path: Path, index: int) -> None:
    paras = [
        f"第 {j} 段：基准文档 {index} 的正文内容，用于 Stage 8 封口评估的"
        f"批量解析计时语料。"
        for j in range(8)
    ]
    body = f"# 基准标题 {index}\n\n" + "\n\n".join(paras) + "\n"
    path.write_text(body, encoding="utf-8")


def _write_docx(path: Path, index: int) -> None:
    doc_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/></Relationships>'
    )
    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:style w:type="paragraph" w:styleId="Heading1">'
        '<w:name w:val="heading 1"/></w:style></w:styles>'
    )
    parts = [
        f'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
        f'<w:r><w:t>基准标题 {index}</w:t></w:r></w:p>'
    ]
    for j in range(8):
        parts.append(
            f'<w:p><w:r><w:t>第 {j} 段：基准文档 {index} 的正文内容，'
            f'用于 Stage 8 封口评估。</w:t></w:r></w:p>'
        )
    parts.append(
        '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>阶段</w:t></w:r></w:p></w:tc>'
        '<w:tc><w:p><w:r><w:t>交付</w:t></w:r></w:p></w:tc></w:tr>'
        '<w:tr><w:tc><w:p><w:r><w:t>Stage 8</w:t></w:r></w:p></w:tc>'
        '<w:tc><w:p><w:r><w:t>生产化</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
    )
    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body>' + "".join(parts) + '</w:body></w:document>'
    )
    ct = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType='
        '"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType='
        '"application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/document.xml", doc_xml)


def _write_pdf(path: Path, index: int) -> None:
    lines = [
        f"Chapter {index} Benchmark Document Line {j}" for j in range(10)
    ]
    stream_parts = ["BT /F1 12 Tf 72 720 Td"]
    for k, line in enumerate(lines):
        op = f"({line}) Tj" if k == 0 else f"0 -14 Td ({line}) Tj"
        stream_parts.append(op)
    stream_parts.append("ET")
    stream = " ".join(stream_parts).encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_pos = len(pdf)
    n = len(objs) + 1
    pdf += b"xref\n" + f"0 {n}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += b"trailer\n<< /Size " + str(n).encode() + b" /Root 1 0 R >>\nstartxref\n"
    pdf += str(xref_pos).encode() + b"\n%%EOF"
    path.write_bytes(pdf)


def build_corpus(corpus_dir: Path, count: int) -> dict[str, int]:
    """确定性混合语料：i%10∈[0,4)→md、[4,7)→docx、[7,10)→pdf。"""
    corpus_dir.mkdir(parents=True, exist_ok=True)
    fmt_counts = {"md": 0, "docx": 0, "pdf": 0}
    for i in range(count):
        bucket = i % 10
        if bucket < 4:
            fmt = "md"
        elif bucket < 7:
            fmt = "docx"
        else:
            fmt = "pdf"
        name = f"bench-{i:03d}.{fmt}"
        p = corpus_dir / name
        if fmt == "md":
            _write_md(p, i)
        elif fmt == "docx":
            _write_docx(p, i)
        else:
            _write_pdf(p, i)
        fmt_counts[fmt] += 1
    return fmt_counts


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Stage 8 封口评估 100 文档基准")
    ap.add_argument("--count", type=int, default=100)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--keep", action="store_true", help="保留 corpus/out 供复查")
    args = ap.parse_args(argv[1:])

    if args.count < 1 or args.workers < 1:
        print("[ERROR] --count/--workers 须为正整数", file=sys.stderr)
        return 2

    if BENCH_DIR.exists():
        shutil.rmtree(BENCH_DIR)
    corpus_dir = BENCH_DIR / "corpus"
    out_dir = BENCH_DIR / "out"
    log_path = BENCH_DIR / "bench.jsonl"

    t0 = time.perf_counter()
    fmt_counts = build_corpus(corpus_dir, args.count)
    gen_seconds = time.perf_counter() - t0

    cmd = [
        sys.executable, "-m", "app.cli", "batch-parse", str(corpus_dir),
        "-o", str(out_dir), "--workers", str(args.workers),
        "--log-file", str(log_path),
    ]
    proc = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        print(f"[ERROR] batch-parse 退出码 {proc.returncode}", file=sys.stderr)
        print(proc.stderr[-4000:], file=sys.stderr)
        return 2

    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    events: dict[str, int] = {}
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ev = json.loads(line).get("event", "?")
        events[ev] = events.get(ev, 0) + 1

    wall = float(summary["wall_time_seconds"])
    passed = (
        summary["failed"] == 0
        and summary["success"] == args.count
        and wall < TIME_LIMIT_SECONDS
    )
    report = {
        "count": args.count,
        "formats": fmt_counts,
        "workers": summary["workers"],
        "cpu_count": os.cpu_count(),
        "corpus_gen_seconds": round(gen_seconds, 3),
        "wall_time_seconds": wall,
        "docs_per_minute": round(args.count / (wall / 60), 2),
        "time_limit_seconds": TIME_LIMIT_SECONDS,
        "success": summary["success"],
        "failed": summary["failed"],
        "jsonl_events": events,
        "passed": passed,
    }
    (BENCH_DIR / "bench-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(
        f"[{'PASS' if passed else 'FAIL'}] {args.count} 文档 "
        f"{wall:.1f}s（上限 {TIME_LIMIT_SECONDS:.0f}s），产出保留于 {BENCH_DIR}"
    )
    if not args.keep:
        shutil.rmtree(corpus_dir)
        shutil.rmtree(out_dir)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
