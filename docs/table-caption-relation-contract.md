# 表格题注关联契约（Stage 6 批次 7）

状态：冻结 v1（2026-08-30 批次 6 封口裁决有条件授权 + Option A 选定：
schema_version 升 0.5.0；执行顺序①–⑦按裁决原文）。

裁决依据：会话 cf170a6f 批次 6 封口裁决——批次 7 复用批次 4/6 成熟
框架、匹配器签名冻结不改、新契约先行 + 全新 holdout 字节固定；版本
政策成文 docs/schema-version-policy.md §3.2（新增 relation type 升
minor）。**Claude 选定 Option A（升 0.5.0）**，理由：与 0.2.0→0.4.0
"版本=writer 能力"沿革一致；consumers 需逻辑更新才能处理新 type。

## §0 盘点（2026-08-30，devset 实测）

- 表题注 caption element 仅 fallback 产出（`_CAPTION_RE` 含
  `Table|表` 前缀，分类口径不动）。
- devset DC-MVP-001（docx）实测：caption e0012 "Table 1. Module
  status matrix" @para:12 紧邻 table e0013 @tbl:0 **之前**（表题注
  惯例在表上方，与图相反）；DC-MVP-001-PDF：表题注文本被 pdfplumber
  融合进前一段落（e0004 以 "2. Structured elements" 开头），无独立
  caption element → devset 上 pdf 表关联为 0 条（归因依据）。
- md/html/text/ipynb/kreuzberg 不产 caption element → 天然零表关联。
- 表 element 几何：pdf 有 page+bbox；docx table 用 table_index
  （与 caption 的 paragraph_index 不同族 → docx 邻接按 **elements
  列表顺序**（=body 迭代顺序）定义，不按 index 数值）。

## §1 范围（本批锁死）

- 仅 fallback pdf/docx 产出 `table_has_caption`。
- 方向固定：`from_id` = table element_id，`to_id` = caption element_id。
- 不改 caption 分类（`_CAPTION_RE`）；不改图题注 has_caption（批次 4
  冻结）；不改 chunker；图/表两类前缀集互斥（Figure/Fig/图 ↔
  Table/表格/表），一个 caption 至多属于一类。
- 评测侧：匹配器 `match_relation_pairs` 签名冻结不改（批次 6 裁决），
  仅以 `relation_type="table_has_caption"` 调用；**不新增报告指标族**
  （annotation v1.0 无表格题注 GT 键、devset 零标注——结构先行无信息
  量，table_caption_* 指标族留待有标注时批次再议，届时按 REPORT_VERSION
  快照政策升版）。EVALUATOR_VERSION 维持 1.8（评测能力未变）。

## §2 表题注前缀集（冻结）

`^(?:Table|表格|表)\s*[0-9]+[\.、\s]`（ASCII 数字；大小写语义沿现状；
`表格` 在 alternation 中先于 `表`，longest-first）。`Figure|Fig|图`
前缀的 caption 不是表题注（反之亦然）。与批次 4 图题注前缀集构成
互斥划分。

## §3 判定规则（确定性；端点缺失/歧义一律不生成）

### docx：紧邻上一元素（表题注在表上方）

对每个 table element（elements 列表位置 i，i>0）：仅当位置 i−1 的
元素是 caption element 且以表题注前缀集开头时，生成一条
`table --table_has_caption--> caption`。i=0（表是首元素）不生成；
一表至多一 relation；一个 caption 至多被一表命中（列表位置唯一）。

### pdf：同页上方几何紧邻（镜像批次 4 下方规则）

候选条件（全部满足）：
1. caption 与 table 同 `page`；
2. 表题注前缀集开头；
3. `gap = table.bbox[1] − caption.bbox[3] > 0`（题注在表上方；
   pdfplumber 坐标，下方为正方向的镜像）；
4. `gap ≤ CAPTION_MAX_GAP_PT = 50`（与批次 4 同冻结值）；
5. x 方向区间相交（`min(t.x1,c.x1) − max(t.x0,c.x0) > 0`）。

全局唯一配对：候选 (table, caption, gap) 按 `(gap, table_id,
caption_id)` 升序依次配对，端点已配则跳过（与批次 4 同构）。

`metadata.rule`：docx=`"docx_adjacent_element_above"`、pdf=
`"pdf_geometry_above"`；不写 gap_pt（pdf 可加，同批次 4 语义：
`gap_pt` = 上述 gap，仅 pdf、number ≥ 0）。缺失行为：无表/无表题注/
候选不满足 → 零 relation（不报错不 warning；关联是能力不是义务）。

## §4 版本语义（Option A）

- `SCHEMA_VERSION_TABLE_CAPTION = "0.5.0"`；`effective_schema_version()`
  无条件返回 0.5.0（writer 能力语义）。
- schema：enum 加 0.5.0；分支——{0.1.0,0.2.0,0.3.0} 拒 has_caption
  （现状）**且** 拒 table_has_caption；{0.4.0} 拒 table_has_caption；
  {0.5.0} 不新增必填项（无表文档 relations 空合法）。
- relations 输出排序维持 `(type, from_id, to_id)` 字典序（含两类
  type 混排）；同一三元组至多一条（构造保证，测试固化）。

## §5 不变量

- caption/table element 的 content/type/locator/metadata 不因本批
  改变；has_caption 语义与产出不变；chunker 与 chunk 形状不变。
- Determinism：同输入字节 + 同 parser 版本 → 同 relation 集（含排序
  与 gap_pt）。
- 批次 5 表格线性化 content 不受影响（本批只加 relation）。

## §6 契约测试与 holdout

- 纯函数（输入 elements 列表，输出 relations）直接喂构造 elements：
  docx 紧邻上方命中 / 紧邻下方不命中 / 前元素非 caption 不生成 /
  图题注前缀不关联 / 首元素表不生成；pdf 同页上方命中 / 下方不命中 /
  超阈值 / 非重叠 / 多对多唯一配对；两类 type 混排排序；版本分支
  （0.4.0 拒 table_has_caption、0.5.0 含与不含均合法、0.3.0 双拒）。
- **评测消费路径（裁决步骤④）**：合成 docx → fallback 解析 →
  `match_relation_pairs(..., relation_type="table_has_caption",
  from_marker_key=..., to_marker_key=...)` 返回真实匹配计数（签名
  不改仅传新 type；GT 键名届时由 annotation 版本升级批次定，本测试
  用构造 pairs）。
- dev 验收断言（skipif 无私样）：DC-MVP-001 docx
  `e0013 --table_has_caption--> e0012`；PDF 零表关联（§0 归因）；
  引用固定基线 commit。
- **holdout（裁决步骤⑤，三类 case）**：合成 docx 生成一次字节固定
  （sha256 登记 ADOPTION.md）：T1 表题注在上（命中）、T2 无题注
  （零）、孤立表题注段落（无邻接表，零）、图题注紧邻表上（前缀互斥
  不命中）——四 case 覆盖裁决三类 + 互斥负例。期望 elements +
  relations 全清单在 parser 运行前手工推导冻结；固定干净 SHA 一次性
  首跑封存 outputs/，永不重跑。pdf 沿批次 3/4 追认先例不进 holdout
  （几何 bbox 手工推导=预跑），dev 验收引用固定哈希；md/html/text/
  ipynb 以回归断言零 table_has_caption。

## §7 明确不做（本批）

- 不新增 table_caption_* 报告指标族 / 不改 annotation.schema.json
  （GT 键留待标注存在时议）。
- 不做跨页表、嵌套表、合并单元格特殊语义。
- 不做表题注在表下方的 docx 关联（惯例在上；devset 实证）。
- 不改 EVALUATOR_VERSION（1.8）/ REPORT_VERSION（1.3）。
- 不改批次 6 match_relation_pairs 签名（裁决冻结）。
