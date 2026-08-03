"""pytest 公共 fixture。"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def schema_path(project_root: Path) -> Path:
    return project_root / "schemas" / "document.schema.json"


@pytest.fixture
def samples_private_dir(project_root: Path) -> Path:
    """真实样例目录。如不存在或为空，依赖它的测试应 SKIPPED。"""
    return project_root / "samples" / "private"


@pytest.fixture
def sample_pdf_path(samples_private_dir: Path) -> Path | None:
    p = samples_private_dir / "sample.pdf"
    return p if p.is_file() else None


@pytest.fixture
def sample_docx_path(samples_private_dir: Path) -> Path | None:
    p = samples_private_dir / "sample.docx"
    return p if p.is_file() else None
