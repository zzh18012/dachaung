"""评测包：开发集清单、自动指标、人工标注指标、报告装配。

设计原则：
- 不依赖任何 app/* 之外的库（jsonschema 已在 Stage 1 引入）
- 不修改 parser / chunker / pipeline
- 缺数据时填 null + reason，不伪造
- 比例指标分母为 0 时返回 null + reason，不返回 1.0
- 计时只记 total，parse/chunk 在本阶段未插桩（reason: not_instrumented）
"""

EVALUATOR_VERSION = "1.0"
REPORT_VERSION = "1.0"
ANNOTATION_VERSION = "1.0"
MANIFEST_VERSION = "1.0"

__all__ = [
    "EVALUATOR_VERSION",
    "REPORT_VERSION",
    "ANNOTATION_VERSION",
    "MANIFEST_VERSION",
]
