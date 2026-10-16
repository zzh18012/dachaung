> 状态：W5 调查+规格 v1（r88-Q3 授权 investigation + spec，不含实现授权）。
> 落点：main/design/（r88 裁决字面指定；同 W4 注）。
> 证据件：adoption 侧私有面（outputs/w5_probe_*.{py,json}，gitignored；探针可复跑）。
> 呈报：r89 简报。acad-03 = holdout（manifest 实测，正文 split 披露节）。

# W5 表格元素检测（table element detection）——调查与设计规格草稿

- 工作项：W5_table_element_detection（r88-Q3 批准立案；**仅授权 investigation + spec，不含任何 parser 实现授权**）
- 日期：2026-10-16（2026-10-15 21:15 429 中断后的完整重做：上轮仅留探针脚本未运行、草稿未写；本轮重读并修正探针后运行、补 2 个探针、落盘本草稿）
- 输出物：本文件 + `outputs/w5_probe_findtables.{py,json}` + `outputs/w5_probe_para_overlap.{py,json}` + `outputs/w5_probe_line_orientation.json`
- 红线前提：确定性规则——无概率匹配、无 OCR、无布局模型。r88 裁决明确 pdfplumber `find_tables`/`TableFinder` 的 `lines`/`lines_strict`（页面 graphical lines 几何策略）属可优先调查的确定性路径；text-based（文字对齐推导边界）策略须另行解释红线边界，本调查只调查不裁决。

## 0. 背景

r87-Q2 几何诊断（acad-03-layoutlmv3）发现预测侧全部 9 个 table 元素都是图内图示碎片（页 2 的 6 个 + 页 3 的 3 个全部落在 fig-2/fig-3 主图 raster bbox 内部）；论文 4 张真实表格（Table 1–4，页 5/6/7/9）零检出，表体全被抽成 paragraph，4 条 table caption 边全部失败。W5 因此立案：弄清伪表来源、设计确定性排除与检出规则。

**split 更正披露**：acad-03-layoutlmv3 实为 **holdout**（冻结 manifest `samples/private/stage9-corpus/manifest.json` 实测：acad-01=comparison，acad-02/04/05/06=dev，acad-03=holdout，acad-07=holdout，acad-08=comparison）。本轮全量实测只覆盖 dev split AcadPDF 四篇（acad-02-layoutlm / acad-04-docling / acad-05-pubtables1m / acad-06-dmap）；acad-03 事实仅引用 r87q2 诊断件（`samples/private/stage9-corpus/evaluation/caption_geometry_failure_analysis_r87q2.json`）已记录内容，comparison/holdout 文档内容零读取、零重放。

**gold 标注核对**：任务要求抽查至少一篇；本轮实际核对了全部四篇（`samples/private/stage9-corpus/annotations/<doc>.json` 的 nontext 单元中 `nontext_ref` 前缀 `tab:` 的页分布），与探针脚本 DOCS 内嵌值逐篇一致：

| doc | gold 表页分布（页:表数） | gold 表总数 | tab refs |
|---|---|---|---|
| acad-02-layoutlm | 6:2, 7:1, 8:2 | 5 | tab:1–tab:5 |
| acad-04-docling | 5:1 | 1 | tab:1 |
| acad-05-pubtables1m | 4:1, 6:1, 7:1, 8:1 | 4 | tab:1–tab:4 |
| acad-06-dmap | 5:1, 6:2, 7:2, 8:1 | 6 | tab:1–tab:6 |

dev 四篇 gold 表合计 16。环境：pdfplumber 0.11.10（探针实测值 = r3 基线 parser_version 记录值，重放无版本漂移）。

## 1. 现状代码路径（9 个伪表怎么来的）

PDF 表格检测现行路径（`app/parsers/fallback_parser.py`，adoption 侧为本轮基线的实际执行副本；与 dachuang-code 侧同名文件 diff 仅在 docx 表格错误处理段（≥L962），PDF 段行号两侧一致）：

- **L619–650 表格检测**：L621 `tbls = page.find_tables() or []`——pdfplumber 默认参数即 `vertical_strategy="lines", horizontal_strategy="lines"`；L624–630 逐表 `extract()`，空行表跳过；L636–650 产出 table Element（confidence 0.7，metadata 记 row/col_count，source="pdfplumber"）。
- **L600 段落路径**：`_group_words_to_paragraphs(words)` 与表格检测**相互独立**——表体词不从段落词池剔除（见 §5 双轨问题）。
- **L651+ 图片路径**：仅 `page.images`（raster XObject）。
- **L507–568 `_vector_figure_clusters`**：rects/lines/curves 空间聚类（gap 15pt，含 curve 且 ≥100×100pt 计为矢量图），L721 用于 figure 元素产出；不参与表格判定。

**9 个伪表来源结论**：伪表全部产自 L621 `find_tables()` 默认 lines/lines 策略本身——**图形区内的矢量笔画（图表坐标轴/网格线/流程图框线/矢量叠加层）被当作表格 ruling lines，形成闭合网格即判为 table**。acad-03（holdout，r87q2 引用）：fig-2/fig-3 主图为 raster 底图 + 矢量叠加，叠加笔画在 raster bbox 内部成网格 → 9 伪表（页 2 六个 + 页 3 三个，r87q2 `surprising_findings[1]`）。dev 侧同机制：acad-04 的 5 个 table 元素内容为条形图轴标签与流程图框（如 p7 内容含倒排轴标签 "egap/ces"）、acad-06 的 7 个中 6 个为 teaser 图/架构图框线（r3 基线 elements 实测，见 §2/§6 表）。**不是** `_vector_figure_clusters` 误判（该函数只产 figure 元素，不产 table）。

## 2. Q1 真 table bbox 识别（lines vs lines_strict，dev 四篇实测）

探针 `outputs/w5_probe_findtables.py` 对 dev 四篇逐页运行 TableFinder 两策略（`lines` = 现生产行为的忠实重放；`lines_strict` 更保守，要求边严格对齐闭合格）。

### 2.1 逐篇检出对照 gold 表页

| doc（页数） | gold 表页（表数）合计 16 表 | lines 检出（页:数） | lines 在 gold 页 | lines_strict 检出（页:数） | strict 在 gold 页 |
|---|---|---|---|---|---|
| acad-02-layoutlm（9） | 6:2, 7:1, 8:2 | **0** | 0 | **0** | 0 |
| acad-04-docling（8） | 5:1 | 5（p2:1, p5:1, p7:3） | 1（p5） | 4（p5:1, p7:3） | 1（p5） |
| acad-05-pubtables1m（10） | 4:1, 6:1, 7:1, 8:1 | **0** | 0 | **0** | 0 |
| acad-06-dmap（12） | 5:1, 6:2, 7:2, 8:1 | 7（p1:2, p4:2, p6:1, p8:2） | 3（p6:1, p8:2） | 1（p6:1） | 1（p6:1） |
| 合计 | 16 | 12 | 4 | 5 | 2 |

**真伪判定（按内容与几何核对，非仅页号）**：12 个 lines 检出中仅 **1 个**是真表——acad-06 p6 检出（bbox [135.21, 229.96, 228.28, 300.50]，3 行×1 列，16 词，内容 "Configuration / Text Image DMAP / ✓ ✓ ✗…" 与 e0030 内 Table 2 表体文本一致，对应 gold tab:2 的**左列带，部分覆盖**）。其余 11 个全为图内伪表：acad-04 p5 检出虽落在 gold 页，内容为 "103 x86 CPU / M3 Max / L4 GPU / 102 / ces…"（性能条形图轴标签），非 gold tab:1；acad-06 p8 两个 2×1 微检出（32.7×18.1pt / 64.2×19.8pt，各 1 词 "Ours"/"MDocAgent"）为结果图图例碎片，非 gold tab:6。**gold 表几何检出率 = 1/16（6.25%，且为部分覆盖）；两策略完全一致地保留这唯一真检出。**

### 2.2 检不出的结构原因（booktabs 无竖线）

gold 表页 ruling lines 方向分类（探针 `outputs/w5_probe_line_orientation.json`，10:1 长宽比判定）：

| gold 页 | lines 总数 | 水平 | 垂直 |
|---|---|---|---|
| acad-02 p6/p7/p8 | 13 / 3 / 17 | 13 / 3 / 17 | 0 / 0 / 0 |
| acad-04 p5 | 88 | 54 | 34 |
| acad-05 p4/p6/p7 | 4 / 5 / 5 | 4 / 5 / 5 | 0 / 0 / 0 |
| acad-05 p8 | 45 | 6 | 39 |
| acad-06 p5/p7/p8 | 3 / 6 / 3 | 3 / 6 / 3 | 0 / 0 / 0 |
| acad-06 p6 | 21 | 9 | 12 |

acad-02（ACL 风格）、acad-05、acad-06 p5/7/8 的 gold 表全部为 **booktabs 风格（只有水平三线，零垂直线）**——纯水平线无法与垂直线相交闭合出单元格，lines/lines_strict 结构性检不出（这是 16 表中 15 表零检出的根因，不是参数问题）。acad-04 p5 的 88 条线主要来自同页矢量图表；acad-06 p6 是唯一"水平+垂直线齐全"的 gold 表，也确实被两策略检出。acad-05 p8 的 39 条垂直线属同页图形网格，未与表的水平线闭合成格。

### 2.3 策略间差异与耗时（性能观察面，如实记录）

- 差异：acad-06 上 lines 检 7 / strict 检 1（strict 剔除了 p1/p4/p8 的 6 个图内碎片，保留同一真表）；acad-04 上 lines 5 / strict 4（strict 少了 p2 的 1 个伪表）。**两策略在 dev 上的真表判定完全相同（1 个），strict 只是伪碎片更少。**
- 耗时（探针 perf_counter，含逐页两策略 TableFinder + words + 聚类）：逐篇总耗时 acad-02 0.715s / acad-04 0.769s / acad-05 0.875s / acad-06 2.684s（中位 0.875s）；单策略逐页累计 lines 0.015/0.008/0.000/0.061s、strict 0.000/0.002/0.000/0.010s；单页峰值 0.036s（acad-06）。**TableFinder 增量成本在 dev 语料上可忽略**（生产现路径本就每页调用一次默认 find_tables）。

## 3. Q2 图内伪 table 排除

### 3.1 排除规则（确定性）

对每个 TableFinder 检出计算两个几何重叠比：`in_raster_frac` = 与页内 raster image bbox 最大交集/检出面积；`in_vecfig_frac` = 与 `_vector_figure_clusters` 簇 bbox 最大交集/检出面积。裁决规则：

1. **图重叠排除**：`max(in_raster_frac, in_vecfig_frac) ≥ 0.5` → 弃（完全含于图或半数以上面积在图内）；
2. **最小实体性**：`words_inside < 4` 或 `rows < 2` → 弃（微碎片/空格网格）；
3. 其余保留为 table 候选。

### 3.2 dev 实测验证（lines 全部 12 检出）

| 检出 | 页 | gold 页 | r×c | words | in_raster | in_vecfig | 规则 1 | 规则 2 | 结果 |
|---|---|---|---|---|---|---|---|---|---|
| acad-04 #0 | 2 | 否 | 4×6 | 47 | 0.009 | **1.000** | 触发 | — | **弃** |
| acad-04 #0 | 5 | 是 | 6×4 | 17 | 0.000 | **1.000** | 触发 | — | **弃**（条形图，非 gold 表） |
| acad-04 #0 | 7 | 否 | 8×12 | 49 | 0.000 | **0.996** | 触发 | — | **弃** |
| acad-04 #1 | 7 | 否 | 4×3 | 0 | 0.000 | **1.000** | 触发 | — | **弃** |
| acad-04 #2 | 7 | 否 | 12×10 | 20 | 0.000 | **1.000** | 触发 | — | **弃** |
| acad-06 #0 | 1 | 否 | 2×3 | 32 | 0.006 | **1.000** | 触发 | — | **弃** |
| acad-06 #1 | 1 | 否 | 1×2 | 3 | 0.000 | **1.000** | 触发+触发 | — | **弃** |
| acad-06 #0 | 4 | 否 | 2×3 | 158 | 0.003 | **1.000** | 触发 | — | **弃** |
| acad-06 #1 | 4 | 否 | 2×2 | 78 | 0.012 | **1.000** | 触发 | — | **弃** |
| acad-06 #0 | 6 | **是** | 3×1 | **16** | **0.000** | **0.000** | 不触发 | 不触发 | **保留（唯一真表）** |
| acad-06 #0 | 8 | 是 | 2×1 | 1 | 0.135 | **1.000** | 触发+触发 | — | **弃**（图例碎片） |
| acad-06 #1 | 8 | 是 | 2×1 | 1 | 0.000 | **1.000** | 触发+触发 | — | **弃**（图例碎片） |

lines_strict 的 5 个检出（acad-04 p5×1 + p7×3、acad-06 p6×1）在同一规则下 4 弃 1 保留（保留者 = 同一真表）。**规则在 dev 上零误杀（保留集恰 = 真表集）、零漏放（伪表全弃）。** acad-03（holdout，不重放）：r87q2 记录 9/9 伪表落在 fig-2/fig-3 raster bbox 内部 → 规则 1 的 raster 分支按 r87q2 几何事实可全部排除（此为引用推断，非本轮实测，如实标注）。

注意规则 2 的 `cols ≥ 2` 变体**不可用**：唯一真表为 3 行×1 列（多行合并单元格线性化），最小列数约束会误杀 dev 上唯一真检出。acad-03 的 9 伪表中多个为 3×1 空内容（r87q2/基线 content 全空管道符），由 words_inside（0 词）而非列数排除。

## 4. Q3 与 image bbox 重叠的确定性裁决

实测相交形态分布（dev 12 检出，lines）：

- **完全含于图（≈1.0）**：11 个伪表 in_vecfig_frac ∈ [0.996, 1.000]；in_raster_frac 完全含于 raster 的案例在 dev 为 0（dev 伪表全为纯矢量图内碎片），acad-03 holdout 为 9/9（r87q2 引用）。
- **部分相交（0 < frac < 0.5）**：仅见于伪表边缘擦碰——in_raster_frac 0.003/0.006/0.009/0.012（矢量图与 raster 图轻擦）与 0.135（acad-06 p8 图例碎片，同时 vecfig=1.000 被规则 1 主判弃）。**dev 上不存在"真表与图部分相交"的案例。**
- **零相交**：唯一真表（0.000/0.000）。

裁决规则（写进规格）：`frac ≥ 0.5` → 弃；`0 < frac < 0.5` → 保留但发结构化 warning（`table_figure_partial_overlap`，记录 frac 与来源 family），不截 bbox、不二次裁剪（裁剪会破坏单元格闭合性，引入新的确定性风险）；`frac = 0` → 正常保留。阈值 0.5 的依据：dev 实测伪表 frac 二值分布（≈0 或 ≥0.996），0.135 为唯一中间值且属应弃碎片——0.5 在实测分布中距两类边界均有余量；无 dev 反例。

## 5. Q4 table 与 paragraph 所有权

### 5.1 现状（r3 基线，dev 四篇实测）

真表体现为 paragraph/caption 文本元素（探针 `w5_probe_para_overlap.json`）：

- **紧致表体段**（表体独立成段，bbox 即表体范围）：acad-02 p6 e0027 [112,88,500,287]（"Modality Model Precision Recall F1 #Parameters BERTBASE…"）、p7 e0030、p8 e0032/e0033；acad-05 p4 e0014 / p6 e0020 / p7 e0024 / p8 e0029。
- **整页合并段**（表体与正文/图内文字合成一个 page-wide 段）：acad-04 p5 e0016 [54,176,558,704] len 2585；acad-06 p5 e0028 / p6 e0030 [54,84,560,709] len 4929 / p7 e0033（len ≈5.3–5.4k）。
- **双轨重复（现行缺陷，实测证实）**：acad-06 p6 同时存在 table 元素 e0031（16 词表体 markdown）与 caption 元素 e0030（整页合并段，**含同样 16 词表体文本** "Configuration EvaluationBenchmarks Variants … ✓ ✓ ✗ 0.320…"）——表体文本在输出中计两次（table 一份 + 段内一份）。根因即 §1：段落词池与表格检测相互独立，L600 分组不剔除已入表词。

### 5.2 归属原则（规格建议）

**词级吸收（word-level absorption），不是段级**：段级吸收在 stage9 不可行——整页合并段的 bbox 覆盖全页，交集比无区分度（e0030 仅 2.1% 面积落在检出表内）。规则：

1. 表格检测提前到段落分组之前（同页顺序：words → TableFinder + 排除/接受规则 → 接受表 bbox 从词池剔除（词中心入 bbox）→ 剩余词再进 `_group_words_to_paragraphs`）；
2. 表体词只存在于 table 元素（消除 §5.1 双轨重复）；
3. 题注（"Table N:" 开头段）**不吸收**、保留 caption 类型（`match_table_caption_relations_pdf` 的 gap 贪心配对依赖独立 caption 元素，批次 4/7 契约不动）；
4. 部分覆盖披露：接受表 bbox 可能只覆盖表体一部（acad-06 p6 仅 93×70pt 列带）——bbox 外表词留在段落，元素 content 边界如实分裂，metadata 记 `partial_coverage`（由 rows×cols 与词数的贫富对照可判定），不做几何外推。

### 5.3 对"分块不丢不重"的影响

- chunk 的 `source_element_ids` 精确划分机制不变：每个词恰属一个元素（表内词→table，其余→段/题注），element→chunk 的划分照旧成立；"不丢"保持，"不重"在**内容语义层**从现状（表体双份）改善为单份——现状的 source_element_ids 划分本身不违规，违规的是语义重复，词级吸收顺带修复。
- 风险点：若吸收与剔除的实现顺序不当（先分段后剔词）会产生空段或残词段——规格要求剔除发生在分组前，且空文本段按现行 L602–603 跳过。

## 6. Q5 指标影响面

### 6.1 元素计数表（dev 四篇，r3 基线 vs W5 几何规则重放）

| doc | r3 现行 table 元素 | 伪表（内容核对） | W5 规则后 table 元素 | gold 表 | 新增真表 | 排除伪表 |
|---|---|---|---|---|---|---|
| acad-02-layoutlm | 0 | 0 | 0 | 5 | 0 | 0 |
| acad-04-docling | 5 | 5 | 0 | 1 | 0 | **5** |
| acad-05-pubtables1m | 0 | 0 | 0 | 4 | 0 | 0 |
| acad-06-dmap | 7 | 6 | 1 | 6 | 0（tab:2 由双轨变正式 table，计 1） | **6** |
| dev 合计 | 12 | 11 | 1 | 16 | +1 转正 | **−11** |

（acad-03 holdout 引用：9 伪表全排除、4 真表仍零检出——不重放，按 r87q2 事实与 §3 规则推断，如实标注。）

### 6.2 Layer B 漂移方向（定性，不承诺数字）

- `nontext_detection_ratio`（table 单元）：**precision 方向改善**（dev −11 伪表、acad-03 −9 引用）；recall 方向基本不变（几何天花板 1/16，唯一增量是 acad-06 tab:2 的部分转正）。
- `extraction_coverage`：表体词从 paragraph 重类型化为 table，覆盖词集不变 → 总量漂移近似中性；acad-06 p6 双轨文本去重后该段 len 下降（4929 − 表体词）。
- element counts：table ↓11（dev）；paragraph/caption 计数可能微降（吸收后空段跳过）或不变。
- `caption_geometry` / `table_has_caption` 边：伪表消失后不再参与 gap 贪心配对，减少伪表偷配真题注的错误配对方向；真表（acad-06 p6）获得配对资格，tab caption 边有望 +1。
- `silent_drop_count`：基于 expectations 的计数不变（gold 表仍主要在 paragraph 中，不丢文本）。

## 7. 推荐策略与备选

- **推荐（本调查范围内）**：维持 `find_tables()` 默认 lines/lines（现生产行为零变更），新增两道确定性门——(a) §3 图重叠 + 最小实体性排除；(b) §5.2 词级吸收与题注保留。dev 实测：伪表 11→0、真表 1 保留、语义双轨修复。`lines_strict` 作为可选配置保留（伪碎片更少：acad-06 7→1），但因两策略真表判定相同、且 strict 在部分矢量图上有不同边界行为，**默认不切换**，留配置项。
- **备选（须另行红线裁决，本轮不裁决）**：booktabs 表召回（dev 15/16 gold 表）需要列边界来自**文字对齐**（如 `vertical_strategy="text"` 或水平线行带 + 词列聚类）——这跨入 r88 指明须单独解释边界的 text-based 路径；若未来裁决放行确定性文字对齐（仍无概率/无 OCR/无布局模型），预期召回上限显著提高，但须重新过红线审查与同套探针验证。
- **不推荐**：调 tolerance/边缘参数微调 lines 策略（结构性缺失垂直线，调参无效，§2.2 已证）。

## 8. 风险与未决

1. **pdfplumber 版本依赖**：0.11.10 的 TableFinder 语义（默认参数、bbox、cells）为实测基线；升级需重放本探针（脚本已固化在 outputs/，可直接复跑）。
2. **无边线表格退化**：booktabs 语料（acad-02/05 全部、acad-06 多数）几何零召回——W5 几何版不解决，见 §7 备选；报告口径须如实披露"几何可检表"与"gold 全表"的差。
3. **`_vector_figure_clusters` 假设时效**：批次 15 的"表格 = 零 curves"断言来自旧 devset；stage9 中 acad-04 p5 gold 表页含 283 条 curves（数学字形），若真表区域内含 curve 笔画且与图簇连通，规则 1 有误杀真表的理论风险——dev 实测未触发（唯一真表 vecfig=0.000），但排除规则与图簇判定解耦（只用簇 bbox 不用其分类语义）可降低耦合风险，实现时应保持这一解耦。
4. **docx 侧不适用**：python-docx 原生 `w:tbl` 已正确产 table 元素（L960+），W5 仅 PDF 路径。
5. **性能面**：dev 实测增量可忽略（§2.3）；但 dev 仅四篇且页数 ≤12，语料放大后 TableFinder 每页成本需在批量通道复测（现有 batch 并行可承接，不新增担忧点）。
6. **部分覆盖检出的表体分裂**：acad-06 p6 型检出只覆盖列带，bbox 外表词留段落——按 §5.2(4) 披露不外推；若未来要求整表 bbox，需 text-based 列扩展（同备选红线）。
7. **未决**：阈值 0.5 与 words_inside ≥ 4 / rows ≥ 2 的常数在 dev 上零反例，但 dev 只有 12 个检出样本——常数敏感性（0.3/0.7、3/5 词）未做扫描，留实现批次带测试守护。

## 9. 声明

本文件为 **W5 调查 + 设计规格草稿**，对应 r88-Q3 的 investigation + spec 授权；**不含任何 parser 实现授权**。全文数字除标注"引用 r87q2"（acad-03 holdout，不重放）与"引用推断"外，均为本轮 dev 四篇实测（探针脚本与原始 JSON 见 outputs/w5_probe_*）。零 git 操作、零 app/ 写入、零 samples 写入。
