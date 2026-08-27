"""开发集清单加载器。

关键不变量：
- path 字段必须是相对路径（正斜杠），拒绝绝对路径与反斜杠
- 解析后路径必须位于项目根目录内（防止 ../../../etc/passwd 之类）
- 不把本机绝对路径写入 manifest 或报告
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evaluation import MANIFEST_VERSION
from evaluation.schema import validate


class ManifestError(Exception):
    """清单加载或校验失败。"""


def _is_absolute_like(path_str: str) -> bool:
    """识别绝对路径：POSIX /foo、Windows C:\\foo、C:/foo。"""
    if not path_str:
        return False
    if path_str.startswith("/"):
        return True
    # Windows 盘符
    if len(path_str) >= 3 and path_str[1] == ":" and path_str[0].isalpha():
        if path_str[2] in ("\\", "/"):
            return True
    return False


def _has_backslash(path_str: str) -> bool:
    return "\\" in path_str


@dataclass(frozen=True)
class DocumentEntry:
    doc_id: str
    path_str: str  # 原始相对路径（正斜杠）
    resolved_path: Path  # 解析后的绝对路径（位于项目根内）
    source_type: str
    sha256: str | None
    categories: tuple[str, ...]
    paired_with: str | None
    annotation_file_str: str | None
    annotation_resolved: Path | None
    expectations: dict[str, Any] | None


@dataclass(frozen=True)
class ExpectedFailure:
    doc_id: str
    path_str: str
    resolved_path: Path
    expected_error_code: str
    source_type: str | None


@dataclass(frozen=True)
class Manifest:
    manifest_version: str
    devset_status: str
    documents: tuple[DocumentEntry, ...]
    expected_failures: tuple[ExpectedFailure, ...]
    project_root: Path

    @property
    def file_count(self) -> int:
        return len(self.documents)

    @property
    def pdf_count(self) -> int:
        return sum(1 for d in self.documents if d.source_type == "pdf")

    @property
    def docx_count(self) -> int:
        return sum(1 for d in self.documents if d.source_type == "docx")

    @property
    def content_group_count(self) -> int:
        """配对的 DOCX+PDF 视为同一内容来源；未配对的 1 个算 1 组。"""
        pair_ids: set[frozenset[str]] = set()
        unpaired = 0
        all_paired: set[str] = set()
        # 先收集所有 paired_with 引用
        for d in self.documents:
            if d.paired_with:
                pair_ids.add(frozenset([d.doc_id, d.paired_with]))
                all_paired.add(d.doc_id)
        # 验证 paired_with 是双向的；单向也算一组，避免重复计数
        seen: set[str] = set()
        groups = 0
        for pair in pair_ids:
            groups += 1
            seen.update(pair)
        for d in self.documents:
            if d.doc_id not in seen and not d.paired_with:
                unpaired += 1
        return groups + unpaired

    @property
    def categories_covered(self) -> list[str]:
        s: set[str] = set()
        for d in self.documents:
            s.update(d.categories)
        return sorted(s)


def _resolve_relative_path(
    path_str: str,
    project_root: Path,
    field_name: str,
) -> Path:
    """校验路径形式并解析为绝对路径（必须位于 project_root 内）。"""
    if not path_str:
        raise ManifestError(f"{field_name} 为空")
    if _is_absolute_like(path_str):
        raise ManifestError(
            f"{field_name} 必须是相对路径，禁止绝对路径：{path_str}"
        )
    if _has_backslash(path_str):
        raise ManifestError(
            f"{field_name} 必须使用正斜杠，禁止反斜杠：{path_str}"
        )
    resolved = (project_root / path_str).resolve()
    project_root_resolved = project_root.resolve()
    try:
        resolved.relative_to(project_root_resolved)
    except ValueError:
        raise ManifestError(
            f"{field_name} 解析后位于项目根目录之外：{path_str} → {resolved}"
        )
    return resolved


def load_manifest(
    manifest_path: Path | str,
    project_root: Path | str | None = None,
) -> Manifest:
    """加载清单：读 JSON → Schema 校验 → 路径形式校验 → 解析路径。

    Args:
        manifest_path: 清单文件路径（本机任意位置，不会写入报告）
        project_root: 项目根目录；默认为 manifest 所在仓库根（向上找 .git 或 pyproject.toml）
    """
    p = Path(manifest_path).resolve()
    if not p.is_file():
        raise ManifestError(f"清单文件不存在: {p}")

    if project_root is None:
        project_root = _detect_project_root(p)
    project_root = Path(project_root).resolve()

    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ManifestError(f"清单 JSON 解析失败: {e}") from e

    # Schema 校验（不通过则抛 EvalSchemaError，调用方决定怎么处理）
    validate(data, "manifest.schema.json")

    if data.get("manifest_version") != MANIFEST_VERSION:
        raise ManifestError(
            f"manifest_version 不兼容：清单={data.get('manifest_version')}，"
            f"代码={MANIFEST_VERSION}"
        )

    documents: list[DocumentEntry] = []
    for d in data.get("documents", []):
        resolved = _resolve_relative_path(d["path"], project_root, f"documents[{d['doc_id']}].path")
        annotation_resolved = None
        if d.get("annotation_file"):
            annotation_resolved = _resolve_relative_path(
                d["annotation_file"], project_root,
                f"documents[{d['doc_id']}].annotation_file",
            )
        exp = d.get("expectations")
        if exp and exp.get("max_silent_drop_count") is not None:
            if not exp.get("element_count_by_type"):
                raise ManifestError(
                    f"documents[{d['doc_id']}].expectations.max_silent_drop_count "
                    "声明了上限但没有 element_count_by_type，无法计算 silent_drop_count"
                )
        documents.append(
            DocumentEntry(
                doc_id=d["doc_id"],
                path_str=d["path"],
                resolved_path=resolved,
                source_type=d["source_type"],
                sha256=d.get("sha256"),
                categories=tuple(d.get("categories", [])),
                paired_with=d.get("paired_with"),
                annotation_file_str=d.get("annotation_file"),
                annotation_resolved=annotation_resolved,
                expectations=d.get("expectations"),
            )
        )

    failures: list[ExpectedFailure] = []
    for ef in data.get("expected_failures", []):
        resolved = _resolve_relative_path(
            ef["path"], project_root, f"expected_failures[{ef['doc_id']}].path"
        )
        failures.append(
            ExpectedFailure(
                doc_id=ef["doc_id"],
                path_str=ef["path"],
                resolved_path=resolved,
                expected_error_code=ef["expected_error_code"],
                source_type=ef.get("source_type"),
            )
        )

    return Manifest(
        manifest_version=data["manifest_version"],
        devset_status=data["devset_status"],
        documents=tuple(documents),
        expected_failures=tuple(failures),
        project_root=project_root,
    )


def _detect_project_root(start: Path) -> Path:
    """从 start 向上找包含 pyproject.toml 的目录。"""
    cur = start.resolve()
    if cur.is_file():
        cur = cur.parent
    for parent in [cur, *cur.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    return cur


__all__ = [
    "ManifestError",
    "Manifest",
    "DocumentEntry",
    "ExpectedFailure",
    "load_manifest",
]
