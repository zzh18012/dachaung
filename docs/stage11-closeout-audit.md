# Stage 11 Closeout 审计（r78 授权，纯文档/只读）

日期：2026-09-23。分支 integration/stage11-closeout-audit，基点
8dc6ec8（P30' A 核验后）。性质冻结（r78 (1)-(2)）：文档 + 证据引用 +
状态审计；**零生产/测试改动**；G⑥ 凭证组装 / agreement 重跑 / gold
digest 全部禁止；顶带 / caption / 图内标签 / continued 不立项；
§3a deferred；font family 扩展暂停。

## ① 批次台账（Stage 11 全部 Closed / 追认）

| 批次 | 内容 | 裁决 |
|------|------|------|
| 11a | 布局重构架构冻结（raw words 一等输入；区域/候选层放词流与元素流之间；五防护面；commit 级回退；11-B 三门未过不实施） | r70 立项 / r71 冻结确认 |
| 14 | 词级属性加富：char 几何事后连接 fontname/font_size（中心落 bbox ±0.5pt，取覆盖 x 跨度最大 char），词边界零触碰，零行为漂移验收（六语料全字段 deep-equal） | r72 立项 / r73 Closed |
| 15 | Tier-2 font/layout 候选设计：shadow analysis 登记候选（digit∧fontOut / 图内尺寸比 / 顶带 / font×§3a），font 只能作组合证据 | r74 追认，Tier-2 暂缓 |
| 16 | 跨语料稳定性审计：Batch 15 发现的六语料复检，四类登记（A digit∧fontOut 升候选但 blocked by r62①；B 图内尺寸比降级非候选；C 顶带架构级候选；D font×§3a 证伪） | r75 采纳 |
| 17 | r62① 边界重开设计：466/466 底带裸数字 = 页码（序列拟合 100%）∧ fontOut 100% ∧ 五类负例零落带；七问必答 + FP taxonomy T1–T5 + D3 提案 | r76 通过，D3 立项 |
| 18 | D3 实施：page_furniture_digit_page_number（Tier-2 首消费点），验收全绿 + 消融两组 | r77 Closed |

## ② Tier-2 演进链（验证闭环）

```
word attribute layer（Batch 14，采集零消费）
        ↓
Tier-2 候选设计 + 跨语料稳定性（Batch 15/16，shadow only）
        ↓
r62① 边界重开（Batch 17：信息面变化消解原始排除理由）
        ↓
D3 page number furniture（Batch 18：首消费点，单点回滚）
```

fontOut 与 size-cap 冻结为 D3 **必要条件**（r77 (3.2)）：语料
466/466 + fontOut 100%；合成反例证明去 fontOut 误杀 T4（底带
正文族数字）、去 size-cap 误杀 T2（章节装饰数字）——存在必要
性证明完成，非经验规则堆叠。

## ③ Final Baseline 冻结表（Stage 11 口径）

证据 = outputs/batch18i_accept.py + batch18i_accept_report.txt
（六语料 vs batch14i_after 冻结基线逐元素 diff，唯一允许差异 =
D3 改型）：

| 语料 | 元素 | heading | chunk | D3 | vs Stage 10 基线 @aaff3df |
|------|------|---------|-------|-----|--------------------------|
| real-02 | 110 | 17 | 44 | 0 | 零变化（D1=12 / D2=2 / form_label_* 16 / form_option_repeat 18 全不变） |
| real-04 | 18 | 3 | 24 | 0 | 零变化 |
| acad-03 | 71 | 9 | 97 | 0 | 零变化 |
| prod-01 | 1308 | 427→**394** | 892→**869** | **恰 33** | 唯一差异 = D3；chunk 覆盖剖面恒等 |
| tech-08 | 979 | 307 | 545 | 0 | 零变化 |
| tech-03 | 4258 | 1297→**1064** | 1547→**1351** | **恰 233** | 唯一差异 = D3；chunk 覆盖剖面恒等 |

行为与回归（@8dc6ec8 = closeout 基点，同树复跑）：
- 全量回归：**5684 passed / 26 skipped / 0 failed**（Batch 18
  记录 5684/26/0 同值）
- guards（批次 4/6/9/12 契约 + Batch 14 属性 + Batch 18 D3）：
  95 passed（五文件）+ 72 passed / 4 skipped（题注契约三文件，
  skip = samples/private 本机资产缺失，既有行为）——与 Batch 18
  记录一致

suppression reason 注册集：7（Stage 10 终态）+ 1
（page_furniture_digit_page_number）= 8 reason；76（Stage 10）
+ 266（D3：prod-01 33 + tech-03 233）。

## ④ residual taxonomy 终局登记

| 类别 | 项 | 处置 |
|------|-----|------|
| 已消费 | digit∧fontOut 家族 | D3（Batch 18） |
| 降级非候选 | 图内尺寸比 | Batch 16 降级，维持 |
| 架构级候选不立批 | 顶带页眉 | r75(6) / r77 / r78 维持 |
| 不扩展 | caption / 图内标签 / continued | r78 冻结清单 |
| deferred | §3a（无线框表格） | 维持 deferred |
| 形态冻结 | 日期 / 罗马数字 / 文件名 | r62① 排除维持（无新证据，Batch 17 仅重开裸数字一项） |
| 开放风险类 | T4 底带非页码数字 | 零实例登记；D3 独立 reason code 单点回滚即保险 |

known residual 九家族（Stage 10 Batch 13 登记）维持登记不修。

## ⑤ G⑤/G⑥ 状态表（r78 (4)(5)，只读）

**G⑤：1/4 完成**（口径 = r3 代表页 §149/§151 冻结）：

| 篇 | 状态 | 依据 |
|----|------|------|
| acad-03 | ✅ 完成（首件召回 → v2 最终件 → agreement → 仲裁追认） | §109–§112，r63 |
| tech-08 | ⏳ 补交（首件 r3rev 部分交回：14 代表页已标 8、缺 6 页 279 行、EXCLUDE 未保留 base、entries 缺第 5 元素 ×2） | §162 |
| prod-01 | ⏳ 等回收（r3 任务包已外发） | §149 |
| tech-03 | ⏳ 等回收（r3 任务包已外发） | §149 |

**tech-08 越界 21 页处置（r78 (4) 裁决）：严格口径作废**——
越界页不是补充信息而是改变采样框架：不进标注统计、不进
agreement、不进 gold candidate、不改 pair-map。补交要求维持
§162.2：(a) 补缺失 6 页（p050/071/075/078/082/083）；(b) 恢复
EXCLUDE_BASE | 座位号 结构；(c) 修复 entries 块第 5 元素 ×2。
不允许：并入越界 21 页结果 / 扩大页集 / 修改代表页设计。

**G⑥：NOT READY**——四篇最终 decision/agreement 未齐（1/4）。
G⑥ 申请材料清单（§82）仅 acad-03 一篇可组装。gold freeze /
gold digest / 24-core gold_revision 全部禁止（r78 (5)）。

## ⑥ Stage 11 关闭后路线（r78 (6)）

进入**待命 / 低频轮换**，不启动新解析规则批。主线风险已从
parser 行为正确性转移到标注收敛与冻结凭证完整性。下一主动
事件：G⑤ 三篇回收 → 四篇 decision/agreement 汇总 → G⑥ freeze
条件检查。

## ⑦ 零漂移验证（本批零实现的结构证明）

- `git diff 8dc6ec8 -- app tests schemas evaluation scripts` 为空；
  tracked 新增仅本文档；
- 探针与验收证据全在 gitignored outputs/（batch18i_after /
  batch18i_accept_report.txt）；
- 本批不 import 生产管线写路径，不触碰 gold / agreement /
  annotations 任何文件。
