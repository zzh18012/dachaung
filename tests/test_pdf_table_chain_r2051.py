"""R2051：main PDF 表格链 find_tables→table element→locator→chunk 行为锁（R2050 P2 裁决面）。

探针背景（outputs/autonomous/probe_pdf_table_r2051.py + .out，main 6c6d398，
7 项矩阵 C0+V1–V6 全成立、零偏差、零 main 缺陷）：main 侧 PDF 表格抽取
（app/parsers/fallback_parser.py _parse_pdf L527-558 @ 6c6d398）结构级零覆盖
——main tests 的 table 断言全部落在 DOCX/HTML/markdown/ipynb，PDF 只有假
样例负例；R2050 盘点 13 面中 P2 是唯一"main 代码路径 + CI 零覆盖 + 三准则
全中"的未锁面（pdfplumber 0.11.10 / pdfminer-six CalVer 传递升级最可能
静默漂移点）。

本轮锁定的 main 契约（真实 CLI 子进程黑盒，被测 main 动态定位、零硬编码）：
1. 正链：ruled 2x2（m/l/S 线算子合成，复用 main test_pdf_vector_graphics
   构造模式）→ table element，content=canonical markdown（首行表头/`---`
   分隔/body），metadata{row_count=2, col_count=2, source="pdfplumber"}，
   confidence=0.7，locator{family="page_geometry", page=1, bbox=[100,92,400,192]}
   （pdfplumber top 系：top=页高792−PDF y）；
2. chunk：table 单独成 chunk，strategy="isolated_table"，
   source_element_ids=[该 table element_id]，text=markdown 全文；
3. 假阳性防线：无线纯文本 / 单横线 → 零 table element（find_tables "lines"
   策略需要线，不能靠文本形态出表）；
4. 升级噪声锚点：合并单元格（首列承载文本、延续格 None→""→`| AB |  |`，
   行列数不塌缩）、空单元格（None→""）、多页同表（page 逐表正确递增）。

被测对象经 `git worktree list --porcelain` 动态定位 branch=refs/heads/main
的 worktree，subprocess 走其 venv（r54 只读跨 worktree 授权：
PYTHONDONTWRITEBYTECODE=1，cwd/PYTHONPATH 指向临时目录与目标根，目标
worktree 零写入）。目标缺失 → 显式 SKIP，绝不伪造通过。
"""

from __future__ import annotations

import json
import os
import subprocess
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
            if (current / "schemas" / "document.schema.json").is_file():
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
    reason="未找到含 schemas/document.schema.json 的 main worktree（git worktree list）",
)


def _run_cli(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    assert _MAIN_ROOT is not None
    py = _target_python(_MAIN_ROOT)
    assert py is not None, "main worktree 缺 .venv 解释器"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_MAIN_ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [py, "-m", "app.cli", *args],
        capture_output=True, env=env, cwd=cwd, timeout=120,
        encoding="utf-8", errors="replace",
    )


# ---------- 最小多页 PDF 构造（手写字节流，无新增依赖） ----------

def _build_pdf(page_streams: list[str]) -> bytes:
    n = len(page_streams)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n))
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode(),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for i, s in enumerate(page_streams):
        objs[4 + 2 * i] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {5 + 2 * i} 0 R /Resources << /Font << /F1 3 0 R >> >> >>"
        ).encode()
        c = s.encode("latin-1")
        objs[5 + 2 * i] = (
            b"<< /Length " + str(len(c)).encode() + b" >>\nstream\n" + c + b"\nendstream"
        )
    out = b"%PDF-1.4\n"
    offs: dict[int, int] = {}
    for i in sorted(objs):
        offs[i] = len(out)
        out += f"{i} 0 obj\n".encode() + objs[i] + b"\nendobj\n"
    xref = len(out)
    m = max(objs) + 1
    out += b"xref\n0 " + str(m).encode() + b"\n0000000000 65535 f \n"
    for i in sorted(objs):
        out += f"{offs[i]:010d} 00000 n \n".encode()
    out += (b"trailer\n<< /Size " + str(m).encode() + b" /Root 1 0 R >>\nstartxref\n"
            + str(xref).encode() + b"\n%%EOF")
    return out


def _txt(x: float, y: float, s: str, size: int = 12) -> str:
    return f"BT /F1 {size} Tf {x} {y} Td ({s}) Tj ET\n"


def _ruled(x0: float, x1: float, ytop: float, ybot: float,
           col_xs: list[float], row_ys: list[float]) -> str:
    """ruled 网格：col_xs/row_ys 为内部分隔线；全部边 m/l/S 线算子（1pt）。"""
    parts = ["1 w\n"]
    for y in [ytop, *row_ys, ybot]:
        parts.append(f"{x0} {y:.1f} m {x1} {y:.1f} l S\n")
    for x in [x0, *col_xs, x1]:
        parts.append(f"{x} {ybot:.1f} m {x} {ytop:.1f} l S\n")
    return "".join(parts)


# 表格区 x∈[100,400] 列分隔 250；y∈[600,700] 行分隔 650（PDF 原点左下）
_GRID = _ruled(100, 400, 700, 600, col_xs=[250], row_ys=[650])
_ABCD = _txt(120, 660, "A") + _txt(270, 660, "B") + _txt(120, 610, "C") + _txt(270, 610, "D")


def _parse(tmp: Path, name: str, pdf: bytes) -> tuple[subprocess.CompletedProcess, dict]:
    """写 PDF → 真实 CLI parse → 返回 (proc, 输出 UDM dict)。"""
    src = tmp / f"{name}.pdf"
    src.write_bytes(pdf)
    out = tmp / f"{name}.out.json"
    p = _run_cli(tmp, "parse", str(src), "-o", str(out))
    if p.returncode != 0:
        return p, {}
    return p, json.loads(out.read_text(encoding="utf-8"))


def _tables(doc: dict) -> list[dict]:
    return [e for e in doc["elements"] if e["type"] == "table"]


def _table_chunks(doc: dict, tables: list[dict]) -> list[dict]:
    tids = {t["element_id"] for t in tables}
    return [c for c in doc["chunks"] if tids & set(c["source_element_ids"])]


# ---------- 1. 正链：ruled 2x2 → table element + locator + chunk ----------

def test_ruled_table_full_chain(tmp_path: Path) -> None:
    """V1 正链全锁：markdown 形状 / 行列元数据 / page_geometry locator（bbox 四数）/ isolated chunk。

    C0 前置：parse rc 0 + 输出经 validate rc 0（合成 PDF 合法性夹具自检）。
    """
    p, doc = _parse(tmp_path, "v1", _build_pdf([_GRID + _ABCD]))
    assert p.returncode == 0, f"parse 失败：{p.stderr[-800:]}"
    v = _run_cli(tmp_path, "validate", str(tmp_path / "v1.out.json"))
    assert v.returncode == 0 and "[OK]" in v.stdout, f"C0 validate 失败：{v.stdout[-300:]}"

    tables = _tables(doc)
    assert len(tables) == 1, f"恰 1 个 table element，实得 {[e['type'] for e in doc['elements']]}"
    t = tables[0]
    # canonical markdown：首行表头 + 每列 --- + body 行（linearize_table 契约）
    assert t["content"] == "| A | B |\n| --- | --- |\n| C | D |"
    assert t["confidence"] == 0.7
    assert t["metadata"] == {"row_count": 2, "col_count": 2, "source": "pdfplumber"}
    # page_geometry locator：top 系 bbox（top=792−PDF y）
    loc = t["source_locator"]
    assert loc["family"] == "page_geometry"
    assert loc["page"] == 1
    assert loc["bbox"] == [100.0, 92.0, 400.0, 192.0]

    # chunk：table 单独成 chunk，引用唯一且文本为 markdown 全文
    chunks = _table_chunks(doc, tables)
    assert len(chunks) == 1
    c = chunks[0]
    assert c["metadata"]["strategy"] == "isolated_table"
    assert c["source_element_ids"] == [t["element_id"]]
    assert c["text"] == t["content"]


# ---------- 2. 假阳性防线：无线 / 单横线不出 table ----------

def test_no_lines_and_single_line_produce_no_table(tmp_path: Path) -> None:
    """V2/V3：find_tables "lines" 策略下无线纯文本与单横线（<2 横边）零 table element。

    若 pdfplumber 升级改用文本策略默认或放宽成表条件，此处响亮失败——
    正是升级噪声检测点（假阳性面：文本不该凭形态成表）。
    """
    p2, doc2 = _parse(tmp_path, "v2", _build_pdf([_ABCD]))
    assert p2.returncode == 0, p2.stderr[-500:]
    assert _tables(doc2) == [], "无线纯文本不得产出 table element"
    v2 = _run_cli(tmp_path, "validate", str(tmp_path / "v2.out.json"))
    assert v2.returncode == 0

    one_line = "1 w\n100 650 m 400 650 l S\n" + _ABCD
    p3, doc3 = _parse(tmp_path, "v3", _build_pdf([one_line]))
    assert p3.returncode == 0, p3.stderr[-500:]
    assert _tables(doc3) == [], "单横线（不足两横边）不得产出 table element"


# ---------- 3. 升级噪声锚点：合并单元格 / 空单元格 / 多页 ----------

def test_merged_empty_multipage_noise_anchors(tmp_path: Path) -> None:
    """V4/V5/V6：extract() None 语义与逐页 locator——pdfplumber 升级最可能漂移的点。

    - 合并单元格：pdfplumber 把跨列文本放首列、延续格 None → linearize
      None→"" 渲染为空格列，行列数不塌缩（row_count/col_count 仍 2/2）；
    - 空单元格：None→""（`| C |  |`）；
    - 多页同表：每页各一表，page 逐表正确（1/2）。
    """
    merged = (
        "1 w\n"
        "100 700 m 400 700 l S\n100 650 m 400 650 l S\n100 600 m 400 600 l S\n"
        "100 600 m 100 700 l S\n250 600 m 250 650 l S\n400 600 m 400 700 l S\n"
        + _txt(120, 660, "AB") + _txt(120, 610, "C") + _txt(270, 610, "D")
    )
    p4, doc4 = _parse(tmp_path, "v4", _build_pdf([merged]))
    assert p4.returncode == 0, p4.stderr[-500:]
    t4 = _tables(doc4)
    assert len(t4) == 1
    assert t4[0]["content"] == "| AB |  |\n| --- | --- |\n| C | D |"
    assert t4[0]["metadata"]["row_count"] == 2 and t4[0]["metadata"]["col_count"] == 2

    p5, doc5 = _parse(
        tmp_path, "v5",
        _build_pdf([_GRID + _txt(120, 660, "A") + _txt(270, 660, "B") + _txt(120, 610, "C")]),
    )
    assert p5.returncode == 0, p5.stderr[-500:]
    t5 = _tables(doc5)
    assert len(t5) == 1
    assert t5[0]["content"] == "| A | B |\n| --- | --- |\n| C |  |"
    assert t5[0]["metadata"]["row_count"] == 2 and t5[0]["metadata"]["col_count"] == 2

    page2 = _GRID + _txt(120, 660, "E") + _txt(270, 660, "F") \
        + _txt(120, 610, "G") + _txt(270, 610, "H")
    p6, doc6 = _parse(tmp_path, "v6", _build_pdf([_GRID + _ABCD, page2]))
    assert p6.returncode == 0, p6.stderr[-500:]
    t6 = _tables(doc6)
    assert len(t6) == 2
    assert [t["source_locator"]["page"] for t in t6] == [1, 2]
    assert [t["content"].splitlines()[0] for t in t6] == ["| A | B |", "| E | F |"]
    # 每表各自 isolated chunk
    assert len(_table_chunks(doc6, t6)) == 2
