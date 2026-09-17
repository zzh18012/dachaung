"""R2052：main PDF 图像渲染链 pypdfium2 裁剪/尺寸口径行为锁（R2050 裁决 Y1 面）。

探针背景（outputs/autonomous/probe_render_y1_r2052.py + .out，main 6c6d398，
7 项矩阵 C0+V1–V6 全成立、零偏差、零 main 缺陷）：main 侧图像渲染链
（app/parsers/fallback_parser.py _render_pdf_image_region_verbose L365-407 +
_parse_pdf 图片分支 L559-626 @ 6c6d398，pypdfium2 5.12.1 / PIL 12.3.0）此前
仅真实样例 e2e 门控弱锁（test_pipeline_integration resource_path 存在性断言，
CI 上 SKIP），合成面零覆盖——pypdfium2 升级最可能静默改 render 口径
（render 签名有前科，且经 pdfplumber 传递锁定可被 uv upgrade 拖动）。

本轮锁定的 main 契约（真实 CLI 子进程黑盒，被测 main 动态定位、零硬编码）：
1. 正链：FlateDecode 裸 RGB 位图 XObject（zlib 压缩，纯标准库合成）→
   image element（content=None、confidence=0.6、metadata{srcsize=[8,8],
   extracted_to_disk=true}）+ locator{family="page_geometry", page=1,
   bbox=[100,142,200,192] top 系} + resource_path 实存 PNG
   `images-<hash16>/image_<hash16>_p1_00.png`；image 元素不进任何 chunk；
2. **裁剪口径=升级噪声锚点**：scale=dpi/72=2.0（100x50pt bbox → 200x100px）；
   坐标换算用 **int 截断**非 round/ceil（100.3..200.7pt bbox → 201px 宽，
   round 会得 200）；渲染页尺寸=MediaBox×scale（612pt→1224px）；
   min(pil.width,·) 越右缘 clamp（x1=700 → 宽 224）；max(0,·) 越左缘
   clamp（x0=-50 → 宽 100）；
3. 计数器/命名：image_counter 跨图跨页连续（同页两图 _00/_01；两页各一图
   p1_00/p2_01），bbox 逐图正确、page 逐图正确。
断言输出 PNG 像素尺寸口径而非像素内容（R2050 裁决：保确定性）。

被测对象经 `git worktree list --porcelain` 动态定位 branch=refs/heads/main
的 worktree，subprocess 走其 venv（r54 只读跨 worktree 授权：
PYTHONDONTWRITEBYTECODE=1，cwd/PYTHONPATH 指向临时目录与目标根，目标
worktree 零写入）。目标缺失 → 显式 SKIP，绝不伪造通过。PNG 尺寸手解
IHDR（struct，零新依赖）。
"""

from __future__ import annotations

import json
import os
import struct
import subprocess
import zlib
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
        capture_output=True, env=env, cwd=cwd, timeout=180,
        encoding="utf-8", errors="replace",
    )


# ---------- 合成 image-bearing PDF（FlateDecode RGB 位图，零新依赖） ----------

_IMG_W, _IMG_H = 8, 8
_IMG_COMP = zlib.compress(
    bytes((255, 0, 0)) * _IMG_W * (_IMG_H // 2)
    + bytes((0, 0, 255)) * _IMG_W * (_IMG_H - _IMG_H // 2),
    9,
)


def _build_pdf(page_streams: list[str]) -> bytes:
    """对象布局：1 Catalog / 2 Pages / 3 Font / 4 Image XObject；页从 5 起两两一组。"""
    n = len(page_streams)
    kids = " ".join(f"{5 + 2 * i} 0 R" for i in range(n))
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode(),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        4: (b"<< /Type /XObject /Subtype /Image /Width " + str(_IMG_W).encode()
            + b" /Height " + str(_IMG_H).encode()
            + b" /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode"
            + b" /Length " + str(len(_IMG_COMP)).encode()
            + b" >>\nstream\n" + _IMG_COMP + b"\nendstream"),
    }
    for i, s in enumerate(page_streams):
        objs[5 + 2 * i] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {6 + 2 * i} 0 R /Resources "
            f"<< /Font << /F1 3 0 R >> /XObject << /Im0 4 0 R >> >> >>"
        ).encode()
        c = s.encode("latin-1")
        objs[6 + 2 * i] = (
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


def _img(x: float, y: float, w: float, h: float) -> str:
    """unit square 经 cm 缩放平移放置图像（PDF 原点左下；页 612x792）。"""
    return f"q {w} 0 0 {h} {x} {y} cm /Im0 Do Q\n"


def _parse(tmp: Path, name: str, pdf: bytes) -> tuple[subprocess.CompletedProcess, dict]:
    src = tmp / f"{name}.pdf"
    src.write_bytes(pdf)
    out = tmp / f"{name}.out.json"
    p = _run_cli(tmp, "parse", str(src), "-o", str(out))
    if p.returncode != 0:
        return p, {}
    return p, json.loads(out.read_text(encoding="utf-8"))


def _images(doc: dict) -> list[dict]:
    return [e for e in doc["elements"] if e["type"] == "image"]


def _png_size(path: Path) -> tuple[int, int]:
    """手解 PNG IHDR：签名 8B + len 4B + 'IHDR' 4B -> width/height 各 4B 大端。"""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR", f"非 PNG：{path}"
    w, h = struct.unpack(">II", data[16:24])
    return w, h


# ---------- 1. 正链：合成图像 PDF -> image element + 实存 PNG + 口径锚 ----------

def test_image_render_full_chain(tmp_path: Path) -> None:
    """C0+V1 全锁：无图零 image element（假阳性防线）；有图正链 element 契约
    （content=None/confidence/metadata/srcsize）+ locator top 系 bbox 四数 +
    resource_path 实存 PNG（images-<hash16>/image_<hash16>_p1_00.png）+
    **scale=2.0 口径**（100x50pt -> 200x100px）+ image 不进任何 chunk。
    """
    # C0：无图纯文本 PDF——不该产 image element
    p0, doc0 = _parse(tmp_path, "c0", _build_pdf([_txt(100, 700, "Hello World Chapter 1")]))
    assert p0.returncode == 0, f"C0 parse 失败：{p0.stderr[-800:]}"
    v0 = _run_cli(tmp_path, "validate", str(tmp_path / "c0.out.json"))
    assert v0.returncode == 0 and "[OK]" in v0.stdout, f"C0 validate 失败：{v0.stdout[-300:]}"
    assert _images(doc0) == [], "无图 PDF 不得产出 image element（假阳性防线）"

    # V1：单图 x∈[100,200] y∈[600,650] -> pdfplumber top 系 bbox [100,142,200,192]
    p, doc = _parse(tmp_path, "v1", _build_pdf([_img(100, 600, 100, 50)]))
    assert p.returncode == 0, f"parse 失败：{p.stderr[-800:]}"
    v = _run_cli(tmp_path, "validate", str(tmp_path / "v1.out.json"))
    assert v.returncode == 0 and "[OK]" in v.stdout, f"validate 失败：{v.stdout[-300:]}"
    assert [w["code"] for w in doc["warnings"]] == [], f"意外 warnings：{doc['warnings']}"

    imgs = _images(doc)
    assert len(imgs) == 1, f"恰 1 个 image element，实得 {[e['type'] for e in doc['elements']]}"
    e = imgs[0]
    assert e["content"] is None
    assert e["confidence"] == 0.6
    assert e["metadata"]["srcsize"] == [8, 8]
    assert e["metadata"]["extracted_to_disk"] is True
    loc = e["source_locator"]
    assert loc["family"] == "page_geometry"
    assert loc["page"] == 1
    assert loc["bbox"] == [100.0, 142.0, 200.0, 192.0]

    # resource_path：images-<hash16>/image_<hash16>_p1_00.png，实存且 PNG 尺寸=口径锚
    rp = e["resource_path"]
    assert isinstance(rp, str) and rp not in ("(unrendered)", "(unsaved)")
    f = Path(rp)
    assert f.is_file() and f.stat().st_size > 0, f"渲染 PNG 不存在：{rp}"
    h16 = doc["document_id"].removeprefix("doc-")
    assert f.parent.name == f"images-{h16}"
    assert f.name == f"image_{h16}_p1_00.png"
    # 裁剪口径锚点：scale=2.0 -> 100x50pt bbox 渲染成 200x100px（截断无损失坐标）
    assert _png_size(f) == (200, 100), f"PNG 尺寸口径漂移：{_png_size(f)} != (200, 100)"

    # image 元素不参与任何 chunk（chunker._element_text 为空）
    img_ids = {e["element_id"]}
    assert all(
        not (img_ids & set(c["source_element_ids"])) for c in doc["chunks"]
    ), "image 元素不得进入文本 chunk"


# ---------- 2. 裁剪数学噪声锚：int 截断 + 双侧 clamp + 渲染页尺寸 ----------

def test_crop_math_truncation_and_clamps(tmp_path: Path) -> None:
    """V3/V4/V5：pypdfium2/PIL 升级最可能静默漂移的裁剪口径三连。

    - 小数坐标：int **截断**（bbox [100.3,140.9,200.7,191.3]pt -> 201x101px；
      若改 round 宽变 200——宽度维区分 int/round）；
    - 越右缘 x1=700>612：min(pil.width=1224, int(700*2)) -> 宽 224px
      （渲染页尺寸=MediaBox×scale=612*2=1224 的隐式锁定）；
    - 越左缘 x0=-50：max(0, int(-50*2)) -> 宽 100px。
    bbox 同步精确锁（top 系：top=792-(y+h)、bottom=792-y；V3 浮点容差）。
    """
    cases = [
        # (名称, pdf bytes, 期望 PNG (w,h), 期望 bbox 或 None, 说明)
        ("v3", _build_pdf([_img(100.3, 600.7, 100.4, 50.4)]), (201, 101),
         [100.3, 140.9, 200.7, 191.3], "int 截断非 round"),
        ("v4", _build_pdf([_img(500, 600, 200, 50)]), (224, 100),
         [500.0, 142.0, 700.0, 192.0], "min(pil.width) clamp"),
        ("v5", _build_pdf([_img(-50, 600, 100, 50)]), (100, 100),
         [-50.0, 142.0, 50.0, 192.0], "max(0) clamp"),
    ]
    for name, pdf, want, want_bbox, why in cases:
        p, doc = _parse(tmp_path, name, pdf)
        assert p.returncode == 0, f"{name} parse 失败：{p.stderr[-500:]}"
        imgs = _images(doc)
        assert len(imgs) == 1, f"{name} 应恰 1 image，实得 {[e['type'] for e in doc['elements']]}"
        rp = imgs[0]["resource_path"]
        assert isinstance(rp, str) and Path(rp).is_file(), f"{name} PNG 未落盘：{rp}"
        size = _png_size(Path(rp))
        assert size == want, (
            f"{name}（{why}）裁剪口径漂移：{size} != {want}"
            f"（bbox={imgs[0]['source_locator']['bbox']}）"
        )
        # bbox 精确锁（top 系换算 top=792-(y+h)；V3 小数经 pdfplumber 浮点，容差锁）
        assert imgs[0]["source_locator"]["bbox"] == pytest.approx(want_bbox, abs=1e-6), (
            f"{name} bbox 漂移：{imgs[0]['source_locator']['bbox']} != {want_bbox}"
        )


# ---------- 3. 计数器与命名：同页两图 / 两页各一图 ----------

def test_counter_naming_multi_image_and_multi_page(tmp_path: Path) -> None:
    """V2/V6：image_counter 跨图跨页连续（_00/_01 与 p1_00/p2_01），
    文件名前缀 p<page>、bbox 逐图正确、locator page 逐图正确（1/2）。
    """
    # V2：同页两图（x∈[100,200] 与 [300,400]）
    p2, doc2 = _parse(
        tmp_path, "v2", _build_pdf([_img(100, 600, 100, 50) + _img(300, 600, 100, 50)])
    )
    assert p2.returncode == 0, p2.stderr[-500:]
    imgs2 = _images(doc2)
    assert len(imgs2) == 2, f"应 2 个 image element，实得 {len(imgs2)}"
    h16 = doc2["document_id"].removeprefix("doc-")
    assert [Path(e["resource_path"]).name for e in imgs2] == [
        f"image_{h16}_p1_00.png", f"image_{h16}_p1_01.png",
    ], "同页两图计数器应连续 _00/_01"
    assert [e["source_locator"]["bbox"][0] for e in imgs2] == [100.0, 300.0]
    assert all(_png_size(Path(e["resource_path"])) == (200, 100) for e in imgs2)

    # V6：两页各一图——计数器跨页连续，前缀随 page 变
    p6, doc6 = _parse(
        tmp_path, "v6", _build_pdf([_img(100, 600, 100, 50), _img(100, 600, 100, 50)])
    )
    assert p6.returncode == 0, p6.stderr[-500:]
    imgs6 = _images(doc6)
    assert len(imgs6) == 2, f"应 2 个 image element（每页各 1），实得 {len(imgs6)}"
    h16b = doc6["document_id"].removeprefix("doc-")
    assert [Path(e["resource_path"]).name for e in imgs6] == [
        f"image_{h16b}_p1_00.png", f"image_{h16b}_p2_01.png",
    ], "两页各一图应 p1_00/p2_01（counter 跨页连续）"
    assert [e["source_locator"]["page"] for e in imgs6] == [1, 2]
    assert all(Path(e["resource_path"]).is_file() for e in imgs6)
