"""Pipeline：把 parse → chunk → validate → write 串起来。

关键不变量：
- 写 JSON 之前必须通过 Schema 校验（否则抛错，不写文件）
- 单文件失败时返回结构化 errors，不抛异常给调用方
- 业务代码不直接依赖具体 parser，通过 parser_name 字符串选工厂
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.chunkers import StructuralChunker
from app.hash import compute_file_hash
from app.models import Document, ErrorRecord
from app.parser_registry import get_parser as _registry_get_parser
from app.parsers import Parser, ParserError
from app.schema import SchemaValidationError, validate


def get_parser(name: str, image_output_dir: Path | str | None = None) -> Parser:
    """parser 名称 → 实例。委托注册表（批次 18），调用方接口不变。"""
    return _registry_get_parser(name, image_output_dir)


def process_single(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    parser_name: str = "fallback",
    max_chars: int = 800,
    write_json: bool = True,
) -> tuple[Document | None, list[ErrorRecord]]:
    """处理单个文件：parse → chunk → validate → （可选）写盘。

    返回 (Document 或 None, errors)。
    - 成功：Document 有完整 elements + chunks，errors 为空
    - 失败：Document 为 None，errors 含至少一条结构化记录

    Args:
        input_path: 输入文件
        output_path: 输出 JSON 路径（None 时不写盘）
        parser_name: 'fallback' 或 'kreuzberg'
        max_chars: 分块上限
        write_json: 是否把 Document 写到 output_path（仅当 output_path 给定时）
    """
    errors: list[ErrorRecord] = []
    input_p = Path(input_path)

    # 1. 算 source_hash
    try:
        source_hash = compute_file_hash(input_p)
    except FileNotFoundError as e:
        errors.append(
            ErrorRecord(
                code="file_not_found",
                message=str(e),
                details={"path": str(input_p)},
            )
        )
        return None, errors
    except OSError as e:
        errors.append(
            ErrorRecord(
                code="hash_io_error",
                message=f"读文件失败: {e}",
                details={"path": str(input_p), "exception_type": type(e).__name__},
            )
        )
        return None, errors

    # 2. 解析
    # 图片输出目录：若给了 output_path，自动推导为同目录的 <doc_id>/ 子目录
    image_output_dir: Path | None = None
    if output_path is not None:
        out_root = Path(output_path).parent
        # 用 source_hash 前 16 位作目录名（与 document_id 一致）
        image_output_dir = out_root / f"images-{source_hash[:16]}"
    try:
        parser = get_parser(parser_name, image_output_dir=image_output_dir)
        document = parser.parse(input_p, source_hash=source_hash)
    except ParserError as e:
        errors.append(
            ErrorRecord(
                code=e.code,
                message=e.message,
                details={"path": str(input_p), **e.details},
            )
        )
        return None, errors
    except Exception as e:
        # 兜底：未预期异常也变成结构化错误，而不是崩溃
        errors.append(
            ErrorRecord(
                code="unexpected_parser_error",
                message=f"{type(e).__name__}: {e}",
                details={"path": str(input_p), "parser_name": parser_name},
            )
        )
        return None, errors

    # 3. 分块
    try:
        chunker = StructuralChunker(max_chars=max_chars)
        document.chunks = chunker.chunk(document)
    except Exception as e:
        errors.append(
            ErrorRecord(
                code="chunker_failed",
                message=f"分块失败: {e}",
                details={"exception_type": type(e).__name__},
            )
        )
        return None, errors

    # 4. 校验（写盘前）
    # 4a. 空内容检查：elements 为空通常意味着 PDF 是扫描件或文件实际无内容，
    #     这种"技术成功但 0 element"对下游无意义，按 manifest 要求视为结构化失败。
    if not document.elements:
        errors.append(
            ErrorRecord(
                code="no_extracted_elements",
                message="解析完成但未提取到任何 element（可能为扫描件或不支持的内容）",
                details={
                    "warnings": [w.to_dict() for w in document.warnings],
                    "source_type": document.source_type,
                },
            )
        )
        return None, errors

    # 4b. Schema 校验
    try:
        validate(document.to_dict())
    except SchemaValidationError as e:
        errors.append(
            ErrorRecord(
                code="schema_validation_failed",
                message=str(e),
                details={
                    "validation_errors": e.errors[:20],  # 截断，避免 JSON 巨大
                },
            )
        )
        return None, errors

    # 5. 写盘
    if write_json and output_path is not None:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        try:
            with out_p.open("w", encoding="utf-8") as f:
                json.dump(document.to_dict(), f, ensure_ascii=False, indent=2)
        except OSError as e:
            errors.append(
                ErrorRecord(
                    code="write_failed",
                    message=f"写文件失败: {e}",
                    details={"path": str(out_p)},
                )
            )
            return None, errors

    return document, errors


def validate_only(json_path: str | Path) -> tuple[bool, str]:
    """仅校验已存在的 JSON 文件。返回 (是否通过, 简要信息)。"""
    from app.schema import validate_file

    try:
        validate_file(json_path)
        return True, "OK"
    except SchemaValidationError as e:
        return False, str(e)
    except FileNotFoundError as e:
        return False, str(e)
    except json.JSONDecodeError as e:
        return False, f"JSON 解析失败: {e}"


__all__ = ["get_parser", "process_single", "validate_only"]
