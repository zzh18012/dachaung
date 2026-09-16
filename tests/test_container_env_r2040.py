"""R2040：container_verify.py CLI 退出码信封 + 校验和先于 docker load 排序证明。

被测 = main worktree（`git worktree list --porcelain` 动态定位 branch refs/heads/main，
零硬编码路径；缺 main / 缺其 venv python / 缺被测脚本 → 显式 SKIP）。真实子进程通道：
main venv `python.exe scripts/container_verify.py`，子进程 env 恒带
PYTHONDONTWRITEBYTECODE=1 + PYTHONIOENCODING=utf-8（main 只读纪律）。子例用函数内
循环（加测口径 = 3 个测试函数，锚 +3，与 R2038/R2039 同法）。

锁面（探针 outputs/autonomous/probe_container_env_r2040.py 实证，15 成立/1 观察/1 缺陷候选）：
1. argparse 信封 rc 2（无参 / --image+--artifact 互斥同给 / 未知 flag）+ --help rc 0
   ——发生在 daemon 预检之前，无 docker 依赖；
2. rc 3 daemon 不可达（DOCKER_HOST 指向不存在 socket，npipe/tcp 双形态，仅子进程 env 内
   生效）且 **先于** 制品存在性/校验和检查（排序证明上半：坏 daemon + 缺制品 → 3 非 4）；
3. rc 4/5 信封 + 排序证明下半（docker-gated，daemon 不可用显式 SKIP，同 main e2e D-E 纪律）：
   缺制品/制品是目录 → 4 artifact_missing；边车缺 → 4 artifact_load「读取」；
   边车不匹配 → 4「校验和不符」（该报文只在 load 之前产生 → load 未被尝试）；
   好校验和 + 垃圾 gzip → 5「docker load 失败」（checksum 已过、死在 load）；
   --image 假 tag → 5 image_contract。
不锁（如实记录非伪造）：rc 6 信封（EXIT_RUN 死常量缺陷候选，main 无返回路径，E14）；
rc 7 需语义对照失败（需故意错误镜像，构建超出本轮边界）。
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

AUTO_ROOT = Path(__file__).resolve().parents[1]

BOGUS_NPIPE = "npipe:////./pipe/r2040-definitely-not-a-docker-engine"
BOGUS_TCP = "tcp://127.0.0.1:1"


def _locate_main() -> Path | None:
    try:
        r = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(AUTO_ROOT), timeout=60,
        )
        r.check_returncode()
    except (OSError, subprocess.SubprocessError):
        return None
    cur: dict[str, str] = {}
    for line in r.stdout.splitlines():
        if not line:
            if cur.get("branch") == "refs/heads/main":
                p = Path(cur["worktree"])
                return p if p.is_dir() else None
            cur = {}
            continue
        k, _, v = line.partition(" ")
        cur[k] = v
    if cur.get("branch") == "refs/heads/main":
        p = Path(cur["worktree"])
        return p if p.is_dir() else None
    return None


MAIN = _locate_main()
_missing_reason = "main worktree（branch refs/heads/main）不可定位"

PY = None
SCRIPT = None
if MAIN is not None:
    _py = MAIN / ".venv" / "Scripts" / "python.exe"
    _sc = MAIN / "scripts" / "container_verify.py"
    if not _py.is_file():
        _missing_reason = f"main venv python 缺失: {_py}"
    elif not _sc.is_file():
        _missing_reason = f"被测脚本缺失: {_sc}"
    else:
        PY, SCRIPT = _py, _sc

pytestmark = pytest.mark.skipif(
    PY is None or SCRIPT is None, reason=f"被测目标不可用：{_missing_reason}"
)

DOCKER_CLI = shutil.which("docker") is not None


def _run_verify(args: list[str], docker_host: str | None = None,
                timeout: int = 300) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if docker_host is not None:
        env["DOCKER_HOST"] = docker_host
    return subprocess.run(
        [str(PY), str(SCRIPT), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env, timeout=timeout,
    )


def _json_of(out: str) -> dict:
    m = re.search(r"\{.*\}", out, flags=re.DOTALL)
    assert m, f"stdout 无 JSON 信封: {out[:200]!r}"
    return json.loads(m.group(0))


def _daemon_available() -> bool:
    if not DOCKER_CLI:
        return False
    try:
        return subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True, text=True, timeout=60,
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def test_argparse_usage_envelope_rc2_and_help_rc0():
    """信封 1：argparse rc 2 三形态 + --help rc 0（全部先于 daemon 预检，无 docker 依赖）。"""
    for args in ([], ["--image", "a:1", "--artifact", "b.tar.gz"],
                 ["--no-such-flag"]):
        r = _run_verify(args)
        assert r.returncode == 2, (args, (r.stdout + r.stderr)[-500:])
        assert "usage:" in r.stderr, args
        assert '"result"' not in r.stdout, "argparse 用法错误不得产出 JSON 信封"
    r = _run_verify(["--help"])
    assert r.returncode == 0
    assert "--image" in r.stdout and "--artifact" in r.stdout


@pytest.mark.skipif(not DOCKER_CLI, reason="docker CLI 缺失：rc 3 信封依赖 docker 子进程")
def test_daemon_unreachable_rc3_and_precedes_artifact_checks():
    """信封 2：rc 3 双形态 + 排序上半（daemon 预检先于制品存在性/校验和：坏 daemon + 缺制品 → 3 非 4）。"""
    for host in (BOGUS_NPIPE, BOGUS_TCP):
        r = _run_verify(["--image", "some-image:tag"], docker_host=host)
        assert r.returncode == 3, (host, (r.stdout + r.stderr)[-500:])
        obj = _json_of(r.stdout)
        assert obj["result"] == "FAIL"
        assert obj["stage"] == "daemon_preflight", (host, obj)
    missing = AUTO_ROOT / "outputs" / "autonomous" / "_r2040_no_such_artifact.tar.gz"
    r = _run_verify(["--artifact", str(missing)], docker_host=BOGUS_TCP)
    assert r.returncode == 3, (r.stdout + r.stderr)[-500:]
    assert _json_of(r.stdout)["stage"] == "daemon_preflight"


@pytest.mark.skipif(
    not _daemon_available(),
    reason="Docker daemon 不可用：rc 4/5 信封为 docker-gated（同 main e2e D-E 纪律）",
)
def test_checksum_before_load_ordering_and_rc4_rc5(tmp_path):
    """信封 3：rc 4/5 全链 + 排序下半（同一 stage 下错误文本区分"未到 load"与"死在 load"）。"""
    # (a) 制品文件不存在 → rc 4 artifact_missing（daemon 已过）
    r = _run_verify(["--artifact", str(tmp_path / "missing.tar.gz")])
    assert r.returncode == 4
    obj = _json_of(r.stdout)
    assert obj["stage"] == "artifact_missing"

    # (a') 制品路径是目录 → 同 rc 4 artifact_missing
    adir = tmp_path / "adir.tar.gz"
    adir.mkdir()
    r = _run_verify(["--artifact", str(adir)])
    assert r.returncode == 4
    assert _json_of(r.stdout)["stage"] == "artifact_missing"

    # (b) 制品在、边车缺 → rc 4 artifact_load「读取 sha256 边车失败」
    art_noside = tmp_path / "img_noside.tar.gz"
    art_noside.write_bytes(b"r2040-payload-noside")
    r = _run_verify(["--artifact", str(art_noside)])
    assert r.returncode == 4
    obj = _json_of(r.stdout)
    assert obj["stage"] == "artifact_load"
    assert "读取" in obj["error"]

    # (c) 边车不匹配 → rc 4「校验和不符」：该报文只在 docker load 之前产生 → load 未被尝试
    art_bad = tmp_path / "img_badsum.tar.gz"
    art_bad.write_bytes(b"r2040-payload-badsum")
    (tmp_path / "img_badsum.tar.gz.sha256").write_text("0" * 64, encoding="utf-8")
    r = _run_verify(["--artifact", str(art_bad)])
    assert r.returncode == 4
    obj = _json_of(r.stdout)
    assert obj["stage"] == "artifact_load"
    assert "校验和不符" in obj["error"]

    # (d) 好校验和 + 垃圾 gzip → 过 checksum、死在 docker load → rc 5
    art_garbage = tmp_path / "img_garbage.tar.gz"
    art_garbage.write_bytes(gzip.compress(b"r2040-garbage-not-a-tarball" * 32))
    digest = hashlib.sha256(art_garbage.read_bytes()).hexdigest()
    (tmp_path / "img_garbage.tar.gz.sha256").write_text(
        f"{digest}  img_garbage.tar.gz\n", encoding="utf-8")
    r = _run_verify(["--artifact", str(art_garbage)], timeout=600)
    assert r.returncode == 5, (r.stdout + r.stderr)[-500:]
    obj = _json_of(r.stdout)
    assert obj["stage"] == "artifact_load"
    assert "docker load" in obj["error"]
    assert "校验和" not in obj["error"], "checksum 已通过，不得同时报校验和错误"

    # (e) --image 假 tag → rc 5 image_contract（镜像契约检查失败信封）
    r = _run_verify(["--image", "r2040-no-such-image:absent"])
    assert r.returncode == 5
    assert _json_of(r.stdout)["stage"] == "image_contract"
