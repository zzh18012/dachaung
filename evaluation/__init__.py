"""评测包：开发集清单、自动指标、人工标注指标、报告装配。

设计原则：
- 不依赖任何 app/* 之外的库（jsonschema 已在 Stage 1 引入）
- 不修改 parser / chunker / pipeline
- 缺数据时填 null + reason，不伪造
- 比例指标分母为 0 时返回 null + reason，不返回 1.0
- 计时只记 total，parse/chunk 在本阶段未插桩（reason: not_instrumented）

版本历史：
- v1.0（初始）：text_preservation 用 ' '.join 重建全文 + normalize_text 比对；
  对 chunker 在词内硬切产生的额外空格误报为不等于。
- v1.1（当前）：text_preservation 改为非空白字符的有序序列对比（口径 D）。
  旧 baseline 的 text_preservation_equal / precision / recall 与新 baseline
  不可横向比较。其它指标语义未变。
"""

EVALUATOR_VERSION = "1.1"
REPORT_VERSION = "1.1"
ANNOTATION_VERSION = "1.0"
MANIFEST_VERSION = "1.0"

__all__ = [
    "EVALUATOR_VERSION",
    "REPORT_VERSION",
    "ANNOTATION_VERSION",
    "MANIFEST_VERSION",
]
