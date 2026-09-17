"""R2046：app.cli validate 子命令 CLI 信封未锁形态（真实子进程，main 只读）。

探针背景（outputs/autonomous/probe_validate_env_r2046.py + .out，main 6c6d398，
23 项：C0 + E1–E6，21 成立 + 4 处探针先验修正，零 main 缺陷）：R2038 已锁
family 路由矩阵 / 0.1.0–0.5.0 历史守卫 / 内置六类型双版本一致 / 0.6.0 内置缺
family / 计数报文 / 非 JSON 文件 rc 1 / 缺文件与目录 rc 2；main 侧
test_pipeline_integration 的 CLI 面只锁 parse 产物 validate rc 0。本轮补锁
CLI 信封残留六组：根类型族（非 object 根 + 空对象 13 处 required）、空/空白
文件（0 字节仍过 is_file 门走 JSON 解析失败而非 rc 2）、BOM JSON（json.loads
对 BOM 字符的专属报文，与 parse 通道 R2043 BOM .md rc 0 留存形成双通道对照）、
尾随垃圾（严格拒绝 Extra data）、argparse 信封（无参/缺 input/多余位置参数/
未知 flag rc 2、--help rc 0）、schema_version 边界（缺失 required/空串/未来
版本/数值型 → enum 单投诉，schema_version 规格仅 enum 无 type 关键字）。

被测对象解析：与 test_schema_routing_cli_r2038.py 同规——经
`git worktree list --porcelain` 动态定位 branch=refs/heads/main 的 worktree，
subprocess 走其 venv（r54 只读跨 worktree 授权：PYTHONDONTWRITEBYTECODE=1，
cwd/PYTHONPATH 指向临时目录与目标根，目标 worktree 零写入）。目标缺失 →
显式 SKIP，绝不伪造通过。
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
    env["PYTHONPATH"] = str(_MAIN_ROOT) + os.pathsep + str(cwd)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [py, "-m", "app.cli", *args],
        capture_output=True, env=env, cwd=cwd, timeout=90,
        encoding="utf-8", errors="replace",
    )


def _udm() -> dict:
    """R2038 同款最小合法 0.6.0 骨架（markdown/line_address）。"""
    return {
        "schema_version": "0.6.0",
        "document_id": "doc-r2046",
        "source_path": "samples/x",
        "source_type": "markdown",
        "source_hash": "a" * 64,
        "parser_name": "probe",
        "parser_version": "test/1.0",
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "parent_id": None,
                "source_locator": {"family": "line_address", "line": 1},
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


def _write(tmp: Path, name: str, data: bytes | str) -> Path:
    f = tmp / name
    if isinstance(data, str):
        f.write_text(data, encoding="utf-8", newline="")
    else:
        f.write_bytes(data)
    return f


def _val(tmp: Path, f: Path) -> subprocess.CompletedProcess:
    return _run_cli(tmp, "validate", str(f))


def test_root_type_family_and_empty_object(tmp_path: Path) -> None:
    """E1 根类型族：非 object 根一律 1 处根类型投诉；空对象 13 处 required。

    C0 前置：合法 0.6.0 骨架 rc 0（夹具自检，失败先疑探针/夹具）。
    """
    # C0
    p = _val(tmp_path, _write(tmp_path, "c0.json", json.dumps(_udm(), ensure_ascii=False)))
    assert p.returncode == 0 and "[OK]" in p.stdout, f"C0 夹具自检失败：{p.stderr}"

    # 非 object 根六形态 → rc 1 [FAIL] + 恰 1 处 "is not of type 'object'" @ path=[]
    non_object_roots = {
        "empty_array": b"[]",
        "array": b"[1, 2, 3]",
        "string": b'"hello"',
        "number": b"3.14",
        "null": b"null",
        "true": b"true",
    }
    for name, raw in non_object_roots.items():
        p = _val(tmp_path, _write(tmp_path, name + ".json", raw))
        assert p.returncode == 1, f"{name}: rc={p.returncode} stderr={p.stderr}"
        assert "[FAIL]" in p.stderr
        assert "Schema 校验失败 (1 处)" in p.stderr
        assert "is not of type 'object'" in p.stderr
        assert "@ path=[]" in p.stderr

    # 空对象 → 根类型合法，13 个 required 全缺（head=schema_version）
    p = _val(tmp_path, _write(tmp_path, "empty_object.json", b"{}"))
    assert p.returncode == 1
    assert "Schema 校验失败 (13 处)" in p.stderr
    assert "'schema_version' is a required property" in p.stderr
    assert "is not of type 'object'" not in p.stderr


def test_empty_whitespace_bom_and_trailing_garbage(tmp_path: Path) -> None:
    """E2/E3/E4：解析期四形态全部 rc 1 JSON 解析失败信封（非 rc 2 门）。

    - 0 字节/仅空白：文件存在（过 is_file 门）→ "Expecting value"；
    - BOM JSON：json.loads 对 BOM 字符的专属报文（Unexpected UTF-8 BOM），
      同内容去 BOM 双胞胎 rc 0——与 parse 通道（R2043）BOM .md rc 0 且
      BOM 留存 content 形成双通道对照：validate 拒、parse 收；
    - 尾随垃圾/双对象拼接：严格拒绝 "Extra data"，无宽松尾随容忍。
    """
    # 0 字节与仅空白
    p = _val(tmp_path, _write(tmp_path, "zero.json", b""))
    assert p.returncode == 1 and "[FAIL]" in p.stderr
    assert "JSON 解析失败" in p.stderr and "Expecting value" in p.stderr
    p = _val(tmp_path, _write(tmp_path, "blank.json", b"\n   \n\t\n"))
    assert p.returncode == 1
    assert "JSON 解析失败" in p.stderr and "Expecting value" in p.stderr

    # BOM JSON → 专属报文；去 BOM 双胞胎 rc 0（内容合法性对照）
    good = json.dumps(_udm(), ensure_ascii=False)
    p = _val(tmp_path, _write(tmp_path, "bom.json", b"\xef\xbb\xbf" + good.encode("utf-8")))
    assert p.returncode == 1 and "[FAIL]" in p.stderr
    assert "JSON 解析失败" in p.stderr
    assert "Unexpected UTF-8 BOM" in p.stderr
    p = _val(tmp_path, _write(tmp_path, "twin.json", good))
    assert p.returncode == 0, f"去 BOM 双胞胎应 rc 0：{p.stderr}"

    # 尾随垃圾与双对象拼接 → 严格拒绝
    p = _val(tmp_path, _write(tmp_path, "trailing.json", good + "\ngarbage"))
    assert p.returncode == 1
    assert "JSON 解析失败" in p.stderr and "Extra data" in p.stderr
    p = _val(tmp_path, _write(tmp_path, "concat.json", good + "\n" + good))
    assert p.returncode == 1 and "Extra data" in p.stderr


def test_argparse_envelope_and_schema_version_boundary(tmp_path: Path) -> None:
    """E5/E6：argparse 信封 rc 2/0 分工 + schema_version 四边界投诉精确性。

    - argparse：裸 CLI（required command）/ validate 缺 input / 多余位置参数 /
      未知 flag → 全 rc 2 usage 报错；--help → rc 0 且含 usage 行；
    - schema_version：缺失 → 恰 1 处 required；空串/未来版本 0.6.1/数值 0.6 →
      enum 单投诉且消息含完整六版本清单 @ path=['schema_version']（该属性
      规格仅 enum 无 type 关键字，数值型不另生 type 投诉）。
    """
    # argparse 信封
    p = _run_cli(tmp_path)
    assert p.returncode == 2
    assert "usage:" in p.stderr.lower() and "required" in p.stderr.lower()
    p = _run_cli(tmp_path, "validate")
    assert p.returncode == 2
    assert "required" in p.stderr.lower() and "input" in p.stderr
    good_file = _write(tmp_path, "ok.json", json.dumps(_udm(), ensure_ascii=False))
    p = _run_cli(tmp_path, "validate", str(good_file), "extra.json")
    assert p.returncode == 2 and "unrecognized arguments" in p.stderr
    p = _run_cli(tmp_path, "validate", "--bogus", str(good_file))
    assert p.returncode == 2 and "unrecognized arguments" in p.stderr.lower()
    p = _run_cli(tmp_path, "validate", "--help")
    assert p.returncode == 0 and "usage: app.cli validate" in p.stdout

    # schema_version 边界
    enum_msg = "is not one of ['0.1.0', '0.2.0', '0.3.0', '0.4.0', '0.5.0', '0.6.0']"

    d = _udm()
    d.pop("schema_version")
    p = _val(tmp_path, _write(tmp_path, "no_sv.json", json.dumps(d, ensure_ascii=False)))
    assert p.returncode == 1
    assert "Schema 校验失败 (1 处)" in p.stderr
    assert "'schema_version' is a required property" in p.stderr

    for name, bad_sv in (("empty_sv", ""), ("future_sv", "0.6.1"), ("number_sv", 0.6)):
        d = _udm()
        d["schema_version"] = bad_sv
        p = _val(tmp_path, _write(tmp_path, name + ".json", json.dumps(d, ensure_ascii=False)))
        assert p.returncode == 1, f"{name}: rc={p.returncode} stderr={p.stderr}"
        assert "Schema 校验失败 (1 处)" in p.stderr
        assert enum_msg in p.stderr
        assert "@ path=['schema_version']" in p.stderr
        assert "is not of type" not in p.stderr  # 仅 enum 无 type 关键字 → 单投诉
