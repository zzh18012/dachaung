# 显式引用 relation 契约（Stage 10 批次 1）

状态：v1（2026-09-10 十六轮裁决批准开工）。

裁决依据（搬运线十六轮，ADOPTION §九十八）："给 fallback_parser 增加
正文显式引用 → 已识别图/表对象的系统预测能力。现有 caption 关系保持
兼容；允许识别类似'见图 X / 如表 N 所示 / Figure X / Table N'等明确
引用，但**不得以单纯最近距离作为歧义对象的最终消歧依据**。编号或
名称在上下文中不能唯一落实到具体 occurrence 时，宁可不产边，也不要
猜 nearest-wins。"

边界（同裁决）：最终评测指标为 **untyped relation edge 的 P/R/F1**，
不新增 caption/xref/implicit 分类型成绩，不往 gold 的 linked_nontext
塞 relation type；本批不做 system↔gold 对齐协议（若 P/R/F1 需要
text-anchor identity 新规则，属指标定义问题，单独提交裁决）。

## §1 编号 token 语法与引用前缀集

- **编号 token**（caption 侧与引用侧同语法，匹配要求严格相等）：
  `[0-9]+(?:[.\-][0-9]+)*` —— ASCII 数字，可带 `.` / `-` 续段
  （`3`、`12`、`3.5`、`3-1`）。数字限 ASCII（全角数字不识别，与
  批次 4/7 caption 契约一致）。
- **figure 家族引用前缀**：`(?<![A-Za-z])(?:Figures|Figure|Figs\.?|Fig\.?|图)`
  —— 英文词前不得是字母（防 `Config 3` / `subfigure 3` 拼接误配）；
  中文"图"无前置条件（`见图 3` / `如图3所示` / `图 3 显示` /
  `（图 3）` 均命中）。
- **table 家族引用前缀**：`(?<![A-Za-z])(?<!图)(?:Tables|Table|表格|表)`
  —— 额外要求"表"前不是"图"（`图表 3` 不落 table 家族）。
- 前缀与编号之间允许零或多个空白（`图3` 与 `图 3` 等价）。

## §2 形状与排序

- relation 形状：`type="references"`，`from_id`=正文文本元素，
  `to_id`=图/表对象元素（image 或 table）。方向与 caption 关系
  相反（caption 是 `对象 --has_caption--> 题注`；引用是
  `正文 --references--> 对象`）。
- `metadata`：`{"rule": "explicit_reference_unique", "token": "<编号 token>"}`
  —— token 为命中该目标的编号（诊断用；目标对象经 caption 唯一
  配对后 token 与目标一一对应，同元素重复引用去重后保留首现 token）。
- 排序沿用契约 §2（caption-relation-contract.md）：全部 relations
  合并后按 `(type, from_id, to_id)` 字典序稳定排序——这是系统边的
  canonical projection。

## §3 匹配规则（唯一性守卫，禁 nearest-wins）

纯函数 `match_reference_relations(elements, caption_relations)`：

1. **编号索引**：遍历 `caption_relations`（`has_caption` → figure
   家族；`table_has_caption` → table 家族），从 `to_id` 题注元素
   文本起始提取编号 token（题注前缀集 = 冻结的
   `_FIGURE_CAPTION_RE` / `_TABLE_CAPTION_RE` 前缀 + §1 token
   语法），建立 `(家族, token) → [对象 element_id]` 索引。题注
   解析不到对应元素或提取不出 token 的条目跳过（防御）。
2. **引用扫描**：来源元素 = `type ∉ {caption, image, table}` 且
   content 非空的元素（题注自身、图/表对象不作为引用来源——题注
   编号是锚，不是引用）。对 content 全文 finditer 两个家族的引用
   正则。
3. **唯一性守卫**：`(家族, token)` 在索引中对应**恰好 1 个对象**
   才产边；0 个（编号无对应题注对象）或 ≥2 个（同编号多对象，
   如分章重复编号）一律不产边。**任何情形不用距离/顺序猜目标**。
4. **去重**：同一来源元素对同一目标只产 1 条边（同 token 重复
   引用、多 token 同目标均合并）。

## §4 版本分支

- schema 0.7.0（本批 writer 能力）：relations 允许包含
  `type="references"`。
- 0.1.0–0.6.0 读格式守卫：relations 不得包含 `references`（与
  has_caption→0.4.0、table_has_caption→0.5.0 同款模式，
  docs/schema-version-policy.md）。
- writer 一律输出 `SCHEMA_VERSION_CURRENT="0.7.0"`；旧版本仅为
  legacy 读入格式。

## §5 边界与已知限制

- **复合编号题注不可解析**：题注分类契约（批次 4/7）要求数字后随
  `[\.、\s]` 分隔，`图 3-1：` 不被分类为 caption → 无
  has_caption → 不进编号索引 → 对其的引用不产边（保守）。
- **CJK 复合词假阳性可能**："版图 3" / "地图 3 幅" 类前缀拼数字会
  命中 figure 家族（编号唯一时产边）。无 Cue 词要求是为覆盖
  "图 3 显示 /（图 3）" 形态；此为已知精度损失，不逐词加黑名单。
- **英文复数只取首个编号**："Figures 3 and 4" 只解析 Figure 3
  （and 链不展开）。
- **区间引用不展开**："图 3-5" / "图 3~5" 解析为复合 token
  （无匹配）或单 token（见上），不枚举区间成员。
- **无题注对象不可达**：目标必须是 caption 关系已配对的图/表
  （"已识别图/表对象"）；无题注的图无法被编号解析。
- **非 fallback parser 不产出**：本批能力仅在 fallback pdf/docx
  路径；md/html/text/ipynb 零 references（同 caption 关系现状）。
- **评测零改动**：evaluation 只按精确 type 消费
  （has_caption/table_has_caption），references 不进入任何现有
  指标键；untyped edge P/R/F1 属后续单独裁决的指标定义批次。
