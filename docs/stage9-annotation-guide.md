# Stage 9 批次 26 — 正式标注指南（句子级 gold 标注）

依据：docs/stage9-batch26-design.md §3/§6 + 步骤 1 封口裁决补录 B
（ARI 分母、N/A 与失败计数规则，禁止静默排除）。
配套实现：`stage9/validation.py`（校验器）+
`scripts/stage9_validate_annotations.py`（CLI）。
标注文件存放：`samples/private/stage9-corpus/annotations/<doc_id>.json`
（gitignored，永不进 git）。

## 1. 标注对象与 ARI 原子单位

- 标注对象 = **人眼可见的正文句子流**（按人眼阅读顺序，多栏 PDF 按栏序
  先左后右，**不迁就任何系统输出**——系统多栏提取弱是已知限制，标注
  恰恰要暴露它）。
- **heading（标题）= text unit，参与 ARI**，与句子同流、同 gold_segment
  规则。
- **图像/表格 = nontext unit，不参与 ARI**：不进句子流、char_span=null，
  以 `nontext_ref`（`img:…`/`tab:…`）登记并挂 gold_segment；正文 unit
  可用 `linked_nontext` 引用它（关联指标单独计）。
- 页眉页脚、页码、水印：不进句子流也不登记 nontext（非内容单元），
  在 notes 里说明处理口径即可。
- **出版方模板块（2026-09-10 十二轮裁决 O1）**：标准 ACM
  publisher-supplied boilerplate（Reference Format 引用块、
  permission-to-copy / 版权印记、ISBN/DOI 出版信息块等）**不进入
  stream**；已入流的删除（窄幅归一），未入流的维持排除（不做机会性
  扩展清理）。作者/机构记录仍按 §3.1 批准规则处理；作者自有的 CC 类
  声明保留（每条声明一条目）。

## 2. 规范化字符流（fold-ws-v1）

1. 将全文正文文本（含标题）按阅读顺序拼接；
2. 规范化：**所有空白（含换行/制表）压成单个空格，两端 strip**
   （与既有"分块不丢不重"测试同源规则）；
3. 结果即 `stream` 字段，必须满足 `fold_ws(stream) == stream`
   （校验器检查 `stream_not_folded`）。

**平铺规则**：text unit 的 char_span 必须连续、无重叠、全覆盖整个流；
unit 之间的分隔空格**归入前一 unit 的 span 末尾**
（如流长 48、三 unit → `[0,18) [18,33) [33,48)`）。
首个 unit 从 0 开始，末个 unit 止于流长。校验器对
`span_gap`/`span_overlap` 报错。

## 3. 句子切分规则（冻结 v1，人机同规）

- 中文：按 `。！？；` 切分（句末符号归前句）；
- 英文：`.`/`!`/`?` 后随空白 + 大写字母或数字才切；
- 缩写白名单**不切**：`Fig. Eq. et al. Dr. No. vs. i.e. e.g. etc.`；
- 省略号（`…`/`...`）不切；
- 标题整体一个 unit，不再按内部标点切分。

标注人按上述规则人工判定；与机械切分器的分歧不构成错误，以人工判定
为准并在 notes 记录争议例。规则一经冻结不改；发现缺陷须升 v2、全量
重切并登记变更（走裁决）。

### 3.1 结构化条目区：条目边界优先（2026-09-09 GPT 裁决 R3'）

无标点文本区（参考文献、作者块、版权/许可块）此前按"人工判定为准"
存在两种读法（per-entry 语义切 vs 视觉行/整块字面切），本节定为
**人工判读特区**：对可从来源辨识的结构化逻辑条目，**先按条目边界
强制 unit 断开，再在条目内部按冻结 v1 切分**。条目首 unit
`hard_boundary_before=true`（条目边界=语义边界；区段标题仍按标题
规则）。

**适用范围（锁定，禁止自由扩展）**：
1. 参考文献/引用条目区——一条完整文献条目 = 一条目；
2. 作者/机构信息块——一条可辨识的作者/机构/元信息记录 = 一条目；
3. 版权/许可元数据块——一条独立声明/条目 = 一条目；
4. 其他区仅在本指南明确列定时适用（本轮未列定）。

**条目边界证据**（判读依据，写入 builder 注释/判读表）：
编号标记（`[1]` `[2]`…）、项目符号、悬挂缩进、独立段落/记录单元、
显式字段边界。

**三锁（R3' 原文语义）**：
- 锁一：**视觉换行 ≠ 条目边界**——折叠排版（一条文献折成多行）仍是
  同一条目，不得按行切 unit；
- 锁二：**条目内部仍走冻结 v1**——条目内有真实句子边界（句末标点
  等）则条目可产生多个 unit；条目内无切分点则整条目一个 unit；
- 锁三：**图内文字不转写**——子题注等以像素形式存在于图内的文字
  不进 stream，本节规则不改变该政策。

**preamble 契约（2026-09-10 十二轮裁决补正）**：entry override 从
第一个被识别的 entry start 开始生效；其前连续 preamble 合并为单一
组并**回落冻结 v1**，不得按物理行人为分组（换行本身不是边界，
锁一；已有 block/heading hard boundary 保留）。

**三通道使用范围契约（2026-09-10 十二轮裁决）**：NUM/LABEL 正则与
显式起始行三通道只在**显式指定为 structured entries 的目标块**内
运行（builder/assembler 的 entries 块必须显式给出边界判断）；宽泛
的 LABEL 正则不得成为普通文本块的全局自动探测器。

本节为**切分政策修订，不升 schema 版本**：`sentence_splitter` 仍为
冻结 v1，本规则只在条目区增加"先断条目边界"这一划分层。工具支持：
一级标注 builder 与第二标注人工具
（`scripts/stage9_user_annotate.py` assemble）均提供 entries 块类型
（blocks 只存来源区间与条目边界判断，机械折叠 + 条目内 v1）。

## 4. 字段填写规范

格式版本 `annotation_schema`（冻结值 `v1.1`，2026-09-05 GPT 裁决
C1/C2 正式化）：v1.0 = 设计 §3 原字段；v1.1 = ①`stream` 由实现偏差
转正为正式字段——norm_hash 复算与 span 全覆盖检查以它为唯一基准；
②page 语义收紧为"只表物理页码"，新增 `body_index`。

```json
{
  "doc_id": "acad-01-sentencebert",
  "annotation_schema": "v1.1",
  "sentence_splitter": "v1",
  "normalization": "fold-ws-v1",
  "annotator": "claude-draft + user-review",
  "stream": "<规范化字符流全文（fold-ws-v1）>",
  "units": [{
    "unit_id": "u0001",
    "kind": "heading | sentence | nontext",
    "page": 1,
    "body_index": null,
    "char_span": [0, 18],
    "norm_text_hash": "sha256:<stream[a:b] 的 sha256 十六进制>",
    "text_preview": "<stream[a:b] 的非空前缀，≤60 字符>",
    "nontext_ref": "img:figure1 | tab:table2（仅 nontext unit）",
    "gold_segment_id": "g01",
    "hard_boundary_before": true,
    "linked_nontext": ["img:figure1"]
  }],
  "segments": [{"gold_segment_id": "g01", "hint": "标题+摘要",
                "kind": "frontmatter"}]
}
```

硬性约束（校验器逐项检查，失败码见 §8）：
- `annotation_schema`：必须为冻结值 `v1.1`；
- `unit_id`：`^u\d{4,}$` 且全文件唯一；
- `kind`：三值枚举；text 类（heading/sentence）必须有合法 span 与
  hash；nontext 类 `char_span`/`norm_text_hash` 必须为 null、必须有
  `nontext_ref`（`^(img|tab):\S+$`，全文件唯一）；
- `page`：**只表物理页码**（人眼所见页码，PDF 用印刷页码所在 PDF
  页序）；null 或 ≥1 整数。DOCX 无物理页码 → 全部 null，定位改用
  `body_index`；同一 unit 两者互斥（禁一字段两义）；
- `body_index`：null 或 ≥1 整数（**解析器定义的 DOCX body block 的
  1-based 源序**，非 unit 序；一个 body block 产生多个 unit 时允许多个
  unit 共享同一 body_index，不为制造 unit 级连续值而重新编号——
  GPT 裁决 2026-09-05 C2 补充定义）；PDF 篇必须 null；
- `char_span`：半开区间 `[start, end)`（end 不含），0 ≤ start <
  end ≤ 流长；text unit 在 `units` 列表序中的 span 单调递增
  （列表序 = 阅读序 = 流序）；text unit 的 span 集精确覆盖全流
  （连续无重叠无间隙）；**unit 间分隔空格归前一 unit 的 span 末尾**
  （平铺规则：unit_i 的 end = unit_{i+1} 的 start）；
- `norm_text_hash`：仅按 `stream[span[0]:span[1]]` 字节复算（不从
  源文档推导）；
- `text_preview`：unit 文本的非空前缀且 ≤60 字符；
- `gold_segment_id`：每个 unit（含 nontext）必须引用存在的 segment；
  每个 segment 必须被 ≥1 unit 引用（双向闭合）；
- `linked_nontext`：可省略；出现则每项必须是文件内存在的 nontext_ref。
  **关联 gold 语义（七轮裁决 B1，2026-09-07 升格为正式结题指标
  gold）**：linked_nontext 表示**无类型的、人类判定的 text→nontext
  语义锚定边**，gold 单位 = `(text_unit, nontext_ref)`——不是
  "有 caption"之类的 relation type。锚来源三类：①题注锚——题注
  作为独立 text unit 链接其明确描述的图/表；②显式引用锚——
  "见图 X/如表 3 所示"等明确指称成边（一句引多对象分多条边、一
  对象被多处引用允许多边）；③隐式锚——仅当文本语义+页面/结构
  关系能**唯一或明确确定**目标对象时成边（**proximity 可作判读
  证据，但不得单独成为 gold link 的充分条件**；多候选无法唯一
  确定即不建边）。装饰性/图标等确实无文本锚的对象允许保持
  anchorless；图内未转写进 stream 的文字不得虚构 text unit 建边。
  **确定性约束**：同一 text unit 禁重复 ref；多 ref 必须按目标
  nontext unit 在 units 列表（阅读序）中的顺序排列——语义相同的
  关系集合不得因填写顺序不同产生随机 gold hash（校验码
  `duplicate_linked_ref` / `linked_ref_order`；重复边必须校验失败，
  禁评测期静默去重）。**gold independence**（约束级纪律）：正则/
  检索脚本只能产生候选；每条边必须人工对照 PDF 核对；禁止读取
  本系统 parser 的 relations；禁止按当前系统预测结果决定加/删边；
  禁止为提高未来关联指标调整 gold 范围。施加工具
  `scripts/stage9_link_apply.py`（只改 linked_nontext，越界拒绝
  写盘；links 判读表存 samples/private 层）。

## 5. gold_segment 判定（语义段 = 主题内聚的知识单元）

- 一个 gold_segment = 人在通读时愿意用一句话概括的连续正文段
  （如"引言动机"、"方法概述"、"实验设置-数据集"）；
- 粒度基准：典型论文 8–20 个 segment；手册类按小节语义归并
  （一个三级小节 ≈ 1 个 segment，可并可拆，以主题内聚为准）；
- segment 边界必须落在 unit 边界上；`kind` 可选常用值
  frontmatter/body/related/conclusion/appendix（自由文本也允许）；
- **纪律：逐句人工查阅原文推导，禁止用任何系统输出（本系统或基线）
  反推**；holdout 集标注先于任何系统/基线在其上的解析运行。

## 6. hard_boundary 判定

`hard_boundary_before=true` 标记人工确定的硬边界（章节切换、主题显著
转折）。判定标准：后续内容开新话题且不延续上一 segment 的概括。
第一个 unit 恒为 true。

## 7. 双标注与仲裁

- 双标注 4 篇（2026-09-06 裁决轮4 定稿，不因 prod-06/prod-09 入库
  重抽）：dev = `tech-03-cncert-annual2020` + `prod-01-python-tutorial`；
  holdout = `acad-03-layoutlmv3` + `tech-08-cnnic57`（全部 PDF）。
  第一标注人 = Claude 草案，第二标注人 = 用户独立复核（不看 Claude
  草案）；
- 比对口径：unit 级（切分一致 + gold_segment 一致）；
- nontext 对齐键 = 家族(img/tab)+物理页（`v3-page-family-bounded`，
  2026-09-07 裁决 B/B'/B'' 三轮落定）：**不含任何按标注自身 nontext
  出现顺序的编号**（序号须来自共同源注册表且不随多登/漏登漂移——
  而机械注册表（page.images/find_tables）经实证无法枚举语义图形：
  栅格碎片与语义图 1:N、矢量图 0:N、FTAB 假阳性大量存在，source
  ordinal 不可表达，故取零编号的页族粒度）。计数层精确：多登/漏登
  只影响该对象自身的并集计数（matched/union 不随组内配对漂移）。
  同页同族 **m×n>1** 的组（歧义组——双方均有对象且对应不唯一，
  **含 1×N/N×1**；1×1 唯一配对、单侧 0 对象无歧义）内"哪个 A
  对象与哪个 B 对象是同一视觉语义对象"无观测依据——结构位置配对
  仅为诊断；该组一致贡献按**所有合法一对一配对**取区间
  [lower, upper]（各配对贡献相同时自然退化为单值），全篇合成
  agreement_lower / agreement_upper；
- 判定（整数/有理数比较，阈值固定 17/20，不经二进制 float 边界）：
  20×lower ≥ 17×union → `pass`；20×upper < 17×union →
  `below_threshold`（照走仲裁）；其间 → `indeterminate`（阈值暂不
  可判定，非新增停机条件）→ 仅对跨线组做 **identity resolution**
  （解析者只看 PDF 页面+双方标注的结构位置、对 gold_segment 与得
  分盲态；只决定"哪个是同一视觉语义对象"，不得改任一标注人的
  切分/kind/segment；pair map 单独保存并记录 sha256，经 CLI
  `--pair-map` 代入后计算确定最终一致率）；
- 报告字段语义：`decision` = pass/below_threshold/indeterminate；
  `requires_action` = below_threshold ∪ indeterminate（CLI rc 1）；
  `below_threshold` 为严格兼容字段（= decision == below_threshold，
  不再兼指 indeterminate）；**对称性契约**：交换两份标注的 A/B
  角色，agreement_lower/agreement_upper/decision（及 matched/
  union/agree）必须逐字段相同；
- 一致率 = 一致 unit 数 / 双方 unit 并集数；**<85% 且仲裁不收敛 =
  停机条件**（区间跨线经 identity resolution 消解后同规）；
- 分歧清单记录于该文档标注文件的 `notes`（或仲裁记录文件），协商
  仲裁结果为准；仲裁修改 gold 后须重跑 validator；其余 20 篇用户
  抽查 ≥2 篇（可用 `scripts/stage9_annotation_report.py` 把标注
  JSON 渲染为人类可读视图对照 PDF——只读支撑件，仅呈现标注内容，
  报告头部含 `annotation_sha256`，抽查记录据此绑定所看的标注版本；
  判定仍以 validator/agreement 为准）。

  抽查结论记录口径（六轮裁决锁定）：渲染件本身只证明抽查材料
  就绪，**不证明义务完成**——完成证据=用户对照 PDF 的实际结论。
  结论若写入标注 `notes`（G⑥ 冻结前允许）须遵守：①只记录抽查
  事实，不改 stream/span/segment 等标注判断；②写入后重跑对应
  validator；③G⑥ 的 per_doc_sha256/gold_digest 基于写入 notes
  后的最终字节；④G⑥ 之后不得再为补抽查说明静默修改标注。结论
  若只记外部审计台账则不动标注字节，无上述字节影响。

### 7.1 操作流程（第二标注人）

零判断辅助工具 `scripts/stage9_user_annotate.py`（dump 摘行 /
assemble 组装+校验）：工具只做机械工作（逐行抽取、规范化、切分、
span 平铺、hash、schema 组装），一切判断由用户的 blocks 文件表达；
工具不读、不显示、不依赖第一标注人（Claude 草案）的任何产物。

1. dump 逐页行清单（稳定 ID：`pNNN` + 列标记 `L`/`R`/`C` + 行号；
   含字号/字体/x0、图片 IMG、表格检测 FTAB 提示）：

```bash
.venv/Scripts/python.exe -X utf8 scripts/stage9_user_annotate.py \
  dump --doc tech-08-cnnic57
# 默认写 outputs/userannot_<短名>_dump.txt（--stdout 直接打印）
```

   - `L`/`R` = 左/右半栏行（页面中线裁剪，双栏文档分栏干净）；
   - `C` = 跨中线整行（题名/整宽题注/跨栏表格行/单栏宽行）；单栏
     文档宽行同时以 L半+R半+C整 三键出现，引用 C 键即自动消费其
     两个半行（标 `≈Ckkk` 的半行勿单独引用，会判重复计数）；
   - `≈Liii+Rjjj` 标记 = C 行可分解为两个半行（同一视觉行）；双栏
     正文页上全页提取会把左右栏基线对齐行融成伪 C 行，同样带此
     标记——正文取 L/R 键，真全宽行（题名/整宽题注）取 C 键。

2. 对照 dump（与 PDF 原文）写 blocks 文件（Python；判断全部在此
   表达：哪些行入流、heading/para/lines 分类、语义段分组、排除项、
   图/表登记）：

```python
ANNOTATOR = "user-independent（自署）"
NOTES = "处理口径说明"
SEGMENTS = [("g00", "题名+摘要", "frontmatter"), ("g01", "§1", "body")]
EXCLUDE = set(P(1, "L", 3, 5))              # 可选：明确排除的行
BLOCKS = [
    (P(1, "C", 0),    "heading", "g00", True),   # 整行标题=1 heading
    (P(1, "L", 9, 27), "para",   "g00", False),  # 段落=冻结 v1 切句
    (P(1, "L", 28),   "lines",   "g00", False),  # 每行行内文字=1 unit（仅限
                                                #   行本身即完整语义单元处）
    (1,               "nontext", "g01", "img:fig-1"),
    (P(2, "L", 5, 60), "entries", "g08", False, r"^\[\d+\]\s*"),
                                                # 条目区（§3.1）：行序匹配
                                                #   该模式的行开新条目，条目
                                                #   内折行合并+冻结 v1；无
                                                #   编号条目区改用显式起点行
                                                #   号列表（见 §3.1）
]
```

`entries` 块（2026-09-09 R3' 裁决新增，用于参考文献/作者块/版权块，
**这些区禁用 lines/整块 para**）：第 5 元素 = 条目边界判断——
`re.compile` 模式（匹配行开新条目）或**显式起点行号元组**（该块行
序内的索引，无编号条目区用，如 `(0, 5, 9, 14)`）。块内首条目首
unit 的 hard 取 BLOCKS 第 4 元素，其后每条目首 unit hard=true。

3. assemble 组装 v1.1 JSON + 就地校验（校验失败不写盘；产物存
   `annotations-user/<doc_id>.json` 独立目录——`annotations/` 会被
   full-set 校验整目录吸入，用户复核件不得混入）：

```bash
.venv/Scripts/python.exe -X utf8 scripts/stage9_user_annotate.py \
  assemble --doc tech-08-cnnic57 \
  --blocks samples/private/stage9-corpus/annotations-user/blocks_tech-08.py \
  --dump outputs/userannot_tech-08_dump.txt
# --dump 核对行注册表指纹未漂移；未处理行清单须逐项确认（排除入
# EXCLUDE 或补引用），BLOCKS 顺序=阅读序
```

4. 单文件校验复核（assemble 已就地校验过，此步可选；须 0 失败再
   比对）：

```bash
.venv/Scripts/python.exe scripts/stage9_validate_annotations.py \
  --manifest samples/private/stage9-corpus/manifest.json \
  --annotations samples/private/stage9-corpus/annotations-user/<doc_id>.json
```

5. 一致率比对（rc 0 = ≥0.85；rc 1 = <0.85 停机线预警，是否停机
   仍须仲裁判定收敛性）：

```bash
.venv/Scripts/python.exe scripts/stage9_agreement.py \
  --a samples/private/stage9-corpus/annotations/<doc_id>.json \
  --b samples/private/stage9-corpus/annotations-user/<doc_id>.json
```

6. 分歧仲裁 →（如改 gold）重建标注+重跑校验 → ⑥gold 冻结。

### 7.2 identity resolution 辅助工具（裁决 B'/B'' 配套，只读）

`scripts/stage9_identity_view.py`——只读辅助，不改 agreement 语义：
- `plan`（操作员视图，`--json` 机器可读）：列未消解且贡献区间
  gap>0 的歧义组（贡献区间/matched/双方成员数），按整数比较复算
  **单独消解即可定判**标志（alone_pass = 该组取上界贡献整篇即
  pass；alone_below = 取下界即 below_threshold），供操作员选定应
  交解析的跨线组；整篇判定已定（不跨线）时明确提示无需 resolution；
- `blind`（解析者视图，盲态纪律工具化）：对选定组只输出 PDF 物理页
  +家族+双方 unit_id（阅读序）+各自前后相邻文本单元内容+需配对数
  matched（presence 信息，填合法 pair map 所必需）；**不输出
  gold_segment_id 与任何得分/贡献数值**。`--skeleton` 生成待填
  pair map 骨架（`{"家族|页": []}`，填恰 matched 对
  `[a_unit_id, b_unit_id]`、单射、仅用组内 unit_id）；
- 两子命令均支持 `--pair-map` 代入已填部分后显示**剩余**未消解组
  （多轮迭代：骨架逐组补齐，最终一次代入
  `scripts/stage9_agreement.py --pair-map` 得确定一致率）。
  退出码 0 正常 / 2 输入错误（组不存在、组已消解等）。

执行口径（五轮裁决 B 锁定）：
- **不为单值而解析**：bounded 区间已可判定（lower ≥ 0.85 或
  upper < 0.85）时质量门即闭合，**禁止**为得到标量而解析无关
  歧义组。正式结果的合法形态允许 `agreement_lower ≠
  agreement_upper` 且 decision=pass/below_threshold；仅
  indeterminate 才继续 identity resolution 至判定可确定；只有
  全部 positive-gap 组解析完毕才可报告唯一标量 agreement。
- **resolution 记录含盲态视图工具 commit**：pair map 的
  resolution 记录应注明生成盲态视图所用工具 commit（当前
  dabe8dd）——证明解析者实际看到的受限视图版本；非 scoring
  依赖，不改 agreement 主报告契约。
- 自比对冒烟仅作性能/接线 smoke；其组数量级估计**不作**质量
  证据或停机规则。

### 7.3 G⑥ gold freeze 凭证（格式预裁定，签发须待 ⑥ 正式申请）

文件：`samples/private/stage9-corpus/
gold-freeze-credential.stage9-b26-gold-r1.json`（私有 gitignored，
永不进 git；**版本化文件名**，签发并计算 SHA 后即 immutable。
core gold 若在冻结后再须改动，不得覆盖 r1——重新裁决签发
stage9-b26-gold-r2 并保留 r1 凭证与哈希链）。

- `gold_revision` 固定形如 `stage9-b26-gold-r1`（stage-batch-
  对象-rN 单调；日期只进 `issued_at`，不承担版本身份）；
- `per_doc_sha256` 记录**全部 24 core**（与 gold_digest 同域，
  凭证可独立展开自证；G⑦ 报告另披露 14 篇
  dev_annotation_hashes，职责不同：24 = 完整 gold 身份，
  14 = 调参输入审计）；
- `digest_definition` 固定五要素：algorithm=sha256、编码 UTF-8、
  排序=doc_id ascending、单行格式 `{doc_id}:{file_sha}\n`、
  范围=24 core；
- `double_annotation` 每篇记录：decision、agreement_lower/
  agreement_upper、**可空** agreement_final（仅区间真正塌缩为
  单值时填）、secondary_annotation_sha256、
  agreement_implementation_commit、pair_map_sha256（无则
  null）、仲裁状态——门槛已定但存留无关歧义时**不得虚构标量**；
- validator 记录：validator/代码 commit 或版本、检查范围、结果、
  执行时间（不只 failures=0）；
- credential 最终字节 SHA **不写入自身**（非自指）；外部记录于
  台账 G⑥ 冻结凭证段 + G⑦ 报告 provenance 字段
  `gold_credential_sha256`（附加 provenance，不改 authoritative
  prereg）。

G⑥ 封口顺序（不得倒置）：四篇判定/必要 resolution → 必要仲裁
（如改 gold 先改 gold 再重跑 validator）→ 最终 gold validator
（在最终 gold 字节状态重跑）→ 24 篇逐文件 hash → 计算
gold_digest → 写 credential → 计算 credential SHA → 外部台账
登记 credential SHA。

### 7.4 关联 gold 补链与 G⑥ 新增前置项（七轮裁决，2026-09-07）

- **执行边界（B2 硬边界）**：补链 pass 只能修改 linked_nontext 及
  必要的非判定性审计说明（notes），不得顺手修改
  text/span/kind/gold_segment/hard_boundary/nontext_ref 或增删
  unit。补链中发现原一级标注真实缺陷（漏图表/错切句/segment 错误）
  时**不得顺手修**：停该文档补链 → 单独披露原 gold defect → 另行
  裁决是否允许结构修订（四篇双标注文档尤其如此——结构修订可能
  影响进行中的 G⑤ agreement）。relation 标注与 segmentation 修订
  严格分流。
- **G⑥ 新增前置项**（在原 ⑤ 四篇收敛之上）：
  1. 24 core 关联补链完成；
  2. --full-set / validator 通过（含 B1 确定性约束与新关联统计）；
  3. **relation 专项独立抽查通过**：≥2 篇 core、≥2 个 domain、所选
     文档须实际存在 linked pairs——逐条核对两篇全部 positive
     linked pairs + 每篇再查 ≥10 个 anchorless nontext 对象（不足
     10 全查）确认无明显漏锚。默认复用用户正抽查的
     prod-05 + tech-01（product + tech，两篇补链后有边即可）；
     若用户的 segmentation 抽查先于补链完成，relation 部分用补链
     后最终字节做一次针对性复核即可，无须重做切分抽查。
- **未来指标边界（本轮锁住）**：linked_nontext 是无类型边 gold。
  将来基于它计算的 P/R/F1 只能称为 **untyped text↔nontext
  relation edge precision/recall/F1**，不得声称 caption /
  explicit-reference / implicit-anchor accuracy（gold 未保存
  relation type）。系统侧 typed relations（has_caption /
  table_has_caption）届时须先归一化为"是否存在 text→nontext 边"
  再对比，或另行申请 typed-relation gold 扩展；不得为实现便利把
  relation type 塞进 linked_nontext。

## 8. 校验

```bash
.venv/Scripts/python.exe scripts/stage9_validate_annotations.py \
  --manifest samples/private/stage9-corpus/manifest.json \
  --annotations samples/private/stage9-corpus/annotations
```

退出码：0 通过 / 1 存在失败 / 2 输入错误。失败码：`frozen_value`
（含 `annotation_schema` 版本）`stream_not_folded` `bad_unit_id_format`
`duplicate_unit_id` `bad_type` `unit_order` `dual_locator`
`locator_format_mismatch` `span_out_of_range` `span_overlap` `span_gap`
`hash_mismatch` `preview_mismatch` `span_not_null_nontext`
`bad_nontext_ref` `duplicate_nontext_ref` `unknown_nontext_ref`
`duplicate_linked_ref` `linked_ref_order`（七轮裁决 B1 确定性约束）
`unknown_segment` `unreferenced_segment` `duplicate_segment_id`
`missing_field` `doc_not_in_manifest`；manifest 一致性检查（D1，
2026-09-06 裁决轮4）始终执行，追加 `manifest_consistency_failure`；
`--full-set` 追加
`split_count_mismatch` `split_domain_coverage` `missing_annotation`
（冻结终检用）+ **关联统计披露**（七轮裁决 B3，从标注字节现场重算，
纯诊断无阈值）：`linked_pairs`（去重边数）/`linked_objects`/
`anchorless_count`/`nontext_total`，恒等式
linked_objects + anchorless_count = nontext_total 由构造保证。

## 9. ARI 分母、N/A 与失败计数规则（封口裁决补录 B）

**总原则：禁止静默排除。** 任何文档/块/unit 不进 ARI 计算都必须有
明确的 reason 码并进入计数披露；报告必须同时给出"计入 ARI 的数量"
与"N/A 及原因分布"。

| 情形 | ARI 处理 | 计数披露 |
| --- | --- | --- |
| 解析失败（非零错误码/异常） | 该文档 ARI = N/A，reason=`parse_failed` | 计入解析成功率分母与失败计数 |
| 空结果（<10 元素或规范化字符 <200） | ARI = N/A，reason=`empty_result` | 保留在语料计数 |
| 图/表零提取（人眼可见但系统没提取） | ARI 不受影响（nontext 本就不参与） | 计入非文本关联指标（召回缺失） |
| 预测 chunk 在字符流上定位失败 | 该 chunk 不产生归属 | `unmatched_chunk_count` 单列 |
| unit 不与任何 chunk 相交 | 该 unit 不进 ARI 求和项 | `uncovered_unit_count` 单列 |
| unit 跨多 chunk | 按最大重叠归属唯一 chunk | `cross_chunk_unit_count` 单列 |
| 标注缺失/校验不过 | 该文档 ARI = N/A，reason=`annotation_invalid` | 禁止剔除语料，修复标注后重跑 |

- **文档级 ARI 分母** = 该文档中被 ≥1 个 chunk 覆盖的 text unit 数
  （即进入 contingency 表的 unit）；heading 计入、nontext 不计入。
- **集级 ARI** = 有 ARI 文档（非 N/A）的 macro average；N/A 文档数
  与 reason 分布为必报字段，缺一即报告无效。
- 解析期表现（失败/空结果/零提取）**一律保留并计入指标**；冻结后
  替换文档 = 停机条件（须单独裁决）。
