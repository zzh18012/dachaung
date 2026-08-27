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
- v1.2：expectation 契约可执行——runner 实际消费
  required_markers（自 schema 起声明但此前从未求值）并新增
  forbidden_markers / must_not_error_codes / max_silent_drop_count；
  summary 新增 expectation_checks 分节。版本语义为精确快照：
  manifest 1.1 才允许新格式（markdown/html/text/ipynb）与新 expectation 键，
  1.0 清单继续按旧契约校验；报告含新分节必须标 report_version 1.2，
  1.1 报告保持旧结构。UDM 侧 document.schema_version 同步改为
  0.1.0（旧形状）/ 0.2.0（新类型或 source_spans）精确快照，
  旧 PDF/DOCX 输出继续生成 0.1.0，与冻结基线字节一致。
- v1.3：评测 CLI 可运行 markdown manifest（--parser choices 补齐；
  自跑线评测从未接 markdown，属搬运线补齐）。能力封口：1.2 evaluator
  无法运行 markdown manifest，同版本不同能力损害复现，故升 1.3 封存
  Markdown 候选（ChatGPT 5.6 Sol 2026-08-27 指示）。
  report_version 保持 1.2（报告结构未变）。
- v1.4：评测 CLI 可运行 html manifest（能力封口同上，
  ChatGPT 5.6 Sol 2026-08-27 指示）。report_version 保持 1.2。
- v1.5（当前）：评测 CLI 新增 --parser auto（混合 manifest 单次调度），
  仅按 manifest 的 source_type 解析 parser（pdf/docx→fallback、
  markdown→markdown、html→html），不按扩展名猜测；显式 --parser
  旧行为不变。报告 per_doc 新增 parser_used（复现不依赖隐式映射），
  按 v1.2 确立的精确快照政策，含新字段的报告必须标 report_version 1.3，
  1.1/1.2 报告保持旧结构（schema 条件分支互斥）。
  auto 模式下 provenance.parser_version 为 null（多 parser 并存，
  单值会误导）（ChatGPT 5.6 Sol 2026-08-27 指示）。
"""

EVALUATOR_VERSION = "1.5"
REPORT_VERSION = "1.3"
ANNOTATION_VERSION = "1.0"
MANIFEST_VERSION = "1.1"
MANIFEST_VERSIONS_SUPPORTED = ("1.0", "1.1")

__all__ = [
    "EVALUATOR_VERSION",
    "REPORT_VERSION",
    "ANNOTATION_VERSION",
    "MANIFEST_VERSION",
]
