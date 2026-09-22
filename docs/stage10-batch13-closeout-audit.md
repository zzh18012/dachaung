# Stage 10 Batch 13 — closeout / residual-baseline audit（r69 授权，只读收口批）

日期：2026-09-22。基点：`aaff3df`（= 已封口的 Batch 12 远端 tip，
P22' A 精确核验后建本分支）。授权性质：**只读验收与文档收口，
零生产解析行为变化**（本批产出 = 本文档 + BACKLOG 状态更新 +
outputs/ 证据脚本；fallback_parser.py 等生产文件零触碰）。

证据生成条件：worktree HEAD = aaff3df（树干净）；六篇语料解析
基线 = outputs/batch12i_after（D-safe 验收轮在同一 commit 内容上
生成，outputs/batch12i_accept.py 可复现）；reason 普查脚本 =
outputs/batch13_reason_census.py（重跑即得下表）。

## ① 冻结基线（Batch 12 封口后六篇语料，@aaff3df）

| 文档 | elements | paragraph | heading | caption | table | image | chunks | 抑制总数 |
|------|---------|-----------|---------|---------|-------|-------|--------|---------|
| real-02 | 110 | 80 | **17** | 0 | 9 | 4 | 44 | 48 |
| real-04 | 18 | 10 | 3 | 1 | 2 | 2 | 24 | 0 |
| acad-03 | 71 | 25 | 9 | 0 | 9 | 28 | 97 | 0 |
| prod-01 | 1308 | 725 | 427 | 0 | 3 | 153 | 892 | 10 |
| tech-08 | 979 | 193 | 307 | 56 | 100 | 323 | 545 | 9 |
| tech-03 | 4258 | 460 | 1297 | 0 | 151 | 2350 | 1547 | 9 |

real-02 heading = 17 的构成（r69 冻结口径）：DOCX 镜像合法 10 +
语义合法 2 + 批次 9 B 类封面日期 residual 1 + 批次 6 表单残留 3 +
批次 12 应答区头 residual 1 = 17。

## ⑤ suppression metadata 原因集合与计数核对（r69 ⑥ 第 5 项）

全语料 `metadata.heading_suppressed` 普查（76 条）：

| reason | 批次 | 计数 |
|--------|------|------|
| form_label_multi_colon | 6 | 15 |
| form_label_short_colon | 6 | 12 |
| form_label_instruction | 6 | 1 |
| form_label_option_suffix | 6 | 2 |
| page_furniture_page_number | 9 | 12 |
| page_furniture_band_repeat | 9 | 16 |
| form_option_repeat | 12 | 18 |

**未注册 reason：0**。注册集 = 批次 6 四信号 + 批次 9 两规则 +
批次 12 D-safe 一规则，逐条对应，无新增。分布注记：批次 9 信号
在 tech-08（8）/tech-03（6）有跨语料命中（批次 9 验收时已接受，
D2 底带跨页逐字重复为文档级通用证据）；批次 6 信号在 prod-01
（10）/tech-08（1）/tech-03（3）有命中（多冒号标签簇为通用形态）；
D-safe form_option_repeat 恰 18 全部 real-02 p5/p6（验收钉死）。

## ②③ 剩余误判稳定家族登记 + 四分类（r69 ⑥ 第 2/3 项）

### processed（已处理并有验收证据）

| 项 | 处置批次 | 证据 |
|----|---------|------|
| real-02 表单域标签 heading FP（45→30，FP 18→3） | 6（r59） | BACKLOG §2 + 30 测试 |
| real-02 页面家具 heading FP（30→16：D1×12 + D2×2） | 9（r62） | BACKLOG §2a + 19 测试 |
| real-02 应答栏选项碎片 18（35→17） | 12 D-safe（r68） | batch12i_accept_report + 16 测试 |
| real-04 多栏题注碎字符（p002 左右分区） | 12 Tier-1（r66） | 词守恒 17/17 EXACT |
| tech-08 六页 TOC 侧栏碎片分离（p008/018/062/066/076/080） | 12 副产 | batch12h_audit A 类 |
| tech-03 p003 交错 heading FP 净消除 1 | 12 副产 | 同上 |
| real-01 跨页表格保守合并（real-01 无实例，合成夹具验证） | 4（r36） | BACKLOG §3 |
| w:tc 内 sdt 递归（零真实命中，防御性） | 3 | BACKLOG §4 |
| pdfplumber C 库崩溃子进程隔离 | 2 | BACKLOG §5 |
| --plugin 文件路径加载 | 5（r43） | BACKLOG §8 |
| plugin_init_report_timeout 测试债务 | 7（r60） | BACKLOG §9 |

### known residual（登记不修，各有裁定依据）

| 家族 | 实例 | 裁定依据 |
|------|------|---------|
| real-02 应答区头 'Brief description and outcome' | ×1 | r68/r69 钉死：**禁补区头特判或扩词集**（无低误伤通用信号，与批次 9 B 类同性质边界） |
| real-02 批次 6 表单残留（纯选项行 'Consigner Carrier Consignee' 类 / >4 token 冒号结尾 / 含括注无 please-tick） | ×3 | r59 局部信号安全边界（token 上限保 5-token 句式 heading） |
| real-02 批次 9 B 类封面日期 'December 2025' | ×1 | r62③ 禁裸日期规则/月份词典/年份范围/封面特判/字号特判 |
| acad-03 图内文字标签（p002 Figure 2 内 'Multimodal Transformer' 等） | ×5 | r69：图内元素语义家族，不修（base 侧同为交错垃圾错误形态） |
| tech-03 封面碎片（'年' 明确 FP；封面标题块/联系方式 2 条不可验证） | ×3 | r69 不修；2 条无 GT 裁定维持两可登记 |
| prod-01 续页标记 '(continuedfrompreviouspage)'（p077，非底带） | ×1 | r69 不修（单实例） |
| prod-01 页码拆分显形（p077/p105/p167 TOC 行尾页码 71/99/161，非底带，base 亦 FP） | ×3 | r69 不修；批次 9 D1 底带信号不覆盖此位置 |
| 单柱/单格假阳性表（real-01 ×3 + real-04 ×1） | ×4 | r40 裁定方案 0 不修（真/假 (2,1) 同形，纯形状过滤不可精确） |
| tech-08 p012 CJK 保守 miss / acad-03 p004 窄槽保守 miss | ×2 | r66 冻结（Tier-1 守护栏内的已知保守不分裂） |

### deferred / blocked

| 项 | 分类 | 依据 |
|----|------|------|
| §3a real-02 PDF 无线框表格欠检测（15 真表丢 5 + 1 结构性不可见） | **deferred / blocked on PDF layout-reconstruction architecture** | r64 改判；批次 11 Tier-2 设计已备（方案 A 双车道），实施授权待裁——**本批维持不变（r69 ④）** |

## ④ §3a 不变声明

§3a 维持 r64/r65 口径：deferred / blocked on PDF
layout-reconstruction architecture。批次 11 共享架构设计轮（r64/r65
授权，零实现）为其预备件，本批不触发、不实施、不改判。

## ⑥ 全量回归与关键 guard suites 核对

- 全量回归 @ aaff3df（D-safe 验收轮与本分支同 commit 内容）：
  **5654 passed / 26 skipped / 0 failed**（55s）
- 关键 guard suites 本分支重跑（2026-09-22）：
  tests/test_pdf_form_heading_suppression.py（批次 6，30）+
  tests/test_pdf_page_furniture_suppression.py（批次 9，19）+
  tests/test_pdf_form_option_repeat_suppression.py（批次 12 D-safe，
  16）+ tests/test_pdf_column_regionizer.py（批次 12 Tier-1）+
  tests/test_pdf_cross_page_tables.py（批次 4）= **99 passed**

## 跨语料候选信号检查（r69：≥2 篇同结构信号才可记候选证据）

逐家族核查结论——**当前无满足条件的家族**：

- 页码类 heading FP：real-02 底带页码（已由批次 9 D1 处理）与
  prod-01 TOC 行尾页码同属"页码文本"语义，但**安全信号不同构**
  （底带位置带 vs TOC 行尾内联位置；后者与合法行尾数字无低误伤
  区分信号）→ 不构成同一结构信号的跨篇候选。
- 家具/续页标记：prod-01 continued ×1，单实例。
- 图内标签（acad-03）与封面碎片（tech-03）：视觉语义不同族，
  各自单篇。
- D-safe 选项碎片：已 processed（real-02 单篇封闭词集信号，无
  第二篇实例，亦无需扩面）。

按 r69 约束，本批**零实施候选登记**；未来任一家族积累出 ≥2 篇
独立版面实例的同一结构信号时，须重新立项裁定。

## ⑦ Stage 10 整体 closeout 结论 + 未关闭风险表

**结论：Stage 10 具备整体 closeout 条件（条件式成立）。**

依据：①批次 1–12 全部落地并各有验收证据（processed 清单上表）；
②六篇语料基线冻结（§①）；③全部剩余误判已按稳定家族登记且每项
有裁定依据（零"未分类"项）；④suppression reason 注册集闭合零外溢
（§⑤）；⑤全量回归与 guard suites 全绿（§⑥）；⑥§3a 独立 deferred
不阻塞 Stage 10 本体收口。

未关闭风险表：

| # | 风险 | 性质 | 影响 |
|---|------|------|------|
| 1 | §3a 无线框表格欠检测 blocked（依赖 layout-reconstruction 架构） | deferred 遗留 | Stage 11+ 候选方向；不影响六篇冻结基线 |
| 2 | known residual 计数与冻结语料绑定 | 基线时效 | 语料扩量后家族计数会变，须重走本审计流程 |
| 3 | 第二标注人 r3 重做未回（Stage 9 batch 26 线） | 独立线 | 不阻塞 Stage 10；一致性结论可能反哺 BACKLOG 登记 |
| 4 | residual 家族未来若积累跨语料证据 | 潜在返工 | 须重新立项裁定，不得直接实施（r69 钉死） |
| 5 | tech-03 封面 2 条不可验证项无 GT | 登记完备性 | 维持两可登记；除非获得 GT 否则永久两可 |
| 6 | 单文档 heuristic 积累倾向 | 治理风险 | r69 已裁定关闭逐类修补通道；防止回潮依赖后续裁决纪律 |

## 边界声明（r69 ⑦）

G⑤ 代表页冻结口径不变；第二标注人进行中工作不因本收口审计改变；
2026-09-28 autonomous-track 周期简报与 execution-baseline 豁免轮
保持独立，不并入本批。本批不含 push 权（commit 留存本分支待裁）。
