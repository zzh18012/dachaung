# BACKLOG（已知限制与未排期修复项）

> 依据：Stage 8 启动裁决（2026-08-31，会话 cf170a6f，批次 15 封口确认回复）。
> 以下 4 项在 Stage 8 期间不处理；每项影响面均限于 devset 中单个文档。

## 1. 候选 B：004-PDF 多栏题注碎字符

- 影响文档：real-04（仅 PDF，多栏布局），devset 1/10
- 现象：多栏布局下题注文字被切碎，caption 对齐计数偏差（caption GT=3）
- 根因方向：多栏栏目坐标聚类后未按栏重组阅读顺序
- 状态：**Tier-1 已实施（Stage 10 批次 12，2026-09-21，r66 授权）**——
  `_page_paragraphs`/`_split_words_into_column_regions` 落地
  （app/parsers/fallback_parser.py，方案 A Tier-1：投影剖面全高空白河 +
  数据驱动下限 + 行级支持判据 + 质量守卫，单区退化直通既有分组）。
  real-04 p002 精确分裂为左右两区（§1 修复本体）；6 文档语料对照
  17 个变化页全部为物理多区页、词守恒 17/17 EXACT、单栏页零差异；
  全量回归 5638 passed。r66 冻结的已知保守 miss 保持：tech-08 p012
  CJK、acad-03 p004 窄槽。设计文档
  docs/stage10-batch11-pdf-layout-architecture-design.md。
- 状态（r68，2026-09-21）：**D-safe 实施完成，验收条件全过，待 push
  授权后封口**——r68 改判授权 **D-safe = S1a ∧ S2a**（不批准 D-min
  的 OR：两理论误伤面取并集无必要；18 个目标 FP 同时满足两信号）。
  落地 `_suppress_form_option_repeat_headings` 页级 heading post-filter
  （`app/parsers/fallback_parser.py`）：heading + 规范化全文 ∈ 冻结
  词集 {yes, no, n/a, no n/a, yes no n/a} + 同页同文 ≥3 且 x 区间
  重叠同列簇 → paragraph + `heading_suppressed=form_option_repeat`；
  规范化仅 trim/空白折叠/大小写（'Yes.' 存活）；**不进批次 6
  `_form_label_signal`**（r68 明令：S1a 单独作全局局部信号会误伤
  合法单个 Yes）。x 聚类=区间重叠（含边界相接），非 rounding。
  验收（outputs/batch12i_accept_report.txt）：real-02 heading 35→17、
  抑制恰 18（Yes×9 + No N/A×9，全 p5/p6）、区头 "Brief description
  and outcome" 保留 heading 列 known residual（**禁加区头规则压
  17→16**）、其余 5 文档零变化、chunk 漂移定性为 p5/p6 窗口内下游
  重组（文本 23932 字符逐字守恒、id 多重集守恒、窗外逐字节不变）、
  全量回归 5654 passed（含 r68 八项必备测试，16 个新测试）。
  封口条件：验收已过，待单独 push 申请 → 精确核验后自动进入
  Stage-10-Batch-12-Closed

## 2. 候选 C：002-PDF 表单域标签误判 heading

- 影响文档：real-02 PDF 侧，devset 1/10
- 现象：表单域标签（空表格单元格旁的短标签行）被误判为 heading，heading 计数 +246%
- 根因方向：表单页缺少"表单域标签"语义信号，短行+无正文字体特征的启发式误触发
- 状态：**已处理（Stage 10 批次 6，2026-09-20，r59 授权；范围经 r59 偏差
  重裁自 DOCX 改判 PDF 侧，见 ADOPTION §144）**——`_classify_pdf_paragraph`
  的 short_line heading 候选先过 `_form_label_signal` 局部负向语义信号
  （多冒号标签簇 / ≤4 token 冒号结尾短标签 / 括注 please/tick 填写指令 /
  'Yes No N/A' 选项行尾；半角/全角冒号均计），命中 → paragraph +
  `metadata.heading_suppressed` 信号名；通用框架/全局阈值/DOCX 路径零改动
- real-02 PDF 验收（只读对照）：heading 45→30，表单标签 FP 18→3，
  DOCX 合法标题镜像匹配 10→10 零损失；页面家具 15 条全部保留（r59 ③）
- 已知残留（3 条，局部信号安全边界内不追，列已知限制）：纯选项行
  （'Consigner Carrier Consignee' 一类：无冒号/括注/行尾信号，与合法
  短标题不可局部区分）；>4 token 冒号结尾标签（token 上限为保
  'This report was prepared by:' 一类 5 token 句式 heading 不受损）；
  含 (CEO equivalent) 类括注但无 please/tick 的长标签行
- 测试：tests/test_pdf_form_heading_suppression.py（30 个：表单标签
  抑制 12 + 正常 heading 不受影响 7 + 家具守护 3 + 既有行为不变 +
  手写最小 PDF 端到端 + 管线 schema；全合成夹具，零真实语料）

## 2a. real-02 PDF 页面家具类 heading 假阳性（r59 ③ 另立）

- 现象：PDF 侧页脚页码（'Page 01'–'Page 12'）、封面日期、宣传语等
  页面家具短行被 short_line 启发式判为 heading，real-02 PDF 共 15 条
- 与 §2 表单标签类属**不同负向语义类别**（r59 ③ 明确排除出批次 6）：
  即使共享 short_line 触发路径，也不得经表单标签规则顺带压制；
  tests/test_pdf_form_heading_suppression.py Group C 为其回归守护
  （三条家具形态合成行必须仍判 heading）
- 根因方向：页脚/封面文字缺少位置（页底边距带/页眉页脚区）与模板
  重复性（同文式跨页复现）信号
- 状态：**已处理（Stage 10 批次 9，2026-09-20，r62 授权）**——
  `_parse_pdf` 文档级后置过滤 `_suppress_page_furniture_headings`
  （`app/parsers/fallback_parser.py`），仅对已判 heading 且位于底带
  （bbox 下边缘/页高 ≥ 0.93，r62④ 冻结阈值）的候选生效：
  **D1** 全文本匹配通用 Page+数字 形态（大小写不敏感；不要求显示
  页码==物理页；不扩展到裸数字/日期/罗马数字/文件名）→
  `page_furniture_page_number`；**D2** 规范化文本（仅首尾空白清理 +
  连续空白折叠）在 ≥2 个不同物理页的底带逐字出现（两实例自身均须
  在底带）→ `page_furniture_band_repeat`。命中 heading→paragraph +
  `metadata.heading_suppressed`；`_classify_pdf_paragraph` 接口/
  short_line 规则/DOCX 路径/公共模型/元素顺序与批次 6 语义零改动。
  页首 running header 不进 v1（r62④ 边界）
- real-02 PDF 只读验收（对批次 8 基线，构成精确命中 r62⑤ 钉死预期）：
  heading 30→16，抑制 14（A 页码 12 走 D1 + C 宣传语 2 走 D2）；
  剩余 16 = 镜像合法 10 + 语义合法 2 + **B 封面日期残留 1（划出范围
  列已知限制：位置/重复性/字号与合法期间标题同形，无低误伤通用
  信号，r62③ 禁止裸日期规则/月份词典/年份范围/封面特判/字号特判）**
  + 批次 6 表单残留 3；DOCX 镜像 10/10 保持
- 测试：tests/test_pdf_page_furniture_suppression.py（19 个：F1 抑制 3 +
  F2 存活 5 + F3 阈值 2 + r62⑤ 两项实现级守护 3 + 单元级 4 + F4 端到端
  2；全合成手写最小 PDF 夹具，零真实语料；阈值夹具标定 bbox[3] =
  792 − y + 2.07，93.0% 抑制 vs 92.9% 存活以 y=57.4/58.4 实现）

## 2b. DOCX 空段落被赋 heading 样式（r59 ⑥，已知现象，不动）

- 现象：real-02 DOCX 2 个空段落自身被文档赋予 heading 样式，样式驱动
  解析如实产出空内容 heading 元素（content 为既有"(空段落)"占位）
- 性质：源文档样式赋值现象，非解析缺陷；r59 ⑥ 明确不进入批次 6，
  实现保持不动
- 状态：独立已知现象（2026-09-20 取证）

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
- 状态：**设计/证据轮完成（Stage 10 批次 10，2026-09-20，r63④
  授权，零实现）**——结论：15 真表中丢失 5 + 结构性不可见 1（空
  1×1）；失败分三类（F-A KV-GAP 网格 / F-B 单列散文区 / F-C 空单元
  格）；pdfplumber text 策略在真实文档上全页误报（14 页中 13 页
  每页 1 个整页"表"）；原型实验证伪两方案——稀疏真表与两行负例在
  同一参数轴不可兼得，编号列表/双栏正文与双列表几何同构（结构性
  误报，分离只能靠文本语义）；可靠实现须并行 word 消费通路 + 元素
  去重替换 = 新全局 table reconstruction framework，且与 §1 多栏
  病理耦合 → 命中 r63 停链条款，只报设计结论。设计文档
  docs/stage10-batch10-borderless-table-design.md；处置（维持挂起
  或限定 KV-GAP 子类授权实施轮）待 r64 裁决
- 批次 11 增补（2026-09-21）：r64 改判 §3a = deferred / blocked on
  PDF layout-reconstruction architecture（ADOPTION §150③）。共享
  架构设计轮完成（r64/r65 授权，零实现）：方案 A 的 Tier-2 候选
  车道把表格性判定与分栏判定解耦——N4 双栏正文成为区域形成的正确
  输出而非表格误报；F-A 候选须 ≥2 确认轴 + 结构锚 + 逐候选与既有
  paragraph 去重替换（该替换点单独待裁）。实施授权待 r66；
  设计文档 docs/stage10-batch11-pdf-layout-architecture-design.md

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
- 状态：**已处理（Stage 10 批次 7，2026-09-20，r60 授权，纯测试债务
  批，生产代码零改动）**——tests/test_batch_plugin_init_timeout.py
  三测：默认值 120.0 钉死守护 / 正常插件默认超时并行零超时事件 /
  超时路径真实跨进程（monkeypatch `PLUGIN_INIT_REPORT_TIMEOUT`=1.0 +
  sentinel 门控 worker 导入挂起 → 父进程 queue.Empty → 受控
  plugin_init_report_timeout，error_type=Empty、expected/received=2/0、
  零文件派发、无 summary、结构化 JSON 无 traceback）
