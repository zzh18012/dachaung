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
- 现象（原记录）：跨页表格被按页拆分为多个 table 元素，table 计数 +300%
- 状态：**已处理（Stage 10 批次 4，2026-09-12，r36 授权）**——保守跨页
  合并已实现（相邻页 + 列网格逐边 |Δ|≤2pt + 唯一连续性证据：重复表头
  或断版位置分区；证据不足一律不合并；详见 CLAUDE.md 批次 4 节）
- **诊断更正（2026-09-12 实证）**：real-01 的 +300%（DOCX 1 表 vs
  PDF 4 表）根因**不是**跨页拆分——修订历史表始终完整在 p2 单页，
  另 3 个"表"是 p6/p17/p17 的高亮/提示框被 `find_tables()` 误检为
  2 行 ×1 列单柱表（假阳性）。批次 4 落地后 real-01 对照：表格数
  4→4、合并 0 次，跨页拆分在该文档无实例；合并能力由合成夹具
  （tests/test_pdf_cross_page_tables.py）验证
- 遗留：**单柱/单格假阳性表误检**（real-01 +300% 的真实根因）——
  **裁定方案 0 不修（r40，2026-09-12），候选挂起**：只读调查
  （outputs/false_positive_investigation.txt，材料在搬运线 worktree）
  证明真 (2,1) 单列表（real-02 DOCX 实例）与假 (2,1) 框同形并存，
  纯形状过滤不可精确；min-cols≥2 会误删未来真实 PDF 单列表，文本
  启发式违反保守"宁缺勿猜"纪律，均不实施。现有 4 个假阳性
  （real-01 ×3 + real-04 ×1）作为已知限制记录

## 3a. real-02 PDF 表格欠检测（独立方向，r40 另立，未立项）

- 现象：real-02 DOCX 15 个真表（含 5 个单列表）vs PDF 侧
  `find_tables()` 仅检出 12 个多柱表——单列表在 PDF 无线框，
  线策略检测天然不可见
- 与 §3 假阳性候选严格分离（r40 裁定不并入）；性质=欠检测非误检，
  根因方向=无线框表格检测（text 策略），工作量大且误检风险高
- 状态：挂起（未立项，需单独授权）

## 4. w:tc 内 sdt（表格单元格内嵌套内容控件）

- 影响范围：批次 14 修复（w:sdt 递归扫描）覆盖 flow 内容，但表格单元格（w:tc）内的 sdt 未纳入递归路径
- 现象：w:tc 内 sdt 包裹的内容欠提取
- 声明位置：ADOPTION.md §四十八（批次 15 附注引用批次 14 边界声明）
- 状态：**已处理（Stage 10 批次 3，2026-09-11）**——`_cell_text` 无 sdt
  后代走 python-docx 原生 `cell.text`（逐字节零变化），有 sdt 走
  `_iter_cell_paragraphs` 文档序递归（保序、不重复提取、嵌套 sdt 递归）。
  已知边界：嵌套 w:tbl 不下钻（其内容在既有管线中本就不进 cell.text）。
  旧 devset 真实命中对照（real-01/02/03/05 四个 DOCX，XML 精确扫描）：
  **零命中**——该缺陷在现有语料中无真实实例，修复价值为合成夹具
  验证的防御性覆盖

## 5. pdfplumber 底层 C 库崩溃（segfault）可能破坏批处理进程池

- 影响范围：Stage 8 批次 16 批量处理与评测并行化（multiprocessing）
- 现象：worker 内 Python 异常已全隔离（单文档失败不中断批）；但 pdfplumber 底层 C 库的原生崩溃（segfault / access violation）会导致进程池整体失效，剩余任务全部失败
- 缓解建议：批量处理前对可疑文档先单文档预测试（`app.cli parse`）
- 依据：批次 16 步骤 1 裁决（2026-08-31，会话 cf170a6f）
- 状态：**已处理（Stage 10 批次 2 首项，2026-09-11）**——`.pdf` 输入在一次性
  subprocess 子进程内解析（`app/process_isolation.py`），原生崩溃由父侧按
  退出码捕获并转为结构化错误 `parser_process_crashed`（无 traceback，
  exitcode 入 message），进程池与批次继续；成功路径输出与隔离前逐字节
  一致。已知边界：仅按 `.pdf` 后缀隔离（其他格式纯 Python 路径不付
  spawn 代价）；C 库死循环（挂起而非崩溃）行为不变；单文件
  `app.cli parse` 仍进程内执行；evaluation 的 expected_failures 通道
  （少量已知失败文档）仍进程内执行
- 设计说明：不用 multiprocessing.Process——Pool worker 是 daemonic
  进程，禁止再派生 mp 子进程（`Process.start()` 直接 AssertionError），
  mp 方案恰在要保护的并行路径上不可用；subprocess 无此限制

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
- 状态：**已处理（Stage 10 批次 5，2026-09-12，r43 授权）**——
  `app/plugin_loader.py` 路径分支：判定（含分隔符或 .py 后缀）/
  确定性解析（resolve 后必须为已存在 .py 文件且 stem 合法标识符）/
  命名冲突规则（sys.modules 同文件幂等、异文件或身份不可证 →
  `plugin_path_conflict`，含 stdlib shadow 防护）/ sys.path 末尾
  append + try/finally 恢复（不污染后续解析与 worker 状态）；错误码
  新增 `plugin_path_not_found` / `plugin_path_invalid` /
  `plugin_path_conflict`；dotted 行为逐字节不变（详见 CLAUDE.md
  批次 5 节与 tests/test_plugin_path_loading.py）

## 9. plugin_init_report_timeout 路径无自动化测试

- 影响范围：Stage 8 批次 19 批量并行受控通道（app/batch.py）
- 现象：worker 初始化回报超时（120s）走受控失败，但该路径需真实超时
  注入，未覆盖自动化测试；worker 失败/成功路径已有跨进程真实测试
- 状态：已知限制（本批不测）
