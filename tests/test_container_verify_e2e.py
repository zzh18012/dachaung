"""批次 25 Phase A：容器 e2e（docker-gated，真实构建 + 真实 CLI）。

纪律：
- Docker daemon 不可用 → 整模块 SKIPPED（CI 提供可执行证据通道）；
- 本地 docker.io 规范名不可达（DNS 污染实证）时构建步骤 SKIPPED——
  Dockerfile 默认值保持 docker.io 规范名 + digest 锁定，不以测试放宽契约；
  本地同 digest 镜像源手工验证路径见 ADOPTION 批次 25 记录。
- 构建失败但非 registry 解析问题 → 直接失败（不静默跳过）。
"""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TAG = "kvfs-doc-parser:b25e2e"

_RESOLUTION_FAILURE_MARKERS = (
    "failed to resolve reference",
    "registry-1.docker.io",
    "failed to do request",
)


def _run(cmd: list[str], timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout,
    )


def _daemon_available() -> bool:
    try:
        return _run(["docker", "version", "--format", "{{.Server.Version}}"],
                    timeout=60).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


pytestmark = pytest.mark.skipif(
    not _daemon_available(),
    reason="Docker daemon 不可用：容器 e2e 证据由 CI 提供（裁决 D-E）",
)


@pytest.fixture(scope="session")
def built_image() -> str:
    r = _run([
        "docker", "build", "--platform", "linux/amd64",
        "--build-arg", "GIT_REVISION=e2e-test",
        "--build-arg", "GIT_VERSION=0.1.0-e2e",
        "--build-arg", "BUILD_DATE=2026-09-02T00:00:00Z",
        "-t", TAG, str(ROOT),
    ], timeout=1200)
    if r.returncode != 0:
        err = (r.stderr or r.stdout or "")
        if any(m in err for m in _RESOLUTION_FAILURE_MARKERS):
            pytest.skip(
                "docker.io 规范名本地不可达（DNS 污染）：CI 为 canonical "
                "构建证据通道；本地同 digest 镜像源验证记录见 ADOPTION"
            )
        pytest.fail(f"docker build 失败（非 registry 解析问题）:\n{err[-2000:]}")
    return TAG


def test_entrypoint_help_contract(built_image):
    r = _run(["docker", "run", "--rm", built_image, "--help"], timeout=180)
    assert r.returncode == 0
    for sub in ("parse", "validate", "batch-parse", "list-parsers",
                "explain-parser", "audit-parsers", "inspect-parser"):
        assert sub in r.stdout, sub


def test_image_config_contract(built_image):
    r = _run(["docker", "image", "inspect", built_image], timeout=120)
    assert r.returncode == 0
    cfg = json.loads(r.stdout)[0]["Config"]
    assert cfg["User"] == "app"
    assert cfg["Entrypoint"] == ["/app/.venv/bin/python", "-m", "app.cli"]
    assert cfg["Cmd"] == ["--help"]
    labels = cfg["Labels"] or {}
    for key in (
        "org.opencontainers.image.title",
        "org.opencontainers.image.version",
        "org.opencontainers.image.revision",
        "org.opencontainers.image.created",
    ):
        assert isinstance(labels.get(key), str) and labels[key].strip(), key
    assert labels["org.opencontainers.image.revision"] == "e2e-test"


def test_full_verify_script_image_mode(built_image):
    r = _run([sys.executable, str(ROOT / "scripts" / "container_verify.py"),
              "--image", built_image], timeout=1200)
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    summary = json.loads(r.stdout)
    assert summary["result"] == "PASS"
    assert summary["checks"]["image_contract"] == "PASS"
    assert summary["detail"]["container_uid"] == "1000"
    assert summary["detail"]["input_ro_probe_rc"] == 0
    for name, info in summary["detail"]["files"].items():
        assert info["status"] == "match", (name, info)
        assert info["chunk_count"] >= 1


def test_artifact_roundtrip_full_load_path(built_image, tmp_path):
    """docker save → gzip → sha256 边车 → rmi → --artifact（校验和先行 + load）。"""
    plain = tmp_path / "img.tar"
    gz = tmp_path / "kvfs-doc-parser_e2e-img.tar.gz"
    r = _run(["docker", "save", "-o", str(plain), built_image], timeout=900)
    assert r.returncode == 0, r.stderr[-1000:]
    with open(plain, "rb") as f_in, gzip.open(gz, "wb") as f_out:
        f_out.writelines(iter(lambda: f_in.read(1 << 20), b""))
    digest = hashlib.sha256(gz.read_bytes()).hexdigest()
    (tmp_path / "kvfs-doc-parser_e2e-img.tar.gz.sha256").write_text(
        f"{digest}  kvfs-doc-parser_e2e-img.tar.gz\n", encoding="utf-8")
    r = _run(["docker", "rmi", built_image], timeout=180)
    assert r.returncode == 0, r.stderr[-500:]
    try:
        v = _run([sys.executable, str(ROOT / "scripts" / "container_verify.py"),
                  "--artifact", str(gz)], timeout=1800)
        assert v.returncode == 0, (v.stdout + v.stderr)[-3000:]
        assert json.loads(v.stdout)["result"] == "PASS"
    finally:
        # 制品验证会把镜像 load 回来；尽力清理，失败不影响结论
        _run(["docker", "rmi", "-f", built_image], timeout=180)
