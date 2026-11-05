# 结题提交包清单（SUBMISSION_PACKAGING）

> r104 §二十剩余主工作之一。截止 2026-12-13。本清单为提交打包的权威
> checklist；所有内容物数字面以 docs/final-report.md 与
> docs/evidence-manifest.md 登记值为唯一来源。

## 1. 提交包内容物清单

| # | 内容物 | 位置 | 状态 | 责任 |
|---|---|---|---|---|
| 1 | 学校结题报告（正式版） | 基于 docs/school-materials-draft.md 改写 | **PENDING_USER_TEMPLATE**（等学校模板 + 格式字段） | 用户供模板 → 协调者改写 |
| 2 | 技术结题报告（母稿） | docs/final-report.md | READY（r104 ACCEPTED_COMPLETE） | — |
| 3 | 答辩 PPT | 基于 docs/defense/outline.md 制片 | PENDING_PRODUCTION（底稿 READY） | 用户确认载体后制作 |
| 4 | 答辩讲稿/Q&A 备答 | docs/defense/outline.md | READY | — |
| 5 | 终测证据包 manifest | docs/evidence-manifest.md | READY（r104 ACCEPTED_COMPLETE） | — |
| 6 | 演示页 | docs/demo.md | READY（r103 ACCEPTED） | — |
| 7 | 项目 README（结题收口版） | README.md | READY（远程 fecff0e 起生效） | — |
| 8 | 代码与复现入口 | 本仓 + docs/final-report.md §12 | READY | — |
| 9 | 台账与裁决链（审计备用） | adoption 仓 ADOPTION.md §1-§233 | READY（随 push 同步） | — |

## 2. 数字一致性（已核声明）

final-report / evidence-manifest / README / defense-outline / school-draft
五份材料的全部指标数字同源于已裁决登记值：comparison 门 0.8297 / 0.7635 /
0.7004 / 0.7378、24/24 schema valid、ARI 0.3345 vs B1 0.2658 / B2 0.2621 vs
oracle 0.4159（80.43%，NOT MET 粒度归因）、Layer C P 1.0 / R 0.35 /
F1 0.5185（fixed-anchor acad-03 / 20 edges）。无重算、无口径改写。

## 3. 口径纪律终检（提交前逐项勾选）

- [ ] ARI 目标 0.75 / NOT MET 与系统/基线/oracle 同表出现
- [ ] relation P/R/F1 三值同报 + fixed-anchor scope 明示
- [ ] holdout 表述为 INFORMATIONAL / WITH_KNOWN_ANCHOR_EXPOSURE
- [ ] extended-N 仅作诊断件表述
- [ ] parser 双身份写法（canonical main b872347 / execution adoption r7 port + r55 C08 delta）
- [ ] 学校模板格式字段由用户填写，不改动技术内容

## 4. 提交前待办时序

1. 两仓待推 commits 全部获批推送（随 r105 简报请批）；
2. 学校模板到位 → 正式结题报告改写（内容取 school-materials-draft，零重算）；
3. 答辩 PPT 制片（数字取 defense/outline.md）；
4. 用户填写格式字段并自行审阅全部材料；
5. 最终打包（zip/提交媒介按学校要求）+ 提交；
6. 提交后本清单状态更新为 CLOSED。

## 5. 边界

- 本清单属 FINALIZATION ARTIFACTS（docs/packaging），不触发 r8、不重开
  protected split、不改任何冻结面（r104 §十八）。
- 代码仓最终状态以远程 main 为准；adoption 台账以远程集成分支为准；
  自跑线独立推进不进入提交包（INDEPENDENT_CONTINUE 边界）。
