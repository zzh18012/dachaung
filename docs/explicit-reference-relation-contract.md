# 显式引用关联契约（W2 explicit reference，design freeze v1）

状态：design freeze v1（2026-10-09，r85 Q2 授权实施；实现前冻结）。

裁决依据：r85 Q2(a) 边类型与方向、Q2(b) 入 Phase 2 首批（实施序
W1 实现 → W2 design freeze → W2 实现）、Q2(c) 编号→元素映射 v1 语义
（document-order + same label number + deterministic only；禁 OCR /
embedding similarity / nearest visual matching / probabilistic
fallback）。关联规格：adoption 线 design/relation-generation-spec-v1.md。

## §1 范围

- 仅 fallback pdf/docx 产出 `references_figure` / `references_table`。
- 检测面：paragraph / heading / list_item 元素 content 内的显式图表
  编号引用（"as shown in Figure 3" / "见表 2" 型）。
- caption 元素**不作为 from 侧**：题注附着归 has_caption /
  table_has_caption 通道（批次 4 / 批次 7 契约），题注文本对自身的
  前缀提及不构成引用边。
- md/html/text/ipynb/kreuzberg 维持 relations 现状（不产出）。
- v1 明确不做：OCR、embedding、nearest visual matching、
  probabilistic fallback（r85 Q2(c) 红线）。

## §2 边形状冻结

- `type = "references_figure"`：`from_id` = 文本元素 element_id，
  `to_id` = image element_id。
- `type = "references_table"`：`from_id` = 文本元素 element_id，
  `to_id` = table element_id。
- 方向语义：source mention → target object（r85 Q2(a)：provenance
  优先于查询友好的 referenced_by 反向）。
- metadata（全部必填）：
  - `resolution_method = "ordinal_document_order"`（r85 Q2(c) 裁决
    常量，两路径统一取值）
  - `confidence = "deterministic"`（裁决常量）
  - `label_source` ∈ `{"caption_label", "ordinal_fallback"}`（目标
    解析路径，见 §4）
  - `label` = 原始匹配串（如 `"Figure 3"` / `"表2"`）
- 排序与去重：`(type, from_id, to_id)` 字典序稳定排序（与既有
  relation 集同规）；同一三元组至多一条。

## §3 提及检测（mention regex，大小写不敏感）

- figure 家族：`(?:Figure|Fig\.?|图)\s*([0-9０-９]+)`
- table 家族：`(?:Table|表格|表)\s*([0-9０-９]+)`
- 全角数字允许（与 `_CAPTION_RE` 分类口径一致，捕获后归一半角）。
- **不设拉丁词边界环视**：acad PDF 无空格抽取的 glued 形
  "…wordFigure3…"（acad-03 实测 10 处，多于分隔形 4 处）是主目标
  形，环视会挡掉它。代价 = 词内噪声（"turntable 5" 命中
  "table 5"）——v1 已知噪声面如实接受（罕见 vs glued 主形），
  determinism 不受影响，precision 影响由 Layer C 端到端度量。
- CJK 无空格分隔（"如图3所示"）自然命中——"报表 3" 类中文误命中
  同为 v1 已知噪声面。
- 数字后不要求分隔符（pdfplumber 无空格抽取形 "inFigure3the" 必须
  命中——与 W1 题注层的差异：引用提及本就出现在句中任意位置）。
- 同一元素内同 label 多次提及去重为一；不同 label 各成一条。

## §4 编号→对象解析（两层，全确定性）

1. **caption-label 层**（label_source = caption_label）：label N →
   文档序第一个"携带标签 N"的对象。标签来源 = 该对象经
   has_caption / table_has_caption 边附着的题注元素文本，其前缀
   匹配 §3 同族正则且捕获数为 N。同标签多对象取文档序第一。
2. **ordinal-fallback 层**（label_source = ordinal_fallback）：无
   任何对象携带标签 N 时 → 同族（image / table）元素列表文档序第
   N 个对象（1 ≤ N ≤ 族内总数）。
   已知噪声面（v1 接受并披露）：pdfplumber 把版面装饰性图形也计为
   image 对象（acad-03 论文 5 图实抽出 28 个 image 对象），
   fallback 层的"第 N 个"可能与语义图号错位——Layer C 评测按端到端
   结果度量，不为 fallback 层单独调参。
3. 两层皆不中 → 不生成（端点缺失不生成，沿批次 4 原则）。

## §5 多重度与排除

- 一个文本元素可产多条引用边（多 label、双家族）；每 (from, label)
 至多一条。
- 解析失败（编号越界且无标签命中）不生成、不报错、不 warning。
- 引用通道不改变任何元素类型（与 W1 题注定型风险不同面：句首
  "Figure 3 shows…" 在引用语义下是真实提及，应产边）。

## §6 版本语义

- schema 0.6.0 relation.type 为自由串 → 不升 schema_version。
- writer 行为变化（新增 relation 类型产出）→ 构成 evaluation
  revision 升版条件 A（relation generation 新增，r84 Q1）；W2 合入
  后的下一评测 revision 承载。

## §7 验收（r85 W2 v1 标准）

- explicit reference extraction implemented（纯函数
  `match_reference_relations(elements, caption_relations)`，装配点
  fallback parser pdf/docx 两分支）。
- gold sampled explicit references 验证：acad-03 credential 抽查
  11 条显式引用边（勘误后权威计数 9+11）逐条对照 from 侧 marker 与
  to 侧家族。
- negative sentence cases：无编号泛指（"see the figure below" /
  "结果如上表所示"）不产边；编号越界不产边；caption 元素不作
  from 侧；词内噪声行为钉住（"turntable 5" 命中 "table 5"——§3
  已知代价，测试固化非缺陷认定）。

## §8 契约测试

纯函数直接喂构造 elements：caption-label 命中 / ordinal-fallback
命中 / 越界不生成 / 同元素同 label 去重 / 双家族多边 / caption 不
作 from / 拉丁词内不命中 / determinism（同输入同输出）。真样本验收
进 W2 验收记录（acad-03），holdout 不设（确定性规则 + 构造用例覆盖，
沿批次 4 "pdf 几何依赖实测值不设 holdout" 先例同理：引用匹配依赖
真实抽取流，手工推导即预跑）。
