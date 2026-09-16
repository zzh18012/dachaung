"""R2041：evaluation run 的 annotation 内容降级信封锁（真实 CLI 子进程）。

探针背景（outputs/autonomous/probe_annotation_env_r2041.py + .out，main 6c6d398，
C0 通过 + E1–E8 全部成立，main 前后 clean）：main 侧降级矩阵已**进程内**锁
（test_annotation_metrics / test_table_caption_prf / test_heading_order_prf /
test_caption_relation_contract），CLI 面仅 test_cli_run_with_annotation 一测
（单一 no_ground_truth_anchors_in_stream reason）。本轮锁 CLI 面三组残留：
1. **四形态区分度矩阵**——缺文件 / 坏 JSON / `{}` 三形态经真实 run 后
   per_doc.metrics **逐键相等**（全部 no_annotation，不可区分；坏 JSON 被
   `_load_annotation` 静默吞，runner.py:63-70，--log-file/--verbose 亦不可见，
   可见性缺陷候选 r54 记录不修）；缺键 JSON（合法骨架无指标键）可区分：
   figure/table→no_annotation_pairs、chunk→no_ground_truth_anchors、
   heading→no_ground_truth_headings。
2. **v1.1 新键消费 + schema 装饰性**——schemas/annotation.schema.json 在 run
   通道零消费（grep 无代码引用）：v1.0+table_caption_pairs（schema v1.0
   禁止的组合）仍被 table_caption_prf 消费（precision=no_predicted_relations
   / recall=0.0 / f1=precision_or_recall_not_evaluated）；schema required 键
   （annotation_version/doc_id）全缺仍消费；doc_id 错配 + 任意 version 仍
   消费（无运行时交叉核对）。
3. **C0 真实消费 + 落盘信封**——全量标注经真实 run 产出**非 null** 指标值
   （heading_order 1.0/1.0/1.0；chunk_boundary 全非 null）；persisted report
   per_doc 键集恰五项（_annotation_present/_tolerance_chars/_missing_markers
   全剔除），全文无 "tolerance" 子串——CLAUDE.md 评测规则"容差必须在报告中
   记录"与落盘实态的差距为文档/实现偏差候选（r54 记录不修）。

被测对象解析：与 test_eval_cli_channel_r2039.py 同规——经
`git worktree list` 动态定位 branch=refs/heads/main 的 worktree，subprocess
走其 venv（只读跨 worktree 授权：PYTHONDONTWRITEBYTECODE=1，cwd/PYTHONPATH
指向临时目录与目标根，目标 worktree 零写入）。目标缺失 → 显式 SKIP，
绝不伪造通过。
"""

from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path

import pytest

_WORKTREE_ROOT = Path(__file__).resolve().parent.parent

# 12 个 annotation 依赖指标键（figure/table/chunk/heading 各 P/R/F1）
ANN_KEYS = (
    "figure_caption_precision", "figure_caption_recall", "figure_caption_f1",
    "table_caption_precision", "table_caption_recall", "table_caption_f1",
    "chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1",
    "heading_order_precision", "heading_order_recall", "heading_order_f1",
)


def _resolve_main_worktree() -> Path | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(_WORKTREE_ROOT), "worktree", "list", "--porcelain"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    current: Path | None = None
    for line in out.stdout.splitlines():
        if line.startswith("worktree "):
            current = Path(line.split(" ", 1)[1])
        elif line == "branch refs/heads/main" and current is not None:
            if (current / "evaluation" / "runner.py").is_file():
                return current
    return None


_MAIN_ROOT = _resolve_main_worktree()


def _target_python(root: Path) -> str | None:
    for cand in (
        root / ".venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
    ):
        if cand.is_file():
            return str(cand)
    return None


pytestmark = pytest.mark.skipif(
    _MAIN_ROOT is None,
    reason="未找到含 evaluation/runner.py 的 main worktree（git worktree list）",
)


# ---------- 合成夹具（形状复制 main tests/test_evaluation_cli.py 构造法） ----------

CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>'''
RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
DOC_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style>
</w:styles>'''


def _build_synthetic_docx(path: Path) -> Path:
    doc_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Chapter 1</w:t></w:r></w:p>
    <w:p><w:r><w:t>Hello world. This is paragraph one.</w:t></w:r></w:p>
  </w:body>
</w:document>'''
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
        z.writestr("word/styles.xml", STYLES)
        z.writestr("word/document.xml", doc_xml)
    return path


def _build_root(tmp_path: Path, tag: str, ann_text: str | None) -> tuple[Path, Path]:
    """临时项目根 + 合成 DOCX + 单文档 manifest（annotation_file 恒指向
    annotations/TEST-001.json；ann_text=None 表示该文件不落盘=缺文件形态）。"""
    root = tmp_path / tag
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='t'\n", encoding="utf-8")
    for cmd in (["git", "init"], ["git", "config", "user.email", "t@t"],
                ["git", "config", "user.name", "t"], ["git", "add", "."],
                ["git", "commit", "-m", "init"]):
        subprocess.run(cmd, cwd=str(root), capture_output=True)
    docx_parent = root / "samples" / "test"
    docx_parent.mkdir(parents=True, exist_ok=True)
    _build_synthetic_docx(docx_parent / "sample.docx")
    if ann_text is not None:
        ann = root / "annotations" / "TEST-001.json"
        ann.parent.mkdir(parents=True)
        ann.write_text(ann_text, encoding="utf-8")
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [{
            "doc_id": "TEST-001",
            "path": "samples/test/sample.docx",
            "source_type": "docx",
            "annotation_file": "annotations/TEST-001.json",
        }],
    }
    mp = root / "manifest.json"
    mp.write_text(json.dumps(manifest), encoding="utf-8")
    return root, mp


def _run_cli(cwd: Path, manifest: Path, *extra: str, timeout: int = 180):
    py = _target_python(_MAIN_ROOT)  # type: ignore[arg-type]
    assert py is not None, "main worktree 缺 .venv 解释器"
    out = cwd / "outputs" / "report.json"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_MAIN_ROOT)  # type: ignore[operator]
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [py, "-m", "evaluation.cli", "run",
         "--manifest", str(manifest), "--output", str(out),
         "--max-chars", "32", *extra],
        capture_output=True, env=env, cwd=str(cwd), timeout=timeout,
        encoding="utf-8", errors="replace",
    )
    return proc, out


def _run_and_load(tmp_path: Path, tag: str, ann_text: str | None) -> tuple[int, dict, str]:
    root, mp = _build_root(tmp_path, tag, ann_text)
    proc, out = _run_cli(root, mp)
    assert out.is_file(), f"report 未写盘 rc={proc.returncode} stderr={proc.stderr[:300]}"
    text = out.read_text(encoding="utf-8")
    return proc.returncode, json.loads(text), text


def _reasons(report: dict) -> dict[str, str | None]:
    m = report["per_doc"][0]["metrics"]
    return {k: m[k]["reason"] for k in ANN_KEYS}


# ---------- 1. 四形态区分度矩阵 ----------


def test_annotation_degradation_matrix(tmp_path: Path):
    """缺文件 / 坏 JSON / {} 三形态不可区分（metrics 逐键相等 + 全 no_annotation）；
    缺键 JSON 可区分（四族 reason 各就各位）。坏 JSON 静默吞为可见性缺陷候选
    （r54 记录不修），本测试只锁当前行为。"""
    rc1, rep1, _ = _run_and_load(tmp_path, "e1_missing", None)
    rc2, rep2, _ = _run_and_load(tmp_path, "e2_badjson", "{ not valid json")
    rc3, rep3, _ = _run_and_load(tmp_path, "e3_empty_obj", "{}")
    assert (rc1, rc2, rc3) == (0, 0, 0)

    m1 = rep1["per_doc"][0]["metrics"]
    m2 = rep2["per_doc"][0]["metrics"]
    m3 = rep3["per_doc"][0]["metrics"]
    # 三形态 per-doc metrics 完全相等（含全部 annotation 族 12 键）
    assert m1 == m2 == m3
    assert set(_reasons(rep1).values()) == {"no_annotation"}

    # 缺键 JSON（合法骨架、无任何指标键）→ 四族各自降级 reason，可区分
    e4 = json.dumps({
        "annotation_version": "1.0", "doc_id": "TEST-001",
        "annotator": "reviewer_a", "date": "2026-09-16",
    })
    rc4, rep4, _ = _run_and_load(tmp_path, "e4_nokeys", e4)
    assert rc4 == 0
    r4 = _reasons(rep4)
    assert {k: r4[k] for k in ANN_KEYS if k.startswith("figure_caption_")} == {
        "figure_caption_precision": "no_annotation_pairs",
        "figure_caption_recall": "no_annotation_pairs",
        "figure_caption_f1": "no_annotation_pairs",
    }
    assert {k: r4[k] for k in ANN_KEYS if k.startswith("table_caption_")} == {
        "table_caption_precision": "no_annotation_pairs",
        "table_caption_recall": "no_annotation_pairs",
        "table_caption_f1": "no_annotation_pairs",
    }
    assert {k: r4[k] for k in ANN_KEYS if k.startswith("chunk_boundary_")} == {
        "chunk_boundary_precision": "no_ground_truth_anchors",
        "chunk_boundary_recall": "no_ground_truth_anchors",
        "chunk_boundary_f1": "no_ground_truth_anchors",
    }
    assert {k: r4[k] for k in ANN_KEYS if k.startswith("heading_order_")} == {
        "heading_order_precision": "no_ground_truth_headings",
        "heading_order_recall": "no_ground_truth_headings",
        "heading_order_f1": "no_ground_truth_headings",
    }


# ---------- 2. v1.1 新键（table_caption_pairs）消费 + schema 装饰性 ----------


def test_annotation_v11_key_consumption_schema_decoration(tmp_path: Path):
    """schemas/annotation.schema.json 在 run 通道零消费：v1.0+禁键、required
    键全缺、doc_id 错配 + 任意 version 三形态全部照常消费。"""
    # (a) v1.0 + table_caption_pairs：schema v1.0 禁止的组合，仍被消费
    e5 = json.dumps({
        "annotation_version": "1.0", "doc_id": "TEST-001",
        "table_caption_pairs": [{"table_marker": "paragraph", "caption_text": "one"}],
    })
    rc5, rep5, _ = _run_and_load(tmp_path, "e5_v1p0_table", e5)
    assert rc5 == 0
    m5 = rep5["per_doc"][0]["metrics"]
    # 文档无 table_has_caption relation → 0 预测；GT 1 对 → recall 诚实 0.0
    assert m5["table_caption_precision"]["reason"] == "no_predicted_relations"
    assert m5["table_caption_recall"] == {"value": 0.0, "reason": None}
    assert m5["table_caption_f1"]["reason"] == "precision_or_recall_not_evaluated"
    # figure 键缺失 → no_annotation_pairs（非 no_annotation，证明 annotation 被读到）
    assert m5["figure_caption_precision"]["reason"] == "no_annotation_pairs"

    # (b) schema required 键（annotation_version/doc_id）全缺仍消费
    e6 = json.dumps({
        "table_caption_pairs": [{"table_marker": "paragraph", "caption_text": "one"}],
    })
    rc6, rep6, _ = _run_and_load(tmp_path, "e6_norequired", e6)
    assert rc6 == 0
    m6 = rep6["per_doc"][0]["metrics"]
    assert m6["table_caption_precision"]["reason"] == "no_predicted_relations"
    assert m6["table_caption_recall"] == {"value": 0.0, "reason": None}

    # (c) doc_id 错配 + 任意 annotation_version 仍消费（无运行时交叉核对）
    e7 = json.dumps({
        "annotation_version": "9.9", "doc_id": "WRONG-DOC",
        "heading_order": [{"level": 1, "text": "Chapter 1"}],
    })
    rc7, rep7, _ = _run_and_load(tmp_path, "e7_mismatch", e7)
    assert rc7 == 0
    m7 = rep7["per_doc"][0]["metrics"]
    assert m7["heading_order_precision"] == {"value": 1.0, "reason": None}
    assert m7["heading_order_recall"] == {"value": 1.0, "reason": None}


# ---------- 3. C0 真实消费 + persisted report 落盘信封 ----------


def test_annotation_real_consumption_and_persisted_envelope(tmp_path: Path):
    """全量标注经真实 run 产出非 null 指标值（CLI 面真实消费证明）；persisted
    report 剔除全部下划线信封键且全文无 tolerance——后者与 CLAUDE.md"容差必须
    在报告中记录"构成文档/实现偏差候选（r54 记录不修），本测试锁当前落盘实态。"""
    ann = json.dumps({
        "annotation_version": "1.0", "doc_id": "TEST-001",
        "annotator": "reviewer_a", "date": "2026-09-16",
        "heading_order": [{"level": 1, "text": "Chapter 1"}],
        "chunk_boundary_anchors": [
            {"marker": "Hello world", "position": "before", "reason": "c0"},
        ],
    })
    rc, rep, text = _run_and_load(tmp_path, "c0_full", ann)
    assert rc == 0
    m = rep["per_doc"][0]["metrics"]
    assert m["heading_order_precision"] == {"value": 1.0, "reason": None}
    assert m["heading_order_recall"] == {"value": 1.0, "reason": None}
    assert m["heading_order_f1"] == {"value": 1.0, "reason": None}
    for k in ANN_KEYS:
        if k.startswith("chunk_boundary_"):
            assert m[k]["value"] is not None, f"{k} 应有非 null 值（真实消费）"

    # 落盘信封：per_doc 键集恰五项；信封键全剔除；全文无 tolerance 子串
    assert set(rep["per_doc"][0].keys()) == {
        "doc_id", "source_type", "parser_used", "metrics", "wall_time_seconds",
    }
    for marker in ("_annotation_present", "_tolerance_chars", "_missing_markers"):
        assert marker not in text
    assert "tolerance" not in text.lower()

    # ZZZ marker 形态（复刻 main test_cli_run_with_annotation）：内部有
    # _missing_markers、落盘不可见
    ann_zzz = json.dumps({
        "annotation_version": "1.0", "doc_id": "TEST-001",
        "chunk_boundary_anchors": [
            {"marker": "ZZZ_NONEXISTENT", "position": "after", "reason": "t"},
        ],
    })
    rc8, rep8, text8 = _run_and_load(tmp_path, "e8_zzz", ann_zzz)
    assert rc8 == 0
    m8 = rep8["per_doc"][0]["metrics"]
    assert m8["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    assert "_missing_markers" not in text8
