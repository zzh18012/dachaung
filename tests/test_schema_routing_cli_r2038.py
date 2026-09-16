"""R2038：schema 0.6.0 family 路由 + validate 子命令契约的 CLI 端到端面（真实子进程）。

探针背景（outputs/autonomous/probe_schema_routing_r2038.py，main 6c6d398，
55/55 PASS）：main 侧 test_schema_source_type_open.py 已在**进程内**（直调
app.schema.validate）锁死 0.6.0 扩展类型 family 路由矩阵、0.1.0–0.5.0 守卫、
pattern 边界与内置六类型 0.5.0/0.6.0 双版本一致；CLI `validate` 子命令在
main 侧只对 **parse 产物**复检过（test_pipeline_integration /
test_plugin_myx_fullchain）。**手造 JSON 经真实 CLI validate 通道的路由
矩阵/历史守卫**，以及**"schema 合法但契约违规"JSON 在 validate 放行
（rc 0）而 parse 经真实插件拒收（parser_contract_mismatch rc 1 不写盘）**
的职责缝隙，两侧均零覆盖。本文件锁三项，全部 subprocess 走 main venv
真实 CLI。

被测对象解析：与 test_registry_cli_freeze_and_rejects.py 同规——经
`git worktree list` 动态定位 branch=refs/heads/main 的 worktree，subprocess
走其 venv（r54 只读跨 worktree 授权：PYTHONDONTWRITEBYTECODE=1，cwd/
PYTHONPATH 指向临时目录与目标根，目标 worktree 零写入）。目标缺失 →
显式 SKIP，绝不伪造通过。
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

_WORKTREE_ROOT = Path(__file__).resolve().parent.parent

# 声明 smk/line_address 但产出 family 可注入的探针插件（R2038 探针同款）。
_SMK_PLUGIN = '''"""R2038 测试插件（tests 专用，永不内置/进 AUTO 映射）。"""
from __future__ import annotations

from pathlib import Path

from app.models import Document, Element
from app.parser_registry import register
from app.parsers.base import Parser, make_document_id


@register
class SmkR2038Parser(Parser):
    name = "r2038_smk"
    version = "test/1.0"
    supported_extensions = (".smk",)
    priority = 10
    source_types = ("smk",)
    locator_family = "line_address"

    def parse(self, path, source_hash):
        p = Path(path)
        document_id = make_document_id(source_hash)
        # 产出 family 与声明不符（page_geometry/page 在 0.6.0 schema 下
        # 按 family 路由自洽合法——只有契约检查能拦截）
        loc = {"family": "page_geometry", "page": 1}
        return Document(
            document_id=document_id,
            source_path=str(p),
            source_type="smk",
            source_hash=source_hash,
            parser_name=self.name,
            parser_version=self.version,
            elements=[Element(element_id=document_id + "::e0001",
                              type="paragraph", content="x",
                              source_locator=loc)],
        )
'''

_SMK_PLUGIN_HONEST = _SMK_PLUGIN.replace(
    'name = "r2038_smk"', 'name = "r2038_smk_honest"'
).replace(
    '        # 产出 family 与声明不符（page_geometry/page 在 0.6.0 schema 下\n'
    '        # 按 family 路由自洽合法——只有契约检查能拦截）\n'
    '        loc = {"family": "page_geometry", "page": 1}',
    '        loc = {"family": "line_address", "line": 1}',
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


def _run_cli(cwd: Path, root: Path, *args: str) -> subprocess.CompletedProcess:
    py = _target_python(root)
    assert py is not None, "main worktree 缺 .venv 解释器"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root) + os.pathsep + str(cwd)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [py, "-m", "app.cli", *args],
        capture_output=True, env=env, cwd=cwd, timeout=90,
        encoding="utf-8", errors="replace",
    )


def _udm(source_type: str, version: str, locators: list[dict]) -> dict:
    """最小合法 document 骨架（形状参照 main test_schema_source_type_open._udm）。"""
    return {
        "schema_version": version,
        "document_id": "doc-r2038",
        "source_path": "samples/x",
        "source_type": source_type,
        "source_hash": "a" * 64,
        "parser_name": "probe",
        "parser_version": "test/1.0",
        "elements": [
            {
                "element_id": f"e{i}",
                "type": "paragraph",
                "parent_id": None,
                "source_locator": loc,
                "content": "x",
                "resource_path": None,
                "confidence": 1.0,
                "metadata": {},
            }
            for i, loc in enumerate(locators, 1)
        ],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def _validate(tmp_path: Path, name: str, doc: dict) -> subprocess.CompletedProcess:
    f = tmp_path / name
    f.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return _run_cli(tmp_path, _MAIN_ROOT, "validate", str(f))


def test_060_family_routing_matrix_via_validate_channel(tmp_path: Path) -> None:
    """扩展类型 @0.6.0 手造 JSON 经真实 CLI validate：路由矩阵正负例。

    - 正例：四 family 各自形状合法 rc 0 [OK]；structural_index 仅 family
      自身也合法（docx_locator minProperties=1 含 family）；line_address
      允许扩展键（additionalProperties true）；**多 element 混 family**
      （各自形状自洽）rc 0——schema 按逐 element 路由，跨 element family
      一致性是 parse 期契约检查的职责而非 schema 的。
    - 负例：缺 family / 未知 family / 各 family 错形状 → rc 1 [FAIL]，
      stderr 报文含精确 schema 投诉（required property / enum / minimum）。
    """
    assert _MAIN_ROOT is not None
    positives = {
        "la": [{"family": "line_address", "line": 1}],
        "pg": [{"family": "page_geometry", "page": 1, "bbox": [0, 0, 1, 1]}],
        "si": [{"family": "structural_index", "paragraph_index": 0}],
        "si_only": [{"family": "structural_index"}],
        "cl": [{"family": "container_line", "cell_index": 0, "cell_type": "code"}],
        "la_extra": [{"family": "line_address", "line": 1, "col": 4}],
        "mixed": [
            {"family": "line_address", "line": 1},
            {"family": "page_geometry", "page": 1},
        ],
    }
    for name, locs in positives.items():
        r = _validate(tmp_path, f"t1p_{name}.json", _udm("smk", "0.6.0", locs))
        assert r.returncode == 0, f"{name}: rc={r.returncode} err={r.stderr}"
        assert "[OK]" in r.stdout

    negatives = {
        # 缺 family / 未知 family
        "no_family": ([{"line": 1}], "'family' is a required property"),
        "vector": ([{"family": "vector", "line": 1}], "'vector' is not one of"),
        # 各 family 错形状
        "pg_no_page": ([{"family": "page_geometry"}], "'page' is a required property"),
        "pg_page0": ([{"family": "page_geometry", "page": 0}], "minimum of 1"),
        "la_no_line": ([{"family": "line_address"}], "'line' is a required property"),
        "cl_bad_type": (
            [{"family": "container_line", "cell_index": 0, "cell_type": "formula"}],
            "'formula' is not one of",
        ),
    }
    for name, (locs, complaint) in negatives.items():
        r = _validate(tmp_path, f"t1n_{name}.json", _udm("smk", "0.6.0", locs))
        assert r.returncode == 1, f"{name}: rc={r.returncode}"
        assert "[FAIL]" in r.stderr
        assert complaint in r.stderr, f"{name}: {r.stderr}"


def test_old_version_guards_and_builtin_parity_via_validate_channel(
    tmp_path: Path,
) -> None:
    """历史守卫与内置双版本一致经真实 CLI validate：

    - 0.1.0–0.5.0 全部五个版本 × 扩展类型 → rc 1（守卫仍限内置六类型，
      历史不回写）；
    - 内置六类型 × {0.5.0, 0.6.0} → 全部 rc 0（升版零回归承诺）；
    - 0.6.0 下内置类型缺 family → rc 1（family 绑定分支已扩到 0.6.0）。
    """
    assert _MAIN_ROOT is not None
    for v in ["0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0"]:
        r = _validate(
            tmp_path, f"t2g_{v}.json",
            _udm("smk", v, [{"family": "line_address", "line": 1}]),
        )
        assert r.returncode == 1, f"{v} + smk 应被守卫拒绝: rc={r.returncode}"

    builtin_loc = {
        "pdf": {"family": "page_geometry", "page": 1},
        "docx": {"family": "structural_index", "paragraph_index": 0},
        "markdown": {"family": "line_address", "line": 1},
        "html": {"family": "line_address", "line": 1},
        "text": {"family": "line_address", "line": 1},
        "ipynb": {"family": "container_line", "cell_index": 0, "cell_type": "code"},
    }
    for st, loc in builtin_loc.items():
        for v in ["0.5.0", "0.6.0"]:
            r = _validate(tmp_path, f"t2b_{st}_{v}.json", _udm(st, v, [loc]))
            assert r.returncode == 0, f"{st}@{v}: rc={r.returncode} err={r.stderr}"

    r = _validate(
        tmp_path, "t2mf.json", _udm("markdown", "0.6.0", [{"line": 1}])
    )
    assert r.returncode == 1, "0.6.0 内置类型缺 family 应被拒"


def test_validate_passes_schema_ok_contract_violating_json_parse_rejects(
    tmp_path: Path,
) -> None:
    """职责边界缝隙（批次 20 契约设计行为，端到端锁定）：

    - validate 是纯 schema 校验（无 parser/注册表上下文）：手造
      smk@0.6.0 + family=page_geometry/page=1 的 JSON（family 路由自洽
      合法）→ **rc 0 [OK]**；
    - 同内容经声明 smk/line_address 但产 page_geometry 的真实插件 parse →
      rc 1 + parser_contract_mismatch + details 三要素
      （expected_locator_family / offending_element_ids / parser_name）
      + **不写盘**；
    - 诚实插件（产 line_address）对照 → parse rc 0 且 validate 其产物
      rc 0——证明拦截由声明绑定驱动，非形状歧视。
    """
    assert _MAIN_ROOT is not None
    liar_doc = _udm("smk", "0.6.0", [{"family": "page_geometry", "page": 1}])
    rv = _validate(tmp_path, "t3_liar_doc.json", liar_doc)
    assert rv.returncode == 0, f"validate 应纯 schema 放行: {rv.stderr}"
    assert "[OK]" in rv.stdout

    (tmp_path / "r2038_smk_mod.py").write_text(_SMK_PLUGIN, encoding="utf-8")
    (tmp_path / "r2038_smk_honest_mod.py").write_text(
        _SMK_PLUGIN_HONEST, encoding="utf-8"
    )
    src = tmp_path / "doc.smk"
    src.write_text("hello smk\n", encoding="utf-8")

    out = tmp_path / "liar.json"
    r = _run_cli(
        tmp_path, _MAIN_ROOT, "parse", str(src), "-o", str(out),
        "--plugin", "r2038_smk_mod", "--parser", "auto",
    )
    assert r.returncode == 1, f"rc={r.returncode}"
    assert not out.exists(), "契约违规产物不得落盘"
    payload = json.loads(r.stderr)
    err = payload["errors"][0]
    assert err["code"] == "parser_contract_mismatch"
    details = err["details"]
    assert details["expected_locator_family"] == "line_address"
    assert details["offending_element_ids"], "须点名违规 element"

    out_ok = tmp_path / "honest.json"
    r2 = _run_cli(
        tmp_path, _MAIN_ROOT, "parse", str(src), "-o", str(out_ok),
        "--plugin", "r2038_smk_honest_mod", "--parser", "auto",
    )
    assert r2.returncode == 0, f"诚实插件应通过: {r2.stderr}"
    rv2 = _run_cli(tmp_path, _MAIN_ROOT, "validate", str(out_ok))
    assert rv2.returncode == 0, rv2.stderr
    assert "[OK]" in rv2.stdout
