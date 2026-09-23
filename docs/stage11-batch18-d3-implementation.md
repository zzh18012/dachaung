# Stage 11 Batch 18 — D3 底带裸数字页码抑制实施（r76 授权）

日期：2026-09-23。分支 integration/stage11-batch18-page-number-font-consumption，
基点 80e817b（P29' A 已核验）。授权（r76，§173）：实现 D3 =
`page_furniture_digit_page_number`（独立 reason code，非 D1 扩展、非通用
digit detector、非 font classifier）；synthetic fixtures；real-02 + 六语料
只读验收；消融两组（去 fontOut / 去 size-cap）。

## 实现（app/parsers/fallback_parser.py，单文件单点）

- `_PAGE_FURNITURE_DIGIT_RE = re.compile(r"\d{1,4}")`（r62① 重开的
  唯一形态边界：1-4 位裸数字；日期/罗马数字/文件名维持冻结）。
- `_PAGE_FURNITURE_DIGIT_SIZE_CAP = 1.2`（r76④ 冻结：观察上界 1.11
  + 8% 余量；T2 章节装饰数字 r=60.76 被 ≥3 个数量级隔离）。
- `_doc_font_stats(words_by_page)`：top-3 = 全文档词级 fontname
  （非 None）按词计数前 3，Counter 并列先插入者胜（页序+行序确定）；
  body_mode = 全文档词级 font_size（round 0.1）众数。文档级而非页级
  （页码字体跨页一致；Batch 15/16/17 观察面全部文档级口径）。
- `_element_font_features(element, words_by_page, top3)`：词中心落
  元素 bbox ±0.5pt 计包含（与 Batch 14 连接规则同口径）；主导字体 =
  元素内非 None fontname 众数；字号取最大（混排以最显眼字号为准）。
  无任何非 None fontname → (None, False, None) 保守不命中。
- 消费点唯一：`_suppress_page_furniture_headings` 新增第三参
  `words_by_page=None`（None = D3 整体不激活，批次 9 既有两参调用
  零变化）；判定顺序 D1 → D2 → D3（重复裸数字仍归 D2）。命中仅改
  type heading→paragraph + 追加 metadata.heading_suppressed。
- `_parse_pdf` 接线：既有的每页 annotated words 存入 words_by_page
  传入后置过滤。`_classify_pdf_paragraph` / short_line / DOCX 路径 /
  表格检测零触碰（r76① 边界）。

## r76③④ 参数钉死回执

| 项 | 钉死值 | 退化行为 |
|----|--------|---------|
| size-cap r | 元素内最大词字号 / 文档字号众数 | body_mode 不可得 → D3 整体不激活 |
| 元素缺 font_size | max_size=None → 不命中（存活） | — |
| 多字体混排元素 | 字号取最大 | 大字混入即超 cap → 存活 |
| top-3 计算 | 文档级词计数前 3 | 全文档无非 None fontname → top3 空集，此时元素主导字体必为 None → 不命中（保守退化由元素侧分支保证，不依赖 top3 空集语义） |
| 词属性缺失 | fontname/font_size None 不计入统计 | 元素内全 None → 不命中 |

## 测试（tests/test_pdf_digit_page_number_furniture.py，18 项）

手写多字体最小 PDF 夹具（4 字体固定对象：F1 Helvetica / F2 Courier /
F3 Times-Roman / F4 Times-Bold；三正文族挤满 top-3，F4 页码圈外——
Batch 15 登记的"极简 PDF 第二字体 unknown"实为其夹具对象编号错位，
Times-Bold 可正常解析，正例 e2e 因此可行）。

- 端到端：底带圈外裸数字抑制 + 页中同字体存活；D1 优先级零变化；
  正文族底带数字存活（fontOut 反向）；24pt 存活（size-cap 反向，
  y 标定 93.014% 批次 9 口径）；重复裸数字归 D2；管线 schema +
  element_id 严格递增 + 抑制计数精确。
- 单元：命中矩阵；size 12.0 边界恰过 / 13.0 存活；属性全 None 存活；
  仅缺 size 存活；words 通道 None 不激活（D1 照常）；全文档无字号
  不激活；混排取最大；形态边界（"12345"/"7."/"iv"/"report.pdf"/
  "-3" 存活；4 位 "2026" 在 \d{1,4} 内命中）；结构保持（仅 type +
  metadata 键变化）；确定性重复。
- 夹具校准注记：行聚类段间距阈值 1.5×行高（16pt）——20pt 基线行距
  视觉空隙仅 9.3pt 会并段，正文行距取 40pt；同页两个底带元素须
  空隙 >16pt 否则并段（首版 y=57.4/y=35 间距 11.7pt 被并成
  "Page 01 1"，改 y=25）。

## 验收（outputs/batch18i_accept.py + 报告，r76(6) 预冻结指标）

vs 冻结基线 outputs/batch14i_after（六语料全量管线输出）：

- **real-02**：D3=0，heading 17→17，D1=12 / D2=2 / form_label_*（16）
  / form_option_repeat（18）全部不变；elements/relations/warnings/
  chunks 深比较恒等（chunk 44 不变）。
- **prod-01**：D3 恰 33（heading 427→394）；chunks 892→869（heading
  硬边界移除的确定性下游）；覆盖剖面 dup/missing 与基线恒等、extra 空。
- **tech-03**：D3 恰 233（heading 1297→1064）；chunks 1547→1351 同上。
- **real-04 / acad-03 / tech-08**：D3=0，全字段零漂移（tech-08 的
  form_label_multi_colon=1 / page_furniture_band_repeat=8、tech-03 的
  band_repeat=6 等既有 reason 全部不变）。
- 全语料：relations / warnings 深比较恒等；元素 id/顺序/计数恒等；
  唯一差异 = D3 改型（逐元素分类断言）。

## 消融（ANALYSIS-ONLY，r76：证明条件为什么存在，非优化数字）

- **语料侧**（基线 heading 面生产函数复算）：P1 digit∧band∧heading =
  P2 +fontOut = P3 +size-cap = prod-01 33 / tech-03 233 / 其余 0；
  去 fontOut 变体 = 去 size-cap 变体 = 同数。当前语料上两条件零增量
  ——它们防护的是零实例开放风险类：
- **合成面**（生产谓词存活 / 变体误杀）：
  - T4 底带正文族数字（fontOut=False, size_ok=True）：生产 D3 存活；
    **去 fontOut 变体误杀**——fontOut 是 T4 唯一区分信号。
  - T2 章节装饰数字（fontOut=True, 24pt, r=2.4）：生产 D3 存活；
    **去 size-cap 变体误杀**——size-cap 是大字装饰唯一防线。
- 独立 reason code + 单点分支 = 单点回滚（关闭 D3 分支重跑基线即恢复）。

## 回归与 guards

- 全量回归：**5684 passed / 26 skipped / 0 failed**（53.42s；基线
  5666 + 本批新增 18，零回归）。
- guards（批次 4/6/9/12 契约 + Batch 14 属性 + 本批 D3，八文件）：
  95 passed（家具/表单/属性/D3 五文件）+ 72 passed / 4 skipped
  （题注契约三文件，skip = samples/private 本机资产缺失）。

## 边界遵守（r76 冻结清单逐项）

- 消费点仅 `_suppress_page_furniture_headings`；D1/D2 正则与行为
  零变化（19 项批次 9 测试 + D1 优先级新证）。
- 不触碰 `_classify_pdf_paragraph` / short_line / Tier-1 / DOCX /
  表格检测；不引入文档级隐式学习（top-3/众数是钉死的只读统计，
  无反馈回路）。
- 未改顶带 / continued / 图内标签 / §3a / 新 font residual 家族。
- schema 未动（metadata 追加键为既有 heading_suppressed 通道）。
