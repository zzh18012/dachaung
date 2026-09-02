"""批次 25 Phase A 静态契约测试：Dockerfile / .dockerignore / CI 工作流。

容器与 CI 属"交付面"而非运行时代码，这里用文本断言锁死裁决要点：
- D-A：两阶段基础镜像 digest 锁定（builder 与 runtime 同一 digest）；
- D2：非 root uid/gid 1000；ENTRYPOINT 指向 venv python；
- D4 修订：OCI 标签注入必须构建期非空（RUN test -n 强制）；
- 修订 1：CI 单 job 链、action 全 SHA 锁定、persist-credentials: false、
  每步 set -euo pipefail、--platform linux/amd64 显式；
- 修订 4：.dockerignore 白名单 default-deny；
- D-G：schema 文件必须随镜像分发（app/schema.py 运行时读取）。
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PYTHON_DIGEST = "sha256:e5c9fa26ffb76e11e0f054f30dc2523a2f9693f0c36c0cf1e39b27e152d899fc"
UV_DIGEST = "sha256:798712e57f879c5393777cbda2bb309b29fcdeb0532129d4b1c3125c5385975a"
CHECKOUT_SHA = "fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09"
UPLOAD_ARTIFACT_SHA = "b7c566a772e6b6bfb58ed0dc250532a479d7789f"


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


# ---------- Dockerfile ----------

def test_dockerfile_base_images_digest_pinned_both_stages():
    text = _read("Dockerfile")
    assert (
        f"ARG PYTHON_BASE=docker.io/library/python:3.12-slim@{PYTHON_DIGEST}" in text
    ), "PYTHON_BASE 默认值必须是 docker.io 规范名 + digest 锁定"
    assert f"ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.11@{UV_DIGEST}" in text
    from_lines = [ln.strip() for ln in text.splitlines() if ln.startswith("FROM ")]
    assert from_lines == [
        "FROM ${UV_IMAGE} AS uv",
        "FROM ${PYTHON_BASE} AS builder",
        "FROM ${PYTHON_BASE} AS runtime",
    ], f"FROM 结构变化: {from_lines}"
    # builder 与 runtime 必须同一 digest：两处引用同一 ARG 即唯一来源
    assert from_lines.count("FROM ${PYTHON_BASE} AS builder") == 1
    assert from_lines.count("FROM ${PYTHON_BASE} AS runtime") == 1


def test_dockerfile_nonroot_and_entrypoint_contract():
    text = _read("Dockerfile")
    assert "groupadd --gid 1000 app" in text
    assert "useradd --uid 1000 --gid app" in text
    assert "\nUSER app\n" in text
    assert 'ENTRYPOINT ["/app/.venv/bin/python", "-m", "app.cli"]' in text
    assert 'CMD ["--help"]' in text


def test_dockerfile_buildarg_labels_enforced_nonempty():
    text = _read("Dockerfile")
    assert 'RUN test -n "$GIT_REVISION" && test -n "$GIT_VERSION" && test -n "$BUILD_DATE"' in text
    for key in (
        "org.opencontainers.image.title",
        "org.opencontainers.image.version",
        "org.opencontainers.image.revision",
        "org.opencontainers.image.created",
    ):
        assert key in text, key
    # 标签注入用的是 build-arg（非字面量），保证每次构建真实注入
    assert 'org.opencontainers.image.version="${GIT_VERSION}"' in text
    assert 'org.opencontainers.image.revision="${GIT_REVISION}"' in text
    assert 'org.opencontainers.image.created="${BUILD_DATE}"' in text


def test_dockerfile_runtime_layout_and_schema_shipping():
    text = _read("Dockerfile")
    assert "COPY --from=builder /app/.venv /app/.venv" in text
    assert "COPY app ./app" in text
    # D-G：app/schema.py 运行时读 schemas/document.schema.json（相对包根）
    assert "COPY schemas/document.schema.json ./schemas/document.schema.json" in text
    assert "uv sync --locked --no-dev" in text
    assert "COPY --from=uv /uv /uvx /usr/local/bin/" in text
    assert "PYTHONDONTWRITEBYTECODE=1" in text
    assert "PYTHONUNBUFFERED=1" in text
    assert "HOME=/tmp" in text


def test_dockerfile_no_package_managers_or_pip():
    text = _read("Dockerfile")
    assert "pip install" not in text
    assert "apt-get" not in text
    assert "apk add" not in text


# ---------- .dockerignore（修订 4：白名单 default-deny） ----------

def test_dockerignore_whitelist_default_deny():
    lines = [
        ln.strip()
        for ln in _read(".dockerignore").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    assert lines[0] == "*", "第一条模式必须是 *（default-deny）"
    whitelist = {ln for ln in lines if ln.startswith("!")}
    assert whitelist == {
        "!Dockerfile",
        "!.dockerignore",
        "!pyproject.toml",
        "!uv.lock",
        "!app",
        "!app/**",
        "!schemas",
        "!schemas/document.schema.json",
    }, f"白名单集合变化: {sorted(whitelist)}"
    assert "**/__pycache__" in lines
    assert "**/*.pyc" in lines


def test_dockerignore_no_sensitive_or_dev_paths():
    whitelist = [
        ln.strip() for ln in _read(".dockerignore").splitlines()
        if ln.strip().startswith("!")
    ]
    joined = "\n".join(whitelist)
    for forbidden in (
        "!tests", "!evaluation", "!docs", "!samples", "!outputs",
        "!scripts", "!.github", "!ADOPTION.md", "!README.md", "!CLAUDE.md",
    ):
        assert forbidden not in joined, forbidden


def test_dockerfile_copy_sources_all_within_whitelist():
    """Dockerfile 的每个 COPY 源路径都必须被 .dockerignore 白名单覆盖。"""
    text = _read("Dockerfile")
    sources = re.findall(r"^COPY\s+(?!--from)(\S+)", text, flags=re.MULTILINE)
    assert set(sources) <= {"pyproject.toml", "uv.lock", "app", "schemas/document.schema.json"}


# ---------- CI 工作流（修订 1 + 修订 3） ----------

def test_ci_single_job_and_actions_sha_pinned():
    text = _read(".github/workflows/ci.yml")
    uses = re.findall(r"uses:\s*(\S+)", text)
    assert set(uses) == {
        f"actions/checkout@{CHECKOUT_SHA}",
        f"actions/upload-artifact@{UPLOAD_ARTIFACT_SHA}",
    }, f"action 集合或锁定变化: {uses}"
    assert len(re.findall(r"^jobs:", text, flags=re.MULTILINE)) == 1
    assert "container-delivery:" in text
    assert "persist-credentials: false" in text
    assert "permissions:" in text
    assert "contents: read" in text


def test_ci_hardening_and_chain_order():
    text = _read(".github/workflows/ci.yml")
    for required in (
        "set -euo pipefail",
        "--platform linux/amd64",
        "--build-arg GIT_REVISION=",
        "--build-arg GIT_VERSION=",
        "--build-arg BUILD_DATE=",
        "scripts/container_verify.py --image kvfs-doc-parser:ci",
        "docker rmi kvfs-doc-parser:ci",
        "scripts/container_verify.py --artifact",
        "if-no-files-found: error",
        "uv sync --locked",
        ".venv/bin/python -m pytest",
    ):
        assert required in text, required
    # 链序：verify --image 必须在 rmi 之前，--artifact 必须在 rmi 之后
    assert text.index("container_verify.py --image") < text.index("docker rmi")
    assert text.index("docker rmi") < text.index("container_verify.py --artifact")
    # 每个 run 步骤都有 set -euo pipefail
    run_blocks = re.findall(r"run:\s*\|\s*\n(.*?)(?=\n\s*- name:|\n\s*uses:|\Z)", text, flags=re.DOTALL)
    assert len(run_blocks) >= 8
    for block in run_blocks:
        assert "set -euo pipefail" in block, block[:120]


def test_ci_triggers_and_digest_crosscheck():
    text = _read(".github/workflows/ci.yml")
    assert 'branches: [main, "integration/**"]' in text
    dockerfile = _read("Dockerfile")
    assert PYTHON_DIGEST in dockerfile
    assert UV_DIGEST in dockerfile
