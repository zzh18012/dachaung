# 批次 25：可复现容器交付（裁决 D-A/D-B/D-G）
#
# - 两阶段（builder/runtime）共用同一 digest 锁定的 python 基础镜像；
# - PYTHON_BASE 仅允许覆盖 registry 前缀（digest 保持锁定）：CI 与默认走
#   docker.io 规范名；本地因 docker.io DNS 污染可用同 digest 镜像源构建，
#   内容寻址保证字节一致（实测 daocloud/1ms.run 双源 digest 一致）；
# - uv 从 ghcr.io digest 锁定镜像 COPY（ghcr 本机与 CI 均可达）；
# - 运行契约（裁决 D1）：非 root uid/gid 1000、只读根、ENTRYPOINT 指向
#   venv python、schema 文件必须随镜像分发（app/schema.py 运行时读取）。

ARG PYTHON_BASE=docker.io/library/python:3.12-slim@sha256:e5c9fa26ffb76e11e0f054f30dc2523a2f9693f0c36c0cf1e39b27e152d899fc
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.11@sha256:798712e57f879c5393777cbda2bb309b29fcdeb0532129d4b1c3125c5385975a

# uv 基础镜像声明为独立 stage（BuildKit 不支持 COPY --from 变量展开；
# 官方 workaround：FROM 全局 ARG，再按 stage 名引用）
FROM ${UV_IMAGE} AS uv

# ---------- builder：uv sync 产出 /app/.venv ----------
FROM ${PYTHON_BASE} AS builder
COPY --from=uv /uv /uvx /usr/local/bin/
WORKDIR /app
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
# pyproject 无 build-system（uv 虚拟项目）：sync 只装依赖，不装包自身；
# 运行期源码由 runtime 阶段直接 COPY app/ 提供（镜像布局 = .venv + 源码）。
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --python /usr/local/bin/python3

# ---------- runtime：最小运行面 ----------
FROM ${PYTHON_BASE} AS runtime
ARG GIT_REVISION=
ARG GIT_VERSION=
ARG BUILD_DATE=
# OCI 标签注入必须在构建期非空（裁决 D4）：缺 build-arg 直接构建失败，
# 不允许产出空标签镜像。
RUN test -n "$GIT_REVISION" && test -n "$GIT_VERSION" && test -n "$BUILD_DATE"

LABEL org.opencontainers.image.title="kvfs-doc-parser" \
      org.opencontainers.image.version="${GIT_VERSION}" \
      org.opencontainers.image.revision="${GIT_REVISION}" \
      org.opencontainers.image.created="${BUILD_DATE}"

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY app ./app
# app/schema.py:15 运行时读 schemas/document.schema.json（相对包根）——必须随镜像分发
COPY schemas/document.schema.json ./schemas/document.schema.json

# 非 root（uid/gid 1000，裁决 D2）；不建 home（--read-only 下无意义），HOME 指向 /tmp（tmpfs 可写）
RUN groupadd --gid 1000 app \
 && useradd --uid 1000 --gid app --no-create-home --shell /usr/sbin/nologin app \
 && chown -R app:app /app
USER app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

ENTRYPOINT ["/app/.venv/bin/python", "-m", "app.cli"]
CMD ["--help"]
