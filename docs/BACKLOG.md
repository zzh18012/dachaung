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
