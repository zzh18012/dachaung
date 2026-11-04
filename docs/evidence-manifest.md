# 终测证据包 manifest（FINAL_EVAL_EVIDENCE_PACKAGE）

> r103 裁决（2026-11-03）批准归档。原始证据文件位于 adoption 仓 gitignored 私有域
> `samples/private/stage9-corpus/evaluation/stage9-eval-terminal-reval-r1/`，
> 按裁决**不复制原始 corpus/gold/证据文件进公开仓**；本 manifest 仅登记
> 文件名、SHA-256、角色、来源 revision 与生成时间戳，供结题审计时按 digest 比对复算。

## 证据清单

| 文件 | SHA-256（前 16 位 / 全量可复算） | 角色 | 来源 revision | 生成时间 (UTC) |
|---|---|---|---|---|
| `freeze_record.json` | `243c1701933c08eb`… | 六要素执行前冻结（parser 身份 / runner / manifest / gold digest / deps / 指标配置） | stage9-eval-terminal-reval-r1 | 2026-11-02T12:59:46Z |
| `metrics.json` | `f087a3153285f317`… | aggregate 步产物：layerB 聚合 + layerC + parser versions + 逐篇稳定计数 | stage9-eval-terminal-reval-r1 | 2026-11-03T08:09:40Z |
| `comparison_gate.json` | `e0c69e1fc23d0842`… | gate 步产物：comparison 回归门判定 **PASS / regressions = 0** | stage9-eval-terminal-reval-r1 | 2026-11-03T08:09:47Z |
| `terminal_comparison.json` | `6f4b3b83151fe5b2`… | 权威比对：**136 稳定字段精确相等，mismatches = 0 → REPRODUCED_IDENTICAL** | stage9-eval-terminal-reval-r1 | 2026-11-03T08:09:55Z |
| `error_registry.json` | `149596c4af27d8a7`… | 伴随件：system_errors 46 条登记（taxonomy 稳定面） | stage9-eval-terminal-reval-r1 | —（aggregate 伴随产物） |
| `layerB_per_doc_raw.json` | `d596a73dbf08f127`… | 伴随件：48 个 process_single 逐篇原始面（2 parser × 24 docs） | stage9-eval-terminal-reval-r1 | 2026-11-03T01:07:55Z |

裁决四件最低集（freeze_record / terminal_comparison / gate / comparison_gate）已全部覆盖；
后两件为 aggregate/layerB 伴随原始面，超集登记便于深度审计。

## 关键判定值（与上表证据一一对应）

- `FINAL_REPRODUCIBILITY_STATUS = REPRODUCED_IDENTICAL`（136/136 稳定字段精确相等）
- `comparison gate = PASS / regressions = 0`
- gold runtime digest `8b0c2a8c…` == credential **MATCH**（六要素第④项）
- parser 双身份写法（r103 §五 record-precision）：
  canonical accepted parser revision = `main b872347`；
  evaluation execution implementation = `adoption r7 port with previously disclosed r55 C08 delta`

## 边界

- `stage9-eval-terminal-reval-r1` 是 FINAL REPRODUCIBILITY SNAPSHOT，**不是 r8**，不改变 baseline 链（r7 = FINAL_FROZEN_BASELINE）。
- protected comparison/holdout 恰一次终测读取授权已消耗，两者恢复 PROTECTED（holdout 口径 INFORMATIONAL_WITH_KNOWN_ANCHOR_EXPOSURE）；不得为结题写作重新执行评测。
- 本 manifest 属 docs/evidence metadata（r103 §十四），不改变 evaluation。
