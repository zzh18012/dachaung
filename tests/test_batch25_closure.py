"""批次 25 Phase B 收口测试：文档面与台账契约（GPT Phase B 范围确认）。

Phase A 的容器/CI/脚本契约已由 test_container_static_contracts.py 与
test_container_verify_logic.py 锁定；此处封口 Phase B 交付的文档与记录：
- README §3.6 部署 runbook（制品≠部署边界、校验和先行、受限运行、
  镜像源前缀仅限本地验证的供应链口径）；
- CLAUDE.md 批次 25 节 + "不做 Docker"范围修订；
- ADOPTION §六十四：三次 CI run 沿革、两项既有缺陷修复提交、
  成功 run、制品名与 SHA-256、Phase B 零行为改动边界。
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ARTIFACT_NAME = "kvfs-doc-parser_0e5d22b8bddc-img.tar.gz"
ARTIFACT_SHA256 = (
    "8c850fde8594b0b74a8b2836fb18d1a96403dc33eba7a81fc6b2856de5e63215"
)
SUCCESS_RUN = "33587036477"
FAILED_RUNS = ("33585538869", "33585903380")
FIX_COMMITS = ("1ab2573", "8bc10c9", "0e5d22b")


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _squeeze(name: str) -> str:
    """删除全部空白：中文短语断言不受 Markdown 换行影响。"""
    return "".join(_read(name).split())


def _sq(phrase: str) -> str:
    return "".join(phrase.split())


# ---------- README §3.6 ----------

def test_readme_runbook_section_present_with_boundary():
    text = _read("README.md")
    assert "### 3.6 容器交付与部署验证（Stage 8 批次 25）" in text
    assert "制品交付 ≠ 部署" in text


def test_readme_runbook_operational_steps():
    text = _read("README.md")
    assert "sha256sum -c" in text
    assert "scripts/container_verify.py" in text
    assert "--artifact" in text
    # 受限运行示例三要素
    assert "--read-only" in text
    assert "--network none" in text
    assert "--tmpfs /tmp:rw,noexec,nosuid" in text


def test_readme_supply_chain_boundary_statement():
    """偏差 A 追认条件：镜像源覆盖仅限受限网络本地验证，非官方路径。"""
    text = _squeeze("README.md")
    assert _sq("不构成官方可复现交付路径或供应链替代") in text
    assert _sq("docker.io 规范名 + digest") in text


# ---------- CLAUDE.md ----------

def test_claudemd_batch25_section_and_scope_revision():
    text = _read("CLAUDE.md")
    assert "## 容器交付与可复现构建（Stage 8 批次 25）" in text
    # 范围修订：不做清单不再包含裸 Docker
    assert "内核代码 / FUSE / Docker / 数据库" not in text
    assert "容器交付已于 Stage 8 批次 25 纳入" in text


def test_claudemd_records_spawn_defect_fix_and_commands():
    text = _read("CLAUDE.md")
    assert 'get_context("spawn")' in text
    assert "docker build --platform linux/amd64" in text
    assert "container_verify.py --image" in text
    assert "container_verify.py --artifact" in text


# ---------- ADOPTION §六十四 ----------

def test_adoption_batch25_record_present_with_ci_history():
    text = _read("ADOPTION.md")
    assert "六十四、批次 25 执行记录" in text
    for run_id in FAILED_RUNS:
        assert run_id in text, run_id
    assert SUCCESS_RUN in text
    assert "33587036477：成功" in text


def test_adoption_records_artifact_and_fix_commits():
    text = _read("ADOPTION.md")
    assert ARTIFACT_NAME in text
    assert ARTIFACT_SHA256 in text
    for sha in FIX_COMMITS:
        assert sha in text, sha
    # E 项缺陷性质按追认条件标注
    assert "批次 25 CI 暴露的既有缺陷" in text


def test_adoption_records_ratified_deviation_boundary():
    text = _squeeze("ADOPTION.md")
    assert _sq("不构成官方可复现交付路径或供应链替代") in text  # 台账同样登记供应链口径
    assert _sq("Phase B 未改动 Phase A 的容器/CI/解析行为") in text


# ---------- 跨文件一致性 ----------

def test_phase_a_files_still_locked_by_static_contracts():
    """Phase B 只动文档：Phase A 契约锚点仍在（细节由静态契约测试全量锁定）。"""
    dockerfile = _read("Dockerfile")
    assert dockerfile.startswith(
        "# 批次 25：可复现容器交付（裁决 D-A/D-B/D-G）"
    )
    adoption = _read("ADOPTION.md")
    # 台账登记的 digest 与 Dockerfile 默认值同源
    digest = "sha256:e5c9fa26ffb76e11e0f054f30dc2523a2f9693f0c36c0cf1e39b27e152d899fc"
    assert digest in dockerfile
    assert digest.replace("sha256:", "") in adoption.replace("\n", "")
