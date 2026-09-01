# BACKLOG（已知限制与未排期修复项）

> 依据：Stage 8 启动裁决（2026-08-31，会话 cf170a6f，批次 15 封口确认回复）。
> 以下 4 项在 Stage 8 期间不处理；每项影响面均限于 devset 中单个文档。

## 1. 候选 B：004-PDF 多栏题注碎字符

- 影响文档：real-04（仅 PDF，多栏布局），devset 1/10
- 现象：多栏布局下题注文字被切碎，caption 对齐计数偏差（caption GT=3）
- 根因方向：多栏栏目坐标聚类后未按栏重组阅读顺序
- 状态：backlog（Stage 8 不动）

## 2. 候选 C：002-PDF 表单域标签误判 heading

- 影响文档：real-02 PDF 侧，devset 1/10
- 现象：表单域标签（空表格单元格旁的短标签行）被误判为 heading，heading 计数 +246%
- 根因方向：表单页缺少"表单域标签"语义信号，短行+无正文字体特征的启发式误触发
- 状态：backlog（Stage 8 不动）

## 3. 候选 D：001-PDF 跨页表格拆分

- 影响文档：real-01 PDF 侧，devset 1/10
- 现象：跨页表格被按页拆分为多个 table 元素，table 计数 +300%
- 根因方向：pdfplumber 按页枚举，无跨页表格合并逻辑（需表头相似度/列对齐信号）
- 状态：backlog（Stage 8 不动）

## 4. w:tc 内 sdt（表格单元格内嵌套内容控件）

- 影响范围：批次 14 修复（w:sdt 递归扫描）覆盖 flow 内容，但表格单元格（w:tc）内的 sdt 未纳入递归路径
- 现象：w:tc 内 sdt 包裹的内容欠提取
- 声明位置：ADOPTION.md §四十八（批次 15 附注引用批次 14 边界声明）
- 状态：backlog（Stage 8 不动）

## 5. pdfplumber 底层 C 库崩溃（segfault）可能破坏批处理进程池

- 影响范围：Stage 8 批次 16 批量处理与评测并行化（multiprocessing）
- 现象：worker 内 Python 异常已全隔离（单文档失败不中断批）；但 pdfplumber 底层 C 库的原生崩溃（segfault / access violation）会导致进程池整体失效，剩余任务全部失败
- 缓解建议：批量处理前对可疑文档先单文档预测试（`app.cli parse`）
- 依据：批次 16 步骤 1 裁决（2026-08-31，会话 cf170a6f）
- 状态：已知限制（本批不修）

## 6. markdown_enhanced 的完整 YAML frontmatter 支持

- 影响范围：Stage 8 批次 18 参考插件（app/parsers/plugins/markdown_enhanced.py）
- 现象：受限解析仅支持扁平 `key: scalar`；嵌套/列表/映射值记
  `frontmatter_*_skipped` warning 后跳过，不伪装为完整 YAML
- 升级条件：需要 PyYAML 依赖（**新增主依赖须用户单独批准**，项目规则禁止未批准引入）；批准后替换 `_parse_frontmatter` 并保留降级语义
- 依据：批次 18 步骤 1 裁决第 7 条（2026-08-31，会话 6a952dc9）
- 状态：backlog

## 7. source_type 封闭枚举限制外部插件新格式

- 影响范围：Stage 8 批次 19 外部插件加载（app/plugin_loader.py）
- 现象：`schemas/document.schema.json` 的 `source_type` 为封闭枚举
  （pdf/docx/markdown/html/text/ipynb），外部插件解析新格式（如 .smk）
  只能复用枚举内取值（测试插件复用 "text"），否则 Schema 校验失败
- 升级条件：开放枚举或注册式扩展需 Schema 变更（report/schema 版本
  政策约束），须单独裁决
- 依据：批次 19 实现中实证（2026-08-31，会话 6a952dc9）
- 状态：**已解决（Stage 8 批次 20，2026-09-01）**——schema 0.6.0 受控
  开放（pattern `^[a-z][a-z0-9_]{0,31}$` + family 四值驱动 locator 形状
  + parser 声明契约 + 运行时 parser_contract_mismatch）；locator family
  集合仍封闭（新增 family = 新 locator 形状/schema 依据，需单独批次裁决）

## 7a. holdout_table_caption_first_run.py 期望版本冻结于 0.5.0

- 影响范围：Stage 6 批次 7 封存的 holdout 首跑对照脚本（scripts/）
- 现象：脚本与 samples/synthetic/holdout-table-caption/expectations.json
  的 `expected_schema_version` 冻结为 0.5.0（批次 7 时代工件）；批次 20
  起 writer 一律输出 0.6.0，对**新**产出重跑该脚本会版本失配
- 升级条件：如需对新产物重跑对照，须同步期望版本并重新封存（holdout
  纪律：已封存工件不追溯改动）；封存的历史结论不受影响
- 状态：已知限制（本批不动）

## 7b. locator family 集合封闭（无扩展机制）

- 影响范围：批次 20 契约（app/source_types.py LOCATOR_FAMILIES）
- 现象：family 仅四值（page_geometry/structural_index/line_address/
  container_line）；新文档类型必须复用现有 family 的 locator 形状
- 升级条件：新增 family 需同时定义新 locator schema 形状 + 契约表 +
  测试矩阵（批次 20 裁决 D3：单独批次处理）
- 状态：设计决定（封闭是有意的，非缺陷）

## 8. --plugin 文件路径加载

- 影响范围：Stage 8 批次 19
- 现象：--plugin 仅接受 dotted 模块名（PYTHONPATH/sys.path 提供模块），
  不支持直接传 .py 文件路径
- 升级条件：路径 → 模块名映射（需 sys.path 临时注入与命名冲突处理），
  另行裁决
- 状态：backlog

## 9. plugin_init_report_timeout 路径无自动化测试

- 影响范围：Stage 8 批次 19 批量并行受控通道（app/batch.py）
- 现象：worker 初始化回报超时（120s）走受控失败，但该路径需真实超时
  注入，未覆盖自动化测试；worker 失败/成功路径已有跨进程真实测试
- 状态：已知限制（本批不测）
