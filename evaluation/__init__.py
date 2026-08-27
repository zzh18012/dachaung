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
- v1.1：text_preservation 改为非空白字符的有序序列对比（口径 D）。
  旧 baseline 的 text_preservation_equal / precision / recall 与新 baseline
  不可横向比较。其它指标语义未变。
- v1.2（当前）：expectation 契约可执行——runner 实际消费
  required_markers（自 schema 起声明但此前从未求值）并新增
  forbidden_markers / must_not_error_codes / max_silent_drop_count；
  summary 新增 expectation_checks 分节；manifest/report schema 的
  source_type 枚举扩至 markdown/html/text/ipynb（additive）。
  旧 manifest（1.0）与旧报告（1.1）在扩展后 schema 下仍然有效。
"""

EVALUATOR_VERSION = "1.2"
REPORT_VERSION = "1.2"
ANNOTATION_VERSION = "1.0"
MANIFEST_VERSION = "1.0"

__all__ = [
    "EVALUATOR_VERSION",
    "REPORT_VERSION",
    "ANNOTATION_VERSION",
    "MANIFEST_VERSION",
]
