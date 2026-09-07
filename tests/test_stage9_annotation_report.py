# -*- coding: utf-8 -*-
"""Stage 9 批次 26：标注人工抽查渲染工具测试（只读支撑件）。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage9_annotation_report.py"


def _ann():
    parts = []
    units = []
    pos = 0
    items = [
        ("h", "Title", "g00", True, 1, None),
        ("s", "First sentence.", "g00", False, 1, None),
        ("s", "Second sentence.", "g01", True, 1, None),
        ("n", "img:fig-1", "g01", False, 1, None),
        ("s", "Next page text.", "g01", False, 2, None),
    ]
    for idx, (kind, payload, seg, hard, page, body) in enumerate(items):
        unit = {"unit_id": "u%04d" % (idx + 1), "page": page,
                "body_index": body, "gold_segment_id": seg,
                "hard_boundary_before": hard}
        if kind == "n":
            unit.update(kind="nontext", char_span=None,
                        nontext_ref=payload)
        else:
            if parts:
                parts.append(" ")
                pos += 1
            start = pos
            parts.append(payload)
            pos += len(payload)
            unit.update(kind="heading" if kind == "h" else "sentence",
                        char_span=[start, pos], nontext_ref=None)
        units.append(unit)
    return {
        "doc_id": "d-test", "annotation_schema": "v1.1",
        "sentence_splitter": "v1", "normalization": "fold-ws-v1",
        "annotator": "test", "stream": "".join(parts), "units": units,
        "notes": "处理口径：目录页未入句子流。",
        "segments": [
            {"gold_segment_id": "g00", "hint": "题名", "kind":
             "frontmatter"},
            {"gold_segment_id": "g01", "hint": "§1", "kind": "body"}],
    }


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True, cwd=str(ROOT))


def test_render_reading_order_view(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text(json.dumps(_ann(), ensure_ascii=False), encoding="utf-8")
    r = run("--annotation", str(p))
    assert r.returncode == 0, r.stdout + r.stderr
    out = r.stdout
    # 头部统计与 segment 一览；annotation_sha256 绑定输入版本
    assert "doc_id: d-test" in out
    import hashlib
    expect_sha = hashlib.sha256(p.read_bytes()).hexdigest()
    assert "annotation_sha256=%s" % expect_sha in out
    assert "units: 5（text 4 + nontext 1）" in out
    assert "标注 notes（处理口径——排除项/判定依据）" in out
    assert "处理口径：目录页未入句子流。" in out
    assert "g00  题名（frontmatter）× 2 units" in out
    # 阅读序：分组标题、硬边界标记、页分隔线、全文呈现
    assert "[segment g00  题名（frontmatter）]" in out
    assert "◆ u0001 p1 heading Title" in out
    assert "  u0002 p1 sentence First sentence." in out
    assert "◆ u0003 p1 sentence Second sentence." in out
    assert "-- 第 2 页 --" in out
    assert "u0005 p2 sentence Next page text." in out
    # nontext 显示 ref 而非 span 文本
    assert "u0004  nontext img:fig-1" in out


def test_render_out_file(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text(json.dumps(_ann(), ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "report.txt"
    r = run("--annotation", str(p), "--out", str(out))
    assert r.returncode == 0, r.stdout + r.stderr
    body = out.read_text(encoding="utf-8")
    assert "doc_id: d-test" in body and "◆ u0001" in body
    assert "已写" in r.stdout


def test_render_body_index_locator_for_docx(tmp_path):
    ann = _ann()
    for u in ann["units"]:
        u["page"] = None
        u["body_index"] = 3
    p = tmp_path / "ann.json"
    p.write_text(json.dumps(ann, ensure_ascii=False), encoding="utf-8")
    r = run("--annotation", str(p))
    assert r.returncode == 0
    assert "u0002 b3 sentence First sentence." in r.stdout
    assert "-- 第" not in r.stdout  # 页未知不插分隔线


def test_input_errors_rc2(tmp_path):
    assert run("--annotation", str(tmp_path / "nope.json")).returncode == 2
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert run("--annotation", str(bad)).returncode == 2
    missing = tmp_path / "missing.json"
    missing.write_text("{}", encoding="utf-8")
    assert run("--annotation", str(missing)).returncode == 0  # 空 tolerant
