"""R2039：evaluation.cli run / validate-report 通道残留面的 CLI 端到端锁（真实子进程）。

探针背景（outputs/autonomous/probe_eval_cli_r2039.py + .out，main 6c6d398，
C0 通过 + E1–E6 全部成立）：main 侧 tests/test_manifest.py 仅在**进程内**锁
documents[].path 守卫三类；tests/test_evaluation_cli.py 仅 7 测（run e2e /
annotation 正例 / validate-report 正例与缺文件 / 缺 manifest / 坏 JSON /
expected failures）。三个残留面在 main 零覆盖：
1. **annotation_file / expected_failures[].path / max_silent_drop_count 守卫
   经 CLI 信封**（manifest.py 另两个 _resolve_relative_path 调用点 +
   expectations 前置检查）——rc 1 + "清单加载失败" + 字段名进报文 + 不写盘；
2. **--workers 1 vs 2 输出等价性**（批次 16 契约；runner.py:203 ≥3 任务才走
   Pool，Windows spawn）——去时变字段后全报告相等、保 manifest 原序；
   <3 任务 workers=2 静默走顺序路径；
3. **validate-report 负例信封**——坏 JSON → rc 1 [ERROR] JSON 解析失败；
   非报告 JSON / schema 违规 → rc 1 [FAIL]（含枚举投诉）；目录 → rc 2。

附带观察（记录不修，r54）：load_manifest docstring 称"向上找 .git 或
pyproject.toml"，实现 _detect_project_root 只找 pyproject.toml；
cwd 无关性与嵌套 manifest 最近祖先语义在探针 E3 实证成立。

被测对象解析：与 test_schema_routing_cli_r2038.py 同规——经
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
            if (current / "evaluation" / "cli.py").is_file():
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
    reason="未找到含 evaluation/cli.py 的 main worktree（git worktree list）",
)


def _run_cli(cwd: Path, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    py = _target_python(_MAIN_ROOT)  # type: ignore[arg-type]
    assert py is not None, "main worktree 缺 .venv 解释器"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_MAIN_ROOT) + os.pathsep + str(cwd)  # type: ignore[operator]
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [py, "-m", "evaluation.cli", *args],
        capture_output=True, env=env, cwd=cwd, timeout=timeout,
        encoding="utf-8", errors="replace",
    )


def _build_synthetic_docx(path: Path) -> Path:
    """最小合法 DOCX（形状复制 main tests/test_evaluation_cli.py 夹具）。"""
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    doc_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style>
</w:styles>'''
    doc_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Chapter 1</w:t></w:r></w:p>
    <w:p><w:r><w:t>Hello world. This is paragraph one.</w:t></w:r></w:p>
  </w:body>
</w:document>'''
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/styles.xml", styles)
        z.writestr("word/document.xml", doc_xml)
    return path


def _make_project(tmp_path: Path, name: str) -> Path:
    """临时项目根：pyproject.toml + git init + 初始提交（provenance 用）。"""
    root = tmp_path / name
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='r2039'\n", encoding="utf-8")
    for cmd in (
        ["git", "init"], ["git", "config", "user.email", "t@t"],
        ["git", "config", "user.name", "t"], ["git", "add", "."],
        ["git", "commit", "-m", "init"],
    ):
        subprocess.run(cmd, cwd=str(root), capture_output=True)
    return root


def _write_manifest(root: Path, data: dict, rel: str = "manifest.json") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def test_manifest_field_guards_via_cli_envelope(tmp_path: Path) -> None:
    """manifest 加载期守卫经真实 CLI 信封（main 进程内只锁了 documents[].path）。

    - annotation_file 三类违规（绝对/反斜杠/越根）→ rc 1 +
      "清单加载失败" + 字段名 documents[X].annotation_file 进报文 + 不写报告；
    - expected_failures[].path 越根 → rc 1 + 字段名 expected_failures[X].path；
    - expectations.max_silent_drop_count 声明上限但无 element_count_by_type
      → rc 1 + 报文点名 max_silent_drop_count。
    documents[].path 本身保持合法（它是第一个被校验的字段，必须干净，
    才能证明触发点在 annotation_file / expected_failures / expectations）。
    """
    root = _make_project(tmp_path, "t1")
    _build_synthetic_docx(root / "samples" / "test" / "sample.docx")
    good_path = "samples/test/sample.docx"

    ann_cases = {
        "absolute": ("C:/Users/foo/ann.json", "绝对路径"),
        "backslash": ("annotations\\a.json", "正斜杠"),
        "escape": ("../../../../etc/ann.json", "项目根目录之外"),
    }
    for name, (ann, complaint) in ann_cases.items():
        m = _write_manifest(root, {
            "manifest_version": "1.0", "devset_status": "incomplete",
            "documents": [{
                "doc_id": "TEST-001", "path": good_path,
                "source_type": "docx", "annotation_file": ann,
            }],
        }, rel=f"m_ann_{name}.json")
        out = root / "outputs" / f"ann_{name}.json"
        r = _run_cli(root, "run", "--manifest", str(m), "--output", str(out))
        assert r.returncode == 1, f"{name}: rc={r.returncode}"
        assert "清单加载失败" in r.stderr, f"{name}: {r.stderr}"
        assert "documents[TEST-001].annotation_file" in r.stderr
        assert complaint in r.stderr, f"{name}: {r.stderr}"
        assert not out.exists(), f"{name}: 违规清单不得产出报告"

    m_ef = _write_manifest(root, {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [{
            "doc_id": "ERR-1", "path": "../../etc/passwd",
            "expected_error_code": "x",
        }],
    }, rel="m_ef.json")
    out_ef = root / "outputs" / "ef.json"
    r = _run_cli(root, "run", "--manifest", str(m_ef), "--output", str(out_ef))
    assert r.returncode == 1
    assert "清单加载失败" in r.stderr
    assert "expected_failures[ERR-1].path" in r.stderr
    assert "项目根目录之外" in r.stderr
    assert not out_ef.exists()

    m_sd = _write_manifest(root, {
        "manifest_version": "1.1", "devset_status": "incomplete",
        "documents": [{
            "doc_id": "TEST-001", "path": good_path, "source_type": "docx",
            "expectations": {"max_silent_drop_count": 0},
        }],
    }, rel="m_sd.json")
    out_sd = root / "outputs" / "sd.json"
    r = _run_cli(root, "run", "--manifest", str(m_sd), "--output", str(out_sd))
    assert r.returncode == 1
    assert "清单加载失败" in r.stderr
    assert "max_silent_drop_count" in r.stderr
    assert "element_count_by_type" in r.stderr
    assert not out_sd.exists()


def _strip_volatile(report: dict) -> dict:
    """去掉时变字段：provenance.run_timestamp_iso 与 per_doc.wall_time_seconds。"""
    r = json.loads(json.dumps(report))
    r["provenance"].pop("run_timestamp_iso", None)
    for pd in r.get("per_doc", []):
        pd.pop("wall_time_seconds", None)
    return r


def test_workers_1_vs_2_report_equivalence(tmp_path: Path) -> None:
    """批次 16 契约端到端：--workers 2 与 --workers 1 输出等价（Windows spawn 池）。

    - 3 docs（≥3 任务）workers=2 真正走 Pool.imap 路径；去时变字段
      （run_timestamp_iso / per_doc.wall_time_seconds）后与 workers=1 全报告
      相等：per_doc 顺序 == manifest 原序、metrics/summary/devset/
      expected_failures 逐字段一致；
    - 同一 manifest 从不同 cwd 跑 → 报告相同（project_root 探测锚定
      manifest 位置，与 cwd 无关）；
    - 2 docs + workers=2（<3 任务）静默走顺序路径：rc 0 且全部成功
      （CLAUDE.md 已记录的已知行为，锁边界）。
    """
    root = _make_project(tmp_path, "t2")
    docs = []
    for i in range(1, 4):
        rel = f"samples/test/d{i}.docx"
        _build_synthetic_docx(root / rel)
        docs.append({"doc_id": f"DOC-{i:03d}", "path": rel, "source_type": "docx"})
    m = _write_manifest(root, {
        "manifest_version": "1.0", "devset_status": "incomplete", "documents": docs,
    })

    reports = {}
    for label, extra, cwd in (
        ("w1", [], root),
        ("w2", ["--workers", "2"], root),
        ("w1_other_cwd", [], tmp_path / "t2_other_cwd"),
    ):
        if label == "w1_other_cwd":
            cwd.mkdir()
        out = root / "outputs" / f"{label}.json"
        r = _run_cli(cwd, "run", "--manifest", str(m), "--output", str(out), *extra)
        assert r.returncode == 0, f"{label}: rc={r.returncode} err={r.stderr}"
        reports[label] = json.loads(out.read_text(encoding="utf-8"))

    expected_order = [f"DOC-{i:03d}" for i in (1, 2, 3)]
    for label in ("w1", "w2", "w1_other_cwd"):
        order = [d["doc_id"] for d in reports[label]["per_doc"]]
        assert order == expected_order, f"{label}: per_doc 未保 manifest 原序: {order}"
        for d in reports[label]["per_doc"]:
            assert d["metrics"]["pipeline_success"]["value"] is True

    baseline = _strip_volatile(reports["w1"])
    assert _strip_volatile(reports["w2"]) == baseline, "workers=2 报告应与 workers=1 等价"
    assert _strip_volatile(reports["w1_other_cwd"]) == baseline, "换 cwd 跑同一 manifest 报告应相同"

    m_small = _write_manifest(root, {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": docs[:2],
    }, rel="m_small.json")
    out_small = root / "outputs" / "small_w2.json"
    r = _run_cli(root, "run", "--manifest", str(m_small),
                 "--output", str(out_small), "--workers", "2")
    assert r.returncode == 0, f"2 docs + workers=2 应静默走顺序路径: {r.stderr}"
    rep_small = json.loads(out_small.read_text(encoding="utf-8"))
    assert len(rep_small["per_doc"]) == 2
    assert all(d["metrics"]["pipeline_success"]["value"] is True for d in rep_small["per_doc"])


def test_validate_report_negative_envelope(tmp_path: Path) -> None:
    """validate-report 负例信封（main 只锁了缺文件 rc 2）。

    - 坏 JSON → rc 1 + [ERROR] + "JSON 解析失败"；
    - 合法 JSON 但非报告（{}）→ rc 1 + [FAIL] + schema 投诉；
    - 删 required 字段 per_doc → rc 1 + [FAIL] + "'per_doc' is a required property"；
    - report_version 非法枚举 → rc 1 + [FAIL] + "is not one of"；
    - 目录输入 → rc 2 + "不存在"。
    """
    root = _make_project(tmp_path, "t3")
    _build_synthetic_docx(root / "samples" / "test" / "sample.docx")
    m = _write_manifest(root, {
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [{
            "doc_id": "TEST-001", "path": "samples/test/sample.docx",
            "source_type": "docx",
        }],
    })
    good_report = root / "outputs" / "report.json"
    r = _run_cli(root, "run", "--manifest", str(m), "--output", str(good_report))
    assert r.returncode == 0, r.stderr
    good = json.loads(good_report.read_text(encoding="utf-8"))

    def check(name: str, text: str, rc_exp: int, *needles: str) -> None:
        f = root / "outputs" / f"neg_{name}.json"
        f.write_text(text, encoding="utf-8")
        rr = _run_cli(root, "validate-report", str(f))
        assert rr.returncode == rc_exp, f"{name}: rc={rr.returncode} err={rr.stderr}"
        for n in needles:
            assert n in rr.stderr, f"{name}: 缺 '{n}': {rr.stderr}"

    check("bad_json", "{ not valid json", 1, "[ERROR]", "JSON 解析失败")
    check("not_report", "{}", 1, "[FAIL]", "'report_version' is a required property")

    dropped = json.loads(json.dumps(good))
    dropped.pop("per_doc")
    check("drop_per_doc", json.dumps(dropped), 1, "[FAIL]",
          "'per_doc' is a required property")

    badver = json.loads(json.dumps(good))
    badver["report_version"] = "9.9"
    check("bad_version", json.dumps(badver), 1, "[FAIL]",
          "'9.9' is not one of")

    rr = _run_cli(root, "validate-report", str(root / "outputs"))
    assert rr.returncode == 2
    assert "不存在" in rr.stderr
