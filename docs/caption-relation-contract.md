# 图片 caption 关联契约（Stage 6 批次 4）

状态：草案 v1（2026-08-30 前置裁定已下，条文与数值阈值送批）。

裁决依据：2026-08-30 会话 6a911adf 批次 3 封口裁决第 ④ 项——caption
文本只进 caption 自身 element；显式 relation
`image --has_caption--> caption`；不复用 parent_id；relation 以稳定
element_id 引用、去重且确定性排序；无法明确判断或端点缺失不生成；
caption 正常进 chunk；版本升 0.4.0；契约冻结 relation schema、缺失
与歧义行为。

## §0 盘点（2026-08-30）

- caption element 仅 fallback parser 产出：pdf `_classify_pdf_paragraph`
  与 docx 均用 `_CAPTION_RE`（`^(Table|Figure|Fig\.?|表|图)\s*数字`）。
- md/html/text/ipynb/kreuzberg 均不产 caption element → 端点缺失，
  天然不生成关系。
- 六个 parser 现状 `relations=[]`；Relation dataclass 与 schema
  relation 定义（type/from_id/to_id/metadata）均已具备，无需改形状。
- chunker 现状：caption 单独成 chunk、image 不参与分块——本批不动。
- devset 实测依据：DC-MVP-001（docx）image@para16 + 图题注@para17
  （紧邻下一段），表题注@para12（不关联）；DC-MVP-001-PDF 同页
  caption bbox.top−image bbox.bottom = 11.5pt（图下方紧邻）。

## §1 范围（本批锁死）

- 仅 fallback pdf/docx 产出 `has_caption` relation。
- 不做 caption 识别扩展：不新增 md `![alt]`/html `<figcaption>` 等
  caption element 语义（alt 仍是 image.metadata.alt，不是 caption）。
- 不做表格题注关联（`Table|表` 前缀的 caption element 保持现状，
  只作为普通元素；表关联留给未来批次）。
- 图题注前缀集（冻结，2026-08-30 裁决①）：`Figure`、`Fig`（含
  `Fig.`）、`图`，数字限 ASCII，即
  `^(?:Figure|Fig\.?|图)\s*[0-9]+[\.、\s]`（大小写语义沿现状）。
  `Table`/`表` 前缀不是图题注。caption element 分类用的
  `_CAPTION_RE`（含全角数字 `[0-9０-９]`）本批不改——两口径分工：
  分类归 `_CAPTION_RE`，关联归前缀集。

## §2 relation 形状冻结

- `type = "has_caption"`；`from_id` = image element_id；`to_id` =
  caption element_id（方向固定 image → caption，不允许反向）。
- `metadata.rule`（必填，string）= 判定规则名：
  - docx：`"docx_adjacent_paragraph"`
  - pdf：`"pdf_geometry_below"`
- `metadata.gap_pt`（仅 pdf，number ≥ 0）= caption.bbox.top −
  image.bbox.bottom（pdfplumber 坐标，图下方为正）。
- 不写 parent_id；caption.parent_id / image.parent_id 维持现状（None）。
- 排序：relations 输出按 `(type, from_id, to_id)` 字典序稳定排序；
  同一 `(type, from_id, to_id)` 至多一条（构造上不会重复，测试固化）。

## §3 判定规则（确定性，端点缺失/歧义一律不生成）

### docx：紧邻下一段

对每个 image element（locator.paragraph_index = P）：
仅当存在图题注 caption element 满足 `paragraph_index == P + 1` 时生成
一条 relation。该 caption 必须以图题注前缀集开头（`Table`/`表` 开头
的 caption 不算）。一图至多一 relation；一 caption 至多被一 image
命中（P 唯一）。

### pdf：同页下方几何紧邻

候选条件（全部满足才进入配对）：
1. caption 与 image 同 `page`；
2. 图题注前缀集开头；
3. `gap = caption.bbox[1] − image.bbox[3] > 0`（题注在图下方）；
4. `gap ≤ CAPTION_MAX_GAP_PT = 50`（pdfplumber pt，冻结值）；
5. x 方向区间相交（`min(caption.x1, image.x1) − max(caption.x0,
   image.x0) > 0`）。

全局唯一配对（消除多对多歧义）：所有候选 (image, caption, gap) 三元组
按 `(gap, image_id, caption_id)` 升序排序，依次配对；任一端点已被
配对则跳过该三元组。gap 并列最小不特殊放弃——排序键完整确定，
无随机性。

两规则共同的缺失行为：无图、无图题注、候选不满足条件 → 该图零
relation（不报错、不产 warning；关联是能力不是义务）。

## §4 版本语义

- writer 形状变化（新增 relation 产出能力）→ `schema_version`
  升 `0.4.0`；`effective_schema_version` 无条件返回 0.4.0
  （writer 能力语义，批次 2/3 已确立）。
- schema：enum 加 `0.4.0`；新增分支：schema_version ∈
  {0.1.0, 0.2.0, 0.3.0} 时 relations **不得包含**
  `type=="has_caption"`（`not.contains` 精确排除）；0.4.0 分支不新增
  必填项（无图文档 relations 为空合法）；`metadata.rule`/
  `gap_pt` 的键语义在 0.4.0 分支不另设 schema 约束（方向性与端点
  存在性由契约测试固化，schema 层不做跨数组引用校验）。
- 0.1.0–0.3.0 全部维持合法读格式。

## §5 不变量

- caption element 的 content/type/locator/metadata 不因本批改变；
  image element 同；chunker 行为与 chunk 形状不变（caption 仍单独
  成 chunk，image 仍不进 chunk）。
- 既有 relation 语义（本批前 relations 恒空）不受影响。
- Determinism：同一输入字节 + 同一解析器版本 → 同一 relation 集合
  （含排序与 gap_pt 数值）。

## §6 契约测试与 holdout

- 判定逻辑实现为纯函数（输入 elements 列表，输出 relations），
  契约测试直接喂构造 elements：docx 紧邻命中 / 上一段不命中 /
  表题注不关联 / 无题注不生成；pdf 同页下方命中 / 超阈值不生成 /
  非重叠不生成 / 多对多唯一配对与排序；版本分支四向
  （0.3.0 拒 has_caption、0.4.0 含与不含均合法）。
- pdf 真样本断言进 dev 验收（DC-MVP-001-PDF 期望
  `e0011 --has_caption--> e0009`，引用基线 commit 63b05ce 先例，
  记录于报告）。
- holdout：合成 docx fixture（python-docx 生成：两图两图题注 + 一表
  题注 + 无题注图），期望 relation 集合实现前手工推导冻结，固定干净
  SHA 一次性首跑，封存 outputs/，不重跑。合成 docx 及其内嵌图片
  资源**生成一次后字节固定**（sha256 登记于 ADOPTION.md），运行时
  不得重新生成（2026-08-30 裁决⑤：防运行时漂移）。pdf 沿用批次 3
  追认的偏差先例不进 holdout（几何判定依赖 pdfplumber 实测 bbox，
  手工推导等于预跑），dev 验收引用固定基线哈希；md/html/text/ipynb
  无 caption 产出，以回归测试断言零 has_caption relation，不设
  holdout。

## §7 明确不做（本批）

- 不做 md/html `<figcaption>`/alt 的 caption 语义。
- 不做表格题注关联。
- 不做 caption 在图上方的关联（图题注惯例在下方；上方一律不生成）。
- 不做跨页关联、不做 OCR、不改 chunker。
