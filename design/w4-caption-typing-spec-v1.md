> 状态：W4 调查+规格 v1（r88-Q3 授权 investigation + spec，不含实现授权）。
> 落点：main/design/（r88 裁决字面指定；r84 P1 先例 relation-generation-spec-v1.md 实际位于 adoption/design/，如裁决方另有所指可移）。
> 证据件：adoption 侧私有面（samples/private/stage9-corpus/ 与 outputs/w4_probe_*，gitignored；探针可复跑）。
> 呈报：r89 简报。acad-03 = holdout（manifest 实测，正文 split 披露节）。

# W4_caption_typing 设计规格草稿（r88-Q3 investigation + spec）

**授权边界**：r88-Q3 批准 W4 立案，仅授权调查 + 规格起草。**本件为调查+规格草稿，不含实现授权**——不据此改任何 `app/` 代码、不做参数调优、不提交 git。

**调查日期**：2026-10-15。**调查者**：W4 investigation agent。

---

## 0. 背景

r87-Q2 几何诊断（acad-03-layoutlmv3）发现：9 条 gold caption 边仅命中 1 条，8 条 MISS 中 7 条的根因是**元素层 typing 缺失**——3 条 figure 题注文本（u0015/u0020/u0121）被吸收进整页 paragraph（预测侧 e0000/e0003/e0055），未产生 caption 类型元素，导致几何配对规则（`match_caption_relations_pdf`：同页 + 下方 0<gap≤50pt + x 相交 + greedy 唯一）的输入集为空。反事实测算（r87q2 JSON `typing_counterfactual_fact`）：不改阈值、仅假设 typing 正确，现行 50pt 规则可直接成边 7 条。W1（commit ee80799）曾扩展 caption 分隔符类使冒号形题注能成 caption 元素，但其作用点在**段落开头**（`_classify_pdf_paragraph`），对"题注行被吸收进 paragraph 中部"无效。W4 的目标即在**行边界**上补齐确定性 caption typing。

**split 合规披露**：manifest.json 实测 `acad-03-layoutlmv3` 的 split = **holdout**（非 dev；dev split AcadPDF 为 acad-02/04/05/06 四篇）。本次调查严格遵守：acad-03 的四条样本**只**使用 r87q2 诊断件 JSON 中已记录的文本（r87-Q2 已授权该诊断），**未重读 acad-03 PDF 内容**；全量统计只在 dev split AcadPDF 四篇 + 其源 PDF（r88-Q3 明确授权通道）上执行。comparison/holdout 文档内容零读取。

---

## 1. 要素一：输入单位边界

### 1.1 现状代码：行如何被合并成 paragraph（`app/parsers/fallback_parser.py`，只读引用）

| 机制 | 行号 | 事实 |
|---|---|---|
| 词抽取 | L590 | `page.extract_words(keep_blank_chars=False, use_text_flow=False)`——每页得到 word dict 列表（x0/top/x1/bottom/text） |
| 行聚类 | L385-398 | 按 `(y_center, x0)` 排序后，y 中心差 ≤ **3.0pt**（硬编码，L390 `abs(yc - current_y) <= 3.0`）归为同一行；行内不区分双栏（同 y 带跨栏文本并入同一行） |
| 段落聚类 | L404-417 | 行间距 `(line_top - last_bottom) > 1.5 × median_h`（中位词高，L400-401/L410-411）切段 |
| 段落融合 | L420-435 | `_lines_to_para` 把行内 word 按 x0 排序后 `" ".join`、行间再 `" ".join`——**行边界在 content 字符串中被销毁**，只保留合并 bbox |
| caption 判定 | L52-59 + L438-447 | `_CAPTION_RE` 只在**段落文本开头**匹配（`_classify_pdf_paragraph`）；题注行在中部即漏 |
| 几何消费 | L110-153 | `match_caption_relations_pdf` 只吃 type=caption 元素的 bbox——上游 typing 缺失则空转 |

acad-03 类 PDF 的 gluing 根因：字符间距小于 pdfplumber 分词阈值时整行成为一个 word（无内部空格），r87q2 实录题注行 glued 形如 `Figure2:Comparisonswithexistingworks(e.g.,DocForme`。

### 1.2 pdfplumber 行级确定性证据（逐项核实）

在 dev AcadPDF 四篇上以 adoption venv（pdfplumber **0.11.10**）实测 `page.extract_text_lines()`：

| 证据源 | 可用性 | 实测 |
|---|---|---|
| 行 bbox（x0/top/x1/bottom） | **可用** | 每行 dict 含全四坐标（acad-02 p0 抽查 68 行全有）。acad-03（holdout）不可重测，但 r87q2 已在其 PDF 上实测行级 bbox（JSON per_edge 录得 u0020 行 `[53.8,372.7,558.2,383.36]` 等），证明该抽取通道对 glued PDF 同样给出 bbox |
| 行文本 + chars | **可用** | line dict 含 `chars`，每 char 含 `size`/`fontname`（acad-02 p0 行 1 实测 size=17.2/fontname=TQUZIZ+LinBiolinumTB） |
| 字体大小（题注 vs 正文判别） | **不可靠** | dev 四篇实测题注行 size 与正文关系不一致：acad-02 题注 9.0 = 正文 9.0（无差）；acad-05 题注 9.0 < 正文 10.0；acad-04 混合（p5 Table1 行 7.0/10.0，其余 10.0=正文）。**不能作主判别条件** |
| 行间距 gapPrev（题注行与上一行） | **可用但无判别力** | dev 实测 TP 题注行 gapPrev ∈ [-6.61, 16.36]pt（含负值——与图/表区域重叠），唯一行级 FP "Table6." gapPrev=1.99 与 TP（Table4 同页 1.99）完全同值。**不能区分 TP/FP** |
| 行宽（x1-x0） | **可用，dev 上有判别力** | 全部 18 条 TP-new 题注行宽 ∈ [117.4, 505.9]pt；唯一 FP 行 "Table6." 宽 **28.2pt**（换行残余独行）。但样本量小，**阈值数字不在本件冻结**（见 §6 未决问题） |
| 行起点 x0 | 可用，无判别力 | TP 分布于左栏（x0≈50-54）与右栏（x0≈308-318），FP 也在右栏 |
| 双栏同行合并 | **风险项** | extract_text_lines 与 parser 自身行聚类（y 带 ±3.0）都会把同一 y 带的左右栏文本合并为一条行记录（acad-06 p7 实测：`'largestnumberofreflectionoperations,as20.6%ofitsquestionsare Table5:Accuracyondiffere…'`——左栏正文与右栏题注混入同一行） |

### 1.3 输入单位边界（规格陈述）

W4 的切分单位 = **行**（pdfplumber 行重建所得的行记录；在 parser 现架构里对应 `_group_words_to_paragraphs` L385-398 的行聚类结果，行合并进段落**之前**）。判定输入 = 行文本 + 行 bbox（+ 页上下文）。**不做任何语义推断**：不看动词、不猜句式、不用字体/间距做模糊打分；仅用（a）行首 grammar 命中、（b）可见分隔符、（c）可选的几何护栏（宽度，参数未冻结）。退化路径：行 bbox 缺失（退化行）→ 放弃切分，保持现状输出（不因 W4 引入新失败模式）。

---

## 2. 要素二：确定性 caption grammar

### 2.1 实际格式枚举（dev 四篇全量普查 + r87q2 记录，全部实测非估值）

| 形态 | 实例（来源） | 频次（dev 行级普查） |
|---|---|---|
| glued 冒号 | `Figure1:…` `Table2:LayoutLM…`（acad-02/04/06；acad-03 r87q2 记录 u0015/u0020/u0121 同形） | 多数 |
| spaced 冒号 | `Figure 1: Sketch of Docling's…`（acad-04 p2）、`Figure 2: Dataset categories…`（acad-04 p5） | 少数 |
| glued 句点 | `Figure1. Anexample…` `Table1.Comparison…`（acad-05 全篇） | acad-05 主形态 |
| spaced 句点 | `Fig. 4. The intersection…`（acad-05 p7，**叙述引用**，负例） | 1 |
| 句尾残余独行 | `Table6.`（acad-06 p7，宽 28.2pt，**FP**） | 1 |
| 数字后无分隔符 | `Figure3givesanoverviewof…`（u0038，acad-03）、`Table5presentsthenumberof`（acad-06 p7 右栏叙述） | 排除类 |
| 数字后右括号 | `Figure 4). Processing a page…`（acad-04 p5 换行引用） | 排除类 |
| 全角冒号/顿号 | dev AcadPDF（英文论文）未出现；W1 类中已有（中文语料域，本次未验证） | 0 |

### 2.2 grammar 最终形态（含迭代记录）

**迭代 1（废弃）**：直接沿用 W1 `_CAPTION_RE` 分隔符类 `[\.、:：\s]`。实测否决：raw 形 `"Figure 3 gives an overview of the LayoutLMv3."` 在该类下**匹配为 True**（u0038 类叙述句只要落在行/段首即被提升为 caption）。dev 实测该风险真实存在（acad-02/04/06 均有 "…shown in Table 5. We can see…" 式引用句）。

**迭代 2（最终，本件冻结的 spec 形态）**：

```
行级：^\s*(?:Table|Figure|Fig\.?|表格|表|图)\s*[0-9０-９]+[\.、:：]
```

- keyword 与数字之间允许空白（`\s*`，覆盖 spaced 形）；**数字后必须紧跟可见分隔符 `[\.、:：]`，删除 `\s`**——这是排除 u0038 类（"Figure 3 gives…" / glued "Figure3gives…"）的唯一判别点；
- 与 W1 段首通道的关系：W4 是行级细化，W1 语义（段首 caption）继续存在；若行级 grammar 冻结后回补 W1，需同裁决处理 \s 差异（本件不联动）；
- `Fig\.?` 覆盖 `Fig. 4` 形；全角数字 `[0-9０-９]` 沿用 W1/W2 契约；
- 候选几何护栏（未冻结）：行宽下限——dev 实测 TP 全部 ≥117.4pt、唯一 FP 28.2pt，有干净分界但样本小，**参数数字留给裁决轮**。

---

## 3. 要素三：正负样本

### 3.1 正样本（必须覆盖；acad-03 r87q2 JSON 记录文本，space-folded 实样）

| unit | gold 题注文本（marker 前 40 字符） | grammar 判定 |
|---|---|---|
| u0015 | `Figure1:ExamplesofDocumentAITasks.` | **命中**（glued 冒号） |
| u0020 | `Figure2:Comparisonswithexistingworks(e.g` | **命中**（glued 冒号；r87q2 行实录 `'Figure2:Comparisonswithexistingworks(e.g.,DocForme'` 行首） |
| u0121 | `Figure4:Lossconvergencecurvesoffine-tuni` | **命中**（glued 冒号；行实录 `'Figure4:Lossconvergencecurvesoffine-tuningtheablat'` 行首） |

三条全部被最终 grammar 覆盖，无需再迭代。

### 3.2 负样本（必须排除）

| 负例 | 来源 | 判定 | 排除机制 |
|---|---|---|---|
| **u0038** `Figure3givesanoverviewoftheLayoutLMv3.`（raw: `Figure 3 gives …`） | acad-03 页 2 叙述句（r88 指定 negative） | **正确排除** | 数字后无可见分隔符（`g`/空格）；同时实测：W1 \s 形 regex 对 raw 形**匹配 True**——证明 \s 删除必要 |
| `is shown in Table 5. We can see that either BERT or RoBERTa` | acad-02 p7 e0031（element 级命中） | 行级排除 / element 级 FP | 行级：keyword 非行首（行首是 `is`）；element 级 flattened content 无法区分 |
| `Table6.`（独行，w=28.2pt） | acad-06 p7（行级命中） | **行级 FP**（唯一） | 仅宽度护栏可排（28.2 vs TP≥117.4）；文本层面无解 |
| `Figure 4). Processing a page in our benchmark dataset re-` | acad-04 p5 换行引用 | 正确排除 | 数字后是 `)` ∉ 分隔符类 |
| `Table5presentsthenumberof…` | acad-06 p7 右栏叙述（glued 无分隔符） | 正确排除 | 无可见分隔符 |
| `in Fig. 4. The intersection of each pair…` | acad-05 p7（element 级命中） | 行级排除 / element 级 FP | 行级：keyword 非行首（行首是 `in`） |
| `Table 4. The PaperTab dataset was ex-` | acad-06 p7 e0033（element 级命中） | 行级排除 / element 级 FP | 同上（跨栏混排后 token 化） |

---

## 4. 要素四：验收证据面（实际执行统计）

**口径**：dev split AcadPDF 全部 4 篇（acad-02-layoutlm / acad-04-docling / acad-05-pubtables1m / acad-06-dmap），**覆盖 4/4 = 100%**。元素级 = 任务指定口径（读 `evaluation/stage9-eval-baseline-r3/parsed/fallback/<doc>.json` 的 type=paragraph 元素 content，无空格适配正则）；行级 = W4 规则在源 PDF `extract_text_lines()` 上的直接模拟（parser 侧真实形态）。探针脚本：`outputs/w4_probe_dev_acad.py`、`outputs/w4_probe_context.py`（均只读；log 同目录）。

### 4.1 候选统计总表

| 篇目 | 行级命中 | TP-new（纯增量，自 paragraph 切出） | DUP（既有同标签 caption 元素已覆盖） | in-other-caption（既有异标签 caption 元素内部污染） | FP | element 级命中 | element TP | element FP | 三正样本覆盖 | u0038 排除 |
|---|---|---|---|---|---|---|---|---|---|---|
| acad-02-layoutlm | 7 | 5（Table1/2/3/4/5） | 2（Fig1, Fig2） | 0 | 0 | 6 | 5 | 1（`Table 5. We can see`） | — | — |
| acad-04-docling | 7 | 6（Fig1/2/3/4/5/6） | 1（Table1） | 0 | 0 | 7 | 6 | 1（`Figure 6. For popular`） | — | — |
| acad-05-pubtables1m | 8 | 3（Fig1, Fig3, Fig4） | 5（Fig2, Tab1/2/3/4） | 0 | 0 | 4 | 3 | 1（`Fig. 4. The intersection`） | — | — |
| acad-06-dmap | 9 | 4（Fig1, Fig2, Table1, Table4） | 3（Table2, Table6, Fig3） | 1（Table3 行在 Table2 的 caption 元素 e0030 内部） | 1（`Table6.` 独行） | 7 | 5（含 Table5，行级漏） | 2（`Table6.`、`Table 4. The PaperTab`） | — | — |
| **合计** | **31** | **18** | **11** | **1** | **1** | **24** | **19** | **5** | **3/3** | **是** |

- 行级 FP 率 1/31 ≈ 3.2%；element 级 FP 率 5/24 ≈ 20.8%（4/5 为 spaced 形中行引用——element 级 flattened content 无行界信息，天然不可靠；**佐证 W4 应做在 parser 行级而非 JSON 后处理**）。
- 互补性：行级漏 acad-06 Table5（跨栏行记录污染，右栏子行首才是真行首）；element 级漏 acad-06 Table3（其宿主是 caption 元素而非 paragraph，超出任务指定扫描域）。两通道合计去重后 dev 上的可新增 caption 标签 = 19 个（18 行级 TP-new + Table5），加 1 个 in-other-caption 待裁决处置。

### 4.2 逐条 FP audit 结论（人工判读源 PDF 行上下文，`w4_probe_context.log`）

1. `Table 5. We can see…`（acad-02 p7）——行上下文 `is shown in Table 5. We can see that either BERT or RoBERTa / underperforms…`：叙述句引用，**FP**（element 级）。
2. `Figure 6. For popular generative AI…`（acad-04 p6）——行上下文 `…and the growing community, a few a[re] / … ing as depicted in Figure 6. For popu…`：叙述句中行引用，**FP**（element 级）。
3. `Fig. 4. The intersection…`（acad-05 p7）——行上下文 `in Fig. 4. The intersection of each pair of table column tentac…`：图内说明性叙述引用（mid-line），**FP**（element 级）。
4. `Table 4. The PaperTab dataset was ex-`（acad-06 p7）——跨栏混排叙述，**FP**（element 级）。
5. `Table6.`（acad-06 p7）——行上下文 `…The results are presented in / Table6. / [左栏] 4.4 MechanismAnalysisofDMAP / Overall, stronger models…`：右栏窄列换行把句尾 `Table 6.` 挤成独行（w=28.2pt），行首+句点分隔符全中——**行级 FP**，唯一文本无解、仅几何可排的样本（真 Table6 题注在 p8 已有 caption 元素 e0035，无净伤害但产生一条假候选）。

### 4.3 与 W1 既有 caption 通道的关系（去重规则输入）

- **DUP（11 条）**：题注行已在段首通道成 caption 元素（gap > 1.5×median_h 使其独立成段 + W1 regex 命中）。去重规则建议：同页 + 行 bbox ⊂ 既有 caption 元素 bbox + 同标签（figure/table 族 + 序号）→ 跳过，不重复发射。
- **TP-new（18 条）**：宿主为 paragraph（行 gap ≤ 1.5×median_h 被并段，acad-02 Table 题注 gapPrev 仅 3.21-5.24pt、acad-06 Fig1 gapPrev 0.68pt、acad-05 Fig1 gapPrev −6.61pt 与图区重叠——**题注与图表/正文行天然紧贴，正是被并段的原因**）。
- **in-other-caption（1 条）**：Table3 行在 Table2 的 caption 元素内部（e0030 content 吸收了表格体行 + 下一题注行）：从 caption 元素中再切行属于二次修正，处置留裁决。

---

## 5. 风险与未决问题

1. **行宽护栏参数未冻结**：dev 实测 TP≥117.4pt vs FP 28.2pt 分界干净，但 4 篇样本外推性弱；且中文/单栏窄版式下限未知。裁决轮需决定：是否加宽度下限、取值、以及是否列入 schema 契约披露。
2. **跨栏行污染**：y 带行重建把左右栏文本合并（acad-06 Table5 实例）。可选确定性增强：行内按 x-gap 聚类分栏后在**子行首**再测 grammar（纯几何，无语义）。收益/复杂度比 = 1/19 TP（dev），是否纳入留裁决。
3. **in-other-caption 二次切分**（Table3-in-e0030）：是否允许从 caption 元素中段再切出新 caption 元素（会改变既有元素 content，影响下游 chunk 不丢不重测试基线），留裁决。
4. **段落 content 变更的下游影响**：切行后宿主 paragraph content 收缩，chunker 输入变化 → Layer B 四指标既有基线会移动；需要实现批次自带 before/after 对照（本件不承诺方向外的数字）。
5. **docx 侧不适用面**：python-docx 的 w:p 是真实段落，题注天然独立成段且 `_is_caption`（L885）已按段文本判型——W4 的"行吸收"问题在 docx 不存在；W4 限定 PDF 侧，docx 通道零改动。
6. **glued PDF 与非 glued PDF 并存**：dev 实测 acad-02/04 部分行有空格（非 glued），grammar 的 `\s*`（keyword 与数字间）+ 可见分隔符已双形适配（spaced `Figure 1:` 与 glued `Figure1:` 均命中）；但 spaced 形在 element 级后处理通道不可靠（FP 4/5 来自 spaced），再次支持 parser 行级实现。
7. **退化路径**：行 bbox 缺失/行退化（宽≤0）→ 放弃切分保持现状；不引入新错误码（本件层面；实现批次再定错误契约）。
8. **u0038 类残余风险**：可见分隔符要求排除 "gives" 形，但排除不了"行首恰逢引用 + 句点分隔"形（`Table6.` 类）。dev 上频率 1/31；中文域（全角、顿号）未验证。
9. **acad-03 split 事实更正**：任务简报称 acad-03 属 dev，manifest 实测 holdout；本调查以 r87q2 诊断件记录文本 + dev 四篇全量统计完成，未触碰 holdout 内容。若后续批次需在 acad-03 上验收益，须单独授权（holdout 纪律）。

## 6. 对评测面的预期影响方向（定性，不承诺数字）

- **Layer C（题注面）**：元素层 caption 补齐直接扩大几何配对规则输入集 → has_caption/table_has_caption 召回方向为**升**（r87q2 反事实：acad-03 语境下 7/8 失败边 typing 修正即可被现行 50pt 规则命中）；精确率方向取决于 FP 样护栏（`Table6.` 类假候选若成元素，可能生成错误边）。W2 显式引用通道的 caption-label 解析亦受益（更多带标签题注 → 更少 ordinal_fallback 依赖）。
- **Layer B（结构四指标）**：paragraph 元素数量/边界变化（题注行移出 paragraph）→ element 计数按类型的 alignment、chunk 边界对齐指标会**移动**（方向不定，取决于 gold 的 caption 标注密度）；dev 四篇合计 19 个可新增标签意味着 caption 类召回有实质上行空间，但四指标是宏平均，净方向以实现批次实测为准。

## 7. 声明

本件为 **W4 调查 + 规格草稿**（r88-Q3 授权范围：investigation + spec only）。所有数字来自探针脚本实测重放（`outputs/w4_probe_dev_acad.py` / `outputs/w4_probe_context.py`，只读，零估值）；不含任何 `app/` 实现授权、参数冻结授权或 git 操作。四要素中唯一冻结的是 grammar 的 spec 形态（§2.2 迭代 2）；宽度护栏、跨栏增强、in-other-caption 处置、W1 \s 联动均为未决项，待裁决轮。
